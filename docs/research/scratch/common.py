"""RESEARCH SCRATCH — shared harness for Phase B idea screening (2026-09-26).

NOT a strategy module. Throwaway research code: minimal implementations run
ONE in-sample backtest each through trade-backtest. No gates, no walk-forward,
no DSR — screening is deliberately loose (documented design).

Conventions used by every idea module in this directory:
  - IDEA_ID, PARAMS, SIMPLIFICATIONS, THESIS_LINE module attributes
  - prepare(panel) -> ctx      : precompute anything (screens, factor series)
  - build(ctx) -> (strategy, sizer, cost_model, symbols, notes)
"""

from __future__ import annotations

import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SUITE = "/home/hatch/workspace/trade-suite"
for _repo in ("trade-backtest", "trade-data-equities", "trade-data-crypto",
              "trade-data-futures", "trade-factors", "trade-pairs",
              "trade-sentiment"):
    _p = os.path.join(_SUITE, _repo, "src")
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ---------------------------------------------------------------------------
# screening-wide constants
# ---------------------------------------------------------------------------

TRADE_START = "2018-01-01"   # in-sample window start (trading)
TRADE_END = "2026-09-26"     # provider [start, end): includes all 2026-09-25 bars
INITIAL_CASH = 100_000.0
EQUITY_BPS_PER_SIDE = 5.0    # light but nonzero, per brief
CRYPTO_BPS_PER_SIDE = 25.0   # brief-authorized choice (see tsmom_cr.py)
PERIODS_PER_YEAR = 252

SCRATCH = _HERE
EVIDENCE = os.path.join(os.path.dirname(_HERE), "evidence")


# ---------------------------------------------------------------------------
# costs
# ---------------------------------------------------------------------------

def equity_costs(bps: float = EQUITY_BPS_PER_SIDE):
    """5 bps/side via commission only; 50 bps/yr borrow on shorts (default)."""
    from trade_backtest.costs import CostModel
    from trade_backtest.execution import PercentCommission
    return CostModel(
        commission=PercentCommission(bps / 10_000.0),
        slippage_entry_bps=0.0,
        slippage_exit_bps=0.0,
        half_spread_bps=0.0,
        borrow_cost_annual_bps=50.0,  # engine default; large-cap GC ~ realistic
    )


def crypto_costs(bps: float = CRYPTO_BPS_PER_SIDE):
    """25 bps/side all-in via commission only; no borrow (long/flat spot)."""
    from trade_backtest.costs import CostModel
    from trade_backtest.execution import PercentCommission
    return CostModel(
        commission=PercentCommission(bps / 10_000.0),
        slippage_entry_bps=0.0,
        slippage_exit_bps=0.0,
        half_spread_bps=0.0,
        borrow_cost_annual_bps=0.0,
    )


# ---------------------------------------------------------------------------
# strategy / sizer pair: strategy publishes target fractions, sizer obeys
# ---------------------------------------------------------------------------

def _load_backtest():
    from trade_backtest.strategy import Strategy
    from trade_backtest.models import Signal, SignalAction
    from trade_backtest.portfolio import PositionSizer
    return Strategy, Signal, SignalAction, PositionSizer


class TargetStrategy:
    """Base: compute target fraction-of-equity per symbol; emit on change only.

    Subclasses implement compute_targets(timestamp, closes) -> dict[symbol, frac].
    ``closes`` maps symbol -> close price at this bar (only symbols with bars).
    Signals are LONG/SHORT/EXIT; the sizer reads self.targets for sizing.
    Emitting only on change avoids daily churn from equity drift.
    """

    def __init__(self, symbols: list[str]):
        Strategy, Signal, SignalAction, _ = _load_backtest()
        self._Strategy = Strategy
        self._Signal = Signal
        self._SignalAction = SignalAction
        # emulate Strategy.__init__ without inheriting (keeps this file ABC-free)
        self.symbols = [s.strip().upper() for s in symbols]
        if not self.symbols:
            raise ValueError("strategy needs at least one symbol")
        self.targets: dict[str, float] = {}
        self._emitted: dict[str, float] = {}

    def compute_targets(self, timestamp, closes: dict[str, float]) -> dict[str, float]:
        raise NotImplementedError

    def on_bar(self, timestamp, bars):
        closes = {s: b.close for s, b in bars.items()}
        new = self.compute_targets(timestamp, closes)
        self.targets = {s: new.get(s, 0.0) for s in self.symbols}
        Signal = self._Signal
        SA = self._SignalAction
        out = []
        for sym in self.symbols:
            if sym not in bars:
                continue  # no bar -> no signal possible (portfolio would raise)
            old = self._emitted.get(sym, 0.0)
            newt = self.targets[sym]
            changed = (old == 0.0) != (newt == 0.0) or (
                old != 0.0 and newt != 0.0 and abs(newt - old) > 1e-9)
            if changed:
                action = SA.LONG if newt > 0 else (SA.SHORT if newt < 0 else SA.EXIT)
                out.append(Signal(symbol=sym, timestamp=timestamp, action=action))
                self._emitted[sym] = newt
        return out


