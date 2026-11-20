"""Clean and standardise raw downloads into tidy panels.

Outputs (data/processed/):
  products.csv          fixed product universe (HS6, description, section, category)
  trade_panel.csv       market x hs6 x year importer-reported imports from India/China/World
  tariff_panel.csv      market x hs6 x year applied tariffs faced by India / China + MFN
  totals_panel.csv      market x year all-product imports (for mirror RCA)
  macro_panel.csv       market x year WDI indicators
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .utils import get_logger, load_config, p

log = get_logger("clean")

# HS sections by chapter (WCO nomenclature structure)
SECTIONS = [
    (1, 5, "I", "Animal products"), (6, 14, "II", "Vegetable products"),
    (15, 15, "III", "Fats & oils"), (16, 24, "IV", "Food, beverages & tobacco"),
    (25, 27, "V", "Mineral products"), (28, 38, "VI", "Chemicals & pharmaceuticals"),
    (39, 40, "VII", "Plastics & rubber"), (41, 43, "VIII", "Leather & travel goods"),
    (44, 46, "IX", "Wood products"), (47, 49, "X", "Paper & printing"),
    (50, 63, "XI", "Textiles & apparel"), (64, 67, "XII", "Footwear & headgear"),
    (68, 70, "XIII", "Stone, ceramic & glass"), (71, 71, "XIV", "Gems & precious metals"),
    (72, 83, "XV", "Base metals & articles"), (84, 85, "XVI", "Machinery & electronics"),
    (86, 89, "XVII", "Vehicles & transport"), (90, 92, "XVIII", "Instruments & optics"),
    (93, 93, "XIX", "Arms"), (94, 96, "XX", "Miscellaneous manufactures"),
    (97, 99, "XXI", "Art & other"),
]


def hs_section(hs6: str) -> tuple[str, str]:
    ch = int(str(hs6)[:2])
    for lo, hi, code, name in SECTIONS:
        if lo <= ch <= hi:
            return code, name
    return "NA", "Unknown"


def select_product_universe(cfg: dict, stable: pd.DataFrame, uni: pd.DataFrame) -> pd.DataFrame:
    """Fixed, ex-ante product universe based on the selection year only."""
    u = cfg["universe"]
    ind_code, chn_code = cfg["partners"]["india"]["comtrade"], cfg["partners"]["china"]["comtrade"]
    uni = uni.copy()
    uni["hs6"] = uni.cmdCode.astype(str).str.zfill(6)
    x = uni.pivot_table(index="hs6", columns="reporterCode", values="primaryValue", aggfunc="sum")
    x = x.rename(columns={ind_code: "india_world_exports", chn_code: "china_world_exports"})
    df = stable.merge(x[["india_world_exports", "china_world_exports"]], left_on="hs6",
                      right_index=True, how="left").fillna({"india_world_exports": 0, "china_world_exports": 0})
    df["chapter"] = df.hs6.str[:2]
    df = df[(df.chapter.astype(int) >= u["min_chapter"]) & (~df.chapter.isin(u["excluded_chapters"]))]
    df = df[(df.india_world_exports >= u["min_india_world_exports_usd"]) &
            (df.china_world_exports >= u["min_china_world_exports_usd"])]
    log.info("Products passing filters: %d (keeping top %d by India 2014 exports)", len(df), u["n_products"])
    df = df.sort_values("india_world_exports", ascending=False).head(u["n_products"]).copy()
    df[["section", "category"]] = df.hs6.apply(lambda h: pd.Series(hs_section(h)))
    df["short_desc"] = df.description.str.replace(r"\s+", " ", regex=True).str.slice(0, 60)
    df = df.sort_values("hs6").reset_index(drop=True)
    df.to_csv(p("data", "processed", "products.csv"), index=False)
    return df


def clean_trade(cfg: dict) -> pd.DataFrame:
    raw = pd.read_csv(p("data", "processed", "imports_raw.csv"), dtype={"cmdCode": str})
    prods = pd.read_csv(p("data", "processed", "products.csv"), dtype={"hs6": str})
    raw["hs6"] = raw.cmdCode.str.zfill(6)
    code2iso = {m["comtrade"]: m["iso3"] for m in cfg["markets"]}
    raw["iso3"] = raw.reporterCode.map(code2iso)
    pmap = {cfg["partners"]["india"]["comtrade"]: "imp_ind",
            cfg["partners"]["china"]["comtrade"]: "imp_chn",
            cfg["partners"]["world"]["comtrade"]: "imp_wld"}
    raw["who"] = raw.partnerCode.map(pmap)
    dup = raw.duplicated(["iso3", "hs6", "refYear", "who"]).sum()
    if dup:
        log.warning("Dropping %d duplicate Comtrade rows (keeping first)", dup)
        raw = raw.drop_duplicates(["iso3", "hs6", "refYear", "who"])
    wide = raw.pivot_table(index=["iso3", "hs6", "refYear"], columns="who",
                           values="primaryValue", aggfunc="sum").reset_index()
    wide = wide.rename(columns={"refYear": "year"})
    # full grid market x product x year
    years = range(cfg["years"]["trade_first"], cfg["years"]["trade_last"] + 1)
    grid = pd.MultiIndex.from_product([[m["iso3"] for m in cfg["markets"]], prods.hs6, years],
                                      names=["iso3", "hs6", "year"]).to_frame(index=False)
    df = grid.merge(wide, on=["iso3", "hs6", "year"], how="left")
    # Did the reporter publish ANY data in that year? Comtrade omits zero flows,
    # so within a reporting market-year a missing partner row = zero trade.
    reported = raw.groupby(["iso3", "refYear"]).size().rename("n").reset_index().rename(columns={"refYear": "year"})
    df = df.merge(reported, on=["iso3", "year"], how="left")
    df["market_reported"] = df.n.fillna(0) > 0
    for c in ["imp_ind", "imp_chn", "imp_wld"]:
        if c not in df:
            df[c] = np.nan
        df.loc[df.market_reported & df[c].isna(), c] = 0.0
    df = df.drop(columns="n")
    # validation: partner flows cannot exceed world
    bad = (df.imp_ind + df.imp_chn > df.imp_wld * 1.001 + 1).sum()
    log.info("Rows where India+China > World (data inconsistency): %d", bad)
    df["flag_partner_gt_world"] = (df.imp_ind + df.imp_chn > df.imp_wld * 1.001 + 1)
    df.to_csv(p("data", "processed", "trade_panel.csv"), index=False)
    log.info("trade_panel: %d rows, %d market-years reported", len(df),
             df.loc[df.market_reported, ["iso3", "year"]].drop_duplicates().shape[0])
    return df


def clean_totals(cfg: dict) -> pd.DataFrame:
    raw = pd.read_csv(p("data", "processed", "totals_raw.csv"))
    code2iso = {m["comtrade"]: m["iso3"] for m in cfg["markets"]}
    raw["iso3"] = raw.reporterCode.map(code2iso)
    pmap = {cfg["partners"]["india"]["comtrade"]: "tot_ind",
            cfg["partners"]["china"]["comtrade"]: "tot_chn",
            cfg["partners"]["world"]["comtrade"]: "tot_wld"}
    raw["who"] = raw.partnerCode.map(pmap)
    df = raw.pivot_table(index=["iso3", "refYear"], columns="who", values="primaryValue",
                         aggfunc="sum").reset_index().rename(columns={"refYear": "year"})
    df.to_csv(p("data", "processed", "totals_panel.csv"), index=False)
    return df


def clean_tariffs(cfg: dict) -> pd.DataFrame:
    """Applied tariff faced by Indian- and Chinese-origin goods.

    Definition (identical for both origins, so the comparison is like-for-like):
      applied_tariff(origin) = TRAINS country-specific preferential series for that
      origin if TRAINS reports one (reciprocal FTA/CEPA/ASEAN/RCEP rates; the
      series already averages preferential lines with MFN lines that have no
      preference), otherwise the MFN rate (both India and China are WTO members).

    Gaps: when TRAINS has *no preferential data for any partner* in a market-year
    (a loading gap, e.g. 2022-2023 for most markets) the last observed origin-
    specific preferential rate is carried forward (backward-looking only).  Years
    after the last TRAINS year (2024-2025) carry forward the last observed MFN and
    applied rates.  Every carried value is flagged.
    """
    raw = pd.read_csv(p("data", "processed", "tariffs_raw.csv"), dtype={"hs6": str, "reporter": str, "partner": str})
    pres = pd.read_csv(p("data", "processed", "pref_presence.csv"))
    prods = pd.read_csv(p("data", "processed", "products.csv"), dtype={"hs6": str})
    wits2iso = {str(m["wits"]).zfill(3): m["iso3"] for m in cfg["markets"]}
    raw["iso3"] = raw.reporter.str.zfill(3).map(wits2iso)
    raw["hs6"] = raw.hs6.str.zfill(6)
    raw["partner"] = raw.partner.str.zfill(3)
    raw = raw[raw.rate.notna()]
    mfn = raw[raw.partner == "000"].groupby(["iso3", "hs6", "year"]).rate.mean().rename("mfn")
    ind = raw[(raw.partner == cfg["partners"]["india"]["wits"]) & (raw.tariff_type == "PREF")] \
        .groupby(["iso3", "hs6", "year"]).rate.mean().rename("pref_ind")
    chn = raw[(raw.partner == cfg["partners"]["china"]["wits"]) & (raw.tariff_type == "PREF")] \
        .groupby(["iso3", "hs6", "year"]).rate.mean().rename("pref_chn")
    na_share = raw[raw.partner == "000"].assign(na=lambda d: d.n_na_lines / d.n_lines.clip(lower=1)) \
        .groupby(["iso3", "hs6", "year"]).na.mean().rename("mfn_share_nonadvalorem_lines")
    years = range(cfg["years"]["tariff_first"], cfg["years"]["trade_last"] + 1)
    grid = pd.MultiIndex.from_product([[m["iso3"] for m in cfg["markets"]], prods.hs6, years],
                                      names=["iso3", "hs6", "year"]).to_frame(index=False)
    df = grid.merge(mfn.reset_index(), how="left").merge(ind.reset_index(), how="left") \
        .merge(chn.reset_index(), how="left").merge(na_share.reset_index(), how="left")
    # Loading-gap detector: number of India- or China-specific preferential
    # series reported across ALL study products in that market-year, plus the
    # any-partner probe. Zero on both = TRAINS did not load preferential
    # schedules that year (e.g. 2022-2023), NOT evidence that FTAs lapsed.
    ic = raw[raw.partner.isin([cfg["partners"]["india"]["wits"], cfg["partners"]["china"]["wits"]])
             & (raw.tariff_type == "PREF")].groupby(["iso3", "year"]).size().rename("ic_pref_series")
    pres = pres.rename(columns={"n_pref_series": "probe_pref_series"})[["iso3", "year", "probe_pref_series"]]
    pres = pres.merge(ic.reset_index(), on=["iso3", "year"], how="outer").fillna(0)
    pres["pref_series_in_market"] = pres.probe_pref_series + pres.ic_pref_series
    df = df.merge(pres[["iso3", "year", "pref_series_in_market", "ic_pref_series"]], on=["iso3", "year"], how="left")
    df["pref_series_in_market"] = df.pref_series_in_market.fillna(0)
    df["ic_pref_series"] = df.ic_pref_series.fillna(0)
    df = df.sort_values(["iso3", "hs6", "year"]).reset_index(drop=True)

    # --- MFN: carry forward over missing years (flagged)
    df["mfn_observed"] = df.mfn.notna()
    df["mfn"] = df.groupby(["iso3", "hs6"]).mfn.ffill()
    # --- origin-specific preferential rates
    for o in ("ind", "chn"):
        obs = df[f"pref_{o}"].notna()
        df[f"pref_{o}_observed"] = obs
        # loading gap = market reports no pref series at all that year
        gap = (df.ic_pref_series == 0) | (~df.mfn_observed)
        carried = df.groupby(["iso3", "hs6"])[f"pref_{o}"].ffill()
        df[f"pref_{o}_carried"] = (~obs) & gap & carried.notna()
        df.loc[df[f"pref_{o}_carried"], f"pref_{o}"] = carried[df[f"pref_{o}_carried"]]
        df[f"tariff_{o}"] = np.where(df[f"pref_{o}"].notna(),
                                     np.minimum(df[f"pref_{o}"], df.mfn.fillna(np.inf)), df.mfn)
        df[f"has_pref_{o}"] = df[f"pref_{o}"].notna() & (df[f"pref_{o}"] < df.mfn - 1e-9)
    df["tariff_adv"] = df.tariff_chn - df.tariff_ind  # +ve = India advantage
    # Years BEFORE TRAINS first reports any India/China preference in a market
    # that does have such preferences: preferential status unknown -> tariff
    # *change* features spanning these years are set to missing downstream.
    first_obs = df[df.ic_pref_series > 0].groupby("iso3").year.min()
    df["pref_unknown_pre"] = df.iso3.map(first_obs).notna() & (df.year < df.iso3.map(first_obs))
    df["tariff_imputed"] = (~df.mfn_observed) | df.pref_ind_carried | df.pref_chn_carried
    out = df[["iso3", "hs6", "year", "mfn", "tariff_ind", "tariff_chn", "tariff_adv",
              "has_pref_ind", "has_pref_chn", "pref_ind_observed", "pref_chn_observed",
              "pref_ind_carried", "pref_chn_carried", "mfn_observed", "tariff_imputed", "pref_unknown_pre",
              "mfn_share_nonadvalorem_lines"]]
    out.to_csv(p("data", "processed", "tariff_panel.csv"), index=False)
    log.info("tariff_panel: %d rows; tariff missing: %d; imputed (carried): %d",
             len(out), out.tariff_ind.isna().sum(), out.tariff_imputed.sum())
    return out


def clean_macro(cfg: dict) -> pd.DataFrame:
    raw = pd.read_csv(p("data", "processed", "wdi_raw.csv"))
    wdi2iso = {m["wdi"]: m["iso3"] for m in cfg["markets"]}
    raw["iso3"] = raw.wdi.map(wdi2iso)
    df = raw.pivot_table(index=["iso3", "year"], columns="indicator", values="value").reset_index()
    df.to_csv(p("data", "processed", "macro_panel.csv"), index=False)
    return df


def run_cleaning(cfg: dict | None = None) -> None:
    cfg = cfg or load_config()
    clean_trade(cfg)
    clean_totals(cfg)
    clean_tariffs(cfg)
    clean_macro(cfg)
    log.info("Cleaning complete")


if __name__ == "__main__":
    run_cleaning()
