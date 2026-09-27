# Phase A round 2 — research idea batch (2026-09-26)

Generated 2026-09-27T02:43:40.358237+00:00. 10 theses across the three tracks, through the agent desk debate protocol (rules mode, bull/bear, 2 rounds) — the same protocol as round 1. No backtests at this stage: hypotheses with falsification criteria, not findings. Pre-evidence conviction prior is 0.5 (maximum ignorance); the bear is expected to win every debate until screening produces numbers.

Steer: pointed AWAY from the five killed classes (single-asset Donchian breakout; short-horizon crypto mean reversion; vol-targeted multi-asset time-series momentum; daily crypto time-series momentum; cross-sectional equity momentum) and away from round 1's screened-but-rejected (pairs/cointegration stat-arb, factor momentum, FX/futures carry, betting-against-beta). Each thesis argues explicitly why it is structurally different from each killed class.

## SENTDIV-1 — Sentiment/price divergence (disagreement trade)
- Track: track1-sentiment-x-price | Class: sentiment x price (divergence)
- Debate synthesis conviction: 0.2761 (base 0.5, debate 0.0522, net pressure -2.9) — BEAR won pre-evidence
- Thesis: Each day, for each liquid US equity, compute divergence = z(price 20-day trend) - z(sentiment 20-day trend). When |divergence| > 2, trade the contrarian-to-price side: short names where price is euphoric but sentiment is fading, long names where price is washed out but sentiment is repairing. Hold 5-10 trading days; the bet is that price and sentiment re-couple.
- Hypothesized edge: Divergences mark crowded positioning: price chasing without narrative support (tops) or narrative repair ahead of price (bottoms). Social sentiment and price run on different clocks, and the gap between them is the mispricing. Persists because fusing two noisy, timestamp-sensitive sources is a data-engineering moat, not a formula anyone can copy-paste.
- Data/horizon: daily bars (trade-data-equities) + Phase-0 sentiment archive / 5-10 trading days per trade
- Trade frequency: ~20-40 names turning over weekly -> 500-1000 trades/yr
- What kills it: divergence z-scores do not predict forward returns out of sample; archive timestamps prove unreliable (lookahead leaks); divergence is just a noisy proxy for short-term price reversal with no incremental signal
- Structural difference vs the five killed classes:
  - vs (1) single-asset Donchian breakout (trial DON-20/10-ATR): cross-sectional and contrarian, not single-asset; no breakout entries at all
  - vs (2) short-horizon crypto mean reversion (trial MR-5M, 5-minute): equities not crypto; daily not 5-minute; sentiment-conditioned event, not a price-oscillator fade
  - vs (3) vol-targeted multi-asset time-series momentum (trial TREND-VT): no vol targeting, no momentum signal — the signal is sentiment/price disagreement
  - vs (4) daily crypto time-series momentum (trial TSMOM-CR): equities, divergence-driven and market-neutral by construction, not directional crypto trend
  - vs (5) cross-sectional equity momentum (trial XMOM-1, 12-1 monthly): trades AGAINST the price trend when sentiment disagrees; CS momentum trades WITH it
- Sentiment data contract: Phase-0 sentiment archive: every observation carries an as-of timestamp; signal at date T uses only observations with recorded_at <= T (no lookahead). Required fields per ticker-day: sentiment polarity (-1..+1), tone label, mention count, source breakdown. >=2y history for percentile/z-score baselines. Archive must be point-in-time: revisions/restatements keyed by record time, not event time.
- Screenable with current stack: maybe

