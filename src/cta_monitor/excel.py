"""ReportRow 列表 → Excel（列/口径与 Slack 文本表一致；qty 列 6 位截断）。"""
from __future__ import annotations

import pandas as pd

from cta_monitor.metrics import trunc_to
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
            "maker%": None if r.maker_ratio is None else round(r.maker_ratio * 100, 2),
            "执行ms(K)": r.duration_ms,
            "twap未完成量(L)": _t6(r.twap_unfilled_qty),
            "未完成金额u(M)": _t6(r.unfilled_u),
            "未完成比例%(N)": r.incomplete_pct,
        })
    pd.DataFrame(records).to_excel(out_path, index=False)
    return len(records)
