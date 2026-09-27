# Research report — round 2, Phases B + C (2026-09-26)

Batch: 10 theses from Phase A (2026-09-26), in
`docs/research/round2/IDEAS-2.md` / `phase-a2-ideas.json`, generated
through the same agent-desk debate protocol as round 1 (rules mode,
bull/bear, 2 rounds; the bear won every debate pre-evidence — correct
behavior). This report covers Phase B (cheap in-sample screening) and
Phase C (shortlist + pre-registration). Trial 4 (validation) is NOT
authorized and was not run.

## The batch at a glance

| Track | Ideas | Outcome |
| --- | --- | --- |
| Track 1 — sentiment × price | SENTDIV-1, ATTN-1, EVTDRIFT-1, SENTCAP-1 | **Deferred, not screened** — no sentiment history exists before archive deployment; none fabricated (see Track-1 deferral below) |
| Track 2 — cross-asset RV | RVBOND-1, BASIS-1, REGCOND-1 | RVBOND-1 screened (loser), BASIS-1 unscreenable, REGCOND-1 screened (winner) |
| Track 3 — vol premium sketches | VOLCAL-1, VOLSKEW-1, VOLDISP-1 | **Sketches only** — no options-chain data in the stack |

## Screening methodology (Phase B)

* One in-sample backtest per screenable idea through
  `trade-backtest` v0.2.0 (`BacktestEngine`, `TargetStrategy` harness),
  window 2018-01-01..2026-09-25, t→t+1 fills, `adjustment_basis="pre_adjusted"`.
* Data: Charlie's stack only — yfinance daily adjusted ETF bars
  (GLD/TLT/TIP/SPY/CPER, 2015-01-01..2026-09-25; pre-2018 used as warmup
  only) and the `trade-macro` copper:gold regime engine
  (`ratio_series` → `enrich_ratios` → `classify_regime`, preset="standard").
* Costs: 5 bps/side; 50 bps/yr borrow on shorts (RVBOND-1 only).
* Implementations: `docs/research/round2/scratch/` — labeled RESEARCH
  SCRATCH, nothing added to `src/`. Evidence:
  `docs/research/round2/evidence/screening2_results.json`.

## Numbers (winners AND losers — full record)

| Rank | Idea | Sharpe | Sortino | MaxDD | Trades | Total ret | CAGR | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | REGCOND-1 | **+0.918** | +1.299 | 0.231 | 90 | +135.7% | +10.3% | advance |
| 2 | RVBOND-1 | **−0.493** | −0.695 | 0.403 | 126 | −34.4% | −4.7% | dead |

**n_screened = 2** — see DSR trial-count accounting below.

**REGCOND-1** (copper:gold regime → SPY/CPER/TLT/GLD tilts, monthly):
thesis-match yes. The regime switch dodges the COVID and 2022 equity
drawdowns into the defensive CONTRACTION mix and catches equity upside in
EXPANSION months. Context (same window): SPY buy-and-hold +227.7% total /
Sharpe +0.813; 60/40 SPY/TLT +129.1% / Sharpe +0.808. REGCOND-1 trails SPY
on total return — its Sharpe edge comes from lower volatility, not higher
return — but beats 60/40 on both. Honest flags recorded in SCREENING-2.md
and frozen into the pre-reg: secular-trend contamination of the regime
label (1,173 of 2,950 days CONTRACTION), label lag by construction, ~2–3
full cycles in-sample, and the killed-TREND-VT cousinship (structurally
different signal, but stated).

**RVBOND-1** (GLD/TLT vs TIP-implied real-yield fair value, 90-day OLS,
monthly coefficient refresh, |z|>1.5 entries, z=0 or 30-day exits): the
residual does not mean-revert — its own kill criterion fired (real-yield
regime shifts broke the relationship in 2020–2022 and it never came back).
−34.4% with 40.3% maxDD. Dead on this evidence; no parameter rescue
attempted.

## Why the winner won

REGCOND-1 won on in-sample risk-adjusted merit (Sharpe +0.918 vs −0.493)
with a thesis-match of yes, and it clears the structural-distance bar
against all five killed classes: it is a discrete macro-regime switch,
not a breakout (K1), not crypto or sub-daily or price mean-reversion
(K2), with no vol targeting and no trailing-return signal (K3 — the
explicit difference from killed TREND-VT), not directional crypto trend
(K4), and not cross-sectional equity ranking (K5). The economic rationale
— copper:gold as the market's growth-expectations vote leading equity
risk appetite — is a documented, slow-moving, hard-to-overfit signal at
monthly cadence. RVBOND-1 lost on the numbers and stays dead.

