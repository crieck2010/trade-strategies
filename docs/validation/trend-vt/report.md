# TREND-VT validation report (trial 3, candidate A)

- Pre-registration: commit 42ecab2 (frozen spec); gate amendment commit 425745b (5 -> 7 gates, before any data pull)
- Data: yfinance daily OHLCV via trade-data-equities EquitiesDataClient + YFinanceProvider, adjusted=True (split/div adjusted), 2010-01-01..2026-09-26
- Costs: 5 bps/side + 30.0 bps/yr borrow on short notional; fills at next trading day's open
- Walk-forward: 60m train / 12m test / 12m step / 21d embargo (1260/252/252/21 daily bars), 11 folds; concatenated OOS = gated series
- DSR N=7 (Phase-B in-sample Sharpes 0.798, 0.485, 0.413, 0.379, 0.106, -0.097, -0.337)

## Gates (trade-overfit standard preset)

| gate | value | threshold | result |
|---|---|---|---|
| deflated_sharpe | 0.0000 | gte 0.95 | FAIL |
| oos_sharpe | 0.0900 | gt 1.0 | FAIL |
| max_drawdown | -0.1913 | gt -0.15 | FAIL |
| regime_stability | -0.2827 | gt 0.0 | FAIL |
| beats_benchmark_net | -0.0664 | gt 0.0 | FAIL |
| sortino | 0.0716 | gte 1.5 | FAIL |
| calmar | 0.0076 | gte 2.0 | FAIL |

**Verdict: KILL**

## Walk-forward folds

| fold | test window | OOS Sharpe | OOS return | OOS maxDD |
|---|---|---|---|---|
| 0 | 2015-02-06..2016-02-05 | -0.284 | -0.0128 | -0.0360 |
| 1 | 2016-02-08..2017-02-06 | -0.779 | -0.0381 | -0.0644 |
| 2 | 2017-02-07..2018-02-06 | 0.623 | 0.0359 | -0.0554 |
| 3 | 2018-02-07..2019-02-07 | -1.585 | -0.1005 | -0.1192 |
| 4 | 2019-02-08..2020-02-07 | 1.320 | 0.0592 | -0.0267 |
| 5 | 2020-02-10..2021-02-08 | -1.015 | -0.0794 | -0.1068 |
| 6 | 2021-02-09..2022-02-07 | 0.744 | 0.0468 | -0.0348 |
| 7 | 2022-02-08..2023-02-08 | -0.662 | -0.0406 | -0.0782 |
| 8 | 2023-02-09..2024-02-09 | 0.090 | 0.0027 | -0.0293 |
| 9 | 2024-02-12..2025-02-12 | 1.016 | 0.0608 | -0.0394 |
| 10 | 2025-02-13..2026-02-13 | 1.647 | 0.1023 | -0.0403 |

- Strategy annualized (OOS): 0.0014
- EW 6-ETF benchmark annualized (net of 5 bps/side): 0.0678
- Excess (strategy - benchmark): -0.0664
- Regime splits: {"calm": {"n_bars": 1387, "sharpe": 0.6024749256039288, "total_return": 0.1466645776291433, "max_drawdown": -0.07817861135833692}, "stress": {"n_bars": 1385, "sharpe": -0.2827366789387324, "total_return": -0.11390364450781088, "max_drawdown": -0.23286489382022224}}
- Final equity: 133,655.15 (from 100,000.00)

## Borrow-cost sensitivity (report-only; gated run uses 30 bps)

| borrow (bps/yr) | final equity | total return | OOS Sharpe |
|---|---|---|---|
| 0 | 134,874.75 | 0.3487 | 0.065 |
| 100 | 130,851.78 | 0.3085 | 0.028 |
| 30 (spec) | 133,655.15 | 0.3366 | 0.054 |

## Honest flags

- Trend-family exposure: TREND-VT shares trial 1 (DON-20/10-ATR)'s exposure to trend failure as a *family*. The diversification is structural — cross-asset (6 ETFs vs single asset), vol-targeted sizing (vs fixed fractional), monthly rebalance (vs daily) — not categorical. In a cross-asset trend-failure regime, both would suffer.
- The 6-ETF set is a researcher choice (documented in the pre-registration, not data-mined).
- yfinance adjusted closes; survivorship is a non-issue for these ETFs but corporate-action adjustment quality is vendor-dependent.
- Borrow cost is an assumption (30 bps disclosed low end; sensitivity above). Retail short-ETF borrow can be higher in stress.
- Vol targeting lags by construction: a mid-month vol spike is unaddressed until the next month-end.
- Fills assumed at next day's open at the open price with 5 bps commission; no spread/slippage modeled beyond that.
- Screening-vs-validation implementation difference: the loose Phase-B screening (`docs/research/scratch/trend_vt.py`) rebalanced on the FIRST trading day of each month with 50 bps/yr borrow; this validation follows the frozen spec literally — LAST trading day of the month, 30 bps/yr borrow. The spec is the law; the screening was documented as deliberately loose. The spec-literal run's +16.4% over 2019-01-01..2026-09-25 is in the same family as screening's +23.9% over 2018-01-01..2026-09-25, so the KILL is not a harness artifact — the edge simply does not survive walk-forward: 5 of 11 OOS folds are negative and the stress-regime Sharpe is -0.28.

## Pre-pull harness fixes (audit trail)

Two harness bugs were caught by the `--smoke` mechanics run (synthetic bars, no network) BEFORE any validation data was pulled; both were fixed and the smoke re-ran green. No invalid validation runs exist — the single real-data run above is the one clean run.

1. `SignalAction` import: lives in `trade_backtest.models`, not `trade_backtest.strategy`.
2. `evidence.json` metadata bug: `first_bar`/`last_bar` comprehensions indexed the bar list with a string key.

A post-run audit (independent re-check of the signal path) confirmed: first nonzero rebalance lands ~252 trading days after series start (2010-12-31 on synthetic), sign(TR) matches sign(weight) on every nonzero leg (one apparent mismatch was a display-rounding artifact of a measure-zero TR), and rebalance-month holes would force legs flat per spec (none occurred in real data).

## Data provenance

- Source: yfinance via trade-data-equities EquitiesDataClient/YFinanceProvider, adjusted=True (split- and dividend-adjusted)
- Window: 2010-01-01..2026-09-25 (client [start, end) with end=2026-09-26)
- Bars per ETF: {"SPY": 4208, "TLT": 4208, "GLD": 4208, "USO": 4208, "EFA": 4208, "VNQ": 4208}
- Rebalance-date holes: none
- Run: 2026-09-27T02:24:10.141981+00:00 .. 2026-09-27T02:24:20.610605+00:00
