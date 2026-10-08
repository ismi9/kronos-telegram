"""Збір даних з Kraken + прогноз Kronos + графік. Без ботової логіки."""
import os
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import urllib.request

KRAKEN_PAIRS = {
    "BTC": "XBTUSD",
    "ETH": "ETHUSD",
    "SOL": "SOLUSD",
    "XRP": "XRPUSD",
}

MODEL_REPO = os.environ.get("KRONOS_MODEL", "NeoQuasar/Kronos-small")
SCENARIOS = int(os.environ.get("KRONOS_SCENARIOS", "5"))


def fetch_candles(pair: str, interval_min: int = 60) -> pd.DataFrame:
    """Свічки з публічного API Kraken (без ключа)."""
    import json
    url = f"https://api.kraken.com/0/public/OHLC?pair={pair}&interval={interval_min // 60}"
    req = urllib.request.Request(url, headers={"User-Agent": "kronos-bot/1.0"})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    key = [k for k in data["result"] if k != "last"][0]
    rows = data["result"][key]
    df = pd.DataFrame(rows, columns=[
        "time", "open", "high", "low", "close", "vwap", "volume", "count"])
    df["timestamps"] = pd.to_datetime(df["time"], unit="s", utc=True)
    for c in ("open", "high", "low", "close", "volume"):
        df[c] = df[c].astype(float)
    return df[["timestamps", "open", "high", "low", "close", "volume"]]


def make_forecast(asset: str, pred_hours: int, lookback: int = 400) -> dict:
    """Власне прогноз. Повертає dict: текст, png (bytes), статистика."""
    asset = asset.upper()
    pair = KRAKEN_PAIRS.get(asset, asset)

    df = fetch_candles(pair)
    df = df.iloc[:-1]  # неповна поточна свічка
    pred_len = max(1, min(pred_hours, 96))
    lookback = min(lookback, len(df) - pred_len - 1)
    if lookback < 64:
        raise ValueError("Замало історії для прогнозу (потрібно >= 64+pred годин)")

    # лінивий імпорт: /start працює без завантаження torch-моделі
    from kronos import Kronos, KronosTokenizer, KronosPredictor

    x_df = df.iloc[-(lookback + pred_len):-pred_len][["open", "high", "low", "close", "volume"]]
    x_ts = df.iloc[-(lookback + pred_len):-pred_len]["timestamps"]
    y_ts = df.iloc[-pred_len:]["timestamps"]

    tokenizer = KronosTokenizer.from_pretrained(
        "NeoQuasar/Kronos-Tokenizer-2k" if "mini" in MODEL_REPO else "NeoQuasar/Kronos-Tokenizer-base")
    model = Kronos.from_pretrained(MODEL_REPO)
    predictor = KronosPredictor(model, tokenizer, max_context=512, device="cpu")

    preds = [
        predictor.predict(x_df, x_ts, y_ts, pred_len, top_p=0.9, T=1.0, verbose=False)
        for _ in range(SCENARIOS)
    ]
    closes = pd.concat([p["close"].reset_index(drop=True) for p in preds], axis=1)
    median = closes.median(axis=1)
    lo, hi = closes.min(axis=1), closes.max(axis=1)

    last_close = float(x_df["close"].iloc[-1])
    final_med = float(median.iloc[-1])
    delta = (final_med - last_close) / last_close * 100
    up = int((closes.iloc[-1] > last_close).sum())

    buf = _plot(df, lookback, pred_len, median, lo, hi, asset)
    return {
        "asset": asset, "pair": pair, "pred_len": pred_len,
        "last_close": last_close, "final_med": final_med,
        "delta": delta, "up": up, "scenarios": SCENARIOS,
        "png": buf, "model": MODEL_REPO.split("/")[-1],
    }


def _plot(df, lookback, pred_len, median, lo, hi, asset):
    import io
    hist = df.iloc[-(lookback + pred_len):-pred_len]
    fig, ax = plt.subplots(figsize=(11, 5), dpi=110)
    xs = list(range(lookback + pred_len))
    ax.plot(xs[:lookback], hist["close"].values, color="#4a6fa5", lw=1.5,
            label="Історія")
    # лінія від останньої точки історії до першої точки прогнозу
    ax.plot(xs[lookback - 1:], np.r_[hist["close"].iloc[-1], median.values],
            color="#e63946", lw=2, ls="--", label="Прогноз Kronos (медіана)")
    ax.fill_between(xs[lookback - 1:], np.r_[hist["close"].iloc[-1], lo.values],
                    np.r_[hist["close"].iloc[-1], hi.values],
                    color="#e63946", alpha=0.15, label="Коридор сценаріїв")
    ax.axvline(lookback - 1, color="#666", ls=":", lw=1)
    ax.set_title(f"Kronos: {asset} 1h — прогноз {pred_len} год", fontsize=13)
    ax.set_xlabel("години")
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def format_reply(res: dict) -> str:
    arrow = "📈" if res["delta"] >= 0 else "📉"
    return (
        f"{arrow} <b>{res['asset']}/USD</b> — прогноз Kronos на {res['pred_len']} год\n"
        f"Зараз: <b>${res['last_close']:,.0f}</b>\n"
        f"Медіана через {res['pred_len']} год: <b>${res['final_med']:,.0f}</b> "
        f"({res['delta']:+.2f}%)\n"
        f"Сценаріїв вгору: {res['up']}/{res['scenarios']} · "
        f"модель: {res['model']}\n"
        f"<i>Дослідний прогноз, не є фінансовою порадою.</i>"
    )
