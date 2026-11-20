# Data dictionary

File: `data/processed/analytical_dataset.csv` (also `.parquet`).
**One row = destination market × HS6 product × decision year t** (candidates only).

* Rows: 12,802  |  markets: 10  |  products: 195  |  decision years: 2015–2025
* Rows with observed t+1 outcome: 11,600 (decision years 2015–2024)
* Candidate rule (decision-time data only): imports from India ≥ US$1m, market imports ≥ US$20m, 3 years of history and both tariffs available.

| Column | Role | Definition | Missing (%) |
|---|---|---|---:|
| `iso3` | id | Destination market code (EUN = European Union as one customs territory) | 0.0 |
| `market` | id | Destination market name | 0.0 |
| `hs6` | id | HS 6-digit product code (continuous across HS2012/2017/2022) | 0.0 |
| `short_desc` | id | Product description (HS2022 nomenclature, truncated) | 0.0 |
| `section` | id | HS section (Roman numeral) | 0.0 |
| `category` | id | Product category (HS section name) | 0.0 |
| `year` | id | Decision year t (all features dated <= t) | 0.0 |
| `strict_1to1` | flag | 1 if the HS6 scope is identical across HS2012/2017/2022 (1:1 correlation) | 0.0 |
| `imp_ind` | trade | Market's imports from India at t, US$ (importer-reported, Comtrade) | 0.0 |
| `imp_chn` | trade | Market's imports from China at t, US$ | 0.0 |
| `imp_wld` | trade | Market's total imports of the product at t, US$ | 0.0 |
| `tariff_imputed` | flag | 1 if any tariff value at t was carried forward (TRAINS gap) | 0.0 |
| `flag_partner_gt_world` | flag | 1 if India+China imports exceed World (reporting inconsistency) | 0.0 |
| `tariff_ind` | tariff | Applied ad valorem tariff faced by Indian-origin goods at t (%; preferential if TRAINS reports one for India, else MFN) | 0.0 |
| `tariff_chn` | tariff | Applied ad valorem tariff faced by Chinese-origin goods at t (%; same rule) | 0.0 |
| `tariff_adv` | tariff | Tariff advantage = tariff_chn - tariff_ind (pp; positive = India advantage) | 0.0 |
| `mfn` | tariff | MFN applied rate at t (%) | 0.0 |
| `d1_tariff_adv` | tariff | 1-year change in tariff advantage (pp); missing if preference status unknown at t-1 | 1.5 |
| `d3_tariff_adv` | tariff | 3-year change in tariff advantage (pp) | 5.6 |
| `has_pref_ind` | tariff | 1 if India's applied rate is below MFN | 0.0 |
| `has_pref_chn` | tariff | 1 if China's applied rate is below MFN | 0.0 |
| `share_ind` | trade | India's share of the market's imports of the product at t (%) | 0.0 |
| `share_chn` | trade | China's share of the market's imports of the product at t (%) | 0.0 |
| `d1_share_ind` | trade | 1-year change in India share (pp) | 0.0 |
| `d3_share_ind` | trade | 3-year change in India share (pp) | 0.0 |
| `d1_share_chn` | trade | 1-year change in China share (pp) | 0.0 |
| `d3_share_chn` | trade | 3-year change in China share (pp) | 0.0 |
| `log_imp_ind` | trade | ln(1 + imports from India) | 0.0 |
| `log_imp_chn` | trade | ln(1 + imports from China) | 0.0 |
| `log_imp_wld` | market | ln(1 + total imports) = market size | 0.0 |
| `g1_ind` | trade | 1-year log growth of imports from India, ln(X_t+c)-ln(X_{t-1}+c), c=US$100k | 0.0 |
| `g3_ind` | trade | Annualised 3-year log growth of imports from India (= baseline score) | 0.0 |
| `g1_chn` | trade | 1-year log growth of imports from China | 0.0 |
| `g3_chn` | trade | Annualised 3-year log growth of imports from China | 0.0 |
| `g1_wld` | market | 1-year log growth of total imports (import-market growth) | 0.0 |
| `g3_wld` | market | Annualised 3-year log growth of total imports | 0.0 |
| `rca_ind_mkt` | trade | ln(1+RCA): India's share in this product / India's share in all the market's imports | 0.0 |
| `rca_chn_mkt` | trade | ln(1+RCA) for China, same definition | 0.0 |
| `rca_ind_basket` | trade | ln(1+RCA) for India over the 10-market import basket | 0.0 |
| `ind_vol_3y` | trade | Std. dev. of India's 1-year growth over the last 3 years | 0.0 |
| `log_gdp` | macro | ln GDP, current US$ (WDI) | 0.0 |
| `gdp_growth_pct` | macro | Real GDP growth, % (WDI) | 0.0 |
| `inflation_pct` | macro | CPI inflation, % (WDI) | 1.2 |
| `fx_change_pct` | macro | % change in official LCU per US$ (WDI); missing for EU aggregate | 15.6 |
| `market_code` | id/feature | Integer code of market (categorical feature) | 0.0 |
| `section_code` | id/feature | Integer code of HS section (categorical feature) | 0.0 |
| `share_ind_next` | OUTCOME | India share at t+1 (%) - never a feature | 9.4 |
| `imp_ind_next` | OUTCOME | Imports from India at t+1, US$ - never a feature | 9.4 |
| `y_d_share_pp` | OUTCOME | PRIMARY: share_ind(t+1) - share_ind(t), pp | 9.4 |
| `y_export_growth_log` | OUTCOME | SECONDARY: ln(X_{t+1}+c) - ln(X_t+c) | 9.4 |
| `y_export_growth_pct` | OUTCOME | X_{t+1}/X_t - 1, % (reported only; heavy-tailed) | 9.4 |
| `y_success` | OUTCOME | 1 if y_d_share_pp > 0 (pre-specified success label) | 9.4 |
| `eligible` | flag | Candidate eligibility at t (always 1 in this file) | 0.0 |
| `has_outcome` | flag | 1 if t+1 outcome is observed (0 for the live 2025 decision year) | 0.0 |

Other processed files:

* `products.csv` — the 200-product universe with 2014 India/China world exports and HS-revision flags
* `trade_panel.csv` — full market × product × year grid of imports (2012–2025), incl. non-candidates
* `tariff_panel.csv` — full grid of tariffs with observed/carried flags
* `totals_panel.csv`, `macro_panel.csv` — all-product imports and WDI indicators by market-year
* `hs6_stable_codes.csv` — HS6 continuity table derived from UNSD correlation tables
* `full_panel.parquet` — merged grid with all derived features (used for descriptive figures)
