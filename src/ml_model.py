"""Approach 2 -- supervised ML ranking.

The model predicts the next-year change in India's import-market share
(percentage points) and candidates are ranked by the prediction.

Candidate models: HistGradientBoostingRegressor and RandomForestRegressor.
Hyper-parameters and the model family are selected ONLY on validation decision
years (rolling origin, 2018-2020); the test years are never touched.
All preprocessing (target winsorisation, imputation, encoding) is fitted on the
training rows of each fold only.
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from .evaluation import ndcg_at_k
from .feature_engineering import CAT_FEATURES
from .utils import get_logger

log = get_logger("ml")


class WinsorisedRegressor:
    """Clip the training target to train-set quantiles before fitting."""

    def __init__(self, model, q=(0.01, 0.99)):
        self.model, self.q = model, q

    def fit(self, X, y):
        lo, hi = np.nanquantile(y, self.q)
        self.clip_ = (lo, hi)
        self.model.fit(X, np.clip(y, lo, hi))
        return self

    def predict(self, X):
        return self.model.predict(X)


def make_model(name: str, params: dict, features: list[str], seed: int):
    cat_idx = [i for i, f in enumerate(features) if f in CAT_FEATURES]
    if name == "hgb":
        return HistGradientBoostingRegressor(categorical_features=cat_idx or None,
                                             random_state=seed, early_stopping=False, **params)
    if name == "rf":
        num = [f for f in features if f not in CAT_FEATURES]
        cats = [f for f in features if f in CAT_FEATURES]
        pre = ColumnTransformer([
            ("num", SimpleImputer(strategy="median"), num),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cats),
        ])
        rf = RandomForestRegressor(random_state=seed, n_jobs=-1, **params)
        return Pipeline([("pre", pre), ("rf", rf)])
    raise ValueError(name)


def fit_predict(train: pd.DataFrame, test: pd.DataFrame, features: list[str], name: str,
                params: dict, target: str, seed: int, q=(0.01, 0.99)):
    model = WinsorisedRegressor(make_model(name, params, features, seed), q)
    Xtr = train[features] if name == "rf" else train[features].to_numpy(dtype=float)
    Xte = test[features] if name == "rf" else test[features].to_numpy(dtype=float)
    model.fit(Xtr, train[target].to_numpy(dtype=float))
    return model, model.predict(Xte)


def param_grid(spec: dict):
    keys = list(spec)
    for vals in itertools.product(*[spec[k] for k in keys]):
        yield dict(zip(keys, vals))


def select_model(df: pd.DataFrame, cfg: dict, features: list[str]) -> tuple[pd.DataFrame, dict]:
    """Rolling-origin validation on cfg.years.validation_years only."""
    seed = cfg["project"]["random_seed"]
    target = "y_d_share_pp"
    first = cfg["years"]["first_decision_year"]
    q = tuple(cfg["ml"]["winsor_quantiles"])
    rows = []
    lab = df[df.has_outcome]
    for name, spec in cfg["ml"]["models"].items():
        for params in param_grid(spec):
            fold_scores = []
            for v in cfg["years"]["validation_years"]:
                tr = lab[lab.year.between(first, v - 1)]
                va = lab[lab.year == v]
                _, pred = fit_predict(tr, va, features, name, params, target, seed, q)
                fold_scores.append({
                    "ndcg_at_20": ndcg_at_k(pred, va[target].values, 20),
                    "ndcg_at_10": ndcg_at_k(pred, va[target].values, 10),
                    "spearman": pd.Series(pred).corr(va[target].reset_index(drop=True), method="spearman"),
                    "mean_d_share_top20": va[target].values[np.argsort(-pred)[:20]].mean(),
                })
            fs = pd.DataFrame(fold_scores).mean()
            rows.append({"model": name, "params": params, **fs.to_dict()})
            log.info("validation %s %s -> ndcg@20=%.3f spearman=%.3f", name, params,
                     fs["ndcg_at_20"], fs["spearman"])
    res = pd.DataFrame(rows)
    metric = cfg["ml"]["selection_metric"]
    best = res.sort_values(metric, ascending=False).iloc[0]
    log.info("Selected model: %s %s (%s=%.3f)", best.model, best.params, metric, best[metric])
    return res, {"model": best.model, "params": best.params}
