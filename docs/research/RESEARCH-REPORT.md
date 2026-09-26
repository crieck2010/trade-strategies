# Strategy research program — report (2026-09-26)

Purpose: find trial-3 candidates honestly. Two strategies had already been killed
by the overfit gates (DON-20/10-ATR: single-asset breakout; MR-5M: 5-minute crypto
mean reversion). Rather than firing single ideas at the gates, this program ran a
research phase: generate broadly, screen cheaply, pre-register the best with full
multiple-testing discipline. **No validation runs were performed in this program —
trial 3 awaits separate authorization.**

## Phase A — idea generation (agent desk)

10 theses generated through `trade-agents`' debate protocol (rules-mode
bull/bear challengers, 2 rounds each), persisted with full transcripts in
`phase-a-ideas.json`; human-readable batch in `IDEAS.md`. Pre-evidence conviction
prior was 0.5 (maximum ignorance); the bear won all 10 debates (synthesis
conviction 0.28) — correct behavior for hypotheses without numbers. Each thesis
records: edge hypothesis + why it might persist, data/horizon, trade frequency,
explicit kill criteria, and diversification vs the two killed classes.

The batch: PAIRS-1 (cointegrated pairs z-score MR — seeded leading candidate),
XMOM-1 (cross-sectional 12-1 momentum), FMOM-1 (factor momentum), SENT-1
(sentiment×price), TREND-VT (vol-targeted multi-asset trend), CARRY-1 (FX/futures
carry), TSMOM-CR (daily crypto time-series momentum), VOLPREM-1 (short vol premium
— sketch, needs options data), PEAD-1 (post-earnings drift — sketch, needs
earnings data), BAB-1 (betting against beta).

## Phase B — cheap screening (in-sample only, deliberately loose)

Minimal implementations in `scratch/` (research scratch — NOT strategy modules),
one in-sample backtest each through `trade-backtest`'s `BacktestEngine`
(2018-01-01..2026-09-25, t→t+1 fills, 5 bps/side equities / 25 bps/side crypto).
No gates, no walk-forward, no DSR — screening is allowed to be loose by design.
Full methodology, per-idea verdicts, and simplifications in `SCREENING.md`;
machine-readable results in `evidence/screening_results.json`.

**n_screened = 7.** VOLPREM-1 and PEAD-1 were sketches (no data); SENT-1 was
unscreenable (no point-in-time historical sentiment archive — none fabricated).
The 7 screened are the multiple-testing trials; see below.

| Rank | Idea | In-sample Sharpe | MaxDD | Trades | Verdict |
|---|---|---|---|---|---|
| 1 | TSMOM-CR | +0.798 | 20.1% | 166 | thesis matched; narrowest evidence (2 coins, 1 bull market) |
| 2 | TREND-VT | +0.485 | 10.6% | 523 | thesis matched; best risk profile |
| 3 | XMOM-1 | +0.413 | 25.3% | 1,275 | thesis matched; textbook momentum shape |
| 4 | CARRY-1 | +0.379 | 4.8% | 38 | partial (approximate carry measure; thin evidence) |
| 5 | BAB-1 | +0.106 | 14.2% | 14,995 | weak — premium doesn't survive monthly turnover |
| 6 | FMOM-1 | −0.097 | 29.8% | 58 | no |
| 7 | PAIRS-1 | −0.337 | 10.2% | 987 | no — and the leading candidate falls |

Notable: the seeded leading candidate (PAIRS-1) failed the screen. A first
screening run had shown +0.584 due to a specification bug (spread replayed in
log-space while the cointegration hedge ratio was estimated on raw prices);
correcting to the spec-consistent residual flipped it to −0.337. The process
caught its own error — that is the screening working, and the corrected number
is the one recorded. All equity results carry survivorship bias (current-
constituent universe); all Sharpes are in-sample with no multiple-testing
correction — that correction belongs to trial 3.

## Phase C — shortlist + pre-registration (this report's endpoint)

Selected, by combined metrics + rationale + diversification from the killed
classes:

1. **TREND-VT** — multi-asset vol-targeted trend (monthly, long/flat/short).
   Best risk profile in the batch (10.6% maxDD), 523 trades, crisis-alpha thesis
   intact. Structurally different from trial 1's single-asset daily breakout
   (cross-asset, vol-targeted, monthly) — honest flag: same trend family.
2. **TSMOM-CR** — daily crypto time-series momentum (long/flat). Best Sharpe
   (0.798) but narrowest evidence. Different mechanism and horizon from trial 2's
   5-minute mean reversion — honest flag: same instruments (BTC/ETH).

XMOM-1 (+0.413, 1,275 trades) was the close third; CARRY-1's carry measure was
too approximate and its 38 trades too thin to pre-register with a straight face.

Frozen specs (universes, signals, sizing, costs, walk-forward geometry — all
fixed before any validation data is touched):
- `docs/validation/trend-vt/PRE-REGISTRATION.md`
- `docs/validation/tsmom-cr/PRE-REGISTRATION.md`

## The honest trial count

**The future trial-3 DSR must use n_trials = 7** — the full screened batch — not
1 or 2. Screening 7 ideas and validating the best is 7 trials of multiple
testing. This is stated in both pre-registration files and will be enforced in
the validation harness. In-sample screening Sharpes above are the trial set.

## What the screening revealed about the stack

- `trade-pairs`' Engle-Granger OLS is estimated on raw prices — the screening
  caught a log-vs-raw specification mismatch against `trade-pairs/docs/
  METHODOLOGY.md`. Worth a cross-check pass on that engine's docs-vs-code
  consistency when convenient (no change made; out of scope).
- `trade-data-crypto` v0.2.0's new Binance.US provider was consumed cleanly by
  the TSMOM-CR screen (daily bars from 2019-09-17); the Phase-1 venue work is
  paying off directly.
- `trade-sentiment` has no historical archive — only live feeds. Any future
  sentiment strategy needs a point-in-time data solution first.
- `trade-factors` factor series were usable for FMOM-1 screening (58-trade
  result stands as screened).

## Hard stop

No validation runs, no gate evaluations, no releases, no registry entries.
Trial 3 (validating one or both pre-registered candidates through the overfit
gates with DSR n_trials=7) awaits Charlie's word.
