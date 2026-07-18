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
    """order_event_his 一条事件（含各 event_type，非仅 FULL_EXEC）。"""
    is_maker: int             # 1=maker, 0=taker（非成交事件无意义）
    quantity: float           # exchange_quantity（非成交事件可能为 0）
    price: float              # exchange_price（非成交事件可能为 0）
    event_time: int           # ms epoch
    event_type: str = "FULL_EXEC"  # 事件类型；maker 只统计 FULL_EXEC，时间跨全部事件
    order_id: str = ""        # 订单号；执行单数 = 本轮全部事件去重 order_id 数（含未成交）


@dataclass(frozen=True)
class TradeAgg:
    maker_ratio: float        # maker成交额 / 总成交额
    start_ms: int             # min(event_time)
    end_ms: int               # max(event_time)
    duration_ms: int          # end - start
    order_count: int = 0      # 执行单数 = 本轮全部事件去重 order_id 数（含挂撤未成交）


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
    account: str                        # 所属 biyi 账户（多账户合表时区分）
    mark_price: float | None            # B
    trade_size: float | None            # C
    order_notional_u: float | None      # D
    qty_change: str                     # E  "cur→target"
    delta_qty: float | None             # F
    delta_u: float | None               # F 的 U 量 = delta_qty × mark_price（1 位小数）
    n_orders: float | None              # G
    maker_ratio: float | None           # H
    end_ms: int | None                  # I
    start_ms: int | None                # J
    duration_ms: int | None             # K
    twap_unfilled_qty: float | None     # L
    unfilled_u: float | None            # M
    incomplete_pct: float | None        # N（未完成比例 %）
    status: RowStatus
    note: str = ""
    order_count: int | None = None      # 执行订单数（FULL_EXEC 去重 order_id）
