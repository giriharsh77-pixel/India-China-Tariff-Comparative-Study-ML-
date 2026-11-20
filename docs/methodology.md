# Methodology

## 1. Decision problem

* **Organisation:** an Indian export-promotion body (e.g. an export-promotion council or industry
  association) with limited market-research, business-development and trade-promotion capacity.
* **Opportunity:** destination market × HS 6-digit product (e.g. *United States × 850440 static
  converters*).
* **Universe:** 10 destination markets × 200 HS6 products = 2,000 possible pairs per year. A pair is
  a *candidate* in decision year *t* if, using data observed at *t* only: India already exports at
  least US$1m of the product to the market, the market imports at least US$20m of it, three years
  of history exist and both tariffs are available. This is an *expansion* decision (where to push
  harder), not green-field market entry; pairs with zero/negligible Indian exports are not credible
  short-term prospects for a promotion budget and their share change is mechanically bounded at 0.
* **Constraint:** K = 10 opportunities per year (sensitivity: K = 5, 20, 50).
* **Objective:** choose the opportunities with the largest *next-year gain in India's share of the
  destination market's imports* of that product.

## 2. Product universe (fixed ex ante)

1. HS6 codes that exist in HS2012, HS2017 and HS2022 and are linked to themselves in both official
   UNSD correlation tables; codes whose own link is n:n are excluded. `strict_1to1` marks codes with
   unchanged scope.
2. HS chapters 25–96, excluding 27 (mineral fuels), 71 (gems/precious metals — price-driven and
   dominated by diamond re-exports), 93 (arms) and 97–99.
3. Both India and China exported ≥ US$50m of the product to the world in **2014** (reporter data).
4. The 200 largest by India's 2014 exports.

Only 2014 data are used, before every decision year whose outcome is evaluated, so the universe
cannot be tuned to future winners.

## 3. Tariff measurement

Tariffs are *imposed by the importing market* on goods *originating in* India or China.

`applied_tariff(origin) = TRAINS country-specific preferential rate for that origin if reported,
else the MFN rate.` The same rule is applied to both origins, so the comparison is always
like-for-like (preferential-vs-preferential, MFN-vs-MFN or the true mixed case where only one
origin enjoys a preference). Rates are simple averages of the national tariff lines in each HS6.

`tariff_adv = tariff faced by China − tariff faced by India` (positive = India advantage).

Gaps: when TRAINS reports no India/China preferential series at all in a market-year (a data
loading gap, e.g. 2022–2023), the last observed origin-specific preferential rate is carried
forward; years after the last TRAINS year carry forward MFN and applied rates. Carried values are
flagged (`tariff_imputed`). Years before TRAINS first reports a market's preferences are treated
as unknown for the *change* features (`d1/d3_tariff_adv` set to missing).

## 4. Features (all dated ≤ t)

| Group | Features |
|---|---|
| Tariffs | tariff on India, tariff on China, tariff advantage, MFN, 1- and 3-year change in advantage, preference flags |
| India trade | log imports from India, 1y and 3y log growth, India share, 1y and 3y share change, growth volatility, mirror RCA (market and 10-market basket) |
| China trade | log imports from China, 1y and 3y growth, China share, 1y and 3y share change, China mirror RCA |
| Market | log market size, 1y and 3y import growth |
| Macro (WDI) | log GDP, GDP growth, inflation, exchange-rate change |
| Identifiers | market and HS section as low-cardinality categoricals (no HS6 id, to avoid memorising products) |

Growth uses `ln(X_t + c) − ln(X_{t−k} + c)` with c = US$100,000, which handles zeros and damps
explosive growth rates on tiny bases. Mirror RCA = (India's share of the market's imports of the
product) / (India's share of the market's total imports), reported as ln(1 + RCA).

## 5. Outcomes (t+1, never used as inputs)

* **Primary:** `y_d_share_pp = share_{t+1} − share_t` (percentage points), with
  `share = imports from India / total imports of the product`, both importer-reported.
  Using a *share* removes common price movements (commodity prices, exchange rates and demand shocks
  that hit all suppliers of the same product in the same market).
* **Secondary:** next-year log export growth `ln(X_{t+1}+c) − ln(X_t+c)`.
* **Success label (pre-specified):** share rises (Δshare > 0).

## 6. Approaches

1. **Historical export momentum (baseline):** rank by India's annualised 3-year export growth to the
   market. No fitted parameters.
2. **ML ranking:** a regressor predicts Δshare; candidates are ranked by prediction. Families:
   HistGradientBoosting and RandomForest, small grids. Target winsorised at training-fold 1st/99th
   percentiles. Selection metric: NDCG@20 averaged over validation decision years 2018–2020
   (rolling origin, each trained only on earlier years). Test years are never used for selection.

## 7. Evaluation

Rolling-origin backtest over decision years 2021–2024 (outcomes 2022–2025). For decision year T the
model is retrained on decision years 2015…T−1, whose outcomes (≤ T) were observable when deciding
at T. Both approaches rank the identical candidate set with the same K. Metrics: Precision@K,
top-decile precision, mean/median realised Δshare of the picks, mean realised export growth,
NDCG@K (relevance = max(Δshare, 0)), overlap with the true top-K, Spearman correlation over the
whole universe, ranking stability (Jaccard of consecutive top-K). Uncertainty: bootstrap CI of the
mean Δshare over the 40 pooled picks.

## 8. Robustness

K ∈ {5, 10, 20, 50}; per-category and per-market performance; leave-one-market-out; strict 1:1 HS
codes only; excluding the 2025 outcome year (US tariff shock); concentration of the shortlist; an
ML model *without tariff features* (tariff ablation); the other ML family; an alternative
share-momentum baseline.

## 9. Trade diversion

Descriptive comparisons of next-year Δshare by tariff-advantage level and change, and OLS with
market×year and product fixed effects, standard errors clustered by market-product pair. Results
are associations, not causal effects.

## 10. Simulation

The final model (trained on decision years 2015–2024) scores the 2025 candidates under perturbed
tariff/demand inputs. Outputs show the model's sensitivity, not causal forecasts.
