// Builds presentation/presentation.pptx from outputs/results_summary.json and outputs/figures.
// Usage:  (cd presentation && npm install pptxgenjs && node build_deck.js)
// Every number on the slides is read from the results JSON produced by the pipeline.
const path = require("path");
const fs = require("fs");
const pptxgen = require(process.env.PPTXGENJS || "pptxgenjs");

const ROOT = path.resolve(__dirname, "..");
const R = JSON.parse(fs.readFileSync(path.join(ROOT, "outputs/results_summary.json"), "utf8"));
const FIG = (n) => path.join(ROOT, "outputs/figures", n + ".png");

// ---------------------------------------------------------------- theme
const NAVY = "1B2A41", SAFFRON = "EB6834", BLUE = "2A78D6", GREY = "8A8984", INK = "1F2328", MUTED = "5B6270",
  LIGHT = "F3F5F8", WHITE = "FFFFFF", RULE = "D9DDE3";
const HEAD = "Cambria", BODY = "Calibri";

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.title = "Tariff Advantage and Export Market Selection";
pres.author = "MLBA Prospect Selection team";
pres.theme = { headFontFace: HEAD, bodyFontFace: BODY };

const W = 13.333, H = 7.5, MX = 0.6;
pres.defineSlideMaster({
  title: "DARK", background: { color: NAVY },
  objects: [],
});
pres.defineSlideMaster({
  title: "CONTENT", background: { color: WHITE },
  objects: [
    { text: { text: "India–China tariff advantage · Prospect Selection · MLBA, Plaksha MS-AI 2026",
      options: { x: MX, y: H - 0.42, w: 9, h: 0.3, fontFace: BODY, fontSize: 9, color: MUTED, margin: 0 } } },
  ],
  slideNumber: { x: W - 1.0, y: H - 0.42, w: 0.5, h: 0.3, fontFace: BODY, fontSize: 9, color: MUTED, align: "right" },
});

// ---------------------------------------------------------------- helpers
const NOTES = [];
function note(slide, text) { slide.addNotes(text); NOTES.push(text); }
const f1 = (x, d = 1) => (x === null || x === undefined || Number.isNaN(x) ? "–" : Number(x).toFixed(d));
const pct = (x, d = 0) => (x === null || x === undefined ? "–" : (100 * x).toFixed(d) + "%");
const sgn = (x, d = 2) => (x >= 0 ? "+" : "") + Number(x).toFixed(d);
const S = (m, k = R.k) => R.summary.find((r) => r.method === m && r.k === k);
const BL = "Historical momentum (baseline)", MLM = "ML ranking", NOT = "ML without tariff features";
const U = R.universe.find((r) => r.k === R.k);

function title(slide, t, sub) {
  slide.addText(t, { x: MX, y: 0.35, w: W - 2 * MX, h: 0.75, fontFace: HEAD, fontSize: 30, bold: true, color: INK, margin: 0, isTextBox: true });
  if (sub) slide.addText(sub, { x: MX, y: 1.1, w: W - 2 * MX, h: 0.45, fontFace: BODY, fontSize: 15, color: MUTED, margin: 0, isTextBox: true });
}
function img(slide, name, x, y, maxW, maxH) {
  const [pw, ph] = R.fig_sizes[name];
  let w = maxW, h = (maxW * ph) / pw;
  if (h > maxH) { h = maxH; w = (maxH * pw) / ph; }
  slide.addImage({ path: FIG(name), x: x + (maxW - w) / 2, y, w, h, altText: name.replace(/_/g, " ") });
}
function card(slide, x, y, w, h, head, body, accent) {
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, fill: { color: LIGHT }, line: { color: LIGHT }, rectRadius: 0.08 });
  slide.addText(head, { x: x + 0.25, y: y + 0.15, w: w - 0.5, h: 0.45, fontFace: HEAD, fontSize: 18, bold: true, color: accent || INK, margin: 0, isTextBox: true });
  slide.addText(body, { x: x + 0.25, y: y + 0.65, w: w - 0.5, h: h - 0.8, fontFace: BODY, fontSize: 14, color: INK, valign: "top", margin: 0, paraSpaceAfter: 6, isTextBox: true });
}
function stat(slide, x, y, w, big, label, color) {
  slide.addText(big, { x, y, w, h: 0.85, fontFace: HEAD, fontSize: 40, bold: true, color: color || INK, margin: 0, isTextBox: true });
  slide.addText(label, { x, y: y + 0.85, w, h: 0.6, fontFace: BODY, fontSize: 13, color: MUTED, margin: 0, valign: "top", isTextBox: true });
}
function bullets(items, size = 15) {
  return items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1, fontSize: size, color: INK } }));
}
const short = (m) => m.replace("United States", "USA").replace("European Union", "EU").replace("United Kingdom", "UK").replace("South Korea", "Korea");

