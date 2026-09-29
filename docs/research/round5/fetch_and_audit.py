#!/usr/bin/env python3
"""Round 5: fetch all candidate bars (cached) and run DataAuditorAgent.

Writes:
  bars.pkl        {symbol: [(date, open, high, low, close, volume), ...]}
  audit.json      DataAuditorAgent report
"""
import datetime as dt
import json
import os
import pickle
import sys

WS = os.path.expanduser("~/workspace/trade-suite")
for repo in ("trade-data-equities", "trade-agents"):
    p = os.path.join(WS, repo, "src")
    if p not in sys.path:
        sys.path.insert(0, p)

from trade_data_equities import EquitiesDataClient
from trade_data_equities.providers.yfinance import YFinanceProvider
from trade_data_equities.models import Timeframe
from trade_agents.data_audit import DataAuditorAgent

HERE = os.path.dirname(os.path.abspath(__file__))

SYMBOLS = [
    "SPY", "CPER", "TLT", "GLD",          # REGCOND-1
    "SHY", "IEF", "TIP", "HYG", "LQD", "MUB", "SGOV",   # rates/credit
    "USO", "DBA", "DBB", "UNG", "DBC", "SLV",           # commodities
    "UUP", "FXE", "FXY", "FXB", "FXC",                  # currencies
    "USMV", "SPLV", "QUAL", "EFA", "EEM",               # equity factors/intl
    "SVXY", "VXX", "^VIX",                              # vol
    "AGG",                                            # benchmark
]
WARMUP_START = dt.date(2015, 1, 1)
END = dt.date(2026, 9, 29)

# Known inception dates (for survivorship screening; pre-2015 marked 2000-01-01 sentinel = "before window")
INCEPTION = {
    "SGOV": dt.date(2020, 5, 26),
    "USMV": dt.date(2011, 10, 18),
    "SPLV": dt.date(2011, 5, 5),
    "QUAL": dt.date(2013, 7, 12),
    "SVXY": dt.date(2011, 10, 3),
    "VXX": dt.date(2009, 1, 30),
    "MUB": dt.date(2007, 9, 7),
    "DBC": dt.date(2006, 2, 3),
    "SLV": dt.date(2006, 4, 21),
    "EFA": dt.date(2001, 8, 14),
    "EEM": dt.date(2003, 4, 7),
    "CPER": dt.date(2010, 12, 15),
    "UNG": dt.date(2007, 4, 18),
    "DBB": dt.date(2007, 1, 5),
    "DBA": dt.date(2007, 1, 5),
    "FXE": dt.date(2005, 12, 12),
    "FXY": dt.date(2007, 2, 12),
    "FXB": dt.date(2006, 6, 21),
    "FXC": dt.date(2006, 6, 21),
    "UUP": dt.date(2007, 2, 20),
    "USO": dt.date(2006, 4, 10),
    "HYG": dt.date(2007, 4, 4),
    "LQD": dt.date(2002, 7, 22),
    "TIP": dt.date(2003, 12, 4),
    "IEF": dt.date(2002, 7, 22),
    "TLT": dt.date(2002, 7, 22),
    "SHY": dt.date(2002, 7, 22),
    "SPY": dt.date(1993, 1, 22),
    "GLD": dt.date(2004, 11, 18),
    "AGG": dt.date(2003, 9, 22),
    "^VIX": dt.date(1990, 1, 2),
}


def main():
    client = EquitiesDataClient(YFinanceProvider())
    bars = {}
    for sym in SYMBOLS:
        try:
            bl = client.get_bars(sym, Timeframe.DAILY, WARMUP_START, END,
                                 adjusted=True, use_cache=True)
            rows = []
            for b in bl:
                d = b.timestamp.date() if hasattr(b.timestamp, "date") else b.timestamp
                rows.append((d, b.open, b.high, b.low, b.close,
                             getattr(b, "volume", None)))
            bars[sym] = rows
            print(f"{sym}: {len(rows)} bars", flush=True)
        except Exception as e:
            print(f"{sym}: FETCH FAILED: {type(e).__name__}: {e}", flush=True)
            bars[sym] = []
    with open(os.path.join(HERE, "bars.pkl"), "wb") as f:
        pickle.dump(bars, f)
    print("bars.pkl written", flush=True)

    # --- data audit ---
    class SimpleProvider:
        def __init__(self, bars):
            self._bars = bars
        def symbols(self):
            return list(self._bars)
        def get_bars(self, symbol):
            out = []
            for (d, o, h, l, c, v) in self._bars.get(symbol, []):
                out.append(SimpleBar(d, c, v))
            return out

    class SimpleBar:
        def __init__(self, d, c, v):
            self.timestamp = d
            self.close = c
            self.volume = v

    auditor = DataAuditorAgent()
    membership = {s: {"first_tradable": INCEPTION.get(s, dt.date(2000, 1, 1)).isoformat()}
                  for s in SYMBOLS}
    report = auditor.audit(SimpleProvider(bars), universe=SYMBOLS,
                           membership=membership)
    with open(os.path.join(HERE, "audit.json"), "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"quarantined: {report['n_quarantined']}", flush=True)
    for q in report["quarantined"]:
        print(" QUARANTINED:", q["symbol"], q["reasons"][:2], flush=True)
    for s in SYMBOLS:
        ps = report["symbols"][s]
        if not ps["quarantined"]:
            fails = [k for k, v in ps["checks"].items() if v["status"] == "unverifiable"]
            if fails:
                print(f" note {s}: unverifiable checks {fails}", flush=True)
    print("audit.json written", flush=True)


if __name__ == "__main__":
    main()
