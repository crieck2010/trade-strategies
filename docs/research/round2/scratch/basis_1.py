"""RESEARCH SCRATCH — BASIS-1: crypto dated-future basis dislocation.

NOT a strategy module. Round-2 Phase B screening note (2026-09-26).

STATUS: UNSCREENABLE — no dated-future history exists on any keyless
source in the stack. This file exists so the reason is on the record;
it was not screened, and no numbers were fabricated.

Thesis (recap): BTC spot vs 3-month dated future, annualized basis z vs
a 90-day rolling mean; fade |z| > 2 delta-neutral. The design needs a
multi-year daily series of a 3-month-dated BTC future.

Depth check (2026-09-26, keyless Kraken Futures API):
  - GET /derivatives/api/v3/tickers lists 300 tickers, but only TWO dated
    BTC contracts: FI_XBTUSD_261030 and FI_XBTUSD_261225 (quarterlies).
  - /derivatives/api/v3/instruments shows FI_XBTUSD_261030
    (the 3m contract closest to the thesis's tenor) with
    openingDate 2026-09-25T15:00:59Z — it has ~1 day of history.
  - Expired contracts are delisted from the API; there is no archive of
    expired dated contracts reachable keyless. Each quarterly exists only
    for its own ~3-month life, so no 90-day rolling baseline of a
    constant-tenor 3m future can be constructed — the very baseline the
    thesis requires.
  - Kraken spot (trade-data-crypto KrakenPublicProvider) has daily candles
    but pages 720/request and is SPOT only — no futures basis on it.
  - Binance.US (spot only) has no dated futures at all.

The 90-day rolling z-score baseline is mathematically impossible here:
the longest 3m-dated BTC future series obtainable is one day long. Using
the perpetual (PI_XBTUSD) funding-rate basis instead would be a different
strategy than the one debated (dated-future basis dislocation); screening
that and calling it BASIS-1 would mislabel the thesis. Not done.

Revisit conditions (honest): a venue with keyless multi-year dated-future
history (e.g., CME BTC futures continuous history via a data vendor, or
a free archive of expired quarterly series) would make this screenable.
No data purchase is authorized in this phase.

IDEA_ID = "BASIS-1" — recorded as unscreenable, n_screened does NOT count it.
"""

IDEA_ID = "BASIS-1"
STATUS = "UNSCREENABLE"
REASON = ("Kraken Futures lists only 2 quarterly BTC contracts; the 3m "
          "contract FI_XBTUSD_261030 opened 2026-09-25 (~1 day of history); "
          "expired contracts are not archived keyless. A 90-day rolling "
          "baseline of constant-tenor 3m basis cannot be constructed.")