const ds = R.dataset, bl = S(BL), ml = S(MLM), nt = S(NOT);
const mlBetterP = ml.precision_at_k > bl.precision_at_k, mlBetterM = ml.mean_d_share_pp_at_k > bl.mean_d_share_pp_at_k;
const T = R.test_year_last, F = R.forward_year;
const nTest = R.folds.filter((f) => f.decision_year <= T).length;
const yrsTest = R.folds.filter((f) => f.decision_year <= T).map((f) => f.decision_year);
const candPerYear = Math.round(Object.values(ds.rows_per_year).reduce((a, b) => a + b, 0) / Object.keys(ds.rows_per_year).length);

// ================================================================ 1 Title
{
  const s = pres.addSlide({ masterName: "DARK" });
  s.addText("Tariff Advantage and Export Market Selection", { x: MX, y: 1.0, w: 12.0, h: 1.0, fit: "shrink", fontFace: HEAD, fontSize: 44, bold: true, color: WHITE, margin: 0, isTextBox: true });
  s.addText("A comparative India–China trade analysis using machine learning", { x: MX, y: 2.2, w: 11.5, h: 0.6, fontFace: HEAD, fontSize: 24, color: "CADCFC", margin: 0, isTextBox: true });
  s.addText("Indian and Chinese goods often face different tariffs in the same market. Can that gap — together with demand and competitiveness — tell an export-promotion body which 10 market–product opportunities to back?",
    { x: MX, y: 3.6, w: 10.5, h: 1.2, fontFace: BODY, fontSize: 18, color: WHITE, margin: 0, isTextBox: true });
  s.addShape(pres.shapes.OVAL, { x: MX, y: 5.35, w: 0.32, h: 0.32, fill: { color: SAFFRON }, line: { color: SAFFRON } });
  s.addText("India", { x: MX + 0.45, y: 5.3, w: 1.5, h: 0.42, fontSize: 15, color: WHITE, margin: 0, isTextBox: true });
  s.addShape(pres.shapes.OVAL, { x: MX + 1.8, y: 5.35, w: 0.32, h: 0.32, fill: { color: BLUE }, line: { color: BLUE } });
  s.addText("China (competitor benchmark)", { x: MX + 2.25, y: 5.3, w: 4, h: 0.42, fontSize: 15, color: WHITE, margin: 0, isTextBox: true });
  s.addText("Machine Learning for Business Analytics · Prospect Selection · Plaksha University MS-AI · Monsoon 2026",
    { x: MX, y: 6.6, w: 11, h: 0.4, fontSize: 12, color: "CADCFC", margin: 0, isTextBox: true });
  note(s, `(~45 s) Open with the question. India and China compete in the same product markets, but the importing country can charge them different tariffs — through free-trade agreements, preferences or extra duties on China. Our project asks whether that tariff gap, combined with demand and India's competitiveness, helps an export-promotion organisation choose where to spend a limited budget. We built the full pipeline on real public data and evaluated it against a simple baseline on held-out years.`);
}

// ================================================================ 2 Business decision
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  title(s, "The decision: which 10 market–product bets to back", "An Indian export-promotion body cannot support every opportunity");
  card(s, MX, 1.8, 6.2, 4.6, "Prospect-selection set-up",
    bullets([
      "Organisation: an Indian export-promotion council / industry association",
      "Opportunity: destination market × HS 6-digit product (e.g. USA × 850440 static converters)",
      "Constraint: research, B2B matchmaking and promotion budget for K = 10 opportunities a year",
      "Objective: next-year gain in India's share of that market's imports of that product",
      "Candidates: India already sells ≥ US$1m and the market imports ≥ US$20m (expansion, not green-field)",
    ], 14));
  stat(s, 7.3, 1.9, 2.6, "2,000", "possible pairs a year (10 markets × 200 HS6 products)", INK);
  stat(s, 10.1, 1.9, 2.6, `~${candPerYear}`, "eligible candidates per decision year", BLUE);
  stat(s, 7.3, 3.7, 2.6, "K = 10", "opportunities the organisation can pursue", SAFFRON);
  stat(s, 10.1, 3.7, 2.6, pct(U.universe_precision), "of candidates gain share in a typical year (random-pick hit rate)", MUTED);
  s.addText("Why K = 10: a realistic annual load for a small market-intelligence team (one deep-dive per month plus buffer). We report K = 5, 20 and 50 as sensitivity.",
    { x: 7.3, y: 5.55, w: 5.4, h: 0.85, fontSize: 13, color: MUTED, margin: 0, isTextBox: true });
  note(s, `(~75 s) The organisation is an export-promotion body. Each opportunity is one destination market and one HS 6-digit product. We study 10 markets and 200 products — 2,000 pairs a year. After requiring that India already sells at least a million dollars and the market is at least 20 million, about ${candPerYear} candidates remain each year. The constraint is K = 10: a realistic number of deep-dives for a small team. The objective is the next-year gain in India's import-market share. In a typical year ${pct(U.universe_precision)} of candidates gain share — that is what random selection would achieve.`);
}

