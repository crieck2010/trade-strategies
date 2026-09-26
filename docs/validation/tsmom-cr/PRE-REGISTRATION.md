# PRE-REGISTRATION — Trial 3 candidate B (of 2)

**Strategy:** TSMOM-CR — daily time-series momentum on BTC/ETH (long/flat)
**Registered:** 2026-09-26 (America/New_York), before any validation data was pulled.
**Trial count for DSR:** 7 — see "Multiple-testing honesty" below. This spec is frozen.
If it fails the gates, the verdict is KILL. No parameter tuning and no re-running
with different parameters.

## One-paragraph description

Daily time-series momentum on BTC/USD and ETH/USD spot: each day, go long a name
if its close exceeds the trailing 90-day high (prior 90 bars, excluding today) OR
its close exceeds its close 50 days ago; otherwise flat. Long/flat only — no
shorts, no stops; the exit is the day after the signal fails. Each name is sized
to a 10% annualized volatility target — notional_i = min(0.10 / σ_ann_i, 1.0) ×
equity, σ from trailing 60 daily returns × √365 — with sizing refreshed monthly
and on fresh entries (not daily, to avoid churn). Signals on the daily close,
fills at the next day's open, 25 bps per side all-in (documented retail cost
assumption).

## Multiple-testing honesty (read first)

This candidate was shortlisted from a **screened batch of 7** (Phase B research,
2026-09-26; full batch, screening methodology, and ranking in
`docs/research/SCREENING.md`, ideas in `docs/research/IDEAS.md`). Screening 7
ideas and validating the best is **7 trials of multiple testing** whether or not
the other 5 are ever validated. The trial-3 Deflated Sharpe Ratio MUST therefore
use **n_trials = 7**, with the Phase B in-sample Sharpe list as the trial set where
the DSR implementation requires it. Any future additional screening restarts this
accounting from the new total. Selecting the winner does not reset the count.

## Why this candidate (Phase B result)

- In-sample (2019-09-17..2026-09-25, 25 bps/side): Sharpe **+0.798** (best of the
  batch), maxDD 20.1%, 166 trades, +104.4% total. Thesis-match: yes.
- Diversification vs killed trials: trial 2 (MR-5M) was 5-minute *mean reversion*,
  long/short scalping; this is daily *trend*, long/flat — different mechanism,
  different horizon, different trade profile. **Honest flag:** it shares trial 2's
  instruments (BTC/ETH). If crypto market structure rather than strategy class
  was trial 2's problem, this fails for the same reason — stated, not hidden.
- Second honest flag: only 2 names over one secular crypto bull market is the
  narrowest evidence in the batch (166 trades). The gates — especially DSR with
  n_trials=7 — are the judge of whether that evidence suffices.

## Universe (frozen)

BTC/USD and ETH/USD spot. Primary venue: **Binance.US** public daily klines via
`trade-data-crypto` v0.2.0 `BinanceUSPublicProvider` (keyless). Fallback, decided
now before any data pull: **Kraken** `KrakenPublicProvider` daily, used ONLY if
Binance.US daily history proves discontinuous on inspection (trial 2 documented a
~17-month hole in Binance.US *5-minute* klines; daily may differ — the venue is
chosen on history completeness, checked once, then frozen). No venue-shopping
after results are seen.

## Data

- Daily OHLCV, 2019-09-17 through 2026-09-25 (Binance.US daily history start),
  via trade-data-crypto. Spot only, no leverage, no funding rates.
- Data holes: a day with no bar = hold (no signal change), exactly as screened.
- Benchmark: BTC buy-and-hold over the same span, net of 25 bps/side entry+exit.

## Signals (frozen; computed on bar t's close, fills at bar t+1's open — no lookahead)

- Per name, per day t (requires 91 prior bars of warmup):
  - `breakout = close[t] > max(high[t-90 .. t-1])` (90-day Donchian high of the
    *prior* 90 bars, excluding t)
  - `mom50 = close[t] > close[t-50]`
  - **Long** if `breakout OR mom50`; **flat** otherwise.
- Exit is the first day the signal is false; the fill is the next day's open.
  No stop-loss, no profit target — the signal IS the exit.
- Re-entry requires a fresh true signal on a later day.

## Position sizing (frozen)

- Per name: `notional_i = min(0.10 / σ_ann_i, 1.0) × equity(t)`,
  `σ_ann_i = stdev(daily returns[t-60..t-1]) × √365`.
- Sizing refreshed on calendar-month boundaries and on fresh entries only
  (not daily — the monthly refresh is part of the spec; daily resizing caused
  ~2,100 churn trades in an early screening variant and is explicitly excluded).
- Long/flat only: no borrow, no margin.

## Costs and frictions (frozen)

- 25 bps per side all-in on every fill (documented retail assumption: sits between
  Binance.US's ~2 bps and Kraken's ~80 bps entry taker tiers — conservative for
  an unspecified retail venue; the venue choice above does not change this number).
- Fills at next day's open. No lookahead. 24/7 market: weekends and holidays are
  trading days; no session handling needed.

## Walk-forward geometry for the validation run (frozen)

- Rolling: **104-week train / 26-week test / 26-week step**, embargo 5 days
  between train end and test start.
- No parameters are fitted (all values above are fixed), so walk-forward tests
  regime stability: report per-fold OOS Sharpe/return/maxDD and the concatenated
  OOS series, which is the gated series.
- Span: 2019-09-17..2026-09-25.

## Gates (trade-overfit standard preset, DSR n_trials = 7)

1. Deflated Sharpe ≥ 0.95
2. Out-of-sample Sharpe > 1.0
3. Out-of-sample max drawdown > −15% (i.e., shallower than 15%)
4. Worst vol-regime Sharpe > 0
5. Beats BTC buy-and-hold net of costs

All five must pass → PASS (paper-trading candidate; paper itself is NOT
authorized here). Any failure → KILL, strategy marked not viable, no registry
entry, no release. (Note: trial 2's lesson applies — beating a deeply negative
benchmark is necessary but not sufficient evidence of edge; the Sharpe and DSR
gates are the binding constraints.)

## Known limitations (frozen with the spec)

- Two names = concentration risk; a single-asset drawdown is a portfolio drawdown.
- The in-sample window is one secular crypto bull market with two violent
  interruptions; the walk-forward folds are the honest test of whether the
  premium survives bear phases.
- 25 bps/side is an assumption, not a measurement; retail taker fees vary by
  venue and tier — validation must include a cost-sensitivity note (10/25/50 bps).
- Daily bars miss intrabar dynamics; the t+1-open fill convention can be
  optimistic on violent gap days — documented, conservative direction unknown.
- Crypto trades 24/7/365: the √365 annualization and calendar-day folds are
  deliberate (not √252); any annualization mismatch vs the equity gates must be
  normalized in the validation harness and documented.
