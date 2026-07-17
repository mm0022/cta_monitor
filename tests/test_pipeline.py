from cta_monitor.models import SignalRecord
from cta_monitor.pipeline import is_stale


def _sig(ts):
    return SignalRecord(mark_price=1, current_qty_at_decision=0, target_qty=1, delta_qty=1, signal_bar_ts_ms=ts)


def test_is_stale_true_when_all_old():
    now = 10_000_000
    assert is_stale([_sig(now - 4 * 3600_000)], now, 1.0) is True


def test_is_stale_false_when_fresh():
    now = 10_000_000
    assert is_stale([_sig(now - 10_000)], now, 1.0) is False


def test_is_stale_true_when_empty():
    assert is_stale([None, None], 10_000_000, 1.0) is True
