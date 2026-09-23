"""Parameter sweep: grid-search SMA fast/slow, rank by Sharpe.

The pattern agents use to tune any strategy: enumerate parameters from
describe_strategies(), run each combination through run_backtest(), rank.

Requires trade-backtest installed (pip install trade-backtest).
Run: python examples/parameter_sweep.py
"""

import itertools
import random
from datetime import datetime, timedelta, timezone

from trade_strategies import SMACrossover, get_strategy, run_backtest


def make_bars(n=252, seed=7):
    random.seed(seed)
    closes, price = [], 100.0
    for i in range(n):
        drift = 0.12 if (i // 63) % 2 == 0 else -0.10
        price *= 1 + drift / 100 + random.uniform(-1.4, 1.4) / 100
        closes.append(price)
    t0 = datetime(2025, 1, 2, tzinfo=timezone.utc)
    return [
        {"symbol": "DEMO", "timestamp": t0 + timedelta(days=i),
         "open": c, "high": c * 1.005, "low": c * 0.995, "close": c,
         "volume": 1_000_000}
        for i, c in enumerate(closes)
    ]


def main():
    bars = make_bars()
    cls = get_strategy("sma_crossover")  # agents pick by name from the registry
    rows = []
    for fast, slow in itertools.product([10, 20, 30], [50, 100, 150]):
        if fast >= slow:
            continue
        result = run_backtest(cls(["DEMO"], fast=fast, slow=slow), bars)
        rows.append({
            "fast": fast, "slow": slow,
            "sharpe": result.metrics["sharpe_ratio"],
            "return": result.metrics["total_return"],
            "max_dd": result.metrics["max_drawdown"],
            "trades": result.num_trades,
        })
    rows.sort(key=lambda r: r["sharpe"], reverse=True)
    print(f"{'fast':>4} {'slow':>4} {'sharpe':>7} {'return':>7} {'max_dd':>7} {'trades':>6}")
    for r in rows:
        print(f"{r['fast']:>4} {r['slow']:>4} {r['sharpe']:>7.3f} "
              f"{r['return']:>+7.3f} {r['max_dd']:>7.3f} {r['trades']:>6}")
    best = rows[0]
    print(f"\nBest: fast={best['fast']}, slow={best['slow']} "
          f"(Sharpe {best['sharpe']:.3f})")


if __name__ == "__main__":
    main()
