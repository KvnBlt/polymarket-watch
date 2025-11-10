from src.formatter import format_trade_message


def test_format_basic():
    trade = {
        "timestamp": 1700000000,
        "side": "BUY",
        "size": 100,
        "price": 0.5,
        "title": "Test Market",
        "txHash": "0xabc",
    }
    msg = format_trade_message(trade)
    assert "Test Market" in msg
    assert "BUY" in msg
    assert "0xabc" in msg
