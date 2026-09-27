"""Round-3 stage 2b: inject the LLM challenger turns (authored separately as
data) into the rules-mode debate transcripts, then re-synthesize.

This is the honest equivalent of the llm_challenger hook: the turns are
my authored judgment in the debate._turn shape, recorded with
agent_id llm_bull_challenger / llm_bear_challenger.
"""
import json, os, sys

BASE = os.path.expanduser("~/workspace/trade-suite")
sys.path.insert(0, os.path.join(BASE, "trade-agents", "src"))

from trade_agents.debate import synthesize

debated = json.load(open("/tmp/round3/debates_rules.json"))
turns = {}
for f in ["llm_turns_trend.json", "llm_turns_mr.json", "llm_turns_vol.json"]:
    turns.update(json.load(open(f"/tmp/round3/{f}")))

def make_turn(agent_id, stance, points, round_no):
    pts = []
    for p in points:
        pts.append({
            "text": p["text"],
            "evidence": dict(p.get("evidence", {})),
            "confidence": max(0.0, min(1.0, float(p["confidence"]))),
            "sentiment": 1 if p["sentiment"] > 0 else -1,
        })
    conf = round(sum(p["confidence"] for p in pts) / len(pts), 4) if pts else 0.0
    return {"round": round_no, "agent_id": agent_id, "stance": stance,
            "points": pts, "confidence": conf}

for d in debated:
    idx = str(d["_idx"])
    t = turns[idx]
    transcript = d["debate"]["transcript"]
    # rounds 3 and 4 are the LLM challenger rounds (rules did 1-2)
    for r, (bp, ep) in enumerate(zip(t["bull"], t["bear"]), start=3):
        transcript.append(make_turn("llm_bull_challenger", "bull", bp, r))
        transcript.append(make_turn("llm_bear_challenger", "bear", ep, r))
    idea_dict = {k: v for k, v in d.items() if not k.startswith("_")}
    s = synthesize(idea_dict, transcript)
    d["debate"]["transcript"] = transcript
    d["debate"]["synthesis"] = s
    d["debate"]["config"] = {"rounds": 4, "mode": "rules+llm",
                             "llm_rounds": [3, 4], "rules_rounds": [1, 2]}
    print(f"[{d['_idx']}] {d['_scout']:28s} {d['symbol']:8s} {d['strategy']:26s} "
          f"conviction={s['conviction']} (base={s['base_conviction']}, debate={s['debate_conviction']}, net={s['net_pressure']})")

json.dump(debated, open("/tmp/round3/debates_final.json", "w"), default=str)
print("saved debates_final.json")
