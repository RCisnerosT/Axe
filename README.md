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

- [x] Core logic: `indicators.py` (Wilder RSI), `pivots.py` (fractals), `divergence.py` — all with tests, no live data required.
- [ ] Alpaca account + `alpaca_client.py` + real data ingestion.
- [ ] `scan.py` entry point + Telegram alerts + health-check.
- [ ] GitHub Actions scheduling (`workflow_dispatch` + cron-job.org + native `schedule` backup).
- [ ] `backtest.py`.
- [ ] Dashboard (Next.js + Supabase + lightweight-charts).
