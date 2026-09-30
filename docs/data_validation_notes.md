# Data Validation: Leakage Check on Accumulated Features

## Why this check exists

The dataset includes engineered "accumulated" columns (e.g. `goals_scored_ft_avg_H`,
`performance_acum_H`) that the data dictionary claims are computed using only
matches **strictly before** the current row ("accumulated until the last match").
Before trusting these as pre-match-safe model features, that claim was
independently verified rather than assumed.

## Method

For a given column (e.g. `goals_scored_ft_avg_H`), for every (team, season)
pair, matches were sorted chronologically and a manual rolling average was
computed by hand from raw per-match columns (`goal_home_ft`, `goal_away_ft`).
This manual value was compared against the stored value at each row, using
a small float tolerance (`< 0.01`).

Script: `src/check_leakage.py`

## Key finding: season boundaries matter

An early version of this check treated each team's home matches as one
continuous sequence across all seasons, and found ~3,100 "mismatches" out of
~4,000 checks. Investigating this revealed the real cause: the `_H`/`_home`
features reset at the start of each new season (per the data dictionary),
but the check wasn't season-aware, so it was comparing accumulations across
season boundaries — not a real leakage issue, but a flawed check. Restricting
the check to within-season sequences fixed this.

**Lesson:** an initial "leakage found" result was actually a bug in the
validation logic itself, not the dataset. Validation code needs its own
scrutiny, not just the data it's checking.

## Key finding: `_A` naming in the data dictionary is misleading

The data dictionary describes `_A` columns as "away team ... in matches as
host", which reads like a contradiction (an away team can't be the host).
Verified directly: `goals_scored_ft_avg_A` matches each team's own
**away**-match history (not anything host-related), confirming this is very
likely a copy-paste artifact in the documentation, not a real distinct
definition. Treat `_A` as "this team's performance specifically as visitor,"
parallel to `_H` being "this team's performance specifically as host."

## Results: accumulated feature checks

| Column checked | Team-season pairs | Row-level checks | Mismatches |
|---|---|---|---|
| `goals_scored_ft_avg_H` | 220 | 3,850 | 0 |
| `goals_conced_ft_avg_H` | 220 | 3,850 | 0 |
| `goals_scored_ft_avg_A` | 220 | 3,850 | 0 |

All columns tested clean: fully consistent with "accumulated using only
prior matches, within season."

## Feature selection decision: `_H`/`_A` over `_home`/`_away`

For predicting a specific fixture (home team X vs away team Y), the venue-
restricted columns are used rather than the season-wide ones:
- Home team's features → `_H` (that team's performance specifically as host)
- Away team's features → `_A` (that team's performance specifically as visitor)

`_home`/`_away` (season-wide, not venue-restricted) are not used as primary
features, since they dilute a team's home-specific and away-specific form
together — less relevant when the model always knows, at prediction time,
which role each team is playing in the upcoming fixture.

## Excluded columns: raw per-match stats (target leakage)

The dataset also contains raw, single-match columns with no `_avg`/`_acum`
suffix — e.g. `goal_home_ft`, `goal_away_ft`, `home_shots`, `away_shots`,
`home_possession`, `away_possession`, `home_passes`, `away_passes`, and
similar. Per the data dictionary, these describe what happened **in this
match** (final-time result, match-day stats) — not history accumulated
before it.

These are **excluded from the model's feature set entirely.** They are not
a "some risk of overfitting" case — they are direct target leakage:
`goal_home_ft`/`goal_away_ft` alone deterministically define the match
outcome (the actual prediction target), so including them would let the
model "cheat" rather than learn.

**General rule applied:** a feature is safe to use only if it would
genuinely be knowable *before kickoff* of the match being predicted —
nothing derived from that match's own final-time result or in-game stats.

**Important nuance:** these raw columns are not useless — they are the
underlying data the `_avg_H`/`_avg_A` accumulated columns were themselves
built from (e.g. a team's `goals_scored_ft_avg_H` at match N is the mean of
`goal_home_ft` from that team's home matches 1..N-1). They remain valid
inputs for engineering *new* historical/accumulated features later, just
never as direct inputs describing the match currently being predicted.

## What is still an assumption, not verified

- The `_home`/`_away` (season-wide, not venue-restricted) column family is
  assumed to follow the same construction logic as `_H`/`_A`, since it
  appears to be produced by the same pipeline — but this has not been
  independently confirmed (and is moot for now, since these columns aren't
  being used as primary features anyway — see above).
- Non-average accumulated columns (e.g. `performance_acum_H`/`performance_acum_A`,
  which are points-based rather than a simple mean) were not tested, since
  they require different manual-computation logic.
- `result_ht` (half-time result) and other half-time-stage columns have not
  yet been evaluated for leakage risk. Half-time data occurs *during* the
  match being predicted, so — unlike full-time raw stats, which are clearly
  post-match — this needs its own deliberate judgment call before use.

If these columns behave differently under scrutiny, this document should be
updated and the affected features re-evaluated before being used in
modeling.
