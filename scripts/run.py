"""cron 入口：跑一次监控，拼文本表发 Slack。用法：uv run python scripts/run.py"""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

from cta_monitor.config import load_config
from cta_monitor.pipeline import run_once
from cta_monitor.render import render_table_text
from cta_monitor.slack import SlackClient

_BEIJING = timezone(timedelta(hours=8))


def main() -> None:
    cfg = load_config("config.toml")
    now_ms = int(time.time() * 1000)
    slack = SlackClient(cfg.slack)

    result = run_once(cfg, now_ms)
    if result.stale:
        slack.post_text(result.summary)
        return

    stamp = datetime.now(tz=_BEIJING).strftime("%Y-%m-%d %H:%M")
    table = render_table_text(result.rows, f"CTA 执行监控 {stamp}｜{result.summary}")
    slack.post_table(f"CTA 执行监控 {stamp}｜{result.summary}", table)


if __name__ == "__main__":
    main()
