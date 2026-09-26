"""RESEARCH SCRATCH — PAIRS-1: cointegrated equity pairs, z-score mean reversion.

NOT a strategy module. Phase B screening implementation (2026-09-26).

Pipeline
--------
1. Universe = cached large-cap panel, full-coverage tickers only.
2. Quarterly re-screen (first trading day of each quarter, 2019Q1..2026Q3)
   on the prior 252 trading days via trade_pairs.find_pairs
   (correlation pre-filter -> Engle-Granger -> rank by ADF), keep <= 10
   pairs, cointegrated first, half-life < 60d filter.
3. Per (quarter, pair), spread = pA - hr*pB - intercept  (RAW prices:
   trade_pairs' Engle-Granger OLS is estimated on raw prices, so the
   cointegrating residual is raw too); signals from
   trade_pairs.signals.generate_signals (causal rolling z, entry |z|>=2,
   exit |z|<=0.5, window 60). Each selection is replayed with its own
   quarter's (hr, intercept). 20-trading-day time stop.
4. Dollar-neutral: each pair 10% gross (5% per leg); gross cap 1.0.

Simplifications (documented):
  - Quarterly re-screen (spec: quarterly — matches) but the pair set is
    frozen between screens and flattened when a pair drops out.
  - Hedge ratio from Engle-Granger is used for the spread signal only;
    legs are sized equal-dollar (dollar-neutral), not hedge-ratio-neutral.
  - exit_z=0.5 (trade-pairs default) instead of spec's z=0; time stop 20d
    instead of 10d (looser = cheaper screen, fewer whipsaw exits).
  - Spreads for screening are aligned to the SPY date grid with
    forward-fill (screening only; trading replays on actual bar dates).
  - Survivorship bias: universe is today's liquid large caps (delisted
    names absent). Screening is in-sample and loose by design.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

IDEA_ID = "PAIRS-1"
PARAMS = {
    "entry_z": 2.0, "exit_z": 0.5, "z_window": 60,
    "screen_lookback": 252, "min_correlation": 0.70,
    "max_pairs": 10, "pair_gross": 0.10, "time_stop_days": 20,
}
SIMPLIFICATIONS = [
    "quarterly static pair set between re-screens; flatten on drop-out",
    "equal-dollar legs (hedge ratio used for signal only)",
    "exit_z=0.5 (pairs default) not z=0; 20d time stop not 10d",
    "screen alignment via SPY grid forward-fill",
    "survivorship-biased universe (today's large caps)",
]
THESIS_LINE = ("Cross-sectional relative mean reversion, market-neutral by "
               "construction; edge from uninformed-flow mispricings reverting.")


def _quarter_starts(dates: list[str]) -> list[str]:
    out, seen = [], set()
    for d in sorted(dates):
        q = d[:4] + "Q" + str((int(d[5:7]) - 1) // 3 + 1)
        if q not in seen:
            seen.add(q)
            out.append(d)
    return out


def prepare(panel: dict) -> dict:
    """panel: ticker -> {date: (o,h,l,c)}. Returns ctx for build()."""
    from trade_pairs.screening import find_pairs
    from trade_pairs.signals import generate_signals

    spy_dates = sorted(panel["SPY"])
    grid = [d for d in spy_dates if d >= "2015-01-01"]
    closes = {}
    for t, series in panel.items():
        if t == "SPY":
            closes[t] = [series[d][3] for d in grid]
            continue
        if t.startswith(("FUT_", "FX_")) or "/" in t:
            continue  # equities only for the pairs screen
        # forward-fill onto the SPY grid (screening alignment only)
        sdates = sorted(series)
        vals, j, last = [], 0, None
        for d in grid:
            while j < len(sdates) and sdates[j] <= d:
                last = series[sdates[j]][3]
                j += 1
            vals.append(last if last is not None else float("nan"))
        closes[t] = vals
    # drop tickers with any NaN on the grid (strict full coverage)
    uni = [t for t in closes
           if all(v == v for v in closes[t]) and t != "SPY"]
    print(f"[pairs] universe: {len(uni)} full-coverage tickers", flush=True)

    trade_dates = [d for d in grid if common.TRADE_START <= d < common.TRADE_END]
    qstarts = [q for q in _quarter_starts(trade_dates) if q >= "2019-01-01"]

    # quarterly screens -> {qstart: [pair dicts]}
    screens: dict[str, list[dict]] = {}
    spreads: dict[tuple[str, str], list[tuple[str, float]]] = {}
    for qi, q in enumerate(qstarts):
        qi_end = grid.index(q)
        hist = {t: closes[t][qi_end - 252:qi_end] for t in uni}
        pairs = find_pairs(hist, lookback=252, min_correlation=0.70,
                           max_candidates=40, max_pairs=10)
        kept = [p for p in pairs
                if p.cointegrated and (p.half_life_bars or 1e9) < 60.0]
        screens[q] = [{
            "a": p.symbol_a, "b": p.symbol_b,
            "hr": p.hedge_ratio, "c": p.intercept,
            "adf": p.adf.stat, "hl": p.half_life_bars,
        } for p in kept]
        print(f"[pairs] {q}: {len(kept)}/{len(pairs)} pairs kept", flush=True)

    # spread + signal replay per (quarter, pair), each with its own
    # quarter's (hr, intercept); spread is the raw-price EG residual.
    pair_replay: dict[tuple[str, str, str], list[tuple[str, int]]] = {}
    for q, ps in screens.items():
        for p in ps:
            a, b, hr, c = p["a"], p["b"], p["hr"], p["c"]
            ca, cb = closes[a], closes[b]
            series = [(d, pa - hr * pb - c)
                      for d, pa, pb in zip(grid, ca, cb) if pa > 0 and pb > 0]
            sdates = [d for d, _ in series]
            svals = [v for _, v in series]
            sigs = generate_signals(svals, entry_z=2.0, exit_z=0.5, window=60)
            act = {}
            for s in sigs:
                act[sdates[s.index]] = s.action  # long_spread/short_spread/exit
            replay, pos, age = [], 0, 0
            for d in sdates:
                k = act.get(d)
                if pos == 0 and k == "long_spread":
                    pos, age = 1, 0
                elif pos == 0 and k == "short_spread":
                    pos, age = -1, 0
                elif pos != 0 and (k == "exit" or age >= 20):
                    pos, age = 0, 0
                elif pos != 0:
                    age += 1
                replay.append((d, pos))
            pair_replay[(a, b, q)] = replay
    return {
        "screens": screens, "qstarts": qstarts,
        "pair_replay": pair_replay, "universe": uni,
    }


class PairsStrategy(common.TargetStrategy):
    def __init__(self, ctx):
        syms = sorted({s for ps in ctx["screens"].values()
                       for p in ps for s in (p["a"], p["b"])})
        super().__init__(syms)
        self.ctx = ctx
        self._replay_idx: dict[tuple[str, str, str], dict[str, int]] = {
            k: dict(v) for k, v in ctx["pair_replay"].items()}
        self._active: list[dict] = []

    def compute_targets(self, timestamp, closes):
        d = timestamp.strftime("%Y-%m-%d")
        qs = self.ctx["qstarts"]
        # active screen = latest qstart <= d
        cur = None
        for q in qs:
            if q <= d:
                cur = q
            else:
                break
        self._active = self.ctx["screens"].get(cur, []) if cur else []
        w = PARAMS["pair_gross"] / 2.0
        tgt: dict[str, float] = {}
        for p in self._active:
            pos = self._replay_idx[(p["a"], p["b"], cur)].get(d, 0)
            if pos == 1:      # long spread: long A, short B
                tgt[p["a"]] = tgt.get(p["a"], 0.0) + w
                tgt[p["b"]] = tgt.get(p["b"], 0.0) - w
            elif pos == -1:   # short spread: short A, long B
                tgt[p["a"]] = tgt.get(p["a"], 0.0) - w
                tgt[p["b"]] = tgt.get(p["b"], 0.0) + w
        # clip gross at 1.0 (overlapping legs across pairs)
        gross = sum(abs(v) for v in tgt.values())
        if gross > 1.0:
            tgt = {k: v / gross for k, v in tgt.items()}
        return {s: tgt.get(s, 0.0) for s in self.symbols}


def build(ctx):
    strat = PairsStrategy(ctx)
    return {"strategy": strat, "sizer": common.TargetsSizer(strat),
            "costs": common.equity_costs(), "symbols": strat.symbols,
            "bars": None,
            "note": "yfinance daily 2015-01-01..2026-09-25, split/div adjusted; "
                    "basis=pre_adjusted; 5 bps/side commission; 50 bps/yr borrow."}
