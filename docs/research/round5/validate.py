#!/usr/bin/env python3
"""Round 5 six-gate walk-forward validation for the 10 admitted candidates.

Frozen specs: docs/validation/<slug>/PRE-REGISTRATION.md (2026-09-28).
Signal logic imported from the frozen triage.py implementations
(stateful factories re-instantiated fresh per run). No parameters fitted;
no AI optimization after OOS.

Walk-forward: 520-bar train / 130-bar test / 130-bar step / 5-bar embargo.
Fills t+1 open, 5 bps/side. DSR n_trials=27 (27 performance-screened
round-5 hypotheses; the 3 data-parked ideas never had performance observed
and contribute zero trials).

Writes docs/validation/<slug>/evidence.json per candidate.
"""
import datetime as dt
import json
import math
import os
import statistics
import sys

WS = os.path.expanduser("~/workspace/trade-suite")
for repo in ("trade-macro", "trade-overfit"):
    p = os.path.join(WS, repo, "src")
    if p not in sys.path:
        sys.path.insert(0, p)
R5 = os.path.join(WS, "trade-strategies/docs/research/round5")
if R5 not in sys.path:
    sys.path.insert(0, R5)

import triage as T
from trade_overfit.dsr import dsr_from_returns
from trade_overfit.metrics import (performance_summary, sharpe_ratio,
                                   max_drawdown, total_return)

HERE = R5
VAL = os.path.join(WS, "trade-strategies/docs/validation")
BPS = 5.0
TRAIN_BARS, TEST_BARS, STEP_BARS, EMBARGO_BARS = 520, 130, 130, 5

CANDIDATES = {
    "hyg-lqd-spread":   dict(idea="idea-0008", symbols=["HYG", "LQD"],
                             signal=T.c0008, freq="monthly",
                             benchmark=("bh", "LQD"), tstart=dt.date(2018, 1, 1)),
    "tlt-shy-slope":    dict(idea="idea-0009", symbols=["TLT", "SHY"],
                             signal=T.c0009, freq="monthly",
                             benchmark=("bh", "IEF"), tstart=dt.date(2018, 1, 1)),
    "short-carry-ladder": dict(idea="idea-0010", symbols=["SGOV", "SHY", "IEF"],
                             signal=T.c0010, freq="quarterly",
                             benchmark=("bh", "SHY"), tstart=dt.date(2020, 9, 1)),
    "svxy-harvest":     dict(idea="idea-0015", symbols=["SVXY", "SHY"],
                             signal=T.c0015, freq="monthly",
                             benchmark=("bh", "SHY"), tstart=dt.date(2018, 1, 1)),
    "vix-dip-buy":      dict(idea="idea-0016", symbols=["SPY", "SHY"],
                             signal="factory_c0016", freq="monthly",
                             benchmark=("bh", "SPY"), tstart=dt.date(2018, 1, 1)),
    "uso-momentum":     dict(idea="idea-0021", symbols=["USO", "SHY"],
                             signal=T.c0021, freq="monthly",
                             benchmark=("bh", "DBC"), tstart=dt.date(2018, 1, 1)),
    "spy-turn-of-month": dict(idea="idea-0026", symbols=["SPY", "SHY"],
                             signal="tom", freq="daily-tom",
                             benchmark=("bh", "SPY"), tstart=dt.date(2018, 1, 1)),
    "fx-momentum":      dict(idea="idea-0031", symbols=["UUP", "FXE", "FXY", "FXB", "FXC"],
                             signal=T.c0031, freq="monthly",
                             benchmark=("bh", "UUP"), tstart=dt.date(2018, 1, 1)),
    "gtaa-5":           dict(idea="idea-0032", symbols=["SPY", "EFA", "EEM", "IEF", "DBC", "SHY"],
                             signal=T.c0032, freq="monthly",
                             benchmark=("fixed", {"SPY": 0.6, "AGG": 0.4}),
                             tstart=dt.date(2018, 1, 1)),
    "efa-eem-rotation": dict(idea="idea-0034", symbols=["EFA", "EEM", "SHY"],
                             signal=T.c0034, freq="monthly",
                             benchmark=("bh", "EFA"), tstart=dt.date(2018, 1, 1)),
}

