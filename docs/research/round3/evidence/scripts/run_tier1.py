"""Round-3 stage 3b: Tier-1 screening for the 15 retained ideas.

Methodology (mirrors trial-4 / REGCOND-1 precedent):
  - Walk-forward geometry: train=520 bars, test=130 bars, step=130 bars,
    5-bar embargo, rolling (train_start advances). Fixed params: no fitting,
    so folds measure OOS regime stability.
  - median_oos_sharpe = median of per-fold test-window Sharpes.
  - maxDD / Sortino / DSR computed on CONCATENATED OOS test-window returns.
  - DSR trial set = all 69 completed Round-3 grid Sharpes (70 screened, 1
    engine failure on CL=F macd_trend) -> n_trials=69.
  - Benchmark = buy-and-hold of the same symbol over the identical OOS
    windows. Benchmark is gross of costs (2 trades lifetime); the strategy
    leg is net of the backtest engine's default cost model (5 bps slippage
    each way + 1 bp half-spread + $0.005/share), so no extra haircut is
    applied -- double-charging would be dishonest.
  - Tier-1 gates expressed through trade_overfit.gates.Gate:
      median OOS Sharpe > 0.3; maxDD > -0.25; DSR > 0.8;
      excess vs benchmark net > 0.0; Sortino >= 0.75.
  - Verdict PASS requires all five.

Output: /tmp/round3/tier1_results.json
"""
import json, os, statistics, sys

BASE = os.path.expanduser("~/workspace/trade-suite")
sys.path.insert(0, os.path.join(BASE, "trade-overfit", "src"))

from trade_overfit.gates import Gate, evaluate_gates
from trade_overfit.dsr import dsr_from_returns
from trade_overfit.metrics import (
    sharpe_ratio, performance_summary, annualized_return,
)

TRAIN_BARS, TEST_BARS, STEP_BARS, EMBARGO_BARS = 520, 130, 130, 5

TIER1_GATES = [
    Gate("oos_sharpe", "median_oos_sharpe", "gt", 0.3,
         "Tier-1: median walk-forward OOS Sharpe > 0.3."),
    Gate("max_drawdown", "max_drawdown", "gt", -0.25,
         "Tier-1: OOS max drawdown shallower than -25%."),
    Gate("deflated_sharpe", "dsr", "gt", 0.8,
         "Tier-1: DSR > 0.8 at full round multiplicity."),
    Gate("beats_benchmark_net", "excess_return_vs_benchmark_after_costs",
         "gt", 0.0, "Tier-1: beats buy-and-hold benchmark net of costs."),
    Gate("sortino", "sortino", "gte", 0.75,
         "Tier-1: OOS Sortino >= 0.75."),
]

grid = json.load(open("/tmp/round3/grid_all.json"))
trial_sharpes = [r["sharpe"] for r in grid
                 if r["status"] == "ok" and r["sharpe"] is not None]
print(f"DSR trial set: n={len(trial_sharpes)} "
      f"(70 screened, {70 - len(trial_sharpes)} engine failure)")

idea_returns = json.load(open("/tmp/round3/idea_returns.json"))
debates = json.load(open("/tmp/round3/debates_final.json"))
debate_by_key = {}
for d in debates:
    k = (f"{d['_scout']}|{d['symbol']}|{d['strategy']}|"
         f"{json.dumps(d['params'], sort_keys=True)}")
    debate_by_key[k] = d["debate"]["synthesis"]


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


results = []
for key, ir in idea_returns.items():
    rets = ir["strategy_returns"]
    brets = ir["benchmark_returns"]
    fl = folds(len(rets))
    fold_rows = []
    oos_idx = []
    for ts, te, ss, se in fl:
        test = rets[ss:se]
        fold_rows.append({
            "train_start": ts, "train_end": te,
            "test_start": ss, "test_end": se,
            "oos_sharpe": sharpe_ratio(test),
        })
        oos_idx.extend(range(ss, se))
    orets = [rets[i] for i in oos_idx]
    obrets = [brets[i] for i in oos_idx]

    med_oos = statistics.median(
        [r["oos_sharpe"] for r in fold_rows if r["oos_sharpe"] is not None])
    summ = performance_summary(orets)
    dsr = dsr_from_returns(orets, trial_sharpes)
    strat_ann = annualized_return(orets)
    bench_ann = annualized_return(obrets)
    excess = (strat_ann - bench_ann
              if strat_ann is not None and bench_ann is not None else None)

    evidence = {
        "median_oos_sharpe": med_oos,
        "max_drawdown": summ["max_drawdown"],
        "dsr": dsr["dsr"],
        "excess_return_vs_benchmark_after_costs": excess,
        "sortino": summ["sortino"],
    }
    gate_results = evaluate_gates(evidence, TIER1_GATES)
    verdict = "PASS" if all(g["passed"] for g in gate_results) else "FAIL"

    results.append({
        "key": key, "scout": ir["scout"], "symbol": ir["symbol"],
        "strategy": ir["strategy"], "params": ir["params"],
        "n_oos_bars": len(orets), "n_folds": len(fl),
        "in_sample_sharpe": ir["in_sample_sharpe"],
        "num_trades": ir["num_trades"],
        "oos_annualized_return": strat_ann,
        "benchmark_oos_annualized_return": bench_ann,
        "dsr_detail": {k: dsr[k] for k in
                       ("sharpe_hat", "n_obs", "n_trials",
                        "expected_sharpe_under_null", "dsr",
                        "skewness", "excess_kurtosis")},
        "fold_oos_sharpes": [r["oos_sharpe"] for r in fold_rows],
        "evidence": evidence,
        "gates": gate_results,
        "n_gates_passed": sum(1 for g in gate_results if g["passed"]),
        "verdict": verdict,
        "debate_conviction": debate_by_key[key]["conviction"],
    })
    ev = evidence
    print(f"{ir['symbol']:8s} {ir['strategy']:26s} "
          f"oos_med={ev['median_oos_sharpe']:+.3f} "
          f"dd={ev['max_drawdown']:+.3f} dsr={ev['dsr']:.3f} "
          f"exc={ev['excess_return_vs_benchmark_after_costs']:+.4f} "
          f"sort={ev['sortino']:.3f} -> {verdict} "
          f"({sum(1 for g in gate_results if g['passed'])}/5)")

results.sort(key=lambda r: (-(r["verdict"] == "PASS"),
                            -(r["evidence"]["dsr"] or -9)))
json.dump({"tier1_gates": [
    {"name": g.name, "metric": g.metric, "op": g.op,
     "threshold": g.threshold, "description": g.description}
    for g in TIER1_GATES],
    "walk_forward_geometry": {
        "train_bars": TRAIN_BARS, "test_bars": TEST_BARS,
        "step_bars": STEP_BARS, "embargo_bars": EMBARGO_BARS,
        "anchored": False, "note": "trial-4 geometry; fixed params, no fitting",
    },
    "cost_note": "strategy leg net of trade-backtest CostModel.defaults() "
                 "(5 bps slippage each way + 1 bp half-spread + $0.005/share) "
                 "charged inside the backtest; no additional haircut. "
                 "Benchmark (buy-and-hold) gross of costs (~2 trades).",
    "n_trials_dsr": len(trial_sharpes),
    "results": results,
    "n_pass": sum(1 for r in results if r["verdict"] == "PASS"),
}, open("/tmp/round3/tier1_results.json", "w"), default=str)
print("saved tier1_results.json")
