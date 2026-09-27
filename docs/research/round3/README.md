# Round 3 — Agentic Strategy Screening

**Date:** 2026-09-27
**Authorization:** Charlie, 2026-09-27 (research/backtest/paper only; no live trades, no purchases, no lifecycle transitions).
**Goal of the round:** find strategy #2 — a second Tier-1 validated strategy to join REGCOND-1 in the allocator candidate pool.
**Result: 0 of 15 ideas passed Tier-1. No strategy #2 this round.**

This is a screening report, not a trial. Nothing was pre-registered and nothing enters paper. The evidence below is complete enough to re-run or audit every number.

---

## 1. How the round ran (four stages)

1. **Scout sweep** — the `trade-agents` desk's researcher scouts ran their fixed parameter grids through the sibling strategy factory (`trade-strategies`) and backtest adapter (`trade-backtest`), via Charlie's data-engine adapters (`trade-data-equities` → yfinance, `trade-data-futures` → yfinance, `trade-data-crypto` → yfinance). Code is his; the bars are public market data pulled through his adapters.
2. **Debate** — every idea clearing the research bar got scripted bull/bear turns (rules mode, 2 rounds) **plus** separately authored LLM challenger turns (2 more rounds), recorded in the debate transcript shape with agent ids `llm_bull_challenger` / `llm_bear_challenger`. The challenger rounds specifically attacked: cousinship with invalidated strategies, secular/sample contamination, thin trade counts, the DSR arithmetic at full-round multiplicity, transaction-cost sensitivity, and benchmark honesty.
3. **Exhaustive grid capture** — re-ran all 70 grid combinations recording metrics for *every* combo (the desk's `research()` only keeps winners). This is the honest DSR denominator.
4. **Tier-1 screening** — walk-forward OOS evaluation (trial-4 geometry) with the five official Tier-1 gates expressed through `trade_overfit.gates.Gate`, DSR at full-round multiplicity, aligned buy-and-hold benchmarks, costs already inside the backtest.

## 2. Screening coverage (honest n_screened)

| Scout | Grid | Combinations screened | Ideas retained |
|---|---|---:|---:|
| `equity_trend_scout` | 6 symbols × 5 param sets (sma×2, donchian×2, supertrend×1) | 30 | 5 |
| `equity_mean_reversion_scout` | 5 symbols × 3 (rsi2, bollinger, zscore) | 15 | 5 |
| `crypto_momentum_scout` | 3 symbols × 3 (tsmom×2, donchian×1) | 9 | 0 |
| `futures_trend_analyst` | 4 symbols × 2 (sma, macd) | 8 | 0 |
| `volatility_breakout_analyst` | 4 symbols × 2 (squeeze, keltner) | 8 | 0 |
| `cross_asset_regime_monitor` | descriptive only (no strategy trials) | 0 | 0 |
| `sentiment_scout` | 7 symbols, 24h-window pops | 7 | 0 |
| **Total** | | **77** | **15** |

**n_screened = 77** (70 strategy trials + 7 sentiment symbols scanned). Of the 70 strategy trials, 69 completed; one engine failure (see §6). **DSR uses n_trials = 69** — every completed trial Sharpe in the round, including the winners' siblings and the bar's rejects.

Regime-monitor snapshot (descriptive, not a trial): SPY volatile, QQQ volatile, IWM volatile, TLT ranging, GLD volatile, BTC-USD ranging.

## 3. The 15 retained ideas (in-sample scout metrics — not evidence)

| # | Scout | Symbol | Strategy | Params | Sharpe | MaxDD | Trades | Score |
|---|---|---|---|---|---|---:|---:|---:|---:|
| 0 | trend | SPY | donchian_breakout | entry 20 / exit 10 | 0.81 | 4.1% | 52 | 0.75 |
| 1 | trend | SPY | sma_crossover | 10 / 30 | 0.73 | 6.6% | 43 | 0.63 |
| 2 | trend | SPY | sma_crossover | 20 / 50 | 0.72 | 10.7% | 25 | 0.56 |
| 3 | trend | AAPL | donchian_breakout | entry 20 / exit 10 | 0.63 | 4.4% | 44 | 0.56 |
| 4 | trend | MSFT | supertrend | atr 10 / mult 3.0 | 0.58 | 7.3% | 42 | 0.47 |
| 5 | mr | JPM | bollinger_reversion | 20 / 2.0σ | 0.53 | 3.9% | 55 | 0.47 |
| 6 | mr | SPY | rsi2_mean_reversion | rsi 2 / os 10 | 0.49 | 3.6% | 92 | 0.43 |
| 7 | mr | MSFT | bollinger_reversion | 20 / 2.0σ | 0.51 | 5.4% | 49 | 0.43 |
| 8 | mr | SPY | bollinger_reversion | 20 / 2.0σ | 0.50 | 7.9% | 56 | 0.38 |
| 9 | mr | SPY | zscore_reversion | 20 / 2.0σ | 0.50 | 8.3% | 59 | 0.37 |
| 10 | vol | QQQ | bollinger_squeeze_breakout | 20 / lookback 60 | 0.60 | 8.1% | 14 | 0.48 |
| 11 | vol | AAPL | keltner_breakout | ema 20 / atr 10 / 2.0 | 0.53 | 4.5% | 48 | 0.46 |
| 12 | vol | NVDA | keltner_breakout | ema 20 / atr 10 / 2.0 | 0.48 | 4.1% | 48 | 0.42 |
| 13 | vol | SPY | keltner_breakout | ema 20 / atr 10 / 2.0 | 0.45 | 4.1% | 50 | 0.39 |
| 14 | vol | AAPL | bollinger_squeeze_breakout | 20 / lookback 60 | 0.47 | 6.1% | 15 | 0.38 |

All ideas are long-only, single-symbol, daily bars, fixed-quantity sizing (100 shares on $100k). Research bar: `score = sharpe × trade_factor − 1.5 × maxDD ≥ 0.30`, top 5 per scout.

**These in-sample numbers are ranking metrics, not Tier-1 evidence.** The next three sections are the evidence.

## 4. Debate (scripted + LLM challenger)

Each idea received 4 debate rounds: rounds 1–2 scripted rules-mode turns, rounds 3–4 LLM challenger turns authored for this round and injected into the transcript in the debate engine's turn shape (the honest equivalent of the `llm_challenger` hook — both are preserved, not substituted). Full transcripts: `evidence/debates.json`; challenger turn source: `evidence/llm_challenger_turns.json`.

Final debate convictions (base → post-debate):

| # | Idea | Base | Post-debate | Net pressure |
|---|---|---:|---:|---:|
| 0 | SPY donchian | 0.62 | 0.78 | +2.65 |
| 1 | SPY sma(10,30) | 0.56 | 0.69 | +1.50 |
| 2 | SPY sma(20,50) | 0.53 | 0.41 | −0.90 |
| 3 | AAPL donchian | 0.53 | 0.73 | +2.60 |
| 4 | MSFT supertrend | 0.49 | 0.71 | +2.75 |
| 5 | JPM bollinger | 0.48 | 0.71 | +2.85 |
| 6 | SPY rsi2 | 0.47 | 0.69 | +2.45 |
| 7 | MSFT bollinger | 0.46 | 0.71 | +3.30 |
| 8 | SPY bollinger | 0.44 | 0.69 | +2.60 |
| 9 | SPY zscore | 0.44 | 0.68 | +2.55 |
| 10 | QQQ squeeze | 0.49 | 0.55 | +0.45 |
| 11 | AAPL keltner | 0.48 | 0.71 | +2.80 |
| 12 | NVDA keltner | 0.46 | 0.69 | +2.50 |
| 13 | SPY keltner | 0.45 | 0.69 | +2.60 |
| 14 | AAPL squeeze | 0.44 | 0.54 | +0.60 |

The scripted rounds were uniformly bullish (debate conviction ≈ 0.97 for most ideas) — the rules engine rewards in-sample metrics. The LLM challenger rounds pulled conviction down where it was deserved: idea 2 (0.61→0.41, duplicate of idea 1 on thinner evidence), idea 10 (0.68→0.55) and idea 14 (0.66→0.54) on thin trade counts. Key challenger objections that survived into the synthesis:

- **Cousinship:** ideas 0/3 are the same donchian 20/10 system as invalidated DON-20/10-ATR; ideas 1/2 sit beside invalidated TREND-VT; ideas 5–9 form one bollinger/zscore MR phenomenon found four times, not four ideas.
- **Secular contamination:** AAPL (~10x), MSFT (~8x), NVDA (AI melt-up) flatter every long-biased system; the edge must be measured against buy-and-hold, not zero.
- **Thin evidence:** the squeeze ideas rest on 14–15 trades; the desk's `trade_factor` ramp stops penalizing after 10 trades — too generous.
- **DSR arithmetic:** at n=69 the null's expected best Sharpe is ≈ 0.43; in-sample 0.45–0.81 starts underwater — only OOS persistence can clear it.
- **Crash-dependence:** the rsi2 idea's 92 trades cluster in stress episodes; its edge must survive ex-2020.

## 5. Exhaustive grid honesty check

Replaying all 70 combinations with full metric capture (replay fidelity vs the scout sweep: max |ΔSharpe| = 0):

- **69 completed, 1 engine failure:** `futures_trend_analyst / CL=F / macd_trend` crashed with `ValueError: slippage must be non-negative, got -0.7` — the April-2020 negative WTI print breaks the cost model's slippage math. The scout sweep silently skipped it (`except Exception: continue`). Flagged as a robustness bug for `trade-backtest`, not a strategy verdict.
- **The research bar did its job on the dangerous tail:** the round's two highest in-sample Sharpes were correctly *rejected* — BTC-USD donchian (Sharpe 0.98, maxDD **54.9%**) and NQ=F sma_crossover (Sharpe 0.86, maxDD **43.4%**). High Sharpe with catastrophic drawdown is exactly what the `−1.5 × maxDD` penalty exists to filter. The bar kept 15 ideas; none of them carry that tail profile.
- Full grid: `evidence/grid_all.json` (70 rows: every Sharpe, drawdown, trade count, score, clear/reject).

## 6. Tier-1 screening

**Geometry** (trial-4 precedent): walk-forward on the strategy return series, train 520 bars / test 130 bars / step 130 bars / 5-bar embargo, rolling. Fixed parameters — no fitting — so folds measure OOS regime stability. ~18 folds, ~2,340 OOS bars per idea.

**Gates** (all five required, via `trade_overfit.gates.Gate`):

| Gate | Metric | Bar |
|---|---|---|
| oos_sharpe | median walk-forward OOS Sharpe | > 0.3 |
| max_drawdown | OOS max drawdown (concatenated test windows) | > −0.25 |
| deflated_sharpe | DSR of concatenated OOS returns, n_trials = 69 | > 0.8 |
| beats_benchmark_net | ann(strategy OOS) − ann(buy-and-hold OOS), same windows | > 0.0 |
| sortino | OOS Sortino (concatenated test windows) | ≥ 0.75 |

**Costs:** the backtest engine's default cost model (5 bps slippage each way + 1 bp half-spread + $0.005/share commission) is charged *inside* every backtest, so strategy returns are already net. No additional haircut was applied — double-charging would be dishonest. Benchmark (buy-and-hold) is gross of costs; at ~2 lifetime trades the difference is ~10 bps total, immaterial to the gate.

**Benchmark choice:** buy-and-hold of the same symbol over the identical OOS windows — what the investor gets for free. This matches Charlie's stated goal (beat the S&P 500 with lower risk) and the two-tier framework's "beat benchmark net."

## 7. Tier-1 results: 0 of 15 pass

| # | Idea | Med OOS Sharpe | OOS maxDD | DSR (n=69) | Excess vs BH | Sortino | Gates | Verdict |
|---|---|---:|---:|---:|---:|---:|---|---|
| 0 | SPY donchian | +0.63 | −4.1% | 1.000 | −0.124 | 1.22 | 4/5 | FAIL |
| 1 | SPY sma(10,30) | +0.59 | −6.6% | 1.000 | −0.122 | 1.11 | 4/5 | FAIL |
| 2 | SPY sma(20,50) | +1.42 | −10.7% | 1.000 | −0.122 | 1.06 | 4/5 | FAIL |
| 3 | AAPL donchian | +0.50 | −4.4% | 1.000 | −0.273 | 0.98 | 4/5 | FAIL |
| 4 | MSFT supertrend | +0.87 | −7.3% | 1.000 | −0.228 | 0.98 | 4/5 | FAIL |
| 5 | JPM bollinger | +0.68 | −3.9% | 0.994 | −0.177 | 0.77 | 4/5 | FAIL |
| 6 | SPY rsi2 | +0.42 | −3.6% | 0.998 | −0.142 | 0.79 | 4/5 | FAIL |
| 7 | MSFT bollinger | +0.98 | −5.4% | 0.998 | −0.241 | 0.80 | 4/5 | FAIL |
| 11 | AAPL keltner | +1.00 | −4.5% | 0.999 | −0.278 | 0.82 | 4/5 | FAIL |
| 10 | QQQ squeeze | +0.57 | −8.1% | 1.000 | −0.188 | 0.93 | 4/5 | FAIL |
| 12 | NVDA keltner | +0.62 | −4.1% | 0.996 | −0.567 | 0.80 | 4/5 | FAIL |
| 14 | AAPL squeeze | +1.01 | −6.1% | 0.996 | −0.276 | 0.73 | 3/5 | FAIL |
| 13 | SPY keltner | +0.31 | −4.1% | 0.886 | −0.140 | 0.64 | 3/5 | FAIL |
| 9 | SPY zscore | +0.86 | −8.3% | 0.836 | −0.136 | 0.73 | 3/5 | FAIL |
| 8 | SPY bollinger | +0.91 | −7.9% | 0.834 | −0.134 | 0.70 | 3/5 | FAIL |

Twelve ideas fail on exactly one gate — `beats_benchmark_net`. Three more fail it plus Sortino (ideas 8, 9, 13, 14 — Sortino 0.64–0.73).

**What the numbers mean.** The OOS edges are statistically *real*: DSR ≈ 1.0 at n_trials=69 (the null's expected best Sharpe is only 0.43), median OOS Sharpes 0.31–1.42, OOS drawdowns 3.6–10.7%. These are genuine low-volatility timing systems. But they earn **+1–3%/yr OOS** while their benchmarks compounded at **+15–58%/yr** (SPY 15.3%, QQQ 21.2%, MSFT 25.9%, AAPL 29.0%, NVDA 57.6%, JPM 18.7% — the 2017–2026 window is a historic bull market). A trend system that sits in cash through half a 15%/yr melt-up can have a Sharpe of 1.0 and still trail buy-and-hold by 12 points a year. **The benchmark gate worked exactly as designed:** Charlie's goal is to beat the S&P 500 with lower risk, and none of these do.

This is not a failure of the screening — it is the screening succeeding. The DSR gate confirmed the phenomena are real; the benchmark gate confirmed they don't clear his bar. In a flat or bear market these same systems might beat buy-and-hold; that is a regime-conditional hypothesis for a future round, not a Tier-1 pass today.

Full per-idea evidence (fold Sharpes, DSR detail, gate evaluations): `evidence/tier1_results.json`.

## 8. Ranked Tier-1 candidates

**The ranked list is empty.** No idea cleared all five gates, so no strategy enters the allocator candidate pool and no lifecycle transition is proposed.

Ordered watchlist (by gates passed, then DSR) — for a future round, not for promotion:

1. SPY sma(20,50) — 4/5, DSR 1.000, med OOS Sharpe 1.42 (strongest OOS persistence in the round; fails only the benchmark gate; note: duplicate phenomenon of idea 1).
2. AAPL keltner — 4/5, DSR 0.999, med OOS Sharpe 1.00.
3. MSFT bollinger — 4/5, DSR 0.998, med OOS Sharpe 0.98.
4. SPY donchian / SPY sma(10,30) / MSFT supertrend / QQQ squeeze / SPY rsi2 / AAPL donchian / NVDA keltner / JPM bollinger — 4/5, DSR 0.994–1.000.
5. AAPL squeeze / SPY zscore / SPY bollinger / SPY keltner — 3/5 (benchmark + Sortino).

## 9. Cousinship with prior discarded strategies

- **Ideas 0, 3 (donchian 20/10)** — direct cousins of invalidated **DON-20/10-ATR** (trial 1: OOS Sharpe 0.87, maxDD −40.2%). Same system, same parameters. The in-sample edge here does not distinguish them; only the Tier-1 screen could have, and it did not (benchmark gate).
- **Ideas 1, 2 (sma_crossover)** — beside invalidated **TREND-VT** (trial 3: OOS Sharpe 0.09). Trend-on-equities keeps dying at the benchmark gate.
- **Ideas 11–13 (keltner)** — ATR-channel breakout, same trend-breakout family as DON-20/10-ATR by mechanism.
- **Ideas 5–9 (bollinger/zscore/rsi2 MR)** — not direct cousins of invalidated **MR-5M** (5-minute crypto vs daily equity — different timeframe, asset, cost structure), but the daily-equity MR cluster is one phenomenon found four times (ideas 5/7/8/9 share identical 2σ logic).
- **Ideas 10, 14 (squeeze)** — structurally novel to the lane (no invalidated predecessor), but thinnest evidence (14–15 trades).

## 10. Mandate compliance

No live mandate file has been adopted; the module defaults apply: allowed asset classes **["equity", "etf"]**, portfolio leverage cap 1.5, long-only ideas unlevered here (100 shares ≤ $60k notional on $100k equity).

- All 15 retained ideas are equity/ETF → compliant with the default allowed-instrument policy.
- The **crypto** (spot) and **futures** scouts screened instruments **outside** the default allowed classes. Zero ideas were retained from those scouts, so there is no candidate-level violation — but the screening itself touched out-of-policy instruments. Fail-closed: any future candidate from those niches requires a mandate amendment *before* screening, not after.
- Concentration note (Tier-2 relevance): single-name ideas would breach the 10% single-name weight at the portfolio level; that is an allocator problem, not a screening violation.

## 11. Blocked / limited tracks

- **Options-chain ideas: blocked on data spend.** Implied-vol / skew / dispersion strategies were not screened — Charlie's data-spend decision is still open, and the round bought nothing.
- **Sentiment: structural limitation.** The scout scanned 7 symbols over a 24h window and produced zero ideas above the conviction bar. The archive backfill (~169k StockTwits messages, reaching ~2026-05-29 as of 2026-09-27) is still far short of the two years needed for backtestable sentiment history. No sentiment idea can be honestly screened until the archive matures. The weekday 4:30 PM ET accumulation cron (first run Mon 2026-09-28) stands.
- **Sizing:** fixed-quantity (100 shares) is notional-naive; any trial must use volatility-normalized sizing.
- **Single-symbol, long-only, daily:** no portfolio effects, no shorts, no intraday — Tier-2 questions are untouched.
- **Benchmark regime:** the 2017–2026 OOS window is one of history's strongest bull markets; the benchmark gate is at its most punishing here. A future round could test the watchlist in defensive regimes, but that is a new hypothesis, not a re-grade.

## 12. Verdict and recommendation

- **Round 3 finds no strategy #2.** All 15 ideas are Tier-1 FAIL; the ranked candidate list is empty.
- **The round was not wasted:** it produced the lane's first honest full-multiplicity DSR (n=69), confirmed the research bar filters Sharpe-with-tail-risk (BTC 0.98/−55%, NQ 0.86/−43% rejected), and showed the benchmark gate binding exactly where Charlie's goal requires it.
- **Recommendation:** do not re-screen these 15 ideas without a new hypothesis (new regime window, new sizing, or portfolio-level Tier-2 framing). The next idea-generation round should target structurally different return generators — the vol-premium track is still blocked on the data-spend decision, which remains Charlie's call.

## 13. Evidence index

- `evidence/scout_results.json` — per-scout grids, scanned counts, all 15 retained ideas with metrics.
- `evidence/grid_all.json` — all 70 screened combinations with Sharpe/drawdown/trades/score/clear-reject (1 engine failure recorded).
- `evidence/debates.json` — full debate transcripts: rounds 1–2 scripted, rounds 3–4 LLM challenger, plus synthesis.
- `evidence/llm_challenger_turns.json` — the authored LLM challenger turns (source data for debate rounds 3–4).
- `evidence/tier1_results.json` — walk-forward geometry, cost/benchmark notes, per-idea OOS evidence, DSR detail, all five gate evaluations.
- `evidence/idea_returns.json` — daily strategy + aligned benchmark returns per idea (the Tier-1 input series).
- `evidence/scripts/` — the exact run scripts (scout sweep, debate, grid capture, Tier-1).

Machine-readable, plain-data, no hidden steps. Hard stop here: no pre-registration, no trial, no lifecycle transition without separate authorization.
