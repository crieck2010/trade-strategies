"""RESEARCH SCRATCH — REGCOND-1: copper:gold regime-conditioned cross-asset tilt.

NOT a strategy module. Round-2 Phase B screening implementation (2026-09-26).

Thesis: use the copper:gold regime (EXPANSION / CONTRACTION / NEUTRAL,
z-scored ratio with whipsaw control) as a discrete allocation switch:
  EXPANSION   -> 60% SPY / 20% CPER / 20% TLT
  CONTRACTION -> 20% SPY / 40% TLT / 40% GLD
  NEUTRAL     -> 25% SPY / 25% CPER / 25% TLT / 25% GLD
Rebalance monthly on the regime label; fixed weights per regime — no vol
targeting, no trailing-return signal.

Regime mechanics (trade-macro, no lookahead):
  - ratio = CPER/GLD (ETF proxies for copper/gold), daily adjusted closes.
  - enrich_ratios: ratio_ma200, z_252 (trailing, z_min_periods=63) — all
    computed from data available at or before each date.
  - classify_regime preset="standard": leave NEUTRAL only when |z|>1.0 AND
    ratio beyond its 200d MA, sustained persist_days=5 sessions.
  - Rebalance on the first trading day of month M reads the regime label
    at the LAST trading day of month M-1.

Simplifications (documented):
  - CPER/GLD ETF proxies instead of HG/GC futures (trade-macro's "etf"
    source trade-off: expense drag + tracking error vs purity). The
    thesis names either; the screen uses ETFs for data cleanliness.
  - preset="standard" (thesis unspecified); single preset, no preset mining.
  - Long-only, no leverage; 5 bps/side.
"""

from __future__ import annotations

import os
import sys

_SCRATCH2 = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_SCRATCH2), "..", "scratch"))  # round-1 common
sys.path.insert(0, "/home/hatch/workspace/trade-suite/trade-macro/src")
import common  # noqa: E402

from trade_macro.ratio import enrich_ratios, ratio_series  # noqa: E402
from trade_macro.regime import classify_regime  # noqa: E402

IDEA_ID = "REGCOND-1"
WEIGHTS = {
    "EXPANSION": {"SPY": 0.60, "CPER": 0.20, "TLT": 0.20, "GLD": 0.00},
    "CONTRACTION": {"SPY": 0.20, "CPER": 0.00, "TLT": 0.40, "GLD": 0.40},
    "NEUTRAL": {"SPY": 0.25, "CPER": 0.25, "TLT": 0.25, "GLD": 0.25},
}
PARAMS = {"preset": "standard", "symbols": ["SPY", "CPER", "TLT", "GLD"]}
SIMPLIFICATIONS = [
    "CPER/GLD ETF proxies for copper/gold (not HG/GC futures)",
    "classify_regime preset='standard', single preset",
    "rebalance on first trading day of month using prior-month-end label",
    "long-only; 5 bps/side",
]
THESIS_LINE = ("Macro-conditioned allocation: copper:gold regime switches "
               "fixed SPY/CPER/TLT/GLD weights; harvests cycle rotation "
               "without trailing-return signals.")


def prepare(panel: dict) -> dict:
    dates = sorted(set(panel["CPER"]) & set(panel["GLD"]))
    copper = [{"date": d, "price": panel["CPER"][d][3]} for d in dates]
    gold = [{"date": d, "price": panel["GLD"][d][3]} for d in dates]
    rows = classify_regime(
        enrich_ratios(ratio_series(copper, gold)), preset=PARAMS["preset"])
    label = {r["date"]: r["regime"] for r in rows}

    trade_dates = sorted(d for d in dates
                         if common.TRADE_START <= d < common.TRADE_END)
    rebal = common.month_rebalances(trade_dates)
    # first-month label lookup needs prior-month-end; build month-end map
    month_end: dict[str, str] = {}
    for d in dates:
        month_end[d[:7]] = d
    months = sorted(month_end)
    pm_end = {m: month_end[months[k - 1]] if k > 0 else None
              for k, m in enumerate(months)}

    sched: dict[str, str] = {}  # rebalance date -> regime label
    for d in rebal:
        pm = pm_end[d[:7]]
        sched[d] = label.get(pm, "NEUTRAL") if pm else "NEUTRAL"
    from collections import Counter
    print(f"[regcond] {len(rows)} ratio days, regimes: {dict(Counter(label.values()))}, "
          f"{len(sched)} rebalances", flush=True)
    return {"trade_dates": trade_dates, "sched": sched}


class RegCondStrategy(common.TargetStrategy):
    def __init__(self, ctx):
        super().__init__(PARAMS["symbols"])
        self.ctx = ctx
        self._cur: dict[str, float] = {}

    def compute_targets(self, timestamp, closes):
        d = timestamp.strftime("%Y-%m-%d")
        if d in self.ctx["sched"]:
            w = WEIGHTS[self.ctx["sched"][d]]
            self._cur = {s: w.get(s, 0.0) for s in self.symbols}
        return {s: self._cur.get(s, 0.0) for s in self.symbols}


def build(ctx):
    strat = RegCondStrategy(ctx)
    return {"strategy": strat, "sizer": common.TargetsSizer(strat),
            "costs": common.equity_costs(), "symbols": strat.symbols,
            "bars": None,
            "note": ("yfinance ETF daily, split/div adjusted; basis=pre_adjusted; "
                     "5 bps/side commission; long-only, no borrow. "
                     "Regime via trade-macro copper:gold (CPER/GLD), "
                     "preset=standard, trailing statistics only.")}
