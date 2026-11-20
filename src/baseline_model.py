"""Approach 1 -- Historical Export Momentum baseline.

Score = annualised 3-year log growth of India's exports to the market
        (importer-reported), g3_ind = [ln(X_t + c) - ln(X_{t-3} + c)] / 3,
        c = US$100,000 smoothing constant.

Commercial logic: an export-promotion body backs product-markets where Indian
exporters have already been gaining traction. No parameters are fitted, so the
baseline cannot leak information from the evaluation years.
"""
from __future__ import annotations

import pandas as pd


def momentum_score(df: pd.DataFrame) -> pd.Series:
    return df["g3_ind"].astype(float)


def share_momentum_score(df: pd.DataFrame) -> pd.Series:
    """Alternative (robustness) baseline: 3-year change in India's market share."""
    return df["d3_share_ind"].astype(float)


def add_baseline_scores(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["score_baseline"] = momentum_score(out)
    out["score_share_momentum"] = share_momentum_score(out)
    return out
