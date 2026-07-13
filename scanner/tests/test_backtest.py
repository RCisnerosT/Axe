import pandas as pd
import pytest

from backtest import replay_divergences, simulate_trades

BASE_TS = pd.Timestamp("2026-01-01", tz="UTC")


def _bars(closes, rsis=None):
    n = len(closes)
    rsis = rsis if rsis is not None else [50.0] * n
    ts = [BASE_TS + pd.Timedelta(hours=i) for i in range(n)]
    return pd.DataFrame(
        {
            "ts": ts,
            "ts_close": [t + pd.Timedelta(hours=1) for t in ts],
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1] * n,
            "rsi": rsis,
        }
    )


def _pivot(index, kind, price, rsi, width=2):
    return {
        "index": index,
        "ts": BASE_TS + pd.Timedelta(hours=index),
        "kind": kind,
        "price_value": price,
        "rsi_value": rsi,
        "confirmed_index": index + width,
    }


def _pivots(rows):
    return pd.DataFrame(rows, columns=["index", "ts", "kind", "price_value", "rsi_value", "confirmed_index"])


def test_replay_divergences_finds_bullish_pair():
    pivots = _pivots(
        [
            _pivot(0, "low", 100, 25),
            _pivot(5, "low", 90, 32),
        ]
    )
    signals = replay_divergences(pivots)
    assert len(signals) == 1
    pivot_1, pivot_2, direction, strength = signals[0]
    assert direction == "bullish"
    assert strength == "strong"
    assert pivot_1["price_value"] == 100
    assert pivot_2["price_value"] == 90


def test_replay_divergences_rejects_cut_pair():
    # Same "cut" scenario as divergence.py's own tests: P1 undercuts P0, so
    # (P0, P2) must not be reported even though its shape matches.
    pivots = _pivots(
        [
            _pivot(0, "low", 100, 20),
            _pivot(3, "low", 80, 18),
            _pivot(6, "low", 90, 25),
        ]
    )
    signals = replay_divergences(pivots)
    assert signals == []


def test_simulate_trades_entry_uses_confirmed_bar_not_pivot_bar():
    # pivot_2 sits at raw index 5 (price 90, its own price_value) but isn't
    # confirmed until index 7 (width=2) -- the trade must enter at bar 7's
    # close, not use bar 5's close or the pivot's own price_value.
    closes = [100, 100, 100, 100, 100, 100, 100, 97, 100, 100]
    bars = _bars(closes)
    pivots = _pivots([_pivot(0, "low", 100, 25), _pivot(5, "low", 90, 32)])

    trades = simulate_trades(bars, pivots, timeframe="1h")

    assert len(trades) == 1
    assert trades[0]["entry_price"] == 97  # close at confirmed_index=7, not the 90 at raw index 5
    assert trades[0]["entry_ts"] == bars.loc[7, "ts_close"]


def test_simulate_trades_exits_on_opposite_signal():
    # Bullish signal confirmed at index 7, bearish signal confirmed at
    # index 17 -- the bullish trade must close out there.
    closes = [100] * 30
    closes[7] = 90  # bullish entry price
    closes[17] = 110  # bearish entry price == bullish exit price
    bars = _bars(closes)
    pivots = _pivots(
        [
            _pivot(0, "low", 100, 25),
            _pivot(5, "low", 90, 32),
            _pivot(10, "high", 100, 75),
            _pivot(15, "high", 110, 68),
        ]
    )

    trades = simulate_trades(bars, pivots, timeframe="1h")
    bullish_trade = next(t for t in trades if t["direction"] == "bullish")

    assert bullish_trade["entry_price"] == 90
    assert bullish_trade["exit_reason"] == "opposite_signal"
    assert bullish_trade["exit_price"] == 110
    assert bullish_trade["return_pct"] == pytest.approx((110 - 90) / 90 * 100)


def test_simulate_trades_exits_on_horizon_when_no_opposite_signal():
    closes = [100] * 60
    closes[7] = 90  # entry price (confirmed_index for the pivot at raw index 5)
    bars = _bars(closes)
    pivots = _pivots([_pivot(0, "low", 100, 25), _pivot(5, "low", 90, 32)])

    trades = simulate_trades(bars, pivots, timeframe="1h")

    assert len(trades) == 1
    assert trades[0]["entry_price"] == 90
    assert trades[0]["exit_reason"] == "horizon"
    # entry confirmed at index 7; "1h" horizon is 40 bars -> forced exit at index 47
    assert trades[0]["exit_ts"] == bars.loc[47, "ts_close"]


def test_simulate_trades_still_open_when_data_runs_out():
    closes = [100] * 10  # too short to ever reach the horizon (7 + 40)
    closes[7] = 90
    bars = _bars(closes)
    pivots = _pivots([_pivot(0, "low", 100, 25), _pivot(5, "low", 90, 32)])

    trades = simulate_trades(bars, pivots, timeframe="1h")

    assert len(trades) == 1
    assert trades[0]["entry_price"] == 90
    assert trades[0]["exit_reason"] == "still_open"
    assert trades[0]["exit_ts"] is None
    assert trades[0]["return_pct"] is None


def test_simulate_trades_bearish_return_is_inverted():
    closes = [100] * 30
    closes[7] = 110  # entry price (confirmed_index for the pivot at raw index 5)
    closes[27] = 90  # forced horizon exit price ("4h" horizon = 20 -> 7 + 20 = 27)
    bars = _bars(closes)
    pivots = _pivots([_pivot(0, "high", 100, 75), _pivot(5, "high", 110, 68)])

    trades = simulate_trades(bars, pivots, timeframe="4h")

    assert len(trades) == 1
    trade = trades[0]
    assert trade["direction"] == "bearish"
    assert trade["entry_price"] == 110
    assert trade["exit_reason"] == "horizon"
    assert trade["exit_price"] == 90
    # Bearish return is (entry - exit) / entry -- profits when price falls.
    assert trade["return_pct"] == pytest.approx((110 - 90) / 110 * 100)
