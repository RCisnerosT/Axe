import pandas as pd
import pytest

from resample import resample_cascade

ET = "America/New_York"


def _bars(date: str, et_times: list, base_price: float = 100.0) -> pd.DataFrame:
    """Synthetic 30m bars for one session: one row per HH:MM in `et_times`,
    prices increasing by 1 per bar so open/high/low/close are distinguishable
    and volume is 1 per bar so summed volume is trivially checkable."""
    rows = []
    for i, t in enumerate(et_times):
        ts = pd.Timestamp(f"{date} {t}", tz=ET).tz_convert("UTC")
        price = base_price + i
        rows.append(
            {
                "timestamp": ts,
                "open": price,
                "high": price + 0.5,
                "low": price - 0.5,
                "close": price + 0.25,
                "volume": 1,
            }
        )
    return pd.DataFrame(rows)


FULL_SESSION_TIMES = [
    "09:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30",
    "13:00", "13:30", "14:00", "14:30", "15:00", "15:30",
]  # 13 bars = 6.5h regular session


def test_completed_session_keeps_short_trailing_bucket():
    bars = _bars("2026-01-05", FULL_SESSION_TIMES)
    now = pd.Timestamp("2026-01-06 12:00", tz=ET).tz_convert("UTC")  # well after close

    result = resample_cascade(bars, now=now)

    # 13 x 30m -> 6 full 1h buckets + 1 short trailing bucket (15:30-16:00)
    assert len(result["1h"]) == 7
    # 13 x 30m -> one 8-bar 4h bucket + one short 5-bar trailing bucket
    assert len(result["4h"]) == 2


def test_short_trailing_bucket_closes_at_actual_market_close_not_nominal_span():
    # The short trailing 1h bucket (15:30-16:00, only one 30m bar) must
    # close at 16:00 ET (market close) -- NOT 16:30, which is what
    # `timestamp + 1h` would naively give. Same for the short trailing 4h
    # bucket (13:30-16:00): must close at 16:00 ET, not 17:30.
    bars = _bars("2026-01-05", FULL_SESSION_TIMES)
    now = pd.Timestamp("2026-01-06 12:00", tz=ET).tz_convert("UTC")

    result = resample_cascade(bars, now=now)

    last_1h = result["1h"].iloc[-1]
    assert last_1h["timestamp"].tz_convert(ET).strftime("%H:%M") == "15:30"
    assert last_1h["ts_close"].tz_convert(ET).strftime("%H:%M") == "16:00"

    last_4h = result["4h"].iloc[-1]
    assert last_4h["timestamp"].tz_convert(ET).strftime("%H:%M") == "13:30"
    assert last_4h["ts_close"].tz_convert(ET).strftime("%H:%M") == "16:00"


def test_full_bucket_closes_at_nominal_span():
    bars = _bars("2026-01-05", FULL_SESSION_TIMES)
    now = pd.Timestamp("2026-01-06 12:00", tz=ET).tz_convert("UTC")

    result = resample_cascade(bars, now=now)

    first_1h = result["1h"].iloc[0]
    assert first_1h["timestamp"].tz_convert(ET).strftime("%H:%M") == "09:30"
    assert first_1h["ts_close"].tz_convert(ET).strftime("%H:%M") == "10:30"

    first_4h = result["4h"].iloc[0]
    assert first_4h["timestamp"].tz_convert(ET).strftime("%H:%M") == "09:30"
    assert first_4h["ts_close"].tz_convert(ET).strftime("%H:%M") == "13:30"


def test_completed_session_aggregation_values_are_correct():
    bars = _bars("2026-01-05", FULL_SESSION_TIMES)
    now = pd.Timestamp("2026-01-06 12:00", tz=ET).tz_convert("UTC")

    result = resample_cascade(bars, now=now)
    first_1h = result["1h"].iloc[0]

    # First 1h bucket = bars[0:2] (09:30, 10:00): open=first.open, close=last.close
    assert first_1h["open"] == bars.iloc[0]["open"]
    assert first_1h["close"] == bars.iloc[1]["close"]
    assert first_1h["high"] == max(bars.iloc[0]["high"], bars.iloc[1]["high"])
    assert first_1h["low"] == min(bars.iloc[0]["low"], bars.iloc[1]["low"])
    assert first_1h["volume"] == 2
    assert first_1h["timestamp"] == bars.iloc[0]["timestamp"]


