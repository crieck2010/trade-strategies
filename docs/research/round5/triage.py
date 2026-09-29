#!/usr/bin/env python3
"""Round 5 triage: structural screens only (NO performance ranking).

For each of the 27 triage hypotheses:
  - implement the frozen signal logic (monthly, t+1 open fills, 5 bps)
  - compute the full-window net-of-costs return stream
  - structural correlation vs REGCOND-1 and pairwise (Pearson on returns)
  - Occam complexity C per trade-agents/docs/design/OCCAMS_DESK.md

Screens: data-clean, C<=5, rho<=0.60 vs REGCOND-1, pairwise rho<=0.60
(prefer lower C on pairwise ties). Writes triage.json.
"""
import datetime as dt
import json
import math
import os
import pickle
import statistics
import sys

WS = os.path.expanduser("~/workspace/trade-suite")
for repo in ("trade-macro",):
    p = os.path.join(WS, repo, "src")
    if p not in sys.path:
        sys.path.insert(0, p)
RV = os.path.join(WS, "trade-strategies/docs/validation/regcond-1")
if RV not in sys.path:
    sys.path.insert(0, RV)

from trade_macro.ratio import ratio_series, enrich_ratios
from trade_macro.regime import classify_regime
from run_validation import simulate as regcond_simulate, WEIGHTS as RC_W

HERE = os.path.dirname(os.path.abspath(__file__))
TRADE_START = dt.date(2018, 1, 1)
BPS = 5.0

bars = pickle.load(open(os.path.join(HERE, "bars.pkl"), "rb"))
B = {s: {d: (o, c) for (d, o, h, l, c, v) in rows} for s, rows in bars.items() if rows}
BO = {s: {d: o for (d, o, h, l, c, v) in rows} for s, rows in bars.items() if rows}

# Master calendar: union of all dates >= 2015; per-symbol ffill panels
CAL = sorted({d for s in B for d in B[s] if d >= dt.date(2015, 1, 1)})
PX, OPX = {}, {}
for s in B:
    m, mo = B[s], BO[s]
    pc, po, last_c, last_o = {}, {}, None, None
    for d in CAL:
        if d in m:
            last_c, last_o = m[d][1], mo[d]
        if last_c is not None:
            pc[d], po[d] = last_c, last_o
    PX[s], OPX[s] = pc, po


def closes_upto(sym, me):
    return [PX[sym][d] for d in CAL if d <= me and d in PX[sym]]


def ratio_upto(a, b, me):
    return [PX[a][d] / PX[b][d] for d in CAL
            if d <= me and d in PX[a] and d in PX[b]]


def month_end_before(d):
    """Last trading day of the month strictly before d's month (on CAL)."""
    j = CAL.index(d) - 1
    while j >= 0 and (CAL[j].year, CAL[j].month) == (d.year, d.month):
        j -= 1
    return CAL[j] if j >= 0 else None


def first_trading_days(dates):
    seen, out = set(), []
    for d in dates:
        k = (d.year, d.month)
        if k not in seen:
            seen.add(k)
            out.append(d)
    return out


START_OVERRIDE = {
    "idea-0010": dt.date(2020, 9, 1),   # SGOV inception 2020-05-26 + 63d carry warmup
    "idea-0017": dt.date(2018, 5, 1),   # VXX Series-B history starts 2018-01-25 + 61d z warmup
}


