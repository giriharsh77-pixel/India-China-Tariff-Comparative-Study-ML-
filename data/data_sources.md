# Data sources

All data are public. No API key or registration was needed for any call used by the pipeline.
Retrieval date for every source: **20 November 2026**. Every raw API response is cached under
`data/raw/` (file names include an MD5 hash of the request), so the pipeline reproduces the
results offline (`python scripts/run_pipeline.py --offline`).

## 1. UN Comtrade — bilateral imports (primary trade source)

| Item | Detail |
|---|---|
| Publisher | United Nations Statistics Division |
| Dataset | UN Comtrade, annual, HS (as reported), goods |
| Access | Public preview API, no key: `https://comtradeapi.un.org/public/v1/preview/C/A/HS` |
| Portal | https://comtradeplus.un.org/ |
| Variables used | `primaryValue` (US$, CIF for imports) for flow = M, partner ∈ {India (699), China (156), World (0)}; `cmdCode` = HS6 and `TOTAL` |
| Reporters (importers) | USA 842, EU-27 97 (extra-EU trade only), UK 826, Japan 392, Korea 410, Australia 36, Canada 124, Indonesia 360, Malaysia 458, Mexico 484 |
| Products | 200 HS6 codes (see `data/processed/products.csv`) |
| Years | 2012–2025 |
| Also used | India's and China's reported world exports by HS6 in 2014 (flow = X) to fix the product universe ex ante |
| Limits | Preview endpoint: ≤500 records and one period per call; short-window rate limits (HTTP 429 and "Quota Exceeded" 403) — the downloader backs off and resumes from cache |
| Notes | Comtrade does not publish zero flows. Inside a market-year the reporter published, a missing India/China row is treated as zero trade; a market-year with no publication is missing (never zero). Importer-reported values are used throughout for consistency (shares and growth use the same reporter). |

Codes: India is **699** in Comtrade (not 356). The EU reporter 97 is the EU as a single customs
territory: a test query with Germany (276) as partner of reporter 97 returned no record, and EU
"World" imports of HS 620342 in 2022 (US$6.35bn) are far below the sum of member-state imports
including intra-EU trade (Germany alone US$3.29bn) — i.e. only extra-EU imports are recorded. No
EU member state is used as a separate market, so nothing is double-counted.

## 2. WITS / UNCTAD TRAINS — applied tariffs by origin

| Item | Detail |
|---|---|
| Publisher | World Bank WITS, data from UNCTAD TRAINS |
| Access | SDMX API, no key: `https://wits.worldbank.org/API/V1/SDMX/V21/datasource/TRN/reporter/{r}/partner/{000;356;156}/product/{hs6;...}/year/all/datatype/reported` |
| Portal | https://wits.worldbank.org/ |
| Variables used | Simple-average ad valorem rate of the national tariff lines in each HS6 (`OBS_VALUE`), tariff type (MFN / PREF), number of lines, number of non-ad-valorem lines |
| Partners | `000` = MFN schedule; `356` India; `156` China (country-specific preferential series) |
| Reporter codes | USA 840, EU 918, UK 826, Japan 392, Korea 410, Australia 036, Canada 124, Indonesia 360, Malaysia 458, Mexico 484 |
| Years available | MFN 2012–2023 (Mexico 2021 missing); country-specific preferences mostly 2012–2021 |
| Also used | `partner/all` probe per market-year (to detect years in which TRAINS loaded no preferential schedules) |
| Limits | URL-length limit (~20 products per call); `partner=all` with `year=all` is refused as "payload too large" |

**What the tariff measure includes:** MFN rates and reciprocal preferential rates (FTAs/CEPAs —
e.g. India–Japan CEPA, India–Korea CEPA, ASEAN–India FTA, China–Australia FTA, ASEAN–China FTA,
China–Korea FTA) which TRAINS reports at the country level.

**What it does not include (documented limitations):**
- US Section 301 duties on China (2018–) and the 2025 US "reciprocal"/IEEPA duties — not in TRAINS;
  the US Census duty data that would capture them now requires an API key, and USITC HTS footnotes
  no longer identify Section 301 coverage.
- Unilateral GSP preferences (EU, UK, Canada GPT, US GSP for India until June 2019): TRAINS stores
  them as beneficiary *groups* whose membership and product graduation cannot be resolved through
  the public API, so they are excluded for both origins.
- Anti-dumping / countervailing / safeguard duties and non-ad-valorem duties.
- Preferential schedules for 2022–2025 are not yet in TRAINS (India–Australia ECTA, India–UAE
  CEPA, RCEP are therefore not captured); the last observed origin-specific rate is carried
  forward and flagged (`tariff_imputed`).

## 3. World Bank World Development Indicators

| Item | Detail |
|---|---|
| Access | `https://api.worldbank.org/v2/country/{codes}/indicator/{id}?format=json` (no key) |
| Indicators | `NY.GDP.MKTP.CD` GDP (current US$); `NY.GDP.MKTP.KD.ZG` GDP growth (%); `FP.CPI.TOTL.ZG` CPI inflation (%); `PA.NUS.FCRF` official exchange rate (LCU per US$) |
| Coverage | 10 markets (EU aggregate `EUU`), 2010–2025 (latest years partly missing) |
| Notes | The EU aggregate has no single official exchange-rate series in WDI → `fx_change_pct` missing for the EU (handled natively by the gradient-boosting model / median-imputed for the random forest, fitted on training folds). |

## 4. UNSD HS correlation tables and Comtrade HS reference lists

| Item | Detail |
|---|---|
| Files | `HS2022toHS2017ConversionAndCorrelationTables.xlsx`, `HS2017toHS2012ConversionAndCorrelationTables.xlsx` |
| URL | https://unstats.un.org/unsd/classifications/Econ/tables/ |
| Use | Keep only HS6 codes that exist under HS2012, HS2017 and HS2022 and are linked to themselves in both tables; exclude codes whose self-link is n:n. `strict_1to1` flags codes with an identical scope (1:1); others kept their code with a partial scope transfer (robustness check uses strict codes only). |
| HS descriptions | `https://comtradeapi.un.org/files/v1/app/reference/H6.json` |

## Sources considered but not used

| Source | Reason |
|---|---|
| WTO Tariff & Trade Data (ttd.wto.org / api.wto.org) | API requires a subscription key; TRAINS via WITS provides the same applied-tariff concept without a key |
| US Census International Trade API (calculated duties by origin) | Now requires an API key (redirects to "Missing Key"); would have captured Section 301 duties for the US |
| ITC Market Access Map, CEPII MAcMap-HS6 | Registration required |
| WITS RCA indicators | Aggregated product groups only; RCA is computed from Comtrade instead (mirror RCA) |

## Redistribution

UN Comtrade, WITS and World Bank data may be used for research with attribution. The cached raw
responses are included for reproducibility; cite the original providers when reusing them.
