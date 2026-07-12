import pandas as pd


def find_pivots(
    df: pd.DataFrame, width: int = 2, low_col: str = "low", high_col: str = "high", rsi_col: str = "rsi"
) -> pd.DataFrame:
    """Fractal swing-pivot detection: bar i is a high (low) pivot if its
    high (low) is strictly the max (min) among itself and `width` bars on
    each side — using each bar's actual wick extreme, not its close, since
    that's the point a chart-reader compares when drawing a divergence
    line. A bar can independently qualify as both a high pivot (via its
    high) and a low pivot (via its low) — they're tracked as separate
    series. A pivot is only usable once `width` bars exist after it, which
    is recorded as `confirmed_index` (the confirmation lag the divergence
    definition relies on).

    Returns a DataFrame with columns: index, ts, kind, price_value,
    rsi_value, confirmed_index — one row per confirmed pivot, ordered by ts.
    """
    lows = df[low_col].reset_index(drop=True)
    highs = df[high_col].reset_index(drop=True)
    rsis = df[rsi_col].reset_index(drop=True)
    ts = df["ts"].reset_index(drop=True)

    rows = []
    n = len(df)
    for i in range(width, n - width):
        if pd.isna(rsis.iloc[i]):
            continue

        low_i, high_i = lows.iloc[i], highs.iloc[i]
        is_high = (high_i > highs.iloc[i - width : i]).all() and (high_i > highs.iloc[i + 1 : i + width + 1]).all()
        is_low = (low_i < lows.iloc[i - width : i]).all() and (low_i < lows.iloc[i + 1 : i + width + 1]).all()

        if is_high:
            rows.append(
                {
                    "index": i,
                    "ts": ts.iloc[i],
                    "kind": "high",
                    "price_value": high_i,
                    "rsi_value": rsis.iloc[i],
                    "confirmed_index": i + width,
                }
            )
        if is_low:
            rows.append(
                {
                    "index": i,
                    "ts": ts.iloc[i],
                    "kind": "low",
                    "price_value": low_i,
                    "rsi_value": rsis.iloc[i],
                    "confirmed_index": i + width,
                }
            )

    return pd.DataFrame(rows, columns=["index", "ts", "kind", "price_value", "rsi_value", "confirmed_index"])
