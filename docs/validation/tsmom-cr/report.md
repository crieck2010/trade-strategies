# TSMOM-CR validation report — trial 3 candidate B (re-run, valid path)

- Pre-registration: commits 42ecab2/425745b (frozen spec, before any validation data pull); gate amendment 425745b
- Run: 2026-09-27, one clean run, no tuning
- Venue: **Binance.US (primary; Kraken fallback not usable — see spec interpretation note in report.md)**
- Data: Binance.US public daily klines via trade-data-crypto BinanceUSPublicProvider (keyless)
- Calendar span: 2019-09-17 .. 2026-09-25 (2566 days)
- Costs: 25.0 bps/side all-in, no borrow
- Walk-forward: 728d train / 182d test / 182d step / 5d embargo — 10 folds, 1820 OOS days
- Annualization: 365 (crypto 24/7; calendar-day folds deliberate)

## Spec interpretation note (frozen-spec resolution)

The pre-registration names Binance.US primary with Kraken fallback ONLY if Binance.US daily history proves discontinuous — 'the venue is chosen on history completeness'. Inspection proved: Binance.US daily has a 585-day hole (2023-07-15..2025-02-18; 1981/2566 bars served for BTC) AND Kraken's public API serves only the most recent ~720 daily candles (verified by probe) — the fallback's background assumption (Kraken deep history) is false, so the fallback cannot serve the 2019-09-17..2026-09-25 span either. The first validation attempt was archived INVALID for exactly this reason: 0 folds fit the frozen 104w/26w/26w geometry on 719 bars, so the gated OOS series was empty (docs/validation/tsmom-cr/invalid_runs/2026-09-27_zero-oos-folds/).

Resolution, staying inside the spec: validate on the primary venue Binance.US under the spec's own data rule — 'Data holes: a day with no bar = hold (no signal change), exactly as screened' — which is also exactly how Phase B screened it (docs/research/scratch/tsmom_cr.py ran the screen on this same gappy Binance.US series). This changes no parameter, no geometry, no venue-shopping: no gate results were seen before this resolution. **Charlie may overrule this interpretation.**

## Venue coverage

| symbol | bars served | calendar days | hole days | hole runs |
|---|---|---|---|---|
| BTC/USD | 1981 | 2566 | 585 | 2023-07-15..2025-02-18 (585d) |
| ETH/USD | 1980 | 2566 | 586 | 2019-09-17..2019-09-17 (1d); 2023-07-15..2025-02-18 (585d) |

Construction: calendar-day-indexed return series. Hole day (no bar) = signals frozen (inherit prior day), positions frozen, equity unchanged → daily return 0. Mark-to-market on a bar day references the most recent available close, so P&L accrued while held through a hole is realized on the first post-hole bar day. Fills at t+1 open; at hole boundaries a fill is deferred to the next day with a bar, at that day's open. Vol for sizing uses trailing 60 one-day bar-to-bar returns, excluding gap-spanning returns.

## Gates (trade-overfit v0.2.0 standard preset, DSR n_trials=7)

| gate | value | threshold | result |
|---|---|---|---|
| deflated_sharpe | 0.0000 | gte 0.95 | FAIL |
| oos_sharpe | -0.2097 | gt 1.0 | FAIL |
| max_drawdown | -0.2706 | gt -0.15 | FAIL |
| regime_stability | -0.4433 | gt 0.0 | FAIL |
| beats_benchmark_net | -0.1201 | gt 0.0 | FAIL |
| sortino | -0.2022 | gte 1.5 | FAIL |
| calmar | -0.0828 | gte 2.0 | FAIL |

**Verdict: KILL**

## Walk-forward folds (OOS)

| fold | test window | OOS Sharpe(365) | OOS return | OOS maxDD |
|---|---|---|---|---|
| 0 | 2021-09-19..2022-03-19 | 0.595 | 0.0319 | -0.0595 |
| 1 | 2022-03-20..2022-09-17 | -1.311 | -0.0640 | -0.0989 |
| 2 | 2022-09-18..2023-03-18 | 0.338 | 0.0187 | -0.0693 |
| 3 | 2023-03-19..2023-09-16 | -0.758 | -0.0347 | -0.0855 |
| 4 | 2023-09-17..2024-03-16 | n/a | 0.0000 | 0.0000 |
| 5 | 2024-03-17..2024-09-14 | n/a | 0.0000 | 0.0000 |
| 6 | 2024-09-15..2025-03-15 | -1.389 | -0.1028 | -0.1284 |
| 7 | 2025-03-16..2025-09-13 | 1.143 | 0.0900 | -0.0679 |
| 8 | 2025-09-14..2026-03-14 | -2.695 | -0.1135 | -0.1170 |
| 9 | 2026-03-15..2026-09-12 | 1.171 | 0.0849 | -0.0971 |

- Concatenated OOS: 1820 days (2021-09-19 .. 2026-09-12)
- Strategy annualized (OOS): -0.0224
- BTC buy-and-hold annualized, net of 25 bps entry+exit: 0.0978 (total 0.5921)
- DSR detail: sharpe_hat=-0.1433, n_obs=1820, n_trials=7, skew=0.243, ex.kurt=20.900, ESR_null=0.5324
- Vol regimes: calm: n=911, sharpe=0.630, ret=0.0853, dd=-0.0462; stress: n=909, sharpe=-0.443, ret=-0.1770, dd=-0.3153

## Cost sensitivity (report-only, full-span re-simulation)

| bps/side | final equity | total return | Sharpe(365) | maxDD | fills |
|---|---|---|---|---|---|
| 25 | 180,564.88 | 0.8056 | 0.678 | -0.2706 | 268 |
| 10.0 | 190,425.67 | 0.9043 | 0.733 | -0.2433 | 268 |
| 50.0 | 165,238.13 | 0.6524 | 0.587 | -0.3138 | 268 |

## Honest flags

- Same instruments as killed trial 2 (MR-5M): BTC/ETH. Mechanism differs (daily trend, long/flat vs 5-min mean reversion, long/short), but if crypto market structure was trial 2's problem, this fails the same way.
- 2-name concentration: a single-asset drawdown is a portfolio drawdown.
- One secular crypto bull market (2019–2026) with two violent interruptions; the walk-forward folds are the honest test.
- ~32% of the concatenated OOS day-count (585 hole days) is the Binance.US data hole: positions are frozen and daily returns are exactly 0 through it, so it contributes no signal and no P&L to the OOS metrics — the gates are evaluated on the remaining OOS days plus the one-day post-hole P&L realizations. The hole cannot create edge; it dilutes both return and volatility.
- 25 bps/side is an assumption, not a measurement (see sensitivity).
- t+1-open fills on daily bars miss intrabar dynamics; optimistic on violent gap days — direction of bias unknown, documented.

## Provenance

- Pre-registration: commits 42ecab2/425745b (frozen spec + gate amendment, both before any validation data pull)
- Data: Binance.US public daily klines via trade-data-crypto BinanceUSPublicProvider (keyless); span 2019-09-17 .. 2026-09-25
- Gates: trade-overfit v0.2.0 preset_gates('standard'); DSR trial_sharpes=[0.798, 0.485, 0.413, 0.379, 0.106, -0.097, -0.337] (n=7), periods=365
- Run: 2026-09-27T02:28:38.127898+00:00 → 2026-09-27T02:28:43.967385+00:00 (UTC)
- Supersedes the INVALID-stamped report.md/evidence.json from the first attempt; that run remains archived under docs/validation/tsmom-cr/invalid_runs/2026-09-27_zero-oos-folds/
