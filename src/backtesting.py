"""Rolling-origin backtest of the two prospect-selection approaches.

For every decision year T:
  * training rows  = decision years first..T-1 (their t+1 outcomes are <= T,
                     i.e. already observable when the decision is made at T)
  * scoring rows   = all eligible candidates of year T
  * evaluation     = realised outcomes in T+1 (never seen by the model)
Both approaches rank exactly the same candidate set with the same K.
"""
from __future__ import annotations

import json

import joblib
import numpy as np
import pandas as pd

from .baseline_model import add_baseline_scores
from .evaluation import evaluate, jaccard, summarise
from .feature_engineering import ALL_FEATURES, NO_TARIFF_FEATURES, TARIFF_FEATURES
from .ml_model import fit_predict, select_model
from .ranking import compare_shortlists, rank_within_year, shortlist_table, top_k
from .utils import get_logger, load_config, p, set_seed

log = get_logger("backtest")


def load_dataset() -> pd.DataFrame:
    return pd.read_parquet(p("data", "processed", "analytical_dataset.parquet"))


def permutation_importance_rank(model, X: pd.DataFrame, y: np.ndarray, features, name, n_rep=5, seed=0):
    """Drop in Spearman rank correlation (prediction vs realised outcome) when a
    feature is shuffled; computed on a held-out year."""
    rng = np.random.default_rng(seed)

    def score(Xm):
        Xin = Xm if name == "rf" else Xm.to_numpy(dtype=float)
        return pd.Series(model.predict(Xin)).corr(pd.Series(y), method="spearman")

    base = score(X)
    out = []
    for f in features:
        drops = []
        for _ in range(n_rep):
            Xp = X.copy()
            Xp[f] = rng.permutation(Xp[f].values)
            drops.append(base - score(Xp))
        out.append({"feature": f, "importance_mean": np.mean(drops), "importance_std": np.std(drops)})
    return pd.DataFrame(out).sort_values("importance_mean", ascending=False), base


