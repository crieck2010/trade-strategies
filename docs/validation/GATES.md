# Validation gates: the two-tier framework

**Adopted 2026-09-27** by the owner's decision. Supersedes the standalone
seven-gate set (DSR, OOS Sharpe > 1.0, maxDD < 15%, worst-regime Sharpe > 0,
beat benchmark net, Sortino ≥ 1.5, Calmar ≥ 2.0) as the official validation
standard for the suite.

**Why.** The standalone set demanded portfolio-level performance from single
strategies: a Sharpe > 1.0, sub-15% drawdown, and Calmar ≥ 2.0 bar describes
an elite *portfolio*, not an entry filter for one component. Applied at the
strategy level it discards statistically genuine edges over risk-bar
technicalities. The two-tier system puts the entry bar where it belongs
(per strategy) and the elite bar where it belongs (the allocated portfolio).

## Terminology standard

- A strategy that passes its gate set is **validated**.
- A strategy that fails is **invalidated** (or **discarded**).
- The word "kill" is retired from this lane's vocabulary — in reports,
  docs, and code comments going forward. Trial reports committed before
  2026-09-27 keep their original language as evidence records; they are
  not rewritten.

## Tier 1 — per-strategy entry filter

A strategy enters the allocator's candidate pool iff ALL hold:

| Gate | Threshold |
|---|---|
| OOS Sharpe (median across walk-forward folds) | > 0.3 |
| Max drawdown | shallower than −25% |
| Deflated Sharpe Ratio | > 0.8 |
| Excess return vs benchmark, net of costs | > 0 |
| Sortino | > 0.75 |
| Cost speed limit | cost Sharpe drag ≤ gross Sharpe / 3 (gross Sharpe > 0) |

See "Gate 6 — cost speed limit" below for the maths.

DSR `n_trials` counts every idea screened in the same research phase
(the honesty rule from trial 4: only screened ideas count as trials).

## Tier 2 — allocated-portfolio promotion

A *portfolio* assembled by trade-allocate graduates toward paper
incubation iff ALL hold at the portfolio level:

| Gate | Threshold |
|---|---|
| Portfolio Sharpe | > 1.0 |
| Portfolio max drawdown | < 15% |
| Portfolio DSR | ≥ 0.95, with `n_trials` = **all strategy-selection trials to date** |
| Portfolio Sortino | ≥ 1.5 |
| Portfolio Calmar | ≥ 2.0 |
| Diversification ratio | ≥ 1.10 (per trade-allocate METHODOLOGY) |

**Load-bearing rule:** the portfolio DSR must include strategy-selection
multiplicity. A portfolio assembled from six screened ideas carries
n_trials ≥ 6 (plus every earlier screened idea in the lane), not n = 1.
Without this, the second tier silently re-introduces the overfitting the
first tier was built to prevent.

## Retrospective application (trials 1–4)

Evaluated against the Tier-1 filter from their frozen evidence:

| Strategy | OOS Sharpe | maxDD | DSR | Beat bmk | Sortino | Tier-1 |
|---|---|---|---|---|---|---|
| DON-20/10-ATR | 0.87 ✓ | −40.2% ✗ | 1.00 ✓ | ✓ | — | **discarded** |
| MR-5M | −2.28 ✗ | −15.7% ✓ | 0.00 ✗ | ✓ | — | **discarded** |
| TREND-VT | 0.09 ✗ | −19.1% ✓ | 0.00 ✗ | ✗ | 0.07 ✗ | **discarded** |
| TSMOM-CR | −0.21 ✗ | −27.1% ✗ | 0.00 ✗ | ✗ | −0.20 ✗ | **discarded** |
| XMOM-1 | 0.77 ✓ | −26.0% ✗ | 0.00 ✗ | ✓ | 0.56 ✗ | **discarded** |
| REGCOND-1 | 1.385 ✓ | −23.0% ✓ | 1.000 ✓ | +4.91%/yr ✓ | 1.41 ✓ | **validated** |

The reform resurrects nothing: the five earlier strategies remain discarded
under Tier-1 (each fails at least one gate, most fail the DSR outright).
REGCOND-1 is the unique Tier-1 validation — a statistically genuine edge
(DSR 1.000) whose trial-4 failure was purely the old risk bar.

**REGCOND-1 status (2026-09-27): Tier-1 validated → allocator candidate pool.**
Its trial-4 verdict under the pre-reform seven-gate set (invalidated, 4/7)
stands as the historical record in `regcond-1/report.md`; the reform is
prospective and does not rewrite it.

