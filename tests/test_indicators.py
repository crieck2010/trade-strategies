"""Indicator unit tests on hand-computed values."""

from __future__ import annotations

from math import isclose

from trade_strategies import indicators as ind


def test_sma():
    assert ind.sma([1, 2, 3, 4, 5], 3) == 4.0
    assert ind.sma([1, 2], 3) is None


def test_ema_seeded_with_sma():
    # seed = sma(10,10,10) = 10; then 20*0.5 + 10*0.5 = 15
    assert isclose(ind.ema([10, 10, 10, 20], 3), 15.0)
    assert ind.ema([1, 2], 3) is None


def test_rsi_all_gains():
    assert ind.rsi([1, 2, 3, 4, 5], 2) == 100.0


def test_rsi_mixed():
    # changes +2,-1,+2; n=2: avg_gain 1->1.5, avg_loss 0.5->0.25; rs=6
    assert isclose(ind.rsi([100, 102, 101, 103], 2), 100 - 100 / 7, rel_tol=1e-9)


def test_rsi_needs_n_plus_1():
    assert ind.rsi([100, 101], 2) is None


def test_bollinger_flat():
    b = ind.bollinger([10.0] * 20, 20, 2.0)
    assert b["mid"] == 10.0 and b["upper"] == 10.0 and b["lower"] == 10.0
    assert b["pct_b"] is None and b["bandwidth"] == 0.0


def test_bollinger_values():
    b = ind.bollinger([1, 2, 3, 4, 5], 5, 2.0)
    assert isclose(b["mid"], 3.0)
    assert isclose(b["upper"], 3 + 2 * 2 ** 0.5, rel_tol=1e-9)


def test_atr_constant_range():
    n = 6
    assert isclose(ind.atr([11] * n, [9] * n, [10] * n, 2), 2.0)


def test_stochastic_midpoint():
    k, d = ind.stochastic([10] * 6, [5] * 6, [7.5] * 6, k=3, d=3)
    assert isclose(k, 50.0) and isclose(d, 50.0)


def test_obv():
    assert ind.obv([1, 2, 1, 3], [10, 10, 10, 10]) == 10.0


def test_rolling_vwap_single_bar():
    assert isclose(ind.rolling_vwap([12], [9], [10.5], [100], 1), 10.5)


def test_zscore():
    # mean 3, sd sqrt(2); (5-3)/sqrt(2) = sqrt(2)
    assert isclose(ind.zscore([1, 2, 3, 4, 5], 5), 2 ** 0.5, rel_tol=1e-9)
    assert ind.zscore([5, 5, 5, 5, 5], 5) is None  # zero variance


def test_roc():
    assert isclose(ind.roc([100, 110], 1), 0.10)
    assert ind.roc([100], 1) is None


def test_macd_warmup_and_shape():
    assert ind.macd([100.0] * 10, 12, 26, 9) == (None, None, None)
    closes = [100 + i * 0.5 for i in range(60)]
    m, s, h = ind.macd(closes, 12, 26, 9)
    assert m is not None and s is not None and h is not None
    assert isclose(h, m - s, rel_tol=1e-9)


def test_adx_bounded():
    closes = [100 + i for i in range(40)]
    highs = [c + 1 for c in closes]
    lows = [c - 1 for c in closes]
    adx_v = ind.adx(highs, lows, closes, 14)
    assert adx_v is not None and 0 <= adx_v <= 100
    assert adx_v > 20  # a relentless trend should read strongly


def test_cross_helpers():
    assert ind.crossed_above(2, 1, 1, 2) is True
    assert ind.crossed_above(2, 1, 2, 1) is False
    assert ind.crossed_above(2, 1, None, None) is True
    assert ind.crossed_below(1, 2, 2, 1) is True
    assert ind.crossed_below(1, 2, None, None) is True
    assert ind.crossed_below(1, 2, 1, 2) is False
