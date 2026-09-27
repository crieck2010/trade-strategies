"""TREND-VT trial 3 candidate A validation: yfinance daily ETF bars -> trade-backtest -> trade-overfit.

Frozen pre-registered spec: docs/validation/trend-vt/PRE-REGISTRATION.md
(commit 42ecab2; gate amendment 425745b). Nothing below changes the spec —
only mechanical choices (paths, date arithmetic, plumbing) live here. This is
trial 3 (candidate A), so the DSR multiple-testing correction uses N=7 (the
full Phase-B screened batch, in-sample Sharpes from docs/research/SCREENING.md).

Pipeline:
  trade-data-equities EquitiesDataClient (yfinance, split/div adjusted)
    -> trade-backtest engine (monthly target weights, fills at next trading
       day's open, 5 bps/side, 30 bps/yr borrow on short notional)
    -> walk-forward folds (60m train / 12m test / 12m step / 21-trading-day
       embargo) on the strategy's daily return series
    -> trade-overfit gates (standard preset = the seven pre-registered gates)

Mechanical choices (documented; all most-literal readings of the spec):
  M1. Walk-forward bars: 1 month = 21 trading days ->
      TRAIN=1260 / TEST=252 / STEP=252 / EMBARGO=21 bars.
  M2. Month-end rebalance date = last trading day of the calendar month in the
      union trading calendar across the six ETFs (all US-listed, same days).
  M3. Vol: sigma_i = sample-stdev of the 60 daily returns[t-60..t-1]
      (indices i-60..i-1 — the 60 returns ending at bar t-1, i.e. EXCLUDING
      the rebalance day's own return) x sqrt(252). Most literal reading of
      "stdev(daily returns[t-60..t-1])".
  M4. TR: needs 252 prior bars (index i >= 252) with positive closes; else flat.
  M5. An ETF with no bar on a rebalance date is flat that month (per spec).
  M6. Initial capital $100,000 (return series is scale-invariant under
      fraction-of-equity sizing; same figure as Phase-B screening).
  M7. Benchmark: equal-weight 6-ETF buy-and-hold, rebalanced monthly to 1/6
      each on the same month-end dates, 5 bps/side on turnover (incl. the
      initial allocation at the series start), full-series portfolio whose
      returns are then subset to the OOS timestamps. Cost applied at the
      rebalance close (standard index methodology; documented).
  M8. Borrow sensitivity (0/30/100 bps) is two extra engine runs, report-only;
      the gated run uses the spec's 30 bps.

Usage:
  cd ~/workspace/trade-suite/trade-strategies
  PYTHONPATH=src:../trade-backtest/src:../trade-data-equities/src:../trade-overfit/src \
      python3 docs/validation/trend-vt/run_validation.py [--smoke]

--smoke runs the whole pipeline on synthetic daily bars (no network) to
validate harness mechanics before the real pull. Smoke outputs are suffixed
_smoke and never overwrite the real evidence/report.
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from datetime import date, datetime, timezone

# ---------------------------------------------------------------------------
# pre-registered constants (from PRE-REGISTRATION.md — do not change)
# ---------------------------------------------------------------------------

START = "2010-01-01"
# Pre-registration: "2010-01-01 through 2026-09-25" (inclusive). The client
# uses [start, end), so end=2026-09-26 includes every 2026-09-25 bar.
END = "2026-09-26"
ETFS = ["SPY", "TLT", "GLD", "USO", "EFA", "VNQ"]

TREND_LOOKBACK = 252        # trading days
VOL_WINDOW = 60             # daily returns
TARGET_VOL = 0.10           # annualized portfolio vol target
COMMISSION_BPS = 5.0        # per side
BORROW_BPS = 30.0           # annual, on short notional (spec)
INITIAL_CASH = 100_000.0

# Walk-forward geometry: 60m train / 12m test / 12m step / 21d embargo,
# on the DAILY return series (1 month = 21 trading days — mechanical choice M1).
TRAIN_BARS = 1260
TEST_BARS = 252
STEP_BARS = 252
EMBARGO_BARS = 21
PERIODS_PER_YEAR = 252

# DSR trial set: the 7 Phase-B in-sample Sharpes (n_trials=7 honesty), in
# screening-rank order: TSMOM-CR, TREND-VT, XMOM-1, CARRY-1, BAB-1, FMOM-1,
# PAIRS-1 (docs/research/SCREENING.md).
TRIAL_SHARPES = [0.798, 0.485, 0.413, 0.379, 0.106, -0.097, -0.337]

SPEC_COMMIT = "42ecab2"
AMENDMENT_COMMIT = "425745b"

OUT_DIR = "docs/validation/trend-vt"


def log(msg: str) -> None:
    print(f"[trendvt] {msg}", flush=True)


def stdev(xs: list[float]) -> float:
    """Sample stdev (n-1); 0.0 when degenerate."""
    n = len(xs)
    if n < 2:
        return 0.0
    mu = sum(xs) / n
    return math.sqrt(sum((x - mu) ** 2 for x in xs) / (n - 1))


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------

def fetch_bars() -> dict[str, list]:
    """Pull adjusted daily bars for the six ETFs through trade-data-equities."""
    try:
        from trade_data_equities.client import EquitiesDataClient
        from trade_data_equities.providers.yfinance import YFinanceProvider
        from trade_data_equities.models import Timeframe
    except ImportError as exc:
        raise SystemExit(
            "trade-data-equities is required. Import failed: "
            f"{exc}"
        ) from exc
    client = EquitiesDataClient(provider=YFinanceProvider())
    start_d = date.fromisoformat(START)
    end_d = date.fromisoformat(END)
    out: dict[str, list] = {}
    for etf in ETFS:
        t0 = time.time()
        bars = client.get_bars(etf, Timeframe.DAILY, start_d, end_d,
                               adjusted=True)
        dt = time.time() - t0
        log(f"{etf}: {len(bars)} bars in {dt:.1f}s "
            f"({bars[0].timestamp} .. {bars[-1].timestamp})")
        out[etf] = bars
    return out


def synthetic_bars(n: int = 2500) -> dict[str, list]:
    """Deterministic synthetic daily bars for --smoke (no network).

    Six pseudo-ETFs, ~10 years of trading days, distinct drifts/vols so the
    momentum signals actually fire.
    """
    out: dict[str, list] = {}
    t0 = datetime(2010, 1, 4, tzinfo=timezone.utc)
    specs = {"SPY": (100.0, 0.00030, 0.011), "TLT": (100.0, 0.00005, 0.006),
             "GLD": (100.0, 0.00010, 0.010), "USO": (100.0, -0.00010, 0.020),
             "EFA": (100.0, 0.00020, 0.010), "VNQ": (100.0, 0.00015, 0.012)}
    # business-day grid (skip weekends), like a real ETF calendar
    days, d = [], t0
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d += __import__("datetime").timedelta(days=1)
    for s, (base, drift, vol) in specs.items():
        price = base
        bars = []
        for i, ts in enumerate(days):
            h = hashlib.sha256(f"{s}{i}".encode()).digest()
            shock = (int.from_bytes(h[:4], "big") / 2**32 - 0.5) * 2 * vol
            price *= math.exp(drift + shock)
            bars.append({"symbol": s, "timestamp": ts, "open": price,
                         "high": price * 1.003, "low": price * 0.997,
                         "close": price, "volume": 1e6})
        out[s] = bars
    return out


def validate_data(bars_by_symbol: dict[str, list]) -> None:
    """Sanity checks; raises on anything that would silently corrupt signals."""
    for etf in ETFS:
        bars = bars_by_symbol[etf]
        assert bars, f"{etf}: no bars returned"
        prev = None
        for b in bars:
            ts = b["timestamp"] if isinstance(b, dict) else b.timestamp
            c = b["close"] if isinstance(b, dict) else b.close
            if prev is not None:
                assert ts > prev, f"{etf}: non-monotonic timestamps at {ts}"
            prev = ts
            assert c == c and c > 0, f"{etf}: bad close {c} at {ts}"
    log("data validation: monotonic, all-positive closes")


def month_end_rebalances(bars_by_symbol: dict[str, list]) -> list:
    """Last trading day of each calendar month in the union calendar (M2)."""
    stamps = set()
    for bars in bars_by_symbol.values():
        for b in bars:
            ts = b["timestamp"] if isinstance(b, dict) else b.timestamp
            stamps.add(ts)
    by_ym: dict[tuple[int, int], list] = {}
    for ts in stamps:
        by_ym.setdefault((ts.year, ts.month), []).append(ts)
    return sorted(max(ts_list) for ts_list in by_ym.values())


def etf_close_series(bars_by_symbol: dict[str, list]) -> dict[str, dict]:
    """ETF -> {'stamps': [...], 'closes': [...], 'idx': {ts: i}}."""
    out = {}
    for etf in ETFS:
        rows = sorted(
            (b["timestamp"] if isinstance(b, dict) else b.timestamp,
             b["close"] if isinstance(b, dict) else b.close)
            for b in bars_by_symbol[etf])
        stamps = [r[0] for r in rows]
        closes = [r[1] for r in rows]
        out[etf] = {"stamps": stamps, "closes": closes,
                    "idx": {ts: i for i, ts in enumerate(stamps)}}
    return out


# ---------------------------------------------------------------------------
# backtest
# ---------------------------------------------------------------------------

class TrendVTStrategy:
    """Frozen-spec monthly trend strategy (long/flat/short, vol-targeted).

    Pattern follows docs/research/scratch/common.py TargetStrategy: the
    strategy publishes target fractions of equity; the sizer obeys; signals
    are emitted only when a target changes (avoids daily churn).
    """

    def __init__(self, symbols: list[str], series: dict[str, dict],
                 rebal_set: set):
        from trade_backtest.models import Signal, SignalAction
        self.symbols = [s.strip().upper() for s in symbols]
        if not self.symbols:
            raise ValueError("strategy needs at least one symbol")
        self._Signal = Signal
        self._SA = SignalAction
        self._series = series
        self._rebal_set = rebal_set
        self.targets: dict[str, float] = {}
        self._emitted: dict[str, float] = {}
        self._cur: dict[str, float] = {}
        self.rebal_log: list[tuple] = []  # (date, {etf: (tr, vol, w)}) for audit

    def _compute_month(self, ts) -> dict[str, float]:
        n = len(self.symbols)
        tgt: dict[str, float] = {}
        audit: dict[str, tuple] = {}
        for e in self.symbols:
            ser = self._series[e]
            i = ser["idx"].get(ts)
            if i is None:
                continue  # M5: no bar on the rebalance date -> flat this month
            if i < TREND_LOOKBACK:  # M4: needs 252 prior bars
                continue
            c = ser["closes"]
            tr = c[i] / c[i - TREND_LOOKBACK] - 1.0
            # M3: 60 daily returns ending at bar t-1 (exclude today's return)
            rets = [c[j] / c[j - 1] - 1.0 for j in range(i - VOL_WINDOW, i)]
            vol = stdev(rets) * math.sqrt(252)
            if vol <= 0:
                continue
            sign = 1.0 if tr > 0 else (-1.0 if tr < 0 else 0.0)
            w = sign * (TARGET_VOL / n) / vol
            tgt[e] = w
            audit[e] = (round(tr, 4), round(vol, 4), round(w, 4))
        self.rebal_log.append((ts.strftime("%Y-%m-%d"), audit))
        return tgt

    def on_bar(self, timestamp, bars):
        if timestamp in self._rebal_set:
            self._cur = self._compute_month(timestamp)
        self.targets = {s: self._cur.get(s, 0.0) for s in self.symbols}
        Signal, SA = self._Signal, self._SA
        out = []
        for sym in self.symbols:
            if sym not in bars:
                continue  # no bar -> no signal possible (portfolio would raise)
            old = self._emitted.get(sym, 0.0)
            newt = self.targets[sym]
            changed = (old == 0.0) != (newt == 0.0) or (
                old != 0.0 and newt != 0.0 and abs(newt - old) > 1e-9)
            if changed:
                action = SA.LONG if newt > 0 else (
                    SA.SHORT if newt < 0 else SA.EXIT)
                out.append(Signal(symbol=sym, timestamp=timestamp,
                                  action=action))
                self._emitted[sym] = newt
        return out


def run_backtest(engine_bars: list, strategy, borrow_bps: float,
                 note: str):
    from trade_backtest.costs import CostModel
    from trade_backtest.data import ListDataHandler
    from trade_backtest.engine import BacktestEngine
    from trade_backtest.execution import PercentCommission, SimulatedExecutionHandler
    from trade_backtest.portfolio import Portfolio
    from trade_backtest.models import SignalAction
    from trade_backtest.portfolio import PositionSizer

    class TargetsSizer(PositionSizer):
        """Size = strategy.targets[symbol] x equity / price. EXIT -> flat."""

        def size(self, signal, price, portfolio):
            if signal.action is SignalAction.EXIT:
                return 0.0
            tgt = strategy.targets.get(signal.symbol, 0.0)
            if tgt == 0.0 or price <= 0:
                return 0.0
            return tgt * portfolio.equity / price

    cost_model = CostModel(
        commission=PercentCommission(COMMISSION_BPS / 10_000),
        slippage_entry_bps=0.0,
        slippage_exit_bps=0.0,
        half_spread_bps=0.0,
        borrow_cost_annual_bps=borrow_bps,
    )
    engine = BacktestEngine(
        data=ListDataHandler(engine_bars),
        strategy=strategy,
        portfolio=Portfolio(INITIAL_CASH, TargetsSizer(), cost_model=cost_model),
        execution=SimulatedExecutionHandler(cost_model=cost_model),
        adjustment_basis="pre_adjusted",
        adjustment_note=note,
    )
    return engine.run()


def to_engine_bars(bars_by_symbol: dict[str, list]) -> list:
    """Union calendar: one trade-backtest Bar per (symbol, day) that traded."""
    from trade_backtest.models import Bar as EngineBar

    out = []
    for etf in ETFS:
        for b in bars_by_symbol[etf]:
            g = (lambda k: b[k]) if isinstance(b, dict) else (lambda k: getattr(b, k))
            ts = g("timestamp")
            out.append(EngineBar(
                symbol=etf, timestamp=ts,
                open=float(g("open")), high=float(g("high")),
                low=float(g("low")), close=float(g("close")),
                volume=float(g("volume")),
            ))
    out.sort(key=lambda b: (b.timestamp, b.symbol))
    return out


def equity_returns(result):
    curve = result.equity_curve
    stamps = [p.timestamp for p in curve]
    eq = [p.equity for p in curve]
    assert all(e > 0 for e in eq), "non-positive equity in curve"
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


def oos_series(stamps, rets, folds):
    """Concatenate the OOS test segments (the gated series)."""
    oos_stamps, oos_rets = [], []
    for f in folds:
        i0 = stamps.index(datetime.fromisoformat(f["test_start"]))
        i1 = stamps.index(datetime.fromisoformat(f["test_end"])) + 1
        oos_stamps.extend(stamps[i0:i1])
        oos_rets.extend(rets[i0:i1])
    return oos_stamps, oos_rets


# ---------------------------------------------------------------------------
# benchmark: equal-weight 6-ETF buy-and-hold, rebalanced monthly, net of costs
# ---------------------------------------------------------------------------

def benchmark_returns(union_stamps: list, series: dict[str, dict],
                      rebal_set: set) -> tuple[list, list[float]]:
    """Daily returns of the monthly-rebalanced EW 6-ETF portfolio (M7).

    Starts 1/6 each at the first union date (5 bps/side on the initial
    allocation). Each day: portfolio return = sum(w_i * r_i); weights drift
    with returns; on month-end, rebalance to 1/6 each with
    cost = 5 bps x sum|1/6 - w_i| applied at the rebalance close.
    Missing ETF bars are forward-filled (daily return 0 that day).
    """
    bps = COMMISSION_BPS / 10_000
    fwd = {e: None for e in ETFS}
    w = {e: 1.0 / len(ETFS) for e in ETFS}
    cost0 = bps * sum(abs(1.0 / len(ETFS) - 0.0) for e in ETFS)  # from cash
    rets: list[float] = []
    first = True
    for ts in union_stamps:
        r: dict[str, float] = {}
        for e in ETFS:
            ser = series[e]
            i = ser["idx"].get(ts)
            if i is not None:
                c = ser["closes"][i]
                if fwd[e] is None:
                    fwd[e] = c
                r[e] = c / fwd[e] - 1.0
                fwd[e] = c
            else:
                r[e] = 0.0 if fwd[e] is not None else 0.0
        day_ret = sum(w[e] * r[e] for e in ETFS)
        if first:
            day_ret = (1.0 - cost0) * (1.0 + day_ret) - 1.0
            first = False
        # drift weights
        tot = 1.0 + day_ret
        w = {e: w[e] * (1.0 + r[e]) / tot if tot > 0 else 1.0 / len(ETFS)
             for e in ETFS}
        if ts in rebal_set:
            cost = bps * sum(abs(1.0 / len(ETFS) - w[e]) for e in ETFS)
            day_ret = (1.0 + day_ret) * (1.0 - cost) - 1.0
            w = {e: 1.0 / len(ETFS) for e in ETFS}
        rets.append(day_ret)
    return union_stamps, rets


# ---------------------------------------------------------------------------
# gates
# ---------------------------------------------------------------------------

def compute_gates(oos_stamps, oos_rets, folds, bench_oos_rets):
    from trade_overfit._stats import median
    from trade_overfit.dsr import dsr_from_returns
    from trade_overfit.gates import evaluate_gates, preset_gates
    from trade_overfit.metrics import (
        annualized_return, calmar_ratio, max_drawdown, sharpe_ratio,
        sortino_ratio,
    )
    from trade_overfit.regimes import regime_report

    dsr_detail = dsr_from_returns(
        oos_rets, trial_sharpes=list(TRIAL_SHARPES), periods=PERIODS_PER_YEAR)
    fold_sharpes = [f["oos_sharpe"] for f in folds
                    if f["oos_sharpe"] is not None]
    dd = max_drawdown(oos_rets)
    reg = regime_report(oos_rets, periods=PERIODS_PER_YEAR)

    strat_ann = annualized_return(oos_rets, periods=PERIODS_PER_YEAR)
    bench_ann = annualized_return(bench_oos_rets, periods=PERIODS_PER_YEAR)
    excess = (strat_ann - bench_ann
              if strat_ann is not None and bench_ann is not None else None)

    evidence = {
        "dsr": dsr_detail["dsr"],
        "median_oos_sharpe": median(fold_sharpes),
        "max_drawdown": dd["max_drawdown"],
        "worst_regime_sharpe": reg["worst_regime_sharpe"],
        "excess_return_vs_benchmark_after_costs": excess,
        "sortino": sortino_ratio(oos_rets, periods=PERIODS_PER_YEAR),
        "calmar": calmar_ratio(oos_rets, periods=PERIODS_PER_YEAR),
    }
    gates = evaluate_gates(evidence, preset_gates("standard"))
    verdict = "PASS" if all(g["passed"] for g in gates) else "KILL"
    return {
        "evidence": evidence,
        "gates": gates,
        "verdict": verdict,
        "dsr_detail": dsr_detail,
        "regimes": reg,
        "n_folds_with_sharpe": len(fold_sharpes),
        "strategy_annualized": strat_ann,
        "benchmark_annualized_net": bench_ann,
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
    validate_data(bars_by_symbol)
    for s, bars in bars_by_symbol.items():
        first = bars[0]["timestamp"] if isinstance(bars[0], dict) else bars[0].timestamp
        last = bars[-1]["timestamp"] if isinstance(bars[-1], dict) else bars[-1].timestamp
        log(f"{s}: {len(bars)} bars, {first.date()} .. {last.date()}")

    series = etf_close_series(bars_by_symbol)
    rebal = month_end_rebalances(bars_by_symbol)
    rebal_set = set(rebal)
    log(f"month-end rebalance dates: {len(rebal)} "
        f"({rebal[0].date()} .. {rebal[-1].date()})")
    # per spec: an ETF missing a bar on a rebalance date is flat that month
    missing = [(r.strftime("%Y-%m-%d"), e)
               for r in rebal for e in ETFS if r not in series[e]["idx"]]
    if missing:
        log(f"WARNING: {len(missing)} rebalance-date holes (leg flat that "
            f"month): {missing[:10]}")
    else:
        log("no rebalance-date holes: all six ETFs present on every month-end")

    engine_bars = to_engine_bars(bars_by_symbol)
    log(f"engine bars: {len(engine_bars)}")

    note = ("yfinance daily ETF OHLCV, split/div adjusted (auto_adjust), "
            "basis=pre_adjusted; 5 bps/side commission; 30 bps/yr borrow on "
            "short notional; fills at next trading day's open")
    strategy = TrendVTStrategy(ETFS, series, rebal_set)
    log(f"running backtest (monthly targets, t+1 open fills, 5 bps/side, "
        f"{BORROW_BPS} bps/yr borrow)")
    result = run_backtest(engine_bars, strategy, BORROW_BPS, note)
    n_rebal = len(strategy.rebal_log)
    n_trades = sum(1 for a in strategy.rebal_log for _ in a[1])
    log(f"rebalances: {n_rebal}, nonzero legs: {n_trades}")

    stamps, rets = equity_returns(result)
    log(f"equity curve: {len(rets)} daily returns, final equity "
        f"{result.equity_curve[-1].equity:,.2f}")

    log(f"walk-forward ({TRAIN_BARS}/{TEST_BARS}/{STEP_BARS} + {EMBARGO_BARS} "
        f"embargo on daily bars)")
    folds = walk_forward_folds(stamps, rets)
    log(f"{len(folds)} folds")
    oos_stamps, oos_rets = oos_series(stamps, rets, folds)
    log(f"OOS series: {len(oos_rets)} bars {oos_stamps[0].date()} .. "
        f"{oos_stamps[-1].date()}")

    # benchmark: full-series EW B&H, then subset to the OOS timestamps
    union_stamps = sorted({b.timestamp for b in engine_bars})
    _, bench_rets = benchmark_returns(union_stamps, series, rebal_set)
    bench_by_ts = dict(zip(union_stamps, bench_rets))
    bench_oos = [bench_by_ts[ts] for ts in oos_stamps]
    assert len(bench_oos) == len(oos_rets)

    log(f"gates (trade-overfit standard preset, DSR N={len(TRIAL_SHARPES)})")
    g = compute_gates(oos_stamps, oos_rets, folds, bench_oos)
    for gate in g["gates"]:
        log(f"  {gate['name']}: {gate['value']} "
            f"({'PASS' if gate['passed'] else 'FAIL'})")
    log(f"verdict: {g['verdict']}")

    # cost-sensitivity note (report-only; the gated run uses 30 bps)
    sens = {}
    for bps in (0.0, 100.0):
        s2 = TrendVTStrategy(ETFS, series, rebal_set)
        r2 = run_backtest(engine_bars, s2, bps, note)
        eq2 = [p.equity for p in r2.equity_curve]
        rets2 = [eq2[i] / eq2[i - 1] - 1.0 for i in range(1, len(eq2))]
        o2_stamps, o2_rets = oos_series(stamps, rets2, folds)
        from trade_overfit.metrics import sharpe_ratio
        sens[str(bps)] = {
            "final_equity": eq2[-1],
            "total_return": eq2[-1] / INITIAL_CASH - 1.0,
            "oos_sharpe": sharpe_ratio(o2_rets, periods=PERIODS_PER_YEAR),
        }
        log(f"borrow {bps:g} bps sensitivity: final equity {eq2[-1]:,.2f}, "
            f"OOS Sharpe {sens[str(bps)]['oos_sharpe']}")

    from trade_overfit.metrics import performance_summary
    series_stats = performance_summary(oos_rets, periods=PERIODS_PER_YEAR)

    bundle = {
        "strategy": "TREND-VT",
        "trial": 3,
        "candidate": "A",
        "pre_registration_commit": SPEC_COMMIT,
        "gate_amendment_commit": AMENDMENT_COMMIT,
        "smoke": smoke,
        "run_started_utc": t0,
        "run_finished_utc": datetime.now(timezone.utc).isoformat(),
        "data": {
            "source": "synthetic" if smoke else
                      "yfinance daily OHLCV via trade-data-equities "
                      "EquitiesDataClient + YFinanceProvider, adjusted=True "
                      "(split/div adjusted)",
            "range": [START, END],
            "range_note": "client uses [start, end); end=2026-09-26 includes "
                          "all 2026-09-25 bars, matching the pre-registered "
                          "'2010-01-01 through 2026-09-25'",
            "symbols": ETFS,
            "bars_per_symbol": {s: len(b) for s, b in bars_by_symbol.items()},
            "first_bar": {s: str((b[0]["timestamp"] if isinstance(b[0], dict)
                                  else b[0].timestamp))
                          for s, b in bars_by_symbol.items()},
            "last_bar": {s: str((b[-1]["timestamp"] if isinstance(b[-1], dict)
                                 else b[-1].timestamp))
                         for s, b in bars_by_symbol.items()},
            "engine_bars": len(engine_bars),
            "rebalance_date_holes": missing,
        },
        "spec": {
            "trend_lookback_bars": TREND_LOOKBACK,
            "vol_window_returns": VOL_WINDOW,
            "target_vol": TARGET_VOL,
            "commission_bps_per_side": COMMISSION_BPS,
            "borrow_cost_annual_bps": BORROW_BPS,
            "initial_cash": INITIAL_CASH,
            "fills": "next trading day's open (SimulatedExecutionHandler)",
        },
        "mechanical_choices": [
            "M1: walk-forward on daily bars: TRAIN=1260/TEST=252/STEP=252/"
            "EMBARGO=21 (21 trading days = 1 month)",
            "M2: month-end = last trading day of calendar month in the union "
            "ETF calendar",
            "M3: vol = sample-stdev of the 60 daily returns ending at bar t-1 "
            "(excludes the rebalance day's own return) x sqrt(252)",
            "M4: TR needs 252 prior bars (index i >= 252), else leg flat",
            "M5: ETF missing a bar on a rebalance date -> leg flat that month",
            "M6: initial capital $100,000 (return series scale-invariant)",
            "M7: benchmark = EW 6-ETF B&H, monthly rebalance to 1/6, "
            "5 bps/side on turnover incl. initial allocation, costs at "
            "rebalance close; returns subset to OOS timestamps",
            "M8: borrow sensitivity (0/100 bps) is extra runs, report-only; "
            "gated run uses the spec 30 bps",
        ],
        "walk_forward": {
            "train_bars": TRAIN_BARS, "test_bars": TEST_BARS,
            "step_bars": STEP_BARS, "embargo_bars": EMBARGO_BARS,
            "periods_per_year": PERIODS_PER_YEAR,
            "n_folds": len(folds),
            "n_oos_bars": len(oos_rets),
            "oos_span": [oos_stamps[0].isoformat(), oos_stamps[-1].isoformat()],
            "folds": folds,
        },
        "gates": g["gates"],
        "evidence": g["evidence"],
        "dsr_detail": g["dsr_detail"],
        "trial_sharpes": TRIAL_SHARPES,
        "regimes": g["regimes"],
        "strategy_annualized": g["strategy_annualized"],
        "benchmark_annualized_net": g["benchmark_annualized_net"],
        "borrow_sensitivity": sens,
        "oos_series_stats": series_stats,
        "final_equity": result.equity_curve[-1].equity,
        "n_rebalances": n_rebal,
        "rebalance_audit": strategy.rebal_log,
    }
    out_path = f"{OUT_DIR}/evidence{'_smoke' if smoke else ''}.json"
    with open(out_path, "w") as fh:
        json.dump(bundle, fh, indent=2, default=str)
    log(f"evidence -> {out_path}")

    lines = [
        "# TREND-VT validation report (trial 3, candidate A)",
        "",
        f"- Pre-registration: commit {SPEC_COMMIT} (frozen spec); gate amendment "
        f"commit {AMENDMENT_COMMIT} (5 -> 7 gates, before any data pull)",
        f"- Data: {bundle['data']['source']}, {START}..{END}",
        f"- Costs: 5 bps/side + {BORROW_BPS} bps/yr borrow on short notional; "
        f"fills at next trading day's open",
        f"- Walk-forward: 60m train / 12m test / 12m step / 21d embargo "
        f"({TRAIN_BARS}/{TEST_BARS}/{STEP_BARS}/{EMBARGO_BARS} daily bars), "
        f"{len(folds)} folds; concatenated OOS = gated series",
        f"- DSR N=7 (Phase-B in-sample Sharpes "
        f"{', '.join(str(x) for x in TRIAL_SHARPES)})",
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
        f"- EW 6-ETF benchmark annualized (net of 5 bps/side): "
        f"{g['benchmark_annualized_net']:.4f}",
        f"- Excess (strategy - benchmark): "
        f"{g['evidence']['excess_return_vs_benchmark_after_costs']:.4f}",
        f"- Regime splits: {json.dumps(g['regimes']['regimes'], default=str)}",
        f"- Final equity: {bundle['final_equity']:,.2f} "
        f"(from {INITIAL_CASH:,.2f})",
        "",
        "## Borrow-cost sensitivity (report-only; gated run uses 30 bps)",
        "",
        "| borrow (bps/yr) | final equity | total return | OOS Sharpe |",
        "|---|---|---|---|",
    ]
    for bps in ("0.0", "100.0"):
        s = sens[bps]
        lines.append(f"| {float(bps):.0f} | {s['final_equity']:,.2f} | "
                     f"{s['total_return']:.4f} | {s['oos_sharpe']:.3f} |")
    s30 = {"final_equity": bundle["final_equity"],
           "total_return": bundle["final_equity"] / INITIAL_CASH - 1.0,
           "oos_sharpe": g["dsr_detail"]["sharpe_hat"]}
    lines.append(f"| 30 (spec) | {s30['final_equity']:,.2f} | "
                 f"{s30['total_return']:.4f} | {s30['oos_sharpe']:.3f} |")
    lines += [
        "",
        "## Honest flags",
        "",
        "- Trend-family exposure: TREND-VT shares trial 1 (DON-20/10-ATR)'s "
        "exposure to trend failure as a *family*. The diversification is "
        "structural — cross-asset (6 ETFs vs single asset), vol-targeted "
        "sizing (vs fixed fractional), monthly rebalance (vs daily) — not "
        "categorical. In a cross-asset trend-failure regime, both would "
        "suffer.",
        "- The 6-ETF set is a researcher choice (documented in the "
        "pre-registration, not data-mined).",
        "- yfinance adjusted closes; survivorship is a non-issue for these "
        "ETFs but corporate-action adjustment quality is vendor-dependent.",
        "- Borrow cost is an assumption (30 bps disclosed low end; sensitivity "
        "above). Retail short-ETF borrow can be higher in stress.",
        "- Vol targeting lags by construction: a mid-month vol spike is "
        "unaddressed until the next month-end.",
        "- Fills assumed at next day's open at the open price with 5 bps "
        "commission; no spread/slippage modeled beyond that.",
        "",
        "## Data provenance",
        "",
        f"- Source: yfinance via trade-data-equities "
        f"EquitiesDataClient/YFinanceProvider, adjusted=True "
        f"(split- and dividend-adjusted)",
        f"- Window: {START}..2026-09-25 (client [start, end) with "
        f"end=2026-09-26)",
        f"- Bars per ETF: {json.dumps(bundle['data']['bars_per_symbol'])}",
        f"- Rebalance-date holes: "
        f"{bundle['data']['rebalance_date_holes'] or 'none'}",
        f"- Run: {t0} .. {bundle['run_finished_utc']}",
    ]
    report_path = f"{OUT_DIR}/report{'_smoke' if smoke else ''}.md"
    with open(report_path, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    log(f"report -> {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
