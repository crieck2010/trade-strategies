# XMOM-1 validation report (trial 3 of 3)

- Pre-registration: commit 4b72b8a (frozen spec, before any OHLC pull)
- Data: yfinance daily OHLCV via trade-data-equities EquitiesDataClient + YFinanceProvider, adjusted=True, 2015-01-01..2026-09-26
- Universe: 271 tickers; 262 eligible (>=95% SPY-grid coverage); 261 tradeable (no leading gap, mirrors screening)
- Costs: 5.0 bps/side + 50.0 bps/yr borrow on shorts; t+1 open fills; no stops, no turnover control
- Walk-forward: 60-month train / 12-month test / 12-month step / 21d embargo, 7 folds; gated series = concatenated OOS (1545 bars)
- DSR n_trials=7 (Phase B in-sample Sharpes 0.798, 0.485, 0.413, 0.379, 0.106, -0.097, -0.337; XMOM-1 was #3)
- Benchmark: irx_forward_filled (annualized 0.0288 over OOS span)

## Gates (trade-overfit standard preset)

| gate | value | threshold | result |
|---|---|---|---|
| deflated_sharpe | 0.0000 | gte 0.95 | FAIL |
| oos_sharpe | 0.7717 | gt 1.0 | FAIL |
| max_drawdown | -0.2596 | gt -0.15 | FAIL |
| regime_stability | 0.1628 | gt 0.0 | PASS |
| beats_benchmark_net | 0.0320 | gt 0.0 | PASS |
| sortino | 0.5598 | gte 1.5 | FAIL |
| calmar | 0.2341 | gte 2.0 | FAIL |

**Verdict: KILL**

## Walk-forward folds (OOS)

| fold | test window | OOS Sharpe | OOS ann. | OOS return | OOS maxDD |
|---|---|---|---|---|---|
| 0 | 2020-02-03..2020-12-31 (2020-01..2021-01) | 0.790 | 0.1610 | 0.1473 | -0.1441 |
| 1 | 2021-02-03..2021-12-31 (2021-01..2022-01) | -0.490 | -0.1019 | -0.0938 | -0.1923 |
| 2 | 2022-02-02..2022-12-30 (2022-01..2023-01) | 0.772 | 0.1008 | 0.0916 | -0.1073 |
| 3 | 2023-02-02..2023-12-29 (2023-01..2024-01) | -0.233 | -0.0329 | -0.0299 | -0.0627 |
| 4 | 2024-02-01..2024-12-31 (2024-01..2025-01) | 1.023 | 0.1362 | 0.1242 | -0.0842 |
| 5 | 2025-02-04..2025-12-31 (2025-01..2026-01) | -0.407 | -0.0570 | -0.0520 | -0.1175 |
| 6 | 2026-02-03..2026-09-25 (2026-01..2026-10) | 1.021 | 0.3664 | 0.2237 | -0.2596 |

- Strategy annualized (OOS): 0.0608
- Benchmark annualized (OOS): 0.0288
- Excess vs benchmark (after costs): 0.0320
- DSR detail: sharpe_hat=0.4040, n_obs=1545, n_trials=7, expected_sharpe_under_null=0.5324
- Regime splits (trailing-63d vol vs median): {"calm": {"n_bars": 773, "sharpe": 0.162762064660058, "total_return": 0.03906534645995485, "max_drawdown": -0.15246576813077384}, "stress": {"n_bars": 772, "sharpe": 0.5588890165676065, "total_return": 0.38194203639715973, "max_drawdown": -0.25962609493155764}}; worst=calm (0.162762064660058)
- Final equity: 163,949.76 (from 100,000.00); 1271 trades, 2593 signals

## Borrow sensitivity (report-only; spec stays 50 bps/yr)

| borrow | OOS Sharpe | OOS ann. | OOS maxDD | final equity |
|---|---|---|---|---|
| 0.0 bps | 0.416 | 0.0632 | -0.2592 | 166,910.58 |
| 50.0 bps | 0.404 | 0.0608 | -0.2596 | 163,949.76 |
| 200.0 bps | 0.368 | 0.0536 | -0.2608 | 155,356.10 |

## Benchmark construction note

- Source used: **irx_forward_filled**.
- ^IRX daily closes via trade-data-equities (same pull as the equity bars); rf_daily = y/100/252 per trading day (simple interest, documented in the pre-registration); ^IRX gaps forward-filled; a leading gap with no prior observation counts as 0.
- Pre-registered fallback (decided before results): if ^IRX could not be fetched at all, benchmark = 0% cash. **The fallback was NOT needed — ^IRX fetched.**

## Honest flags (from the pre-registration, restated)

- **Survivorship bias**: the universe is today's large-cap constituents; delisted names are absent, which flatters momentum (dead losers are missing from the short leg's history). Documented in Phase B and the spec — the gates judge whether the premium survives it, not whether the bias exists.
- **Momentum-crash profile**: the 25.3% in-sample screening maxDD already exceeds the 15% gate; a crash inside the OOS window is the binding failure mode.
- **Momentum-family exposure**: shared with trial 1 (DON-20/10-ATR). The diversification is structural (cross-sectional + dollar-neutral + monthly), not categorical.
- **Borrow at 50 bps/yr is a general-collateral assumption**; hard-to-borrow names in the short leg cost more — see the borrow-sensitivity table above.
- **t+1 fill whipsaw**: signals on the rebalance close fill at the next open; violent reversals on rebalance months are the known enemy (stated in Phase A).
- No turnover control: full monthly reconstitution maximizes cost drag; the screening's 1,275 trades are the evidence this is affordable, not optimal.

