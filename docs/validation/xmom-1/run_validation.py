"""XMOM-1 trial 3 validation: yfinance daily bars -> trade-backtest -> trade-overfit.

Frozen pre-registered spec: docs/validation/xmom-1/PRE-REGISTRATION.md
(commit 4b72b8a in this repo). Nothing below changes the spec — only
mechanical choices (paths, timeouts, sys.path, cache TTL) live here.
This is trial 3 of 3; the DSR multiple-testing correction uses N=7 with
the Phase B in-sample Sharpe list from the pre-registration (XMOM-1 was
idea #3 of the 7, so validating it adds no new trials).

Pipeline:
  EquitiesDataClient + YFinanceProvider, Timeframe.DAILY, adjusted=True
    (trade-data-equities; raw bars cached under evidence/cache/)
    -> trade-backtest engine (t+1 open fills via SimulatedExecutionHandler,
       5 bps/side PercentCommission, 50 bps/yr borrow on shorts)
    -> walk-forward folds on the daily return series (60-month train /
       12-month test / 12-month step, 21-trading-day embargo)
    -> trade-overfit v0.2.0 gates (standard preset: 7 gates)

Usage:
  python3 docs/validation/xmom-1/run_validation.py [--smoke]
(run from the trade-strategies repo root; plain python3, no PYTHONPATH
needed — sibling suite repos are wired below as a mechanical choice)

--smoke runs the whole pipeline on deterministic synthetic daily bars
(no network) to validate the harness mechanics before the real pull.
Smoke verdicts are meaningless (random-walk data has no edge).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# mechanical sys.path (NOT a spec choice): sibling suite repos are source
# checkouts, not pip installs, in this environment.
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))          # docs/validation/xmom-1
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
_SUITE = os.path.dirname(_REPO)
for _repo in ("trade-backtest", "trade-data-equities", "trade-overfit"):
    _p = os.path.join(_SUITE, _repo, "src")
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ---------------------------------------------------------------------------
# pre-registered constants (from PRE-REGISTRATION.md — do not change)
# ---------------------------------------------------------------------------

START_S = "2015-01-01"
# Pre-registration: "2015-01-01 through 2026-09-25" (inclusive). The provider
# uses [start, end), so end=2026-09-26 includes every 2026-09-25 bar.
END_S = "2026-09-26"
START_D = date(2015, 1, 1)
END_D = date(2026, 9, 26)
TRADE_START_S = "2019-01-01"   # 2015-2018 = formation warmup; trading from here
INITIAL_CASH = 100_000.0

LOOKBACK = 252          # formation window (trading days)
SKIP = 21               # skip most recent 21 trading days (12-1)
DECILE = 0.10
GROSS_PER_LEG = 0.50    # dollar-neutral, gross 1.0
COMM_BPS = 5.0          # per side
BORROW_BPS = 50.0       # annualized, on short notional (large-cap GC)

EMBARGO_DAYS = 21       # trading-day embargo between train end and test start
PERIODS_PER_YEAR = 252

# Phase B in-sample Sharpes of the screened batch of 7 (pre-registered);
# XMOM-1 was #3 (0.413). DSR n_trials = 7 honesty.
TRIAL_SHARPES = [0.798, 0.485, 0.413, 0.379, 0.106, -0.097, -0.337]

SPEC_COMMIT = "4b72b8a"
OUT_DIR = os.path.join(_REPO, "docs", "validation", "xmom-1")
EVIDENCE_DIR = os.path.join(OUT_DIR, "evidence")
UNIVERSE_PATH = os.path.join(
    _REPO, "docs", "research", "evidence", "universe.txt")
IRX = "^IRX"
GRID_SYMBOL = "SPY"     # SPY bars define the trading-day grid (not a candidate)


def log(msg: str) -> None:
    print(f"[xmom1] {msg}", flush=True)


# ---------------------------------------------------------------------------
# small pure helpers (mirror docs/research/scratch/common.py mechanics)
# ---------------------------------------------------------------------------

def dstr(ts: datetime) -> str:
    return ts.date().isoformat()


def trailing_return(closes: list[float], lookback: int, skip: int = 0):
    """Return over [t-lookback-skip, t-skip]; None when history is short."""
    n = len(closes)
    if n < lookback + skip + 1:
        return None
    base = closes[n - 1 - skip - lookback]
    last = closes[n - 1 - skip]
    if base <= 0:
        return None
    return last / base - 1.0


def month_rebalances(dates: list[str]) -> list[str]:
    """First trading day of each calendar month present in the date list."""
    out, seen = [], set()
    for d in sorted(dates):
        ym = d[:7]
        if ym not in seen:
            seen.add(ym)
            out.append(d)
    return out


def add_months(ym: tuple[int, int], k: int) -> tuple[int, int]:
    m0 = ym[0] * 12 + (ym[1] - 1) + k
    return (m0 // 12, m0 % 12 + 1)


def load_universe(path: str) -> list[str]:
    with open(path) as fh:
        return [ln.strip() for ln in fh if ln.strip()]

# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------

def fetch_bars(tickers: list[str]) -> dict[str, list]:
    """Pull daily OHLCV via trade-data-equities (YFinanceProvider, adjusted).

    Raw provider bars are cached as JSON under evidence/cache/ with a long
    TTL so a re-run does not refetch. Tickers that fail keep an empty list
    (they fail the 95% coverage rule -> ineligible; documented, not fatal).
    """
    from trade_data_equities.cache import DiskCache
    from trade_data_equities.client import EquitiesDataClient
    from trade_data_equities.models import Timeframe
    from trade_data_equities.providers.yfinance import YFinanceProvider

    os.makedirs(os.path.join(EVIDENCE_DIR, "cache"), exist_ok=True)
    cache = DiskCache(
        root=os.path.join(EVIDENCE_DIR, "cache"),
        ttl={"daily": timedelta(days=365), "corp": timedelta(days=365)},
    )
    client = EquitiesDataClient(provider=YFinanceProvider(), cache=cache)
    out: dict[str, list] = {}
    manifest = {"pulled_at_utc": datetime.now(timezone.utc).isoformat(),
                "provider": "YFinanceProvider via trade-data-equities",
                "timeframe": "1d", "adjusted": True,
                "range": [START_S, END_S], "tickers": {}}
    t0 = time.time()
    for i, t in enumerate(tickers):
        try:
            bars = client.get_bars(t, Timeframe.DAILY, start=START_D,
                                   end=END_D, adjusted=True)
            out[t] = [(b.timestamp, float(b.open), float(b.high),
                       float(b.low), float(b.close), float(b.volume))
                      for b in bars]
            manifest["tickers"][t] = {
                "bars": len(bars),
                "first": dstr(bars[0].timestamp) if bars else None,
                "last": dstr(bars[-1].timestamp) if bars else None,
            }
        except Exception as exc:  # noqa: BLE001 - one bad ticker must not kill the pull
            log(f"{t}: FETCH FAILED ({type(exc).__name__}: {exc}) -> ineligible")
            out[t] = []
            manifest["tickers"][t] = {"bars": 0, "error": str(exc)[:200]}
        if (i + 1) % 25 == 0:
            log(f"fetched {i + 1}/{len(tickers)} tickers "
                f"({time.time() - t0:.0f}s elapsed)")
    manifest["elapsed_s"] = round(time.time() - t0, 1)
    with open(os.path.join(EVIDENCE_DIR, "fetch_manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=2)
    log(f"fetch done: {time.time() - t0:.0f}s; manifest -> evidence/fetch_manifest.json")
    return out


def synthetic_bars(tickers: list[str]) -> dict[str, list]:
    """Deterministic synthetic daily bars for --smoke (no network).

    ~40 tickers + SPY + ^IRX, every weekday 2015-01-01..2026-09-25,
    geometric random walks (no edge by construction).
    """
    out: dict[str, list] = {}
    days = []
    d = date(2015, 1, 1)
    while d < date(2026, 9, 26):
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    for t in tickers:
        seed = 100.0 if t == GRID_SYMBOL else 50.0
        price = seed
        bars = []
        for i, dd in enumerate(days):
            h = hashlib.sha256(f"{t}{i}".encode()).digest()
            shock = (int.from_bytes(h[:4], "big") / 2**32 - 0.5) * 0.03
            price *= math.exp(shock - 0.00001 * math.log(price / seed))
            ts = datetime(dd.year, dd.month, dd.day, tzinfo=timezone.utc)
            if t == IRX:
                y = 4.0  # flat 4% T-bill yield
                bars.append((ts, y, y, y, y, 0.0))
            else:
                bars.append((ts, price, price * 1.002, price * 0.998, price, 1e6))
        out[t] = bars
    return out


def build_panel(bars_by_ticker: dict[str, list]):
    """SPY grid, eligibility, forward-filled aligned closes, rebalance dates.

    Mirrors docs/research/scratch/xmom_1.py prepare() + common.aligned_closes:
      * grid = SPY trading days over [START_S, END_S)
      * eligible (static): bars on >=95% of grid dates
      * aligned closes: causal forward-fill onto the grid; tickers with any
        leading gap are dropped from the tradeable set (screening's
        aligned_closes behavior — documented literal-reading choice)
      * rebalance dates: first trading day of each calendar month >= 2019-01-01
    Returns (grid, eligible_static, aligned, rebal, bars_raw, coverage).
    bars_raw: ticker -> {date_str: (o,h,l,c,v)} (full OHLCV, actual bars only).
    coverage: ticker -> fraction of grid dates with a bar.
    """
    spy_bars = bars_by_ticker.get(GRID_SYMBOL, [])
    grid = sorted({dstr(ts) for ts, *_ in spy_bars
                   if START_S <= dstr(ts) < END_S})
    if not grid:
        raise SystemExit("empty SPY grid — cannot build the trading-day grid")
    log(f"SPY grid: {len(grid)} trading days ({grid[0]} .. {grid[-1]})")

    bars_raw: dict[str, dict[str, tuple]] = {}
    coverage: dict[str, float] = {}
    for t, bars in bars_by_ticker.items():
        if t in (GRID_SYMBOL, IRX):
            continue
        d: dict[str, tuple] = {}
        for ts, o, h, l, c, v in bars:
            ds = dstr(ts)
            if START_S <= ds < END_S and c and c > 0:
                d[ds] = (o, h, l, c, v)
        bars_raw[t] = d
        coverage[t] = sum(1 for g in grid if g in d) / len(grid)

    eligible_static = sorted(t for t, cov in coverage.items() if cov >= 0.95)
    log(f"eligible (>=95% grid coverage): {len(eligible_static)}/"
        f"{len(bars_raw)} tickers")

    aligned: dict[str, list[float]] = {}
    dropped_leading_gap = []
    for t in eligible_static:
        d = bars_raw[t]
        vals, last = [], None
        for g in grid:
            if g in d:
                last = d[g][3]
            vals.append(last)
        if all(v is not None and v > 0 for v in vals):
            aligned[t] = vals
        else:
            dropped_leading_gap.append(t)
    if dropped_leading_gap:
        log(f"dropped (leading gap on grid, mirrors screening): "
            f"{dropped_leading_gap}")
    symbols = sorted(aligned)

    rebal = month_rebalances([g for g in grid if g >= TRADE_START_S])
    log(f"tradeable symbols: {len(symbols)}; rebalance months: {len(rebal)} "
        f"({rebal[0]} .. {rebal[-1]})")
    return grid, eligible_static, aligned, symbols, rebal, bars_raw, coverage

# ---------------------------------------------------------------------------
# strategy (mirrors docs/research/scratch/xmom_1.py XMOMStrategy)
# ---------------------------------------------------------------------------

class XMOMStrategy:
    """Target-weight cross-sectional momentum, monthly rebalance.

    Duck-typed like common.TargetStrategy (needs .symbols + .on_bar):
    compute target fraction-of-equity per symbol; emit LONG/SHORT/EXIT only
    on change; skip symbols with no bar that day (no bar -> no signal
    possible — this is the spec's "missing a bar on the rebalance date
    itself -> ineligible that month" rule, mirrored from screening).
    """

    def __init__(self, symbols: list[str], grid: list[str],
                 aligned: dict[str, list[float]], rebal: list[str]):
        from trade_backtest.models import Signal, SignalAction
        self.symbols = [s.strip().upper() for s in symbols]
        if not self.symbols:
            raise ValueError("strategy needs at least one symbol")
        self._Signal = Signal
        self._SA = SignalAction
        self._grid_idx = {d: i for i, d in enumerate(grid)}
        self._aligned = aligned
        self._rebal = set(rebal)
        self.targets: dict[str, float] = {}
        self._emitted: dict[str, float] = {}
        self._cur: dict[str, float] = {}
        self.n_signals = 0
        self.rebal_stats: list[dict] = []

    def compute_targets(self, timestamp, closes):
        d = timestamp.strftime("%Y-%m-%d")
        if d in self._rebal:
            i = self._grid_idx[d]
            scored = []
            for t, cs in self._aligned.items():
                r = trailing_return(cs[:i + 1], LOOKBACK, skip=SKIP)
                if r is not None:
                    scored.append((r, t))
            scored.sort()  # ascending by formation return
            n = max(1, int(len(scored) * DECILE))
            longs = [t for _, t in scored[-n:]]
            shorts = [t for _, t in scored[:n]]
            traded = bool(longs and shorts)
            if traded:  # empty early in history -> hold current positions
                wl, ws = GROSS_PER_LEG / len(longs), GROSS_PER_LEG / len(shorts)
                self._cur = {t: wl for t in longs}
                self._cur.update({t: -ws for t in shorts})
            self.rebal_stats.append({"date": d, "n_scored": len(scored),
                                     "n_leg": n if traded else 0,
                                     "traded": traded})
        return {s: self._cur.get(s, 0.0) for s in self.symbols}

    def on_bar(self, timestamp, bars):
        new = self.compute_targets(timestamp, {})
        self.targets = {s: new.get(s, 0.0) for s in self.symbols}
        SA, Signal = self._SA, self._Signal
        out = []
        for sym in self.symbols:
            if sym not in bars:
                continue  # no bar -> no signal possible
            old = self._emitted.get(sym, 0.0)
            newt = self.targets[sym]
            changed = (old == 0.0) != (newt == 0.0) or (
                old != 0.0 and newt != 0.0 and abs(newt - old) > 1e-9)
            if changed:
                action = SA.LONG if newt > 0 else (SA.SHORT if newt < 0 else SA.EXIT)
                out.append(Signal(symbol=sym, timestamp=timestamp, action=action))
                self._emitted[sym] = newt
                self.n_signals += 1
        return out


class TargetsSizer:
    """Size = strategy.targets[symbol] * equity / price. EXIT -> flat.

    Mirrors common.TargetsSizer.
    """

    def __init__(self, strategy: XMOMStrategy):
        from trade_backtest.models import SignalAction
        from trade_backtest.portfolio import PositionSizer

        class _Sizer(PositionSizer):
            def size(self, signal, price, portfolio):
                if signal.action is SignalAction.EXIT:
                    return 0.0
                tgt = strategy.targets.get(signal.symbol, 0.0)
                if tgt == 0.0 or price <= 0:
                    return 0.0
                return tgt * portfolio.equity / price

        self._sizer = _Sizer()

    def __getattr__(self, name):
        return getattr(self._sizer, name)


# ---------------------------------------------------------------------------
# backtest
# ---------------------------------------------------------------------------

def run_backtest(symbols: list[str], bars_raw: dict[str, dict],
                 grid: list[str], aligned: dict[str, list[float]],
                 rebal: list[str], borrow_bps: float):
    """One full engine run. Engine bars: actual bars only, 2019-01-01..END_S.

    Timestamps are normalized to UTC midnight per calendar date so every
    trading day is exactly one engine timestamp (yfinance daily stamps carry
    time-of-day/DST quirks that would split a day into two buckets).
    """
    import trade_backtest.costs as tbc
    import trade_backtest.data as tbd
    import trade_backtest.engine as tbe
    import trade_backtest.execution as tbx
    import trade_backtest.portfolio as tbp
    from trade_backtest.models import Bar as EngineBar

    engine_bars = []
    for s in symbols:
        for ds, (o, h, l, c, v) in bars_raw[s].items():
            if not (TRADE_START_S <= ds < END_S):
                continue
            ts = datetime(int(ds[0:4]), int(ds[5:7]), int(ds[8:10]),
                          tzinfo=timezone.utc)
            engine_bars.append(EngineBar(
                symbol=s, timestamp=ts, open=float(o), high=float(h),
                low=float(l), close=float(c), volume=float(v)))
    engine_bars.sort(key=lambda b: (b.timestamp, b.symbol))

    strategy = XMOMStrategy(symbols, grid, aligned, rebal)
    cost_model = tbc.CostModel(
        commission=tbx.PercentCommission(COMM_BPS / 10_000.0),
        slippage_entry_bps=0.0,
        slippage_exit_bps=0.0,
        half_spread_bps=0.0,
        borrow_cost_annual_bps=borrow_bps,
    )
    engine = tbe.BacktestEngine(
        data=tbd.ListDataHandler(engine_bars),
        strategy=strategy,
        portfolio=tbp.Portfolio(INITIAL_CASH, TargetsSizer(strategy),
                                cost_model=cost_model),
        execution=tbx.SimulatedExecutionHandler(cost_model=cost_model),
        adjustment_basis="pre_adjusted",  # bars already split/div adjusted
        adjustment_note="yfinance daily OHLCV, split- and dividend-adjusted "
                        "closes; basis=pre_adjusted (mirrors Phase B screening)",
    )
    result = engine.run()
    return result, strategy


def equity_returns(result):
    """Daily (date, return) series from the engine equity curve."""
    pts = result.equity_curve
    dates = [p.timestamp.date() for p in pts]
    eq = [p.equity for p in pts]
    rets = [eq[i] / eq[i - 1] - 1.0 for i in range(1, len(eq))]
    return dates[1:], rets

# ---------------------------------------------------------------------------
# walk-forward on the daily return series
# ---------------------------------------------------------------------------

def walk_forward_folds(dates: list[date], rets: list[float]):
    """60-month train / 12-month test / 12-month step, 21-trading-day embargo.

    Folds are defined on calendar months over the pre-registered span
    2015-01-01..2026-09-25 (no parameters are fitted, so walk-forward tests
    regime stability, not tuning):
      fold k: train months [2015-01+12k, +60), test months [2020-01+12k, +12)
      test bars = trading days in the test months strictly after
      (last train bar + 21 trading days). Rebalance months inside the embargo
      gap belong to neither fold.
    The final fold's test window is partial (2026-01..2026-09) — documented.
    """
    from trade_overfit.metrics import max_drawdown, sharpe_ratio, total_return

    months = [(d.year, d.month) for d in dates]
    folds = []
    k = 0
    while True:
        train_lo = add_months((2015, 1), 12 * k)
        train_hi = add_months(train_lo, 60)
        test_lo = add_months((2020, 1), 12 * k)
        if test_lo > (2026, 9):
            break
        test_hi = min(add_months(test_lo, 12), (2026, 10))
        train_idx = [i for i, m in enumerate(months) if train_lo <= m < train_hi]
        if not train_idx:
            k += 1
            continue
        train_last = train_idx[-1]
        test_idx = [i for i, m in enumerate(months)
                    if test_lo <= m < test_hi and i > train_last + EMBARGO_DAYS]
        if not test_idx:
            break
        te = [rets[i] for i in test_idx]
        folds.append({
            "fold": k,
            "train_start": dates[train_idx[0]].isoformat(),
            "train_end": dates[train_idx[-1]].isoformat(),
            "train_months": f"{train_lo[0]:04d}-{train_lo[1]:02d}.."
                            f"{train_hi[0]:04d}-{train_hi[1]:02d}",
            "test_start": dates[test_idx[0]].isoformat(),
            "test_end": dates[test_idx[-1]].isoformat(),
            "test_months": f"{test_lo[0]:04d}-{test_lo[1]:02d}.."
                           f"{test_hi[0]:04d}-{test_hi[1]:02d}",
            "oos_sharpe": sharpe_ratio(te, periods=PERIODS_PER_YEAR),
            "oos_annualized": None,  # filled below (needs import-free math)
            "oos_return": total_return(te),
            "oos_max_drawdown": max_drawdown(te)["max_drawdown"],
            "n_oos_bars": len(te),
            "_idx": test_idx,
        })
        k += 1

    from trade_overfit.metrics import annualized_return
    for f in folds:
        te = [rets[i] for i in f["_idx"]]
        f["oos_annualized"] = annualized_return(te, periods=PERIODS_PER_YEAR)
        del f["_idx"]
    return folds


def concat_oos(dates: list[date], rets: list[float], folds: list[dict]):
    """Concatenated OOS series = the gated series (folds are disjoint)."""
    idx = []
    for f in folds:
        i0 = dates.index(date.fromisoformat(f["test_start"]))
        i1 = dates.index(date.fromisoformat(f["test_end"])) + 1
        idx.extend(range(i0, i1))
    idx = sorted(set(idx))
    return [dates[i] for i in idx], [rets[i] for i in idx]


# ---------------------------------------------------------------------------
# benchmark: 3-month T-bill total return from ^IRX
# ---------------------------------------------------------------------------

def benchmark_daily_rf(irx_bars: list, oos_dates: list[date]):
    """rf_daily = y/100/252 per trading day (simple interest, documented).

    ^IRX missing on a date -> carry the last observation forward. Leading
    missing (no prior observation) -> 0. Returns (series, note).
    """
    by_date: dict[str, float] = {}
    for ts, o, h, l, c, v in irx_bars:
        ds = dstr(ts)
        if c and c > 0:
            by_date[ds] = c
    if not by_date:
        return None, "fallback_0pct_cash"
    out, last = [], None
    for d in oos_dates:
        y = by_date.get(d.isoformat())
        if y is not None:
            last = y
        out.append((last if last is not None else 0.0) / 100.0 / 252.0)
    return out, "irx_forward_filled"


def annualized(total_return: float, n_bars: int, periods: int = 252):
    return (1.0 + total_return) ** (periods / n_bars) - 1.0 if n_bars else None


# ---------------------------------------------------------------------------
# gates
# ---------------------------------------------------------------------------

def compute_gates(oos_dates, oos_rets, folds, irx_bars):
    from trade_overfit._stats import median
    from trade_overfit.dsr import dsr_from_returns
    from trade_overfit.gates import evaluate_gates, preset_gates
    from trade_overfit.metrics import (
        annualized_return, calmar_ratio, max_drawdown, sortino_ratio,
    )
    from trade_overfit.regimes import regime_report

    dsr = dsr_from_returns(oos_rets, trial_sharpes=TRIAL_SHARPES,
                           periods=PERIODS_PER_YEAR)
    fold_sharpes = [f["oos_sharpe"] for f in folds if f["oos_sharpe"] is not None]
    dd = max_drawdown(oos_rets)
    reg = regime_report(oos_rets, periods=PERIODS_PER_YEAR)  # desk vol-regime default

    rf_daily, bench_note = benchmark_daily_rf(irx_bars, oos_dates)
    if rf_daily is None:
        bench_total, bench_ann = 0.0, 0.0
        log("WARNING: ^IRX unfetchable -> 0% cash benchmark fallback (pre-registered)")
    else:
        bench_total = math.prod(1.0 + r for r in rf_daily) - 1.0
        bench_ann = annualized(bench_total, len(rf_daily), PERIODS_PER_YEAR)
    strat_ann = annualized_return(oos_rets, periods=PERIODS_PER_YEAR)
    excess = strat_ann - bench_ann

    evidence = {
        "dsr": dsr["dsr"],
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
        "dsr_detail": dsr,
        "regimes": reg,
        "n_folds_with_sharpe": len(fold_sharpes),
        "strategy_annualized": strat_ann,
        "benchmark_annualized": bench_ann,
        "benchmark_note": bench_note,
        "benchmark_total": bench_total,
    }

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def rebal_stats_by_year(rebal_stats: list[dict]) -> dict:
    by_year: dict[str, list[dict]] = {}
    for s in rebal_stats:
        by_year.setdefault(s["date"][:4], []).append(s)
    out = {}
    for y in sorted(by_year):
        rows = by_year[y]
        scored = [r["n_scored"] for r in rows]
        legs = [r["n_leg"] for r in rows if r["traded"]]
        out[y] = {
            "rebalances": len(rows),
            "months_traded": sum(1 for r in rows if r["traded"]),
            "mean_scored": round(sum(scored) / len(scored), 1),
            "mean_n_per_leg": round(sum(legs) / len(legs), 1) if legs else 0,
        }
    return out


def main() -> int:
    smoke = "--smoke" in sys.argv
    t0 = datetime.now(timezone.utc).isoformat()
    log(f"starting (smoke={smoke}); spec commit {SPEC_COMMIT}")

    universe = load_universe(UNIVERSE_PATH)
    log(f"universe: {len(universe)} tickers ({UNIVERSE_PATH})")
    fetch_list = universe + [IRX]

    if smoke:
        tickers = [f"T{i:03d}" for i in range(40)]
        bars_by_ticker = synthetic_bars(tickers + [GRID_SYMBOL, IRX])
        universe = tickers
    else:
        bars_by_ticker = fetch_bars(fetch_list)

    grid, eligible_static, aligned, symbols, rebal, bars_raw, coverage = \
        build_panel(bars_by_ticker)

    # ---- spec run: 50 bps/yr borrow -------------------------------------
    log(f"running backtest (borrow={BORROW_BPS} bps/yr, t+1 open fills, "
        f"{COMM_BPS} bps/side)")
    t_run = time.time()
    result, strategy = run_backtest(symbols, bars_raw, grid, aligned, rebal,
                                    BORROW_BPS)
    log(f"backtest done in {time.time() - t_run:.0f}s: "
        f"{len(result.trades)} trades, {strategy.n_signals} signals, "
        f"final equity {result.equity_curve[-1].equity:,.2f}")

    dates, rets = equity_returns(result)
    log(f"daily return series: {len(rets)} bars "
        f"({dates[0]} .. {dates[-1]})")

    log("walk-forward (60-month train / 12-month test / 12-month step / "
        f"{EMBARGO_DAYS}d embargo)")
    folds = walk_forward_folds(dates, rets)
    log(f"{len(folds)} folds")
    oos_dates, oos_rets = concat_oos(dates, rets, folds)
    log(f"OOS series: {len(oos_rets)} bars ({oos_dates[0]} .. {oos_dates[-1]})")

    irx_bars = bars_by_ticker.get(IRX, [])
    log(f"^IRX bars: {len(irx_bars)}")
    log("gates (trade-overfit standard preset, DSR n_trials=7)")
    g = compute_gates(oos_dates, oos_rets, folds, irx_bars)
    for gate in g["gates"]:
        v = gate["value"]
        vs = f"{v:.4f}" if isinstance(v, float) else str(v)
        log(f"  {gate['name']}: {vs} "
            f"({'PASS' if gate['passed'] else 'FAIL'})")
    log(f"verdict: {g['verdict']}")

    # ---- borrow sensitivity (report-only; spec stays 50 bps) -------------
    borrow_sens = {}
    for bps in (0.0, 200.0):
        log(f"borrow-sensitivity re-run (borrow={bps} bps/yr, report-only)")
        r2, _ = run_backtest(symbols, bars_raw, grid, aligned, rebal, bps)
        d2, r2rets = equity_returns(r2)
        _, oos2 = concat_oos(d2, r2rets, walk_forward_folds(d2, r2rets))
        from trade_overfit.metrics import (
            annualized_return, max_drawdown, sharpe_ratio)
        borrow_sens[str(bps)] = {
            "oos_sharpe": sharpe_ratio(oos2, periods=PERIODS_PER_YEAR),
            "oos_annualized": annualized_return(oos2, periods=PERIODS_PER_YEAR),
            "oos_max_drawdown": max_drawdown(oos2)["max_drawdown"],
            "final_equity": r2.equity_curve[-1].equity,
        }
    bs50 = {
        "oos_sharpe": sharpe_ratio(oos_rets, periods=PERIODS_PER_YEAR),
        "oos_annualized": g["strategy_annualized"],
        "oos_max_drawdown": max_drawdown(oos_rets)["max_drawdown"],
        "final_equity": result.equity_curve[-1].equity,
    }
    borrow_sens["50.0"] = bs50

    # ---- evidence.json ----------------------------------------------------
    bundle = {
        "strategy": "XMOM-1",
        "trial": 3,
        "pre_registration_commit": SPEC_COMMIT,
        "smoke": smoke,
        "run_started_utc": t0,
        "run_finished_utc": datetime.now(timezone.utc).isoformat(),
        "data": {
            "source": "synthetic" if smoke else
                      "yfinance daily OHLCV via trade-data-equities "
                      "EquitiesDataClient + YFinanceProvider, adjusted=True",
            "range": [START_S, END_S],
            "range_note": "provider uses [start, end); end=2026-09-26 includes "
                          "all 2026-09-25 bars, matching the pre-registered "
                          "'2015-01-01 through 2026-09-25'",
            "universe_file": "docs/research/evidence/universe.txt",
            "universe_tickers": len(universe),
            "grid": f"{GRID_SYMBOL} trading days",
            "grid_bars": len(grid),
            "grid_span": [grid[0], grid[-1]],
            "cache": "evidence/cache/ (DiskCache, 365d TTL)",
        },
        "universe_counts": {
            "universe": len(universe),
            "eligible_ge95pct": len(eligible_static),
            "tradeable_no_leading_gap": len(symbols),
            "coverage_failures": sorted(
                t for t, cov in coverage.items() if cov < 0.95),
            "rebal_stats_by_year": rebal_stats_by_year(strategy.rebal_stats),
        },
        "costs": {
            "commission_bps_per_side": COMM_BPS,
            "borrow_cost_annual_bps": BORROW_BPS,
            "fills": "t+1 open (SimulatedExecutionHandler)",
            "adjustment_basis": "pre_adjusted",
        },
        "walk_forward": {
            "train": "60 calendar months", "test": "12 calendar months",
            "step": "12 calendar months",
            "embargo_trading_days": EMBARGO_DAYS,
            "periods_per_year": PERIODS_PER_YEAR,
            "n_folds": len(folds),
            "n_oos_bars": len(oos_rets),
            "oos_span": [oos_dates[0].isoformat(), oos_dates[-1].isoformat()],
            "folds": folds,
        },
        "benchmark": {
            "source": g["benchmark_note"],
            "construction": "rf_daily = ^IRX_close/100/252 per trading day "
                            "(simple interest); ^IRX gaps forward-filled; "
                            "unfetchable ^IRX -> 0% cash (pre-registered fallback)",
            "annualized": g["benchmark_annualized"],
            "total": g["benchmark_total"],
        },
        "gates": g["gates"],
        "evidence": g["evidence"],
        "dsr_detail": g["dsr_detail"],
        "dsr_trial_sharpes": TRIAL_SHARPES,
        "dsr_n_trials": len(TRIAL_SHARPES),
        "regimes": g["regimes"],
        "strategy_annualized_oos": g["strategy_annualized"],
        "borrow_sensitivity_report_only": borrow_sens,
        "final_equity": result.equity_curve[-1].equity,
        "n_trades": len(result.trades),
        "n_signals": strategy.n_signals,
        "engine_metrics": {k: v for k, v in dict(result.metrics).items()},
    }
    out_path = os.path.join(OUT_DIR, f"evidence{'_smoke' if smoke else ''}.json")
    with open(out_path, "w") as fh:
        json.dump(bundle, fh, indent=2, default=str)
    log(f"evidence -> {out_path}")

    # ---- report.md ---------------------------------------------------------
    L = [
        "# XMOM-1 validation report (trial 3 of 3)",
        "",
        f"- Pre-registration: commit {SPEC_COMMIT} (frozen spec, before any OHLC pull)",
        f"- Data: {bundle['data']['source']}, {START_S}..{END_S}",
        f"- Universe: {len(universe)} tickers; {len(eligible_static)} eligible "
        f"(>=95% {GRID_SYMBOL}-grid coverage); {len(symbols)} tradeable "
        f"(no leading gap, mirrors screening)",
        f"- Costs: {COMM_BPS} bps/side + {BORROW_BPS} bps/yr borrow on shorts; "
        f"t+1 open fills; no stops, no turnover control",
        f"- Walk-forward: 60-month train / 12-month test / 12-month step / "
        f"{EMBARGO_DAYS}d embargo, {len(folds)} folds; gated series = "
        f"concatenated OOS ({len(oos_rets)} bars)",
        f"- DSR n_trials=7 (Phase B in-sample Sharpes "
        f"{', '.join(str(x) for x in TRIAL_SHARPES)}; XMOM-1 was #3)",
        f"- Benchmark: {g['benchmark_note']} "
        f"(annualized {g['benchmark_annualized']:.4f} over OOS span)",
        "",
        "## Gates (trade-overfit standard preset)",
        "",
        "| gate | value | threshold | result |",
        "|---|---|---|---|",
    ]
    for gate in g["gates"]:
        v = gate["value"]
        vs = f"{v:.4f}" if isinstance(v, float) else str(v)
        L.append(f"| {gate['name']} | {vs} | {gate['op']} {gate['threshold']} | "
                 f"{'PASS' if gate['passed'] else 'FAIL'} |")
    L += [
        "",
        f"**Verdict: {g['verdict']}**",
        "",
        "## Walk-forward folds (OOS)",
        "",
        "| fold | test window | OOS Sharpe | OOS ann. | OOS return | OOS maxDD |",
        "|---|---|---|---|---|---|",
    ]
    for fl in folds:
        sh = fl["oos_sharpe"]
        shs = f"{sh:.3f}" if sh is not None else "n/a"
        L.append(
            f"| {fl['fold']} | {fl['test_start']}..{fl['test_end']} "
            f"({fl['test_months']}) | {shs} | {fl['oos_annualized']:.4f} | "
            f"{fl['oos_return']:.4f} | {fl['oos_max_drawdown']:.4f} |")
    L += [
        "",
        f"- Strategy annualized (OOS): {g['strategy_annualized']:.4f}",
        f"- Benchmark annualized (OOS): {g['benchmark_annualized']:.4f}",
        f"- Excess vs benchmark (after costs): "
        f"{g['evidence']['excess_return_vs_benchmark_after_costs']:.4f}",
        f"- DSR detail: sharpe_hat={g['dsr_detail']['sharpe_hat']:.4f}, "
        f"n_obs={g['dsr_detail']['n_obs']}, n_trials={g['dsr_detail']['n_trials']}, "
        f"expected_sharpe_under_null="
        f"{g['dsr_detail']['expected_sharpe_under_null']:.4f}",
        f"- Regime splits (trailing-63d vol vs median): "
        f"{json.dumps(g['regimes']['regimes'], default=str)}; "
        f"worst={g['regimes']['worst_regime']} "
        f"({g['evidence']['worst_regime_sharpe']})",
        f"- Final equity: {bundle['final_equity']:,.2f} "
        f"(from {INITIAL_CASH:,.2f}); {bundle['n_trades']} trades, "
        f"{bundle['n_signals']} signals",
        "",
        "## Borrow sensitivity (report-only; spec stays 50 bps/yr)",
        "",
        "| borrow | OOS Sharpe | OOS ann. | OOS maxDD | final equity |",
        "|---|---|---|---|---|",
    ]
    for bps in ("0.0", "50.0", "200.0"):
        s = borrow_sens[bps]
        L.append(f"| {bps} bps | {s['oos_sharpe']:.3f} | "
                 f"{s['oos_annualized']:.4f} | {s['oos_max_drawdown']:.4f} | "
                 f"{s['final_equity']:,.2f} |")
    L += [
        "",
        "## Benchmark construction note",
        "",
        f"- Source used: **{g['benchmark_note']}**.",
        "- ^IRX daily closes via trade-data-equities (same pull as the "
        "equity bars); rf_daily = y/100/252 per trading day (simple "
        "interest, documented in the pre-registration); ^IRX gaps "
        "forward-filled; a leading gap with no prior observation counts "
        "as 0.",
        "- Pre-registered fallback (decided before results): if ^IRX could "
        "not be fetched at all, benchmark = 0% cash. "
        + ("**The fallback was NOT needed — ^IRX fetched.**"
           if g["benchmark_note"] == "irx_forward_filled"
           else "**The fallback WAS used — ^IRX was unfetchable.**"),
        "",
        "## Honest flags (from the pre-registration, restated)",
        "",
        "- **Survivorship bias**: the universe is today's large-cap "
        "constituents; delisted names are absent, which flatters momentum "
        "(dead losers are missing from the short leg's history). "
        "Documented in Phase B and the spec — the gates judge whether the "
        "premium survives it, not whether the bias exists.",
        "- **Momentum-crash profile**: the 25.3% in-sample screening maxDD "
        "already exceeds the 15% gate; a crash inside the OOS window is the "
        "binding failure mode.",
        "- **Momentum-family exposure**: shared with trial 1 (DON-20/10-ATR). "
        "The diversification is structural (cross-sectional + "
        "dollar-neutral + monthly), not categorical.",
        "- **Borrow at 50 bps/yr is a general-collateral assumption**; "
        "hard-to-borrow names in the short leg cost more — see the "
        "borrow-sensitivity table above.",
        "- **t+1 fill whipsaw**: signals on the rebalance close fill at the "
        "next open; violent reversals on rebalance months are the known "
        "enemy (stated in Phase A).",
        "- No turnover control: full monthly reconstitution maximizes cost "
        "drag; the screening's 1,275 trades are the evidence this is "
        "affordable, not optimal.",
        "",
        "## Literal-reading choices (ambiguities resolved, never optimized)",
        "",
        "1. `close[t-21]` / `close[t-273]` are taken on the SPY trading-day "
        "grid; missing bars inside the window are causally forward-filled "
        "(mirrors screening `aligned_closes`). Tickers with any leading gap "
        "on the grid are excluded from the tradeable set — this is the "
        "screening implementation mirrored literally; it is stricter than "
        "the >=95% rule and only affects tickers listed after 2015.",
        "2. 'Ticker missing a bar on the rebalance date itself -> ineligible "
        "that month' is implemented as in screening: no bar -> no signal "
        "emitted for that symbol that day (an existing position is left "
        "untouched rather than force-exited).",
        "3. Eligibility (>=95% coverage) is static over 2015-01-01..2026-09-25 "
        "per the frozen spec — the same lookahead the screening had, "
        "documented as part of the survivorship-bias flag.",
        "4. Engine timestamps are normalized to UTC midnight per calendar "
        "date (yfinance daily stamps carry time-of-day/DST quirks); one "
        "engine timestamp = one trading day.",
        "5. Walk-forward folds are calendar-month blocks; the embargo is 21 "
        "trading days after the last train bar; test bars are trading days "
        "in the test months strictly after the embargo.",
        "6. Borrow sensitivity re-runs the full engine at 0/200 bps/yr — "
        "report-only; the 50 bps spec run is the gated one.",
        "",
        "## Data provenance",
        "",
        f"- Raw bars: yfinance via trade-data-equities "
        f"`EquitiesDataClient` + `YFinanceProvider`, `Timeframe.DAILY`, "
        f"`adjusted=True`, cached under `evidence/cache/` "
        f"(per-ticker manifest: `evidence/fetch_manifest.json`).",
        f"- Grid: {len(grid)} {GRID_SYMBOL} trading days, "
        f"{grid[0]}..{grid[-1]}.",
        f"- Rebalance months traded: "
        f"{sum(1 for s in strategy.rebal_stats if s['traded'])}/"
        f"{len(strategy.rebal_stats)} "
        f"(empty-leg months, if any, held positions per spec).",
    ]
    report_path = os.path.join(OUT_DIR, f"report{'_smoke' if smoke else ''}.md")
    with open(report_path, "w") as fh:
        fh.write("\n".join(L) + "\n")
    log(f"report -> {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
