"""运行结果落 JSONL 供后续参数评估——一次运行一行 JSON。

后续分析：pd.read_json("output/runs.jsonl", lines=True) 一行读全部历史。
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timedelta, timezone

from cta_monitor.config import Config
from cta_monitor.metrics import (
    ATTENTION_MAKER_RATIO,
    ATTENTION_ORDER_COUNT,
    account_summary,
)
from cta_monitor.models import ReportRow, RowStatus

_BEIJING = timezone(timedelta(hours=8))


def run_record(rows: list[ReportRow], now_ms: int, cfg: Config) -> dict:
    """把一次运行组装成一条可 JSON 序列化的记录（纯函数）。

    params 里同时记下配置参数(freshness/min_notional)与代码常量阈值
    (attention_*)——这正是「后续评估参数」要横向对比的量。
    """
    ok = sum(1 for r in rows if r.status == RowStatus.OK)
    running = sum(1 for r in rows if r.status == RowStatus.RUNNING)
    alert = sum(
        1 for r in rows
        if r.status in (RowStatus.SIGNAL_TIME_MISMATCH, RowStatus.NO_TRADES)
    )

    out_rows = []
    for r in rows:
        d = asdict(r)
        d["status"] = r.status.value  # 枚举 → 字符串
        out_rows.append(d)

    return {
        "ts_ms": now_ms,
        "time_bj": datetime.fromtimestamp(now_ms / 1000, _BEIJING).strftime(
            "%Y-%m-%d %H:%M"
        ),
        "params": {
            "freshness_hours": cfg.freshness_hours,
            "min_notional_u": cfg.min_notional_u,
            "attention_order_count": ATTENTION_ORDER_COUNT,
            "attention_maker_ratio": ATTENTION_MAKER_RATIO,
        },
        "summary": {"ticker": len(rows), "ok": ok, "running": running, "alert": alert},
        "accounts": account_summary(rows),
        "rows": out_rows,
    }


def append_run_record(path: str, record: dict) -> None:
    """把一条记录以一行 JSON 追加到 path（JSONL，不覆盖历史）。"""
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
