# Influencer Distortion Detection — Sidecar

A stateless FastAPI sidecar that scrapes social-media posts and runs a 3-level
distortion classifier over them. No database; all state lives in the caller.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness probe |
| GET | `/test-connection` | Verify scraper can reach the target platform |
| POST | `/analyze` | Start an async analysis job; returns `job_id` |
| GET | `/analyze/{job_id}` | Poll job status / fetch results |

## Architecture

```
app/api/analyze_routes.py   ← HTTP layer (request validation, SSE progress)
app/services/jobs.py        ← in-process job registry & async orchestration
app/services/classifier.py  ← 3-level distortion classifier (rules → LLM)
app/services/scraper.py     ← multi-platform scraper (RSS, YouTube, Twitter/X, Weibo)
app/main.py                 ← FastAPI app + CORS + /health
```

## Running

```bash
# Local (uvicorn)
cd distortion-backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
uvicorn app.main:app --reload --port 8001

# Docker
docker build -t distortion-backend .
docker run -p 8001:8000 -e OPENAI_API_KEY=sk-... distortion-backend
```

## Environment variables

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `ANTHROPIC_API_KEY` | One LLM key¹ | — | Level-3 verification via native Claude |
| `OPENROUTER_API_KEY` | One LLM key¹ | — | Level-3 via Claude on OpenRouter (OpenAI-compatible) |
| `OPENAI_API_KEY` | One LLM key¹ | — | Level-3 via OpenAI (`gpt-4o-mini`) |
| `DISTORTION_LLM_MODEL` | No | per-provider² | Overrides the Level-3 model slug |
| `TWITTER_AUTH_TOKEN` | For Twitter/X | — | `auth_token` cookie of a logged-in x.com session |
| `TWITTER_CT0` | For Twitter/X | — | `ct0` cookie of the same session |
| `WEIBO_SUB` | For Weibo | — | `SUB` cookie of a logged-in weibo.com session |
| `WEIBO_SUBP` | For Weibo | — | `SUBP` cookie of the same session |
| `CHROMIUM_LOW_MEMORY` | No | `1` | Set to `0` in prod (≥2 GB) to enable full Twitter/X rendering; with `1` Twitter scrapes return 0 posts |
| `ANALYZE_CONCURRENCY` | No | `3` | Max parallel scrape jobs |
| `CORS_ORIGINS` | No | `http://localhost:8080` | Comma-separated allowed origins |

¹ Level-3 verification picks the first configured provider in this order:
`ANTHROPIC_API_KEY` → `OPENROUTER_API_KEY` → `OPENAI_API_KEY`. With **none** set,
classification runs rules-only (`method: rules_v2`) — still fully functional.
² Default model per provider: `claude-haiku-4-5` (Anthropic),
`anthropic/claude-haiku-4-5` (OpenRouter), `gpt-4o-mini` (OpenAI).

## Twitter / Weibo cookies

Twitter/X and Weibo require a logged-in session to scrape. The sidecar reads the
session cookies from **its own environment** — end users never see or paste them:

| Platform | Env vars | Injected as |
|----------|----------|-------------|
| Twitter/X | `TWITTER_AUTH_TOKEN`, `TWITTER_CT0` | `{auth_token, ct0}` |
| Weibo | `WEIBO_SUB`, `WEIBO_SUBP` | `{sub, subp}` |

`scraper.cookies_for_platform(platform)` resolves these on every `/analyze` and
`/test-connection` call. Set them via `.env` (see `.env.example`) locally or the
deploy secret store in production — **never commit real cookie values**. Keyless
platforms (YouTube, Reddit, Bluesky, RSS) need no cookies.

## Memory requirements

Chromium requires at least **2 GB** of container memory to render Twitter/X
correctly (`CHROMIUM_LOW_MEMORY=0`). In constrained environments leave
`CHROMIUM_LOW_MEMORY=1` (single-process mode) but expect Twitter scrapes to
return 0 posts.
