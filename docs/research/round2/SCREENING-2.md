# Phase B — Strategy Screening, round 2 (in-sample, 2026-09-26)

Screening pass over the Track-2 ideas in
`docs/research/round2/IDEAS-2.md` / `phase-a2-ideas.json`. Same design as
round 1: **screening is not validation.** In-sample backtests, loose, nonzero
costs. Winners still have to survive pre-registration, embargo, and the
trial-4 DSR (with n_screened trials) before any paper use. Trial 4
(validation) is NOT authorized in this phase — it stops at pre-registration.

## How it was run

* One backtest per screenable idea, 2018-01-01..2026-09-25 (t→t+1 fills,
  no lookahead), through `trade-backtest`'s `BacktestEngine` (v0.2.0) and
  the `TargetStrategy`/`TargetsSizer` harness, with explicit
  `adjustment_basis="pre_adjusted"`.
* Data: Charlie's stack only — `trade-data-equities`/yfinance daily
  adjusted ETF bars (GLD, TLT, TIP, SPY, CPER, 2015-01-01..2026-09-25;
  pre-2018 data used as warmup only, never traded). `trade-macro`
  copper:gold regime engine (`ratio_series` → `enrich_ratios` →
  `classify_regime`, preset="standard") for REGCOND-1.
* Costs: 5 bps/side equities & ETFs; 50 bps/yr borrow on shorts
  (RVBOND-1 only — REGCOND-1 is long-only).
* Implementations live under `docs/research/round2/scratch/` and are
  labeled **RESEARCH SCRATCH — NOT a strategy module**. Nothing was added
  to `src/`. Simplifications are recorded per idea below and in each
  scratch file's `SIMPLIFICATIONS` block.
* Machine-readable evidence:
  `docs/research/round2/evidence/screening2_results.json` (per-idea params,
  metrics, assumptions, timestamps). The 5-ETF panel CSVs live under
  `docs/research/round2/evidence/panel/` (local; same convention as round 1).

## Ranking (primary: in-sample Sharpe)

| Rank | Idea | Sharpe | Sortino | MaxDD | Trades | Total ret | CAGR | Window |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | REGCOND-1 | **+0.918** | +1.299 | 0.231 | 90 | +135.7% | +10.3% | 2018-01-01..2026-09-25 |
| 2 | RVBOND-1 | **−0.493** | −0.695 | 0.403 | 126 | −34.4% | −4.7% | 2018-01-01..2026-09-25 |

**n_screened = 2.** Only ideas actually screened count. Track-1's four
ideas were NEVER screened (deferred — see below), BASIS-1 was
unscreenable, and the three Track-3 sketches were never run. No
placeholder trials are entered for any of them. This number is the future
trial-4 DSR trial count.

## Per-idea verdicts

### REGCOND-1 — SCREENED, rank 1 (Sharpe +0.918)
Copper:gold regime-conditioned allocation (trade-macro `copper:gold`
indicator, CPER/GLD proxies, preset="standard"): rebalance monthly on the
regime label at the prior month-end — EXPANSION → 60% SPY / 20% CPER /
20% TLT; CONTRACTION → 20% SPY / 40% TLT / 40% GLD; NEUTRAL → 25% each.
+135.7% total (+10.3% CAGR) with 23.1% maxDD over 8.75y, 90 trades
(~10/yr), 72% win rate on round trips, profit factor 5.02.
Thesis match: **yes** — the regime switch avoids the worst equity
drawdowns (COVID, 2022) by rotating into the defensive
TLT/GLD-heavy CONTRACTION mix, and EXPANSION months (60% SPY) capture
equity upside.

Context benchmarks, same window (diagnostic, not gated):
- SPY buy-and-hold: +227.7% total, Sharpe +0.813 — the regime tilt
  underperforms SPY on total return; its Sharpe edge (0.918 vs 0.813)
  comes from lower volatility, not higher return.
- 60/40 SPY/TLT buy-and-hold: +129.1% total, Sharpe +0.808 — REGCOND-1
  beats the classic multi-asset allocation on both return and Sharpe.
- Per active-regime day: EXPANSION days (n=292) Sharpe +2.26;
  CONTRACTION days (n=918) Sharpe +1.27; NEUTRAL days (n=984) Sharpe
  +0.26 — the value concentrates in the two directional regimes.

**Honest flags** (recorded for the pre-reg):
1. The CPER/GLD ratio trended DOWN secularly over 2015–2026: 1,173 of
   2,950 regime days are labeled CONTRACTION. The label is partly a
   secular copper-weakness tag, not purely a business-cycle signal; the
   CONTRACTION mix rode the 2019–2021 bond bull and the long gold run.
   Validation must test whether the label still adds value when copper
   is in a secular uptrend.