## Track-1 deferral statement (explicit)

The four sentiment×price theses were NOT screened, and deliberately so.
The Phase-0 backfill investigation found no keyless historical text
source: GDELT's query API rate-refuses programmatic access and its bulk
files aren't ticker-addressable; no keyless Reddit/StockTwits/Google-News
archive is ticker-addressable at daily grain. **No sentiment history
exists before deployment, and none was fabricated.** The
`trade-sentiment` v0.3.0 point-in-time archive (`Archive`, sqlite3,
`query(symbol, as_of)` with SQL-enforced no-lookahead) accumulates from
deployment forward.

Screening Track-1 on price-derived proxies (volatility for "attention",
returns for "tone") would test price signals while claiming to test
sentiment — dishonest — and cannot measure sentiment's incremental value
over price, which is every Track-1 thesis's kill criterion. Track-1
screening happens once real archive history exists (each thesis's
sentiment contract requires ≥2y of ticker-day observations for
z-score/percentile baselines).

To build that history, a daily accumulation cron is needed — **NOT set
up by the research agent; for Charlie's approval:**

```
30 16 * * 1-5 PYTHONPATH=$HOME/workspace/trade-suite/trade-sentiment/src \
    python3 -m trade_sentiment scan AAPL MSFT NVDA AMZN META GOOGL TSLA \
    AVGO BRK-B JPM XOM UNH V MA JNJ WMT ORCL HD PG BAC COST LLY NFLX \
    CRM AMD ADBE QCOM TXN LIN CAT IBM GE INTU NOW AMAT BKNG ISRG VRTX \
    --archive $HOME/.trade-sentiment/sentiment-archive.db \
    >> $HOME/.trade-sentiment/cron.log 2>&1
```

(~30 min after US close, weekdays; `--archive` records every scored
mention into the point-in-time archive. Ticker list should match the
eventual screening universe; weekend runs are pointless.)

## DSR trial-count accounting (explicit, for trial 4)

* n_screened = 2 (RVBOND-1, REGCOND-1 — the only ideas actually screened).
* Track-1's 4 ideas: deferred, never screened → **0 trials**.
* BASIS-1: unscreenable → **0 trials**.
* Track-3's 3 sketches: never run → **0 trials**.
* Trial-4 DSR for the REGCOND-1 pre-registration MUST use **n_trials = 2**
  with the round-2 in-sample Sharpe list as the trial set. The pre-reg
  records this (see `docs/validation/regcond-1/PRE-REGISTRATION.md`).
* No validation runs, no gate evaluations, no releases, no registry
  entries were made in this phase.

## Phase C outcome

* **Pre-registered (frozen spec):** REGCOND-1 —
  `docs/validation/regcond-1/PRE-REGISTRATION.md`. Universe (SPY/CPER/TLT/GLD),
  trade-macro copper:gold signals (preset="standard", prior-month-end
  label, monthly rebalance), fixed regime weights, 5 bps/side, t+1 fills,
  walk-forward geometry (104w train / 26w test / 26w step, 5-day embargo),
  benchmark 60/40 SPY/TLT (monthly, net of costs; SPY buy-and-hold as
  context), the current 7-gate set with DSR n_trials = 2, honest flags
  frozen, and the two-tier-gate-reform note (dated amendment procedure if
  adopted before validation).
* **Not pre-registered:** RVBOND-1 (negative in-sample — no second slot
  filled rather than registering a known loser).
* **Archive consumption:** none — nothing in this phase read from the
  sentiment archive; Track-1 screening awaits real accumulated history.

## Stack gaps confirmed (round 2)

No historical sentiment archive (Track-1 deferred); no historical
options chains / IV surface (Track-3 sketches); no keyless dated-crypto-
future history (BASIS-1 unscreenable); JJC delisted (CPER used as copper
proxy). `trade-macro`'s copper:gold pipeline works cleanly on ETF
proxies.

## Hard stop

Screening and pre-registration only. No validation data touched beyond
the in-sample screens documented here. The trial-4 validation run for
REGCOND-1 awaits Charlie's authorization.
