"""Trial 3 candidate B (TSMOM-CR) validation — candidate B re-run, valid path.

Frozen pre-registered spec: docs/validation/tsmom-cr/PRE-REGISTRATION.md
(commits 42ecab2/425745b in this repo). A first attempt was archived as INVALID
under docs/validation/tsmom-cr/invalid_runs/2026-09-27_zero-oos-folds/ — root
cause there: the Kraken fallback could not serve the span (its public API only
serves ~720 recent daily candles), so ZERO walk-forward folds fit the frozen
104w/26w/26w geometry and the gated OOS series was empty. This script is the
valid re-run per the frozen-spec resolution documented in report.md ("Spec
interpretation note"): validate on the primary venue Binance.US under the spec's
own data rule — "Data holes: a day with no bar = hold (no signal change),
exactly as screened" — which is also exactly how Phase B screened it
(docs/research/scratch/tsmom_cr.py ran on this same gappy Binance.US series).

Implementation notes (mechanical choices only; spec is untouched):

* Calendar-day-indexed simulation. Crypto trades 24/7, so every calendar day
  is a period. A "hole day" (venue served no bar) = hold: signals frozen,
  positions frozen, equity unchanged -> daily return 0. Mark-to-market on a
  bar day uses the most recent available close as the reference, so the P&L
  accrued while held through a hole is realized on the first post-hole bar
  day. Positions are NOT liquidated across holes (literal "hold").
* Signals per name per day t: computed only on days with bars (needs 91 prior
  bars of actual data); hole days inherit the prior day's signal. Breakout =
  close[t] > max(high[t-90..t-1]) over the 90 prior ACTUAL bars; mom50 =
  close[t] > close[t-50] (50 actual bars back). Long if either; flat otherwise.
* Fills at the next day's open (t->t+1). If t+1 is a hole day (only possible at
  hole boundaries), the fill is deferred to the next day with a bar, at that
  day's open. Order of operations on a bar day: (1) execute pending fills at
  the open; (2) monthly sizing refresh at the close (first bar day of a new
  calendar month, open position, no pending order); (3) compute the signal at
  the close for next-day fills.
* Sizing: notional_i = min(0.10 / sigma_ann_i, 1.0) x equity; sigma_ann =
  stdev(trailing 60 ONE-DAY bar-to-bar returns, i.e. consecutive bars one
  calendar day apart — gap-spanning returns across the hole are excluded from
  the vol estimate) x sqrt(365). Refreshed on calendar-month boundaries and on
  fresh entries only (not daily).
* Costs: 25 bps/side all-in on every fill (plus report-only 10/50 bps runs).
* Why a bespoke daily simulator rather than the trade-backtest engine: the
  engine operates on available bars and cannot represent calendar-day-indexed
  zero-return hold days with frozen positions without synthetic bars; the
  frozen spec mandates the calendar-day construction ("calendar-day folds are
  deliberate"). The mr-5m template pattern is followed (fetch -> simulate ->
  walk-forward on the calendar-day return series -> trade-overfit gates).

Walk-forward: 104-week train / 26-week test / 26-week step, 5-calendar-day
embargo, on the calendar-day return series. All annualization with periods=365
(crypto 24/7; per the spec this is deliberate).

Gates: trade-overfit v0.2.0 `evaluate_gates(evidence, preset_gates("standard"))`
with evidence keys dsr, median_oos_sharpe, max_drawdown, worst_regime_sharpe,
excess_return_vs_benchmark_after_costs, sortino, calmar. DSR:
dsr_from_returns(oos_rets,
    trial_sharpes=[0.798, 0.485, 0.413, 0.379, 0.106, -0.097, -0.337],
    periods=365)  (the 7 screened Phase B in-sample sharpes; n_trials = 7).

Outputs: docs/validation/tsmom-cr/{evidence.json, report.md} (overwrites the
INVALID-stamped files from the first attempt; the invalid run stays archived).

Usage:
  cd <repo-root> && PYTHONPATH=src python3 docs/validation/tsmom-cr/run_validation.py
"""

from __future__ import annotations

import json
import math
import sys
import time
from datetime import date, datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# pre-registered constants (from PRE-REGISTRATION.md — do not change)
# ---------------------------------------------------------------------------

