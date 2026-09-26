# Phase A — research idea batch (2026-09-26)

Generated 2026-09-26T22:49:11.489421+00:00. 10 theses through the agent desk debate protocol (rules mode, bull/bear, 2 rounds). No backtests at this stage — these are hypotheses with falsification criteria, not findings. Pre-evidence conviction prior is 0.5 (maximum ignorance); the bear is expected to win every debate until screening produces numbers.

## PAIRS-1 — Cointegrated equity pairs, z-score mean reversion
- Class: cross-sectional relative value — **LEADING CANDIDATE**
- Debate synthesis conviction: 0.2761 (base 0.5, debate 0.0522)
- Thesis: Economically linked large-cap pairs (e.g. KO/PEP, V/MA) share common risk factors, so their price spread is stationary over medium horizons. When the spread's z-score exceeds +/-2 (60-day window), trade the reversion: long the laggard, short the leader, dollar-neutral, exit at z=0 or a 10-day time stop. Universe: liquid US large caps; pairs re-screened quarterly on cointegration (ADF) + half-life < 30 days.
- Hypothesized edge: Relative mispricings from uninformed flow (index rebalances, ETF creation/redemption, tax-loss selling) revert as arbitrageurs lean in. Persists because the mispricing is small per unit and capacity-limited: too small for mega-funds to bother, too fiddly for retail.
- Data/horizon: daily OHLCV, liquid US large caps (trade-data-equities); trade-pairs engine / days to weeks per trade
- Trade frequency: ~2-6 round trips per pair per month; 10-20 pairs -> 30-80 trades/mo
- What kills it: spread half-life stretches past costs; cointegration breaks in stress and pairs never re-converge; or the screen finds no pairs passing ADF at size
- Diversification vs killed trials: DIFFERENT from both kills: trial 1 was single-asset absolute momentum; trial 2 was single-asset short-horizon time-series mean reversion. This is cross-sectional relative mean reversion — market-neutral by construction, a different risk entirely.
- Screenable with current stack: True

## XMOM-1 — Cross-sectional momentum 12-1, dollar-neutral
- Class: cross-sectional momentum
- Debate synthesis conviction: 0.2761 (base 0.5, debate 0.0522)
- Thesis: Each month, rank liquid US large caps on trailing 12-month return skipping the most recent month; go long the top decile, short the bottom decile, equal-weighted, dollar-neutral, hold one month. The classic Jegadeesh-Titman cross-sectional momentum, plainly implemented.
- Hypothesized edge: Slow information diffusion + herding + disposition effects make winners keep winning for 3-12 months. One of the most replicated premia in finance; persists across a century of data and dozens of markets.
- Data/horizon: daily OHLCV, liquid US large caps (trade-data-equities) / 1-month holding period, monthly rebalance
- Trade frequency: ~40-100 positions turning over monthly -> 500+ trades/yr
- What kills it: momentum crash (2009-style reversal wipes a year of gains); turnover costs exceed the premium at our fee tier; premium arbitraged away in large caps
- Diversification vs killed trials: DIFFERENT from both kills: cross-sectional and monthly, not single-asset daily breakout (trial 1) nor intraday mean reversion (trial 2). Note: it is still a momentum-family strategy, so it shares trial 1's exposure to trend failure — the cross-sectional construction is what differs.
- Screenable with current stack: True

## FMOM-1 — Factor momentum (momentum of factors)
- Class: factor timing
- Debate synthesis conviction: 0.2761 (base 0.5, debate 0.0522)
- Thesis: Style factors themselves trend: factors with strong trailing 12-month performance keep outperforming for several months (Ehsani-Babani 2019). Build long-short factor portfolios (value, momentum, low-vol, quality proxies) from trade-factors, rank on trailing return, hold the top half, monthly rebalance.
- Hypothesized edge: Factor returns exhibit positive autocorrelation from slow-moving institutional capital rotating between styles. Less crowded than single-stock momentum because it requires a factor engine most retail desks lack.
- Data/horizon: daily bars + trade-factors factor series / months per factor tilt
- Trade frequency: ~4-8 factor legs rebalanced monthly -> 100-200 trades/yr
- What kills it: factor series too short/noisy to rank on; factor crowding makes rotations violent; the autocorrelation was a 2010s artifact
- Diversification vs killed trials: DIFFERENT from both kills: operates on factor portfolios, not single names; monthly horizon; long-short across styles rather than directional.
- Screenable with current stack: True

