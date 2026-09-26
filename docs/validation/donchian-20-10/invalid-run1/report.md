# DON-20/10-ATR validation report — trial 1 of 1

**Verdict: KILL** (run 2026-09-26T21:15:15.940416+00:00)

## Universe
S&P 500 constituents retrieved 2026-09-26; 503 downloaded ok, 0 failed; final universe **458** symbols (coverage≥99%: 458).

## Walk-forward (rolling 756/252/252, 10-day embargo, params frozen)

| fold | test window | OOS Sharpe | OOS return | OOS maxDD |
|------|-------------|------------|------------|-----------|
| 0 | 2018-01-19..2019-01-18 | -0.07 | -1860.88% | -480.17% |
| 1 | 2019-01-22..2020-01-21 | -1.69 | -11496.06% | -5523.60% |
| 2 | 2020-01-22..2021-01-20 | -0.82 | 8279.84% | -595.99% |
| 3 | 2021-01-21..2022-01-19 | -0.49 | 3144.03% | -147.12% |
| 4 | 2022-01-20..2023-01-20 | -0.76 | 8284.96% | -1357.53% |
| 5 | 2023-01-23..2024-01-23 | -1.21 | 9726.37% | -273.91% |
| 6 | 2024-01-24..2025-01-24 | -0.58 | 1787498.29% | -181.04% |
| 7 | 2025-01-27..2026-01-27 | 0.87 | 21974.56% | -454.34% |

## Gates (standard preset, N=1)

| gate | value | threshold | pass |
|------|-------|-----------|------|
| deflated_sharpe | 0.0000 | gte 0.95 | FAIL |
| oos_sharpe | -0.6676 | gt 1.0 | FAIL |
| max_drawdown | -5.9599 | gt -0.15 | FAIL |
| regime_stability | -1.0751 | gt 0.0 | FAIL |
| beats_benchmark_net | 140.8790 | gt 0.0 | PASS |

## Notes
- DSR inputs: Sharpe_hat=-0.743, n_obs=2015, n_trials=1, skew=-13.06, excess_kurt=258.09.
- Regime splits (desk vol-regime): {"calm": {"n_bars": 1008, "sharpe": 0.05082009902313834, "total_return": -1.0, "max_drawdown": -1.3754717384634971}, "stress": {"n_bars": 1007, "sharpe": -1.0751153602884596, "total_return": 7.610690914663196e+33, "max_drawdown": -796.0200257075201}}.
- Signal/fill reconciliation: 2478 LONG signals, 2782 filled entries.
- Costs are in-engine (5 bps/side); the OOS series is already net.
- Survivorship bias (upward): universe drawn from today's constituents.
