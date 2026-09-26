# DON-20/10-ATR validation — trial 1 of 1

Pre-registered spec: [PRE-REGISTRATION.md](PRE-REGISTRATION.md) (committed
2026-09-26 21:13 UTC, before any market data was touched).

## Runs

| run | time (UTC) | status | cause |
|-----|-----------|--------|-------|
| invalid-run1 | 21:21 | **INVALID** | Split double-adjustment: Yahoo pre-adjusts splits server-side; the client divided pre-split prices again, fabricating ~N:x jumps on ex-dates. Fixed in trade-data-equities (`get_splits` → `[]`). |
| invalid-run2 | 21:25 | **INVALID** | Harness sizer compared `signal.action` against `trade_backtest.models.SignalAction` while the strategy emits `trade_strategies.base.SignalAction` — distinct Enum classes, so `==` was always False and every EXIT became a ~100%-of-equity BUY. Fixed by importing the strategy's own enum. |
| evidence.json / report.md | 21:36 | **VALID — verdict: KILL** | The one trial. 2 of 5 gates failed (median OOS Sharpe 0.87 < 1.0; OOS max drawdown −40.2% > 15% limit). |

Neither invalid run tested the strategy; both are archived untouched for
provenance. The strategy spec, parameters, and implementation
(`src/trade_strategies/donchian_swing.py`) are byte-identical across all
three runs.

## Reproduce

```bash
PYTHONPATH=src:../trade-backtest/src:../trade-data-equities/src:../trade-overfit/src \
  python docs/validation/donchian-20-10/run_validation.py
```

Needs network (yfinance) and the `yfinance`, `pandas`, `lxml` packages.
Writes `evidence.json` (machine-readable: universe, folds, DSR inputs,
gates, verdict) and `report.md`.

## Limitations (carried from the pre-registration)

- yfinance daily data; current-constituent **survivorship bias (upward)** —
  today's S&P 500 omits delisted failures.
- One US large-cap market, daily bars only; no intraday behavior modeled.
- Costs: 5 bps/side slippage; zero commission/spread (approximate).
- Gates reduce overfitting risk; they do not eliminate it. Past performance
  does not predict future returns.
