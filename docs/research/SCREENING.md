# Phase B — Strategy Screening (in-sample, 2026-09-26)

Screening pass over the candidate ideas in `docs/research/IDEAS.md` /
`docs/research/phase-a-ideas.json`. Purpose: rank ideas by a fast
in-sample backtest so the strongest 2–3 can be considered for full
validation later. **Screening is not validation.** No walk-forward, no
overfit gates, no DSR here — winners from this page still have to survive
the full trial machinery (pre-registration, embargo, DSR with
n_screened trials) before any paper use.

## How it was run

* One backtest per screenable idea, 2018-01-01..2026-09-25 (t→t+1 fills,
  no lookahead), through `trade-backtest`'s `BacktestEngine` and the
  `Strategy` interface, with explicit `adjustment_basis="pre_adjusted"`.
* Data: Charlie's stack only — `trade-data-equities`/yfinance daily bars
  (equities + ETFs + FX spot + 6E/6J/6B futures), `trade-data-crypto`
  (Binance.US BTC/USD + ETH/USD daily from 2019-09-17).
* Costs: 5 bps/side equities & ETFs; 25 bps/side crypto (task-authorized
  conservative assumption between Binance.US 2 bps and Kraken retail
  80 bps taker); 50 bps/yr borrow on shorts.
* Implementations live under `docs/research/scratch/` and are labeled
  **RESEARCH SCRATCH — NOT a strategy module**. Nothing was added to
  `src/`. Exact simplifications are recorded per idea below and in the
  scratch files' `SIMPLIFICATIONS` blocks.
* Machine-readable evidence:
  `docs/research/evidence/screening_results.json` (per-idea params,
  metrics, assumptions, timestamps).

## Ranking (primary: in-sample Sharpe)

| Rank | Idea | Sharpe | MaxDD | Trades | Total ret | Window |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | TSMOM-CR | **0.798** | 0.201 | 166 | +104.4% | 2019-09-17..2026-09-25 |
| 2 | TREND-VT | **0.485** | 0.106 | 523 | +23.9% | 2018-01-01..2026-09-25 |
| 3 | XMOM-1 | **0.413** | 0.253 | 1,275 | +61.7% | 2019-01-01..2026-09-25 |
| 4 | CARRY-1 | **0.379** | 0.048 | 38 | +12.3% | 2018-01-01..2026-09-25 |
| 5 | BAB-1 | 0.106 | 0.142 | 14,995 | +4.7% | 2019-01-01..2026-09-25 |
| 6 | FMOM-1 | −0.097 | 0.298 | 58 | −10.2% | 2018-01-01..2026-09-25 |
| 7 | PAIRS-1 | −0.337 | 0.102 | 987 | −8.1% | 2018-01-01..2026-09-25 |

**n_screened = 7.** Sketches and unrun ideas do not count. This number is
the future trial-3 DSR trial count.

## Per-idea verdicts

### TSMOM-CR — SCREENED, rank 1 (Sharpe 0.798)
Crypto time-series momentum: long BTC/ETH on 90-day breakout or positive
50-day momentum, long/flat, 10% vol-target sizing per name (refreshed
monthly / on entry), 25 bps/side. +104% with 20% maxDD over the 7-year
Binance.US daily window. Thesis match: **yes** — rode the major crypto
uptrends, flat through drawdowns. Caveats: only 2 names, only 166 trades,
and the entire edge is one asset-class bull market; in-sample Sharpe is
flattered by the 2020–21 and 2024–25 runs. Needs regime-split validation
before any conclusion.

### PAIRS-1 — SCREENED, rank 7 (Sharpe −0.337). Loser.
Quarterly cointegration screen (252-day lookback, ≤10 pairs, half-life
< 60d) on the raw-price Engle-Granger residual, z-entry ±2 / exit ±0.5,
60-day z window, 20-day time stop, 10% gross per pair. −8.1% with 10.2%
maxDD, 987 trades. Thesis match: **no** — the mean-reversion edge does
not survive costs and quarterly pair turnover in this implementation.

**Important correction, documented honestly:** an early version of this
screen replayed the spread as `log(pA) − hr·log(pB) − c`, but
`trade-pairs`' Engle-Granger OLS is estimated on **raw** prices, so the
true cointegrating residual is `pA − hr·pB − c` (confirmed against
`trade-pairs/docs/METHODOLOGY.md`). The log-spread version printed
Sharpe +0.584; the corrected spec-consistent version prints −0.337.
The +0.584 was a specification bug, not an edge — the final number is
the corrected one. This is exactly why specs get frozen before
validation runs.

