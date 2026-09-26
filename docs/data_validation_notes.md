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

Both columns tested clean: fully consistent with "accumulated using only
prior matches, within season."

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
