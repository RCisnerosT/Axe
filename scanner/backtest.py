import pandas as pd

import config
import supabase_client
from alpaca_client import get_client
from divergence import _is_cut_by_intervening_bar, _is_cut_by_intervening_pivot, check_divergence
from pipeline import compute_signals

BAR_LOOKBACK_DAYS = 180


def _divergence_ending_at(bars: pd.DataFrame, same_kind: pd.DataFrame, j: int, kind: str, lookback: int):
    """Search backward from pivot `j` for the nearest (fewest pivots
    skipped) valid, uncut divergence pair with pivot_2 = same_kind[j].
    Unlike find_latest_divergence (which searches a whole window for the
    single best pair, live-scan style), this is anchored to one specific
    pivot -- what a bar-by-bar historical replay needs, since it must
    check every pivot as it's confirmed, not just report the best pair in
    hindsight."""
    for gap in range(1, min(j, lookback) + 1):
        i = j - gap
        if _is_cut_by_intervening_pivot(same_kind, i, j, kind):
            continue
        pivot_1, pivot_2 = same_kind.iloc[i], same_kind.iloc[j]
        if _is_cut_by_intervening_bar(bars, pivot_1, pivot_2, kind):
            continue
        result = check_divergence(pivot_1, pivot_2)
        if result:
            direction, strength = result
            return pivot_1, pivot_2, direction, strength
    return None


def replay_divergences(bars: pd.DataFrame, pivots: pd.DataFrame, lookback: int = 20) -> list:
    """Replay divergence detection bar-by-bar over `pivots`' full history:
    for every pivot, at the moment it's confirmed, check whether it forms
    a fresh divergence within its own kind. Returns a chronological
    (by confirmed_index) list of (pivot_1, pivot_2, direction, strength).
    """
    bars = bars.reset_index(drop=True)
    signals = []
    for kind in ("low", "high"):
        same_kind = pivots[pivots["kind"] == kind].sort_values("ts").reset_index(drop=True)
        for j in range(1, len(same_kind)):
            result = _divergence_ending_at(bars, same_kind, j, kind, lookback)
            if result:
                signals.append(result)
    signals.sort(key=lambda s: s[1]["confirmed_index"])
    return signals


def simulate_trades(bars: pd.DataFrame, pivots: pd.DataFrame, timeframe: str, lookback: int = 20) -> list:
    """Turn replayed historical divergences into simulated trades: enter
    at the close of the bar where the signal is actually confirmed
    (pivot_2's confirmed_index, not pivot_2's own bar -- a trader can't
    act on a pivot before it's confirmed), exit on the next opposite-
    direction signal, or force an exit after BACKTEST_HORIZON_BARS if none
    comes. No slippage/commissions modeled.
    """
    if pivots.empty or bars.empty:
        return []

    signals = replay_divergences(bars, pivots, lookback=lookback)
    horizon = config.BACKTEST_HORIZON_BARS[timeframe]
    trades = []

    for idx, (_, pivot_2, direction, strength) in enumerate(signals):
        entry_index = pivot_2["confirmed_index"]
        if entry_index >= len(bars):
            continue  # pivot confirmed past the edge of the fetched bar window

        entry_ts = bars.loc[entry_index, "ts_close"]
        entry_price = float(bars.loc[entry_index, "close"])

        next_opposite_index = None
        for _, other_pivot_2, other_direction, _ in signals[idx + 1 :]:
            other_index = other_pivot_2["confirmed_index"]
            if other_direction != direction and other_index > entry_index:
                next_opposite_index = other_index
                break

        horizon_index = entry_index + horizon
        if next_opposite_index is not None and next_opposite_index <= horizon_index:
            exit_index, exit_reason = next_opposite_index, "opposite_signal"
        elif horizon_index < len(bars):
            exit_index, exit_reason = horizon_index, "horizon"
        elif next_opposite_index is not None and next_opposite_index < len(bars):
            exit_index, exit_reason = next_opposite_index, "opposite_signal"
        else:
            exit_index, exit_reason = None, "still_open"

        if exit_index is not None:
            exit_ts = bars.loc[exit_index, "ts_close"]
            exit_price = float(bars.loc[exit_index, "close"])
            return_pct = (
                (exit_price - entry_price) / entry_price * 100
                if direction == "bullish"
                else (entry_price - exit_price) / entry_price * 100
            )
        else:
            exit_ts, exit_price, return_pct = None, None, None

        trades.append(
            {
                "timeframe": timeframe,
                "direction": direction,
                "strength": strength,
                "entry_ts": entry_ts,
                "entry_price": entry_price,
                "exit_ts": exit_ts,
                "exit_price": exit_price,
                "exit_reason": exit_reason,
                "return_pct": return_pct,
            }
        )

    return trades


def run_backtest(lookback_days: int = BAR_LOOKBACK_DAYS) -> list:
    alpaca = get_client()
    supabase = supabase_client.get_client()

    all_trades = []
    for symbol in config.UNIVERSE:
        ticker = symbol["ticker"]
        signals = compute_signals(alpaca, ticker, lookback_days=lookback_days)
        for timeframe, by_scope in signals.items():
            for session_scope, result in by_scope.items():
                for trade in simulate_trades(result["bars"], result["pivots"], timeframe):
                    trade["ticker"] = ticker
                    trade["session_scope"] = session_scope
                    all_trades.append(trade)

    supabase_client.replace_backtest_results(supabase, all_trades)
    return all_trades


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    trades = run_backtest()
    print(f"{len(trades)} trades simulated and persisted")