## SENT-1 — News sentiment x price momentum
- Class: sentiment x price
- Debate synthesis conviction: 0.2761 (base 0.5, debate 0.0522)
- Thesis: Each day, score news sentiment per name from keyless feeds (trade-sentiment: Reddit/StockTwits/RSS). Go long names in the top sentiment quintile AND top price-momentum quintile; short the bottom of both; hold 5 trading days. The interaction matters: sentiment without price confirmation is noise, price without sentiment is crowded.
- Hypothesized edge: News diffuses slowly into prices, especially for mid-caps with thin analyst coverage; sentiment leads price by hours-to-days. The interaction filter cuts false positives from both legs.
- Data/horizon: daily bars + trade-sentiment history (keyless feeds) / days (5-day hold)
- Trade frequency: ~20-40 names x weekly turnover -> 1000+ trades/yr
- What kills it: sentiment history too shallow/noisy; timestamp misalignment creates lookahead; the interaction adds nothing over plain momentum
- Diversification vs killed trials: DIFFERENT from both kills: new information source (text), not price patterns; cross-sectional; short holding period but not intraday.
- Screenable with current stack: maybe

## TREND-VT — Vol-targeted multi-asset time-series momentum
- Class: risk premia / managed futures
- Debate synthesis conviction: 0.2761 (base 0.5, debate 0.0522)
- Thesis: Classic managed-futures at retail scale: on liquid ETFs spanning equities (SPY), bonds (TLT), gold (GLD), oil (USO), go long/flat/short each by the sign of its trailing 12-month return, sizing each leg to equal volatility contribution (vol-targeted). Monthly rebalance. Harvests the trend premium with crisis alpha from the bond/gold legs.
- Hypothesized edge: Time-series momentum is a documented cross-asset premium (Moskowitz-Ooi-Pedersen); vol targeting keeps risk constant so one asset can't dominate. Crisis alpha: trends in bonds/gold pay exactly when equities crash.
- Data/horizon: daily bars, 4-8 liquid ETFs (trade-data-equities) / months per position
- Trade frequency: ~4-8 legs x monthly rebalance -> 50-100 trades/yr
- What kills it: range-bound years with no trends (2015, 2018-style chop) bleed via whipsaw; vol-targeting lags regime changes; ETF set too small to diversify
- Diversification vs killed trials: PARTIALLY overlaps trial 1 (trend-following) but differs structurally: multi-asset, long/flat/short with vol targeting, monthly — not single-asset daily breakout. The diversification is real but imperfect; note it.
- Screenable with current stack: True

## CARRY-1 — FX/futures carry, long high-carry short low-carry
- Class: risk premia / carry
- Debate synthesis conviction: 0.2761 (base 0.5, debate 0.0522)
- Thesis: Rank G10 FX (or front-month futures where data allows) by implied carry; long the top tercile, short the bottom tercile, equal risk, monthly rebalance. Harvests the forward-rate bias: high-yield currencies don't depreciate as much as interest differentials imply.
- Hypothesized edge: One of the oldest documented premia (Bilson 1981); compensation for crash risk in high-yielders. Persists because the risk is real and periodic — carry unwinds violently, which keeps tourists out.
- Data/horizon: FX/futures series with carry measure (trade-data-futures / FX) / months
- Trade frequency: ~6-10 legs x monthly -> 100 trades/yr
- What kills it: no clean carry series in the current stack; carry unwinds (2008, 2020) can erase years; FX data costs if free feeds lack history
- Diversification vs killed trials: DIFFERENT from both kills: cross-currency risk premium, nothing like equity breakout or crypto mean reversion.
- Screenable with current stack: maybe

