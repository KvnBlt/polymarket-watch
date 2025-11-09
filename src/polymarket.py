from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional, Sequence

import requests

BASE_URL = "https://data-api.polymarket.com"
TRADES_ENDPOINT = "/trades"
ACTIVITY_ENDPOINT = "/activity"
TRADE_LIMIT = 1000
HTTP_TIMEOUT = 10
MAX_RETRIES = 1
BACKOFF_SECONDS = 2

logger = logging.getLogger(__name__)
_API_CALL_COUNT = 0


class PolymarketError(RuntimeError):
    """Base exception for Polymarket client failures."""


class PolymarketServerError(PolymarketError):
    """Raised when the API responds with a 5xx or the request fails at transport level."""


def get_api_call_count() -> int:
    """Return the total number of API calls performed by this module."""
    return _API_CALL_COUNT


def reset_api_call_count() -> None:
    """Reset the API call counter. Useful for tests."""
    global _API_CALL_COUNT
    _API_CALL_COUNT = 0


def fetch_trades(address: str, since_epoch: int) -> List[Dict[str, Any]]:
    """Fetch recent trades for an address, falling back to /activity if needed."""
    if not address:
        return []

    params = {"user": address, "limit": TRADE_LIMIT}
    try:
        payload = _request_json(TRADES_ENDPOINT, params)
        records = _extract_records(payload, ("data", "trades", "records"))
    except PolymarketServerError as exc:
        logger.warning(
            "Primary /trades endpoint failed for %s (%s). Falling back to /activity.",
            address,
            exc,
        )
        payload = _request_json(ACTIVITY_ENDPOINT, params)
        records = _extract_records(payload, ("data", "activity", "activities", "results"))

    normalized: List[Dict[str, Any]] = []
    for raw_trade in records:
        timestamp = _coerce_timestamp(raw_trade)
        if timestamp is None or timestamp <= since_epoch:
            continue
        normalized_trade = _normalize_trade(raw_trade, address, timestamp)
        normalized.append(normalized_trade)
    return normalized


def format_trades_for_email(trades_by_address: Mapping[str, Sequence[Mapping[str, Any]]]) -> str:
    """Return a plain-text email body summarising trades per address in a clear, visual format."""
    blocks: List[str] = []
    
    for address, trades in trades_by_address.items():
        if not trades:
            continue
        
        sorted_trades = sorted(trades, key=lambda item: item.get("timestamp", 0), reverse=True)
        blocks.append("=" * 80)  # Visual separator
        blocks.append(f"🔍 TRADES PAR {address}")
        blocks.append("=" * 80)
        blocks.append("")  # Empty line for readability
        
        for trade in sorted_trades:
            # Format timestamp in a more readable way
            timestamp = trade.get("timestamp")
            if timestamp:
                dt = datetime.fromtimestamp(float(timestamp), tz=timezone.utc).astimezone()
                time_str = dt.strftime("%d/%m/%Y %H:%M:%S")
            else:
                time_str = "Heure inconnue"
            
            # Get trade details
            side = str(trade.get("side", "") or "").upper()
            side_emoji = "🟢" if side == "BUY" else "🔴" if side == "SELL" else "⚪"
            size = _format_decimal(trade.get("size"))
            price = _format_decimal(trade.get("price"))
            title = trade.get("title") or trade.get("marketSlug") or trade.get("eventSlug") or "Marché inconnu"
            
            # Calculate number of shares (size/price)
            try:
                shares = float(size) / float(price) if size and price and float(price) != 0 else None
                shares_str = f"{shares:,.0f}" if shares is not None else "N/A"
            except (TypeError, ValueError):
                shares_str = "N/A"

            # Format block in a clear, visual way
            trade_block = [
                f"⏰ {time_str}",
                f"{side_emoji} Action: {side}",
                f"🎯 Parts: {shares_str}",
                f"💰 Montant Total: {size} USDC",
                f"💵 Prix par part: {price} USDC",
                f"🎲 Marché: {title}",
                ""  # Empty line between trades
            ]
            blocks.extend(trade_block)
            blocks.append("-" * 40)  # Visual separator between trades
            blocks.append("")  # Empty line for readability
            
    return "\n".join(blocks)


