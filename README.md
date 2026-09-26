# trade-strategies

A comprehensive, dependency-free library of trading strategies for the
trade-suite ecosystem — from simple moving-average crosses to multi-strategy
ensembles. Pure decision logic: **bars in, signals out**. No NumPy, no pandas,
no backtester import; strategies run anywhere, including inside research agents.

Part of the [trade-suite](https://github.com/crieck2010/trade-suite) project.

## Installation

```bash
pip install trade-strategies
```

To actually backtest a strategy, also install the (optional) engine:

```bash
pip install trade-backtest
```

## Quickstart

```python
from trade_strategies import SMACrossover, describe_strategies, run_backtest

# What can the agents pick from?
for info in describe_strategies():
    print(info["name"], info["family"], info["parameters"])

# bars: dicts (or objects) with timestamp/open/high/low/close/volume
result = run_backtest(SMACrossover(["AAPL"], fast=20, slow=50), bars)
print(result.metrics["sharpe_ratio"], result.num_trades)
```

See `examples/quickstart.py` (library tour + one backtest) and
`examples/parameter_sweep.py` (grid-search tuning, the pattern agents use).

## The strategy contract

```python
class Strategy:
    name = "..."            # registry key
    family = "..."          # trend | mean_reversion | momentum | ...
    description = "..."
    DEFAULT_PARAMS = {...}  # every tunable, with defaults

    def __init__(self, symbols, **params): ...
    def on_bar(self, timestamp, bars) -> list[Signal]: ...
    @property
    def warmup_bars(self) -> int: ...   # bars needed before first signal
```

- **Signals are edge-triggered**: a strategy emits `LONG`/`SHORT`/`EXIT`
  only when its regime *changes*, never a stream of repeats.
- **`Signal.strength`** (0–1) carries conviction; sizers may scale by it.
- **Bars are structural**: dicts, sibling engine bars, or
  `trade_backtest.Bar` all work — anything with
  `timestamp/open/high/low/close/volume` attributes or keys.
- **No lookahead**: signals are computed from bars up to and including bar
  *t*; `trade-backtest` fills them at bar *t+1*'s open.
- Unknown parameters raise `ValueError` immediately (fail fast on typos).

## Strategy catalog

| Strategy | Family | Idea |
|---|---|---|
| `sma_crossover` | trend | Dual-SMA cross |
| `ema_crossover` | trend | Dual-EMA cross (faster) |
| `macd_trend` | trend | MACD line vs signal line regime |
| `donchian_breakout` | trend | Turtle-style channel breakout + faster exit channel |
| `supertrend` | trend | ATR bands that only tighten; flips on genuine breaks |
| `bollinger_reversion` | mean_reversion | Fade band tags, exit at the midline |
| `rsi2_mean_reversion` | mean_reversion | Connors-style RSI(2) washouts above a trend filter |
| `zscore_reversion` | mean_reversion | Fade ±z extremes, cover inside the exit band |
| `stochastic_reversion` | mean_reversion | Buy stochastic washouts, exit on recovery |
| `time_series_momentum` | momentum | Own the sign of the trailing return |
| `keltner_breakout` | volatility | ATR-channel breakout, midline exits |
| `bollinger_squeeze_breakout` | volatility | Trade the resolution of bandwidth compression |
| `obv_trend` | volume | Trend-follow the OBV line's own MA cross |
| `vwap_deviation` | volume | Fade stretches from rolling VWAP |
| `pairs_trading` | multi_asset | Dollar-neutral z-score of the A/B price ratio |
| `cross_sectional_momentum` | multi_asset | Rotate into trailing-return winners (/ short losers) |
| `trailing_stop` | meta | ATR trailing-stop exit overlay for **any** strategy |
| `regime_filter` | meta | ADX switch: trend leg when trending, mean-reversion leg when not |
| `ensemble_vote` | meta | Act only when ≥ N strategies agree per symbol |

Every strategy exposes `get_parameters()` / `describe()` and is reachable
by name via `get_strategy("sma_crossover")` — the surface research agents
use to enumerate, compare, and propose candidates.

## Indicators

`trade_strategies.indicators` holds pure functions over float lists
(SMA, EMA, RSI, MACD, Bollinger, ATR, stochastic, OBV, VWAP, Donchian,
Keltner, ADX, z-score, ROC, …). Agents compose these directly for research
without instantiating a strategy.

## The trade-backtest bridge

`trade_strategies.adapters` is the **only** module that touches
`trade-backtest`, imported lazily so this package stays installable without it:

- `to_backtest_strategy(strategy)` → a `trade_backtest.Strategy` delegating
  to yours, converting signal types.
- `run_backtest(strategy, bars, ...)` → normalize → adapt → run → result.

## Writing a custom strategy

```python
from trade_strategies import SingleAssetStrategy, Signal
from trade_strategies import indicators as ind
from trade_strategies.base import closes

class MyStrategy(SingleAssetStrategy):
    name = "my_strategy"
    family = "trend"
    description = "Does something clever."
    DEFAULT_PARAMS = {"n": 20}

    @property
    def warmup_bars(self): return self.params["n"] + 1

    def on_symbol(self, timestamp, symbol, history):
        c = closes(history)
        ma = ind.sma(c, self.params["n"])
        target = 1 if c[-1] > ma else 0
        regime = self._transition(symbol, target)  # edge-trigger helper
        if regime is None: return None
        return self._signal_for(timestamp, symbol, regime)
```

Register it for the agents with
`trade_strategies.registry.STRATEGY_REGISTRY["my_strategy"] = MyStrategy`.

## Interop & scaling notes

- **Engine/UI split**: this package is pure logic — no UI imports, no I/O.
- **Dependency-free core**: only the stdlib; `adapters` imports
  `trade-backtest` lazily and only when called.
- **Bounded memory**: per-symbol bar history is capped (`history_bars()`);
  long backtests don't grow state without bound.
- **Vectorization path**: indicators are pure functions over sequences —
  swapping the list internals for NumPy later doesn't change the API.
- **Parallelism path**: strategies are stateful per instance but share
  nothing globally; parameter sweeps parallelize by process today
  (`examples/parameter_sweep.py` is trivially shardable).
- **Multi-asset aware**: pairs, cross-sectional rotation, and the meta
  strategies operate across symbols; single-asset strategies loop symbols
  independently.

## Limitations

- Strategies assume fills follow signals (the `trade-backtest` convention);
  `TrailingStop` and the multi-asset strategies track *virtual* positions
  from their own signals, so a fill missed in live trading would desync them.
  A live-trading layer should reconcile against real positions.
- Edge-triggered signals mean a trend already underway when warmup ends
  produces no entry — the cross must be observed.
- No transaction-cost awareness inside strategies; costs live in
  `trade-backtest`'s execution handler.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## The maths

**What you learn.** How raw bars become trading decisions: each strategy is
a small piece of signal arithmetic — a moving-average cross, a z-score
extreme, a volatility-channel break — evaluated bar by bar, emitting an
edge-triggered signal only when its regime *changes*.

**Why it matters.** "Bars in, signals out" with no backtester import means
the maths must stand on its own: inspectable, parameter-explicit, and free
of lookahead by construction. `Signal.strength` (0–1) carries conviction so
sizers downstream can scale by it, and every tunable lives in
`DEFAULT_PARAMS` with unknown-parameter typos failing fast.

**The maths.**

- *Edge-triggered signals*: a strategy tracks its own regime per symbol and
  emits `LONG` / `SHORT` / `EXIT` only on a transition — never a stream of
  repeats. `warmup_bars` gates the first signal so indicators are defined.
- *Z-score reversion*: `z = (price − mean_n) / stdev_n` over the trailing
  window; `zscore_reversion` (defaults: lookback 20, `entry_z=2.0`,
  `exit_z=0.5`) fades ±2σ extremes and covers inside ±0.5σ.
- *Trend*: dual SMA/EMA crosses (e.g. 20/50), MACD line vs. signal line,
  Donchian channel breakouts (highest high / lowest low over N bars), and
  Supertrend — ATR bands that only tighten in the position's favor and flip
  on a genuine close through the band.
- *Mean reversion*: Wilder's RSI (Connors-style RSI(2) washouts above a
  trend filter), Bollinger band tags faded back to the midline, stochastic
  washouts bought on recovery.
