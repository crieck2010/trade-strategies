# PRE-REGISTRATION — Crypto scalping strategy trial 2 of 2

**Strategy:** MR-5M — 5-minute mean reversion, long/flat, on BTC/USD and ETH/USD spot
**Registered:** 2026-09-26 (America/New_York), before any OHLC market data was pulled.
**Trial count:** 2. Trial 1 was DON-20/10-ATR (KILLED 2026-09-26 for risk profile:
median OOS Sharpe 0.87 < 1.0, OOS maxDD −40.2%). This spec is frozen. If it fails
the gates, the verdict is KILL. No parameter tuning and no re-running with
different parameters — that would be trial 3 and must be accounted for in the
Deflated Sharpe Ratio.

**Data-touch audit:** as of this commit, no OHLC market data has been pulled for
this trial. Pre-registration research used only: (a) public web sources for fee
schedules (not market data), (b) Binance.US `/api/v3/exchangeInfo` and Kraken
`/0/public/AssetPairs` *listing* endpoints on 2026-09-26 to confirm symbols
exist and both venues' APIs are reachable (no prices returned by those calls),
(c) connectivity pings. The first OHLC pull happens after this commit.

## One-paragraph description

A long/flat 5-minute mean-reversion scalper on BTC/USD and ETH/USD spot
(Binance.US): when the close prints more than 2.0 trailing-8-hour standard
deviations below the trailing-8-hour mean, buy 10% of equity; exit when the
z-score crosses back to ≥ 0, or on a stop if it extends to −4.0, or after 48
bars (4 hours) — whichever comes first. Signals are computed at bar t's close
and filled at bar t+1's open (no lookahead); one position per symbol; costs
modeled at the venue's documented retail taker fee plus half-spread plus
slippage — no maker-fill fantasy.

## Venue (frozen selection rule)

- **Primary: Binance.US**, spot pairs `BTCUSD` and `ETHUSD` (confirmed `TRADING`
  on 2026-09-26 via listing check). Fee schedule (frozen): **0% maker / 0.02%
  taker flat on all spot pairs**, April 2026 overhaul, no volume tiers.
  Sources: Binance.US fee change reporting (crypto-economy.com, 2026-04;
  tradersunion.com, 2026-04) and fee-schedule screenshot (cryptsy.com,
  captured 2026-07-08). Taker assumption: **2 bps/side**.
- **Fallback: Kraken**, spot pairs `XXBTZUSD` / `XETHZUSD`, ONLY if Binance.US
  public klines are unreachable at data-pull time. Kraken fee (frozen):
  **0.80% taker** (Kraken Pro Tier 1 entry, effective 2026-07-09; source:
  Kraken official blog fee-tier announcement + fee schedule). Under Kraken
  fees this strategy is *expected* to fail — that outcome would be reported
  as a venue-economics KILL, which is itself the finding.
- The venue used is recorded in the evidence bundle. The cost model always
  matches the data venue.

## Data

- 5-minute OHLCV bars, **2024-01-01 through 2026-09-25** (~2.75 years; crypto
  trades 24/7 → ~288 bars/day → ~289k bars/symbol), via the new
  `BinanceUSPublicProvider` in trade-data-crypto (Phase 1 of this build).
- Benchmark: BTC buy-and-hold over the same span (buy first bar open, hold;
  no costs — the buy-and-hold investor trades twice).

## Signals (frozen; all computed on bar t's close; fills at bar t+1's open)

- **z-score:** `z[t] = (close[t] − mean(close[t−96..t−1])) / std(close[t−96..t−1])`,
  population std (ddof=0), 96 bars = 8 hours. Guard: `std ≤ 0` or non-finite →
  no signal (covers flat/maintenance windows).
- **Entry (flat → long):** fresh cross below −2.0: `z[t−1] ≥ −2.0 and z[t] < −2.0`.
  Buy at `open[t+1]`. One position per symbol; no pyramiding.
- **Exits (long → flat),** evaluated at bar t's close, filled at `open[t+1]`
  (first trigger wins):
  1. Mean reversion complete: `z[t] ≥ 0`.
  2. Stop (adverse extension — breakout, not reversion): `z[t] ≤ −4.0`.
  3. Time stop: 48 bars after the entry bar.
- **Re-entry:** requires a fresh cross (same rule as entry).
- **Warmup:** no signals before bar index 96.

## Position sizing and portfolio constraints (frozen)

- Each position: **10% of current equity** notional.
- Max **1** concurrent position per symbol (**2** portfolio-wide).
- Skip if position value < exchange minimum (documents but never binds at
  10% of $100k).