# all 27 performance-screened ideas for the DSR trial set (idea -> (symbols, signal, freq, tstart))
TRIAL_SET = dict(CANDIDATES)
TRIAL_SET.update({
    "t0011": dict(symbols=["TIP", "IEF"], signal=T.c0011, freq="monthly", tstart=dt.date(2018,1,1)),
    "t0012": dict(symbols=["USMV", "SPY"], signal=T.c0012, freq="monthly", tstart=dt.date(2018,1,1)),
    "t0013": dict(symbols=["USMV", "SPLV", "QUAL"], signal=T.c0013, freq="monthly", tstart=dt.date(2018,1,1)),
    "t0014": dict(symbols=["SPLV", "SPY"], signal="factory_c0014", freq="monthly", tstart=dt.date(2018,1,1)),
    "t0017": dict(symbols=["VXX", "SPY", "SHY"], signal="factory_c0017", freq="monthly", tstart=dt.date(2018,5,1)),
    "t0018": dict(symbols=["SVXY", "SHY"], signal="factory_c0018", freq="monthly", tstart=dt.date(2018,1,1)),
    "t0019": dict(symbols=["HYG", "LQD", "SHY"], signal=T.c0019, freq="monthly", tstart=dt.date(2018,1,1)),
    "t0022": dict(symbols=["UUP", "SHY"], signal=T.c0022, freq="monthly", tstart=dt.date(2018,1,1)),
    "t0024": dict(symbols=["SPY"], signal="overnight_SPY", freq="overnight", tstart=dt.date(2018,1,1)),
    "t0027": dict(symbols=["GLD"], signal="overnight_GLD", freq="overnight", tstart=dt.date(2018,1,1)),
    "t0028": dict(symbols=["USO","GLD","DBA","DBB","CPER","UNG"], signal=T.c0028, freq="monthly", tstart=dt.date(2018,1,1)),
    "t0029": dict(symbols=["SHY","IEF","TLT","TIP","HYG","LQD","MUB"], signal=T.c0029, freq="monthly", tstart=dt.date(2018,1,1)),
    "t0033": dict(symbols=["SPY","EFA","EEM","SHY"], signal=T.c0033, freq="monthly", tstart=dt.date(2018,1,1)),
    "t0035": dict(symbols=["GLD","SHY"], signal=T.c0035, freq="monthly", tstart=dt.date(2018,1,1)),
    "t0036": dict(symbols=["DBC","SHY"], signal=T.c0036, freq="monthly", tstart=dt.date(2018,1,1)),
    "t0037": dict(symbols=["SLV","GLD"], signal=T.c0037, freq="monthly", tstart=dt.date(2018,1,1)),
    "t0038": dict(symbols=["USO","GLD","SHY"], signal=T.c0038, freq="monthly", tstart=dt.date(2018,1,1)),
})


def fresh_signal(spec):
    s = spec["signal"]
    if s == "factory_c0016":
        return T.c0016_factory()
    if s == "factory_c0014":
        return T.c0014_factory()
    if s == "factory_c0017":
        return T.c0017_factory()
    if s == "factory_c0018":
        return T.c0018_factory()
    return s


