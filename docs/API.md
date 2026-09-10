# API Reference

Base URL: `http://localhost:8000/api/v1`. Interactive docs (Swagger UI) are
served by FastAPI itself at `/docs` when the backend is running.

Every endpoint except none requires `Authorization: Bearer <backendToken>`
(see [ARCHITECTURE.md#auth](ARCHITECTURE.md#auth) for where that token
comes from). League-scoped endpoints additionally require the caller to be
an active member of that league; admin-only actions require the caller to
be the league's creator.

## Auth

| Method | Path | Description |
|---|---|---|
| GET | `/auth/me` | Verifies the bearer token, lazily provisions the user, returns their profile |

## Leagues

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/leagues` | member | Create a league (caller becomes admin) |
| POST | `/leagues/join` | member | Join via `{ invite_code }` |
| GET | `/leagues` | member | List the caller's leagues |
| GET | `/leagues/{league_id}` | member | League detail incl. member list |
| PATCH | `/leagues/{league_id}` | admin | Rename / change `budget_per_gameweek` |
| DELETE | `/leagues/{league_id}/members/{user_id}` | admin | Remove a member |
| POST | `/leagues/{league_id}/reset-season` | admin | Archive the current season, start a new one at 0 |

## Gameweeks, matches & predictions

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/leagues/{league_id}/gameweeks/current` | member | The active (non-settled) gameweek, with matches, live odds, the caller's wallet and existing picks |
| GET | `/leagues/{league_id}/gameweeks/{gameweek_id}` | member | Same shape, for a specific (e.g. past) gameweek |
| POST | `/leagues/{league_id}/gameweeks/generate-next` | admin | Pull fixtures+odds from the odds provider and open the next gameweek |
| POST | `/leagues/{league_id}/gameweeks/{gameweek_id}/refresh-odds` | admin | Re-fetch prices for not-yet-locked matches (appends new snapshots) |
| POST | `/leagues/{league_id}/gameweeks/{gameweek_id}/predictions` | member | Place or overwrite a prediction: `{ match_id, market, selection, line?, stake }` |
| DELETE | `/leagues/{league_id}/gameweeks/{gameweek_id}/predictions/{prediction_id}` | member | Cancel (only before kickoff), refunds the stake |
| GET | `/leagues/{league_id}/gameweeks/{gameweek_id}/predictions/me` | member | The caller's picks for that gameweek |
| POST | `/leagues/{league_id}/gameweeks/{gameweek_id}/settle` | admin | Sync results + settle if every match has finished (the worker also calls this automatically) |
| GET | `/leagues/{league_id}/matches/{match_id}/insight` | member | AI-generated context paragraph for a match |

`market` is one of `winner | double_chance | over_under | both_teams_to_score`.
`selection` depends on the market — see `backend/app/models/enums.py::Selection`.

## Rankings

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/leagues/{league_id}/rankings/season` | member | Cumulative net-winnings leaderboard for the active season |
| GET | `/leagues/{league_id}/rankings/{gameweek_id}` | member | That gameweek's own leaderboard (balance vs. starting budget) |
| GET | `/leagues/{league_id}/rankings/{gameweek_id}/result-summary` | member | The caller's personal end-of-gameweek recap (net change, position swing, new badges, rival overtaken) — powers the results screen |

## Profile & gamification

| Method | Path | Description |
|---|---|---|
| GET | `/profile/me/stats?league_id=` | Accuracy, best week, longest streak, highest multiplier, ROI, XP/level, earned badges. Omit `league_id` for stats across all of the caller's leagues |

## Notifications

| Method | Path | Description |
|---|---|---|
| GET | `/notifications` | Caller's notifications, newest first |
| POST | `/notifications/{id}/read` | Mark one as read |

## Realtime

| Protocol | Path | Description |
|---|---|---|
| WebSocket | `/ws/leagues/{league_id}?token=<backendToken>` | Live push — currently emits `gameweek_settled` with the fresh ranking. The token travels as a query param because browsers can't set custom headers on a WS handshake. |

## Error shape

Validation and business-rule errors return FastAPI's standard shape:

```json
{ "detail": "Stake exceeds available budget (4000 credits left)" }
```
or, for Pydantic validation errors, `detail` is a list of
`{ "loc": [...], "msg": "...", "type": "..." }` objects.
