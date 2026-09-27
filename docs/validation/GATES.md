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

## Process notes

- Trial pre-registrations continue to freeze the *gate set in force at
  registration time*. A mid-trial framework change is recorded as a dated
  amendment appendix, never an edit of the frozen spec.
- Tier-1 numbers are computed alongside every future trial's official gate
  table, so a later framework change never requires a re-run.
