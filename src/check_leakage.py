import pandas as pd

DATA_PATH = "../data/raw/archive/df_full_premierleague.csv"


def load_data(path: str) -> pd.DataFrame:
    data = pd.read_csv(path)
    data['date'] = pd.to_datetime(data['date'])
    return data


def get_team_home_matches(df: pd.DataFrame, team: str, season) -> pd.DataFrame:
    """Return only the rows where `team` played as the HOME team,
    WITHIN one season, sorted chronologically (oldest first).

    Restricted to a single season because "_avg_H"/"_avg_home" features
    reset each season (data dictionary: "accumulated in the season") —
    mixing seasons would make row-to-row accumulation meaningless.
    """
    rows = df[(df["home_team"] == team) & (df["season"] == season)]
    rows = rows.sort_values(by='date', ascending=True)
    rows = rows.reset_index(drop=True)
    return rows


def manual_accumulated_average(team_matches: pd.DataFrame, up_to_row: int, source_column: str = "goal_home_ft") -> float:
    """Compute the mean of `source_column` over rows strictly before `up_to_row`.

    `source_column` defaults to 'goal_home_ft' (used for validating
    goals_scored_ft_avg_H), but can be swapped — e.g. 'goal_away_ft' to
    validate goals_conced_ft_avg_H (goals conceded by the home team).
    """
    prior_matches = team_matches.iloc[0:up_to_row]
    return prior_matches[source_column].mean()


def compare_to_stored_value(team_matches: pd.DataFrame, row_index: int, column: str, source_column: str = "goal_home_ft") -> None:
    manual_accu_no = manual_accumulated_average(team_matches, row_index, source_column)
    stored_value = team_matches.loc[row_index, column]
    print(f"Manually accumulated value: {manual_accu_no}")
    print(f"Stored value:               {stored_value}")
    difference = abs(manual_accu_no - stored_value)
    is_match = difference < 0.01
    print("Match!" if is_match else "MISMATCH!")


def check_all_teams(df: pd.DataFrame, column: str, source_column: str = "goal_home_ft") -> list:
    """Run the leakage check for every (team, season) pair, at every
    eligible row, and return a list of mismatches (empty = all passed).
    """
    mismatches = []
    checks_run = 0

    team_season_pairs = df[['home_team', 'season']].drop_duplicates().values

    for team, season in team_season_pairs:
        team_matches = get_team_home_matches(df, team, season)

        # Row 0 has no prior matches -> nothing to compare, so start at row 1
        for row_index in range(1, len(team_matches)):
            manual_value = manual_accumulated_average(team_matches, row_index, source_column)
            stored_value = team_matches.loc[row_index, column]
            checks_run += 1

            if abs(manual_value - stored_value) >= 0.01:
                mismatches.append({
                    "team": team,
                    "season": season,
                    "row_index": row_index,
                    "manual_value": manual_value,
                    "stored_value": stored_value,
                })

    print(f"Ran {checks_run} checks across {len(team_season_pairs)} team-season pairs.")
    print(f"Mismatches found: {len(mismatches)}")
    return mismatches


def get_team_away_matches(df: pd.DataFrame, team: str, season) -> pd.DataFrame:
    """Return only the rows where `team` played as the AWAY team,
    WITHIN one season, sorted chronologically (oldest first).

    Mirrors get_team_home_matches, but filters on away_team instead of
    home_team. Used to test what the "_A" column family actually tracks:
    the away team's own away-match history, or something else.
    """
    rows = df[(df["away_team"] == team) & (df["season"] == season)]
    rows = rows.sort_values(by='date', ascending=True)
    rows = rows.reset_index(drop=True)
    return rows


def check_all_teams_away(df: pd.DataFrame, column: str, source_column: str = "goal_away_ft") -> list:
    """Same logic as check_all_teams, but for the away side: checks whether
    `column` (e.g. goals_scored_ft_avg_A) matches a manually-computed
    rolling average of `source_column` over each team's own AWAY matches,
    within season.
    """
    mismatches = []
    checks_run = 0

    team_season_pairs = df[['away_team', 'season']].drop_duplicates().values

    for team, season in team_season_pairs:
        team_matches = get_team_away_matches(df, team, season)

        for row_index in range(1, len(team_matches)):
            manual_value = manual_accumulated_average(team_matches, row_index, source_column)
            stored_value = team_matches.loc[row_index, column]
            checks_run += 1

            if abs(manual_value - stored_value) >= 0.01:
                mismatches.append({
                    "team": team,
                    "season": season,
                    "row_index": row_index,
                    "manual_value": manual_value,
                    "stored_value": stored_value,
                })

    print(f"Ran {checks_run} checks across {len(team_season_pairs)} team-season pairs.")
    print(f"Mismatches found: {len(mismatches)}")
    return mismatches


if __name__ == "__main__":
    TEAM = "Arsenal"
    COLUMN = "goals_scored_ft_avg_H"
    ROW_TO_CHECK = 5

    df = load_data(DATA_PATH)
    SEASON = df[df["home_team"] == TEAM]["season"].iloc[0]  # Arsenal's first season, for the single-team demo
    team_matches = get_team_home_matches(df, TEAM, SEASON)

    print(f"{TEAM} has {len(team_matches)} home matches in season {SEASON}.")
    compare_to_stored_value(team_matches, ROW_TO_CHECK, COLUMN)

    print()
    print("Checking ALL teams, ALL seasons, ALL rows...")
    print(f"Column: {COLUMN}")
    failures = check_all_teams(df, COLUMN)
    if failures:
        print("First few failures:")
        for f in failures[:5]:
            print(f)

    print()
    print("Second spot check: goals_conced_ft_avg_H (goals conceded by home team)")
    failures_2 = check_all_teams(df, "goals_conced_ft_avg_H", source_column="goal_away_ft")
    if failures_2:
        print("First few failures:")
        for f in failures_2[:5]:
            print(f)
