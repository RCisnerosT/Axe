import pandas as pd
from dotenv import load_dotenv

import alpaca_client
import config
import pipeline
import supabase_client
import telegram


def check_health(supabase) -> None:
    last_success = (
        supabase.table("scan_runs")
        .select("finished_at")
        .eq("status", "success")
        .order("finished_at", desc=True)
        .limit(1)
        .execute()
    )
    if not last_success.data:
        return  # first run ever — nothing to compare against yet

    last_ts = pd.Timestamp(last_success.data[0]["finished_at"])
    gap_hours = (pd.Timestamp.now(tz="UTC") - last_ts).total_seconds() / 3600
    if gap_hours > config.SCAN_HEALTHCHECK_MAX_GAP_HOURS:
        telegram.send_health_check_alert(gap_hours)


def scan_ticker(supabase, alpaca, ticker: str) -> None:
    signals = pipeline.compute_signals(alpaca, ticker)

    for timeframe, result in signals.items():
        supabase_client.upsert_price_bars(supabase, ticker, timeframe, result["bars"])
        ts_to_id = supabase_client.sync_pivots(supabase, ticker, timeframe, result["pivots"])

        divergence = result["divergence"]
        if divergence is None:
            continue

        pivot_1, pivot_2, direction, strength = divergence
        divergence_id = supabase_client.sync_divergence(
            supabase,
            ticker,
            timeframe,
            ts_to_id[pivot_1["ts"].isoformat()],
            ts_to_id[pivot_2["ts"].isoformat()],
            direction,
            strength,
            pivot_2["price_value"],
        )
        if divergence_id is not None:
            telegram.send_divergence_alert(
                ticker,
                timeframe,
                direction,
                strength,
                pivot_2["price_value"],
                pivot_1["ts_close"],
                pivot_2["ts_close"],
            )
            supabase_client.mark_alerted(supabase, divergence_id)


def run_scan() -> None:
    supabase = supabase_client.get_client()
    alpaca = alpaca_client.get_client()

    check_health(supabase)
    supabase_client.upsert_symbols(supabase, config.UNIVERSE)

    run = supabase.table("scan_runs").insert({"status": "running"}).execute()
    run_id = run.data[0]["id"]

    try:
        for symbol in config.UNIVERSE:
            scan_ticker(supabase, alpaca, symbol["ticker"])
    except Exception as exc:
        supabase.table("scan_runs").update(
            {"status": "failed", "finished_at": pd.Timestamp.now(tz="UTC").isoformat(), "error": str(exc)}
        ).eq("id", run_id).execute()
        raise
    else:
        supabase.table("scan_runs").update(
            {"status": "success", "finished_at": pd.Timestamp.now(tz="UTC").isoformat()}
        ).eq("id", run_id).execute()


if __name__ == "__main__":
    load_dotenv()
    run_scan()
