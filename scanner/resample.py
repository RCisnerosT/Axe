import pandas as pd
import pandas_market_calendars as mcal

NYSE = mcal.get_calendar("NYSE")

BAR_COLUMNS = ["timestamp", "ts_close", "open", "high", "low", "close", "volume"]

# Sub-bars per bucket, anchored to each session window's own open rather
# than the clock hour — e.g. the first regular-session "1h" bucket is
# 9:30-10:30 ET, not 9:00-10:00.
BARS_PER_BUCKET = {"1h": 2, "4h": 4}  # "4h" groups 4 of the *resulting* 1h bars

# Alpaca's SIP feed returns bars for all three sessions by default, not
# just regular hours — pre-market ~4:00-9:30 ET and after-hours
# ~16:00-20:00 ET, per the plan's decision to scan those on 1h/4h too.
PRE_MARKET_SPAN = pd.Timedelta(hours=5, minutes=30)  # 04:00 ET -> market open
POST_MARKET_SPAN = pd.Timedelta(hours=4)  # market close -> ~20:00 ET

_TS_DTYPE = "datetime64[ns, UTC]"


def _session_windows(start_date, end_date) -> pd.DataFrame:
    """One row per (date, session) with window_open/window_close covering
    pre-market, regular, and after-hours."""
    schedule = NYSE.schedule(start_date=start_date, end_date=end_date)
    windows = []
    for _, row in schedule.iterrows():
        market_open, market_close = row["market_open"], row["market_close"]
        windows.append({"window_open": market_open - PRE_MARKET_SPAN, "window_close": market_open})
        windows.append({"window_open": market_open, "window_close": market_close})
        windows.append({"window_open": market_close, "window_close": market_close + POST_MARKET_SPAN})
    return (
        pd.DataFrame(windows)
        .astype({"window_open": _TS_DTYPE, "window_close": _TS_DTYPE})
        .sort_values("window_open")
        .reset_index(drop=True)
    )


def _assign_windows(bars: pd.DataFrame) -> pd.DataFrame:
    """Match each (already time-sorted) bar to the session window it falls
    in, via backward as-of merge on window_open."""
    start = bars["timestamp"].min().date() - pd.Timedelta(days=1)
    end = bars["timestamp"].max().date() + pd.Timedelta(days=1)
    windows = _session_windows(start, end)

    ts = bars[["timestamp"]].astype({"timestamp": _TS_DTYPE})
    matched = pd.merge_asof(ts, windows, left_on="timestamp", right_on="window_open", direction="backward")
    return matched[["window_open", "window_close"]]


def filter_regular_session(bars: pd.DataFrame) -> pd.DataFrame:
    """Drop pre-market and after-hours bars, keeping only the regular
    9:30-16:00 ET session -- thin pre/post-market volume produces noisy
    wicks that don't reflect genuine price discovery."""
    if bars.empty:
        return bars
    bars = bars.sort_values("timestamp").reset_index(drop=True)

    start = bars["timestamp"].min().date() - pd.Timedelta(days=1)
    end = bars["timestamp"].max().date() + pd.Timedelta(days=1)
    schedule = NYSE.schedule(start_date=start, end_date=end).astype(
        {"market_open": _TS_DTYPE, "market_close": _TS_DTYPE}
    )

    ts = bars[["timestamp"]].astype({"timestamp": _TS_DTYPE})
    matched = pd.merge_asof(
        ts, schedule[["market_open", "market_close"]], left_on="timestamp", right_on="market_open", direction="backward"
    )
    in_regular = (bars["timestamp"] >= matched["market_open"]) & (bars["timestamp"] < matched["market_close"])
    return bars[in_regular].reset_index(drop=True)


def _bucket_and_aggregate(bars: pd.DataFrame, bar_span: pd.Timedelta, bars_per_bucket: int, now: pd.Timestamp) -> pd.DataFrame:
    """Group consecutive bars into buckets of `bars_per_bucket`, anchored to
    each bar's session window open, and aggregate each bucket into one
    OHLCV bar.

    `bars` must carry a `ts_close` column (the true close time of each
    input bar). The output's `ts_close` is the *last* sub-bar's own
    ts_close, not `timestamp + bar_span` — that stays correct even for a
    short trailing bucket (e.g. the last half hour of the 6.5h regular
    session), where adding the nominal bar_span would overshoot past
    market close.

    The trailing bucket is dropped if it belongs to a session window that
    hasn't closed yet (still forming) and is short of a full bucket. A
    short trailing bucket on an already-closed window is kept: no more
    bars will ever arrive to fill it.
    """
    bars = bars.sort_values("timestamp").reset_index(drop=True)
    windows = _assign_windows(bars)

    idx_in_window = (bars["timestamp"] - windows["window_open"]) // bar_span
    bucket = windows["window_open"].astype(str) + "-" + (idx_in_window // bars_per_bucket).astype(str)

    window_still_open = windows["window_close"].iloc[-1] > now
    if window_still_open:
        last_bucket = bucket.iloc[-1]
        if (bucket == last_bucket).sum() < bars_per_bucket:
            bucket = bucket.mask(bucket == last_bucket)

    grouped = bars.assign(_bucket=bucket).dropna(subset=["_bucket"]).groupby("_bucket", sort=True)
    return pd.DataFrame(
        {
            "timestamp": grouped["timestamp"].first(),
            "ts_close": grouped["ts_close"].last(),
            "open": grouped["open"].first(),
            "high": grouped["high"].max(),
            "low": grouped["low"].min(),
            "close": grouped["close"].last(),
            "volume": grouped["volume"].sum(),
        }
    ).reset_index(drop=True)


def resample_cascade(bars_30m: pd.DataFrame, now: pd.Timestamp | None = None, regular_session_only: bool = True) -> dict:
    """Aggregate 30m bars into 1h and 4h bars, cascading 30m -> 1h -> 4h.

    Pre-market/after-hours bars are dropped by default (see
    `filter_regular_session`) rather than resampled into their own 1h/4h
    bars.
    """
    now = now if now is not None else pd.Timestamp.now(tz="UTC")
    if regular_session_only:
        bars_30m = filter_regular_session(bars_30m)
    bars_30m = bars_30m.assign(ts_close=bars_30m["timestamp"] + pd.Timedelta(minutes=30))

    bars_1h = _bucket_and_aggregate(bars_30m, pd.Timedelta(minutes=30), BARS_PER_BUCKET["1h"], now)
    bars_4h = _bucket_and_aggregate(bars_1h, pd.Timedelta(hours=1), BARS_PER_BUCKET["4h"], now)

    return {"1h": bars_1h[BAR_COLUMNS], "4h": bars_4h[BAR_COLUMNS]}
