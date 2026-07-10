create type timeframe_t as enum ('30m', '1h', '4h', '1d');
create type session_t as enum ('pre', 'regular', 'post');
create type pivot_kind_t as enum ('high', 'low');
create type direction_t as enum ('bullish', 'bearish');
create type divergence_status_t as enum ('active', 'invalidated', 'expired');
create type exit_reason_t as enum ('opposite_signal', 'horizon', 'still_open');

create table symbols (
  ticker text primary key,
  name text not null,
  type text not null check (type in ('stock', 'etf')),
  active boolean not null default true,
  updated_at timestamptz not null default now()
);

create table price_bars (
  id bigserial primary key,
  ticker text not null references symbols(ticker),
  timeframe timeframe_t not null,
  ts timestamptz not null,
  session session_t not null default 'regular',
  open numeric not null,
  high numeric not null,
  low numeric not null,
  close numeric not null,
  volume bigint not null,
  rsi numeric,
  unique (ticker, timeframe, ts)
);

create index price_bars_ticker_timeframe_ts_idx on price_bars (ticker, timeframe, ts desc);

create table pivots (
  id bigserial primary key,
  ticker text not null references symbols(ticker),
  timeframe timeframe_t not null,
  ts timestamptz not null,
  kind pivot_kind_t not null,
  price_value numeric not null,
  rsi_value numeric not null,
  confirmed_at timestamptz not null
);

create table divergences (
  id bigserial primary key,
  ticker text not null references symbols(ticker),
  timeframe timeframe_t not null,
  direction direction_t not null,
  pivot_1_id bigint not null references pivots(id),
  pivot_2_id bigint not null references pivots(id),
  detected_at timestamptz not null default now(),
  price_at_signal numeric not null,
  status divergence_status_t not null default 'active',
  alerted_at timestamptz
);

create table backtest_results (
  id bigserial primary key,
  ticker text not null references symbols(ticker),
  timeframe timeframe_t not null,
  direction direction_t not null,
  entry_ts timestamptz not null,
  entry_price numeric not null,
  exit_ts timestamptz,
  exit_price numeric,
  exit_reason exit_reason_t not null default 'still_open',
  return_pct numeric
);

-- Alpaca API key/secret son de larga duración (no rotan como el refresh token de
-- Schwab), así que basta con guardarlas como GitHub Actions secrets; no se
-- necesita una tabla de rotación de tokens.

create table scan_runs (
  id bigserial primary key,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  status text not null default 'running' check (status in ('running', 'success', 'failed')),
  error text
);
