# PRE-REGISTRATION — Trial 3 candidate C (of 3)

**Strategy:** XMOM-1 — cross-sectional momentum 12-1, dollar-neutral (monthly)
**Registered:** 2026-09-26 (America/New_York), before any validation data was pulled.
**Trial count for DSR:** 7 — see "Multiple-testing honesty" below. This spec is frozen.
If it fails the gates, the verdict is KILL. No parameter tuning and no re-running
with different parameters.

## One-paragraph description

Classic Jegadeesh-Titman cross-sectional momentum on liquid US large caps: on the
first trading day of each calendar month, rank eligible names by trailing
252-trading-day total return skipping the most recent 21 trading days; go long
the top decile and short the bottom decile, equal-weighted within each leg, 50%
gross per leg (dollar-neutral, gross 1.0), hold one month, rebalance in full.
Signals on the rebalance date's close; fills on the next bar (t→t+1, in-engine).
5 bps per side plus 50 bps/year borrow on short notional, in-engine.

## Multiple-testing honesty (read first)

This candidate was shortlisted from a **screened batch of 7** (Phase B research,
2026-09-26; full batch, screening methodology, and ranking in
`docs/research/SCREENING.md`, ideas in `docs/research/IDEAS.md`). Screening 7
ideas and validating the best is **7 trials of multiple testing** whether or not
the other candidates are ever validated. The trial-3 Deflated Sharpe Ratio MUST
therefore use **n_trials = 7**, with the Phase B in-sample Sharpe list as the
trial set where the DSR implementation requires it. Any future additional
screening restarts this accounting from the new total. Selecting from the batch
does not reset the count. (XMOM-1 was idea #3 of the 7 by in-sample Sharpe, so
validating it adds no new trials beyond the 7 already counted.)

## Why this candidate (Phase B result)

- In-sample (2019-01-01..2026-09-25, 5 bps/side + 50 bps/yr borrow): Sharpe
  **+0.413**, maxDD **25.3%**, 1,275 trades, +61.7% total. Thesis-match: yes —
  textbook momentum payoff shape (steady grind, crash-profile drawdown).
- Diversification vs killed trials: trial 1 (DON-20/10-ATR) was single-asset daily
  breakout; trial 2 (MR-5M) was single-asset 5-minute mean reversion. XMOM-1 is
  cross-sectional, monthly, dollar-neutral — a different construction. Honest
  flags: (a) it is still momentum-family, so it shares trial 1's exposure to
  trend failure — the diversification is structural (cross-sectional +
  market-neutral), not categorical; (b) the screening universe is today's
  large-cap constituents (survivorship bias, likely flattering — documented,
  not hidden); (c) 25.3% in-sample maxDD is the classic momentum-crash profile
  and already exceeds the 15% gate — the walk-forward OOS drawdown is the
  binding question.

## Universe (frozen)

The committed ticker list `docs/research/evidence/universe.txt` (271 current
US large-cap tickers, committed in Phase B). On each rebalance date, a ticker
is eligible iff it has daily bars on ≥95% of the SPY trading-day grid over
2015-01-01..2026-09-25. No substitutions, no additions. If a ticker lacks a
bar on the rebalance date itself, it is ineligible that month (no signal
possible — same rule as screening). Survivorship bias is a known, documented
limitation (see below), not a defect discovered later.

## Data

- Daily OHLCV (split- and dividend-adjusted closes), 2015-01-01 through
  2026-09-25, via yfinance (`auto_adjust=True`), pulled through
  `trade-data-equities`. 2015-01-01..2018-12-31 is formation warmup only;
  trading begins 2019-01-01 (matches the screening window).
- Benchmark: US 3-month T-bill total return, from ^IRX daily closes via
  trade-data-equities, converted mechanically: rf_daily = y/100/252 per
  trading day (simple interest, documented). ^IRX missing on a date → carry
  the last observation forward (documented). If ^IRX cannot be fetched at
  all, benchmark = 0% cash (mechanical fallback, decided before results,
  documented in the report). Rationale: the strategy is dollar-neutral, so
  the trivial alternative is cash — the academically standard hurdle for
  market-neutral L/S.

