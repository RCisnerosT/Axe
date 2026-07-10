import pandas as pd
import pytest

from indicators import wilder_rsi


def _brute_force_rsi(values, period=14):
    """Independent reference implementation (plain Python, no pandas
    vectorization) to cross-check wilder_rsi against a differently-written
    calculation of the same Wilder's smoothing definition."""
    gains = [0.0]
    losses = [0.0]
    for i in range(1, len(values)):
        change = values[i] - values[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    out = [None] * len(values)
    if len(values) <= period:
        return out

    avg_gain = sum(gains[1 : period + 1]) / period
    avg_loss = sum(losses[1 : period + 1]) / period
    out[period] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)

    for i in range(period + 1, len(values)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        out[i] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)

    return out


PRICES = [
    44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42, 45.84, 46.08,
    45.89, 46.03, 45.61, 46.28, 46.28, 46.00, 46.03, 46.41, 46.22, 45.64,
]


def test_matches_independent_reference_implementation():
    result = wilder_rsi(pd.Series(PRICES), period=14)
    expected = _brute_force_rsi(PRICES, period=14)

    for i, exp in enumerate(expected):
        if exp is None:
            assert pd.isna(result.iloc[i])
        else:
            assert result.iloc[i] == pytest.approx(exp, abs=1e-9)


def test_first_valid_value_at_period_index():
    result = wilder_rsi(pd.Series(PRICES), period=14)
    assert result.iloc[:14].isna().all()
    assert not pd.isna(result.iloc[14])


def test_monotonically_rising_series_approaches_100():
    rising = pd.Series(range(1, 40))
    result = wilder_rsi(rising, period=14)
    assert result.iloc[-1] == pytest.approx(100.0)


def test_monotonically_falling_series_approaches_0():
    falling = pd.Series(range(40, 1, -1))
    result = wilder_rsi(falling, period=14)
    assert result.iloc[-1] == pytest.approx(0.0)


def test_rsi_bounded_between_0_and_100():
    result = wilder_rsi(pd.Series(PRICES), period=14).dropna()
    assert (result >= 0).all()
    assert (result <= 100).all()


def test_short_series_returns_all_nan():
    result = wilder_rsi(pd.Series(PRICES[:10]), period=14)
    assert result.isna().all()
