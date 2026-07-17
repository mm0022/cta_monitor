from cta_monitor.models import ReportRow, RowStatus
from cta_monitor.render import render_table_text


def _row(status=RowStatus.OK, ticker="DOGE/USDT"):
    return ReportRow(
        ticker=ticker, mark_price=0.07187, trade_size=2500.0,
        order_notional_u=179.0, qty_change="-128815.0→-97875.9", delta_qty=30939.1,
        n_orders=12.3, maker_ratio=0.75, end_ms=1783987839911, start_ms=1783987729868,
        duration_ms=110043, twap_unfilled_qty=1376.0, unfilled_u=98.9, completion_pct=95.55,
        status=status,
    )


def test_render_text_has_header_and_rows():
    txt = render_table_text([_row(), _row(RowStatus.RUNNING, "BTC/USDT")], "测试标题")
    assert "测试标题" in txt
    assert "TICKER" in txt and "完成%" in txt
    assert "DOGE/USDT" in txt and "BTC/USDT" in txt
    # 百分比显示：maker 整数%、完成 两位小数%
    assert "75%" in txt and "95.55%" in txt
    # 运行中行带状态标记
    assert "运行中" in txt
    # 每列等宽对齐：表头行与数据行列数一致
    lines = [l for l in txt.splitlines() if "|" in l]
    assert len({l.count("|") for l in lines}) == 1
