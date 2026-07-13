export interface MockTrade {
  ticker: string;
  timeframe: string;
  direction: "bullish" | "bearish";
  entryDate: string;
  exitDate: string | null;
  returnPct: number | null;
  exitReason: "opposite_signal" | "horizon" | "still_open";
}

// Placeholder data — scanner/backtest.py hasn't been built yet. This page
// exists so the layout/UI can be built and reviewed now; swap for a real
// Supabase query against backtest_results once that exists.
export const MOCK_TRADES: MockTrade[] = [
  { ticker: "AAPL", timeframe: "4h", direction: "bullish", entryDate: "2026-06-10", exitDate: "2026-06-14", returnPct: 3.2, exitReason: "opposite_signal" },
  { ticker: "TSLA", timeframe: "1d", direction: "bullish", entryDate: "2026-06-10", exitDate: "2026-06-26", returnPct: 8.7, exitReason: "opposite_signal" },
  { ticker: "QQQ", timeframe: "4h", direction: "bullish", entryDate: "2026-06-26", exitDate: null, returnPct: null, exitReason: "still_open" },
  { ticker: "MSFT", timeframe: "1h", direction: "bearish", entryDate: "2026-06-18", exitDate: "2026-06-19", returnPct: -1.4, exitReason: "horizon" },
  { ticker: "GLD", timeframe: "1d", direction: "bullish", entryDate: "2026-06-10", exitDate: "2026-06-24", returnPct: 4.1, exitReason: "opposite_signal" },
  { ticker: "SOXS", timeframe: "1d", direction: "bullish", entryDate: "2026-06-22", exitDate: "2026-06-30", returnPct: -2.8, exitReason: "opposite_signal" },
];

export function mockSummary(trades: MockTrade[]) {
  const closed = trades.filter((t) => t.returnPct !== null);
  const wins = closed.filter((t) => (t.returnPct as number) > 0);
  const winRate = closed.length ? (wins.length / closed.length) * 100 : 0;
  const avgReturn = closed.length ? closed.reduce((sum, t) => sum + (t.returnPct as number), 0) / closed.length : 0;
  return { totalTrades: trades.length, closedTrades: closed.length, winRate, avgReturn };
}
