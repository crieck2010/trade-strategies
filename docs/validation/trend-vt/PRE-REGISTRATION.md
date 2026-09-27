# PRE-REGISTRATION — Trial 3 candidate A (of 2)

**Strategy:** TREND-VT — vol-targeted multi-asset time-series momentum (long/flat/short, monthly)
**Registered:** 2026-09-26 (America/New_York), before any validation data was pulled.
**Trial count for DSR:** 7 — see "Multiple-testing honesty" below. This spec is frozen.
If it fails the gates, the verdict is KILL. No parameter tuning and no re-running
with different parameters.

## One-paragraph description

A retail-scale managed-futures system on six liquid ETFs (SPY, TLT, GLD, USO, EFA,
VNQ): on each month-end rebalance date, each ETF is assigned long (+1), short (−1),
or flat (0) by the sign of its trailing 252-trading-day total return, and sized to
an equal volatility contribution — weight_i = sign_i × (0.10 / 6) / σ_i, where σ_i
is the ETF's trailing 60-trading-day daily volatility annualized. Target portfolio
volatility is 10% annualized. Positions are held until the next monthly rebalance.
Signals use month-end closes; fills at the next trading day's open; 5 bps per side
plus a 30 bps/year borrow charge on short notional.

## Multiple-testing honesty (read first)

This candidate was shortlisted from a **screened batch of 7** (Phase B research,
2026-09-26; full batch, screening methodology, and ranking in
`docs/research/SCREENING.md`, ideas in `docs/research/IDEAS.md`). Screening 7
ideas and validating the best is **7 trials of multiple testing** whether or not
the other 5 are ever validated. The trial-3 Deflated Sharpe Ratio MUST therefore
use **n_trials = 7**, with the Phase B in-sample Sharpe list as the trial set where
the DSR implementation requires it. Any future additional screening restarts this
accounting from the new total. Selecting the winner does not reset the count.

## Why this candidate (Phase B result)

- In-sample (2018-01-01..2026-09-25, 5 bps/side): Sharpe **+0.485**, maxDD **10.6%**
  (best risk profile of the batch), 523 trades, +23.9% total. Thesis-match: yes.
- Diversification vs killed trials: trial 1 (DON-20/10-ATR) was single-asset daily
  breakout; trial 2 (MR-5M) was single-asset 5-minute mean reversion. TREND-VT is
  multi-asset, monthly, vol-targeted, long/flat/short — a different construction
  and a different risk. Honest flag: it is still trend-following, so it shares
  trial 1's exposure to trend failure as a *family*; the diversification is
  structural (cross-asset + vol targeting + monthly), not categorical.

## Universe (frozen)

SPY, TLT, GLD, USO, EFA, VNQ — six liquid US-listed ETFs spanning equities,
Treasuries, gold, oil, developed-ex-US equities, and REITs. No substitutions.
If an ETF lacks bars on a rebalance date, that leg is flat for the month
(documented; USO reverse splits are handled by split-adjusted data).

## Data

- Daily OHLCV (split- and dividend-adjusted closes), 2010-01-01 through 2026-09-25,
  via yfinance (`auto_adjust=True`), pulled through `trade-data-equities`.
- Benchmark: buy-and-hold equal-weighted 6-ETF portfolio, rebalanced monthly, net
  of the same 5 bps/side costs. (Not SPY alone: the strategy is multi-asset, so
  the benchmark must be too.)

## Signals (frozen; computed on month-end close, fills next trading day's open)

- On each month-end rebalance date t (last trading day of the calendar month):
  for each ETF, compute trailing 252-trading-day total return
  `TR = close[t] / close[t-252] − 1` (requires 252 prior bars; otherwise the leg
  is flat).
- `sign_i = +1` if TR > 0, `−1` if TR < 0, `0` if TR == 0 (measure-zero event,
  specified for completeness).
- Positions held until the next rebalance; no intra-month trading, no stops.

## Position sizing (frozen)

- Per-ETF annualized volatility: `σ_i = stdev(daily returns[t-60..t-1]) × √252`.
- `weight_i = sign_i × (0.10 / 6) / σ_i`, evaluated on the rebalance date.
- No gross/leverage cap beyond the vol formula (documented; screening gross
  floated ~0.5–1.2). Volatility targeting IS the risk control.
- Rebalance trades are sized to the new target weights in full each month
  (turnover is part of the cost accounting).

## Costs and frictions (frozen)

- Commission/slippage: 5 bps per side on every rebalance trade, in-engine.
- Short borrow: 30 bps annualized on short notional, accrued daily (documented
  assumption — retail ETF borrow is typically 25–100 bps; 30 is the low,
  disclosed end).
- Fills at next trading day's open after the month-end signal. No lookahead.

## Walk-forward geometry for the validation run (frozen)

- Rolling: **60-month train / 12-month test / 12-month step**, embargo 21 trading
  days between train end and test start.
- No parameters are fitted (all values above are fixed), so walk-forward tests
  regime stability, not tuning: report per-fold OOS Sharpe/return/maxDD and the
  concatenated OOS series, which is the gated series.
- Span: 2010-01-01..2026-09-25 (test folds begin once 60 months of history exist).

## Gates (trade-overfit standard preset, DSR n_trials = 7)

1. Deflated Sharpe ≥ 0.95
2. Out-of-sample Sharpe > 1.0
3. Out-of-sample max drawdown > −15% (i.e., shallower than 15%)
4. Worst vol-regime Sharpe > 0
5. Beats the equal-weight 6-ETF benchmark net of costs

All five must pass → PASS (paper-trading candidate; paper itself is NOT
authorized here). Any failure → KILL, strategy marked not viable, no registry
entry, no release.

## Known limitations (frozen with the spec)

- yfinance ETF history; survivorship is a non-issue for ETFs but the 6-ETF set
  is a researcher choice (documented, not data-mined — it matches the Phase A
  thesis written before screening).
- Monthly rebalance months with violent intra-month reversals will show
  whipsaw; the 2015/2018-style chop years are the known enemy (stated in Phase A).
- Borrow cost is an assumption; validation must include a borrow-sensitivity
  note (0/30/100 bps).
- Vol targeting lags: σ_i is backward-looking; a vol spike mid-month is
  unaddressed until the next rebalance — by construction.

## Amendment 2026-09-26 — gate set extended from 5 to 7

The frozen specification above is unchanged. The gate set referenced in
"Gates (trade-overfit standard preset, DSR n_trials = 7)" is amended:

6. Sortino ≥ 1.5 (downside-adjusted return; trade-overfit standard preset)
7. Calmar ≥ 2.0 (annualized return per unit of max drawdown; trade-overfit
   standard preset)

All seven must pass → PASS. Any failure → KILL.

This amendment is dated and committed **before any validation data has been
pulled** (the validation run for trial 3 has not started). The direction is
conservative — the amended gate set is strictly harder to pass than the
original five, so it cannot manufacture a PASS that the original set would
have killed. DSR n_trials = 7 is unchanged. Trial-1 and trial-2 evidence is
untouched by this amendment.
