# src/pipeline.py
"""
Core numeric pipeline for the NBA props analyzer.

- Load props from a CSV
- Convert American odds to implied probabilities
- Estimate a "true" probability (simple placeholder model)
- Compute expected value (EV) per $1 bet
"""

from __future__ import annotations
import pandas as pd


def load_props(csv_path: str) -> pd.DataFrame:
    """
    Load props from a CSV file into a pandas DataFrame.

    Expected columns:
        player, stat_line, american_odds
    """
    df = pd.read_csv(csv_path)
    if "american_odds" not in df.columns:
        raise ValueError("CSV must contain an 'american_odds' column.")
    return df


def american_to_prob(odds: float) -> float:
    """
    Convert American odds to implied win probability (no vig removed).

    Positive odds: P = 100 / (odds + 100)
    Negative odds: P = -odds / (-odds + 100)
    """
    odds = float(odds)
    if odds > 0:
        return 100.0 / (odds + 100.0)
    else:
        return -odds / (-odds + 100.0)


def compute_ev_per_dollar(true_prob: float, odds: float) -> float:
    """
    Expected value per $1 stake given:
      - true_prob: your estimated probability that the bet wins
      - odds: American odds for the bet

    Returns:
        EV per $1 bet.
    """
    p = float(true_prob)
    odds = float(odds)

    # Net return if the bet wins (for a $1 stake)
    if odds > 0:
        win_return = odds / 100.0
    else:
        win_return = 100.0 / -odds

    lose_return = -1.0

    ev = p * win_return + (1.0 - p) * lose_return
    return ev


def enrich_props(df: pd.DataFrame) -> pd.DataFrame:
    """
    Take a raw props DataFrame and add:
      - implied_prob
      - true_prob (placeholder model)
      - ev_per_dollar

    For now, 'true_prob' is just a slightly adjusted version of implied_prob.
    You can later plug in a real model here.
    """
    df = df.copy()

    # Implied probability from American odds
    df["implied_prob"] = df["american_odds"].apply(american_to_prob)

    # Placeholder "true" probability: adjust implied_prob slightly
    # (e.g., assume sportsbook has a small edge)
    df["true_prob"] = df["implied_prob"] * 0.98

    # Expected value per $1 bet
    df["ev_per_dollar"] = df.apply(
        lambda row: compute_ev_per_dollar(row["true_prob"], row["american_odds"]),
        axis=1,
    )

    return df
