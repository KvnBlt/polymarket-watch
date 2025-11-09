from __future__ import annotations

import logging
import os
import sys
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

import yaml
from dotenv import load_dotenv

from .emailer import send_email
from .polymarket import (
    fetch_trades,
    format_trades_for_email,
    get_api_call_count,
    reset_api_call_count,
)

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = BASE_DIR / "config.yaml"
logger = logging.getLogger("polymarket_watch")


def main() -> int:
    start_time = time.perf_counter()
    load_dotenv()
    _configure_logging()

    config = _load_config(DEFAULT_CONFIG)
    window_minutes = int(config.get("window_minutes", 20))
    if window_minutes <= 0:
        raise SystemExit("window_minutes must be > 0")

    addresses = config.get("addresses") or []
    if not isinstance(addresses, list) or not addresses:
        logger.warning("No addresses configured; nothing to do.")
        return 0

    since_epoch = _compute_since_epoch(window_minutes)
    filters = config.get("filters") or {}

    reset_api_call_count()
    trades_by_address: "OrderedDict[str, List[Dict[str, Any]]]" = OrderedDict()
    total_before_filters = 0
    total_after_filters = 0

    for address in addresses:
        trades = fetch_trades(address, since_epoch)
        total_before_filters += len(trades)
        filtered = _apply_filters(trades, filters)
        total_after_filters += len(filtered)
        trades_by_address[address] = filtered

    duration = time.perf_counter() - start_time
    logger.info(
        "API calls=%s total_trades=%s filtered_trades=%s window=%s min duration=%.2fs",
        get_api_call_count(),
        total_before_filters,
        total_after_filters,
        window_minutes,
        duration,
    )

    if total_after_filters == 0:
        logger.info("No new trades found; skipping email notification.")
        return 0

    email_cfg = config.get("email") or {}
    recipient = email_cfg.get("to")
    if not recipient:
        raise SystemExit("Missing email.to in config.yaml")
    subject_prefix = email_cfg.get("subject_prefix", "[Polymarket Watch]").strip()
    subject = _build_subject(subject_prefix, total_after_filters)
    body = format_trades_for_email(trades_by_address)

    send_email(config.get("smtp", {}), recipient, subject, body)
    logger.info("Notification sent to %s", recipient)
    return 0


def _configure_logging() -> None:
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"Missing config file at {path}")
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise SystemExit("config.yaml must contain a mapping at the root")
    return data


def _compute_since_epoch(window_minutes: int) -> int:
    now = datetime.now(timezone.utc)
    delta = timedelta(minutes=window_minutes)
    return int((now - delta).timestamp())


def _apply_filters(trades: Iterable[Mapping[str, Any]], filters: Mapping[str, Any]) -> List[Dict[str, Any]]:
    min_size = filters.get("min_size")
    min_size_value = _coerce_float(min_size)
    sides = filters.get("sides") or []
    allowed_sides = {str(side).upper() for side in sides if side}

    filtered: List[Dict[str, Any]] = []
    for trade in trades:
        size = trade.get("size")
        side = (trade.get("side") or "").upper()
        if min_size_value is not None and (size is None or size < min_size_value):
            continue
        if allowed_sides and side not in allowed_sides:
            continue
        filtered.append(dict(trade))
    return filtered


def _coerce_float(value: Any) -> Any:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        raise SystemExit(f"Invalid numeric filter value: {value}")


def _build_subject(prefix: str, count: int) -> str:
    suffix = "nouveaux trades" if count > 1 else "nouveau trade"
    return f"{prefix} {count} {suffix}".strip()


if __name__ == "__main__":
    sys.exit(main())
