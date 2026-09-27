"""RESEARCH SCRATCH — Track-1 deferral statement (SENTDIV-1, ATTN-1,
EVTDRIFT-1, SENTCAP-1).

NOT a strategy module. Round-2 Phase B screening note (2026-09-26).

STATUS: DEFERRED — NOT SCREENED, and deliberately so.

The Phase-0 backfill investigation (trade-sentiment v0.3.0 archive, sqlite3,
`trade_sentiment.archive.Archive`, `query(symbol, as_of)` with SQL-enforced
no-lookahead) found NO keyless historical text source for point-in-time
sentiment:

  - GDELT's query API rate-refuses programmatic access.
  - GDELT bulk files are not ticker-addressable.
  - No keyless Reddit/StockTwits/Google-News archive is ticker-addressable
    at the required daily grain.

Conclusion on record: **no sentiment history exists before deployment, and
none was fabricated.** The archive accumulates from deployment forward;
a daily accumulation job (see the cron command below, for Charlie's
approval — NOT set up by the research agent) will build real history.

Screening the four Track-1 theses against price-derived proxies (e.g.,
volatility spikes standing in for "attention", returns standing in for
"tone") and calling the result sentiment screening would be dishonest —
it would test price signals while claiming to test sentiment. The kill
criterion of every Track-1 thesis is explicitly about the INCREMENTAL
value of sentiment over price; a price-proxy screen cannot measure that.
So: Track-1 screening happens once real archive history exists (the
sentiment contract in each thesis requires >=2y of ticker-day observations
for z-score/percentile baselines).

DSR honesty: n_screened for round 2 counts ONLY ideas actually screened
(RVBOND-1, REGCOND-1). These four do NOT count — they were never screened,
and no placeholder trials are entered for them.

Suggested accumulation cron (NOT enabled — for Charlie's approval):
  # daily weekday sentiment archive accumulation, ~30 min after US close
  30 16 * * 1-5 PYTHONPATH=$HOME/workspace/trade-suite/trade-sentiment/src \
      python3 -m trade_sentiment scan AAPL MSFT NVDA AMZN META GOOGL TSLA \
      AVGO BRK-B JPM XOM UNH V MA JNJ WMT ORCL HD PG BAC COST LLY NFLX \
      CRM AMD ADBE QCOM TXN LIN CAT IBM GE INTU NOW AMAT BKNG ISRG VRTX \
      --archive $HOME/.trade-sentiment/sentiment-archive.db \
      >> $HOME/.trade-sentiment/cron.log 2>&1
  # notes: --archive takes the DB path (default ~/.trade-sentiment/
  # sentiment-archive.db if omitted from config); ticker list should match
  # the eventual screening universe; weekend runs are pointless (no new
  # social chatter window beyond the 24h default); sources are keyless but
  # watch rate limits as the universe grows.

IDEAS_DEFERRED = ["SENTDIV-1", "ATTN-1", "EVTDRIFT-1", "SENTCAP-1"]
"""

IDEAS_DEFERRED = ["SENTDIV-1", "ATTN-1", "EVTDRIFT-1", "SENTCAP-1"]
STATUS = "DEFERRED"
REASON = ("No keyless historical sentiment source exists; the archive has "
          "no history before deployment and none was fabricated. Screening "
          "on price-derived proxies would be dishonest.")