## TSMOM-CR — Time-series momentum on crypto majors (daily)
- Class: trend, crypto
- Debate synthesis conviction: 0.2761 (base 0.5, debate 0.0522)
- Thesis: On BTC and ETH daily bars: go long when price is above its trailing 90-day high (breakout) or when 50-day momentum is positive; flat otherwise. Long/flat only, 10% vol-targeted sizing per name. Crypto trends harder and longer than equities once moving.
- Hypothesized edge: Crypto exhibits stronger time-series momentum than equities (thin institutional participation, reflexive narratives, 24/7 momentum chasing). Long/flat avoids the worst of crypto's violent reversals.
- Data/horizon: daily bars BTC/ETH (trade-data-crypto, any venue) / weeks to months per trade
- Trade frequency: ~10-30 trades/yr per name
- What kills it: crypto trend breaks are violent enough to erase the premium; only 2 names = concentration; shares the instrument with killed trial 2 (different mechanism, but note it)
- Diversification vs killed trials: MECHANISM differs from trial 2 (daily trend vs 5-minute mean reversion) but the INSTRUMENT overlaps (BTC/ETH). Honest flag: if crypto microstructure is the problem rather than the strategy, this fails for the same reason.
- Screenable with current stack: True

## VOLPREM-1 — Systematic short volatility premium (options)
- Class: volatility premium — SKETCH
- Debate synthesis conviction: 0.2761 (base 0.5, debate 0.0522)
- Thesis: SKETCH — not screenable with current data. Harvest the variance risk premium by systematically selling 30-delta SPY strangles 30 days to expiry, delta-hedged daily, sized to a fixed vol budget. The VRP (implied > realized) is among the most persistent premia known.
- Hypothesized edge: Investors overpay for crash protection; the premium compensates short-vol sellers for left-tail risk. Persistent across decades.
- Data/horizon: REQUIRES options chains history (trade-data-options has no historical chain feed today) — data purchase needed / 30-day cycles
- Trade frequency: ~24 trades/yr
- What kills it: short-gamma blowup (a 1987/2020 week ends the strategy); data costs exceed the research budget; hedging frictions at retail size
- Diversification vs killed trials: DIFFERENT from both kills: volatility as the asset, not price direction.
- Screenable with current stack: False

## PEAD-1 — Post-earnings announcement drift
- Class: event-driven — SKETCH
- Debate synthesis conviction: 0.2761 (base 0.5, debate 0.0522)
- Thesis: SKETCH — not screenable with current data. Long top-decile earnings surprises, short bottom-decile, hold 60 trading days. PEAD is one of the oldest anomalies (Ball-Brown 1968): prices underreact to earnings news and drift for weeks.
- Hypothesized edge: Analyst and investor underreaction to fundamental news; limited attention. Persists because it requires timely earnings-surprise data most retail desks can't systematize.
- Data/horizon: REQUIRES earnings calendar + surprise data — no feed in the stack today / 60 trading days per event
- Trade frequency: ~4 earnings seasons x 20-40 names -> 100-150 trades/yr
- What kills it: no data feed = no strategy; surprise definition is fiddly; transaction costs on 60-day holds are fine but the data bill isn't
- Diversification vs killed trials: DIFFERENT from both kills: event-driven, fundamentally anchored.
- Screenable with current stack: False

## BAB-1 — Betting against beta (long low-beta, short high-beta)
- Class: cross-sectional low-risk anomaly
- Debate synthesis conviction: 0.2761 (base 0.5, debate 0.0522)
- Thesis: Each month, estimate 1-year beta vs SPY for liquid US large caps; go long the bottom-beta tercile, short the top-beta tercile, lever the long leg (or de-lever the short) to beta-neutral. Harvests the leverage-aversion premium: constrained investors overpay for high-beta lottery tickets.
- Hypothesized edge: Frazzini-Pedersen (2014): leverage-constrained investors bid up high-beta assets, depressing their forward returns. Structural, tied to institutional constraints that aren't going away.
- Data/horizon: daily bars, liquid US large caps (trade-data-equities) / monthly rebalance
- Trade frequency: ~60-100 names x monthly -> 700+ trades/yr
- What kills it: BAB crashes violently in sharp rebounds (high-beta snapbacks); beta estimates are noisy; leverage on the long leg adds real risk at retail
- Diversification vs killed trials: DIFFERENT from both kills: cross-sectional, beta-sorted, monthly — no breakout entries, no intraday mean reversion.
- Screenable with current stack: True