## ATTN-1 — Attention-shock drift
- Track: track1-sentiment-x-price | Class: sentiment x price (attention event)
- Debate synthesis conviction: 0.2761 (base 0.5, debate 0.0522, net pressure -2.9) — BEAR won pre-evidence
- Thesis: Detect attention shocks: daily mention volume z-score > 3 vs the 60-day baseline, per ticker. On a shock day, take the direction of the contemporaneous tone (bullish tone -> long, bearish -> short); hold 3-5 trading days. The trigger is attention, the sign is tone; tone alone never triggers a trade.
- Hypothesized edge: Attention shocks mark genuine information arrival; limited investor attention means prices underreact for days (Barber-Odean attention effects). Persists because retail flow follows chatter with a lag that institutions cannot fully arbitrage in mid-caps (short-sale frictions, mandate constraints).
- Data/horizon: daily bars + Phase-0 archive: mention counts + tone per ticker-day / 3-5 trading days per shock
- Trade frequency: shocks are rare per name; broad universe -> 300-600 trades/yr
- What kills it: attention spikes are fully priced within the shock day (no drift); z-triggers dominated by bot spam; tone sign adds nothing over the attention flag
- Structural difference vs the five killed classes:
  - vs (1) single-asset Donchian breakout (trial DON-20/10-ATR): event-triggered by an external attention signal, not a price breakout
  - vs (2) short-horizon crypto mean reversion (trial MR-5M, 5-minute): equities, daily, attention-event driven — nothing like 5-minute price mean reversion
  - vs (3) vol-targeted multi-asset time-series momentum (trial TREND-VT): no vol targeting, no trend signal; absolute attention threshold, not trailing returns
  - vs (4) daily crypto time-series momentum (trial TSMOM-CR): cross-sectional equity attention events, not directional crypto momentum
  - vs (5) cross-sectional equity momentum (trial XMOM-1, 12-1 monthly): daily event trigger on absolute attention, not monthly cross-sectional price ranking
- Sentiment data contract: Phase-0 sentiment archive: every observation carries an as-of timestamp; signal at date T uses only observations with recorded_at <= T (no lookahead). Required fields per ticker-day: sentiment polarity (-1..+1), tone label, mention count, source breakdown. >=2y history for percentile/z-score baselines. Archive must be point-in-time: revisions/restatements keyed by record time, not event time.
- Screenable with current stack: maybe

## EVTDRIFT-1 — Chatter-detected event drift (social PEAD)
- Track: track1-sentiment-x-price | Class: event-driven (sentiment-detected)
- Debate synthesis conviction: 0.2761 (base 0.5, debate 0.0522, net pressure -2.9) — BEAR won pre-evidence
- Thesis: Detect corporate events from chatter itself: a mention spike plus event-keyword co-occurrence (earnings, guidance, FDA, lawsuit, upgrade/downgrade) classifies an event day per ticker. Trade the direction of the day-0 tone and hold 10-20 trading days through the post-event drift, equal-weighted across concurrent events. No earnings calendar needed — the chatter IS the calendar, and it also catches non-earnings events (lawsuits, product launches) that structured feeds miss.
- Hypothesized edge: PEAD exists because investors underreact to news; social chatter detects the event faster than structured feeds, but the drift still plays out over weeks. Persists because building a chatter-based event classifier with clean point-in-time timestamps is engineering work most desks have not done, and the non-earnings event surface is underexploited.
- Data/horizon: daily bars + Phase-0 archive: mention text or keyword tags + tone per ticker-day / 10-20 trading days per event
- Trade frequency: ~200-400 detected events/yr across a liquid universe -> 200-400 trades/yr
- What kills it: chatter 'events' are mostly false positives; day-0 tone does not match true surprise sign; drift is absent once transaction costs are included
- Structural difference vs the five killed classes:
  - vs (1) single-asset Donchian breakout (trial DON-20/10-ATR): event-driven and fundamentally anchored, not a price-pattern breakout
  - vs (2) short-horizon crypto mean reversion (trial MR-5M, 5-minute): equities, multi-week event drift — opposite horizon and mechanism of 5-minute crypto MR
  - vs (3) vol-targeted multi-asset time-series momentum (trial TREND-VT): tone-signed event drift, not vol-targeted trailing-return momentum
  - vs (4) daily crypto time-series momentum (trial TSMOM-CR): equity event drift, not directional crypto trend
  - vs (5) cross-sectional equity momentum (trial XMOM-1, 12-1 monthly): event trigger with fixed 10-20d hold, not monthly momentum ranking
