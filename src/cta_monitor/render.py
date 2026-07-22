"""ReportRow 列表 → 等宽对齐文本表（Slack 代码块用）。"""
from __future__ import annotations

import unicodedata

from cta_monitor.metrics import is_low_maker, trunc_to
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
    "决策持仓", "目标", "delta", "deltaU", "maker%", "执行ms", "执行单数",
    "未完成量", "未完成u", "未完成%", "未完成",
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

# 异常状态行首标记（正常留空）。全部用标准 CJK 字符（east_asian_width=W，恒等宽）；
# 不用 emoji/符号（如 ⚠ 的 east_asian_width=N，会被 Slack 渲成 2 宽而算成 1 宽 → 串列）。
_STATUS_TAG = {
    RowStatus.OK: "",
    RowStatus.RUNNING: "运行中",
    RowStatus.SMALL_NOTIONAL: "小额",
    RowStatus.BELOW_TRADE_SIZE: "未下单",
    RowStatus.SIGNAL_TIME_MISMATCH: "时间异常",
    RowStatus.NO_TRADES: "无成交",
    RowStatus.NO_SIGNAL: "无信号",
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


def _maker_cell(r: ReportRow) -> str:
    """maker% 两位小数；命中「多单低maker」（单数>10 且 maker<70%）后缀 🐢。None → ''。"""
    if r.maker_ratio is None:
        return ""
    s = f"{r.maker_ratio * 100:.2f}%"
    return s + "🐢" if is_low_maker(r) else s


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
        _q(cur), _q(tgt), _q(r.delta_qty), _fmt(r.delta_u),
        _maker_cell(r),   # maker% 两位小数；命中「多单低maker」后缀 🐢
        _fmt(r.duration_ms), _fmt(r.order_count),
        _q(r.twap_unfilled_qty), _q(r.unfilled_u),
        "" if r.incomplete_pct is None else f"{r.incomplete_pct:.2f}%",   # 未完成% 两位小数
        "🚩" if r.truly_unfilled else "",   # 真未完成标记（剩余>1个单笔粒度）
    ]


def _grid(headers: list[str], rows_cells: list[list[str]], title: str) -> str:
    """通用等宽表：表头 + 分隔线 + 数据行，按显示宽度对齐。"""
    matrix = [headers] + rows_cells
    widths = [max(_disp_width(row[c]) for row in matrix) for c in range(len(headers))]

    def line(cells: list[str]) -> str:
        return " | ".join(_pad(cell, widths[c]) for c, cell in enumerate(cells))

    sep = "-+-".join("-" * w for w in widths)
    return title + "\n" + "\n".join([line(headers), sep] + [line(r) for r in rows_cells])


def render_table_text(rows: list[ReportRow], title: str) -> str:
    """标题 + 明细等宽表。"""
    return _grid(_HEADERS, [_cells(r) for r in rows], title)


_SUMMARY_HEADERS = ["账户", "统计", "已执行", "未完成数", "总交易额u", "平均maker%", "平均完成度%", "完成度最低"]


def render_account_summary(rows: list[ReportRow], title: str = "按账户汇总（maker比例 / 完成度）") -> str:
    """按账户的简报：总交易额、平均 maker%、平均完成度%、完成度最低的币。"""
    from cta_monitor.metrics import account_summary

    def pct(v) -> str:
        return "" if v is None else f"{v:.2f}%"

    cells = []
    for s in account_summary(rows):
        worst = f"{s['worst_ticker']} {pct(s['worst_completion'])}" if s["worst_ticker"] else ""
        cells.append([
            short_account(s["account"]),
            str(s["n"]), str(s["executed"]), str(s["unfilled_n"]),
            f"{s['total_notional']:.0f}",
            pct(s["avg_maker"]), pct(s["avg_completion"]), worst,
        ])
    return _grid(_SUMMARY_HEADERS, cells, title)


_ATTENTION_HEADERS = ["账户", "TICKER", "关注原因", "未完成%", "执行单数", "maker%"]


def render_attention(rows: list[ReportRow]) -> str:
    """需要关注的账户/币对清单：超单笔量未完成 / 多单低maker。无 → 一句话。"""
    from cta_monitor.metrics import attention_reason

    flagged = [(r, attention_reason(r)) for r in rows]
    flagged = [(r, why) for r, why in flagged if why]
    title = f"🚩 需要关注（{len(flagged)}）"
    if not flagged:
        return title + "\n无异常，全部正常执行。"
    cells = [
        [
            short_account(r.account), r.ticker, why,
            "" if r.incomplete_pct is None else f"{r.incomplete_pct:.2f}%",
            _fmt(r.order_count),
            "" if r.maker_ratio is None else f"{r.maker_ratio * 100:.2f}%",
        ]
        for r, why in flagged
    ]
    return _grid(_ATTENTION_HEADERS, cells, title)
