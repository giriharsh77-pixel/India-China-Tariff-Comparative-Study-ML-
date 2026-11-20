"""Build docs/report.docx (academic report). Every number comes from
outputs/results_summary.json, which the pipeline writes; figures from outputs/figures.

    python scripts/export_results.py && python scripts/build_report.py
"""
import json
import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT  # noqa: F401
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parents[1]
R = json.loads((ROOT / "outputs/results_summary.json").read_text())
FIG = ROOT / "outputs/figures"
NAVY = RGBColor(0x1B, 0x2A, 0x41)
MUTED = RGBColor(0x5B, 0x62, 0x70)

BL, ML, NT = "Historical momentum (baseline)", "ML ranking", "ML without tariff features"
K, T, F = R["k"], R["test_year_last"], R["forward_year"]
ds = R["dataset"]
S = {(r["method"], r["k"]): r for r in R["summary"]}
U = {r["k"]: r for r in R["universe"]}
bl, ml, nt = S[(BL, K)], S[(ML, K)], S[(NT, K)]
alt_name = [m for m, k in S if m.startswith("ML alternative")][0]
alt = S[(alt_name, K)]
test_years = [f["decision_year"] for f in R["folds"] if f["decision_year"] <= T]
boot = {b["method"]: b for b in R["bootstrap"]}
sm = R["selected_model"]
FL = R["flags"]
div_sentence = ("Fixed-effects regressions find a statistically significant association between India's tariff advantage and "
                "its subsequent share gains (Section 17); this is correlational evidence and cannot establish causality."
                if FL["diversion_significant"] else
                ("Fixed-effects regressions find " + ("positive but " if FL["diversion_sign_positive"] else "") +
                 "statistically insignificant associations (p > 0.05) between India's tariff advantage and its subsequent share "
                 "gains (Section 17); this is correlational evidence and cannot establish causality."))
tariff_sentence = ("add some predictive information, although trade structure and momentum dominate"
                   if FL["tariff_effect"] == "positive" else
                   "add no measurable predictive information (the model without them performs at least as well)")
EXR = {r["method"]: r for r in R["robust_ex2025"] if r["k"] == K}
fam = "HistGradientBoostingRegressor" if sm["model"] == "hgb" else "RandomForestRegressor"


def pct(x, d=0):
    """Percent with round-half-up (matches JavaScript toFixed used in the deck)."""
    if x is None:
        return "–"
    from decimal import ROUND_HALF_UP, Decimal
    q = Decimal(1).scaleb(-d)
    return f"{Decimal(str(round(100 * x, 9))).quantize(q, rounding=ROUND_HALF_UP)}%"


def sg(x, d=2):
    return "–" if x is None else f"{x:+.{d}f}"


def f(x, d=3):
    return "–" if x is None else f"{x:.{d}f}"


# ------------------------------------------------------------------ document
doc = Document()
st = doc.styles["Normal"]
st.font.name = "Calibri"
st.font.size = Pt(11)
st.paragraph_format.space_after = Pt(6)
st.paragraph_format.line_spacing = 1.15
for lvl, size in [(1, 16), (2, 13), (3, 11.5)]:
    h = doc.styles[f"Heading {lvl}"]
    h.font.name = "Cambria"
    h.font.size = Pt(size)
    h.font.color.rgb = NAVY
    h.font.bold = True
for sec in doc.sections:
    sec.left_margin = sec.right_margin = Cm(2.3)
    sec.top_margin = sec.bottom_margin = Cm(2.2)

# page numbers in footer
fp = doc.sections[0].footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
for t, txt in [("begin", None), (None, "PAGE"), ("end", None)]:
    r = fp.add_run()
    if t:
        el = OxmlElement("w:fldChar")
        el.set(qn("w:fldCharType"), t)
    else:
        el = OxmlElement("w:instrText")
        el.set(qn("xml:space"), "preserve")
        el.text = txt
    r._r.append(el)

fig_no = [0]
tab_no = [0]


def P(text="", bold=False, italic=False, size=None, color=None, align=None, after=None):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold, r.italic = bold, italic
    if size:
        r.font.size = Pt(size)
    if color:
        r.font.color.rgb = color
    if align is not None:
        p.alignment = align
    if after is not None:
        p.paragraph_format.space_after = Pt(after)
    return p


def B(items, style="List Bullet"):
    for it in items:
        p = doc.add_paragraph(style=style)
        if isinstance(it, tuple):
            p.add_run(it[0]).bold = True
            p.add_run(it[1])
        else:
            p.add_run(it)


def H(text, lvl=1):
    doc.add_heading(text, lvl)


