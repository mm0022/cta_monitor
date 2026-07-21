from cta_monitor.metrics import (
    coin_from_ticker,
    sym_from_ticker,
    trunc_to,
    n_orders,
    incomplete_pct,
    classify_status,
    build_row,
    SHOULD_QUERY_STATUSES,
)
from cta_monitor.metrics import account_summary
from cta_monitor.models import BiyiRow, ReportRow, SignalRecord, TradeAgg, RowStatus


def test_coin_and_sym():
    assert coin_from_ticker("DOGE/USDT") == "doge"
    assert sym_from_ticker("DOGE/USDT", "BINANCE_PERP") == "BINANCE_PERP_DOGE_USDT"
    assert coin_from_ticker("1000PEPE/USDT") == "1000pepe"


def test_trunc_to():
    # 截断（向零取整），非四舍五入
    assert trunc_to(2.287, 1) == 2.2
    assert trunc_to(12.376, 1) == 12.3
    assert trunc_to(0.0634, 1) == 0.0
    assert trunc_to(179.675, 0) == 179.0
    assert trunc_to(2.0, 1) == 2.0


def test_trunc_to_two_decimals_no_float_drift():
    assert trunc_to(0.29, 2) == 0.29
    assert trunc_to(2.01, 2) == 2.01
    assert trunc_to(4.35, 2) == 4.35
    # 仍是截断，不进位
    assert trunc_to(1.239, 2) == 1.23


def test_n_orders_truncates():
    # DOGE：30939.1 / 2500 = 12.3756 -> 截断 1 位 = 12.3（图值）
    assert n_orders(30939.1, 2500.0) == 12.3
    # AAVE：13.0376 / 5.7 = 2.287 -> 2.2（图值，roundup 会是 2.3）
    assert n_orders(-13.0376, 5.7) == 2.2


def test_incomplete_pct_doge():
    # 1376/30939.1 = 0.044486 -> 4.45（未完成比例）
    assert incomplete_pct(1376.0, 30939.1) == 4.45


def test_incomplete_pct_negative_delta():
    # 1000PEPE：L=-1, delta=-95225.8 -> 未完成 ~0
    assert incomplete_pct(-1.0, -95225.8) == 0.0


def _biyi(**kw):
    base = dict(
        strategy_name="s1", account="acc", ticker="DOGE/USDT", venue="BINANCE",
        trade_size=2500.0, signal_time_ms=1000, txn_status="stop",
        tracing_id="t1", current_inventory=-97875.9, target_inventory=-97875.9 - 1376,
    )
    base.update(kw)
    return BiyiRow(**base)


def _sig(**kw):
    base = dict(
        mark_price=0.07187, current_qty_at_decision=-128815.0,
        target_qty=-97875.9, delta_qty=30939.1, signal_bar_ts_ms=1000,
    )
    base.update(kw)
    return SignalRecord(**base)


def test_classify_running():
    assert classify_status(_biyi(txn_status="RUNNING"), _sig(), min_notional_u=10) == RowStatus.RUNNING


def test_classify_no_signal():
    assert classify_status(_biyi(), None, min_notional_u=10) == RowStatus.NO_SIGNAL


def test_classify_small_notional():
    s = _sig(delta_qty=1.0, mark_price=0.5)  # 0.5u < 10u
    assert classify_status(_biyi(), s, min_notional_u=10) == RowStatus.SMALL_NOTIONAL


def test_classify_below_trade_size():
    s = _sig(delta_qty=100.0, mark_price=1.0)  # notional 100u ok
    b = _biyi(trade_size=200.0)                # 100/200 < 1
    assert classify_status(b, s, min_notional_u=10) == RowStatus.BELOW_TRADE_SIZE


def test_classify_signal_time_mismatch():
    b = _biyi(signal_time_ms=999)
    assert classify_status(b, _sig(signal_bar_ts_ms=1000), min_notional_u=10) == RowStatus.SIGNAL_TIME_MISMATCH


def test_classify_ok():
    assert classify_status(_biyi(), _sig(), min_notional_u=10) == RowStatus.OK
    assert SHOULD_QUERY_STATUSES == {RowStatus.OK, RowStatus.SIGNAL_TIME_MISMATCH}


