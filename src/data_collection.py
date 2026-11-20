"""Download raw public data (cached) from UN Comtrade, WITS/TRAINS, World Bank WDI
and the UNSD HS correlation tables.

Every request is cached under data/raw/ so that the pipeline can be re-run
offline and so that the exact raw responses are part of the submission.

Sources (no API key required for any call used here):
  * UN Comtrade public preview API  https://comtradeapi.un.org/public/v1/preview/
    (max 500 records & 1 period per call; we batch accordingly)
  * WITS UNCTAD-TRAINS SDMX API      https://wits.worldbank.org/API/V1/SDMX/V21/
  * World Bank WDI API v2            https://api.worldbank.org/v2/
  * UNSD HS correlation tables       https://unstats.un.org/unsd/classifications/Econ
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

import pandas as pd
import requests

from .utils import get_logger, load_config, p

log = get_logger("collect")

COMTRADE = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
WITS_TRN = "https://wits.worldbank.org/API/V1/SDMX/V21/datasource/TRN"
WDI = "https://api.worldbank.org/v2"
UNSD = "https://unstats.un.org/unsd/classifications/Econ/tables"
HS_REF = "https://comtradeapi.un.org/files/v1/app/reference"

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "academic-research-pipeline/1.0"})


# --------------------------------------------------------------------------- #
# generic cached GET
# --------------------------------------------------------------------------- #
def _get(url: str, cache: Path, params: dict | None = None, binary: bool = False,
         retries: int = 25, pause: float = 1.2) -> bytes | str:
    if cache.exists() and cache.stat().st_size > 0:
        return cache.read_bytes() if binary else cache.read_text(encoding="utf-8")
    cache.parent.mkdir(parents=True, exist_ok=True)
    last = None
    for attempt in range(retries):
        try:
            r = SESSION.get(url, params=params, timeout=180)
            if r.status_code == 403 and "uota" in r.text + r.reason:
                mt = re.search(r"replenished in (\d+):(\d+):(\d+)", r.text)
                wait = (int(mt[1]) * 3600 + int(mt[2]) * 60 + int(mt[3]) + 15) if mt else 180
                log.warning("Comtrade call quota exhausted; sleeping %ss", wait)
                time.sleep(wait)
                continue
            if r.status_code == 429:
                wait = 5 * (attempt + 1)
                log.warning("429 rate-limited; sleeping %ss", wait)
                time.sleep(wait)
                continue
            if r.status_code == 404 and "NoRecordsFound" in r.text:
                cache.write_text("NoRecordsFound", encoding="utf-8")
                return "NoRecordsFound"
            r.raise_for_status()
            if binary:
                cache.write_bytes(r.content)
                time.sleep(pause)
                return r.content
            cache.write_text(r.text, encoding="utf-8")
            time.sleep(pause)
            return r.text
        except Exception as exc:  # network errors, 5xx
            last = exc
            log.warning("GET failed (%s/%s) %s: %s", attempt + 1, retries, url[:120], exc)
            time.sleep(3 * (attempt + 1))
    raise RuntimeError(f"Failed to download {url}: {last}")


# --------------------------------------------------------------------------- #
# HS reference & correlation tables
# --------------------------------------------------------------------------- #
def download_hs_tables() -> None:
    d = p("data", "raw", "hs", "x").parent
    for f in ["HS2022toHS2017ConversionAndCorrelationTables.xlsx",
              "HS2017toHS2012ConversionAndCorrelationTables.xlsx"]:
        _get(f"{UNSD}/{f}", d / f, binary=True)
    for f in ["H4", "H5", "H6"]:
        _get(f"{HS_REF}/{f}.json", d / f"{f}.json")


def stable_hs6_codes() -> pd.DataFrame:
    """HS6 codes whose scope is unchanged (1:1, same code) across HS2012, HS2017
    and HS2022, according to the official UNSD correlation tables."""
    d = p("data", "raw", "hs", "x").parent
    c22 = pd.read_excel(d / "HS2022toHS2017ConversionAndCorrelationTables.xlsx",
                        sheet_name="HS2022-HS2017 Correlations", header=1, dtype=str)
    c22.columns = ["hs22", "hs17", "rel"]
    c17 = pd.read_excel(d / "HS2017toHS2012ConversionAndCorrelationTables.xlsx",
                        sheet_name="Correlation HS17-HS12", header=1, dtype=str)
    c17 = c17.iloc[:, [0, 2, 3]]
    c17.columns = ["hs17", "hs12", "rel"]
    for c in (c22, c17):
        for col in c.columns[:2]:
            c[col] = c[col].astype(str).str.strip().str.zfill(6)
        c["rel"] = c["rel"].astype(str).str.strip()
    # Continuity rule: the same 6-digit code exists in HS2012, HS2017 and HS2022
    # and is linked to itself in both official correlation tables. Strict 1:1
    # codes have an identical scope; 1:n / n:1 codes kept their code but had a
    # partial transfer of scope (flagged, robustness-checked). n:n links
    # (complex reallocations) are excluded.
    def links(c, a, b):
        same = c[c[a] == c[b]]
        return dict(zip(same[a], same.rel))
    l22, l17 = links(c22, "hs22", "hs17"), links(c17, "hs17", "hs12")
    # exclude a code whose own same-code link is n:n (complex reallocation).
    # (Codes that merely *contributed* a minor part of their scope to a new
    # HS2022 heading such as 8524 or 8549 keep an n:1 / 1:n self-link.)
    codes = sorted(c for c in set(l22) & set(l17) if l22[c] != "n:n" and l17[c] != "n:n")
    h6 = json.loads((d / "H6.json").read_text(encoding="utf-8"))["results"]
    desc = {r["id"]: r["text"].split(" - ", 1)[-1] for r in h6 if len(r["id"]) == 6}
    out = pd.DataFrame({"hs6": codes})
    out["rel_2022_2017"] = out.hs6.map(l22)
    out["rel_2017_2012"] = out.hs6.map(l17)
    out["strict_1to1"] = (out.rel_2022_2017 == "1:1") & (out.rel_2017_2012 == "1:1")
    out["description"] = out.hs6.map(desc)
    log.info("Continuous HS6 codes across HS2012/2017/2022: %d (strict 1:1: %d)",
             len(out), int(out.strict_1to1.sum()))
    return out


# --------------------------------------------------------------------------- #
# UN Comtrade
# --------------------------------------------------------------------------- #
def comtrade(reporters, partners, cmds, year: int, flow: str, tag: str) -> pd.DataFrame:
    """One preview call (<=500 rows, single period). Cached by tag."""
    params = {
        "reporterCode": ",".join(map(str, reporters)),
        "partnerCode": ",".join(map(str, partners)),
        "cmdCode": ",".join(cmds),
        "period": str(year),
        "flowCode": flow,
        "partner2Code": "0", "customsCode": "C00", "motCode": "0",
    }
    h = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:8]
    cache = p("data", "raw", "comtrade", f"{tag}_{h}.json")
    txt = _get(COMTRADE, cache, params=params, pause=1.5)
    js = json.loads(txt)
    if js.get("error"):
        raise RuntimeError(f"Comtrade error {tag}: {js['error']}")
    rows = js.get("data", []) or []
    if len(rows) >= 500:
        raise RuntimeError(f"Comtrade call {tag} hit the 500-row preview cap; reduce batch")
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    keep = ["refYear", "reporterCode", "partnerCode", "flowCode", "cmdCode",
            "classificationCode", "primaryValue", "netWgt", "qty", "qtyUnitCode",
            "isReported", "isAggregate"]
    return df[[c for c in keep if c in df.columns]]


def collect_universe_exports(cfg: dict, stable: pd.DataFrame) -> pd.DataFrame:
    """India and China world exports by HS6 in the universe-selection year."""
    y = cfg["universe"]["selection_year"]
    codes = stable.hs6.tolist()
    chunks = [codes[i:i + 240] for i in range(0, len(codes), 240)]
    frames = []
    for who in ("india", "china"):
        rep = cfg["partners"][who]["comtrade"]
        for i, ch in enumerate(chunks):
            frames.append(comtrade([rep], [0], ch, y, "X", f"universe_{who}_X_{y}_{i:02d}"))
    df = pd.concat(frames, ignore_index=True)
    log.info("Universe export rows: %d", len(df))
    return df


def _comtrade_cache_exists(reporters, partners, cmds, year, flow, tag) -> bool:
    params = {
        "reporterCode": ",".join(map(str, reporters)), "partnerCode": ",".join(map(str, partners)),
        "cmdCode": ",".join(cmds), "period": str(year), "flowCode": flow,
        "partner2Code": "0", "customsCode": "C00", "motCode": "0",
    }
    h = hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest()[:8]
    return p("data", "raw", "comtrade", f"{tag}_{h}.json").exists()


def collect_bilateral_imports(cfg: dict, products: list[str]) -> pd.DataFrame:
    """Importer-reported imports from India, China and World for each market,
    product and year.

    Call budget: products are split into a 150-product chunk (one market per
    call: 3 partners x 150 = 450 rows <= 500 cap) and a remainder chunk that is
    requested for up to 3 markets at once (3 x 3 x 50 = 450 rows), because the
    keyless endpoint allows only ~100 calls per hour."""
    partners = [cfg["partners"][k]["comtrade"] for k in ("india", "china", "world")]
    frames = []
    chunk = 150
    main, rest = products[:chunk], products[chunk:]
    per_call = max(1, 500 // (len(partners) * max(len(rest), 1)) - 0)
    per_call = min(per_call, 3)
    for y in range(cfg["years"]["trade_first"], cfg["years"]["trade_last"] + 1):
        pending = []
        for m in cfg["markets"]:
            frames.append(comtrade([m["comtrade"]], partners, main, y, "M", f"imports_{m['iso3']}_{y}_00"))
            if rest:
                tag1 = f"imports_{m['iso3']}_{y}_01"
                if _comtrade_cache_exists([m["comtrade"]], partners, rest, y, "M", tag1):
                    frames.append(comtrade([m["comtrade"]], partners, rest, y, "M", tag1))
                else:
                    pending.append(m)
        for i in range(0, len(pending), per_call):
            grp = pending[i:i + per_call]
            tag = f"imports_multi_{y}_{'-'.join(g['iso3'] for g in grp)}"
            frames.append(comtrade([g["comtrade"] for g in grp], partners, rest, y, "M", tag))
        log.info("Comtrade imports collected for %s", y)
    return pd.concat(frames, ignore_index=True)


def collect_total_imports(cfg: dict) -> pd.DataFrame:
    """All-product total imports from India, China, World (for mirror RCA)."""
    partners = [cfg["partners"][k]["comtrade"] for k in ("india", "china", "world")]
    reps = [m["comtrade"] for m in cfg["markets"]]
    frames = []
    for y in range(cfg["years"]["trade_first"], cfg["years"]["trade_last"] + 1):
        frames.append(comtrade(reps, partners, ["TOTAL"], y, "M", f"totals_{y}"))
    return pd.concat(frames, ignore_index=True)


# --------------------------------------------------------------------------- #
# WITS / TRAINS tariffs
# --------------------------------------------------------------------------- #
_SERIES = re.compile(r"<Series ([^>]*)>(.*?)</Series>", re.S)
_ATTR = re.compile(r'(\w+)="([^"]*)"')
_OBS = re.compile(r"<Obs ([^>]*)/>")


def parse_trains(xml: str) -> list[dict]:
    rows = []
    if not xml or xml.startswith("NoRecordsFound"):
        return rows
    for sattr, body in _SERIES.findall(xml):
        s = dict(_ATTR.findall(sattr))
        for oattr in _OBS.findall(body):
            o = dict(_ATTR.findall(oattr))
            rows.append({
                "reporter": s.get("REPORTER"), "partner": s.get("PARTNER"),
                "hs6": s.get("PRODUCTCODE"), "year": int(o["TIME_PERIOD"]),
                "rate": float(o["OBS_VALUE"]) if o.get("OBS_VALUE") not in (None, "") else None,
                "tariff_type": o.get("TARIFFTYPE"),
                "n_lines": int(float(o.get("TOTALNOOFLINES", 0) or 0)),
                "n_pref_lines": int(float(o.get("NBR_PREF_LINES", 0) or 0)),
                "n_mfn_lines": int(float(o.get("NBR_MFN_LINES", 0) or 0)),
                "n_na_lines": int(float(o.get("NBR_NA_LINES", 0) or 0)),
                "min_rate": o.get("MIN_RATE"), "max_rate": o.get("MAX_RATE"),
                "nomen": o.get("NOMENCODE"),
            })
    return rows


def collect_tariffs(cfg: dict, products: list[str]) -> pd.DataFrame:
    partners = ";".join(cfg["partners"][k]["wits"] for k in ("world", "india", "china"))
    rows = []
    chunk = 20  # WITS URL length limit
    chunks = [products[i:i + chunk] for i in range(0, len(products), chunk)]
    for m in cfg["markets"]:
        for i, ch in enumerate(chunks):
            url = (f"{WITS_TRN}/reporter/{m['wits']}/partner/{partners}/product/"
                   f"{';'.join(ch)}/year/all/datatype/reported")
            h = hashlib.md5(url.encode()).hexdigest()[:8]
            cache = p("data", "raw", "wits", f"trains_{m['iso3']}_{i:02d}_{h}.xml")
            rows += parse_trains(_get(url, cache, pause=0.8))
        log.info("TRAINS tariffs collected for %s", m["name"])
    return pd.DataFrame(rows)


def collect_pref_presence(cfg: dict, probe_products: list[str]) -> pd.DataFrame:
    """For each market-year, does TRAINS report ANY country-specific preferential
    series (for any partner)?  Used to distinguish 'India/China genuinely face MFN'
    from 'preferential schedule not yet loaded in TRAINS for that year'."""
    rows = []
    y0, y1 = cfg["years"]["tariff_first"], cfg["years"]["trade_last"]
    for m in cfg["markets"]:
        for y in range(y0, y1 + 1):  # partner=all & year=all is "payload too large"
            url = (f"{WITS_TRN}/reporter/{m['wits']}/partner/all/product/"
                   f"{';'.join(probe_products)}/year/{y}/datatype/reported")
            h = hashlib.md5(url.encode()).hexdigest()[:8]
            cache = p("data", "raw", "wits", f"prefprobe_{m['iso3']}_{y}_{h}.xml")
            recs = parse_trains(_get(url, cache, pause=0.5))
            n_pref = sum(r["tariff_type"] == "PREF" for r in recs)
            rows.append({"iso3": m["iso3"], "year": y, "n_pref_series": int(n_pref),
                         "n_series": len(recs)})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# World Bank WDI
# --------------------------------------------------------------------------- #
WDI_INDICATORS = {
    "NY.GDP.MKTP.CD": "gdp_usd",
    "NY.GDP.MKTP.KD.ZG": "gdp_growth_pct",
    "FP.CPI.TOTL.ZG": "inflation_pct",
    "PA.NUS.FCRF": "fx_lcu_per_usd",
}


def collect_wdi(cfg: dict) -> pd.DataFrame:
    codes = ";".join(m["wdi"] for m in cfg["markets"])
    frames = []
    for ind, name in WDI_INDICATORS.items():
        url = f"{WDI}/country/{codes}/indicator/{ind}"
        cache = p("data", "raw", "wdi", f"{ind}.json")
        txt = _get(url, cache, params={"format": "json", "date": "2010:2025", "per_page": 2000})
        js = json.loads(txt)
        data = js[1] if len(js) > 1 and js[1] else []
        frames.append(pd.DataFrame([{
            "wdi": r["countryiso3code"] or r["country"]["id"], "year": int(r["date"]),
            "indicator": name, "value": r["value"]} for r in data]))
    return pd.concat(frames, ignore_index=True)


# --------------------------------------------------------------------------- #
def run_collection(cfg: dict | None = None) -> None:
    cfg = cfg or load_config()
    download_hs_tables()
    stable = stable_hs6_codes()
    stable.to_csv(p("data", "processed", "hs6_stable_codes.csv"), index=False)
    uni = collect_universe_exports(cfg, stable)
    uni.to_csv(p("data", "processed", "universe_exports_raw.csv"), index=False)
    from .data_cleaning import select_product_universe
    products = select_product_universe(cfg, stable, uni)
    codes = products.hs6.tolist()
    collect_bilateral_imports(cfg, codes).to_csv(p("data", "processed", "imports_raw.csv"), index=False)
    collect_total_imports(cfg).to_csv(p("data", "processed", "totals_raw.csv"), index=False)
    collect_tariffs(cfg, codes).to_csv(p("data", "processed", "tariffs_raw.csv"), index=False)
    collect_pref_presence(cfg, codes[:4]).to_csv(p("data", "processed", "pref_presence.csv"), index=False)
    collect_wdi(cfg).to_csv(p("data", "processed", "wdi_raw.csv"), index=False)
    log.info("Collection complete")


if __name__ == "__main__":
    run_collection()
