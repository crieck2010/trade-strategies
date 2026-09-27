"""RESEARCH SCRATCH — RVBOND-1: gold vs long-bond real-yield relative value.

NOT a strategy module. Round-2 Phase B screening implementation (2026-09-26).

Thesis: trade the GLD/TLT relative value anchored on real yields. Regress
log(GLD/TLT) on log(TIP) — TIP's price is the inverse real-yield proxy —
and trade the residual. Long the cheap leg / short the rich leg when
|z| > 1.5 on a 90-day residual window; exit at z = 0 or a 30-day time
stop. Dollar-neutral; coefficients refreshed monthly.

Signal mechanics (all trailing, no lookahead):
  - y = log(GLD/TLT), x = log(TIP), daily adjusted closes.
  - On the last trading day tau of each month: OLS fit of y on x over the
    trailing 90 trading days -> (a, b); residual r_t = y_t - (a + b*x_t)
    over the same 90 days -> (mu, sigma).
  - During the following month: z_d = (r_d - mu) / sigma with the frozen
    (a, b, mu, sigma) — the residual is a fair-value forecast made with
    month-end information only.
  - Entry: z > +1.5 -> short spread (short GLD, long TLT); z < -1.5 ->
    long spread (long GLD, short TLT). 50% equity per leg, dollar-neutral.
  - Exit: z crosses zero against the position (z*entry_sign <= 0) or
    30 trading days since entry.

Simplifications (documented):
  - Single 90-day OLS window (spec's residual window) with monthly
    coefficient refresh; no robust regression, no heteroskedasticity
    correction.
  - Equal-dollar legs rather than beta-matched legs (residual is a ratio
    log, so the natural hedge is ~1:-1 on the log legs; at these
    magnitudes equal-dollar is close).
  - ETF-level costs (5 bps/side); borrow 50 bps/yr on the short leg.
  - TIP-as-real-yield-proxy taken as given; the screen does not test
    whether TIP tracks 10y TIPS yields at this horizon.
"""

from __future__ import annotations

import math
import os
import sys

_SCRATCH2 = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(_SCRATCH2), "..", "scratch"))  # round-1 common
import common  # noqa: E402

IDEA_ID = "RVBOND-1"
PARAMS = {"z_entry": 1.5, "time_stop_days": 30, "resid_window": 90,
          "leg_weight": 0.5, "symbols": ["GLD", "TLT"]}
SIMPLIFICATIONS = [
    "90d OLS, coefficients + residual mean/std refreshed monthly (frozen within month)",
    "exit at z crossing zero or 30-trading-day time stop",
    "equal-dollar legs (0.5/0.5), no beta matching",
    "5 bps/side + 50 bps/yr borrow on shorts",
]
THESIS_LINE = ("Intermarket RV: log(GLD/TLT) vs TIP-implied real-yield fair "
               "value; trade the residual, dollar-neutral.")


def _ols(xs: list[float], ys: list[float]) -> tuple[float, float]:
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx if sxx > 0 else 0.0
    return my - b * mx, b


def prepare(panel: dict) -> dict:
    # Full-history dates (2015+) for warmup; trading window enforced in
    # compute_targets (no signals before TRADE_START).
    dates = sorted(set(panel["GLD"]) & set(panel["TLT"]) & set(panel["TIP"]))
    y = [math.log(panel["GLD"][d][3] / panel["TLT"][d][3]) for d in dates]
    x = [math.log(panel["TIP"][d][3]) for d in dates]
    W = PARAMS["resid_window"]

    # month -> (a, b, mu, sigma) fit on the trailing-90d window ending at
    # the LAST trading day of the PRIOR month; applies to this month.
    idx = {d: i for i, d in enumerate(dates)}
    month_of = {d: d[:7] for d in dates}
    months = sorted(set(month_of.values()))
    fit: dict[str, tuple[float, float, float, float] | None] = {}
    for m in months:
        mdays = [d for d in dates if month_of[d] == m]
        tau = mdays[-1]
        i = idx[tau]
        if i < W:  # insufficient warmup: no fit for this month
            fit[m] = None
            continue
        xs, ys = x[i - W + 1: i + 1], y[i - W + 1: i + 1]
        a, beta = _ols(xs, ys)
        rs = [yy - (a + beta * xx) for yy, xx in zip(ys, xs)]
        mu, sig = sum(rs) / W, common.stdev(rs)
        fit[m] = (a, beta, mu, sig) if sig > 0 else None

    # per in-window trading day: (z, y, x); warmup history is in the series.
    # NO LOOKAHEAD: a day in month M uses the fit made on the last trading
    # day of month M-1 (trailing-90d window ending at that date).
    z_by_date: dict[str, float | None] = {}
    prev_month = {m: months[k - 1] if k > 0 else None
                  for k, m in enumerate(months)}
    for j, d in enumerate(dates):
        pm = prev_month[month_of[d]]
        f = fit[pm] if pm is not None else None
        if f is None:
            z_by_date[d] = None
            continue
        a, b, mu, sig = f
        r = y[j] - (a + b * x[j])
        z_by_date[d] = (r - mu) / sig
    trade_dates = sorted(d for d in dates
                         if common.TRADE_START <= d < common.TRADE_END)
    n_fit = sum(1 for v in fit.values() if v is not None)
    print(f"[rvbond] {len(dates)} days, {len(months)} months, {n_fit} monthly fits, "
          f"{len(trade_dates)} trading days", flush=True)
    return {"dates": dates, "trade_dates": trade_dates,
            "z_by_date": z_by_date}


class RVBondStrategy(common.TargetStrategy):
    def __init__(self, ctx):
        super().__init__(PARAMS["symbols"])
        self.ctx = ctx
        self._pos = 0          # -1 short spread, +1 long spread, 0 flat
        self._entry_day = -1   # index in trade_dates
        self._entry_sign = 0   # sign of z at entry
        self._tdx = {d: i for i, d in enumerate(ctx["trade_dates"])}

    def compute_targets(self, timestamp, closes):
        d = timestamp.strftime("%Y-%m-%d")
        z = self.ctx["z_by_date"].get(d)
        i = self._tdx[d]
        if z is not None and z == z:  # not None/NaN
            if self._pos == 0 and abs(z) > PARAMS["z_entry"]:
                self._pos = -1 if z > 0 else 1
                self._entry_day = i
                self._entry_sign = 1 if z > 0 else -1
            elif self._pos != 0:
                timed_out = (i - self._entry_day) >= PARAMS["time_stop_days"]
                crossed = z * self._entry_sign <= 0
                if timed_out or crossed:
                    self._pos, self._entry_sign = 0, 0
        # short spread: short GLD, long TLT; long spread: the mirror
        w = PARAMS["leg_weight"]
        tgt = {"GLD": 0.0, "TLT": 0.0}
        if self._pos == 1:
            tgt = {"GLD": w, "TLT": -w}
        elif self._pos == -1:
            tgt = {"GLD": -w, "TLT": w}
        return {s: tgt[s] for s in self.symbols}


def build(ctx):
    strat = RVBondStrategy(ctx)
    return {"strategy": strat, "sizer": common.TargetsSizer(strat),
            "costs": common.equity_costs(), "symbols": strat.symbols,
            "bars": None,
            "note": ("yfinance ETF daily, split/div adjusted; basis=pre_adjusted; "
                     "5 bps/side commission; 50 bps/yr borrow on shorts. "
                     "Coefficients fit trailing-90d at prior month-end; "
                     "fills t->t+1 via engine.")}
