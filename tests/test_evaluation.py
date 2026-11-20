import numpy as np
import pandas as pd

from src.evaluation import dcg, ndcg_at_k, year_metrics, jaccard


def _frame():
    # 5 candidates with known outcomes
    return pd.DataFrame({
        "iso3": list("ABCDE"), "hs6": ["1"] * 5, "year": 2020,
        "imp_ind": [5, 4, 3, 2, 1],
        "y_d_share_pp": [2.0, -1.0, 0.5, 0.0, 3.0],
        "y_export_growth_log": [0.1, -0.2, 0.0, 0.3, 0.5],
        "y_success": [1, 0, 1, 0, 1.0],
        "perfect": [2.0, -1.0, 0.5, 0.0, 3.0],
        "worst": [-2.0, 1.0, -0.5, 0.0, -3.0],
    })


def test_dcg_simple():
    assert np.isclose(dcg([3, 2]), 3 / np.log2(2) + 2 / np.log2(3))


def test_ndcg_perfect_is_one():
    d = _frame()
    assert np.isclose(ndcg_at_k(d.perfect.values, d.y_d_share_pp.values, 3), 1.0)


def test_ndcg_worst_is_lower():
    d = _frame()
    assert ndcg_at_k(d.worst.values, d.y_d_share_pp.values, 2) < 0.2


def test_precision_at_k():
    d = _frame()
    m = year_metrics(d, "perfect", 2)
    assert m["precision_at_k"] == 1.0           # E (3.0) and A (2.0) both gained
    assert np.isclose(m["mean_d_share_pp_at_k"], 2.5)
    assert m["overlap_true_top_k"] == 1.0
    m2 = year_metrics(d, "worst", 2)             # picks B (-1) and D (0)
    assert m2["precision_at_k"] == 0.0
    assert np.isclose(m2["universe_precision"], 0.6)


def test_jaccard():
    assert jaccard({1, 2}, {2, 3}) == 1 / 3
