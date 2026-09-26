"""RESEARCH SCRATCH — CARRY-1: FX carry, long high-carry / short low-carry.

NOT a strategy module. Phase B screening implementation (2026-09-26).

Carry measure: trade_data_futures.implied_carry(F, S, T) = ln(F/S)/T with
  F = front-month CME FX futures continuous (6E=F, 6J=F, 6B=F via yfinance),
  S = spot FX in matching quote units (EURUSD=X, 100/USDJPY, GBPUSD=X),
  T = (approximate front-contract expiry - date)/365.25 from
      trade_data_futures.calendar.approximate_expiry (quarterly H/M/U/Z).
Monthly (first trading day): rank the 3 roots by carry; long the highest
(+50%), short the lowest (-50%), middle flat. Positions held in the
continuous front-month series (synthetic symbols FX6E/FX6J/FX6B).

Simplifications (documented):
  - Only 3 FX roots have yfinance continuous tickers (6E/6J/6B); the
    "terciles" are 1 long / 1 short / 1 flat. Thin by construction.
  - 6J quote convention (USD per 100 JPY): S = 100/USDJPY.
  - Front-contract identity from the calendar approximation; yfinance's
    =F roll timing may differ by a few days around expiry.
  - yfinance =F is a vendor-spliced continuous series; roll jumps are
    checked diagnostically (see prepare() print) but not adjusted out.
  - No interest-rate data used: carry is purely the futures/spot basis.
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

IDEA_ID = "CARRY-1"
PARAMS = {"roots": ["6E", "6J", "6B"], "gross": 1.0}
SIMPLIFICATIONS = [
    "3 FX roots only (yfinance continuous coverage); 1 long / 1 short",
    "6J units: S = 100/USDJPY",
    "calendar-approximated front contract; vendor roll timing may differ",
    "carry = futures/spot basis only (no rate data)",
]
THESIS_LINE = ("Forward-rate bias (Bilson 1981): high-yield currencies don't "
               "depreciate as much as rate differentials imply; carry "
               "compensates crash risk. Thin 3-root screen.")


def _front_expiry(root: str, d: str):
    """First quarterly contract with approximate expiry after date d."""
    from trade_data_futures.calendar import approximate_expiry
    y, m, day = int(d[:4]), int(d[5:7]), int(d[8:10])
    for k in range(8):
        mm = ((m - 1 + k * 3) % 12) + 1
        yy = y + (m - 1 + k * 3) // 12
        exp = approximate_expiry(root, yy, mm)
        if (exp.year, exp.month, exp.day) > (y, m, day):
            return exp
    raise AssertionError("no front contract found")


def prepare(panel: dict) -> dict:
    from trade_data_futures.carry import implied_carry

    fut = {r: panel["FUT_" + r] for r in PARAMS["roots"]}
    fx = {"6E": panel["FX_EURUSD=X"], "6J": panel["FX_JPY=X"],
          "6B": panel["FX_GBPUSD=X"]}
    dates = sorted(set(fut["6E"]) & set(fut["6J"]) & set(fut["6B"]) &
                   set(fx["6E"]) & set(fx["6J"]) & set(fx["6B"]))
    dates = [d for d in dates if common.TRADE_START <= d < common.TRADE_END]

    carry: dict[str, dict[str, float]] = {r: {} for r in PARAMS["roots"]}
    for d in dates:
        for r in PARAMS["roots"]:
            F = fut[r][d][3]
            raw = fx[r][d][3]
            S = 100.0 / raw if r == "6J" else raw
            exp = _front_expiry(r, d)
            T = ((exp.year * 365.25 + exp.month * 30.44 + exp.day) -
                 (int(d[:4]) * 365.25 + int(d[5:7]) * 30.44 + int(d[8:10]))) / 365.25
            if F > 0 and S > 0 and T > 1 / 365.25:
                carry[r][d] = implied_carry(F, S, T)

    # diagnostic: worst overnight jump on quarter-boundary months (roll artifacts)
    for r in PARAMS["roots"]:
        cs = [fut[r][d][3] for d in dates]
        worst = 0.0
        for j in range(1, len(cs)):
            if dates[j][5:7] != dates[j - 1][5:7] and dates[j][5:7] in ("03", "06", "09", "12"):
                worst = max(worst, abs(cs[j] / cs[j - 1] - 1.0))
        print(f"[carry] {r}: worst quarter-boundary overnight jump {worst:.4f}",
              flush=True)
    syms = {"6E": "FX6E", "6J": "FX6J", "6B": "FX6B"}
    return {"carry": carry, "fut": fut, "dates": dates, "syms": syms,
            "rebal": [d for d in common.month_rebalances(dates)
                      if d >= "2019-01-01"]}


class CarryStrategy(common.TargetStrategy):
    def __init__(self, ctx):
        super().__init__([ctx["syms"][r] for r in PARAMS["roots"]])
        self.ctx = ctx
        self._rebal_set = set(ctx["rebal"])
        self._cur: dict[str, float] = {}
        self._inv = {v: k for k, v in ctx["syms"].items()}

    def compute_targets(self, timestamp, closes):
        d = timestamp.strftime("%Y-%m-%d")
        if d in self._rebal_set:
            ranked = sorted(
                ((self.ctx["carry"][r].get(d, float("nan")), r)
                 for r in PARAMS["roots"]),
                key=lambda x: (x[0] != x[0], x[0]))
            ranked = [(c, r) for c, r in ranked if c == c]
            if len(ranked) == 3:
                hi, mid, lo = ranked[2][1], ranked[1][1], ranked[0][1]
                self._cur = {self.ctx["syms"][hi]: 0.5,
                             self.ctx["syms"][lo]: -0.5,
                             self.ctx["syms"][mid]: 0.0}
        return {s: self._cur.get(s, 0.0) for s in self.symbols}


def build(ctx):
    strat = CarryStrategy(ctx)
    bars = {}
    for r in PARAMS["roots"]:
        s = ctx["syms"][r]
        bars[s] = [{"ts": _parse(d), "o": b[0], "h": b[1], "l": b[2],
                    "c": b[3], "v": b[4] if len(b) > 4 else 0.0}
                   for d, b in sorted(ctx["fut"][r].items())
                   if common.TRADE_START <= d < common.TRADE_END]
    return {"strategy": strat, "sizer": common.TargetsSizer(strat),
            "costs": common.equity_costs(), "symbols": strat.symbols,
            "bars": bars,
            "note": "yfinance =F continuous front-month; basis=pre_adjusted; "
                    "5 bps/side commission; no borrow."}


def _parse(d: str):
    from datetime import datetime, timezone
    return datetime(int(d[:4]), int(d[5:7]), int(d[8:10]), tzinfo=timezone.utc)
