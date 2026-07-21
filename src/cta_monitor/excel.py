"""ReportRow 列表 → Excel（列/口径与 Slack 文本表一致；qty 列 6 位截断）。"""
from __future__ import annotations

import pandas as pd

from cta_monitor.metrics import account_summary, trunc_to
from cta_monitor.models import ReportRow
from cta_monitor.render import short_account


def _t6(x) -> float | None:
    """截断到 6 位小数；None/空 → None。"""
    if x is None or x == "":
        return None
    return trunc_to(float(x), 6)


def _split_change(s: str) -> tuple[str, str]:
    return tuple(s.split("→", 1)) if "→" in s else ("", "")


def write_report_excel(rows: list[ReportRow], out_path: str) -> int:
    """把报告行写成 xlsx（14 列，与 Slack 表一致）。返回写入行数。"""
    records = []
    for r in rows:
        cur, tgt = _split_change(r.qty_change)
        records.append({
            "账户": short_account(r.account),
            "状态": r.status.value,
            "TICKER": r.ticker,
            "mark_price": r.mark_price,
            "单笔粒度": r.trade_size,
            "单笔报单u(D)": r.order_notional_u,
            "决策时持仓(cur)": _t6(cur),
            "目标(target)": _t6(tgt),
            "delta币量(F)": _t6(r.delta_qty),
            "delta金额u": r.delta_u,
            "maker%": None if r.maker_ratio is None else round(r.maker_ratio * 100, 2),
            "执行ms(K)": r.duration_ms,
            "执行单数": r.order_count,
            "twap未完成量(L)": _t6(r.twap_unfilled_qty),
            "未完成金额u(M)": _t6(r.unfilled_u),
            "未完成比例%(N)": r.incomplete_pct,
        })

    summary = [
        {
            "账户": short_account(s["account"]),
            "统计币数": s["n"],
            "已执行": s["executed"],
            "总交易额u": s["total_notional"],
            "平均maker%": s["avg_maker"],
            "平均完成度%": s["avg_completion"],
            "完成度最低-币": s["worst_ticker"],
            "完成度最低%": s["worst_completion"],
        }
        for s in account_summary(rows)
    ]

    with pd.ExcelWriter(out_path) as writer:
        pd.DataFrame(records).to_excel(writer, sheet_name="明细", index=False)
        pd.DataFrame(summary).to_excel(writer, sheet_name="账户汇总", index=False)
    return len(records)
