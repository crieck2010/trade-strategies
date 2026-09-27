"""Tests for the cost-speed-limit gate (Carver).

Covers: the gate maths, Carver's worked examples as regression tests,
boundary behaviour, monotonicity (property-style), multi-instrument
notional weighting, fail-closed invalid inputs, and the thin
trade-overfit Gate adapter.
"""

from __future__ import annotations

import math

import pytest

from trade_strategies.gates import (
    ADOPTION_DATE,
    BUDGET_FRACTION,
    cost_speed_limit_gate,
    evaluate_cost_speed_limit,
    evaluate_cost_speed_limit_multi,
    notional_weighted_cost_vol,
)

REQUIRED_KEYS = {
    "gate", "turnover_ann", "round_trip_cost", "instrument_vol_ann",
    "gross_sharpe", "budget_fraction", "cost_sharpe_drag", "budget",
    "pass", "rationale",
}


# -- core maths -----------------------------------------------------------

def test_result_carries_every_intermediate():
    r = evaluate_cost_speed_limit(50, 0.0002, 0.10, 0.4)
    assert REQUIRED_KEYS <= set(r)
    assert r["gate"] == "cost_speed_limit"
    assert r["pass"] is True
    assert r["rationale"]


def test_drag_formula():
    # drag = turnover * round_trip_cost / vol
    r = evaluate_cost_speed_limit(100, 0.001, 0.20, 1.0)
    assert r["cost_sharpe_drag"] == pytest.approx(100 * 0.001 / 0.20)
    assert r["budget"] == pytest.approx(1.0 / 3.0)


def test_budget_is_one_third_of_gross_sharpe():
    assert BUDGET_FRACTION == pytest.approx(1 / 3)
    r = evaluate_cost_speed_limit(10, 0.0001, 0.15, 0.9)
    assert r["budget"] == pytest.approx(0.3)


def test_zero_turnover_passes():
    r = evaluate_cost_speed_limit(0, 0.01, 0.20, 0.4)
    assert r["cost_sharpe_drag"] == 0.0
    assert r["pass"] is True


def test_zero_gross_sharpe_fails():
    r = evaluate_cost_speed_limit(10, 0.0001, 0.15, 0.0)
    assert r["pass"] is False
    assert "gross_sharpe" in r["rationale"]


def test_negative_gross_sharpe_fails():
    r = evaluate_cost_speed_limit(10, 0.0001, 0.15, -0.5)
    assert r["pass"] is False


def test_exact_boundary_passes():
    # drag == budget is a pass (<=).
    # gross 0.3 -> budget 0.1; 50 * 0.0002 / 0.10 = 0.1 exactly.
    r = evaluate_cost_speed_limit(50, 0.0002, 0.10, 0.3)
    assert r["cost_sharpe_drag"] == pytest.approx(r["budget"])
    assert r["pass"] is True


def test_just_over_boundary_fails():
    r = evaluate_cost_speed_limit(50.0001, 0.0002, 0.10, 0.3)
    assert r["pass"] is False


# -- Carver's worked examples (regression) --------------------------------
# Video: a typical single rule earns ~0.4 gross Sharpe -> ~0.13 SR/yr budget.
# Cheap futures: ~65 round trips/yr. BTC: ~26 round trips/yr.
# Documented assumptions consistent with those figures:
#   futures: 2 bp round trip, 10% instrument vol
#   BTC:     40 bp round trip, 80% instrument vol

def test_carver_cheap_futures_example():
    gross, cost, vol = 0.4, 0.0002, 0.10
    per_trade = cost / vol  # 0.002 SR per round trip
    assert per_trade == pytest.approx(0.002)
    assert evaluate_cost_speed_limit(65, cost, vol, gross)["pass"] is True
    assert evaluate_cost_speed_limit(67, cost, vol, gross)["pass"] is False
    # implied max turnover ~= 66.7, i.e. "around 65"
    r = evaluate_cost_speed_limit(65, cost, vol, gross)
    assert r["budget"] == pytest.approx(0.4 / 3)
    assert r["cost_sharpe_drag"] == pytest.approx(65 * 0.002)


