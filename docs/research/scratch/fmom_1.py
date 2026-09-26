"""RESEARCH SCRATCH — FMOM-1: factor momentum (momentum of factors).

NOT a strategy module. Phase B screening implementation (2026-09-26).

1. Build 4 long-short factor proxy return series from the equity price
   panel (price characteristics only), rebalanced monthly on the first
   trading day, via trade_factors.long_short_weights (dollar-neutral,
   tercile sorts):
     F_MOM : 252d return skipping 21d  (top tercile long / bottom short)
     F_VOL : 60d daily volatility      (low-vol long / high-vol short)
     F_REV : 21d return                (losers long / winners short)
     F_BETA: 252d beta vs SPY          (low-beta long / high-beta short)
2. Cumulate each factor's daily returns into a synthetic price index.
3. Monthly: rank the 4 factor indices on trailing 252d return; long the
   top half (2), short the bottom half (2), equal-weighted (25% each),
   gross 1.0. Factor indices trade as synthetic symbols through the
   engine (o=h=l=c=index, v=0).

Simplifications (documented):
  - No fundamentals: value/quality/size built from price only is not
    attempted; F_REV (short-term reversal) and F_BETA stand in for the
    missing value/quality legs. This tests "factor momentum" as a
    mechanism, not the Fama-French factor set.
  - Tercile (not decile) sorts; equal dollar-neutral weights.
  - Factor series start 2016-06; FMOM trading starts 2018-01-01.
  - Synthetic symbols: no bid/ask, costs modeled as 5 bps/side anyway.
  - Survivorship-biased equity panel underneath.
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

IDEA_ID = "FMOM-1"
PARAMS = {"n_factors": 4, "rank_lookback": 252, "gross": 1.0}
SIMPLIFICATIONS = [
    "price-only factor proxies; F_REV/F_BETA stand in for value/quality",
    "tercile sorts via trade_factors.long_short_weights",
    "synthetic factor indices as tradable symbols",
    "survivorship-biased panel underneath",
]
THESIS_LINE = ("Style factors themselves trend (Ehsani-Babani 2019): slow "
               "institutional rotation makes factor returns autocorrelated.")


def _daily_returns(cs: list[float]) -> list[float]:
    return [cs[i] / cs[i - 1] - 1.0 for i in range(1, len(cs))]


def prepare(panel: dict) -> dict:
    from trade_factors.portfolios import long_short_weights

    spy_dates = sorted(d for d in panel["SPY"]
                       if "2015-01-01" <= d < common.TRADE_END)
    uni = [t for t, s in panel.items()
           if t != "SPY" and not t.startswith(("FUT_", "FX_"))
           and sum(1 for d in spy_dates if d in s) >= 0.95 * len(spy_dates)]
    closes = common.aligned_closes(panel, spy_dates, uni)
    uni = sorted(closes)  # aligned_closes drops gappy tickers; iterate survivors
    spy = [panel["SPY"][d][3] for d in spy_dates]
    spy_r = _daily_returns(spy)
    rets = {t: _daily_returns(cs) for t, cs in closes.items()}
    # return dates: spy_dates[1:]
    rdates = spy_dates[1:]
    rebal = [d for d in common.month_rebalances(rdates)
             if "2016-06-01" <= d <= common.TRADE_END]
    # per-rebalance weights for each factor
    fdefs = ["F_MOM", "F_VOL", "F_REV", "F_BETA"]
    weights: dict[str, dict[str, list[float]]] = {f: {} for f in fdefs}
    for rb in rebal:
        i = rdates.index(rb)  # return index; price index = i+1
        n = len(uni)
        k = max(1, n // 3)
        scores = {}
        mom, vol, rev, beta = [], [], [], []
        for t in uni:
            cs = closes[t][: i + 2]
            r = rets[t]
            m = common.trailing_return(cs, 252, skip=21)
            mom.append(m if m is not None else 0.0)
            v = common.stdev(r[max(0, i - 59): i + 1])
            vol.append(v)
            rev.append(cs[-1] / cs[-22] - 1.0 if len(cs) > 22 and cs[-22] > 0 else 0.0)
            b = _beta(r[max(0, i - 251): i + 1], spy_r[max(0, i - 251): i + 1])
            beta.append(b)
        weights["F_MOM"][rb] = long_short_weights(mom, k, k)
        weights["F_VOL"][rb] = long_short_weights([-v for v in vol], k, k)
        weights["F_REV"][rb] = long_short_weights([-x for x in rev], k, k)
        weights["F_BETA"][rb] = long_short_weights([-b for b in beta], k, k)

    # factor daily return series -> synthetic price index
    tickers = uni
    factor_idx: dict[str, list[tuple[str, float]]] = {}
    for f in fdefs:
        idx, w = 1.0, None
        series = []
        for j, d in enumerate(rdates):
            # weights computed from data through the rebalance close apply
            # from the NEXT day (no lookahead); series starts the day after
            # the first rebalance.
            if w is not None:
                fr = sum(wi * rets[t][j] for wi, t in zip(w, tickers))
                idx *= (1.0 + fr)
                series.append((d, idx))
            if d in weights[f]:
                w = weights[f][d]
        factor_idx[f] = series
    n_days = min(len(v) for v in factor_idx.values())
    print(f"[fmom] factor series: {n_days} days each", flush=True)
    return {"factor_idx": factor_idx, "fdefs": fdefs}


def _beta(rx: list[float], ry: list[float]) -> float:
    n = min(len(rx), len(ry))
    if n < 60:
        return 1.0
    rx, ry = rx[-n:], ry[-n:]
    mx, my = sum(rx) / n, sum(ry) / n
    var = sum((y - my) ** 2 for y in ry)
    if var <= 0:
        return 1.0
    return sum((x - mx) * (y - my) for x, y in zip(rx, ry)) / var


class FMOMStrategy(common.TargetStrategy):
    def __init__(self, ctx):
        super().__init__(ctx["fdefs"])
        self.ctx = ctx
        dates = sorted({d for s in ctx["factor_idx"].values() for d, _ in s})
        self._grid = {d: i for i, d in enumerate(dates)}
        self._rebal = set(d for d in common.month_rebalances(dates)
                           if d >= "2018-01-01")
        self._cur: dict[str, float] = {}
        # date-aligned index series
        self._idx = {f: dict(s) for f, s in ctx["factor_idx"].items()}

    def compute_targets(self, timestamp, closes):
        d = timestamp.strftime("%Y-%m-%d")
        if d in self._rebal and d in self._grid:
            i = self._grid[d]
            scored = []
            for f in self.symbols:
                s = self.ctx["factor_idx"][f]
                # trailing 252d return of the factor index
                if i >= 252:
                    r = s[i][1] / s[i - 252][1] - 1.0
                    scored.append((r, f))
            scored.sort()
            if len(scored) == 4:
                self._cur = {scored[3][1]: 0.25, scored[2][1]: 0.25,
                             scored[1][1]: -0.25, scored[0][1]: -0.25}
        return {s: self._cur.get(s, 0.0) for s in self.symbols}


def build(ctx):
    strat = FMOMStrategy(ctx)
    # synthetic bars: o=h=l=c=index
    bars = {}
    for f, series in ctx["factor_idx"].items():
        bars[f] = [{"ts": _parse(d), "o": v, "h": v, "l": v, "c": v, "v": 0.0}
                   for d, v in series]
    return {"strategy": strat, "sizer": common.TargetsSizer(strat),
            "costs": common.equity_costs(), "symbols": strat.symbols,
            "bars": bars,
            "note": "synthetic factor indices from yfinance panel; "
                    "basis=pre_adjusted; 5 bps/side commission; no borrow "
                    "(factors are LS portfolios)."}


def _parse(d: str):
    from datetime import datetime, timezone
    return datetime(int(d[:4]), int(d[5:7]), int(d[8:10]), tzinfo=timezone.utc)
