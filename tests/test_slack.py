from unittest.mock import patch

from cta_monitor.config import SlackConfig
from cta_monitor.slack import SlackClient, chunk_code_block

CFG = SlackConfig(webhook_url="https://hooks.slack.com/services/x")


def test_chunk_wraps_and_splits():
    text = "\n".join(f"line{i}" for i in range(200))
    chunks = chunk_code_block(text, limit=200)
    assert len(chunks) > 1
    for c in chunks:
        assert c.startswith("```") and c.rstrip().endswith("```")
        assert len(c) <= 200 + 10  # 围栏余量


@patch("cta_monitor.slack.requests")
def test_post_text_posts_to_webhook(mock_req):
    mock_req.post.return_value.raise_for_status.return_value = None
    SlackClient(CFG).post_text("hello")
    args, kwargs = mock_req.post.call_args
    assert args[0] == CFG.webhook_url
    assert kwargs["json"]["text"] == "hello"


@patch("cta_monitor.slack.requests")
def test_post_table_sends_title_then_code_chunks(mock_req):
    mock_req.post.return_value.raise_for_status.return_value = None
    SlackClient(CFG).post_table("标题", "a\nb\nc")
    # 至少两次：标题一条 + 代码块一条
    assert mock_req.post.call_count >= 2
    first = mock_req.post.call_args_list[0].kwargs["json"]["text"]
    assert first == "标题"
    last = mock_req.post.call_args_list[-1].kwargs["json"]["text"]
    assert last.startswith("```")
