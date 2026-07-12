import os

import pandas as pd
from supabase import Client, create_client


def get_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY are not set. "
            "Copy scanner/.env.example to scanner/.env and fill in your "
            "Supabase project URL and secret/service_role key."
        )
    # create_client appends the REST path itself — strip it in case the
    # project's base URL was copied from the "Data API" endpoint instead
    # of the plain Project URL (e.g. "https://xxx.supabase.co/rest/v1/").
    url = url.rstrip("/")
    if url.endswith("/rest/v1"):
        url = url[: -len("/rest/v1")]
    return create_client(url, key)


def upsert_symbols(client: Client, universe: list) -> None:
    rows = [{"ticker": s["ticker"], "name": s["name"], "type": s["type"]} for s in universe]
    client.table("symbols").upsert(rows, on_conflict="ticker").execute()


def upsert_price_bars(client: Client, ticker: str, timeframe: str, bars: pd.DataFrame) -> None:
    """bars: DataFrame with columns ts, open, high, low, close, volume, and
    optionally rsi. Relies on price_bars' (ticker, timeframe, ts) unique
    constraint to stay idempotent across repeated scan runs."""
    if bars.empty:
        return
    rows = [
        {
            "ticker": ticker,
            "timeframe": timeframe,
            "ts": row["ts"].isoformat(),
            "open": float(row["open"]),
            "high": float(row["high"]),
            "low": float(row["low"]),
            "close": float(row["close"]),
            "volume": int(row["volume"]),
            "rsi": None if "rsi" not in row or pd.isna(row["rsi"]) else float(row["rsi"]),
        }
        for _, row in bars.iterrows()
    ]
    client.table("price_bars").upsert(rows, on_conflict="ticker,timeframe,ts").execute()


def sync_pivots(client: Client, ticker: str, timeframe: str, pivots: pd.DataFrame) -> dict:
    """Insert any pivots not already stored (there's no DB-level unique
    constraint on pivots, so dedup happens here by `ts`, which is stable
    across scan runs since a given bar's timestamp never changes).

    Returns {ts: db_id} for every pivot in `pivots`, old and newly
    inserted, so callers can resolve the ids a divergence needs to
    reference.
    """
    if pivots.empty:
        return {}

    existing = (
        client.table("pivots")
        .select("id, ts")
        .eq("ticker", ticker)
        .eq("timeframe", timeframe)
        .in_("ts", [ts.isoformat() for ts in pivots["ts"]])
        .execute()
    )
    ts_to_id = {row["ts"]: row["id"] for row in existing.data}

    new_rows = [
        {
            "ticker": ticker,
            "timeframe": timeframe,
            "ts": row["ts"].isoformat(),
            "kind": row["kind"],
            "price_value": float(row["price_value"]),
            "rsi_value": float(row["rsi_value"]),
            "confirmed_at": row["ts"].isoformat(),
        }
        for _, row in pivots.iterrows()
        if row["ts"].isoformat() not in ts_to_id
    ]
    if new_rows:
        inserted = client.table("pivots").insert(new_rows).execute()
        ts_to_id.update({row["ts"]: row["id"] for row in inserted.data})

    return {row["ts"].isoformat(): ts_to_id[row["ts"].isoformat()] for _, row in pivots.iterrows()}


def sync_divergence(
    client: Client,
    ticker: str,
    timeframe: str,
    pivot_1_id: int,
    pivot_2_id: int,
    direction: str,
    price_at_signal: float,
) -> bool:
    """Insert the divergence if this exact pivot pair hasn't been recorded
    yet. Returns True if a new row was inserted (i.e. this is a fresh
    signal, not one already seen on a prior scan run)."""
    existing = (
        client.table("divergences")
        .select("id")
        .eq("pivot_1_id", pivot_1_id)
        .eq("pivot_2_id", pivot_2_id)
        .execute()
    )
    if existing.data:
        return False

    client.table("divergences").insert(
        {
            "ticker": ticker,
            "timeframe": timeframe,
            "direction": direction,
            "pivot_1_id": pivot_1_id,
            "pivot_2_id": pivot_2_id,
            "price_at_signal": float(price_at_signal),
        }
    ).execute()
    return True
