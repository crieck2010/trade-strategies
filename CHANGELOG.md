# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
