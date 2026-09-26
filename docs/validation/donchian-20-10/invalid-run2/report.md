# DON-20/10-ATR validation report — trial 1 of 1

**Verdict: KILL** (run 2026-09-26T21:24:45.290165+00:00)

## Universe
S&P 500 constituents retrieved 2026-09-26; 503 downloaded ok, 0 failed; final universe **458** symbols (coverage≥99%: 458).

## Walk-forward (rolling 756/252/252, 10-day embargo, params frozen)

| fold | test window | OOS Sharpe | OOS return | OOS maxDD |
|------|-------------|------------|------------|-----------|
| 0 | 2018-01-19..2019-01-18 | -2.06 | -913.21% | -417.61% |
| 1 | 2019-01-22..2020-01-21 | -1.60 | -39013.27% | -3941.05% |
| 2 | 2020-01-22..2021-01-20 | -0.24 | 3337.07% | -668.13% |
| 3 | 2021-01-21..2022-01-19 | 1.78 | 1187.01% | -171.68% |
| 4 | 2022-01-20..2023-01-20 | -0.56 | -561.04% | -1050.23% |
| 5 | 2023-01-23..2024-01-23 | 0.52 | -7515.37% | -749.50% |
| 6 | 2024-01-24..2025-01-24 | 1.38 | 14139.38% | -230.13% |
| 7 | 2025-01-27..2026-01-27 | 1.26 | 8943.94% | -541.55% |

## Gates (standard preset, N=1)

| gate | value | threshold | pass |
|------|-------|-----------|------|
| deflated_sharpe | 1.0000 | gte 0.95 | PASS |
| oos_sharpe | 0.1385 | gt 1.0 | FAIL |
| max_drawdown | -6.6813 | gt -0.15 | FAIL |
| regime_stability | -0.5695 | gt 0.0 | FAIL |
| beats_benchmark_net | 38.1463 | gt 0.0 | PASS |

## Notes
- DSR inputs: Sharpe_hat=0.138, n_obs=2015, n_trials=1, skew=7.09, excess_kurt=430.83.
- Regime splits (desk vol-regime): {"calm": {"n_bars": 1008, "sharpe": -0.5694969993456467, "total_return": -0.9999999999999387, "max_drawdown": -1.3840728657165864}, "stress": {"n_bars": 1007, "sharpe": 0.2882879510101814, "total_return": 9.129518502535931e+25, "max_drawdown": -223.17406014796137}}.
- Signal/fill reconciliation: 2503 LONG signals, 2484 filled entries.
- Costs are in-engine (5 bps/side); the OOS series is already net.
- Survivorship bias (upward): universe drawn from today's constituents.
