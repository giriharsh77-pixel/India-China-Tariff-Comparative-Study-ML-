"""Quality-control checks on the final dataset and outputs (QC list in the brief).
Writes outputs/metrics/qc_report.csv and raises if a hard check fails."""
from __future__ import annotations

import pandas as pd

from .feature_engineering import ALL_FEATURES
from .utils import get_logger, load_config, p

log = get_logger("validate")


def run_validation(cfg: dict | None = None) -> pd.DataFrame:
    cfg = cfg or load_config()
    ds = pd.read_parquet(p("data", "processed", "analytical_dataset.parquet"))
    sc = pd.read_parquet(p("outputs", "rankings", "scored_candidates.parquet"))
    folds = pd.read_csv(p("outputs", "metrics", "backtest_folds.csv"))
    checks = []

    def add(name, ok, detail, hard=True):
        checks.append({"check": name, "passed": bool(ok), "hard": hard, "detail": detail})

    add("No duplicate market-product-year rows", not ds.duplicated(["iso3", "hs6", "year"]).any(), f"{len(ds)} rows")
    add("Shares within [0, 100]", ds.share_ind.between(0, 100).all() and ds.share_chn.between(0, 100).all(), "share_ind, share_chn")
    add("Tariff advantage = China - India", (ds.tariff_adv - (ds.tariff_chn - ds.tariff_ind)).abs().max() < 1e-9, "identity")
    add("No outcome column used as feature", not any(f.startswith("y_") or f.endswith("_next") for f in ALL_FEATURES),
        f"{len(ALL_FEATURES)} features")
    ok = all(int(r.train_years.split("-")[1]) < r.decision_year for r in folds.itertuples())
    add("Training years strictly precede each decision year", ok, "; ".join(f"{r.decision_year}:{r.train_years}" for r in folds.itertuples()))
    ty = cfg["years"]["test_years"]
    vy = cfg["years"]["validation_years"]
    add("Validation and test years disjoint", not set(ty) & set(vy), f"val={vy} test={ty}")
    t = sc[sc.year.isin(ty)]
    add("Both approaches score the same universe", t.score_baseline.notna().sum() == t.score_ml.notna().sum() == len(t),
        f"{len(t)} test candidates")
    add("All test candidates have a realised outcome", t.has_outcome.mean() > 0.99, f"{t.has_outcome.mean():.3f}")
    add("Candidates eligible only on decision-time data", (ds.imp_ind >= cfg["candidates"]["min_india_imports_usd"]).all(), "imp_ind >= US$1m at t")
    imp = ds.tariff_imputed.mean()
    add("Share of tariff values carried forward (disclosed)", True, f"{imp:.1%} of candidate rows", hard=False)
    add("India+China <= World imports", (~ds.flag_partner_gt_world.astype(bool)).mean() > 0.99,
        f"{ds.flag_partner_gt_world.astype(bool).sum()} rows flagged", hard=False)
    q = pd.DataFrame(checks)
    q.to_csv(p("outputs", "metrics", "qc_report.csv"), index=False)
    log.info("QC report:\n%s", q.to_string(index=False))
    if not q[q.hard].passed.all():
        raise AssertionError("Hard QC check failed - see outputs/metrics/qc_report.csv")
    return q


if __name__ == "__main__":
    run_validation()
