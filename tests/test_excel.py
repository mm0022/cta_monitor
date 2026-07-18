import pandas as pd

from cta_monitor.excel import write_report_excel
from cta_monitor.models import ReportRow, RowStatus

_COLS = [
    "账户", "状态", "TICKER", "mark_price", "单笔粒度", "单笔报单u(D)",
    "决策时持仓(cur)", "目标(target)", "delta币量(F)", "delta金额u", "maker%", "执行ms(K)",
    "执行单数", "twap未完成量(L)", "未完成金额u(M)", "未完成比例%(N)",
]


def _row():
    return ReportRow(
        ticker="DOGE/USDT", account="binance_client_asf_managed_trade1",
        mark_price=0.07191, trade_size=85.0, order_notional_u=6.0,
        qty_change="-10784.0→-11325.892210", delta_qty=-541.892210, delta_u=-38.97,
        n_orders=6.3, maker_ratio=0.7856, end_ms=2, start_ms=1, duration_ms=233325,
        twap_unfilled_qty=0.892210, unfilled_u=0.064159, incomplete_pct=0.16,
        status=RowStatus.OK,
    )


def test_write_report_excel(tmp_path):
    out = str(tmp_path / "r.xlsx")
    n = write_report_excel([_row()], out)
    assert n == 1
    df = pd.read_excel(out, engine="openpyxl")
    assert list(df.columns) == _COLS
    r = df.iloc[0]
    assert r["账户"] == "asf"                 # 别名生效
    assert r["TICKER"] == "DOGE/USDT"
    assert r["目标(target)"] == -11325.89221  # 6 位截断
    assert r["maker%"] == 78.56               # ratio*100 两位
    assert r["执行ms(K)"] == 233325
    assert r["未完成比例%(N)"] == 0.16
