"""Format trades into Telegram-friendly text messages."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping, Optional


def format_trade_message(trade: Mapping[str, any]) -> str:
    ts = trade.get("timestamp")
    if ts:
        dt = datetime.fromtimestamp(float(ts), tz=timezone.utc).astimezone()
        time_str = dt.strftime("%d/%m/%Y %H:%M:%S")
    else:
        time_str = "unknown"
    side = (trade.get("side") or "").upper()
    side_emoji = "🟢" if side == "BUY" else "🔴" if side == "SELL" else "⚪"
    size = trade.get("size")
    price = trade.get("price")
    try:
        shares = int(float(size) / float(price)) if size and price and float(price) != 0 else None
    except Exception:
        shares = None
    shares_str = f"{shares:,}" if shares is not None else "N/A"
    title = trade.get("title") or trade.get("marketSlug") or "Unknown market"
    msg = (
        f"⏰ {time_str}\n"
        f"{side_emoji} Action: {side}\n"
        f"🎯 Parts: {shares_str}\n"
        f"💰 Montant total: {size or 'N/A'} USDC\n"
        f"💵 Prix: {price or 'N/A'} USDC\n"
        f"🎲 Marché: {title}\n"
        f"🔗 Tx: {trade.get('txHash') or trade.get('id') or 'n/a'}"
    )
    return msg
