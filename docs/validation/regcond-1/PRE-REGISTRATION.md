# PRE-REGISTRATION — Trial 4 candidate (1 of 1)

**Strategy:** REGCOND-1 — copper:gold regime-conditioned cross-asset tilt
**Registered:** 2026-09-26 (America/New_York), before any validation data was pulled.
**Trial count for DSR:** 2 — see "Multiple-testing honesty" below. This spec is frozen.
If it fails the gates, the verdict is KILL. No parameter tuning and no re-running
with different parameters.

## One-paragraph description

Monthly multi-asset allocation switched by the copper:gold macro regime from
`trade-macro`'s `copper_gold` indicator (preset="standard"): on the first
trading day of each month, read the regime label at the last trading day of
the prior month and set fixed weights — EXPANSION: 60% SPY / 20% CPER /
20% TLT; CONTRACTION: 20% SPY / 40% TLT / 40% GLD; NEUTRAL: 25% each of
SPY/CPER/TLT/GLD. Long-only, no leverage, no vol targeting, no
trailing-return signal — the only signal is the discrete copper:gold regime.
Fills at the next trading day's open, 5 bps per side (documented retail cost
assumption).

## Multiple-testing honesty (read first)

This candidate was shortlisted from a **screened batch of 2** (round-2
Phase B research, 2026-09-26; full batch, screening methodology, and
ranking in `docs/research/round2/SCREENING-2.md`, ideas in
`docs/research/round2/IDEAS-2.md`). Screening 2 ideas and validating the
best is **2 trials of multiple testing** whether or not the other one is
ever validated. The trial-4 Deflated Sharpe Ratio MUST therefore use
**n_trials = 2**, with the round-2 Phase B in-sample Sharpe list as the
trial set where the DSR implementation requires it. Any future additional
screening restarts this accounting from the new total. Selecting the
winner does not reset the count.

The four Track-1 ideas (SENTDIV-1, ATTN-1, EVTDRIFT-1, SENTCAP-1) were
**deferred, not screened** — no sentiment history exists before archive
deployment and none was fabricated (see
`docs/research/round2/scratch/track1_deferral.py`) — and contribute zero
trials. BASIS-1 was unscreenable (no keyless dated-future history; see
`docs/research/round2/scratch/basis_1.py`) and contributes zero trials.
The three Track-3 sketches were never run and contribute zero trials.

## Why this candidate (Phase B result)

- In-sample (2018-01-01..2026-09-25, 5 bps/side): Sharpe **+0.918** (best
  of the batch), Sortino +1.299, maxDD 23.1%, 90 trades (~10/yr),
  +135.7% total (+10.3% CAGR), 72% round-trip win rate, profit factor
  5.02. Thesis-match: yes — the regime switch sidesteps the COVID and
  2022 equity drawdowns via the defensive CONTRACTION mix and captures
  equity upside in EXPANSION months.
- Beats the classic 60/40 SPY/TLT buy-and-hold (+129.1% total, Sharpe
  +0.808) on both return and Sharpe over the same window. Trails SPY
  buy-and-hold (+227.7% total, Sharpe +0.813) on total return — the
  in-sample Sharpe edge comes from lower volatility, not higher return.
- Diversification vs killed trials: the closest cousin is the killed
  TREND-VT class (vol-targeted multi-asset time-series momentum), but
  the mechanism is structurally different — the signal is the
  copper:gold macro regime (fundamental, discrete), NOT per-asset
  trailing returns, and there is NO vol targeting. **Honest flag:** if
  "slow multi-asset allocation" itself rather than TREND-VT's signal was
  the problem, this fails for the same reason — stated, not hidden.
- Second honest flag: the CPER/GLD ratio trended down secularly over the
  sample (1,173 of 2,950 regime days labeled CONTRACTION), so the label
  is partly a secular copper-weakness tag. The CONTRACTION mix rode the
  2019–2021 bond bull and the long gold run; whether the label adds
  value when copper is in a secular uptrend is untested in-sample.
- Third honest flag: ~105 monthly rebalances = roughly 2–3 full
  expansion/contraction cycles in-sample. Thin cycle evidence; the
  walk-forward regime-split folds are the honest test.

RVBOND-1, the only other screened idea, printed Sharpe −0.493 / −34.4%
(total) in-sample — its own kill criterion fired (the real-yield residual
does not mean-revert) — so it is NOT pre-registered. No second candidate
is advanced rather than registering a known in-sample loser.

## Universe (frozen)

SPY, CPER, TLT, GLD — US-listed ETFs. Primary source: **yfinance daily
adjusted bars via `trade-data-equities` v0.x `EquitiesDataClient` /
`YFinanceProvider`** (keyless), corporate-action adjusted, basis
`pre_adjusted`. CPER is the copper proxy (JJC is delisted on yfinance);
GLD is the gold proxy. No venue fallback is needed — the source is
frozen; if yfinance bars prove discontinuous on inspection, the gap
policy below governs.

## Data

