"""order_event_his 取数与聚合。"""
from __future__ import annotations

from datetime import datetime, timezone

import psycopg

from cta_monitor.config import PgConfig
from cta_monitor.models import TradeAgg, TradeRow

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


def signal_ms_to_utc_str(signal_bar_ts_ms: int) -> str:
    """UTC ms → 'YYYY-MM-DD HH:MM:SS'（UTC）。
    order_event.app_receive 实测为 UTC（app_receive==event_time UTC），与 signal_bar_ts_ms 同口径。"""
    dt = datetime.fromtimestamp(signal_bar_ts_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def fetch_trades(
    pg: PgConfig, strategy_name: str, sym: str, signal_time_utc: str
) -> list[TradeRow]:
    """按 (strategy_name, sym, app_receive>信号时间(UTC), FULL_EXEC) 拉成交。"""
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
                is_maker=int(r[0]),
                quantity=float(r[1]),
                price=float(r[2]),
                event_time=int(r[3]),
            )
            for r in cur.fetchall()
        ]