- Sentiment data contract: Phase-0 sentiment archive: every observation carries an as-of timestamp; signal at date T uses only observations with recorded_at <= T (no lookahead). Required fields per ticker-day: sentiment polarity (-1..+1), tone label, mention count, source breakdown. >=2y history for percentile/z-score baselines. Archive must be point-in-time: revisions/restatements keyed by record time, not event time. Additionally: event keyword tags per ticker-day (or raw text for the classifier); >=3y archive for event-study calibration of the drift window.
- Screenable with current stack: maybe

## SENTCAP-1 — Sentiment capitulation reversal
- Track: track1-sentiment-x-price | Class: sentiment x price (contrarian event)
- Debate synthesis conviction: 0.2761 (base 0.5, debate 0.0522, net pressure -2.9) — BEAR won pre-evidence
- Thesis: Contrarian event trade: when a ticker's sentiment hits a 1-year extreme (below 5th or above 95th percentile) AND the price bar shows climax (volume > 2x the 60-day average, daily range > 2x ATR), fade it — buy panic, short euphoria. Hold 2-5 days; exit on tone normalization. Both conditions required; sentiment extreme without climax is just trending sentiment.
- Hypothesized edge: Sentiment extremes plus volume climax mark forced/capitulation flow (margin calls, stop cascades, FOMO chasing) that exhausts itself; the reversal is the unwind of uninformed flow. Persists because the double trigger is rare and capacity-limited — unscalable for large funds, uneconomic to overfit.
- Data/horizon: daily bars + Phase-0 archive: sentiment percentiles (>=1y history), volume/range / 2-5 trading days per event
- Trade frequency: rare per name; broad universe -> 200-400 trades/yr
- What kills it: extremes keep trending (sentiment leads rather than exhausts); the climax definition overfits; reversals do not survive transaction costs
- Structural difference vs the five killed classes:
  - vs (1) single-asset Donchian breakout (trial DON-20/10-ATR): fade-the-extreme event trade, not a breakout entry; single-name events, not trend entries
  - vs (2) short-horizon crypto mean reversion (trial MR-5M, 5-minute): daily equities with a sentiment-extreme + volume-climax trigger, not 5-minute crypto price-oscillator MR
  - vs (3) vol-targeted multi-asset time-series momentum (trial TREND-VT): no vol targeting, no momentum — contrarian on sentiment extremes
  - vs (4) daily crypto time-series momentum (trial TSMOM-CR): equity contrarian event, not directional crypto trend
  - vs (5) cross-sectional equity momentum (trial XMOM-1, 12-1 monthly): event-driven reversal on sentiment extremes, not monthly price-rank momentum
- Sentiment data contract: Phase-0 sentiment archive: every observation carries an as-of timestamp; signal at date T uses only observations with recorded_at <= T (no lookahead). Required fields per ticker-day: sentiment polarity (-1..+1), tone label, mention count, source breakdown. >=2y history for percentile/z-score baselines. Archive must be point-in-time: revisions/restatements keyed by record time, not event time.
- Screenable with current stack: maybe

