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


def find_latest_divergence(pivots: pd.DataFrame, lookback: int = 20):
    """Searches the most recent `lookback` confirmed pivots of each kind
    for the tightest divergence pair — the one with the fewest other
    pivots skipped between pivot_1 and pivot_2. That mirrors how a
    divergence actually reads off a chart: the closest matching swing, not
    necessarily the single latest pivot paired with whatever's right
    before it. Ties (same gap) are broken by recency. Returns (pivot_1,
    pivot_2, direction, strength) for the first kind (low, then high) with
    a match, else None.
    """
    for kind in ("low", "high"):
        same_kind = pivots[pivots["kind"] == kind].sort_values("ts").tail(lookback).reset_index(drop=True)
        n = len(same_kind)
        if n < 2:
            continue

        for gap in range(1, n):
            for j in range(n - 1, gap - 1, -1):
                pivot_1 = same_kind.iloc[j - gap]
                pivot_2 = same_kind.iloc[j]
                result = check_divergence(pivot_1, pivot_2)
                if result:
                    direction, strength = result
                    return pivot_1, pivot_2, direction, strength
    return None