## Signals (frozen; computed on the rebalance date, fills next bar — no lookahead)

- Rebalance dates: the first trading day of each calendar month present in the
  SPY date grid, from 2019-01-01 onward.
- On rebalance date t, for each eligible ticker: formation return
  `R = close[t-21] / close[t-273] − 1`, i.e. trailing 252-trading-day total
  return skipping the most recent 21 trading days (exactly
  `trailing_return(hist, 252, skip=21)` from the screening implementation).
  Tickers with insufficient history are unscored.
- Rank scored tickers by R ascending. `n = max(1, floor(0.10 × #scored))`.
  Long the top n, short the bottom n.
- Weights: `+0.50/n` per long name, `−0.50/n` per short name (fraction of
  equity). Dollar-neutral, gross 1.0.
- If either leg is empty (early history), hold current positions — no trade.
- Positions held until the next rebalance; no intra-month trading, no stops,
  no turnover control.

## Position sizing (frozen)

- As above: equal-weighted within each leg, 50% gross per leg. No vol
  targeting, no leverage beyond gross 1.0. Rebalance trades bring each name
  to its new target weight in full (turnover is part of the cost accounting).

## Costs and frictions (frozen)

- Commission: 5 bps per side on every fill, in-engine (`PercentCommission`).
- Short borrow: 50 bps annualized on short notional, in-engine
  (`borrow_cost_annual_bps=50.0`; large-cap general-collateral realistic).
- Fills on the next bar after the signal bar (t→t+1,
  `SimulatedExecutionHandler`). No lookahead.

## Walk-forward geometry for the validation run (frozen)

- Rolling: **60-month train / 12-month test / 12-month step**, embargo 21
  trading days between train end and test start.
- No parameters are fitted (all values above are fixed), so walk-forward tests
  regime stability, not tuning: report per-fold OOS Sharpe/return/maxDD and the
  concatenated OOS series, which is the gated series.
- Span: 2015-01-01..2026-09-25 (test folds begin once 60 months of history
  exist: first test window 2020-01..2020-12 after embargo; final window
  2026-01..2026-09, partial, documented).
- Rebalance months falling inside the embargo gap belong to neither fold's
  trading (documented).

## Gates (trade-overfit standard preset, DSR n_trials = 7)

1. Deflated Sharpe ≥ 0.95
2. Out-of-sample Sharpe > 1.0
3. Out-of-sample max drawdown > −15% (i.e., shallower than 15%)
4. Worst vol-regime Sharpe > 0
5. Beats the T-bill benchmark net of costs
6. Sortino ≥ 1.5 (downside-adjusted return; trade-overfit standard preset)
7. Calmar ≥ 2.0 (annualized return per unit of max drawdown; trade-overfit
   standard preset)

All seven must pass → PASS (paper-trading candidate; paper itself is NOT
authorized here). Any failure → KILL, strategy marked not viable, no registry
entry, no release.

## Known limitations (frozen with the spec)

- Survivorship bias: the universe is today's constituents; delisted names are
  absent, which flatters momentum (losers that died are missing from the short
  leg's history). Stated in Phase B, restated here — the gates judge whether
  the premium survives it, not whether the bias exists.
- Momentum crashes: the 25.3% in-sample maxDD is the known 2009-style payoff
  shape; a crash inside the OOS window likely kills the strategy at gate 3.
- Borrow at 50 bps is a GC assumption; hard-to-borrow names in the short leg
  cost more — validation includes a borrow-sensitivity note (0/50/200 bps).
- Monthly formation on daily data; the t→t+1 fill on rebalance months with
  violent reversals is the known whipsaw enemy (stated in Phase A).
- No turnover control: full monthly reconstitution maximizes cost drag; the
  1,275 screening trades are the evidence this is affordable, not optimal.
