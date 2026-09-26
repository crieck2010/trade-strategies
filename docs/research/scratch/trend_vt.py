"""RESEARCH SCRATCH — TREND-VT: vol-targeted multi-asset time-series momentum.

NOT a strategy module. Phase B screening implementation (2026-09-26).

On 6 liquid ETFs (SPY equities, TLT bonds, GLD gold, USO oil, EFA
developed-ex-US, VNQ REITs): monthly, go long/flat/short each by the sign
of its trailing 252-trading-day return, sizing each leg to equal
volatility contribution: w_i = sign_i * (TARGET_VOL / n) / vol_i with
TARGET_VOL = 10% annualized, vol_i = 60d daily vol annualized. Gross is
left wherever the vol targeting puts it (documented, typically ~0.5-1.2).

Simplifications (documented):
  - 6 ETFs (spec range 4-8); no TIPS/commodities-basket legs.
  - Trading-day 252/60 windows for 12m/3m.
  - No gross cap / leverage control beyond the vol formula.
  - yfinance continuous ETF series; USO reverse-split handled by adjustment.
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

IDEA_ID = "TREND-VT"
PARAMS = {"etfs": ["SPY", "TLT", "GLD", "USO", "EFA", "VNQ"],
          "trend_lookback": 252, "vol_window": 60, "target_vol": 0.10}
SIMPLIFICATIONS = [
    "6-ETF set; no TIPS/broad-commodity legs",
    "252/60 trading-day windows",
    "no gross/leverage cap; gross floats with vol targeting",
]
THESIS_LINE = ("Managed-futures at retail scale (Moskowitz-Ooi-Pedersen): "
               "cross-asset time-series momentum + vol targeting + crisis "
               "alpha from bond/gold legs.")


def prepare(panel: dict) -> dict:
    etfs = PARAMS["etfs"]
    dates = sorted(d for d in panel["SPY"]
                   if common.TRADE_START <= d < common.TRADE_END)
    closes = {e: [panel[e][d][3] for d in dates] for e in etfs}
    ok = all(all(c == c and c > 0 for c in cs) for cs in closes.values())
    print(f"[trend] etfs: {etfs}, clean={ok}, {len(dates)} days", flush=True)
    return {"closes": closes, "dates": dates,
            "rebal": [d for d in common.month_rebalances(dates)
                      if d >= "2019-01-01"]}


class TrendVTStrategy(common.TargetStrategy):
    def __init__(self, ctx):
        super().__init__(PARAMS["etfs"])
        self.ctx = ctx
        self._rebal_set = set(ctx["rebal"])
        self._cur: dict[str, float] = {}

    def compute_targets(self, timestamp, closes):
        d = timestamp.strftime("%Y-%m-%d")
        if d in self._rebal_set:
            ctx, dates = self.ctx, self.ctx["dates"]
            i = dates.index(d)
            n = len(self.symbols)
            tgt = {}
            for e in self.symbols:
                cs = ctx["closes"][e][: i + 1]
                tr = common.trailing_return(cs, 252)
                rets = [cs[j] / cs[j - 1] - 1.0
                        for j in range(max(1, len(cs) - 60), len(cs))]
                vol = common.stdev(rets) * math.sqrt(252)
                if tr is None or vol <= 0:
                    continue
                sign = 1.0 if tr > 0 else (-1.0 if tr < 0 else 0.0)
                tgt[e] = sign * (0.10 / n) / vol
            self._cur = tgt
        return {s: self._cur.get(s, 0.0) for s in self.symbols}


def build(ctx):
    strat = TrendVTStrategy(ctx)
    return {"strategy": strat, "sizer": common.TargetsSizer(strat),
            "costs": common.equity_costs(), "symbols": strat.symbols,
            "bars": None,
            "note": "yfinance ETF daily, split/div adjusted; basis=pre_adjusted; "
                    "5 bps/side commission; no borrow (long/flat/short ETF)."}
