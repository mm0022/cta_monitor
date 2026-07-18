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


from unittest.mock import MagicMock

import cta_monitor.pipeline as pipeline_mod
from cta_monitor.pipeline import run_once
from cta_monitor.config import Config, PgConfig, BiyiConfig, DatahubConfig, SlackConfig
from cta_monitor.models import BiyiRow, SignalRecord, RowStatus, TradeAgg


def _cfg(accounts=(), portfolio_accounts=None):
    return Config(
        pg=PgConfig("h", "1", "u", "p", "shiji"),
        biyi=BiyiConfig("lu", "bu", "u", "pw"),
        datahub=DatahubConfig("g", "k", "CYBERX_PROD"),
        slack=SlackConfig("wh"),
        accounts=tuple(accounts),
        min_notional_u=10.0,
        freshness_hours=1.0,
        portfolio_accounts=portfolio_accounts or {},
    )


def _biyi_row(ticker, account, spec, **kw):
    base = dict(
        strategy_name=spec, account=account, ticker=ticker, venue="BINANCE",
        trade_size=100.0, signal_time_ms=1000, txn_status="stop",
        tracing_id="t", current_inventory=50.0, target_inventory=50.0,
    )
    base.update(kw)
    return BiyiRow(**base)


def _pipe_sig(ts=1000, **kw):
    base = dict(mark_price=1.0, current_qty_at_decision=0.0, target_qty=50.0,
                delta_qty=50.0, signal_bar_ts_ms=ts)
    base.update(kw)
    return SignalRecord(**base)


_NOW = 20_000_000
_FRESH_TS = _NOW - 10          # 在 1h 窗内
_STALE_TS = _NOW - 4 * 3600_000  # 4h 前


def test_run_once_respects_account_allowlist():
    biyi = MagicMock()
    biyi.strategy_list_all.return_value = {"specX": "accX", "specY": "accY"}
    biyi.fetch_financials.side_effect = lambda spec, acc: [_biyi_row("DOGE/USDT", acc, spec)]
    datahub = MagicMock()
    datahub.latest_signal.return_value = _pipe_sig(ts=_FRESH_TS)  # trade_size100/delta50 -> BELOW_TRADE_SIZE, 不查PG
    res = run_once(_cfg(accounts=["accX"]), _NOW, biyi=biyi, datahub=datahub)
    assert res.stale is False
    # allowlist 只保留 accX -> 只处理 specX/accX 一行
    assert [r.ticker for r in res.rows] == ["DOGE/USDT"]
    biyi.fetch_financials.assert_called_once_with("specX", "accX")


def test_run_once_stale_gate_returns_no_new_signal():
    biyi = MagicMock()
    biyi.strategy_list_all.return_value = {"specX": "accX"}
    biyi.fetch_financials.side_effect = lambda spec, acc: [_biyi_row("DOGE/USDT", acc, spec)]
    datahub = MagicMock()
    datahub.latest_signal.return_value = _pipe_sig(ts=_STALE_TS)
    res = run_once(_cfg(), _NOW, biyi=biyi, datahub=datahub)
    assert res.stale is True
    assert res.rows == []
    assert "没有新信号" in res.summary


def test_run_once_portfolio_account_uses_per_token(monkeypatch):
    # 组合级账户：走 latest_portfolio_signals（拆 per_token），不走 latest_signal
    biyi = MagicMock()
    biyi.strategy_list_all.return_value = {"specP": "accP"}
    biyi.fetch_financials.side_effect = lambda spec, acc: [
        _biyi_row("DOGE/USDT", acc, spec, trade_size=10.0, signal_time_ms=_FRESH_TS),
        _biyi_row("BTC/USDT", acc, spec, trade_size=10.0, signal_time_ms=_FRESH_TS),
    ]
    datahub = MagicMock()
    datahub.latest_portfolio_signals.return_value = {
        "doge": _pipe_sig(ts=_FRESH_TS), "btc": _pipe_sig(ts=_FRESH_TS),
    }
    monkeypatch.setattr(pipeline_mod, "fetch_trades", lambda *a, **k: [])
    monkeypatch.setattr(pipeline_mod, "aggregate_trades", lambda rows: None)
    res = run_once(
        _cfg(portfolio_accounts={"accP": "xs_carry_daily"}),
        _NOW, biyi=biyi, datahub=datahub,
    )
    datahub.latest_portfolio_signals.assert_called_once_with("accP", "xs_carry_daily")
    datahub.latest_signal.assert_not_called()
    assert sorted(r.ticker for r in res.rows) == ["BTC/USDT", "DOGE/USDT"]


def test_run_once_drops_rows_with_stale_signal():
    # 同账户两个币：一个信号新鲜、一个超 3h -> 只统计新鲜的那个
    biyi = MagicMock()
    biyi.strategy_list_all.return_value = {"specX": "accX"}
    biyi.fetch_financials.side_effect = lambda spec, acc: [
        _biyi_row("DOGE/USDT", acc, spec),
        _biyi_row("XRP/USDT", acc, spec),
    ]
    def latest(account, coin):
        return _pipe_sig(ts=_FRESH_TS) if coin == "doge" else _pipe_sig(ts=_STALE_TS)
    datahub = MagicMock()
    datahub.latest_signal.side_effect = latest
    res = run_once(_cfg(), _NOW, biyi=biyi, datahub=datahub)
    assert res.stale is False
    assert [r.ticker for r in res.rows] == ["DOGE/USDT"]  # 超 3h 的 XRP 被过滤


def test_run_once_ok_demotes_to_no_trades_when_no_fills(monkeypatch):
    biyi = MagicMock()
    biyi.strategy_list_all.return_value = {"specX": "accX"}
    # trade_size=10, delta=50 -> 5>=1; notional 50>=10; signal_time_ms==ts -> OK
    biyi.fetch_financials.side_effect = lambda spec, acc: [
        _biyi_row("DOGE/USDT", acc, spec, trade_size=10.0, signal_time_ms=_FRESH_TS)
    ]
    datahub = MagicMock()
    datahub.latest_signal.return_value = _pipe_sig(ts=_FRESH_TS)
    monkeypatch.setattr(pipeline_mod, "fetch_trades", lambda *a, **k: [])
    monkeypatch.setattr(pipeline_mod, "aggregate_trades", lambda rows: None)
    res = run_once(_cfg(), _NOW, biyi=biyi, datahub=datahub)
    assert [r.status for r in res.rows] == [RowStatus.NO_TRADES]


def test_run_once_ok_fills_maker_from_agg(monkeypatch):
    biyi = MagicMock()
    biyi.strategy_list_all.return_value = {"specX": "accX"}
    biyi.fetch_financials.side_effect = lambda spec, acc: [
        _biyi_row("DOGE/USDT", acc, spec, trade_size=10.0, signal_time_ms=_FRESH_TS)
    ]
    datahub = MagicMock()
    datahub.latest_signal.return_value = _pipe_sig(ts=_FRESH_TS)
    monkeypatch.setattr(pipeline_mod, "fetch_trades", lambda *a, **k: [object()])
    monkeypatch.setattr(pipeline_mod, "aggregate_trades",
                        lambda rows: TradeAgg(maker_ratio=0.5, start_ms=1, end_ms=2, duration_ms=1))
    res = run_once(_cfg(), _NOW, biyi=biyi, datahub=datahub)
    assert res.rows[0].status == RowStatus.OK
    assert res.rows[0].maker_ratio == 0.5
