"""MR-5M trial 2 validation: Binance.US 5m bars -> trade-backtest -> trade-overfit.

Frozen pre-registered spec: docs/validation/mr-5m/PRE-REGISTRATION.md
(commit 998f2a0 in this repo). Nothing below changes the spec — only
mechanical choices (paths, timeouts) live here. This is trial 2 of 2, so
the DSR multiple-testing correction uses N=2.

Pipeline:
  BinanceUSPublicProvider (trade-data-crypto v0.2.0, keyless)
    -> trade-backtest engine (t+1 open fills, 6 bps/side all-in costs)
    -> walk-forward folds (12w train / 2w test / 2w step / 1d embargo)
    -> trade-overfit gates (standard preset = the five pre-registered gates)

Usage:
  PYTHONPATH=src python3 docs/validation/mr-5m/run_validation.py [--smoke]

--smoke runs the whole pipeline on synthetic bars (no network) to validate
the harness mechanics before the real pull.
"""

from __future__ import annotations

import json
import math
import sys
import time
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# pre-registered constants (from PRE-REGISTRATION.md — do not change)
# ---------------------------------------------------------------------------

START = "2024-01-01"
# Pre-registration: "2024-01-01 through 2026-09-25" (inclusive). The provider
# uses [start, end), so end=2026-09-26 includes every 2026-09-25 bar.
END = "2026-09-26"
SYMBOLS = ["BTC/USD", "ETH/USD"]
INITIAL_CASH = 100_000.0
EQUITY_FRACTION = 0.10
MAX_POSITIONS = 2

TRAIN_BARS = 24192    # 12 weeks of 5-minute bars
TEST_BARS = 4032      # 2 weeks
STEP_BARS = 4032      # 2 weeks
EMBARGO_BARS = 288    # 1 day
PERIODS_PER_YEAR = 105_120  # 5-minute bars

# all-in cost per side: 2 bps taker + 2 bps half-spread + 2 bps slippage
TAKER_BPS = 2.0
HALF_SPREAD_BPS = 2.0
SLIPPAGE_BPS = 2.0

TRIAL1_OOS_SHARPE = 0.666  # DON-20/10-ATR, trial 1 of 2 (per pre-registration)

OUT_DIR = "docs/validation/mr-5m"


def log(msg: str) -> None:
    print(f"[mr5m] {msg}", flush=True)


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------

def fetch_bars() -> dict[str, list]:
    """Pull M5 bars for both symbols through the released Binance.US provider."""
    try:
        from trade_data_crypto import BinanceUSPublicProvider, Timeframe
    except ImportError as exc:
        raise SystemExit(
            "trade-data-crypto v0.2.0+ with BinanceUSPublicProvider is required. "
            f"Import failed: {exc}"
        ) from exc
    provider = BinanceUSPublicProvider()
    start_d = datetime.strptime(START, "%Y-%m-%d").date()
    end_d = datetime.strptime(END, "%Y-%m-%d").date()
    out: dict[str, list] = {}
    for symbol in SYMBOLS:
        t0 = time.time()
        bars = provider.get_bars(symbol, Timeframe.M5, start=start_d, end=end_d)
        dt = time.time() - t0
        log(f"{symbol}: {len(bars)} bars in {dt:.1f}s "
            f"({bars[0].timestamp} .. {bars[-1].timestamp})")
        out[symbol] = bars
    return out


def synthetic_bars(n: int = 40_000) -> dict[str, list]:
    """Deterministic synthetic 5m bars for --smoke (no network)."""
    import hashlib

    out: dict[str, list] = {}
    t0 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    for s, base in zip(SYMBOLS, (60_000.0, 3_000.0)):
        bars = []
        price = base
        for i in range(n):
            h = hashlib.sha256(f"{s}{i}".encode()).digest()
            shock = (int.from_bytes(h[:4], "big") / 2**32 - 0.5) * 0.004
            # slow mean-reverting drift + noise: gives the z-score something to bite
            price *= math.exp(shock - 0.00002 * math.log(price / base))
            ts = t0 + timedelta(minutes=5 * i)
            bars.append({
                "symbol": s, "timestamp": ts, "open": price,
                "high": price * 1.0005, "low": price * 0.9995,
                "close": price, "volume": 10.0,
            })
        out[s] = bars
    return out


