# INVALID RUN — 2026-09-27_zero-oos-folds

Root cause: ZERO walk-forward folds fit the frozen geometry on the frozen venue's data. Geometry needs 915 daily returns for a single fold (728d train + 5d embargo + 182d test); the venue serves 719 daily bars -> 718 returns. The concatenated OOS series (the gated series) is empty, so none of the 7 gates can be evaluated. This is a data/geometry incompatibility, not a strategy result: no PASS/KILL verdict is possible without changing the frozen spec.

## What ran

- Venue decision: Kraken (frozen per pre-registered completeness rule)
- Backtest: continuous single run, t+1-open fills, 25 bps/side all-in, final equity 108,477.45 (diagnostic only — in-sample on the venue's short window, NOT gated)
- Walk-forward: 0 folds fit the frozen geometry

## What is missing

- The concatenated OOS series is empty; the 7 gates (DSR, OOS Sharpe, maxDD, regime Sharpe, benchmark excess, Sortino, Calmar) cannot be evaluated. No PASS/KILL verdict exists for this run.

## Fix status

No spec-consistent fix exists: every remedy (shorter train window, accepting the Binance.US hole, another data source) changes the frozen spec (geometry, venue rule, or universe/data). Re-running requires a dated amendment from the user before any new data pull — recorded here as outstanding, not applied.

## Cost sensitivity (report-only, full diagnostic series)

| bps/side | final equity | total return | Sharpe(365) | maxDD | trades |
|---|---|---|---|---|---|
| 10 | 110,635.26 | 0.1064 | 0.483 | -0.1957 | 42 |
| 25 | 108,477.45 | 0.0848 | 0.400 | -0.2070 | 42 |
| 50 | 104,970.87 | 0.0497 | 0.263 | -0.2254 | 42 |
