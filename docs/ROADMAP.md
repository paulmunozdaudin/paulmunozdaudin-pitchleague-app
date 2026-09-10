# Roadmap

Phased per the original brief. Each phase below is marked **done** (built
and tested this pass), **partial** (a real, working slice — not a stub —
with clearly scoped gaps), or **open** (documented, not built).

## Fase 1 — Arquitectura ✅ done
Monorepo (`backend/` FastAPI, `frontend/` Next.js), Docker Compose for
postgres + backend + worker + frontend, layered backend (`models` /
`schemas` / `services` / `api`), design-system-first frontend.

## Fase 2 — Autenticación ✅ done (Google, Discord) · ⚠️ partial (Apple)
NextAuth → signed-JWT bridge → FastAPI, lazy user provisioning. Apple Sign
In is wired structurally in `frontend/src/lib/auth.ts` but requires a paid
Apple Developer account to generate its JWT client secret, so it's not
enabled by default.

## Fase 3 — Base de datos ✅ done
Full schema (leagues, seasons, gameweeks, matches, odds snapshots,
predictions, wallets, badges, streaks, XP, challenges, notifications), one
Alembic migration, naive-UTC datetime convention documented in
`docs/DATABASE.md`.

## Fase 4 — Ligas ✅ done
Create/join via invite code, member list, admin rename/budget/kick, season
reset. Chat (mentioned in the brief as "chat futuro preparado") is **open**
— the schema has no chat table yet; it's a clean addition (`league_id` +
`user_id` + `body` + `created_at`) whenever it's prioritized.

## Fase 5 — Integración de cuotas ✅ done
Provider interface with two implementations: a deterministic mock (default,
zero config, what all tests run against) and a real
[The Odds API](https://the-odds-api.com) client. See ADR-001 in
`docs/ARCHITECTURE.md` for the comparison behind that choice. Odds are
timestamped, append-only snapshots. **Not exercised against the live Odds
API in this pass** — no key was available in this environment; the client
is written to their documented contract but its first real run should be
treated as an integration smoke test.

## Fase 6 — Predicciones ✅ done
All four MVP markets (winner, double chance, over/under, both-teams-to-score),
budget validation, kickoff-lock, re-pick overwrites instead of stacking.

## Fase 7 — Liquidación ✅ done
Automatic once the worker is running (`app/workers/scheduler.py`), manual
trigger also available from the admin panel. Idempotent, per-market
settlement logic, unit-tested for all four markets including push/void.

## Fase 8 — Rankings ✅ done
Per-gameweek leaderboard and season-cumulative leaderboard, with
animated position-change UI on the frontend.

## Fase 9 — IA ✅ done (heuristic) · ✅ done (Claude, needs key)
Pluggable `AIInsightProvider`; heuristic is the zero-config default,
Anthropic Claude is a config swap away. Always falls back to heuristic on
any LLM error. Never recommends a selection (enforced in the prompt), per
spec.

## Fase 10 — Gamificación ✅ done (core) · ⚠️ partial (breadth)
XP/levels, 2 streak types (top-3 finish, perfect week), 8 badges from the
brief (`first_place, hat_trick, comeback, giant_killer, perfect_week,
underdog, invencible, sniper`), 3 default weekly challenges auto-generated
per gameweek. **Open:** more challenge variety, a dedicated
badges/achievements gallery beyond the profile page's grid, playoffs
(season champion is tracked structurally via `Season.champion_user_id` but
nothing sets it yet).

## Fase 11 — Notificaciones ⚠️ partial
In-app notifications (`gameweek_settled` today, deep-linking to the
results screen) plus a WebSocket channel for live ranking pushes. **Open:**
push notifications (would need a service worker + web push subscriptions,
or a native app), and the other notification types from the brief
("Tu amigo te ha adelantado", "Quedan dos horas", "Has bajado al segundo
puesto") — the plumbing (`services/notifications.py::create_notification`)
supports adding these as new triggers without a schema change.

## Fase 12 — Lanzamiento ⚠️ partial
What's ready: CI (`​.github/workflows/ci.yml` — backend tests + frontend
build/lint on every push), Docker images for both apps, deployment guide
(`docs/DEPLOYMENT.md`). **Open before a real launch:**
- Run the full flow against real Google/Discord OAuth apps and a real
  Postgres instance (this pass validated against SQLite + dev tokens —
  see `backend/tests/conftest.py`).
- Rate limiting on the API (mentioned in the original brief under
  "Seguridad" — not yet implemented; `slowapi` or a reverse-proxy-level
  limiter are natural fits).
- E2E browser tests (Playwright) covering the full onboarding → predict →
  settle → results loop through a real browser session. Backend has 24
  passing unit/integration tests (~83% coverage); the frontend was
  validated by building, linting, and visually reviewing every screen
  with mock data (screenshots reviewed during this pass), but has no
  automated E2E suite yet.
- A PNG/image export of the shareable result card (currently a styled
  component + native Web Share API / clipboard text — real image
  generation would add `satori` or `html-to-image`).

## Not in this pass, by design

- **Real money / real odds trading** — explicitly out of scope; this is a
  virtual-credits game, never a betting product.
- **Native mobile app** — the frontend is a responsive, mobile-first web
  app; a wrapped/native shell is a separate future project.
