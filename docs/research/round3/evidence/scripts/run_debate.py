"""Round-3 stage 2a: rules-mode debate for every idea clearing the research bar.

Output: /tmp/round3/debates_rules.json — debated idea dicts (transcript +
synthesis). The LLM challenger turns are authored separately and injected
by inject_llm_turns.py (the honest equivalent of the llm_challenger hook).
"""
import json, os, sys

BASE = os.path.expanduser("~/workspace/trade-suite")
for repo in ["trade-agents"]:
    sys.path.insert(0, os.path.join(BASE, repo, "src"))

from trade_agents.debate import debate_idea

scout_results = json.load(open("/tmp/round3/scout_results.json"))
ideas = []
for sname, v in scout_results["scouts"].items():
    for i in v.get("ideas", []):
        ideas.append((sname, i))

print(f"debating {len(ideas)} ideas (rules mode, 2 rounds)")
debated = []
for idx, (sname, idea) in enumerate(ideas):
    d = debate_idea(dict(idea), rounds=2, llm_challenger=None)
    d["_scout"] = sname
    d["_idx"] = idx
    debated.append(d)
    s = (d.get("debate") or {}).get("synthesis") or {}
    print(f"[{idx}] {sname:28s} {idea['symbol']:8s} {idea['strategy']:26s} "
          f"conviction={s.get('conviction')} (base={s.get('base_conviction')}, debate={s.get('debate_conviction')})")

json.dump(debated, open("/tmp/round3/debates_rules.json", "w"), default=str)
print("saved")
