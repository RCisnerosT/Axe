import pandas as pd
import pytest

from divergence import check_divergence, find_latest_divergence


def pivot(kind, price, rsi):
    return {"kind": kind, "price_value": price, "rsi_value": rsi}


# Each case: (pivot_1, pivot_2, expected_direction)
CASES = [
    # Bullish: lower low in price, higher low in RSI, both oversold
    ("bullish_textbook", pivot("low", 100, 25), pivot("low", 90, 32), "bullish"),
    # Bearish: higher high in price, lower high in RSI, both overbought
    ("bearish_textbook", pivot("high", 100, 75), pivot("high", 110, 68), "bearish"),
    # Price didn't make a lower low -> no bullish divergence
    ("bullish_price_wrong_direction", pivot("low", 90, 25), pivot("low", 95, 32), None),
    # RSI didn't make a higher low -> no bullish divergence
    ("bullish_rsi_wrong_direction", pivot("low", 100, 32), pivot("low", 90, 25), None),
    # Price/RSI shape is right but RSI never entered oversold zone
    ("bullish_outside_zone", pivot("low", 100, 45), pivot("low", 90, 50), None),
    # Only one of the two pivots is inside the oversold zone
    ("bullish_only_one_pivot_in_zone", pivot("low", 100, 25), pivot("low", 90, 55), None),
    # Price didn't make a higher high -> no bearish divergence
    ("bearish_price_wrong_direction", pivot("high", 110, 75), pivot("high", 100, 68), None),
    # RSI didn't make a lower high -> no bearish divergence
    ("bearish_rsi_wrong_direction", pivot("high", 100, 68), pivot("high", 110, 75), None),
    # Shape is right but RSI never entered overbought zone
    ("bearish_outside_zone", pivot("high", 100, 55), pivot("high", 110, 50), None),
    # Mismatched pivot kinds should never be compared
    ("mismatched_kind", pivot("low", 100, 25), pivot("high", 110, 68), None),
    # Boundary: RSI exactly at the oversold threshold (40) still counts as "in zone"
    ("bullish_zone_boundary_inclusive", pivot("low", 100, 30), pivot("low", 90, 40), "bullish"),
    # Just above the oversold threshold breaks the zone requirement
    ("bullish_just_outside_zone", pivot("low", 100, 30), pivot("low", 90, 41), None),
]


@pytest.mark.parametrize("name,pivot_1,pivot_2,expected", CASES, ids=[c[0] for c in CASES])
def test_divergence_definition(name, pivot_1, pivot_2, expected):
    assert check_divergence(pivot_1, pivot_2) == expected


def test_find_latest_divergence_picks_most_recent_pair():
    pivots = pd.DataFrame(
        [
            {"ts": pd.Timestamp("2026-01-01"), "kind": "low", "price_value": 110, "rsi_value": 20},
            {"ts": pd.Timestamp("2026-01-02"), "kind": "low", "price_value": 100, "rsi_value": 25},
            {"ts": pd.Timestamp("2026-01-03"), "kind": "low", "price_value": 90, "rsi_value": 33},
        ]
    )
    result = find_latest_divergence(pivots)
    assert result is not None
    pivot_1, pivot_2, direction = result
    assert direction == "bullish"
    assert pivot_1["price_value"] == 100
    assert pivot_2["price_value"] == 90


def test_find_latest_divergence_returns_none_when_no_match():
    pivots = pd.DataFrame(
        [
            {"ts": pd.Timestamp("2026-01-01"), "kind": "low", "price_value": 90, "rsi_value": 25},
            {"ts": pd.Timestamp("2026-01-02"), "kind": "low", "price_value": 100, "rsi_value": 32},
        ]
    )
    assert find_latest_divergence(pivots) is None