## Gate 6 — cost speed limit (adopted 2026-09-27)

Robert Carver's rule from *Systematic Trading*: every round-trip trade
costs Sharpe units, and a strategy must not spend more than about one
third of its gross edge on trading costs.

### The maths

Inputs (plain data, from the trial's cost model and backtest):

- `turnover_ann` — annualised round-trip trades per year.
- `round_trip_cost` — one round trip as a fraction of notional
  (commission + spread + slippage, from the configured cost model).
- `instrument_vol_ann` — annualised volatility of the traded instrument
  as a fraction (daily log-return stdev × √252).
- `gross_sharpe` — pre-cost Sharpe from the backtest.

Derivation: trading `turnover_ann` round trips a year on one unit of
notional bleeds `turnover_ann × round_trip_cost` per year in return
terms. A pure return drag `d` on a return stream with annualised
volatility `σ` reduces the Sharpe ratio by `d / σ` (to first order —
the drag is treated as deterministic and vol is assumed unchanged).
Hence the cost drag in Sharpe units:

```
cost_sharpe_drag = turnover_ann × round_trip_cost / instrument_vol_ann
budget           = gross_sharpe / 3
```

**PASS iff `gross_sharpe > 0` AND `cost_sharpe_drag ≤ budget`.**

Carver's rule of thumb: a typical single rule earns ~0.4 gross Sharpe,
giving the familiar ~0.13 SR/yr default budget. This gate uses the
strategy's *own* gross Sharpe adaptively — a stronger edge earns a
larger turnover budget — rather than hard-coding 0.4.

### Worked examples (regression-pinned in the test suite)

| Market | Round-trip cost | Instr. vol | Cost per trade (SR) | Budget (0.4/3) | Max round trips/yr |
|---|---|---|---|---|---|
| Cheap futures | 2 bps | 10% | 0.002 | 0.133 | ~65 |
| BTC | 40 bps | 80% | 0.005 | 0.133 | ~26 |

The video figures (~65 and ~26) are reproduced: 65 passes / 67 fails for
futures; 26 passes / 27 fails for BTC. The cost/vol assumptions above
are documented here — they are the inputs consistent with Carver's
figures, not figures from the video itself.

### Multi-instrument strategies

Costs and vols are notional-weighted: with weight
`w_i = notional_i / total_notional`,

```
round_trip_cost   = Σ w_i × cost_i
instrument_vol_ann = Σ w_i × vol_i
```

then the single-instrument gate runs. This ignores correlation between
the instruments' cost/vol realisations — conservative enough for a gate,
since diversification can only lower realised portfolio vol relative to
the weighted sum.

### Why this gate exists alongside "beat benchmark net"

The benchmark gate depends on the cost model being *exactly right*.
This gate bounds the *sensitivity* to cost-model error: a strategy
spending 0.05 of its 0.4 edge on costs survives a 2× slippage
mis-estimate; one spending 0.13 does not. It structurally favours higher
timeframes — the same conclusion Carver draws, now enforced as a gate.

### Machine-readable evidence

Future trials record under `tier1_evidence.json`:

```json
"cost_speed_limit": {
  "turnover_ann": 65.0,
  "round_trip_cost": 0.0002,
  "instrument_vol_ann": 0.10,
  "gross_sharpe": 0.4,
  "cost_sharpe_drag": 0.13,
  "budget": 0.1333,
  "pass": true
}
```

Multi-instrument trials add an `instruments` array with the
per-instrument cost/vol/weight breakdown. `trade-allocate`'s
`validate_evidence()` should accept the block once present; the block is
optional until a trial pre-registers under the post-2026-09-27 gate set.

### Grandfathering

The gate applies to trials **pre-registered after its adoption date
(2026-09-27)**. Existing Tier-1 validations stand as recorded and are
not retroactively re-judged: REGCOND-1 remains Tier-1 validated 5/5
under the gate set in force at its trial. Pre-registrations continue to
freeze the gate set in force at registration time (see Process notes).

## Process notes

- Trial pre-registrations continue to freeze the *gate set in force at
  registration time*. A mid-trial framework change is recorded as a dated
  amendment appendix, never an edit of the frozen spec.
- Tier-1 numbers are computed alongside every future trial's official gate
  table, so a later framework change never requires a re-run.
