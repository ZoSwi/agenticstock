# AI Stock Intelligence Agent

Production-ready, Dockerized monorepo that provides:

- **AI agent**: natural-language stock queries with structured, risk-aware guidance
- **Backend APIs**: FastAPI + PostgreSQL + Redis
- **Data pipeline**: scheduled early-morning refresh + live feed pulls + feature store build
- **ML prediction system**: baseline + XGBoost ensemble outputs (direction, risk, confidence) — **no exact price predictions**
- **Web portal**: Next.js (TypeScript) + Tailwind, mobile-first premium UI with dark/light mode

## Architecture

- `frontend/`: Next.js web portal
- `backend/`: FastAPI API + agent + persistence
- `ml/`: feature engineering, training, and inference service
- `infra/`: docker assets (db init, local configs)

## Quickstart (local)

1) Ensure Docker Desktop is running.

2) Create an env file:

```bash
copy .env.example .env
```

3) Start the stack:

```bash
docker compose up --build
```

Optional: train and persist a better ML model (stored in the `ml_artifacts` volume):

```bash
docker compose run --rm ml python -m app.train
```

Optional: run a one-off daily data job (OHLCV ingestion + provider stubs):

```bash
docker compose --profile manual run --rm pipeline_once
```

4) Open:

- **Web**: `http://localhost:3000`
- **Backend API**: `http://localhost:8000/docs`
- **ML service**: `http://localhost:8001/docs`

Key live endpoints:

- `GET /stocks/market/live?limit=12`
- `GET /stocks/market/stream?limit=10&interval_seconds=12` (SSE)
- `GET /news/live?limit=20` (global live headlines from free RSS sources)
- `GET /news/{ticker}?limit=20` (ticker-specific live headlines)
- `POST /system/symbols/sync` (bootstrap/update broad US symbol catalog)
- `GET /stocks/{ticker}/analysis`
- `GET /stocks/{ticker}/signals` (nowcast + 1d/5d/20d forecast summary)

## Notes

- This system produces **probabilistic directional outlooks** (bullish/neutral/bearish) and **risk-aware guidance**. It does **not** output or imply exact future price targets.
- Data ingestion uses a pluggable adapter design. By default, it can run without paid API keys using public endpoints (and can be upgraded to premium providers via environment variables).
- For stronger free-tier live flow, configure at least one of:
  - `ALPHAVANTAGE_API_KEY` (free tier, strict daily cap)
  - `FINNHUB_API_KEY` (free tier, good intraday quote coverage)
  - `TWELVEDATA_API_KEY` (free tier daily candles fallback for stock detail charts)
  - Optional tuning: `MARKET_UNIVERSE`, `MARKET_ALPHA_QUOTE_LIMIT`, `MARKET_FINNHUB_QUOTE_LIMIT`, `MARKET_YAHOO_FALLBACK_LIMIT`, `MARKET_STOOQ_QUOTE_LIMIT`, `MARKET_LIVE_MAX_AGE_SECONDS`, `NEWS_LIVE_MAX_AGE_SECONDS`, `LIVE_WARM_INTERVAL_SECONDS`, `AUTO_SYNC_SYMBOLS_ON_STARTUP`, `CORS_ALLOW_ORIGINS`
  - Keep `ALLOW_YAHOO_FALLBACK=true` in `.env` for best resilience when Alpha Vantage is throttled.
- If `/stocks/{ticker}/analysis` cannot use model inference, backend now serves a live-flow heuristic signal (`live_heuristic` / `live_breadth_proxy`) so UI stays active instead of showing empty/default cards.
- The `pipeline` service now runs continuously and supports:
  - `PIPELINE_DAILY_REFRESH_TIME` (default `05:15`) for the full early-morning refresh
  - `LIVE_FEED_REFRESH_MINUTES` (default `15`) for rolling live feed pulls
  - `PIPELINE_TIMEZONE` (default `America/New_York`)
  - `NEWS_RSS_SOURCES` (default `google_news_rss,yahoo_finance_rss`)
  - Automatic ticker coverage from both `TICKERS` and all user watchlists

## LLM explanation layer (optional)

Copy `.env.example` to `.env` and set:

- `LLM_PROVIDER=none` — no external AI; answers use the built-in template from structured analysis (default).
- `LLM_PROVIDER=openai` — set `OPENAI_API_KEY` and `OPENAI_MODEL` (use any model ID your account supports, e.g. `gpt-4o-mini`).
- `LLM_PROVIDER=anthropic` — set `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL`.
- `LLM_PROVIDER=ollama` — local models; set `OLLAMA_BASE_URL` and `OLLAMA_MODEL` (OpenAI-compatible `/v1/chat/completions` on your Ollama host).

The API still returns the same **structured JSON**; the LLM only rewrites the **Markdown** narrative when enabled.

## Dependency updates and “latest release” safety

- **Dependabot** (`.github/dependabot.yml`) opens weekly PRs when newer dependency versions exist. Merge only after CI is green.
- **Smoke workflow** (`.github/workflows/smoke.yml`) runs on push/PR and weekly: installs Python + Node deps, compiles backend/ML, and builds the frontend so broken upgrades are caught before you adopt them.

Fully automatic upgrades in production (auto-deploy on green) require your own release pipeline (staging, tests, approvals). This repo provides verification; you choose when to merge and deploy.
