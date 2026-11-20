"""All project figures (PNG, 200 dpi) built from the final dataset and results.

Colour roles (validated reference palette):
  India  = orange #eb6834      China = blue #2a78d6
  ML     = blue   #2a78d6      Baseline = neutral grey #8a8984
  Diverging tariff advantage: China-advantage blue <- grey -> India-advantage orange
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .utils import get_logger, load_config, p

log = get_logger("viz")

IND, CHN, ML, BASE, GREY = "#eb6834", "#2a78d6", "#2a78d6", "#8a8984", "#c3c2b7"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
SRC_TRADE = "Source: UN Comtrade (importer-reported imports, US$), project calculations."
SRC_TARIFF = "Source: WITS / UNCTAD TRAINS applied tariffs (simple avg. of ad valorem lines), project calculations."

plt.rcParams.update({
    "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb", "savefig.facecolor": "#fcfcfb",
    "font.size": 11, "axes.titlesize": 13, "axes.titleweight": "bold", "axes.labelcolor": INK2,
    "axes.edgecolor": GRID, "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
    "legend.frameon": False, "font.family": "DejaVu Sans", "axes.axisbelow": True,
})


def _save(fig, name, note):
    fig.text(0.01, 0.005, note, fontsize=8, color=INK2, ha="left", va="bottom")
    fig.tight_layout(rect=(0, 0.035, 1, 1))
    out = p("outputs", "figures", f"{name}.png")
    fig.savefig(out, dpi=200)
    plt.close(fig)
    return out


def _load():
    panel = pd.read_parquet(p("data", "processed", "full_panel.parquet"))
    ds = pd.read_parquet(p("data", "processed", "analytical_dataset.parquet"))
    return panel, ds


def fig_tariff_by_category(panel, year):
    d = panel[(panel.year == year) & panel.market_reported]
    g = d.groupby("category")[["tariff_ind", "tariff_chn"]].mean().sort_values("tariff_chn")
    fig, ax = plt.subplots(figsize=(10, 6))
    y = np.arange(len(g))
    ax.barh(y + 0.2, g.tariff_ind, 0.38, color=IND, label="Faced by Indian-origin goods")
    ax.barh(y - 0.2, g.tariff_chn, 0.38, color=CHN, label="Faced by Chinese-origin goods")
    ax.set_yticks(y, g.index)
    ax.set_xlabel("Average applied tariff across 10 markets (%, ad valorem)")
    ax.set_title(f"Tariffs faced by Indian vs Chinese goods by category ({year})")
    ax.legend(loc="lower right")
    return _save(fig, "01_tariff_india_vs_china_by_category", SRC_TARIFF + " Excludes US Section 301 & trade-remedy duties.")


def fig_tariff_adv_by_market(panel, year):
    d = panel[(panel.year == year)].dropna(subset=["tariff_adv"])
    g = d.groupby("market").agg(ind=("tariff_adv", lambda s: (s > 0.5).mean() * 100),
                                chn=("tariff_adv", lambda s: (s < -0.5).mean() * 100),
                                mean=("tariff_adv", "mean")).sort_values("mean")
    fig, ax = plt.subplots(figsize=(10, 6))
    y = np.arange(len(g))
    ax.barh(y, g.ind, color=IND, label="India faces lower tariff (> 0.5pp)")
    ax.barh(y, -g.chn, color=CHN, label="China faces lower tariff (> 0.5pp)")
    for i, (a, b, m) in enumerate(zip(g.ind, g.chn, g["mean"])):
        ax.text(max(a, 2) + 1, i, f"mean {m:+.2f}pp", va="center", fontsize=9, color=INK2)
    ax.axvline(0, color=INK2, lw=1)
    ax.set_yticks(y, g.index)
    ax.set_xlim(-105, 125)
    ax.set_xlabel("% of the 200 HS6 products  (left = China advantage, right = India advantage)")
    ax.set_title(f"Where does India have a tariff advantage over China? ({year})")
    ax.legend(loc="center right")
    return _save(fig, "02_tariff_advantage_by_market", SRC_TARIFF + " Advantage = tariff on China - tariff on India.")


def _trend(panel, col, color, title, name):
    d = panel[panel.market_reported].groupby(["year", "market"])[col].sum().unstack() / 1e9
    fig, ax = plt.subplots(figsize=(10, 6))
    tot = d.sum(axis=1)
    ax.plot(tot.index, tot.values, color=color, lw=2.5, marker="o", ms=5, label="All 10 markets")
    top = d.iloc[-2].sort_values(ascending=False).index[:4]
    for i, m in enumerate(top):
        ax.plot(d.index, d[m], color=color, lw=1.2, alpha=0.35 + 0.15 * (3 - i), ls="--")
        ax.text(d.index[-1] + 0.15, d[m].iloc[-1], m, fontsize=9, color=INK2, va="center")
    ax.text(tot.index[-1] + 0.15, tot.iloc[-1], "All 10 markets", fontsize=9, color=INK, va="center", weight="bold")
    ax.set_xlim(d.index.min() - 0.3, d.index.max() + 2.2)
    ax.set_ylabel("Imports of the 200 study products (US$ billion)")
    ax.set_title(title)
    return _save(fig, name, SRC_TRADE + " Dashed = four largest markets.")


def fig_market_share(panel, year):
    d = panel[(panel.year == year) & panel.market_reported]
    g = d.groupby("market")[["imp_ind", "imp_chn", "imp_wld"]].sum()
    g["India"] = g.imp_ind / g.imp_wld * 100
    g["China"] = g.imp_chn / g.imp_wld * 100
    g = g.sort_values("China")
    fig, ax = plt.subplots(figsize=(10, 6))
    y = np.arange(len(g))
    ax.hlines(y, g.India, g.China, color=GREY, lw=2)
    ax.scatter(g.India, y, color=IND, s=70, zorder=3, label="India share", edgecolor="white", linewidth=2)
    ax.scatter(g.China, y, color=CHN, s=70, zorder=3, label="China share", edgecolor="white", linewidth=2)
    for i, (a, b) in enumerate(zip(g.India, g.China)):
        ax.text(a - 1, i, f"{a:.1f}%", ha="right", va="center", fontsize=9, color=INK2)
        ax.text(b + 1, i, f"{b:.1f}%", ha="left", va="center", fontsize=9, color=INK2)
    ax.set_yticks(y, g.index)
    ax.set_xlim(-4, g.China.max() + 6)
    ax.set_xlabel("Share of market's imports of the 200 study products (%)")
    ax.set_title(f"India vs China share of destination imports ({year})")
    ax.legend(loc="lower right")
    return _save(fig, "05_market_share_india_vs_china", SRC_TRADE)


def fig_import_growth_by_category(panel, y0, y1):
    d = panel[panel.market_reported & panel.year.isin([y0, y1])]
    g = d.groupby(["category", "year"]).imp_wld.sum().unstack()
    g["cagr"] = ((g[y1] / g[y0]) ** (1 / (y1 - y0)) - 1) * 100
    g = g.sort_values("cagr")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(g.index, g.cagr, color=BASE)
    for i, v in enumerate(g.cagr):
        ax.text(v + (0.1 if v >= 0 else -0.1), i, f"{v:+.1f}%", va="center",
                ha="left" if v >= 0 else "right", fontsize=9, color=INK2)
    ax.axvline(0, color=INK2, lw=1)
    ax.set_xlim(min(g.cagr.min() - 1.2, -0.5), g.cagr.max() + 1)
    ax.set_xlabel(f"Compound annual growth of total imports, {y0}-{y1} (%)")
    ax.set_title(f"Import-market growth by product category ({y0}-{y1}, 10 markets)")
    return _save(fig, "06_import_growth_by_category", SRC_TRADE)


def fig_adv_distribution(ds):
    d = ds.dropna(subset=["tariff_adv"])
    fig, ax = plt.subplots(figsize=(10, 6))
    nz = d.tariff_adv[d.tariff_adv.abs() > 0.05]
    bins = np.arange(-15, 15.5, 0.5)
    vals = nz.clip(-15, 15)
    ax.hist(vals[vals < 0], bins=bins, color=CHN, label="China advantage")
    ax.hist(vals[vals > 0], bins=bins, color=IND, label="India advantage")
    zero = (d.tariff_adv.abs() <= 0.05).mean() * 100
    ax.set_xlabel("Tariff advantage = tariff on China - tariff on India (pp; clipped at ±15)")
    ax.set_ylabel("Candidate opportunities (market x product x year)")
    ax.set_title("Distribution of India's tariff advantage over China (non-zero cases)")
    ax.text(0.98, 0.78, f"{zero:.0f}% of the {len(d):,} candidate rows have\nno difference (|adv| ≤ 0.05pp) and are not shown",
            transform=ax.transAxes, va="top", ha="right", fontsize=10, color=INK2)
    ax.legend(loc="upper right")
    return _save(fig, "07_tariff_advantage_distribution", SRC_TARIFF + " Candidate universe, decision years 2015-2025.")


NICE = {
    "tariff_ind": "Tariff on India", "tariff_chn": "Tariff on China", "tariff_adv": "Tariff advantage (China-India)",
    "mfn": "MFN tariff", "d1_tariff_adv": "1y change in tariff advantage", "d3_tariff_adv": "3y change in tariff advantage",
    "has_pref_ind": "India has preference", "has_pref_chn": "China has preference", "share_ind": "India market share",
    "share_chn": "China market share", "d1_share_ind": "1y change India share", "d3_share_ind": "3y change India share",
    "d1_share_chn": "1y change China share", "d3_share_chn": "3y change China share", "log_imp_ind": "log imports from India",
    "log_imp_chn": "log imports from China", "log_imp_wld": "log market size", "g1_ind": "India export growth 1y",
    "g3_ind": "India export growth 3y", "g1_chn": "China export growth 1y", "g3_chn": "China export growth 3y",
    "g1_wld": "Market import growth 1y", "g3_wld": "Market import growth 3y", "rca_ind_mkt": "India RCA (market)",
    "rca_chn_mkt": "China RCA (market)", "rca_ind_basket": "India RCA (10-market basket)", "ind_vol_3y": "India growth volatility",
    "log_gdp": "log GDP", "gdp_growth_pct": "GDP growth", "inflation_pct": "Inflation", "fx_change_pct": "FX change",
    "market_code": "Market (categorical)", "section_code": "HS section (categorical)",
}


def fig_feature_importance():
    imp = pd.read_csv(p("outputs", "metrics", "feature_importance_permutation.csv")).head(15)[::-1]
    tariff = imp.feature.str.contains("tariff|pref|mfn")
    fig, ax = plt.subplots(figsize=(10, 6.5))
    ax.barh(imp.feature.map(NICE), imp.importance_mean, xerr=imp.importance_std,
            color=np.where(tariff, IND, ML), error_kw=dict(ecolor=INK2, lw=1))
    ax.set_xlabel("Drop in Spearman rank correlation when feature is shuffled")
    yr = int(imp.heldout_year.iloc[0])
    ax.set_title(f"Permutation importance of the ML ranking (held-out {yr})")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=IND, label="Tariff feature"), Patch(color=ML, label="Trade / macro feature")], loc="lower right")
    return _save(fig, "08_feature_importance", "Predictive importance, not causal effect. Model trained on decision years before the held-out year.")


def fig_actual_vs_pred(cfg):
    sc = pd.read_parquet(p("outputs", "rankings", "scored_candidates.parquet"))
    d = sc[sc.year.isin(cfg["years"]["test_years"]) & sc.has_outcome].copy()
    d["bin"] = d.groupby("year").score_ml.transform(lambda s: pd.qcut(s.rank(method="first"), 10, labels=False)) + 1
    g = d.groupby("bin").agg(pred=("score_ml", "mean"), act=("y_d_share_pp", "mean"),
                             se=("y_d_share_pp", lambda s: s.std() / np.sqrt(len(s))))
    gb = d.copy()
    gb["bin_b"] = gb.groupby("year").score_baseline.transform(lambda s: pd.qcut(s.rank(method="first"), 10, labels=False)) + 1
    gbb = gb.groupby("bin_b").y_d_share_pp.mean()
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(g.index, g.act, color=ML, lw=2, marker="o", ms=8, label="ML: realised change (mean ± 1 s.e.)")
    ax.fill_between(g.index, g.act - g.se, g.act + g.se, color=ML, alpha=0.12, lw=0)
    ax.plot(g.index, g.pred, color=ML, lw=1.5, ls="--", label="ML: predicted change")
    ax.plot(gbb.index, gbb.values, color=BASE, lw=2, marker="s", ms=7, label="Baseline momentum: realised change")
    ax.axhline(0, color=INK2, lw=1)
    ax.set_xticks(range(1, 11))
    ax.set_xlabel("Decile of score within decision year (10 = highest-ranked)")
    ax.set_ylabel("Next-year change in India's market share (pp)")
    ax.set_title("Actual vs predicted: realised share change by score decile (test years)")
    ax.legend(loc="upper left")
    ty = cfg["years"]["test_years"]
    return _save(fig, "09_actual_vs_predicted", f"Held-out decision years {ty[0]}-{ty[-1]} (outcomes {ty[0]+1}-{ty[-1]+1}). " + SRC_TRADE)


def fig_topk_comparison(cfg, year):
    cmp = pd.read_csv(p("outputs", "rankings", f"shortlist_comparison_{year}.csv"), dtype={"hs6": str})
    cmp["label"] = cmp.market.str.replace("United States", "USA").str.replace("European Union", "EU").str.replace("United Kingdom", "UK") + \
        " · " + cmp.hs6 + " " + cmp.short_desc.str.slice(0, 32)
    fig, axes = plt.subplots(1, 2, figsize=(13, 6.5), sharex=True)
    for ax, col, title, color in [(axes[0], "rank_baseline", "Historical momentum (baseline)", BASE),
                                  (axes[1], "rank_ml", "ML ranking", ML)]:
        t = cmp[cmp[col].notna()].sort_values(col, ascending=False)
        has = t.y_d_share_pp.notna().any()
        vals = t.y_d_share_pp if has else t.score_ml
        cols = [IND if s == "both" else color for s in t["in"]]
        ax.barh(range(len(t)), vals, color=cols)
        ax.set_yticks(range(len(t)), [f"{int(r)}. {l}" for r, l in zip(t[col], t.label)], fontsize=8.5)
        ax.axvline(0, color=INK2, lw=1)
        ax.set_title(title, fontsize=12)
        ax.set_xlabel(f"Realised change in India share {year+1} (pp)" if has else "ML-predicted change (pp)")
    from matplotlib.patches import Patch
    fig.legend(handles=[Patch(color=IND, label="Selected by both"), Patch(color=BASE, label="Baseline only"),
                        Patch(color=ML, label="ML only")], loc="upper right", ncol=3, fontsize=9)
    fig.suptitle(f"Top-10 shortlists for decision year {year}", fontweight="bold", x=0.02, ha="left")
    return _save(fig, f"10_topk_comparison_{year}", SRC_TRADE)


def fig_performance(cfg):
    s = pd.read_csv(p("outputs", "metrics", "backtest_metrics_summary.csv"))
    uni = pd.read_csv(p("outputs", "metrics", "universe_reference.csv")).set_index("k")
    meths = ["Historical momentum (baseline)", "ML ranking"]
    fig, axes = plt.subplots(1, 3, figsize=(14, 5.5))
    for ax, met, lab, ref in [(axes[0], "precision_at_k", "Precision@K (share of picks gaining share)", "universe_precision"),
                              (axes[1], "mean_d_share_pp_at_k", "Mean realised share change of picks (pp)", "universe_mean_d_share_pp"),
                              (axes[2], "ndcg_at_k", "NDCG@K", None)]:
        for m, c, mk in zip(meths, [BASE, ML], ["s", "o"]):
            d = s[s.method == m].sort_values("k")
            ax.plot(d.k.astype(str), d[met], color=c, marker=mk, ms=8, lw=2, label=m)
        if ref:
            ax.plot(uni.index.astype(str), uni[ref], color=INK2, ls=":", lw=1.5, label="Random pick (universe mean)")
        ax.set_xlabel("K (shortlist size)")
        ax.set_title(lab, fontsize=11)
    axes[0].legend(loc="best", fontsize=9)
    ty = cfg["years"]["test_years"]
    fig.suptitle(f"Backtest performance, averaged over decision years {ty[0]}-{ty[-1]}", fontweight="bold", x=0.02, ha="left")
    return _save(fig, "11_performance_comparison", "Rolling-origin backtest; each fold trains only on earlier decision years. " + SRC_TRADE)


def fig_backtest_by_year(cfg):
    m = pd.read_csv(p("outputs", "metrics", "backtest_metrics_by_year.csv"))
    m = m[(m.k == cfg["evaluation"]["k_main"]) & m.method.isin(["Historical momentum (baseline)", "ML ranking"])]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    for ax, met, lab in [(axes[0], "precision_at_k", "Precision@10"), (axes[1], "mean_d_share_pp_at_k", "Mean share change of top-10 (pp)")]:
        piv = m.pivot(index="year", columns="method", values=met)
        x = np.arange(len(piv))
        ax.bar(x - 0.2, piv["Historical momentum (baseline)"], 0.38, color=BASE, label="Baseline")
        ax.bar(x + 0.2, piv["ML ranking"], 0.38, color=ML, label="ML")
        ax.set_xticks(x, [f"{y}→{y+1}" for y in piv.index])
        ax.axhline(0, color=INK2, lw=1)
        ax.set_title(lab, fontsize=11)
        ax.set_xlabel("Decision year → outcome year")
    axes[0].legend()
    fig.suptitle("Backtest results by fold (K = 10)", fontweight="bold", x=0.02, ha="left")
    return _save(fig, "11b_backtest_by_year", SRC_TRADE)


def fig_precision_by_fold(cfg):
    m = pd.read_csv(p("outputs", "metrics", "backtest_metrics_by_year.csv"))
    m = m[(m.k == cfg["evaluation"]["k_main"]) & m.method.isin(["Historical momentum (baseline)", "ML ranking"])]
    piv = m.pivot(index="year", columns="method", values="precision_at_k") * 100
    uni = m.groupby("year").universe_precision.first() * 100
    fig, ax = plt.subplots(figsize=(6.2, 5.6))
    x = np.arange(len(piv))
    b1 = ax.bar(x - 0.2, piv["Historical momentum (baseline)"], 0.38, color=BASE, label="Baseline")
    b2 = ax.bar(x + 0.2, piv["ML ranking"], 0.38, color=ML, label="ML")
    ax.bar_label(b1, fmt="%.0f%%", fontsize=9, color=INK2, padding=2)
    ax.bar_label(b2, fmt="%.0f%%", fontsize=9, color=INK2, padding=2)
    ax.plot(x, uni.values, color=INK2, ls=":", marker="_", ms=20, lw=1.2, label="Random pick")
    ax.set_xticks(x, [f"{y}→{y+1}" for y in piv.index])
    ax.set_ylim(0, 105)
    ax.set_ylabel("Precision@10 (% of picks gaining share)")
    ax.set_xlabel("Decision year → outcome year")
    ax.set_title("Precision@10 by test fold")
    ax.legend(loc="upper left", fontsize=9, ncol=3)
    return _save(fig, "11c_precision_by_fold", "Held-out folds; same candidates and K.")


def fig_simulation(cfg):
    y = cfg["years"]["forward_decision_year"]
    s = pd.read_csv(p("outputs", "simulation_results", f"scenario_summary_{y}.csv"))
    s = s[s.k == 10]
    s = s[s.scenario != "Status quo"].sort_values("n_new")
    cur = pd.read_csv(p("outputs", "simulation_results", f"sensitivity_china_shift_{y}.csv"))
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.8), gridspec_kw={"width_ratios": [1.3, 1]})
    ax = axes[0]
    ax.barh(s.scenario, s.n_new, color=ML)
    for i, (n, dm) in enumerate(zip(s.n_new, s.mean_pred_change_all)):
        ax.text(n + 0.1, i, f"{n} new  |  mean Δpred {dm:+.3f}pp", va="center", fontsize=9, color=INK2)
    ax.set_xlim(0, 10.5)
    ax.set_xlabel("Opportunities entering the ML top-10 (out of 10)")
    ax.set_title("How much does each what-if change the ML shortlist?", fontsize=11)
    ax = axes[1]
    ax.plot(cur.china_shift_pp, cur.mean_pred_all, color=ML, marker="o", lw=2)
    ax.axvline(0, color=INK2, lw=1, ls=":")
    ax.set_xlabel("Uniform change in tariff faced by China (pp)")
    ax.set_ylabel("Mean predicted share change, all candidates (pp)")
    ax.set_title("Model sensitivity to China's tariff", fontsize=11)
    fig.suptitle(f"Model-based what-if analysis on {y} candidates (illustrative, NOT causal)", fontweight="bold", x=0.02, ha="left")
    return _save(fig, "12_simulation_scenarios", "Scenarios perturb model inputs; outputs show model sensitivity, not predicted policy effects.")


def fig_diversion():
    d = pd.read_csv(p("outputs", "metrics", "diversion_by_advantage_change.csv"))
    b = pd.read_csv(p("outputs", "metrics", "diversion_by_advantage_bin.csv"))
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.2))
    for ax, t, col, title in [(axes[0], b, "adv_bin", "By level of tariff advantage at t"),
                              (axes[1], d, "adv_change", "By 1-year change in tariff advantage")]:
        colors = [CHN, GREY, IND]
        ax.bar(range(len(t)), t.mean_d_share_pp, color=colors[:len(t)])
        ax.set_xticks(range(len(t)), [f"{c}\n(n={n:,})" for c, n in zip(t[col], t.n)], fontsize=9)
        ax.axhline(0, color=INK2, lw=1)
        ax.set_ylabel("Mean change in India share, t→t+1 (pp)")
        ax.set_title(title, fontsize=11)
    fig.suptitle("Trade diversion check: tariff advantage vs subsequent India share change (association only)",
                 fontweight="bold", x=0.02, ha="left")
    return _save(fig, "13_trade_diversion", SRC_TARIFF)


def fig_tariff_adv_time(panel):
    d = panel.dropna(subset=["tariff_adv"])
    d = d[~d.pref_unknown_pre.fillna(False).astype(bool)]  # preference status unknown -> not plotted
    g = d.groupby(["year", "market"]).tariff_adv.mean().unstack()
    fig, ax = plt.subplots(figsize=(10, 6))
    show = g.columns[(g.abs() > 0.3).any()]
    for m in g.columns:
        lw, a = (2, 1) if m in show else (1, 0.35)
        ax.plot(g.index, g[m], color=IND if g[m].mean() > 0 else (CHN if m in show else GREY), lw=lw, alpha=a)
        if m in show:
            ax.text(g.index[-1] + 0.15, g[m].iloc[-1], m, fontsize=9, color=INK2, va="center")
    ax.axhline(0, color=INK2, lw=1)
    ax.set_xlim(g.index.min() - 0.3, g.index.max() + 2)
    ax.set_ylabel("Mean tariff advantage across 200 products (pp)")
    ax.set_title("India's tariff advantage over China over time, by market")
    return _save(fig, "14_tariff_advantage_over_time", "Source: WITS/UNCTAD TRAINS, project calculations. 2022-25 carried forward; years before a market's first reported preference omitted.")


def make_all(cfg: dict | None = None) -> list:
    cfg = cfg or load_config()
    panel, ds = _load()
    yrs = cfg["years"]
    outs = [
        fig_tariff_by_category(panel, 2021),
        fig_tariff_adv_by_market(panel, 2021),
        _trend(panel, "imp_ind", IND, "Imports from India of the 200 study products, 10 markets", "03_india_export_trend"),
        _trend(panel, "imp_chn", CHN, "Imports from China of the 200 study products, 10 markets", "04_china_export_trend"),
        fig_market_share(panel, 2024),
        fig_import_growth_by_category(panel, 2015, 2024),
        fig_adv_distribution(ds),
        fig_feature_importance(),
        fig_actual_vs_pred(cfg),
        fig_topk_comparison(cfg, yrs["test_years"][-1]),
        fig_topk_comparison(cfg, yrs["forward_decision_year"]),
        fig_performance(cfg),
        fig_backtest_by_year(cfg),
        fig_precision_by_fold(cfg),
        fig_simulation(cfg),
        fig_diversion(),
        fig_tariff_adv_time(panel),
    ]
    log.info("Wrote %d figures", len(outs))
    return outs


if __name__ == "__main__":
    make_all()
