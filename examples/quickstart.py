"""Quickstart: enumerate the library, run one backtest, print the report.

Requires trade-backtest installed (pip install trade-backtest).
Run: python examples/quickstart.py
"""

from datetime import datetime, timedelta, timezone

from trade_strategies import (
    SMACrossover,
    describe_strategies,
    list_families,
    run_backtest,
)

# 1. The agents' menu: every strategy with its parameters.
print(f"Families: {list_families()}")
for info in describe_strategies():
    print(f"  {info['name']:28s} [{info['family']}] warmup={info['warmup_bars']}")

# 2. Synthetic daily bars with a trend + noise regime.
import random

random.seed(42)
closes, price = [], 100.0
for i in range(252):
    drift = 0.15 if i < 126 else -0.12
    price *= 1 + drift / 100 + random.uniform(-1.2, 1.2) / 100
    closes.append(price)

t0 = datetime(2025, 1, 2, tzinfo=timezone.utc)
bars = [
    {"symbol": "DEMO", "timestamp": t0 + timedelta(days=i),
     "open": c, "high": c * 1.005, "low": c * 0.995, "close": c,
     "volume": 1_000_000}
    for i, c in enumerate(closes)
]

# 3. One-call backtest through the lazy trade-backtest bridge.
result = run_backtest(SMACrossover(["DEMO"], fast=20, slow=50), bars)

print(f"\nTrades: {result.num_trades}")
for key in ("total_return", "cagr", "sharpe_ratio", "sortino_ratio",
            "max_drawdown", "calmar_ratio", "win_rate", "profit_factor"):
    print(f"  {key:15s} {result.metrics[key]:+.4f}")
