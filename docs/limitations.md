# Limitations and threats to validity

## Data and measurement
1. **US Section 301 and 2025 US tariffs on China are not measured.** TRAINS records only the US
   MFN schedule, so the measured India–China tariff advantage in the US is zero although Chinese
   goods faced additional 7.5–25% duties on most lists from 2018–19 (and very different 2025
   duties). The US key case of trade diversion is therefore *not* captured by the tariff features.
2. **Unilateral GSP preferences are excluded** for both origins (EU/UK GSP, Canada GPT, US GSP
   for India until June 2019) because TRAINS stores them as beneficiary groups that cannot be
   resolved via the public API. India's advantage in the EU, UK and Canada is understated.
3. **2022–2025 preferential schedules are carried forward** from the last TRAINS year (India–Australia
   ECTA, India–UAE CEPA and RCEP are not captured). The share of candidate rows with carried tariff
   values is reported in `outputs/metrics/qc_report.csv`.
4. **Trade remedies and non-tariff barriers** (anti-dumping, SPS/TBT, quotas, rules of origin,
   preference utilisation) are not included; applied preferential rates assume full utilisation.
5. **Simple-average HS6 tariffs** ignore which national tariff lines are actually traded and
   exclude non-ad-valorem lines.
6. **HS revisions:** 71 of the 200 products kept their code but transferred part of their scope in
   HS2017/HS2022 (flagged; robustness check on strict 1:1 codes). Shares are less affected than
   levels because numerator and denominator change together.
7. **Importer-reported data** have valuation (CIF), timing, confidentiality and re-export issues
   (e.g. trans-shipment through third countries), and the latest year may be revised.

## Modelling and evaluation
8. **Selection bias in the universe:** only products in which both countries were sizeable in 2014
   and pairs where India already sells ≥ US$1m are considered; results do not speak to green-field
   market entry or to products India did not export in 2014.
9. **Few test years.** Four held-out decision years × K = 10 = 40 picks per approach; differences
   are reported with bootstrap intervals and per-year results, and should be read as indicative.
10. **Regime shifts:** COVID-19 (2020–21), the 2022 commodity spike, and the 2025 US tariff shock
    change the data-generating process; a model trained on earlier years may not transfer.
11. **Share changes are noisy and mean-reverting**, especially in small markets; the objective
    rewards absolute pp gains, which favours pairs where India already has a meaningful share.
12. **Feature importance is predictive, not causal.**

## Causal interpretation
13. **No causal identification.** Preferences are negotiated, phased in and often coincide with
    products where trade was already growing; geopolitical shifts (China+1 sourcing, sanctions,
    supply-chain diversification), exchange rates and Indian industrial policy (e.g. PLI schemes)
    move shares at the same time. The trade-diversion analysis reports associations only.
14. **The simulation is a sensitivity analysis of the model.** Tariff changes in the historical
    data were rare and concentrated in a few markets, so the model's response to hypothetical
    tariffs extrapolates beyond the observed variation and must not be read as a forecast.
