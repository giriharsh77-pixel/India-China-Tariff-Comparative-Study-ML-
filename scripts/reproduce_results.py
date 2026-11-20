"""Reproducibility check: rebuild everything from the cached raw data and verify
the headline metrics match the shipped results/outputs exactly (within 1e-9).

    python scripts/reproduce_results.py
"""
import subprocess
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FILES = ["outputs/metrics/backtest_metrics_summary.csv", "outputs/metrics/backtest_metrics_by_year.csv",
         "outputs/metrics/diversion_regressions.csv"]


def main():
    before = {f: pd.read_csv(ROOT / f) for f in FILES}
    r = subprocess.run([sys.executable, str(ROOT / "scripts/run_pipeline.py"), "--offline", "--from", "clean"], cwd=ROOT)
    if r.returncode:
        sys.exit("pipeline failed")
    ok = True
    for f, b in before.items():
        a = pd.read_csv(ROOT / f)
        num = b.select_dtypes("number").columns
        same = a.shape == b.shape and ((a[num] - b[num]).abs().max().max() < 1e-9 or b[num].empty)
        print(("OK   " if same else "DIFF ") + f)
        ok &= bool(same)
    print("REPRODUCED" if ok else "NOT REPRODUCED")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