## RVBOND-1 — Gold vs long-bond real-yield relative value
- Track: track2-cross-asset-rv | Class: intermarket relative value
- Debate synthesis conviction: 0.2761 (base 0.5, debate 0.0522, net pressure -2.9) — BEAR won pre-evidence
- Thesis: Trade the GLD/TLT relative value anchored on real yields: regress log(GLD/TLT) on log(TIP) — TIP's price is the real-yield proxy (inverse) — and trade the residual. Long the cheap leg / short the rich leg when |z| > 1.5 on a 90-day residual window; exit at z=0 or a 30-day time stop. Dollar-neutral; the z estimate is refreshed monthly.
- Hypothesized edge: Gold and long bonds both respond to real yields but with different elasticities and different flow clienteles (inflation hedgers vs duration buyers); the residual mean-reverts as relative flows normalize. Persists because it is cross-asset plumbing — too slow for HFT, too small for macro mandates. NOTE: this is NOT a re-proposal of the killed pairs stat-arb — no cointegrated equity pairs are mined, no ADF screening; the fair-value anchor is economic (real yields via TIP), not a statistical cointegration fit.
- Data/horizon: daily bars: GLD, TLT, TIP (trade-data-equities) / weeks per trade; monthly z refresh
- Trade frequency: slow: 1-3 round trips/mo -> 12-36 trades/yr
- What kills it: the residual has a unit root (relationship breaks in real-yield regime shifts); TIP is a poor real-yield proxy at the horizons that matter; bond-leg costs erase the residual
- Structural difference vs the five killed classes:
  - vs (1) single-asset Donchian breakout (trial DON-20/10-ATR): cross-asset spread vs a macro fundamental, not a single-asset price breakout
  - vs (2) short-horizon crypto mean reversion (trial MR-5M, 5-minute): ETF intermarket RV on real yields, not crypto, not sub-daily, not price MR
  - vs (3) vol-targeted multi-asset time-series momentum (trial TREND-VT): mean-reverting cross-asset residual, not vol-targeted trailing momentum
  - vs (4) daily crypto time-series momentum (trial TSMOM-CR): rates-anchored gold/bond RV, not directional crypto trend
  - vs (5) cross-sectional equity momentum (trial XMOM-1, 12-1 monthly): two-asset spread vs TIP-implied fair value, not cross-sectional equity ranking
- Screenable with current stack: True

## BASIS-1 — Crypto dated-future basis dislocation (delta-neutral)
- Track: track2-cross-asset-rv | Class: term-structure relative value (basis)
- Debate synthesis conviction: 0.2761 (base 0.5, debate 0.0522, net pressure -2.9) — BEAR won pre-evidence
- Thesis: On BTC: annualized basis = (F_3m - S)/S, annualized; z-score vs its 90-day rolling mean. When |z| > 2, fade the dislocation delta-neutral — long spot / short future when basis is stretched wide, short spot / long future when compressed — unwind at z=0 or a 21-day stop. The position carries no directional crypto exposure; it is pure basis.
- Hypothesized edge: Basis dislocations come from leveraged positioning squeezes and venue funding imbalances; the spot-futures arbitrage band snaps back as arbitrage capital arrives with a lag. Persists because arbitrage capital is limited and venue risk, margin, and fee frictions keep the band wide. NOTE: not a re-proposal of the killed FX/futures carry — carry holds the positive-carry leg unconditionally and ranks across assets; this fades temporary dislocations of a single underlying's basis, is flat most of the time, and is delta-neutral.
- Data/horizon: BTC spot + 3-month dated future, daily (trade-data-crypto: Kraken futures public) / days to weeks per dislocation
- Trade frequency: 20-40 dislocations/yr -> 20-40 trades/yr
- What kills it: Kraken dated-future history too short/thin for a 90-day baseline; basis does not mean-revert (persistent regime shifts); margin and fee frictions eat the band
- Structural difference vs the five killed classes:
  - vs (1) single-asset Donchian breakout (trial DON-20/10-ATR): delta-neutral basis spread, not a directional breakout
  - vs (2) short-horizon crypto mean reversion (trial MR-5M, 5-minute): daily, delta-neutral, dislocation-fading — opposite mechanism to 5-minute directional price MR
  - vs (3) vol-targeted multi-asset time-series momentum (trial TREND-VT): no vol targeting, no momentum; z-scored basis mean reversion
  - vs (4) daily crypto time-series momentum (trial TSMOM-CR): delta-neutral basis trade, not directional daily crypto trend — zero beta by construction
  - vs (5) cross-sectional equity momentum (trial XMOM-1, 12-1 monthly): single-underlying term-structure spread, not cross-sectional equity ranking
- Screenable with current stack: maybe

