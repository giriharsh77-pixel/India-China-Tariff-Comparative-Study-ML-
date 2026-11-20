"""Ranking metrics computed only from realised (held-out) t+1 outcomes."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .ranking import rank_within_year


def dcg(gains: np.ndarray) -> float:
    gains = np.asarray(gains, dtype=float)
    return float(np.sum(gains / np.log2(np.arange(2, len(gains) + 2))))


def ndcg_at_k(scores: np.ndarray, outcomes: np.ndarray, k: int) -> float:
    """NDCG@K with relevance = max(realised share gain, 0) in pp."""
    rel = np.clip(np.asarray(outcomes, dtype=float), 0, None)
    order = np.argsort(-np.asarray(scores, dtype=float), kind="stable")[:k]
    ideal = np.sort(rel)[::-1][:k]
    denom = dcg(ideal)
    return dcg(rel[order]) / denom if denom > 0 else np.nan


def year_metrics(d: pd.DataFrame, score_col: str, k: int, top_q: float = 0.9) -> dict:
    """Metrics for one decision year. d = full candidate universe with outcomes."""
    d = d[d.y_d_share_pp.notna()]
    r = rank_within_year(d, score_col)
    sel = r[r["rank"] <= k]
    top_cut = d.y_d_share_pp.quantile(top_q)
    true_top_k = set(map(tuple, d.nlargest(k, "y_d_share_pp")[["iso3", "hs6"]].values))
    sel_keys = set(map(tuple, sel[["iso3", "hs6"]].values))
    rho = spearmanr(d[score_col], d.y_d_share_pp, nan_policy="omit").correlation
    return {
        "k": k, "n_candidates": len(d),
        "precision_at_k": sel.y_success.mean(),
        "top_decile_precision_at_k": (sel.y_d_share_pp >= top_cut).mean(),
        "mean_d_share_pp_at_k": sel.y_d_share_pp.mean(),
        "median_d_share_pp_at_k": sel.y_d_share_pp.median(),
        "mean_export_growth_log_at_k": sel.y_export_growth_log.mean(),
        "ndcg_at_k": ndcg_at_k(d[score_col].values, d.y_d_share_pp.values, k),
        "overlap_true_top_k": len(sel_keys & true_top_k) / k,
        "spearman_all": rho,
        "universe_precision": d.y_success.mean(),
        "universe_mean_d_share_pp": d.y_d_share_pp.mean(),
        "universe_mean_export_growth_log": d.y_export_growth_log.mean(),
        "n_markets_in_top_k": sel.iso3.nunique(),
        "n_products_in_top_k": sel.hs6.nunique(),
    }


def evaluate(df: pd.DataFrame, score_cols: dict, years, ks) -> pd.DataFrame:
    rows = []
    for y in years:
        d = df[df.year == y]
        for name, col in score_cols.items():
            for k in ks:
                m = year_metrics(d, col, k)
                m.update({"year": y, "method": name})
                rows.append(m)
    return pd.DataFrame(rows)


def summarise(metrics: pd.DataFrame) -> pd.DataFrame:
    cols = ["precision_at_k", "top_decile_precision_at_k", "mean_d_share_pp_at_k",
            "median_d_share_pp_at_k", "mean_export_growth_log_at_k", "ndcg_at_k",
            "overlap_true_top_k", "spearman_all"]
    return metrics.groupby(["method", "k"])[cols].mean().reset_index()


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a or b) else np.nan
