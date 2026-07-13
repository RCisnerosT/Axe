from __future__ import annotations

import os
from datetime import datetime

import pandas as pd
from alpaca.data.enums import Adjustment, DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

# Granularities fetched natively from Alpaca. 1h/4h are deliberately not
# listed here — Alpaca's native hourly bars align to the clock hour, not
# to the 9:30 ET market open, so those are built later by resampling the
# 30m bars in cascade (see ingestion, not yet implemented).
NATIVE_TIMEFRAMES = {
    "30m": TimeFrame(30, TimeFrameUnit.Minute),
    "1d": TimeFrame(1, TimeFrameUnit.Day),
}

BAR_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


def get_client() -> StockHistoricalDataClient:
    api_key = os.environ.get("ALPACA_API_KEY")
    secret_key = os.environ.get("ALPACA_SECRET_KEY")
    if not api_key or not secret_key:
        raise RuntimeError(
            "ALPACA_API_KEY / ALPACA_SECRET_KEY are not set. "
            "Copy scanner/.env.example to scanner/.env and fill in your "
            "Alpaca paper-trading API keys."
        )
    return StockHistoricalDataClient(api_key, secret_key)


def get_bars(
    client: StockHistoricalDataClient,
    ticker: str,
    timeframe: str,
    start: datetime,
    end: datetime | None = None,
) -> pd.DataFrame:
    """Fetch raw historical bars for a single ticker/timeframe.

    Uses the SIP feed, which is free for Alpaca as long as the queried
    range ends more than 15 minutes in the past (never live data).
    """
    if timeframe not in NATIVE_TIMEFRAMES:
        raise ValueError(
            f"{timeframe!r} is not fetched natively from Alpaca "
            f"(only {sorted(NATIVE_TIMEFRAMES)} are) — 1h/4h are derived "
            "by resampling 30m bars during ingestion."
        )

    request = StockBarsRequest(
        symbol_or_symbols=ticker,
        timeframe=NATIVE_TIMEFRAMES[timeframe],
        start=start,
        end=end,
        feed=DataFeed.SIP,
        # Split-adjusted, not dividend-adjusted -- unadjusted prices break
        # across a reverse split (SOXL/SOXS do these often) with a fake
        # multi-thousand-percent jump; dividend adjustment isn't relevant
        # to price-action/RSI pivots the way it is for total-return calcs.
        adjustment=Adjustment.SPLIT,
    )
    bars = client.get_stock_bars(request)
    df = bars.df
    if df.empty:
        return pd.DataFrame(columns=BAR_COLUMNS)

    df = df.loc[ticker].reset_index()
    return df[BAR_COLUMNS]
