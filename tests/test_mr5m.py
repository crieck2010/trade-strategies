"""Unit tests for mr5m (trial 2) on synthetic bars. No market data."""

from datetime import datetime, timedelta, timezone

import pytest

from trade_strategies.base import SignalAction
from trade_strategies.mr5m import MR5MConfig, MR5MScalper, zscore

T0 = datetime(2026, 1, 5, tzinfo=timezone.utc)
LB = 96


def make_bars(closes, symbol="BTC/USD", start=T0):
    """Dict bars, 5 minutes apart, open=prev close."""
    bars = []
    prev = closes[0]
    for i, c in enumerate(closes):
        bars.append({
            "symbol": symbol,
            "timestamp": start + timedelta(minutes=5 * i),
            "open": prev, "high": c + 0.05, "low": c - 0.05,
            "close": c, "volume": 10.0,
        })
        prev = c
    return bars


def feed(strat, bars_by_symbol):
    """Drive on_bar over the union of timestamps; return (ts, symbol, action)."""
    sigs = []
    stamps = sorted({b["timestamp"] for bars in bars_by_symbol.values() for b in bars})
    for ts in stamps:
        bars = {}
        for s, blist in bars_by_symbol.items():
            for b in blist:
                if b["timestamp"] == ts:
                    bars[s] = b
        for sig in strat.on_bar(ts, bars):
            sigs.append((ts, sig.symbol, sig.action))
    return sigs


def wobble(n, base=100.0, amp=0.2):
    """n closes alternating base±amp (mean=base, std=amp) — never flat."""
    return [base + amp if i % 2 else base - amp for i in range(n)]


def base_closes():
    """98 bars: 96-bar wobble window + one flat bar, so the first evaluated
    bar (index 97, warmup=98) has a full 96-bar window and a defined prior z."""
    return wobble(LB) + [100.0, 100.0]  # 98 bars


# --- zscore unit tests -------------------------------------------------------

def test_zscore_known_value():
    # window [98,100,102]: mean 100, pop-var 8/3, std 1.633; z=(99-100)/1.633
    z = zscore([98.0, 100.0, 102.0, 99.0], 3)
    assert z == pytest.approx(-0.6123724356957945)


def test_zscore_none_on_flat_window():
    assert zscore([100.0] * 100, LB) is None


def test_zscore_none_on_short_history():
    assert zscore([100.0, 101.0], LB) is None


def test_zscore_excludes_current_bar_from_window():
    # last close must not contaminate the window
    z1 = zscore([100.0, 100.2, 99.8, 100.0, 90.0], 4)
    z2 = zscore([100.0, 100.2, 99.8, 100.0, 110.0], 4)
    assert z1 is not None and z2 is not None
    assert z1 < -10 and z2 > 10  # window identical, last close drives z


# --- strategy behavior -------------------------------------------------------

def test_config_defaults_match_preregistration():
    cfg = MR5MConfig()
    assert cfg.as_dict() == {
        "lookback": 96, "entry_z": 2.0, "exit_z": 0.0,
        "stop_z": 4.0, "max_hold_bars": 48, "equity_fraction": 0.10,
    }
    strat = MR5MScalper(["BTC/USD"])
    assert strat.get_parameters() == cfg.as_dict()
    assert strat.warmup_bars == 98


def test_no_signals_before_warmup():
    bars = make_bars(wobble(90) + [99.0] * 7)  # 97 bars < warmup 98
    strat = MR5MScalper(["BTC/USD"])
    assert feed(strat, {"BTC/USD": bars}) == []


def test_entry_on_fresh_cross_below_minus2():
    closes = base_closes() + [99.5]  # z ≈ -2.5, prev z = 0
    bars = make_bars(closes)
    strat = MR5MScalper(["BTC/USD"])
    sigs = feed(strat, {"BTC/USD": bars})
    assert len(sigs) == 1
    ts, sym, action = sigs[0]
    assert sym == "BTC/USD" and action == SignalAction.LONG
    assert ts == bars[-1]["timestamp"]  # signal at the dip bar's close


