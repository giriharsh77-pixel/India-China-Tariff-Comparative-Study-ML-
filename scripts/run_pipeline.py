"""End-to-end pipeline.

    python scripts/run_pipeline.py                 # full run (downloads only what is not cached)
    python scripts/run_pipeline.py --offline       # rebuild everything from the cached raw files
    python scripts/run_pipeline.py --from features # start at a later stage

Stages: collect -> clean -> features -> backtest -> robustness -> diversion
        -> simulation -> figures -> validate
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils import get_logger, load_config, set_seed  # noqa: E402

STAGES = ["collect", "clean", "features", "backtest", "robustness", "diversion", "simulation", "figures", "validate"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="start", default="collect", choices=STAGES)
    ap.add_argument("--offline", action="store_true", help="skip the download stage (use cached raw data)")
    args = ap.parse_args()
    cfg = load_config()
    set_seed(cfg["project"]["random_seed"])
    log = get_logger("pipeline")
    stages = STAGES[STAGES.index(args.start):]
    if args.offline and "collect" in stages:
        stages.remove("collect")
    for st in stages:
        t0 = time.time()
        log.info("=== stage: %s", st)
        if st == "collect":
            from src.data_collection import run_collection
            run_collection(cfg)
        elif st == "clean":
            from src.data_cleaning import run_cleaning
            run_cleaning(cfg)
        elif st == "features":
            from src.feature_engineering import build_dataset
            build_dataset(cfg)
        elif st == "backtest":
            from src.backtesting import run_backtest
            run_backtest(cfg)
        elif st == "robustness":
            from src.backtesting import run_robustness
            run_robustness(cfg)
        elif st == "diversion":
            from src.trade_diversion import run_trade_diversion
            run_trade_diversion()
        elif st == "simulation":
            from src.simulation import run_scenarios
            run_scenarios(cfg)
        elif st == "figures":
            from src.visualisation import make_all
            make_all(cfg)
        elif st == "validate":
            from src.validation import run_validation
            run_validation(cfg)
        log.info("=== stage %s done in %.1fs", st, time.time() - t0)


if __name__ == "__main__":
    main()
