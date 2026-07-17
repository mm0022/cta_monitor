"""ReportRow 列表 → 等宽对齐文本表（Slack 代码块用）。"""
from __future__ import annotations

import unicodedata

from cta_monitor.models import ReportRow, RowStatus


def _disp_width(s: str) -> int:
    """显示宽度：CJK 全角/宽字符按 2 列计，其余按 1 列。"""
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)


def _pad(cell: str, width: int) -> str:
    """按显示宽度右侧补空格到 width。"""
    return cell + " " * (width - _disp_width(cell))

_HEADERS = [
    "账户", "状态", "TICKER", "mark", "单笔粒度", "单笔报单u", "币量变化", "delta",
    "报单笔数", "maker%", "结束时间", "开始时间", "执行ms",
    "未完成量", "未完成u", "完成%",
]


def _short_account(account: str) -> str:
    """账户短名：去掉 binance_ / cta_ 冗余段，保留可区分尾部。"""
    return account.replace("binance_", "").replace("cta_", "")

# 异常状态行首标记（正常留空）
_STATUS_TAG = {
    RowStatus.OK: "",
    RowStatus.RUNNING: "运行中",
    RowStatus.SMALL_NOTIONAL: "小额",
    RowStatus.BELOW_TRADE_SIZE: "未下单",
    RowStatus.SIGNAL_TIME_MISMATCH: "⚠时间不符",
    RowStatus.NO_TRADES: "⚠无成交",
    RowStatus.NO_SIGNAL: "⚠无信号",
}


def _fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def _cells(r: ReportRow) -> list[str]:
    return [
        _short_account(r.account),
        _STATUS_TAG.get(r.status, r.status.value),
        r.ticker,
        _fmt(r.mark_price), _fmt(r.trade_size), _fmt(r.order_notional_u),
        r.qty_change, _fmt(r.delta_qty), _fmt(r.n_orders),
        "" if r.maker_ratio is None else f"{round(r.maker_ratio * 100)}%",   # H 整数百分比
        _fmt(r.end_ms), _fmt(r.start_ms), _fmt(r.duration_ms),
        _fmt(r.twap_unfilled_qty), _fmt(r.unfilled_u),
        "" if r.completion_pct is None else f"{r.completion_pct:.2f}%",       # N 两位小数百分比
    ]


def render_table_text(rows: list[ReportRow], title: str) -> str:
    """标题 + 等宽表（列按最大宽度左对齐，' | ' 分隔）。"""
    matrix = [_HEADERS] + [_cells(r) for r in rows]
    widths = [max(_disp_width(row[c]) for row in matrix) for c in range(len(_HEADERS))]

    def line(cells: list[str]) -> str:
        return " | ".join(_pad(cell, widths[c]) for c, cell in enumerate(cells))

    sep = "-+-".join("-" * w for w in widths)
    body = [line(_HEADERS), sep] + [line(row) for row in matrix[1:]]
    return title + "\n" + "\n".join(body)
