"""RESEARCH SCRATCH — round-2 Phase B screening driver (2026-09-26).

Runs the screenable Track-2 ideas (RVBOND-1, REGCOND-1) — ONE in-sample
backtest each through trade-backtest — and writes
docs/research/round2/evidence/screening2_results.json.

NOT screened here (recorded elsewhere, do NOT count toward n_screened):
  - Track-1 (SENTDIV-1, ATTN-1, EVTDRIFT-1, SENTCAP-1): deferred, see
    scratch/track1_deferral.py
  - BASIS-1: unscreenable, see scratch/basis_1.py
  - Track-3 (VOLCAL-1, VOLSKEW-1, VOLDISP-1): sketches only, IDEAS-2.md

Run:  python3 docs/research/round2/scratch/run_screening2.py
"""

from __future__ import annotations

import csv
import json
import os
import sys
import time
import traceback
from datetime import datetime, timezone

_SCRATCH2 = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _SCRATCH2)                      # rvbond_1, regcond_1
sys.path.insert(0, os.path.join(os.path.dirname(_SCRATCH2), "..", "scratch"))  # round-1 common
sys.path.insert(0, "/home/hatch/workspace/trade-suite/trade-macro/src")
import common  # noqa: E402

PANEL = os.path.join(os.path.dirname(_SCRATCH2), "evidence", "panel")

IDEAS = ["rvbond_1", "regcond_1"]


def load_panel() -> dict:
    panel: dict[str, dict[str, tuple]] = {}
    for fn in sorted(os.listdir(PANEL)):
        if not fn.endswith(".csv"):
            continue
        series = {}
        with open(os.path.join(PANEL, fn)) as fh:
            for row in csv.DictReader(fh):
                try:
                    series[row["date"]] = (
                        float(row["o"]), float(row["h"]),
                        float(row["l"]), float(row["c"]),
                        float(row["v"]))
                except ValueError:
                    continue
        if series:
            panel[fn[:-4]] = series
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
    bars = panel_bars(panel, spec["symbols"])
    result = common.run_backtest(
        spec["symbols"], bars, spec["strategy"], spec["sizer"],
        spec["costs"], note="Round-2 Phase B screening: " + spec["note"])
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
        "metrics": m,
        "assumptions": result.assumptions,
        "elapsed_s": round(time.time() - t0, 1),
    }


def main() -> int:
    panel = load_panel()
    print(f"[screen2] panel keys: {sorted(panel)}", flush=True)
    results, errors = [], {}
    for modname in IDEAS:
        try:
            r = screen_one(modname, panel)
            results.append(r)
            m = r["metrics"]
            print(f"[screen2] {r['idea']}: Sharpe={m['sharpe_ratio']:.3f} "
                  f"maxDD={m['max_drawdown']:.3f} trades={m['num_trades']:.0f} "
                  f"ret={m['total_return']:.3f} ({r['elapsed_s']}s)", flush=True)
        except Exception:  # noqa: BLE001 - one idea must not kill the batch
            errors[modname] = traceback.format_exc()
            print(f"[screen2] {modname} FAILED:\n{errors[modname]}", flush=True)
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_screened": len(results),
        "not_screened": {
            "deferred_track1": ["SENTDIV-1", "ATTN-1", "EVTDRIFT-1",
                                "SENTCAP-1"],
            "unscreenable": {"BASIS-1": "no keyless dated-future history"},
            "sketches": ["VOLCAL-1", "VOLSKEW-1", "VOLDISP-1"],
        },
        "results": results,
        "errors": {k: v[-2000:] for k, v in errors.items()},
    }
    evid = os.path.join(os.path.dirname(_SCRATCH2), "evidence")
    os.makedirs(evid, exist_ok=True)
    path = os.path.join(evid, "screening2_results.json")
    with open(path, "w") as fh:
        json.dump(out, fh, indent=2, default=str)
    print(f"[screen2] n_screened={len(results)} -> {path}", flush=True)

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
