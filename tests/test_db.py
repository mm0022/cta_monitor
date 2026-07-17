from cta_monitor.db import aggregate_trades, signal_ms_to_beijing
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


def test_signal_ms_to_beijing():
    # 2026-07-17 06:07:00 北京 == 2026-07-16 22:07:00 UTC
    ms = 1784239620000
    assert signal_ms_to_beijing(ms) == "2026-07-17 06:07:00"
