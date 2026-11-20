"""Write data/data_dictionary.md from the final analytical dataset (so the
dictionary always matches the columns and coverage actually shipped)."""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

DESC = {
    "iso3": ("id", "Destination market code (EUN = European Union as one customs territory)"),
    "market": ("id", "Destination market name"),
    "hs6": ("id", "HS 6-digit product code (continuous across HS2012/2017/2022)"),
    "short_desc": ("id", "Product description (HS2022 nomenclature, truncated)"),
    "section": ("id", "HS section (Roman numeral)"),
    "category": ("id", "Product category (HS section name)"),
    "year": ("id", "Decision year t (all features dated <= t)"),
    "strict_1to1": ("flag", "1 if the HS6 scope is identical across HS2012/2017/2022 (1:1 correlation)"),
    "imp_ind": ("trade", "Market's imports from India at t, US$ (importer-reported, Comtrade)"),
    "imp_chn": ("trade", "Market's imports from China at t, US$"),
    "imp_wld": ("trade", "Market's total imports of the product at t, US$"),
    "tariff_imputed": ("flag", "1 if any tariff value at t was carried forward (TRAINS gap)"),
    "flag_partner_gt_world": ("flag", "1 if India+China imports exceed World (reporting inconsistency)"),
    "tariff_ind": ("tariff", "Applied ad valorem tariff faced by Indian-origin goods at t (%; preferential if TRAINS reports one for India, else MFN)"),
    "tariff_chn": ("tariff", "Applied ad valorem tariff faced by Chinese-origin goods at t (%; same rule)"),
    "tariff_adv": ("tariff", "Tariff advantage = tariff_chn - tariff_ind (pp; positive = India advantage)"),
    "mfn": ("tariff", "MFN applied rate at t (%)"),
    "d1_tariff_adv": ("tariff", "1-year change in tariff advantage (pp); missing if preference status unknown at t-1"),
    "d3_tariff_adv": ("tariff", "3-year change in tariff advantage (pp)"),
    "has_pref_ind": ("tariff", "1 if India's applied rate is below MFN"),
    "has_pref_chn": ("tariff", "1 if China's applied rate is below MFN"),
    "share_ind": ("trade", "India's share of the market's imports of the product at t (%)"),
    "share_chn": ("trade", "China's share of the market's imports of the product at t (%)"),
    "d1_share_ind": ("trade", "1-year change in India share (pp)"),
    "d3_share_ind": ("trade", "3-year change in India share (pp)"),
    "d1_share_chn": ("trade", "1-year change in China share (pp)"),
    "d3_share_chn": ("trade", "3-year change in China share (pp)"),
    "log_imp_ind": ("trade", "ln(1 + imports from India)"),
    "log_imp_chn": ("trade", "ln(1 + imports from China)"),
    "log_imp_wld": ("market", "ln(1 + total imports) = market size"),
    "g1_ind": ("trade", "1-year log growth of imports from India, ln(X_t+c)-ln(X_{t-1}+c), c=US$100k"),
    "g3_ind": ("trade", "Annualised 3-year log growth of imports from India (= baseline score)"),
    "g1_chn": ("trade", "1-year log growth of imports from China"),
    "g3_chn": ("trade", "Annualised 3-year log growth of imports from China"),
    "g1_wld": ("market", "1-year log growth of total imports (import-market growth)"),
    "g3_wld": ("market", "Annualised 3-year log growth of total imports"),
    "rca_ind_mkt": ("trade", "ln(1+RCA): India's share in this product / India's share in all the market's imports"),
    "rca_chn_mkt": ("trade", "ln(1+RCA) for China, same definition"),
    "rca_ind_basket": ("trade", "ln(1+RCA) for India over the 10-market import basket"),
    "ind_vol_3y": ("trade", "Std. dev. of India's 1-year growth over the last 3 years"),
    "log_gdp": ("macro", "ln GDP, current US$ (WDI)"),
    "gdp_growth_pct": ("macro", "Real GDP growth, % (WDI)"),
    "inflation_pct": ("macro", "CPI inflation, % (WDI)"),
    "fx_change_pct": ("macro", "% change in official LCU per US$ (WDI); missing for EU aggregate"),
    "market_code": ("id/feature", "Integer code of market (categorical feature)"),
    "section_code": ("id/feature", "Integer code of HS section (categorical feature)"),
    "share_ind_next": ("OUTCOME", "India share at t+1 (%) - never a feature"),
    "imp_ind_next": ("OUTCOME", "Imports from India at t+1, US$ - never a feature"),
    "y_d_share_pp": ("OUTCOME", "PRIMARY: share_ind(t+1) - share_ind(t), pp"),
    "y_export_growth_log": ("OUTCOME", "SECONDARY: ln(X_{t+1}+c) - ln(X_t+c)"),
    "y_export_growth_pct": ("OUTCOME", "X_{t+1}/X_t - 1, % (reported only; heavy-tailed)"),
    "y_success": ("OUTCOME", "1 if y_d_share_pp > 0 (pre-specified success label)"),
    "eligible": ("flag", "Candidate eligibility at t (always 1 in this file)"),
    "has_outcome": ("flag", "1 if t+1 outcome is observed (0 for the live 2025 decision year)"),
}


def main():
    d = pd.read_parquet(ROOT / "data/processed/analytical_dataset.parquet")
    lines = ["# Data dictionary", "",
             "File: `data/processed/analytical_dataset.csv` (also `.parquet`).",
             "**One row = destination market × HS6 product × decision year t** (candidates only).", "",
             f"* Rows: {len(d):,}  |  markets: {d.iso3.nunique()}  |  products: {d.hs6.nunique()}  |  "
             f"decision years: {d.year.min()}–{d.year.max()}",
             f"* Rows with observed t+1 outcome: {int(d.has_outcome.sum()):,} (decision years {d[d.has_outcome].year.min()}–{d[d.has_outcome].year.max()})",
             "* Candidate rule (decision-time data only): imports from India ≥ US$1m, market imports ≥ US$20m, "
             "3 years of history and both tariffs available.", "",
             "| Column | Role | Definition | Missing (%) |", "|---|---|---|---:|"]
    for c in d.columns:
        role, txt = DESC.get(c, ("", ""))
        lines.append(f"| `{c}` | {role} | {txt} | {d[c].isna().mean() * 100:.1f} |")
    lines += ["", "Other processed files:", "",
              "* `products.csv` — the 200-product universe with 2014 India/China world exports and HS-revision flags",
              "* `trade_panel.csv` — full market × product × year grid of imports (2012–2025), incl. non-candidates",
              "* `tariff_panel.csv` — full grid of tariffs with observed/carried flags",
              "* `totals_panel.csv`, `macro_panel.csv` — all-product imports and WDI indicators by market-year",
              "* `hs6_stable_codes.csv` — HS6 continuity table derived from UNSD correlation tables",
              "* `full_panel.parquet` — merged grid with all derived features (used for descriptive figures)"]
    (ROOT / "data/data_dictionary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("wrote data/data_dictionary.md")


if __name__ == "__main__":
    main()
