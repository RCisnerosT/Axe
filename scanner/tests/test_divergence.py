import pandas as pd
import pytest

from divergence import check_divergence, find_latest_divergence


def pivot(kind, price, rsi):
    return {"kind": kind, "price_value": price, "rsi_value": rsi}


# Each case: (pivot_1, pivot_2, expected) where expected is (direction, strength) or None
CASES = [
    # Bullish: lower low in price, higher low in RSI, both oversold -> strong
    ("bullish_textbook", pivot("low", 100, 25), pivot("low", 90, 32), ("bullish", "strong")),
    # Bearish: higher high in price, lower high in RSI, both overbought -> strong
    ("bearish_textbook", pivot("high", 100, 75), pivot("high", 110, 68), ("bearish", "strong")),
    # Price didn't make a lower low -> no bullish divergence
    ("bullish_price_wrong_direction", pivot("low", 90, 25), pivot("low", 95, 32), None),
    # RSI didn't make a higher low -> no bullish divergence
    ("bullish_rsi_wrong_direction", pivot("low", 100, 32), pivot("low", 90, 25), None),
    # Shape is right but RSI never entered the oversold zone -> still a divergence, just weak
    ("bullish_outside_zone", pivot("low", 100, 45), pivot("low", 90, 50), ("bullish", "weak")),
    # Only one of the two pivots is inside the oversold zone -> weak
    ("bullish_only_one_pivot_in_zone", pivot("low", 100, 25), pivot("low", 90, 55), ("bullish", "weak")),
    # Price didn't make a higher high -> no bearish divergence
    ("bearish_price_wrong_direction", pivot("high", 110, 75), pivot("high", 100, 68), None),
    # RSI didn't make a lower high -> no bearish divergence
    ("bearish_rsi_wrong_direction", pivot("high", 100, 68), pivot("high", 110, 75), None),
    # Shape is right but RSI never entered the overbought zone -> weak
    ("bearish_outside_zone", pivot("high", 100, 55), pivot("high", 110, 50), ("bearish", "weak")),
    # Mismatched pivot kinds should never be compared
    ("mismatched_kind", pivot("low", 100, 25), pivot("high", 110, 68), None),
    # Boundary: RSI exactly at the oversold threshold (40) still counts as "in zone"
    ("bullish_zone_boundary_inclusive", pivot("low", 100, 30), pivot("low", 90, 40), ("bullish", "strong")),
    # Just above the oversold threshold -> shape still holds, but now weak
    ("bullish_just_outside_zone", pivot("low", 100, 30), pivot("low", 90, 41), ("bullish", "weak")),
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
    pivot_1, pivot_2, direction, strength = result
    assert direction == "bullish"
    assert strength == "strong"
    assert pivot_1["price_value"] == 100
    assert pivot_2["price_value"] == 90


def test_find_latest_divergence_returns_weak_when_outside_zone():
    pivots = pd.DataFrame(
        [
            {"ts": pd.Timestamp("2026-01-01"), "kind": "low", "price_value": 100, "rsi_value": 45},
            {"ts": pd.Timestamp("2026-01-02"), "kind": "low", "price_value": 90, "rsi_value": 50},
        ]
    )
    result = find_latest_divergence(pivots)
    assert result is not None
    _, _, direction, strength = result
    assert direction == "bullish"
    assert strength == "weak"


def test_find_latest_divergence_returns_none_when_no_match():
    pivots = pd.DataFrame(
        [
            {"ts": pd.Timestamp("2026-01-01"), "kind": "low", "price_value": 90, "rsi_value": 25},
            {"ts": pd.Timestamp("2026-01-02"), "kind": "low", "price_value": 100, "rsi_value": 32},
        ]
    )
    assert find_latest_divergence(pivots) is None


def _low_pivots(rows):
    return pd.DataFrame(
        [
            {"ts": pd.Timestamp("2026-01-01") + pd.Timedelta(hours=i), "kind": "low", "price_value": p, "rsi_value": r}
            for i, (p, r) in enumerate(rows)
        ]
    )


def test_find_latest_divergence_skips_a_non_matching_intermediate_pivot():
    # Reproduces a real case found comparing against a live QQQ chart: the
    # adjacent pair doesn't diverge, but skipping one pivot back does.
    pivots = _low_pivots(
        [
            (707.21, 24.03),  # P0
            (707.68, 32.41),  # P1 — P0,P1 and P1,P2 are both non-matches
            (698.95, 25.59),  # P2 — but P0,P2 (gap=2) is a valid bullish divergence
        ]
    )
    result = find_latest_divergence(pivots)
    assert result is not None
    pivot_1, pivot_2, direction, strength = result
    assert direction == "bullish"
    assert pivot_1["price_value"] == 707.21
    assert pivot_2["price_value"] == 698.95


def test_find_latest_divergence_prefers_smaller_gap_over_more_recent_pivot():
    pivots = _low_pivots(
        [
            (100, 20),  # P0
            (90, 30),  # P1 — P0,P1 is a valid gap=1 divergence
            (95, 25),  # P2 — P1,P2 no match
            (85, 22),  # P3 — P2,P3 no match; P0,P3 (gap=3) *would* match too
        ]
    )
    result = find_latest_divergence(pivots)
    assert result is not None
    pivot_1, pivot_2, direction, strength = result
    # The tighter (gap=1) pair wins even though it isn't the most recent pivot.
    assert pivot_1["price_value"] == 100
    assert pivot_2["price_value"] == 90


def test_find_latest_divergence_breaks_gap_ties_by_recency():
    pivots = _low_pivots(
        [
            (100, 20),  # P0
            (90, 25),  # P1 — P0,P1 valid gap=1 (older)
            (95, 22),  # P2 — P1,P2 no match
            (80, 15),  # P3 — P2,P3 no match
            (70, 28),  # P4 — P3,P4 valid gap=1 (more recent)
        ]
    )
    result = find_latest_divergence(pivots)
    assert result is not None
    pivot_1, pivot_2, direction, strength = result
    # Two gap=1 matches exist; the more recent one wins the tie.
    assert pivot_1["price_value"] == 80
    assert pivot_2["price_value"] == 70


def test_find_latest_divergence_respects_lookback_bound():
    pivots = _low_pivots(
        [
            (100, 20),  # P0
            (90, 30),  # P1 — P0,P1 is a valid divergence, but falls outside the lookback below
            (95, 25),  # P2
            (98, 27),  # P3
            (99, 29),  # P4
        ]
    )
    # Only the last 3 pivots (P2,P3,P4) are considered — none of them diverge.
    assert find_latest_divergence(pivots, lookback=3) is None
    # With the full history in view, the P0,P1 pair is found.
    assert find_latest_divergence(pivots, lookback=20) is not None