def _request_json(endpoint: str, params: Mapping[str, Any]) -> Any:
    """Call the Polymarket API endpoint and return JSON, handling retries."""
    url = f"{BASE_URL}{endpoint}"
    last_error: Optional[Exception] = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = _perform_request(url, params)
            if response.status_code == 200:
                try:
                    return response.json()
                except ValueError as exc:
                    raise PolymarketError(f"Invalid JSON from {endpoint}: {exc}") from exc

            if response.status_code >= 500:
                last_error = PolymarketServerError(
                    f"{endpoint} responded with {response.status_code}"
                )
            else:
                response.raise_for_status()
        except (requests.RequestException, PolymarketServerError) as exc:
            last_error = exc if isinstance(exc, PolymarketError) else PolymarketServerError(str(exc))

        if attempt < MAX_RETRIES:
            time.sleep(BACKOFF_SECONDS)
        else:
            break

    if isinstance(last_error, PolymarketServerError):
        raise last_error
    raise PolymarketError(last_error or f"Unable to reach {endpoint}")


def _perform_request(url: str, params: Mapping[str, Any]) -> requests.Response:
    global _API_CALL_COUNT
    response = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
    _API_CALL_COUNT += 1
    return response


def _extract_records(payload: Any, candidate_keys: Iterable[str]) -> Sequence[MutableMapping[str, Any]]:
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in candidate_keys:
            value = payload.get(key)
            if isinstance(value, list):
                return value
        # Some endpoints embed the list inside "data" -> "trades"
        data = payload.get("data")
        if isinstance(data, dict):
            for key in candidate_keys:
                value = data.get(key)
                if isinstance(value, list):
                    return value
    return []


def _coerce_timestamp(trade: Mapping[str, Any]) -> Optional[int]:
    raw = trade.get("timestamp") or trade.get("created_at") or trade.get("createdAt")
    if raw is None:
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value > 1e12:  # milliseconds
        value /= 1000.0
    return int(value)


def _normalize_trade(trade: Mapping[str, Any], address: str, timestamp: int) -> Dict[str, Any]:
    market = _get_mapping(trade.get("market"))
    event = _get_mapping(trade.get("event"))

    def pick(*keys: str, source: Optional[Mapping[str, Any]] = None) -> Optional[Any]:
        containers = [trade]
        if source:
            containers.insert(0, source)
        for container in containers:
            for key in keys:
                value = container.get(key) if isinstance(container, Mapping) else None
                if value not in (None, ""):
                    return value
        return None

    tx_hash = pick("txHash", "transactionHash", "tx_hash", "id")
    title = pick("title", "question", "name", source=market) or pick("title", "name", source=event)
    slug = pick("marketSlug", "slug", source=market)
    event_slug = pick("eventSlug", "slug", source=event)
    condition_id = pick("conditionId", source=market)
    outcome = pick("outcome", "outcomeToken", "token") or trade.get("side")

    return {
        "address": address,
        "timestamp": timestamp,
        "title": title,
        "conditionId": condition_id,
        "outcome": outcome,
        "side": (trade.get("side") or "").upper() or None,
        "size": _to_float(trade.get("size"), trade.get("amount"), trade.get("quantity")),
        "price": _to_float(trade.get("price")),
        "txHash": tx_hash,
        "id": trade.get("id"),
        "marketSlug": slug,
        "eventSlug": event_slug,
    }


def _get_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _to_float(*values: Any) -> Optional[float]:
    for value in values:
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _format_timestamp(timestamp: Any) -> str:
    if not isinstance(timestamp, (int, float)):
        return "unknown-time"
    dt = datetime.fromtimestamp(float(timestamp), tz=timezone.utc).astimezone()
    return dt.isoformat()


def _format_decimal(value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    if value >= 100:
        return f"{value:,.0f}"
    if value >= 10:
        return f"{value:,.2f}"
    return f"{value:,.4f}"
