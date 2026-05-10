# AgenticStock

AgenticStock is a full-stack stock intelligence workspace for:

- Live market flow monitoring
- AI-assisted stock analysis (decision-first, risk-aware)
- Portfolio tracking with P/L
- Risk engine output (position sizing, stop/target guidance)
- Decision audit trail for review and accountability

This project is designed for practical business users who need clear "invest / wait / avoid" style outcomes, not long generic reports.

## What You Get

- **Frontend**: Next.js + TypeScript dashboard and stock workspaces
- **Backend**: FastAPI APIs with PostgreSQL + Redis
- **ML service**: feature engineering and directional model inference
- **Pipeline**: scheduled and live data refresh jobs

## Repo Structure

- `frontend/` - web app
- `backend/` - API services and business logic
- `ml/` - model training and inference service
- `infra/` - infrastructure-related assets

## Prerequisites

- Docker Desktop
- Git

Optional for richer live data and AI quality:

- `FINNHUB_API_KEY`
- `ALPHAVANTAGE_API_KEY`
- `TWELVEDATA_API_KEY`
- `OPENAI_API_KEY` (if using OpenAI provider)

## Quick Start (Recommended)

1. Clone repo

```bash
git clone https://github.com/ZoSwi/agenticstock.git
cd agenticstock
```

2. Create environment file

```bash
copy .env.example .env
```

3. Start services

```bash
docker compose up -d --build
```

4. Open apps

- Web: `http://localhost:3000`
- Backend docs: `http://localhost:8000/docs`
- ML docs: `http://localhost:8001/docs`

## Main Product Surfaces

- `/dashboard` - professional live market dashboard
- `/stocks/{ticker}` - compact decision-first stock view
- `/portfolio` - position book, P/L, and audit timeline
- `/chat` - AI chat with structured investment guidance

## Key APIs

### Stocks

- `GET /stocks/{ticker}/analysis`
- `GET /stocks/{ticker}/signals`
- `GET /stocks/{ticker}/ai-outcome`
- `GET /stocks/{ticker}/risk-engine?capital=100000&risk_budget_pct=0.01`

### Live market and news

- `GET /stocks/market/live?limit=20`
- `GET /stocks/market/stream?limit=20&interval_seconds=12` (SSE)
- `GET /news/live?limit=20`
- `GET /news/{ticker}?limit=20`

### Portfolio and audit

- `POST /portfolio/positions`
- `GET /portfolio/positions?user_id=demo`
- `GET /portfolio/summary?user_id=demo`
- `DELETE /portfolio/positions?user_id=demo&ticker=TSLA`
- `POST /audit/events`
- `GET /audit/events?user_id=demo&limit=50`

## LLM Provider Setup

In `.env`, set:

- `LLM_PROVIDER=openai` (or `anthropic`, `ollama`, `none`, `auto`)
- `OPENAI_API_KEY=...`
- `OPENAI_MODEL=...`

If provider is unavailable, the app degrades gracefully to deterministic structured output.

## Security and Privacy Notes

- `.env` is ignored by git.
- Do not commit API keys or personal secrets.
- Rotate any key that was ever exposed in plain text.

## Troubleshooting

### UI loads but data looks stale

- Check backend and ML service health:
  - `http://localhost:8000/health`
  - `http://localhost:8001/health`
- Restart stack:

```bash
docker compose down
docker compose up -d --build
```

### Stock page error or missing output

- Confirm `/stocks/{ticker}/analysis` returns 200 in backend docs.
- Verify `.env` has required provider keys.
- Wait for cache refresh (or restart backend/redis).

### Chat answers too generic

- Ensure `LLM_PROVIDER` and key are correctly set.
- Use ticker-explicit prompts:
  - "Should I invest in MU this week?"

## Development Notes

- Backend compile check:

```bash
python -m compileall backend/app
```

- Frontend production build check:

```bash
cd frontend
npm run build
```

## Disclaimer

AgenticStock provides probabilistic, educational guidance and workflow support. It is not personalized financial advice.
