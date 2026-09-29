# Round 5 triage report (2026-09-28)

**Batch:** 30 hypotheses — 23 carried from round 4 (idea-0007→idea-0031 minus
the 3 tested/discarded: 0006, 0020, 0023) + 7 new (idea-0032→idea-0038) in
families rounds 3–4 didn't exhaust (multi-asset absolute momentum, dual
momentum, international rotation, precious-metals cross-section,
inflation-driven commodity tilts).

**Method** (`triage.py`, deterministic): for each hypothesis, implement the
frozen signal literally (monthly signals, t+1-open fills, 5 bps/side),
compute the full-window net-of-costs return stream, and apply structural
screens only — **no performance ranking** (no Sharpe/Sortino/return is
computed before the admission decision):
1. Data-availability (audit in `audit.json`).
2. Occam complexity C ≤ 5 (per trade-agents `docs/design/OCCAMS_DESK.md`).
3. Structural return correlation vs the book (REGCOND-1) ρ ≤ 0.60.
4. Pairwise structural correlation ρ ≤ 0.60 (keep the lower-C representative
   on ties).

## Data audit findings (`audit.json`, `fetch_and_audit.py`)

- All 31 tickers fetched via yfinance (keyless), 2015-01-01 → 2026-09-28.
- The auditor's coverage-gap check (GAP_TOTAL_TOLERANCE=5) is **miscalibrated
  for 11.7-year windows**: all 111 "missing" sessions per symbol were verified
  as NYSE holidays (list in the audit record). Not a data defect — a check
  calibration limitation, recorded here.
- SGOV's "stale print" findings (11 consecutive identical closes) carry **real
  volume** (16k–24k shares) — pinned T-bill-ETF pricing in 2020, not a stale
  feed. Not a defect; the ≥10-identical-closes rule is oversensitive for
  ultra-low-volatility fixed-income ETFs.
- **VXX ticker history starts 2018-01-25** (Series B; the Series-A ETN matured
  Jan 2019). Idea-0017's signal history starts there — recorded limitation.
- Corporate-action adjustment is backward-ratio (`adjusted=True`); no
  survivorship correction (standing limitation).

## Screen outcomes (machine-readable: `triage.json`)

**Parked as data-pending (no free keyless source, not assumed):**
- idea-0007, idea-0030 — historical futures curve for roll-yield sorts
  (trade-data-futures' yfinance provider only serves continuous front-month;
  no historical curve).
- idea-0025 — intraday 30-minute bars 2017–2026.

**Cut by hard ρ > 0.60 vs REGCOND-1:**
- idea-0035 (GLD 10m trend, ρ=0.647), idea-0037 (SLV/GLD rotation, ρ=0.605).

**Cut by prospective cost-speed failure (documented math, not a hunch):**
- idea-0024 (SPY overnight), idea-0027 (GLD overnight): ~252 round trips/yr ×
  10 bps / ~0.10 overnight vol ≈ **2.5 Sharpe units of drag** vs budget
  gross_sharpe/3 — would need gross Sharpe ≈ 7.5. (The validation trial set
  later confirmed both are outright negative net of costs: −1.18 / −0.80.)

**Cut as redundant cousins (pairwise ρ > 0.60, one representative kept):**
- Defensive-equity cluster {0012, 0013, 0014, 0033, 0034} (pairwise up to
  0.815): kept **idea-0034** (EFA/EEM rotation, C=2, international diversifier).
- Credit {0019 vs 0008, ρ=0.675}: kept **idea-0008** (C=2).
- idea-0029 vs 0008 (ρ=0.627): kept **idea-0008**.
- Rates {0011 vs 0009, ρ=0.685}: kept **idea-0009** (lower book correlation).
- Vol {0017 vs 0016, ρ=0.628}: kept **idea-0016** (0017 is C=5 with short history).
- FX {0022 vs 0031}: kept **idea-0031** (cross-sectional representative).
- Commodity cluster {0021, 0028, 0036, 0038} (pairwise up to 0.732): kept
  **idea-0021** (USO absolute momentum, C=2, ρ=0.036 vs book — best diversifier).

**Parked (paired variant):** idea-0018 (40-bar wait improvement on 0015) —
testable only if idea-0015 validates.

**Admitted (10):** idea-0008, 0009, 0010, 0015, 0016, 0021, 0026, 0031, 0032, 0034.
All pairwise ρ ≤ 0.60 among admitted; all ρ ≤ 0.60 vs REGCOND-1; all C ≤ 3.

**Implementation bug caught and fixed during triage:** the trailing-drawdown
helpers for idea-0014/0018 initially measured drawdown against the all-time
peak instead of the trailing 20-day window (made 0018 ≈ 100% SHY, ρ≈0 vs its
0015 base). Fixed to proper trailing-window peak-to-trough; 0018 now behaves
as specified (ρ=0.218, matching base). Neither was admitted, so no admission
decision was affected — recorded for the log.
