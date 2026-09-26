"""RESEARCH SCRATCH — Phase B data pull (2026-09-26).

Pulls everything the six screenable ideas need and persists it under
docs/research/evidence/panel/ as per-ticker CSVs (date,o,h,l,c,v):

  panel/eq/{T}.csv        271 cached US large caps, yfinance daily, split/div adjusted
  panel/etf/{T}.csv       SPY TLT GLD USO EFA VNQ (5 need network; SPY cached)
  panel/fut/{ROOT}.csv    6E 6J 6B front-month continuous (yfinance =F feed)
  panel/fx/{T}.csv        spot FX for carry: EURUSD=X, JPY=X, GBPUSD=X
  panel/crypto/{S}.csv    BTC/USD, ETH/USD daily (Binance.US keyless)

Run:  PYTHONPATH=scratch python3 docs/research/scratch/fetch_panel.py
"""

from __future__ import annotations

import csv
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common  # noqa: E402  (bootstraps all trade-* src dirs)

from trade_data_equities import EquitiesDataClient
from trade_data_equities.providers.yfinance import YFinanceProvider
from trade_data_equities.models import Timeframe as EqTF

EVID = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "evidence")
PANEL = os.path.join(EVID, "panel")

from datetime import date as _d
EQ_START, EQ_END = _d(2015, 1, 1), _d(2026, 9, 26)  # matches warm disk cache
CR_START, CR_END = "2018-01-01", "2026-09-26"

ETFS = ["SPY", "TLT", "GLD", "USO", "EFA", "VNQ"]
FX_SPOT = {"EURUSD=X": "EUR", "JPY=X": "JPY", "GBPUSD=X": "GBP"}  # USDJPY for 6J
FUT_ROOTS = ["6E", "6J", "6B"]
CRYPTO = ["BTC/USD", "ETH/USD"]


def cached_tickers() -> list[str]:
    # Committed research universe (reproducible). Falls back to the
    # ephemeral /tmp list only if the committed file is missing.
    uni = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "..", "evidence", "universe.txt")
    if os.path.isfile(uni):
        with open(uni) as fh:
            return [ln.strip() for ln in fh
                    if ln.strip() and not ln.startswith("#")]
    path = "/tmp/cached_tickers.txt"
    with open(path) as fh:
        lines = fh.read().split()
    return [t for t in lines if t != lines[0] or not t.isdigit()]


def write_csv(path: str, rows: list[tuple]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "o", "h", "l", "c", "v"])
        w.writerows(rows)


def eq_rows(bars) -> list[tuple]:
    return [(b.timestamp.strftime("%Y-%m-%d"),
             f"{b.open:.6f}", f"{b.high:.6f}", f"{b.low:.6f}",
             f"{b.close:.6f}", f"{b.volume:.1f}") for b in bars]


def main() -> int:
    t0 = time.time()
    client = EquitiesDataClient(YFinanceProvider())

    tickers = cached_tickers()
    print(f"[fetch] {len(tickers)} cached equity tickers", flush=True)
    n_eq = 0
    for t in tickers:
        out = os.path.join(PANEL, "eq", f"{t}.csv")
        if os.path.exists(out):
            n_eq += 1
            continue
        try:
            bars = client.get_bars(t, EqTF.DAILY, EQ_START, EQ_END, adjusted=True)
        except Exception as exc:  # noqa: BLE001 - one bad ticker must not stop the pull
            print(f"[fetch] SKIP {t}: {exc}", flush=True)
            continue
        if len(bars) < 500:
            print(f"[fetch] SKIP {t}: only {len(bars)} bars", flush=True)
            continue
        write_csv(out, eq_rows(bars))
        n_eq += 1
    print(f"[fetch] equities: {n_eq} files ({time.time()-t0:.0f}s)", flush=True)

    for t in ETFS:
        out = os.path.join(PANEL, "etf", f"{t}.csv")
        if os.path.exists(out):
            continue
        bars = client.get_bars(t, EqTF.DAILY, EQ_START, EQ_END, adjusted=True)
        write_csv(out, eq_rows(bars))
        print(f"[fetch] etf {t}: {len(bars)} bars", flush=True)

    for yf, _ccy in FX_SPOT.items():
        out = os.path.join(PANEL, "fx", f"{yf}.csv")
        if os.path.exists(out):
            continue
        bars = client.get_bars(yf, EqTF.DAILY, EQ_START, EQ_END, adjusted=False)
        write_csv(out, eq_rows(bars))
        print(f"[fetch] fx {yf}: {len(bars)} bars", flush=True)

    # -- futures: front-month continuous via yfinance =F feed -----------------
    from trade_data_futures import FuturesDataClient
    from trade_data_futures.providers.yfinance import YFinanceFuturesProvider
    from trade_data_futures.models import Timeframe as FutTF
    from datetime import date
    fclient = FuturesDataClient(YFinanceFuturesProvider())
    for root in FUT_ROOTS:
        out = os.path.join(PANEL, "fut", f"{root}.csv")
        if os.path.exists(out):
            continue
        bars = fclient.get_continuous(
            root, FutTF.DAILY, date(2015, 1, 1), date(2026, 9, 26))
        write_csv(out, [(b.timestamp.strftime("%Y-%m-%d"),
                         f"{b.open:.6f}", f"{b.high:.6f}", f"{b.low:.6f}",
                         f"{b.close:.6f}", f"{b.volume:.1f}") for b in bars])
        print(f"[fetch] fut {root}: {len(bars)} bars", flush=True)

    # -- crypto: Binance.US daily -------------------------------------------
    from trade_data_crypto import BinanceUSPublicProvider, Timeframe as CrTF
    from datetime import date as _date
    cprov = BinanceUSPublicProvider()
    for s in CRYPTO:
        out = os.path.join(PANEL, "crypto", s.replace("/", "_") + ".csv")
        if os.path.exists(out):
            continue
        bars = cprov.get_bars(s, CrTF.D1, start=_date(2018, 1, 1),
                              end=_date(2026, 9, 26))
        write_csv(out, [(b.timestamp.strftime("%Y-%m-%d"),
                         f"{b.open:.6f}", f"{b.high:.6f}", f"{b.low:.6f}",
                         f"{b.close:.6f}", f"{b.volume:.4f}") for b in bars])
        print(f"[fetch] crypto {s}: {len(bars)} bars "
              f"({bars[0].timestamp.date()}..{bars[-1].timestamp.date()})", flush=True)

    print(f"[fetch] done in {time.time()-t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
