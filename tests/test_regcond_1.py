"""Unit tests for the REGCOND-1 production strategy (``regcond_1``).

Offline: all data is synthetic.  Exact fidelity against the validated
evidence lives in ``docs/validation/regcond-1/fidelity_check.py`` (needs
network + the validation harness).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest

from trade_strategies import (
    REGCOND_1_SYMBOLS,
    REGCOND_1_WEIGHTS,
    RegCond1,
    SignalAction,
    describe_strategies,
    get_strategy,
    list_strategies,
)

pytestmark = pytest.mark.skipif(
    __import__("importlib").util.find_spec("trade_macro") is None,
    reason="trade_macro not installed",
)


def _synth_stream(n_bars: int, cu_trend: float, au_trend: float,
                  start: date = date(2020, 1, 1)):
    """Yield ``(timestamp, bars)`` with deterministic metal trends.

    SPY/TLT are flat at 100; CPER/GLD follow exponential trends so the
    copper:gold ratio is a clean linear trend (positive -> EXPANSION,
    negative -> CONTRACTION, zero -> NEUTRAL via the zero-variance rule).
    """
    out = []
    day = start
    for i in range(n_bars):
        bars = {
            "SPY": {"close": 100.0},
            "CPER": {"close": 100.0 * (1.0 + cu_trend) ** i},
            "TLT": {"close": 100.0},
            "GLD": {"close": 100.0 * (1.0 + au_trend) ** i},
        }
        out.append((datetime(day.year, day.month, day.day), bars))
        day += timedelta(days=1)
    return out


def _run(stream):
    strat = RegCond1(list(REGCOND_1_SYMBOLS))
    events = []  # (date, label, signals)
    for ts, bars in stream:
        sigs = strat.on_bar(ts, bars)
        if sigs:
            events.append((ts.date(), strat.label_history[ts.date()], sigs))
    return strat, events


def test_registry_wires_regcond_1():
    assert get_strategy("regcond_1") is RegCond1
    assert "regcond_1" in list_strategies()
    meta = next(d for d in describe_strategies() if d["name"] == "regcond_1")
    assert meta["warmup_bars"] == 260
    assert "copper" in meta["description"].lower()


def test_frozen_universe_enforced():
    with pytest.raises(ValueError):
        RegCond1(["SPY", "CPER", "TLT"])
    with pytest.raises(ValueError):
        RegCond1(["SPY", "CPER", "TLT", "GLD", "BTC"])
    # order and case are free
    RegCond1(["gld", "tlt", "cper", "spy"])


def test_no_parameters_allowed():
    with pytest.raises(ValueError):
        RegCond1(list(REGCOND_1_SYMBOLS), lookback=100)


def test_weights_sum_to_one():
    for label, w in REGCOND_1_WEIGHTS.items():
        assert set(w) == set(REGCOND_1_SYMBOLS), label
        assert abs(sum(w.values()) - 1.0) < 1e-12, label


def test_warmup_emits_no_signals():
    strat, events = _run(_synth_stream(200, 0.002, 0.0))
    assert events == []
    assert len(strat.label_history) == 200  # labels still tracked


def test_expansion_weights_after_warmup():
    strat, events = _run(_synth_stream(400, 0.002, 0.0))
    assert events, "expected rebalance events after warmup"
    for day, label, sigs in events:
        assert label == "EXPANSION", (day, label)
        longs = {s.symbol: s.strength for s in sigs
                 if s.action is SignalAction.LONG}
        exits = {s.symbol for s in sigs if s.action is SignalAction.EXIT}
        assert longs == {"SPY": 0.60, "CPER": 0.20, "TLT": 0.20}
        assert exits == {"GLD"}
        assert abs(sum(longs.values()) - 1.0) < 1e-12


def test_contraction_weights_after_warmup():
    strat, events = _run(_synth_stream(400, -0.002, 0.0))
    assert events
    for day, label, sigs in events:
        assert label == "CONTRACTION", (day, label)
        longs = {s.symbol: s.strength for s in sigs
                 if s.action is SignalAction.LONG}
        exits = {s.symbol for s in sigs if s.action is SignalAction.EXIT}
        assert longs == {"SPY": 0.20, "TLT": 0.40, "GLD": 0.40}
        assert exits == {"CPER"}


def test_neutral_weights_when_flat():
    strat, events = _run(_synth_stream(400, 0.0, 0.0))
    assert events
    for day, label, sigs in events:
        assert label == "NEUTRAL", (day, label)
        longs = {s.symbol: s.strength for s in sigs
                 if s.action is SignalAction.LONG}
        assert longs == {"SPY": 0.25, "CPER": 0.25, "TLT": 0.25, "GLD": 0.25}
        assert not [s for s in sigs if s.action is SignalAction.EXIT]


def test_rebalance_uses_prior_month_end_label():
    """D4: the first-trading-day-of-month signal reads the persisted label
    as of the previous month's final trading day."""
    strat, events = _run(_synth_stream(400, 0.002, 0.0))
    assert events
    for day, _label, sigs in events:
        # previous trading day in the stream (consecutive calendar days)
        prev = day - timedelta(days=1)
        expected = REGCOND_1_WEIGHTS[strat.label_history[prev]]
        got = {s.symbol: (s.strength if s.action is SignalAction.LONG else 0.0)
               for s in sigs}
        assert got == expected, (day, strat.label_history[prev])


def test_signals_only_on_month_boundaries():
    strat, events = _run(_synth_stream(400, 0.002, 0.0))
    for day, _label, _sigs in events:
        assert day.day == 1, day  # consecutive-day stream: 1st of month
    # every month start after warmup produced exactly one rebalance
    months = {(d.year, d.month) for d, _l, _s in events}
    assert len(months) == len(events)


def test_missing_leg_carries_last_close():
    """D3 hold policy: a missing bar reuses the last known close."""
    stream = _synth_stream(300, 0.002, 0.0)
    for i in range(50, 300, 37):  # punch holes in CPER
        del stream[i][1]["CPER"]
    strat = RegCond1(list(REGCOND_1_SYMBOLS))
    for ts, bars in stream:
        strat.on_bar(ts, bars)
    assert strat.label_history[stream[-1][0].date()] == "EXPANSION"
