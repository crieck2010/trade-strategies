# Trial 4 validation report — REGCOND-1

**Verdict: KILL** (4 of 7 official gates pass; the binding failures are the
drawdown gate and the two downside-risk gates).
**Spec:** `PRE-REGISTRATION.md`, frozen at commit `ca2aa4e` (2026-09-26),
before any validation data was pulled. Implemented literally; no parameter
tuning; one clean run.
**Date run:** 2026-09-27. **Evidence:** `evidence.json` (this directory).

## Official 7-gate table (trade-overfit standard preset, DSR n_trials = 2)

| Gate | Value | Threshold | Result |
|---|---|---|---|
| Deflated Sharpe (n=2) | 1.000 | ≥ 0.95 | PASS |
| Median OOS Sharpe | +1.385 | > 1.0 | PASS |
| Max drawdown (OOS) | −23.0% | > −15% | **FAIL** |
| Worst-regime Sharpe | +0.44 | > 0 | PASS |
| Excess vs 60/40 SPY/TLT, net | +4.91%/yr | > 0 | PASS |
| Sortino | 1.41 | ≥ 1.5 | **FAIL** |
| Calmar | 0.52 | ≥ 2.0 | **FAIL** |

## What the numbers say

- Walk-forward 104w/26w/26w, 5-day embargo, 13 folds, 1,670 concatenated
  OOS bars (2018-01-01..2026-09-25 trading window; 2015–2017 warmup).
- OOS: +12.0%/yr annualized, Sharpe 0.99, Sortino 1.41, profit factor 1.18,
  win rate 56%, vol 12.2%.
- The 60/40 SPY/TLT benchmark (same monthly t+1-open machinery, 5 bps):
  +7.1%/yr, Sharpe 0.59, maxDD −27.5%. The strategy beats it by +4.9%/yr
  with a *shallower* drawdown — but the absolute −15% gate is not relative,
  and −23.0% fails it.
- DSR is a clean 1.000: OOS Sharpe_hat 0.99 vs expected best-of-2 under
  the null 0.52. Statistically this is real edge, not luck. The kill is
  economic (risk), not statistical.
- The −23.0% drawdown ran **2022-03-04 → 2022-10-20**. The label correctly
  read CONTRACTION through it (20% SPY / 40% TLT / 40% GLD) — but 2022 was
  the bond crash, and the "defensive" mix's 40% TLT allocation (TLT ≈ −30%
  that year) was the pain source. The regime signal worked; the
  CONTRACTION *mix* carried duration risk the gate doesn't forgive.
- COVID March 2020: label read CONTRACTION — the defensive mix sidestepped
  the crash, thesis-match confirmed for that episode.
- Fold Sharpes: +2.25, +1.55, +1.74, +0.47, **−1.80** (2022 fold),
  +0.28, +0.30, +1.92, +2.38, −0.25, +2.79, +1.39, −0.06. Median +1.39.
  Ten of thirteen folds positive; the damage is concentrated in one fold.
- Label mix over the OOS window: 299 EXPANSION / 953 NEUTRAL / 943
  CONTRACTION days; 105 monthly rebalances; turnover ≈ $32 per $1 of
  capital over the full window (monthly cadence keeps costs tiny —
  see sensitivity).

## Two-tier supplementary (NOT the official verdict; no pre-reg amendment)

Computed so a future gate reform needs no re-run:

| Check | Value | Tier-1 bar | Result |
|---|---|---|---|
| OOS Sharpe | +1.385 | > 0.3 | pass |
| Max drawdown | −23.0% | > −25% | pass |
| DSR | 1.000 | ≥ 0.8 | pass |
| Beats benchmark net | +4.91%/yr | > 0 | pass |
| Sortino | 1.41 | ≥ 0.75 | pass |

**Supplementary Tier-1: PASS (5/5).** Under the proposed two-tier system
this strategy would enter the allocator's candidate pool (subject to
portfolio-level gates). Stated as fact, not advocacy — the official
verdict above is KILL under the frozen 7-gate set.

## Cost sensitivity (official run is 5 bps/side)

