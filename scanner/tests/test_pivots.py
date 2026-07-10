import pandas as pd

from pivots import find_pivots

PRICES = [1, 2, 3, 2, 1, 2, 3, 4, 3, 2, 1]


def _df(prices, rsi=None):
    n = len(prices)
    return pd.DataFrame(
        {
            "ts": pd.date_range("2026-01-01", periods=n, freq="h"),
            "close": prices,
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
