# TREND-VT validation report (trial 3, candidate A)

- Pre-registration: commit 42ecab2 (frozen spec); gate amendment commit 425745b (5 -> 7 gates, before any data pull)
- Data: synthetic, 2010-01-01..2026-09-26
- Costs: 5 bps/side + 30.0 bps/yr borrow on short notional; fills at next trading day's open
- Walk-forward: 60m train / 12m test / 12m step / 21d embargo (1260/252/252/21 daily bars), 4 folds; concatenated OOS = gated series
- DSR N=7 (Phase-B in-sample Sharpes 0.798, 0.485, 0.413, 0.379, 0.106, -0.097, -0.337)

## Gates (trade-overfit standard preset)

| gate | value | threshold | result |
|---|---|---|---|
| deflated_sharpe | 0.0000 | gte 0.95 | FAIL |
| oos_sharpe | 0.1446 | gt 1.0 | FAIL |
| max_drawdown | -0.0677 | gt -0.15 | PASS |
| regime_stability | 0.2276 | gt 0.0 | PASS |
| beats_benchmark_net | -0.0087 | gt 0.0 | FAIL |
| sortino | 0.3996 | gte 1.5 | FAIL |
| calmar | 0.1520 | gte 2.0 | FAIL |

**Verdict: KILL**

## Walk-forward folds

| fold | test window | OOS Sharpe | OOS return | OOS maxDD |
|---|---|---|---|---|
| 0 | 2014-12-03..2015-11-19 | 0.510 | 0.0190 | -0.0241 |
| 1 | 2015-11-20..2016-11-07 | -0.239 | -0.0108 | -0.0583 |
| 2 | 2016-11-08..2017-10-25 | -0.220 | -0.0098 | -0.0370 |
| 3 | 2017-10-26..2018-10-12 | 1.089 | 0.0438 | -0.0380 |

- Strategy annualized (OOS): 0.0103
- EW 6-ETF benchmark annualized (net of 5 bps/side): 0.0190
- Excess (strategy - benchmark): -0.0087
- Regime splits: {"calm": {"n_bars": 505, "sharpe": 0.22764214966153515, "total_return": 0.0160252696030736, "max_drawdown": -0.06223471563410099}, "stress": {"n_bars": 503, "sharpe": 0.3156674299096935, "total_return": 0.025343649728469142, "max_drawdown": -0.051200503768054406}}
- Final equity: 126,880.90 (from 100,000.00)

## Borrow-cost sensitivity (report-only; gated run uses 30 bps)

| borrow (bps/yr) | final equity | total return | OOS Sharpe |
|---|---|---|---|
| 0 | 127,952.40 | 0.2795 | 0.301 |
| 100 | 124,415.01 | 0.2442 | 0.211 |
| 30 (spec) | 126,880.90 | 0.2688 | 0.274 |

## Honest flags

- Trend-family exposure: TREND-VT shares trial 1 (DON-20/10-ATR)'s exposure to trend failure as a *family*. The diversification is structural — cross-asset (6 ETFs vs single asset), vol-targeted sizing (vs fixed fractional), monthly rebalance (vs daily) — not categorical. In a cross-asset trend-failure regime, both would suffer.
- The 6-ETF set is a researcher choice (documented in the pre-registration, not data-mined).
- yfinance adjusted closes; survivorship is a non-issue for these ETFs but corporate-action adjustment quality is vendor-dependent.
- Borrow cost is an assumption (30 bps disclosed low end; sensitivity above). Retail short-ETF borrow can be higher in stress.
- Vol targeting lags by construction: a mid-month vol spike is unaddressed until the next month-end.
- Fills assumed at next day's open at the open price with 5 bps commission; no spread/slippage modeled beyond that.

## Data provenance

- Source: yfinance via trade-data-equities EquitiesDataClient/YFinanceProvider, adjusted=True (split- and dividend-adjusted)
- Window: 2010-01-01..2026-09-25 (client [start, end) with end=2026-09-26)
- Bars per ETF: {"SPY": 2500, "TLT": 2500, "GLD": 2500, "USO": 2500, "EFA": 2500, "VNQ": 2500}
- Rebalance-date holes: none
- Run: 2026-09-27T02:24:02.320341+00:00 .. 2026-09-27T02:24:03.031227+00:00
