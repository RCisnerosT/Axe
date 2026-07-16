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


def sync_pivots(client: Client, ticker: str, timeframe: str, session_scope: str, pivots: pd.DataFrame) -> dict:
    """Insert any pivots not already stored (there's no DB-level unique
    constraint on pivots, so dedup happens here by (ts, kind) — a single
    bar can be both a high and a low pivot at once, so `ts` alone isn't a
    unique key; and by session_scope, since the same bar's neighbors (and
    therefore whether it's a pivot at all) can differ between the
    regular-only and extended-hours pivot series.

    Returns {(ts, kind): db_id} for every pivot in `pivots`, old and newly
    inserted, so callers can resolve the ids a divergence needs to
    reference.
    """
    if pivots.empty:
        return {}

    existing = (
        client.table("pivots")
        .select("id, ts, kind")
        .eq("ticker", ticker)
        .eq("timeframe", timeframe)
        .eq("session_scope", session_scope)
        .in_("ts", [ts.isoformat() for ts in pivots["ts"]])
        .execute()
    )
    key_to_id = {(row["ts"], row["kind"]): row["id"] for row in existing.data}

    new_rows = [
        {
            "ticker": ticker,
            "timeframe": timeframe,
            "session_scope": session_scope,
            "ts": row["ts"].isoformat(),
            "kind": row["kind"],
            "price_value": float(row["price_value"]),
            "rsi_value": float(row["rsi_value"]),
            "confirmed_at": row["ts"].isoformat(),
        }
        for _, row in pivots.iterrows()
        if (row["ts"].isoformat(), row["kind"]) not in key_to_id
    ]
    if new_rows:
        inserted = client.table("pivots").insert(new_rows).execute()
        key_to_id.update({(row["ts"], row["kind"]): row["id"] for row in inserted.data})

    return {
        (row["ts"].isoformat(), row["kind"]): key_to_id[(row["ts"].isoformat(), row["kind"])]
        for _, row in pivots.iterrows()
    }


def sync_divergence(
    client: Client,
    ticker: str,
    timeframe: str,
    session_scope: str,
    pivot_1_id: int,
    pivot_2_id: int,
    direction: str,
    strength: str,
    price_at_signal: float,
):
    """Insert the divergence if this exact pivot pair hasn't been recorded
    yet. Returns the new row's id (a fresh signal the caller should alert
    on), or None if this pair was already seen on a prior scan run."""
    existing = (
        client.table("divergences")
        .select("id")
        .eq("pivot_1_id", pivot_1_id)
        .eq("pivot_2_id", pivot_2_id)
        .execute()
    )
    if existing.data:
        return None

    inserted = (
        client.table("divergences")
        .insert(
            {
                "ticker": ticker,
                "timeframe": timeframe,
                "session_scope": session_scope,
                "direction": direction,
                "strength": strength,
                "pivot_1_id": pivot_1_id,
                "pivot_2_id": pivot_2_id,
                "price_at_signal": float(price_at_signal),
            }
        )
        .execute()
    )
    return inserted.data[0]["id"]


def fetch_active_divergences(client: Client, ticker: str, timeframe: str, session_scope: str) -> list:
    """Active divergences for this ticker/timeframe/scope, joined with
    pivot_2 -- the point whose price a later bar breaking past would
    invalidate the signal (see divergence.is_invalidated)."""
    result = (
        client.table("divergences")
        .select("id, pivot_2:pivots!divergences_pivot_2_id_fkey(kind, price_value, ts)")
        .eq("ticker", ticker)
        .eq("timeframe", timeframe)
        .eq("session_scope", session_scope)
        .eq("status", "active")
        .execute()
    )
    return result.data


def invalidate_divergences(client: Client, divergence_ids: list) -> None:
    if not divergence_ids:
        return
    client.table("divergences").update({"status": "invalidated"}).in_("id", divergence_ids).execute()


def mark_alerted(client: Client, divergence_id: int) -> None:
    client.table("divergences").update({"alerted_at": pd.Timestamp.now(tz="UTC").isoformat()}).eq(
        "id", divergence_id
    ).execute()


def replace_backtest_results(client: Client, trades: list) -> None:
    """backtest_results is a snapshot of the latest run, not an append-only
    log like divergences -- wipe and reinsert rather than dedup, since
    re-running the (deterministic) backtest over the same history would
    otherwise just accumulate duplicate rows."""
    client.table("backtest_results").delete().gte("id", 0).execute()
    if not trades:
        return

    rows = [
        {
            "ticker": t["ticker"],
            "timeframe": t["timeframe"],
            "session_scope": t["session_scope"],
            "direction": t["direction"],
            "entry_ts": t["entry_ts"].isoformat(),
            "entry_price": t["entry_price"],
            "exit_ts": t["exit_ts"].isoformat() if t["exit_ts"] is not None else None,
            "exit_price": t["exit_price"],
            "exit_reason": t["exit_reason"],
            "return_pct": t["return_pct"],
        }
        for t in trades
    ]
    for i in range(0, len(rows), 500):
        client.table("backtest_results").insert(rows[i : i + 500]).execute()
