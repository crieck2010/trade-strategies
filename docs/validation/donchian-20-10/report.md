# DON-20/10-ATR validation report — trial 1 of 1

**Verdict: KILL** (run 2026-09-26T21:36:58.625568+00:00)

## Universe
S&P 500 constituents retrieved 2026-09-26; 503 downloaded ok, 0 failed; final universe **458** symbols (coverage≥99%: 458).

## Walk-forward (rolling 756/252/252, 10-day embargo, params frozen)

| fold | test window | OOS Sharpe | OOS return | OOS maxDD |
|------|-------------|------------|------------|-----------|
| 0 | 2018-01-19..2019-01-18 | -0.15 | -7.75% | -28.56% |
| 1 | 2019-01-22..2020-01-21 | 1.08 | 27.40% | -21.48% |
| 2 | 2020-01-22..2021-01-20 | 0.56 | 15.22% | -29.88% |
| 3 | 2021-01-21..2022-01-19 | 1.08 | 36.31% | -16.18% |
| 4 | 2022-01-20..2023-01-20 | -0.10 | -11.42% | -40.15% |
| 5 | 2023-01-23..2024-01-23 | 1.39 | 49.21% | -23.55% |
| 6 | 2024-01-24..2025-01-24 | 1.09 | 34.17% | -25.36% |
| 7 | 2025-01-27..2026-01-27 | 0.67 | 19.09% | -34.96% |

## Gates (standard preset, N=1)

| gate | value | threshold | pass |
|------|-------|-----------|------|
| deflated_sharpe | 1.0000 | gte 0.95 | PASS |
| oos_sharpe | 0.8738 | gt 1.0 | FAIL |
| max_drawdown | -0.4015 | gt -0.15 | FAIL |
| regime_stability | 0.6093 | gt 0.0 | PASS |
| beats_benchmark_net | 0.0436 | gt 0.0 | PASS |

## Notes
- DSR inputs: Sharpe_hat=0.666, n_obs=2015, n_trials=1, skew=-0.48, excess_kurt=2.98.
- Regime splits (desk vol-regime): {"calm": {"n_bars": 1008, "sharpe": 0.7575400603492131, "total_return": 1.0117864399999443, "max_drawdown": -0.33312389428045064}, "stress": {"n_bars": 1007, "sharpe": 0.6092783918300876, "total_return": 0.8868234110147111, "max_drawdown": -0.3961110965887127}}.
- Signal/fill reconciliation: 2503 LONG signals, 2481 filled entries.
- Costs are in-engine (5 bps/side); the OOS series is already net.
- Survivorship bias (upward): universe drawn from today's constituents.
