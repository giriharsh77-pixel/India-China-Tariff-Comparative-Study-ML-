# Speaking script — 12-minute presentation + 6-minute Q&A

Suggested split for a team of three: Speaker 1 slides 1–3, Speaker 2 slides 4–6, Speaker 3 slides 7–10. Timings in brackets sum to 12:00. Appendix slides are for questions only.

## Slide 1 — Title and motivation

(~45 s) Open with the question. India and China compete in the same product markets, but the importing country can charge them different tariffs — through free-trade agreements, preferences or extra duties on China. Our project asks whether that tariff gap, combined with demand and India's competitiveness, helps an export-promotion organisation choose where to spend a limited budget. We built the full pipeline on real public data and evaluated it against a simple baseline on held-out years.

## Slide 2 — Business decision

(~75 s) The organisation is an export-promotion body. Each opportunity is one destination market and one HS 6-digit product. We study 10 markets and 200 products — 2,000 pairs a year. After requiring that India already sells at least a million dollars and the market is at least 20 million, about 1164 candidates remain each year. The constraint is K = 10: a realistic number of deep-dives for a small team. The objective is the next-year gain in India's import-market share. In a typical year 54% of candidates gain share — that is what random selection would achieve.

## Slide 3 — Why tariffs matter

(~75 s) A common confusion: India and China do not tax their own exports — the importing market sets the duty. So for each market and product we compare the duty on Indian-origin goods with the duty on Chinese-origin goods, both from UNCTAD TRAINS via WITS, using the same rule for both. The chart shows where India has the edge — Japan and Korea, thanks to CEPAs — and where China has it — Australia, Indonesia and Malaysia through its FTAs. In the US, EU, UK, Canada and Mexico the measured gap is zero, and an honest caveat: TRAINS does not include the US Section 301 duties on China, so the US gap is understated.

## Slide 4 — Dataset

(~75 s) All data are public and every API response is cached in the submission. Comtrade gives importer-reported imports from India, China and the world for 200 HS6 products in 10 markets from 2012 to 2025. TRAINS gives the tariffs. The World Bank gives macro controls. We kept only HS codes that stay continuous across the 2012, 2017 and 2022 HS revisions, and fixed the product list using 2014 data only, so we cannot have picked products that later became winners. The final dataset has 12,802 candidate rows. TRAINS has not yet loaded preferences for 2022 onwards, so 30% of rows carry a forward-filled tariff; these are flagged.

## Slide 5 — Methodology

(~90 s) For a decision in year T we only use information up to T. The model is trained on earlier decision years whose next-year outcomes were already known by T, scores all candidates in T, and is judged on what actually happened in T+1. Years 2018–2020 were used only to choose the model and its hyper-parameters; 2021–2024 are pure test decisions. The target is the change in India's share of the market's imports — a share removes price and exchange-rate effects common to all suppliers. Features cover tariffs, India and China's trade momentum and comparative advantage, market demand and macro conditions.

## Slide 6 — Two prospect-selection approaches

(~60 s) The baseline is what many export bodies do informally: back the product-markets where Indian exports have grown fastest over the last three years. It needs no model. The ML approach predicts the next-year share change from 33 decision-time features and ranks by the prediction. We compared gradient boosting and random forests on validation years only; random forest won and was frozen before touching the test years.

## Slide 7 — Actual top-K shortlists

(~90 s) Here are the actual shortlists for the 2024 decision, scored against what happened in 2025. Only 0 opportunities appear in both lists. In this year 5 of the baseline's picks and 3 of the ML picks gained share. The baseline is, by construction, drawn to momentum: in its picks India's share had risen +13.6 points over three years, and such jumps tend to reverse. The ML model learned the mirror image — its picks are positions where India had lost -16.3 points and is likely to regain ground. In other words, the model's main skill is exploiting mean reversion, not tariffs. The trade-off: the baseline is easy to explain; the ML list is harder to explain but uses more information.

## Slide 8 — Evaluation

(~105 s) This is the key evidence. Averaged over 4 held-out decision years: Precision@10 is 33% for the baseline and 55% for ML, against 54% for a random pick. The average realised share change of the ten picks is -6.47 pp for the baseline and -0.93 pp for ML. NDCG@10 is 0.112 versus 0.123. The chart shows the result fold by fold — with only ten picks a year, results are noisy, so we also report bootstrap intervals. Two honest caveats: ML's hit rate is only 1% points above a random pick, and in the 2024-to-2025 fold — the year of the US tariff shock — ML did worse than the baseline; excluding that fold ML reaches 63%. And the model without tariff features does at least as well, so the tariff variables add no measurable predictive value.

## Slide 9 — Simulation and trade diversion

(~75 s) Is there trade diversion — does India gain share where China pays more? Descriptively we compare share changes by the level and change of tariff advantage; in a regression with market-year and product fixed effects, one extra point of advantage is associated with +0.029 pp next-year share change, p = 0.25. That is an association, not a causal effect: preferences are negotiated and coincide with other changes. The table shows how many of the model's top 10 change under illustrative tariff and demand shocks. How far the list moves depends on how much weight the model learned to put on tariffs — this is model sensitivity, not a forecast.

## Slide 10 — Conclusion

(~30 s) Three takeaways. First, simply backing the fastest growers is worse than random, because rapid growth mean-reverts; the ML ranking avoids that trap and delivered larger average share changes, but its advantage over a random pick is small and disappeared in the 2025 tariff-shock year. Second, measured tariff gaps between India and China are uncommon and removing them does not hurt the ranking — with the caveat that our public tariff data miss US Section 301 duties and GSP. Third, the practical use is as a screening tool that filters out mean-reverting momentum picks; the 2025 shortlist shown here is a starting point for expert vetting, not an automatic decision. Thank you — happy to take questions.

## Slide 11 — A1 Feature importance

Permutation importance: drop in rank correlation when one feature is shuffled on a held-out year. Tariff features in orange.

## Slide 12 — A2 Calibration

If the ranking works, realised share change should rise with the score decile. Grey = baseline deciles.

## Slide 13 — A3 Robustness

Robustness: results across K, strict HS codes, excluding the 2025 shock year, and dropping each market in turn.

## Slide 14 — A4 Tariff measurement

Use this slide for questions about tariff definitions, MFN vs preferential, data gaps and HS revisions.

## Slide 15 — A5 Live shortlists

Forward-looking shortlists using 2025 data, from the model trained on decision years up to 2024. 0 opportunities overlap.

## Slide 16 — A6 Regressions

Coefficients are associations. Identification would need e.g. an event study around agreement entry-into-force with matched control products.