2. Regime labels lag by construction (252-day z, 200-day MA, 5-session
   persistence) — a growth shock hits equities before the label flips.
   This is the thesis's own kill criterion; the screen does not disprove
   it, it only prices the lag in-sample.
3. Thin cycle count: ~105 monthly rebalances, roughly 2–3 full
   expansion/contraction cycles in-sample. The walk-forward regime-split
   is the honest test.
4. Closest cousin: the killed TREND-VT class (vol-targeted multi-asset
   time-series momentum). Structural difference is real — the signal is
   the copper:gold macro regime (fundamental, discrete), NOT per-asset
   trailing returns, and there is NO vol targeting — but if
   "multi-asset slow allocation" itself was TREND-VT's problem rather
   than its signal, REGCOND-1 fails for the same reason. Stated, not
   hidden.

### RVBOND-1 — SCREENED, rank 2 (Sharpe −0.493). Loser.
GLD/TLT vs TIP-implied real-yield fair value: 90-day OLS of log(GLD/TLT)
on log(TIP), coefficients + residual mean/std frozen monthly (fit on the
prior month-end, no lookahead); |z| > 1.5 entries, exit at z=0 or a
30-trading-day stop; dollar-neutral 50/50 legs; 5 bps/side + 50 bps/yr
borrow. −34.4% total with 40.3% maxDD, 126 trades (~14/yr, inside the
thesis's 12–36/yr band). Thesis match: **no**.
The residual does not mean-revert profitably — exactly the thesis's own
kill criterion fired: *"the residual has a unit root (relationship breaks
in real-yield regime shifts)"*. The 2020–2022 real-yield regime shift
broke the GLD/TLT-vs-TIP relationship and the spread never came back
within the sample. No parameter rescue attempted; the idea is dead on
this evidence.

## Not screened (do NOT count toward n_screened)

* **SENTDIV-1, ATTN-1, EVTDRIFT-1, SENTCAP-1 — DEFERRED, not screened.**
  The Phase-0 archive backfill investigation found no keyless historical
  text source (GDELT's query API rate-refuses programmatic access; bulk
  files aren't ticker-addressable): **no sentiment history exists before
  deployment, and none was fabricated.** Screening these theses on
  price-derived proxies (volatility for "attention", returns for "tone")
  would test price signals while claiming to test sentiment — dishonest,
  and it cannot measure the incremental value of sentiment over price,
  which is every Track-1 thesis's kill criterion. The archive accumulates
  from deployment forward; Track-1 screening happens once real history
  exists (the sentiment contract requires ≥2y of ticker-day observations).
  See `scratch/track1_deferral.py`. DSR accounting: these four contribute
  zero trials.
* **BASIS-1 — UNSCREENABLE.** Kraken Futures lists only two quarterly BTC
  contracts; the 3-month contract FI_XBTUSD_261030 opened 2026-09-25
  (~1 day of history) and expired contracts are delisted with no keyless
  archive. A 90-day rolling baseline of constant-tenor 3m basis cannot be
  constructed — the baseline the thesis requires. Screening the perpetual
  funding basis instead would mislabel the thesis. See
  `scratch/basis_1.py`. Would become screenable with a keyless multi-year
  dated-future history (e.g., a free archive of expired quarterly series);
  no data purchase authorized in this phase.
* **VOLCAL-1, VOLSKEW-1, VOLDISP-1 — SKETCHES ONLY.** No historical
  options-chain data in the stack; design sketches in IDEAS-2.md. Not
  run, not counted.

## Stack gaps found (round 2)

* No historical sentiment archive (Track-1 deferred) — same gap as round 1.
* No historical options chains / IV surface (Track-3 sketches) — same gap.
* No keyless dated-crypto-future history (BASIS-1 unscreenable) — new gap.
* JJC (copper ETN) is delisted on yfinance; CPER used as the copper proxy.
* trade-macro's copper:gold pipeline works cleanly on ETF proxies
  (CPER/GLD); HG/GC futures would be purer but carry roll effects.

## Combined judgment

One candidate advances: **REGCOND-1** — best in-sample risk-adjusted
return of the batch, thesis-match yes, structural distance from all five
killed classes documented, beats 60/40 on both return and Sharpe. Its
honest flags are recorded above and frozen into the pre-registration.
RVBOND-1 is a clean loser (own kill criterion fired). Track-1 waits on
real archive history; BASIS-1 waits on a dated-future history source;
Track-3 waits on options-chain data or Charlie's call on the spend.

**n_screened = 2** → the trial-4 DSR trial count.
