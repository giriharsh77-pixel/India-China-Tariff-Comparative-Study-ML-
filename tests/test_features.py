import numpy as np
import pandas as pd
import pytest

from src.baseline_model import momentum_score
from src.data_cleaning import hs_section
from src.feature_engineering import ALL_FEATURES, NO_TARIFF_FEATURES, TARIFF_FEATURES
from src.simulation import apply_scenario


def test_hs_section():
    assert hs_section("850440")[1] == "Machinery & electronics"
    assert hs_section("620342")[1] == "Textiles & apparel"
    assert hs_section("300490")[1] == "Chemicals & pharmaceuticals"


def test_no_leakage_in_feature_lists():
    for f in ALL_FEATURES:
        assert not f.startswith("y_") and "next" not in f
    assert not set(TARIFF_FEATURES) & set(NO_TARIFF_FEATURES)


def test_momentum_score_is_g3():
    d = pd.DataFrame({"g3_ind": [0.1, -0.2]})
    assert momentum_score(d).tolist() == [0.1, -0.2]


def _cand():
    return pd.DataFrame({"market": ["X", "Y"], "category": ["a", "b"], "mfn": [10.0, 5.0],
                         "tariff_ind": [10.0, 0.0], "tariff_chn": [10.0, 5.0], "tariff_adv": [0.0, 5.0],
                         "d1_tariff_adv": [0.0, 0.0], "d3_tariff_adv": [0.0, 1.0],
                         "has_pref_ind": [0.0, 1.0], "has_pref_chn": [0.0, 0.0],
                         "g1_wld": [0.0, 0.0], "g3_wld": [0.0, 0.0]})


def test_scenario_china_shift():
    s = apply_scenario(_cand(), china_shift=5)
    assert s.tariff_adv.tolist() == [5.0, 10.0]
    assert s.d1_tariff_adv.tolist() == [5.0, 5.0]


def test_scenario_india_floor_and_loss():
    s = apply_scenario(_cand(), india_shift=-5)
    assert s.tariff_ind.tolist() == [5.0, 0.0]       # floored at zero
    s2 = apply_scenario(_cand(), remove_india_advantage=True)
    assert s2.tariff_adv.tolist() == [0.0, 0.0]


def test_scenario_equal_shift_keeps_advantage():
    s = apply_scenario(_cand(), india_shift=5, china_shift=5)
    assert s.tariff_adv.tolist() == [0.0, 5.0]


def test_demand_shift():
    s = apply_scenario(_cand(), demand_shift_pp=5)
    assert np.allclose(s.g3_wld, np.log(1.05))
