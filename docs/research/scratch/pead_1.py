"""RESEARCH SCRATCH — PEAD-1 design sketch (2026-09-26).

IDEA_ID = "PEAD-1"
Status: SKETCH ONLY — no implementation, no backtest (per task brief).

Thesis (from docs/research/IDEAS.md): post-earnings-announcement drift —
buy (sell) stocks with large positive (negative) earnings surprises and
hold the drift for ~60 trading days.

Why sketch-only
--------------
A real screen needs point-in-time earnings-announcement dates plus a
surprise measure (actual vs consensus at the announcement time).
The stack has no historical earnings calendar, no IBES-style consensus
history, and no authorized paid feed for this phase. Reconstructing
"surprises" from price jumps alone would screen a different idea
(earnings-gap momentum) under PEAD's name.

Sketch of a future screenable spec (for later phases, Charlie's call):
  * Data: point-in-time earnings dates + consensus surprise (SUE =
    (actual - consensus)/dispersion, or simple price-gap deciles).
  * Universe: liquid US equities; exclude microcaps and announcement-day
    halts.
  * Signal: top/bottom SUE decile within ±2 days of the announcement.
  * Holding: 60 trading days or next earnings, whichever first;
    equal-weight; monthly cohort formation.
  * Costs: 5 bps/side; model the announcement-day open gap explicitly
    (t -> t+1 execution already forces buying the gap — keep it).
  * Controls: sector neutrality; exclude the Fama-French earnings
    months already explained by momentum overlap — report PEAD x MOM
    interaction.
  * Overfit discipline: pre-register surprise definition and holding
    window; drift has decayed in published literature, so OOS by
    subperiod (pre/post-2015) is the key table.

n_screened contribution: 0 (sketches do not count).
"""

IDEA_ID = "PEAD-1"
STATUS = "SKETCH"
REASON = ("No point-in-time earnings-date / consensus-surprise history in "
          "the stack.")
