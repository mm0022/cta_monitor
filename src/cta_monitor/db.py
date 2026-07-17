"""order_event_his 取数与聚合。"""
from __future__ import annotations

from datetime import datetime, timezone

import psycopg

from cta_monitor.config import PgConfig
from cta_monitor.models import TradeAgg, TradeRow

# 注意：不加 event_type 过滤。执行窗口（开始/结束/执行ms）跨本轮全部事件
# （下单/撤改/成交等）；maker 比例只从 FULL_EXEC 成交子集算（见 aggregate_trades）。
_SQL = """
SELECT s.event_type, s.is_maker, s.exchange_quantity, s.exchange_price, s.event_time
FROM order_event_his s
WHERE s.strategy_name = %(strategy_name)s
  AND s.sym          = %(sym)s
  AND s.app_receive  > %(signal_time)s;
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
    )


def signal_ms_to_utc_str(signal_bar_ts_ms: int) -> str:
    """UTC ms → 'YYYY-MM-DD HH:MM:SS'（UTC）。
    order_event.app_receive 实测为 UTC（app_receive==event_time UTC），与 signal_bar_ts_ms 同口径。"""
    dt = datetime.fromtimestamp(signal_bar_ts_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def fetch_trades(
    pg: PgConfig, strategy_name: str, sym: str, signal_time_utc: str
) -> list[TradeRow]:
    """按 (strategy_name, sym, app_receive>信号时间(UTC)) 拉本轮全部事件（不限 event_type）。"""
    with psycopg.connect(
        host=pg.host,
        port=pg.port,
        user=pg.user,
        password=pg.password,
        dbname=pg.database,
    ) as conn, conn.cursor() as cur:
        cur.execute(
            _SQL,
            {"strategy_name": strategy_name, "sym": sym, "signal_time": signal_time_utc},
        )
        return [
            TradeRow(
                event_type=r[0],
                is_maker=int(r[1]) if r[1] is not None else 0,
                quantity=float(r[2]) if r[2] is not None else 0.0,
                price=float(r[3]) if r[3] is not None else 0.0,
                event_time=int(r[4]),
            )
            for r in cur.fetchall()
        ]
