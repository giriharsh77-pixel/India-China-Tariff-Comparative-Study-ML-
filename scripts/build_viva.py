"""Viva / defence preparation: docs/viva_questions_answers.md (+ .docx via pandoc).
All numbers are read from outputs/results_summary.json."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
R = json.loads((ROOT / "outputs/results_summary.json").read_text())
K, T, F = R["k"], R["test_year_last"], R["forward_year"]
S = {(r["method"], r["k"]): r for r in R["summary"]}
U = {r["k"]: r for r in R["universe"]}
BL, ML, NT = "Historical momentum (baseline)", "ML ranking", "ML without tariff features"
bl, ml, nt = S[(BL, K)], S[(ML, K)], S[(NT, K)]
ds = R["dataset"]
sm = R["selected_model"]
boot = {b["method"]: b for b in R["bootstrap"]}
reg2 = next(r for r in R["div_reg"] if r["spec"].startswith("(2)"))
reg3 = next(r for r in R["div_reg"] if r["spec"].startswith("(3)") and r["variable"] == "d1_tariff_adv")
test_years = [f["decision_year"] for f in R["folds"] if f["decision_year"] <= T]
imp = [r["feature"] for r in R["importance"][:5]]
tariff_rank = [i + 1 for i, r in enumerate(R["importance"]) if any(s in r["feature"] for s in ("tariff", "pref", "mfn"))]
pct = lambda x: f"{int(100 * x + 0.5 + 1e-9) if x >= 0 else -int(-100 * x + 0.5 + 1e-9)}%"  # round half up (matches deck)
sg = lambda x, d=2: f"{x:+.{d}f}"
better = ml["precision_at_k"] > bl["precision_at_k"]

QA = [
    ("Why is this a prospect-selection problem?",
     f"Because the organisation faces many more opportunities than it can pursue: 2,000 market–product pairs a year "
     f"(about {round(sum(ds['rows_per_year'].values()) / len(ds['rows_per_year']))} eligible candidates) but capacity for K = {K}. "
     "The output is a ranked shortlist evaluated on the realised outcomes of the selected items, not a point forecast for every pair."),
    ("Why did you select K = 10?",
     "It reflects a small market-intelligence team running roughly one deep-dive per month plus a buffer. Because the choice is a "
     "business assumption, we also report K = 5, 20 and 50 (Appendix A3 / report Section 16); the ranking of the two approaches "
     "can be checked at each K."),
    ("Why India as exporter and China as the competitor?",
     "China is the largest supplier in most of the manufactured products India exports, so it is the natural benchmark; "
     "tariff asymmetries between the two (FTAs, preferences, US duties on China) are a frequently cited source of opportunity "
     "for Indian exporters under 'China+1' sourcing."),
    ("How are tariffs measured?",
     "From WITS/UNCTAD TRAINS: the simple average of the national ad valorem tariff lines within each HS6, imposed by the importing "
     "market. For each origin we use the origin-specific preferential series if TRAINS reports one, otherwise the MFN rate. "
     "Tariff advantage = tariff faced by China − tariff faced by India."),
    ("What is the difference between MFN and applied tariffs?",
     "MFN is the rate a WTO member charges all other members by default. The applied rate actually faced by an origin can be lower "
     "under a preferential agreement (FTA, CEPA, GSP) or higher with additional duties (anti-dumping, Section 301). We compare "
     "like with like: the same rule is applied to India and China, so we never set a preferential rate against an MFN rate "
     "unless that asymmetry is real (only one origin has a preference)."),
    ("Why HS 6-digit codes?",
     "HS6 is the most detailed level harmonised internationally, so the same product can be matched across Comtrade and TRAINS and "
     "across countries. We only kept codes continuous across HS2012, HS2017 and HS2022 using the official UNSD correlation tables, "
     f"and checked robustness on the {ds['n_strict']} strictly 1:1 codes."),
    ("Why use country–product pairs as observations?",
     "That is the unit at which a promotion body acts (a trade fair, buyer-seller meet or market study is for a product in a "
     "market) and the level at which tariffs and market shares are defined."),
    ("Why predict future market performance rather than tariffs?",
     "The business objective is export success; tariffs are an input. Predicting tariffs would not tell the organisation where "
     "Indian exporters will gain."),
    ("Why use market-share changes?",
     "A share compares India with all other suppliers of the same product in the same market and year, so price changes, "
     "exchange-rate swings and demand shocks common to all suppliers cancel out. Export growth is reported as a secondary outcome."),
    ("Why is historical export growth a meaningful baseline?",
     "It is what an organisation without a model would do — back what is already growing — and it has no fitted parameters, "
     "so it cannot leak information. Beating it shows the model adds value beyond momentum."),
    ("Why did you select this particular ML model?",
     f"We compared gradient boosting and random forests over small grids and picked the configuration with the best mean NDCG@20 "
     f"on validation decision years 2018–2020 only. The winner was {sm['model'].upper()} with {sm['params']}. Tree ensembles handle "
     "non-linear interactions, mixed scales and (for HGB) missing values natively; we avoided more complex models because the "
     "sample is modest."),
    ("What is Precision@K?",
     f"The share of the K selected opportunities that are successes. Success was pre-specified as India's import share rising in "
     f"the next year. A random pick achieves about {pct(U[K]['universe_precision'])}; our baseline {pct(bl['precision_at_k'])} and "
     f"ML {pct(ml['precision_at_k'])} at K = {K}."),
    ("Why not use a random train/test split?",
     "Trade data are serially correlated and the decision is made in time. A random split would train on later years and test on "
     "earlier ones, leaking information about shocks such as COVID-19. We use rolling-origin backtesting: for decision year T the "
     "model is trained only on decision years before T."),
    ("What is data leakage?",
     "Any use, during training or feature construction, of information that would not have been available at decision time — "
     "e.g. future outcomes, future tariffs, preprocessing fitted on the full sample, or choosing the model on the test years."),
    ("How did you avoid look-ahead bias?",
     "(1) The product universe was fixed with 2014 data; (2) all features are dated ≤ t and outcomes (y_*) are separate columns never "
     "passed to models — checked by a unit test; (3) each fold trains on decision years ≤ T−1 whose outcomes are known at T; "
     "(4) winsorisation and imputation are fitted on training rows; (5) model selection used validation years 2018–2020, disjoint "
     "from test years; (6) candidate eligibility uses only data at t; (7) tariff gaps are filled only forward in time."),
    ("What is trade diversion?",
     "Viner's term for a preferential tariff shifting imports from a more efficient non-member supplier to a member. Here: if a "
     "market charges China more than India, buyers may switch some sourcing to India."),
    ("Can you conclude that tariffs cause export growth?",
     f"No. Our fixed-effects regression gives {sg(reg2['coef'], 3)} pp per pp of advantage (p = {reg2['p_value']:.2f}) and "
     f"{sg(reg3['coef'], 3)} pp per pp change in advantage (p = {reg3['p_value']:.2f}). Even a significant coefficient would be an "
     "association: preferences are negotiated for products where trade is already expanding and coincide with other shocks. "
     "A causal design would need an event study around agreement entry-into-force with matched controls, or structural gravity."),
    ("How reliable is your simulation?",
     "It is a sensitivity analysis of the trained model, labelled as such. It shows how the model's ranking responds to changed "
     "inputs, not what would happen to trade. Tariff changes in the training data were rare and concentrated in a few markets, "
     "so large hypothetical shocks extrapolate beyond the observed variation."),
    ("What happens if the ML model performs worse than the baseline?",
     ("In our backtest the ML model " + ("outperformed" if better else "did not outperform") +
      f" the baseline on Precision@{K} ({pct(ml['precision_at_k'])} vs {pct(bl['precision_at_k'])}), but it did worse than the "
      f"baseline in one fold: decisions made in 2024 and judged on 2025, the year of the US tariff shock. Its overall hit rate is "
      f"also close to a random pick ({pct(U[K]['universe_precision'])}). We report this as it is: the model is a screen that avoids "
      "the mean-reversion trap of momentum, not a reliable predictor of winners; under a regime shift its learned patterns can "
      "fail, and the transparent baseline would be preferred if it were consistently better.")),
    ("What are the limitations of the project?",
     "US Section 301 and 2025 duties on China are not in TRAINS (US advantage measured as zero); unilateral GSP is excluded; "
     f"preferences after 2021 are carried forward ({pct(ds['share_tariff_imputed'])} of rows); non-tariff barriers and rules of "
     f"origin are not modelled; only {len(test_years)} test years; selection of products with large 2014 exports; importer data "
     "revisions and trans-shipment."),
    ("Did tariff features help the model?",
     f"Ablation: dropping all tariff features changes Precision@{K} from {pct(ml['precision_at_k'])} to {pct(nt['precision_at_k'])} "
     f"and mean share change from {sg(ml['mean_d_share_pp_at_k'])} to {sg(nt['mean_d_share_pp_at_k'])} pp. The most important "
     f"features were {', '.join(imp)}; the highest-ranked tariff feature is at position "
     f"{tariff_rank[0] if tariff_rank else 'n/a'} of the permutation-importance list."),
    ("How certain are the performance differences?",
     f"With 10 picks per year over {len(test_years)} years, uncertainty is substantial. Bootstrap 95% intervals of the mean share "
     f"change of the pooled picks: ML {sg(boot[ML]['ci_low'])} to {sg(boot[ML]['ci_high'])} pp; baseline "
     f"{sg(boot[BL]['ci_low'])} to {sg(boot[BL]['ci_high'])} pp. We also show results per fold and for K = 5–50."),
    ("Why treat the EU as one market?",
     "The EU applies a single common external tariff. Using member states would double-count the same tariff and include "
     "intra-EU trade; Comtrade reporter 97 gives extra-EU imports of the EU as a single customs territory."),
    ("How did you handle zero exports and extreme growth rates?",
     "Comtrade omits zero flows, so within a reported market-year a missing India row is a true zero. Growth uses logs with a "
     "US$100,000 smoothing constant; candidates must have at least US$1m of Indian exports, so tiny bases do not dominate; the "
     "training target is winsorised at fold-specific 1st/99th percentiles; no observation is dropped."),
    ("Why exclude opportunities where India currently exports nothing?",
     "They are green-field entry decisions with different costs and a mechanically non-negative share change, which would bias "
     "Precision@K upward for any rule that picks them. The eligibility rule uses only decision-time data and is applied "
     "identically to both approaches."),
]


def main():
    lines = ["# Viva and defence preparation — questions and answers", "",
             "Numbers are generated from `outputs/results_summary.json`, so they match the report and slides.", ""]
    for i, (q, a) in enumerate(QA, 1):
        lines += [f"## Q{i}. {q}", "", a, ""]
    md = ROOT / "docs" / "viva_questions_answers.md"
    md.write_text("\n".join(lines), encoding="utf-8")
    try:
        subprocess.run(["pandoc", str(md), "-o", str(md.with_suffix(".docx"))], check=True)
    except Exception as exc:  # pandoc optional
        print("pandoc conversion skipped:", exc)
    print("wrote", md, f"({len(QA)} questions)")


if __name__ == "__main__":
    main()