def simulate_monthly(symbols, target_fn, bps=BPS, tstart=TRADE_START):
    """target_fn(month_end_date) -> {sym: weight}. Fill t+1 open."""
    tdates = [d for d in CAL if d >= tstart and all(dd in PX[s] for s in symbols for dd in [d])]
    # simpler: require all symbols present on the date
    tdates = [d for d in CAL if d >= tstart and all(d in PX[s] for s in symbols)]
    firsts = set(first_trading_days(tdates))
    shares = None
    rets, n_trades, turnover = [], 0, 0.0
    pending = None
    prev_close_val = 1.0
    for i, d in enumerate(tdates):
        if d in firsts:
            me = month_end_before(d)
            if me is not None:
                fill = tdates[i + 1] if i + 1 < len(tdates) else None
                pending = (fill, target_fn(me))
        if pending is not None and pending[0] == d:
            _, tw = pending
            pending = None
            tw = {s: tw.get(s, 0.0) for s in symbols}
            if shares is None:
                open_val, turn_frac = 1.0, 1.0
            else:
                open_val = sum(shares[s] * OPX[s][d] for s in symbols)
                if open_val <= 0:
                    rets.append(-1.0)
                    break
                cur_w = {s: shares[s] * OPX[s][d] / open_val for s in symbols}
                turn_frac = sum(abs(tw[s] - cur_w[s]) for s in symbols)
            cost = (bps / 1e4) * turn_frac * open_val
            turnover += turn_frac
            n_trades += 1
            post_cost = open_val - cost
            shares = {s: tw[s] * post_cost / OPX[s][d] for s in symbols}
        if shares is None:
            rets.append(0.0)
        else:
            close_val = sum(shares[s] * PX[s][d] for s in symbols)
            rets.append(close_val / prev_close_val - 1.0)
            prev_close_val = close_val
    return rets, n_trades, turnover, tdates


def mom_12m1(cl):
    if len(cl) < 253:
        return None
    return cl[-22] / cl[-253] - 1.0 if cl[-253] else None


def mom_6m1(cl):
    if len(cl) < 133:
        return None
    return cl[-22] / cl[-133] - 1.0 if cl[-133] else None


def max_dd(values):
    peak, md = values[0], 0.0
    for v in values[1:]:
        peak = max(peak, v)
        md = min(md, v / peak - 1.0)
    return md