- *Volatility / volume*: Keltner ATR-channel breakouts with midline exits,
  Bollinger-bandwidth squeezes traded on resolution, OBV trend-following via
  the OBV line's own moving-average cross, and fades of stretches from a
  rolling VWAP.
- *Multi-asset & meta*: `pairs_trading` trades the z-score of the A/B price
  ratio dollar-neutral; `cross_sectional_momentum` rotates into trailing-
  return winners; `ensemble_vote` acts only when ≥ `min_votes` (default 2)
  member strategies agree per symbol; `trailing_stop` is an ATR-multiple
  exit overlay for any strategy; `regime_filter` uses ADX to switch between
  a trend leg and a mean-reversion leg.
- *No lookahead*: signals use bars up to and including bar *t*; the
  trade-backtest bridge fills them at bar *t+1*'s open.

**Validated-then-killed example: DON-20/10-ATR.** `donchian_swing.py`
implements a pre-registered long/flat swing strategy (Donchian 20-day
breakout entries, 10-day / 2.5×ATR exits, 1% risk per trade, 10% cap per
position, 20 max positions) that was run through the full overfit-gate
protocol once, honestly, on 2026-09-26 — and **killed**. The maths it
exercises:

- *Donchian channel*: entry when `close_t > max(high_{t-20..t-1})`
  (prior window — the current bar never sets its own trigger); exit when
  `close_t < min(low_{t-10..t-1})`.
