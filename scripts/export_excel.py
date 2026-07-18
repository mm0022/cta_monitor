"""只出 Excel、不发 Slack。用法：uv run python scripts/export_excel.py
输出：output/cta_monitor_<北京时间戳>.xlsx"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone

import pandas as pd

from cta_monitor.config import load_config
from cta_monitor.excel import write_report_excel
from cta_monitor.pipeline import run_once

_BEIJING = timezone(timedelta(hours=8))


def main() -> None:
    cfg = load_config("config.toml")
    res = run_once(cfg, int(time.time() * 1000))
    os.makedirs("output", exist_ok=True)
    out_path = f"output/cta_monitor_{datetime.now(tz=_BEIJING).strftime('%Y%m%d_%H%M')}.xlsx"

    if res.stale:
        pd.DataFrame([{"提示": res.summary}]).to_excel(out_path, index=False)
        print(f"无新信号，已写：{out_path}")
        return

    n = write_report_excel(res.rows, out_path)
    print(f"已写 {n} 行：{out_path}")
    print(f"汇总：{res.summary}")


if __name__ == "__main__":
    main()