## REGCOND-1 — Copper:gold regime-conditioned cross-asset tilt
- Track: track2-cross-asset-rv | Class: macro-conditioned cross-asset allocation
- Debate synthesis conviction: 0.2761 (base 0.5, debate 0.0522, net pressure -2.9) — BEAR won pre-evidence
- Thesis: Use trade-macro's copper:gold regime (EXPANSION / CONTRACTION / NEUTRAL from the z-scored ratio) as a discrete allocation switch: EXPANSION -> 60% SPY / 20% copper proxy (CPER) / 20% TLT; CONTRACTION -> 20% SPY / 40% TLT / 40% GLD; NEUTRAL -> 25% each. Rebalance monthly on the regime label; fixed weights per regime — no vol targeting, no trailing-return signal.
- Hypothesized edge: Copper:gold is the market's growth-expectations vote and leads equity risk appetite; regime-conditioned allocation harvests the business-cycle rotation without whipsawing on every price wiggle. Persists because the signal is economic (industrial vs safe-haven demand), slow-moving, and hard to overfit at monthly cadence with three discrete states.
- Data/horizon: HG/GC futures or CPER/JJC vs GLD (trade-data-futures / trade-data-equities) + SPY/TLT; trade-macro regime engine / regime persistence: weeks to months
- Trade frequency: regime changes ~2-6/yr -> 12-24 rebalance trades/yr
- What kills it: regime labels lag (copper:gold turns after equities do); three regimes too coarse to matter; allocation differences too small to beat buy-and-hold after costs
- Structural difference vs the five killed classes:
  - vs (1) single-asset Donchian breakout (trial DON-20/10-ATR): discrete macro-regime switch across asset classes, not single-asset breakout
  - vs (2) short-horizon crypto mean reversion (trial MR-5M, 5-minute): monthly multi-asset regime allocation, not sub-daily crypto MR
  - vs (3) vol-targeted multi-asset time-series momentum (trial TREND-VT): closest cousin — but: signal is the copper:gold macro regime (fundamental, discrete), NOT per-asset trailing returns; NO vol targeting; allocation tilt, not long/flat/short per asset
  - vs (4) daily crypto time-series momentum (trial TSMOM-CR): no crypto, no trend signal; regime-conditioned multi-asset weights
  - vs (5) cross-sectional equity momentum (trial XMOM-1, 12-1 monthly): three-state macro allocation, not monthly cross-sectional equity ranking
- Screenable with current stack: True

## VOLCAL-1 — Vol term-structure calendar (short 30d / long 90d straddle)
- Track: track3-vol-premium | Class: volatility premium — SKETCH
- Debate synthesis conviction: 0.2761 (base 0.5, debate 0.0522, net pressure -2.9) — BEAR won pre-evidence
- Thesis: SKETCH — not screenable with current data. Harvest the SPY implied-vol term-structure contango: each month, sell the 30-day ATM straddle and buy the 90-day ATM straddle in a vega-neutral ratio, delta-hedging residual delta daily. The near-dated leg's event premium decays faster than the far-dated leg's; the long leg's roll-down cushions realized-vol spikes. Roll monthly.
- Hypothesized edge: The equity IV term structure is upward-sloping on average because near-dated options embed event premium that decays with time; the calendar harvests the differential decay. Persists because the term-structure shape is driven by structural demand for near-dated protection, not by a tradeable inefficiency anyone can arb away without warehousing gamma risk.
- Data/horizon: REQUIRES daily EOD options chains for SPY (all strikes, >=2 expiries); >=3y history for term-structure calibration; greeks/IV computed in-house by the trade-data-options engine on purchased raw chains / 30-day cycles; monthly rolls
- Trade frequency: ~12 rolls/yr (+ daily delta hedges)
- What kills it: term structure inverts and stays inverted (crisis); delta-hedging frictions at retail size exceed the decay differential; data costs exceed the research budget
- Structural difference vs the five killed classes:
  - vs (1) single-asset Donchian breakout (trial DON-20/10-ATR): volatility term structure as the asset, not price direction
  - vs (2) short-horizon crypto mean reversion (trial MR-5M, 5-minute): options term-structure RV on SPY, not crypto price MR
  - vs (3) vol-targeted multi-asset time-series momentum (trial TREND-VT): volatility RV, not vol-targeted price momentum
  - vs (4) daily crypto time-series momentum (trial TSMOM-CR): SPY options calendar, not directional crypto trend
  - vs (5) cross-sectional equity momentum (trial XMOM-1, 12-1 monthly): single-underlying vol term structure, not cross-sectional equity momentum