def to_engine_bars(bars_by_symbol: dict[str, list]) -> list:
    """Inner-join both symbols on timestamp; emit trade-backtest Bars."""
    from trade_backtest.models import Bar as EngineBar

    stamps = None
    for bars in bars_by_symbol.values():
        ts = {b["timestamp"] if isinstance(b, dict) else b.timestamp for b in bars}
        stamps = ts if stamps is None else stamps & ts
    log(f"inner-join timestamps: {len(stamps)} common bars")
    by_ts: dict = {}
    for symbol, bars in bars_by_symbol.items():
        for b in bars:
            ts = b["timestamp"] if isinstance(b, dict) else b.timestamp
            if ts in stamps:
                by_ts.setdefault(ts, {})[symbol] = b
    out = []
    for ts in sorted(by_ts):
        row = by_ts[ts]
        if set(row) != set(SYMBOLS):
            continue
        for symbol, b in row.items():
            g = (lambda k: b[k]) if isinstance(b, dict) else (lambda k: getattr(b, k))
            out.append(EngineBar(
                symbol=symbol, timestamp=ts,
                open=float(g("open")), high=float(g("high")),
                low=float(g("low")), close=float(g("close")),
                volume=float(g("volume")),
            ))
    out.sort(key=lambda b: (b.timestamp, b.symbol))
    return out


# ---------------------------------------------------------------------------
# backtest
# ---------------------------------------------------------------------------

def run_backtest(engine_bars: list):
    import trade_backtest.costs as tbc
    import trade_backtest.data as tbd
    import trade_backtest.engine as tbe
    import trade_backtest.execution as tbx
    import trade_backtest.portfolio as tbp

    from trade_strategies.base import SignalAction as SA
    from trade_strategies.mr5m import MR5MScalper

    symbols = sorted({b.symbol for b in engine_bars})

    class CountingStrategy(MR5MScalper):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.signal_log: list[tuple] = []

        def on_bar(self, timestamp, bars):
            sigs = super().on_bar(timestamp, bars)
            for s in sigs:
                self.signal_log.append(
                    (timestamp.isoformat(), s.symbol, s.action.name,
                     round(s.strength, 4)))
            return sigs

    class MR5MSizer(tbp.PositionSizer):
        """10% of equity per LONG; EXIT flattens; hard cap of 2 open positions.

        Compares against trade_strategies.base.SignalAction — trade_backtest
        defines a second, distinct SignalAction enum; comparing against it is
        always False (trial-1 invalid run 2 root cause, documented there).
        """

        def size(self, signal, price, portfolio):
            if signal.action == SA.EXIT:
                return 0.0
            n_open = sum(1 for q in portfolio.positions().values() if q > 0)
            if n_open >= MAX_POSITIONS:
                return 0.0
            qty = EQUITY_FRACTION * portfolio.equity / price
            return qty if qty * price >= 10.0 else 0.0  # $10 min notional

    strategy = CountingStrategy(symbols)
    cost_model = tbc.CostModel(
        commission=tbx.PercentCommission(TAKER_BPS / 10_000),  # 2 bps taker
        slippage_entry_bps=SLIPPAGE_BPS,
        slippage_exit_bps=SLIPPAGE_BPS,
        half_spread_bps=HALF_SPREAD_BPS,
        borrow_cost_annual_bps=0.0,  # spot only, no leverage
    )
    engine = tbe.BacktestEngine(
        data=tbd.ListDataHandler(engine_bars),
        strategy=strategy,
        portfolio=tbp.Portfolio(INITIAL_CASH, MR5MSizer(), cost_model=cost_model),
        execution=tbx.SimulatedExecutionHandler(cost_model=cost_model),
        adjustment_basis="none",  # crypto spot: no corporate actions
        adjustment_note="Binance.US public klines (keyless) via trade-data-crypto "
                        "BinanceUSPublicProvider v0.2.0; spot 5m bars, no adjustments",
    )
    result = engine.run()
    return result, strategy


