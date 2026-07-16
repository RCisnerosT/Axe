from datetime import datetime, timedelta, timezone

import pandas as pd

import config
from alpaca_client import get_bars
from divergence import find_latest_divergence
from indicators import wilder_rsi
from pivots import find_pivots
from resample import NYSE, resample_cascade

SESSION_SCOPES = {
    "1h": ("regular", "extended"),
    "4h": ("regular", "extended"),
    "1d": ("regular",),  # daily bars have no pre/post-market concept
}


def _with_rsi(bars: pd.DataFrame) -> pd.DataFrame:
    df = bars.rename(columns={"timestamp": "ts"})
    df["rsi"] = wilder_rsi(df["close"], period=config.RSI_PERIOD)
    return df


def _with_daily_close_ts(bars_1d: pd.DataFrame) -> pd.DataFrame:
    """Daily bars from Alpaca aren't timestamped at market close, but a
    "1d" pivot/divergence should still be reported by its actual close
    (16:00 ET, or earlier on a half day) rather than its open."""
    if bars_1d.empty:
        return bars_1d.assign(ts_close=bars_1d["timestamp"])

    start = bars_1d["timestamp"].min().date() - pd.Timedelta(days=1)
    end = bars_1d["timestamp"].max().date() + pd.Timedelta(days=1)
    schedule = NYSE.schedule(start_date=start, end_date=end)
    close_by_date = dict(zip(schedule.index.date, schedule["market_close"]))

    ts_close = bars_1d["timestamp"].dt.date.map(close_by_date)
    return bars_1d.assign(ts_close=ts_close)


def _signals_for(df: pd.DataFrame) -> dict:
    pivots = find_pivots(df, width=config.FRACTAL_WIDTH)
    if not pivots.empty:
        ts_close = df.loc[pivots["index"], "ts_close"].reset_index(drop=True)
        pivots = pivots.assign(ts_close=ts_close)
    divergence = find_latest_divergence(pivots, df) if not pivots.empty else None
    return {"bars": df, "pivots": pivots, "divergence": divergence}


def compute_signals(client, ticker: str, lookback_days: int = 60) -> dict:
    """Fetch real Alpaca bars for `ticker` and run pivot/divergence
    detection on every (timeframe, session_scope) combination: 1h/4h are
    computed both on regular-session-only bars and on the full
    pre+regular+post extended set, since thin pre/post-market volume can
    produce different (often noisier) pivots than regular hours alone. 1d
    only has a "regular" scope.

    Returns {timeframe: {session_scope: {"bars": DataFrame,
    "pivots": DataFrame, "divergence": (pivot_1, pivot_2, direction,
    strength) | None}}}.
    """
    start = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    bars_30m = get_bars(client, ticker, "30m", start=start)
    bars_1d = get_bars(client, ticker, "1d", start=start)

    resampled_by_scope = {
        "regular": resample_cascade(bars_30m, regular_session_only=True),
        "extended": resample_cascade(bars_30m, regular_session_only=False),
    }

    signals = {}
    for timeframe in ("1h", "4h"):
        signals[timeframe] = {
            scope: _signals_for(_with_rsi(resampled_by_scope[scope][timeframe]))
            for scope in SESSION_SCOPES[timeframe]
        }
    signals["1d"] = {"regular": _signals_for(_with_rsi(_with_daily_close_ts(bars_1d)))}

    return signals
