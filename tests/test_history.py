import json

from cta_monitor.config import (
    BiyiConfig,
    Config,
    DatahubConfig,
    PgConfig,
    SlackConfig,
)
from cta_monitor.history import append_run_record, run_record
from cta_monitor.metrics import ATTENTION_MAKER_RATIO, ATTENTION_ORDER_COUNT
from cta_monitor.models import ReportRow, RowStatus


def _cfg(freshness_hours=3.0, min_notional_u=10.0):
    return Config(
        pg=PgConfig("h", "1", "u", "p", "shiji"),
        biyi=BiyiConfig("lu", "bu", "u", "pw"),
        datahub=DatahubConfig("g", "k", "CYBERX_PROD"),
        slack=SlackConfig("wh"),
        accounts=(),
        min_notional_u=min_notional_u,
        freshness_hours=freshness_hours,
    )


def _row(account="binance_cta_acc1", status=RowStatus.OK, ticker="DOGE/USDT",
         maker=0.9, incomplete=1.0):
    return ReportRow(
        ticker=ticker, account=account, mark_price=1.0, trade_size=2.0,
        order_notional_u=2.0, qty_change="10→5", delta_qty=-5.0, delta_u=-5.0,
        n_orders=2.5, maker_ratio=maker, end_ms=2000, start_ms=1000, duration_ms=1000,
        twap_unfilled_qty=0.1, unfilled_u=0.1, incomplete_pct=incomplete, status=status,
        order_count=8, maker_notional=90.0, total_notional=100.0, truly_unfilled=False,
    )


def test_run_record_structure_and_params():
    rows = [
        _row(status=RowStatus.OK),
        _row(status=RowStatus.RUNNING, ticker="BTC/USDT"),
        _row(status=RowStatus.NO_TRADES, ticker="XRP/USDT"),
    ]
    rec = run_record(rows, now_ms=1784687971666, cfg=_cfg(freshness_hours=3.0))

    assert rec["ts_ms"] == 1784687971666
    assert rec["time_bj"] == "2026-07-22 10:39"          # 北京时区格式化
    # 参数：配置 + 代码常量阈值
    assert rec["params"] == {
        "freshness_hours": 3.0,
        "min_notional_u": 10.0,
        "attention_order_count": ATTENTION_ORDER_COUNT,
        "attention_maker_ratio": ATTENTION_MAKER_RATIO,
    }
    # 汇总计数
    assert rec["summary"] == {"ticker": 3, "ok": 1, "running": 1, "alert": 1}
    # 账户汇总 + 明细
    assert isinstance(rec["accounts"], list) and rec["accounts"]
    assert len(rec["rows"]) == 3


def test_run_record_status_is_string_and_json_serializable():
    rec = run_record([_row(status=RowStatus.OK)], now_ms=1784687971666, cfg=_cfg())
    assert rec["rows"][0]["status"] == "ok"              # 枚举 → 字符串
    # 整条记录可 JSON round-trip（不抛异常）
    s = json.dumps(rec, ensure_ascii=False)
    back = json.loads(s)
    assert back["rows"][0]["ticker"] == "DOGE/USDT"
    assert back["rows"][0]["maker_ratio"] == 0.9


def test_append_run_record_appends_not_overwrites(tmp_path):
    p = str(tmp_path / "runs.jsonl")
    append_run_record(p, run_record([_row()], 1784687971666, _cfg()))
    append_run_record(p, run_record([_row(), _row(ticker="BTC/USDT")], 1784691571666, _cfg()))

    lines = [json.loads(x) for x in open(p, encoding="utf-8")]
    assert len(lines) == 2                                # 两次运行两行，未覆盖
    assert lines[0]["summary"]["ticker"] == 1
    assert lines[1]["summary"]["ticker"] == 2


def test_run_record_params_reflect_config():
    rec = run_record([_row()], 1784687971666, _cfg(freshness_hours=4.0, min_notional_u=25.0))
    assert rec["params"]["freshness_hours"] == 4.0
    assert rec["params"]["min_notional_u"] == 25.0
