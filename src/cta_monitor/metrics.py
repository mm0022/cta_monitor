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