// ================================================================ 3 Why tariffs matter
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  title(s, "Tariffs are set by the importer, and they can differ by origin", "We compare the duty the same market charges on Indian-origin vs Chinese-origin goods");
  card(s, MX, 1.8, 4.9, 2.1, "Tariff advantage (pp)", [
    { text: "= tariff faced by China − tariff faced by India", options: { bold: true, fontSize: 15, color: INK, breakLine: true } },
    { text: "> 0 India advantage   ·   = 0 equal   ·   < 0 China advantage", options: { fontSize: 13, color: MUTED } },
  ]);
  s.addText(bullets([
    "Same rule for both origins: the rate each origin actually faces — its preferential rate if the market grants one, otherwise MFN",
    "India gains in Japan and Korea (CEPAs); China gains in Australia, Indonesia, Malaysia (ChAFTA, ACFTA)",
    `Only ${pct(ds.share_nonzero_adv)} of candidate rows show any difference — tariffs are a narrow lever`,
    "Not captured: US Section 301 duties on China, unilateral GSP, anti-dumping",
  ], 14), { x: MX, y: 4.1, w: 4.9, h: 2.6, valign: "top", margin: 0, paraSpaceAfter: 6, isTextBox: true });
  img(s, "02_tariff_advantage_by_market", 5.75, 1.7, 7.0, 5.1);
  note(s, `(~75 s) A common confusion: India and China do not tax their own exports — the importing market sets the duty. So for each market and product we compare the duty on Indian-origin goods with the duty on Chinese-origin goods, both from UNCTAD TRAINS via WITS, using the same rule for both. The chart shows where India has the edge — Japan and Korea, thanks to CEPAs — and where China has it — Australia, Indonesia and Malaysia through its FTAs. In the US, EU, UK, Canada and Mexico the measured gap is zero, and an honest caveat: TRAINS does not include the US Section 301 duties on China, so the US gap is understated.`);
}

// ================================================================ 4 Dataset
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  title(s, "Dataset: real public data, one row per market × product × year", `${ds.n_rows.toLocaleString()} candidate observations, decision years ${ds.years[0]}–${ds.years[1]}`);
  const rows = [
    [{ text: "Source", options: { bold: true, color: WHITE, fill: { color: NAVY } } }, { text: "What we use", options: { bold: true, color: WHITE, fill: { color: NAVY } } }, { text: "Coverage", options: { bold: true, color: WHITE, fill: { color: NAVY } } }],
    ["UN Comtrade (public API)", "Importer-reported imports from India, China, World (US$)", "10 markets · 200 HS6 · 2012–2025"],
    ["WITS / UNCTAD TRAINS", "MFN and origin-specific preferential applied tariffs", "2012–2023 (gaps carried forward, flagged)"],
    ["World Bank WDI", "GDP, GDP growth, inflation, exchange rate", "10 markets · 2012–2025"],
    ["UNSD HS correlation tables", "HS2012 ↔ 2017 ↔ 2022 code continuity", "200 continuous HS6 codes"],
  ];
  s.addTable(rows, { x: MX, y: 1.8, w: 7.6, colW: [2.1, 3.2, 2.3], fontFace: BODY, fontSize: 12, color: INK, border: { type: "solid", pt: 0.5, color: RULE }, rowH: 0.5, valign: "middle" });
  stat(s, 8.7, 1.8, 2.0, String(ds.n_markets), "markets (EU-27 as one customs territory)", INK);
  stat(s, 10.8, 1.8, 2.0, "200", `HS6 products fixed with 2014 data (${ds.n_products} ever eligible)`, INK);
  stat(s, 8.7, 3.55, 2.0, ds.n_with_outcome.toLocaleString(), "rows with an observed t+1 outcome", BLUE);
  stat(s, 10.8, 3.55, 2.0, pct(ds.share_tariff_imputed), "rows with a carried-forward tariff", SAFFRON);
  s.addText(bullets([
    "Markets: USA, EU-27, UK, Japan, Korea, Australia, Canada, Indonesia, Malaysia, Mexico",
    "Products: HS 25–96 excl. fuels, gems, arms; both India and China exported ≥ US$50m in 2014",
    "Share = imports from India ÷ total imports of that product (same reporter, same year)",
  ], 13), { x: MX, y: 4.6, w: 7.6, h: 1.9, valign: "top", margin: 0, paraSpaceAfter: 4, isTextBox: true });
  s.addText("Sources: UN Comtrade; WITS/UNCTAD TRAINS; World Bank WDI; UNSD. Retrieved 20 Nov 2026.", { x: 8.7, y: 5.6, w: 4.1, h: 0.8, fontSize: 11, color: MUTED, margin: 0, isTextBox: true });
  note(s, `(~75 s) All data are public and every API response is cached in the submission. Comtrade gives importer-reported imports from India, China and the world for 200 HS6 products in 10 markets from 2012 to 2025. TRAINS gives the tariffs. The World Bank gives macro controls. We kept only HS codes that stay continuous across the 2012, 2017 and 2022 HS revisions, and fixed the product list using 2014 data only, so we cannot have picked products that later became winners. The final dataset has ${ds.n_rows.toLocaleString()} candidate rows. TRAINS has not yet loaded preferences for 2022 onwards, so ${pct(ds.share_tariff_imputed)} of rows carry a forward-filled tariff; these are flagged.`);
}

