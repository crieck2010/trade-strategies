"""RESEARCH SCRATCH — VOLPREM-1 design sketch (2026-09-26).

IDEA_ID = "VOLPREM-1"
Status: SKETCH ONLY — no implementation, no backtest (per task brief).

Thesis (from docs/research/IDEAS.md): harvest the volatility risk premium
by systematically selling overpriced implied volatility — e.g. short
delta-hedged strangles/straddles on index or single-name options, or a
simpler proxy: short VIX futures / long VIX-roll-yield when the term
structure is in contango.

Why sketch-only
--------------
A real screen needs historical OPTION chains (strikes, expiries, IVs,
greeks) or at minimum a daily implied-vol surface history. The stack has
trade-data-options (chain snapshot tooling) and trade-volsurface, but no
historical options archive and no authorized paid feed for this phase.
Any "backtest" would be invented data — explicitly out of scope.

Sketch of a future screenable spec (for later phases, Charlie's call):
  * Universe: SPX/SPY options (most liquid, tightest spreads).
  * Signal: 30-day implied vol percentile vs trailing 1y realized vol;
    sell 30-delta strangles when IVp > 70th percentile.
  * Position: delta-hedged daily with the underlying; 1-2% risk per trade.
  * Holding: to 21 DTE or 50% of max profit; hard stop at 2x premium.
  * Costs: real option commissions + realistic bid/ask (mid +/- half
    spread at minimum; no mid-price fills).
  * Benchmarks: buy-and-hold SPY; short-VIX-ETN with its known blowup
    tails (2018-02 must appear in-sample).
  * Overfit discipline: pre-register entry/exit/hedge rules; the strategy
    has obvious tail risk, so maxDD and tail metrics dominate Sharpe.

n_screened contribution: 0 (sketches do not count).
"""

IDEA_ID = "VOLPREM-1"
STATUS = "SKETCH"
REASON = "No historical options-chain / IV-surface archive in the stack."
