"""Trade-diversion analysis: is a tariff advantage for India (China faces a
higher applied tariff) associated with subsequent gains in India's import share?

Everything here is ASSOCIATIONAL. The fixed-effects regressions absorb
market-year shocks and time-invariant product characteristics, but tariff
preferences are not randomly assigned (they are negotiated, often for products
where trade already grows), so no coefficient is interpreted causally.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from .utils import get_logger, p

log = get_logger("diversion")


def run_trade_diversion() -> dict:
    df = pd.read_parquet(p("data", "processed", "analytical_dataset.parquet"))
    d = df[df.has_outcome].copy()
    d["adv_bin"] = pd.cut(d.tariff_adv, [-np.inf, -0.5, 0.5, np.inf],
                          labels=["China advantage (< -0.5pp)", "No material difference", "India advantage (> +0.5pp)"])
    d["adv_change"] = pd.cut(d.d1_tariff_adv, [-np.inf, -0.5, 0.5, np.inf],
                             labels=["Advantage moved to China", "No change", "Advantage moved to India"])

    # 1) descriptive
    desc = d.groupby("adv_bin", observed=True).agg(
        n=("y_d_share_pp", "size"), mean_d_share_pp=("y_d_share_pp", "mean"),
        median_d_share_pp=("y_d_share_pp", "median"), share_gaining=("y_success", "mean"),
        mean_export_growth_log=("y_export_growth_log", "mean"), mean_tariff_adv=("tariff_adv", "mean")).reset_index()
    desc.to_csv(p("outputs", "metrics", "diversion_by_advantage_bin.csv"), index=False)
    chg = d.groupby("adv_change", observed=True).agg(
        n=("y_d_share_pp", "size"), mean_d_share_pp=("y_d_share_pp", "mean"),
        share_gaining=("y_success", "mean"), mean_export_growth_log=("y_export_growth_log", "mean")).reset_index()
    chg.to_csv(p("outputs", "metrics", "diversion_by_advantage_change.csv"), index=False)
    by_mkt = d.groupby("market").agg(mean_tariff_adv=("tariff_adv", "mean"),
                                     share_rows_india_adv=("tariff_adv", lambda s: (s > 0.5).mean()),
                                     share_rows_china_adv=("tariff_adv", lambda s: (s < -0.5).mean()),
                                     mean_d_share_pp=("y_d_share_pp", "mean")).reset_index()
    by_mkt.to_csv(p("outputs", "metrics", "diversion_by_market.csv"), index=False)

    # 2) fixed-effects regressions (clustered by market-product pair)
    d["pair"] = d.iso3 + "_" + d.hs6
    d["mkt_year"] = d.iso3 + "_" + d.year.astype(str)
    d = d.dropna(subset=["tariff_adv", "d1_tariff_adv", "share_ind", "g3_ind", "g3_wld", "y_d_share_pp"])
    specs = {
        "(1) level, market-year FE": "y_d_share_pp ~ tariff_adv + C(mkt_year)",
        "(2) + product FE + controls": "y_d_share_pp ~ tariff_adv + share_ind + g3_ind + g3_wld + C(mkt_year) + C(hs6)",
        "(3) change in advantage": "y_d_share_pp ~ d1_tariff_adv + tariff_adv + share_ind + g3_ind + g3_wld + C(mkt_year) + C(hs6)",
        "(4) export growth outcome": "y_export_growth_log ~ d1_tariff_adv + tariff_adv + share_ind + g3_ind + g3_wld + C(mkt_year) + C(hs6)",
    }
    rows = []
    for nm, f in specs.items():
        res = smf.ols(f, data=d).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.pair)[0]})
        for v in ["tariff_adv", "d1_tariff_adv"]:
            if v in res.params:
                rows.append({"spec": nm, "variable": v, "coef": res.params[v], "se": res.bse[v],
                             "p_value": res.pvalues[v], "n": int(res.nobs), "r2": res.rsquared})
    reg = pd.DataFrame(rows)
    reg.to_csv(p("outputs", "metrics", "diversion_regressions.csv"), index=False)
    log.info("Trade-diversion regressions:\n%s", reg.to_string(index=False))
    return {"desc": desc, "change": chg, "reg": reg, "by_market": by_mkt}


if __name__ == "__main__":
    run_trade_diversion()
