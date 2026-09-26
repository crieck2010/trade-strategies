"""RESEARCH SCRATCH — SENT-1 screening record (2026-09-26).

IDEA_ID = "SENT-1"
Status: UNSCREENABLE — no implementation, no backtest.

Rationale
---------
SENT-1 (per docs/research/IDEAS.md) is a social/news sentiment momentum
strategy: go long (short) names with strongly positive (negative)
aggregate sentiment, presumably with some lookback and holding period.

Screening requires a point-in-time historical sentiment panel aligned to
the 2018-01-01..2026-09-25 trade window. What the stack actually offers:

* trade-sentiment (v0.1.2, in-suite) exposes keyless Reddit, StockTwits,
  and Google News RSS sources plus an aggregation pipeline — but every
  source's `fetch(symbol, limit)` returns the CURRENT window of mentions
  only. There is no archive, no backfill endpoint, and no bundled
  historical sentiment dataset anywhere in the suite.
* No third-party historical sentiment feed is connected (no API keys,
  no paid data authorized for this phase).

Fabricating a "sentiment" proxy from price or volume action would not be
screening SENT-1; it would be screening a different (price-based) idea
under a false name, and its in-sample Sharpe would be meaningless for
the trial-3 DSR count. Per the task brief, SENT-1 is therefore marked
UNSCREENABLE rather than proxied.

What would make it screenable (for a future phase, with Charlie's
approval):
  1. A licensed point-in-time news/social sentiment archive (e.g. RavenPack,
     Bloomberg Event Sentiment, or a self-collected archive built by
     running trade-sentiment's collectors on a schedule for 12+ months).
  2. Survivorship-aware entity mapping (ticker -> entity id) for the
     archive's history.
  3. A frozen spec: sentiment definition, aggregation window,
     neutralization (e.g. sector/market), rebalance frequency, costs.

n_screened contribution: 0 (sketches and unrun ideas do not count).
"""

IDEA_ID = "SENT-1"
STATUS = "UNSCREENABLE"
REASON = ("No point-in-time historical sentiment archive exists in the "
          "stack; trade-sentiment only scans current feeds.")
