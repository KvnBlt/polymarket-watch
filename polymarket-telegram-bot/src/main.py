"""Orchestrator for the Telegram alert bot.
Supports --dry-run to avoid sending real messages (useful for CI and manual tests).
"""
from __future__ import annotations

import argparse
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

from .polymarket_client import fetch_trades, dedupe_trades
from .bot import send_alerts

logger = logging.getLogger(__name__)
DEFAULT_CONFIG = Path("config.yaml")


def load_config(path: Path) -> Dict[str, Any]:
    # Minimal loader: prefer environment variables + example config if provided
    import yaml
    if path.exists():
        with path.open() as f:
            return yaml.safe_load(f) or {}
    return {}


def main_once(config: Dict[str, Any], dry_run: bool = False) -> int:
    addresses = config.get("addresses") or []
    window = int(config.get("window_minutes", 15))
    since_epoch = int((time.time() - window * 60))
    telegram_token = os.getenv("TELEGRAM_TOKEN")
    chat_ids = os.getenv("TELEGRAM_CHAT_IDS", "").split(",") if os.getenv("TELEGRAM_CHAT_IDS") else []
    if not telegram_token or not chat_ids:
        logger.warning("Telegram token or chat IDs not set; exiting")
        return 0

    seen = set()
    for address in addresses:
        trades = fetch_trades(address, since_epoch)
        new_trades = dedupe_trades(trades, seen)
        if not new_trades:
            continue
        for chat in chat_ids:
            send_alerts(new_trades, bot_token=telegram_token, chat_id=chat.strip(), dry_run=dry_run)
    return 0


def cli() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Do not send real Telegram messages")
    parser.add_argument("--once", action="store_true", help="Run one iteration and exit")
    args = parser.parse_args()

    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = load_config(DEFAULT_CONFIG)

    if args.once or os.getenv("CI") == "true":
        return main_once(config, dry_run=args.dry_run)

    # long-running loop
    while True:
        try:
            main_once(config, dry_run=args.dry_run)
        except Exception:
            logger.exception("Error while running main loop")
        time.sleep(int(config.get("poll_interval_seconds", 900)))


if __name__ == "__main__":
    raise SystemExit(cli())