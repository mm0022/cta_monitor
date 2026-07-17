"""读 config.toml 成强类型 Config。"""
from __future__ import annotations

import tomllib
from dataclasses import dataclass


@dataclass(frozen=True)
class PgConfig:
    host: str
    port: str
    user: str
    password: str
    database: str


@dataclass(frozen=True)
class BiyiConfig:
    login_url: str
    base_url: str
    user: str
    passwd: str


@dataclass(frozen=True)
class DatahubConfig:
    gateway_url: str
    api_key: str
    prefix: str


@dataclass(frozen=True)
class SlackConfig:
    webhook_url: str


@dataclass(frozen=True)
class Config:
    pg: PgConfig
    biyi: BiyiConfig
    datahub: DatahubConfig
    slack: SlackConfig
    accounts: tuple[str, ...]
    min_notional_u: float
    freshness_hours: float


def load_config(path: str) -> Config:
    with open(path, "rb") as f:
        raw = tomllib.load(f)
    mon = raw.get("monitor", {})
    return Config(
        pg=PgConfig(**raw["postgres"]),
        biyi=BiyiConfig(**raw["biyi"]),
        datahub=DatahubConfig(**raw["datahub"]),
        slack=SlackConfig(**raw["slack"]),
        accounts=tuple(mon.get("accounts", [])),
        min_notional_u=float(mon.get("min_notional_u", 10.0)),
        freshness_hours=float(mon.get("freshness_hours", 1.0)),
    )
