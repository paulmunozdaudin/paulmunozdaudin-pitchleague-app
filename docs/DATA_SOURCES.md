# Data Sources

Two separate data problems, two separate sources — conflating them was the
first thing to avoid. **Live odds** (what a user sees on a match card this
week) and **historical results+odds** (what the Model Engine trains and
backtests on) have different freshness, coverage, and licensing needs, and
are sourced independently.

## 1. Live odds — for the match screen and settlement

Unchanged from the original ADR, restated here as the canonical source of
truth (`backend/app/services/odds_providers/`).

| Provider | Pricing | Coverage | Integration | Verdict |
|---|---|---|---|---|
| **The Odds API** | Free tier (500 req/mo), then metered, no minimum commit | Dozens of bookmakers across all major soccer leagues; h2h/totals/btts markets | Plain REST/JSON, one API key | **Chosen.** Best fit for an MVP serving a handful of small private leagues |
| Betfair Exchange API | Free access, requires a funded/verified account | Deep liquidity, real exchange prices | Complex exchange protocol (streaming, session auth, back/lay) | Overkill — built for placing real exchange bets, not showing reference odds |
| Pinnacle API | Free for approved partners, approval discretionary/slow | Sharp, low-margin odds | REST, but partner approval blocks an MVP timeline | Great odds quality, bad fit for "ship this week" |
| API-Football (RapidAPI) | Free tier very limited (100 req/day); paid tiers for real volume | Fixtures/results/odds/lineups in one API | REST, well documented | Good alternative if The Odds API's coverage gap (btts availability varies) becomes a problem — kept as the documented fallback |
| sportsdataio | Paid tiers only | Very broad (odds + stats + live scores, one contract) | REST, clean docs | Good if we later want the stats feed too; too pricey to start |

`ODDS_PROVIDER=mock` remains the default (deterministic, zero-config,
what tests and local dev run against) — see `services/odds_providers/mock.py`.
Not exercised against the live Odds API in this environment: this
sandbox's network egress is allowlisted (see "What this sandbox can
actually reach," below) and `api.the-odds-api.com` isn't on it, so the
client is written to their documented contract but its first real call
should be treated as an integration smoke test, not a proven path.

## 2. Historical results + odds — for the Model Engine

This is the harder problem, and the one worth explaining properly: the
Model Engine (`docs/ARCHITECTURE.md#model-engine`) needs tens of thousands
of *real* past matches with *real* market odds to backtest against — not
a handful of examples, and never synthetic data standing in for it.

### What this sandbox can actually reach

Before picking a source, this environment's real constraint: outbound
network is allowlisted at the infrastructure level, and it does **not**
include football-data.co.uk, football-data.org, api-football, or any
dedicated sports-data host directly (`www.football-data.co.uk:443` and
`api.football-data.org:443` both reject the CONNECT at the proxy — this
was tested, not assumed). It **does** allow `github.com` and
`raw.githubusercontent.com`. That constraint shaped the sourcing decision
below as much as licensing did — this isn't a workaround, it's the actual
data that ended up sourced.

### Options considered

| Source | Real odds? | License | Reachable here? | Verdict |
|---|---|---|---|---|
| football-data.co.uk (original) | Yes (multi-bookmaker, since 2000) | Explicitly free for personal/research use | **No** — blocked by sandbox egress | Would be the direct source in an environment with open internet; not usable here |
| football-data.org API | No (fixtures/results only, no odds on free tier) | Free tier: 10 req/min, limited competitions | No — blocked | Insufficient even if reachable (no odds) |
| Kaggle football datasets | Varies, mostly results-only or stale snapshots | Varies per dataset, often unclear/non-commercial | No — Kaggle itself not reachable | License uncertainty alone would rule most of these out |
| StatsBomb Open Data | No odds; excellent event-level/xG data for ~40 free competitions | Free, CC BY-NC-SA (non-commercial) | Reachable in principle (GitHub-hosted) | Great future addition for real xG once the product needs it, but non-commercial license and no odds make it a poor fit for the MVP's backtest-against-the-market use case |
| Understat (unofficial xG scraping) | No | No formal license; scraping ToS is gray-area | N/A | Rejected — "don't invent/scrape gray-area data" applies here |
| **[xgabora/Club-Football-Match-Data-2000-2025](https://github.com/xgabora/Club-Football-Match-Data-2000-2025)** | **Yes** — real Bet365 + ~17-bookmaker-max odds (1X2, O/U 2.5), sourced from football-data.co.uk | **MIT** | **Yes** — GitHub-hosted, verified reachable and downloaded | **Chosen** |

### What was actually pulled

`data/Matches.csv` from that repository: **238,858 matches, 2000-07-28 to
2026-09-03**, across 38 league/division codes, each row carrying **real
Bet365 1X2 and Over/Under 2.5 odds**, plus **real Elo ratings** (sourced
from [ClubElo](https://www.clubelo.com/), an independent, long-running,
football-specific Elo rating service) and rolling pre-match form —
verified by downloading the file (45MB, `content-length` checked before
and after) and inspecting real rows (Marseille vs Troyes, 2000-07-28,
Bet365 odds 1.65/3.3/4.3, etc. — not fabricated examples).

Filtered down to what the product actually needs and committed to the repo
as `backend/data/historical_matches.csv` (2.9MB, 29,960 rows):

- **5 leagues**: `E0` Premier League, `SP1` La Liga, `I1` Serie A, `D1`
  Bundesliga, `F1` Ligue 1 — the same five the mock odds provider covers.
- **2010-01-01 onward** — recent enough that team identities and rosters
  are still meaningful for an Elo/form-based model, while keeping ~16
  seasons per league (plenty for walk-forward validation).
- **Only rows with both a final result and real 1X2 odds** — a row
  missing either isn't usable for training (no label) or backtesting
  (nothing to compare the model against).
- **Columns kept**: `Division, MatchDate, HomeTeam, AwayTeam, HomeElo,
  AwayElo, Form3Home, Form5Home, Form3Away, Form5Away, FTHome, FTAway,
  FTResult, OddHome, OddDraw, OddAway, Over25, Under25`.

### Columns deliberately dropped — this is the leakage boundary

The source file also has shots, shots-on-target, corners, fouls, and
cards **for the match being predicted**. Those are *outcomes* of the
match, not information available before kickoff — a model trained on "how
many corners did the home team get" to predict that same match's result
would be a textbook example of the leakage `docs/ARCHITECTURE.md#no-leakage`
and the brief both call out. They're excluded from
`historical_matches.csv` entirely, on purpose, not just left unused. The
only pre-match-safe fields kept are `HomeElo`/`AwayElo` (a rating that
only updates *after* each match closes) and `Form3/5` (rolling stats over
the *preceding* 3/5 matches) — both are explicitly "state entering the
match," not the match's own outcome.

### Refresh strategy

This is a **static, versioned snapshot**, not a live feed — appropriate
for backtesting (you want a stable, reproducible dataset to compare model
versions against) but it will go stale for *training* a model meant to
predict next month's fixtures. `app/model_engine/ingest.py` is written to
re-pull and re-filter from the same GitHub source on demand
(`python -m app.model_engine.ingest`); re-run it periodically (quarterly
is plenty for a hobby-scale league) and retrain — see
`docs/ARCHITECTURE.md#model-engine` for the retraining/versioning story.

### License compliance

The source repository is MIT-licensed (verified on GitHub, not assumed);
MIT permits redistribution of the derived, filtered CSV committed here,
which is what `backend/data/historical_matches.csv` is. Attribution is
kept in this file and in the dataset repository's own citation request
(Gábor, A. (2026), *Club Football Match Data*).
