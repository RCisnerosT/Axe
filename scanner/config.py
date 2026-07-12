TIMEFRAMES = ["30m", "1h", "4h", "1d"]

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
    {"ticker": "IWM", "name": "iShares Russell 2000", "type": "etf"},
    {"ticker": "DIA", "name": "SPDR Dow Jones", "type": "etf"},
    # Commodities (via liquid, optionable ETFs)
    {"ticker": "GLD", "name": "SPDR Gold Shares", "type": "etf"},
    {"ticker": "SLV", "name": "iShares Silver Trust", "type": "etf"},
    {"ticker": "USO", "name": "United States Oil Fund", "type": "etf"},
    {"ticker": "UNG", "name": "United States Natural Gas Fund", "type": "etf"},
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
    "30m": 40,
    "1h": 40,
    "4h": 20,
    "1d": 15,
}

SCAN_HEALTHCHECK_MAX_GAP_HOURS = 3
