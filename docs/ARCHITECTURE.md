# Architecture

## Overview

```
┌─────────────┐      bearer JWT       ┌──────────────┐      SQLAlchemy      ┌────────────┐
│  Next.js     │ ───────────────────▶ │   FastAPI     │ ───────────────────▶ │ PostgreSQL │
│  (App Router)│ ◀─────────────────── │   (app/)      │ ◀─────────────────── │            │
└─────┬───────┘      JSON / WS        └──────┬───────┘                      └────────────┘
      │                                       │
      │ NextAuth (Google/Discord)             │ services/odds_providers  → mock | The Odds API
      │                                       │ services/ai_providers    → heuristic | Anthropic
      ▼                                       ▼
  OAuth providers                    app/workers/scheduler.py (separate process)
                                       locks gameweeks, refreshes odds, settles
```

The backend is a fairly conventional layered FastAPI app:

- **`api/v1/routers/`** — thin HTTP layer. Auth, validation via Pydantic
  schemas, permission checks (`api/v1/deps.py`), then delegates to…
- **`services/`** — all business logic. Every router handler is a few lines
  because the actual rules (budget math, settlement, ranking, badge
  triggers) live here and are unit-testable without spinning up HTTP.
- **`models/`** — SQLAlchemy 2.0 declarative models, one module per domain
  area (`league.py`, `gameweek.py`, `prediction.py`, `gamification.py`, …).
- **`workers/scheduler.py`** — the only place that runs on a timer instead
  of a request. It calls the exact same service functions the API does.

## Auth

The product spec asks for Google, Apple and Discord sign-in from a Next.js
frontend, verified by a separate FastAPI backend. Two standard options
exist: give FastAPI its own OAuth flow (duplicate provider config, two
places that can drift), or let NextAuth own the OAuth dance and hand
FastAPI something it can verify statelessly. We do the latter:

1. User signs in with Google/Discord via NextAuth (`frontend/src/lib/auth.ts`).
2. NextAuth's `session` callback mints a **second, small HS256 JWT** —
   `{ sub, email, name, picture, provider }` — signed with a secret shared
   between the two apps (`NEXTAUTH_SECRET` on the frontend,
   `AUTH_SHARED_SECRET` on the backend — **must be the same value**).
3. The frontend attaches that token as `Authorization: Bearer <token>` on
   every API call (see `frontend/src/hooks/useApi.ts`).
4. `backend/app/core/security.py::get_current_user` verifies it and
   **lazily provisions** the local `User` row on first sight — there's no
   separate "register" endpoint.

This is deliberately *not* NextAuth's own session cookie, which is an
internal encrypted JWE (A256CBC-HS512) that's awkward to verify from a
different stack. A second, purpose-built, plainly-verifiable token is the
standard way to bridge NextAuth to an external backend.

Apple Sign In is wired into `frontend/src/lib/auth.ts` structurally but
requires a paid Apple Developer account (to generate the JWT client
secret Apple requires), so it's off by default — see ROADMAP.

## Budget & wallets

Spec requirement: everyone gets a fresh virtual budget every gameweek, and
a bad week should never eliminate anyone. Modeled as a `Wallet` row scoped
to `(user, league, gameweek)` — `starting_balance` is copied from the
league's configured budget the first time a wallet is touched, and
`current_balance` is debited/credited as predictions are placed, cancelled,
or settled. Because it's a full new row every gameweek (not a running
balance), the "reset every week" behavior is structural, not a special
case, and season standings are simply `sum(current_balance -
starting_balance)` across every settled gameweek's wallet.

## Odds: timestamped snapshots, never overwritten

`OddsSnapshot` rows are append-only, keyed by
`(match, market, selection, line, fetched_at)`. Predictions store the exact
price they were placed against (`odds_price_at_pick`), so re-fetching odds
before kickoff (price movement) never retroactively changes an already-placed
prediction, and the full price history is free — useful for a future
"here's how the odds moved" feature.

### ADR-001: odds provider