## Literal-reading choices (ambiguities resolved, never optimized)

1. `close[t-21]` / `close[t-273]` are taken on the SPY trading-day grid; missing bars inside the window are causally forward-filled (mirrors screening `aligned_closes`). Tickers with any leading gap on the grid are excluded from the tradeable set — this is the screening implementation mirrored literally; it is stricter than the >=95% rule and only affects tickers listed after 2015.
2. 'Ticker missing a bar on the rebalance date itself -> ineligible that month' is implemented as in screening: no bar -> no signal emitted for that symbol that day (an existing position is left untouched rather than force-exited).
3. Eligibility (>=95% coverage) is static over 2015-01-01..2026-09-25 per the frozen spec — the same lookahead the screening had, documented as part of the survivorship-bias flag.
4. Engine timestamps are normalized to UTC midnight per calendar date (yfinance daily stamps carry time-of-day/DST quirks); one engine timestamp = one trading day.
5. Walk-forward folds are calendar-month blocks; the embargo is 21 trading days after the last train bar; test bars are trading days in the test months strictly after the embargo.
6. Borrow sensitivity re-runs the full engine at 0/200 bps/yr — report-only; the 50 bps spec run is the gated one.

## Data provenance

- Raw bars: yfinance via trade-data-equities `EquitiesDataClient` + `YFinanceProvider`, `Timeframe.DAILY`, `adjusted=True`, cached under `evidence/cache/` (per-ticker manifest: `evidence/fetch_manifest.json`). The cache (~133 MB) is intentionally NOT committed to git — it is reproducible from the manifest + `run_validation.py`.
- Grid: 2950 SPY trading days, 2015-01-02..2026-09-25.
- Rebalance months traded: 93/93 (empty-leg months, if any, held positions per spec).

## Run history

- Attempt A (2026-09-26): killed mid-pull by a VM restart; no outputs.
- Attempt B (2026-09-26): completed but INVALID — the restart had wiped
  the `yfinance` install, so 6 tickers (WST, WY, XOM, XYL, YUM, ZTS) and
  `^IRX` failed to fetch; the 0%-cash benchmark fallback was used.
  Verdict was KILL anyway. Post-mortem:
  `invalid_runs/run-2026-09-26-incomplete-data/NOTE.md`.
- This report is the clean re-run (attempt C): all 271 tickers + `^IRX`
  fetched, `^IRX`-based benchmark, no fallback.
