# Influencer Distortion System

Detect coordinated emotional manipulation in influencer/creator posts across
**YouTube, Twitter/X, Weibo, Bluesky, Reddit** and RSS/newsletters. Each post is
scored through a 3-level pipeline (rules → heuristics → optional LLM
verification) for five distortion dimensions: **significance inflation, anxiety
manufacturing, novelty bias, loaded language, and temporal pressure**.

This repository is a standalone extraction of the tool from a larger app. It has
two independent parts:

| Part | Path | Standalone? |
|------|------|-------------|
| **Sidecar** (FastAPI scraper + classifier) | [`backend/`](backend/) | ✅ Deploy on its own |
| **Frontend page** (Next.js 15 components) | [`frontend/`](frontend/) | ⚠️ Drop-in components for an existing Next.js app |

---

## Architecture

```
Browser ──▶ Next.js page + API proxy routes ──▶ Backend gateway ──▶ Sidecar (this repo's backend/)
           (frontend/, this repo)               (NOT included —      scrape + classify
                                                  see "Gateway" below)
```

The **sidecar** does all the real work: it scrapes posts (Playwright for
Twitter/X, Weibo, Reddit; keyless HTTP for YouTube/Bluesky/RSS) and classifies
them. It is self-contained and can be deployed and called directly.

The **frontend** is the public analyzer page. Its API proxy routes
(`frontend/src/app/api/distortion/*`) call a backend **gateway** at
`/api/v1/distortion/*`. In the original app that gateway is a thin service that
adds a Redis result-cache, per-IP rate limiting, and developer cookie storage,
then forwards to the sidecar. **That gateway is not part of this repo.** For a
standalone deployment you have two options:

1. **Point the proxy routes straight at the sidecar** (simplest). The sidecar
   exposes `/analyze`, `/analyze/{job_id}`, `/test-connection`, and `/health` —
   the same shapes the proxy routes expect. Repoint `backendFetch(...)` (in
   `frontend/src/app/api/distortion/*/route.ts`) at the sidecar's base URL.
   Note the **`cookies` / `cookies/verify` endpoints and the developer cookie
   gate are gateway-only** (they need Redis + a shared dev password); against the
   bare sidecar, configure cookies via the sidecar's env vars instead (below).
2. **Reimplement a tiny gateway** if you want the cache / rate-limit / dev-gate
   behavior.

---

## Repository layout

```
backend/                      # Deployable FastAPI sidecar
├── app/
│   ├── main.py               # FastAPI app + CORS + /health
│   ├── api/analyze_routes.py # /analyze, /analyze/{id}, /test-connection
│   └── services/
│       ├── scraper.py        # Multi-platform scraping (Playwright + HTTP)
│       ├── classifier.py     # 3-level distortion classifier
│       └── jobs.py           # In-memory async job store
├── Dockerfile                # Playwright base image (Chromium preinstalled)
├── requirements.txt
├── .env.example              # Copy to .env and fill in (gitignored)
└── README.md                 # Sidecar-specific notes

frontend/                     # Drop-in Next.js 15 components (NOT a standalone app)
├── src/app/[locale]/(marketing)/tools/distortion/   # the page (client + server)
├── src/app/api/distortion/                          # API proxy routes → gateway/sidecar
├── src/components/distortion/                        # results UI + developer cookie gate
├── src/hooks/use-distortion.ts                       # TanStack Query hooks
├── src/types/distortion.ts
└── messages/distortion.{en,pl}.json                  # i18n keys to merge into your messages
```

---

## Backend (sidecar) — deploy independently

The sidecar is a standard FastAPI service on a Playwright base image.

### Run with Docker

```bash
cd backend
cp .env.example .env          # fill in the values you need (see below)
docker build -t influencer-distortion .
docker run --rm -p 8000:8000 --env-file .env influencer-distortion
```

