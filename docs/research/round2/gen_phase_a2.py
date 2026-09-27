"""Phase A round 2 — idea generation through the agent desk.

10 theses distributed across the three tracks, each debated with
trade-agents' rules-mode bull/bear challengers for 2 rounds (exactly the
round-1 protocol: no LLM challenger, default weights, empty metrics so the
bear is expected to win pre-evidence). Output: phase-a2-ideas.json +
IDEAS-2.md. RESEARCH PROVENANCE — not a strategy module.

Usage:
    PYTHONPATH=/home/hatch/workspace/trade-suite/trade-agents/src \
        python3 docs/research/round2/gen_phase_a2.py
"""

import json
import os
import sys
from datetime import datetime, timezone

from trade_agents import debate_idea

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)))
NOW = datetime.now(timezone.utc).isoformat()

KILLED = {
    "k1": "single-asset Donchian breakout (trial DON-20/10-ATR)",
    "k2": "short-horizon crypto mean reversion (trial MR-5M, 5-minute)",
    "k3": "vol-targeted multi-asset time-series momentum (trial TREND-VT)",
    "k4": "daily crypto time-series momentum (trial TSMOM-CR)",
    "k5": "cross-sectional equity momentum (trial XMOM-1, 12-1 monthly)",
}


def spec(
    sid,
    name,
    track,
    klass,
    strategy,
    thesis,
    edge,
    data,
    horizon,
    frequency,
    kill,
    structural_difference,
    screenable,
    sentiment_contract=None,
    vol_data=None,
):
    s = {
        "id": sid,
        "name": name,
        "track": track,
        "class": klass,
        "strategy": strategy,
        "thesis": thesis,
        "edge": edge,
        "data": data,
        "horizon": horizon,
        "frequency": frequency,
        "kill": kill,
        "structural_difference": structural_difference,
        "screenable": screenable,
    }
    if sentiment_contract:
        s["sentiment_contract"] = sentiment_contract
    if vol_data:
        s["vol_data_requirements"] = vol_data
    return s


S1_CONTRACT = (
    "Phase-0 sentiment archive: every observation carries an as-of timestamp; "
    "signal at date T uses only observations with recorded_at <= T (no lookahead). "
    "Required fields per ticker-day: sentiment polarity (-1..+1), tone label, "
    "mention count, source breakdown. >=2y history for percentile/z-score baselines. "
    "Archive must be point-in-time: revisions/restatements keyed by record time, not event time."
)

