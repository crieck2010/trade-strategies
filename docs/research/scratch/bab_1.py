"""RESEARCH SCRATCH — BAB-1: betting against beta (long low-beta, short high-beta).

NOT a strategy module. Phase B screening implementation (2026-09-26).

Monthly: estimate 252-trading-day beta vs SPY for liquid US large caps;
long the bottom-beta tercile, short the top-beta tercile, equal-weighted
within terciles. Beta-neutral scaling: with bL = mean beta of longs,
bH = mean beta of shorts, allocate L = bH/(bL+bH) of equity long and
S = bL/(bL+bH) short (gross = 1.0, portfolio beta ~ 0).

Simplifications (documented):
  - Beta from 252d daily OLS vs SPY (no shrinkage / no Dimson).
  - Terciles of the available full-coverage universe.
  - Beta-neutral via tercile-mean betas, not per-name hedge ratios; no
    explicit leverage on the long leg beyond the L/S split.
  - First-trading-day-of-month rebalance; survivorship-biased universe.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

IDEA_ID = "BAB-1"
PARAMS = {"beta_lookback": 252, "gross": 1.0}
SIMPLIFICATIONS = [
    "252d OLS beta vs SPY, no shrinkage",
    "terciles of available universe",
    "beta-neutral via tercile-mean beta split (L=bH/(bL+bH), S=bL/(bL+bH))",
    "survivorship-biased universe",
]
THESIS_LINE = ("Frazzini-Pedersen (2014): leverage-constrained investors "
               "overpay for high-beta lottery tickets; low-beta wins "
               "risk-adjusted. Structural, tied to institutional constraints.")


def _beta(rx: list[float], ry: list[float]) -> float | None:
    n = min(len(rx), len(ry))
    if n < 200:
        return None
    rx, ry = rx[-n:], ry[-n:]
    mx, my = sum(rx) / n, sum(ry) / n
    var = sum((y - my) ** 2 for y in ry)
    if var <= 0:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(rx, ry)) / var


def prepare(panel: dict) -> dict:
    full = sorted(d for d in panel["SPY"]
                  if "2015-01-01" <= d < common.TRADE_END)
    uni = [t for t, s in panel.items()
           if t != "SPY" and not t.startswith(("FUT_", "FX_"))
           and sum(1 for d in full if d in s) >= 0.95 * len(full)]
    closes = common.aligned_closes(panel, full, uni)
    spy = [panel["SPY"][d][3] for d in full]
    trade_dates = [d for d in full if d >= common.TRADE_START]
    print(f"[bab] universe: {len(closes)} tickers", flush=True)
    return {"closes": closes, "spy": spy, "dates": full,
            "rebal": [d for d in common.month_rebalances(trade_dates)
                      if d >= "2019-01-01"]}


class BABStrategy(common.TargetStrategy):
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
            spy_r = [ctx["spy"][j] / ctx["spy"][j - 1] - 1.0
                     for j in range(max(1, i - 251), i + 1)]
            scored = []
            for t, cs in ctx["closes"].items():
                r = [cs[j] / cs[j - 1] - 1.0
                     for j in range(max(1, i - 251), i + 1)]
                b = _beta(r, spy_r)
                if b is not None:
                    scored.append((b, t))
            scored.sort()
            n = max(1, len(scored) // 3)
            longs = scored[:n]
            shorts = scored[-n:]
            bL = sum(b for b, _ in longs) / len(longs)
            bH = sum(b for b, _ in shorts) / len(shorts)
            # beta-neutral split; guard degenerate betas
            if bL <= 0.05 or bH <= 0.05:
                L, S = 0.5, 0.5
            else:
                L, S = bH / (bL + bH), bL / (bL + bH)
            cur = {t: L / len(longs) for _, t in longs}
            cur.update({t: -S / len(shorts) for _, t in shorts})
            self._cur = cur
        return {s: self._cur.get(s, 0.0) for s in self.symbols}


def build(ctx):
    strat = BABStrategy(ctx)
    return {"strategy": strat, "sizer": common.TargetsSizer(strat),
            "costs": common.equity_costs(), "symbols": strat.symbols,
            "bars": None,
            "note": "yfinance daily, split/div adjusted; basis=pre_adjusted; "
                    "5 bps/side commission; 50 bps/yr borrow."}
