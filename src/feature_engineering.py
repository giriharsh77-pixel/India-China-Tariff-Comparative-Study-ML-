"""Build the analytical dataset: one row = destination market x HS6 x decision year.

All features at decision year t use information dated t or earlier.
Outcomes are dated t+1 and are kept in clearly prefixed columns (y_*), which the
models never receive as inputs.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .utils import get_logger, load_config, p

log = get_logger("features")

ID_COLS = ["iso3", "market", "hs6", "short_desc", "section", "category", "year"]

TARIFF_FEATURES = ["tariff_ind", "tariff_chn", "tariff_adv", "mfn", "d1_tariff_adv",
                   "d3_tariff_adv", "has_pref_ind", "has_pref_chn"]
TRADE_FEATURES = ["share_ind", "share_chn", "d1_share_ind", "d3_share_ind", "d1_share_chn",
                  "d3_share_chn", "log_imp_ind", "log_imp_chn", "log_imp_wld", "g1_ind", "g3_ind",
                  "g1_chn", "g3_chn", "g1_wld", "g3_wld", "rca_ind_mkt", "rca_chn_mkt",
                  "rca_ind_basket", "ind_vol_3y"]
MACRO_FEATURES = ["log_gdp", "gdp_growth_pct", "inflation_pct", "fx_change_pct"]
CAT_FEATURES = ["market_code", "section_code"]
ALL_FEATURES = TARIFF_FEATURES + TRADE_FEATURES + MACRO_FEATURES + CAT_FEATURES
NO_TARIFF_FEATURES = TRADE_FEATURES + MACRO_FEATURES + CAT_FEATURES


def _lag(df: pd.DataFrame, col: str, k: int) -> pd.Series:
    return df.groupby(["iso3", "hs6"])[col].shift(k)


def _lead(df: pd.DataFrame, col: str, k: int = 1) -> pd.Series:
    return df.groupby(["iso3", "hs6"])[col].shift(-k)


def build_dataset(cfg: dict | None = None) -> pd.DataFrame:
    cfg = cfg or load_config()
    c = float(cfg["baseline"]["smoothing_usd"])
    trade = pd.read_csv(p("data", "processed", "trade_panel.csv"), dtype={"hs6": str})
    tariffs = pd.read_csv(p("data", "processed", "tariff_panel.csv"), dtype={"hs6": str})
    totals = pd.read_csv(p("data", "processed", "totals_panel.csv"))
    macro = pd.read_csv(p("data", "processed", "macro_panel.csv"))
    prods = pd.read_csv(p("data", "processed", "products.csv"), dtype={"hs6": str})

    df = trade.merge(tariffs, on=["iso3", "hs6", "year"], how="left")
    df = df.merge(prods[["hs6", "short_desc", "section", "category", "strict_1to1"]], on="hs6", how="left")
    df["market"] = df.iso3.map({m["iso3"]: m["name"] for m in cfg["markets"]})
    df = df.sort_values(["iso3", "hs6", "year"]).reset_index(drop=True)

    # A market-year that did not report is missing (NaN), never zero.
    for col in ["imp_ind", "imp_chn", "imp_wld"]:
        df.loc[~df.market_reported, col] = np.nan

    # ---------------- shares (importer-reported, consistent definition)
    wld = df.imp_wld.where(df.imp_wld > 0)
    df["share_ind"] = (df.imp_ind / wld).clip(upper=1.0) * 100   # percent
    df["share_chn"] = (df.imp_chn / wld).clip(upper=1.0) * 100

    # ---------------- trade dynamics (log growth with US$ smoothing constant c)
    for who in ("ind", "chn", "wld"):
        v = df[f"imp_{who}"]
        df[f"log_imp_{who}"] = np.log1p(v)
        df[f"g1_{who}"] = np.log(v + c) - np.log(_lag(df, f"imp_{who}", 1) + c)
        df[f"g3_{who}"] = (np.log(v + c) - np.log(_lag(df, f"imp_{who}", 3) + c)) / 3
    for who in ("ind", "chn"):
        df[f"d1_share_{who}"] = df[f"share_{who}"] - _lag(df, f"share_{who}", 1)
        df[f"d3_share_{who}"] = df[f"share_{who}"] - _lag(df, f"share_{who}", 3)
    # volatility of India's annual growth over the last 3 years
    g = df.groupby(["iso3", "hs6"]).g1_ind
    df["ind_vol_3y"] = g.transform(lambda s: s.rolling(3, min_periods=3).std())

    # ---------------- mirror RCA (importer-side, Balassa-type)
    df = df.merge(totals, on=["iso3", "year"], how="left")
    df["rca_ind_mkt"] = (df.imp_ind / df.tot_ind) / (df.imp_wld / df.tot_wld)
    df["rca_chn_mkt"] = (df.imp_chn / df.tot_chn) / (df.imp_wld / df.tot_wld)
    basket = df[df.market_reported].groupby(["hs6", "year"])[["imp_ind", "imp_wld"]].sum()
    tb = totals.groupby("year")[["tot_ind", "tot_wld"]].sum()
    basket = basket.join(tb, on="year")
    basket["rca_ind_basket"] = (basket.imp_ind / basket.tot_ind) / (basket.imp_wld / basket.tot_wld)
    df = df.merge(basket[["rca_ind_basket"]].reset_index(), on=["hs6", "year"], how="left")
    for col in ("rca_ind_mkt", "rca_chn_mkt", "rca_ind_basket"):
        df[col] = np.log1p(df[col].replace([np.inf, -np.inf], np.nan))  # log(1+RCA)

    # ---------------- tariff dynamics
    df = df.sort_values(["iso3", "hs6", "year"]).reset_index(drop=True)
    df["d1_tariff_adv"] = df.tariff_adv - _lag(df, "tariff_adv", 1)
    df["d3_tariff_adv"] = df.tariff_adv - _lag(df, "tariff_adv", 3)
    unk = df.pref_unknown_pre.fillna(False).astype(bool)
    df.loc[unk | _lag(df, "pref_unknown_pre", 1).fillna(False).astype(bool), "d1_tariff_adv"] = np.nan
    df.loc[unk | _lag(df, "pref_unknown_pre", 3).fillna(False).astype(bool), "d3_tariff_adv"] = np.nan
    for col in ("has_pref_ind", "has_pref_chn", "tariff_imputed", "strict_1to1"):
        df[col] = df[col].astype(float)

    # ---------------- macro (destination market)
    macro = macro.sort_values(["iso3", "year"])
    macro["log_gdp"] = np.log(macro.gdp_usd)
    macro["fx_change_pct"] = macro.groupby("iso3").fx_lcu_per_usd.pct_change(fill_method=None) * 100
    df = df.merge(macro[["iso3", "year", "log_gdp", "gdp_growth_pct", "inflation_pct", "fx_change_pct"]],
                  on=["iso3", "year"], how="left")

    # ---------------- categorical codes (stable, alphabetical)
    df["market_code"] = df.iso3.map({m["iso3"]: i for i, m in enumerate(sorted(cfg["markets"], key=lambda m: m["iso3"]))})
    secs = sorted(prods.section.unique())
    df["section_code"] = df.section.map({s: i for i, s in enumerate(secs)})

    # ---------------- outcomes (t+1) -- NEVER used as features
    df = df.sort_values(["iso3", "hs6", "year"]).reset_index(drop=True)
    df["share_ind_next"] = _lead(df, "share_ind")
    df["imp_ind_next"] = _lead(df, "imp_ind")
    df["y_d_share_pp"] = df.share_ind_next - df.share_ind
    df["y_export_growth_log"] = np.log(df.imp_ind_next + c) - np.log(df.imp_ind + c)
    df["y_export_growth_pct"] = (df.imp_ind_next / df.imp_ind - 1) * 100
    thr = cfg["evaluation"]["success_threshold_pp"]
    df["y_success"] = (df.y_d_share_pp > thr).astype(float).where(df.y_d_share_pp.notna())

    # ---------------- candidate universe at decision year t
    cand = cfg["candidates"]
    yrs = cfg["years"]
    df["eligible"] = (
        df.market_reported
        & (df.imp_ind >= cand["min_india_imports_usd"])
        & (df.imp_wld >= cand["min_market_imports_usd"])
        & df.g3_ind.notna() & df.tariff_ind.notna() & df.tariff_chn.notna()
        & df.year.between(yrs["first_decision_year"], yrs["forward_decision_year"])
    )
    df["has_outcome"] = df.y_d_share_pp.notna()

    keep = ID_COLS + ["strict_1to1", "imp_ind", "imp_chn", "imp_wld", "tariff_imputed",
                      "flag_partner_gt_world"] + \
        [f for f in ALL_FEATURES if f not in ID_COLS] + \
        ["share_ind_next", "imp_ind_next", "y_d_share_pp", "y_export_growth_log",
         "y_export_growth_pct", "y_success", "eligible", "has_outcome"]
    ds = df.loc[df.eligible, keep].reset_index(drop=True)
    dup = ds.duplicated(["iso3", "hs6", "year"]).sum()
    assert dup == 0, f"{dup} duplicate market-product-year rows"
    ds.to_csv(p("data", "processed", "analytical_dataset.csv"), index=False)
    ds.to_parquet(p("data", "processed", "analytical_dataset.parquet"), index=False)
    df.to_parquet(p("data", "processed", "full_panel.parquet"), index=False)
    log.info("Analytical dataset: %d candidate rows (%d with observed outcome); years %s",
             len(ds), int(ds.has_outcome.sum()), sorted(ds.year.unique()))
    return ds


if __name__ == "__main__":
    build_dataset()
