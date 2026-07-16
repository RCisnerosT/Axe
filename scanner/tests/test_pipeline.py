import os

import pytest

from alpaca_client import get_client
from pipeline import SESSION_SCOPES, compute_signals

HAS_CREDENTIALS = bool(os.environ.get("ALPACA_API_KEY")) and bool(
    os.environ.get("ALPACA_SECRET_KEY")
)

pytestmark = pytest.mark.skipif(
    not HAS_CREDENTIALS,
    reason="ALPACA_API_KEY/ALPACA_SECRET_KEY not set — copy scanner/.env.example "
    "to scanner/.env and fill in your Alpaca paper-trading keys to run this test",
)


def test_compute_signals_runs_end_to_end_for_all_timeframes_and_scopes():
    client = get_client()

    signals = compute_signals(client, "AAPL", lookback_days=90)

    assert set(signals.keys()) == set(SESSION_SCOPES.keys())
    for timeframe, by_scope in signals.items():
        assert set(by_scope.keys()) == set(SESSION_SCOPES[timeframe])
        for session_scope, result in by_scope.items():
            bars = result["bars"]
            assert not bars.empty, f"no bars returned for {timeframe}/{session_scope}"
            assert "rsi" in bars.columns
            assert (bars["rsi"].dropna() >= 0).all() and (bars["rsi"].dropna() <= 100).all()
            # ts_close must be strictly after the bar's own open (ts)
            assert (bars["ts_close"] > bars["ts"]).all()
            # divergence, if any, must reference two pivots of the same kind
            if result["divergence"] is not None:
                pivot_1, pivot_2, direction, strength = result["divergence"]
                assert pivot_1["kind"] == pivot_2["kind"]
                assert direction in ("bullish", "bearish")
                assert strength in ("strong", "weak")
                assert pivot_1["ts_close"] > pivot_1["ts"]
                assert pivot_2["ts_close"] > pivot_2["ts"]


def test_4h_extended_has_more_or_equal_bars_than_regular():
    client = get_client()

    signals = compute_signals(client, "AAPL", lookback_days=30)

    regular_bars = len(signals["4h"]["regular"]["bars"])
    extended_bars = len(signals["4h"]["extended"]["bars"])
    assert extended_bars >= regular_bars
