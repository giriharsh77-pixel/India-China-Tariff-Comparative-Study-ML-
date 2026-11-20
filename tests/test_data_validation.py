"""Checks on the built dataset (skipped if the pipeline has not been run)."""
from pathlib import Path

import pandas as pd
import pytest

from src.data_collection import parse_trains

DS = Path(__file__).resolve().parents[1] / "data" / "processed" / "analytical_dataset.parquet"


def test_parse_trains():
    xml = ('<Series FREQ="A" PRODUCTCODE="620342" PARTNER="356" REPORTER="392">'
           '<Obs TIME_PERIOD="2021" OBS_VALUE="0" TARIFFTYPE="PREF" TOTALNOOFLINES="2" NBR_PREF_LINES="2" '
           'NBR_MFN_LINES="0" NBR_NA_LINES="0" MIN_RATE="0" MAX_RATE="0" NOMENCODE="H5" /></Series>')
    r = parse_trains(xml)
    assert r[0]["partner"] == "356" and r[0]["year"] == 2021 and r[0]["rate"] == 0.0
    assert parse_trains("NoRecordsFound") == []


@pytest.mark.skipif(not DS.exists(), reason="dataset not built")
def test_dataset_integrity():
    d = pd.read_parquet(DS)
    assert not d.duplicated(["iso3", "hs6", "year"]).any()
    assert d.share_ind.between(0, 100).all()
    assert (d.imp_ind >= 1_000_000).all()
    assert ((d.tariff_adv - (d.tariff_chn - d.tariff_ind)).abs() < 1e-9).all()
    # outcome is the t+1 share minus the t share
    o = d.dropna(subset=["y_d_share_pp"])
    assert ((o.share_ind_next - o.share_ind - o.y_d_share_pp).abs() < 1e-9).all()


@pytest.mark.skipif(not DS.exists(), reason="dataset not built")
def test_eu_single_customs_territory():
    d = pd.read_parquet(DS)
    eu_members = {"DEU", "FRA", "ITA", "NLD", "ESP", "BEL"}
    assert not eu_members & set(d.iso3.unique())