// ================================================================ 5 Methodology
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  title(s, "Method: decide with data up to t, judge with outcomes at t+1", "Rolling-origin backtest — no random split, no look-ahead");
  const years = []; for (let y = 2015; y <= F; y++) years.push(y);
  const x0 = MX, bw = (W - 2 * MX) / years.length;
  const val = [2018, 2019, 2020];
  years.forEach((y, i) => {
    const c = y === F ? GREY : val.includes(y) ? "9EC5F4" : yrsTest.includes(y) ? BLUE : "D9DDE3";
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x0 + i * bw + 0.04, y: 1.85, w: bw - 0.08, h: 0.6, fill: { color: c }, line: { color: c }, rectRadius: 0.06 });
    s.addText(String(y), { x: x0 + i * bw, y: 1.85, w: bw, h: 0.6, align: "center", valign: "middle", fontSize: 13, bold: true, color: yrsTest.includes(y) ? WHITE : INK, margin: 0, isTextBox: true });
  });
  s.addText([
    { text: "■ ", options: { color: "D9DDE3" } }, { text: "training-only years   ", options: { color: MUTED } },
    { text: "■ ", options: { color: "9EC5F4" } }, { text: "validation (model choice)   ", options: { color: MUTED } },
    { text: "■ ", options: { color: BLUE } }, { text: `held-out test decisions (outcomes ${yrsTest[0] + 1}–${T + 1})   `, options: { color: MUTED } },
    { text: "■ ", options: { color: GREY } }, { text: `live ${F} shortlist (outcome unknown)`, options: { color: MUTED } },
  ], { x: MX, y: 2.5, w: W - 2 * MX, h: 0.4, fontSize: 12, margin: 0, isTextBox: true });
  card(s, MX, 3.15, 3.9, 3.4, "Target (t+1)", bullets([
    "Primary: Δ India import share, pp",
    "Secondary: log export growth",
    "Success = share rises (pre-specified)",
    "Shares cancel common price & FX shocks",
  ], 14), SAFFRON);
  card(s, MX + 4.1, 3.15, 3.9, 3.4, "Features (≤ t)", bullets([
    "Tariffs: India, China, advantage, MFN, Δadvantage",
    "India & China: share, growth, RCA, volatility",
    "Market: size, import growth; GDP, inflation, FX",
    "Market & HS-section categoricals",
  ], 14), BLUE);
  card(s, MX + 8.2, 3.15, 3.9, 3.4, "Guards against leakage", bullets([
    "Each fold trains on decisions ≤ T−1 only",
    "Preprocessing fitted inside training folds",
    "Model chosen on 2018–20, never on test",
    "Same candidates and K for both approaches",
  ], 14), INK);
  note(s, `(~90 s) For a decision in year T we only use information up to T. The model is trained on earlier decision years whose next-year outcomes were already known by T, scores all candidates in T, and is judged on what actually happened in T+1. Years 2018–2020 were used only to choose the model and its hyper-parameters; ${yrsTest[0]}–${T} are pure test decisions. The target is the change in India's share of the market's imports — a share removes price and exchange-rate effects common to all suppliers. Features cover tariffs, India and China's trade momentum and comparative advantage, market demand and macro conditions.`);
}

// ================================================================ 6 Two approaches
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  title(s, "Two defensible ways to pick the top 10", "Both rank exactly the same candidates each year");
  const sm = R.selected_model, fam = sm.model === "hgb" ? "Histogram gradient boosting" : "Random forest";
  card(s, MX, 1.8, 5.9, 4.8, "1 · Historical export momentum (baseline)", bullets([
    "Score = India's annualised 3-year export growth to the market",
    "Logic a business already uses: back what is already growing",
    "Transparent, zero fitted parameters, cannot leak",
    "Blind to tariffs, market demand and China's position",
  ], 15), GREY);
  card(s, MX + 6.2, 1.8, 5.9, 4.8, "2 · Machine-learning ranking", bullets([
    `${fam} regressor predicts next-year Δ share`,
    `Chosen over the ${sm.model === "hgb" ? "random forest" : "gradient boosting"} by validation NDCG@20 (2018–20)`,
    `Hyper-parameters: ${Object.entries(sm.params).map(([k, v]) => k.replace(/_/g, " ") + " " + v).join(", ")}`,
    "Target winsorised at training-fold 1st/99th percentiles",
    "Ranks candidates by predicted share gain → top 10",
  ], 15), BLUE);
  note(s, `(~60 s) The baseline is what many export bodies do informally: back the product-markets where Indian exports have grown fastest over the last three years. It needs no model. The ML approach predicts the next-year share change from 33 decision-time features and ranks by the prediction. We compared gradient boosting and random forests on validation years only; ${fam.toLowerCase()} won and was frozen before touching the test years.`);
}