- Vol data requirements: >=3 years of daily EOD chains (SPY, all strikes, >=2 expiries per day)
  - Vendor options: CBOE DataShop EOD Open-Close ad-hoc historical: $400 one-time (back to 2018) — authoritative, cheapest credible; DiscountOptionData: ~$200-300 one-time (2005-present EOD, ~4000 symbols) — historical only; ORATS near-EOD: $99/mo recurring + $599 one-time backfill (back to 2007, Greeks/IV/smoothed vols included, no survivorship bias); Polygon/Massive Options Developer: $79/mo (4y history); Advanced $199/mo (tick-level, real-time Greeks); ThetaData: ~$80-160/mo (tick-level historical, ~10-12y cached)
  - Cost estimate: $250-600 one-time for backtest history (CBOE ad-hoc or DiscountOptionData); $79-99/mo if ongoing daily updates needed (Polygon Developer or ORATS). Greeks/IV computed in-house via trade-data-options — do not pay extra for pre-computed Greeks.
  - Charlie's call on the spend; no purchase made.
- Screenable with current stack: False

## VOLSKEW-1 — Systematic put-spread skew harvest
- Track: track3-vol-premium | Class: volatility premium — SKETCH
- Debate synthesis conviction: 0.2761 (base 0.5, debate 0.0522, net pressure -2.9) — BEAR won pre-evidence
- Thesis: SKETCH — not screenable with current data. Monthly: sell the 30-delta SPY put and buy the 10-delta SPY put, 30-45 DTE, defined-risk put credit spread; hold to 7 DTE or 50% of max profit, whichever comes first; light delta hedge weekly. Harvests the downside-skew premium: crash protection is structurally overbid by hedgers, and the spread caps the left tail that kills naked short-vol.
- Hypothesized edge: Downside puts carry a persistent premium over their realized payoff because institutions must buy protection regardless of price (mandates, not alpha). The spread structure keeps the catastrophic tail defined, which is what makes the premium harvestable at retail size. Persists as long as hedging demand is structural.
- Data/horizon: REQUIRES daily EOD SPY chains (put wing, 30d/10d deltas); >=5y history to include multiple vol regimes / 30-45 day cycles
- Trade frequency: ~12 spreads/yr
- What kills it: a sustained grind-down (not a spike) bleeds the short put faster than theta accrues; skew compresses structurally; assignment/early-exercise frictions
- Structural difference vs the five killed classes:
  - vs (1) single-asset Donchian breakout (trial DON-20/10-ATR): defined-risk options spread harvesting skew, not a price breakout
  - vs (2) short-horizon crypto mean reversion (trial MR-5M, 5-minute): SPY options skew, not crypto price MR
  - vs (3) vol-targeted multi-asset time-series momentum (trial TREND-VT): volatility skew premium, not vol-targeted price momentum
  - vs (4) daily crypto time-series momentum (trial TSMOM-CR): SPY put spreads, not directional crypto trend
  - vs (5) cross-sectional equity momentum (trial XMOM-1, 12-1 monthly): single-underlying skew structure, not cross-sectional equity momentum
