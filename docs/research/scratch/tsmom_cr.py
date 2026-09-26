"""RESEARCH SCRATCH — TSMOM-CR: daily time-series momentum on BTC/ETH.

NOT a strategy module. Phase B screening implementation (2026-09-26).

Per name (BTC/USD, ETH/USD, Binance.US daily spot):
  long  if close > max(high, 90d) OR close > close[50d ago]
  flat  otherwise (evaluated daily; exit is the day after the signal fails)
Long/flat only. Sizing: 10% vol-targeted per name —
notional_i = 0.10 * equity / vol_ann_i, capped at 1.0x equity per name
(vol = 60d daily std annualized).

Costs: 25 bps/side all-in via commission (brief-authorized choice; sits
between Binance.US's documented 2 bps taker and Kraken's 80 bps entry
taker — a conservative retail assumption for an unspecified venue).
t->t+1 open fills per engine default. No lookahead.

Simplifications (documented):
  - 2 names only (concentration risk is the point of the screen).
  - Flat evaluated daily = exit the day after signal failure (no stop).
  - Vol-target cap 1.0x equity per name is arbitrary.
  - Binance.US daily bars; any venue data hole is held through (no bars =
    no signal change).
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

IDEA_ID = "TSMOM-CR"
PARAMS = {"symbols": ["BTC/USD", "ETH/USD"], "donchian": 90, "mom": 50,
          "vol_window": 60, "target_vol": 0.10, "cap": 1.0}
SIMPLIFICATIONS = [
    "2 names only",
    "daily long/flat evaluation; no stop-loss",
    "10% vol target per name, 1.0x equity cap (arbitrary); vol target "
    "refreshed monthly and on fresh entries (not daily — avoids churn)",
    "25 bps/side all-in cost assumption (documented choice)",
]
THESIS_LINE = ("Crypto trends harder/longer than equities (thin institutional "
               "participation, reflexive narratives); long/flat dodges violent "
               "reversals. NOTE: shares instruments with killed trial 2 (5-min "
               "mean reversion) — mechanism differs, instrument overlap flagged.")


def prepare(panel: dict) -> dict:
    # panel keyed by crypto symbol -> {date: (o,h,l,c)}
    out = {}
    for s in PARAMS["symbols"]:
        series = panel.get(s, {})
        dates = sorted(d for d in series
                       if common.TRADE_START <= d < common.TRADE_END)
        out[s] = {"dates": dates,
                  "ohlc": [series[d] for d in dates]}
    for s, v in out.items():
        print(f"[tsmom] {s}: {len(v['dates'])} days "
              f"({v['dates'][0] if v['dates'] else '?'}.."
              f"{v['dates'][-1] if v['dates'] else '?'})", flush=True)
    return out


class TSMOMStrategy(common.TargetStrategy):
    def __init__(self, ctx):
        super().__init__(PARAMS["symbols"])
        self.ctx = ctx
        self._size: dict[str, float] = {}   # vol-target size, refreshed monthly / on entry
        self._sig: dict[str, bool] = {}
        self._last_ym: str | None = None

    def compute_targets(self, timestamp, closes):
        d = timestamp.strftime("%Y-%m-%d")
        new_month = d[:7] != self._last_ym
        tgt = {}
        for s in self.symbols:
            info = self.ctx[s]
            if d not in info["dates"]:
                continue  # data hole: hold (no signal change)
            i = info["dates"].index(d)
            ohlc = info["ohlc"][: i + 1]
            if len(ohlc) < 91:
                continue
            closes_s = [b[3] for b in ohlc]
            highs = [b[1] for b in ohlc]
            breakout = closes_s[-1] > max(highs[-91:-1])
            sig = bool(breakout or closes_s[-1] > closes_s[-51])
            prev = self._sig.get(s, False)
            if new_month or (sig and not prev) or s not in self._size:
                rets = [closes_s[j] / closes_s[j - 1] - 1.0
                        for j in range(len(closes_s) - 60, len(closes_s))]
                vol = common.stdev(rets) * math.sqrt(365)
                self._size[s] = min(0.10 / vol, 1.0) if vol > 0 else 0.0
            self._sig[s] = sig
            tgt[s] = self._size[s] if sig else 0.0
        self._last_ym = d[:7]
        base = {s: self.targets.get(s, 0.0) for s in self.symbols
                if s not in closes}
        base.update({s: tgt.get(s, 0.0) for s in self.symbols})
        return base


def build(ctx):
    strat = TSMOMStrategy(ctx)
    bars = {}
    for s, info in ctx.items():
        bars[s] = [{"ts": _parse(d), "o": b[0], "h": b[1], "l": b[2],
                    "c": b[3], "v": b[4] if len(b) > 4 else 0.0}
                   for d, b in zip(info["dates"], info["ohlc"])]
    return {"strategy": strat, "sizer": common.TargetsSizer(strat),
            "costs": common.crypto_costs(), "symbols": strat.symbols,
            "bars": bars,
            "note": "Binance.US public daily spot via trade-data-crypto; "
                    "basis=pre_adjusted; 25 bps/side all-in; no borrow."}


def _parse(d: str):
    from datetime import datetime, timezone
    return datetime(int(d[:4]), int(d[5:7]), int(d[8:10]), tzinfo=timezone.utc)
