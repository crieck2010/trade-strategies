# Invalid run — 2026-09-26, incomplete data (superseded)

**Status:** INVALID — outputs superseded by the clean re-run the same day.
This directory holds the post-mortem only; the invalid run's
`evidence.json` / `report.md` were overwritten by the valid re-run and are
not preserved (the re-run's files are the record).

## What happened

Two attempts preceded the valid run:

1. **Attempt A (interrupted, no outputs):** the data pull (271 tickers ×
   ~11y via yfinance) was ~65% complete when the VM restarted, killing the
   background process and wiping `/tmp` (including its log). No
   `evidence.json` / `report.md` was produced — nothing to archive beyond
   this note. Raw bars already fetched survived in `evidence/cache/`
   (persistent workspace) and were reused.

2. **Attempt B (completed, INVALID — data error):** the re-run after the
   restart completed with EXIT=0, but the VM restart had also wiped the
   `pip install --break-system-packages yfinance` from attempt A (system
   site-packages did not persist the restart). Result: the 7 tickers not
   yet cached (WST, WY, XOM, XYL, YUM, ZTS) plus `^IRX` failed with
   `ProviderError: yfinance is not installed` and were recorded as
   ineligible / missing. Consequences vs the frozen spec:
   - universe traded: 255 tradeable symbols instead of 261 (XOM is a large
     name; its absence is material);
   - benchmark: `^IRX` unfetchable → the pre-registered 0%-cash fallback
     was used (mechanical, but triggered by an environment defect, not by
     genuine ^IRX unavailability).
   - Its gate values (for the record): DSR 0.0003 FAIL, median OOS Sharpe
     0.7341 FAIL, maxDD −0.2598 FAIL, worst-regime Sharpe 0.1755 PASS,
     excess vs 0%-cash 0.0654 PASS, Sortino 0.5908 FAIL, Calmar 0.2341
     FAIL → verdict KILL. 1,231 trades, final equity $169,523.89.

## Root cause

Environment, not harness: the restart cleared the non-persistent system
pip install of `yfinance`, and the harness's per-ticker failure handling
(correctly) degraded to ineligible/missing instead of aborting.

## Fix

Reinstalled `yfinance` (1.7.0), verified `XOM` and `^IRX` fetch cleanly
(^IRX: 2,940 bars, last close 4.07%), then re-ran the identical harness.
All 271 tickers + `^IRX` fetched; benchmark = `^IRX` forward-filled
(2.88% annualized over OOS) — the fallback was not needed. The valid
run's verdict is independently KILL (5 of 7 gates fail), so the invalid
run's incompleteness did not flip the outcome, but the valid run is the
only one that counts.

## Lesson

Pin the `yfinance` install so it survives restarts (venv under
`~/workspace/` or a requirements install), and add a pre-flight check in
future validation harnesses: fail fast if a fetch dependency is missing
rather than degrading ticker-by-ticker. (Noted for the parent; the frozen
XMOM-1 harness itself is unchanged.)
