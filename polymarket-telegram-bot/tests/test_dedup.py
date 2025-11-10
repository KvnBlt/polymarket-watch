from src.polymarket_client import dedupe_trades


def test_dedupe():
    seen = set()
    trades = [
        {"id": "1", "txHash": None, "timestamp": 1, "title": "A"},
        {"id": "2", "txHash": "0x2", "timestamp": 2, "title": "B"},
        {"id": "2", "txHash": "0x2", "timestamp": 2, "title": "B"},
    ]
    out = dedupe_trades(trades, seen)
    assert len(out) == 2
