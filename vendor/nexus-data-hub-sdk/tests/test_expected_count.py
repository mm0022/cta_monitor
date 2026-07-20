"""
Integration test: for each start/end window, request DATABENTO/FUT/NQ_V0 KLINE_1H via
the SDK and assert that the resulting ``HubData.missing`` flag is False — i.e. every
trading-hour timestamp derived from EVENT_1H is present in the kline DataFrame's index
(extra non-trading-hour bars are ignored; absent trading hours flip the flag).

Each window is a separate parametrized case so per-window failures are isolated in the
pytest report. Requires SDK access to a running data-hub with valid DATABENTO/FUT/NQ_V0
KLINE_1H + EVENT_1H coverage.

Run:
    pytest tests/test_expected_count.py -v
Overrides:
    DATA_HUB_API_KEY=... pytest tests/test_expected_count.py
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone

import pytest

from nexus_data_hub_sdk import Client, DataType, ParamInvalidError, NexusHubAPIError


# ── config ──────────────────────────────────────────────────────────────────
API_KEY = os.environ.get(
    'DATA_HUB_API_KEY', '5aed5488fec148b291b0b90f2c701c1e')
EXCHANGE = 'DATABENTO'
BUSINESS = 'FUT'
DATA_TYPE = DataType.KLINE_1H
SYM = 'NQ_V0'

INTERVAL_MS = 3_600_000
MIN_MS = 1640995200000  # 2022-01-01T00:00:00.000Z — server-side DATABENTO_MIN_START_MS


# ── helpers ─────────────────────────────────────────────────────────────────
def utc_ms(year: int, month: int, day: int, hour: int = 0) -> int:
    return int(datetime(year, month, day, hour, tzinfo=timezone.utc).timestamp() * 1000)


def hour_window(year: int, month: int, day: int, hours: int) -> tuple[int, int]:
    """Start at year/month/day 00:00 UTC, span ``hours`` hourly bars (inclusive)."""
    start = utc_ms(year, month, day)
    end = start + hours * INTERVAL_MS - 1
    return start, end


def _current_max_ms() -> int:
    """Last-complete-hour inclusive-end-ms (mirrors ``truncatedToStart(now, 1H) - 1``)."""
    now = int(time.time() * 1000)
    return (now // INTERVAL_MS) * INTERVAL_MS - 1


def _build_windows() -> list[tuple[str, int, int]]:
    max_ms = _current_max_ms()
    next_bar_start = max_ms + 1
    one_hour_ago_start = max_ms - INTERVAL_MS + 1
    return [
        # ── happy-path windows ────────────────────────────────────────────────
        ('user-example (2022-01-01 → 2022-01-03 23:00)', 1640995200000, 1641164400000),
        ('one CME trading day (Mon 2024-06-03)',) + hour_window(2024, 6, 3, 24),
        ('weekend only (Sat 2024-06-08 → Mon 2024-06-10, 48h)',) + hour_window(2024, 6, 8, 48),
        ('one week (Mon 2024-06-03 → Sun 2024-06-09)',) + hour_window(2024, 6, 3, 7 * 24),
        ('month boundary (2024-05-31 → 2024-06-01)',) + hour_window(2024, 5, 31, 48),
        ('US Independence Day (2024-07-02 → 2024-07-05)',) + hour_window(2024, 7, 2, 4 * 24),
        ('very narrow (1 hour bar)',) + hour_window(2024, 6, 3, 1),

        # ── boundary / collapse cases ─────────────────────────────────────────
        ('entirely before 2022 (2021-06 → 2021-07)',
         utc_ms(2021, 6, 1), utc_ms(2021, 7, 1) - 1),
        ('entirely after MAX (future 1h window)',
         next_bar_start, next_bar_start + INTERVAL_MS - 1),
        ('straddles MIN (2021-12-31 → end of 2022-01-02)',
         utc_ms(2021, 12, 31), utc_ms(2022, 1, 3) - 1),
        ('straddles MAX (24h ago → +24h future)',
         max_ms - 24 * INTERVAL_MS + 1, max_ms + 24 * INTERVAL_MS),

        # ── degenerate / single-point cases ───────────────────────────────────
        ('start == end at a bar boundary', utc_ms(2024, 6, 3), utc_ms(2024, 6, 3)),
        ('start == end mid-bar (12:30 exact)',
         utc_ms(2024, 6, 3, 12) + 30 * 60_000, utc_ms(2024, 6, 3, 12) + 30 * 60_000),
        ('start < end == MIN floor', utc_ms(2021, 12, 1), MIN_MS),
        ('start == MAX < end', max_ms, max_ms + 7 * 24 * INTERVAL_MS),
        ('start == MIN, one bar', MIN_MS, MIN_MS + INTERVAL_MS - 1),
        ('end == MAX, last complete hour', one_hour_ago_start, max_ms),

        # ── invalid / defensive cases ─────────────────────────────────────────
        ('inverted (start > end)', utc_ms(2024, 6, 4), utc_ms(2024, 6, 3)),
    ]


WINDOWS = _build_windows()

# Windows the SDK is expected to reject before producing a ``HubData``:
# ``ParamInvalidError`` is raised client-side by ``__validate_range`` for inverted
# ranges; ``NexusHubAPIError`` is raised server-side (422) for windows entirely
# past the last available bar. Listing them explicitly keeps the happy-path
# assertion strict — an unexpected raise on any other window fails the test.
INVALID_WINDOWS = {
    'inverted (start > end)',
    'entirely after MAX (future 1h window)',
}


# ── fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture(scope='module')
def client() -> Client:
    kwargs = {
        'missing_exception': False,
        'updated_exception': False,
        'local_first': False,
    }
    return Client(API_KEY, **kwargs)


# ── tests ───────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    'name,start_ms,end_ms',
    WINDOWS,
    ids=[w[0] for w in WINDOWS],
)
def test_no_missing(client: Client, name: str, start_ms: int, end_ms: int) -> None:
    if name in INVALID_WINDOWS:
        with pytest.raises((ParamInvalidError, NexusHubAPIError)):
            client.request_by_type(
                EXCHANGE, BUSINESS, SYM, DATA_TYPE, start_ms, end_ms)
        return
    hd = client.request_by_type(
        EXCHANGE, BUSINESS, SYM, DATA_TYPE, start_ms, end_ms)
    assert not hd.missing, (
        f'{name}: start_ms={start_ms}, end_ms={end_ms}, rows={len(hd.data)}'
    )