### TREND-VT — SCREENED, rank 3 (Sharpe 0.485)
6-ETF trend (SPY/TLT/GLD/USO/EFA/VNQ), sign of trailing 252-day return,
60-day vol targeting toward 10% portfolio vol, monthly. +24% with only
10.6% maxDD — the best risk profile of the equity ideas. Thesis match:
**yes**, behaves like a defensive trend overlay. Caveat: no gross cap;
low absolute return.

### XMOM-1 — SCREENED, rank 4 (Sharpe 0.413)
Monthly cross-sectional momentum, 252-day formation skipping 21 days,
top/bottom decile, 50/50 L/S. +62% but 25.3% maxDD (momentum crashes).
Thesis match: **yes** — textbook momentum payoff shape. Caveat: current
large-cap universe = survivorship bias, likely flattering.

### CARRY-1 — SCREENED, rank 5 (Sharpe 0.379)
FX carry via front-future vs spot basis (6E/6J/6B vs EUR/JPY/GBP),
monthly 1-long/1-short/1-flat. +12.3% with 4.8% maxDD, only 38 trades.
Thesis match: **partial** — directionally a carry payoff, but the carry
measure is an approximation (yfinance continuous =F rolls, quarterly
expiry grid) and the portfolio is tiny (2 positions). Honest as a
screen; a validation-grade version needs proper futures term-structure
data.

### BAB-1 — SCREENED, rank 5 (Sharpe 0.106)
Monthly 252-day beta vs SPY, long low-beta tercile / short high-beta
tercile, beta-neutral sizing. +4.7% net over 8.75y, 14,995 closed legs —
the monthly full rebalance of ~180 names churns hard at 5 bps/side.
Thesis match: **weak** — the classic BAB premium does not survive costs
and monthly turnover in this implementation. Loser.

### FMOM-1 — SCREENED, rank 7 (Sharpe −0.097)
Factor momentum on price-derived proxies (momentum, low-vol, reversal,
low-beta indices via `trade-factors.long_short_weights`), long top-2 /
short bottom-2 factor indices monthly. −10.2% with 29.8% maxDD.
Thesis match: **no** — factor timing adds nothing here; the synthetic
short factor legs (no borrow) still lose. Loser.

## Not screened

* **SENT-1 — UNSCREENABLE.** No point-in-time historical sentiment
  archive exists in the stack (`trade-sentiment` scans current feeds
  only). No proxy was fabricated; see `scratch/sent_1.py`.
* **VOLPREM-1 — SKETCH ONLY.** No historical options-chain / IV-surface
  data. Design sketch in `scratch/volprem_1.py`.
* **PEAD-1 — SKETCH ONLY.** No point-in-time earnings-date / consensus
  surprise history. Design sketch in `scratch/pead_1.py`.

## Combined judgment (top 2–3)

1. **TSMOM-CR** — best in-sample risk-adjusted return, but the narrowest
   evidence base (2 coins, one secular bull market, 166 trades). Validate
   with regime splits and a longer/poorer crypto history before trusting it.
2. **TREND-VT** — lowest drawdown of the equity set (10.6%) at a
   respectable 0.485 Sharpe; a natural defensive trend overlay rather
   than a standalone engine.
3. **XMOM-1** — textbook momentum payoff (+62%, 25% maxDD crash profile);
   the classic candidate, but survivorship bias flatters it.

**Losers:** PAIRS-1 (spec-corrected screen loses money), FMOM-1
(negative Sharpe — factor timing adds nothing here), BAB-1 (+4.7% net
over 8.75y; the premium does not survive monthly turnover at 5 bps).

Honest note: every equity cross-sectional result carries survivorship
bias from the current-constituent universe, and every Sharpe above is
in-sample with no multiple-testing correction — that correction is
exactly what the trial-3 DSR (N=7) is for.

## Stack gaps found

* No historical sentiment archive (SENT-1 blocked).
* No historical options chains / IV surface (VOLPREM-1 blocked).
* No earnings-date / consensus-surprise history (PEAD-1 blocked).
* Binance.US daily spot history starts 2019-09-17 (crypto screens are
  7y, not 8.75y); its 5-minute history has the known 2023-09..2025-02
  hole (not used here).
* FX futures carry screening is approximate: yfinance `=F` continuous
  rolls + quarterly expiry grid; a validation-grade carry needs real
  term-structure data.
