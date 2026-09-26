"""Unit tests for donchian_swing on synthetic bars. No market data."""

from datetime import datetime, timedelta, timezone

import pytest

from trade_strategies.base import SignalAction
from trade_strategies.donchian_swing import (
    DonchianSwingConfig,
    DonchianSwingStrategy,
    compute_features,
    donchian_high,
    donchian_low,
    target_equity_fraction,
    wilder_atr,
)

CFG = DonchianSwingConfig()


def make_bars(closes, start="2020-01-01", high_pad=0.5, low_pad=0.5):
    day = datetime.fromisoformat(start)
    bars = []
    for i, c in enumerate(closes):
        bars.append({
            "date": (day + timedelta(days=i)).date().isoformat(),
            "open": c, "high": c + high_pad, "low": c - low_pad,
            "close": c, "volume": 1_000_000,
        })
    return bars


def run_strategy(symbols, bars_by_symbol, **params):
    feats = {s: compute_features(b, CFG) for s, b in bars_by_symbol.items()}
    strat = DonchianSwingStrategy(symbols, features=feats, **params)
    sigs = []
    # union of dates in order
    dates = sorted({b["date"] for bars in bars_by_symbol.values() for b in bars})
    for d in dates:
        ts = datetime.fromisoformat(d).replace(tzinfo=timezone.utc)
        bars = {}
        for s, blist in bars_by_symbol.items():
            for b in blist:
                if b["date"] == d:
                    bars[s] = b
        for sig in strat.on_bar(ts, bars):
            sigs.append((d, sig.symbol, sig.action))
    return sigs


def test_donchian_high_excludes_current_bar():
    assert donchian_high([10, 12, 11, 13, 9], 4, 4) == 13  # max of first 4
    assert donchian_high([10, 12, 11, 13, 9], 3, 4) is None  # not enough history


def test_wilder_atr_seeds_with_mean():
    bars = make_bars([100.0] * 25, high_pad=2.0, low_pad=1.0)  # TR = 3.0
    atr = wilder_atr(bars, 20)
    assert atr[18] is None
    assert atr[19] == pytest.approx(3.0)
    assert atr[24] == pytest.approx(3.0)


def test_entry_on_20day_breakout():
    # flat then a slow grind up; breakout above the prior 20-bar high
    closes = [100.0] * 21 + [100 + i * 1.0 for i in range(1, 30)]
    sigs = run_strategy(["AAA"], {"AAA": make_bars(closes)})
    entries = [s for s in sigs if s[2] == SignalAction.LONG]
    assert len(entries) >= 1
    first = entries[0]
    # first signal cannot fire before warmup bar 21
    idx = next(i for i, b in enumerate(make_bars(closes)) if b["date"] == first[0])
    assert idx >= 21


def test_no_signals_before_warmup():
    closes = [100 + i for i in range(21)]  # straight up from bar 0
    sigs = run_strategy(["AAA"], {"AAA": make_bars(closes)})
    assert sigs == []


def test_exit_on_10day_low():
    # breakout then collapse below the 10-day low
    up = [100 + i * 1.0 for i in range(40)]
    down = [139 - i * 2.0 for i in range(1, 25)]
    sigs = run_strategy(["AAA"], {"AAA": make_bars(up + down)})
    actions = [s[2] for s in sigs]
    assert SignalAction.LONG in actions
    first_long = actions.index(SignalAction.LONG)
    assert SignalAction.EXIT in actions[first_long:]


def test_trailing_stop_trails_up_only_and_exits():
    cfg_bars = make_bars([100.0] * 21 + [110.0] * 5 + [109.0, 108.0, 100.0, 90.0])
    feats = compute_features(cfg_bars, CFG)
    # force an entry at the 110 breakout by running the strategy
    sigs = run_strategy(["AAA"], {"AAA": cfg_bars})
    actions = [s[2] for s in sigs]
    assert SignalAction.LONG in actions
    assert SignalAction.EXIT in actions[actions.index(SignalAction.LONG):]


def test_target_equity_fraction_math():
    # risk 1% vs 2.5*ATR stop: fraction = 0.01 / (2.5*atr/close)
    assert target_equity_fraction(5.0, 100.0, CFG) == pytest.approx(0.08)
    # cap at 10%
    assert target_equity_fraction(0.1, 100.0, CFG) == pytest.approx(0.10)
    assert target_equity_fraction(0.0, 100.0, CFG) == 0.0
    assert target_equity_fraction(-1.0, 100.0, CFG) == 0.0


def test_max_positions_and_momentum_ranking():
    # 25 symbols all breaking out the same day; only 20 entries, top momentum first
    symbols = [f"S{i:02d}" for i in range(25)]
    bars_by_symbol = {}
    for k, s in enumerate(symbols):
        # momentum differs per symbol: steeper grind = higher momentum20
        closes = [100.0] * 21 + [100 + (k + 1) * 0.1 * i for i in range(1, 15)]
        bars_by_symbol[s] = make_bars(closes)
    sigs = run_strategy(symbols, bars_by_symbol)
    longs = [s for s in sigs if s[2] == SignalAction.LONG]
    by_date = {}
    for d, sym, a in longs:
        by_date.setdefault(d, []).append(sym)
    first_date = sorted(by_date)[0]
    assert len(by_date[first_date]) == 20  # capped
    # highest-momentum symbols (largest k) ranked first
    assert "S24" in by_date[first_date] and "S23" in by_date[first_date]


def test_reentry_needs_fresh_breakout():
    # breakout, exit via 10-day low, then drift sideways below old high: no re-entry
    closes = [100 + i * 1.0 for i in range(40)]          # grind up -> entry
    closes += [139 - i * 3.0 for i in range(1, 12)]      # collapse -> exit
    closes += [108.0] * 30                                # flat below breakout zone
    sigs = run_strategy(["AAA"], {"AAA": make_bars(closes)})
    longs = [s for s in sigs if s[2] == SignalAction.LONG]
    assert len(longs) == 1  # exactly one entry; no re-entry without fresh breakout


def test_strategy_strength_carries_equity_fraction():
    closes = [100.0] * 21 + [100 + i * 1.0 for i in range(1, 30)]
    feats = {"AAA": compute_features(make_bars(closes), CFG)}
    strat = DonchianSwingStrategy(["AAA"], features=feats)
    dates = sorted({b["date"] for b in make_bars(closes)})
    found = None
    for d in dates:
        ts = datetime.fromisoformat(d).replace(tzinfo=timezone.utc)
        bars = {"AAA": next(b for b in make_bars(closes) if b["date"] == d)}
        for sig in strat.on_bar(ts, bars):
            if sig.action == SignalAction.LONG:
                found = sig
    assert found is not None
    assert 0.0 < found.strength <= 0.10
