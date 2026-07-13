export type Timeframe = "1h" | "4h" | "1d";
export type SessionScope = "regular" | "extended";
export type PivotKind = "high" | "low";
export type Direction = "bullish" | "bearish";
export type DivergenceStrength = "strong" | "weak";
export type DivergenceStatus = "active" | "invalidated" | "expired";

export interface Symbol {
  ticker: string;
  name: string;
  type: "stock" | "etf";
  active: boolean;
}

export interface PriceBar {
  id: number;
  ticker: string;
  timeframe: Timeframe;
  ts: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  rsi: number | null;
}

export interface Pivot {
  id: number;
  ticker: string;
  timeframe: Timeframe;
  session_scope: SessionScope;
  ts: string;
  kind: PivotKind;
  price_value: number;
  rsi_value: number;
  confirmed_at: string;
}

export interface Divergence {
  id: number;
  ticker: string;
  timeframe: Timeframe;
  session_scope: SessionScope;
  direction: Direction;
  strength: DivergenceStrength;
  pivot_1_id: number;
  pivot_2_id: number;
  detected_at: string;
  price_at_signal: number;
  status: DivergenceStatus;
  alerted_at: string | null;
}

export interface DivergenceWithPivots extends Divergence {
  pivot_1: Pivot;
  pivot_2: Pivot;
}
