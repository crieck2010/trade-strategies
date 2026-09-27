"""Round-3 stage 3a: exhaustive grid capture.

Replays the five backtesting scouts' grids EXACTLY (same classes, same
strategy_factory/backtest_fn as the desk) but records metrics for EVERY
combination, not just the research-bar winners. This is the honest DSR
denominator: n_trials = completed grid Sharpes.

Also captures full equity curves for the 15 retained ideas (matched by
scout/symbol/strategy/params against scout_results.json) plus aligned
buy-and-hold benchmark returns per idea.

Outputs:
  /tmp/round3/grid_all.json     - 70 rows: scout/symbol/strategy/params +
                                  sharpe/maxDD/num_trades/score/status
  /tmp/round3/idea_returns.json - 15 ideas: daily strategy returns,
                                  benchmark returns, metadata
"""
import json, os, sys

BASE = os.path.expanduser("~/workspace/trade-suite")
for repo in ["trade-agents", "trade-strategies", "trade-backtest"]:
    sys.path.insert(0, os.path.join(BASE, repo, "src"))

from trade_agents.base import DictBarsProvider
from trade_agents.scouts import (
    EquityTrendScout, EquityMeanReversionScout, CryptoMomentumScout,
    FuturesTrendAnalyst, VolatilityBreakoutAnalyst,
)
from trade_agents.adapters import make_strategy_factory, make_backtest_fn
from trade_agents.research import backtest_candidate, score_result

bars = json.load(open("/tmp/round3/bars.json"))
provider = DictBarsProvider({s: bs for s, bs in bars.items()})
strategy_factory = make_strategy_factory()
backtest_fn = make_backtest_fn()

# retained ideas -> keys for equity-curve capture
scout_results = json.load(open("/tmp/round3/scout_results.json"))
retained = {}
for sname, v in scout_results["scouts"].items():
    for i in v.get("ideas", []):
        key = (sname, i["symbol"], i["strategy"],
               json.dumps(i["params"], sort_keys=True))
        retained[key] = i

SCOUTS = [EquityTrendScout(), EquityMeanReversionScout(), CryptoMomentumScout(),
          FuturesTrendAnalyst(), VolatilityBreakoutAnalyst()]

grid = []
idea_returns = {}
n_fail = 0
for scout in SCOUTS:
    for symbol in scout.universe:
        all_bars = provider.get_bars(symbol)
        if len(all_bars) < scout.min_bars:
            continue
        for strategy_name in scout.strategies:
            for params in scout.param_grid.get(strategy_name, [{}]):
                key = (scout.name, symbol, strategy_name,
                       json.dumps(params, sort_keys=True))
                row = {"scout": scout.name, "symbol": symbol,
                       "strategy": strategy_name, "params": params}
                try:
                    metrics = backtest_candidate(
                        symbol, strategy_name, params, all_bars,
                        strategy_factory, backtest_fn)
                except Exception as exc:
                    n_fail += 1
                    row.update({"status": "error", "error": f"{type(exc).__name__}: {exc}",
                                "sharpe": None, "max_drawdown": None,
                                "num_trades": None, "score": None})
                    grid.append(row)
                    continue
                score = score_result(metrics)
                row.update({"status": "ok",
                            "sharpe": metrics.get("sharpe_ratio"),
                            "max_drawdown": metrics.get("max_drawdown"),
                            "num_trades": metrics.get("num_trades"),
                            "score": score,
                            "cleared_bar": score >= scout.min_score})
                grid.append(row)

                if key in retained:
                    # full result for the equity curve (same backtest_fn)
                    strat = strategy_factory(strategy_name, [symbol], params)
                    result = backtest_fn(strat, all_bars)
                    eq = [float(p.equity) for p in result.equity_curve]
                    srets = [eq[i] / eq[i - 1] - 1.0
                             for i in range(1, len(eq)) if eq[i - 1] != 0]
                    closes = [float(b["close"] if isinstance(b, dict) else b.close)
                              for b in all_bars]
                    # align benchmark to the equity curve length
                    n = len(srets)
                    brets = [closes[i + 1] / closes[i] - 1.0
                             for i in range(len(closes) - 1)][:n]
                    # equity curve may be shorter/longer than bars-1; trim to common
                    m = min(len(srets), len(brets))
                    idea_returns[f"{scout.name}|{symbol}|{strategy_name}|{json.dumps(params, sort_keys=True)}"] = {
                        "scout": scout.name, "symbol": symbol,
                        "strategy": strategy_name, "params": params,
                        "strategy_returns": srets[:m],
                        "benchmark_returns": brets[:m],
                        "n_bars": len(all_bars),
                        "num_trades": metrics.get("num_trades"),
                        "in_sample_sharpe": metrics.get("sharpe_ratio"),
                        "in_sample_maxdd": metrics.get("max_drawdown"),
                    }
                    print(f"  captured returns: {symbol} {strategy_name} "
                          f"n={m} trades={metrics.get('num_trades')}", flush=True)

print(f"\ngrid rows: {len(grid)}, failed: {n_fail}, "
      f"retained captured: {len(idea_returns)}/15")
json.dump(grid, open("/tmp/round3/grid_all.json", "w"))
json.dump(idea_returns, open("/tmp/round3/idea_returns.json", "w"))
print("saved grid_all.json, idea_returns.json")
