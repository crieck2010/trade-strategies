# PRE-REGISTRATION — Swing strategy trial 1 of 1

**Strategy:** DON-20/10-ATR — Donchian-20/10 breakout with ATR trailing stop (long/flat)
**Registered:** 2026-09-26 (America/New_York), before any market data was pulled.
**Trial count:** 1. This spec is frozen. If it fails the gates, the verdict is KILL.
No parameter tuning and no re-running with different parameters — that would be
trial 2 and must be accounted for in the Deflated Sharpe Ratio.

## One-paragraph description

A long/flat Donchian trend system on liquid S&P 500 names: buy 20-day closing
highs, exit on 10-day closing lows or a 2.5×ATR(20) trailing stop, risking 1% of
equity per trade (position value capped at 10% of equity, at most 20 concurrent
positions). Signals are computed on the daily close and executed at the next
day's open, with 5 bps slippage per side and zero commission.

## Universe (mechanical selection rule)

1. Start from the S&P 500 constituent list on Wikipedia ("List of S&P 500
   companies") as retrieved on **2026-09-26** (retrieval date recorded in the
   evidence bundle).
2. Keep a constituent only if ALL hold:
   - (a) daily bars available from 2015-01-01, with bar count ≥ 99% of SPY's bar
         count over the same period (missing symbol-days are simply absent from
         that symbol's walk — no forward-fill, no imputation);
   - (b) close ≥ $10.00 on 2026-09-01;
   - (c) median 63-trading-day dollar volume (close × volume) ≥ $25M ending
         2026-09-01.
3. Survivorship note (frozen as a known limitation): the list is today's
   constituents, so companies that were delisted / went bankrupt are missing.
   **Direction of bias: upward** — the backtest cannot lose money on names that
   died. This flatters absolute returns and is stated, not hidden.

## Data

- Daily OHLCV, 2015-01-01 through 2026-09-25 (~10.7 years), via yfinance
  (`auto_adjust=True`: split- and dividend-adjusted OHLC; volume unadjusted).
- Benchmark: SPY adjusted daily returns over the same span.

## Signals (all computed on bar t's close; fills at bar t+1's open — no lookahead)

- **Entry (flat → long):** `close[t] > max(high[t-20 .. t-1])` (20-day Donchian
  high of the *prior* 20 bars, excluding t). Buy at `open[t+1]`.
- **Exit — Donchian (long → flat):** `close[t] < min(low[t-10 .. t-1])`
  (10-day Donchian low of the prior 10 bars). Sell at `open[t+1]`.
- **Exit — trailing stop (long → flat):** Wilder ATR(20), seeded with the mean
  of the first 20 true ranges. On the entry-signal bar: `stop = close[t] − 2.5 × ATR20[t]`.
  Each bar while in position: `stop = max(stop, close[t] − 2.5 × ATR20[t])`
  (trails up only, never down). If `close[t] < stop` → sell at `open[t+1]`.
  Stop *triggers* are evaluated at the close; the *fill* is next open — a
  documented one-bar simplification (same convention as trade-swing).
- **Re-entry:** after any exit, re-entry requires a *fresh* 20-day breakout
  signal. No re-entry on mere price recovery.
- **Warmup:** no signals before bar index 21 (Donchian-20 needs 20 prior bars;
  ATR(20) is defined from bar 19; 21 covers both).

## Position sizing and portfolio constraints (frozen)

- Risk 1.0% of current equity per position:
  `target_value = (0.01 × equity) / (2.5 × ATR20[t] / close[t])`
  (a 2.5×ATR adverse move loses 1% of equity).
- Cap: `target_value ≤ 10% of equity`. Minimum: skip if target < 1 share.
- Max **20** concurrent positions. If more entry signals than free slots on one
  day, rank by 20-day momentum `close[t]/close[t-20] − 1` descending, take the
  top; ties broken alphabetically (deterministic).
- Slot accounting uses the strategy's own emitted entry/exit intents and assumes
  all signals fill at the next open (standard for liquid large-caps; documented).

## Costs (frozen; applied in-engine, so the return series is already net)

- Slippage 5 bps per side, adverse (buys lift, sells hit).
- Half-spread 0 bps. Commission $0.00. Long-only: no borrow cost.
- Corporate actions: pre-adjusted bars; no separate dividend/split events
  (dividends are in the adjusted price; no double-counting).

## Walk-forward (frozen; validates stability, NOT tuning — parameters never change)

- Rolling folds over the full-sample daily strategy returns (one global
  backtest run; the strategy is deterministic and causal, so per-fold OOS
  returns equal a per-fold re-run's):
  train = 756 trading days, test = 252, step = 252, embargo = 10 trading days
  between train end and test start.
- Per fold: in-sample Sharpe (train, context only), OOS Sharpe, OOS return,
  OOS max drawdown.
- **The concatenated OOS test-fold returns are THE return series for gating.**
  In-sample performance is reported for context only and never gates.

## Gates (trade-overfit standard preset; frozen thresholds; trial count N = 1)

| # | Gate | Metric | Rule |
|---|------|--------|------|
| 1 | deflated_sharpe | DSR (N=1) | ≥ 0.95 |
| 2 | oos_sharpe | median OOS Sharpe across folds | > 1.0 |
| 3 | max_drawdown | max drawdown of OOS series | > −0.15 |
| 4 | regime_stability | worst-regime Sharpe (desk vol-regime splits on OOS series) | > 0.0 |
| 5 | beats_benchmark_net | ann. OOS return − ann. SPY OOS return, net of costs | > 0.0 |

**Verdict:** ALL five pass → PASS. Any single failure → **KILL**, with the
failing gate(s) named. No exceptions, no re-tuning.

## What happens on PASS / KILL

- PASS → strategy ships in trade-strategies as a validated module (minor
  release + CHANGELOG); it becomes a *candidate* for paper trading. Paper
  trading itself is NOT started (out of scope).
- KILL → spec + evidence + docs are committed (the kill is documented); the
  strategy is NOT shipped as viable; no release.

## Known limitations (frozen with the spec)

- ~10.7 years of daily yfinance data, one market (US large-cap), no intraday.
- Survivorship bias (upward) as noted above.
- Gates reduce overfitting; they do not eliminate it. Past ≠ future.
- A 10-day embargo is conservative hygiene; with fixed parameters and no
  fitting, train→test leakage through parameter selection is zero by
  construction — the embargo guards only against autocorrelation artifacts.
