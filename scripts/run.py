"""cron 入口：跑一次监控，同时发 Slack + 存 Excel。用法：uv run python scripts/run.py"""
from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone

from cta_monitor.config import load_config
from cta_monitor.excel import write_report_excel
from cta_monitor.pipeline import run_once
from cta_monitor.render import render_account_summary, render_table_text
from cta_monitor.slack import SlackClient

_BEIJING = timezone(timedelta(hours=8))


def main() -> None:
    cfg = load_config("config.toml")
    now_ms = int(time.time() * 1000)
    slack = SlackClient(cfg.slack)

    result = run_once(cfg, now_ms)
    now_bj = datetime.now(tz=_BEIJING)
    stamp = now_bj.strftime("%Y-%m-%d %H:%M")

    if result.stale:
        slack.post_text(result.summary)  # 无新信号：只发提示，不出 Excel
        print(result.summary)
        return

    title = f"CTA 执行监控 {stamp}｜{result.summary}"

    # 1) 发 Slack：先账户汇总（maker/完成度概览），再明细
    slack.post_table(title, render_account_summary(result.rows))
    slack.post_table("明细", render_table_text(result.rows, "明细"))

    # 2) 存 Excel
    os.makedirs("output", exist_ok=True)
    out_path = f"output/cta_monitor_{now_bj.strftime('%Y%m%d_%H%M')}.xlsx"
    n = write_report_excel(result.rows, out_path)
    print(f"已发送 Slack + 存 Excel：{n} 行 -> {out_path}")


if __name__ == "__main__":
    main()
