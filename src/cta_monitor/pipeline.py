"""一次运行编排：拉 biyi → 逐 ticker 拉 datahub → 闸门 → 查 PG → 组表。"""
from __future__ import annotations

from dataclasses import dataclass

from cta_monitor.biyi import BiyiClient
from cta_monitor.config import Config
from cta_monitor.datahub import DatahubReader
from cta_monitor.db import aggregate_trades, fetch_trades, signal_ms_to_utc_str
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

    # 3) 无新信号闸门（全部信号都超出 freshness 窗 → 整体跳过）
    if is_stale([sig for _, sig in pairs], now_ms, cfg.freshness_hours):
        return RunResult(
            True, [], f"最近 {cfg.freshness_hours:g} 小时内没有新信号在运行"
        )

    # 4) 逐行判定 → 该查 PG 的查 → 组行
    #    只统计「信号时间在 freshness_hours 内」的币：无信号、或信号超窗（≥freshness）→ 不进表
    cutoff_ms = now_ms - int(cfg.freshness_hours * 3600_000)
    rows: list[ReportRow] = []
    for b, sig in pairs:
        if sig is None or sig.signal_bar_ts_ms < cutoff_ms:
            continue  # datahub 无信号 / 信号超出 3h 窗 → 不纳入本轮报告
        status = classify_status(b, sig, min_notional_u=cfg.min_notional_u)
        agg = None
        if status in SHOULD_QUERY_STATUSES:
            trades = fetch_trades(
                cfg.pg,
                b.account,
                sym_from_ticker(b.ticker, b.venue),
                signal_ms_to_utc_str(sig.signal_bar_ts_ms),
            )
            agg = aggregate_trades(trades)
            if agg is None and status == RowStatus.OK:
                status = RowStatus.NO_TRADES
        rows.append(build_row(b, sig, agg, status))

    rows.sort(key=lambda r: (r.account, r.ticker))
    ok = sum(1 for r in rows if r.status == RowStatus.OK)
    running = sum(1 for r in rows if r.status == RowStatus.RUNNING)
    alert = sum(1 for r in rows if r.status in (RowStatus.SIGNAL_TIME_MISMATCH, RowStatus.NO_TRADES))
    summary = (
        f"CTA 执行监控 | ticker={len(rows)} 正常={ok} 运行中={running} 告警={alert}"
    )
    return RunResult(False, rows, summary)
