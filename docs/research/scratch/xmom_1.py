"""RESEARCH SCRATCH — XMOM-1: cross-sectional momentum 12-1, dollar-neutral.

NOT a strategy module. Phase B screening implementation (2026-09-26).

Monthly: rank liquid US large caps on trailing 252-trading-day return
skipping the most recent 21 trading days; long top decile, short bottom
decile, equal-weighted, dollar-neutral (50% gross each side), hold 1 month.

Simplifications (documented):
  - Trading days (252/21) stand in for calendar 12-1 months.
  - Deciles of the available full-coverage universe (~250 names -> 25/25).
  - Rebalance on the first trading day of each month; no turnover control.
  - Survivorship bias: today's liquid large caps (delisted names absent).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

IDEA_ID = "XMOM-1"
PARAMS = {"lookback": 252, "skip": 21, "decile": 0.10, "gross": 1.0}
SIMPLIFICATIONS = [
    "252/21 trading days for 12-1 calendar months",
    "deciles of available universe (no fixed count)",
    "first-trading-day-of-month rebalance, no turnover control",
    "survivorship-biased universe",
]
THESIS_LINE = ("Classic Jegadeesh-Titman cross-sectional momentum: slow "
               "information diffusion + herding keeps winners winning 3-12m.")


def prepare(panel: dict) -> dict:
    full = sorted(d for d in panel["SPY"]
                  if "2015-01-01" <= d < common.TRADE_END)
    uni = [t for t, s in panel.items()
           if t != "SPY" and not t.startswith(("FUT_", "FX_"))
           and sum(1 for d in full if d in s) >= 0.95 * len(full)]
    closes = common.aligned_closes(panel, full, uni)
    trade_dates = [d for d in full if d >= common.TRADE_START]
    print(f"[xmom] universe: {len(closes)} tickers", flush=True)
    return {"closes": closes, "dates": full, "trade_dates": trade_dates,
            "rebal": [d for d in common.month_rebalances(trade_dates)
                      if d >= "2019-01-01"]}


class XMOMStrategy(common.TargetStrategy):
    def __init__(self, ctx):
        super().__init__(sorted(ctx["closes"]))
        self.ctx = ctx
        self._rebal_set = set(ctx["rebal"])
        self._cur: dict[str, float] = {}

    def compute_targets(self, timestamp, closes):
        d = timestamp.strftime("%Y-%m-%d")
        if d in self._rebal_set:
            ctx, dates = self.ctx, self.ctx["dates"]
            i = dates.index(d)
            scored = []
            for t, cs in ctx["closes"].items():
                hist = cs[:i + 1]
                r = common.trailing_return(hist, 252, skip=21)
                if r is not None:
                    scored.append((r, t))
            scored.sort()
            n = max(1, int(len(scored) * 0.10))
            longs = [t for _, t in scored[-n:]]
            shorts = [t for _, t in scored[:n]]
            if longs and shorts:  # empty early in history -> hold
                wl, ws = 0.5 / len(longs), 0.5 / len(shorts)
                self._cur = {t: wl for t in longs}
                self._cur.update({t: -ws for t in shorts})
        return {s: self._cur.get(s, 0.0) for s in self.symbols}


def build(ctx):
    strat = XMOMStrategy(ctx)
    return {"strategy": strat, "sizer": common.TargetsSizer(strat),
            "costs": common.equity_costs(), "symbols": strat.symbols,
            "bars": None,
            "note": "yfinance daily, split/div adjusted; basis=pre_adjusted; "
                    "5 bps/side commission; 50 bps/yr borrow."}
