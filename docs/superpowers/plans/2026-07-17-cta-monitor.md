# CTA Monitor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 每小时对被监控 CTA 账户下每个 ticker 的最新一轮信号，核对 TWAP 执行是否到位，产出 14 列表渲染成 PNG 发 Slack。

**Architecture:** 独立 uv 项目。三个薄数据源客户端（biyi HTTP / datahub SDK / PG）各自把原始数据取成纯 dataclass；纯函数层 `metrics` 做闸门判定 + 列公式；`render` 把结果拼成等宽文本表、`slack` 用 webhook 发送；`pipeline` 编排一次运行；`scripts/run.py` 为 cron 入口。所有业务逻辑（解析、公式、闸门、文本表）是无 IO 的纯函数，单测覆盖；IO 客户端保持薄，靠手动 e2e 验证。

**Tech Stack:** Python 3.12 · uv · psycopg[binary] · pydantic v2 · pandas · requests（biyi + slack webhook）· nexus-data-hub-sdk 2.0.27（vendor 本地源）

**输出形态：Slack 不发图片**，把 14 列结果拼成等宽文本表，包在 ``` 代码块里，用 incoming webhook 发到频道（文本形式，超长自动分片）。

## Global Constraints

- Python `>=3.12`（与 vendor SDK 所在 venv 一致）。
- 语言：注释/文档中文；代码标识符英文。
- `nexus-data-hub-sdk` 经 `[tool.uv.sources]` 指向本地目录 `/Users/mac/dev/alpha_copy/vendor/nexus-data-hub-sdk`（version 2.0.27）。
- datahub key 严格 = `CYBERX_PROD-CTA_SIGNAL_PUBLISHER-LAST_PUBLISHED_V1-<account>-<coin小写>`，无映射。
- 监控范围 = biyi `strategy/list` 中 `key ∈ ('CTA','CTA_EMS')` 且 `state=='RUNNING'`；可选 config `accounts` allowlist 收窄（空 = 全部）。
- `order_event.strategy_name == strategySpec`；`sym == '<VENUE>_PERP_<BASE>_<QUOTE>'`；仅 `event_type='FULL_EXEC'`。
- 阈值常量（可配）：`MIN_NOTIONAL_U = 10.0`（<10u 名义额 biyi 不下单也不更新信号时间，属正常）；`FRESHNESS_HOURS = 1.0`（最新信号超过此窗视为无新信号）。
- `app_receive` 是北京时间（UTC+8）字符串；datahub `signal_bar_ts_ms` 是 UTC ms —— 查 PG 前须 +8h 转北京时间字符串 `YYYY-MM-DD HH:MM:SS`。
- PG 凭证复用 `analyse_excution/config.toml` 的 `[postgres]` 值；表名 `order_event_his`。
- 秘密进 `config.toml`（`.gitignore`），`config.example.toml` 只留占位。
- 提交信息不加 Claude/Co-Authored-By（用户全局规则）。本项目当前非 git 仓库；Task 1 执行 `git init`。

## 行状态与列（贯穿全计划的口径）

`RowStatus` 单值状态 + 每行的 14 列：

| 状态 | 判定（按序，命中即定） | DB 列(H/I/J/K) |
|---|---|---|
| `NO_SIGNAL` | 该 coin datahub 无最新信号 | 空 |
| `RUNNING` | biyi `事务状态`（小写）== `running` | 空 |
| `SMALL_NOTIONAL` | `abs(delta_qty)*mark_price < MIN_NOTIONAL_U` | 空 |
| `BELOW_TRADE_SIZE` | `abs(delta_qty)/单笔粒度 < 1` | 空 |
| `SIGNAL_TIME_MISMATCH` | biyi 信号时间 ≠ datahub `signal_bar_ts_ms`（且已过前面阈值）→ **告警** | 有（尽量出，供核对） |
| `NO_TRADES` | 应统计但 order_event 一条 FULL_EXEC 都没捞到 | 空 |
| `OK` | 其余 | 有 |

会去查 PG 的状态：`{OK, SIGNAL_TIME_MISMATCH}`（查完若无成交且本应 OK → 落 `NO_TRADES`）。

14 列（一行 = 一 ticker 最新一轮）：A TICKER / B mark_price / C 单笔粒度 / D 单笔报单金额u=C×B / E 币量变化`cur→target` / F delta币量 / G 报单笔数=roundup(abs(F)/C,1) / H maker比例 / I 结束时间=max(event_time) / J 开始时间=min(event_time) / K 执行时间ms=I−J / L twap未完成量=当前库存−target_qty / M 未完成金额u=L×B / N 完成比例=round((1−abs(L)/abs(F))×100,2)。

---

## Task 1: 项目脚手架 + 配置 + 数据模型

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `config.example.toml`, `src/cta_monitor/__init__.py`
- Create: `src/cta_monitor/config.py`
- Create: `src/cta_monitor/models.py`
- Test: `tests/test_config.py`, `tests/__init__.py`

**Interfaces:**
- Produces: `load_config(path: str) -> Config`；`Config`（含 `.pg/.biyi/.datahub/.slack/.accounts/.min_notional_u/.freshness_hours`）。
- Produces 数据模型：`SignalRecord`、`BiyiRow`、`TradeRow`、`TradeAgg`、`RowStatus`、`ReportRow`（下游全部任务共用这些名字/字段）。

- [ ] **Step 1: 初始化项目骨架**

创建 `pyproject.toml`：

```toml
[project]
name = "cta-monitor"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "psycopg[binary]>=3.1",
    "pydantic>=2.6",
    "pandas>=2.0",
    "requests>=2.31",
    "nexus-data-hub-sdk",
]

[project.optional-dependencies]
dev = ["pytest>=8.0"]

