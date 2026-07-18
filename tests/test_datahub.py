from cta_monitor.datahub import datahub_key, portfolio_key, parse_portfolio_signals


def test_datahub_key():
    assert datahub_key("CYBERX_PROD", "binance_tokyo_cta_momentum_test1_new", "btc") == (
        "CYBERX_PROD-CTA_SIGNAL_PUBLISHER-LAST_PUBLISHED_V1-"
        "binance_tokyo_cta_momentum_test1_new-btc"
    )


def test_portfolio_key():
    assert portfolio_key("CYBERX_PROD", "binance_tokyo_cta_momentum_trade1", "xs_carry_daily") == (
        "CYBERX_PROD-PORTFOLIO_PUBLISHER-LAST_PUBLISHED_V1-"
        "binance_tokyo_cta_momentum_trade1-xs_carry_daily"
    )


def test_parse_portfolio_signals():
    content = {
        "signal_as_of_ts_ms": 1784332800000,
        "per_token": {
            "1000PEPE": {"mark_price": 0.0027416, "current_qty": 677459.0,
                         "target_qty": 631367.865, "delta_qty": -46091.135},
            "BTC": {"mark_price": 63903.2, "current_qty": 0.383,
                    "target_qty": 0.3937, "delta_qty": 0.0107},
        },
    }
    sigs = parse_portfolio_signals(content)
    assert set(sigs) == {"1000pepe", "btc"}          # token 小写作 coin
    s = sigs["1000pepe"]
    assert s.mark_price == 0.0027416
    assert s.current_qty_at_decision == 677459.0     # current_qty → 决策持仓
    assert s.target_qty == 631367.865
    assert s.delta_qty == -46091.135
    assert s.signal_bar_ts_ms == 1784332800000       # 组合级 signal_as_of_ts_ms 共用