SPECS = [
    spec(
        "SENTDIV-1",
        "Sentiment/price divergence (disagreement trade)",
        "track1-sentiment-x-price",
        "sentiment x price (divergence)",
        "sentdiv_1",
        "Each day, for each liquid US equity, compute divergence = z(price 20-day "
        "trend) - z(sentiment 20-day trend). When |divergence| > 2, trade the "
        "contrarian-to-price side: short names where price is euphoric but sentiment "
        "is fading, long names where price is washed out but sentiment is repairing. "
        "Hold 5-10 trading days; the bet is that price and sentiment re-couple.",
        "Divergences mark crowded positioning: price chasing without narrative support "
        "(tops) or narrative repair ahead of price (bottoms). Social sentiment and price "
        "run on different clocks, and the gap between them is the mispricing. Persists "
        "because fusing two noisy, timestamp-sensitive sources is a data-engineering "
        "moat, not a formula anyone can copy-paste.",
        "daily bars (trade-data-equities) + Phase-0 sentiment archive",
        "5-10 trading days per trade",
        "~20-40 names turning over weekly -> 500-1000 trades/yr",
        "divergence z-scores do not predict forward returns out of sample; archive "
        "timestamps prove unreliable (lookahead leaks); divergence is just a noisy "
        "proxy for short-term price reversal with no incremental signal",
        {
            "k1": "cross-sectional and contrarian, not single-asset; no breakout entries at all",
            "k2": "equities not crypto; daily not 5-minute; sentiment-conditioned event, not a price-oscillator fade",
            "k3": "no vol targeting, no momentum signal — the signal is sentiment/price disagreement",
            "k4": "equities, divergence-driven and market-neutral by construction, not directional crypto trend",
            "k5": "trades AGAINST the price trend when sentiment disagrees; CS momentum trades WITH it",
        },
        "maybe",
        sentiment_contract=S1_CONTRACT,
    ),
    spec(
        "ATTN-1",
        "Attention-shock drift",
        "track1-sentiment-x-price",
        "sentiment x price (attention event)",
        "attn_1",
        "Detect attention shocks: daily mention volume z-score > 3 vs the 60-day "
        "baseline, per ticker. On a shock day, take the direction of the contemporaneous "
        "tone (bullish tone -> long, bearish -> short); hold 3-5 trading days. The "
        "trigger is attention, the sign is tone; tone alone never triggers a trade.",
        "Attention shocks mark genuine information arrival; limited investor attention "
        "means prices underreact for days (Barber-Odean attention effects). Persists "
        "because retail flow follows chatter with a lag that institutions cannot fully "
        "arbitrage in mid-caps (short-sale frictions, mandate constraints).",
        "daily bars + Phase-0 archive: mention counts + tone per ticker-day",
        "3-5 trading days per shock",
        "shocks are rare per name; broad universe -> 300-600 trades/yr",
        "attention spikes are fully priced within the shock day (no drift); z-triggers "
        "dominated by bot spam; tone sign adds nothing over the attention flag",
        {
            "k1": "event-triggered by an external attention signal, not a price breakout",
            "k2": "equities, daily, attention-event driven — nothing like 5-minute price mean reversion",
            "k3": "no vol targeting, no trend signal; absolute attention threshold, not trailing returns",
            "k4": "cross-sectional equity attention events, not directional crypto momentum",
            "k5": "daily event trigger on absolute attention, not monthly cross-sectional price ranking",
        },
        "maybe",
        sentiment_contract=S1_CONTRACT,
    ),
    spec(
        "EVTDRIFT-1",
        "Chatter-detected event drift (social PEAD)",
        "track1-sentiment-x-price",
        "event-driven (sentiment-detected)",
        "evtdrift_1",
        "Detect corporate events from chatter itself: a mention spike plus event-keyword "
        "co-occurrence (earnings, guidance, FDA, lawsuit, upgrade/downgrade) classifies an "
        "event day per ticker. Trade the direction of the day-0 tone and hold 10-20 "
        "trading days through the post-event drift, equal-weighted across concurrent "
        "events. No earnings calendar needed — the chatter IS the calendar, and it also "
        "catches non-earnings events (lawsuits, product launches) that structured feeds miss.",
        "PEAD exists because investors underreact to news; social chatter detects the "
        "event faster than structured feeds, but the drift still plays out over weeks. "
        "Persists because building a chatter-based event classifier with clean "
        "point-in-time timestamps is engineering work most desks have not done, and the "
        "non-earnings event surface is underexploited.",
        "daily bars + Phase-0 archive: mention text or keyword tags + tone per ticker-day",
        "10-20 trading days per event",
        "~200-400 detected events/yr across a liquid universe -> 200-400 trades/yr",
        "chatter 'events' are mostly false positives; day-0 tone does not match true "
        "surprise sign; drift is absent once transaction costs are included",
        {
            "k1": "event-driven and fundamentally anchored, not a price-pattern breakout",
            "k2": "equities, multi-week event drift — opposite horizon and mechanism of 5-minute crypto MR",
            "k3": "tone-signed event drift, not vol-targeted trailing-return momentum",
            "k4": "equity event drift, not directional crypto trend",
            "k5": "event trigger with fixed 10-20d hold, not monthly momentum ranking",
        },
        "maybe",
        sentiment_contract=(
            S1_CONTRACT + " Additionally: event keyword tags per ticker-day (or raw text "
            "for the classifier); >=3y archive for event-study calibration of the drift window."
        ),
    ),
    spec(
        "SENTCAP-1",
        "Sentiment capitulation reversal",
        "track1-sentiment-x-price",
        "sentiment x price (contrarian event)",
        "sentcap_1",
        "Contrarian event trade: when a ticker's sentiment hits a 1-year extreme "
        "(below 5th or above 95th percentile) AND the price bar shows climax (volume "
        "> 2x the 60-day average, daily range > 2x ATR), fade it — buy panic, short "
        "euphoria. Hold 2-5 days; exit on tone normalization. Both conditions required; "
        "sentiment extreme without climax is just trending sentiment.",
        "Sentiment extremes plus volume climax mark forced/capitulation flow (margin "
        "calls, stop cascades, FOMO chasing) that exhausts itself; the reversal is the "
        "unwind of uninformed flow. Persists because the double trigger is rare and "
        "capacity-limited — unscalable for large funds, uneconomic to overfit.",
        "daily bars + Phase-0 archive: sentiment percentiles (>=1y history), volume/range",
        "2-5 trading days per event",
        "rare per name; broad universe -> 200-400 trades/yr",
        "extremes keep trending (sentiment leads rather than exhausts); the climax "
        "definition overfits; reversals do not survive transaction costs",
        {
            "k1": "fade-the-extreme event trade, not a breakout entry; single-name events, not trend entries",
            "k2": "daily equities with a sentiment-extreme + volume-climax trigger, not 5-minute crypto price-oscillator MR",
            "k3": "no vol targeting, no momentum — contrarian on sentiment extremes",
            "k4": "equity contrarian event, not directional crypto trend",
            "k5": "event-driven reversal on sentiment extremes, not monthly price-rank momentum",
        },
        "maybe",
        sentiment_contract=S1_CONTRACT,
    ),
    spec(
        "RVBOND-1",
        "Gold vs long-bond real-yield relative value",
        "track2-cross-asset-rv",
        "intermarket relative value",
        "rvbond_1",
        "Trade the GLD/TLT relative value anchored on real yields: regress "
        "log(GLD/TLT) on log(TIP) — TIP's price is the real-yield proxy (inverse) — "
        "and trade the residual. Long the cheap leg / short the rich leg when |z| > 1.5 "
        "on a 90-day residual window; exit at z=0 or a 30-day time stop. Dollar-neutral; "
        "the z estimate is refreshed monthly.",
        "Gold and long bonds both respond to real yields but with different elasticities "
        "and different flow clienteles (inflation hedgers vs duration buyers); the "
        "residual mean-reverts as relative flows normalize. Persists because it is "
        "cross-asset plumbing — too slow for HFT, too small for macro mandates. NOTE: "
        "this is NOT a re-proposal of the killed pairs stat-arb — no cointegrated equity "
        "pairs are mined, no ADF screening; the fair-value anchor is economic (real "
        "yields via TIP), not a statistical cointegration fit.",
        "daily bars: GLD, TLT, TIP (trade-data-equities)",
        "weeks per trade; monthly z refresh",
        "slow: 1-3 round trips/mo -> 12-36 trades/yr",
        "the residual has a unit root (relationship breaks in real-yield regime shifts); "
        "TIP is a poor real-yield proxy at the horizons that matter; bond-leg costs "
        "erase the residual",
        {
            "k1": "cross-asset spread vs a macro fundamental, not a single-asset price breakout",
            "k2": "ETF intermarket RV on real yields, not crypto, not sub-daily, not price MR",
            "k3": "mean-reverting cross-asset residual, not vol-targeted trailing momentum",
            "k4": "rates-anchored gold/bond RV, not directional crypto trend",
            "k5": "two-asset spread vs TIP-implied fair value, not cross-sectional equity ranking",
        },
        True,
    ),
    spec(
        "BASIS-1",
        "Crypto dated-future basis dislocation (delta-neutral)",
        "track2-cross-asset-rv",
        "term-structure relative value (basis)",
        "basis_1",
        "On BTC: annualized basis = (F_3m - S)/S, annualized; z-score vs its 90-day "
        "rolling mean. When |z| > 2, fade the dislocation delta-neutral — long spot / "
        "short future when basis is stretched wide, short spot / long future when "
        "compressed — unwind at z=0 or a 21-day stop. The position carries no "
        "directional crypto exposure; it is pure basis.",
        "Basis dislocations come from leveraged positioning squeezes and venue funding "
        "imbalances; the spot-futures arbitrage band snaps back as arbitrage capital "
        "arrives with a lag. Persists because arbitrage capital is limited and venue "
        "risk, margin, and fee frictions keep the band wide. NOTE: not a re-proposal of "
        "the killed FX/futures carry — carry holds the positive-carry leg unconditionally "
        "and ranks across assets; this fades temporary dislocations of a single "
        "underlying's basis, is flat most of the time, and is delta-neutral.",
        "BTC spot + 3-month dated future, daily (trade-data-crypto: Kraken futures public)",
        "days to weeks per dislocation",
        "20-40 dislocations/yr -> 20-40 trades/yr",
        "Kraken dated-future history too short/thin for a 90-day baseline; basis does not "
        "mean-revert (persistent regime shifts); margin and fee frictions eat the band",
        {
            "k1": "delta-neutral basis spread, not a directional breakout",
            "k2": "daily, delta-neutral, dislocation-fading — opposite mechanism to 5-minute directional price MR",
            "k3": "no vol targeting, no momentum; z-scored basis mean reversion",
            "k4": "delta-neutral basis trade, not directional daily crypto trend — zero beta by construction",
            "k5": "single-underlying term-structure spread, not cross-sectional equity ranking",
        },
        "maybe",
    ),
    spec(
        "REGCOND-1",
        "Copper:gold regime-conditioned cross-asset tilt",
        "track2-cross-asset-rv",
        "macro-conditioned cross-asset allocation",
        "regcond_1",
        "Use trade-macro's copper:gold regime (EXPANSION / CONTRACTION / NEUTRAL from the "
        "z-scored ratio) as a discrete allocation switch: EXPANSION -> 60% SPY / 20% "
        "copper proxy (CPER) / 20% TLT; CONTRACTION -> 20% SPY / 40% TLT / 40% GLD; "
        "NEUTRAL -> 25% each. Rebalance monthly on the regime label; fixed weights per "
        "regime — no vol targeting, no trailing-return signal.",
        "Copper:gold is the market's growth-expectations vote and leads equity risk "
        "appetite; regime-conditioned allocation harvests the business-cycle rotation "
        "without whipsawing on every price wiggle. Persists because the signal is "
        "economic (industrial vs safe-haven demand), slow-moving, and hard to overfit "
        "at monthly cadence with three discrete states.",
        "HG/GC futures or CPER/JJC vs GLD (trade-data-futures / trade-data-equities) + "
        "SPY/TLT; trade-macro regime engine",
        "regime persistence: weeks to months",
        "regime changes ~2-6/yr -> 12-24 rebalance trades/yr",
        "regime labels lag (copper:gold turns after equities do); three regimes too "
        "coarse to matter; allocation differences too small to beat buy-and-hold after costs",
        {
            "k1": "discrete macro-regime switch across asset classes, not single-asset breakout",
            "k2": "monthly multi-asset regime allocation, not sub-daily crypto MR",
            "k3": "closest cousin — but: signal is the copper:gold macro regime (fundamental, discrete), NOT per-asset trailing returns; NO vol targeting; allocation tilt, not long/flat/short per asset",
            "k4": "no crypto, no trend signal; regime-conditioned multi-asset weights",
            "k5": "three-state macro allocation, not monthly cross-sectional equity ranking",
        },
        True,
    ),
    spec(
        "VOLCAL-1",
        "Vol term-structure calendar (short 30d / long 90d straddle)",
        "track3-vol-premium",
        "volatility premium — SKETCH",
        "volcal_1",
        "SKETCH — not screenable with current data. Harvest the SPY implied-vol "
        "term-structure contango: each month, sell the 30-day ATM straddle and buy the "
        "90-day ATM straddle in a vega-neutral ratio, delta-hedging residual delta "
        "daily. The near-dated leg's event premium decays faster than the far-dated "
        "leg's; the long leg's roll-down cushions realized-vol spikes. Roll monthly.",
        "The equity IV term structure is upward-sloping on average because near-dated "
        "options embed event premium that decays with time; the calendar harvests the "
        "differential decay. Persists because the term-structure shape is driven by "
        "structural demand for near-dated protection, not by a tradeable inefficiency "
        "anyone can arb away without warehousing gamma risk.",
        "REQUIRES daily EOD options chains for SPY (all strikes, >=2 expiries); "
        ">=3y history for term-structure calibration; greeks/IV computed in-house by "
        "the trade-data-options engine on purchased raw chains",
        "30-day cycles; monthly rolls",
        "~12 rolls/yr (+ daily delta hedges)",
        "term structure inverts and stays inverted (crisis); delta-hedging frictions at "
        "retail size exceed the decay differential; data costs exceed the research budget",
        {
            "k1": "volatility term structure as the asset, not price direction",
            "k2": "options term-structure RV on SPY, not crypto price MR",
            "k3": "volatility RV, not vol-targeted price momentum",
            "k4": "SPY options calendar, not directional crypto trend",
            "k5": "single-underlying vol term structure, not cross-sectional equity momentum",
        },
        False,
        vol_data={
            "vendor_options": [
                "CBOE DataShop EOD Open-Close ad-hoc historical: $400 one-time (back to 2018) — authoritative, cheapest credible",
                "DiscountOptionData: ~$200-300 one-time (2005-present EOD, ~4000 symbols) — historical only",
                "ORATS near-EOD: $99/mo recurring + $599 one-time backfill (back to 2007, Greeks/IV/smoothed vols included, no survivorship bias)",
                "Polygon/Massive Options Developer: $79/mo (4y history); Advanced $199/mo (tick-level, real-time Greeks)",
                "ThetaData: ~$80-160/mo (tick-level historical, ~10-12y cached)",
            ],
            "required_history_depth": ">=3 years of daily EOD chains (SPY, all strikes, >=2 expiries per day)",
            "cost_estimate": "$250-600 one-time for backtest history (CBOE ad-hoc or DiscountOptionData); $79-99/mo if ongoing daily updates needed (Polygon Developer or ORATS). Greeks/IV computed in-house via trade-data-options — do not pay extra for pre-computed Greeks.",
            "decision": "Charlie's call on the spend; no purchase made.",
        },
    ),
    spec(
        "VOLSKEW-1",
        "Systematic put-spread skew harvest",
        "track3-vol-premium",
        "volatility premium — SKETCH",
        "volskew_1",
        "SKETCH — not screenable with current data. Monthly: sell the 30-delta SPY put "
        "and buy the 10-delta SPY put, 30-45 DTE, defined-risk put credit spread; hold "
        "to 7 DTE or 50% of max profit, whichever comes first; light delta hedge weekly. "
        "Harvests the downside-skew premium: crash protection is structurally overbid "
        "by hedgers, and the spread caps the left tail that kills naked short-vol.",
        "Downside puts carry a persistent premium over their realized payoff because "
        "institutions must buy protection regardless of price (mandates, not alpha). The "
        "spread structure keeps the catastrophic tail defined, which is what makes the "
        "premium harvestable at retail size. Persists as long as hedging demand is "
        "structural.",
        "REQUIRES daily EOD SPY chains (put wing, 30d/10d deltas); >=5y history to "
        "include multiple vol regimes",
        "30-45 day cycles",
        "~12 spreads/yr",
        "a sustained grind-down (not a spike) bleeds the short put faster than theta "
        "accrues; skew compresses structurally; assignment/early-exercise frictions",
        {
            "k1": "defined-risk options spread harvesting skew, not a price breakout",
            "k2": "SPY options skew, not crypto price MR",
            "k3": "volatility skew premium, not vol-targeted price momentum",
            "k4": "SPY put spreads, not directional crypto trend",
            "k5": "single-underlying skew structure, not cross-sectional equity momentum",
        },
        False,
        vol_data={
            "vendor_options": [
                "Same menu as VOLCAL-1: CBOE DataShop ad-hoc $400 one-time; DiscountOptionData ~$200-300 one-time; ORATS $99/mo + $599 backfill; Polygon Developer $79/mo; ThetaData ~$80-160/mo",
                "Put-wing only is sufficient — single-underlying, cheapest tier of any vendor works",
            ],
            "required_history_depth": ">=5 years of daily EOD SPY chains (must span multiple vol regimes: 2020, 2022, 2025)",
            "cost_estimate": "$250-600 one-time, or $79-99/mo. Same spend as VOLCAL-1 covers both sketches — one SPY chain purchase serves all single-underlying vol sketches.",
            "decision": "Charlie's call on the spend; no purchase made.",
        },
    ),
    spec(
        "VOLDISP-1",
        "Dispersion: short index straddle / long component straddles",
        "track3-vol-premium",
        "volatility premium — SKETCH",
        "voldisp_1",
        "SKETCH — not screenable with current data. Harvest the correlation risk "
        "premium: monthly, sell the SPY 30-DTE ATM straddle and buy an equal-vega "
        "basket of the top-8 component ATM straddles, delta-hedging daily. Index "
        "implied correlation persistently exceeds realized correlation because index "
        "options embed systematic-risk demand; the basket-vs-index vol differential is "
        "the edge. Re-strike monthly.",
        "Index options are structurally bid by portfolio hedgers while single-stock "
        "options are not, so implied correlation sits above realized. The premium "
        "compensates the dispersion trader for correlation-spike risk (correlations go "
        "to 1 in crashes — the known killer). Persists because the hedging demand is "
        "structural and the crash risk keeps tourists out.",
        "REQUIRES daily EOD chains for SPY + 8-10 components (>=3y); most expensive "
        "of the three sketches (multi-underlying)",
        "30-day cycles",
        "~12 re-strikes/yr (+ daily delta hedges on ~9 underlyings)",
        "correlation spike to 1 in a crash (the textbook dispersion killer); "
        "component selection turnover; hedging frictions across 9 underlyings at retail size",
        {
            "k1": "correlation RV across options, not a price breakout",
            "k2": "equity options dispersion, not crypto price MR",
            "k3": "implied-vs-realized correlation, not vol-targeted price momentum",
            "k4": "SPY vs components dispersion, not directional crypto trend",
            "k5": "index-vs-basket vol RV, not cross-sectional equity momentum",
        },
        False,
        vol_data={
            "vendor_options": [
                "ORATS near-EOD $99/mo + $599 one-time backfill — best fit: multi-symbol included, Greeks/IV/smoothed vols, no survivorship bias",
                "Polygon/Massive Options Advanced $199/mo (tick-level, real-time Greeks)",
                "CBOE DataShop ad-hoc $400 one-time per request covers any number of months back to 2018 — viable if scoped to SPY + 8 names",
                "DiscountOptionData ~$200-300 one-time (2005-present, ~4000 symbols) — cheapest multi-symbol historical",
            ],
            "required_history_depth": ">=3 years of daily EOD chains for SPY + 8-10 components",
            "cost_estimate": "$600-1200 first year (ORATS backfill + a few months recurring, or DiscountOptionData one-time + Polygon Developer for updates). Multi-underlying is the cost driver — roughly 2x the single-underlying sketches.",
            "decision": "Charlie's call on the spend; no purchase made.",
        },
    ),
]