// ================================================================ 7 Shortlists
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  const ov = R[`overlap_${T}`];
  const bt = R[`top10_baseline_${T}`], mt = R[`top10_ml_${T}`];
  const bp = bt.filter((r) => r.y_success === 1).length, mp = mt.filter((r) => r.y_success === 1).length;
  const PB = R.profiles[`baseline_${T}`], PM = R.profiles[`ml_${T}`];
  title(s, `The ${T} shortlists ${ov <= 3 ? "barely overlap" : "partly overlap"}: ${ov} of 10 in common`, `Decision year ${T}, judged on realised ${T + 1} share change`);
  img(s, `10_topk_comparison_${T}`, MX, 1.65, 8.6, 5.2);
  card(s, 9.45, 1.75, 3.3, 5.0, "What differs", bullets([
    `Baseline hit rate: ${bp}/10 gained share`,
    `ML hit rate: ${mp}/10 gained share`,
    `Baseline = momentum bets: India's share rose ${sgn(PB.d3_share_ind, 1)} pp over the prior 3 years`,
    `ML = rebound bets: India's share fell ${sgn(PM.d3_share_ind, 1)} pp over the prior 3 years (all candidates: ${sgn(R.profiles["universe_" + T].d3_share_ind, 1)} pp)`,
    `Average India share of picks: baseline ${f1(PB.share_ind)}%, ML ${f1(PM.share_ind)}%`,
  ], 12.5), INK);
  note(s, `(~90 s) Here are the actual shortlists for the ${T} decision, scored against what happened in ${T + 1}. Only ${ov} opportunities appear in both lists. In this year ${bp} of the baseline's picks and ${mp} of the ML picks gained share. The baseline is, by construction, drawn to momentum: in its picks India's share had risen ${sgn(PB.d3_share_ind, 1)} points over three years, and such jumps tend to reverse. The ML model learned the mirror image — its picks are positions where India had lost ${sgn(PM.d3_share_ind, 1)} points and is likely to regain ground. In other words, the model's main skill is exploiting mean reversion, not tariffs. The trade-off: the baseline is easy to explain; the ML list is harder to explain but uses more information.`);
}

// ================================================================ 8 Evaluation
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  const nearRandom = R.flags.ml_minus_random_prec < 0.05;
  const verdict = mlBetterP && mlBetterM ? (nearRandom ? "ML beats momentum, but its hit rate is close to a random pick" : "ML beats the momentum baseline on held-out years") : (!mlBetterP && !mlBetterM ? "The momentum baseline is not beaten on held-out years" : "Mixed result: ML and baseline each win on some metrics");
  const EX = Object.fromEntries(R.robust_ex2025.filter((r) => r.k === R.k).map((r) => [r.method, r]));
  title(s, verdict, `Averages over ${nTest} held-out decision years (${yrsTest[0]}–${T}), K = 10`);
  const hdr = (t) => ({ text: t, options: { bold: true, color: WHITE, fill: { color: NAVY }, align: "center" } });
  const row = (lab, a, b, c, d) => [{ text: lab, options: { bold: true } }, { text: a, options: { align: "center" } }, { text: b, options: { align: "center", bold: true, color: BLUE } }, { text: c, options: { align: "center" } }, { text: d, options: { align: "center", color: MUTED } }];
  const boot = Object.fromEntries(R.bootstrap.map((b) => [b.method, b]));
  s.addTable([
    [hdr("Metric (K = 10)"), hdr("Baseline"), hdr("ML"), hdr("ML w/o tariffs"), hdr("Random pick")],
    row("Precision@10", pct(bl.precision_at_k), pct(ml.precision_at_k), pct(nt.precision_at_k), pct(U.universe_precision)),
    row("Avg. Δ share@10 (pp)", sgn(bl.mean_d_share_pp_at_k), sgn(ml.mean_d_share_pp_at_k), sgn(nt.mean_d_share_pp_at_k), sgn(U.universe_mean_d_share_pp)),
    row("Avg. log export growth@10", sgn(bl.mean_export_growth_log_at_k), sgn(ml.mean_export_growth_log_at_k), sgn(nt.mean_export_growth_log_at_k), sgn(U.universe_mean_export_growth_log)),
    row("NDCG@10", f1(bl.ndcg_at_k, 3), f1(ml.ndcg_at_k, 3), f1(nt.ndcg_at_k, 3), f1(U.random_ndcg, 3)),
    row("Top-decile precision@10", pct(bl.top_decile_precision_at_k), pct(ml.top_decile_precision_at_k), pct(nt.top_decile_precision_at_k), "10%"),
  ], { x: MX, y: 1.75, w: 7.4, colW: [2.4, 1.2, 1.2, 1.4, 1.2], fontFace: BODY, fontSize: 13, color: INK, border: { type: "solid", pt: 0.5, color: RULE }, rowH: 0.48, valign: "middle" });
  s.addText(`Bootstrap 95% CI of mean Δ share over the ${boot[MLM].n_picks} pooled picks: baseline ${sgn(boot[BL].ci_low)} to ${sgn(boot[BL].ci_high)} pp; ML ${sgn(boot[MLM].ci_low)} to ${sgn(boot[MLM].ci_high)} pp.`,
    { x: MX, y: 4.85, w: 7.4, h: 0.6, fontSize: 12, color: MUTED, margin: 0, isTextBox: true });
  img(s, "11c_precision_by_fold", 8.25, 1.65, 4.5, 3.75);
  s.addText([
    { text: `Excluding the 2025 outcome year (US tariff shock): ML ${pct(EX.ml.precision_at_k)} vs baseline ${pct(EX.baseline.precision_at_k)} Precision@10.`, options: { breakLine: true } },
    { text: `Tariff ablation: without tariff features Precision@10 is ${pct(nt.precision_at_k)} (vs ${pct(ml.precision_at_k)}) and mean Δ share ${sgn(nt.mean_d_share_pp_at_k)} pp (vs ${sgn(ml.mean_d_share_pp_at_k)}).` },
  ], { x: MX, y: 5.45, w: 12.1, h: 0.75, fontSize: 13, color: INK, margin: 0, isTextBox: true });
  note(s, `(~105 s) This is the key evidence. Averaged over ${nTest} held-out decision years: Precision@10 is ${pct(bl.precision_at_k)} for the baseline and ${pct(ml.precision_at_k)} for ML, against ${pct(U.universe_precision)} for a random pick. The average realised share change of the ten picks is ${sgn(bl.mean_d_share_pp_at_k)} pp for the baseline and ${sgn(ml.mean_d_share_pp_at_k)} pp for ML. NDCG@10 is ${f1(bl.ndcg_at_k, 3)} versus ${f1(ml.ndcg_at_k, 3)}. The chart shows the result fold by fold — with only ten picks a year, results are noisy, so we also report bootstrap intervals. Two honest caveats: ML's hit rate is only ${pct(R.flags.ml_minus_random_prec)} points above a random pick, and in the 2024-to-2025 fold — the year of the US tariff shock — ML did worse than the baseline; excluding that fold ML reaches ${pct(EX.ml.precision_at_k)}. And the model without tariff features does at least as well, so the tariff variables add no measurable predictive value.`);
}