def figure(name, caption, width=15.5):
    fig_no[0] += 1
    doc.add_picture(str(FIG / f"{name}.png"), width=Cm(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    P(f"Figure {fig_no[0]}. {caption}", italic=True, size=9.5, color=MUTED, align=WD_ALIGN_PARAGRAPH.CENTER)


def table(header, rows, caption, widths=None, size=9.5):
    tab_no[0] += 1
    P(f"Table {tab_no[0]}. {caption}", bold=True, size=10, after=2)
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Light Grid Accent 1"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        run = c.paragraphs[0].add_run(str(h))
        run.bold = True
        run.font.size = Pt(size)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            run = cells[i].paragraphs[0].add_run(str(v))
            run.font.size = Pt(size)
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    P("", after=2)
    return t


def page_break():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# ------------------------------------------------------------------ 1 cover
for _ in range(5):
    P("")
P("Tariff Advantage and Export Market Selection", bold=True, size=26, color=NAVY, align=WD_ALIGN_PARAGRAPH.CENTER)
P("A Comparative India–China Trade Analysis Using Machine Learning", size=16, color=NAVY, align=WD_ALIGN_PARAGRAPH.CENTER)
P("")
P("Prospect Selection Project", size=13, align=WD_ALIGN_PARAGRAPH.CENTER)
P("Machine Learning for Business Analytics", size=12, align=WD_ALIGN_PARAGRAPH.CENTER)
P("MS in Artificial Intelligence · Plaksha University · Monsoon 2026", size=12, align=WD_ALIGN_PARAGRAPH.CENTER)
P("")
P("Data retrieved 20 November 2026 from UN Comtrade, WITS/UNCTAD TRAINS, World Bank WDI and UNSD.",
  italic=True, size=10, color=MUTED, align=WD_ALIGN_PARAGRAPH.CENTER)
page_break()

# ------------------------------------------------------------------ 2 executive summary
H("Executive summary")
verdict = ("outperformed" if ml["precision_at_k"] > bl["precision_at_k"] and ml["mean_d_share_pp_at_k"] > bl["mean_d_share_pp_at_k"]
           else "did not consistently outperform")
P(f"An Indian export-promotion organisation can support only K = {K} destination-market × product opportunities a year. "
  f"We built a reproducible pipeline on real public data — {ds['n_markets']} importing markets (the EU-27 treated as one customs "
  f"territory), {ds['n_products']} HS 6-digit products and decision years {ds['years'][0]}–{ds['years'][1]} — to rank these "
  f"opportunities by the next-year gain in India's share of the market's imports. The dataset contains "
  f"{ds['n_rows']:,} candidate observations, of which {ds['n_with_outcome']:,} have an observed outcome.")
P("We compare two approaches on the identical candidate set: (1) a historical export-momentum baseline (India's annualised "
  "three-year export growth to the market) and (2) a supervised machine-learning ranking that predicts the next-year share "
  "change from tariff, trade-competitiveness, demand and macroeconomic features. Tariffs are those imposed by the importer on "
  "Indian-origin and Chinese-origin goods; the tariff advantage is the tariff faced by China minus the tariff faced by India.")
B([
    ("Main result. ", f"In a rolling-origin backtest over {len(test_years)} held-out decision years ({test_years[0]}–{T}, outcomes "
     f"{test_years[0] + 1}–{T + 1}), the ML ranking {verdict} the baseline: Precision@{K} {pct(ml['precision_at_k'])} vs "
     f"{pct(bl['precision_at_k'])}; average realised share change of the shortlist {sg(ml['mean_d_share_pp_at_k'])} pp vs "
     f"{sg(bl['mean_d_share_pp_at_k'])} pp; NDCG@{K} {f(ml['ndcg_at_k'])} vs {f(bl['ndcg_at_k'])} (random ranking "
     f"{f(U[K]['random_ndcg'])})."),
    ("Momentum backfires. ", f"A random pick gains share {pct(U[K]['universe_precision'])} of the time, so the momentum baseline is "
     f"worse than random: the fastest recent growers tend to mean-revert. The ML ranking avoids this, but its hit rate is only "
     f"{FL['ml_minus_random_prec'] * 100:+.1f} points above random overall; excluding the 2025 outcome year (the US tariff shock) "
     f"it reaches {pct(EXR['ml']['precision_at_k'])} against {pct(EXR['baseline']['precision_at_k'])} for the baseline, while in "
     f"the 2024→2025 fold it underperformed the baseline."),
    ("Uncertainty. ", f"With 10 picks per year the evidence is limited: the bootstrap 95% interval of the mean share change of the "
     f"{boot[ML]['n_picks']} pooled ML picks is {sg(boot[ML]['ci_low'])} to {sg(boot[ML]['ci_high'])} pp, against "
     f"{sg(boot[BL]['ci_low'])} to {sg(boot[BL]['ci_high'])} pp for the baseline."),
    ("Tariffs. ", f"Measured India–China tariff differences are uncommon ({pct(ds['share_nonzero_adv'])} of candidate rows) and "
     f"concentrated in Japan and Korea (India advantage through CEPAs) and Australia, Indonesia and Malaysia (China advantage "
     f"through its FTAs). Removing all tariff features changes Precision@{K} from {pct(ml['precision_at_k'])} to "
     f"{pct(nt['precision_at_k'])} and the mean share change from {sg(ml['mean_d_share_pp_at_k'])} to "
     f"{sg(nt['mean_d_share_pp_at_k'])} pp."),
    ("Trade diversion. ", div_sentence),
    ("Business use. ", f"Do not prioritise on recent export momentum alone. The model is best used as a screening tool that "
     f"produces a {F} shortlist for expert due diligence, not as an automatic decision rule. Key limitations: US Section 301 "
     "duties on China, unilateral GSP preferences and 2022+ preferential schedules are not in the public tariff data used."),
])
page_break()

# ------------------------------------------------------------------ 3 intro
H("1. Introduction and research motivation")
P("India and China compete for the same import markets in textiles, chemicals, metals, machinery and many other manufactured "
  "goods. Since 2018, tariff policy has become an explicit instrument of trade strategy: the United States imposed additional "
  "duties on Chinese goods, regional agreements such as the China–Australia FTA and RCEP deepened China's preferential access, "
  "and India signed or upgraded agreements with Japan, Korea, ASEAN, the UAE and Australia. For an Indian export-promotion "
  "organisation the practical question is not whether tariffs matter in general, but where its limited promotion budget "
  "should go next year.")
P("Central research question: can differences in tariffs faced by Indian and Chinese goods, combined with trade "
  "competitiveness and market demand, help identify the most attractive export markets for Indian exporters?")
P("Supporting questions: (1) How do import tariffs faced by Indian-origin and Chinese-origin goods differ across markets? "
  "(2) Which country-product markets offer India a relative tariff advantage? (3) Does that advantage, together with demand "
  "and competitiveness, help identify future export growth? (4) Can an ML model rank opportunities better than a simple "
  "historical export-growth strategy? (5) Which opportunities should be prioritised when only K can be pursued?")

H("2. Background: international tariffs and India–China trade")
P("Tariffs are imposed by the importing customs territory on goods according to their origin. Under WTO rules members apply "
  "the most-favoured-nation (MFN) rate to each other unless a preferential arrangement applies: reciprocal free-trade "
  "agreements (e.g. India–Japan CEPA 2011, India–Korea CEPA 2010, ASEAN–India FTA 2010, China–Australia FTA 2015, ASEAN–China "
  "FTA, China–Korea FTA 2015) or unilateral schemes such as the Generalised System of Preferences. Additional duties — "
  "anti-dumping, countervailing, safeguard or country-specific measures such as the US Section 301 tariffs on China — can be "
  "layered on top. The relevant comparison for this project is therefore the duty a given market levies on Indian-origin "
  "versus Chinese-origin goods of the same product.")
P(f"Within our study universe, importing markets bought US${ds['china_imports_2024_bn']:,.0f} billion of the 200 products from "
  f"China in 2024 against US${ds['india_imports_2024_bn']:,.0f} billion from India (US${ds['china_imports_2015_bn']:,.0f} bn and "
  f"US${ds['india_imports_2015_bn']:,.0f} bn in 2015), out of total imports of US${ds['world_imports_2024_bn']:,.0f} billion.")
figure("03_india_export_trend", "Imports from India of the 200 study products by the 10 markets, 2012–2025 (US$ bn).", 14)
figure("04_china_export_trend", "Imports from China of the 200 study products by the 10 markets, 2012–2025 (US$ bn).", 14)

# ------------------------------------------------------------------ 5 business decision
H("3. Business decision and prospect-selection formulation")
table(["Element", "Definition in this project"], [
    ["Organisation", "Indian export-promotion council / industry association with limited research, B2B and promotion budget"],
    ["Opportunity", "Destination market × HS 6-digit product (e.g. United States × 850440 static converters)"],
    ["Universe", f"{ds['n_markets']} markets × {ds['n_products']} products = 2,000 pairs per year"],
    ["Candidate rule (at t)", "India exports ≥ US$1m to the market and market imports ≥ US$20m; 3 years of history; both tariffs known"],
    ["Constraint", f"K = {K} opportunities per year (sensitivity K = 5, 20, 50)"],
    ["Objective", "Maximise the next-year change in India's share of the market's imports of the product"],
    ["Exporter / competitor", "India / China"],
], "Prospect-selection formulation.", [4, 12])
P("Why K = 10: a small market-intelligence team can realistically run about one deep-dive per month (market study, buyer "
  "mapping, trade-fair participation) plus a buffer. Why an expansion universe: opportunities where India sells nothing "
  "are green-field entry decisions with different economics (certification, distribution set-up), and their share change is "
  "mechanically bounded at zero, which would distort the evaluation. Restricting to pairs where India already sells at least "
  "US$1m uses only information available at the decision date.")

H("4. Research questions and hypotheses")
B([
    ("H1 (tariff gap): ", "Indian and Chinese goods face materially different applied tariffs in markets with asymmetric trade agreements."),
    ("H2 (trade diversion): ", "A larger tariff advantage for India (or an increase in it) is associated with subsequent gains in India's import share."),
    ("H3 (prediction): ", "A model combining tariffs, competitiveness and demand ranks next-year share gains better than historical export momentum."),
    ("H4 (incremental value of tariffs): ", "Removing tariff features worsens the ML ranking."),
])

H("5. Literature and economic context")
P("The idea that preferential tariffs can create or divert trade goes back to Viner (1950). Empirically, Baier and Bergstrand "
  "(2007) show that free-trade agreements raise members' trade substantially once the endogeneity of agreement formation is "
  "addressed, and Romalis (2007) finds that NAFTA tariff preferences shifted import sourcing. The 2018–2019 US tariffs on China "
  "were passed almost fully into US import prices (Amiti, Redding and Weinstein, 2019; Fajgelbaum et al., 2020) and led to "
  "reallocation of US imports towards other suppliers, including some developing economies (Fajgelbaum et al., 2024; "
  "Freund et al., 2024; Alfaro and Chor, 2023). These studies motivate a tariff-advantage feature but also warn that preferences "
  "are endogenous and that trade responses depend on supply capacity. Revealed comparative advantage follows Balassa (1965). "
  "Structural gravity (Yotov et al., 2016) is the standard framework for causal trade-policy analysis, which this project does "
  "not attempt.")
P("On the methods side, tree ensembles (Breiman, 2001; Friedman, 2001; Ke et al., 2017) are strong baselines for tabular data; "
  "ranking quality is evaluated with Precision@K and NDCG (Järvelin and Kekäläinen, 2002); out-of-time evaluation follows the "
  "rolling-origin principle for forecasting (Tashman, 2000; Bergmeir and Benítez, 2012), and leakage risks are discussed by "
  "Kaufman et al. (2012).")

# ------------------------------------------------------------------ data
H("6. Data sources and collection methodology")
table(["Source", "Variables", "Coverage", "Access"], [
    ["UN Comtrade", "Importer-reported imports (US$, CIF) from India, China, World; India/China world exports 2014", "10 reporters, 200 HS6, 2012–2025", "Public preview API (no key; ≤500 rows/call; hourly call quota)"],
    ["WITS / UNCTAD TRAINS", "MFN and origin-specific preferential applied tariffs (simple average of national lines)", "2012–2023; preferences mostly to 2021", "SDMX API (no key)"],
    ["World Bank WDI", "GDP, GDP growth, CPI inflation, official exchange rate", "10 markets, 2012–2025", "API v2 (no key)"],
    ["UNSD", "HS2022↔HS2017↔HS2012 correlation tables", "All HS6 codes", "Excel download"],
], "Data sources (retrieved 20 Nov 2026; full documentation in data/data_sources.md).", [3, 5.5, 3.8, 3.7], 9)
P("Data feasibility gate. Before committing to the design we verified that (i) TRAINS reports India-specific and "
  "China-specific preferential series for the same importer and HS6 product (e.g. Japan reports a 0% preferential rate for "
  "Indian cotton trousers against a 9.55% MFN rate in 2021); (ii) the same HS6 codes can be matched to Comtrade imports; "
  "(iii) Comtrade supplies importer-reported imports from India, China and the world for 2012–2025 for all ten markets; "
  "(iv) shares and next-year changes can be computed; and (v) the panel is large enough for rolling-origin evaluation. "
  "UAE and Vietnam were dropped because their Comtrade data end in 2023; Thailand and Saudi Arabia because their TRAINS "
  "coverage is sparse.")
P("Several design limits were discovered during collection and are disclosed rather than patched with assumptions: the US "
  "Census duty data that would capture Section 301 duties now require an API key; unilateral GSP preferences are stored in "
  "TRAINS as beneficiary groups whose membership cannot be resolved through the public API; and TRAINS contains no "
  "preferential schedules for 2022 onwards for any of the ten markets.")

H("7. Dataset construction and data dictionary")
P(f"The unit of observation is one destination market × one HS6 product × one decision year. The product universe was fixed "
  f"ex ante with 2014 data: HS6 codes continuous across HS2012, HS2017 and HS2022 (linked to themselves in both UNSD "
  f"correlation tables, excluding many-to-many links), HS chapters 25–96 excluding fuels (27), gems and precious metals (71) "
  f"and arms (93), with India and China each exporting at least US$50m to the world in 2014; the 200 largest by India's 2014 "
  f"exports were kept. {ds['n_strict']} of the 200 codes have an identical scope across revisions (strict 1:1); the rest kept "
  f"their code but transferred a minor part of their scope (e.g. to the new HS2022 headings 8524 and 8549) and are flagged.")
B([
    ("Zero flows: ", "Comtrade omits zero trade. Within a market-year the reporter published, a missing India or China record is a "
     "true zero; a market-year without any publication is missing, never zero."),
    ("Shares: ", "India share = imports from India ÷ total imports of the product, both reported by the same importer in the same year."),
    ("Growth: ", "log growth with a US$100,000 smoothing constant, which handles zeros and damps explosive growth from tiny bases."),
    ("Outliers: ", "no observation is dropped; the ML training target is winsorised at the 1st/99th percentile of each training fold."),
    ("Duplicates: ", "none — one row per market × product × year is asserted in code."),
    ("Commodity prices: ", "share-based outcomes cancel price movements common to all suppliers of the same product in the same market."),
])
P(f"The analytical dataset has {ds['n_rows']:,} rows; the full data dictionary with missing-value rates is in "
  f"data/data_dictionary.md. Rows per decision year range from {min(ds['rows_per_year'].values())} to "
  f"{max(ds['rows_per_year'].values())}.")

# ------------------------------------------------------------------ EDA
H("8. Exploratory data analysis")
P("Figure 3 shows average applied tariffs faced by Indian and Chinese goods by product category in 2021, the last year with "
  "complete preferential data. Figure 4 shows where each country holds the advantage. The advantage is zero in the five "
  "markets where neither origin has a reciprocal agreement captured by TRAINS (USA, EU, UK, Canada, Mexico).")
figure("01_tariff_india_vs_china_by_category", "Applied tariffs faced by Indian vs Chinese goods by category (2021).")
figure("02_tariff_advantage_by_market", "Share of the 200 products with an India or China tariff advantage, by market (2021).")
figure("14_tariff_advantage_over_time", "Mean tariff advantage by market over time.", 14)
figure("07_tariff_advantage_distribution", "Distribution of non-zero tariff advantages across candidate rows.", 14)
figure("05_market_share_india_vs_china", "India vs China share of each market's imports of the study products (2024).", 14)
figure("06_import_growth_by_category", "Import-market growth by product category, 2015–2024.", 14)

# ------------------------------------------------------------------ features & methods
H("9. Feature engineering")
table(["Group", "Features (all dated ≤ t)"], [
    ["Tariff", "tariff on India, tariff on China, tariff advantage, MFN, 1- and 3-year change in advantage, preference flags"],
    ["India trade", "log imports, 1y/3y growth, share, 1y/3y share change, growth volatility, market and basket mirror RCA"],
    ["China trade", "log imports, 1y/3y growth, share, 1y/3y share change, mirror RCA"],
    ["Market demand", "log market size, 1y/3y import growth"],
    ["Macro", "log GDP, GDP growth, inflation, exchange-rate change (WDI)"],
    ["Identifiers", "market and HS section as categoricals (no HS6 identifier, to avoid memorisation)"],
], "Feature set (33 features).", [3, 13])
P("Mirror RCA is computed from importer data: (India's share of the market's imports of the product) / (India's share of the "
  "market's total imports), also over the 10-market basket, and entered as ln(1 + RCA). Tariff-change features are set to "
  "missing when the preferential status at the earlier date is unknown (years before TRAINS first reports a market's "
  "preferences).")

H("10. Methodology and model formulation")
P("Let i index market–product pairs and t decision years. The decision at t uses features x_it observed at or before t and "
  "selects S_t ⊂ C_t with |S_t| = K from the candidate set C_t. The primary outcome is y_it = share_i,t+1 − share_i,t (pp); "
  "success is y_it > 0, specified before any evaluation. Each approach produces a score s_it and selects the K highest scores. "
  "Both approaches are evaluated on the same C_t, the same K and the same outcome year.")

H("11. Baseline approach: historical export momentum")
P("s_it = [ln(X_it + c) − ln(X_i,t−3 + c)] / 3, where X is imports from India and c = US$100,000. This is how many export bodies "
  "prioritise in practice — back what is already growing — and it has no fitted parameters, so it cannot leak future "
  "information. An alternative share-momentum baseline (3-year change in India's share) is reported as a robustness check.")

H("12. Machine-learning approach")
P(f"A regressor predicts y_it; candidates are ranked by the prediction. Two families were compared — gradient boosting "
  f"(HistGradientBoostingRegressor, native handling of missing values and categoricals) and random forests (median imputation "
  f"and one-hot encoding fitted inside each training fold) — over small grids. Selection used the mean NDCG@20 across "
  f"validation decision years 2018, 2019 and 2020, each trained only on earlier decision years. The selected model is a "
  f"{fam} with {', '.join(f'{k} = {v}' for k, v in sm['params'].items())}. The training target is winsorised at the "
  f"training fold's 1st and 99th percentiles. A classification formulation was not used because the business objective "
  f"(largest share gains) is continuous and a binary label would discard the magnitude of gains.")
val = sorted(R["validation"], key=lambda r: -r["ndcg_at_20"])[:6]
table(["Model", "Parameters", "NDCG@20", "Spearman", "Mean Δshare top-20"],
      [[v["model"], v["params"], f(v["ndcg_at_20"]), f(v["spearman"]), sg(v["mean_d_share_top20"])] for v in val],
      "Validation results (decision years 2018–2020; top six configurations).", [1.6, 8.5, 1.9, 1.9, 2.4], 8.5)

H("13. Temporal validation and backtesting")
P("We use rolling-origin (expanding-window) backtesting rather than a random split, because a random split would let the "
  "model learn from later years' outcomes when predicting earlier decisions. For each decision year T the model is retrained "
  "on decision years 2015…T−1 — whose next-year outcomes were already observable at T — and scores all candidates of year T; "
  "the shortlist is judged on realised T+1 outcomes. Hyper-parameters are frozen from the validation stage. Preprocessing "
  "(winsorisation bounds, imputation, encoding) is fitted only on training rows. The final model, trained on decision years "
  f"2015–{F - 1}, produces the live {F} shortlist whose outcome is not yet observable.")
table(["Decision year", "Training years", "Training rows", "Candidates", "With outcome"],
      [[r["decision_year"], r["train_years"], f"{r['n_train']:,}", r["n_candidates"], r["n_with_outcome"]] for r in R["folds"]],
      "Backtest folds.", [3, 3.5, 3, 3, 3])

# ------------------------------------------------------------------ results
H("14. Model evaluation and results")
rows = []
for lab, key, fmt in [("Precision@10", "precision_at_k", pct), ("Average future market-share change@10 (pp)", "mean_d_share_pp_at_k", sg),
                      ("Median future market-share change@10 (pp)", "median_d_share_pp_at_k", sg),
                      ("Average future export growth@10 (log)", "mean_export_growth_log_at_k", sg),
                      ("NDCG@10", "ndcg_at_k", f), ("Top-decile precision@10", "top_decile_precision_at_k", pct),
                      ("Overlap with true top-10", "overlap_true_top_k", pct), ("Spearman (whole universe)", "spearman_all", f)]:
    rows.append([lab, fmt(bl[key]), fmt(ml[key]), fmt(nt[key]), fmt(alt[key])])
rows.append(["Random selection: Precision / mean Δshare / NDCG", pct(U[K]["universe_precision"]) + " / " + sg(U[K]["universe_mean_d_share_pp"]) + " / " + f(U[K]["random_ndcg"]), "", "", ""])
table(["Metric (K = 10)", "Historical baseline", "ML model", "ML w/o tariffs", alt_name.replace("ML alternative family", "Alt. family")],
      rows, f"Backtest results averaged over decision years {test_years[0]}–{T} (outcomes {test_years[0] + 1}–{T + 1}).", [5.6, 2.6, 2.4, 2.6, 2.6], 9)
P(f"Interpretation. Precision@10 is the share of the ten selected opportunities in which India's share rose; a random "
  f"selection would achieve about {pct(U[K]['universe_precision'])}. The baseline achieves {pct(bl['precision_at_k'])} — worse "
  f"than random, because the fastest recent growers tend to mean-revert — and the ML model {pct(ml['precision_at_k'])}, only "
  f"slightly above random. On NDCG@10, which rewards picking the largest gainers, both beat a random ranking "
  f"({f(U[K]['random_ndcg'])}). The ML advantage grows with K (NDCG@50 {f(S[(ML, 50)]['ndcg_at_k'])} vs "
  f"{f(S[(BL, 50)]['ndcg_at_k'])}). Fold by fold, ML beat the baseline in the first three test years but not in the "
  f"2024→2025 fold — the year of the 2025 US tariff changes, a plausible (but untested) regime shift. The average realised share change of the ML shortlist is "
  f"{sg(ml['mean_d_share_pp_at_k'])} pp versus {sg(bl['mean_d_share_pp_at_k'])} pp for the baseline. The pooled bootstrap "
  f"95% intervals of the mean share change ({sg(boot[ML]['ci_low'])} to {sg(boot[ML]['ci_high'])} pp for ML; "
  f"{sg(boot[BL]['ci_low'])} to {sg(boot[BL]['ci_high'])} pp for the baseline) quantify how much of the difference could be "
  f"sampling noise.")
by = R["by_year"]
yrs = sorted({r["year"] for r in by})
g = {(r["year"], r["method"]): r for r in by}
table(["Decision → outcome", "Baseline P@10", "ML P@10", "Baseline Δshare@10", "ML Δshare@10", "Baseline NDCG", "ML NDCG"],
      [[f"{y}→{y + 1}", pct(g[(y, BL)]["precision_at_k"]), pct(g[(y, ML)]["precision_at_k"]),
        sg(g[(y, BL)]["mean_d_share_pp_at_k"]), sg(g[(y, ML)]["mean_d_share_pp_at_k"]),
        f(g[(y, BL)]["ndcg_at_k"]), f(g[(y, ML)]["ndcg_at_k"])] for y in yrs],
      "Results by test fold (K = 10).", [3, 2.2, 2, 2.6, 2.4, 2.3, 2.1], 9)
figure("11b_backtest_by_year", "Precision@10 and mean share change of the top-10 by test fold.", 15)
figure("11_performance_comparison", "Performance as a function of shortlist size K, averaged over test folds.", 16)
figure("09_actual_vs_predicted", "Realised share change by score decile (test folds): ML and baseline.", 14)
figure("08_feature_importance", "Permutation importance of the ML model on the last held-out decision year.", 14)
imp = R["importance"][:8]
P("The most important predictors (Figure above) are: " + "; ".join(f"{r['feature']} ({r['importance_mean']:.3f})" for r in imp) +
  ". Importance measures predictive contribution in this model, not causal effect.")

H("15. Top-K shortlist comparison")
cmp = R[f"cmp_{T}"]
both = [r for r in cmp if r["in"] == "both"]
P(f"For the {T} decision, {len(both)} of the 10 opportunities appear in both shortlists. Figure below shows each list with the "
  f"realised {T + 1} share change.")
figure(f"10_topk_comparison_{T}", f"Top-10 shortlists for decision year {T}, with realised {T + 1} share change.", 16)


def sl_rows(lst):
    return [[r["rank"], r["market"], r["hs6"], r["short_desc"][:38], f"{r['share_ind']:.1f}", sg(r["tariff_adv"], 1),
             sg(r["g3_ind"]), sg(r.get("y_d_share_pp")) if r.get("y_d_share_pp") is not None else "n/a"] for r in lst]


hdr = ["#", "Market", "HS6", "Product", "India share %", "Tariff adv.", "3y growth", "Realised Δshare"]
wd = [0.7, 2.4, 1.5, 5.6, 1.6, 1.5, 1.5, 1.8]
table(hdr, sl_rows(R[f"top10_baseline_{T}"]), f"Baseline shortlist, decision year {T}.", wd, 8)
table(hdr, sl_rows(R[f"top10_ml_{T}"]), f"ML shortlist, decision year {T}.", wd, 8)
PB, PM, PU = R["profiles"][f"baseline_{T}"], R["profiles"][f"ml_{T}"], R["profiles"][f"universe_{T}"]
P(f"Why the lists differ. By construction the momentum baseline selects the fastest recent growers (average 3-year log growth "
  f"{sg(PB['g3_ind'])} a year against {sg(PU['g3_ind'])} for all candidates; median Indian exports US${PB['imp_ind_m']:.1f}m), "
  f"and very fast growth tends to mean-revert. The ML picks have average 3-year growth of {sg(PM['g3_ind'])}, median Indian "
  f"exports of US${PM['imp_ind_m']:.1f}m and an average Indian share of {PM['share_ind']:.1f}% (baseline picks "
  f"{PB['share_ind']:.1f}%; all candidates {PU['share_ind']:.1f}%). The decisive difference is the recent share trajectory: "
  f"in the baseline picks India's share had risen {sg(PB['d3_share_ind'], 1)} pp over the previous three years, whereas in the "
  f"ML picks it had fallen {sg(PM['d3_share_ind'], 1)} pp (all candidates {sg(PU['d3_share_ind'], 1)} pp). The same pattern holds "
  f"in every test year: the baseline makes momentum bets, the ML model makes rebound bets, consistent with the 3-year share "
  f"change being its most important feature. The model's skill is thus mainly exploiting mean reversion in import shares. "
  f"The trade-off is transparency (baseline) against use of more information (ML).")
st_ = {r["method"]: r["jaccard_top10"] for r in R["stability"]}
P(f"Ranking stability (Jaccard overlap of consecutive years' top-10): baseline {f(st_.get(BL), 2)}, ML {f(st_.get(ML), 2)}.")

# ------------------------------------------------------------------ robustness
H("16. Robustness")
strict = {r["method"]: r for r in R["robust_strict"] if r["k"] == K}
ex = {r["method"]: r for r in R["robust_ex2025"] if r["k"] == K}
lomo = R["robust_lomo"]


def rng(m):
    v = [r["precision_at_10"] for r in lomo if r["method"] == m]
    return f"{pct(min(v))}–{pct(max(v))}"


table(["Check (K = 10)", "Baseline", "ML"], [
    ["Strict 1:1 HS codes only: Precision@10", pct(strict["baseline"]["precision_at_k"]), pct(strict["ml"]["precision_at_k"])],
    ["Strict 1:1 HS codes only: mean Δshare (pp)", sg(strict["baseline"]["mean_d_share_pp_at_k"]), sg(strict["ml"]["mean_d_share_pp_at_k"])],
    ["Excluding 2025 outcomes: Precision@10", pct(ex["baseline"]["precision_at_k"]), pct(ex["ml"]["precision_at_k"])],
    ["Excluding 2025 outcomes: mean Δshare (pp)", sg(ex["baseline"]["mean_d_share_pp_at_k"]), sg(ex["ml"]["mean_d_share_pp_at_k"])],
    ["Leave-one-market-out: range of Precision@10", rng("baseline"), rng("ml")],
    [f"K = 5: Precision@5", pct(S[(BL, 5)]["precision_at_k"]), pct(S[(ML, 5)]["precision_at_k"])],
    [f"K = 20: Precision@20", pct(S[(BL, 20)]["precision_at_k"]), pct(S[(ML, 20)]["precision_at_k"])],
    [f"K = 50: Precision@50", pct(S[(BL, 50)]["precision_at_k"]), pct(S[(ML, 50)]["precision_at_k"])],
    ["Share-momentum baseline: Precision@10", pct(S[("Share-momentum (alt. baseline)", K)]["precision_at_k"]), ""],
], "Robustness checks.", [8, 3.5, 3.5])
grp = [r for r in R["robust_group"] if r["group_type"] == "category"]
cats = sorted({r["group"] for r in grp})
gg = {(r["group"], r["method"]): r for r in grp}
table(["Category", "n / year", "Spearman baseline", "Spearman ML", "Prec. top-10% baseline", "Prec. top-10% ML"],
      [[c, f"{gg[(c, 'ml')]['n']:.0f}", f(gg[(c, 'baseline')]["spearman"], 2), f(gg[(c, 'ml')]["spearman"], 2),
        pct(gg[(c, 'baseline')]["precision_top10pct"]), pct(gg[(c, 'ml')]["precision_top10pct"])] for c in cats if (c, "ml") in gg],
      "Performance within product categories (test folds).", [4.6, 1.6, 2.3, 2.1, 2.7, 2.5], 8.5)
grp = [r for r in R["robust_group"] if r["group_type"] == "market"]
gg = {(r["group"], r["method"]): r for r in grp}
mk = sorted({r["group"] for r in grp})
table(["Market", "n / year", "Spearman baseline", "Spearman ML", "Prec. top-10% baseline", "Prec. top-10% ML"],
      [[c, f"{gg[(c, 'ml')]['n']:.0f}", f(gg[(c, 'baseline')]["spearman"], 2), f(gg[(c, 'ml')]["spearman"], 2),
        pct(gg[(c, 'baseline')]["precision_top10pct"]), pct(gg[(c, 'ml')]["precision_top10pct"])] for c in mk if (c, "ml") in gg],
      "Performance within destination markets (test folds).", [4.6, 1.6, 2.3, 2.1, 2.7, 2.5], 8.5)
conc = [r for r in R["concentration"] if r["method"] == "ml"]
P("Concentration of the ML shortlist: " + "; ".join(f"{r['year']}: {r['n_markets']} markets, {r['n_products']} products, "
                                                   f"most frequent market {r['top_market']} ({r['top_market_count']})" for r in conc) + ".")

# ------------------------------------------------------------------ trade diversion
H("17. Trade diversion analysis")
P("We test whether opportunities where China faces a higher tariff than India are followed by gains in India's share. We "
  "distinguish (a) observed correlations, (b) predictive relationships (the tariff ablation in Section 14), (c) plausible "
  "mechanisms and (d) causal effects, which we do not estimate.")
table(["Tariff advantage at t", "n", "Mean Δshare (pp)", "Share gaining", "Mean log export growth"],
      [[r["adv_bin"], f"{r['n']:,}", sg(r["mean_d_share_pp"]), pct(r["share_gaining"]), sg(r["mean_export_growth_log"])] for r in R["div_bins"]],
      "Next-year outcomes by level of tariff advantage.", [5.5, 1.8, 2.8, 2.6, 3.3])
table(["1-year change in advantage", "n", "Mean Δshare (pp)", "Share gaining", "Mean log export growth"],
      [[r["adv_change"], f"{r['n']:,}", sg(r["mean_d_share_pp"]), pct(r["share_gaining"]), sg(r["mean_export_growth_log"])] for r in R["div_change"]],
      "Next-year outcomes by change in tariff advantage.", [5.5, 1.8, 2.8, 2.6, 3.3])
table(["Specification", "Variable", "Coef.", "SE", "p", "N", "R²"],
      [[r["spec"], r["variable"], f(r["coef"], 4), f(r["se"], 4), f(r["p_value"], 3), r["n"], f(r["r2"], 3)] for r in R["div_reg"]],
      "Fixed-effects OLS; SE clustered by market–product pair.", [5, 2.4, 1.6, 1.6, 1.3, 1.3, 1.3], 8.5)
figure("13_trade_diversion", "Mean next-year share change by tariff-advantage level and change (association only).", 16)
_db = {r["adv_bin"]: r for r in R["div_bins"]}
_dc = {r["adv_change"]: r for r in R["div_change"]}
P(f"Descriptively, pairs where India held a tariff advantage gained on average "
  f"{sg(_db['India advantage (> +0.5pp)']['mean_d_share_pp'])} pp of share the following year, against "
  f"{sg(_db['China advantage (< -0.5pp)']['mean_d_share_pp'])} pp where China held the advantage — the expected direction, but "
  f"the shares of pairs gaining share are almost identical and the regression coefficients are not statistically significant. "
  f"Changes in the advantage point the other way: pairs where the advantage moved towards China (mostly the phasing-in of "
  f"China's FTAs) saw India gain {sg(_dc['Advantage moved to China']['mean_d_share_pp'])} pp, versus "
  f"{sg(_dc['Advantage moved to India']['mean_d_share_pp'])} pp where it moved towards India (n = "
  f"{_dc['Advantage moved to India']['n']}), so there is no consistent trade-diversion pattern in this sample.")
P("Interpretation. Preferential margins are negotiated, phased in over many years and frequently granted on products where "
  "trade was already expanding; they also coincide with exchange-rate movements, supply-chain relocation and industrial "
  "policy. The associations above should therefore not be read as the effect of tariffs on Indian exports. A credible causal "
  "design would require, for example, an event study around the entry into force of a specific agreement with matched "
  "control products and markets, or a structural gravity model (Yotov et al., 2016), and it would need the US Section 301 "
  "duties that are missing from our tariff data.")

# ------------------------------------------------------------------ simulation
H("18. Simulation methodology and findings")
P(f"The simulation (app/streamlit_app.py; notebooks/08_simulation.ipynb) perturbs the decision-time inputs of the final model "
  f"for the {F} candidates and re-ranks them. Tariff shocks change the tariff on India and/or China (floored at zero) and "
  f"propagate to the advantage and its 1- and 3-year changes; the demand scenario shifts the market import-growth features. "
  f"Users choose K (5, 10, 20), presets or custom shocks, and can restrict a shock to selected markets or categories. The "
  f"baseline shortlist does not depend on tariffs, so it is unchanged in every tariff scenario.")
table(["Scenario", "New in top-10", "Removed", "Mean Δ prediction, all candidates (pp)", "Mean |rank change|"],
      [[r["scenario"], r["n_new"], r["n_removed"], sg(r["mean_pred_change_all"], 3), f(r["mean_abs_rank_change_all"], 1)]
       for r in R["scenarios"] if r["k"] == K], f"Model-based what-if scenarios on {F} candidates (K = 10).", [6, 2, 1.8, 3.6, 2.6], 9)
figure("12_simulation_scenarios", "Scenario impact on the ML shortlist and sensitivity to China's tariff.", 16)
P("These are sensitivity analyses of a predictive model. Tariff changes in the training data were rare and concentrated in a "
  "few markets, so the model's response to hypothetical tariffs extrapolates beyond the observed variation; the results are "
  "illustrative and must not be read as forecasts of policy effects.")

# ------------------------------------------------------------------ implications etc.
H("19. Business implications")
fwd = R[f"top10_ml_{F}"]
B([
    f"Use the ML ranking as a screening tool: it narrows ~{round(sum(ds['rows_per_year'].values()) / len(ds['rows_per_year']))} "
    f"candidates to a shortlist that domain experts then vet for non-tariff barriers, capacity and buyer interest.",
    f"Do not prioritise purely on recent export momentum: in our backtest it was worse than a random pick "
    f"({pct(bl['precision_at_k'])} vs {pct(U[K]['universe_precision'])}) because rapid growth frequently reverses.",
    "Treat tariff advantages as one input. Where India gains a margin (e.g. new CEPAs/ECTA), monitor utilisation and rules-of-origin "
    "compliance rather than assuming automatic gains.",
    f"Live {F} ML shortlist (top 5): " + "; ".join(f"{r['market']} – {r['hs6']} {r['short_desc'][:40]}" for r in fwd[:5]) + ".",
])
table(hdr[:-1], [r[:-1] for r in sl_rows(R[f"top10_ml_{F}"])], f"Live ML shortlist for decision year {F} (outcome not yet observable).", wd[:-1], 8)

H("20. Limitations and threats to validity")
B([
    "US Section 301 duties on China (2018–) and 2025 US tariffs are not in TRAINS; the US India–China advantage is understated (measured as zero).",
    "Unilateral GSP preferences (EU, UK, Canada GPT, US GSP for India until June 2019) are excluded for both origins.",
    f"Preferential schedules for 2022–2025 are carried forward ({pct(ds['share_tariff_imputed'])} of candidate rows); India–Australia ECTA, India–UAE CEPA and RCEP are not captured.",
    "Anti-dumping, safeguards, non-tariff barriers, rules of origin and preference utilisation are not modelled.",
    "Selection: only products where both countries were large exporters in 2014 and pairs where India already sells ≥ US$1m.",
    f"Only {len(test_years)} test years × 10 picks; differences are indicative and reported with bootstrap intervals.",
    "Regime shifts (COVID-19, the 2022 commodity spike, 2025 US tariffs) limit transferability across years.",
    "Importer-reported data have valuation, timing and re-export/trans-shipment issues and are revised.",
    "Feature importance and regression coefficients are predictive/associational, not causal.",
])

H("21. Conclusion")
P(f"Using real public data and a leakage-safe rolling-origin design, we built and evaluated a prospect-selection system for "
  f"Indian export promotion. The ML ranking {verdict} a historical momentum baseline on held-out years "
  f"(Precision@10 {pct(ml['precision_at_k'])} vs {pct(bl['precision_at_k'])}; mean share change {sg(ml['mean_d_share_pp_at_k'])} vs "
  f"{sg(bl['mean_d_share_pp_at_k'])} pp), mainly because momentum picks mean-revert; against a random pick "
  f"({pct(U[K]['universe_precision'])}) the ML edge is small and did not survive the 2025 tariff shock. Measured India–China tariff differences exist mainly in Asia-Pacific markets with "
  f"asymmetric trade agreements, but they are rare in the candidate universe and {tariff_sentence}; the trade-diversion "
  f"association is {'statistically significant' if FL['diversion_significant'] else 'not statistically significant'}. The answer to the central question is "
  f"therefore qualified: tariff differences are a relevant but secondary signal; combining them with competitiveness and "
  f"demand in a supervised ranking helps primarily through the non-tariff features. Better tariff data (Section 301, GSP, "
  f"recent agreements) is the most valuable next step.")

H("22. References")
refs = [
    "Alfaro, L., & Chor, D. (2023). Global supply chains: The looming “great reallocation”. NBER Working Paper 31661.",
    "Amiti, M., Redding, S. J., & Weinstein, D. E. (2019). The impact of the 2018 tariffs on prices and welfare. Journal of Economic Perspectives, 33(4), 187–210.",
    "Baier, S. L., & Bergstrand, J. H. (2007). Do free trade agreements actually increase members' international trade? Journal of International Economics, 71(1), 72–95.",
    "Balassa, B. (1965). Trade liberalisation and “revealed” comparative advantage. The Manchester School, 33(2), 99–123.",
    "Bergmeir, C., & Benítez, J. M. (2012). On the use of cross-validation for time series predictor evaluation. Information Sciences, 191, 192–213.",
    "Breiman, L. (2001). Random forests. Machine Learning, 45(1), 5–32.",
    "Fajgelbaum, P. D., Goldberg, P. K., Kennedy, P. J., & Khandelwal, A. K. (2020). The return to protectionism. Quarterly Journal of Economics, 135(1), 1–55.",
    "Fajgelbaum, P., Goldberg, P., Kennedy, P., Khandelwal, A., & Taglioni, D. (2024). The US–China trade war and global reallocations. American Economic Review: Insights, 6(2), 295–312.",
    "Freund, C., Mattoo, A., Mulabdic, A., & Ruta, M. (2024). Is US trade policy reshaping global supply chains? Journal of International Economics, 152, 104011.",
    "Friedman, J. H. (2001). Greedy function approximation: A gradient boosting machine. Annals of Statistics, 29(5), 1189–1232.",
    "Järvelin, K., & Kekäläinen, J. (2002). Cumulated gain-based evaluation of IR techniques. ACM Transactions on Information Systems, 20(4), 422–446.",
    "Kaufman, S., Rosset, S., Perlich, C., & Stitelman, O. (2012). Leakage in data mining: Formulation, detection, and avoidance. ACM Transactions on Knowledge Discovery from Data, 6(4), 1–21.",
    "Ke, G., Meng, Q., Finley, T., et al. (2017). LightGBM: A highly efficient gradient boosting decision tree. Advances in Neural Information Processing Systems, 30.",
    "Pedregosa, F., et al. (2011). Scikit-learn: Machine learning in Python. Journal of Machine Learning Research, 12, 2825–2830.",
    "Romalis, J. (2007). NAFTA's and CUSFTA's impact on international trade. Review of Economics and Statistics, 89(3), 416–435.",
    "Tashman, L. J. (2000). Out-of-sample tests of forecasting accuracy: An analysis and review. International Journal of Forecasting, 16(4), 437–450.",
    "Viner, J. (1950). The Customs Union Issue. New York: Carnegie Endowment for International Peace.",
    "Yotov, Y. V., Piermartini, R., Monteiro, J.-A., & Larch, M. (2016). An Advanced Guide to Trade Policy Analysis: The Structural Gravity Model. Geneva: WTO and UNCTAD.",
    "Data: United Nations (2026). UN Comtrade Database, https://comtradeplus.un.org/ (accessed 20 Nov 2026).",
    "Data: World Bank (2026). World Integrated Trade Solution — UNCTAD TRAINS, https://wits.worldbank.org/ (accessed 20 Nov 2026).",
    "Data: World Bank (2026). World Development Indicators, https://databank.worldbank.org/source/world-development-indicators (accessed 20 Nov 2026).",
    "Data: United Nations Statistics Division (2026). HS correlation and conversion tables, https://unstats.un.org/unsd/classifications/Econ (accessed 20 Nov 2026).",
]
for r_ in refs:
    p = doc.add_paragraph(r_)
    p.paragraph_format.left_indent = Cm(0.8)
    p.paragraph_format.first_line_indent = Cm(-0.8)
    for run in p.runs:
        run.font.size = Pt(10)

H("Appendix A. Formulas")
B([
    "Tariff advantage: ADV = τ_China − τ_India (pp); τ_o = origin-specific preferential rate if reported by TRAINS, else MFN.",
    "India share: s = M_India / M_World × 100; outcome Δs = s_{t+1} − s_t.",
    "Log growth: g_k = [ln(X_t + c) − ln(X_{t−k} + c)] / k, c = US$100,000.",
    "Mirror RCA: RCA = (M_India,p / M_India,total) / (M_World,p / M_World,total); feature = ln(1 + RCA).",
    "Precision@K = (1/K) Σ_{i∈S} 1[Δs_i > 0].",
    "NDCG@K = DCG@K / IDCG@K, DCG@K = Σ_{r=1..K} rel_r / log2(r + 1), rel = max(Δs, 0).",
    "Top-decile precision@K = share of the K picks whose Δs is in the top decile of that year's candidates.",
])
H("Appendix B. Technical implementation")
P("Python 3 pipeline (scripts/run_pipeline.py) with stages collect → clean → features → backtest → robustness → diversion → "
  "simulation → figures → validate; configuration in config/config.yaml; fixed random seed 42; all raw API responses cached "
  "in data/raw; unit tests in tests/ (pytest); quality-control report in outputs/metrics/qc_report.csv. See README.md for run "
  "instructions.")
qc = R["qc"]
table(["Quality-control check", "Passed", "Detail"], [[q["check"], "yes" if q["passed"] else "NO", q["detail"]] for q in qc],
      "Automated quality-control checks.", [7, 1.5, 7.5], 8.5)

out = ROOT / "docs" / "report.docx"
doc.save(out)
print("wrote", out)
