# Round 5 research report (2026-09-28)

**Goal:** find Tier-1-validated strategies #2 and #3 for the paper book.
**Result: 0 clean validations out of 10 tested.** One 6/6 pass carries a
degeneracy flag (see below); it is not recommended for the book.

## Batch accounting

| Stage | n |
|---|---|
| Hypotheses (23 carried + 7 new) | 30 |
| Triage-screened (structural only, no performance ranking) | 27 |
| Parked data-pending (no free keyless source) | 3 |
| Admitted to validation | 10 |
| Tested (pre-registered before testing, DSR n=27) | 10 |
| Validated | 1* |
| Invalidated | 9 |

\* idea-0010 passes 6/6 on the letter but is flagged degenerate (below).

## Scorecard (all six Tier-1 gates)

| Candidate | Sharpe | maxDD | DSR | Excess bmk | Sortino | Cost-speed | Verdict |
|---|---|---|---|---|---|---|---|
| hyg-lqd-spread (0008) | 0.36 ✓ | −21.8% ✓ | 0.00 ✗ | +3.2%/yr ✓ | 0.55 ✗ | ✓ | invalidated |
| tlt-shy-slope (0009) | −0.39 ✗ | −36.5% ✗ | 0.00 ✗ | −2.9%/yr ✗ | −0.40 ✗ | ✗ | invalidated |
| short-carry-ladder (0010) | 20.5 ✓ | −0.02% ✓ | 1.00 ✓ | +1.1%/yr ✓ | 195.7 ✓ | ✓ | validated* |
| svxy-harvest (0015) | 0.71 ✓ | −29.1% ✗ | 0.00 ✗ | +4.6%/yr ✓ | 0.57 ✗ | ✓ | invalidated |
| vix-dip-buy (0016) | 0.46 ✓ | −33.7% ✗ | 0.00 ✗ | −13.8%/yr ✗ | 0.27 ✗ | ✗ | invalidated |
| uso-momentum (0021) | 0.63 ✓ | −42.2% ✗ | 0.00 ✗ | −3.9%/yr ✗ | 0.74 ✗ | ✓ | invalidated |
| spy-turn-of-month (0026) | 0.84 ✓ | −13.6% ✓ | 0.00 ✗ | −6.9%/yr ✗ | 1.34 ✓ | ✗ | invalidated |
| fx-momentum (0031) | −0.05 ✗ | −9.0% ✓ | 0.00 ✗ | −3.7%/yr ✗ | 0.00 ✗ | ✗ | invalidated |
| gtaa-5 (0032) | 1.04 ✓ | −23.2% ✓ | 0.00 ✗ | +1.1%/yr ✓ | 1.06 ✓ | ✓ | invalidated |
| efa-eem-rotation (0034) | 0.35 ✓ | −33.4% ✗ | 0.00 ✗ | −4.6%/yr ✗ | 0.52 ✗ | ✓ | invalidated |

Full evidence per candidate: `docs/validation/<slug>/evidence.json`.
Harness: `docs/research/round5/validate.py` (frozen signal implementations
imported from `triage.py`; walk-forward 520/130/130/5; t+1-open fills; 5 bps/side).

## What killed them (structural reasons)

1. **DSR with n=27 killed 8 of 10.** The trial set's in-sample Sharpes reach
   +0.66…+0.71 (several candidates), putting the expected Sharpe under the
   null near 1.3. This is the multiple-testing honesty mechanism working as
   designed — the same discipline that validated REGCOND-1 (DSR 1.000 at n=2
   in trial 4). The closest call was **gtaa-5**: 5/6 with OOS Sharpe 1.04,
   maxDD −23.2%, +1.05%/yr over 60/40 — real numbers, but DSR 0.00 at n=27.
2. **The benchmark gate killed 5** (0009, 0016, 0021, 0026, 0034) — the same
   regime-punishment of diversifiers against 2017–2026 buy-and-hold that
   round 4 documented. Turn-of-month is the sharpest case: Sharpe 0.84,
   Sortino 1.34, maxDD −13.6% — but −6.9%/yr vs SPY buy-and-hold.
3. **The 2022 hiking-cycle graveyard** claimed tlt-shy-slope (0/6, maxDD
   −36.5%) — slow rates timing, same as round 4's victims.
4. **Vol-spike gap risk** killed svxy-harvest (maxDD −29.1%; the monthly
   rebalance cannot exit intraday) and vix-dip-buy (maxDD −33.7%, and
   −13.8%/yr vs SPY from sitting in SHY through the bull market).
5. **Cost-speed killed the switch-heavy** (0016: drag 0.105 > budget 0.068;
   0026: drag 0.415 > budget 0.302) — Carver's gate doing exactly its job.
6. **FX momentum is dead** in this window (Sharpe −0.05).

## The flagged 6/6 pass: short-carry-ladder (idea-0010)

Passes all six gates on the letter — but **holds SGOV 95.8% of the time**.
Its Sharpe of 20.5 / Sortino of 195.7 are an artifact of near-zero
T-bill-ETF volatility (backward-ratio-adjusted prices smooth the monthly
distributions into daily appreciation), not a tradeable edge. The +1.08%/yr
over SHY is the SGOV–SHY yield spread during the inverted-curve regime,
i.e. **cash management, not a strategy**. It adds nothing to the book (the
book already uses SHY as the cash proxy). **Not recommended for paper
enrollment.** Journal status left at `tested` (not adopted); the call is
Charlie's.

**Framework finding:** Tier-1 has no economic-meaningfulness floor — a
near-zero-volatility cash proxy can pass all six gates on Sharpe/DSR
arithmetic. A future amendment could add a minimum-volatility or
minimum-absolute-excess gate; not adopted unilaterally here (frozen spec).

## Standing rules honored

- No gates lowered; all six applied as frozen.
- Free/keyless data only; no purchases; no options data.
- All 10 pre-registered BEFORE testing (`docs/validation/<slug>/PRE-REGISTRATION.md`);
  frozen signal implementations; no AI optimization after OOS.
- DSR n=27 = all performance-screened hypotheses (the 3 data-parked ideas
  never had performance observed → zero trials, per the pre-reg honesty section).
- Costs 5 bps/side throughout. Language: validated / invalidated / discarded.
- Nothing enrolled in lifecycle/paper (per-strategy approval is Charlie's call).
