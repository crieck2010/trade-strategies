# MR-5M validation — trial 2 of 2

Pre-registered spec: [PRE-REGISTRATION.md](PRE-REGISTRATION.md) (committed
2026-09-26 22:05 UTC, before any OHLC was pulled).

## Runs

| run | time (UTC) | status | cause |
|-----|-----------|--------|-------|
| evidence.json / report.md | 22:48 | **VALID — verdict: KILL** | The one trial. 4 of 5 gates failed (DSR 0.00; median OOS Sharpe −2.28; max drawdown −15.67%; worst-regime Sharpe −6.76). Only beats-benchmark passed (+8.38%/yr vs a −19.81%/yr BTC buy-and-hold — losing less than the benchmark is not an edge). |

No invalid runs: the harness was validated on synthetic bars (`--smoke`)
before the live pull, and the single live run completed without errors.

**Data-range deviation (documented, not tuned):** the spec assumed
2024-01-01 through 2026-09-25, but Binance.US serves no 5-minute klines
between ~2023-09 and 2025-02-19T13:00Z for BTCUSD/ETHUSD (venue hole from
its 2023–2024 disruption, confirmed by direct API probes). The run uses
the maximum continuous history the pre-registered venue offers:
167,928 bars/symbol, 2025-02-19 .. 2026-09-25, 35 walk-forward folds.

## Reproduce

PRE-REGISTRATION.md
evidence.json
report.md
run_validation.py