**Decision: [The Odds API](https://the-odds-api.com)**, behind a provider
interface (`services/odds_providers/base.py::OddsProvider`) so it's a
one-line config swap (`ODDS_PROVIDER=the_odds_api` + `THE_ODDS_API_KEY`),
and a deterministic **mock provider is the default** so the whole product
works with zero API keys.

Compared:

| Provider | Pricing | Coverage | Integration | Notes |
|---|---|---|---|---|
| **The Odds API** | Free tier (500 req/mo), then metered, no minimum commit | Dozens of bookmakers across all major soccer leagues, h2h/totals/btts markets | Plain REST/JSON, one API key | **Chosen.** Best fit for an MVP serving a handful of small private leagues — cheap to start, scales by paying per request, no exchange protocol to integrate |
| Betfair Exchange API | Free access, but requires a funded/verified Betfair account | Deep liquidity, real exchange prices | Complex (streaming API, session auth, exchange-specific concepts like back/lay) | Overkill for showing reference odds; built for placing real exchange bets |
| Pinnacle API | Free for approved partners, but approval is discretionary/slow | Sharp, low-margin odds | REST, but partner approval is a blocker for an MVP timeline | Great odds quality, bad fit for "ship this week" |
| sportsdataio | Paid tiers only, no free odds tier | Very broad (odds + stats + live scores in one contract) | REST, clean docs | Good if we later also want the stats feed for AI insights; too pricey to start |

`double_chance` isn't a market The Odds API sells directly — we derive it
from the `h2h` (1X2) implied probabilities ourselves
(`the_odds_api.py::_derive_double_chance`), carrying the market's own
overround through rather than inventing a new margin. `both_teams_to_score`
coverage varies by bookmaker/competition; when nobody quotes it for a match
we simply omit that market instead of fabricating a price.

### The mock provider

`services/odds_providers/mock.py` is not a toy — every price and every
simulated match result is a **pure, deterministic function** of team names
and a day bucket (via a seeded PRNG), including a realistic bookmaker
overround. That determinism is what lets the settlement engine, the
gamification triggers, and the full integration test suite exercise a
real end-to-end weekly cycle with zero external dependencies and zero
flakiness.

## Settlement

`services/settlement.py::settle_gameweek` is idempotent and safe to call
repeatedly (the worker does, every 5 minutes): it fetches results only for
matches that have kicked off and aren't `FINISHED` yet, and only fully
settles the gameweek once *every* match in it is finished. Each pending
prediction is evaluated against the match's actual final score
(`_prediction_outcome`) — not against the odds — for all four MVP markets,
credited back to the wallet, and only then does `services/gamification.py`
run (badges, streaks, XP) followed by per-user notifications and a
WebSocket broadcast to the league room.

## AI match insights

Same pluggable-provider pattern as odds
(`services/ai_providers/base.py::AIInsightProvider`):
a **heuristic provider is the default** (deterministic, no key, derives a
plausible-sounding form/odds-skew narrative the same way the mock odds
provider derives prices), and an **Anthropic Claude provider**
(`AI_INSIGHTS_PROVIDER=anthropic` + `ANTHROPIC_API_KEY`) can be swapped in.
The insight endpoint always falls back to the heuristic provider on any
LLM failure — a flaky/misconfigured key never breaks the match screen. The
prompt explicitly instructs the model to never recommend a selection,
matching the product requirement that AI only informs, never decides.

## Realtime

A single in-process `ConnectionManager` (`services/realtime.py`) holding
WebSocket connections per league room — no external broker. Settlement
broadcasts a `gameweek_settled` event with the fresh ranking to everyone
connected to `/ws/leagues/{league_id}`. This is the right scope for an MVP
on a single backend instance; the natural upgrade path if the app ever runs
multiple API workers is Supabase Realtime or a Redis-backed pub/sub,
dropped in behind the same `broadcast()` call.

## Frontend

- **App Router, mostly client components.** Data is fetched client-side
  through `useApi()` (wraps `fetch` with the bridge token from
  `useSession()`), which keeps the same request pattern usable for both
  SSR-agnostic pages and interactive flows (predicting, admin actions)
  without a separate server-action layer to keep in sync.
- **Design system** (`components/ui/`) is hand-rolled in the shadcn
  convention — Radix primitives + `class-variance-authority` + `cn()`,
  copied into the repo rather than pulled from a component registry, so it
  fully matches the "Apple/Linear/Arc/Spotify" brief without fighting a
  pre-built theme.
- **`LeagueContext`** fetches a league's detail once per league-scoped
  route tree and shares it (name, budget, admin flag, members) rather than
  every sub-page re-fetching it.
