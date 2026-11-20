"""Model-based what-if (sensitivity) analysis.

IMPORTANT: these scenarios perturb the INPUTS of a predictive model and show how
the model's ranking reacts. They are NOT causal forecasts of what would happen
to trade if a tariff changed: the model learned correlations from historical
data in which tariff changes were rare and not randomly assigned.
"""
from __future__ import annotations

import joblib
import numpy as np
import pandas as pd

from .ranking import rank_within_year
from .utils import get_logger, load_config, p

log = get_logger("simulation")

SCENARIOS = {
    "Status quo": dict(),
    "China faces +5pp tariff": dict(china_shift=5.0),
    "India receives -5pp tariff cut": dict(india_shift=-5.0),
    "Both face +5pp tariff": dict(india_shift=5.0, china_shift=5.0),
    "India loses its tariff advantage": dict(remove_india_advantage=True),
    "China's tariff advantage increases (China -5pp)": dict(china_shift=-5.0),
    "Import demand +5pp growth": dict(demand_shift_pp=5.0),
    "Import demand -5pp growth": dict(demand_shift_pp=-5.0),
}


def load_bundle():
    return joblib.load(p("outputs", "metrics", "final_model.joblib"))


def apply_scenario(df: pd.DataFrame, india_shift: float = 0.0, china_shift: float = 0.0,
                   remove_india_advantage: bool = False, demand_shift_pp: float = 0.0,
                   markets: list[str] | None = None, categories: list[str] | None = None) -> pd.DataFrame:
    """Return a copy of the candidate frame with perturbed decision-time features.
    Tariff shifts are in percentage points and are treated as a change that
    happened in the decision year (so 1- and 3-year tariff changes move too).
    Tariffs are floored at zero. Optionally restrict the shock to some markets or
    product categories."""
    s = df.copy()
    mask = pd.Series(True, index=s.index)
    if markets:
        mask &= s.market.isin(markets)
    if categories:
        mask &= s.category.isin(categories)
    old_adv = s.tariff_adv.copy()
    new_ind = s.tariff_ind.where(~mask, (s.tariff_ind + india_shift).clip(lower=0))
    new_chn = s.tariff_chn.where(~mask, (s.tariff_chn + china_shift).clip(lower=0))
    if remove_india_advantage:
        lose = mask & (s.tariff_chn - new_ind > 0)
        new_ind = new_ind.where(~lose, new_chn)
    common = min(india_shift, china_shift) if (india_shift > 0 and china_shift > 0) else 0.0
    s["mfn"] = s.mfn.where(~mask, s.mfn + common)
    s["tariff_ind"], s["tariff_chn"] = new_ind, new_chn
    s["tariff_adv"] = s.tariff_chn - s.tariff_ind
    delta = s.tariff_adv - old_adv
    s["d1_tariff_adv"] = s.d1_tariff_adv + delta
    s["d3_tariff_adv"] = s.d3_tariff_adv + delta
    s["has_pref_ind"] = (s.tariff_ind < s.mfn - 1e-9).astype(float)
    s["has_pref_chn"] = (s.tariff_chn < s.mfn - 1e-9).astype(float)
    if demand_shift_pp:
        g = np.log1p(demand_shift_pp / 100.0)
        s.loc[mask, "g1_wld"] = s.loc[mask, "g1_wld"] + g
        s.loc[mask, "g3_wld"] = s.loc[mask, "g3_wld"] + g
    return s


def score(df: pd.DataFrame, bundle: dict) -> np.ndarray:
    X = df[bundle["features"]]
    X = X if bundle["name"] == "rf" else X.to_numpy(dtype=float)
    return bundle["model"].predict(X)


def compare(base: pd.DataFrame, scen: pd.DataFrame, k: int) -> pd.DataFrame:
    """Rank movements between status-quo and scenario predictions."""
    b = rank_within_year(base.assign(score=base.pred), "score")[["iso3", "hs6", "rank", "pred"]]
    s = rank_within_year(scen.assign(score=scen.pred), "score")[["iso3", "hs6", "rank", "pred", "tariff_adv"]]
    m = b.merge(s, on=["iso3", "hs6"], suffixes=("_base", "_scen"))
    m["rank_change"] = m.rank_base - m.rank_scen  # +ve = moved up
    m["status"] = np.select([(m.rank_base <= k) & (m.rank_scen <= k), (m.rank_base > k) & (m.rank_scen <= k),
                             (m.rank_base <= k) & (m.rank_scen > k)], ["kept", "new", "removed"], "outside")
    meta = base[["iso3", "hs6", "market", "short_desc", "category", "tariff_ind", "tariff_chn", "g3_ind"]]
    return m.merge(meta, on=["iso3", "hs6"]).rename(columns={"tariff_adv": "tariff_adv_scen"})


def run_scenarios(cfg: dict | None = None, year: int | None = None) -> pd.DataFrame:
    cfg = cfg or load_config()
    year = year or cfg["years"]["forward_decision_year"]
    bundle = load_bundle()
    cand = pd.read_parquet(p("outputs", "rankings", "scored_candidates.parquet"))
    cand = cand[cand.year == year].reset_index(drop=True)
    base = cand.copy()
    base["pred"] = score(base, bundle)
    rows, details = [], []
    for name, kw in SCENARIOS.items():
        sc = apply_scenario(cand, **kw)
        sc["pred"] = score(sc, bundle)
        for k in (5, 10, 20):
            c = compare(base, sc, k)
            rows.append({"scenario": name, "k": k, "n_new": int((c.status == "new").sum()),
                         "n_removed": int((c.status == "removed").sum()),
                         "mean_pred_topk_base": base.nlargest(k, "pred").pred.mean(),
                         "mean_pred_topk_scen": sc.nlargest(k, "pred").pred.mean(),
                         "mean_pred_change_all": (sc.pred - base.pred).mean(),
                         "mean_abs_rank_change_all": c.rank_change.abs().mean()})
            if k == 10:
                details.append(c[c.status.isin(["kept", "new", "removed"])].assign(scenario=name))
    out = pd.DataFrame(rows)
    out.to_csv(p("outputs", "simulation_results", f"scenario_summary_{year}.csv"), index=False)
    pd.concat(details).to_csv(p("outputs", "simulation_results", f"scenario_top10_changes_{year}.csv"), index=False)

    # sensitivity curve: uniform China tariff shift from -10 to +20 pp
    curve = []
    for shift in [-10, -5, -2.5, 0, 2.5, 5, 10, 15, 20]:
        sc = apply_scenario(cand, china_shift=float(shift))
        sc["pred"] = score(sc, bundle)
        c = compare(base, sc, 10)
        curve.append({"china_shift_pp": shift, "mean_pred_all": sc.pred.mean(),
                      "mean_pred_top10": sc.nlargest(10, "pred").pred.mean(),
                      "top10_changed": int((c.status == "new").sum())})
    pd.DataFrame(curve).to_csv(p("outputs", "simulation_results", f"sensitivity_china_shift_{year}.csv"), index=False)
    log.info("Scenario summary (K=10):\n%s", out[out.k == 10].to_string(index=False))
    return out


if __name__ == "__main__":
    run_scenarios()
