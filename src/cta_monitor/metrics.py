"""列公式与符号解析——全部无 IO 纯函数。"""
from __future__ import annotations

import math

from cta_monitor.models import BiyiRow, ReportRow, RowStatus, SignalRecord, TradeAgg


def coin_from_ticker(ticker: str) -> str:
    """"DOGE/USDT" -> "doge"（datahub key 的 coin 段，小写 base）。"""
    return ticker.split("/", 1)[0].strip().lower()


def sym_from_ticker(ticker: str, venue: str) -> str:
    """("DOGE/USDT","BINANCE_PERP") -> "BINANCE_PERP_DOGE_USDT"（order_event.sym）。
    biyi VENUE 值已含市场段（如 BINANCE_PERP），直接与 base/quote 拼接。"""
    base, quote = ticker.split("/", 1)
    return f"{venue.strip().upper()}_{base.strip().upper()}_{quote.strip().upper()}"


def trunc_to(value: float, ndigits: int) -> float:
    """截断（向零取整）到 ndigits 位小数——复现截图口径，非四舍五入。"""
    factor = 10 ** ndigits
    return math.trunc(round(value * factor, 9)) / factor


def n_orders(delta_qty: float, trade_size: float) -> float:
    """报单笔数 = 截断(abs(delta)/单笔粒度, 1 位)。"""
    return trunc_to(abs(delta_qty) / trade_size, 1)


def incomplete_pct(unfilled_qty: float, delta_qty: float) -> float:
    """未完成比例 = round(abs(未完成)/abs(delta) * 100, 2)。分母取 abs 兼容负 delta。"""
    return round(abs(unfilled_qty) / abs(delta_qty) * 100, 2)


SHOULD_QUERY_STATUSES: set[RowStatus] = {RowStatus.OK, RowStatus.SIGNAL_TIME_MISMATCH}


def account_summary(rows: list["ReportRow"]) -> list[dict]:
    """按账户聚合执行质量（maker比例 + 完成度），供简报展示。纯函数。
    完成度 = 100 − 未完成比例%；平均只对「已执行」行（maker_ratio 非空）统计。
    返回按账户排序的 dict 列表。"""
    from collections import defaultdict

    groups: dict[str, list] = defaultdict(list)
    for r in rows:
        groups[r.account].append(r)

    out: list[dict] = []
    for acc in sorted(groups):
        rs = groups[acc]
        execed = [r for r in rs if r.maker_ratio is not None]
        # 账户级 maker% = 该账户所有币的 maker 总成交额 / 总成交额（成交额加权）
        maker_notional = sum(r.maker_notional or 0.0 for r in execed)
        total_notional = sum(r.total_notional or 0.0 for r in execed)
        comps = [
            (r.ticker, round(100 - r.incomplete_pct, 2))
            for r in execed if r.incomplete_pct is not None
        ]
        worst = min(comps, key=lambda x: x[1]) if comps else None
        out.append({
            "account": acc,
            "n": len(rs),
            "executed": len(execed),
            "total_notional": round(total_notional, 2),  # 该账户总成交额(USD)
            "avg_maker": (
                round(maker_notional / total_notional * 100, 2)
                if total_notional else None
            ),
            "avg_completion": (
                round(sum(c for _, c in comps) / len(comps), 2) if comps else None
            ),
            "worst_ticker": worst[0] if worst else "",
            "worst_completion": worst[1] if worst else None,
        })
    return out


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
            ticker=biyi.ticker, account=biyi.account, mark_price=None, trade_size=biyi.trade_size,
            order_notional_u=None, qty_change="", delta_qty=None, n_orders=None,
            maker_ratio=None, end_ms=None, start_ms=None, duration_ms=None,
            delta_u=None,
            twap_unfilled_qty=None, unfilled_u=None, incomplete_pct=None,
            status=status, note="datahub 无信号",
        )

    unfilled = biyi.current_inventory - sig.target_qty
    incomplete = (
        incomplete_pct(unfilled, sig.delta_qty) if sig.delta_qty != 0 else None
    )
    return ReportRow(
        ticker=biyi.ticker,
        account=biyi.account,
        mark_price=sig.mark_price,
        trade_size=biyi.trade_size,
        order_notional_u=trunc_to(biyi.trade_size * sig.mark_price, 0),  # 图为整数、截断
        qty_change=f"{sig.current_qty_at_decision}→{sig.target_qty}",
        delta_qty=sig.delta_qty,
        delta_u=round(sig.delta_qty * sig.mark_price, 1),
        n_orders=n_orders(sig.delta_qty, biyi.trade_size),
        maker_ratio=agg.maker_ratio if agg else None,
        end_ms=agg.end_ms if agg else None,
        start_ms=agg.start_ms if agg else None,
        duration_ms=agg.duration_ms if agg else None,
        twap_unfilled_qty=unfilled,
        unfilled_u=round(unfilled * sig.mark_price, 6),
        incomplete_pct=incomplete,
        status=status,
        note="",
        order_count=agg.order_count if agg else None,
        maker_notional=agg.maker_notional if agg else None,
        total_notional=agg.total_notional if agg else None,
    )
