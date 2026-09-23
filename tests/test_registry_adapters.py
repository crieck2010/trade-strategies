"""Registry and trade-backtest bridge tests."""

from __future__ import annotations

import pytest

from helpers import make_bars

from trade_strategies import (
    describe_strategies,
    get_strategy,
    list_families,
    list_strategies,
)
from trade_strategies.registry import STRATEGY_REGISTRY
from trade_strategies.trend import SMACrossover


def test_registry_counts():
    assert len(STRATEGY_REGISTRY) == 19
    assert len(list_strategies()) == 19


def test_families():
    families = list_families()
    for expected in ("trend", "mean_reversion", "momentum", "volatility",
                     "volume", "multi_asset", "meta"):
        assert expected in families


def test_family_filter():
    trend = list_strategies("trend")
    assert "sma_crossover" in trend
    assert "pairs_trading" not in trend


def test_get_strategy_unknown():
    with pytest.raises(KeyError):
        get_strategy("nope")


def test_describe_strategies_shape():
    infos = describe_strategies()
    assert len(infos) == 19
    for info in infos:
        assert {"name", "family", "description", "parameters"} <= set(info)
    sma = next(i for i in infos if i["name"] == "sma_crossover")
    assert sma["parameters"] == {"fast": 10, "slow": 30, "long_only": True}
    assert sma["warmup_bars"] == 31


def test_get_strategy_instantiates():
    cls = get_strategy("donchian_breakout")
    strat = cls(["T"], entry=10)
    assert strat.params["entry"] == 10


tb = pytest.importorskip("trade_backtest")


def test_to_backtest_strategy_adapts_signals():
    from trade_strategies.adapters import to_backtest_strategy
    strat = SMACrossover(["T"], fast=2, slow=3)
    adapted = to_backtest_strategy(strat)
    assert isinstance(adapted, tb.Strategy)
    assert adapted.symbols == ["T"]


def test_run_backtest_end_to_end():
    from trade_strategies.adapters import run_backtest
    # Flat base so the MA cross happens after the strategy's warmup.
    closes = [100] * 20 + [100 + i for i in range(25)] + [125 - i for i in range(15)]
    bars = make_bars(closes, opens=closes)  # gapless: valid OHLC
    result = run_backtest(SMACrossover(["T"], fast=5, slow=15), bars)
    assert result.num_trades >= 1
    assert "sharpe_ratio" in result.metrics
    assert len(result.equity_curve) == len(closes)
