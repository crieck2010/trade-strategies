"""Round-3 agentic screening, stage 1: run the desk's researcher scouts.

Uses the trade-agents library (ResearchAgent.research) with the sibling
strategy factory + backtest fn. Records per-scout scanned counts (the DSR
honesty denominator) and every idea clearing the research bar.
"""
import json, os, sys

BASE = os.path.expanduser("~/workspace/trade-suite")
for repo in ["trade-agents", "trade-strategies", "trade-backtest", "trade-overfit"]:
    sys.path.insert(0, os.path.join(BASE, repo, "src"))

from trade_agents.base import DictBarsProvider
from trade_agents.scouts import (
    EquityTrendScout, EquityMeanReversionScout, CryptoMomentumScout,
    FuturesTrendAnalyst, VolatilityBreakoutAnalyst, CrossAssetRegimeMonitor,
    SentimentScout,
)
from trade_agents.adapters import make_strategy_factory, make_backtest_fn

bars = json.load(open("/tmp/round3/bars.json"))
provider = DictBarsProvider({s: bs for s, bs in bars.items()})

strategy_factory = make_strategy_factory()
backtest_fn = make_backtest_fn()

result = {"scouts": {}}
SCOUTS = [EquityTrendScout(), EquityMeanReversionScout(), CryptoMomentumScout(),
          FuturesTrendAnalyst(), VolatilityBreakoutAnalyst(),
          CrossAssetRegimeMonitor()]

for scout in SCOUTS:
    if isinstance(scout, CrossAssetRegimeMonitor):
        brief = scout.research(provider)
    else:
        brief = scout.research(provider, strategy_factory, backtest_fn)
    ideas = []
    for i in brief.ideas:
        d = i.to_dict()
        ideas.append(d)
    result["scouts"][scout.name] = {
        "niche": scout.niche,
        "scanned": brief.notes.get("scanned"),
        "universe": brief.notes.get("universe"),
        "n_ideas": len(ideas),
        "regimes": brief.notes.get("regimes"),
        "ideas": ideas,
    }
    print(f"{scout.name}: scanned={brief.notes.get('scanned')} ideas={len(ideas)}"
          + (f" regimes={brief.notes.get('regimes')}" if brief.notes.get("regimes") else ""))

# sentiment scout: run to confirm/report the data limitation
ss = SentimentScout()
try:
    b = ss.research(provider, strategy_factory, backtest_fn)
    result["scouts"][ss.name] = {
        "niche": ss.niche, "scanned": b.notes.get("scanned"),
        "n_ideas": len(b.ideas),
        "error": b.notes.get("error"),
        "note": "24h-window pops only; no multi-year history exists. "
                "Not screenable for Tier-1; excluded from candidates.",
        "ideas": [i.to_dict() for i in b.ideas],
    }
    print(f"{ss.name}: scanned={b.notes.get('scanned')} ideas={len(b.ideas)} error={b.notes.get('error')}")
except Exception as e:
    result["scouts"][ss.name] = {"error": f"{type(e).__name__}: {e}",
        "note": "Not screenable for Tier-1; excluded from candidates."}
    print(f"{ss.name}: FAILED {e}")

json.dump(result, open("/tmp/round3/scout_results.json", "w"), default=str)
total_scanned = sum((v.get("scanned") or 0) for v in result["scouts"].values())
total_ideas = sum(v.get("n_ideas", 0) for v in result["scouts"].values())
print(f"TOTAL scanned={total_scanned} ideas={total_ideas}")
