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