START = date(2019, 9, 17)
END_EXCL = date(2026, 9, 26)   # provider uses [start, end); includes 2026-09-25
SYMBOLS = ["BTC/USD", "ETH/USD"]
INITIAL_CASH = 100_000.0
TARGET_VOL = 0.10
NOTIONAL_CAP = 1.0
VOL_WINDOW = 60
WARMUP_BARS = 91               # 90 prior bars + today
DONCHIAN_LOOKBACK = 90
MOM_LOOKBACK = 50

TRAIN_DAYS = 728               # 104 weeks
TEST_DAYS = 182                # 26 weeks
STEP_DAYS = 182                # 26 weeks
EMBARGO_DAYS = 5
PERIODS = 365                  # crypto 24/7

COST_BPS = 25.0                # 25 bps/side all-in
TRIAL_SHARPES = [0.798, 0.485, 0.413, 0.379, 0.106, -0.097, -0.337]  # n=7

OUT_DIR = "docs/validation/tsmom-cr"
PRE_REG_COMMITS = "42ecab2/425745b"


def log(msg: str) -> None:
    print(f"[tsmom-cr] {msg}", flush=True)


# ---------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------

def fetch_bars() -> dict[str, dict[date, tuple]]:
    """Pull D1 bars for both symbols through the released Binance.US provider."""
    try:
        from trade_data_crypto import BinanceUSPublicProvider, Timeframe
    except ImportError as exc:
        raise SystemExit(
            "trade-data-crypto v0.2.0+ with BinanceUSPublicProvider is required. "
            f"Import failed: {exc}"
        ) from exc
    provider = BinanceUSPublicProvider()
    out: dict[str, dict[date, tuple]] = {}
    for symbol in SYMBOLS:
        t0 = time.time()
        bars = provider.get_bars(symbol, Timeframe.D1, start=START, end=END_EXCL)
        dt = time.time() - t0
        per_day: dict[date, tuple] = {}
        for b in bars:
            d = b.timestamp.date()
            per_day[d] = (float(b.open), float(b.high), float(b.low),
                          float(b.close), float(b.volume or 0.0))
        ds = sorted(per_day)
        log(f"{symbol}: {len(bars)} bars in {dt:.1f}s ({ds[0]} .. {ds[-1]})")
        out[symbol] = per_day
    return out


def calendar_days() -> list[date]:
    days, d = [], START
    while d < END_EXCL:
        days.append(d)
        d += timedelta(days=1)
    return days


# ---------------------------------------------------------------------------
# spec-literal daily simulator over the calendar-day-indexed series
# ---------------------------------------------------------------------------

class SimResult:
    def __init__(self):
        self.dates: list[date] = []
        self.rets: list[float] = []
        self.equity: list[float] = []
        self.n_fills = 0
        self.n_hole_days = 0
        self.trades: list[dict] = []  # fill log