class TargetsSizer:
    """Size = strategy.targets[symbol] * equity / price. EXIT -> flat."""

    def __init__(self, strategy: TargetStrategy):
        _, _, SignalAction, PositionSizer = _load_backtest()

        class _Sizer(PositionSizer):
            def size(self, signal, price, portfolio):
                if signal.action is SignalAction.EXIT:
                    return 0.0
                tgt = strategy.targets.get(signal.symbol, 0.0)
                if tgt == 0.0 or price <= 0:
                    return 0.0
                return tgt * portfolio.equity / price

        self._sizer = _Sizer()

    def __getattr__(self, name):
        return getattr(self._sizer, name)


# ---------------------------------------------------------------------------
# engine runner
# ---------------------------------------------------------------------------

def run_backtest(symbols: list[str], bars_by_symbol: dict[str, list[dict]],
                 strategy: TargetStrategy, sizer, cost_model,
                 note: str, start: str = TRADE_START, end: str = TRADE_END):
    """bars_by_symbol: symbol -> [{ts(datetime), o,h,l,c, v}]; window [start,end)."""
    from trade_backtest.models import Bar as EngineBar
    from trade_backtest.data import ListDataHandler
    from trade_backtest.portfolio import Portfolio
    from trade_backtest.engine import BacktestEngine
    from trade_backtest.execution import SimulatedExecutionHandler

    engine_bars = []
    for sym in symbols:
        for b in bars_by_symbol.get(sym, []):
            ts = b["ts"]
            if not (start <= ts.strftime("%Y-%m-%d") < end):
                continue
            engine_bars.append(EngineBar(
                symbol=sym, timestamp=ts,
                open=float(b["o"]), high=float(b["h"]),
                low=float(b["l"]), close=float(b["c"]),
                volume=float(b.get("v", 0.0)),
            ))
    engine = BacktestEngine(
        data=ListDataHandler(engine_bars),
        strategy=strategy,  # duck-typed: needs .symbols + .on_bar
        portfolio=Portfolio(INITIAL_CASH, sizer, cost_model=cost_model),
        execution=SimulatedExecutionHandler(cost_model=cost_model),
        adjustment_basis="pre_adjusted",
        adjustment_note=note,
    )
    return engine.run()


def metrics_summary(result) -> dict:
    m = dict(result.metrics)
    return {
        "total_return": m.get("total_return"),
        "cagr": m.get("cagr"),
        "sharpe_ratio": m.get("sharpe_ratio"),
        "sortino_ratio": m.get("sortino_ratio"),
        "max_drawdown": m.get("max_drawdown"),
        "num_trades": m.get("num_trades"),
        "win_rate": m.get("win_rate"),
        "profit_factor": m.get("profit_factor"),
        "final_equity": result.final_equity,
    }


# ---------------------------------------------------------------------------
# small date / series helpers
# ---------------------------------------------------------------------------

def aligned_closes(panel: dict, spy_dates: list[str],
                 tickers: list[str]) -> dict[str, list[float]]:
    """Close series aligned to the SPY date grid with forward-fill.

    Forward-fill is causal (uses only past closes). Tickers with any
    remaining gap (leading NaN) are dropped.
    """
    out = {}
    for t in tickers:
        s = panel.get(t, {})
        vals, last = [], None
        for d in spy_dates:
            if d in s:
                last = s[d][3]
            vals.append(last)
        if all(v is not None and v > 0 for v in vals):
            out[t] = vals
    return out


def month_rebalances(dates: list[str]) -> list[str]:
    """First trading day of each calendar month present in the date list."""
    out, seen = [], set()
    for d in sorted(dates):
        ym = d[:7]
        if ym not in seen:
            seen.add(ym)
            out.append(d)
    return out


def trailing_return(closes: list[float], lookback: int, skip: int = 0) -> float | None:
    """Return over [t-lookback-skip, t-skip]; None when history is short."""
    n = len(closes)
    if n < lookback + skip + 1:
        return None
    base = closes[n - 1 - skip - lookback]
    last = closes[n - 1 - skip]
    if base <= 0:
        return None
    return last / base - 1.0


def stdev(xs: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mu = sum(xs) / n
    return math.sqrt(sum((x - mu) ** 2 for x in xs) / (n - 1))
