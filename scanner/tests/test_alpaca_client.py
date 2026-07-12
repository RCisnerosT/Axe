import os
from datetime import datetime, timedelta, timezone

import pytest

from alpaca_client import get_bars, get_client

HAS_CREDENTIALS = bool(os.environ.get("ALPACA_API_KEY")) and bool(
    os.environ.get("ALPACA_SECRET_KEY")
)

pytestmark = pytest.mark.skipif(
    not HAS_CREDENTIALS,
    reason="ALPACA_API_KEY/ALPACA_SECRET_KEY not set — copy scanner/.env.example "
    "to scanner/.env and fill in your Alpaca paper-trading keys to run this test",
)


def test_get_bars_returns_recent_daily_aapl_bars():
    client = get_client()
    start = datetime.now(timezone.utc) - timedelta(days=14)

    df = get_bars(client, "AAPL", "1d", start=start)

    assert not df.empty
    assert list(df.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
    assert (df["close"] > 0).all()