def run_backtest(cfg: dict | None = None) -> dict:
    cfg = cfg or load_config()
    seed = cfg["project"]["random_seed"]
    set_seed(seed)
    yrs = cfg["years"]
    first, ks, K = yrs["first_decision_year"], cfg["evaluation"]["k_list"], cfg["evaluation"]["k_main"]
    q = tuple(cfg["ml"]["winsor_quantiles"])
    target = "y_d_share_pp"

    df = add_baseline_scores(load_dataset())
    lab = df[df.has_outcome]

    # ---------------------------------------------------------------- selection
    val_res, best = select_model(df, cfg, ALL_FEATURES)
    val_res.assign(params=val_res.params.astype(str)).to_csv(p("outputs", "metrics", "validation_model_selection.csv"), index=False)
    json.dump(best, open(p("outputs", "metrics", "selected_model.json"), "w"), indent=2, default=str)
    name, params = best["model"], best["params"]

    # ---------------------------------------------------------------- rolling test
    pred_frames, fold_info = [], []
    test_years = yrs["test_years"]
    for T in test_years + [yrs["forward_decision_year"]]:
        tr = lab[lab.year.between(first, T - 1)]
        te = df[df.year == T].copy()
        m_all, te["score_ml"] = fit_predict(tr, te, ALL_FEATURES, name, params, target, seed, q)
        _, te["score_ml_no_tariff"] = fit_predict(tr, te, NO_TARIFF_FEATURES, name, params, target, seed, q)
        # second (non-selected) family, reported for transparency only
        other = "rf" if name == "hgb" else "hgb"
        oth = val_res[val_res.model == other].sort_values(cfg["ml"]["selection_metric"], ascending=False).iloc[0]
        _, te["score_ml_alt"] = fit_predict(tr, te, ALL_FEATURES, other, oth.params, target, seed, q)
        pred_frames.append(te)
        fold_info.append({"decision_year": T, "train_years": f"{first}-{T-1}", "n_train": len(tr),
                          "n_candidates": len(te), "n_with_outcome": int(te.has_outcome.sum())})
        if T == test_years[-1]:
            held = te[te.has_outcome]
            imp, base_rho = permutation_importance_rank(m_all, held[ALL_FEATURES], held[target].values,
                                                        ALL_FEATURES, name, seed=seed)
            imp["heldout_year"] = T
            imp["baseline_spearman"] = base_rho
            imp.to_csv(p("outputs", "metrics", "feature_importance_permutation.csv"), index=False)
        if T == yrs["forward_decision_year"]:
            joblib.dump({"model": m_all, "features": ALL_FEATURES, "name": name, "params": params,
                         "trained_on": f"{first}-{T-1}"}, p("outputs", "metrics", "final_model.joblib"))
        log.info("Fold T=%s: train %d rows, scored %d candidates", T, len(tr), len(te))
    preds = pd.concat(pred_frames, ignore_index=True)
    preds.to_parquet(p("outputs", "rankings", "scored_candidates.parquet"), index=False)
    pd.DataFrame(fold_info).to_csv(p("outputs", "metrics", "backtest_folds.csv"), index=False)

    # ---------------------------------------------------------------- metrics
    test = preds[preds.year.isin(test_years)]
    methods = {"Historical momentum (baseline)": "score_baseline",
               "ML ranking": "score_ml",
               "ML without tariff features": "score_ml_no_tariff",
               f"ML alternative family ({'RF' if name == 'hgb' else 'HGB'})": "score_ml_alt",
               "Share-momentum (alt. baseline)": "score_share_momentum"}
    met = evaluate(test, methods, test_years, ks)
    met.to_csv(p("outputs", "metrics", "backtest_metrics_by_year.csv"), index=False)
    summ = summarise(met)
    uni = met.groupby("k")[["universe_precision", "universe_mean_d_share_pp", "universe_mean_export_growth_log"]].mean()
    # expected NDCG@K of a random ranking (Monte Carlo, 500 permutations per test year)
    from .evaluation import ndcg_at_k
    rng0 = np.random.default_rng(seed)
    rnd = {k: np.mean([np.mean([ndcg_at_k(rng0.random(len(dy)), dy.y_d_share_pp.values, k) for _ in range(500)])
                       for _, dy in test[test.has_outcome].groupby("year")]) for k in ks}
    uni["random_ndcg"] = pd.Series(rnd)
    summ.to_csv(p("outputs", "metrics", "backtest_metrics_summary.csv"), index=False)
    uni.to_csv(p("outputs", "metrics", "universe_reference.csv"))

    # paired per-year difference ML - baseline (K main)
    a = met[(met.k == K) & (met.method == "ML ranking")].set_index("year")
    b = met[(met.k == K) & (met.method == "Historical momentum (baseline)")].set_index("year")
    diff = (a[["precision_at_k", "mean_d_share_pp_at_k", "mean_export_growth_log_at_k", "ndcg_at_k"]] -
            b[["precision_at_k", "mean_d_share_pp_at_k", "mean_export_growth_log_at_k", "ndcg_at_k"]])
    diff.to_csv(p("outputs", "metrics", "paired_difference_ml_minus_baseline.csv"))

    # pooled bootstrap of the top-K picks (uncertainty of mean share change)
    rng = np.random.default_rng(seed)
    boot = []
    for meth, col in [("Historical momentum (baseline)", "score_baseline"), ("ML ranking", "score_ml")]:
        picks = pd.concat([top_k(test[test.year == y], col, K) for y in test_years])
        vals = picks.y_d_share_pp.values
        bs = [rng.choice(vals, len(vals)).mean() for _ in range(2000)]
        boot.append({"method": meth, "n_picks": len(vals), "mean": vals.mean(),
                     "ci_low": np.percentile(bs, 2.5), "ci_high": np.percentile(bs, 97.5),
                     "precision": (vals > 0).mean()})
    pd.DataFrame(boot).to_csv(p("outputs", "metrics", "pooled_topk_bootstrap.csv"), index=False)

    # ---------------------------------------------------------------- shortlists
    for T in test_years + [yrs["forward_decision_year"]]:
        d = preds[preds.year == T]
        for meth, col in [("baseline", "score_baseline"), ("ml", "score_ml")]:
            for k in (5, 10, 20):
                shortlist_table(d, col, k, T).to_csv(p("outputs", "rankings", f"top{k}_{meth}_{T}.csv"), index=False)
        cmp = compare_shortlists(top_k(d, "score_baseline", K), top_k(d, "score_ml", K))
        cmp = cmp.merge(d[["iso3", "hs6", "market", "short_desc", "category", "imp_ind", "share_ind",
                           "tariff_adv", "g3_ind", "score_ml", "y_d_share_pp", "y_export_growth_log"]],
                        on=["iso3", "hs6"], how="left")
        cmp.to_csv(p("outputs", "rankings", f"shortlist_comparison_{T}.csv"), index=False)

    # ---------------------------------------------------------------- stability
    stab = []
    for meth, col in methods.items():
        sets = {y: set(map(tuple, top_k(preds[preds.year == y], col, K)[["iso3", "hs6"]].values))
                for y in test_years + [yrs["forward_decision_year"]]}
        ys = sorted(sets)
        for y0, y1 in zip(ys[:-1], ys[1:]):
            stab.append({"method": meth, "from": y0, "to": y1, "jaccard_top10": jaccard(sets[y0], sets[y1])})
    pd.DataFrame(stab).to_csv(p("outputs", "metrics", "ranking_stability.csv"), index=False)

    log.info("Backtest summary (K=%d):\n%s", K, summ[summ.k == K].to_string(index=False))
    return {"summary": summ, "metrics": met, "preds": preds, "best": best}