def test_build_row_ok_fills_all_columns():
    agg = TradeAgg(maker_ratio=0.75, start_ms=1783987729868, end_ms=1783987839911, duration_ms=110043)
    # current_inventory = target_qty + 1376 -> L = current - target = +1376, 未完成=4.45
    biyi = _biyi(current_inventory=-97875.9 + 1376)
    row = build_row(biyi, _sig(), agg, RowStatus.OK)
    assert row.ticker == "DOGE/USDT"
    assert row.order_notional_u == 179.0            # trunc(2500*0.07187)=trunc(179.675)=179
    assert row.qty_change == "-128815.0→-97875.9"
    assert row.n_orders == 12.3                      # trunc(30939.1/2500,1)=12.3
    assert row.maker_ratio == 0.75
    assert row.duration_ms == 110043
    assert row.twap_unfilled_qty == 1376.0
    assert row.incomplete_pct == 4.45               # 1376/30939.1*100
    assert row.unfilled_u == round(1376.0 * 0.07187, 6)


def test_build_row_no_signal():
    row = build_row(_biyi(), None, None, RowStatus.NO_SIGNAL)
    assert row.ticker == "DOGE/USDT"
    assert row.trade_size == 2500.0
    assert row.note == "datahub 无信号"
    assert row.status == RowStatus.NO_SIGNAL
    # sig 为空：数值列全 None
    for v in (row.mark_price, row.order_notional_u, row.delta_qty, row.n_orders,
              row.maker_ratio, row.end_ms, row.start_ms, row.duration_ms,
              row.twap_unfilled_qty, row.unfilled_u, row.incomplete_pct):
        assert v is None
    assert row.qty_change == ""


def test_build_row_no_agg_leaves_db_columns_none():
    biyi = _biyi(current_inventory=-97875.9 + 1376)
    row = build_row(biyi, _sig(), None, RowStatus.NO_TRADES)
    # DB 列（H/I/J/K）为 None
    assert row.maker_ratio is None
    assert row.end_ms is None and row.start_ms is None and row.duration_ms is None
    # 非 DB 列仍填充
    assert row.order_notional_u == 179.0
    assert row.n_orders == 12.3
    assert row.twap_unfilled_qty == 1376.0
    assert row.incomplete_pct == 4.45
    assert row.status == RowStatus.NO_TRADES


def _rr(account, maker, incomplete, status=RowStatus.OK, ticker="X/USDT",
        maker_notional=None, total_notional=None):
    return ReportRow(
        ticker=ticker, account=account, mark_price=1.0, trade_size=1.0,
        order_notional_u=1.0, qty_change="0→0", delta_qty=1.0, delta_u=1.0, n_orders=1.0,
        maker_ratio=maker, end_ms=None, start_ms=None, duration_ms=None,
        twap_unfilled_qty=None, unfilled_u=None, incomplete_pct=incomplete, status=status,
        maker_notional=maker_notional, total_notional=total_notional,
    )


def test_account_summary_maker_is_notional_weighted():
    # 账户级 maker% = 该账户所有币 maker 总成交额 / 总成交额（成交额加权，非简单平均）
    rows = [
        # BTC: maker 80/总100；DOGE: maker 540/总900 -> 加权 620/1000 = 62%（简单平均会是 70%）
        _rr("accA", 0.80, 2.0, ticker="BTC/USDT", maker_notional=80.0, total_notional=100.0),
        _rr("accA", 0.60, 20.0, ticker="DOGE/USDT", maker_notional=540.0, total_notional=900.0),
        _rr("accA", None, 100.0, status=RowStatus.SMALL_NOTIONAL, ticker="SOL/USDT"),
        _rr("accB", 1.00, 0.0, ticker="ETH/USDT", maker_notional=50.0, total_notional=50.0),
    ]
    s = {d["account"]: d for d in account_summary(rows)}
    a = s["accA"]
    assert a["n"] == 3 and a["executed"] == 2          # SOL 未执行不计
    assert a["total_notional"] == 1000.0                # 100+900 总成交额
    assert a["avg_maker"] == 62.0                       # 620/1000 加权（非简单平均 70）
    assert a["avg_completion"] == 89.0                  # 完成度=100-未完成: (98+80)/2
    assert a["worst_ticker"] == "DOGE/USDT" and a["worst_completion"] == 80.0
    assert s["accB"]["avg_maker"] == 100.0
