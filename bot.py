"""Маленький Telegram-бот: прогноз Kronos для крипто-активів.

ENV:
  TELEGRAM_BOT_TOKEN — токен бота від @BotFather (обов'язково)
  ALLOWED_CHAT_IDS   — опційно, через кому: обмежити доступ (порожньо = усім)
  KRONOS_MODEL       — опційно, за замовчуванням NeoQuasar/Kronos-small

Запуск: python bot.py (long polling, без webhook-ів).
"""
import logging
import os
import re

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (Application, CommandHandler, ContextTypes,
                          MessageHandler, filters)

import forecast as fc

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("kronos-bot")


def allowed(chat_id: int) -> bool:
    raw = os.environ.get("ALLOWED_CHAT_IDS", "").strip()
    if not raw:
        return True
    return str(chat_id) in [x.strip() for x in raw.split(",") if x.strip()]


def guard(func):
    async def wrapper(update: Update, ctx):
        if not update.effective_chat or not allowed(update.effective_chat.id):
            return
        return await func(update, ctx)
    return wrapper


@guard
async def cmd_start(update: Update, ctx):
    await update.message.reply_html(
        "Привіт! Я прогнозую рух крипти моделлю <b>Kronos</b> "
        "(foundation-модель для K-line, AAAI 2026).\n\n"
        "Команди:\n"
        "<code>/forecast BTC 24</code> — прогноз на 24 год\n"
        "<code>/forecast ETH 12</code> — на 12 год\n"
        "Активи: BTC, ETH, SOL, XRP (або будь-яка пара Kraken).\n"
        "Горизонт: 1–96 годин.\n\n"
        "<i>Досліджування, не фінансова порада.</i>"
    )


@guard
async def cmd_forecast(update: Update, ctx):
    args = ctx.args or []
    asset = args[0] if args else "BTC"
    hours = 24
    if len(args) > 1 and re.fullmatch(r"\d{1,3}", args[1]):
        hours = int(args[1])

    asset = asset.upper()
    hours = max(1, min(hours, 96))
    msg = await update.message.reply_html(
        f"⏳ Збираю свічки {asset} і рахую прогноз ({hours} год)…")
    try:
        res = fc.make_forecast(asset, hours)
    except Exception as e:
        log.exception("forecast failed")
        await msg.edit_text(f"Не вийшло: {e}")
        return
    await msg.delete()
    await update.message.reply_photo(
        photo=res["png"], caption=fc.format_reply(res), parse_mode=ParseMode.HTML)


@guard
async def fallback(update: Update, ctx):
    await update.message.reply_text("Скористайся /forecast BTC 24 — див. /start")


def main():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("forecast", cmd_forecast))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback))
    log.info("kronos-bot запущено (polling)")
    app.run_polling()


if __name__ == "__main__":
    main()
