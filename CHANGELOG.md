# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-10-07

### Added
- `docs/validation/GATES.md`: "Multiplicity engine" section declaring
  `trade-multitest` (crieck2010/trade-multitest v0.1.0) the canonical
  multiplicity engine — DSR via `trade_multitest.dsr` (honesty rule
  enforced in code), round-level White's Reality Check / Hansen's SPA
  gate (a round both invalidate contributes no allocator candidates),
  Holm step-down baseline, and the `multitest.request.v1` /
  `multitest.report.v1` interchange for trade-agents (Occam's Desk).

### Fixed
- `__init__.__version__` now matches the package version (was 0.3.0
  while pyproject said 0.3.1).

## [0.3.1] - 2026-09-28

### Fixed
- `adapters.run_backtest` now declares `adjustment_basis="pre_adjusted"`
  (with an explicit provider-bars note) for the backtest engine's declared
  basis requirement. No behaviour change; needed by the engine since the
  basis-declaration requirement landed.

## [0.3.0] - 2026-09-28

### Added
- `trade_strategies.regcond_1.RegCond1` (registry name `regcond_1`): the
  executable form of lifecycle candidate REGCOND-1 (Tier-1 validated 5/5,
  status PAPER). Frozen design from
  `docs/validation/regcond-1/PRE-REGISTRATION.md`: monthly copper:gold
  regime tilt across SPY/CPER/TLT/GLD — EXPANSION 60/20/20/0, CONTRACTION
  20/0/40/40, NEUTRAL 25/25/25/25 — rebalanced on the first trading day of
  each month from the persisted label as of the prior month-end (fills at
  the next open, 5 bps/side in the validated evidence). Regime labels come
  from the frozen `trade_macro` pipeline (`ratio_series` → `enrich_ratios`
  → `classify_regime`, `"standard"` preset), imported lazily so the package
  keeps its dependency boundary. Target-weight `Signal` contract: a LONG
  signal's `strength` IS the target portfolio weight, EXIT means weight 0;
  the four signals of a rebalance sum to 1.0. Frozen universe enforced in
  the constructor (exactly SPY/CPER/TLT/GLD); no parameters accepted.
  `production = True` marks it runnable by the pointed trade-paper path.
- `describe_strategies()` demo symbols for `regcond_1` so agent metadata
  describes it fully instead of falling back.
- `docs/validation/regcond-1/fidelity_check.py`: exact-fidelity proof —
  streams the validation's own price grid through `RegCond1`, asserts
  label/decision identity, and replays the strategy's labels through the
  validation's simulator to reproduce the Tier-1 evidence numbers.
- `tests/test_regcond_1.py`: 11 offline unit tests (registry wiring,
  frozen universe/params, weight sums, warmup silence, EXPANSION /
  CONTRACTION / NEUTRAL decisions, prior-month-end decision rule,
  month-boundary-only emission, missing-leg hold policy).

### Fixed
- `__init__.__version__` now matches the package version (was stuck at
  0.1.0 while pyproject said 0.2.0).

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
