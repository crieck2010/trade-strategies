"""RESEARCH SCRATCH — Phase B (round 2) data pull (2026-09-26).

Pulls the Track-2 idea data into docs/research/round2/evidence/panel/ as
per-ticker CSVs (date,o,h,l,c,v):

  panel/{GLD,TLT,TIP,SPY,CPER}.csv   yfinance daily, split/div adjusted

These five ETFs cover both screenable Track-2 ideas:
  - RVBOND-1: GLD, TLT, TIP (gold / long bond / TIPS real-yield proxy)
  - REGCOND-1: CPER (copper proxy), GLD (gold) for the trade-macro
    copper:gold regime; SPY, TLT for the allocation legs

BASIS-1 (Kraken dated futures) is NOT fetched: the futures depth check
showed only two quarterly BTC contracts listed and the 3m contract opened
2026-09-25 — no historical series exists. See scratch/basis_1.py.

Track-1 (sentiment x price): no sentiment history exists before deployment
(archive backfill investigation, Phase 0). No proxy was fabricated. See
scratch/track1_deferral.py.

Track-3 (vol premium): sketches only; no options-chain data. Not fetched.

Run:  python3 docs/research/round2/scratch/fetch_panel2.py
"""

from __future__ import annotations

import csv
import os
import sys
import time

sys.path.insert(0, "/home/hatch/workspace/trade-suite/trade-data-equities/src")

from datetime import date as _date

from trade_data_equities import EquitiesDataClient
from trade_data_equities.providers.yfinance import YFinanceProvider
from trade_data_equities.models import Timeframe as EqTF

EVID = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "evidence")
PANEL = os.path.join(EVID, "panel")

ETFS = ["GLD", "TLT", "TIP", "SPY", "CPER"]
START, END = _date(2015, 1, 1), _date(2026, 9, 26)


def main() -> int:
    t0 = time.time()
    client = EquitiesDataClient(YFinanceProvider())
    for t in ETFS:
        out = os.path.join(PANEL, f"{t}.csv")
        if os.path.exists(out):
            print(f"[fetch2] {t}: cached", flush=True)
            continue
        bars = client.get_bars(t, EqTF.DAILY, START, END, adjusted=True)
        rows = [(b.timestamp.strftime("%Y-%m-%d"),
                 f"{b.open:.6f}", f"{b.high:.6f}", f"{b.low:.6f}",
                 f"{b.close:.6f}", f"{b.volume:.1f}") for b in bars]
        os.makedirs(PANEL, exist_ok=True)
        with open(out, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["date", "o", "h", "l", "c", "v"])
            w.writerows(rows)
        print(f"[fetch2] {t}: {len(rows)} bars "
              f"({rows[0][0]}..{rows[-1][0]})", flush=True)
    print(f"[fetch2] done in {time.time()-t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