// ================================================================ 9 Simulation & diversion
{
  const s = pres.addSlide({ masterName: "CONTENT" });
  title(s, R.flags.diversion_significant ? "Trade diversion and what-if scenarios" : "Trade diversion and what-if scenarios: weak tariff signal", "Associations and model sensitivity — not causal effects");
  img(s, "13_trade_diversion", MX, 1.65, 7.4, 3.3);
  const reg = R.div_reg.find((r) => r.spec.startsWith("(2)") && r.variable === "tariff_adv");
  const regc = R.div_reg.find((r) => r.spec.startsWith("(3)") && r.variable === "d1_tariff_adv");
  s.addText(bullets([
    `FE regression: +1 pp tariff advantage ↔ ${sgn(reg.coef, 3)} pp next-year share change (p = ${f1(reg.p_value, 2)})`,
    `+1 pp change in advantage ↔ ${sgn(regc.coef, 3)} pp (p = ${f1(regc.p_value, 2)}); market×year and product fixed effects`,
    "Preferences are negotiated, not random → no causal claim",
  ], 13), { x: MX, y: 5.05, w: 7.4, h: 1.6, valign: "top", margin: 0, paraSpaceAfter: 4, isTextBox: true });
  const sc = R.scenarios.filter((r) => r.k === 10 && r.scenario !== "Status quo");
  const hdr = (t) => ({ text: t, options: { bold: true, color: WHITE, fill: { color: NAVY } } });
  s.addTable([[hdr(`Scenario on ${F} candidates`), hdr("New in top 10"), hdr("Mean Δ pred.")],
    ...sc.map((r) => [r.scenario, { text: String(r.n_new), options: { align: "center" } }, { text: sgn(r.mean_pred_change_all, 3), options: { align: "center" } }])],
  { x: 8.3, y: 1.7, w: 4.45, colW: [2.65, 0.9, 0.9], fontFace: BODY, fontSize: 10.5, color: INK, border: { type: "solid", pt: 0.5, color: RULE }, rowH: 0.42, valign: "middle" });
  s.addText("Interactive version: streamlit run app/streamlit_app.py", { x: 8.3, y: 5.75, w: 4.45, h: 0.4, fontSize: 11, color: MUTED, margin: 0, isTextBox: true });
  note(s, `(~75 s) Is there trade diversion — does India gain share where China pays more? Descriptively we compare share changes by the level and change of tariff advantage; in a regression with market-year and product fixed effects, one extra point of advantage is associated with ${sgn(reg.coef, 3)} pp next-year share change, p = ${f1(reg.p_value, 2)}. That is an association, not a causal effect: preferences are negotiated and coincide with other changes. The table shows how many of the model's top 10 change under illustrative tariff and demand shocks. How far the list moves depends on how much weight the model learned to put on tariffs — this is model sensitivity, not a forecast.`);
}

