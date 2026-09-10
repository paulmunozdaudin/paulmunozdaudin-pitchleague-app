# Database

PostgreSQL, accessed through SQLAlchemy 2.0 declarative models
(`backend/app/models/`) and versioned with Alembic
(`backend/alembic/versions/`). One initial migration currently creates the
full schema below.

## Entity overview

```
User ──┬─< LeagueMembership >──┬── League ──< Season ──< Gameweek ──< Match ──< OddsSnapshot
       │                       │                                       │
       ├─< Prediction >────────┴───────────────────────────────────────┘
       ├─< Wallet >─────────────────────────────────────────────────────(user, league, gameweek)
       ├─< UserBadge >──< Badge
       ├─< UserStreak
       ├─< UserXP
       ├─< UserChallenge >──< Challenge
       └─< Notification
```

## Tables

### `users`
One row per human, provisioned lazily on first verified sign-in (see
ARCHITECTURE.md#auth). `auth_provider` + `auth_provider_id` identify the
OAuth identity that created the account; `email` is used to merge a second
provider into the same account.

### `leagues`
`invite_code` (`PL-XXXX`, unambiguous alphabet — no `0/O/1/I`) is unique
and how friends join. `admin_user_id` is the creator; `budget_per_gameweek`
is the credits everyone starts each gameweek with (admin-configurable).

### `league_memberships`
Join table between `users` and `leagues`, with a `role` (`admin`/`member`)
and `is_active` (soft-delete on kick, so history/predictions aren't lost).

### `seasons`
A league can have many seasons over time (`reset-season` archives the
current one and opens a fresh one at 0). Exactly one `is_active=true`
season per league at a time.

### `gameweeks`
Belongs to a season, numbered sequentially. `status` moves
`upcoming → open → locked → settled` (upcoming is currently unused —
gameweeks are created already `open`, reserved for a future "schedule
ahead of time" flow). `locks_at` is the earliest `kickoff_at` among its
matches — the whole gameweek's picks freeze together at kickoff of the
first match, per spec. `budget` is copied from the league at creation time
so changing the league's budget later doesn't retroactively change a
gameweek in progress.

### `matches`
`external_id` is the odds provider's own id for the fixture — used to
re-fetch odds/results for the *same* match on a later call. `result` is
only set once `status = finished`.

### `odds_snapshots`
**Append-only.** Every fetch adds new rows instead of updating existing
ones, keyed by `(match, market, selection, line, fetched_at)`. `Match.current_odds()`
picks the latest snapshot per `(market, selection, line)` for display; a
`Prediction` stores the exact price it was placed against
(`odds_price_at_pick`), so a later odds refresh never changes an
already-placed prediction's payout math.

### `predictions`
One row per `(user, league, match)` — unique constraint means re-picking a
match overwrites the previous selection/stake rather than stacking a
second bet, matching the spec's "elige de nuevo = se actualiza" UX. Stores
the market/selection/line, the price it was locked in at, the stake, the
computed `potential_payout`, and after settlement the actual `payout` and
`status` (`pending → won | lost | void`).

### `wallets`
One row per `(user, league, gameweek)` — this *is* the "fresh budget every
week" mechanic: `starting_balance` is the gameweek's budget,
`current_balance` moves as predictions are placed/cancelled/settled. Season
standings are `sum(current_balance - starting_balance)` across every
settled gameweek's wallet for that user in that league.

### `badges` / `user_badges`
`badges` is a small seeded catalog (`services/gamification.py::BADGE_CATALOG`).
`user_badges` records every time a user earns one, scoped to
`(user, league, badge, gameweek)` — a badge can be earned again in a later
gameweek, and each earning is its own row (a running trophy case, not a
single boolean per badge).

### `user_streaks`
One row per `(user, league, streak_type)` — currently `top_3_finish` and
`correct_picks` (perfect-week streak). Tracks `current_count` and
`best_count`; reset to 0 the moment a gameweek breaks the streak.

### `user_xp`
One row per user (global, not per-league): `xp` and a derived `level`
(`1 + xp // 500`). XP is earned only by playing — correct picks, picks
made, and completed weekly challenges — never purchasable.

### `challenges` / `user_challenges`
`challenges` are generated per gameweek (`services/gameweeks.py::DEFAULT_CHALLENGES`)
when it's opened. `user_challenges` tracks completion + XP payout per user.

### `notifications`
Generic in-app notification (`type`, `title`, `body`, free-form `data`
JSON, `read_at`). Currently only `gameweek_settled` is emitted
automatically; the `data` JSON carries `{ league_id, gameweek_id, position,
net_change }` so the frontend can deep-link straight to the results screen.

## Design notes

- **UUID primary keys** everywhere (`uuid4`, generated app-side) — avoids
  leaking sequential IDs (league size, user count) and makes merging data
  across environments trivial.
- **Naive UTC datetimes, consistently.** Every datetime column is stored
  without a timezone offset, by convention always UTC
  (`app/db/base.py::utcnow`). This sidesteps a real cross-database
  footgun: SQLite's `DateTime(timezone=True)` silently returns naive
  datetimes on read, which breaks `aware >= naive` comparisons the moment a
  row round-trips through the DB. Naive-but-always-UTC works identically
  on SQLite (tests) and Postgres (prod).
