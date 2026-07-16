import pandas as pd

from config import RSI_OVERBOUGHT, RSI_OVERSOLD


def check_divergence(pivot_1, pivot_2, oversold: float = RSI_OVERSOLD, overbought: float = RSI_OVERBOUGHT):
    """pivot_1 is the earlier pivot, pivot_2 the more recent one. Both must
    be the same kind (two highs or two lows). Returns (direction, strength)
    where direction is 'bullish'/'bearish' and strength is 'strong' if both
    pivots sit in the oversold/overbought zone associated with that
    direction, else 'weak' — or None if there's no divergence shape at all.
    """
    if pivot_1["kind"] != pivot_2["kind"]:
        return None

    if pivot_1["kind"] == "low":
        lower_low = pivot_1["price_value"] > pivot_2["price_value"]
        higher_rsi_low = pivot_1["rsi_value"] < pivot_2["rsi_value"]
        if lower_low and higher_rsi_low:
            both_oversold = pivot_1["rsi_value"] <= oversold and pivot_2["rsi_value"] <= oversold
            return "bullish", ("strong" if both_oversold else "weak")
        return None

    if pivot_1["kind"] == "high":
        higher_high = pivot_1["price_value"] < pivot_2["price_value"]
        lower_rsi_high = pivot_1["rsi_value"] > pivot_2["rsi_value"]
        if higher_high and lower_rsi_high:
            both_overbought = pivot_1["rsi_value"] >= overbought and pivot_2["rsi_value"] >= overbought
            return "bearish", ("strong" if both_overbought else "weak")
        return None

    return None


def _is_cut_by_intervening_pivot(same_kind: pd.DataFrame, i: int, j: int, kind: str) -> bool:
    """True if some pivot strictly between i and j is more extreme than
    pivot_1 (i) — a lower low for bullish, a higher high for bearish. That
    intervening pivot is the one a chart-reader would actually compare
    against, so pairing pivot_2 with the older, less extreme pivot_1
    "cuts through" it and isn't a valid divergence line."""
    between = same_kind["price_value"].iloc[i + 1 : j]
    if between.empty:
        return False
    anchor = same_kind["price_value"].iloc[i]
    return bool((between < anchor).any() if kind == "low" else (between > anchor).any())


def _is_cut_by_intervening_bar(bars: pd.DataFrame, pivot_1, pivot_2, kind: str) -> bool:
    """True if any raw bar strictly between pivot_1 and pivot_2 has a
    low/high more extreme than pivot_1's price value. `_is_cut_by_intervening_pivot`
    only sees bars that already qualified as their own confirmed fractal
    pivot — a wick that dips/spikes past pivot_1 without becoming a
    confirmed pivot itself (e.g. a tied double bottom/top, where neither
    bar is *strictly* less than the other) would slip through that check.
    This compares against the actual price series instead, which is what
    a chart-reader is really looking at when they say a low/high "crosses"
    the divergence line."""
    i_idx, j_idx = int(pivot_1["index"]), int(pivot_2["index"])
    if j_idx - i_idx <= 1:
        return False
    col = "low" if kind == "low" else "high"
    between = bars[col].iloc[i_idx + 1 : j_idx]
    if between.empty:
        return False
    anchor = pivot_1["price_value"]
    return bool((between < anchor).any() if kind == "low" else (between > anchor).any())


def is_invalidated(pivot_2_kind: str, pivot_2_price: float, pivot_2_ts, bars: pd.DataFrame) -> bool:
    """True if any bar strictly after pivot_2 has broken past its price in
    the adverse direction — a new low below pivot_2 for a bullish
    (low-kind) divergence, or a new high above pivot_2 for bearish. Once
    that happens, pivot_2 is no longer the swing extreme the divergence
    was anchored to (and since pivot_2 is by definition already more
    extreme than pivot_1, it's past pivot_1 too), so the signal is stale
    and callers should stop treating it as active."""
    after = bars[bars["ts"] > pivot_2_ts]
    if after.empty:
        return False
    if pivot_2_kind == "low":
        return bool((after["low"] < pivot_2_price).any())
    return bool((after["high"] > pivot_2_price).any())


def find_latest_divergence(pivots: pd.DataFrame, bars: pd.DataFrame, lookback: int = 20):
    """Searches the most recent `lookback` confirmed pivots of each kind
    for the tightest divergence pair — the one with the fewest other
    pivots skipped between pivot_1 and pivot_2. That mirrors how a
    divergence actually reads off a chart: the closest matching swing, not
    necessarily the single latest pivot paired with whatever's right
    before it. Ties (same gap) are broken by recency. A candidate pair is
    skipped if it's cut by a more extreme intervening pivot or raw bar
    (see `_is_cut_by_intervening_pivot` and `_is_cut_by_intervening_bar`),
    even if that intervening point doesn't itself form a valid divergence
    with pivot_2. Returns (pivot_1, pivot_2, direction, strength) for the
    first kind (low, then high) with a match, else None.
    """
    bars = bars.reset_index(drop=True)
    for kind in ("low", "high"):
        same_kind = pivots[pivots["kind"] == kind].sort_values("ts").tail(lookback).reset_index(drop=True)
        n = len(same_kind)
        if n < 2:
            continue

        for gap in range(1, n):
            for j in range(n - 1, gap - 1, -1):
                i = j - gap
                if _is_cut_by_intervening_pivot(same_kind, i, j, kind):
                    continue
                pivot_1 = same_kind.iloc[i]
                pivot_2 = same_kind.iloc[j]
                if _is_cut_by_intervening_bar(bars, pivot_1, pivot_2, kind):
                    continue
                result = check_divergence(pivot_1, pivot_2)
                if result:
                    direction, strength = result
                    return pivot_1, pivot_2, direction, strength
    return None
