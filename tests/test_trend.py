"""Trend-family strategy tests."""

from __future__ import annotations

from helpers import actions, feed, make_bars

from trade_strategies.trend import (
    DonchianBreakout,
    EMACrossover,
    MACDTrend,
    SMACrossover,
    Supertrend,
)


def test_sma_crossover_signals():
    strat = SMACrossover(["T"], fast=2, slow=3)
    closes = [1, 2, 3, 2, 1, 2, 3, 4]
    sigs = feed(strat, make_bars(closes))
    # The first cross-up happens inside the warmup window; the observable
    # edges are EXIT at idx4 (1.5 < 2.0) and LONG at idx6.
    assert [s.action.name for s in sigs] == ["EXIT", "LONG"]
    assert sigs[0].timestamp == make_bars(closes)[4]["timestamp"]


def test_sma_crossover_short_mode():
    strat = SMACrossover(["T"], fast=2, slow=3, long_only=False)
    sigs = feed(strat, make_bars([1, 2, 3, 2, 1]))
    assert [s.action.name for s in sigs] == ["SHORT"]


def test_sma_unknown_param_rejected():
    try:
        SMACrossover(["T"], bogus=1)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError")


def test_ema_crossover_trend_change():
    strat = EMACrossover(["T"], fast=2, slow=4)
    # Flat, then a rally, then a decline: both crosses happen after warmup.
    closes = [10] * 6 + [11, 12, 13, 14, 15] + [14, 13, 12, 11, 10]
    sigs = feed(strat, make_bars(closes))
    names = [s.action.name for s in sigs]
    assert names[0] == "LONG"
    assert "EXIT" in names[1:]
    assert names.index("LONG") < names.index("EXIT")


def test_macd_trend_regime_switch():
    strat = MACDTrend(["T"], fast=3, slow=6, signal=3)
    closes = [100] * 12 + list(range(101, 113)) + list(range(113, 101, -1))
    sigs = feed(strat, make_bars(closes))
    names = [s.action.name for s in sigs]
    assert names[0] == "LONG"
    assert "EXIT" in names[1:]


def test_donchian_breakout_entry_exit():
    strat = DonchianBreakout(["T"], entry=3, exit=2)
    closes = [10, 11, 12, 14, 12, 10, 11]
    sigs = feed(strat, make_bars(closes))
    names = [s.action.name for s in sigs]
    assert names[0] == "LONG"      # 14 breaks the prior 3-bar high of 13
    assert "EXIT" in names[1:]     # 10 breaks the 2-bar low


def test_supertrend_crash_flips_short():
    strat = Supertrend(["T"], atr_period=3, multiplier=3.0, long_only=False)
    closes = [100] * 8 + [80]
    sigs = feed(strat, make_bars(closes))
    assert [s.action.name for s in sigs] == ["SHORT"]
    assert sigs[0].symbol == "T"


def test_supertrend_crash_flips_exit_when_long_only():
    strat = Supertrend(["T"], atr_period=3, multiplier=3.0, long_only=True)
    closes = [100] * 8 + [80]
    sigs = feed(strat, make_bars(closes))
    assert [s.action.name for s in sigs] == ["EXIT"]


def test_supertrend_quiet_market_no_signals():
    strat = Supertrend(["T"], atr_period=3, multiplier=3.0)
    sigs = feed(strat, make_bars([100] * 15))
    assert sigs == []


def test_warmup_respected():
    strat = SMACrossover(["T"], fast=10, slow=30)
    assert strat.warmup_bars == 31
    sigs = feed(strat, make_bars(list(range(20))))
    assert sigs == []
