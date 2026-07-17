"""ReportRow 列表 → 等宽对齐文本表（Slack 代码块用）。"""
from __future__ import annotations

import unicodedata

from cta_monitor.metrics import trunc_to
from cta_monitor.models import ReportRow, RowStatus


def _disp_width(s: str) -> int:
    """显示宽度：CJK 全角/宽字符按 2 列计，其余按 1 列。"""
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)


def _pad(cell: str, width: int) -> str:
    """按显示宽度右侧补空格到 width。"""
    return cell + " " * (width - _disp_width(cell))

# 列与 Excel 导出保持一致（14 列；不含 报单笔数/结束时间/开始时间）
_HEADERS = [
    "账户", "状态", "TICKER", "mark", "单笔粒度", "单笔报单u",
    "决策持仓", "目标", "delta", "maker%", "执行ms",
    "未完成量", "未完成u", "未完成%",
]


# 账户别名（全名 → 短名）；未在表中的账户回退到去前缀
_ACCOUNT_ALIAS = {
    "binance_client_asf_managed_trade1": "asf",
    "binance_cta_client_luminova_trade1": "luminova",
    "binance_tokyo_cta_momentum_test1_new": "test_new",
    "binance_tokyo_cta_momentum_trade1": "momentum1",
}


def short_account(account: str) -> str:
    """账户短名/别名：优先用 _ACCOUNT_ALIAS，否则去掉 binance_/cta_ 前缀段。"""
    if account in _ACCOUNT_ALIAS:
        return _ACCOUNT_ALIAS[account]
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


def _q(v) -> str:
    """qty 列：截断到 6 位小数、去尾零（与 Excel 一致）。None/空 → ''。"""
    if v is None or v == "":
        return ""
    s = f"{trunc_to(float(v), 6):.6f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def _split_change(s: str) -> tuple[str, str]:
    """'cur→target' → (cur, target)；无箭头 → ('', '')。"""
    return tuple(s.split("→", 1)) if "→" in s else ("", "")


def _cells(r: ReportRow) -> list[str]:
    cur, tgt = _split_change(r.qty_change)
    return [
        short_account(r.account),
        _STATUS_TAG.get(r.status, r.status.value),
        r.ticker,
        _fmt(r.mark_price), _fmt(r.trade_size), _fmt(r.order_notional_u),
        _q(cur), _q(tgt), _q(r.delta_qty),
        "" if r.maker_ratio is None else f"{r.maker_ratio * 100:.2f}%",   # maker% 两位小数
        _fmt(r.duration_ms),
        _q(r.twap_unfilled_qty), _q(r.unfilled_u),
        "" if r.incomplete_pct is None else f"{r.incomplete_pct:.2f}%",   # 未完成% 两位小数
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
