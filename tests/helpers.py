"""Shared test helpers: synthetic bars and strategy feeding."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

T0 = datetime(2026, 1, 5, tzinfo=timezone.utc)


def make_bars(closes, symbol="T", volume=1000.0, spread=1.0, start=T0, opens=None):
    """Dict bars: high=close+spread/2, low=close-spread/2.

    ``opens`` defaults to the previous close (gappy); pass ``opens=closes``
    for gapless bars valid under strict OHLC checks.
    """
    bars = []
    prev = closes[0]
    for i, c in enumerate(closes):
        bars.append({
            "symbol": symbol,
            "timestamp": start + timedelta(days=i),
            "open": prev if opens is None else opens[i],
            "high": c + spread / 2, "low": c - spread / 2,
            "close": c, "volume": volume,
        })
        prev = c
    return bars


def feed(strategy, bars):
    """Feed bars grouped by timestamp; return all signals in order."""
    by_ts = {}
    for b in bars:
        by_ts.setdefault(b["timestamp"], {})[b["symbol"]] = b
    signals = []
    for ts in sorted(by_ts):
        signals.extend(strategy.on_bar(ts, by_ts[ts]))
    return signals


def actions(signals):
    return [(s.symbol, s.action.name) for s in signals]
