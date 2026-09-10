# Deployment

This is written for a small-scale production deploy (a handful of private
leagues) rather than an internet-scale one — matching where the product
actually is right now.

## Recommended shape

| Component | Suggestion | Why |
|---|---|---|
| Frontend | [Vercel](https://vercel.com) | Native Next.js App Router support, zero-config |
| Backend + worker | Any container host (Fly.io, Railway, Render, a plain VM with Docker) | It's a standard Docker image (`backend/Dockerfile`); no platform lock-in |
| Database | Managed Postgres (Supabase, Neon, RDS, Railway) | Automated backups; Supabase also gives you Realtime/Storage for free if you later want to move off the in-process WebSocket manager |

## Environment variables

Copy `.env.example` to `.env` and fill in:

- `AUTH_SHARED_SECRET` **must equal** the frontend's `NEXTAUTH_SECRET` —
  this is the one value both apps need to agree on. Generate with
  `openssl rand -hex 32`.
- `DATABASE_URL` — production Postgres connection string
  (`postgresql+psycopg://...`).
- `BACKEND_CORS_ORIGINS` — the frontend's real origin(s), comma-separated.
- `ODDS_PROVIDER=the_odds_api` + `THE_ODDS_API_KEY` — switch off the mock
  provider once you have a key (see ARCHITECTURE.md#adr-001-odds-provider).
- `AI_INSIGHTS_PROVIDER=anthropic` + `ANTHROPIC_API_KEY` — optional, falls
  back to the free heuristic provider if unset or if a call fails.
- `GOOGLE_CLIENT_ID`/`SECRET`, `DISCORD_CLIENT_ID`/`SECRET` — OAuth app
  credentials. Redirect URI for each: `https://<your-domain>/api/auth/callback/<provider>`.

## Database migrations

```bash
cd backend
alembic upgrade head
```

Run this once against the production database before starting the API
(the Docker Compose `backend` service already does this on every start —
`alembic upgrade head` is idempotent/no-op once applied).

## The worker process

Settlement, odds refresh, and gameweek locking are **not** automatic
unless `app/workers/scheduler.py` is running as its own long-lived process
(`python -m app.workers.scheduler`, or the `worker` service in
`docker-compose.yml`). Without it, an admin can still trigger the same
actions manually from the admin panel (`Actualizar cuotas` /
`Liquidar jornada`), but production should run the worker.

## Checklist before going live

- [ ] Real `AUTH_SHARED_SECRET` (matching on both apps), not the dev default
- [ ] Real Postgres, migrations applied
- [ ] Google/Discord OAuth apps created with the production redirect URIs
- [ ] `THE_ODDS_API_KEY` set (or knowingly staying on the mock provider for a soft launch)
- [ ] Worker process running (odds/settlement won't happen automatically otherwise)
- [ ] `BACKEND_CORS_ORIGINS` set to the real frontend origin
- [ ] HTTPS on both frontend and backend (required for secure OAuth cookies)

## Scaling notes (not needed at current scale, documented for later)

- **Realtime** is a single in-process WebSocket manager
  (`services/realtime.py`) — fine for one backend instance. Running more
  than one API replica means league rooms would split across instances;
  swap in Supabase Realtime or Redis pub/sub behind the same
  `manager.broadcast()` call when that's actually needed.
- **Odds provider rate limits**: The Odds API's free tier is 500
  requests/month. Each `refresh-odds` call is one request per configured
  sport key (currently 4), so budget accordingly or raise
  `DEFAULT_GAMEWEEK_BUDGET`/reduce refresh frequency in the worker.
