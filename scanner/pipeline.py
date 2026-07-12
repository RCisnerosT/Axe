from datetime import datetime, timedelta, timezone

import pandas as pd

import config
from alpaca_client import get_bars
from divergence import find_latest_divergence
from indicators import wilder_rsi
from pivots import find_pivots
from resample import resample_cascade


def _with_rsi(bars: pd.DataFrame) -> pd.DataFrame:
    df = bars.rename(columns={"timestamp": "ts"})
    df["rsi"] = wilder_rsi(df["close"], period=config.RSI_PERIOD)
    return df


def compute_signals(client, ticker: str, lookback_days: int = 60) -> dict:
    """Fetch real Alpaca bars for `ticker`, resample to all of
    config.TIMEFRAMES, and run pivot/divergence detection on each.

    Returns {timeframe: {"bars": DataFrame, "pivots": DataFrame,
    "divergence": (pivot_1, pivot_2, direction, strength) | None}}.
    """
    start = datetime.now(timezone.utc) - timedelta(days=lookback_days)

    bars_30m = get_bars(client, ticker, "30m", start=start)
    bars_1d = get_bars(client, ticker, "1d", start=start)
    resampled = resample_cascade(bars_30m)
    raw_bars = {"30m": bars_30m, "1h": resampled["1h"], "4h": resampled["4h"], "1d": bars_1d}

    signals = {}
    for timeframe in config.TIMEFRAMES:
        df = _with_rsi(raw_bars[timeframe])
        pivots = find_pivots(df, width=config.FRACTAL_WIDTH)
        divergence = find_latest_divergence(pivots) if not pivots.empty else None
        signals[timeframe] = {"bars": df, "pivots": pivots, "divergence": divergence}
    return signals
