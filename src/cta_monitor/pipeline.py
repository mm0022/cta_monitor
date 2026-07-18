"""一次运行编排：拉 biyi → 逐 ticker 拉 datahub → 闸门 → 查 PG → 组表。"""
from __future__ import annotations

from dataclasses import dataclass

from cta_monitor.biyi import BiyiClient
from cta_monitor.config import Config
from cta_monitor.datahub import DatahubReader
from cta_monitor.db import aggregate_trades, fetch_events_batch, signal_ms_to_utc_str
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
    #    组合级账户(portfolio_accounts)：一次读组合 key 拆 per_token；其余按币逐个读 CTA key
    pairs: list[tuple] = []  # (BiyiRow, SignalRecord | None)
    for spec, account in strategies.items():
        portfolio_id = cfg.portfolio_accounts.get(account)
        port_sigs = (
            datahub.latest_portfolio_signals(account, portfolio_id)
            if portfolio_id else None
        )
        for b in biyi.fetch_financials(spec, account):
            coin = coin_from_ticker(b.ticker)
            if port_sigs is not None:
                sig = port_sigs.get(coin)
            else:
                sig = datahub.latest_signal(account, coin)
            pairs.append((b, sig))

    # 3) 无新信号闸门（全部信号都超出 freshness 窗 → 整体跳过）
    if is_stale([sig for _, sig in pairs], now_ms, cfg.freshness_hours):
        return RunResult(
            True, [], f"最近 {cfg.freshness_hours:g} 小时内没有新信号在运行"
        )

    # 4) 逐行判定；只统计「信号时间在 freshness_hours 内」的币（无信号/超窗 → 不进表）
    cutoff_ms = now_ms - int(cfg.freshness_hours * 3600_000)
    fresh = [
        (b, sig) for b, sig in pairs
        if sig is not None and sig.signal_bar_ts_ms >= cutoff_ms
    ]
    entries = []  # (b, sig, status, sym)
    requests = []  # (account_no, sym, signal_time_utc) —— 需查 PG 的
    for b, sig in fresh:
        status = classify_status(b, sig, min_notional_u=cfg.min_notional_u)
        sym = sym_from_ticker(b.ticker, b.venue)
        entries.append((b, sig, status, sym))
        if status in SHOULD_QUERY_STATUSES:
            requests.append((b.account, sym, signal_ms_to_utc_str(sig.signal_bar_ts_ms)))

    # 一次连接、一条查询批量拉成交事件，再按 (account, sym) 分发聚合
    events = fetch_events_batch(cfg.pg, requests)

    rows: list[ReportRow] = []
    for b, sig, status, sym in entries:
        agg = None
        if status in SHOULD_QUERY_STATUSES:
            agg = aggregate_trades(events.get((b.account, sym), []))
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