def equity_returns(result):
    curve = result.equity_curve
    stamps = [p.timestamp for p in curve]
    eq = [p.equity for p in curve]
    rets = [eq[i] / eq[i - 1] - 1.0 for i in range(1, len(eq))]
    return stamps[1:], rets


# ---------------------------------------------------------------------------
# walk-forward
# ---------------------------------------------------------------------------

def walk_forward_folds(stamps, rets):
    from trade_overfit.metrics import max_drawdown, sharpe_ratio, total_return

    n = len(rets)
    folds = []
    start = 0
    while True:
        train_end = start + TRAIN_BARS
        test_start = train_end + EMBARGO_BARS
        test_end = test_start + TEST_BARS
        if test_end > n:
            break
        te = rets[test_start:test_end]
        folds.append({
            "fold": len(folds),
            "train_start": stamps[start].isoformat(),
            "train_end": stamps[train_end - 1].isoformat(),
            "test_start": stamps[test_start].isoformat(),
            "test_end": stamps[test_end - 1].isoformat(),
            "oos_sharpe": sharpe_ratio(te, periods=PERIODS_PER_YEAR),
            "oos_return": total_return(te),
            "oos_max_drawdown": max_drawdown(te)["max_drawdown"],
            "n_oos_bars": len(te),
        })
        start += STEP_BARS
    return folds


# ---------------------------------------------------------------------------
# gates
# ---------------------------------------------------------------------------

