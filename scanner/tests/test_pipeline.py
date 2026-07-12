import os

import pytest

import config
from alpaca_client import get_client
from pipeline import compute_signals

HAS_CREDENTIALS = bool(os.environ.get("ALPACA_API_KEY")) and bool(
    os.environ.get("ALPACA_SECRET_KEY")
)

pytestmark = pytest.mark.skipif(
    not HAS_CREDENTIALS,
    reason="ALPACA_API_KEY/ALPACA_SECRET_KEY not set — copy scanner/.env.example "
    "to scanner/.env and fill in your Alpaca paper-trading keys to run this test",
)


def test_compute_signals_runs_end_to_end_for_all_timeframes():
    client = get_client()

    signals = compute_signals(client, "AAPL", lookback_days=90)

    assert set(signals.keys()) == set(config.TIMEFRAMES)
    for timeframe, result in signals.items():
        bars = result["bars"]
        assert not bars.empty, f"no bars returned for {timeframe}"
        assert "rsi" in bars.columns
        assert (bars["rsi"].dropna() >= 0).all() and (bars["rsi"].dropna() <= 100).all()
        # divergence, if any, must reference two pivots of the same kind
        if result["divergence"] is not None:
            pivot_1, pivot_2, direction = result["divergence"]
            assert pivot_1["kind"] == pivot_2["kind"]
            assert direction in ("bullish", "bearish")