def simulate(symbols, signal_fn, freq, tstart, bps):
    """Return (dates, returns, turnover_total, n_trades, avg_abs_weights)."""
    tdates = [d for d in T.CAL if d >= tstart and all(d in T.PX[s] for s in symbols)]
    if freq == "overnight":
        sym = symbols[0]
        rets, dates = [], []
        for i, d in enumerate(tdates[:-1]):
            nxt = tdates[i + 1]
            rets.append(T.OPX[sym][nxt] / T.PX[sym][d] - 1.0 - 2 * (bps / 1e4))
            dates.append(d)
        return dates, rets, len(rets), len(rets), {sym: 1.0}
    if freq == "daily-tom":
        in_tom = set()
        for i, d in enumerate(T.CAL):
            back = sum(1 for j in range(0, i + 1)
                       if (T.CAL[j].year, T.CAL[j].month) == (d.year, d.month))
            fwd = sum(1 for j in range(i, len(T.CAL))
                      if (T.CAL[j].year, T.CAL[j].month) == (d.year, d.month))
            if back <= 3 or fwd <= 2:
                in_tom.add(d)
        rets, dates, wsum, n = [], [], {"SPY": 0.0, "SHY": 0.0}, 0
        prev = None
        for d in tdates:
            sym = "SPY" if d in in_tom else "SHY"
            wsum[sym] += 1.0
            n += 1
            if prev is not None:
                # switch cost when position changes
                r = T.PX[sym][d] / T.PX[sym][prev] - 1.0
                rets.append(r)
                dates.append(d)
            prev = d
        # turnover: count switches
        switches = sum(1 for i in range(1, len(dates))
                       if (dates[i] in in_tom) != (dates[i - 1] in in_tom))
        turnover = switches * 1.0  # full notional each switch
        avg_w = {s: wsum[s] / n for s in wsum}
        return dates, rets, turnover, switches, avg_w
    # monthly / quarterly
    firsts = T.first_trading_days(tdates)
    if freq == "quarterly":
        firsts = [d for d in firsts if d.month in (1, 4, 7, 10)]
    firsts_set = set(firsts)
    shares = None
    rets, dates = [], []
    turnover_total, n_trades = 0.0, 0
    pending = None
    prev_close_val = 1.0
    wsum, wn = {s: 0.0 for s in symbols}, 0
    for i, d in enumerate(tdates):
        if d in firsts_set:
            me = T.month_end_before(d)
            if me is not None:
                fill = tdates[i + 1] if i + 1 < len(tdates) else None
                tw = signal_fn(me)
                tw = {s: tw.get(s, 0.0) for s in symbols}
                for s in symbols:
                    wsum[s] += abs(tw[s])
                wn += 1
                pending = (fill, tw)
        if pending is not None and pending[0] == d:
            _, tw = pending
            pending = None
            if shares is None:
                open_val, turn_frac = 1.0, 1.0
            else:
                open_val = sum(shares[s] * T.OPX[s][d] for s in symbols)
                if open_val <= 0:
                    rets.append(-1.0)
                    dates.append(d)
                    break
                cur_w = {s: shares[s] * T.OPX[s][d] / open_val for s in symbols}
                turn_frac = sum(abs(tw[s] - cur_w[s]) for s in symbols)
            cost = (bps / 1e4) * turn_frac * open_val
            turnover_total += turn_frac
            n_trades += 1
            post_cost = open_val - cost
            shares = {s: tw[s] * post_cost / T.OPX[s][d] for s in symbols}
        if shares is None:
            rets.append(0.0)
        else:
            close_val = sum(shares[s] * T.PX[s][d] for s in symbols)
            rets.append(close_val / prev_close_val - 1.0)
            prev_close_val = close_val
        dates.append(d)
    avg_w = {s: wsum[s] / wn for s in symbols} if wn else {s: 0.0 for s in symbols}
    return dates, rets, turnover_total, n_trades, avg_w


def simulate_bh(symbols, weights, tstart, bps):
    """Buy-and-hold (single asset) or fixed-weight monthly rebalance."""
    tdates = [d for d in T.CAL if d >= tstart and all(d in T.PX[s] for s in symbols)]
    if weights is None:
        # single-asset BH: buy at t+1 open after first date
        s = symbols[0]
        rets, dates = [], []
        buy_d = tdates[1]
        shares = (1.0 - bps / 1e4) / T.OPX[s][buy_d]
        prev = shares * T.PX[s][buy_d]
        for d in tdates[1:]:
            val = shares * T.PX[s][d]
            rets.append(val / prev - 1.0)
            prev = val
            dates.append(d)
        return dates, rets
    # fixed-weight monthly rebalance
    tw = {s: weights.get(s, 0.0) for s in symbols}
    firsts = set(T.first_trading_days(tdates))
    shares = None
    rets, dates = [], []
    prev_close_val = 1.0
    for i, d in enumerate(tdates):
        if i == 0 or d in firsts:
            if shares is None:
                open_val = 1.0
                shares = {s: tw[s] / T.OPX[s][d] for s in symbols}
            else:
                open_val = sum(shares[s] * T.OPX[s][d] for s in symbols)
                cur_w = {s: shares[s] * T.OPX[s][d] / open_val for s in symbols}
                turn_frac = sum(abs(tw[s] - cur_w[s]) for s in symbols)
                open_val -= (bps / 1e4) * turn_frac * open_val
                shares = {s: tw[s] * open_val / T.OPX[s][d] for s in symbols}
        close_val = sum(shares[s] * T.PX[s][d] for s in symbols)
        rets.append(close_val / prev_close_val - 1.0)
        prev_close_val = close_val
        dates.append(d)
    return dates, rets


