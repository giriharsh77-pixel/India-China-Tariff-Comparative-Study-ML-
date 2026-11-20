import pandas as pd

from src.ranking import rank_within_year, top_k, compare_shortlists


def _df():
    return pd.DataFrame({"iso3": ["A", "B", "C", "D", "A", "B"], "hs6": ["1"] * 6,
                         "year": [2020] * 4 + [2021] * 2, "imp_ind": [1, 2, 3, 4, 1, 2],
                         "s": [0.5, 0.9, 0.9, 0.1, 1.0, 0.0]})


def test_rank_within_year_and_ties():
    r = rank_within_year(_df(), "s")
    r20 = r[r.year == 2020].set_index("iso3")["rank"]
    # B and C tie on score -> higher imp_ind (C) ranks first
    assert r20["C"] == 1 and r20["B"] == 2 and r20["D"] == 4


def test_top_k_per_year_same_k():
    t = top_k(_df(), "s", 1)
    assert t.groupby("year").size().tolist() == [1, 1]


def test_compare_shortlists():
    d = _df()[lambda x: x.year == 2020]
    a, b = top_k(d, "s", 2), top_k(d.assign(s=-d.s), "s", 2)
    c = compare_shortlists(a, b)
    assert set(c["in"]) <= {"both", "baseline only", "ml only"}
    assert len(c) == 4