def test_carver_btc_example():
    gross, cost, vol = 0.4, 0.004, 0.80
    per_trade = cost / vol  # 0.005 SR per round trip
    assert per_trade == pytest.approx(0.005)
    assert evaluate_cost_speed_limit(26, cost, vol, gross)["pass"] is True
    assert evaluate_cost_speed_limit(27, cost, vol, gross)["pass"] is False


def test_stronger_edge_earns_larger_budget():
    # Adaptive, not hard-coded to 0.4: double the edge, double the budget.
    cost, vol = 0.0002, 0.10
    assert evaluate_cost_speed_limit(65, cost, vol, 0.4)["pass"] is True
    assert evaluate_cost_speed_limit(65, cost, vol, 0.2)["pass"] is False
    assert evaluate_cost_speed_limit(130, cost, vol, 0.8)["pass"] is True


# -- monotonicity (property-style) ----------------------------------------

def test_monotone_in_turnover():
    prev_drag = -1.0
    seen_fail = False
    for t in range(0, 200):
        r = evaluate_cost_speed_limit(t, 0.0002, 0.10, 0.4)
        assert r["cost_sharpe_drag"] >= prev_drag
        prev_drag = r["cost_sharpe_drag"]
        if not r["pass"]:
            seen_fail = True
        # pass never comes back once lost (single crossing)
        assert not (seen_fail and r["pass"])
    assert seen_fail  # the sweep actually crosses the boundary


def test_monotone_in_cost():
    prev = -1.0
    for bps in range(0, 200):
        r = evaluate_cost_speed_limit(50, bps / 10000, 0.10, 0.4)
        assert r["cost_sharpe_drag"] >= prev
        prev = r["cost_sharpe_drag"]


def test_higher_vol_relaxes_the_gate():
    # Same turnover and cost: a more volatile instrument pays fewer
    # Sharpe units per trade.
    low = evaluate_cost_speed_limit(100, 0.0002, 0.10, 0.4)
    high = evaluate_cost_speed_limit(100, 0.0002, 0.40, 0.4)
    assert high["cost_sharpe_drag"] < low["cost_sharpe_drag"]
    assert low["pass"] is False
    assert high["pass"] is True


# -- multi-instrument weighting --------------------------------------------

def test_multi_matches_single_for_one_instrument():
    inst = [{"name": "ES", "round_trip_cost": 0.0002, "instrument_vol_ann": 0.10,
             "weight": 3.0}]
    multi = evaluate_cost_speed_limit_multi(50, inst, 0.4)
    single = evaluate_cost_speed_limit(50, 0.0002, 0.10, 0.4)
    assert multi["pass"] == single["pass"]
    assert multi["cost_sharpe_drag"] == pytest.approx(single["cost_sharpe_drag"])
    assert multi["round_trip_cost"] == pytest.approx(0.0002)
    assert multi["instrument_vol_ann"] == pytest.approx(0.10)


def test_notional_weighted_average():
    agg = notional_weighted_cost_vol([
        {"name": "A", "round_trip_cost": 0.0002, "instrument_vol_ann": 0.10,
         "weight": 1.0},
        {"name": "B", "round_trip_cost": 0.0006, "instrument_vol_ann": 0.30,
         "weight": 3.0},
    ])
    assert agg["round_trip_cost"] == pytest.approx((0.0002 + 3 * 0.0006) / 4)
    assert agg["instrument_vol_ann"] == pytest.approx((0.10 + 3 * 0.30) / 4)
    weights = [r["weight"] for r in agg["instruments"]]
    assert weights == pytest.approx([0.25, 0.75])
    assert sum(weights) == pytest.approx(1.0)


def test_equal_weighting_when_weights_absent():
    agg = notional_weighted_cost_vol([
        {"round_trip_cost": 0.0002, "instrument_vol_ann": 0.10},
        {"round_trip_cost": 0.0004, "instrument_vol_ann": 0.20},
    ])
    assert agg["round_trip_cost"] == pytest.approx(0.0003)
    assert agg["instrument_vol_ann"] == pytest.approx(0.15)