def corr(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    sa = sum((x - ma) ** 2 for x in a)
    sb = sum((x - mb) ** 2 for x in b)
    if sa == 0 or sb == 0:
        return 0.0
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(sa * sb)


# ---------------- REGCOND-1 stream (for the rho screen) ----------------




def _regcond_block():
    global RC_DATES, RC_RETS

    RC_SYMS = ["SPY", "CPER", "TLT", "GLD"]
    rc_dates = sorted({d for s in RC_SYMS for d in B[s]})
    rc_op = {s: {d: BO[s][d] for d in rc_dates if d in BO[s]} for s in RC_SYMS}
    rc_cl = {s: {d: B[s][d][1] for d in rc_dates if d in B[s]} for s in RC_SYMS}
    # forward-fill holes on rc grid
    for s in RC_SYMS:
        last = None
        for d in rc_dates:
            if d in rc_cl[s]:
                last = (rc_op[s][d], rc_cl[s][d])
            rc_op[s][d], rc_cl[s][d] = last
    cu = [{"date": d.isoformat(), "price": rc_cl["CPER"][d]} for d in rc_dates]
    au = [{"date": d.isoformat(), "price": rc_cl["GLD"][d]} for d in rc_dates]
    rows = classify_regime(enrich_ratios(ratio_series(cu, au)), preset="standard")
    lab = {dt.date.fromisoformat(r["date"]): r["regime"] for r in rows}
    labels, cur = {}, "NEUTRAL"
    for d in rc_dates:
        if d in lab:
            cur = lab[d]
        labels[d] = cur
    rrets, _, _, _ = regcond_simulate(rc_dates, rc_op, rc_cl, labels,
                                      lambda l: RC_W[l], BPS)
    RC_DATES = [d for d in rc_dates if d >= TRADE_START]
    RC_RETS = rrets
    print(f"REGCOND-1 stream: {len(RC_RETS)} bars", flush=True)



# ---------------- candidate signal definitions ----------------
CANDS = {}

def c0008(me):
    r = ratio_upto("HYG", "LQD", me)
    hist = r[-504:]
    pct = sum(1 for x in hist if x <= r[-1]) / len(hist)
    return {"HYG": 1.0} if pct > 0.5 else {"LQD": 1.0}
CANDS["idea-0008"] = (["HYG", "LQD"], c0008, 2, "HYG/LQD spread-percentile rotation")

def c0009(me):
    r = ratio_upto("TLT", "SHY", me)
    if len(r) < 504 + 63:
        return {"SHY": 1.0}
    carry = r[-1] / r[-64]
    hist = [r[i] / r[i - 63] for i in range(len(r) - 504, len(r))]
    return {"TLT": 1.0} if carry > statistics.median(hist) else {"SHY": 1.0}
CANDS["idea-0009"] = (["TLT", "SHY"], c0009, 2, "TLT/SHY slope timing")

def c0011(me):
    r = ratio_upto("TIP", "IEF", me)
    if len(r) < 64:
        return {"IEF": 1.0}
    return {"TIP": 1.0} if r[-1] > r[-64] else {"IEF": 1.0}
CANDS["idea-0011"] = (["TIP", "IEF"], c0011, 2, "TIP CPI-proxy timing")

def c0012(me):
    c = closes_upto("SPY", me)
    if len(c) < 504 + 60:
        return {"SPY": 1.0}
    rets = [c[i] / c[i - 1] - 1 for i in range(1, len(c))]
    v60 = statistics.stdev(rets[-60:])
    hist = [statistics.stdev(rets[i - 60:i]) for i in range(len(rets) - 504, len(rets))]
    return {"USMV": 1.0} if v60 > statistics.median(hist) else {"SPY": 1.0}
CANDS["idea-0012"] = (["USMV", "SPY"], c0012, 2, "USMV vol-timing")

def c0013(me):
    ds = [d for d in CAL if d <= me][-126:]
    dd = {s: max_dd([PX[s][d] for d in ds]) for s in ("USMV", "SPLV", "QUAL")}
    return {min(dd, key=dd.get): 1.0}
CANDS["idea-0013"] = (["USMV", "SPLV", "QUAL"], c0013, 3, "defensive min-DD rotation")

def trailing_dd(c, window=21):
    """Max peak-to-trough decline within the trailing `window` closes."""
    w = c[-window:]
    return min(w[i] / max(w[:i + 1]) - 1 for i in range(len(w)))

def c0014_factory():
    state = {"until": None}
    def fn(me):
        c = closes_upto("SPY", me)
        if len(c) >= 21:
            if trailing_dd(c) < -0.10:
                idx = CAL.index(me)
                state["until"] = CAL[min(idx + 60, len(CAL) - 1)]
        if state["until"] is not None and me <= state["until"]:
            return {"SPLV": 1.0}
        return {"SPY": 1.0}
    return fn
CANDS["idea-0014"] = (["SPLV", "SPY"], c0014_factory(), 3, "SPLV post-shock")

def c0015(me):
    v = closes_upto("^VIX", me)
    if len(v) < 252:
        return {"SHY": 1.0}
    hist = sorted(v[-252:])
    return {"SVXY": 1.0} if v[-1] <= hist[int(0.2 * 252)] else {"SHY": 1.0}
CANDS["idea-0015"] = (["SVXY", "SHY"], c0015, 2, "SVXY contango harvest")

def c0016_factory():
    state = {"until": None}
    def fn(me):
        v = closes_upto("^VIX", me)
        if len(v) >= 252:
            hist = sorted(v[-252:])
            if v[-1] >= hist[int(0.9 * 252)]:
                idx = CAL.index(me)
                state["until"] = CAL[min(idx + 20, len(CAL) - 1)]
        if state["until"] is not None and me <= state["until"]:
            return {"SPY": 1.0}
        return {"SHY": 1.0}
    return fn
CANDS["idea-0016"] = (["SPY", "SHY"], c0016_factory(), 3, "VIX-spike dip buy")

def c0017_factory():
    state = {"pos": "SHY"}
    def fn(me):
        r = ratio_upto("VXX", "SPY", me)
        if len(r) >= 61:
            w = r[-61:-1]
            m, s = statistics.mean(w), statistics.pstdev(w)
            z = (r[-1] - m) / s if s > 0 else 0
            if z > 2:
                state["pos"] = "SPY"
            elif z < -2:
                state["pos"] = "SHY"
        return {state["pos"]: 1.0}
    return fn
CANDS["idea-0017"] = (["VXX", "SPY", "SHY"], c0017_factory(), 5, "VXX/SPY z-score rotation")

def c0018_factory():
    state = {"wait_until": None}
    def fn(me):
        c = closes_upto("SVXY", me)
        if len(c) >= 21:
            if trailing_dd(c) < -0.20:
                idx = CAL.index(me)
                state["wait_until"] = CAL[min(idx + 40, len(CAL) - 1)]
        if state["wait_until"] is not None and me <= state["wait_until"]:
            return {"SHY": 1.0}
        return c0015(me)
    return fn
CANDS["idea-0018"] = (["SVXY", "SHY"], c0018_factory(), 4, "SVXY harvest + post-spike wait")

def c0019(me):
    r = ratio_upto("HYG", "LQD", me)
    if len(r) < 504 + 126:
        return {"SHY": 1.0}
    if r[-1] > r[-127]:
        return {"HYG": 1.0}
    if r[-1] > statistics.median(r[-504:]):
        return {"LQD": 1.0}
    return {"SHY": 1.0}
CANDS["idea-0019"] = (["HYG", "LQD", "SHY"], c0019, 3, "credit 3-way")

def c0021(me):
    m = mom_12m1(closes_upto("USO", me))
    return {"USO": 1.0} if (m is not None and m > 0) else {"SHY": 1.0}
CANDS["idea-0021"] = (["USO", "SHY"], c0021, 2, "USO absolute momentum")

def c0022(me):
    m = mom_12m1(closes_upto("UUP", me))
    return {"UUP": 1.0} if (m is not None and m > 0) else {"SHY": 1.0}
CANDS["idea-0022"] = (["UUP", "SHY"], c0022, 2, "UUP absolute momentum")

COMMS = ["USO", "GLD", "DBA", "DBB", "CPER", "UNG"]
def c0028(me):
    ms = {s: mom_12m1(closes_upto(s, me)) for s in COMMS}
    ms = {s: v for s, v in ms.items() if v is not None}
    if not ms:
        return {"SHY": 1.0}
    top = sorted(ms, key=ms.get, reverse=True)[:2]
    return {s: (0.5 if s in top else 0.0) for s in COMMS}
CANDS["idea-0028"] = (COMMS, c0028, 2, "commodity momentum top-2")

BONDS = ["SHY", "IEF", "TLT", "TIP", "HYG", "LQD", "MUB"]
def c0029(me):
    ms = {s: mom_6m1(closes_upto(s, me)) for s in BONDS}
    ms = {s: v for s, v in ms.items() if v is not None}
    if not ms:
        return {"SHY": 1.0}
    top = sorted(ms, key=ms.get, reverse=True)[:2]
    return {s: (0.5 if s in top else 0.0) for s in BONDS}
CANDS["idea-0029"] = (BONDS, c0029, 2, "bond momentum top-2")

FXS = ["UUP", "FXE", "FXY", "FXB", "FXC"]
def c0031(me):
    ms = {s: mom_12m1(closes_upto(s, me)) for s in FXS}
    ms = {s: v for s, v in ms.items() if v is not None}
    if not ms:
        return {"SHY": 1.0}
    top = sorted(ms, key=ms.get, reverse=True)[:2]
    return {s: (0.5 if s in top else 0.0) for s in FXS}
CANDS["idea-0031"] = (FXS, c0031, 2, "currency momentum top-2")

G5 = ["SPY", "EFA", "EEM", "IEF", "DBC"]
def c0032(me):
    held = []
    for s in G5:
        c = closes_upto(s, me)
        if len(c) >= 210 and c[-1] > sum(c[-210:]) / 210:
            held.append(s)
    if not held:
        return {"SHY": 1.0}
    w = {s: 0.0 for s in G5}
    for s in held:
        w[s] = 1.0 / len(held)
    return w
CANDS["idea-0032"] = (G5 + ["SHY"], c0032, 2, "GTAA-5 absolute momentum")

def c0033(me):
    ms = {s: mom_12m1(closes_upto(s, me)) for s in ("SPY", "EFA", "EEM")}
    ms = {s: v for s, v in ms.items() if v is not None}
    if not ms:
        return {"SHY": 1.0}
    top = max(ms, key=ms.get)
    shy_r = mom_12m1(closes_upto("SHY", me)) or 0
    return {top: 1.0} if ms[top] > shy_r else {"SHY": 1.0}
CANDS["idea-0033"] = (["SPY", "EFA", "EEM", "SHY"], c0033, 3, "dual momentum GEM")

def c0034(me):
    ms = {s: mom_12m1(closes_upto(s, me)) for s in ("EFA", "EEM")}
    ms = {s: v for s, v in ms.items() if v is not None}
    if not ms:
        return {"SHY": 1.0}
    top = max(ms, key=ms.get)
    return {top: 1.0} if ms[top] > 0 else {"SHY": 1.0}
CANDS["idea-0034"] = (["EFA", "EEM", "SHY"], c0034, 2, "EFA/EEM rotation")

def c0035(me):
    c = closes_upto("GLD", me)
    if len(c) >= 210 and c[-1] > sum(c[-210:]) / 210:
        return {"GLD": 1.0}
    return {"SHY": 1.0}
CANDS["idea-0035"] = (["GLD", "SHY"], c0035, 2, "GLD 10m trend")

def c0036(me):
    r = ratio_upto("TIP", "IEF", me)
    if len(r) < 64:
        return {"SHY": 1.0}
    return {"DBC": 1.0} if r[-1] > r[-64] else {"SHY": 1.0}
CANDS["idea-0036"] = (["DBC", "SHY"], c0036, 2, "breakeven commodity tilt")

def c0037(me):
    r = ratio_upto("SLV", "GLD", me)
    if len(r) < 127:
        return {"GLD": 1.0}
    return {"SLV": 1.0} if r[-1] > r[-127] else {"GLD": 1.0}
CANDS["idea-0037"] = (["SLV", "GLD"], c0037, 2, "SLV/GLD rotation")

def c0038(me):
    ms = {s: mom_12m1(closes_upto(s, me)) for s in ("USO", "GLD")}
    ms = {s: v for s, v in ms.items() if v is not None}
    if not ms:
        return {"SHY": 1.0}
    top = max(ms, key=ms.get)
    return {top: 1.0} if ms[top] > 0 else {"SHY": 1.0}
CANDS["idea-0038"] = (["USO", "GLD", "SHY"], c0038, 2, "USO/GLD rotation")

def c0010(me):
    cs = {s: closes_upto(s, me) for s in ("SGOV", "SHY", "IEF")}
    if any(len(v) < 64 for v in cs.values()):
        return {"SHY": 1.0}
    carry = {s: cs[s][-1] / cs[s][-64] - 1 for s in cs}
    dur = {"SGOV": 0.25, "SHY": 2.0, "IEF": 7.5}
    return {max(carry, key=lambda s: carry[s] / dur[s]): 1.0}
CANDS["idea-0010"] = (["SGOV", "SHY", "IEF"], c0010, 3, "short carry ladder")


def simulate_overnight(sym, tstart=TRADE_START):
    tdates = [d for d in CAL if d >= tstart and d in PX[sym]]
    rets = []
    for i, d in enumerate(tdates[:-1]):
        nxt = tdates[i + 1]
        r = OPX[sym][nxt] / PX[sym][d] - 1.0 - 2 * (BPS / 1e4)
        rets.append(r)
    return rets, len(rets), 0.0, tdates[:-1]


def simulate_tom(tstart=TRADE_START):
    tdates = [d for d in CAL if d >= tstart and d in PX["SPY"] and d in PX["SHY"]]
    in_tom = set()
    for i, d in enumerate(CAL):
        fwd = sum(1 for j in range(i, len(CAL))
                  if (CAL[j].year, CAL[j].month) == (d.year, d.month))
        back = sum(1 for j in range(0, i + 1)
                   if (CAL[j].year, CAL[j].month) == (d.year, d.month))
        if back <= 3 or fwd <= 2:
            in_tom.add(d)
    rets = []
    prev = None
    for d in tdates:
        sym = "SPY" if d in in_tom else "SHY"
        if prev is not None:
            rets.append(PX[sym][d] / PX[sym][prev] - 1.0)
        else:
            rets.append(0.0)
        prev = d
    return rets, 0, 0.0, tdates



def _run_results():
    results, streams = {}, {}
    for iid, (syms, fn, C, desc) in CANDS.items():
        tstart = START_OVERRIDE.get(iid, TRADE_START)
        rets, nt, to, cdates = simulate_monthly(syms, fn, tstart=tstart)
        rmap = dict(zip(RC_DATES, RC_RETS))
        pairs = [(r, rmap[d]) for d, r in zip(cdates, rets) if d in rmap]
        rho = corr([p[0] for p in pairs], [p[1] for p in pairs]) if len(pairs) > 126 else None
        results[iid] = {"desc": desc, "C": C, "n_bars": len(rets),
                        "n_trades": nt, "rho_vs_regcond1": rho, "symbols": syms,
                        "tstart": str(tstart)}
        streams[iid] = (cdates, rets)
        print(f"{iid}: C={C} bars={len(rets)} trades~{nt} rho_vs_RC={rho if rho is None else round(rho,3)}  {desc}", flush=True)

    for iid, sym in (("idea-0024", "SPY"), ("idea-0027", "GLD")):
        rets, nt, to, cdates = simulate_overnight(sym)
        rmap = dict(zip(RC_DATES, RC_RETS))
        pairs = [(r, rmap[d]) for d, r in zip(cdates, rets) if d in rmap]
        rho = corr([p[0] for p in pairs], [p[1] for p in pairs]) if len(pairs) > 126 else None
        C = 1
        results[iid] = {"desc": "overnight " + sym, "C": C, "n_bars": len(rets),
                        "n_trades": nt, "rho_vs_regcond1": rho, "symbols": [sym],
                        "tstart": str(TRADE_START)}
        streams[iid] = (cdates, rets)
        print(f"{iid}: C={C} bars={len(rets)} trades~{nt} rho_vs_RC={rho if rho is None else round(rho,3)}  overnight {sym}", flush=True)

    rets, nt, to, cdates = simulate_tom()
    rmap = dict(zip(RC_DATES, RC_RETS))
    pairs = [(r, rmap[d]) for d, r in zip(cdates, rets) if d in rmap]
    rho = corr([p[0] for p in pairs], [p[1] for p in pairs]) if len(pairs) > 126 else None
    results["idea-0026"] = {"desc": "SPY turn-of-month", "C": 2, "n_bars": len(rets),
                            "n_trades": nt, "rho_vs_regcond1": rho,
                            "symbols": ["SPY", "SHY"], "tstart": str(TRADE_START)}
    streams["idea-0026"] = (cdates, rets)
    print(f"idea-0026: C=2 bars={len(rets)} rho_vs_RC={rho if rho is None else round(rho,3)}  SPY turn-of-month", flush=True)

    # pairwise correlations (inner join on dates)
    ids = sorted(results)
    pair = {}
    for i, a in enumerate(ids):
        da, ra = streams[a]
        ma = dict(zip(da, ra))
        for b in ids[i + 1:]:
            db, rb = streams[b]
            common = sorted(set(da) & set(db))
            if len(common) > 126:
                pair[f"{a}|{b}"] = corr([ma[d] for d in common],
                                        [dict(zip(db, rb))[d] for d in common])

    with open(os.path.join(HERE, "triage.json"), "w") as f:
        json.dump({"results": results, "pairwise_rho": pair,
                   "n_triage": len(results)}, f, indent=2)
    print("triage.json written", flush=True)




def main():
    _regcond_block()
    _run_results()


if __name__ == "__main__":
    main()
