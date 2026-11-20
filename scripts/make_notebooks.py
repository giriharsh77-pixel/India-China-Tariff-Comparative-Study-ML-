"""Generate and execute the 8 walk-through notebooks in notebooks/.

Each notebook is a thin, readable layer over the src/ modules (the single
source of truth), so notebooks and pipeline can never disagree.
Run after the pipeline:  python scripts/make_notebooks.py
"""
from pathlib import Path

import nbformat as nbf
from nbconvert.preprocessors import ExecutePreprocessor

ROOT = Path(__file__).resolve().parents[1]
NB = ROOT / "notebooks"
SETUP = """import sys, pathlib
ROOT = pathlib.Path.cwd().resolve().parent
sys.path.insert(0, str(ROOT))
import os; os.chdir(ROOT)
import pandas as pd, numpy as np
pd.set_option('display.max_columns', 40); pd.set_option('display.width', 200)
from src.utils import load_config
cfg = load_config()"""

BOOKS = {
    "01_data_exploration": [
        ("md", "# 01 · Data exploration\nRaw downloads: Comtrade imports, TRAINS tariffs, WDI macro, HS continuity tables. "
               "All files are cached in `data/raw/`; see `data/data_sources.md`."),
        ("code", SETUP),
        ("code", "prods = pd.read_csv('data/processed/products.csv', dtype={'hs6': str})\nprods.category.value_counts()"),
        ("code", "prods[['hs6','short_desc','india_world_exports','china_world_exports','strict_1to1']].head(15)"),
        ("code", "raw = pd.read_csv('data/processed/imports_raw.csv', dtype={'cmdCode': str})\n"
                 "raw.groupby(['reporterCode','partnerCode']).refYear.agg(['min','max','count'])"),
        ("code", "tar = pd.read_csv('data/processed/tariffs_raw.csv', dtype={'hs6': str, 'partner': str})\n"
                 "tar.groupby(['reporter','partner','tariff_type']).year.agg(['min','max','count'])"),
    ],
    "02_data_cleaning": [
        ("md", "# 02 · Data cleaning\nZero-flow handling, EU as one customs territory, tariff gap carry-forward (`src/data_cleaning.py`)."),
        ("code", SETUP),
        ("code", "trade = pd.read_csv('data/processed/trade_panel.csv', dtype={'hs6': str})\n"
                 "trade.groupby('iso3').market_reported.mean().round(3)"),
        ("code", "print('rows where India+China > World:', int(trade.flag_partner_gt_world.sum()))\ntrade.describe().T"),
        ("code", "tp = pd.read_csv('data/processed/tariff_panel.csv', dtype={'hs6': str})\n"
                 "tp.groupby('year')[['mfn_observed','pref_ind_carried','pref_chn_carried','tariff_imputed']].mean().round(3)"),
    ],
    "03_feature_engineering": [
        ("md", "# 03 · Feature engineering\nOne row = market × HS6 × decision year; all features dated ≤ t; outcomes `y_*` dated t+1."),
        ("code", SETUP),
        ("code", "from src.feature_engineering import ALL_FEATURES, TARIFF_FEATURES\n"
                 "ds = pd.read_parquet('data/processed/analytical_dataset.parquet')\nprint(len(ds), 'candidate rows')\nds.groupby('year').size()"),
        ("code", "ds[ALL_FEATURES].describe().T.round(3)"),
        ("code", "ds[['y_d_share_pp','y_export_growth_log','y_success']].describe().round(3)"),
    ],
    "04_exploratory_analysis": [
        ("md", "# 04 · Exploratory analysis\nFigures are produced by `src/visualisation.py`."),
        ("code", SETUP + "\nfrom IPython.display import Image, display"),
        ("code", "for f in ['01_tariff_india_vs_china_by_category','02_tariff_advantage_by_market','14_tariff_advantage_over_time',"
                 "'03_india_export_trend','04_china_export_trend','05_market_share_india_vs_china','06_import_growth_by_category',"
                 "'07_tariff_advantage_distribution']:\n    display(Image(f'outputs/figures/{f}.png', width=800))"),
    ],
    "05_baseline_model": [
        ("md", "# 05 · Baseline: historical export momentum\nScore = annualised 3-year log growth of India's exports to the market."),
        ("code", SETUP),
        ("code", "from src.baseline_model import add_baseline_scores\nfrom src.ranking import shortlist_table\n"
                 "ds = add_baseline_scores(pd.read_parquet('data/processed/analytical_dataset.parquet'))\n"
                 "shortlist_table(ds, 'score_baseline', 10, cfg['years']['test_years'][-1])"),
    ],
    "06_ml_model": [
        ("md", "# 06 · ML model\nModel family and hyper-parameters chosen on validation years only."),
        ("code", SETUP + "\nimport json"),
        ("code", "pd.read_csv('outputs/metrics/validation_model_selection.csv').sort_values('ndcg_at_20', ascending=False)"),
        ("code", "json.load(open('outputs/metrics/selected_model.json'))"),
        ("code", "pd.read_csv('outputs/metrics/backtest_folds.csv')"),
        ("code", "pd.read_csv('outputs/metrics/feature_importance_permutation.csv').head(15)"),
    ],
    "07_model_evaluation": [
        ("md", "# 07 · Evaluation\nRolling-origin backtest, same universe and K for both approaches."),
        ("code", SETUP + "\nfrom IPython.display import Image, display"),
        ("code", "s = pd.read_csv('outputs/metrics/backtest_metrics_summary.csv'); s[s.k==10].round(3)"),
        ("code", "pd.read_csv('outputs/metrics/backtest_metrics_by_year.csv').query('k==10')[['year','method','precision_at_k','mean_d_share_pp_at_k','ndcg_at_k']].round(3)"),
        ("code", "pd.read_csv('outputs/metrics/pooled_topk_bootstrap.csv').round(3)"),
        ("code", "pd.read_csv('outputs/rankings/shortlist_comparison_%d.csv' % cfg['years']['test_years'][-1], dtype={'hs6': str})"),
        ("code", "for f in ['11_performance_comparison','11b_backtest_by_year','09_actual_vs_predicted','08_feature_importance']:\n"
                 "    display(Image(f'outputs/figures/{f}.png', width=800))"),
        ("code", "pd.read_csv('outputs/metrics/diversion_regressions.csv').round(4)"),
    ],
    "08_simulation": [
        ("md", "# 08 · Simulation (model-based what-if, not causal)\nInteractive version: `streamlit run app/streamlit_app.py`."),
        ("code", SETUP),
        ("code", "from src.simulation import load_bundle, apply_scenario, score, compare\n"
                 "b = load_bundle()\nsc = pd.read_parquet('outputs/rankings/scored_candidates.parquet')\n"
                 "cand = sc[sc.year == cfg['years']['forward_decision_year']].reset_index(drop=True)\n"
                 "base = cand.assign(pred=score(cand, b))\n"
                 "scen = apply_scenario(cand, china_shift=5.0); scen['pred'] = score(scen, b)\n"
                 "c = compare(base, scen, 10); c[c.status != 'outside'].sort_values('rank_scen')"),
        ("code", "pd.read_csv('outputs/simulation_results/scenario_summary_%d.csv' % cfg['years']['forward_decision_year'])"),
    ],
}


def main():
    NB.mkdir(exist_ok=True)
    ep = ExecutePreprocessor(timeout=600, kernel_name="python3")
    for name, cells in BOOKS.items():
        nb = nbf.v4.new_notebook()
        nb.cells = [nbf.v4.new_markdown_cell(c) if t == "md" else nbf.v4.new_code_cell(c) for t, c in cells]
        ep.preprocess(nb, {"metadata": {"path": str(NB)}})
        nbf.write(nb, NB / f"{name}.ipynb")
        print("executed", name)


if __name__ == "__main__":
    main()
