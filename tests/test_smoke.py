"""Легкі тести без мережі і без torch."""
import ast, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_syntax():
    for f in ("bot.py", "forecast.py", "kronos/kronos.py", "kronos/module.py"):
        ast.parse((ROOT / f).read_text(encoding="utf-8"), filename=f)


def test_pairs_mapping():
    import forecast as fc  # noqa: F401  (імпорт без запуску мережі)
    assert fc.KRAKEN_PAIRS["BTC"] == "XBTUSD"
    assert fc.KRAKEN_PAIRS["ETH"] == "ETHUSD"
