import pandas as pd

from pivots import find_pivots

PRICES = [1, 2, 3, 2, 1, 2, 3, 4, 3, 2, 1]


def _df(prices, rsi=None, low=None, high=None):
    n = len(prices)
    return pd.DataFrame(
        {
            "ts": pd.date_range("2026-01-01", periods=n, freq="h"),
            "close": prices,
            "low": low if low is not None else prices,
            "high": high if high is not None else prices,
            "rsi": rsi if rsi is not None else [50.0] * n,
        }
    )


def test_detects_expected_zigzag_pivots():
    pivots = find_pivots(_df(PRICES), width=2)

    assert list(zip(pivots["index"], pivots["kind"], pivots["price_value"])) == [
        (2, "high", 3),
        (4, "low", 1),
        (7, "high", 4),
    ]


def test_confirmed_index_is_offset_by_width():
    pivots = find_pivots(_df(PRICES), width=2)
    row = pivots[pivots["index"] == 2].iloc[0]
    assert row["confirmed_index"] == 4


def test_no_pivots_within_width_of_series_boundaries():
    pivots = find_pivots(_df(PRICES), width=2)
    assert (pivots["index"] >= 2).all()
    assert (pivots["index"] <= len(PRICES) - 1 - 2).all()


def test_flat_series_has_no_pivots():
    flat = [5] * 10
    pivots = find_pivots(_df(flat), width=2)
    assert pivots.empty


def test_pivot_skipped_when_rsi_is_nan():
    rsi = [50.0] * len(PRICES)
    rsi[2] = float("nan")  # the index-2 high pivot bar
    pivots = find_pivots(_df(PRICES, rsi=rsi), width=2)
    assert 2 not in list(pivots["index"])


def test_wider_fractal_width_finds_fewer_pivots():
    narrow = find_pivots(_df(PRICES), width=1)
    wide = find_pivots(_df(PRICES), width=3)
    assert len(wide) <= len(narrow)


def test_pivots_use_wick_extreme_not_close():
    # Bar 2's close makes it look like a lower high than a naive
    # close-only reading would suggest, but its actual high (wick) is the
    # true local max -- the pivot's value must be the wick, not the close.
    closes = [1, 2, 1.5, 1, 0.5]
    highs = [1, 2, 3, 1, 0.5]  # bar 2's wick spikes to 3, close settles at 1.5
    lows = closes

    pivots = find_pivots(_df(closes, low=lows, high=highs), width=1)

    high_pivot = pivots[pivots["kind"] == "high"].iloc[0]
    assert high_pivot["index"] == 2
    assert high_pivot["price_value"] == 3  # the wick high, not the 1.5 close


def test_single_bar_can_be_both_a_high_and_low_pivot():
    # A bar with a wide range compared to its neighbors can be a local
    # extreme on both its high and its low -- these are independent series.
    closes = [1, 1, 1, 1, 1]
    highs = [1, 1, 5, 1, 1]
    lows = [1, 1, -5, 1, 1]

    pivots = find_pivots(_df(closes, low=lows, high=highs), width=2)

    kinds_at_2 = set(pivots[pivots["index"] == 2]["kind"])
    assert kinds_at_2 == {"high", "low"}
