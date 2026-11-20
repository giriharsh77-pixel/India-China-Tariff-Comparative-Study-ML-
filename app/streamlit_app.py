"""Interactive prospect-selection simulator.

Run:  streamlit run app/streamlit_app.py

Shows (1) the historical backtest evidence, (2) the baseline vs ML shortlists
for any decision year, and (3) model-based what-if scenarios on tariffs and
import demand. Scenarios are SENSITIVITY ANALYSIS of a predictive model, not
causal forecasts.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.ranking import rank_within_year  # noqa: E402
from src.simulation import SCENARIOS, apply_scenario, compare, load_bundle, score  # noqa: E402

IND, CHN, ML, BASE = "#eb6834", "#2a78d6", "#2a78d6", "#8a8984"
st.set_page_config(page_title="India–China Tariff Prospect Selection", layout="wide")


@st.cache_data
def load():
    sc = pd.read_parquet(ROOT / "outputs/rankings/scored_candidates.parquet")
    summ = pd.read_csv(ROOT / "outputs/metrics/backtest_metrics_summary.csv")
    by_year = pd.read_csv(ROOT / "outputs/metrics/backtest_metrics_by_year.csv")
    return sc, summ, by_year


@st.cache_resource
def bundle():
    return load_bundle()


sc, summ, by_year = load()
b = bundle()
years = sorted(sc.year.unique())

st.title("Tariff Advantage & Export Market Selection — India vs China")
st.caption("Opportunity = destination market × HS6 product. Objective: next-year gain in India's share of the "
           "market's imports. Data: UN Comtrade, WITS/TRAINS, World Bank WDI.")

with st.sidebar:
    st.header("Decision settings")
    year = st.selectbox("Decision year", years, index=len(years) - 1,
                        help="Years up to the last test year have realised outcomes; the final year is the live shortlist.")
    K = st.radio("Resource constraint K", [5, 10, 20], index=1, horizontal=True)
    st.header("What-if scenario")
    preset = st.selectbox("Preset", list(SCENARIOS))
    kw = dict(SCENARIOS[preset])
    st.caption("Fine-tune (overrides preset values):")
    china_shift = st.slider("Change in tariff faced by China (pp)", -10.0, 25.0, float(kw.get("china_shift", 0.0)), 0.5)
    india_shift = st.slider("Change in tariff faced by India (pp)", -10.0, 25.0, float(kw.get("india_shift", 0.0)), 0.5)
    demand = st.slider("Change in import-demand growth (pp per year)", -10.0, 10.0, float(kw.get("demand_shift_pp", 0.0)), 0.5)
    remove_adv = st.checkbox("India loses its tariff advantage", value=kw.get("remove_india_advantage", False))
    mk = st.multiselect("Apply shock only to markets", sorted(sc.market.unique()))
    cats = st.multiselect("Apply shock only to categories", sorted(sc.category.unique()))

st.warning("Scenario results show how the **trained model's ranking responds to changed inputs**. They are illustrative "
           "sensitivity analysis — not causal forecasts of trade outcomes or policy effects.", icon="⚠️")

# Shortlists for any year use the OUT-OF-SAMPLE backtest score of that year's fold
# (the model trained only on earlier decision years).
cand = sc[sc.year == year].reset_index(drop=True)
# Scenarios use the final model on the live decision year only (its training data
# include all earlier years, so re-scoring past years would be in-sample).
live_year = int(max(years))
live = sc[sc.year == live_year].reset_index(drop=True)
base = live.copy()
base["pred"] = score(base, b)
scen = apply_scenario(live, india_shift=india_shift, china_shift=china_shift, remove_india_advantage=remove_adv,
                      demand_shift_pp=demand, markets=mk or None, categories=cats or None)
scen["pred"] = score(scen, b)
cmp = compare(base, scen, K)

tab1, tab2, tab3, tab4 = st.tabs(["Shortlists", "Scenario impact", "Backtest evidence", "Tariff landscape"])

with tab1:
    c1, c2 = st.columns(2)
    cols = ["rank", "market", "hs6", "short_desc", "imp_ind", "share_ind", "tariff_ind", "tariff_chn", "tariff_adv", "g3_ind"]
    has_out = cand.has_outcome.any()
    if has_out:
        cols += ["y_d_share_pp"]
    bl = rank_within_year(cand, "score_baseline").query("rank <= @K")
    ml = rank_within_year(cand, "score_ml").query("rank <= @K").assign(pred=lambda d: d.score_ml)
    fmt = {"imp_ind": lambda v: f"${v/1e6:,.1f}m", "share_ind": "{:.1f}%", "tariff_ind": "{:.1f}", "tariff_chn": "{:.1f}",
           "tariff_adv": "{:+.1f}", "g3_ind": "{:+.2f}", "y_d_share_pp": "{:+.2f}"}
    with c1:
        st.subheader("Historical momentum (baseline)")
        st.dataframe(bl[cols].style.format(fmt), hide_index=True, width="stretch")
        if has_out:
            st.metric("Precision@K (realised)", f"{bl.y_success.mean():.0%}", f"mean Δshare {bl.y_d_share_pp.mean():+.2f}pp")
    with c2:
        st.subheader("ML ranking (out-of-sample score)")
        st.dataframe(ml[cols + ["pred"]].style.format({**fmt, "pred": "{:+.2f}"}), hide_index=True, width="stretch")
        if has_out:
            st.metric("Precision@K (realised)", f"{ml.y_success.mean():.0%}", f"mean Δshare {ml.y_d_share_pp.mean():+.2f}pp")
    both = set(zip(bl.iso3, bl.hs6)) & set(zip(ml.iso3, ml.hs6))
    st.info(f"{len(both)} of {K} opportunities are selected by both approaches. "
            "The baseline ignores tariffs entirely, so its list never changes under tariff scenarios.")

with tab2:
    st.caption(f"Scenarios are applied to the live {live_year} candidates using the final model (trained on all earlier decision years).")
    new, rem = cmp[cmp.status == "new"], cmp[cmp.status == "removed"]
    a, bb, c = st.columns(3)
    a.metric("New entries in ML top-K", len(new))
    bb.metric("Removed from ML top-K", len(rem))
    c.metric("Mean change in predicted Δshare (all candidates)", f"{(scen.pred - base.pred).mean():+.3f}pp")
    st.subheader("Scenario ML shortlist")
    show = cmp[cmp.rank_scen <= K].sort_values("rank_scen")
    st.dataframe(show[["rank_scen", "rank_base", "rank_change", "status", "market", "hs6", "short_desc", "tariff_ind",
                       "tariff_chn", "tariff_adv_scen", "pred_base", "pred_scen"]]
                 .style.format({"pred_base": "{:+.2f}", "pred_scen": "{:+.2f}", "tariff_adv_scen": "{:+.1f}"}),
                 hide_index=True, width="stretch")
    if len(rem):
        st.subheader("Dropped from the shortlist")
        st.dataframe(rem[["rank_base", "rank_scen", "market", "hs6", "short_desc", "pred_base", "pred_scen"]],
                     hide_index=True, width="stretch")
    fig, ax = plt.subplots(figsize=(9, 4))
    movers = cmp.reindex(cmp.rank_change.abs().sort_values(ascending=False).index).head(15)
    ax.barh(movers.market.str.slice(0, 14) + " · " + movers.hs6, movers.rank_change,
            color=[IND if v > 0 else CHN for v in movers.rank_change])
    ax.axvline(0, color="#52514e", lw=1)
    ax.set_xlabel("Rank movement (positive = moved up)")
    ax.set_title("Largest rank movements under the scenario")
    st.pyplot(fig)

with tab3:
    st.subheader("Rolling-origin backtest (held-out decision years)")
    s = summ[summ.method.isin(["Historical momentum (baseline)", "ML ranking", "ML without tariff features"])]
    st.dataframe(s.pivot(index="k", columns="method", values="precision_at_k").style.format("{:.0%}"),
                 width="stretch")
    st.caption("Precision@K = share of shortlisted opportunities where India's import share rose the following year.")
    st.dataframe(s.pivot(index="k", columns="method", values="mean_d_share_pp_at_k").style.format("{:+.2f}"),
                 width="stretch")
    st.caption("Mean realised next-year change in India's share (pp) of the shortlisted opportunities.")
    st.dataframe(by_year[by_year.k == K].pivot(index="year", columns="method", values="precision_at_k").style.format("{:.0%}"),
                 width="stretch")

with tab4:
    d = cand.groupby("market")[["tariff_ind", "tariff_chn"]].mean().sort_values("tariff_chn")
    fig, ax = plt.subplots(figsize=(9, 4.5))
    y = range(len(d))
    ax.barh([i + 0.2 for i in y], d.tariff_ind, 0.38, color=IND, label="India")
    ax.barh([i - 0.2 for i in y], d.tariff_chn, 0.38, color=CHN, label="China")
    ax.set_yticks(list(y), d.index)
    ax.set_xlabel("Mean applied tariff on candidate products (%)")
    ax.legend()
    st.pyplot(fig)
    st.caption("Source: WITS/UNCTAD TRAINS. Excludes US Section 301 duties, trade remedies and unilateral GSP schemes.")
