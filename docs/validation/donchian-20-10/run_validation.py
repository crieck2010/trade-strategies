"""One-shot validation runner for the pre-registered DON-20/10-ATR trial.

Implements docs/validation/donchian-20-10/PRE-REGISTRATION.md exactly:
universe -> features -> trade-backtest engine -> walk-forward (embargo) ->
trade-overfit gates -> evidence.json + report.md.

Run from the trade-strategies repo root::

    PYTHONPATH=src:/path/to/trade-backtest/src:/path/to/trade-data-equities/src:/path/to/trade-overfit/src \\
        /tmp/valvenv/bin/python docs/validation/donchian-20-10/run_validation.py

Uses yfinance (no keys) through trade-data-equities' provider interface.
"""

from __future__ import annotations

import json
import math
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent

# -- frozen pre-registration parameters --------------------------------------
START = date(2015, 1, 1)
END = date(2026, 9, 26)          # client end is exclusive -> data through 2026-09-25
FILTER_DATE = "2026-09-01"  # liquidity/price filter reference date
MIN_PRICE = 10.0
MIN_DOLLAR_VOL = 25_000_000.0
DOLLAR_VOL_LOOKBACK = 63
COVERAGE = 0.99
INITIAL_CASH = 100_000.0
SLIPPAGE_BPS = 5.0
TRAIN = 756
TEST = 252
STEP = 252
EMBARGO = 10
WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"


def log(msg: str) -> None:
    print(f"[validate] {msg}", flush=True)


# -- universe ----------------------------------------------------------------

def fetch_sp500_tickers() -> tuple[list[str], str]:
    import io
    import urllib.request

    import pandas as pd

    retrieval_date = date.today().isoformat()
    # Wikipedia 403s non-browser user agents; same page, honest client header.
    req = urllib.request.Request(
        WIKI_URL,
        headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) research-validation/1.0"},
    )
    html = urllib.request.urlopen(req, timeout=60).read()
    tables = pd.read_html(io.BytesIO(html))
    tickers: list[str] = []
    for t in tables:
        cols = [str(c).strip().lower() for c in t.columns]
        if "symbol" in cols:
            sym_col = t.columns[cols.index("symbol")]
            for raw in t[sym_col].astype(str):
                tk = raw.strip().upper().replace(".", "-")  # BRK.B -> BRK-B for yfinance
                if tk and tk not in tickers:
                    tickers.append(tk)
            break
    if not tickers:
        raise RuntimeError("could not parse S&P 500 ticker table from Wikipedia")
    return tickers, retrieval_date


def download_all(tickers: list[str]) -> tuple[dict[str, list], dict[str, str]]:
    from trade_data_equities.client import EquitiesDataClient
    from trade_data_equities.models import Timeframe
    from trade_data_equities.providers.yfinance import YFinanceProvider

    client = EquitiesDataClient(YFinanceProvider(), auto_adjust=True)
    bars: dict[str, list] = {}
    failures: dict[str, str] = {}

    def one(ticker: str):
        try:
            blist = client.get_bars(ticker, Timeframe.DAILY, START, END, adjusted=True)
            return ticker, blist, None
        except Exception as exc:  # noqa: BLE001 - per-symbol isolation
            return ticker, None, f"{type(exc).__name__}: {exc}"

    with ThreadPoolExecutor(max_workers=16) as ex:
        futs = {ex.submit(one, t): t for t in tickers}
        done = 0
        for f in as_completed(futs):
            ticker, blist, err = f.result()
            done += 1
            if done % 100 == 0:
                log(f"downloaded {done}/{len(tickers)}")
            if err:
                failures[ticker] = err
            else:
                bars[ticker] = [b for b in blist if b.close > 0]
    return bars, failures


