# 30m bars are still fetched natively and used as the base for resampling
# into 1h/4h (see resample.py) -- they're just not scanned for
# pivots/divergences on their own anymore.
TIMEFRAMES = ["1h", "4h", "1d"]

UNIVERSE = [
    # Magnificent 7
    {"ticker": "AAPL", "name": "Apple", "type": "stock"},
    {"ticker": "MSFT", "name": "Microsoft", "type": "stock"},
    {"ticker": "GOOGL", "name": "Alphabet", "type": "stock"},
    {"ticker": "AMZN", "name": "Amazon", "type": "stock"},
    {"ticker": "META", "name": "Meta Platforms", "type": "stock"},
    {"ticker": "NVDA", "name": "Nvidia", "type": "stock"},
    {"ticker": "TSLA", "name": "Tesla", "type": "stock"},
    # Index ETFs
    {"ticker": "SPY", "name": "SPDR S&P 500", "type": "etf"},
    {"ticker": "QQQ", "name": "Invesco QQQ (Nasdaq 100)", "type": "etf"},
    # Commodities (via liquid, optionable ETFs)
    {"ticker": "GLD", "name": "SPDR Gold Shares", "type": "etf"},
    # Leveraged semiconductor ETFs
    {"ticker": "SOXL", "name": "Direxion Daily Semiconductor Bull 3X", "type": "etf"},
    {"ticker": "SOXS", "name": "Direxion Daily Semiconductor Bear 3X", "type": "etf"},
]

RSI_PERIOD = 14
RSI_OVERSOLD = 40
RSI_OVERBOUGHT = 60

FRACTAL_WIDTH = 2  # N bars on each side required to confirm a swing pivot

# Bar horizon used by backtest.py to force an exit if no opposite signal appears
BACKTEST_HORIZON_BARS = {
    "1h": 40,
    "4h": 20,
    "1d": 15,
}

SCAN_HEALTHCHECK_MAX_GAP_HOURS = 3
