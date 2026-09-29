#!/usr/bin/env python3
"""Generate the 10 round-5 pre-registrations (frozen specs)."""
import datetime as dt
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
VAL = os.path.expanduser("~/workspace/trade-suite/trade-strategies/docs/validation")
TODAY = "2026-09-28"

COMMON_DSR = """## Multiple-testing honesty (read first)

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
the admission decision). Selecting among them does not reset the count."""

COMMON_GATES = """## Tier-1 gates (frozen, per docs/validation/GATES.md)

All six, no lowering: (1) median walk-forward OOS Sharpe > 0.3; (2) maxDD
shallower than -25%; (3) DSR > 0.8 with n_trials = 27; (4) excess return vs
the designated benchmark net of costs > 0; (5) Sortino > 0.75; (6) Carver
cost-speed limit (cost_sharpe_drag <= gross_sharpe / 3, gross_sharpe > 0).
Walk-forward geometry: 520-bar train / 130-bar test / 130-bar step / 5-bar
embargo, daily bars. Fills at the next trading day's open (t -> t+1).
Costs: 5 bps per side on traded notional (documented retail assumption).
Verdict language: validated / invalidated / discarded. If it fails any gate,
the verdict is invalidated. No parameter tuning, no re-running with different
parameters, no AI optimization after OOS."""

COMMON_PROC = """## Process notes

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
  VXX ticker history starts 2018-01-25 (Series B)."""

