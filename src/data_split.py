"""
Temporal train/test split for PitchMind AI.

Why not sklearn.train_test_split(shuffle=True)?
------------------------------------------------
Random shuffling would let later matches (whose accumulated _H/_A features
reflect more of the season having been played) leak into training while
earlier matches end up in test -- unrealistic, since in real use the model
only ever has to predict matches that haven't happened yet, using only
data from matches that came before.

Correct approach: sort by date, then split chronologically -- everything
before a cutoff point goes to train, everything after goes to test.
"""

import pandas as pd
import numpy as np
from pathlib import Path



PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "archive" / "df_full_premierleague.csv"
 
FEATURE_COLUMNS = [
    "clearances_avg_H", "corners_avg_H", "fouls_conceded_avg_H", "offsides_avg_H",
    "passes_avg_H", "possession_avg_H", "red_cards_avg_H", "shots_avg_H",
    "shots_on_target_avg_H", "tackles_avg_H", "touches_avg_H", "yellow_cards_avg_H",
    "goals_scored_ft_avg_H", "goals_conced_ft_avg_H", "sg_match_ft_acum_H",
    "goals_scored_ht_avg_H", "goals_conced_ht_avg_H", "sg_match_ht_acum_H",
    "performance_acum_H",
    "clearances_avg_A", "corners_avg_A", "fouls_conceded_avg_A", "offsides_avg_A",
    "passes_avg_A", "possession_avg_A", "red_cards_avg_A", "shots_avg_A",
    "shots_on_target_avg_A", "tackles_avg_A", "touches_avg_A", "yellow_cards_avg_A",
    "goals_scored_ft_avg_A", "goals_conced_ft_avg_A", "sg_match_ft_acum_A",
    "goals_scored_ht_avg_A", "goals_conced_ht_avg_A", "sg_match_ht_acum_A",
    "performance_acum_A",
]


TARGET_COLUMN = "match_outcome"

def derive_match_outcome(df: pd.DataFrame) -> pd.DataFrame:
    """Derive match outcome from goals scored/conceded."""
    conditions = [
        df['goal_home_ft'] > df['goal_away_ft'],
        df['goal_home_ft'] == df['goal_away_ft'],
        df['goal_home_ft'] < df['goal_away_ft']
    ]
    choices = ['H', 'D', 'A']
    df['match_outcome'] = np.select(conditions, choices, default='Unknown')

    return df



def load_and_prepare(path: str) -> pd.DataFrame:
    """Load the dataset, parse dates, and sort chronologically.

    TODO:
    - Read the CSV.
    - Parse 'date' as datetime (you've done this before in check_leakage.py).
    - Sort the WHOLE dataframe by date, ascending.
    - Reset the index.

    Why sort the whole dataframe here, rather than per-team like before?
    Think about what unit this split actually operates on (one match row
    per prediction) vs. what check_leakage.py operated on (one team's
    sequence of matches).
    """
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values(by='date')
    df = df.reset_index(drop=True)
    df  = derive_match_outcome(df)

    return df


def temporal_split(df: pd.DataFrame, test_size: float = 0.2) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split a date-sorted dataframe into train/test, chronologically.

    TODO:
    - Compute the cutoff index: how many rows should go to train, given
      test_size (e.g. 0.2 means last 20% of rows -> test)?
    - Slice df into train (earlier rows) and test (later rows) using .iloc.
    - Print the date range covered by each split, so you can sanity-check
      that train dates all come before test dates with no overlap.
    - Return (train_df, test_df).

    Think about: should test_size=0.2 mean "last 20% of ROWS", or would
    "last N seasons" be a more natural way to split a sports dataset?
    There's no single right answer -- but you should be able to justify
    whichever one you pick.
    """
    cutoff_index = int(len(df) * (1 - test_size))
    train_df = df.iloc[:cutoff_index]
    test_df = df.iloc[cutoff_index:]

    print(f"Train date range: {train_df['date'].min()} to {train_df['date'].max()}")
    print(f"Test date range: {test_df['date'].min()} to {test_df['date'].max()}")

    return train_df, test_df


def get_X_y(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Split a dataframe into feature matrix X and target vector y.

    TODO:
    - X = df[FEATURE_COLUMNS]
    - y = df[TARGET_COLUMN]
    - Return (X, y)
    """
    X = df[FEATURE_COLUMNS]
    y = df[TARGET_COLUMN]
    return X, y


if __name__ == "__main__":

    df = load_and_prepare(DATA_PATH)
    train_df, test_df = temporal_split(df, test_size=0.2)

    X_train, y_train = get_X_y(train_df)
    X_test, y_test = get_X_y(test_df)

    print(f"Train shape: {X_train.shape}, Test shape: {X_test.shape}")
    print(f"Train target distribution:\n{y_train.value_counts(normalize=True)}")
    print(f"Test target distribution:\n{y_test.value_counts(normalize=True)}")
