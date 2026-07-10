import pandas as pd

from config import RSI_OVERBOUGHT, RSI_OVERSOLD


def check_divergence(pivot_1, pivot_2, oversold: float = RSI_OVERSOLD, overbought: float = RSI_OVERBOUGHT):
    """pivot_1 is the earlier pivot, pivot_2 the more recent one. Both must
    be the same kind (two highs or two lows). Returns 'bullish', 'bearish',
    or None per the divergence definition."""
    if pivot_1["kind"] != pivot_2["kind"]:
        return None

    if pivot_1["kind"] == "low":
        lower_low = pivot_1["price_value"] > pivot_2["price_value"]
        higher_rsi_low = pivot_1["rsi_value"] < pivot_2["rsi_value"]
        both_oversold = pivot_1["rsi_value"] <= oversold and pivot_2["rsi_value"] <= oversold
        if lower_low and higher_rsi_low and both_oversold:
            return "bullish"
        return None

    if pivot_1["kind"] == "high":
        higher_high = pivot_1["price_value"] < pivot_2["price_value"]
        lower_rsi_high = pivot_1["rsi_value"] > pivot_2["rsi_value"]
        both_overbought = pivot_1["rsi_value"] >= overbought and pivot_2["rsi_value"] >= overbought
        if higher_high and lower_rsi_high and both_overbought:
            return "bearish"
        return None

    return None


def find_latest_divergence(pivots: pd.DataFrame):
    """Compares the two most recent confirmed pivots of the same kind
    (chronologically ordered) and returns (pivot_1, pivot_2, direction) if a
    divergence is found, else None."""
    for kind in ("low", "high"):
        same_kind = pivots[pivots["kind"] == kind].sort_values("ts")
        if len(same_kind) < 2:
            continue
        pivot_1 = same_kind.iloc[-2]
        pivot_2 = same_kind.iloc[-1]
        direction = check_divergence(pivot_1, pivot_2)
        if direction:
            return pivot_1, pivot_2, direction
    return None
