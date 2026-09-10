# PitchLeague

Private prediction leagues for groups of friends, settled against real market
odds. Every gameweek everyone gets the same virtual budget, picks their
predictions, and watches the ranking shake out — a bad week never eliminates
you, because next week starts fresh.

> **Status: working MVP.** The full weekly loop (create a league → invite
> friends → open a gameweek → predict → settle → rank → gamify) runs
> end-to-end against a deterministic mock odds provider with no API keys
> required. See [docs/ROADMAP.md](docs/ROADMAP.md) for exactly what's built
> vs. what's a documented next step.

## Stack

| | |
|---|---|
| Frontend | Next.js 15 (App Router) · TypeScript · Tailwind CSS · Framer Motion · a hand-rolled shadcn-style UI kit |
| Backend | FastAPI · Python 3.12 · SQLAlchemy 2.0 · Alembic |
| Database | PostgreSQL |
| Auth | NextAuth.js (Google, Discord; Apple wired but needs a paid Apple dev account) bridged to FastAPI via a signed JWT |
| Realtime | Native WebSockets (per-league room) |
| Odds | Pluggable provider — deterministic mock (default, no key) or [The Odds API](https://the-odds-api.com) |
| AI insights | Pluggable provider — deterministic heuristic (default, no key) or Anthropic Claude |

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the reasoning behind
each of these choices, including the odds-provider comparison (ADR-001).

## Project layout

```
backend/            FastAPI app
  app/
    models/          SQLAlchemy models
    schemas/         Pydantic request/response models
    api/v1/routers/  HTTP endpoints (thin — delegate to services/)
    services/        Business logic: leagues, predictions, settlement,
                      rankings, gamification, odds_providers/, ai_providers/
    workers/         Standalone scheduler (auto-lock, sync odds, settle)
    db/              Engine/session, declarative base
  alembic/           Migrations
  tests/             pytest — unit/ (pure logic) + integration/ (API flows)

frontend/            Next.js app
  src/
    app/             Routes (App Router)
    components/      ui/ (design system) + feature components
    hooks/           useApi, useLeagueRealtime
    lib/             API client, auth config, utils
    types/           Shared TS types mirroring the backend schemas

docs/                ARCHITECTURE · API · DATABASE · DEPLOYMENT · ROADMAP
docker-compose.yml   postgres + backend + worker + frontend
```

## Running locally

### With Docker (closest to production)

```bash
cp .env.example .env   # fill in at least NEXTAUTH_SECRET / AUTH_SHARED_SECRET
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000 (docs at `/docs`)

### Without Docker

**Backend**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# Point DATABASE_URL at a real Postgres, or use SQLite for a quick spin:
#   DATABASE_URL=sqlite:///./dev.db
alembic upgrade head        # only needed against Postgres — see note below
uvicorn app.main:app --reload
```

> The bundled migration targets Postgres. For a zero-setup local spin
> against SQLite, skip `alembic upgrade head` and instead run
> `python -c "from app.models import Base; from app.db.session import engine; Base.metadata.create_all(engine)"`.

In a second terminal, run the worker that locks/settles gameweeks automatically:

```bash
python -m app.workers.scheduler
```

**Frontend**

```bash
cd frontend
npm install
cp ../.env.example .env.local   # NEXT_PUBLIC_API_URL, NEXTAUTH_*, OAuth keys
npm run dev
```

Without real Google/Discord OAuth credentials you can still exercise the
API directly (see `backend/tests/conftest.py::issue_dev_token` for how the
test suite mints a valid session token without a real OAuth round trip).

## Tests

```bash
cd backend && python -m pytest --cov=app          # 24 tests, ~83% coverage
cd frontend && npm run build && npm run lint       # typecheck + lint
```

## Documentation

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) — system design, auth bridge, ADRs
- [API.md](docs/API.md) — endpoint reference
- [DATABASE.md](docs/DATABASE.md) — schema and domain model
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) — shipping this to production
- [ROADMAP.md](docs/ROADMAP.md) — phased plan, what's done vs. open
