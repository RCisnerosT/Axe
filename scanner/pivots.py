import pandas as pd


def find_pivots(df: pd.DataFrame, width: int = 2, price_col: str = "close", rsi_col: str = "rsi") -> pd.DataFrame:
    """Fractal swing-pivot detection: bar i is a high (low) pivot if its
    price is strictly the max (min) among itself and `width` bars on each
    side. A pivot is only usable once `width` bars exist after it, which is
    recorded as `confirmed_index` (the confirmation lag the divergence
    definition relies on).

    Returns a DataFrame with columns: index, ts, kind, price_value,
    rsi_value, confirmed_index — one row per confirmed pivot, ordered by ts.
    """
    prices = df[price_col].reset_index(drop=True)
    rsis = df[rsi_col].reset_index(drop=True)
    ts = df["ts"].reset_index(drop=True)

    rows = []
    n = len(df)
    for i in range(width, n - width):
        if pd.isna(rsis.iloc[i]):
            continue
        window_before = prices.iloc[i - width : i]
        window_after = prices.iloc[i + 1 : i + width + 1]
        price_i = prices.iloc[i]

        is_high = (price_i > window_before).all() and (price_i > window_after).all()
        is_low = (price_i < window_before).all() and (price_i < window_after).all()

        if is_high:
            rows.append(
                {
                    "index": i,
                    "ts": ts.iloc[i],
                    "kind": "high",
                    "price_value": price_i,
                    "rsi_value": rsis.iloc[i],
                    "confirmed_index": i + width,
                }
            )
        elif is_low:
            rows.append(
                {
                    "index": i,
                    "ts": ts.iloc[i],
                    "kind": "low",
                    "price_value": price_i,
                    "rsi_value": rsis.iloc[i],
                    "confirmed_index": i + width,
                }
            )

    return pd.DataFrame(rows, columns=["index", "ts", "kind", "price_value", "rsi_value", "confirmed_index"])
