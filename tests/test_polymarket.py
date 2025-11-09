from __future__ import annotations

import time
from datetime import datetime, timezone

import pytest

from src import polymarket
from src.polymarket import PolymarketServerError, fetch_trades, format_trades_for_email


def test_format_trades_for_email_orders_entries_desc():
    timestamp_old = 1_700_000_000
    timestamp_new = timestamp_old + 600
    trades_by_address = {
        "0xabc": [
            {
                "timestamp": timestamp_old,
                "side": "sell",
                "outcome": "NO",
                "size": 12.5,
                "price": 0.44,
                "title": "Old market",
                "marketSlug": "old-market",
                "txHash": "0xold",
            },
            {
                "timestamp": timestamp_new,
                "side": "BUY",
                "outcome": "YES",
                "size": 42.0,
                "price": 0.61,
                "title": "New market",
                "marketSlug": "new-market",
                "txHash": "0xnew",
            },
        ],
        "0xdef": [],
    }

    body = format_trades_for_email(trades_by_address)
    assert "Address: 0xabc" in body
    iso_new = datetime.fromtimestamp(timestamp_new, tz=timezone.utc).astimezone().isoformat()
    iso_old = datetime.fromtimestamp(timestamp_old, tz=timezone.utc).astimezone().isoformat()
    assert body.index(iso_new) < body.index(iso_old)
    assert "slug=new-market" in body
    assert "tx=0xnew" in body


def test_fetch_trades_filters_by_since_epoch(monkeypatch):
    now = int(time.time())
    entries = [
        {"timestamp": now - 300, "side": "BUY", "size": "25", "price": "0.45", "market": {"slug": "recent"}},
        {"timestamp": now - 2400, "side": "SELL", "size": "10", "price": "0.55", "market": {"slug": "old"}},
    ]
    called_endpoints = []

    def fake_request(endpoint, params):
        called_endpoints.append(endpoint)
        return {"trades": entries}

    monkeypatch.setattr(polymarket, "_request_json", fake_request)

    result = fetch_trades("0xabc", since_epoch=now - 1200)
    assert len(result) == 1
    trade = result[0]
    assert trade["marketSlug"] == "recent"
    assert trade["size"] == 25.0
    assert trade["side"] == "BUY"
    assert called_endpoints == [polymarket.TRADES_ENDPOINT]


def test_fetch_trades_falls_back_to_activity_on_server_error(monkeypatch):
    now = int(time.time())
    responses = [
        PolymarketServerError("500 error"),
        {"activity": [{"timestamp": now, "side": "SELL", "amount": "30", "market": {"slug": "activity"}}]},
    ]
    called_endpoints = []

    def fake_request(endpoint, params):
        called_endpoints.append(endpoint)
        response = responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr(polymarket, "_request_json", fake_request)

    trades = fetch_trades("0x123", since_epoch=now - 60)
    assert len(trades) == 1
    assert trades[0]["marketSlug"] == "activity"
    assert called_endpoints == [polymarket.TRADES_ENDPOINT, polymarket.ACTIVITY_ENDPOINT]
