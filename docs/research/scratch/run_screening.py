"""RESEARCH SCRATCH — Phase B screening driver (2026-09-26).

Loads the persisted panel, runs each screenable idea's minimal
implementation through trade-backtest (ONE in-sample backtest each),
writes docs/research/evidence/screening_results.json, prints the ranking.

Run:  python3 docs/research/scratch/run_screening.py [IDEA_ID ...]
With no args, runs all six screenable ideas in dependency-free order.
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402

SCRATCH = os.path.dirname(os.path.abspath(__file__))
PANEL = os.path.join(SCRATCH, "..", "evidence", "panel")

IDEAS = ["pairs_1", "xmom_1", "fmom_1", "trend_vt", "tsmom_cr", "bab_1",
         "carry_1"]


def load_panel() -> dict:
    panel: dict[str, dict[str, tuple]] = {}

    def read(sub: str, keyfn):
        d = os.path.join(PANEL, sub)
        if not os.path.isdir(d):
            return
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".csv"):
                continue
            key = keyfn(fn[:-4])
            series = {}
            with open(os.path.join(d, fn)) as fh:
                for row in csv.DictReader(fh):
                    try:
                        series[row["date"]] = (
                            float(row["o"]), float(row["h"]),
                            float(row["l"]), float(row["c"]),
                            float(row["v"]))
                    except ValueError:
                        continue
            if series:
                panel[key] = series

    read("eq", lambda t: t)
    read("etf", lambda t: t)
    read("fut", lambda r: "FUT_" + r)
    read("fx", lambda t: "FX_" + t)
    read("crypto", lambda s: s.replace("_", "/"))
    return panel


def panel_bars(panel: dict, symbols: list[str]) -> dict[str, list[dict]]:
    out = {}
    for s in symbols:
        series = panel.get(s, {})
        rows = []
        for d in sorted(series):
            if not (common.TRADE_START <= d < common.TRADE_END):
                continue
            o, h, l, c, v = series[d]
            rows.append({
                "ts": datetime(int(d[:4]), int(d[5:7]), int(d[8:10]),
                                   tzinfo=timezone.utc),
                "o": o, "h": h, "l": l, "c": c, "v": v,
            })
        out[s] = rows
    return out


def screen_one(modname: str, panel: dict) -> dict:
    mod = __import__(modname)
    t0 = time.time()
    ctx = mod.prepare(panel)
    spec = mod.build(ctx)
    bars = spec["bars"] if spec["bars"] is not None else panel_bars(
        panel, spec["symbols"])
    result = common.run_backtest(
        spec["symbols"], bars, spec["strategy"], spec["sizer"],
        spec["costs"], note="Phase B screening: " + spec["note"])
    m = common.metrics_summary(result)
    return {
        "idea": mod.IDEA_ID,
        "module": modname,
        "params": mod.PARAMS,
        "simplifications": mod.SIMPLIFICATIONS,
        "thesis_line": mod.THESIS_LINE,
        "note": spec["note"],
        "window": [common.TRADE_START, "2026-09-25"],
        "symbols_traded": spec["symbols"],
        "n_symbols": len(spec["symbols"]),
        "metrics": m,
        "assumptions": result.assumptions,
        "elapsed_s": round(time.time() - t0, 1),
    }


def main() -> int:
    which = sys.argv[1:] or IDEAS
    panel = load_panel()
    print(f"[screen] panel keys: {len(panel)}", flush=True)
    results, errors = [], {}
    for modname in which:
        try:
            r = screen_one(modname, panel)
            results.append(r)
            m = r["metrics"]
            print(f"[screen] {r['idea']}: Sharpe={m['sharpe_ratio']:.3f} "
                  f"maxDD={m['max_drawdown']:.3f} trades={m['num_trades']:.0f} "
                  f"ret={m['total_return']:.3f} ({r['elapsed_s']}s)", flush=True)
        except Exception:  # noqa: BLE001 - one idea must not kill the batch
            errors[modname] = traceback.format_exc()
            print(f"[screen] {modname} FAILED:\n{errors[modname]}", flush=True)
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_screened": len(results),
        "results": results,
        "errors": {k: v[-2000:] for k, v in errors.items()},
    }
    os.makedirs(os.path.join(SCRATCH, "..", "evidence"), exist_ok=True)
    path = os.path.join(SCRATCH, "..", "evidence", "screening_results.json")
    with open(path, "w") as fh:
        json.dump(out, fh, indent=2, default=str)
    print(f"[screen] n_screened={len(results)} -> {path}", flush=True)

    print("\n=== RANKING (in-sample Sharpe) ===")
    for r in sorted(results,
                    key=lambda r: r["metrics"]["sharpe_ratio"]
                    if r["metrics"]["sharpe_ratio"] == r["metrics"]["sharpe_ratio"]
                    else -99):
        m = r["metrics"]
        print(f"{r['idea']:9s} Sharpe {m['sharpe_ratio']:+.3f}  "
              f"maxDD {m['max_drawdown']:.3f}  trades {m['num_trades']:6.0f}  "
              f"ret {m['total_return']:+.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