def test_multi_gate_uses_weighted_inputs():
    # 75% weight on the expensive instrument dominates the drag.
    instruments = [
        {"name": "cheap", "round_trip_cost": 0.0001, "instrument_vol_ann": 0.10,
         "weight": 1.0},
        {"name": "pricey", "round_trip_cost": 0.002, "instrument_vol_ann": 0.10,
         "weight": 3.0},
    ]
    r = evaluate_cost_speed_limit_multi(60, instruments, 0.4)
    wavg_cost = (0.0001 + 3 * 0.002) / 4
    assert r["round_trip_cost"] == pytest.approx(wavg_cost)
    assert r["cost_sharpe_drag"] == pytest.approx(60 * wavg_cost / 0.10)
    assert r["pass"] is False  # 60 * 0.001525 / 0.10 = 0.915 >> 0.133
    assert r["instruments"] is not None and len(r["instruments"]) == 2


def test_multi_fails_closed_on_bad_instruments():
    assert evaluate_cost_speed_limit_multi(50, [], 0.4)["pass"] is False
    zero_w = [{"round_trip_cost": 0.0002, "instrument_vol_ann": 0.10,
               "weight": 0.0}]
    r = evaluate_cost_speed_limit_multi(50, zero_w, 0.4)
    assert r["pass"] is False
    assert "zero" in r["rationale"]
    bad = [{"round_trip_cost": float("nan"), "instrument_vol_ann": 0.10}]
    assert evaluate_cost_speed_limit_multi(50, bad, 0.4)["pass"] is False


# -- fail closed ------------------------------------------------------------

@pytest.mark.parametrize("bad", [None, float("nan"), float("inf"),
                                 float("-inf"), "50", True])
@pytest.mark.parametrize("pos", [0, 1, 2, 3])
def test_invalid_scalar_inputs_fail_closed(bad, pos):
    args = [50, 0.0002, 0.10, 0.4]
    args[pos] = bad
    r = evaluate_cost_speed_limit(*args)
    assert r["pass"] is False
    assert r["cost_sharpe_drag"] is None
    assert "FAIL" in r["rationale"]


def test_negative_turnover_fails_closed():
    r = evaluate_cost_speed_limit(-5, 0.0002, 0.10, 0.4)
    assert r["pass"] is False
    assert "turnover_ann" in r["rationale"]


def test_negative_cost_fails_closed():
    r = evaluate_cost_speed_limit(50, -0.0002, 0.10, 0.4)
    assert r["pass"] is False


def test_zero_or_negative_vol_fails_closed():
    for v in (0.0, -0.1):
        r = evaluate_cost_speed_limit(50, 0.0002, v, 0.4)
        assert r["pass"] is False
        assert r["cost_sharpe_drag"] is None  # never divide by zero


def test_bad_budget_fraction_rejected():
    for bf in (0.0, -0.5, 1.5, float("nan"), None):
        r = evaluate_cost_speed_limit(50, 0.0002, 0.10, 0.4,
                                      budget_fraction=bf)
        assert r["pass"] is False


# -- trade-overfit adapter ---------------------------------------------------

def test_adapter_builds_matching_gate():
    pytest.importorskip("trade_overfit.gates")
    gate = cost_speed_limit_gate(0.6)
    assert gate.name == "cost_speed_limit"
    assert gate.metric == "cost_sharpe_drag"
    assert gate.op == "lte"
    assert gate.threshold == pytest.approx(0.2)
    assert "Carver" in gate.description


def test_adapter_agrees_with_core_evaluation():
    pytest.importorskip("trade_overfit.gates")
    from trade_overfit.gates import evaluate_gates

    gross = 0.6
    gate = cost_speed_limit_gate(gross)
    core = evaluate_cost_speed_limit(100, 0.0004, 0.20, gross)
    adapted = evaluate_gates(
        {"cost_sharpe_drag": core["cost_sharpe_drag"]}, [gate])[0]
    assert adapted["passed"] == core["pass"]
    assert adapted["value"] == pytest.approx(core["cost_sharpe_drag"])
    assert adapted["threshold"] == pytest.approx(core["budget"])


def test_adapter_rejects_nonpositive_gross_sharpe():
    with pytest.raises(ValueError):
        cost_speed_limit_gate(0.0)
    with pytest.raises(ValueError):
        cost_speed_limit_gate(-1.0)


def test_adoption_date_recorded():
    assert ADOPTION_DATE == "2026-09-27"
