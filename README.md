# Kronos Telegram

Маленький Telegram-сервіс прогнозу крипто-ринку моделлю **Kronos** —
першою відкритою foundation-моделлю для K-line свічок (AAAI 2026, MIT).

Бот тягне свіжі годинні свічки з публічного API Kraken (без ключів),
ганіє `Kronos-small` (24.7M параметрів, CPU), малює графік з коридором
сценаріїв і надсилає у чат.

## Команди

```
/forecast BTC 24    — прогноз BTC на 24 години
/forecast ETH 12    — прогноз ETH на 12 годин
/start              — довідка
```

Активи: BTC, ETH, SOL, XRP або будь-яка пара Kraken. Горизонт: 1–96 годин.

## Запуск локально

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN="токен від @BotFather"
python bot.py
```

## Деплой на Railway (рекомендовано)

1. Створи бота через @BotFather → `/newbot` → скопіюй токен
2. Заведи репо на Railway: **New Project → Deploy from GitHub repo**
   Railway сам підхватить `Dockerfile` + `railway.json`
3. У **Variables** додай:
   - `TELEGRAM_BOT_TOKEN` — обов'язково
   - `ALLOWED_CHAT_IDS` — свій Telegram ID через кому (опційно, приватність)
   - `KRONOS_MODEL` — `NeoQuasar/Kronos-base` для кращої якості (опційно)
4. Deploy → бот одразу слухає команди (long polling, webhook не потрібен)

Перший запуск займає 2–3 хвилини: модель і токенізатор завантажуються
з Hugging Face і кешуються в пам'яті процеса.

## Дисклеймер

Дослідницький інструмент. Ринки шумні, точність обмежена контекстом
512 свічок. Не є фінансовою порадою.

## Кредити

Модуль `kronos/` — vendored-код проєкту
[Kronos](https://github.com/shiyu-coder/Kronos) (MIT License).
Дані — публічний API Kraken.
