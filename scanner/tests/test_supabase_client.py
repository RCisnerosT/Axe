import os

import pytest

import config
import supabase_client
from alpaca_client import get_client as get_alpaca_client
from pipeline import compute_signals

HAS_CREDENTIALS = all(
    os.environ.get(k)
    for k in ("ALPACA_API_KEY", "ALPACA_SECRET_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY")
)

pytestmark = pytest.mark.skipif(
    not HAS_CREDENTIALS,
    reason="Alpaca and/or Supabase credentials not set in scanner/.env — see .env.example",
)


def test_round_trip_symbols_bars_pivots_and_divergence():
    supabase = supabase_client.get_client()
    alpaca = get_alpaca_client()

    supabase_client.upsert_symbols(supabase, config.UNIVERSE)
    stored_symbol = supabase.table("symbols").select("*").eq("ticker", "AAPL").execute()
    assert len(stored_symbol.data) == 1
    assert stored_symbol.data[0]["name"] == "Apple"

    signals = compute_signals(alpaca, "AAPL", lookback_days=90)
    timeframe = "1d"
    bars = signals[timeframe]["bars"]
    pivots = signals[timeframe]["pivots"]

    supabase_client.upsert_price_bars(supabase, "AAPL", timeframe, bars)
    stored_bars = (
        supabase.table("price_bars")
        .select("id", count="exact")
        .eq("ticker", "AAPL")
        .eq("timeframe", timeframe)
        .execute()
    )
    assert stored_bars.count >= len(bars)

    ts_to_id = supabase_client.sync_pivots(supabase, "AAPL", timeframe, pivots)
    assert len(ts_to_id) == len(pivots)
    assert all(isinstance(v, int) for v in ts_to_id.values())

    divergence = signals[timeframe]["divergence"]
    if divergence is not None:
        pivot_1, pivot_2, direction, strength = divergence
        pivot_1_id = ts_to_id[pivot_1["ts"].isoformat()]
        pivot_2_id = ts_to_id[pivot_2["ts"].isoformat()]

        # This exact pivot pair may already be stored from a prior scan run
        # (dedup working as intended) — either way, a second sync must not
        # insert a duplicate, and we must end up with exactly one row.
        divergence_id = supabase_client.sync_divergence(
            supabase, "AAPL", timeframe, pivot_1_id, pivot_2_id, direction, strength, pivot_2["price_value"]
        )
        inserted_again = supabase_client.sync_divergence(
            supabase, "AAPL", timeframe, pivot_1_id, pivot_2_id, direction, strength, pivot_2["price_value"]
        )
        assert inserted_again is None

        if divergence_id is not None:
            supabase_client.mark_alerted(supabase, divergence_id)
            stored_after_alert = supabase.table("divergences").select("alerted_at").eq("id", divergence_id).execute()
            assert stored_after_alert.data[0]["alerted_at"] is not None

        stored_divergence = (
            supabase.table("divergences")
            .select("*")
            .eq("pivot_1_id", pivot_1_id)
            .eq("pivot_2_id", pivot_2_id)
            .execute()
        )
        assert len(stored_divergence.data) == 1
