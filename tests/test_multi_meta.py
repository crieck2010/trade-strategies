"""Multi-asset and meta strategy tests."""

from __future__ import annotations

from datetime import datetime

import pytest

from helpers import actions, feed, make_bars, T0

from trade_strategies.base import Signal, SignalAction, Strategy
from trade_strategies.meta import EnsembleVote, RegimeFilter, TrailingStop
from trade_strategies.multi_asset import CrossSectionalMomentum, PairsTrading
from trade_strategies.trend import SMACrossover
from trade_strategies.mean_reversion import ZScoreReversion


def test_pairs_trading_opens_on_divergence():
    strat = PairsTrading(["A", "B"], lookback=20, entry_z=2.0, exit_z=0.5)
    bars_a = make_bars([100] * 40 + [130] * 10, symbol="A")
    bars_b = make_bars([100] * 50, symbol="B")
    sigs = feed(strat, bars_a + bars_b)
    assert len(sigs) >= 2
    first = sigs[0]
    # A jumped rich vs B -> short A, long B
    assert (sigs[0].symbol, sigs[0].action.name) == ("A", "SHORT")
    assert (sigs[1].symbol, sigs[1].action.name) == ("B", "LONG")


def test_pairs_trading_exits_on_convergence():
    strat = PairsTrading(["A", "B"], lookback=20, entry_z=2.0, exit_z=0.5)
    a = [100] * 40 + [130] * 5 + [130 - 1.5 * i for i in range(1, 21)]
    bars_a = make_bars(a, symbol="A")
    bars_b = make_bars([100] * len(a), symbol="B")
    sigs = feed(strat, bars_a + bars_b)
    exits = [s for s in sigs if s.action.name == "EXIT"]
    assert len(exits) >= 2  # both legs covered


def test_pairs_trading_needs_two_symbols():
    with pytest.raises(ValueError):
        PairsTrading(["A"])


def test_cross_sectional_momentum_rotation():
    strat = CrossSectionalMomentum(["A", "B", "C"], lookback=5, top_n=1)
    # Phase 1: A wins. Phase 2: C rallies past A.
    a = [100 + i for i in range(10)] + [110] * 10
    b = [100] * 20
    c = [100 - i for i in range(10)] + [90 + 3 * i for i in range(10)]
    bars = (make_bars(a, symbol="A") + make_bars(b, symbol="B")
            + make_bars(c, symbol="C"))
    sigs = feed(strat, bars)
    longs = [s.symbol for s in sigs if s.action.name == "LONG"]
    exits = [s.symbol for s in sigs if s.action.name == "EXIT"]
    assert longs[0] == "A"
    assert "C" in longs[1:]
    assert "A" in exits


def test_trailing_stop_exits_on_crash():
    class AlwaysLong(Strategy):
        name, family, description = "always_long", "test", ""
        def on_bar(self, timestamp, bars):
            if not getattr(self, "_fired", False):
                self._fired = True
                return [Signal("T", timestamp, SignalAction.LONG)]
            return []

    inner = AlwaysLong(["T"])
    strat = TrailingStop(inner, atr_period=3, multiplier=2.0)
    closes = [100] * 5 + [90]
    sigs = feed(strat, make_bars(closes))
    names = [s.action.name for s in sigs]
    assert names[0] == "LONG"
    assert "EXIT" in names[1:]


def test_trailing_stop_quiet_market_no_exit():
    class AlwaysLong(Strategy):
        name, family, description = "always_long", "test", ""
        def on_bar(self, timestamp, bars):
            if not getattr(self, "_fired", False):
                self._fired = True
                return [Signal("T", timestamp, SignalAction.LONG)]
            return []

    strat = TrailingStop(AlwaysLong(["T"]), atr_period=3, multiplier=2.0)
    sigs = feed(strat, make_bars([100] * 12))
    assert [s.action.name for s in sigs] == ["LONG"]


def test_ensemble_vote_requires_quorum():
    s1 = SMACrossover(["T"], fast=2, slow=3)
    s2 = SMACrossover(["T"], fast=2, slow=3)
    ens = EnsembleVote([s1, s2], min_votes=2)
    sigs = feed(ens, make_bars([2, 1, 2, 3, 4, 3, 2]))
    assert [s.action.name for s in sigs] == ["LONG", "EXIT"]
    assert all(s.strength == 1.0 for s in sigs)


def test_ensemble_vote_no_quorum_no_signal():
    s1 = SMACrossover(["T"], fast=2, slow=3)
    s2 = SMACrossover(["T"], fast=2, slow=3)
    ens = EnsembleVote([s1, s2], min_votes=3)
    assert feed(ens, make_bars([2, 1, 2, 3, 4, 3, 2])) == []


def test_regime_filter_runs_and_describes():
    trend = SMACrossover(["T"], fast=2, slow=5)
    mr = ZScoreReversion(["T"], lookback=5)
    strat = RegimeFilter(trend, mr, adx_period=5, adx_threshold=25.0)
    closes = list(range(100, 140))  # strong trend -> ADX regime
    sigs = feed(strat, make_bars(closes))
    assert all(isinstance(s, Signal) for s in sigs)
    # No signals before the combined warmup.
    assert strat.warmup_bars >= 2 * 5 + 1
    info = strat.describe()
    assert info["trend_leg"]["name"] == "sma_crossover"
    assert info["mean_reversion_leg"]["name"] == "zscore_reversion"


def test_regime_filter_selects_trend_leg():
    # With threshold 0 the filter always routes to the trend leg once the
    # ADX is computable; its signals must match the trend leg run solo.
    closes = [100, 102, 101, 103, 102, 104, 103, 105, 104, 106,
              105, 107, 106, 108, 107, 109]
    filt = RegimeFilter(SMACrossover(["T"], fast=2, slow=3),
                        ZScoreReversion(["T"], lookback=4),
                        adx_period=5, adx_threshold=0.0)
    sigs = feed(filt, make_bars(closes))
    solo = feed(SMACrossover(["T"], fast=2, slow=3), make_bars(closes))
    solo_keys = {(s.timestamp, s.action.name) for s in solo}
    assert len(sigs) > 0
    assert all((s.timestamp, s.action.name) in solo_keys for s in sigs)
