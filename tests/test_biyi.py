from cta_monitor.biyi import parse_financials
from cta_monitor.models import BiyiRow

# 合成表头（列顺序任意，解析按列名找下标）
COLS = {
    "ticker": "TICKER",
    "venue": "VENUE",
    "trade_size": "TRADE_SIZE",
    "signal_time": "SIGNAL_TIME",
    "txn_status": "TASK_STATE",
    "tracing_id": "TRACING_ID",
    "current_inventory": "CURRENT_INVENTORY",
    "target_inventory": "TARGET_INVENTORY",
}
HEADER = "TICKER|str,VENUE|str,TRADE_SIZE|num,SIGNAL_TIME|num,TASK_STATE|str,TRACING_ID|str,CURRENT_INVENTORY|num,TARGET_INVENTORY|num"


def test_parse_financials_basic():
    table = [
        HEADER,
        "DOGE/USDT,BINANCE,2500,1000,stop,tr1,-97000,-97875.9",
        "BTC/USDT,BINANCE,0.012,1000,running,tr2,-0.16,-0.16",
    ]
    rows = parse_financials("spec1", "acc1", table, COLS)
    assert len(rows) == 2
    r0 = rows[0]
    assert isinstance(r0, BiyiRow)
    assert r0.strategy_name == "spec1" and r0.account == "acc1"
    assert r0.ticker == "DOGE/USDT" and r0.venue == "BINANCE"
    assert r0.trade_size == 2500.0
    assert r0.signal_time_ms == 1000
    assert r0.txn_status == "stop"
    assert r0.current_inventory == -97000.0
    assert r0.target_inventory == -97875.9
    assert rows[1].txn_status == "running"
