"""Collect every number quoted in the report / presentation into
outputs/results_summary.json (single source of truth for the documents)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.utils import load_config  # noqa: E402

M = ROOT / "outputs" / "metrics"
R = ROOT / "outputs" / "rankings"
S = ROOT / "outputs" / "simulation_results"


def recs(df):
    return json.loads(df.to_json(orient="records"))


def main():
    cfg = load_config()
    yrs = cfg["years"]
    T, F, K = yrs["test_years"][-1], yrs["forward_decision_year"], cfg["evaluation"]["k_main"]
    ds = pd.read_parquet(ROOT / "data/processed/analytical_dataset.parquet")
    panel = pd.read_parquet(ROOT / "data/processed/full_panel.parquet")
    summ = pd.read_csv(M / "backtest_metrics_summary.csv")
    by_year = pd.read_csv(M / "backtest_metrics_by_year.csv")
    uni = pd.read_csv(M / "universe_reference.csv")
    out = {
        "dataset": {
            "n_rows": int(len(ds)), "n_with_outcome": int(ds.has_outcome.sum()),
            "n_markets": int(ds.iso3.nunique()), "n_products": int(ds.hs6.nunique()),
            "years": [int(ds.year.min()), int(ds.year.max())],
            "rows_per_year": {int(k): int(v) for k, v in ds.groupby("year").size().items()},
            "share_tariff_imputed": float(ds.tariff_imputed.mean()),
            "share_nonzero_adv": float((ds.tariff_adv.abs() > 0.05).mean()),
            "share_india_adv": float((ds.tariff_adv > 0.05).mean()),
            "share_china_adv": float((ds.tariff_adv < -0.05).mean()),
            "base_rate_success": float(ds.y_success.mean()),
            "mean_d_share": float(ds.y_d_share_pp.mean()),
            "panel_rows": int(len(panel)),
            "categories": ds.drop_duplicates("hs6").category.value_counts().to_dict(),
            "n_strict": int(ds.drop_duplicates("hs6").strict_1to1.sum()),
            "india_imports_2024_bn": float(panel[panel.year == 2024].imp_ind.sum() / 1e9),
            "china_imports_2024_bn": float(panel[panel.year == 2024].imp_chn.sum() / 1e9),
            "world_imports_2024_bn": float(panel[panel.year == 2024].imp_wld.sum() / 1e9),
            "india_imports_2015_bn": float(panel[panel.year == 2015].imp_ind.sum() / 1e9),
            "china_imports_2015_bn": float(panel[panel.year == 2015].imp_chn.sum() / 1e9),
        },
        "selected_model": json.load(open(M / "selected_model.json")),
        "validation": recs(pd.read_csv(M / "validation_model_selection.csv")),
        "folds": recs(pd.read_csv(M / "backtest_folds.csv")),
        "summary": recs(summ),
        "universe": recs(uni),
        "by_year": recs(by_year[by_year.k == K]),
        "paired_diff": recs(pd.read_csv(M / "paired_difference_ml_minus_baseline.csv")),
        "bootstrap": recs(pd.read_csv(M / "pooled_topk_bootstrap.csv")),
        "stability": recs(pd.read_csv(M / "ranking_stability.csv").groupby("method").jaccard_top10.mean().reset_index()),
        "importance": recs(pd.read_csv(M / "feature_importance_permutation.csv").head(15)),
        "robust_group": recs(pd.read_csv(M / "robustness_by_group.csv")),
        "robust_lomo": recs(pd.read_csv(M / "robustness_leave_one_market_out.csv")),
        "robust_strict": recs(pd.read_csv(M / "robustness_strict_hs_codes.csv")),
        "robust_ex2025": recs(pd.read_csv(M / "robustness_excluding_2025_outcomes.csv")),
        "concentration": recs(pd.read_csv(M / "robustness_concentration.csv")),
        "div_bins": recs(pd.read_csv(M / "diversion_by_advantage_bin.csv")),
        "div_change": recs(pd.read_csv(M / "diversion_by_advantage_change.csv")),
        "div_reg": recs(pd.read_csv(M / "diversion_regressions.csv")),
        "div_market": recs(pd.read_csv(M / "diversion_by_market.csv")),
        "scenarios": recs(pd.read_csv(S / f"scenario_summary_{F}.csv")),
        "sensitivity": recs(pd.read_csv(S / f"sensitivity_china_shift_{F}.csv")),
        "qc": recs(pd.read_csv(M / "qc_report.csv")),
        "test_year_last": T, "forward_year": F, "k": K,
    }
    for y in (T, F):
        cmp = pd.read_csv(R / f"shortlist_comparison_{y}.csv", dtype={"hs6": str})
        out[f"cmp_{y}"] = recs(cmp)
        out[f"top10_baseline_{y}"] = recs(pd.read_csv(R / f"top10_baseline_{y}.csv", dtype={"hs6": str}))
        out[f"top10_ml_{y}"] = recs(pd.read_csv(R / f"top10_ml_{y}.csv", dtype={"hs6": str}))
        out[f"overlap_{y}"] = int((cmp["in"] == "both").sum())
    # scenario top-10 changes (K=10) for the forward year
    ch = pd.read_csv(S / f"scenario_top10_changes_{F}.csv", dtype={"hs6": str})
    out["scenario_changes"] = recs(ch[ch.status.isin(["new", "removed"])])
    reg = pd.read_csv(M / "diversion_regressions.csv")
    share_specs = reg[~reg.spec.str.startswith("(4)")]
    sm_ = summ.set_index(["method", "k"])
    d_prec = sm_.loc[("ML ranking", K), "precision_at_k"] - sm_.loc[("ML without tariff features", K), "precision_at_k"]
    d_mean = sm_.loc[("ML ranking", K), "mean_d_share_pp_at_k"] - sm_.loc[("ML without tariff features", K), "mean_d_share_pp_at_k"]
    out["flags"] = {
        "diversion_significant": bool((share_specs.p_value < 0.05).any()),
        "diversion_sign_positive": bool((share_specs.coef > 0).all()),
        "growth_spec_p": float(reg[reg.spec.str.startswith("(4)") & (reg.variable == "tariff_adv")].p_value.iloc[0]),
        "tariff_ablation_d_prec": float(d_prec), "tariff_ablation_d_mean": float(d_mean),
        "tariffs_add_little": bool(abs(d_prec) <= 0.05 and abs(d_mean) <= 0.5),
        "tariff_effect": ("none_or_negative" if (d_prec <= 0.025 and d_mean <= 0.25)
                          else "positive" if (d_prec > 0.025 and d_mean > 0.25) else "mixed"),
        "ml_minus_random_prec": float(sm_.loc[("ML ranking", K), "precision_at_k"] - uni.set_index("k").loc[K, "universe_precision"]),
        "base_minus_random_prec": float(sm_.loc[("Historical momentum (baseline)", K), "precision_at_k"] - uni.set_index("k").loc[K, "universe_precision"]),
        "ml_wins_both": bool(sm_.loc[("ML ranking", K), "precision_at_k"] > sm_.loc[("Historical momentum (baseline)", K), "precision_at_k"]
                             and sm_.loc[("ML ranking", K), "mean_d_share_pp_at_k"] > sm_.loc[("Historical momentum (baseline)", K), "mean_d_share_pp_at_k"]),
    }
    sc = pd.read_parquet(R / "scored_candidates.parquet")
    from src.ranking import top_k
    prof = {}
    for y in (T, F):
        d = sc[sc.year == y]
        for meth, col in (("baseline", "score_baseline"), ("ml", "score_ml")):
            t = top_k(d, col, K)
            prof[f"{meth}_{y}"] = {"share_ind": float(t.share_ind.mean()), "g3_ind": float(t.g3_ind.mean()),
                                   "d3_share_chn": float(t.d3_share_chn.mean()), "imp_ind_m": float(t.imp_ind.median() / 1e6),
                                   "d3_share_ind": float(t.d3_share_ind.mean())}
        prof[f"universe_{y}"] = {"share_ind": float(d.share_ind.mean()), "g3_ind": float(d.g3_ind.mean()),
                                 "d3_share_chn": float(d.d3_share_chn.mean()), "imp_ind_m": float(d.imp_ind.median() / 1e6),
                                 "d3_share_ind": float(d.d3_share_ind.mean())}
    out["profiles"] = prof
    from PIL import Image
    out["fig_sizes"] = {fp.stem: list(Image.open(fp).size) for fp in (ROOT / "outputs/figures").glob("*.png")}
    def clean(o):  # NaN/inf -> null so the JSON is valid for JavaScript
        if isinstance(o, dict):
            return {k: clean(v) for k, v in o.items()}
        if isinstance(o, list):
            return [clean(v) for v in o]
        if isinstance(o, (float, np.floating)):
            return None if not np.isfinite(o) else float(o)
        if isinstance(o, np.integer):
            return int(o)
        return o
    (ROOT / "outputs" / "results_summary.json").write_text(json.dumps(clean(out), indent=1, default=float))
    print("wrote outputs/results_summary.json")


if __name__ == "__main__":
    main()
