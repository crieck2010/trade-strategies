#!/usr/bin/env python3
"""Trial-4 validation harness: REGCOND-1 walk-forward through the 7-gate desk.

Frozen spec: docs/validation/regcond-1/PRE-REGISTRATION.md (commit ca2aa4e).
Implements the spec literally. No parameters are fitted; walk-forward tests
regime stability per the pre-reg geometry (104w/26w/26w, 5-day embargo).

Design decisions (all documented, none optimizing):
  D1. Weeks are trading days: train=520 bars, test=130 bars, step=130 bars,
      embargo=5 bars. (The series is daily bars; "26-week" ~= 130 trading days.)
  D2. Regime labels are computed ONCE on the full 2015+ series via
      trade-macro's frozen pipeline. Every label at day t uses only data <= t
      (trailing z_252 / ma200, persistence from NEUTRAL), so per-fold
      recomputation would give identical labels; the 2015-2017 warmup lets
      persistence converge before trading starts 2018-01-01. This is what a
      live implementation would have produced.
  D3. Date grid = union of the four ETFs' trading dates; a missing bar is
      forward-filled (hold): no signal change, no rebalance advance, prices
      carried. The regime ratio rows only exist on shared CPER/GLD dates
      (trade-macro align_series); a hole in either metal = no new label row =
      persisted label carries. Hole-day count is reported.
  D4. Rebalance: first trading day of month M reads the persisted label at
      the LAST trading day of M-1; fills at the next trading day's OPEN
      (t->t+1). Turnover cost = bps * |target_w - drifted_w| summed, charged
      against portfolio value at the fill; target shares set on post-cost
      value. Fully invested, long-only, no cash buffer.
  D5. Benchmark 60/40 SPY/TLT: same monthly t+1-open machinery, fixed
      weights, same bps. Gated excess = ann(strategy OOS) - ann(benchmark
      OOS) over the identical concatenated test windows.
  D6. DSR trial set = round-2 Phase B in-sample Sharpes [0.918, -0.493]
      (REGCOND-1, RVBOND-1), n_trials=2, per the pre-reg's honesty section.
  D7. Cost sensitivity (2/5/10 bps) re-runs the simulator; only the 5 bps
      run is the official validation.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.expanduser("~/workspace/trade-suite")
for repo in ("trade-data-equities", "trade-macro", "trade-overfit"):
    p = os.path.join(WS, repo, "src")
    if p not in sys.path:
        sys.path.insert(0, p)

from trade_data_equities import EquitiesDataClient  # noqa: E402
from trade_data_equities.providers.yfinance import YFinanceProvider  # noqa: E402
from trade_data_equities.models import Timeframe  # noqa: E402
from trade_macro.ratio import ratio_series, enrich_ratios  # noqa: E402
from trade_macro.regime import classify_regime  # noqa: E402
from trade_overfit.dsr import dsr_from_returns  # noqa: E402
from trade_overfit.gates import preset_gates, evaluate_gates  # noqa: E402
from trade_overfit.metrics import performance_summary, sharpe_ratio  # noqa: E402
from trade_overfit.metrics import max_drawdown, total_return  # noqa: E402
from trade_overfit.regimes import regime_report  # noqa: E402

SYMBOLS = ["SPY", "CPER", "TLT", "GLD"]
WARMUP_START = dt.date(2015, 1, 1)
TRADE_START = dt.date(2018, 1, 1)
TRADE_END = dt.date(2026, 9, 25)  # inclusive; client end bound is exclusive
COST_BPS = 5.0

WEIGHTS = {
    "EXPANSION": {"SPY": 0.60, "CPER": 0.20, "TLT": 0.20, "GLD": 0.00},
    "CONTRACTION": {"SPY": 0.20, "CPER": 0.00, "TLT": 0.40, "GLD": 0.40},
    "NEUTRAL": {"SPY": 0.25, "CPER": 0.25, "TLT": 0.25, "GLD": 0.25},
}
BENCH_WEIGHTS = {"SPY": 0.60, "CPER": 0.0, "TLT": 0.40, "GLD": 0.0}

TRAIN_BARS, TEST_BARS, STEP_BARS, EMBARGO_BARS = 520, 130, 130, 5
TRIAL_SHARPES = [0.918, -0.493]  # round-2 Phase B in-sample: REGCOND-1, RVBOND-1


# ------------------------------------------------------------------ data --
def fetch_bars():
    client = EquitiesDataClient(YFinanceProvider())
    out = {}
    for sym in SYMBOLS:
        bars = client.get_bars(sym, Timeframe.DAILY, WARMUP_START,
                               TRADE_END + dt.timedelta(days=1),
                               adjusted=True, use_cache=True)
        out[sym] = {b.timestamp.date(): (b.open, b.close) for b in bars}
        print(f"{sym}: {len(out[sym])} bars "
              f"{min(out[sym])}..{max(out[sym])}", flush=True)
    return out


def build_grid(bars_by_sym):
    """Union date grid; forward-fill holes (hold policy)."""
    dates = sorted({d for m in bars_by_sym.values() for d in m})
    closes, opens = {}, {}
    hole_days = 0
    for sym in SYMBOLS:
        m = bars_by_sym[sym]
        c, o, last = {}, {}, None
        for d in dates:
            if d in m:
                last = m[d]
            else:
                hole_days += 1
            if last is None:
                raise RuntimeError(f"{sym}: no bar on or before grid start")
            o[d], c[d] = last[0], last[1]
        opens[sym], closes[sym] = o, c
    return dates, opens, closes, hole_days


def regime_labels(dates, closes):
    """Persisted copper:gold regime per date via trade-macro frozen pipeline."""
    cu = [{"date": d.isoformat(), "price": closes["CPER"][d]} for d in dates]
    au = [{"date": d.isoformat(), "price": closes["GLD"][d]} for d in dates]
    rows = classify_regime(enrich_ratios(ratio_series(cu, au)),
                           preset="standard")
    lab = {dt.date.fromisoformat(r["date"]): r["regime"] for r in rows}
    # carry the persisted label across ratio-hole days (no signal change)
    out, cur = {}, "NEUTRAL"
    for d in dates:
        if d in lab:
            cur = lab[d]
        out[d] = cur
    return out


# ------------------------------------------------------------ simulation --
def month_key(d):
    return (d.year, d.month)


def first_trading_days(dates):
    seen, out = set(), []
    for d in dates:
        k = month_key(d)
        if k not in seen:
            seen.add(k)
            out.append(d)
    return out


def simulate(dates, opens, closes, labels, weights_fn, bps):
    """Monthly rebalance at t+1 open. Returns (daily_returns, n_trades,
    turnover_total, rebalance_log)."""
    tdates = [d for d in dates if d >= TRADE_START]
    firsts = set(first_trading_days(tdates))
    # last_of_prev built on the FULL grid so January 2018 reads the
    # 2017-12-29 label from warmup history (spec-literal: every month trades)
    last_of_prev = {}
    prev = None
    for d in dates:
        if prev is not None and month_key(d) != month_key(prev):
            last_of_prev[d] = prev
        prev = d
    shares = None
    rets, log = [], []
    turnover_total, n_trades = 0.0, 0
    pending = None  # (fill_date, target_weights, signal_label)
    prev_close_val = 1.0  # capital / portfolio value at previous close

    for i, d in enumerate(tdates):
        if d in firsts and d in last_of_prev:
            read_day = last_of_prev[d]
            pending = (tdates[i + 1] if i + 1 < len(tdates) else None,
                       weights_fn(labels[read_day]), labels[read_day])
        if pending is not None and pending[0] == d:
            _, tw, sig_label = pending
            pending = None
            if shares is None:
                open_val = 1.0
                turn_frac = 1.0  # full notional deployed
            else:
                open_val = sum(shares[s] * opens[s][d] for s in SYMBOLS)
                cur_w = {s: shares[s] * opens[s][d] / open_val
                         for s in SYMBOLS}
                turn_frac = sum(abs(tw[s] - cur_w[s]) for s in SYMBOLS)
            cost = (bps / 1e4) * turn_frac * open_val
            turnover_total += turn_frac * open_val
            n_trades += 1
            post_cost = open_val - cost
            shares = {s: tw[s] * post_cost / opens[s][d] for s in SYMBOLS}
            log.append({"date": d.isoformat(),
                        "label": sig_label,
                        "weights": tw})
        if shares is None:
            rets.append(0.0)
        else:
            close_val = sum(shares[s] * closes[s][d] for s in SYMBOLS)
            rets.append(close_val / prev_close_val - 1.0)
            prev_close_val = close_val
    return rets, n_trades, turnover_total, log


# ------------------------------------------------------------- walk-forward
def folds(n):
    """(train_start, train_end, test_start, test_end) index tuples."""
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


def fold_stats(rets):
    fl = folds(len(rets))
    rows = []
    for ts, te, ss, se in fl:
        test = rets[ss:se]
        rows.append({
            "train_start": ts, "train_end": te,
            "test_start": ss, "test_end": se,
            "n_bars": len(test),
            "oos_sharpe": sharpe_ratio(test),
            "oos_return": total_return(test),
            "oos_max_drawdown": max_drawdown(test)["max_drawdown"],
        })
    return rows


def concat_oos(rets):
    idx = []
    for _, _, ss, se in folds(len(rets)):
        idx.extend(range(ss, se))
    return [rets[i] for i in idx], idx


# ------------------------------------------------------------------- main
def main():
    print("== fetch ==", flush=True)
    bars_by_sym = fetch_bars()
    dates, opens, closes, hole_days = build_grid(bars_by_sym)
    print(f"grid: {len(dates)} dates, {hole_days} symbol-hole-days", flush=True)

    print("== regime labels ==", flush=True)
    labels = regime_labels(dates, closes)
    trade_dates = [d for d in dates if d >= TRADE_START]
    from collections import Counter
    print("OOS-window label mix:",
          dict(Counter(labels[d] for d in trade_dates)), flush=True)

    print("== simulate strategy @5bps ==", flush=True)
    srets, n_trades, turnover, rlog = simulate(
        dates, opens, closes, labels, lambda lab: WEIGHTS[lab], COST_BPS)
    print(f"rebalances: {len(rlog)}, round trips~{n_trades}, "
          f"turnover ${turnover:,.0f} per $1", flush=True)

    print("== simulate 60/40 benchmark @5bps ==", flush=True)
    brets, _, _, _ = simulate(dates, opens, closes, labels,
                              lambda lab: BENCH_WEIGHTS, COST_BPS)

    orets, oidx = concat_oos(srets)
    obrets = [brets[i] for i in oidx]
    frows = fold_stats(srets)
    print(f"folds: {len(frows)}, OOS bars: {len(orets)}", flush=True)

    summ = performance_summary(orets)
    bsumm = performance_summary(obrets)
    dsr = dsr_from_returns(orets, TRIAL_SHARPES)
    reg = regime_report(orets)

    evidence = {
        "dsr": dsr["dsr"],
        "median_oos_sharpe": (statistics.median(
            [r["oos_sharpe"] for r in frows
             if r["oos_sharpe"] is not None])
            if any(r["oos_sharpe"] is not None for r in frows) else None),
        "max_drawdown": summ["max_drawdown"],
        "worst_regime_sharpe": reg["worst_regime_sharpe"],
        "excess_return_vs_benchmark_after_costs":
            (summ["annualized_return"] - bsumm["annualized_return"]
             if summ["annualized_return"] is not None
             and bsumm["annualized_return"] is not None else None),
        "sortino": summ["sortino"],
        "calmar": summ["calmar"],
    }
    gate_results = evaluate_gates(evidence, preset_gates("standard"))
    verdict = "PASS" if all(g["passed"] for g in gate_results) else "KILL"

    # two-tier supplementary (NOT the official verdict; no pre-reg amendment)
    tier1 = {
        "oos_sharpe": {"value": evidence["median_oos_sharpe"],
                       "threshold": 0.3,
                       "pass": (evidence["median_oos_sharpe"] is not None
                                and evidence["median_oos_sharpe"] > 0.3)},
        "max_drawdown": {"value": evidence["max_drawdown"],
                         "threshold": -0.25,
                         "pass": (evidence["max_drawdown"] is not None
                                  and evidence["max_drawdown"] > -0.25)},
        "dsr": {"value": evidence["dsr"], "threshold": 0.8,
                "pass": (evidence["dsr"] is not None
                         and evidence["dsr"] >= 0.8)},
        "beats_benchmark_net": {
            "value": evidence["excess_return_vs_benchmark_after_costs"],
            "threshold": 0.0,
            "pass": (evidence["excess_return_vs_benchmark_after_costs"]
                     is not None
                     and evidence["excess_return_vs_benchmark_after_costs"] > 0.0)},
        "sortino": {"value": evidence["sortino"], "threshold": 0.75,
                    "pass": (evidence["sortino"] is not None
                             and evidence["sortino"] >= 0.75)},
    }
    tier1_verdict = ("PASS" if all(v["pass"] for v in tier1.values())
                     else "FAIL")

    # cost sensitivity (2/10 bps; official run is 5 bps)
    sens = {}
    for bps in (2.0, 10.0):
        r2, _, _, _ = simulate(dates, opens, closes, labels,
                               lambda lab: WEIGHTS[lab], bps)
        o2 = [r2[i] for i in oidx]
        s2 = performance_summary(o2)
        sens[f"{bps:g}bps"] = {
            "total_return": s2["total_return"],
            "annualized_return": s2["annualized_return"],
            "sharpe": s2["sharpe"],
            "max_drawdown": s2["max_drawdown"],
        }

    payload = {
        "strategy": "REGCOND-1",
        "trial": 4,
        "verdict_official_7gate": verdict,
        "verdict_two_tier_supplementary": tier1_verdict,
        "spec_commit": "ca2aa4e",
        "design_decisions": ["D1", "D2", "D3", "D4", "D5", "D6", "D7"],
        "data": {
            "symbols": SYMBOLS,
            "warmup_start": str(WARMUP_START),
            "trade_start": str(TRADE_START),
            "trade_end": str(TRADE_END),
            "grid_dates": len(dates),
            "symbol_hole_days": hole_days,
            "source": "trade-data-equities YFinanceProvider, adjusted=True",
        },
        "walk_forward": {
            "train_bars": TRAIN_BARS, "test_bars": TEST_BARS,
            "step_bars": STEP_BARS, "embargo_bars": EMBARGO_BARS,
            "n_folds": len(frows), "oos_bars": len(orets),
            "folds": frows,
        },
        "oos_summary": summ,
        "benchmark_oos_summary": bsumm,
        "dsr": dsr,
        "dsr_trial_sharpes": TRIAL_SHARPES,
        "regime_report": reg,
        "label_mix_oos": {k: v for k, v in
                          Counter(labels[d] for d in trade_dates).items()},
        "rebalances": len(rlog),
        "gates_official": gate_results,
        "tier1_supplementary": tier1,
        "cost_sensitivity": sens,
        "official_cost_bps": COST_BPS,
    }
    with open(os.path.join(HERE, "evidence.json"), "w") as f:
        json.dump(payload, f, indent=2, default=str)

    print("\n== OFFICIAL 7-GATE TABLE ==")
    for g in gate_results:
        v = g["value"]
        vs = f"{v:.4f}" if isinstance(v, float) else v
        print(f"  [{'PASS' if g['passed'] else 'FAIL'}] {g['name']}: "
              f"{vs} vs {g['op']} {g['threshold']}")
    print(f"OFFICIAL VERDICT: {verdict}")
    print("\n== TWO-TIER SUPPLEMENTARY ==")
    for name, t in tier1.items():
        v = t["value"]
        vs = f"{v:.4f}" if isinstance(v, float) else v
        print(f"  [{'pass' if t['pass'] else 'fail'}] {name}: "
              f"{vs} vs threshold {t['threshold']}")
    print(f"SUPPLEMENTARY TIER-1: {tier1_verdict}")
    print("\n== COST SENSITIVITY ==")
    for k, v in sens.items():
        print(f"  {k}: ann={v['annualized_return']:.4f} "
              f"sharpe={v['sharpe']:.3f} maxDD={v['max_drawdown']:.3f}")
    print("evidence.json written")


if __name__ == "__main__":
    main()