| Cost | Ann. return | Sharpe | MaxDD |
|---|---|---|---|
| 2 bps | 12.11% | 0.996 | −22.9% |
| **5 bps (official)** | **12.03%** | **0.990** | **−23.0%** |
| 10 bps | 11.91% | 0.981 | −23.0% |

Monthly rebalancing of liquid ETFs: costs move the needle by ~±0.1%/yr.
Verdict is cost-robust.

## Honest flags (frozen in the pre-reg, plus what validation revealed)

1. **Secular-contamination flag CONFIRMED INSTRUCTIVE:** the CONTRACTION
   mix rode the 2019–2021 bond bull (in-sample thesis-match) and then ate
   the 2022 bond crash through the same 40% TLT allocation. The label
   isn't just a secular-copper-weakness tag — it correctly flagged both
   2020 and 2022 as stress — but the defensive mix's duration exposure is
   the strategy's structural weak point, and 2022 is the single fold that
   kills the drawdown gate.
2. **Label lag:** 252-day z + 200-day MA + 5-day persistence + monthly
   cadence. The label was NEUTRAL entering 2022 (2021-12-31) and flipped
   CONTRACTION by mid-2022 — the March–June 2022 damage was taken partly
   in NEUTRAL/transition mixes.
3. **Thin cycles:** ~2–3 full expansion/contraction cycles in-sample; the
   walk-forward shows the premium surviving 10 of 13 folds, with the 2022
   regime as the counterexample.
4. **Cousinship with killed TREND-VT:** stated in the pre-reg. The
   mechanism here is a discrete fundamental regime, not trailing returns
   and no vol targeting — and unlike TREND-VT (0/7, deeply negative),
   REGCOND-1 is statistically real (DSR 1.0) and beats its benchmark by
   +4.9%/yr. The failure is the risk bar, not the edge.

## Methodology notes

- Data: SPY/CPER/TLT/GLD daily adjusted bars 2015-01-01..2026-09-25 via
  trade-data-equities `YFinanceProvider` (adjusted=True). 2,950 bars each,
  **zero symbol-hole-days** — the union grid needed no forward-fills.
- Regime: trade-macro `ratio_series → enrich_ratios → classify_regime`
  (preset="standard"), computed once on the full 2015+ series. Every label
  at day t uses only data ≤ t (trailing z_252/ma200, persistence from
  NEUTRAL); the 2015–2017 warmup lets persistence converge before the
  2018-01-01 trading start. Per-fold recomputation would give identical
  labels — this is what a live implementation would have produced.
- Weeks are trading days (train 520 / test 130 / step 130 / embargo 5).
- Fills at next-day open, t→t+1, 5 bps/side on traded notional, charged
  against portfolio value at the fill; fully invested, long-only.
- Benchmark: 60/40 SPY/TLT, same monthly t+1-open machinery, 5 bps.
- DSR trial set = round-2 Phase B in-sample Sharpes [0.918, −0.493]
  (REGCOND-1, RVBOND-1), n_trials = 2, per the pre-reg's honesty section.
- **Harness bugs found and fixed before evidence was committed** (no
  invalid run; nothing was committed with either bug):
  (a) the fill-day return was computed with post-trade shares on both
  sides of the ratio, making costs vanish — verified by the
  non-monotonic cost check, fixed so costs deduct from portfolio value;
  (b) the first trading month (Jan 2018) was skipped because the
  prior-month map was built from the trading window only — rebuilt on the
  full grid so January reads the 2017-12-29 warmup label (spec-literal).
  Neither fix changed any gated number (test windows start at bar 525),
  which is itself a consistency check.
- No invalid runs. No releases, no registry entries, no agent
  registration — per trade-lifecycle, REGCOND-1 is marked not viable
  under the frozen gate set.

## Files

- `PRE-REGISTRATION.md` — frozen spec (commit `ca2aa4e`)
- `run_validation.py` — the harness (documents decisions D1–D7)
- `evidence.json` — full numbers: gate tables, 13-fold table, OOS and
  benchmark summaries, DSR detail, regime report, cost sensitivity
- `report.md` — this file