// ================================================================ 10 Conclusion
{
  const s = pres.addSlide({ masterName: "DARK" });
  s.addText("Conclusions", { x: MX, y: 0.45, w: 10, h: 0.8, fontFace: HEAD, fontSize: 36, bold: true, color: WHITE, margin: 0, isTextBox: true });
  const fwd = R[`top10_ml_${F}`].slice(0, 5).map((r) => `${short(r.market)} · ${r.short_desc.slice(0, 34)}`);
  const col = (x, head, items, color) => {
    s.addText(head, { x, y: 1.5, w: 3.9, h: 0.5, fontFace: HEAD, fontSize: 20, bold: true, color, margin: 0, isTextBox: true });
    s.addText(items.map((t, i) => ({ text: t, options: { bullet: true, breakLine: i < items.length - 1 } })), { x, y: 2.1, w: 3.9, h: 4.3, fontSize: 14, color: WHITE, valign: "top", margin: 0, paraSpaceAfter: 8, isTextBox: true });
  };
  col(MX, "What we found", [
    `Chasing momentum backfires: baseline hit rate ${pct(bl.precision_at_k)} vs ${pct(U.universe_precision)} for a random pick — fast growers mean-revert`,
    `ML avoids that trap (${pct(ml.precision_at_k)}; mean Δ share ${sgn(ml.mean_d_share_pp_at_k)} vs ${sgn(bl.mean_d_share_pp_at_k)} pp) but its edge over random is small and broke down in the 2025 shock year`,
    R.flags.tariff_effect === "positive" ? "Tariff features add some predictive signal" : "Tariff gaps are rare and add no measurable predictive value; no significant trade-diversion association",
  ], SAFFRON);
  col(MX + 4.15, `${F} shortlist (ML, top 5)`, fwd, "9EC5F4");
  col(MX + 8.3, "Limits & next steps", [
    "Add US Section 301 / 2025 duties and GSP (needs keyed data)",
    "Few test years → treat gains as indicative",
    "Use ML as a screen, then expert due diligence on non-tariff barriers",
  ], WHITE);
  note(s, `(~30 s) Three takeaways. First, simply backing the fastest growers is worse than random, because rapid growth mean-reverts; the ML ranking avoids that trap and ${mlBetterM ? "delivered larger" : "did not deliver larger"} average share changes, but its advantage over a random pick is small and disappeared in the 2025 tariff-shock year. Second, measured tariff gaps between India and China are uncommon and ${R.flags.tariff_effect === "positive" ? "add some signal" : "removing them does not hurt the ranking"} — with the caveat that our public tariff data miss US Section 301 duties and GSP. Third, the practical use is as a screening tool that filters out mean-reverting momentum picks; the ${F} shortlist shown here is a starting point for expert vetting, not an automatic decision. Thank you — happy to take questions.`);
}

