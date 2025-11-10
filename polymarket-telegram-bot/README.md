# Polymarket Telegram Bot (scaffold)

This repository folder contains a lightweight scaffold for a Telegram bot that watches Polymarket trades and sends alerts to Telegram chats.

Quick start (local):

1. Copy `config.yaml.example` to `config.yaml` and adjust addresses/filters.
2. Create a `.env` file or set environment variables: `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_IDS`, `RPC_URL`, `PRIVATE_KEY` (private key only if you implement mirroring).
3. Install deps:

```bash
python -m pip install -r polymarket-telegram-bot/requirements.txt
```

4. Run once (dry-run):

```bash
cd polymarket-telegram-bot
python -m src.main --dry-run --once
```

Notes/TODOs:
- `/mirror <tradeId>` handler is a stub; real mirroring requires building and signing transactions and is intentionally left for later (TODO).
- The bot currently uses synchronous `python-telegram-bot` helpers; for production you may switch to an async library.
