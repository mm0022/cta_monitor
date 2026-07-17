from cta_monitor.metrics import (
    coin_from_ticker,
    sym_from_ticker,
    trunc_to,
    n_orders,
    completion_pct,
)


def test_coin_and_sym():
    assert coin_from_ticker("DOGE/USDT") == "doge"
    assert sym_from_ticker("DOGE/USDT", "BINANCE") == "BINANCE_PERP_DOGE_USDT"
    assert coin_from_ticker("1000PEPE/USDT") == "1000pepe"


def test_trunc_to():
    # 截断（向零取整），非四舍五入
    assert trunc_to(2.287, 1) == 2.2
    assert trunc_to(12.376, 1) == 12.3
    assert trunc_to(0.0634, 1) == 0.0
    assert trunc_to(179.675, 0) == 179.0
    assert trunc_to(2.0, 1) == 2.0


def test_n_orders_truncates():
    # DOGE：30939.1 / 2500 = 12.3756 -> 截断 1 位 = 12.3（图值）
    assert n_orders(30939.1, 2500.0) == 12.3
    # AAVE：13.0376 / 5.7 = 2.287 -> 2.2（图值，roundup 会是 2.3）
    assert n_orders(-13.0376, 5.7) == 2.2


def test_completion_pct_doge():
    # 1 - 1376/30939.1 = 0.95551 -> 95.55
    assert completion_pct(1376.0, 30939.1) == 95.55


def test_completion_pct_negative_delta():
    # 1000PEPE：L=-1, delta=-95225.8 -> ~100
    assert completion_pct(-1.0, -95225.8) == 100.0