def compute_gates(oos_stamps, oos_rets, folds, btc_closes):
    from trade_overfit._stats import median
    from trade_overfit.dsr import dsr_from_returns
    from trade_overfit.gates import evaluate_gates, preset_gates
    from trade_overfit.metrics import (
        annualized_return, max_drawdown, sharpe_ratio,
    )
    from trade_overfit.regimes import regime_report

    oos_sharpe_all = dsr_from_returns(
        oos_rets,
        trial_sharpes=[TRIAL1_OOS_SHARPE,
                       sharpe_ratio(oos_rets, periods=PERIODS_PER_YEAR)],
        periods=PERIODS_PER_YEAR,
    )
    fold_sharpes = [f["oos_sharpe"] for f in folds if f["oos_sharpe"] is not None]
    dd = max_drawdown(oos_rets)
    reg = regime_report(oos_rets, periods=PERIODS_PER_YEAR)  # desk vol-regime default

    # BTC buy-and-hold over the same OOS span, net of 1 entry + 1 exit (6 bps/side)
    closes = [btc_closes[s] for s in oos_stamps]
    gross = closes[-1] / closes[0] - 1.0
    per_side = (TAKER_BPS + HALF_SPREAD_BPS + SLIPPAGE_BPS) / 10_000
    bh_net = (1.0 + gross) * (1.0 - per_side) ** 2 - 1.0
    bh_ann = (1.0 + bh_net) ** (PERIODS_PER_YEAR / len(oos_rets)) - 1.0
    strat_ann = annualized_return(oos_rets, periods=PERIODS_PER_YEAR)
    excess = strat_ann - bh_ann

    evidence = {
        "dsr": oos_sharpe_all["dsr"],
        "median_oos_sharpe": median(fold_sharpes),
        "max_drawdown": dd["max_drawdown"],
        "worst_regime_sharpe": reg["worst_regime_sharpe"],
        "excess_return_vs_benchmark_after_costs": excess,
    }
    gates = evaluate_gates(evidence, preset_gates("standard"))
    verdict = "PASS" if all(g["passed"] for g in gates) else "KILL"
    return {
        "evidence": evidence,
        "gates": gates,
        "verdict": verdict,
        "dsr_detail": oos_sharpe_all,
        "regimes": reg,
        "n_folds_with_sharpe": len(fold_sharpes),
        "strategy_annualized": strat_ann,
        "btc_bh_annualized_net": bh_ann,
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    smoke = "--smoke" in sys.argv
    t0 = datetime.now(timezone.utc).isoformat()
    log(f"starting (smoke={smoke})")

    if smoke:
        bars_by_symbol = synthetic_bars()
    else:
        bars_by_symbol = fetch_bars()
    for s, bars in bars_by_symbol.items():
        first = bars[0]["timestamp"] if isinstance(bars[0], dict) else bars[0].timestamp
        last = bars[-1]["timestamp"] if isinstance(bars[-1], dict) else bars[-1].timestamp
        log(f"{s}: {len(bars)} bars, {first} .. {last}")

    engine_bars = to_engine_bars(bars_by_symbol)
    log(f"engine bars: {len(engine_bars)}")

    log("running backtest (continuous, t+1 open fills, 6 bps/side)")
    result, strategy = run_backtest(engine_bars)
    log(f"signals: {len(strategy.signal_log)} "
        f"({sum(1 for x in strategy.signal_log if x[2]=='LONG')} LONG, "
        f"{sum(1 for x in strategy.signal_log if x[2]=='EXIT')} EXIT)")

    stamps, rets = equity_returns(result)
    log(f"equity curve: {len(rets)} returns, final equity "
        f"{result.equity_curve[-1].equity:,.2f}")

    log(f"walk-forward ({TRAIN_BARS}/{TEST_BARS}/{STEP_BARS} + {EMBARGO_BARS} embargo)")
    folds = walk_forward_folds(stamps, rets)
    log(f"{len(folds)} folds")

    oos_stamps, oos_rets = [], []
    for f in folds:
        i0 = stamps.index(datetime.fromisoformat(f["test_start"]))
        i1 = stamps.index(datetime.fromisoformat(f["test_end"])) + 1
        oos_stamps.extend(stamps[i0:i1])
        oos_rets.extend(rets[i0:i1])
    log(f"OOS series: {len(oos_rets)} bars {oos_stamps[0]} .. {oos_stamps[-1]}")

    btc_closes = {}
    for b in engine_bars:
        if b.symbol == "BTC/USD":
            btc_closes[b.timestamp] = b.close

    log("gates (trade-overfit standard preset, DSR N=2)")
    g = compute_gates(oos_stamps, oos_rets, folds, btc_closes)
    for gate in g["gates"]:
        log(f"  {gate['name']}: {gate['value']} "
            f"({'PASS' if gate['passed'] else 'FAIL'})")
    log(f"verdict: {g['verdict']}")

    bundle = {
        "strategy": "MR-5M",
        "trial": 2,
        "pre_registration_commit": "998f2a0",
        "smoke": smoke,
        "run_started_utc": t0,
        "run_finished_utc": datetime.now(timezone.utc).isoformat(),
        "data": {
            "source": "synthetic" if smoke else
                      "Binance.US public klines via trade-data-crypto "
                      "BinanceUSPublicProvider",
            "range": [START, END],
            "range_note": "provider uses [start, end); end=2026-09-26 includes "
                          "all 2026-09-25 bars, matching the pre-registered "
                          "'2024-01-01 through 2026-09-25'",
            "symbols": SYMBOLS,
            "bars_per_symbol": {s: len(b) for s, b in bars_by_symbol.items()},
            "engine_bars": len(engine_bars),
        },
        "costs_bps_per_side": {
            "taker": TAKER_BPS, "half_spread": HALF_SPREAD_BPS,
            "slippage": SLIPPAGE_BPS,
            "total": TAKER_BPS + HALF_SPREAD_BPS + SLIPPAGE_BPS,
        },
        "walk_forward": {
            "train_bars": TRAIN_BARS, "test_bars": TEST_BARS,
            "step_bars": STEP_BARS, "embargo_bars": EMBARGO_BARS,
            "periods_per_year": PERIODS_PER_YEAR,
            "n_folds": len(folds),
            "n_oos_bars": len(oos_rets),
            "folds": folds,
        },
        "gates": g["gates"],
        "evidence": g["evidence"],
        "dsr_detail": g["dsr_detail"],
        "regimes": g["regimes"],
        "strategy_annualized": g["strategy_annualized"],
        "btc_bh_annualized_net": g["btc_bh_annualized_net"],
        "final_equity": result.equity_curve[-1].equity,
        "n_signals": len(strategy.signal_log),
        "exit_reasons": {
            r: sum(1 for x in strategy.exit_log if x[2] == r)
            for r in ("reversion", "stop", "time")
        },
    }
    out_path = f"{OUT_DIR}/evidence{'_smoke' if smoke else ''}.json"
    with open(out_path, "w") as fh:
        json.dump(bundle, fh, indent=2, default=str)
    log(f"evidence -> {out_path}")

    lines = [
        "# MR-5M validation report (trial 2 of 2)",
        "",
        f"- Pre-registration: commit 998f2a0 (frozen spec, before any OHLC pull)",
        f"- Data: {bundle['data']['source']}, {START}..{END}, "
        f"{bundle['data']['engine_bars']} engine bars",
        f"- Costs: 6 bps/side all-in (2 taker + 2 half-spread + 2 slippage)",
        f"- Walk-forward: 12w train / 2w test / 2w step / 1d embargo, "
        f"{len(folds)} folds",
        f"- DSR N=2 (trial 1 OOS Sharpe 0.666, this trial OOS Sharpe "
        f"{g['dsr_detail']['sharpe_hat']})",
        "",
        "## Gates (trade-overfit standard preset)",
        "",
        "| gate | value | threshold | result |",
        "|---|---|---|---|",
    ]
    for gate in g["gates"]:
        v = gate["value"]
        vs = f"{v:.4f}" if isinstance(v, float) else str(v)
        lines.append(f"| {gate['name']} | {vs} | {gate['op']} {gate['threshold']} | "
                     f"{'PASS' if gate['passed'] else 'FAIL'} |")
    lines += [
        "",
        f"**Verdict: {g['verdict']}**",
        "",
        "## Walk-forward folds",
        "",
        "| fold | test window | OOS Sharpe | OOS return | OOS maxDD |",
        "|---|---|---|---|---|",
    ]
    for fl in folds:
        sh = fl["oos_sharpe"]
        lines.append(
            f"| {fl['fold']} | {fl['test_start'][:10]}..{fl['test_end'][:10]} | "
            f"{sh:.3f} | {fl['oos_return']:.4f} | {fl['oos_max_drawdown']:.4f} |"
            if sh is not None else
            f"| {fl['fold']} | {fl['test_start'][:10]}..{fl['test_end'][:10]} | "
            f"n/a | {fl['oos_return']:.4f} | {fl['oos_max_drawdown']:.4f} |")
    lines += [
        "",
        f"- Strategy annualized (OOS): {g['strategy_annualized']:.4f}",
        f"- BTC buy-and-hold annualized (net of 6 bps/side entry+exit): "
        f"{g['btc_bh_annualized_net']:.4f}",
        f"- Regime splits: {json.dumps(g['regimes']['regimes'], default=str)}",
        f"- Exit reasons: {json.dumps(bundle['exit_reasons'])}",
        f"- Final equity: {bundle['final_equity']:,.2f} "
        f"(from {INITIAL_CASH:,.2f})",
    ]
    report_path = f"{OUT_DIR}/report{'_smoke' if smoke else ''}.md"
    with open(report_path, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    log(f"report -> {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
