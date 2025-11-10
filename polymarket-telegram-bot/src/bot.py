"""Telegram bot helpers (using python-telegram-bot in simple, synchronous style).
Dry-run mode supported to avoid sending messages in CI.
"""
from __future__ import annotations

import logging
from typing import Iterable, Mapping, Optional

from telegram import Bot  # python-telegram-bot

from .formatter import format_trade_message

logger = logging.getLogger(__name__)


def send_alerts(trades: Iterable[Mapping[str, any]], bot_token: str, chat_id: str, dry_run: bool = False):
    """Send formatted messages for each trade to the given chat_id.
    If dry_run is True, messages are logged instead of sent.
    """
    messages = [format_trade_message(t) for t in trades]
    if dry_run:
        for m in messages:
            logger.info("[dry-run] would send to %s: %s", chat_id, m.replace('\n', ' | '))
        return

    bot = Bot(token=bot_token)
    for m in messages:
        try:
            bot.send_message(chat_id=chat_id, text=m)
        except Exception as exc:
            logger.exception("Failed to send Telegram message: %s", exc)


# Handler stubs for commands (to be wired into real handler functions if using async framework)
def handle_mirror_command(trade_id: str):
    """Stub for mirroring a trade: TODO implement transaction creation/signing/sending.
    Keep a clear TODO for future work.
    """
    # TODO: implement mirroring: build transaction, sign with PRIVATE_KEY, broadcast to RPC
    logger.info("mirror command received for trade_id=%s (stub)", trade_id)
    return {"status": "stub", "trade_id": trade_id}