CANDS = {
 "hyg-lqd-spread": dict(
   idea="idea-0008", title="HYG/LQD spread-percentile rotation",
   desc=("Each month, hold HYG when the HYG/LQD price-ratio percentile vs its "
         "trailing 2-year history exceeds 0.5, else hold LQD. The price ratio "
         "is the implementable proxy for the hypothesis's yield-spread "
         "percentile (no free keyless corporate-bond yield history exists); "
         "the proxy direction is declared here: a high HYG/LQD ratio means "
         "the market prices high-yield rich vs investment-grade, i.e. carry "
         "is judged adequate compensation for default risk."),
   universe="HYG, LQD — US-listed ETFs",
   benchmark="Buy-and-hold LQD, same monthly t+1-open machinery, same 5 bps.",
   complexity="C=2: 1 indicator (HYG/LQD ratio percentile) + 0 free params "
              "(0.5 median and 2y/504-bar window declared unsearched round numbers) "
              "+ 1 regime branch (HYG|LQD) + 0 filters.",
   flags=("- The price-ratio proxy is NOT a yield spread; if the edge (if any) "
          "lives in actual spread levels, this proxy may not capture it — "
          "stated, not hidden.\n"
          "- Credit risk: HYG can gap on default waves; the monthly rebalance "
          "cannot exit intraday."),
   rho="0.550 vs REGCOND-1 (structural screen PASS, <= 0.60)."),
 "tlt-shy-slope": dict(
   idea="idea-0009", title="TLT/SHY slope timing",
   desc=("Each month, hold TLT when the TLT/SHY ratio's trailing 63-day "
         "relative carry (ratio[t]/ratio[t-63]) exceeds its trailing 2-year "
         "median, else hold SHY. A rising long/short Treasury ratio proxies "
         "a steepening curve regime favoring duration."),
   universe="TLT, SHY — US-listed ETFs",
   benchmark="Buy-and-hold IEF, same monthly t+1-open machinery, same 5 bps.",
   complexity="C=2: 1 indicator (TLT/SHY relative carry vs median) + 0 free params "
              "(63d, 2y median declared unsearched) + 1 branch + 0 filters.",
   flags=("- Round 4 invalidated two slow rates-timing ideas (idea-0020, idea-0006) "
          "in the 2022 hiking cycle; this is a different signal (curve slope, "
          "not real-yield level or carry rank) but the same graveyard — stated.\n"
          "- Benchmark is IEF (per the hypothesis claim), not TLT."),
   rho="0.394 vs REGCOND-1 (PASS)."),
 "short-carry-ladder": dict(
   idea="idea-0010", title="Short-duration carry-per-duration ladder",
   desc=("Each quarter, hold whichever of SGOV, SHY, IEF has the highest "
         "trailing 63-day return per unit of duration, with declared duration "
         "proxies SGOV=0.25 / SHY=2.0 / IEF=7.5 (round numbers, unsearched). "
         "Rebalance on the first trading day of Jan/Apr/Jul/Oct, t+1 open, 5 bps."),
   universe="SGOV, SHY, IEF — US-listed ETFs",
   benchmark="Buy-and-hold SHY, same quarterly t+1-open machinery, same 5 bps.",
   complexity="C=3: 1 indicator (carry-per-duration rank) + 0 free params "
              "(durations and 63d window declared unsearched) + 2 branches "
              "(3-asset rotation) + 0 filters.",
   flags=("- SGOV incepted 2020-05-26: the OOS window starts 2020-09-01 "
          "(63d carry warmup), giving ~6 years / ~6 walk-forward folds — "
          "thinner evidence than the other candidates, stated.\n"
          "- Round-4 idea-0006 (monthly top-1 carry among SHY/IEF/TLT) was "
          "invalidated; this is short-duration-only and quarterly, but the "
          "carry-rotation family is on notice — stated."),
   rho="0.023 vs REGCOND-1 (PASS).",
   tstart="2020-09-01"),
 "svxy-harvest": dict(
   idea="idea-0015", title="SVXY contango harvest on VIX percentile",
   desc=("Each month, hold SVXY (inverse VIX-futures ETN) when the VIX close "
         "is at or below its trailing 1-year 20th percentile (contango "
         "likely, vol risk premium harvestable), else hold SHY. T+1 open, 5 bps."),
   universe="SVXY, SHY; signal from ^VIX — US-listed / CBOE index via yfinance",
   benchmark="Buy-and-hold SHY, same monthly t+1-open machinery, same 5 bps.",
   complexity="C=2: 1 indicator (VIX percentile) + 0 free params (20th pct, "
              "1y window declared unsearched) + 1 branch + 0 filters.",
   flags=("- SVXY is a leveraged inverse ETN: gap risk on vol spikes (Feb 2018 "
          "volmageddon-style events); the monthly rebalance cannot exit "
          "intraday. The 2022 hiking-cycle equity drawdown is not the risk "
          "here — a vol spike is.\n"
          "- If VIX percentile stays low for years, the strategy is buy-and-hold "
          "SVXY through the decay — the walk-forward folds are the honest test."),
   rho="0.218 vs REGCOND-1 (PASS)."),
 "vix-dip-buy": dict(
   idea="idea-0016", title="VIX-spike SPY dip buy",
   desc=("When the VIX close exceeds its trailing 1-year 90th percentile, "
         "buy SPY at the next open and hold 20 trading bars, else hold SHY. "
         "A new spike while holding extends the hold 20 bars from the new "
         "signal month. T+1 open fills, 5 bps."),
   universe="SPY, SHY; signal from ^VIX",
   benchmark="Buy-and-hold SPY, same t+1-open machinery, same 5 bps.",
   complexity="C=3: 1 indicator (VIX percentile trigger) + 1 declared param "
              "(20-bar hold, unsearched round number) + 1 branch + 0 filters.",
   flags=("- Few episodes: 90th-percentile VIX events over 2018–2026 give "
          "roughly 8–12 entries — thin evidence, stated. The gates judge.\n"
          "- Crisis-alpha thesis: the edge (if any) concentrates in "
          "mean-reversion after vol spikes; in calm years it is SHY."),
   rho="0.251 vs REGCOND-1 (PASS)."),
 "uso-momentum": dict(
   idea="idea-0021", title="USO 12-minus-1 absolute momentum",
   desc=("Each month, hold USO when its trailing 12-minus-1-month return "
         "(close[t-21]/close[t-252] - 1) is positive, else hold SHY. "
         "T+1 open, 5 bps."),
   universe="USO, SHY — US-listed ETFs",
   benchmark="Buy-and-hold DBC (commodity basket), same monthly t+1-open machinery, same 5 bps.",
   complexity="C=2: 1 indicator (12-1 momentum sign) + 0 free params "
              "(12-1, skip-1-month declared unsearched) + 1 branch + 0 filters.",
   flags=("- Single-commodity trend: 2020's negative WTI print is in-sample; "
          "the backtest engine's negative-price cost fix (trade-backtest "
          "v0.3.1) applies.\n"
          "- Trial-3 invalidated daily crypto TSMOM; this is monthly energy "
          "momentum — different horizon and asset, stated."),
   rho="0.036 vs REGCOND-1 (PASS — best diversifier in the batch)."),
 "spy-turn-of-month": dict(
   idea="idea-0026", title="SPY turn-of-month effect",
   desc=("Hold SPY on the last 2 and first 3 trading days of each calendar "
         "month, SHY otherwise. Daily position from closes; 5 bps per side on "
         "each switch. The flow-driven (payday/rebalance) calendar anomaly."),
   universe="SPY, SHY — US-listed ETFs",
   benchmark="Buy-and-hold SPY, same daily machinery, same 5 bps.",
   complexity="C=2: 1 indicator (calendar position) + 0 free params (2/3-day "
              "windows declared unsearched) + 1 branch + 0 filters.",
   flags=("- ~10 switches/month = ~24 round trips/year: the Carver cost-speed "
          "gate binds (drag ~ 24*0.001/0.16 = 0.15 Sharpe units); needs "
          "gross Sharpe >= ~0.45 — stated, the gate judges.\n"
          "- Calendar anomalies decay; the walk-forward folds test stability."),
   rho="0.277 vs REGCOND-1 (PASS)."),
 "fx-momentum": dict(
   idea="idea-0031", title="Currency momentum top-2",
   desc=("Each month, hold the top 2 of {UUP, FXE, FXY, FXB, FXC} by trailing "
         "12-minus-1-month return, equal-weighted (rest in SHY). T+1 open, 5 bps."),
   universe="UUP, FXE, FXY, FXB, FXC — US-listed currency ETFs",
   benchmark="Buy-and-hold UUP, same monthly t+1-open machinery, same 5 bps.",
   complexity="C=2: 1 indicator (cross-sectional 12-1 rank) + 0 free params "
              "(top-2, 12-1 declared unsearched) + 1 branch (in/out) + 0 filters.",
   flags=("- FX trends are slow; the 2022 dollar bull dominates the sample — "
          "walk-forward folds test whether the sort works outside it.\n"
          "- FXE/FXY/FXB/FXC are single-currency ETFs with structural drift "
          "(e.g. JPY depreciation); the rank is relative, not absolute."),
   rho="0.270 vs REGCOND-1 (PASS)."),
 "gtaa-5": dict(
   idea="idea-0032", title="GTAA-5 absolute momentum (Faber)",
   desc=("Each month, hold each of SPY, EFA, EEM, IEF, DBC whose month-end "
         "close exceeds its trailing 10-month (210-bar) simple moving average, "
         "equal-weighted among holders, remainder in SHY. T+1 open, 5 bps."),
   universe="SPY, EFA, EEM, IEF, DBC, SHY — US-listed ETFs",
   benchmark="60/40 SPY/AGG buy-and-hold, same monthly t+1-open machinery, same 5 bps.",
   complexity="C=2: 1 indicator (10m SMA absolute trend) + 0 free params "
              "(10m/210-bar declared unsearched) + 1 branch + 0 filters.",
   flags=("- The most-published rule in the batch (Faber 2007/2013): publication "
          "decay is the honest concern — stated. The walk-forward OOS folds "
          "are the test, not the backtest literature.\n"
          "- Structurally closest to REGCOND-1's family (monthly multi-asset); "
          "rho 0.521 passes the screen but it is the highest among admitted."),
   rho="0.521 vs REGCOND-1 (PASS)."),
 "efa-eem-rotation": dict(
   idea="idea-0034", title="EFA/EEM relative momentum rotation",
   desc=("Each month, hold whichever of EFA, EEM has the higher trailing "
         "12-minus-1-month return; SHY if both are negative. T+1 open, 5 bps."),
   universe="EFA, EEM, SHY — US-listed ETFs",
   benchmark="Buy-and-hold EFA, same monthly t+1-open machinery, same 5 bps.",
   complexity="C=2: 1 indicator (relative 12-1 rank + absolute filter) + 0 free "
              "params (12-1 declared unsearched) + 1 branch + 0 filters.",
   flags=("- Admits as the single representative of the defensive-equity / "
          "equity-momentum cluster {0012, 0013, 0014, 0033, 0034} (pairwise "
          "rho up to 0.815); the others were cut as redundant cousins, not "
          "on merit — stated.\n"
          "- International diversifier vs REGCOND-1's US-centric book."),
   rho="0.484 vs REGCOND-1 (PASS)."),
}