[tool.uv.sources]
nexus-data-hub-sdk = { path = "/Users/mac/dev/alpha_copy/vendor/nexus-data-hub-sdk", editable = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/cta_monitor"]
```

创建 `.gitignore`：

```gitignore
config.toml
__pycache__/
*.pyc
.venv/
output/
.pytest_cache/
```

创建空文件 `src/cta_monitor/__init__.py`、`tests/__init__.py`。

- [ ] **Step 2: 写 config.example.toml（占位，进 git）**

```toml
[postgres]
host = "REPLACE"
port = "REPLACE"
user = "REPLACE"
password = "REPLACE"
database = "shiji"

[biyi]
login_url = "https://biyi.tky.laozi.pro/biyi/api/login"
base_url  = "https://biyi.tky.laozi.pro/biyi"
user = "REPLACE"
passwd = "REPLACE"

[datahub]
gateway_url = "https://nexus.tyo.cyberx.com/nexus-data-hub-gateway/"
api_key = "REPLACE"
prefix = "CYBERX_PROD"

[slack]
webhook_url = "REPLACE"    # incoming webhook URL（发文本表格，不发图片）

[monitor]
accounts = []              # 空 = 监控全部在跑 CTA 账户；否则填 biyi accountNames 白名单
min_notional_u = 10.0
freshness_hours = 1.0
```

- [ ] **Step 3: 写 models.py**

```python
"""跨模块共享数据模型。IO 客户端产出这些类型，纯函数层消费。"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, ConfigDict


class SignalRecord(BaseModel):
    """datahub LastPublishedRecord 的子集（只取本报告要的字段，其余忽略）。"""
    model_config = ConfigDict(extra="ignore")

    mark_price: float
    current_qty_at_decision: float
    target_qty: float
    delta_qty: float
    signal_bar_ts_ms: int


@dataclass(frozen=True)
class BiyiRow:
    """biyi strategies/{s}/financials 里一行（一个 symbol）。"""
    strategy_name: str        # = strategySpec，= order_event.strategy_name
    account: str              # = accountNames[0]，= datahub key 的 account 段
    ticker: str               # 如 "DOGE/USDT"
    venue: str                # 如 "BINANCE"
    trade_size: float         # 单笔粒度
    signal_time_ms: int       # biyi 信号时间（UTC ms）
    txn_status: str           # 事务状态，原样（判定时 .lower()）
    tracing_id: str           # 追踪ID
    current_inventory: float  # 当前库存
    target_inventory: float   # 目标库存


@dataclass(frozen=True)
class TradeRow:
    """order_event_his 一条 FULL_EXEC。"""
    is_maker: int             # 1=maker, 0=taker
    quantity: float           # exchange_quantity
    price: float              # exchange_price
    event_time: int           # ms epoch


@dataclass(frozen=True)
class TradeAgg:
    maker_ratio: float        # maker成交额 / 总成交额
    start_ms: int             # min(event_time)
    end_ms: int               # max(event_time)
    duration_ms: int          # end - start


class RowStatus(str, Enum):
    OK = "ok"
    RUNNING = "running"
    SMALL_NOTIONAL = "small_notional"
    BELOW_TRADE_SIZE = "below_trade_size"
    SIGNAL_TIME_MISMATCH = "signal_time_mismatch"
    NO_TRADES = "no_trades"
    NO_SIGNAL = "no_signal"


@dataclass(frozen=True)
class ReportRow:
    ticker: str                         # A
    mark_price: float | None            # B
    trade_size: float | None            # C
    order_notional_u: float | None      # D
    qty_change: str                     # E  "cur→target"
    delta_qty: float | None             # F
    n_orders: float | None              # G
    maker_ratio: float | None           # H
    end_ms: int | None                  # I
    start_ms: int | None                # J
    duration_ms: int | None             # K
    twap_unfilled_qty: float | None     # L
    unfilled_u: float | None            # M
    completion_pct: float | None        # N
    status: RowStatus
    note: str = ""
```

- [ ] **Step 4: 写 config.py**

```python
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
```

- [ ] **Step 5: 写失败测试 tests/test_config.py**

```python
from cta_monitor.config import load_config


def test_load_config(tmp_path):
    p = tmp_path / "c.toml"
    p.write_text(
        """
[postgres]
host="h"
port="1"
user="u"
password="pw"
database="shiji"
[biyi]
login_url="lu"
base_url="bu"
user="bu2"
passwd="pp"
[datahub]
gateway_url="g"
api_key="k"
prefix="CYBERX_PROD"
[slack]
webhook_url="https://hooks.slack.com/services/x"
[monitor]
accounts=["a1"]
min_notional_u=10.0
freshness_hours=1.0
""",
        encoding="utf-8",
    )
    cfg = load_config(str(p))
    assert cfg.pg.database == "shiji"
    assert cfg.datahub.prefix == "CYBERX_PROD"
    assert cfg.accounts == ("a1",)
    assert cfg.min_notional_u == 10.0
```

- [ ] **Step 6: 建 venv 并跑测试**

Run:
```bash
cd /Users/mac/dev/cta_monitor
uv sync --extra dev
uv run pytest tests/test_config.py -v
```
Expected: PASS（`uv sync` 会从 vendor 源装 nexus-data-hub-sdk；若装不上先解决源可达性再继续）。

- [ ] **Step 7: git init + commit**

```bash
cd /Users/mac/dev/cta_monitor
git init
git add -A
git commit -m "feat: 项目脚手架 + config + 数据模型"
```

---

## Task 2: metrics 纯函数（符号/币种/公式）

**Files:**
- Create: `src/cta_monitor/metrics.py`
- Test: `tests/test_metrics.py`

**Interfaces:**
- Produces: `coin_from_ticker(ticker) -> str`、`sym_from_ticker(ticker, venue) -> str`、`trunc_to(value, ndigits) -> float`、`n_orders(delta_qty, trade_size) -> float`、`completion_pct(unfilled_qty, delta_qty) -> float`。
- 口径：G 报单笔数、D 单笔报单金额u 均按**截断（向零取整）**复现截图（非四舍五入/roundup）。

- [ ] **Step 1: 写失败测试 tests/test_metrics.py**

```python
from cta_monitor.metrics import (
    coin_from_ticker,
    sym_from_ticker,
    trunc_to,
    n_orders,
    completion_pct,
)


def test_coin_and_sym():
    assert coin_from_ticker("DOGE/USDT") == "doge"
    assert sym_from_ticker("DOGE/USDT", "BINANCE") == "BINANCE_PERP_DOGE_USDT"
    assert coin_from_ticker("1000PEPE/USDT") == "1000pepe"


def test_trunc_to():
    # 截断（向零取整），非四舍五入
    assert trunc_to(2.287, 1) == 2.2
    assert trunc_to(12.376, 1) == 12.3
    assert trunc_to(0.0634, 1) == 0.0
    assert trunc_to(179.675, 0) == 179.0
    assert trunc_to(2.0, 1) == 2.0


def test_n_orders_truncates():
    # DOGE：30939.1 / 2500 = 12.3756 -> 截断 1 位 = 12.3（图值）
    assert n_orders(30939.1, 2500.0) == 12.3
    # AAVE：13.0376 / 5.7 = 2.287 -> 2.2（图值，roundup 会是 2.3）
    assert n_orders(-13.0376, 5.7) == 2.2


def test_completion_pct_doge():
    # 1 - 1376/30939.1 = 0.95551 -> 95.55
    assert completion_pct(1376.0, 30939.1) == 95.55


def test_completion_pct_negative_delta():
    # 1000PEPE：L=-1, delta=-95225.8 -> ~100
    assert completion_pct(-1.0, -95225.8) == 100.0
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/test_metrics.py -v`
Expected: FAIL（ImportError: cannot import name ...）

- [ ] **Step 3: 写 metrics.py（本任务部分）**

```python
"""列公式与符号解析——全部无 IO 纯函数。"""
from __future__ import annotations

import math


def coin_from_ticker(ticker: str) -> str:
    """"DOGE/USDT" -> "doge"（datahub key 的 coin 段，小写 base）。"""
    return ticker.split("/", 1)[0].strip().lower()


def sym_from_ticker(ticker: str, venue: str) -> str:
    """("DOGE/USDT","BINANCE") -> "BINANCE_PERP_DOGE_USDT"（order_event.sym）。"""
    base, quote = ticker.split("/", 1)
    return f"{venue.strip().upper()}_PERP_{base.strip().upper()}_{quote.strip().upper()}"


def trunc_to(value: float, ndigits: int) -> float:
    """截断（向零取整）到 ndigits 位小数——复现截图口径，非四舍五入。"""
    factor = 10 ** ndigits
    return math.trunc(value * factor) / factor


def n_orders(delta_qty: float, trade_size: float) -> float:
    """报单笔数 = 截断(abs(delta)/单笔粒度, 1 位)。"""
    return trunc_to(abs(delta_qty) / trade_size, 1)


def completion_pct(unfilled_qty: float, delta_qty: float) -> float:
    """完成比例 = round((1 - abs(未完成)/abs(delta)) * 100, 2)。分母取 abs 兼容负 delta。"""
    return round((1 - abs(unfilled_qty) / abs(delta_qty)) * 100, 2)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/test_metrics.py -v`
Expected: PASS

- [ ] **Step 5: commit**

```bash
git add src/cta_monitor/metrics.py tests/test_metrics.py
git commit -m "feat: metrics 符号解析与列公式纯函数"
```

---

## Task 3: 行状态判定 + 组行（核心）

**Files:**
- Modify: `src/cta_monitor/metrics.py`（追加 `classify_status`、`build_row`、`SHOULD_QUERY_STATUSES`）
- Test: `tests/test_metrics.py`（追加）

**Interfaces:**
- Consumes: `BiyiRow`、`SignalRecord`、`TradeAgg`、`RowStatus`、`ReportRow`（Task 1）；本文件的公式函数（Task 2）。
- Produces:
  - `SHOULD_QUERY_STATUSES: set[RowStatus]`（= `{OK, SIGNAL_TIME_MISMATCH}`）
  - `classify_status(biyi: BiyiRow, sig: SignalRecord | None, *, min_notional_u: float) -> RowStatus`（不需要 agg，pipeline 用它决定是否查 PG）
  - `build_row(biyi: BiyiRow, sig: SignalRecord | None, agg: TradeAgg | None, status: RowStatus) -> ReportRow`

- [ ] **Step 1: 追加失败测试**

```python
from cta_monitor.metrics import classify_status, build_row, SHOULD_QUERY_STATUSES
from cta_monitor.models import BiyiRow, SignalRecord, TradeAgg, RowStatus


def _biyi(**kw):
    base = dict(
        strategy_name="s1", account="acc", ticker="DOGE/USDT", venue="BINANCE",
        trade_size=2500.0, signal_time_ms=1000, txn_status="stop",
        tracing_id="t1", current_inventory=-97875.9, target_inventory=-97875.9 - 1376,
    )
    base.update(kw)
    return BiyiRow(**base)


def _sig(**kw):
    base = dict(
        mark_price=0.07187, current_qty_at_decision=-128815.0,
        target_qty=-97875.9, delta_qty=30939.1, signal_bar_ts_ms=1000,
    )
    base.update(kw)
    return SignalRecord(**base)


def test_classify_running():
    assert classify_status(_biyi(txn_status="RUNNING"), _sig(), min_notional_u=10) == RowStatus.RUNNING


def test_classify_no_signal():
    assert classify_status(_biyi(), None, min_notional_u=10) == RowStatus.NO_SIGNAL


def test_classify_small_notional():
    s = _sig(delta_qty=1.0, mark_price=0.5)  # 0.5u < 10u
    assert classify_status(_biyi(), s, min_notional_u=10) == RowStatus.SMALL_NOTIONAL


def test_classify_below_trade_size():
    s = _sig(delta_qty=100.0, mark_price=1.0)  # notional 100u ok
    b = _biyi(trade_size=200.0)                # 100/200 < 1
    assert classify_status(b, s, min_notional_u=10) == RowStatus.BELOW_TRADE_SIZE


def test_classify_signal_time_mismatch():
    b = _biyi(signal_time_ms=999)
    assert classify_status(b, _sig(signal_bar_ts_ms=1000), min_notional_u=10) == RowStatus.SIGNAL_TIME_MISMATCH


def test_classify_ok():
    assert classify_status(_biyi(), _sig(), min_notional_u=10) == RowStatus.OK
    assert SHOULD_QUERY_STATUSES == {RowStatus.OK, RowStatus.SIGNAL_TIME_MISMATCH}


def test_build_row_ok_fills_all_columns():
    agg = TradeAgg(maker_ratio=0.75, start_ms=1783987729868, end_ms=1783987839911, duration_ms=110043)
    # current_inventory = target_qty + 1376 -> L = current - target = +1376, completion=95.55（对齐图）
    biyi = _biyi(current_inventory=-97875.9 + 1376)
    row = build_row(biyi, _sig(), agg, RowStatus.OK)
    assert row.ticker == "DOGE/USDT"
    assert row.order_notional_u == 179.0            # trunc(2500*0.07187)=trunc(179.675)=179
    assert row.qty_change == "-128815.0→-97875.9"
    assert row.n_orders == 12.3                      # trunc(30939.1/2500,1)=12.3
    assert row.maker_ratio == 0.75
    assert row.duration_ms == 110043
    assert row.twap_unfilled_qty == 1376.0
    assert row.completion_pct == 95.55
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/test_metrics.py -v`
Expected: FAIL（ImportError classify_status）

- [ ] **Step 3: 追加实现到 metrics.py**

```python
from cta_monitor.models import BiyiRow, ReportRow, RowStatus, SignalRecord, TradeAgg

SHOULD_QUERY_STATUSES: set[RowStatus] = {RowStatus.OK, RowStatus.SIGNAL_TIME_MISMATCH}


def classify_status(
    biyi: BiyiRow, sig: SignalRecord | None, *, min_notional_u: float
) -> RowStatus:
    """按序判定行状态（命中即返回）。不涉及 PG。"""
    if sig is None:
        return RowStatus.NO_SIGNAL
    if biyi.txn_status.strip().lower() == "running":
        return RowStatus.RUNNING
    if abs(sig.delta_qty) * sig.mark_price < min_notional_u:
        return RowStatus.SMALL_NOTIONAL
    if abs(sig.delta_qty) / biyi.trade_size < 1:
        return RowStatus.BELOW_TRADE_SIZE
    if biyi.signal_time_ms != sig.signal_bar_ts_ms:
        return RowStatus.SIGNAL_TIME_MISMATCH
    return RowStatus.OK


def build_row(
    biyi: BiyiRow,
    sig: SignalRecord | None,
    agg: TradeAgg | None,
    status: RowStatus,
) -> ReportRow:
    """组一行 14 列。sig 为空只出 ticker + 状态；DB 列仅在 agg 存在时填。"""
    if sig is None:
        return ReportRow(
            ticker=biyi.ticker, mark_price=None, trade_size=biyi.trade_size,
            order_notional_u=None, qty_change="", delta_qty=None, n_orders=None,
            maker_ratio=None, end_ms=None, start_ms=None, duration_ms=None,
            twap_unfilled_qty=None, unfilled_u=None, completion_pct=None,
            status=status, note="datahub 无信号",
        )

    unfilled = biyi.current_inventory - sig.target_qty
    completion = (
        completion_pct(unfilled, sig.delta_qty) if sig.delta_qty != 0 else None
    )
    return ReportRow(
        ticker=biyi.ticker,
        mark_price=sig.mark_price,
        trade_size=biyi.trade_size,
        order_notional_u=trunc_to(biyi.trade_size * sig.mark_price, 0),  # 图为整数、截断
        qty_change=f"{sig.current_qty_at_decision}→{sig.target_qty}",
        delta_qty=sig.delta_qty,
        n_orders=n_orders(sig.delta_qty, biyi.trade_size),
        maker_ratio=agg.maker_ratio if agg else None,
        end_ms=agg.end_ms if agg else None,
        start_ms=agg.start_ms if agg else None,
        duration_ms=agg.duration_ms if agg else None,
        twap_unfilled_qty=unfilled,
        unfilled_u=round(unfilled * sig.mark_price, 6),
        completion_pct=completion,
        status=status,
        note="",
    )
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/test_metrics.py -v`
Expected: PASS（若 `test_build_row_ok_fills_all_columns` 的 completion 断言不符，按 Step 1 注释修 fixture 的 `current_inventory`）

- [ ] **Step 5: commit**

```bash
git add src/cta_monitor/metrics.py tests/test_metrics.py
git commit -m "feat: 行状态判定 + 组行核心逻辑"
```

---

## Task 4: order_event 聚合（纯函数 + PG 查询）

**Files:**
- Create: `src/cta_monitor/db.py`
- Test: `tests/test_db.py`

**Interfaces:**
- Consumes: `TradeRow`、`TradeAgg`、`PgConfig`（Task 1）。
- Produces:
  - `aggregate_trades(rows: list[TradeRow]) -> TradeAgg | None`（纯函数）
  - `signal_ms_to_beijing(signal_bar_ts_ms: int) -> str`（UTC ms → `'YYYY-MM-DD HH:MM:SS'` 北京时间）
  - `fetch_trades(pg: PgConfig, strategy_name: str, sym: str, signal_time_beijing: str) -> list[TradeRow]`

- [ ] **Step 1: 写失败测试 tests/test_db.py**

```python
from cta_monitor.db import aggregate_trades, signal_ms_to_beijing
from cta_monitor.models import TradeRow


def test_aggregate_none_on_empty():
    assert aggregate_trades([]) is None


def test_aggregate_maker_ratio_by_notional():
    rows = [
        TradeRow(is_maker=1, quantity=10, price=2.0, event_time=1000),   # maker 20u
        TradeRow(is_maker=0, quantity=10, price=2.0, event_time=1500),   # taker 20u
        TradeRow(is_maker=1, quantity=10, price=2.0, event_time=1200),   # maker 20u
    ]
    agg = aggregate_trades(rows)
    assert agg is not None
    assert abs(agg.maker_ratio - (40 / 60)) < 1e-9
    assert agg.start_ms == 1000
    assert agg.end_ms == 1500
    assert agg.duration_ms == 500


def test_signal_ms_to_beijing():
    # 2026-07-17 06:07:00 北京 == 2026-07-16 22:07:00 UTC
    ms = 1784247420000
    assert signal_ms_to_beijing(ms) == "2026-07-17 06:07:00"
```

> 注：Step 里 `test_signal_ms_to_beijing` 的 `ms` 常量需与断言一致。实现完若数值对不上，用 `python -c "import datetime,calendar; print(...)"` 反推正确 ms 填入，勿改函数逻辑。

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/test_db.py -v`
Expected: FAIL（ImportError）

- [ ] **Step 3: 写 db.py**

```python
"""order_event_his 取数与聚合。"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import psycopg

from cta_monitor.config import PgConfig
from cta_monitor.models import TradeAgg, TradeRow

_BEIJING = timezone(timedelta(hours=8))

_SQL = """
SELECT s.is_maker, s.exchange_quantity, s.exchange_price, s.event_time
FROM order_event_his s
WHERE s.strategy_name = %(strategy_name)s
  AND s.sym          = %(sym)s
  AND s.app_receive  > %(signal_time)s
  AND s.event_type   = 'FULL_EXEC';
"""


def aggregate_trades(rows: list[TradeRow]) -> TradeAgg | None:
    """maker比例=maker成交额/总成交额；start/end=min/max(event_time)。空 → None。"""
    if not rows:
        return None
    total_notional = sum(r.quantity * r.price for r in rows)
    maker_notional = sum(r.quantity * r.price for r in rows if r.is_maker == 1)
    times = [r.event_time for r in rows]
    start_ms, end_ms = min(times), max(times)
    return TradeAgg(
        maker_ratio=(maker_notional / total_notional) if total_notional else 0.0,
        start_ms=start_ms,
        end_ms=end_ms,
        duration_ms=end_ms - start_ms,
    )


def signal_ms_to_beijing(signal_bar_ts_ms: int) -> str:
    """UTC ms → 北京时间 'YYYY-MM-DD HH:MM:SS'（与 app_receive 同时区比较）。"""
    dt = datetime.fromtimestamp(signal_bar_ts_ms / 1000, tz=timezone.utc).astimezone(_BEIJING)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def fetch_trades(
    pg: PgConfig, strategy_name: str, sym: str, signal_time_beijing: str
) -> list[TradeRow]:
    """按 (strategy_name, sym, app_receive>信号时间, FULL_EXEC) 拉成交。"""
    conninfo = (
        f"host={pg.host} port={pg.port} user={pg.user} "
        f"password={pg.password} dbname={pg.database}"
    )
    with psycopg.connect(conninfo) as conn, conn.cursor() as cur:
        cur.execute(
            _SQL,
            {"strategy_name": strategy_name, "sym": sym, "signal_time": signal_time_beijing},
        )
        return [
            TradeRow(
                is_maker=int(r[0]),
                quantity=float(r[1]),
                price=float(r[2]),
                event_time=int(r[3]),
            )
            for r in cur.fetchall()
        ]
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/test_db.py -v`
Expected: PASS（`fetch_trades` 不在单测覆盖，靠 Task 10 e2e）

- [ ] **Step 5: commit**

```bash
git add src/cta_monitor/db.py tests/test_db.py
git commit -m "feat: order_event 聚合 + 北京时间转换 + PG 查询"
```

---

## Task 5: biyi 客户端（登录 + 策略列表 + financials 解析）

**Files:**
- Create: `src/cta_monitor/biyi.py`
- Create: `scripts/probe_financials.py`（一次性探针，确认表头 token）
- Test: `tests/test_biyi.py`

**Interfaces:**
- Consumes: `BiyiConfig`（Task 1）、`BiyiRow`（Task 1）。
- Produces:
  - `FINANCIALS_COLS: dict[str, str]`（业务名 → tableData 表头 token）
  - `parse_financials(strategy_name: str, account: str, table_data: list[str], cols: dict[str, str]) -> list[BiyiRow]`（纯函数）
  - `class BiyiClient`：`login() -> str`、`strategy_list_all() -> dict[str, str]`、`fetch_financials(strategy_name: str, account: str) -> list[BiyiRow]`

- [ ] **Step 1: 探针脚本 scripts/probe_financials.py（先跑，拿真实表头）**

```python
"""一次性探针：打印一条 CTA 策略 financials 的表头 token，用于填 FINANCIALS_COLS。
用法：uv run python scripts/probe_financials.py
"""
import sys

import requests

from cta_monitor.config import load_config

cfg = load_config("config.toml")
tok = requests.post(
    cfg.biyi.login_url,
    json={"userName": cfg.biyi.user, "passwd": cfg.biyi.passwd},
).json()["data"]["token"]
h = {"Authorization": f"Bearer {tok}"}

lst = requests.get(
    f"{cfg.biyi.base_url}/strategy/list?curPage=0&pageSize=100", headers=h
).json()["data"]
spec = next(
    s["strategySpec"] for s in lst
    if s["key"] in ("CTA", "CTA_EMS") and s["state"] == "RUNNING"
)
fin = requests.get(
    f"{cfg.biyi.base_url}/api/strategies/{spec}/financials", headers=h
).json()["data"]
print("strategySpec:", spec)
print("表头列（token|type）：")
for i, cell in enumerate(fin["tableData"][0].split(",")):
    print(f"  [{i}] {cell}")
print("首行数据：")
print(" ", fin["tableData"][1] if len(fin["tableData"]) > 1 else "(空)")
sys.exit(0)
```

- [ ] **Step 2: 用真实凭证跑探针，记录表头 token**

Run: `cd /Users/mac/dev/cta_monitor && uv run python scripts/probe_financials.py`
Expected: 打印各列 `token|type`。把 `单笔粒度 / 信号时间 / 事务状态 / 追踪ID / 当前库存 / 目标库存 / VENUE` 对应的 **token** 记下来，填进 Step 4 的 `FINANCIALS_COLS`。已知：`TICKER`、`INVENTORY_BASE`。
> 若此刻拿不到凭证：先用 Step 3 的合成表头把纯函数写完、测过，`FINANCIALS_COLS` 的 6 个待确认值先按占位跑不通没关系；e2e（Task 10）前必须回来用探针坐实。

- [ ] **Step 3: 写失败测试 tests/test_biyi.py（用合成表头，锁死解析行为）**

```python
from cta_monitor.biyi import parse_financials
from cta_monitor.models import BiyiRow

# 合成表头（列顺序任意，解析按列名找下标）
COLS = {
    "ticker": "TICKER",
    "venue": "VENUE",
    "trade_size": "TRADE_SIZE",
    "signal_time": "SIGNAL_TIME",
    "txn_status": "TASK_STATE",
    "tracing_id": "TRACING_ID",
    "current_inventory": "CURRENT_INVENTORY",
    "target_inventory": "TARGET_INVENTORY",
}
HEADER = "TICKER|str,VENUE|str,TRADE_SIZE|num,SIGNAL_TIME|num,TASK_STATE|str,TRACING_ID|str,CURRENT_INVENTORY|num,TARGET_INVENTORY|num"


def test_parse_financials_basic():
    table = [
        HEADER,
        "DOGE/USDT,BINANCE,2500,1000,stop,tr1,-97000,-97875.9",
        "BTC/USDT,BINANCE,0.012,1000,running,tr2,-0.16,-0.16",
    ]
    rows = parse_financials("spec1", "acc1", table, COLS)
    assert len(rows) == 2
    r0 = rows[0]
    assert isinstance(r0, BiyiRow)
    assert r0.strategy_name == "spec1" and r0.account == "acc1"
    assert r0.ticker == "DOGE/USDT" and r0.venue == "BINANCE"
    assert r0.trade_size == 2500.0
    assert r0.signal_time_ms == 1000
    assert r0.txn_status == "stop"
    assert r0.current_inventory == -97000.0
    assert r0.target_inventory == -97875.9
    assert rows[1].txn_status == "running"
```

- [ ] **Step 4: 写 biyi.py**

```python
"""biyi 客户端：登录 + 策略列表 + financials 解析。"""
from __future__ import annotations

import requests

from cta_monitor.config import BiyiConfig
from cta_monitor.models import BiyiRow

# 业务名 → financials tableData 表头 token。
# TICKER / INVENTORY_BASE 已确认；其余 6 个 **必须用 scripts/probe_financials.py 坐实**后回填。
FINANCIALS_COLS: dict[str, str] = {
    "ticker": "TICKER",
    "venue": "VENUE",                       # 待探针确认
    "trade_size": "TRADE_SIZE",             # 单笔粒度，待探针确认
    "signal_time": "SIGNAL_TIME",           # 信号时间，待探针确认
    "txn_status": "TASK_STATE",             # 事务状态，待探针确认
    "tracing_id": "TRACING_ID",             # 追踪ID，待探针确认
    "current_inventory": "CURRENT_INVENTORY",  # 当前库存，待探针确认
    "target_inventory": "TARGET_INVENTORY",    # 目标库存，待探针确认
}


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
                signal_time_ms=int(float(f[idx[cols["signal_time"]]])),
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
        resp = requests.get(url, headers=self._headers())
        resp.raise_for_status()
        data = resp.json().get("data") or []
        out: dict[str, str] = {}
        for s in data:
            if s.get("key") in ("CTA", "CTA_EMS") and s.get("state") == "RUNNING":
                out.setdefault(s["strategySpec"], s["accountNames"][0])
        return out

    def fetch_financials(self, strategy_name: str, account: str) -> list[BiyiRow]:
        url = f"{self._cfg.base_url}/api/strategies/{strategy_name}/financials"
        resp = requests.get(url, headers=self._headers())
        resp.raise_for_status()
        table = resp.json()["data"]["tableData"]
        return parse_financials(strategy_name, account, table, FINANCIALS_COLS)
```

- [ ] **Step 5: 跑测试确认通过**

Run: `uv run pytest tests/test_biyi.py -v`
Expected: PASS（合成表头驱动解析；HTTP 方法靠 e2e）

- [ ] **Step 6: commit**

```bash
git add src/cta_monitor/biyi.py scripts/probe_financials.py tests/test_biyi.py
git commit -m "feat: biyi 客户端 + financials 解析（表头 token 待探针坐实）"
```

---

## Task 6: datahub 读取（vendor SDK 薄封装）

**Files:**
- Create: `src/cta_monitor/datahub.py`
- Test: `tests/test_datahub.py`

**Interfaces:**
- Consumes: `DatahubConfig`（Task 1）、`SignalRecord`（Task 1）。
- Produces: `datahub_key(prefix, account, coin) -> str`；`class DatahubReader`（`__init__(cfg: DatahubConfig)`、`latest_signal(account: str, coin: str) -> SignalRecord | None`）。

- [ ] **Step 1: 写失败测试 tests/test_datahub.py（只测 key 拼接纯函数）**

```python
from cta_monitor.datahub import datahub_key


def test_datahub_key():
    assert datahub_key("CYBERX_PROD", "binance_tokyo_cta_momentum_test1_new", "btc") == (
        "CYBERX_PROD-CTA_SIGNAL_PUBLISHER-LAST_PUBLISHED_V1-"
        "binance_tokyo_cta_momentum_test1_new-btc"
    )
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/test_datahub.py -v`
Expected: FAIL（ImportError）

- [ ] **Step 3: 写 datahub.py**

```python
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
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/test_datahub.py -v`
Expected: PASS

- [ ] **Step 5: 手动 smoke（有凭证后）**

Run:
```bash
uv run python -c "
from cta_monitor.config import load_config
from cta_monitor.datahub import DatahubReader
r = DatahubReader(load_config('config.toml').datahub)
print(r.latest_signal('binance_tokyo_cta_momentum_test1_new','btc'))
"
```
Expected: 打印一个 `SignalRecord(...)`（或 None）。若字段缺失报 ValidationError，核对 datahub content 实际字段名与 `SignalRecord`。

- [ ] **Step 6: commit**

```bash
git add src/cta_monitor/datahub.py tests/test_datahub.py
git commit -m "feat: datahub sequenced 读薄封装"
```

---

## Task 7: 文本表渲染

**Files:**
- Create: `src/cta_monitor/render.py`
- Test: `tests/test_render.py`

**Interfaces:**
- Consumes: `ReportRow`、`RowStatus`（Task 1）。
- Produces: `render_table_text(rows: list[ReportRow], title: str) -> str`（返回等宽对齐文本表；异常行行首加状态标记；不含 ``` 围栏，围栏在 slack 层加）。

- [ ] **Step 1: 写失败测试 tests/test_render.py**

```python
from cta_monitor.models import ReportRow, RowStatus
from cta_monitor.render import render_table_text


def _row(status=RowStatus.OK, ticker="DOGE/USDT"):
    return ReportRow(
        ticker=ticker, mark_price=0.07187, trade_size=2500.0,
        order_notional_u=179.0, qty_change="-128815.0→-97875.9", delta_qty=30939.1,
        n_orders=12.3, maker_ratio=0.75, end_ms=1783987839911, start_ms=1783987729868,
        duration_ms=110043, twap_unfilled_qty=1376.0, unfilled_u=98.9, completion_pct=95.55,
        status=status,
    )


def test_render_text_has_header_and_rows():
    txt = render_table_text([_row(), _row(RowStatus.RUNNING, "BTC/USDT")], "测试标题")
    assert "测试标题" in txt
    assert "TICKER" in txt and "完成%" in txt
    assert "DOGE/USDT" in txt and "BTC/USDT" in txt
    # 百分比显示：maker 整数%、完成 两位小数%
    assert "75%" in txt and "95.55%" in txt
    # 运行中行带状态标记
    assert "运行中" in txt
    # 每列等宽对齐：表头行与数据行列数一致
    lines = [l for l in txt.splitlines() if "|" in l]
    assert len({l.count("|") for l in lines}) == 1
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/test_render.py -v`
Expected: FAIL（ImportError）

- [ ] **Step 3: 写 render.py**

```python
"""ReportRow 列表 → 等宽对齐文本表（Slack 代码块用）。"""
from __future__ import annotations

from cta_monitor.models import ReportRow, RowStatus

_HEADERS = [
    "状态", "TICKER", "mark", "单笔粒度", "单笔报单u", "币量变化", "delta",
    "报单笔数", "maker%", "结束时间", "开始时间", "执行ms",
    "未完成量", "未完成u", "完成%",
]

# 异常状态行首标记（正常留空）
_STATUS_TAG = {
    RowStatus.OK: "",
    RowStatus.RUNNING: "运行中",
    RowStatus.SMALL_NOTIONAL: "小额",
    RowStatus.BELOW_TRADE_SIZE: "未下单",
    RowStatus.SIGNAL_TIME_MISMATCH: "⚠时间不符",
    RowStatus.NO_TRADES: "⚠无成交",
    RowStatus.NO_SIGNAL: "⚠无信号",
}


def _fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def _cells(r: ReportRow) -> list[str]:
    return [
        _STATUS_TAG.get(r.status, r.status.value),
        r.ticker,
        _fmt(r.mark_price), _fmt(r.trade_size), _fmt(r.order_notional_u),
        r.qty_change, _fmt(r.delta_qty), _fmt(r.n_orders),
        "" if r.maker_ratio is None else f"{round(r.maker_ratio * 100)}%",   # H 整数百分比
        _fmt(r.end_ms), _fmt(r.start_ms), _fmt(r.duration_ms),
        _fmt(r.twap_unfilled_qty), _fmt(r.unfilled_u),
        "" if r.completion_pct is None else f"{r.completion_pct:.2f}%",       # N 两位小数百分比
    ]


def render_table_text(rows: list[ReportRow], title: str) -> str:
    """标题 + 等宽表（列按最大宽度左对齐，' | ' 分隔）。"""
    matrix = [_HEADERS] + [_cells(r) for r in rows]
    widths = [max(len(row[c]) for row in matrix) for c in range(len(_HEADERS))]

    def line(cells: list[str]) -> str:
        return " | ".join(cell.ljust(widths[c]) for c, cell in enumerate(cells))

    sep = "-+-".join("-" * w for w in widths)
    body = [line(_HEADERS), sep] + [line(row) for row in matrix[1:]]
    return title + "\n" + "\n".join(body)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/test_render.py -v`
Expected: PASS

- [ ] **Step 5: commit**

```bash
git add src/cta_monitor/render.py tests/test_render.py
git commit -m "feat: 等宽文本表渲染"
```

---

## Task 8: Slack 发送（webhook，纯文本 + 代码块 + 分片）

**Files:**
- Create: `src/cta_monitor/slack.py`
- Test: `tests/test_slack.py`

**Interfaces:**
- Consumes: `SlackConfig`（Task 1）。
- Produces:
  - `chunk_code_block(text: str, limit: int = 3800) -> list[str]`（纯函数：按行切分，每片包在 ```\n...\n``` 里，单片不超 limit）
  - `class SlackClient`（`__init__(cfg: SlackConfig)`、`post_text(text: str) -> None` 纯文本、`post_table(title: str, table_text: str) -> None` 表文本包代码块分片发）

> 说明：不发图片，用 incoming webhook `POST {webhook_url} json={"text": ...}`。表宽 14 列，包 ``` 代码块保持等宽对齐；Slack 单条消息约 40k 字符、代码块过长影响观感，按 ~3800 字符分片多条发。

- [ ] **Step 1: 写失败测试 tests/test_slack.py（mock requests，不打网络）**

```python
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/test_slack.py -v`
Expected: FAIL（ImportError）

- [ ] **Step 3: 写 slack.py**

```python
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
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/test_slack.py -v`
Expected: PASS

- [ ] **Step 5: commit**

```bash
git add src/cta_monitor/slack.py tests/test_slack.py
git commit -m "feat: Slack webhook 文本表发送 + 分片"
```

---

## Task 9: pipeline 编排（无新信号闸门 + 组表）

**Files:**
- Create: `src/cta_monitor/pipeline.py`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: 全部前序模块。
- Produces:
  - `is_stale(signals: list[SignalRecord | None], now_ms: int, freshness_hours: float) -> bool`（纯函数，无新信号闸门）
  - `run_once(cfg: Config, now_ms: int, *, biyi=None, datahub=None) -> RunResult`（编排；`biyi`/`datahub` 可注入便于测试）
  - `@dataclass RunResult(stale: bool, rows: list[ReportRow], summary: str)`

- [ ] **Step 1: 写失败测试 tests/test_pipeline.py**

```python
from cta_monitor.models import SignalRecord
from cta_monitor.pipeline import is_stale


def _sig(ts):
    return SignalRecord(mark_price=1, current_qty_at_decision=0, target_qty=1, delta_qty=1, signal_bar_ts_ms=ts)


def test_is_stale_true_when_all_old():
    now = 10_000_000
    assert is_stale([_sig(now - 4 * 3600_000)], now, 1.0) is True


def test_is_stale_false_when_fresh():
    now = 10_000_000
    assert is_stale([_sig(now - 10_000)], now, 1.0) is False


def test_is_stale_true_when_empty():
    assert is_stale([None, None], 10_000_000, 1.0) is True
```

- [ ] **Step 2: 跑测试确认失败**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: FAIL（ImportError）

- [ ] **Step 3: 写 pipeline.py**

```python
"""一次运行编排：拉 biyi → 逐 ticker 拉 datahub → 闸门 → 查 PG → 组表。"""
from __future__ import annotations

from dataclasses import dataclass

from cta_monitor.biyi import BiyiClient
from cta_monitor.config import Config
from cta_monitor.datahub import DatahubReader
from cta_monitor.db import aggregate_trades, fetch_trades, signal_ms_to_beijing
from cta_monitor.metrics import (
    SHOULD_QUERY_STATUSES,
    build_row,
    classify_status,
    coin_from_ticker,
    sym_from_ticker,
)
from cta_monitor.models import ReportRow, RowStatus, SignalRecord


@dataclass(frozen=True)
class RunResult:
    stale: bool
    rows: list[ReportRow]
    summary: str


def is_stale(
    signals: list[SignalRecord | None], now_ms: int, freshness_hours: float
) -> bool:
    """最新信号时间超过 freshness 窗 → 视为无新信号。全空也 stale。"""
    times = [s.signal_bar_ts_ms for s in signals if s is not None]
    if not times:
        return True
    return max(times) < now_ms - int(freshness_hours * 3600_000)


def run_once(
    cfg: Config,
    now_ms: int,
    *,
    biyi: BiyiClient | None = None,
    datahub: DatahubReader | None = None,
) -> RunResult:
    biyi = biyi or BiyiClient(cfg.biyi)
    datahub = datahub or DatahubReader(cfg.datahub)

    # 1) biyi 策略列表（按 allowlist 收窄）
    strategies = biyi.strategy_list_all()
    if cfg.accounts:
        strategies = {s: a for s, a in strategies.items() if a in cfg.accounts}

    # 2) 逐策略逐 symbol：biyi 行 + datahub 信号
    pairs: list[tuple] = []  # (BiyiRow, SignalRecord | None)
    for spec, account in strategies.items():
        for b in biyi.fetch_financials(spec, account):
            sig = datahub.latest_signal(account, coin_from_ticker(b.ticker))
            pairs.append((b, sig))

    # 3) 无新信号闸门
    if is_stale([sig for _, sig in pairs], now_ms, cfg.freshness_hours):
        return RunResult(True, [], "上一小时没有新信号在运行")

    # 4) 逐行判定 → 该查 PG 的查 → 组行
    rows: list[ReportRow] = []
    for b, sig in pairs:
        status = classify_status(b, sig, min_notional_u=cfg.min_notional_u)
        agg = None
        if status in SHOULD_QUERY_STATUSES and sig is not None:
            trades = fetch_trades(
                cfg.pg,
                b.strategy_name,
                sym_from_ticker(b.ticker, b.venue),
                signal_ms_to_beijing(sig.signal_bar_ts_ms),
            )
            agg = aggregate_trades(trades)
            if agg is None and status == RowStatus.OK:
                status = RowStatus.NO_TRADES
        rows.append(build_row(b, sig, agg, status))

    rows.sort(key=lambda r: r.ticker)
    ok = sum(1 for r in rows if r.status == RowStatus.OK)
    running = sum(1 for r in rows if r.status == RowStatus.RUNNING)
    alert = sum(1 for r in rows if r.status in (RowStatus.SIGNAL_TIME_MISMATCH, RowStatus.NO_TRADES))
    summary = (
        f"CTA 执行监控 | ticker={len(rows)} 正常={ok} 运行中={running} 告警={alert}"
    )
    return RunResult(False, rows, summary)
```

- [ ] **Step 4: 跑测试确认通过**

Run: `uv run pytest tests/test_pipeline.py -v`
Expected: PASS

- [ ] **Step 5: commit**

```bash
git add src/cta_monitor/pipeline.py tests/test_pipeline.py
git commit -m "feat: pipeline 编排 + 无新信号闸门"
```

---

## Task 10: cron 入口 + 端到端验证

**Files:**
- Create: `scripts/run.py`
- Modify: `src/cta_monitor/biyi.py`（用探针结果回填 `FINANCIALS_COLS`）
- Test: 手动 e2e（无新单测）

**Interfaces:**
- Consumes: `load_config`、`run_once`、`render_table_text`、`SlackClient`。

- [ ] **Step 1: 回填 FINANCIALS_COLS**

用 Task 5 Step 2 探针打印的表头 token，把 `src/cta_monitor/biyi.py` 的 `FINANCIALS_COLS` 6 个待确认值改成真实 token。改完重跑 `uv run pytest tests/test_biyi.py -v`（合成表头测试不受影响，仍 PASS）。

- [ ] **Step 2: 写 scripts/run.py**

```python
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
```

- [ ] **Step 3: 全量单测**

Run: `uv run pytest -v`
Expected: 全 PASS。

- [ ] **Step 4: 端到端跑一次（真实凭证）**

前置：`config.toml` 填好 PG（复用 `analyse_excution/config.toml`）、biyi、datahub api_key、slack webhook_url。
Run: `cd /Users/mac/dev/cta_monitor && uv run python scripts/run.py`
Expected（择一）：
- 有新信号 → Slack 频道收到一条标题 + 一/多条代码块文本表（14 列等宽对齐）。
- 无新信号 → Slack 收到「上一小时没有新信号在运行」。

验证：对 1-2 个 ticker 手工核对文本表数字与图口径一致（尤其 完成比例、maker比例、执行时间ms）；确认 running 行首标「运行中」、时间不匹配行首标「⚠时间不符」。

- [ ] **Step 5: 配置每小时 cron**

在部署机 crontab（整点跑）：
```cron
5 * * * * cd /Users/mac/dev/cta_monitor && /path/to/uv run python scripts/run.py >> output/cron.log 2>&1
```
（分钟设 5 是给整点信号留出发布余量；按实际 grid 点微调。）

- [ ] **Step 6: commit**

```bash
git add scripts/run.py src/cta_monitor/biyi.py
git commit -m "feat: cron 入口 + 回填 financials 表头 token"
```

---

## 自查记录（对照 spec）

- §3 闸门：无新信号（`is_stale`, Task 9）/ running（`classify_status`, Task 3）/ 小额（`SMALL_NOTIONAL`, Task 3）/ 信号时间不匹配告警（`SIGNAL_TIME_MISMATCH`, Task 3）—— 均有任务覆盖。
- §4.1 biyi 过滤（CTA/CTA_EMS+RUNNING+allowlist）：Task 5 `strategy_list_all` + Task 9 allowlist。
- §4.2 datahub key（biyi 驱动、CYBERX_PROD 严格拼）：Task 6 `datahub_key`。
- §4.3 PG 汇总（strategy_name/sym/app_receive>信号时间/FULL_EXEC；maker成交额占比；min/max event_time）：Task 4。
- §5 14 列公式（含负 delta abs 分母、报单笔数 roundup、小于单笔报单量）：Task 2/3。
- §6 输出（**文本表**代码块 + 汇总 + 无新信号文本，webhook 发送，不发图片）：Task 7/8/9/10。
- §7 工程结构：全任务。
- §8 开放项：凭证（Task 1 config.example + Task 10 前置）；datahub 薄实现（Task 6，已确认走 vendor SDK 无需 alpha_copy）；financials 表头 token（Task 5 探针 + Task 10 回填）。
- 类型一致性：`SignalRecord/BiyiRow/TradeRow/TradeAgg/ReportRow/RowStatus` 在 Task 1 定义，后续任务签名一致；`SHOULD_QUERY_STATUSES` 定义于 Task 3、消费于 Task 9。