def simulate(bars: dict[str, dict[date, tuple]], cost_bps: float) -> SimResult:
    days = calendar_days()
    cost = cost_bps / 10_000.0

    # per-symbol bar arrays for fast lookups
    info: dict[str, dict] = {}
    for s in SYMBOLS:
        bdates = sorted(bars[s])
        info[s] = {
            "dates": bdates,
            "idx": {d: i for i, d in enumerate(bdates)},
            "opens": [bars[s][d][0] for d in bdates],
            "highs": [bars[s][d][1] for d in bdates],
            "closes": [bars[s][d][3] for d in bdates],
        }

    cash = INITIAL_CASH
    shares = {s: 0.0 for s in SYMBOLS}
    signal = {s: False for s in SYMBOLS}      # inherited signal state
    frac = {s: 0.0 for s in SYMBOLS}          # vol-target fraction per name
    pending: dict[str, dict | None] = {s: None for s in SYMBOLS}  # {"kind","frac"}
    last_ym = {s: None for s in SYMBOLS}
    last_close = {s: None for s in SYMBOLS}   # mark reference (frozen on holes)

    def equity_at(price_of: dict[str, float | None]) -> float:
        eq = cash
        for s in SYMBOLS:
            if shares[s] and price_of.get(s) is not None:
                eq += shares[s] * price_of[s]
        return eq

    def one_day_vol_rets(s: str, i: int) -> list[float]:
        """Trailing up-to-60 one-calendar-day bar-to-bar returns ending at bar i.

        Gap-spanning returns (across the data hole) are excluded — they are not
        daily returns and would corrupt the vol estimate.
        """
        rets, j = [], i
        bdates = info[s]["dates"]
        closes = info[s]["closes"]
        while j > 0 and len(rets) < VOL_WINDOW:
            if (bdates[j] - bdates[j - 1]).days == 1:
                rets.append(closes[j] / closes[j - 1] - 1.0)
            j -= 1
        return rets

    def size_frac(s: str, i: int) -> float:
        rets = one_day_vol_rets(s, i)
        if len(rets) < 2:
            return 0.0
        m = sum(rets) / len(rets)
        var = sum((r - m) ** 2 for r in rets) / (len(rets) - 1)
        vol = math.sqrt(var) * math.sqrt(PERIODS)
        return min(TARGET_VOL / vol, NOTIONAL_CAP) if vol > 0 else 0.0

    res = SimResult()
    prev_eq = INITIAL_CASH

    for d in days:
        day_bars: dict[str, tuple] = {}
        for s in SYMBOLS:
            if d in bars[s]:
                day_bars[s] = bars[s][d]

        # (1) pending fills at the open of any bar day
        if day_bars:
            open_px = {s: day_bars[s][0] for s in day_bars}
            mark = {s: open_px.get(s, last_close[s]) for s in SYMBOLS}
            eq_open = equity_at(mark)
            for s in SYMBOLS:
                p = pending[s]
                if p is None or s not in day_bars:
                    continue
                px = open_px[s]
                if p["kind"] == "enter":
                    if eq_open > 0 and px > 0:
                        notion = p["frac"] * eq_open
                        q = notion / px
                        fee = notion * cost
                        cash -= notion + fee
                        shares[s] += q
                        res.n_fills += 1
                        res.trades.append({"date": d.isoformat(), "symbol": s,
                                           "side": "BUY", "price": px,
                                           "notional": notion, "fee": fee})
                else:  # exit
                    if shares[s] > 0:
                        notion = shares[s] * px
                        fee = notion * cost
                        cash += notion - fee
                        res.n_fills += 1
                        res.trades.append({"date": d.isoformat(), "symbol": s,
                                           "side": "SELL", "price": px,
                                           "notional": notion, "fee": fee})
                    shares[s] = 0.0
                pending[s] = None

            # (2) monthly sizing refresh at the close (first bar day of a new
            # calendar month, open position, no pending order)
            close_px = {s: day_bars[s][3] for s in day_bars}
            for s in SYMBOLS:
                ym = d.strftime("%Y-%m")
                if (ym != last_ym[s] and s in day_bars and shares[s] > 0
                        and pending[s] is None):
                    i = info[s]["idx"][d]
                    f = size_frac(s, i)
                    frac[s] = f
                    mark_c = {x: close_px.get(x, last_close[x]) for x in SYMBOLS}
                    eq_c = equity_at(mark_c)
                    target_notion = f * eq_c
                    cur_notion = shares[s] * close_px[s]
                    delta = target_notion - cur_notion
                    if abs(delta) > 1e-9 and close_px[s] > 0:
                        dq = delta / close_px[s]
                        fee = abs(delta) * cost
                        cash -= delta + fee
                        shares[s] += dq
                        res.n_fills += 1
                        res.trades.append({"date": d.isoformat(), "symbol": s,
                                           "side": "RESIZE", "price": close_px[s],
                                           "notional": abs(delta), "fee": fee})
                if s in day_bars:
                    last_ym[s] = ym

        # (3) signals at the close (bar days only; hole days inherit)
        for s in SYMBOLS:
            if s in day_bars:
                i = info[s]["idx"][d]
                highs, closes = info[s]["highs"], info[s]["closes"]
                if i >= WARMUP_BARS:
                    breakout = closes[i] > max(highs[i - DONCHIAN_LOOKBACK:i])
                    mom50 = closes[i] > closes[i - MOM_LOOKBACK]
                    new_sig = bool(breakout or mom50)
                    # fresh entry -> refresh sizing now (fill uses it at t+1 open)
                    if new_sig and not signal[s]:
                        frac[s] = size_frac(s, i)
                    signal[s] = new_sig
                last_close[s] = closes[i]
                # schedule fills for the next bar day's open
                if signal[s] and shares[s] == 0.0 and pending[s] is None:
                    pending[s] = {"kind": "enter", "frac": frac[s]}
                elif (not signal[s] and (shares[s] > 0.0
                      or (pending[s] is not None
                          and pending[s]["kind"] == "enter"))):
                    pending[s] = {"kind": "exit"}

        # mark equity: frozen on hole days (no bar -> no price -> return 0)
        if day_bars:
            mark_px = {s: day_bars[s][3] if s in day_bars else last_close[s]
                       for s in SYMBOLS}
            eq = equity_at(mark_px)
        else:
            eq = prev_eq
            res.n_hole_days += 1
        r = eq / prev_eq - 1.0 if prev_eq > 0 else 0.0
        res.dates.append(d)
        res.rets.append(r)
        res.equity.append(eq)
        prev_eq = eq

    return res