def test_no_entry_without_fresh_cross():
    # already stretched (z_prev < -2): second dip is not a fresh cross
    closes = base_closes() + [99.5, 99.4]
    bars = make_bars(closes)
    strat = MR5MScalper(["BTC/USD"])
    sigs = feed(strat, {"BTC/USD": bars})
    assert [a for _, _, a in sigs] == [SignalAction.LONG]  # only the first dip


def test_no_entry_above_threshold():
    closes = base_closes() + [99.8]  # z ≈ -1.0, not stretched enough
    bars = make_bars(closes)
    strat = MR5MScalper(["BTC/USD"])
    assert feed(strat, {"BTC/USD": bars}) == []


def test_exit_on_reversion():
    closes = base_closes() + [99.5, 100.0]  # dip then reclaim of the mean
    bars = make_bars(closes)
    strat = MR5MScalper(["BTC/USD"])
    sigs = feed(strat, {"BTC/USD": bars})
    assert [a for _, _, a in sigs] == [SignalAction.LONG, SignalAction.EXIT]
    assert strat.exit_log[-1][2] == "reversion"


def test_exit_on_stop():
    closes = base_closes() + [99.5, 98.0]  # dip then collapse: z ≈ -10
    bars = make_bars(closes)
    strat = MR5MScalper(["BTC/USD"])
    sigs = feed(strat, {"BTC/USD": bars})
    assert [a for _, _, a in sigs] == [SignalAction.LONG, SignalAction.EXIT]
    assert strat.exit_log[-1][2] == "stop"


def test_exit_on_time_stop():
    closes = base_closes() + [99.5] + [99.5] * 50  # pinned at z≈-2.5
    bars = make_bars(closes)
    strat = MR5MScalper(["BTC/USD"])
    sigs = feed(strat, {"BTC/USD": bars})
    actions = [a for _, _, a in sigs]
    assert actions[0] == SignalAction.LONG
    assert actions.count(SignalAction.EXIT) == 1
    exit_ts = sigs[-1][0]
    entry_ts = sigs[0][0]
    assert (exit_ts - entry_ts) == timedelta(minutes=5 * 48)
    assert strat.exit_log[-1][2] == "time"


def test_no_pyramiding_while_holding():
    closes = base_closes() + [99.5, 99.4, 99.6]  # stays stretched, never exits
    bars = make_bars(closes)
    strat = MR5MScalper(["BTC/USD"])
    sigs = feed(strat, {"BTC/USD": bars})
    assert [a for _, _, a in sigs].count(SignalAction.LONG) == 1


def test_reentry_after_exit():
    closes = base_closes() + [99.5, 100.0] + [99.5]  # enter, exit, fresh dip
    bars = make_bars(closes)
    strat = MR5MScalper(["BTC/USD"])
    sigs = feed(strat, {"BTC/USD": bars})
    assert [a for _, _, a in sigs] == [
        SignalAction.LONG, SignalAction.EXIT, SignalAction.LONG]


def test_symbols_independent():
    btc = make_bars(base_closes() + [99.5], symbol="BTC/USD")
    eth = make_bars(base_closes() + [100.2], symbol="ETH/USD")
    strat = MR5MScalper(["BTC/USD", "ETH/USD"])
    sigs = feed(strat, {"BTC/USD": btc, "ETH/USD": eth})
    assert len(sigs) == 1 and sigs[0][1] == "BTC/USD"


def test_entry_signal_strength_is_equity_fraction():
    closes = base_closes() + [99.5]
    bars = make_bars(closes)
    strat = MR5MScalper(["BTC/USD"])
    got = []
    by_ts = {b["timestamp"]: b for b in bars}
    for ts in sorted(by_ts):
        for sig in strat.on_bar(ts, {"BTC/USD": by_ts[ts]}):
            got.append(sig)
    assert len(got) == 1 and got[0].strength == pytest.approx(0.10)
