"""Mean-reversion, momentum, volatility, and volume strategy tests."""

from __future__ import annotations

from helpers import actions, feed, make_bars

from trade_strategies.mean_reversion import (
    BollingerReversion,
    RSI2MeanReversion,
    StochasticReversion,
    ZScoreReversion,
)
from trade_strategies.momentum import (
    BollingerSqueezeBreakout,
    KeltnerBreakout,
    OBVTrend,
    TimeSeriesMomentum,
    VWAPDeviation,
)


def test_bollinger_reversion_tag_and_recover():
    strat = BollingerReversion(["T"], period=20, num_std=2.0)
    base = [100 + (i % 3) * 0.3 for i in range(25)]
    closes = base + [99, 97, 94, 90, 86, 88, 92, 96, 100]
    sigs = feed(strat, make_bars(closes))
    names = [s.action.name for s in sigs]
    assert names[0] == "LONG"   # lower-band tag after the basing period
    assert "EXIT" in names[1:]   # midline reclaimed on the bounce


def test_rsi2_washout_long():
    # A long rally lifts the slow trend filter well above the washout zone;
    # the sharp pullback then trips RSI(2) while price holds above trend.
    strat = RSI2MeanReversion(["T"], rsi_period=2, trend_period=30,
                              oversold=10, exit_sma=5)
    closes = list(range(100, 135)) + [132, 129, 127, 125, 124]
    sigs = feed(strat, make_bars(closes))
    longs = [s for s in sigs if s.action.name == "LONG"]
    assert len(longs) == 1
    assert 0.2 <= longs[0].strength <= 1.0


def test_zscore_reversion_round_trip():
    strat = ZScoreReversion(["T"], lookback=5, entry_z=1.5, exit_z=0.5)
    closes = [100] * 5 + [90, 92, 95, 98, 99, 100]
    sigs = feed(strat, make_bars(closes))
    names = [s.action.name for s in sigs]
    assert names[0] == "LONG"
    assert "EXIT" in names[1:]


def test_stochastic_reversion_washout():
    strat = StochasticReversion(["T"], k=5, d=3, oversold=20, exit_level=50)
    closes = [100, 98, 96, 94, 92, 90, 88, 86, 88, 90, 92, 94]
    sigs = feed(strat, make_bars(closes))
    names = [s.action.name for s in sigs]
    assert names[0] == "LONG"
    assert "EXIT" in names[1:]


def test_time_series_momentum_direction():
    strat = TimeSeriesMomentum(["T"], lookback=5, skip=0)
    up = feed(strat, make_bars([100, 102, 104, 106, 108, 110, 112]))
    assert [s.action.name for s in up] == ["LONG"]
    strat2 = TimeSeriesMomentum(["T"], lookback=5, skip=0)
    down = feed(strat2, make_bars([112, 110, 108, 106, 104, 102, 100]))
    assert [s.action.name for s in down] == ["EXIT"]


def test_keltner_breakout_jump():
    strat = KeltnerBreakout(["T"], ema_period=5, atr_period=3, mult=1.0)
    closes = [100] * 10 + [110, 112]
    sigs = feed(strat, make_bars(closes))
    assert sigs and sigs[0].action.name == "LONG"


def test_bollinger_squeeze_breakout():
    strat = BollingerSqueezeBreakout(["T"], period=10, squeeze_lookback=20)
    closes = [100] * 30 + [110]
    sigs = feed(strat, make_bars(closes))
    assert sigs and sigs[0].action.name == "LONG"


def test_obv_trend_cross():
    strat = OBVTrend(["T"], fast=2, slow=3)
    # V-shaped reversal: OBV falls then its fast EMA crosses back up.
    sigs = feed(strat, make_bars([100, 99, 98, 97, 96, 97, 98]))
    assert [s.action.name for s in sigs] == ["LONG"]


def test_vwap_deviation_fade():
    strat = VWAPDeviation(["T"], lookback=5, threshold=0.02)
    closes = [100] * 5 + [95]
    sigs = feed(strat, make_bars(closes))
    assert sigs and sigs[0].action.name == "LONG"
    assert 0 < sigs[0].strength <= 1.0


def test_multi_symbol_independent():
    strat = TimeSeriesMomentum(["A", "B"], lookback=5, skip=0)
    bars_a = make_bars([100, 102, 104, 106, 108, 110, 112], symbol="A")
    bars_b = make_bars([112, 110, 108, 106, 104, 102, 100], symbol="B")
    sigs = feed(strat, bars_a + bars_b)
    by_sym = {}
    for s in sigs:
        by_sym.setdefault(s.symbol, []).append(s.action.name)
    assert by_sym["A"] == ["LONG"]
    assert by_sym["B"] == ["EXIT"]