// ================================================================ Appendix
const appx = (t, sub) => { const s = pres.addSlide({ masterName: "CONTENT" }); title(s, t, sub); return s; };
{
  const s = appx("Appendix A1 · What drives the ML ranking", "Permutation importance on held-out decisions (predictive, not causal)");
  img(s, "08_feature_importance", MX + 1.0, 1.65, 10.1, 5.2);
  note(s, "Permutation importance: drop in rank correlation when one feature is shuffled on a held-out year. Tariff features in orange.");
}
{
  const s = appx("Appendix A2 · Calibration of the ranking", "Realised share change by score decile, all test folds");
  img(s, "09_actual_vs_predicted", MX + 1.0, 1.65, 10.1, 5.2);
  note(s, "If the ranking works, realised share change should rise with the score decile. Grey = baseline deciles.");
}
{
  const s = appx("Appendix A3 · Robustness", "Shortlist size, HS revisions, the 2025 tariff shock, single-market dependence");
  img(s, "11_performance_comparison", MX, 1.6, 12.1, 3.2);
  const st = R.robust_strict.filter((r) => r.k === 10), ex = R.robust_ex2025.filter((r) => r.k === 10);
  const lo = R.robust_lomo;
  const lomo = (m) => { const v = lo.filter((r) => r.method === m).map((r) => r.precision_at_10); return `${pct(Math.min(...v))}–${pct(Math.max(...v))}`; };
  const g = (arr, m, f) => { const r = arr.find((x) => x.method === m); return r ? f(r) : "–"; };
  const hdr = (t) => ({ text: t, options: { bold: true, color: WHITE, fill: { color: NAVY } } });
  s.addTable([[hdr("Check (K = 10)"), hdr("Baseline"), hdr("ML")],
    ["Strict 1:1 HS codes only — Precision@10", g(st, "baseline", (r) => pct(r.precision_at_k)), g(st, "ml", (r) => pct(r.precision_at_k))],
    ["Excluding 2025 outcomes — Precision@10", g(ex, "baseline", (r) => pct(r.precision_at_k)), g(ex, "ml", (r) => pct(r.precision_at_k))],
    ["Leave-one-market-out — range of Precision@10", lomo("baseline"), lomo("ml")],
  ], { x: MX, y: 5.0, w: 9.0, colW: [5.4, 1.8, 1.8], fontFace: BODY, fontSize: 12, color: INK, border: { type: "solid", pt: 0.5, color: RULE }, rowH: 0.38 });
  note(s, "Robustness: results across K, strict HS codes, excluding the 2025 shock year, and dropping each market in turn.");
}
{
  const s = appx("Appendix A4 · Tariff measurement and data gaps", "What the tariff advantage does and does not capture");
  img(s, "14_tariff_advantage_over_time", 6.9, 1.65, 5.9, 4.9);
  s.addText(bullets([
    "Rate = simple average of national ad valorem lines in the HS6 (WITS TRAINS, 'reported')",
    "Origin-specific preferential series where TRAINS reports one; else MFN — identical rule for India and China",
    "TRAINS has no preferential schedules for 2022+: last observed rate carried forward (flag tariff_imputed)",
    "Years before a market's first reported preference: change features set to missing",
    "Excluded: US Section 301 & 2025 duties, unilateral GSP (group-coded), anti-dumping, specific duties",
    "HS revisions: only codes continuous across HS2012/2017/2022; strict 1:1 subset as robustness",
  ], 13), { x: MX, y: 1.75, w: 6.0, h: 4.9, valign: "top", margin: 0, paraSpaceAfter: 6, isTextBox: true });
  note(s, "Use this slide for questions about tariff definitions, MFN vs preferential, data gaps and HS revisions.");
}
{
  const s = appx(`Appendix A5 · Live ${F} shortlists (outcome not yet observable)`, "Recommendation for the next promotion cycle");
  const hdr = (t) => ({ text: t, options: { bold: true, color: WHITE, fill: { color: NAVY } } });
  const tbl = (rows, x, label, color) => {
    s.addText(label, { x, y: 1.65, w: 6, h: 0.4, fontFace: HEAD, fontSize: 16, bold: true, color, margin: 0, isTextBox: true });
    s.addTable([[hdr("#"), hdr("Market · product"), hdr("India share"), hdr("Adv. pp")],
      ...rows.map((r) => [String(r.rank), `${short(r.market)} · ${r.hs6} ${r.short_desc.slice(0, 26)}`, f1(r.share_ind) + "%", sgn(r.tariff_adv, 1)])],
    { x, y: 2.1, w: 6.0, colW: [0.4, 3.8, 0.95, 0.85], fontFace: BODY, fontSize: 10.5, color: INK, border: { type: "solid", pt: 0.5, color: RULE }, rowH: 0.4 });
  };
  tbl(R[`top10_baseline_${F}`], MX, "Baseline (momentum)", GREY);
  tbl(R[`top10_ml_${F}`], 6.75, "ML ranking", BLUE);
  note(s, `Forward-looking shortlists using ${F} data, from the model trained on decision years up to ${F - 1}. ${R[`overlap_${F}`]} opportunities overlap.`);
}
{
  const s = appx("Appendix A6 · Trade-diversion regressions", "OLS, market×year and product fixed effects, SE clustered by market–product");
  const hdr = (t) => ({ text: t, options: { bold: true, color: WHITE, fill: { color: NAVY } } });
  s.addTable([[hdr("Specification"), hdr("Variable"), hdr("Coef."), hdr("SE"), hdr("p"), hdr("N")],
    ...R.div_reg.map((r) => [r.spec, r.variable, f1(r.coef, 4), f1(r.se, 4), f1(r.p_value, 3), String(r.n)])],
  { x: MX, y: 1.8, w: 12.1, colW: [4.6, 2.0, 1.4, 1.4, 1.2, 1.5], fontFace: BODY, fontSize: 12, color: INK, border: { type: "solid", pt: 0.5, color: RULE }, rowH: 0.42 });
  s.addText("Outcome: next-year change in India share (pp), except (4): next-year log export growth. Controls: India share, India and market 3-year growth.",
    { x: MX, y: 5.6, w: 12.1, h: 0.6, fontSize: 12, color: MUTED, margin: 0, isTextBox: true });
  note(s, "Coefficients are associations. Identification would need e.g. an event study around agreement entry-into-force with matched control products.");
}

const TITLES = ["Title and motivation", "Business decision", "Why tariffs matter", "Dataset", "Methodology",
  "Two prospect-selection approaches", "Actual top-K shortlists", "Evaluation", "Simulation and trade diversion", "Conclusion",
  "A1 Feature importance", "A2 Calibration", "A3 Robustness", "A4 Tariff measurement", "A5 Live shortlists", "A6 Regressions"];
let md = "# Speaking script — 12-minute presentation + 6-minute Q&A\n\n" +
  "Suggested split for a team of three: Speaker 1 slides 1–3, Speaker 2 slides 4–6, Speaker 3 slides 7–10. " +
  "Timings in brackets sum to 12:00. Appendix slides are for questions only.\n\n";
NOTES.forEach((n, i) => { md += `## Slide ${i + 1} — ${TITLES[i] || ""}\n\n${n}\n\n`; });
fs.writeFileSync(path.join(__dirname, "speaking_script.md"), md);
pres.writeFile({ fileName: path.join(__dirname, "presentation.pptx") }).then((f) => console.log("wrote", f));
