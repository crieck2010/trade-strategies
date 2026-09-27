# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-09-27

### Added
- `trade_strategies.gates.cost_speed_limit`: Tier-1 gate 6 — Carver's
  cost speed limit. `evaluate_cost_speed_limit()` (single instrument)
  and `evaluate_cost_speed_limit_multi()` (notional-weighted
  multi-instrument) return plain-data dicts with every intermediate
  (`cost_sharpe_drag = turnover_ann × round_trip_cost /
  instrument_vol_ann`, `budget = gross_sharpe / 3`; PASS iff
  `gross_sharpe > 0` and drag ≤ budget). Invalid inputs fail closed.
  `cost_speed_limit_gate()` is a thin adapter onto
  `trade_overfit.gates.Gate` (lazy import; repo stays dependency-free).
- `docs/validation/GATES.md`: Tier-1 gate-6 section with "The maths"
  derivation, Carver's worked examples (cheap futures ~65 round
  trips/yr, BTC ~26), multi-instrument weighting, machine-readable
  evidence fields for `tier1_evidence.json`, and the grandfathering
  rule (applies to trials pre-registered after 2026-09-27; REGCOND-1's
  Tier-1 validation stands as recorded).
- 51 tests: Carver regression examples, boundary, monotonicity,
  multi-instrument weighting, fail-closed inputs, adapter agreement.

## [0.1.0] - 2026-09-23

### Added
- `Strategy` / `SingleAssetStrategy` ABCs: bars in, signals out; edge-triggered
  signals with conviction `strength`; structural bar inputs (dicts or objects).
- `indicators`: pure stdlib functions — SMA, EMA, stdev, ROC, z-score, RSI
  (Wilder), MACD, Bollinger (%b, bandwidth), ATR, stochastic, OBV, rolling
  VWAP, Donchian, Keltner, ADX, cross helpers.
- 19 strategies across 7 families: trend (5), mean reversion (4), momentum (1),
  volatility (2), volume (2), multi-asset (2), meta (3: trailing-stop overlay,
  ADX regime filter, voting ensemble).
- `registry`: `STRATEGY_REGISTRY`, `list_strategies`, `list_families`,
  `get_strategy`, agent-facing `describe_strategies()`.
- `adapters`: lazy `trade-backtest` bridge — `to_backtest_strategy()` and
  one-call `run_backtest()`.
- Examples: `quickstart.py`, `parameter_sweep.py`.
- 54 tests; README with full strategy catalog and interop/scaling notes.