def apply_universe_filters(bars: dict[str, list], spy_n: int) -> tuple[list[str], dict]:
    """Pre-registered filter cascade. Returns (universe, stage_counts)."""
    stage_counts = {"retrieved": len(bars)}
    # (a) history coverage >= 99% of SPY bar count
    cov = {s: b for s, b in bars.items() if len(b) >= COVERAGE * spy_n}
    stage_counts["coverage"] = len(cov)
    # (b)+(c) price >= $10 and median 63d dollar volume >= $25M as of FILTER_DATE
    universe = []
    dropped_price, dropped_liq = 0, 0
    for s, blist in sorted(cov.items()):
        ref = [b for b in blist if b.timestamp.date().isoformat() <= FILTER_DATE]
        if not ref:
            continue
        if ref[-1].close < MIN_PRICE:
            dropped_price += 1
            continue
        tail = ref[-DOLLAR_VOL_LOOKBACK:]
        dvols = sorted(b.close * b.volume for b in tail)
        med = dvols[len(dvols) // 2]
        if med < MIN_DOLLAR_VOL:
            dropped_liq += 1
            continue
        universe.append(s)
    stage_counts["price_filter_dropped"] = dropped_price
    stage_counts["liquidity_filter_dropped"] = dropped_liq
    stage_counts["final_universe"] = len(universe)
    return universe, stage_counts


# -- backtest ------------------------------------------------------------------

def to_engine_bars(bars_by_symbol: dict[str, list]):
    from trade_backtest.models import Bar as EngineBar

    out = []
    for symbol, blist in bars_by_symbol.items():
        for b in blist:
            out.append(EngineBar(
                symbol=symbol, timestamp=b.timestamp,
                open=b.open, high=b.high, low=b.low,
                close=b.close, volume=b.volume,
            ))
    return out


def run_backtest(engine_bars, features):
    import trade_backtest.costs as tbc
    import trade_backtest.data as tbd
    import trade_backtest.engine as tbe
    import trade_backtest.execution as tbx
    import trade_backtest.portfolio as tbp

    from trade_strategies.donchian_swing import DonchianSwingStrategy

    symbols = sorted(features)

    class CountingStrategy(DonchianSwingStrategy):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.signal_log: list[tuple] = []

        def on_bar(self, timestamp, bars):
            sigs = super().on_bar(timestamp, bars)
            for s in sigs:
                self.signal_log.append(
                    (timestamp.date().isoformat(), s.symbol, s.action.name, s.strength))
            return sigs

    class FractionEquitySizer(tbp.PositionSizer):
        """Target quantity = signal.strength (equity fraction) * equity / price."""

        def size(self, signal, price, portfolio):
            # NOTE: compare against trade_strategies.base.SignalAction --
            # that is the enum the strategy emits. trade_backtest.models
            # defines a second, distinct SignalAction class with identical
            # members; comparing against it is always False and turned
            # every EXIT into a full-equity BUY (run 2 invalid).
            from trade_strategies.base import SignalAction as SA
            if signal.action == SA.EXIT:
                return 0.0
            qty = signal.strength * portfolio.equity / price
            return qty if qty >= 1.0 else 0.0

    strategy = CountingStrategy(symbols, features=features)
    cost_model = tbc.CostModel(
        commission=tbx.NoCommission(),
        slippage_entry_bps=SLIPPAGE_BPS,
        slippage_exit_bps=SLIPPAGE_BPS,
        half_spread_bps=0.0,
        borrow_cost_annual_bps=0.0,
    )
    engine = tbe.BacktestEngine(
        data=tbd.ListDataHandler(engine_bars),
        strategy=strategy,
        portfolio=tbp.Portfolio(INITIAL_CASH, FractionEquitySizer(), cost_model=cost_model),
        execution=tbx.SimulatedExecutionHandler(cost_model=cost_model),
        adjustment_basis="pre_adjusted",
        adjustment_note="yfinance split/dividend-adjusted daily bars via "
                        "trade-data-equities YFinanceProvider (auto_adjust=True)",
    )
    result = engine.run()
    return result, strategy.signal_log


def equity_returns(result):
    curve = result.equity_curve
    dates = [p.timestamp.date().isoformat() for p in curve]
    eq = [p.equity for p in curve]
    rets = [eq[i] / eq[i - 1] - 1.0 for i in range(1, len(eq))]
    return dates[1:], rets


# -- walk-forward --------------------------------------------------------------

def walk_forward_folds(dates, rets):
    from trade_overfit.metrics import max_drawdown, sharpe_ratio, total_return

    n = len(rets)
    folds = []
    start = 0
    while True:
        train_end = start + TRAIN
        test_start = train_end + EMBARGO
        test_end = test_start + TEST
        if test_end > n:
            break
        tr = rets[start:train_end]
        te = rets[test_start:test_end]
        folds.append({
            "fold": len(folds),
            "train_start": dates[start], "train_end": dates[train_end - 1],
            "test_start": dates[test_start], "test_end": dates[test_end - 1],
            "is_sharpe": sharpe_ratio(tr),
            "oos_sharpe": sharpe_ratio(te),
            "oos_return": total_return(te),
            "oos_max_drawdown": max_drawdown(te)["max_drawdown"],
            "n_oos_bars": len(te),
        })
        start += STEP
    return folds


def main() -> None:
    t0 = datetime.now(timezone.utc).isoformat()
    log("fetching S&P 500 constituent list (first data touch)")
    tickers, retrieval_date = fetch_sp500_tickers()
    log(f"{len(tickers)} tickers retrieved {retrieval_date}")

    log("downloading SPY (benchmark + coverage reference)")
    spy_bars, spy_fail = download_all(["SPY"])
    if "SPY" not in spy_bars:
        raise RuntimeError(f"SPY download failed: {spy_fail.get('SPY')}")
    spy_n = len(spy_bars["SPY"])
    log(f"SPY bars: {spy_n}")

    log("downloading constituent bars (threaded, cached)")
    bars, failures = download_all(tickers)
    log(f"ok={len(bars)} failed={len(failures)}")

    universe, stage_counts = apply_universe_filters(bars, spy_n)
    log(f"universe: {universe.__len__()} symbols | stages={stage_counts}")

    # features per symbol on adjusted bars
    from trade_strategies.donchian_swing import compute_features, DonchianSwingConfig
    cfg = DonchianSwingConfig()
    features = {}
    for s in universe:
        blist = bars[s]
        dicts = [{
            "date": b.timestamp.date().isoformat(), "open": b.open,
            "high": b.high, "low": b.low, "close": b.close, "volume": b.volume,
        } for b in blist]
        features[s] = compute_features(dicts, cfg)

    log("running backtest engine (signals t -> fills t+1 open, costs in-engine)")
    engine_bars = to_engine_bars({s: bars[s] for s in universe})
    result, signal_log = run_backtest(engine_bars, features)
    dates, rets = equity_returns(result)
    log(f"backtest done: {len(result.trades)} closed trades, "
        f"{len(rets)} return bars {dates[0]}..{dates[-1]}")

    # signal/fill reconciliation (intended positions assume fills)
    n_long_signals = sum(1 for _, _, a, _ in signal_log if a == "LONG")
    n_entry_fills = len(result.trades)  # one closed trade per filled entry
    log(f"reconciliation: LONG signals={n_long_signals} filled entries={n_entry_fills}")

    log("walk-forward (rolling 756/252/252 + 10d embargo, params frozen)")
    folds = walk_forward_folds(dates, rets)
    log(f"{len(folds)} folds")
    oos_dates, oos_rets = [], []
    for f in folds:
        i0 = dates.index(f["test_start"])
        i1 = dates.index(f["test_end"]) + 1
        oos_dates.extend(dates[i0:i1])
        oos_rets.extend(rets[i0:i1])
    log(f"OOS series: {len(oos_rets)} bars {oos_dates[0]}..{oos_dates[-1]}")

    # benchmark aligned to OOS dates
    spy_map = {b.timestamp.date().isoformat(): b.close for b in spy_bars["SPY"]}
    spy_closes = [spy_map[d] for d in oos_dates]
    spy_rets = [spy_closes[i] / spy_closes[i - 1] - 1.0 for i in range(1, len(spy_closes))]
    oos_aligned = oos_rets[1:]  # drop first bar (no prior SPY close)
    oos_dates_aligned = oos_dates[1:]
    assert len(oos_aligned) == len(spy_rets)

    log("gates (trade-overfit, standard preset, N=1 trial)")
    from trade_overfit.dsr import dsr_from_returns
    from trade_overfit.gates import evaluate_gates, preset_gates
    from trade_overfit.metrics import annualized_return, max_drawdown
    from trade_overfit.regimes import regime_report
    from trade_overfit._stats import median

    dsr = dsr_from_returns(oos_aligned)  # trial_sharpes=None -> N=1
    fold_oos_sharpes = [f["oos_sharpe"] for f in folds if f["oos_sharpe"] is not None]
    dd = max_drawdown(oos_aligned)
    reg = regime_report(oos_aligned)  # desk's own vol-regime splits
    excess = annualized_return(oos_aligned) - annualized_return(spy_rets)
    evidence = {
        "dsr": dsr["dsr"],
        "median_oos_sharpe": median(fold_oos_sharpes),
        "max_drawdown": dd["max_drawdown"],
        "worst_regime_sharpe": reg["worst_regime_sharpe"],
        "excess_return_vs_benchmark_after_costs": excess,
    }
    gates = evaluate_gates(evidence, preset_gates("standard"))
    verdict = "PASS" if all(g["passed"] for g in gates) else "KILL"
    log(f"verdict: {verdict}")

    bundle = {
        "strategy": "DON-20/10-ATR",
        "trial": 1,
        "pre_registration_commit": "5a96b1a",
        "run_started_utc": t0,
        "run_finished_utc": datetime.now(timezone.utc).isoformat(),
        "data": {
            "source": "yfinance via trade-data-equities YFinanceProvider (auto_adjust=True)",
            "range": [START, END],
            "universe_rule": "S&P 500 constituents (Wikipedia, retrieved %s), "
                             ">=99%% SPY coverage, close>=10 @%s, "
                             "median 63d dollar volume >= $25M @%s" % (
                                 retrieval_date, FILTER_DATE, FILTER_DATE),
            "retrieval_date": retrieval_date,
            "stage_counts": stage_counts,
            "universe": universe,
            "n_download_failures": len(failures),
            "download_failures": sorted(failures)[:50],
        },
        "costs": {
            "slippage_bps_per_side": SLIPPAGE_BPS,
            "half_spread_bps": 0.0,
            "commission": 0.0,
            "execution": "signals on t close -> fills at t+1 open (engine convention)",
            "adjustment_basis": "pre_adjusted",
        },
        "walk_forward": {
            "scheme": "rolling", "train": TRAIN, "test": TEST,
            "step": STEP, "embargo_bars": EMBARGO,
            "n_folds": len(folds), "oos_bars": len(oos_aligned),
            "oos_range": [oos_dates_aligned[0], oos_dates_aligned[-1]],
            "folds": folds,
        },
        "full_sample_context": {
            "n_bars": len(rets),
            "annualized_return": annualized_return(rets),
            "n_closed_trades": len(result.trades),
            "n_long_signals": n_long_signals,
        },
        "dsr_inputs": dsr,
        "regimes": reg,
        "gates": gates,
        "evidence": evidence,
        "verdict": verdict,
    }
    with open(OUT_DIR / "evidence.json", "w") as f:
        json.dump(bundle, f, indent=2, default=str)

    lines = [
        "# DON-20/10-ATR validation report — trial 1 of 1",
        "",
        f"**Verdict: {verdict}** (run {t0})",
        "",
        "## Universe",
        f"S&P 500 constituents retrieved {retrieval_date}; "
        f"{stage_counts['retrieved']} downloaded ok, {len(failures)} failed; "
        f"final universe **{len(universe)}** symbols "
        f"(coverage≥99%: {stage_counts['coverage']}).",
        "",
        "## Walk-forward (rolling 756/252/252, 10-day embargo, params frozen)",
        "",
        "| fold | test window | OOS Sharpe | OOS return | OOS maxDD |",
        "|------|-------------|------------|------------|-----------|",
    ]
    for fl in folds:
        lines.append(
            f"| {fl['fold']} | {fl['test_start']}..{fl['test_end']} | "
            f"{fl['oos_sharpe']:.2f} | {fl['oos_return']:.2%} | {fl['oos_max_drawdown']:.2%} |")
    lines += [
        "",
        "## Gates (standard preset, N=1)",
        "",
        "| gate | value | threshold | pass |",
        "|------|-------|-----------|------|",
    ]
    for g in gates:
        v = g["value"]
        vs = f"{v:.4f}" if isinstance(v, float) else str(v)
        lines.append(f"| {g['name']} | {vs} | {g['op']} {g['threshold']} | "
                     f"{'PASS' if g['passed'] else 'FAIL'} |")
    lines += [
        "",
        "## Notes",
        f"- DSR inputs: Sharpe_hat={dsr['sharpe_hat']:.3f}, n_obs={dsr['n_obs']}, "
        f"n_trials={dsr['n_trials']}, skew={dsr['skewness']:.2f}, "
        f"excess_kurt={dsr['excess_kurtosis']:.2f}.",
        f"- Regime splits (desk vol-regime): {json.dumps(reg['regimes'], default=str)}.",
        f"- Signal/fill reconciliation: {n_long_signals} LONG signals, "
        f"{n_entry_fills} filled entries.",
        "- Costs are in-engine (5 bps/side); the OOS series is already net.",
        "- Survivorship bias (upward): universe drawn from today's constituents.",
    ]
    (OUT_DIR / "report.md").write_text("\n".join(lines) + "\n")
    log("wrote evidence.json + report.md")
    print(f"FINAL_VERDICT={verdict}")


if __name__ == "__main__":
    main()
