"""datahub sequenced 读——薄封装 nexus_data_hub_sdk.Client。"""
from __future__ import annotations

import json

from nexus_data_hub_sdk import Client

from cta_monitor.config import DatahubConfig
from cta_monitor.models import SignalRecord

_KEY_MID = ["CTA_SIGNAL_PUBLISHER", "LAST_PUBLISHED_V1"]
_PORTFOLIO_KEY_MID = ["PORTFOLIO_PUBLISHER", "LAST_PUBLISHED_V1"]


def datahub_key(prefix: str, account: str, coin: str) -> str:
    return "-".join([prefix, *_KEY_MID, account, coin])


def portfolio_key(prefix: str, account: str, portfolio_id: str) -> str:
    return "-".join([prefix, *_PORTFOLIO_KEY_MID, account, portfolio_id])


def parse_portfolio_signals(content: dict) -> dict[str, SignalRecord]:
    """PortfolioLastPublished 记录 → {coin(小写): SignalRecord}。
    per_token 每个 token 拆成一条 per-symbol 信号；signal_bar_ts_ms 用组合级
    signal_as_of_ts_ms（本轮共用）。current_qty → current_qty_at_decision。"""
    ts = content["signal_as_of_ts_ms"]
    out: dict[str, SignalRecord] = {}
    for token, t in content["per_token"].items():
        out[token.lower()] = SignalRecord(
            mark_price=t["mark_price"],
            current_qty_at_decision=t["current_qty"],
            target_qty=t["target_qty"],
            delta_qty=t["delta_qty"],
            signal_bar_ts_ms=ts,
        )
    return out


class DatahubReader:
    def __init__(self, cfg: DatahubConfig):
        self._prefix = cfg.prefix
        self._client = Client(
            api_key=cfg.api_key,
            gateway_url=cfg.gateway_url,
            updated_exception=False,
            missing_exception=False,
            api_timeout=30.0,
            route_meta_uri="",
        )

    def latest_signal(self, account: str, coin: str) -> SignalRecord | None:
        """取最新一条 LastPublishedRecord；无 → None。"""
        key = datahub_key(self._prefix, account, coin)
        hub = self._client.request_latest_sequenced_data(key)
        if hub.data.empty:
            return None
        content = hub.data.iloc[0]["content"]
        return SignalRecord(**json.loads(content))

    def latest_portfolio_signals(
        self, account: str, portfolio_id: str
    ) -> dict[str, SignalRecord]:
        """读组合级 PORTFOLIO_PUBLISHER key，拆 per_token → {coin: SignalRecord}。无 → {}。"""
        key = portfolio_key(self._prefix, account, portfolio_id)
        hub = self._client.request_latest_sequenced_data(key)
        if hub.data.empty:
            return {}
        return parse_portfolio_signals(json.loads(hub.data.iloc[0]["content"]))
