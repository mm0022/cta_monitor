"""跑一次监控并把结果导出 Excel（供人工核对原始数值）。
用法：uv run python scripts/export_excel.py
输出：output/cta_monitor_<北京时间戳>.xlsx
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone

import pandas as pd

from cta_monitor.config import load_config
from cta_monitor.metrics import trunc_to
from cta_monitor.pipeline import run_once
from cta_monitor.render import short_account

_BEIJING = timezone(timedelta(hours=8))


def _t6(x) -> float | None:
    """截断到 6 位小数（展示用）。None/空 → None。"""
    if x is None or x == "":
        return None
    return trunc_to(float(x), 6)


def _split_change(s: str) -> tuple[str, str]:
    if "→" not in s:
        return "", ""
    a, b = s.split("→", 1)
    return a, b


def main() -> None:
    cfg = load_config("config.toml")
    res = run_once(cfg, int(time.time() * 1000))
    stamp = datetime.now(tz=_BEIJING).strftime("%Y%m%d_%H%M")
    os.makedirs("output", exist_ok=True)
    out_path = f"output/cta_monitor_{stamp}.xlsx"

    if res.stale:
        pd.DataFrame([{"提示": res.summary}]).to_excel(out_path, index=False)
        print(f"无新信号，已写：{out_path}")
        return

    records = []
    for r in res.rows:
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

    df = pd.DataFrame(records)
    df.to_excel(out_path, index=False)
    print(f"已写 {len(records)} 行：{out_path}")
    print(f"汇总：{res.summary}")


if __name__ == "__main__":
    main()
