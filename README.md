# RSI Divergence Scanner

Personal swing-trading tool: scans a curated universe of stocks/ETFs/commodity ETFs for RSI/price divergences on 30m/1h/4h/1d timeframes, alerts via Telegram, and backtests the strategy. Two parts in one repo: a Python scanner (runs via GitHub Actions) and a Next.js dashboard (Vercel).

See [docs/blueprint.md](docs/blueprint.md) for the original design blueprint, and [docs/plan.md](docs/plan.md) for the build plan and the decisions made while adapting it (data provider, universe, timeframes, cost).

## Commands

Scanner (`cd scanner`):
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
pytest
```

Dashboard (`cd dashboard`, once scaffolded):
```bash
pnpm install
pnpm dev
```

## Status

- [x] Core logic: `indicators.py` (Wilder RSI), `pivots.py` (wick-based fractals), `divergence.py` (nearest-pair search with intervening-pivot rejection) — all with tests.
- [x] Alpaca account + `alpaca_client.py` + real data ingestion.
- [x] `scan.py` entry point + Telegram alerts (dated, session-scope-labeled) + health-check.
- [x] GitHub Actions scheduling (`workflow_dispatch` + native `schedule` on odd minutes) — secrets uploaded, verified working.
- [ ] cron-job.org + Vercel trigger endpoint for more precise scheduling (needs the dashboard deployed first).
- [ ] `backtest.py`.
- [x] Dashboard (Next.js + Supabase + lightweight-charts) — divergence table, symbol chart (1h/4h/1d, wick pivots + divergence markers), backtest page (mock data until `backtest.py` exists). Not yet deployed to Vercel.

Universe: `AAPL, MSFT, GOOGL, AMZN, META, NVDA, TSLA, SPY, QQQ, GLD, SOXL, SOXS`. Timeframes: `1h, 4h, 1d` (30m only used internally to build 1h/4h). Every 1h/4h signal is computed both on regular-session-only bars and on the full pre/post-market extended set, tagged accordingly.
