"""datahub sequenced 读——薄封装 nexus_data_hub_sdk.Client。"""
from __future__ import annotations

import json

from nexus_data_hub_sdk import Client

from cta_monitor.config import DatahubConfig
from cta_monitor.models import SignalRecord

_KEY_MID = ["CTA_SIGNAL_PUBLISHER", "LAST_PUBLISHED_V1"]


def datahub_key(prefix: str, account: str, coin: str) -> str:
    return "-".join([prefix, *_KEY_MID, account, coin])


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
