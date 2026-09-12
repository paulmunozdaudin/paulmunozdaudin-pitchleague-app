# Legal & Regulatory Notes

**This is engineering-level research, not legal advice.** It exists to make
the product's compliance posture explicit and to flag exactly which design
constraints are load-bearing for that posture. Get a lawyer licensed in
each target market to review before any public launch — this document is
the brief you'd hand them, not a substitute for them.

Target market analyzed: **Spain** (primary — Spanish-language product,
`.es` audience implied by the brief) and, at a lighter level, **the EU**
generally, since a web product is trivially reachable EU-wide.

## The core question: is this "juego" under Spanish law?

Spain's gambling framework, **Ley 13/2011, de regulación del juego**,
defines gambling ("juego") as an activity where **money or
economically-valuable goods are staked** on a future, uncertain result,
where sums can be **transferred between participants** — regardless of how
much skill is involved. Any gambling activity that isn't licensed by the
DGOJ (Dirección General de Ordenación del Juego) is prohibited outright;
there's no "unregulated but tolerated" middle ground in Spain the way there
is in some other markets.

The operative word is **stake of real economic value**. PitchLeague's
credits are:

- granted for free by the platform every gameweek (never bought),
- worth nothing outside the app (no exchange rate to any currency),
- not transferable between users in any way that carries economic value,
- not withdrawable, not convertible, not redeemable for anything.

Under that design, there is no "apuesta" in the Ley 13/2011 sense — nobody
risks anything of value, and nothing of value changes hands between
players or between a player and the operator. That takes the product
outside DGOJ's licensing scope, on the same basis "social casino" apps and
free fantasy-sports games operate legally without a gambling license
across the EU.

**This conclusion is entirely dependent on the constraints holding.** The
moment any of the following is added, the legal analysis has to be redone
from scratch, likely concluding the product now needs a DGOJ gambling
license (a materially different, expensive, heavily regulated business):

- **Selling credits for real money**, even one-way with no cash-out. This
  is exactly the pattern the European Commission's 2023 consumer-protection
  guidelines on virtual currencies in games target — "you can't cash out,
  but you paid real money to play" is treated as a gambling-adjacent
  pattern for minors' protection purposes even where it technically
  doesn't meet Ley 13/2011's definition. **Do not add a "buy credits" flow
  without new legal review.**
- **Any cash-out, prize, or reward with real-world value** — merchandise,
  gift cards, discounts, anything. The instant a credit can become
  something of value, the "no stake of value" argument collapses.
- **Peer-to-peer credit transfers** with any resale/exchange angle (e.g. a
  marketplace where users trade credits, or credits tradeable for
  something that itself has value).
- **Charging an entry fee** to join or create a league, in money or in
  anything of value.

## What to do regardless of the above

- **Never market this as a way to win money**, even virtual. No "gana
  premios", no implication of real value, anywhere in copy, App Store
  listing, or ads.
- **Terms of Service** must state explicitly, in plain language: credits
  have no monetary value, cannot be purchased, cannot be cashed out, and
  are reset/granted at the platform's discretion.
- **Age signal**: this looks and feels like a betting product even though
  it structurally isn't gambling. Treat it like one for minors' protection
  regardless of legal necessity — don't target under-18s in marketing, and
  consider an age gate at signup even though Ley 13/2011 doesn't legally
  require KYC/age verification for a non-gambling product (the EU
  consumer-protection guidance above cares about *design that resembles
  gambling*, not just the legal label).
- **GDPR** (applies regardless of the gambling question, as with any EU
  product handling personal data): document a lawful basis for processing
  (session `docs/DATABASE.md` — email, name, avatar from OAuth), give
  users a way to request deletion, and don't retain more than needed. This
  MVP doesn't yet implement a self-serve data-deletion flow — see
  ROADMAP.md.
- **Advertising / market-data attribution**: the odds shown are real
  market prices sourced from a licensed odds aggregator (see
  DATA_SOURCES.md) purely as reference data, exactly like a sports news
  site publishing odds comparisons. Don't present them in a way that
  implies PitchLeague itself is a bookmaker or is facilitating real
  wagering — UI copy should read "cuotas de referencia del mercado," not
  "apuesta aquí."
- **Other EU markets**: gambling law is not harmonized at EU level — each
  member state runs its own regime (this is explicitly true even within
  the EU's single market rules, per the sources reviewed). The "no stake
  of real value" argument is the right one to lean on everywhere, but
  local counsel is needed per country before marketing there specifically.

## Why this matters for engineering, not just legal

Two decisions elsewhere in this codebase exist *because of* this analysis,
not despite it:

1. `services/predictions.py` (and its combination-bet successor) has no
   code path that accepts a real payment method — there's no Stripe
   integration, no "buy credits" endpoint, on purpose. Adding one is a
   legal decision, not just a feature request — see the ROADMAP entry.
2. Credits reset every gameweek to the league's configured budget, rather
   than being a persistent tradeable balance — this is a product decision
   (bad week ≠ elimination) that also happens to reinforce "this number
   means nothing outside the app."

## Sources consulted

- [Ley 13/2011, de regulación del juego (Spain)](https://www.g-regs.com/downloads/SPGamblingRegLaw13_2011b.pdf)
- [DGOJ — Dirección General de Ordenación del Juego](https://www.ordenacionjuego.es/en)
- [Chambers and Partners — Gaming Law 2025: Spain](https://practiceguides.chambers.com/practice-guides/gaming-law-2025/spain)
- [European Gaming — What is social casino?](https://europeangaming.eu/portal/what-is-social-casino/)
- [National Law Review — EU consumer protection guidelines on virtual currencies in video games](https://natlawreview.com/article/eu-new-european-consumer-protection-guidelines-virtual-currencies-video-games)