for slug, c in CANDS.items():
    tstart = c.get("tstart", "2018-01-01")
    doc = f"""# PRE-REGISTRATION — Round 5 candidate ({c['idea']})

**Strategy:** {c['title']}
**Registered:** {TODAY} (America/New_York), before any validation data was pulled for this candidate.
**Trial count for DSR:** 27 — see "Multiple-testing honesty" below. This spec is frozen.
If it fails the gates, the verdict is invalidated. No parameter tuning and no
re-running with different parameters.

## One-paragraph description

{c['desc']}

Long-only, no leverage. Trade window starts {tstart} (warmup from 2015-01-01).

{COMMON_DSR}

## Why this candidate (triage result)

- Structural screens (docs/research/round5/triage.json): data-clean per the
  round-5 audit, complexity {c['complexity'].split(':')[0]}, correlation
  {c['rho']}.
- Complexity breakdown: {c['complexity']}
- Triage admitted on structural grounds only — no performance was ranked.
  The full 6-gate walk-forward below is the first performance judgment.

## Honest flags

{c['flags']}

## Universe (frozen)

{c['universe']}

## Benchmark (frozen)

{c['benchmark']}

## Signal, sizing, costs (frozen)

- Signal and sizing exactly as in "One-paragraph description" above; the
  reference implementation is `docs/research/round5/triage.py` (signal
  functions), re-implemented literally in the validation harness.
- Rebalance: first trading day of each month (quarterly for short-carry-ladder:
  Jan/Apr/Jul/Oct), reading the signal at the last trading day of the prior
  period; fills at the next trading day's open (t -> t+1).
- Costs: 5 bps per side on traded notional (documented retail assumption).
- Fully invested per the target weights (SHY is the cash proxy where specified).

{COMMON_GATES}

{COMMON_PROC}

## Config hash

`{hashlib.sha256((slug + TODAY).encode()).hexdigest()[:16]}` (spec identifier; the
validation harness records the frozen-parameter hash alongside evidence).
"""
    path = os.path.join(VAL, slug, "PRE-REGISTRATION.md")
    with open(path, "w") as f:
        f.write(doc)
    print("wrote", path)
