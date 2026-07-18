"""order_event 取数与聚合。

性能：一次连接、一条查询批量拉全部 (account, sym) 的事件（app_receive > 最早信号时间），
再在内存按每行自己的信号时间过滤 + 聚合，避免逐行反复连库。
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

import psycopg

from cta_monitor.config import PgConfig
from cta_monitor.models import TradeAgg, TradeRow

# 用 order_event（全生命周期事件，非仅成交的 order_event_his）。
# 不加 event_type 过滤：执行窗口（开始/结束/执行ms）跨本轮全部事件的 event_time min/max；
# maker 比例只从 FULL_EXEC 成交子集算（见 aggregate_trades）。
_BATCH_SQL = """
SELECT s.account_no, s.sym, s.event_type, s.is_maker,
       s.exchange_quantity, s.exchange_price, s.event_time, s.app_receive, s.order_id
FROM order_event s
WHERE s.app_receive > %(min_time)s
  AND s.account_no = ANY(%(accounts)s)
  AND s.sym        = ANY(%(syms)s);
"""


def aggregate_trades(rows: list[TradeRow]) -> TradeAgg | None:
    """执行窗口(start/end/duration)= 全部事件 event_time 的 min/max/差；
    maker比例 = FULL_EXEC 成交里 maker成交额/总成交额。无任何事件 → None。"""
    if not rows:
        return None
    times = [r.event_time for r in rows]
    start_ms, end_ms = min(times), max(times)
    fills = [r for r in rows if r.event_type == "FULL_EXEC"]
    total_notional = sum(r.quantity * r.price for r in fills)
    maker_notional = sum(r.quantity * r.price for r in fills if r.is_maker == 1)
    return TradeAgg(
        maker_ratio=(maker_notional / total_notional) if total_notional else 0.0,
        start_ms=start_ms,
        end_ms=end_ms,
        duration_ms=end_ms - start_ms,
        order_count=len({r.order_id for r in fills if r.order_id}),
    )


def signal_ms_to_utc_str(signal_bar_ts_ms: int) -> str:
    """UTC ms → 'YYYY-MM-DD HH:MM:SS'（UTC）。
    order_event.app_receive 实测为 UTC（app_receive==event_time UTC），与 signal_bar_ts_ms 同口径。"""
    dt = datetime.fromtimestamp(signal_bar_ts_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def _to_naive_utc(dt: datetime) -> datetime:
    """把 DB 取回的 app_receive 归一成 naive UTC，便于和信号时间字符串比较。"""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def fetch_events_batch(
    pg: PgConfig, requests: list[tuple[str, str, str]]
) -> dict[tuple[str, str], list[TradeRow]]:
    """一次连接、一条查询拉全部事件，再按每个 (account_no, sym) 自己的信号时间过滤。

    requests: [(account_no, sym, signal_time_utc), ...]（每个 (account,sym) 唯一）。
    返回 {(account_no, sym): [TradeRow(app_receive>该行信号时间)]}。
    """
    if not requests:
        return {}
    st_map = {(a, s): st for a, s, st in requests}
    st_dt = {k: datetime.strptime(v, "%Y-%m-%d %H:%M:%S") for k, v in st_map.items()}
    min_time = min(st_map.values())
    accounts = sorted({a for a, _, _ in requests})
    syms = sorted({s for _, s, _ in requests})

    with psycopg.connect(
        host=pg.host, port=pg.port, user=pg.user,
        password=pg.password, dbname=pg.database,
    ) as conn, conn.cursor() as cur:
        cur.execute(_BATCH_SQL, {"min_time": min_time, "accounts": accounts, "syms": syms})
        fetched = cur.fetchall()

    out: dict[tuple[str, str], list[TradeRow]] = defaultdict(list)
    for r in fetched:
        key = (r[0], r[1])
        st = st_dt.get(key)
        if st is None:                       # account×sym 交叉里不需要的组合
            continue
        if _to_naive_utc(r[7]) <= st:        # 只保留本行信号时间之后的事件（严格 >）
            continue
        out[key].append(TradeRow(
            event_type=r[2],
            is_maker=int(r[3]) if r[3] is not None else 0,
            quantity=float(r[4]) if r[4] is not None else 0.0,
            price=float(r[5]) if r[5] is not None else 0.0,
            event_time=int(r[6]),
            order_id=str(r[8]) if r[8] is not None else "",
        ))
    # 保证请求过的 key 都有条目（可能为空列表）
    return {k: out.get(k, []) for k in st_map}
