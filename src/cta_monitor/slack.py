"""Slack incoming webhook 发送：纯文本 + 代码块表（分片）。不发图片。"""
from __future__ import annotations

import requests

from cta_monitor.config import SlackConfig


def chunk_code_block(text: str, limit: int = 3800) -> list[str]:
    """按行装箱，每片包在 ``` 代码块里，单片正文不超 limit。"""
    chunks: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for ln in text.splitlines():
        if cur and cur_len + len(ln) + 1 > limit:
            chunks.append("```\n" + "\n".join(cur) + "\n```")
            cur, cur_len = [], 0
        cur.append(ln)
        cur_len += len(ln) + 1
    if cur:
        chunks.append("```\n" + "\n".join(cur) + "\n```")
    return chunks


class SlackClient:
    def __init__(self, cfg: SlackConfig):
        self._cfg = cfg

    def post_text(self, text: str) -> None:
        resp = requests.post(self._cfg.webhook_url, json={"text": text})
        resp.raise_for_status()

    def post_table(self, title: str, table_text: str) -> None:
        self.post_text(title)
        for chunk in chunk_code_block(table_text):
            self.post_text(chunk)
