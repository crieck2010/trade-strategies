"""Fidelity check: the executable ``regcond_1`` strategy vs the frozen
REGCOND-1 validation evidence.

What it proves
--------------
1. **Label identity** -- streaming the validation's own price grid through
   ``RegCond1.on_bar`` reproduces the validation's persisted copper:gold
   regime labels *exactly* (every date).
2. **Decision identity** -- the strategy's month-boundary rebalance events
   (date, decision label, target weights) match the labels/weights the
   validation's simulator consumes, exactly.
3. **Evidence identity** -- feeding the strategy's labels through the
   validation's own ``simulate`` reproduces the Tier-1 evidence numbers in
   ``tier1_evidence.json`` (bit-identical expected: same labels, same
   simulator, same data, same metric functions).

Needs network (yfinance, cached when available) and the trade-macro /
trade-strategies / trade-overfit packages on ``PYTHONPATH``.  Takes a few
minutes: the strategy recomputes the regime pipeline per bar, exactly as it
does in production.

Usage:
    PYTHONPATH=src:../trade-macro/src:../trade-overfit/src python3 \\
        docs/validation/regcond-1/fidelity_check.py
"""

from __future__ import annotations

import importlib.util
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVIDENCE = json.loads((HERE / "tier1_evidence.json").read_text())


def load_validation_module():
    spec = importlib.util.spec_from_file_location(
        "run_validation", HERE / "run_validation.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    rv = load_validation_module()
    from trade_overfit.metrics import performance_summary, sharpe_ratio  # noqa: E402
    from trade_strategies import RegCond1, SignalAction  # noqa: E402
    from trade_strategies.regcond_1 import WEIGHTS  # noqa: E402

    symbols = ["SPY", "CPER", "TLT", "GLD"]
    bars_by_sym = rv.fetch_bars()
    dates, opens, closes, hole_days = rv.build_grid(bars_by_sym)
    print(f"grid: {len(dates)} trading days, {hole_days} symbol-hole-days, "
          f"{dates[0]} .. {dates[-1]}", flush=True)

    # -- 1. the validation's own labels -----------------------------------
    val_labels = rv.regime_labels(dates, closes)

    # -- stream the identical grid through the production strategy ---------
    strat = RegCond1(symbols)
    events: list[tuple] = []  # (date, decision_label, {sym: weight})
    prev = None
    for d in dates:
        bars = {
            s: {"timestamp": d.isoformat(), "open": opens[s][d],
                "high": opens[s][d], "low": opens[s][d],
                "close": closes[s][d], "volume": 0}
            for s in symbols
        }
        sigs = strat.on_bar(datetime(d.year, d.month, d.day), bars)
        if sigs:
            decision_label = strat.label_history[prev]
            weights = {
                s.symbol: (s.strength if s.action is SignalAction.LONG else 0.0)
                for s in sigs
            }
            events.append((d, decision_label, weights))
        prev = d
    print(f"strategy emitted {len(events)} rebalance events", flush=True)

    mism = [d for d in dates
            if strat.label_history.get(d) != val_labels.get(d)]
    if mism:
        print(f"FAIL: {len(mism)} label mismatches, first: {mism[:5]}")
        return 1
    print(f"1. label identity: OK ({len(dates)} dates, exact match)")

    # -- 2. decision identity ----------------------------------------------
    expected = []
    for i, d in enumerate(dates):
        if i > 0 and (d.year, d.month) != (dates[i - 1].year, dates[i - 1].month):
            read_day = dates[i - 1]
            expected.append(
                (d, val_labels[read_day], dict(WEIGHTS[val_labels[read_day]])))
    exp_tail = [e for e in expected if e[0] >= events[0][0]]
    assert len(events) == len(exp_tail), (len(events), len(exp_tail))
    for (d, lab, w), (ed, elab, ew) in zip(events, exp_tail):
        assert (d, lab, w) == (ed, elab, ew), (d, lab, w, ed, elab, ew)
    print(f"2. decision identity: OK ({len(events)} rebalance events, "
          f"date+label+weights exact)")

    # -- 3. evidence identity through the validation's own simulator ------
    strat_labels = {d: strat.label_history[d] for d in dates}
    srets, n_trades, _turn, _rlog = rv.simulate(
        dates, opens, closes, strat_labels, lambda lab: WEIGHTS[lab], 5.0)
    brets, _, _, _ = rv.simulate(
        dates, opens, closes, strat_labels, lambda lab: rv.BENCH_WEIGHTS, 5.0)
    orets, oidx = rv.concat_oos(srets)
    obrets = [brets[i] for i in oidx]
    frows = rv.fold_stats(srets)
    oos_sharpes = [r["oos_sharpe"] for r in frows
                   if r["oos_sharpe"] is not None]
    sharpe_med = statistics.median(oos_sharpes)
    summ = performance_summary(orets)
    bsumm = performance_summary(obrets)

    # Evidence values are rounded in tier1_evidence.json; the honest check is
    # that the strategy-driven full-precision value rounds to the published
    # figure (same labels + same simulator + same data => same series).
    def _decimals(x: float) -> int:
        s = repr(x)
        return len(s.split(".")[1]) if "." in s else 0

    checks = [
        ("oos_sharpe_median", sharpe_med, EVIDENCE["gates"][0]["value"]),
        ("max_drawdown", summ["max_drawdown"], EVIDENCE["gates"][1]["value"]),
        ("excess_return_vs_benchmark_net_per_yr",
         summ["annualized_return"] - bsumm["annualized_return"],
         EVIDENCE["gates"][3]["value"]),
        ("sortino", summ["sortino"], EVIDENCE["gates"][4]["value"]),
    ]
    ok = True
    for name, got, want in checks:
        good = (got is not None
                and round(got, _decimals(want)) == want)
        ok &= good
        g = f"{got:.6f}" if got is not None else "None"
        print(f"   {name}: strategy-driven {g} rounds to evidence {want} "
              f"-> {'OK' if good else 'MISMATCH'}")
    print("   deflated_sharpe: 1.0 (trial-4 trade-overfit evidence; "
          "n_trials=2 pre-registered — re-anchored, not recomputed)")
    if not ok:
        print("FAIL: evidence mismatch")
        return 1
    print(f"3. evidence identity: OK ({n_trades} rebalances, "
          f"{len(frows)} folds; Tier-1 numbers reproduced)")
    print("FIDELITY: VALIDATED — regcond_1 == REGCOND-1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
