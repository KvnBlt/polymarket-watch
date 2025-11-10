"""Lightweight Polymarket client reused from polymarket-watch logic.
Provides fetch_trades and simple deduplication utilities.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence

import requests

logger = logging.getLogger(__name__)
BASE_URL = "https://data-api.polymarket.com"
TRADES_ENDPOINT = "/trades"
ACTIVITY_ENDPOINT = "/activity"
TRADE_LIMIT = 1000
HTTP_TIMEOUT = 10
MAX_RETRIES = 1
BACKOFF_SECONDS = 2


class PMError(RuntimeError):
    pass


def _perform_request(url: str, params: Mapping[str, Any]):
    return requests.get(url, params=params, timeout=HTTP_TIMEOUT)


def _coerce_timestamp(trade: Mapping[str, Any]) -> Optional[int]:
    raw = trade.get("timestamp") or trade.get("created_at") or trade.get("createdAt")
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value > 1e12:
        value /= 1000.0
    return int(value)


def _to_float(val) -> Optional[float]:
    try:
        return float(val)  # type: ignore
    except Exception:
        return None


def _normalize_trade(trade: Mapping[str, Any], address: str, timestamp: int) -> Dict[str, Any]:
    def pick(*keys, source=None):
        containers = [trade]
        if source:
            containers.insert(0, source)
        for container in containers:
            for k in keys:
                v = container.get(k) if isinstance(container, Mapping) else None
                if v not in (None, ""):
                    return v
        return None

    tx_hash = pick("txHash", "transactionHash", "tx_hash", "id")
    title = pick("title", "question", "name") or "Unknown market"
    slug = pick("marketSlug", "slug")
    outcome = pick("outcome", "outcomeToken", "token") or trade.get("side")

    return {
        "address": address,
        "timestamp": timestamp,
        "title": title,
        "outcome": outcome,
        "side": (trade.get("side") or "").upper() or None,
        "size": _to_float(trade.get("size") or trade.get("amount") or trade.get("quantity")),
        "price": _to_float(trade.get("price")),
        "txHash": tx_hash,
        "id": trade.get("id"),
        "marketSlug": slug,
    }


def fetch_trades(address: str, since_epoch: int) -> List[Dict[str, Any]]:
    """Fetch recent trades for an address from Polymarket data API and return normalized trades newer than since_epoch."""
    if not address:
        return []
    params = {"user": address, "limit": TRADE_LIMIT}
    last_err = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            r = _perform_request(f"{BASE_URL}{TRADES_ENDPOINT}", params)
            if r.status_code == 200:
                payload = r.json()
                records = payload.get("data", {}).get("trades", {}).get("records") or []
            else:
                # fallback to activity
                r2 = _perform_request(f"{BASE_URL}{ACTIVITY_ENDPOINT}", params)
                if r2.status_code == 200:
                    payload = r2.json()
                    records = payload.get("data", {}).get("activity", {}).get("activities", {}).get("results") or []
                else:
                    r.raise_for_status()
            # process records
            out = []
            for raw_trade in records:
                ts = _coerce_timestamp(raw_trade)
                if ts is None or ts <= since_epoch:
                    continue
                out.append(_normalize_trade(raw_trade, address, ts))
            return out
        except Exception as exc:
            last_err = exc
            logger.debug("Polymarket fetch attempt %s failed: %s", attempt, exc)
            if attempt < MAX_RETRIES:
                time.sleep(BACKOFF_SECONDS)
            else:
                break
    raise PMError(last_err or "Failed to fetch trades")


# Simple deduplication helper: keep trades that are not present in seen set (by txHash or id)
def dedupe_trades(trades: Sequence[Mapping[str, Any]], seen: set) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for t in trades:
        key = t.get("txHash") or t.get("id")
        if not key:
            # fallback to timestamp+title
            key = f"{t.get('timestamp')}-{t.get('title')}"
        if key in seen:
            continue
        seen.add(key)
        result.append(dict(t))
    return result
