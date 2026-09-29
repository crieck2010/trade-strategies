# PRE-REGISTRATION — Round 5 candidate (idea-0026)

**Strategy:** SPY turn-of-month effect
**Registered:** 2026-09-28 (America/New_York), before any validation data was pulled for this candidate.
**Trial count for DSR:** 27 — see "Multiple-testing honesty" below. This spec is frozen.
If it fails the gates, the verdict is invalidated. No parameter tuning and no
re-running with different parameters.

## One-paragraph description

Hold SPY on the last 2 and first 3 trading days of each calendar month, SHY otherwise. Daily position from closes; 5 bps per side on each switch. The flow-driven (payday/rebalance) calendar anomaly.

Long-only, no leverage. Trade window starts 2018-01-01 (warmup from 2015-01-01).

## Multiple-testing honesty (read first)

This candidate was shortlisted from the **round-5 research batch of 30 hypotheses**
(idea-0006 → idea-0038 in the idea journal; round-5 triage in
`docs/research/round5/TRIAGE.md`, full batch in `docs/research/round5/triage.json`).
27 of the 30 were structurally screened (triage.py: data-availability check,
Occam complexity score, structural return-correlation screen vs the REGCOND-1
book member at rho <= 0.60 and pairwise rho <= 0.60). The 3 remaining ideas
(idea-0007, idea-0025, idea-0030) were parked as **data-pending** — no free
keyless source exists for historical futures curves (0007, 0030) or 2017–2026
intraday 30-minute bars (0025) — and **no performance was ever observed for
them**, so they contribute zero selection trials (selection bias comes from
selecting on observed performance; data-availability screening happens before
any performance exists).

The round-5 Deflated Sharpe Ratio MUST therefore use **n_trials = 27**, with
the 27 triage full-window net-of-costs Sharpes as the trial set. Triage
admitted 10 candidates on structural grounds only — **no performance ranking
was used in triage** (triage.py computes no Sharpe, Sortino, or return before
the admission decision). Selecting among them does not reset the count.

## Why this candidate (triage result)

- Structural screens (docs/research/round5/triage.json): data-clean per the
  round-5 audit, complexity C=2, correlation
  0.277 vs REGCOND-1 (PASS)..
- Complexity breakdown: C=2: 1 indicator (calendar position) + 0 free params (2/3-day windows declared unsearched) + 1 branch + 0 filters.
- Triage admitted on structural grounds only — no performance was ranked.
  The full 6-gate walk-forward below is the first performance judgment.

## Honest flags

- ~10 switches/month = ~24 round trips/year: the Carver cost-speed gate binds (drag ~ 24*0.001/0.16 = 0.15 Sharpe units); needs gross Sharpe >= ~0.45 — stated, the gate judges.
- Calendar anomalies decay; the walk-forward folds test stability.

## Universe (frozen)

SPY, SHY — US-listed ETFs

## Benchmark (frozen)

Buy-and-hold SPY, same daily machinery, same 5 bps.

## Signal, sizing, costs (frozen)

- Signal and sizing exactly as in "One-paragraph description" above; the
  reference implementation is `docs/research/round5/triage.py` (signal
  functions), re-implemented literally in the validation harness.
- Rebalance: first trading day of each month (quarterly for short-carry-ladder:
  Jan/Apr/Jul/Oct), reading the signal at the last trading day of the prior
  period; fills at the next trading day's open (t -> t+1).
- Costs: 5 bps per side on traded notional (documented retail assumption).
- Fully invested per the target weights (SHY is the cash proxy where specified).

## Tier-1 gates (frozen, per docs/validation/GATES.md)

All six, no lowering: (1) median walk-forward OOS Sharpe > 0.3; (2) maxDD
shallower than -25%; (3) DSR > 0.8 with n_trials = 27; (4) excess return vs
the designated benchmark net of costs > 0; (5) Sortino > 0.75; (6) Carver
cost-speed limit (cost_sharpe_drag <= gross_sharpe / 3, gross_sharpe > 0).
Walk-forward geometry: 520-bar train / 130-bar test / 130-bar step / 5-bar
embargo, daily bars. Fills at the next trading day's open (t -> t+1).
Costs: 5 bps per side on traded notional (documented retail assumption).
Verdict language: validated / invalidated / discarded. If it fails any gate,
the verdict is invalidated. No parameter tuning, no re-running with different
parameters, no AI optimization after OOS.

## Process notes

- This spec is frozen at the pre-registration commit. A mid-trial framework
  change is recorded as a dated amendment appendix, never an edit.
- Complexity C is frozen here (Occam's Desk §6): no adding indicators,
  params, branches, or filters mid-trial.
- Data: yfinance daily adjusted bars via trade-data-equities
  EquitiesDataClient/YFinanceProvider (keyless), basis pre_adjusted
  (backward-ratio); no survivorship correction (stated limitation).
- Data audit (round5/audit.json): all tickers fetched; the auditor's
  coverage-gap check is miscalibrated for 11.7-year windows (all 111
  missing sessions verified as NYSE holidays); SGOV's identical-close
  runs carry real volume (pinned T-bill ETF pricing, not stale feed);
  VXX ticker history starts 2018-01-25 (Series B).

## Config hash

`297d582efe4cd35b` (spec identifier; the
validation harness records the frozen-parameter hash alongside evidence).
