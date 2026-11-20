# Viva and defence preparation — questions and answers

Numbers are generated from `outputs/results_summary.json`, so they match the report and slides.

## Q1. Why is this a prospect-selection problem?

Because the organisation faces many more opportunities than it can pursue: 2,000 market–product pairs a year (about 1164 eligible candidates) but capacity for K = 10. The output is a ranked shortlist evaluated on the realised outcomes of the selected items, not a point forecast for every pair.

## Q2. Why did you select K = 10?

It reflects a small market-intelligence team running roughly one deep-dive per month plus a buffer. Because the choice is a business assumption, we also report K = 5, 20 and 50 (Appendix A3 / report Section 16); the ranking of the two approaches can be checked at each K.

## Q3. Why India as exporter and China as the competitor?

China is the largest supplier in most of the manufactured products India exports, so it is the natural benchmark; tariff asymmetries between the two (FTAs, preferences, US duties on China) are a frequently cited source of opportunity for Indian exporters under 'China+1' sourcing.

## Q4. How are tariffs measured?

From WITS/UNCTAD TRAINS: the simple average of the national ad valorem tariff lines within each HS6, imposed by the importing market. For each origin we use the origin-specific preferential series if TRAINS reports one, otherwise the MFN rate. Tariff advantage = tariff faced by China − tariff faced by India.

## Q5. What is the difference between MFN and applied tariffs?

MFN is the rate a WTO member charges all other members by default. The applied rate actually faced by an origin can be lower under a preferential agreement (FTA, CEPA, GSP) or higher with additional duties (anti-dumping, Section 301). We compare like with like: the same rule is applied to India and China, so we never set a preferential rate against an MFN rate unless that asymmetry is real (only one origin has a preference).

## Q6. Why HS 6-digit codes?

HS6 is the most detailed level harmonised internationally, so the same product can be matched across Comtrade and TRAINS and across countries. We only kept codes continuous across HS2012, HS2017 and HS2022 using the official UNSD correlation tables, and checked robustness on the 124 strictly 1:1 codes.

## Q7. Why use country–product pairs as observations?

That is the unit at which a promotion body acts (a trade fair, buyer-seller meet or market study is for a product in a market) and the level at which tariffs and market shares are defined.

## Q8. Why predict future market performance rather than tariffs?

The business objective is export success; tariffs are an input. Predicting tariffs would not tell the organisation where Indian exporters will gain.

## Q9. Why use market-share changes?

A share compares India with all other suppliers of the same product in the same market and year, so price changes, exchange-rate swings and demand shocks common to all suppliers cancel out. Export growth is reported as a secondary outcome.

## Q10. Why is historical export growth a meaningful baseline?

It is what an organisation without a model would do — back what is already growing — and it has no fitted parameters, so it cannot leak information. Beating it shows the model adds value beyond momentum.

## Q11. Why did you select this particular ML model?

We compared gradient boosting and random forests over small grids and picked the configuration with the best mean NDCG@20 on validation decision years 2018–2020 only. The winner was RF with {'n_estimators': 400, 'max_depth': 8, 'min_samples_leaf': 20, 'max_features': 0.5}. Tree ensembles handle non-linear interactions, mixed scales and (for HGB) missing values natively; we avoided more complex models because the sample is modest.

## Q12. What is Precision@K?

The share of the K selected opportunities that are successes. Success was pre-specified as India's import share rising in the next year. A random pick achieves about 54%; our baseline 33% and ML 55% at K = 10.

## Q13. Why not use a random train/test split?

Trade data are serially correlated and the decision is made in time. A random split would train on later years and test on earlier ones, leaking information about shocks such as COVID-19. We use rolling-origin backtesting: for decision year T the model is trained only on decision years before T.

## Q14. What is data leakage?

Any use, during training or feature construction, of information that would not have been available at decision time — e.g. future outcomes, future tariffs, preprocessing fitted on the full sample, or choosing the model on the test years.

## Q15. How did you avoid look-ahead bias?

(1) The product universe was fixed with 2014 data; (2) all features are dated ≤ t and outcomes (y_*) are separate columns never passed to models — checked by a unit test; (3) each fold trains on decision years ≤ T−1 whose outcomes are known at T; (4) winsorisation and imputation are fitted on training rows; (5) model selection used validation years 2018–2020, disjoint from test years; (6) candidate eligibility uses only data at t; (7) tariff gaps are filled only forward in time.

## Q16. What is trade diversion?

Viner's term for a preferential tariff shifting imports from a more efficient non-member supplier to a member. Here: if a market charges China more than India, buyers may switch some sourcing to India.

## Q17. Can you conclude that tariffs cause export growth?

No. Our fixed-effects regression gives +0.029 pp per pp of advantage (p = 0.25) and +0.086 pp per pp change in advantage (p = 0.48). Even a significant coefficient would be an association: preferences are negotiated for products where trade is already expanding and coincide with other shocks. A causal design would need an event study around agreement entry-into-force with matched controls, or structural gravity.

## Q18. How reliable is your simulation?

It is a sensitivity analysis of the trained model, labelled as such. It shows how the model's ranking responds to changed inputs, not what would happen to trade. Tariff changes in the training data were rare and concentrated in a few markets, so large hypothetical shocks extrapolate beyond the observed variation.

## Q19. What happens if the ML model performs worse than the baseline?

In our backtest the ML model outperformed the baseline on Precision@10 (55% vs 33%), but it did worse than the baseline in one fold: decisions made in 2024 and judged on 2025, the year of the US tariff shock. Its overall hit rate is also close to a random pick (54%). We report this as it is: the model is a screen that avoids the mean-reversion trap of momentum, not a reliable predictor of winners; under a regime shift its learned patterns can fail, and the transparent baseline would be preferred if it were consistently better.

## Q20. What are the limitations of the project?

US Section 301 and 2025 duties on China are not in TRAINS (US advantage measured as zero); unilateral GSP is excluded; preferences after 2021 are carried forward (30% of rows); non-tariff barriers and rules of origin are not modelled; only 4 test years; selection of products with large 2014 exports; importer data revisions and trans-shipment.

## Q21. Did tariff features help the model?

Ablation: dropping all tariff features changes Precision@10 from 55% to 60% and mean share change from -0.93 to +0.14 pp. The most important features were d3_share_ind, rca_ind_basket, section_code, log_gdp, rca_ind_mkt; the highest-ranked tariff feature is at position 11 of the permutation-importance list.

## Q22. How certain are the performance differences?

With 10 picks per year over 4 years, uncertainty is substantial. Bootstrap 95% intervals of the mean share change of the pooled picks: ML -3.95 to +1.71 pp; baseline -12.28 to -1.09 pp. We also show results per fold and for K = 5–50.

## Q23. Why treat the EU as one market?

The EU applies a single common external tariff. Using member states would double-count the same tariff and include intra-EU trade; Comtrade reporter 97 gives extra-EU imports of the EU as a single customs territory.

## Q24. How did you handle zero exports and extreme growth rates?

Comtrade omits zero flows, so within a reported market-year a missing India row is a true zero. Growth uses logs with a US$100,000 smoothing constant; candidates must have at least US$1m of Indian exports, so tiny bases do not dominate; the training target is winsorised at fold-specific 1st/99th percentiles; no observation is dropped.

## Q25. Why exclude opportunities where India currently exports nothing?

They are green-field entry decisions with different costs and a mechanically non-negative share change, which would bias Precision@K upward for any rule that picks them. The eligibility rule uses only decision-time data and is applied identically to both approaches.