- Daily adjusted OHLCV, 2018-01-01 through 2026-09-25 (trading window),
  via trade-data-equities. Warmup history 2015-01-01..2017-12-31 is used
  ONLY to fill the trailing 252-day z-score and 200-day MA — no trading
  signals are acted on before 2018-01-01.
- Data holes: a day with no bar = hold (no signal change, no rebalance
  advance), exactly as screened.
- Benchmark: **60/40 SPY/TLT buy-and-hold, rebalanced monthly, net of
  5 bps/side** — the classic multi-asset allocation this tilt claims to
  improve on. SPY buy-and-hold reported as context, not gated.

## Signals (frozen; computed on trailing data only — no lookahead)

- Per trading day t (requires ≥63 prior ratio days for the z-score,
  which the 2015 warmup provides):
  - `ratio_t = CPER_close_t / GLD_close_t`
  - trailing: `ratio_ma200_t`, `z_252_t` (per `trade_macro.ratio.enrich_ratios`)
  - raw label: EXPANSION if `z_252_t > 1.0` AND `ratio_t > ratio_ma200_t`;
    CONTRACTION if `z_252_t < -1.0` AND `ratio_t < ratio_ma200_t`;
    else NEUTRAL
  - persisted label: raw must hold `persist_days = 5` consecutive
    sessions before the regime flips (per `trade_macro.regime.classify_regime`,
    preset="standard")
- Rebalance: on the first trading day of month M, act on the persisted
  label at the LAST trading day of month M−1. Signals are monthly only —
  no intra-month trading.
- Regime detection code is `trade-macro`'s published pipeline
  (`ratio_series` → `enrich_ratios` → `classify_regime`, preset
  `"standard"`); the preset is frozen, single-preset, no preset mining.

## Position sizing (frozen)

- Target fractions = the regime's fixed weights (long-only, sum = 1.0):
  - EXPANSION: SPY 0.60, CPER 0.20, TLT 0.20, GLD 0.00
  - CONTRACTION: SPY 0.20, CPER 0.00, TLT 0.40, GLD 0.40
  - NEUTRAL: SPY 0.25, CPER 0.25, TLT 0.25, GLD 0.25
- No leverage, no shorting, no borrow. Full investment at every rebalance.

## Costs and frictions (frozen)

- 5 bps per side on every fill (documented retail assumption for liquid
  US ETFs). No borrow (long-only).
- Fills at the next trading day's open after the rebalance signal
  (t→t+1). The signal uses only prior-month-end information, so the
  one-day fill lag is conservative, matching the screen.

## Walk-forward geometry for the validation run (frozen)

- Rolling: **104-week train / 26-week test / 26-week step**, embargo 5 days
  between train end and test start.
- No parameters are fitted (all values above are fixed), so walk-forward
  tests regime stability: report per-fold OOS Sharpe/return/maxDD and the
  concatenated OOS series, which is the gated series.
- Span: 2018-01-01..2026-09-25 (warmup history 2015+ available to every
  fold for the trailing statistics).

## Gates (trade-overfit standard preset, DSR n_trials = 2)

1. Deflated Sharpe ≥ 0.95
2. Out-of-sample Sharpe > 1.0
3. Out-of-sample max drawdown > −15% (i.e., shallower than 15%)
4. Worst vol-regime Sharpe > 0
5. Beats the 60/40 SPY/TLT benchmark net of costs
6. Sortino ≥ 1.5 (downside-adjusted return; trade-overfit standard preset)
7. Calmar ≥ 2.0 (annualized return per unit of max drawdown; trade-overfit
   standard preset)

All seven must pass → PASS (paper-trading candidate; paper itself is NOT
authorized here). Any failure → KILL, strategy marked not viable, no
registry entry, no release.

**Gate-set note (recorded at pre-registration):** a two-tier gate reform
is under Charlie's consideration. If it is adopted before the validation
run, this pre-registration gets a dated amendment (same procedure as the
5→7 amendment on the trial-3 pre-regs): the frozen specification is
unchanged, the new gate set is recorded with its date, and the amendment
is committed before any validation data is touched. No retroactive
amendments after validation starts.

## Known limitations (frozen with the spec)

- Secular-trend contamination: the copper:gold label is partly a
  secular-copper-weakness tag over this sample; the CONTRACTION mix's
  bond/gold tailwind may not repeat. Untested in a secular copper
  uptrend.
- Label lag: 252-day z + 200-day MA + 5-day persistence means growth
  shocks hit equities before the label flips; the monthly cadence
  prices the lag in, but a fast regime change can be missed for a full
  month.
- Thin cycle count (~2–3 full cycles in-sample); the walk-forward folds
  must show the premium surviving across folds, not riding one cycle.
- CPER/GLD are ETF proxies with expense drag and tracking error vs the
  metals (trade-macro documents the futures alternative, HG/GC, with its
  own roll-effect caveats); a validation-grade version may revisit the
  source choice, but the choice is frozen here.
- Trails SPY buy-and-hold on total return in-sample; the claim is
  risk-adjusted, not absolute, outperformance.
- 5 bps/side is an assumption; validation must include a
  cost-sensitivity note (2/5/10 bps).