# ---------------------------------------------------------------------------
# walk-forward
# ---------------------------------------------------------------------------

def walk_forward_folds(dates: list[date], rets: list[float]) -> list[dict]:
    from trade_overfit.metrics import max_drawdown, sharpe_ratio, total_return

    n = len(rets)
    folds, start = [], 0
    while True:
        train_end = start + TRAIN_DAYS
        test_start = train_end + EMBARGO_DAYS
        test_end = test_start + TEST_DAYS
        if test_end > n:
            break
        te = rets[test_start:test_end]
        folds.append({
            "fold": len(folds),
            "train_start": dates[start].isoformat(),
            "train_end": dates[train_end - 1].isoformat(),
            "test_start": dates[test_start].isoformat(),
            "test_end": dates[test_end - 1].isoformat(),
            "oos_sharpe": sharpe_ratio(te, periods=PERIODS),
            "oos_return": total_return(te),
            "oos_max_drawdown": max_drawdown(te)["max_drawdown"],
            "n_oos_days": len(te),
        })
        start += STEP_DAYS
    return folds


# ---------------------------------------------------------------------------
# gates
# ---------------------------------------------------------------------------

def compute_gates(oos_rets: list[float], folds: list[dict],
                  btc_daily_rets: list[float]) -> dict:
    from trade_overfit._stats import median
    from trade_overfit.dsr import dsr_from_returns
    from trade_overfit.gates import evaluate_gates, preset_gates
    from trade_overfit.metrics import (
        annualized_return, calmar_ratio, max_drawdown, sortino_ratio,
    )
    from trade_overfit.regimes import regime_report

    dsr = dsr_from_returns(oos_rets, trial_sharpes=TRIAL_SHARPES,
                           periods=PERIODS)
    fold_sharpes = [f["oos_sharpe"] for f in folds
                    if f["oos_sharpe"] is not None]
    dd = max_drawdown(oos_rets)
    reg = regime_report(oos_rets, periods=PERIODS)  # vol-regime default

    # BTC buy-and-hold over the same OOS span, net of 25 bps entry + exit.
    # btc_daily_rets is the calendar-day BTC series sliced to the same windows.
    gross = 1.0
    for r in btc_daily_rets:
        gross *= (1.0 + r)
    gross -= 1.0
    bh_net = (1.0 + gross) * (1.0 - COST_BPS / 10_000) ** 2 - 1.0
    bh_ann = (1.0 + bh_net) ** (PERIODS / len(btc_daily_rets)) - 1.0
    strat_ann = annualized_return(oos_rets, periods=PERIODS)
    excess = strat_ann - bh_ann

    evidence = {
        "dsr": dsr["dsr"],
        "median_oos_sharpe": median(fold_sharpes),
        "max_drawdown": dd["max_drawdown"],
        "worst_regime_sharpe": reg["worst_regime_sharpe"],
        "excess_return_vs_benchmark_after_costs": excess,
        "sortino": sortino_ratio(oos_rets, periods=PERIODS),
        "calmar": calmar_ratio(oos_rets, periods=PERIODS),
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
        "btc_bh_annualized_net": bh_ann,
        "btc_bh_total_net": bh_net,
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    t0 = datetime.now(timezone.utc).isoformat()
    log("starting (venue=Binance.US primary per spec interpretation)")

    bars = fetch_bars()
    days = calendar_days()
    n_days = len(days)
    log(f"calendar span: {days[0]} .. {days[-1]} ({n_days} days)")

    # venue coverage / hole accounting
    cov = {}
    for s in SYMBOLS:
        have = len(bars[s])
        missing = sorted(set(days) - set(bars[s]))
        holes = []
        if missing:
            a = b = missing[0]
            for d in missing[1:]:
                if d == b + timedelta(days=1):
                    b = d
                else:
                    holes.append((a, b))
                    a = b = d
            holes.append((a, b))
        cov[s] = {"bars": have, "missing_days": len(missing),
                  "holes": [(a.isoformat(), b.isoformat(),
                             (b - a).days + 1) for a, b in holes]}
        log(f"{s}: {have}/{n_days} bars; {len(missing)} hole days in "
            f"{len(holes)} runs"
            + (f"; largest: {max(h[2] for h in cov[s]['holes'])}d" if holes else ""))

    log(f"simulating at {COST_BPS} bps/side")
    res = simulate(bars, COST_BPS)
    log(f"fills: {res.n_fills}, hole days: {res.n_hole_days}, "
        f"final equity: {res.equity[-1]:,.2f}")

    log(f"walk-forward ({TRAIN_DAYS}d train / {TEST_DAYS}d test / "
        f"{STEP_DAYS}d step + {EMBARGO_DAYS}d embargo)")
    folds = walk_forward_folds(res.dates, res.rets)
    log(f"{len(folds)} folds")

    # BTC benchmark: calendar-day returns (mark-to-last-available-close,
    # hole days = 0), sliced to the same OOS windows
    btc_rets = []
    prev = None
    for d in res.dates:
        c = bars["BTC/USD"][d][3] if d in bars["BTC/USD"] else None
        if c is None or prev is None:
            btc_rets.append(0.0)
        else:
            btc_rets.append(c / prev - 1.0)
        if c is not None:
            prev = c

    # concatenated OOS = gated series
    oos_rets, oos_btc, oos_idx = [], [], []
    n = len(res.rets)
    start = 0
    while True:
        train_end = start + TRAIN_DAYS
        test_start = train_end + EMBARGO_DAYS
        test_end = test_start + TEST_DAYS
        if test_end > n:
            break
        oos_rets.extend(res.rets[test_start:test_end])
        oos_btc.extend(btc_rets[test_start:test_end])
        oos_idx.append((res.dates[test_start].isoformat(),
                        res.dates[test_end - 1].isoformat()))
        start += STEP_DAYS
    log(f"OOS series: {len(oos_rets)} days "
        f"({oos_idx[0][0]} .. {oos_idx[-1][1]})")

    log("gates (trade-overfit v0.2.0 standard preset, DSR n_trials=7)")
    g = compute_gates(oos_rets, folds, oos_btc)
    for gate in g["gates"]:
        v = gate["value"]
        vs = f"{v:.4f}" if isinstance(v, float) else str(v)
        log(f"  {gate['name']}: {vs} "
            f"({'PASS' if gate['passed'] else 'FAIL'})")
    log(f"verdict: {g['verdict']}")

    # cost sensitivity (report-only): full re-simulation at 10 / 50 bps
    from trade_overfit.metrics import (max_drawdown as _mdd,
                                       sharpe_ratio as _sh,
                                       total_return as _tr)
    sens = {}
    for bps in (10.0, 50.0):
        r2 = simulate(bars, bps)
        sens[str(bps)] = {
            "final_equity": r2.equity[-1],
            "total_return": _tr(r2.rets),
            "sharpe_365": _sh(r2.rets, periods=PERIODS),
            "max_drawdown": _mdd(r2.rets)["max_drawdown"],
            "fills": r2.n_fills,
        }
        log(f"  {bps} bps/side: final {r2.equity[-1]:,.2f}, "
            f"Sharpe(365) {sens[str(bps)]['sharpe_365']:.3f}, "
            f"maxDD {sens[str(bps)]['max_drawdown']:.4f}")

    bundle = {
        "strategy": "TSMOM-CR",
        "trial": 3,
        "candidate": "B of 2",
        "pre_registration_commit": PRE_REG_COMMITS,
        "run_started_utc": t0,
        "run_finished_utc": datetime.now(timezone.utc).isoformat(),
        "venue": "Binance.US (primary; Kraken fallback not usable — see spec "
                 "interpretation note in report.md)",
        "data": {
            "source": "Binance.US public daily klines via trade-data-crypto "
                      "BinanceUSPublicProvider (keyless)",
            "calendar_span": [days[0].isoformat(), days[-1].isoformat()],
            "n_calendar_days": n_days,
            "symbols": SYMBOLS,
            "coverage": cov,
            "construction": "calendar-day-indexed: hole day = no bar for the "
                            "symbol -> signals frozen (inherit), positions "
                            "frozen, equity unchanged -> daily return 0; "
                            "mark-to-market on bar days uses the most recent "
                            "available close as reference, so P&L accrued "
                            "through a hole is realized on the first post-hole "
                            "bar day.",
        },
        "signals": {
            "breakout": "close[t] > max(high[t-90..t-1]) over prior 90 ACTUAL "
                        "bars, excluding t",
            "mom50": "close[t] > close[t-50] (50 actual bars back)",
            "rule": "long if breakout OR mom50; else flat; exit = first false day",
            "warmup": "91 prior bars of actual data before signals",
            "holes": "signals computed only on days with bars; hole days inherit",
        },
        "sizing": {
            "formula": "notional_i = min(0.10/sigma_ann_i, 1.0) x equity",
            "sigma": "stdev(trailing 60 ONE-DAY bar-to-bar returns, "
                     "gap-spanning returns excluded) x sqrt(365)",
            "refresh": "calendar-month boundaries and fresh entries only",
            "monthly_resize_px": "close of first bar day of the month",
        },
        "execution": {
            "fills": "next day's open (t->t+1); deferred to next bar day's "
                     "open at hole boundaries",
            "costs_bps_per_side": COST_BPS,
            "borrow": "none (long/flat, no margin)",
        },
        "walk_forward": {
            "train_days": TRAIN_DAYS, "test_days": TEST_DAYS,
            "step_days": STEP_DAYS, "embargo_days": EMBARGO_DAYS,
            "periods_per_year": PERIODS,
            "n_folds": len(folds),
            "n_oos_days": len(oos_rets),
            "oos_span": [oos_idx[0][0], oos_idx[-1][1]],
            "folds": folds,
        },
        "simulation_25bps": {
            "final_equity": res.equity[-1],
            "total_return_full_span": _tr(res.rets),
            "sharpe_365_full_span": _sh(res.rets, periods=PERIODS),
            "max_drawdown_full_span": _mdd(res.rets)["max_drawdown"],
            "fills": res.n_fills,
            "hole_days": res.n_hole_days,
        },
        "cost_sensitivity_report_only": sens,
        "gates": g["gates"],
        "evidence": g["evidence"],
        "dsr_detail": g["dsr_detail"],
        "regimes": g["regimes"],
        "strategy_annualized_oos": g["strategy_annualized"],
        "btc_bh_annualized_net": g["btc_bh_annualized_net"],
        "btc_bh_total_net": g["btc_bh_total_net"],
        "verdict": g["verdict"],
        "note": "No parameters fitted (all values fixed per frozen spec); "
                "walk-forward tests regime stability only. One clean run, no "
                "tuning.",
    }
    with open(f"{OUT_DIR}/evidence.json", "w") as fh:
        json.dump(bundle, fh, indent=2, default=str)
    log("evidence -> docs/validation/tsmom-cr/evidence.json")

    write_report(bundle)
    log("report -> docs/validation/tsmom-cr/report.md")
    return 0


def write_report(b: dict) -> None:
    cov = b["data"]["coverage"]
    L = []
    A = L.append
    A("# TSMOM-CR validation report — trial 3 candidate B (re-run, valid path)")
    A("")
    A(f"- Pre-registration: commits {b['pre_registration_commit']} (frozen spec, "
      f"before any validation data pull); gate amendment 425745b")
    A(f"- Run: {b['run_started_utc'][:10]}, one clean run, no tuning")
    A(f"- Venue: **{b['venue']}**")
    A(f"- Data: {b['data']['source']}")
    A(f"- Calendar span: {b['data']['calendar_span'][0]} .. "
      f"{b['data']['calendar_span'][1]} ({b['data']['n_calendar_days']} days)")
    A(f"- Costs: {b['execution']['costs_bps_per_side']} bps/side all-in, no borrow")
    A(f"- Walk-forward: {b['walk_forward']['train_days']}d train / "
      f"{b['walk_forward']['test_days']}d test / {b['walk_forward']['step_days']}d step "
      f"/ {b['walk_forward']['embargo_days']}d embargo — "
      f"{b['walk_forward']['n_folds']} folds, {b['walk_forward']['n_oos_days']} OOS days")
    A("- Annualization: 365 (crypto 24/7; calendar-day folds deliberate)")
    A("")
    A("## Spec interpretation note (frozen-spec resolution)")
    A("")
    A("The pre-registration names Binance.US primary with Kraken fallback ONLY "
      "if Binance.US daily history proves discontinuous — 'the venue is chosen "
      "on history completeness'. Inspection proved: Binance.US daily has a "
      f"585-day hole (2023-07-15..2025-02-18; {cov['BTC/USD']['bars']}/"
      f"{b['data']['n_calendar_days']} bars served for BTC) AND Kraken's public "
      "API serves only the most recent ~720 daily candles (verified by probe) — "
      "the fallback's background assumption (Kraken deep history) is false, so "
      "the fallback cannot serve the 2019-09-17..2026-09-25 span either. The "
      "first validation attempt was archived INVALID for exactly this reason: "
      "0 folds fit the frozen 104w/26w/26w geometry on 719 bars, so the gated "
      "OOS series was empty "
      "(docs/validation/tsmom-cr/invalid_runs/2026-09-27_zero-oos-folds/).")
    A("")
    A("Resolution, staying inside the spec: validate on the primary venue "
      "Binance.US under the spec's own data rule — 'Data holes: a day with no "
      "bar = hold (no signal change), exactly as screened' — which is also "
      "exactly how Phase B screened it (docs/research/scratch/tsmom_cr.py ran "
      "the screen on this same gappy Binance.US series). This changes no "
      "parameter, no geometry, no venue-shopping: no gate results were seen "
      "before this resolution. **Charlie may overrule this interpretation.**")
    A("")
    A("## Venue coverage")
    A("")
    A("| symbol | bars served | calendar days | hole days | hole runs |")
    A("|---|---|---|---|---|")
    for s in b["data"]["symbols"]:
        c = cov[s]
        runs = "; ".join(f"{a}..{bb} ({n}d)" for a, bb, n in c["holes"])
        A(f"| {s} | {c['bars']} | {b['data']['n_calendar_days']} | "
          f"{c['missing_days']} | {runs} |")
    A("")
    A("Construction: calendar-day-indexed return series. Hole day (no bar) = "
      "signals frozen (inherit prior day), positions frozen, equity unchanged "
      "→ daily return 0. Mark-to-market on a bar day references the most "
      "recent available close, so P&L accrued while held through a hole is "
      "realized on the first post-hole bar day. Fills at t+1 open; at hole "
      "boundaries a fill is deferred to the next day with a bar, at that day's "
      "open. Vol for sizing uses trailing 60 one-day bar-to-bar returns, "
      "excluding gap-spanning returns.")
    A("")
    A("## Gates (trade-overfit v0.2.0 standard preset, DSR n_trials=7)")
    A("")
    A("| gate | value | threshold | result |")
    A("|---|---|---|---|")
    for gate in b["gates"]:
        v = gate["value"]
        vs = f"{v:.4f}" if isinstance(v, float) else str(v)
        A(f"| {gate['name']} | {vs} | {gate['op']} {gate['threshold']} | "
          f"{'PASS' if gate['passed'] else 'FAIL'} |")
    A("")
    A(f"**Verdict: {b['verdict']}**")
    A("")
    A("## Walk-forward folds (OOS)")
    A("")
    A("| fold | test window | OOS Sharpe(365) | OOS return | OOS maxDD |")
    A("|---|---|---|---|---|")
    for f in b["walk_forward"]["folds"]:
        sh = f["oos_sharpe"]
        shs = f"{sh:.3f}" if sh is not None else "n/a"
        A(f"| {f['fold']} | {f['test_start']}..{f['test_end']} | {shs} | "
          f"{f['oos_return']:.4f} | {f['oos_max_drawdown']:.4f} |")
    A("")
    A(f"- Concatenated OOS: {b['walk_forward']['n_oos_days']} days "
      f"({b['walk_forward']['oos_span'][0]} .. {b['walk_forward']['oos_span'][1]})")
    A(f"- Strategy annualized (OOS): {b['strategy_annualized_oos']:.4f}")
    A(f"- BTC buy-and-hold annualized, net of 25 bps entry+exit: "
      f"{b['btc_bh_annualized_net']:.4f} "
      f"(total {b['btc_bh_total_net']:.4f})")
    A(f"- DSR detail: sharpe_hat={b['dsr_detail']['sharpe_hat']:.4f}, "
      f"n_obs={b['dsr_detail']['n_obs']}, n_trials={b['dsr_detail']['n_trials']}, "
      f"skew={b['dsr_detail']['skewness']:.3f}, "
      f"ex.kurt={b['dsr_detail']['excess_kurtosis']:.3f}, "
      f"ESR_null={b['dsr_detail']['expected_sharpe_under_null']:.4f}")
    reg = b["regimes"]["regimes"]
    A("- Vol regimes: " + "; ".join(
        f"{k}: n={v['n_bars']}, sharpe={v['sharpe']:.3f}, "
        f"ret={v['total_return']:.4f}, dd={v['max_drawdown']:.4f}"
        for k, v in sorted(reg.items())))
    A("")
    A("## Cost sensitivity (report-only, full-span re-simulation)")
    A("")
    A("| bps/side | final equity | total return | Sharpe(365) | maxDD | fills |")
    A("|---|---|---|---|---|---|")
    s25 = b["simulation_25bps"]
    A(f"| 25 | {s25['final_equity']:,.2f} | {s25['total_return_full_span']:.4f} | "
      f"{s25['sharpe_365_full_span']:.3f} | {s25['max_drawdown_full_span']:.4f} | "
      f"{s25['fills']} |")
    for bps, s in b["cost_sensitivity_report_only"].items():
        A(f"| {bps} | {s['final_equity']:,.2f} | {s['total_return']:.4f} | "
          f"{s['sharpe_365']:.3f} | {s['max_drawdown']:.4f} | {s['fills']} |")
    A("")
    A("## Honest flags")
    A("")
    A("- Same instruments as killed trial 2 (MR-5M): BTC/ETH. Mechanism differs "
      "(daily trend, long/flat vs 5-min mean reversion, long/short), but if "
      "crypto market structure was trial 2's problem, this fails the same way.")
    A("- 2-name concentration: a single-asset drawdown is a portfolio drawdown.")
    A("- One secular crypto bull market (2019–2026) with two violent "
      "interruptions; the walk-forward folds are the honest test.")
    hole_days = cov["BTC/USD"]["missing_days"]
    hole_frac = hole_days / b["walk_forward"]["n_oos_days"]
    A(f"- ~{hole_frac:.0%} of the concatenated OOS day-count ({hole_days} "
      "hole days) is the Binance.US data hole: positions are frozen and daily "
      "returns are exactly 0 through it, so it contributes no signal and no "
      "P&L to the OOS metrics — the gates are evaluated on the remaining "
      "OOS days plus the one-day post-hole P&L realizations. The hole cannot "
      "create edge; it dilutes both return and volatility.")
    A("- 25 bps/side is an assumption, not a measurement (see sensitivity).")
    A("- t+1-open fills on daily bars miss intrabar dynamics; optimistic on "
      "violent gap days — direction of bias unknown, documented.")
    A("")
    A("## Provenance")
    A("")
    A(f"- Pre-registration: commits {b['pre_registration_commit']} "
      "(frozen spec + gate amendment, both before any validation data pull)")
    A(f"- Data: {b['data']['source']}; span {b['data']['calendar_span'][0]} .. "
      f"{b['data']['calendar_span'][1]}")
    A(f"- Gates: trade-overfit v0.2.0 preset_gates('standard'); DSR "
      f"trial_sharpes={TRIAL_SHARPES} (n=7), periods=365")
    A(f"- Run: {b['run_started_utc']} → {b['run_finished_utc']} (UTC)")
    A("- Supersedes the INVALID-stamped report.md/evidence.json from the "
      "first attempt; that run remains archived under "
      "docs/validation/tsmom-cr/invalid_runs/2026-09-27_zero-oos-folds/")
    with open(f"{OUT_DIR}/report.md", "w") as fh:
        fh.write("\n".join(L) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