def build_idea(s):
    return {
        "agent": "research_lead",
        "symbol": "BASKET",
        "strategy": s["strategy"],
        "params": {"class": s["class"], "screenable": s["screenable"], "track": s["track"]},
        "direction": "long",
        "metrics": {},
        "score": 0.0,
        "conviction": 0.5,
        "thesis": s["thesis"],
    }


def main():
    records = []
    for s in SPECS:
        idea = build_idea(s)
        debated = debate_idea(idea, rounds=2)
        synth = debated["debate"]["synthesis"]
        debated["conviction"] = synth["conviction"]
        records.append({"spec": s, "idea": debated, "as_of": NOW})

    payload = {"generated_at": NOW, "n_ideas": len(records), "records": records,
               "protocol": {"rounds": 2, "mode": "rules", "challengers": ["bull_challenger", "bear_challenger"],
                            "weights": "default (no ledger)", "metrics": "empty (pre-evidence)",
                            "killed_classes_avoided": KILLED}}
    with open(os.path.join(OUT, "phase-a2-ideas.json"), "w") as f:
        json.dump(payload, f, indent=2)

    lines = [
        "# Phase A round 2 — research idea batch (2026-09-26)",
        "",
        f"Generated {NOW}. 10 theses across the three tracks, through the agent desk "
        "debate protocol (rules mode, bull/bear, 2 rounds) — the same protocol as round 1. "
        "No backtests at this stage: hypotheses with falsification criteria, not findings. "
        "Pre-evidence conviction prior is 0.5 (maximum ignorance); the bear is expected to "
        "win every debate until screening produces numbers.",
        "",
        "Steer: pointed AWAY from the five killed classes (single-asset Donchian breakout; "
        "short-horizon crypto mean reversion; vol-targeted multi-asset time-series momentum; "
        "daily crypto time-series momentum; cross-sectional equity momentum) and away from "
        "round 1's screened-but-rejected (pairs/cointegration stat-arb, factor momentum, "
        "FX/futures carry, betting-against-beta). Each thesis argues explicitly why it is "
        "structurally different from each killed class.",
        "",
    ]
    for rec in records:
        s = rec["spec"]
        synth = rec["idea"]["debate"]["synthesis"]
        lines += [
            f"## {s['id']} — {s['name']}",
            f"- Track: {s['track']} | Class: {s['class']}",
            f"- Debate synthesis conviction: {synth['conviction']} (base {synth['base_conviction']}, "
            f"debate {synth['debate_conviction']}, net pressure {synth['net_pressure']}) — "
            f"{'BEAR won' if synth['conviction'] < 0.5 else 'BULL won'} pre-evidence",
            f"- Thesis: {s['thesis']}",
            f"- Hypothesized edge: {s['edge']}",
            f"- Data/horizon: {s['data']} / {s['horizon']}",
            f"- Trade frequency: {s['frequency']}",
            f"- What kills it: {s['kill']}",
            "- Structural difference vs the five killed classes:",
        ]
        for k in ("k1", "k2", "k3", "k4", "k5"):
            lines.append(f"  - vs ({k[1:]}) {KILLED[k]}: {s['structural_difference'][k]}")
        if "sentiment_contract" in s:
            lines.append(f"- Sentiment data contract: {s['sentiment_contract']}")
        if "vol_data_requirements" in s:
            v = s["vol_data_requirements"]
            lines.append(f"- Vol data requirements: {v['required_history_depth']}")
            lines.append(f"  - Vendor options: {'; '.join(v['vendor_options'])}")
            lines.append(f"  - Cost estimate: {v['cost_estimate']}")
            lines.append(f"  - {v['decision']}")
        lines.append(f"- Screenable with current stack: {s['screenable']}")
        lines.append("")
    lines += [
        "## Debate standard (applies to all 10)",
        "",
        "Rules-mode challengers with empty metrics: the bull can only cite the thesis and "
        "generic risk acknowledgment; the bear cites Sharpe 0.00 below the 1.5 bar, zero "
        "trades, and the overfit archetype. The bear wins every debate pre-evidence — "
        "correct behavior. Full transcripts live in phase-a2-ideas.json.",
        "",
        "## Hard stop",
        "",
        "Idea generation only. No screening, no validation, no backtests, no data "
        "purchases, no code changes outside research docs. Round-1 files untouched.",
        "",
    ]
    with open(os.path.join(OUT, "IDEAS-2.md"), "w") as f:
        f.write("\n".join(lines))

    print(f"wrote {len(records)} ideas")
    for rec in records:
        synth = rec["idea"]["debate"]["synthesis"]
        print(f"  {rec['spec']['id']}: conviction {synth['conviction']} "
              f"({'BEAR' if synth['conviction'] < 0.5 else 'BULL'} won)")


if __name__ == "__main__":
    main()