def folds(n):
    out, k = [], 0
    while True:
        ts = k * STEP_BARS
        te = ts + TRAIN_BARS
        ss = te + EMBARGO_BARS
        se = ss + TEST_BARS
        if ss >= n:
            break
        out.append((ts, min(te, n), ss, min(se, n)))
        k += 1
    return out


def ann_vol(symbol, dates):
    r = [T.PX[symbol][dates[i]] / T.PX[symbol][dates[i - 1]] - 1.0
         for i in range(1, len(dates))]
    return statistics.stdev(r) * math.sqrt(252) if len(r) > 1 else 0.0


def main():
    only = sys.argv[1:] or None
    # ---- trial Sharpe set (n=27), frozen simulators, full-window net ----
    print("== trial Sharpe set ==", flush=True)
    trial_sharpes = []
    for key, spec in TRIAL_SET.items():
        if spec["freq"] in ("overnight",):
            dates, rets, _, _, _ = simulate(spec["symbols"], None, "overnight",
                                            spec["tstart"], BPS)
        elif spec["freq"] == "daily-tom":
            dates, rets, _, _, _ = simulate(spec["symbols"], None, "daily-tom",
                                            spec["tstart"], BPS)
        else:
            dates, rets, _, _, _ = simulate(spec["symbols"], fresh_signal(spec),
                                            spec["freq"], spec["tstart"], BPS)
        sh = sharpe_ratio(rets)
        trial_sharpes.append(sh if sh is not None else 0.0)
        print(f"  {key}: sharpe={trial_sharpes[-1]:+.4f} n={len(rets)}", flush=True)
    print(f"n_trials={len(trial_sharpes)}", flush=True)

    for slug, spec in CANDIDATES.items():
        if only and slug not in only:
            continue
        print(f"\n===== {slug} ({spec['idea']}) =====", flush=True)
        symbols = spec["symbols"]
        # net + gross runs (fresh stateful signals each)
        dates, rets, turnover, n_trades, avg_w = simulate(
            symbols, fresh_signal(spec), spec["freq"], spec["tstart"], BPS)
        _, grets, _, _, _ = simulate(
            symbols, fresh_signal(spec), spec["freq"], spec["tstart"], 0.0)
        n = len(rets)
        fl = folds(n)
        frows = []
        for ts, te, ss, se in fl:
            test = rets[ss:se]
            frows.append({"oos_sharpe": sharpe_ratio(test),
                          "oos_return": total_return(test),
                          "oos_max_drawdown": max_drawdown(test)["max_drawdown"],
                          "n_bars": len(test)})
        oos_idx = []
        for _, _, ss, se in fl:
            oos_idx.extend(range(ss, se))
        orets = [rets[i] for i in oos_idx]
        odates = [dates[i] for i in oos_idx]
        ogrets = [grets[i] for i in oos_idx]
        med_sharpe = statistics.median(
            [r["oos_sharpe"] for r in frows if r["oos_sharpe"] is not None])

        # benchmark over identical OOS dates
        bkind = spec["benchmark"]
        if bkind[0] == "bh":
            bdates, brets = simulate_bh([bkind[1]], None, spec["tstart"], BPS)
        else:
            bsyms = list(bkind[1].keys())
            bdates, brets = simulate_bh(bsyms, bkind[1], spec["tstart"], BPS)
        bmap = dict(zip(bdates, brets))
        brets_oos = [bmap[d] for d in odates if d in bmap]
        orets_a = [r for d, r in zip(odates, orets) if d in bmap]
        summ = performance_summary(orets_a)
        bsumm = performance_summary(brets_oos)
        excess = (summ["annualized_return"] - bsumm["annualized_return"]
                  if summ["annualized_return"] is not None
                  and bsumm["annualized_return"] is not None else None)

        dsr = dsr_from_returns(orets, trial_sharpes)

        # cost-speed limit
        years = n / 252
        turnover_ann = turnover / years if years else 0.0
        round_trip = 2 * (BPS / 1e4)
        ivol = sum(avg_w.get(s, 0.0) * ann_vol(s, dates) for s in symbols)
        gsharpe = sharpe_ratio(ogrets)
        drag = turnover_ann * round_trip / ivol if ivol > 0 else None
        budget = gsharpe / 3 if gsharpe else None
        cost_pass = (gsharpe is not None and gsharpe > 0 and drag is not None
                     and drag <= budget)

        tier1 = {
            "oos_sharpe": {"value": med_sharpe, "threshold": 0.3,
                           "pass": med_sharpe is not None and med_sharpe > 0.3},
            "max_drawdown": {"value": summ["max_drawdown"], "threshold": -0.25,
                             "pass": summ["max_drawdown"] is not None
                             and summ["max_drawdown"] > -0.25},
            "dsr": {"value": dsr["dsr"], "threshold": 0.8,
                    "pass": dsr["dsr"] is not None and dsr["dsr"] >= 0.8},
            "beats_benchmark_net": {"value": excess, "threshold": 0.0,
                                    "pass": excess is not None and excess > 0.0},
            "sortino": {"value": summ["sortino"], "threshold": 0.75,
                        "pass": summ["sortino"] is not None and summ["sortino"] >= 0.75},
            "cost_speed_limit": {
                "value": {"cost_sharpe_drag": drag, "budget": budget,
                          "turnover_ann": turnover_ann,
                          "round_trip_cost": round_trip,
                          "instrument_vol_ann": ivol, "gross_sharpe": gsharpe},
                "pass": cost_pass},
        }
        verdict = "validated" if all(v["pass"] for v in tier1.values()) else "invalidated"

        payload = {
            "strategy": slug, "idea": spec["idea"], "round": 5,
            "verdict_tier1": verdict,
            "walk_forward": {"train_bars": TRAIN_BARS, "test_bars": TEST_BARS,
                             "step_bars": STEP_BARS, "embargo_bars": EMBARGO_BARS,
                             "n_folds": len(frows), "oos_bars": len(orets),
                             "folds": frows},
            "oos_summary": summ,
            "benchmark": {"kind": bkind[0], "ref": bkind[1],
                          "oos_summary": bsumm,
                          "excess_return_net": excess},
            "dsr": dsr, "n_trials": len(trial_sharpes),
            "tier1": tier1,
            "trades": n_trades, "turnover_total": turnover,
            "avg_abs_weights": avg_w,
            "data": {"symbols": symbols, "tstart": str(spec["tstart"]),
                     "source": "yfinance daily adjusted via trade-data-equities, pre_adjusted"},
        }
        outdir = os.path.join(VAL, slug)
        with open(os.path.join(outdir, "evidence.json"), "w") as f:
            json.dump(payload, f, indent=2, default=str)
        print(f"  folds={len(frows)} oos_bars={len(orets)} trades~{n_trades}", flush=True)
        for name, t in tier1.items():
            v = t["value"]
            vs = f"{v:.4f}" if isinstance(v, float) else (
                f"drag={v['cost_sharpe_drag']:.4f} budget={v['budget']:.4f}"
                if isinstance(v, dict) else v)
            print(f"  [{'PASS' if t['pass'] else 'FAIL'}] {name}: {vs}", flush=True)
        print(f"  VERDICT: {verdict}", flush=True)


if __name__ == "__main__":
    main()
