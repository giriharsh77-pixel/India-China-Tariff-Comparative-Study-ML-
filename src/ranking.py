"""Top-K selection utilities shared by every approach (same universe, same K)."""
from __future__ import annotations

import pandas as pd


def rank_within_year(df: pd.DataFrame, score_col: str, rank_col: str = "rank") -> pd.DataFrame:
    """Rank candidates inside each decision year (1 = best). Ties are broken
    deterministically by current Indian export value and then by id, so the
    shortlist is reproducible."""
    out = df.sort_values(["year", score_col, "imp_ind", "iso3", "hs6"],
                         ascending=[True, False, False, True, True]).copy()
    out[rank_col] = out.groupby("year").cumcount() + 1
    return out


def top_k(df: pd.DataFrame, score_col: str, k: int) -> pd.DataFrame:
    r = rank_within_year(df, score_col)
    return r[r["rank"] <= k].copy()


def shortlist_table(df: pd.DataFrame, score_col: str, k: int, year: int) -> pd.DataFrame:
    t = top_k(df[df.year == year], score_col, k)
    cols = ["rank", "market", "hs6", "short_desc", "category", "imp_ind", "share_ind", "share_chn",
            "tariff_ind", "tariff_chn", "tariff_adv", "g3_ind", score_col]
    extra = [c for c in ["y_d_share_pp", "y_export_growth_log", "y_success"] if c in t]
    return t[cols + extra]


def compare_shortlists(a: pd.DataFrame, b: pd.DataFrame, name_a: str = "baseline",
                       name_b: str = "ml") -> pd.DataFrame:
    """Union of two top-K lists with membership flags."""
    key = ["iso3", "hs6"]
    ka = a[key + ["rank"]].rename(columns={"rank": f"rank_{name_a}"})
    kb = b[key + ["rank"]].rename(columns={"rank": f"rank_{name_b}"})
    m = ka.merge(kb, on=key, how="outer")
    m["in"] = m.apply(lambda r: "both" if pd.notna(r[f"rank_{name_a}"]) and pd.notna(r[f"rank_{name_b}"])
                      else (f"{name_a} only" if pd.notna(r[f"rank_{name_a}"]) else f"{name_b} only"), axis=1)
    return m
