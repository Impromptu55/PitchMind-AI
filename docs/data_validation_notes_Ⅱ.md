# Data Validation: Leakage Check on Accumulated Features

## Why this check exists

The dataset includes engineered "accumulated" columns (e.g. `goals_scored_ft_avg_H`,
`performance_acum_H`) that the data dictionary claims are computed using only
matches **strictly before** the current row ("accumulated until the last match").
Before trusting these as pre-match-safe model features, that claim was
independently verified rather than assumed.

## Method

For a given column (e.g. `goals_scored_ft_avg_H`), for every (team, season)
pair, home matches were sorted chronologically and a manual rolling average
was computed by hand from raw per-match columns (`goal_home_ft`,
`goal_away_ft`). This manual value was compared against the stored value at
each row, using a small float tolerance (`< 0.01`).

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

## Results

| Column checked | Team-season pairs | Row-level checks | Mismatches |
|---|---|---|---|
| `goals_scored_ft_avg_H` | 220 | 3,850 | 0 |
| `goals_conced_ft_avg_H` | 220 | 3,850 | 0 |
| `goals_scored_ft_avg_A` | 220 | 3,850 | 0 |

Note on `_A` naming: the data dictionary describes `_A` columns as "away team
... in matches as host", which reads like a contradiction (an away team
can't be the host). Verified directly: `goals_scored_ft_avg_A` matches each
team's own **away**-match history (not anything host-related), confirming
this is very likely a copy-paste artifact in the documentation, not a real
distinct definition. Treat `_A` as "this team's performance specifically as
visitor," parallel to `_H` being "this team's performance specifically as
host."

Both columns tested clean: fully consistent with "accumulated using only
prior matches, within season."

## Feature selection decision informed by this validation

For predicting a specific fixture (home team X vs away team Y), the venue-
restricted columns are used rather than the season-wide ones:
- Home team's features → `_H` (that team's performance specifically as host)
- Away team's features → `_A` (that team's performance specifically as visitor)

`_home`/`_away` (season-wide, not venue-restricted) are not used as primary
features, since they dilute a team's home-specific and away-specific form
together — less relevant when the model always knows, at prediction time,
which role each team is playing in the upcoming fixture.

## What is still an assumption, not verified

- Only the `_H` (home-team-as-host) family was directly tested. The `_A`
  (away-team-as-host) and `_home`/`_away` (season-wide, not host-restricted)
  column families are assumed to follow the same construction logic, since
  they appear to be produced by the same pipeline — but this has not been
  independently confirmed.
- Non-average accumulated columns (e.g. `performance_acum_H`, which is
  points-based rather than a simple mean) were not tested, since they
  require different manual-computation logic.

If these columns behave differently under scrutiny, this document should be
updated and the affected features re-evaluated before being used in
modeling.
