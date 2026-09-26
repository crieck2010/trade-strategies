# MR-5M validation report — trial 2 of 2

**Verdict: KILL** (run 2026-09-26, pre-registration commit 998f2a0)

## Data

Binance.US public klines (keyless) via `trade-data-crypto` v0.2.0
`BinanceUSPublicProvider`, pulled 2026-09-26. **167,928 five-minute bars per
symbol, 2025-02-19T13:00Z .. 2026-09-25T23:55Z**, inner-joined on timestamp
(167,928 common bars → 335,856 engine bars).

**Data-range deviation from the pre-registration (documented, not tuned):**
the frozen spec assumed 2024-01-01 through 2026-09-25, but Binance.US serves
no 5-minute klines between ~2023-09 and 2025-02-19T13:00Z for BTCUSD/ETHUSD
(direct API probes 2026-09-26: any `startTime` in that window returns bars
starting 2025-02-19T13:00Z; earlier 2023 data exists). The gap coincides with
Binance.US's 2023–2024 SEC/banking disruption. The provider paginated
correctly — the venue simply has a ~17-month hole. The run uses the maximum
continuous history the pre-registered venue offers (19 months, 35 folds);
no venue-shopping was done after the fact.

## Walk-forward (12w train / 2w test / 2w step / 1d embargo, params frozen)

35 folds, 141,120 OOS bars (2025-05-15 .. 2026-09-17). Continuous single run,
t+1-open fills, 6 bps/side all-in costs (2 taker + 2 half-spread + 2 slippage).
2,299 round trips: 1,026 reversion exits / 490 stop exits / 783 time-stop exits.
Final equity $79,986.57 from $100,000 (−20.0%).

| fold | test window | OOS Sharpe | OOS return | OOS maxDD |
|------|-------------|------------|------------|-----------|
| 0 | 2025-05-15..2025-05-29 | -0.76 | -0.11% | -0.74% |
| 1 | 2025-05-29..2025-06-12 | -2.28 | -0.33% | -0.89% |
| 2 | 2025-06-12..2025-06-26 | -6.46 | -1.26% | -2.14% |
| 3 | 2025-06-26..2025-07-10 | 2.35 | 0.24% | -0.49% |
| 4 | 2025-07-10..2025-07-24 | 10.52 | 1.86% | -0.36% |
| 5 | 2025-07-24..2025-08-07 | -1.99 | -0.32% | -1.10% |
| 6 | 2025-08-07..2025-08-21 | 0.70 | 0.13% | -0.77% |
| 7 | 2025-08-21..2025-09-04 | -6.87 | -1.16% | -1.38% |
| 8 | 2025-09-04..2025-09-18 | 4.00 | 0.42% | -0.36% |
| 9 | 2025-09-18..2025-10-02 | -7.50 | -1.04% | -1.18% |
| 10 | 2025-10-02..2025-10-16 | -3.71 | -1.06% | -1.86% |
| 11 | 2025-10-16..2025-10-30 | -5.65 | -0.95% | -1.12% |
| 12 | 2025-10-30..2025-11-13 | -4.66 | -1.13% | -2.09% |
| 13 | 2025-11-13..2025-11-27 | 0.02 | -0.01% | -1.43% |
| 14 | 2025-11-27..2025-12-11 | -8.22 | -1.42% | -1.79% |
| 15 | 2025-12-11..2025-12-25 | -0.01 | -0.01% | -0.71% |
| 16 | 2025-12-25..2026-01-08 | -1.22 | -0.12% | -0.54% |
| 17 | 2026-01-08..2026-01-22 | 1.33 | 0.21% | -0.96% |
| 18 | 2026-01-22..2026-02-05 | -8.79 | -2.98% | -3.08% |
| 19 | 2026-02-05..2026-02-19 | -3.62 | -1.14% | -2.24% |
| 20 | 2026-02-19..2026-03-05 | 0.07 | 0.01% | -1.44% |
| 21 | 2026-03-05..2026-03-19 | -4.67 | -0.78% | -0.84% |
| 22 | 2026-03-19..2026-04-02 | -6.86 | -1.14% | -1.59% |
| 23 | 2026-04-02..2026-04-16 | 0.23 | 0.03% | -0.55% |
| 24 | 2026-04-16..2026-04-30 | 1.60 | 0.22% | -0.73% |
| 25 | 2026-04-30..2026-05-14 | -2.96 | -0.33% | -0.78% |
| 26 | 2026-05-14..2026-05-28 | -13.22 | -1.75% | -2.06% |
| 27 | 2026-05-28..2026-06-11 | -1.52 | -0.40% | -1.98% |
| 28 | 2026-06-11..2026-06-25 | -3.31 | -0.52% | -1.03% |
| 29 | 2026-06-25..2026-07-09 | 1.98 | 0.34% | -0.66% |
| 30 | 2026-07-09..2026-07-23 | -3.00 | -0.32% | -0.54% |
| 31 | 2026-07-23..2026-08-06 | -2.06 | -0.24% | -0.73% |
| 32 | 2026-08-06..2026-08-20 | -1.33 | -0.10% | -0.42% |
| 33 | 2026-08-20..2026-09-03 | -2.83 | -0.36% | -0.61% |
| 34 | 2026-09-03..2026-09-17 | -5.08 | -0.62% | -1.11% |

Only 10 of 35 folds have positive OOS Sharpe. Median −2.28.

## Gates (trade-overfit standard preset, DSR N=2)

| gate | value | threshold | pass |
|------|-------|-----------|------|
| deflated_sharpe | 0.0000 | gte 0.95 | FAIL |
| oos_sharpe | -2.2755 | gt 1.0 | FAIL |
| max_drawdown | -0.1567 | gt -0.15 | FAIL |
| regime_stability | -6.7567 | gt 0.0 | FAIL |
| beats_benchmark_net | 0.0838 | gt 0.0 | PASS |

## Notes

- DSR inputs: Sharpe_hat=−2.5219, n_obs=141120, n_trials=2
  ([0.666, −2.5219]), skew=0.14, excess_kurt=95.91; expected Sharpe under
  null = 1.1716 → DSR 0.0.
- Strategy annualized (OOS): −11.43%. BTC buy-and-hold annualized net of
  6 bps/side entry+exit over the same span: −19.81%. The benchmark gate
  passes only because the benchmark lost more — losing less than a
  −20%/yr benchmark is not an edge.
- Regime splits (desk vol-regime, 5m default): calm Sharpe −6.76
  (n=70,562), stress Sharpe −2.70 (n=70,558). Negative in both regimes.
- Costs are in-engine (6 bps/side); the OOS series is already net.
- 2,299 LONG / 2,299 EXIT — every opened position was closed; no orphans.
- No invalid runs: the harness was validated on synthetic bars (`--smoke`)
  before the real pull, and the single live run completed without errors.
- Pre-registered spec honored throughout: frozen parameters, Binance.US
  primary venue, cost model, fold geometry, DSR N=2, five gates. The only
  deviation is the data range (venue limitation, documented above).
- **Verdict rationale:** killed for negative risk-adjusted returns, not
  for the data shortfall — 4 of 5 gates fail decisively on 141k OOS bars.