def run_robustness(cfg: dict | None = None) -> None:
    cfg = cfg or load_config()
    K = cfg["evaluation"]["k_main"]
    test_years = cfg["years"]["test_years"]
    preds = pd.read_parquet(p("outputs", "rankings", "scored_candidates.parquet"))
    test = preds[preds.year.isin(test_years) & preds.has_outcome]
    cols = {"baseline": "score_baseline", "ml": "score_ml"}

    # (a) by category / by market: Spearman and precision of each group's top 10%
    rows = []
    for gcol in ("category", "market"):
        for g, d in test.groupby(gcol):
            for meth, col in cols.items():
                for y, dy in d.groupby("year"):
                    if len(dy) < 10:
                        continue
                    kk = max(1, int(round(0.1 * len(dy))))
                    sel = rank_within_year(dy, col).query("rank <= @kk")
                    rows.append({"group_type": gcol, "group": g, "method": meth, "year": y, "n": len(dy),
                                 "spearman": dy[col].corr(dy.y_d_share_pp, method="spearman"),
                                 "precision_top10pct": sel.y_success.mean(),
                                 "mean_d_share_top10pct": sel.y_d_share_pp.mean()})
    grp = pd.DataFrame(rows).groupby(["group_type", "group", "method"]).agg(
        n=("n", "mean"), spearman=("spearman", "mean"), precision_top10pct=("precision_top10pct", "mean"),
        mean_d_share_top10pct=("mean_d_share_top10pct", "mean")).reset_index()
    grp.to_csv(p("outputs", "metrics", "robustness_by_group.csv"), index=False)

    # (b) leave-one-market-out: does the ML advantage depend on a single market?
    lomo = []
    for m in sorted(test.iso3.unique()):
        d = test[test.iso3 != m]
        for meth, col in cols.items():
            vals = pd.concat([top_k(d[d.year == y], col, K) for y in test_years])
            lomo.append({"excluded_market": m, "method": meth, "precision_at_10": vals.y_success.mean(),
                         "mean_d_share_pp_at_10": vals.y_d_share_pp.mean()})
    pd.DataFrame(lomo).to_csv(p("outputs", "metrics", "robustness_leave_one_market_out.csv"), index=False)

    # (c) strict 1:1 HS codes only (no scope change across HS revisions)
    strict = test[test.strict_1to1 == 1]
    met = evaluate(strict, {"baseline": "score_baseline", "ml": "score_ml"}, test_years, [5, 10, 20])
    summarise(met).to_csv(p("outputs", "metrics", "robustness_strict_hs_codes.csv"), index=False)

    # (d) excluding the 2025 outcome year (US tariff-shock year)
    met2 = evaluate(test, {"baseline": "score_baseline", "ml": "score_ml"}, [y for y in test_years if y < 2024], [5, 10, 20])
    summarise(met2).to_csv(p("outputs", "metrics", "robustness_excluding_2025_outcomes.csv"), index=False)

    # (e) concentration of top-K
    conc = []
    for y in test_years + [cfg["years"]["forward_decision_year"]]:
        for meth, col in cols.items():
            t = top_k(preds[preds.year == y], col, K)
            conc.append({"year": y, "method": meth, "n_markets": t.iso3.nunique(), "n_products": t.hs6.nunique(),
                         "n_categories": t.category.nunique(), "top_market": t.market.value_counts().index[0],
                         "top_market_count": int(t.market.value_counts().iloc[0])})
    pd.DataFrame(conc).to_csv(p("outputs", "metrics", "robustness_concentration.csv"), index=False)
    log.info("Robustness checks written")


if __name__ == "__main__":
    run_backtest()
    run_robustness()