def test_in_progress_session_drops_incomplete_trailing_buckets():
    # 5 bars: 09:30, 10:00, 10:30, 11:00, 11:30 — session still open at 11:45
    bars = _bars("2026-01-07", FULL_SESSION_TIMES[:5])
    now = pd.Timestamp("2026-01-07 11:45", tz=ET).tz_convert("UTC")

    result = resample_cascade(bars, now=now)

    # bucket0 (09:30,10:00) and bucket1 (10:30,11:00) are complete;
    # the 5th bar alone (11:30) forms an incomplete trailing bucket -> dropped
    assert len(result["1h"]) == 2
    # all 5 bars fall in a single (incomplete, session open) 4h bucket -> dropped entirely
    assert len(result["4h"]) == 0


def test_completed_session_with_exactly_complete_buckets_keeps_all():
    # 8 bars = exactly one full 4h bucket, session already closed
    bars = _bars("2026-01-05", FULL_SESSION_TIMES[:8])
    now = pd.Timestamp("2026-01-06 12:00", tz=ET).tz_convert("UTC")

    result = resample_cascade(bars, now=now)

    assert len(result["1h"]) == 4
    assert len(result["4h"]) == 1
    assert result["4h"].iloc[0]["volume"] == 8


def test_two_sessions_do_not_bleed_into_each_other():
    day1 = _bars("2026-01-05", FULL_SESSION_TIMES)
    day2 = _bars("2026-01-06", FULL_SESSION_TIMES)
    bars = pd.concat([day1, day2], ignore_index=True)
    now = pd.Timestamp("2026-01-07 12:00", tz=ET).tz_convert("UTC")  # both days closed

    result = resample_cascade(bars, now=now)

    # Each day independently produces 7 1h buckets / 2 4h buckets -> 14 / 4 total
    assert len(result["1h"]) == 14
    assert len(result["4h"]) == 4
    # No 1h bucket should span the overnight gap: last bucket of day1 stays
    # short (15:30-16:00) rather than merging with day2's first bar.
    day1_last_1h = result["1h"].iloc[6]
    assert day1_last_1h["timestamp"].tz_convert(ET).strftime("%Y-%m-%d %H:%M") == "2026-01-05 15:30"


def test_pre_market_bars_bucket_separately_from_regular_session():
    # Pre-market (04:00-09:30 ET) is a separate 5.5h window from the
    # regular session — real Alpaca SIP data includes both by default, so
    # a bar at 09:00 must not get merged into the same 1h bucket as 09:30.
    pre_market_times = ["04:00", "04:30", "05:00", "08:00", "08:30", "09:00"]
    bars = pd.concat(
        [_bars("2026-01-05", pre_market_times, base_price=90), _bars("2026-01-05", FULL_SESSION_TIMES)],
        ignore_index=True,
    )
    now = pd.Timestamp("2026-01-06 12:00", tz=ET).tz_convert("UTC")

    result = resample_cascade(bars, now=now)

    # Pre-market bars (anchored to the 04:00 ET window open) form 4
    # buckets: [04:00,04:30), [05:00) alone, [08:00,08:30), [09:00) alone
    # — none of them merged with the regular session that starts right after.
    pre_market_bucket_count = len(result["1h"]) - 7  # 7 = regular-session buckets from FULL_SESSION_TIMES
    assert pre_market_bucket_count == 4
    first_regular_1h = result["1h"].iloc[pre_market_bucket_count]
    assert first_regular_1h["timestamp"].tz_convert(ET).strftime("%H:%M") == "09:30"


def test_post_market_bars_form_their_own_clean_4h_bucket():
    # After-hours (16:00-20:00 ET) is exactly 4h = one clean 4h bucket
    # when the window has fully closed, with no short trailing remainder.
    post_market_times = ["16:00", "16:30", "17:00", "17:30", "18:00", "18:30", "19:00", "19:30"]
    bars = pd.concat(
        [_bars("2026-01-05", FULL_SESSION_TIMES), _bars("2026-01-05", post_market_times, base_price=110)],
        ignore_index=True,
    )
    now = pd.Timestamp("2026-01-06 12:00", tz=ET).tz_convert("UTC")

    result = resample_cascade(bars, now=now)

    post_market_4h = result["4h"].iloc[-1]
    assert post_market_4h["timestamp"].tz_convert(ET).strftime("%H:%M") == "16:00"
    assert post_market_4h["volume"] == 8
