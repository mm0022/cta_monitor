import pytest

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
    # SIGNAL_TS 是 UTC 日期时间字符串 -> 解析成 UTC ms
    table = [
        HEADER,
        "DOGE/USDT,BINANCE_PERP,2500,2026-07-16 12:00:00,STOP,tr1,-97000,-97875.9",
        "BTC/USDT,BINANCE_PERP,0.012,2026-07-16 12:00:00,RUNNING,tr2,-0.16,-0.16",
    ]
    rows = parse_financials("spec1", "acc1", table, COLS)
    assert len(rows) == 2
    r0 = rows[0]
    assert isinstance(r0, BiyiRow)
    assert r0.strategy_name == "spec1" and r0.account == "acc1"
    assert r0.ticker == "DOGE/USDT" and r0.venue == "BINANCE_PERP"
    assert r0.trade_size == 2500.0
    assert r0.signal_time_ms == 1784203200000  # 2026-07-16 12:00:00 UTC
    assert r0.txn_status == "STOP"
    assert r0.tracing_id == "tr1"
    assert r0.current_inventory == -97000.0
    assert r0.target_inventory == -97875.9
    assert rows[1].txn_status == "RUNNING"


def test_parse_financials_missing_column_fail_loud():
    # 表头缺 TRADE_SIZE 列 -> fail-loud KeyError（不 silent）
    bad_header = "TICKER|str,VENUE|str,SIGNAL_TIME|num,TASK_STATE|str,TRACING_ID|str,CURRENT_INVENTORY|num,TARGET_INVENTORY|num"
    with pytest.raises(KeyError):
        parse_financials("spec1", "acc1", [bad_header, "DOGE/USDT,BINANCE,1000,stop,tr1,-1,-1"], COLS)