### Run locally

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/analyze` | Start a job: `{platform, handle, cookies?, max_posts?}` → `{job_id}` |
| `GET`  | `/analyze/{job_id}` | Poll: `{status, progress, result, error}` |
| `POST` | `/test-connection` | Probe a platform's cookies: `{platform, cookies?}` → `{ok, message}` |
| `GET`  | `/health` | Liveness |

`platform` ∈ `youtube | twitter | weibo | bluesky | reddit | rss`.
`handle` is a username/channel-id, `r/<subreddit>` or `u/<user>` for Reddit, etc.

### Configuration (`backend/.env`)

Everything is optional; unset keys degrade gracefully.

- **LLM verification (Level 3)** — first configured provider wins:
  `ANTHROPIC_API_KEY` → native Claude, else `OPENROUTER_API_KEY` → Claude via
  OpenRouter, else `OPENAI_API_KEY` → OpenAI. Without any key, classification is
  rules + heuristics only. `DISTORTION_LLM_MODEL` overrides the model slug.
- **Twitter/X** needs a logged-in session: `TWITTER_AUTH_TOKEN` + `TWITTER_CT0`
  (from a browser's `x.com` cookies). Optional `TWITTER_PROXY` for a residential
  proxy. Set `CHROMIUM_LOW_MEMORY=0` on hosts with ≥2 GB RAM to render x.com
  fully (the lean single-process mode can return 0 tweets on heavy SPAs).
- **Weibo** needs `WEIBO_SUB` + `WEIBO_SUBP` (from a logged-in `weibo.com`
  session).
- **Reddit** works anonymously on public subreddits. `REDDIT_USERNAME` +
  `REDDIT_PASSWORD` are an optional fallback used **only** when Reddit forces a
  login wall — an IP block cannot be bypassed by logging in (see notes).
- **CORS** — `CORS_ORIGINS` (comma-separated) must include the origin that calls
  the sidecar.

> Cookies/keys are secrets: keep them in the gitignored `.env` or your platform's
> secret store. Never commit real values.

### Tests

```bash
cd backend && pip install pytest anyio[trio] && python -m pytest -q
```

---

## Frontend — integrate into a Next.js 15 app

These are the distortion page's source files, not a runnable app. Copy the
`frontend/src/**` tree into a Next.js 15 (App Router) project and merge the i18n
keys. They assume the host app already provides:

- **next-intl** (i18n; locale-prefixed routes under `[locale]`) — merge
  `frontend/messages/distortion.{en,pl}.json` into your message catalogs.
- **@tanstack/react-query** (the hooks in `use-distortion.ts`).
- **shadcn/ui-style primitives** imported from `@/components/ui`: `Button`,
  `Input`, `Label`, `Skeleton`, `Progress` (+ Tailwind CSS).
- **`@/lib/api-client`** (a `fetch` wrapper exposing `apiClient.get/post` and an
  `ApiError` class) and **`@/lib/server-api`** (`backendFetch` + `BackendApiError`,
  used by the API proxy routes to reach the backend). Repoint `backendFetch`'s
  base URL at your gateway or the sidecar.
- A marketing layout for the `(marketing)` route group (or move the page out of
  that group).

### Wiring the proxy routes

`frontend/src/app/api/distortion/*` proxy the browser → backend:

- `analyze/route.ts` → `POST /api/v1/distortion/analyze`
- `analyze/[jobId]/route.ts` → `GET /api/v1/distortion/analyze/{jobId}`
- `cookies/route.ts`, `cookies/verify/route.ts` → gateway-only developer cookie
  refresh (needs the gateway's Redis + `DISTORTION_DEV_PASSWORD`). Omit these if
  you run sidecar-only and set cookies via the sidecar env instead.

The developer cookie gate (`components/distortion/dev-cookie-gate.tsx`) is a
dev-only UI shown for Twitter/Weibo that lets an operator refresh expired session
cookies without a redeploy; it depends on the gateway endpoints above.

### Frontend tests

The included Vitest specs (`__tests__/`) expect the host app's test setup
(`vitest`, `@testing-library/react`, `jsdom`). Run with `bunx vitest run` (or
`npx vitest run`) once integrated.

---

## Notes & caveats

- **Reddit from datacenter IPs.** Reddit blocks many datacenter/VPN exit IPs
  (403 on the JSON API + anti-bot timeouts on the browser path). Scraping works
  from residential IPs. Logging in does **not** bypass an IP block — the login
  fallback only helps when Reddit shows a login wall.
- **Twitter/X memory.** x.com is a heavy SPA. On <2 GB hosts, keep
  `CHROMIUM_LOW_MEMORY=1` (may return 0 tweets); on ≥2 GB set it to `0` for
  reliable rendering. A residential `TWITTER_PROXY` improves reliability.
- **Job store is in-memory.** `jobs.py` keeps jobs in process memory, so run a
  single worker (or add a shared store) if you scale horizontally.
- **This is an extraction.** Some behaviors (Redis result cache, per-IP rate
  limiting, the developer cookie gate) lived in a separate gateway service that
  is not included here — see the Architecture section.