- Vol data requirements: >=5 years of daily EOD SPY chains (must span multiple vol regimes: 2020, 2022, 2025)
  - Vendor options: Same menu as VOLCAL-1: CBOE DataShop ad-hoc $400 one-time; DiscountOptionData ~$200-300 one-time; ORATS $99/mo + $599 backfill; Polygon Developer $79/mo; ThetaData ~$80-160/mo; Put-wing only is sufficient — single-underlying, cheapest tier of any vendor works
  - Cost estimate: $250-600 one-time, or $79-99/mo. Same spend as VOLCAL-1 covers both sketches — one SPY chain purchase serves all single-underlying vol sketches.
  - Charlie's call on the spend; no purchase made.
- Screenable with current stack: False

## VOLDISP-1 — Dispersion: short index straddle / long component straddles
- Track: track3-vol-premium | Class: volatility premium — SKETCH
- Debate synthesis conviction: 0.2761 (base 0.5, debate 0.0522, net pressure -2.9) — BEAR won pre-evidence
- Thesis: SKETCH — not screenable with current data. Harvest the correlation risk premium: monthly, sell the SPY 30-DTE ATM straddle and buy an equal-vega basket of the top-8 component ATM straddles, delta-hedging daily. Index implied correlation persistently exceeds realized correlation because index options embed systematic-risk demand; the basket-vs-index vol differential is the edge. Re-strike monthly.
- Hypothesized edge: Index options are structurally bid by portfolio hedgers while single-stock options are not, so implied correlation sits above realized. The premium compensates the dispersion trader for correlation-spike risk (correlations go to 1 in crashes — the known killer). Persists because the hedging demand is structural and the crash risk keeps tourists out.
- Data/horizon: REQUIRES daily EOD chains for SPY + 8-10 components (>=3y); most expensive of the three sketches (multi-underlying) / 30-day cycles
- Trade frequency: ~12 re-strikes/yr (+ daily delta hedges on ~9 underlyings)
- What kills it: correlation spike to 1 in a crash (the textbook dispersion killer); component selection turnover; hedging frictions across 9 underlyings at retail size
- Structural difference vs the five killed classes:
  - vs (1) single-asset Donchian breakout (trial DON-20/10-ATR): correlation RV across options, not a price breakout
  - vs (2) short-horizon crypto mean reversion (trial MR-5M, 5-minute): equity options dispersion, not crypto price MR
  - vs (3) vol-targeted multi-asset time-series momentum (trial TREND-VT): implied-vs-realized correlation, not vol-targeted price momentum
  - vs (4) daily crypto time-series momentum (trial TSMOM-CR): SPY vs components dispersion, not directional crypto trend
  - vs (5) cross-sectional equity momentum (trial XMOM-1, 12-1 monthly): index-vs-basket vol RV, not cross-sectional equity momentum
- Vol data requirements: >=3 years of daily EOD chains for SPY + 8-10 components
  - Vendor options: ORATS near-EOD $99/mo + $599 one-time backfill — best fit: multi-symbol included, Greeks/IV/smoothed vols, no survivorship bias; Polygon/Massive Options Advanced $199/mo (tick-level, real-time Greeks); CBOE DataShop ad-hoc $400 one-time per request covers any number of months back to 2018 — viable if scoped to SPY + 8 names; DiscountOptionData ~$200-300 one-time (2005-present, ~4000 symbols) — cheapest multi-symbol historical
  - Cost estimate: $600-1200 first year (ORATS backfill + a few months recurring, or DiscountOptionData one-time + Polygon Developer for updates). Multi-underlying is the cost driver — roughly 2x the single-underlying sketches.
  - Charlie's call on the spend; no purchase made.
- Screenable with current stack: False

## Debate standard (applies to all 10)

Rules-mode challengers with empty metrics: the bull can only cite the thesis and generic risk acknowledgment; the bear cites Sharpe 0.00 below the 1.5 bar, zero trades, and the overfit archetype. The bear wins every debate pre-evidence — correct behavior. Full transcripts live in phase-a2-ideas.json.

## Hard stop

Idea generation only. No screening, no validation, no backtests, no data purchases, no code changes outside research docs. Round-1 files untouched.
