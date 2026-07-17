from cta_monitor.db import aggregate_trades, signal_ms_to_utc_str
from cta_monitor.models import TradeRow


def test_aggregate_none_on_empty():
    assert aggregate_trades([]) is None


def test_aggregate_maker_ratio_by_notional():
    rows = [
        TradeRow(is_maker=1, quantity=10, price=2.0, event_time=1000),   # maker 20u
        TradeRow(is_maker=0, quantity=10, price=2.0, event_time=1500),   # taker 20u
        TradeRow(is_maker=1, quantity=10, price=2.0, event_time=1200),   # maker 20u
    ]
    agg = aggregate_trades(rows)
    assert agg is not None
    assert abs(agg.maker_ratio - (40 / 60)) < 1e-9
    assert agg.start_ms == 1000
    assert agg.end_ms == 1500
    assert agg.duration_ms == 500


def test_aggregate_timing_spans_all_events_maker_only_fills():
    # 执行窗口跨全部事件（下单/撤单）；maker 只从 FULL_EXEC 成交算
    rows = [
        TradeRow(is_maker=0, quantity=0, price=0, event_time=900, event_type="NEW"),
        TradeRow(is_maker=1, quantity=10, price=2.0, event_time=1000, event_type="FULL_EXEC"),
        TradeRow(is_maker=0, quantity=10, price=2.0, event_time=1500, event_type="FULL_EXEC"),
        TradeRow(is_maker=0, quantity=0, price=0, event_time=2000, event_type="CANCEL"),
    ]
    agg = aggregate_trades(rows)
    assert agg is not None
    assert agg.start_ms == 900 and agg.end_ms == 2000  # 跨全部事件
    assert agg.duration_ms == 1100
    assert abs(agg.maker_ratio - 20 / 40) < 1e-9        # 仅 FULL_EXEC 计 maker


def test_signal_ms_to_utc_str():
    # app_receive 实测为 UTC，故信号时间也按 UTC 格式化
    ms = 1784239620000
    assert signal_ms_to_utc_str(ms) == "2026-07-16 22:07:00"


def test_aggregate_zero_notional_no_div_error():
    rows = [
        TradeRow(is_maker=1, quantity=0.0, price=2.0, event_time=1000),
        TradeRow(is_maker=0, quantity=0.0, price=3.0, event_time=1200),
    ]
    agg = aggregate_trades(rows)
    assert agg is not None
    assert agg.maker_ratio == 0.0     # total_notional==0 -> 0.0, 不抛异常
    assert agg.start_ms == 1000 and agg.end_ms == 1200