- *Wilder ATR*: `ATR_t = (ATR_{t-1} × 19 + TR_t) / 20`, the smoothed true
  range; the trailing stop sits `2.5 × ATR` below the entry close.
- *ATR risk sizing*: `fraction = min(10%, 1% / (2.5 × ATR / close))` — one
  percent of equity risked against the stop distance, capped at a tenth of
  equity per name.
- *Walk-forward*: rolling 756-day train / 252-day test / 252-day step with a
  10-day embargo; the concatenated out-of-sample returns are the gating
  series, so no in-sample number ever touches a gate.
- *Deflated Sharpe (DSR)*: asks whether the observed Sharpe survives a
  multiple-testing haircut — here with exactly one trial, so the haircut is
  zero and the DSR is just the ordinary significance of the Sharpe.
- *The five gates*: DSR ≥ 0.95, median OOS Sharpe > 1.0, OOS max drawdown <
  15%, worst volatility-regime Sharpe > 0, and positive excess return vs
  SPY net of costs. Any single failure kills the strategy; there are no
  second runs.

Result: DSR 1.00 (pass), median OOS Sharpe 0.87 (fail), OOS max drawdown
−40.2% (fail), worst-regime Sharpe +0.61 (pass), +4.4%/yr vs SPY net
(pass) — **KILL**, two gates failed. Full evidence (fold table, DSR inputs,
gate table, pre-registration): `docs/validation/donchian-20-10/`. The two
discarded runs are archived there too: run 1 hit a data bug (splits were
double-adjusted), run 2 hit a harness bug (a duplicated `SignalAction`
enum turned every EXIT into a full-equity BUY). Neither ever tested the
strategy; the killed verdict comes from the one valid run.

**Honest limitations.**

- `TrailingStop` and the multi-asset strategies track *virtual* positions
  from their own signals — a missed fill in live trading desyncs them, so
  reconcile against real positions.
- Edge-triggered signals mean a trend already underway when warmup ends
  produces no entry; the cross must be observed.
- No transaction-cost awareness lives inside strategies — costs are the
  execution handler's job in trade-backtest.
- Indicator math is textbook (SMA/EMA/RSI/MACD/ATR); the edge, if any, is in
  the regime logic and parameters, not the formulas.

## License

MIT — see [LICENSE](LICENSE).
