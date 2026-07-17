"""biyi 客户端：登录 + 策略列表 + financials 解析。"""
from __future__ import annotations

from datetime import datetime, timezone

import requests

from cta_monitor.config import BiyiConfig
from cta_monitor.models import BiyiRow

# 业务名 → financials tableData 表头 token（全部已用 scripts/probe_financials.py 实测坐实）。
FINANCIALS_COLS: dict[str, str] = {
    "ticker": "TICKER",
    "venue": "VENUE",                              # 值形如 BINANCE_PERP
    "trade_size": "TRADE_SIZE",                    # 单笔粒度
    "signal_time": "SIGNAL_TS",                    # 信号时间（UTC 日期时间字符串）
    "txn_status": "TRANSACTION_STATE",             # 事务状态 RUNNING/STOP
    "tracing_id": "TRACE_ID",                      # 追踪ID
    "current_inventory": "INVENTORY_BASE",         # 当前库存
    "target_inventory": "TWAP_TARGET_INVENTORY",   # 目标库存
}


def _biyi_signal_ts_to_ms(s: str) -> int:
    """biyi SIGNAL_TS 是 UTC 日期时间字符串 'YYYY-MM-DD HH:MM:SS' → UTC ms epoch。
    与 datahub signal_bar_ts_ms（同为 UTC ms）同口径，供信号时间匹配比对。"""
    dt = datetime.strptime(s.strip(), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def _col_index(header_cells: list[str]) -> dict[str, int]:
    """表头每格形如 'TOKEN|type'，返回 token → 下标。"""
    idx: dict[str, int] = {}
    for i, cell in enumerate(header_cells):
        token = cell.split("|", 1)[0].strip()
        idx[token] = i
    return idx


def parse_financials(
    strategy_name: str, account: str, table_data: list[str], cols: dict[str, str]
) -> list[BiyiRow]:
    """把 financials tableData 解析成 BiyiRow 列表。表头缺列 → fail-loud。"""
    if not table_data:
        return []
    idx = _col_index(table_data[0].split(","))
    missing = [c for c in cols.values() if c not in idx]
    if missing:
        raise KeyError(f"financials 表头缺列 {missing}；实际表头 {sorted(idx)}")

    out: list[BiyiRow] = []
    for line in table_data[1:]:
        f = line.split(",")
        out.append(
            BiyiRow(
                strategy_name=strategy_name,
                account=account,
                ticker=f[idx[cols["ticker"]]],
                venue=f[idx[cols["venue"]]],
                trade_size=float(f[idx[cols["trade_size"]]]),
                signal_time_ms=_biyi_signal_ts_to_ms(f[idx[cols["signal_time"]]]),
                txn_status=f[idx[cols["txn_status"]]],
                tracing_id=f[idx[cols["tracing_id"]]],
                current_inventory=float(f[idx[cols["current_inventory"]]]),
                target_inventory=float(f[idx[cols["target_inventory"]]]),
            )
        )
    return out


class BiyiClient:
    def __init__(self, cfg: BiyiConfig):
        self._cfg = cfg
        self._token: str | None = None

    def login(self) -> str:
        resp = requests.post(
            self._cfg.login_url,
            json={"userName": self._cfg.user, "passwd": self._cfg.passwd},
            timeout=30,
        )
        resp.raise_for_status()
        self._token = resp.json()["data"]["token"]
        return self._token

    def _headers(self) -> dict[str, str]:
        if self._token is None:
            self.login()
        return {"Authorization": f"Bearer {self._token}"}

    def strategy_list_all(self) -> dict[str, str]:
        """返回 {strategySpec: accountNames[0]}，仅 CTA/CTA_EMS 且 RUNNING。"""
        url = f"{self._cfg.base_url}/strategy/list?curPage=0&pageSize=100"
        resp = requests.get(url, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        data = resp.json().get("data") or []
        out: dict[str, str] = {}
        for s in data:
            if s.get("key") in ("CTA", "CTA_EMS") and s.get("state") == "RUNNING":
                out.setdefault(s["strategySpec"], s["accountNames"][0])
        return out

    def fetch_financials(self, strategy_name: str, account: str) -> list[BiyiRow]:
        url = f"{self._cfg.base_url}/api/strategies/{strategy_name}/financials"
        resp = requests.get(url, headers=self._headers(), timeout=30)
        resp.raise_for_status()
        table = resp.json()["data"]["tableData"]
        return parse_financials(strategy_name, account, table, FINANCIALS_COLS)