- Long/flat only: upside deviations (z > +2) are ignored — no short leg.
  Spot only, no leverage, no funding, no borrow cost.

## Session handling (frozen)

Crypto trades 24/7: no sessions, no weekend exclusion, no calendar logic.
Exchange maintenance windows appear in the data as-is (flat/low-volume bars);
the `std ≤ 0` guard handles them.

## Costs (frozen; applied in-engine via trade-backtest CostModel)

Per-side decomposition (bps of notional), Binance.US venue:
- Taker fee: **2 bps** (0.02% flat; market orders assumed — no maker-fill fantasy).
- Half-spread: **2 bps** (conservative *assumption* for BTC/ETH spot; typical
  observed 1–3 bps — assumed, not measured; stated, not hidden).
- Slippage: **2 bps** adverse.
- **Total: 6 bps/side = 12 bps round-trip on notional.**
- Engine mapping: `slippage_entry_bps = 4.0` (2 slippage + 2 taker fee),
  `slippage_exit_bps = 4.0`, `half_spread_bps = 2.0`, commission
  `NoCommission()`, borrow 0. The assumptions block records this decomposition
  so the taker fee is never mistaken for slippage.
- If the Kraken fallback triggers, the taker leg becomes 80 bps/side and the
  totals are recomputed in the evidence bundle.

## Backtest (frozen)

- trade-backtest engine, `periods_per_year = 105_120` (365 × 24 × 12),
  `adjustment_basis = "none"` (crypto spot: no splits/dividends),
  initial cash **$100,000**, risk-free 0.
- Signals t → fills t+1 open (the engine's native convention — no lookahead).

## Walk-forward (frozen; validates stability, NOT tuning — parameters never change)

- Rolling folds over the full-sample 5-minute strategy returns (one global
  backtest run; the strategy is deterministic and causal, so per-fold OOS
  returns equal a per-fold re-run's):
  train = **24,192** bars (12 weeks), test = **4,032** bars (2 weeks),
  step = **4,032** bars, embargo = **288** bars (1 day) between train end and
  test start.
- Per fold: in-sample Sharpe (train, context only), OOS Sharpe, OOS return,
  OOS max drawdown.
- **The concatenated OOS test-fold returns are THE return series for gating.**

## Gates (trade-overfit standard preset; frozen thresholds; trial count N = 2)

| # | Gate | Metric | Rule |
|---|------|--------|------|
| 1 | deflated_sharpe | DSR, trial_sharpes = [0.666 (trial 1 OOS Sharpe), trial-2 OOS Sharpe] | ≥ 0.95 |
| 2 | oos_sharpe | median OOS Sharpe across folds (annualized, 105120) | > 1.0 |
| 3 | max_drawdown | max drawdown of OOS series | > −0.15 |
| 4 | regime_stability | worst-regime Sharpe (desk vol-regime splits on OOS series) | > 0.0 |
| 5 | beats_benchmark_net | ann. OOS return − ann. BTC buy-and-hold return, net of costs | > 0.0 |

**Verdict:** ALL five pass → PASS. Any single failure → **KILL**, with the
failing gate(s) named. No exceptions, no re-tuning.

Note on gate 5: BTC buy-and-hold is the opportunity-cost benchmark — if the
scalper can't beat holding BTC, the capital shouldn't trade it. The 10%
notional sizing means the strategy carries ~90% cash drag versus a
fully-invested benchmark; that asymmetry is disclosed here, not adjusted away.

## What happens on PASS / KILL

- PASS → strategy ships in trade-strategies as a validated module (minor
  release + CHANGELOG); it becomes a *candidate* for paper trading. Paper
  trading itself is NOT started (out of scope — a 5-minute scalper cannot run
  on the current 3×-daily paper loop; that is future infrastructure work).
- KILL → spec + evidence + docs are committed (the kill is documented); the
  strategy is NOT shipped as viable; no release.

## Known limitations (frozen with the spec)

- 5-minute bars miss intrabar dynamics; the t→t+1-open fill is a documented
  simplification (a real scalper fills intrabar, for better or worse).
- No order-book or adverse-selection modeling; taker assumption is the
  conservative side of this.
- Half-spread (2 bps/side) is an assumption, not a measurement.
- Fee tier is retail entry; higher 30-day volume would lower fees
  (conservative direction).
- Binance.US carries regulatory overhang (US Senate scrutiny reported Feb
  2026) — venue risk is not modeled.
- Gates reduce overfitting; they do not eliminate it. Past ≠ future.
- The regime arbiter's daily-horizon conviction sits above this strategy's
  horizon and is not wired in — documented, not hidden.
