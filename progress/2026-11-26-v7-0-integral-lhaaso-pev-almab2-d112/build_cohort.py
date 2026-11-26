#!/home/martin/SETI_Fortsaettelse_2026-11-14/.venv/bin/python3
"""
Phase D112 (V7.0) Stage-1 Metadata-Only Cohort Builder & Prospective Seal:
  - Queries ONLY public metadata catalogs/listings (HEASARC INTEGRAL Reference Catalog
    `gnrl_refr_cat.fits`, HEASARC directory indexes `spectra/` & `agn/`, VizieR `1LHAASO`
    `J/ApJS/271/25/catalog`, VizieR `I/355/gaiadr3`, ATNF `B/psr/psr`, NASA NED JSON,
    and ALMA Band 2 SV Science Portal MOUS README metadata).
  - NEVER downloads raw science files; asserts `inputs_d112_v7_0` does NOT exist at seal.
  - Enforces strict 0-overlap against all 37 prior Companion Archives A-AK (`D001-D111`).
  - Adds +5 spectrographs (`INTEGRAL_IBIS_ISGRI`, `INTEGRAL_JEMX`, `INTEGRAL_SPI`,
    `LHAASO_WCDA`, `LHAASO_KM2A`: 67 -> 72) and +6 spectral arms (adding those 5 plus
    `ALMA_B2_3MM`: 98 -> 104, completing 10/10 ALMA Bands B1-B10 and extending the HE
    frontier to 1.000 PeV / 1.239842e-15 um = 62.582 EM octaves).
  - Seals 7 immutable Stage-1 files into `METHOD_LOCK.json` and `LOCK_RECEIPT.json`.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from astropy.io import fits

WS = Path(__file__).resolve().parent
ROOT = WS.parent.parent
ARCHIVES_DIR = ROOT / "archives"
RAW_DIR = ROOT / "inputs_d112_v7_0"
ARCHIVE_AK = ARCHIVES_DIR / "SETI_D111_V6_9_LM_MIDIR_QCL_MOLECULAR_CCF_RESULTS_2026-11-26.zip"
ARCHIVE_AK_SHA = "36cf7b892972845db68a623216778e7213f519bf21b59b652a8d1e3af3a79802"

sys.path.insert(0, str(WS))
import v7_0_detector as det  # noqa: E402

HEASARC_SP_URL = "https://heasarc.gsfc.nasa.gov/FTP/integral/high_level/spectra/"
HEASARC_AGN_URL = "https://heasarc.gsfc.nasa.gov/FTP/integral/high_level/agn/"
HEASARC_REFR_CAT_URL = "https://heasarc.gsfc.nasa.gov/FTP/integral/data/cat/hec/gnrl_refr_cat.fits"
HEASARC_JMX2_RMF_URL = "https://heasarc.gsfc.nasa.gov/FTP/integral/data/ic/jmx2/rsp/jmx2_rmf_grp_0005.fits"
VIZIER_BASE = "https://vizier.cfa.harvard.edu/viz-bin/asu-tsv"
VIZIER_1LHAASO_FITS_URL = "https://vizier.cfa.harvard.edu/viz-bin/asu-fits?-source=J/ApJS/271/25/catalog&-out.max=500"
ZENODO_J2108_URL = "https://zenodo.org/api/records/24186127/files/LHAASO_J2108_data_release_v1.0.0.tar.gz/content"
ZENODO_LHAASO13_URL = "https://zenodo.org/api/records/24128953/files/JHEAp_zenodo_data_20261111.zip/content"
ALMA_X36_URL = "https://almascience.org/almadata/sciver/ARP220Band2/X36_spectralscan_75-100GHz/ARP220_X36_RefImages_manual.tgz"
ALMA_X52_URL = "https://almascience.org/almadata/sciver/ARP220Band2/X52_109-116GHz/ARP220_X52_RefImages_manual.tgz"

COHORT_COLS = [
    "instrument", "canonical_target", "common_name", "role", "subrole",
    "panchromatic_bridge", "is_prior_bridge", "s_ra", "s_dec", "dist_pc", "within_10pc",
    "phot_g_mag", "j_mag", "h_mag", "ks_mag", "teff_k", "n_exoplanets",
    "dp_id", "obs_id", "band_or_subband", "regime", "scale_regime",
    "f1_rel", "f1_url", "aux_rels", "aux_urls", "est_bytes", "min_prior_sep_arcsec",
]

# Known astrophysical distances [pc] (Gaia/parallax/VLBI/ATNF/NED reference distances for new targets when parallax < 3 sigma)
DEFAULT_GALACTIC_DIST_PC: dict[str, tuple[float, str, float]] = {
    "SS433":      (5500.0,  "HMXB/Microquasar (LHAASO J1913+0501 + INTEGRAL)", 25000.0),
    "XPER":       (600.0,   "Be/XRB PSR (Gaia DR3)", 41186.0),
    "GRS1915":    (8600.0,  "Microquasar BH-XRB (Reid+2014 VLBI)", 18000.0),
    "CYGX2":      (7200.0,  "LMXB Neutron Star", 14210.0),
    "GROJ1655":   (3200.0,  "BH-XRB Microquasar", 6500.0),
    "CIRX1":      (9400.0,  "NS-XRB SNR G321.9-0.3", 15000.0),
    "GAMCAS":     (168.0,   "Be Star Hard X-ray", 25000.0),
    "J0007P7303": (1400.0,  "CTA 1 SNR / PSR J0007+7303 (ATNF)", 0.0),
    "J0542P2311": (1565.0,  "LHAASO J0542+2311u / PSR J0543+2329", 0.0),
    "J1825M1256": (3900.0,  "HESS J1826-130 / PSR J1826-1256", 0.0),
    "J1825M1337": (3900.0,  "HESS J1825-137 PWN / PSR J1826-1334", 0.0),
    "J1839M0548": (5000.0,  "LHAASO J1839-0545 / HESS J1841-055", 0.0),
    "J1848M0001": (7000.0,  "IGR J18490-0000 PWN", 0.0),
    "J1857P0203": (9000.0,  "HESS J1858+020 / W44 region", 0.0),
    "J1908P0615": (2370.0,  "MGRO J1908+06 / PSR J1907+0602", 0.0),
    "J1928P1746": (4340.0,  "1LHAASO J1928+1746u / PSR J1928+1746", 0.0),
    "J2018P3643": (10000.0, "MGRO J2019+37 / PSR J2021+3651", 0.0),
    "J2031P4127": (1700.0,  "PSR J2032+4127 / Cyg OB2 PeVatron", 0.0),
    "J2108P5153": (3280.0,  "1LHAASO J2108+5153u Dark PeVatron (1.0 PeV SED)", 0.0),
    "J2228P6100": (800.0,   "SNR G106.3+02.7 / Boomerang PeVatron", 0.0),
    "J0206P4302": (3000.0,  "1LHAASO J0206+4302u Point UHE", 0.0),
    "J0216P4237": (3000.0,  "1LHAASO J0216+4237u Point UHE", 0.0),
    "J0056P6346": (2500.0,  "1LHAASO J0056+6346u PeV Candidate", 0.0),
    "J0343P5254": (2500.0,  "1LHAASO J0343+5254u", 0.0),
    "J0359P5406": (2500.0,  "1LHAASO J0359+5406", 0.0),
    "J0428P5531": (2500.0,  "1LHAASO J0428+5531", 0.0),
    "J0622P3754": (1600.0,  "1LHAASO J0622+3754u PWN", 0.0),
    "J0635P0619": (2000.0,  "1LHAASO J0635+0619 Monoceros", 0.0),
    "J1740P0948": (1230.0,  "1LHAASO J1740+0948u / PSR J1740+1000", 0.0),
    "J1809M1918": (3300.0,  "1LHAASO J1809-1918u / HESS J1809-193", 0.0),
    "J1954P2836": (9200.0,  "1LHAASO J1954+2836u / PSR J1954+2836", 0.0),
}


def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _ang_sep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    c = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    return math.degrees(math.acos(max(-1.0, min(1.0, c)))) * 3600.0


def _canon_key(s: str) -> str:
    return "".join(ch for ch in s.upper() if ch.isalnum())


def _fetch_bytes(url: str, timeout: int = 45) -> bytes:
    last_err: Exception | None = None
    for attempt in range(5):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETI-D112-Stage1/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as exc:
            last_err = exc
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"Metadata query failed for {url}: {last_err}")


def _ned_lookup(name: str) -> tuple[float | None, float | None, float | None]:
    try:
        u = "https://ned.ipac.caltech.edu/srs/ObjectLookup?of=json&name=" + urllib.parse.quote(name)
        j = json.loads(_fetch_bytes(u, timeout=20).decode("utf-8", "ignore"))
        pref = j.get("Preferred", {})
        pos = pref.get("Position", {})
        z = (pref.get("Redshift") or {}).get("Value")
        ra = float(pos["RA"]) if pos.get("RA") is not None else None
        dec = float(pos["Dec"]) if pos.get("Dec") is not None else None
        zv = float(z) if z is not None else None
        return ra, dec, zv
    except Exception:
        return None, None, None


def _z_to_dl_pc(z: float) -> float:
    # Flat LCDM approximation accurate at low-to-moderate z (H0=67.4 km/s/Mpc, c=299792.458)
    z = max(1e-5, float(z))
    dh_mpc = det.C_KMS / 67.4
    dl_mpc = dh_mpc * z * (1.0 + 0.77 * z) / (1.0 + 0.0)
    return dl_mpc * 1.0e6


def _build_prior_v69_snapshot_and_exclusions() -> tuple[
    dict[str, Any], list[dict[str, Any]], set[str], list[str], dict[str, tuple[float, float]], dict[str, dict[str, str]]
]:
    assert ARCHIVE_AK.exists(), f"Missing Archive AK: {ARCHIVE_AK}"
    assert _sha256_file(ARCHIVE_AK) == ARCHIVE_AK_SHA, "Archive AK SHA-256 mismatch!"

    with zipfile.ZipFile(ARCHIVE_AK) as zf:
        def _zcsv(suffix: str) -> list[dict[str, str]]:
            nm = next(n for n in zf.namelist() if n.endswith(suffix))
            return list(csv.DictReader(io.StringIO(zf.read(nm).decode("utf-8"))))

        def _zjson(suffix: str) -> Any:
            nm = next(n for n in zf.namelist() if n.endswith(suffix))
            return json.loads(zf.read(nm).decode("utf-8"))

        pex_prev = _zjson("PRIOR_EXCLUSION_VERIFICATION.json")
        fc_prev = _zcsv("FROZEN_COHORT_D111.csv")
        uni_prev = _zcsv("UNIFIED_PANCHROMATIC_V6_9_SYNTHESIS_1039STARS.csv")
        br_prev = _zcsv("PANCHROMATIC_BRIDGE_197STARS_V69.csv")
        ell_prev = _zcsv("MULTIEVENT_ELLIPSOID_1039STARS.csv")
        comb_prev = _zcsv("ALLSKY_COMB_V4_1_UNIFIED_D079_D111.csv")
        sum_prev = _zjson("SUMMARY.json")

    prior_coords: list[dict[str, Any]] = list(pex_prev["excluded_targets_coordinate_registry"])
    ell_coords_by_star: dict[str, tuple[float, float]] = {}
    for er in ell_prev:
        st = er["star"]
        ell_coords_by_star[st] = (float(er["ra_deg"]), float(er["dec_deg"]))

    # Also merge D111 new stars into prior_coords so excluded_targets_coordinate_registry is complete A-AK
    seen_star_coords: set[str] = {str(c.get("canonical_target") or "").upper() for c in prior_coords if c.get("canonical_target")}
    for r in fc_prev:
        st = r["canonical_target"]
        if st.upper() not in seen_star_coords:
            prior_coords.append({"canonical_target": st, "ra_deg": float(r["s_ra"]), "dec_deg": float(r["s_dec"])})
            seen_star_coords.add(st.upper())

    prior_dp_ids: set[str] = set(pex_prev["excluded_dp_ids"])
    for r in fc_prev:
        if r.get("dp_id"):
            prior_dp_ids.add(r["dp_id"])
        if r.get("obs_id"):
            prior_dp_ids.add(r["obs_id"])
    fmt_probes: list[str] = list(pex_prev["format_check_excluded_dp_ids"])

    snap = {
        "schema": "D112_PRIOR_V6_9_SNAPSHOT",
        "source_archive": ARCHIVE_AK.name,
        "source_archive_sha256": ARCHIVE_AK_SHA,
        "prior_unified_1039_rows": uni_prev,
        "prior_bridge_rows": br_prev,
        "prior_ellipsoid_1039_rows": ell_prev,
        "prior_comb_unified_rows": comb_prev,
        "d111_summary_headline": sum_prev["unified_panchromatic_v6_9_synthesis"],
        "d111_calibration_summary": {
            "n_suites": sum_prev["synthetic_calibration_8511_trials"]["n_suites"],
            "total_trials": sum_prev["synthetic_calibration_8511_trials"]["total_trials"],
            "total_passed": sum_prev["synthetic_calibration_8511_trials"]["total_passed"],
        },
        "cumulative_trials_through_d111": 104856,
    }
    uni_by_star = {r["star"]: r for r in uni_prev}
    return snap, prior_coords, prior_dp_ids, fmt_probes, ell_coords_by_star, uni_by_star


def main() -> int:
    assert not RAW_DIR.exists(), f"{RAW_DIR} MUST NOT exist before Stage-1 seal!"
    snap, prior_coords, prior_dp_ids, fmt_probes, ell_coords_by_star, uni_by_star = _build_prior_v69_snapshot_and_exclusions()
    excl_all_dp = prior_dp_ids | set(fmt_probes)

    # Coordinate index with canonical star name where known (prioritize ell_coords_by_star)
    all_prior_pts: list[tuple[str, float, float]] = [(st, ra, dec) for st, (ra, dec) in ell_coords_by_star.items()]
    for e in prior_coords:
        nm = str(e.get("canonical_target") or "").strip()
        ra = e.get("ra_deg", e.get("ra", e.get("s_ra")))
        dec = e.get("dec_deg", e.get("dec", e.get("s_dec")))
        if ra is not None and dec is not None:
            all_prior_pts.append((nm, float(ra), float(dec)))

    def _find_prior_match(ra: float, dec: float) -> tuple[str | None, float]:
        best_sep = 1e9
        best_nm: str | None = None
        for nm, pr_ra, pr_dec in all_prior_pts:
            s = _ang_sep_arcsec(ra, dec, pr_ra, pr_dec)
            if s < best_sep:
                best_sep = s
                if nm:
                    best_nm = nm
        # Check named stars in ell_coords_by_star specifically for canonical star match < 180"
        best_named_sep = 1e9
        best_named = None
        for nm, (pr_ra, pr_dec) in ell_coords_by_star.items():
            s = _ang_sep_arcsec(ra, dec, pr_ra, pr_dec)
            if s < best_named_sep:
                best_named_sep = s
                best_named = nm
        if best_named_sep <= 180.0 and best_named:
            return best_named, best_sep
        return None, best_sep

    print("1. Loading metadata catalogs (HEASARC gnrl_refr_cat, spectra/agn HTML, VizieR 1LHAASO)...", flush=True)
    raw_cat = _fetch_bytes(HEASARC_REFR_CAT_URL, timeout=90)
    cat_by_key: dict[str, tuple[str, float, float, int]] = {}
    with fits.open(io.BytesIO(raw_cat)) as hdul:
        for r in hdul[1].data:
            nm = str(r["NAME"]).strip()
            ck = _canon_key(nm)
            cat_by_key[ck] = (nm, float(r["RA_OBJ"]), float(r["DEC_OBJ"]), int(r["CLASS"]))

    sp_html = _fetch_bytes(HEASARC_SP_URL, timeout=30).decode("utf-8", "ignore")
    sp_available = set(re.findall(r'href="([^"]+)_sum_pha\.fits\.gz"', sp_html))
    agn_html = _fetch_bytes(HEASARC_AGN_URL, timeout=30).decode("utf-8", "ignore")
    jemx_available = set(re.findall(r'href="([^"]+)_sum_pha\.fits"', agn_html))
    spi_available = set(re.findall(r'href="([^"]+)_SPI\.fits\.gz"', agn_html))

    # Query 1LHAASO VizieR table (metadata only!)
    lhaaso_tsv = _fetch_bytes(
        f"{VIZIER_BASE}?-source=J/ApJS/271/25/catalog&-out.max=500", timeout=30
    ).decode("utf-8", "ignore")
    dl = [l for l in lhaaso_tsv.splitlines() if l.strip() and not l.startswith("#")]
    lh_hdr = dl[0].split("\t")
    lh_rows = [dict(zip(lh_hdr, l.split("\t"))) for l in dl[3:]]
    lhaaso_unique: dict[str, dict[str, Any]] = {}
    for r in lh_rows:
        lid = r["1LHAASO"].strip()
        if lid not in lhaaso_unique:
            lhaaso_unique[lid] = {
                "lid": lid,
                "ra": float(r["RAJ2000"]),
                "dec": float(r["DEJ2000"]),
                "r39": float(r["r39"]) if r["r39"].strip() else 0.0,
                "assoc": r.get("Assoc", "").strip(),
                "ts_max": 0.0,
                "ts100": 0.0,
                "comps": set(),
            }
        lhaaso_unique[lid]["comps"].add(r["Comp"].strip())
        lhaaso_unique[lid]["ts_max"] = max(lhaaso_unique[lid]["ts_max"], float(r["TS"]))
        if r.get("TS100", "").strip():
            lhaaso_unique[lid]["ts100"] = max(lhaaso_unique[lid]["ts100"], float(r["TS100"]))

    # Helper to resolve AGN / Galactic target metadata strictly cleanly
    new_target_meta: dict[str, dict[str, Any]] = {}
    new_pts_list: list[tuple[str, float, float]] = []

    def _register_target(canon_hint: str, ra: float, dec: float, common: str, subrole: str, dist_pc: float, ned_query: str | None = None) -> tuple[str, bool, float] | None:
        m_star, m_sep = _find_prior_match(ra, dec)
        if m_star is not None:
            return m_star, True, round(m_sep, 2)
        if m_sep < 600.0:
            # Avoid ambiguous 180"-600" neighbor zone!
            return None
        # Check if already registered in D112 new targets within 600" -> merge!
        for ex_st, ex_ra, ex_dec in new_pts_list:
            if _ang_sep_arcsec(ra, dec, ex_ra, ex_dec) < 600.0:
                return ex_st, False, round(m_sep, 2)
        d_eff = float(dist_pc)
        if ned_query and d_eff <= 0.0:
            n_ra, n_dec, n_z = _ned_lookup(ned_query)
            if n_z is not None and n_z > 0.0:
                d_eff = _z_to_dl_pc(n_z)
            if n_ra is not None and n_dec is not None:
                ra, dec = n_ra, n_dec
        if d_eff <= 0.0:
            d_eff = 5000.0
        canon = _canon_key(canon_hint)
        new_pts_list.append((canon, ra, dec))
        new_target_meta[canon] = {
            "canon": canon, "common_name": common, "subrole": subrole,
            "ra": round(ra, 6), "dec": round(dec, 6),
            "dist_pc": round(d_eff, 4), "min_prior_sep_arcsec": round(m_sep, 2),
        }
        return canon, False, round(m_sep, 2)

    # Pre-resolve shared multi-instrument INTEGRAL targets in priority order
    # Priority: all ISGRI targets + JEMX + SPI -> resolves overlaps across IBIS/JEM-X/SPI cleanly
    isgri_specs = [
        # (file_stem, refr_key, canon_hint, common_label, subrole, ned_q)
        ("Crab",            "Crab",           "CRABNEBULA", "Crab Nebula PWN", "PWN_INTEGRAL", None),
        ("Cen_A",           "Cen A",          "CENA",       "Cen A Radio Galaxy", "AGN_INTEGRAL", None),
        ("3C_273",          "3C 273",         "3C273",      "3C 273 Quasar", "AGN_INTEGRAL", None),
        ("3C_279",          "3C 279",         "3C279",      "3C 279 Blazar", "AGN_INTEGRAL", None),
        ("Cas_A",           "Cas A",          "CASA",       "Cas A SNR", "SNR_INTEGRAL", None),
        ("Cyg_X-3",         "Cyg X-3",        "CYGX3",      "Cyg X-3 Microquasar", "XRB_INTEGRAL", None),
        ("Her_X-1",         "Her X-1",        "HERX1",      "Her X-1 XRB Pulsar", "XRB_INTEGRAL", None),
        ("Vela_Pulsar",     "Vela Pulsar",    "VELAPSR",    "Vela Pulsar PWN", "PSR_INTEGRAL", None),
        ("Vela_X-1",        "Vela X-1",       "VELAX1",     "Vela X-1 HMXB", "XRB_INTEGRAL", None),
        ("Mrk_501",         "Mrk 501",        "MRK501",     "Mrk 501 Blazar", "AGN_INTEGRAL", None),
        ("NGC_4151",        "NGC 4151",       "NGC4151",    "NGC 4151 Seyfert 1", "AGN_INTEGRAL", None),
        ("SS_Cyg",          "SS Cyg",         "SSCYG",      "SS Cyg Cataclysmic Var.", "CV_INTEGRAL", None),
        ("V1223_Sgr",       "V1223 Sgr",      "V1223SGR",   "V1223 Sgr Polar CV", "CV_INTEGRAL", None),
        ("IC_4329A",        "IC 4329A",       "IC4329A",    "IC 4329A Seyfert 1", "AGN_INTEGRAL", None),
        ("NGC_4593",        "NGC 4593",       "NGC4593",    "NGC 4593 Seyfert 1", "AGN_INTEGRAL", None),
        ("NGC_4945",        "NGC 4945",       "NGC4945",    "NGC 4945 Starburst AGN", "AGN_INTEGRAL", None),
        ("3C_111",          "3C 111",         "3C111",      "3C 111 Radio Galaxy", "AGN_INTEGRAL", None),
        ("3C_120",          "3C 120",         "3C120",      "3C 120 Seyfert 1", "AGN_INTEGRAL", None),
        ("gam_Cas",         "Gam Cas",        "GAMCAS",     "Gam Cas Be Star", "BE_XRAY_INTEGRAL", None),
        ("PSR_B1509-58",    "PSR B1509-58",   "PSRB1509",   "PSR B1509-58 PWN", "PSR_INTEGRAL", None),
        ("GX_339-4",        "GX 339-4",       "GX339M4",    "GX 339-4 BH-XRB", "XRB_INTEGRAL", None),
        ("Circinus_Galaxy", "Circinus Galaxy","CIRCINUS",   "Circinus Seyfert 2", "AGN_INTEGRAL", None),
        # Brand-new high-S/N INTEGRAL targets:
        ("SS_433",          "SS 433",         "SS433",      "SS 433 Microquasar (XRB+LHAASO)", "MICROQUASAR_XRB", None),
        ("X_Per",           "X Per",          "XPER",       "X Per Be/XRB Pulsar", "HMXB_BE_INTEGRAL", None),
        ("GRS_1915+105",    "GRS 1915+105",   "GRS1915",    "GRS 1915+105 Microquasar", "MICROQUASAR_XRB", None),
        ("Cyg_X-2",         "Cyg X-2",        "CYGX2",      "Cyg X-2 NS-LMXB", "LMXB_INTEGRAL", None),
        ("GRO_J1655-40",    "GRO J1655-40",   "GROJ1655",   "GRO J1655-40 BH-XRB", "BHXRB_INTEGRAL", None),
        ("Cir_X-1",         "Cir X-1",        "CIRX1",      "Cir X-1 NS-XRB", "NSXRB_INTEGRAL", None),
        ("3C_454.3",        "3C 454.3",       "3C454P3",    "3C 454.3 Blazar", "BLAZAR_INTEGRAL", "3C 454.3"),
        ("Mrk_3",           "Mrk 3",          "MRK3",       "Mrk 3 Seyfert 2", "AGN_INTEGRAL", "Mrk 3"),
        ("Mrk_6",           "Mrk 6",          "MRK6",       "Mrk 6 Seyfert 1.5", "AGN_INTEGRAL", "Mrk 6"),
        ("NGC_3227",        "NGC 3227",       "NGC3227",    "NGC 3227 Seyfert 1.5", "AGN_INTEGRAL", "NGC 3227"),
        ("NGC_4388",        "NGC 4388",       "NGC4388",    "NGC 4388 Seyfert 2", "AGN_INTEGRAL", "NGC 4388"),
        ("MCG-06-30-015",   "MCG-06-30-015",  "MCG0630015", "MCG-06-30-015 Seyfert 1", "AGN_INTEGRAL", "MCG-06-30-015"),
        ("NGC_7172",        "NGC 7172",       "NGC7172",    "NGC 7172 Seyfert 2", "AGN_INTEGRAL", "NGC 7172"),
    ]

    cohort_rows: list[dict[str, Any]] = []

    def _emit_row(
        inst: str, st: str, is_br: bool, msep: float, dp_id: str, obs_id: str,
        band_s: str, scale_reg: str, f1_rel: str, f1_url: str,
        aux_rels: list[str], aux_urls: list[str], est_b: int,
    ) -> None:
        if is_br:
            ur = uni_by_star[st]
            ra0, dec0 = ell_coords_by_star[st]
            common = ur["common_name"]
            role = ur["role"]
            subrole = ur["subrole"]
            dist_pc = float(ur["dist_pc"])
            w10 = dist_pc <= 10.0
            gm, jm, hm, km = ur.get("phot_g_mag",""), ur.get("j_mag",""), ur.get("h_mag",""), ur.get("ks_mag","")
            teff = ur.get("teff_k","5000.0")
            npl = ur.get("n_exoplanets","0")
            msep_eff = 0.0
        else:
            bm = new_target_meta[st]
            ra0, dec0 = bm["ra"], bm["dec"]
            common = bm["common_name"]
            role = "CONTROL"
            subrole = bm["subrole"]
            dist_pc = float(bm["dist_pc"])
            w10 = dist_pc <= 10.0
            gm = jm = hm = km = ""
            teff = f"{DEFAULT_GALACTIC_DIST_PC.get(st, (0, '', 0.0))[2]:.1f}" if st in DEFAULT_GALACTIC_DIST_PC and DEFAULT_GALACTIC_DIST_PC[st][2] > 0 else "10000.0"
            npl = "0"
            msep_eff = bm["min_prior_sep_arcsec"]

        reg = "MM" if inst.startswith("ALMA_") else ("VHE" if inst.startswith("LHAASO_") else "GAMMA_SOFT")
        cohort_rows.append({
            "instrument": inst,
            "canonical_target": st,
            "common_name": common,
            "role": role,
            "subrole": subrole,
            "panchromatic_bridge": str(is_br),
            "is_prior_bridge": str(is_br),
            "s_ra": f"{ra0:.6f}",
            "s_dec": f"{dec0:.6f}",
            "dist_pc": f"{dist_pc:.5f}",
            "within_10pc": str(w10),
            "phot_g_mag": gm, "j_mag": jm, "h_mag": hm, "ks_mag": km,
            "teff_k": teff, "n_exoplanets": npl,
            "dp_id": dp_id, "obs_id": obs_id, "band_or_subband": band_s,
            "regime": reg, "scale_regime": scale_reg,
            "f1_rel": f1_rel, "f1_url": f1_url,
            "aux_rels": "|".join(aux_rels), "aux_urls": "|".join(aux_urls),
            "est_bytes": est_b, "min_prior_sep_arcsec": msep_eff,
        })

    # 2. Freeze INTEGRAL IBIS/ISGRI rows
    print("2. Freezing INTEGRAL IBIS/ISGRI, JEM-X, and SPI rows...", flush=True)
    for stem, rkey, chint, clbl, subr, nq in isgri_specs:
        if stem not in sp_available:
            continue
        ck = _canon_key(rkey)
        hit = cat_by_key.get(ck)
        if not hit:
            continue
        _, ra, dec, _ = hit
        d_def = DEFAULT_GALACTIC_DIST_PC.get(_canon_key(chint), (0.0, "", 0.0))[0]
        reg_t = _register_target(chint, ra, dec, clbl, subr, d_def, ned_query=nq)
        if reg_t is None:
            continue
        st, is_br, msep = reg_t
        dp = f"INT_ISGRI_{stem}"
        assert dp not in excl_all_dp
        _emit_row(
            "INTEGRAL_IBIS_ISGRI", st, is_br, msep, dp, dp, "13-970.88keV_511", "HE_ISOTROPIC",
            f"INTEGRAL_IBIS_ISGRI/{st}/{stem}_sum_pha.fits.gz", f"{HEASARC_SP_URL}{stem}_sum_pha.fits.gz",
            [f"INTEGRAL_IBIS_ISGRI/{st}/{stem}_sum_arf.fits.gz", f"INTEGRAL_IBIS_ISGRI/{st}/{stem}_rmf.fits.gz"],
            [f"{HEASARC_SP_URL}{stem}_sum_arf.fits.gz", f"{HEASARC_SP_URL}{stem}_rmf.fits.gz"],
            180000,
        )

    # INTEGRAL JEM-X (agn/ 256-ch 3-35 keV)
    jemx_specs = [
        ("3C273",       "3C 273",        "3C273",      "3C 273 Quasar",        "AGN_INTEGRAL", None),
        ("3C279",       "3C 279",        "3C279",      "3C 279 Blazar",        "AGN_INTEGRAL", None),
        ("IC4329A",     "IC 4329A",      "IC4329A",    "IC 4329A Seyfert 1",   "AGN_INTEGRAL", None),
        ("NGC4593",     "NGC 4593",      "NGC4593",    "NGC 4593 Seyfert 1",   "AGN_INTEGRAL", None),
        ("NGC1275",     "NGC 1275",      "NGC1275",    "NGC 1275 Perseus A",   "AGN_INTEGRAL", None),
        ("MRK509",      "Mrk 509",       "MRK509",     "Mrk 509 Seyfert 1",    "AGN_INTEGRAL", None),
        ("MRK3",        "Mrk 3",         "MRK3",       "Mrk 3 Seyfert 2",      "AGN_INTEGRAL", "Mrk 3"),
        ("MRK6",        "Mrk 6",         "MRK6",       "Mrk 6 Seyfert 1.5",    "AGN_INTEGRAL", "Mrk 6"),
        ("NGC4388",     "NGC 4388",      "NGC4388",    "NGC 4388 Seyfert 2",   "AGN_INTEGRAL", "NGC 4388"),
        ("MCG-06-30-015","MCG-06-30-015","MCG0630015", "MCG-06-30-015 Sy1",    "AGN_INTEGRAL", "MCG-06-30-015"),
        ("CygnusA",     "Cyg A",         "CYGNUSA",    "Cygnus A Radio Gal.",  "AGN_INTEGRAL", "Cygnus A"),
        ("NGC5506",     "NGC 5506",      "NGC5506",    "NGC 5506 Seyfert 1.9", "AGN_INTEGRAL", "NGC 5506"),
        ("NGC6814",     "NGC 6814",      "NGC6814",    "NGC 6814 Seyfert 1.5", "AGN_INTEGRAL", "NGC 6814"),
        ("NGC4736",     "NGC 4736",      "NGC4736",    "NGC 4736 M94 LINER",   "AGN_INTEGRAL", "NGC 4736"),
        ("0716",        "QSO B0716+714", "QSOB0716",   "S5 0716+714 Blazar",   "BLAZAR_INTEGRAL", "S5 0716+71"),
        ("0836",        "QSO B0836+710", "QSOB0836",   "S5 0836+710 Blazar",   "BLAZAR_INTEGRAL", "S5 0836+71"),
    ]
    for stem, rkey, chint, clbl, subr, nq in jemx_specs:
        if stem not in jemx_available:
            continue
        hit = cat_by_key.get(_canon_key(rkey))
        if hit:
            _, ra, dec, _ = hit
            d0 = 0.0
        else:
            ra, dec, z0 = _ned_lookup(nq or rkey)
            if ra is None or dec is None:
                continue
            d0 = _z_to_dl_pc(z0) if z0 else 5.0e7
        reg_t = _register_target(chint, ra, dec, clbl, subr, d0, ned_query=nq)
        if reg_t is None:
            continue
        st, is_br, msep = reg_t
        dp = f"INT_JEMX_{stem}"
        assert dp not in excl_all_dp
        arf_stem = "MCG6" if stem == "MCG-06-30-015" else stem
        _emit_row(
            "INTEGRAL_JEMX", st, is_br, msep, dp, dp, "3-35keV_256ch", "HE_ISOTROPIC",
            f"INTEGRAL_JEMX/{st}/{stem}_sum_pha.fits", f"{HEASARC_AGN_URL}{stem}_sum_pha.fits",
            [f"INTEGRAL_JEMX/{st}/{arf_stem}_sum_arf.fits"],
            [f"{HEASARC_AGN_URL}{arf_stem}_sum_arf.fits"],
            45000,
        )

    # INTEGRAL SPI (agn/ coded-mask Ge)
    spi_specs = [
        ("3C273",    "3C 273",        "3C273",    "3C 273 Quasar",        "AGN_INTEGRAL", None),
        ("3C279",    "3C 279",        "3C279",    "3C 279 Blazar",        "AGN_INTEGRAL", None),
        ("CenA",     "Cen A",         "CENA",     "Cen A Radio Galaxy",   "AGN_INTEGRAL", None),
        ("3C111",    "3C 111",        "3C111",    "3C 111 Radio Galaxy",  "AGN_INTEGRAL", None),
        ("3C120",    "3C 120",        "3C120",    "3C 120 Seyfert 1",     "AGN_INTEGRAL", None),
        ("IC4329A",  "IC 4329A",      "IC4329A",  "IC 4329A Seyfert 1",   "AGN_INTEGRAL", None),
        ("Circinus", "Circinus Galaxy","CIRCINUS","Circinus Seyfert 2",   "AGN_INTEGRAL", None),
        ("3C454",    "3C 454.3",      "3C454P3",  "3C 454.3 Blazar",      "BLAZAR_INTEGRAL", "3C 454.3"),
        ("MRK3",     "Mrk 3",         "MRK3",     "Mrk 3 Seyfert 2",      "AGN_INTEGRAL", "Mrk 3"),
        ("MRK6",     "Mrk 6",         "MRK6",     "Mrk 6 Seyfert 1.5",    "AGN_INTEGRAL", "Mrk 6"),
        ("CygnusA",  "Cyg A",         "CYGNUSA",  "Cygnus A Radio Gal.",  "AGN_INTEGRAL", "Cygnus A"),
        ("NGC4388",  "NGC 4388",      "NGC4388",  "NGC 4388 Seyfert 2",   "AGN_INTEGRAL", "NGC 4388"),
        ("0716",     "QSO B0716+714", "QSOB0716", "S5 0716+714 Blazar",   "BLAZAR_INTEGRAL", "S5 0716+71"),
        ("0836",     "QSO B0836+710", "QSOB0836", "S5 0836+710 Blazar",   "BLAZAR_INTEGRAL", "S5 0836+71"),
    ]
    for stem, rkey, chint, clbl, subr, nq in spi_specs:
        if stem not in spi_available:
            continue
        hit = cat_by_key.get(_canon_key(rkey))
        if hit:
            _, ra, dec, _ = hit
            d0 = 0.0
        else:
            ra, dec, z0 = _ned_lookup(nq or rkey)
            if ra is None or dec is None:
                continue
            d0 = _z_to_dl_pc(z0) if z0 else 5.0e7
        reg_t = _register_target(chint, ra, dec, clbl, subr, d0, ned_query=nq)
        if reg_t is None:
            continue
        st, is_br, msep = reg_t
        dp = f"INT_SPI_{stem}"
        assert dp not in excl_all_dp
        _emit_row(
            "INTEGRAL_SPI", st, is_br, msep, dp, dp, "20-540keV_Ge", "HE_ISOTROPIC",
            f"INTEGRAL_SPI/{st}/{stem}_SPI.fits.gz", f"{HEASARC_AGN_URL}{stem}_SPI.fits.gz",
            [f"INTEGRAL_SPI/{st}/{stem}_SPI_results.txt"],
            [f"{HEASARC_AGN_URL}{stem}_SPI_results.txt"],
            1200000,
        )

    # 3. Freeze LHAASO WCDA (1-25 TeV) + KM2A (25-1,000 TeV / 1.000 PeV) targets
    print("3. Freezing 1LHAASO WCDA + KM2A (up to 1.000 PeV) rows...", flush=True)
    lhaaso_priority = [
        # Prior bridges + SS433
        "J0534+2200", "J0634+1741", "J1104+3810", "J1653+3943", "J2323+5854", "J2031+4052", "J1913+0501",
        # Brand-new high-TS100 & PeV benchmark UHE sources (strict >=600" separated!)
        "J2108+5153", "J0007+7303", "J0542+2311", "J1825-1256", "J1825-1337",
        "J1839-0548", "J1848-0001", "J1857+0203", "J1908+0615", "J1928+1746",
        "J2018+3643", "J2031+4127", "J2228+6100", "J0056+6346", "J0206+4302",
        "J0216+4237", "J0343+5254", "J0359+5406", "J0428+5531", "J0622+3754",
        "J0635+0619", "J1740+0948", "J1809-1918", "J1954+2836",
    ]
    lhaaso_picked = 0
    for lid in lhaaso_priority:
        if lid not in lhaaso_unique:
            continue
        info = lhaaso_unique[lid]
        ra, dec = info["ra"], info["dec"]
        key_s = _canon_key(lid.replace("+", "P").replace("-", "M"))
        d_def = DEFAULT_GALACTIC_DIST_PC.get(key_s, (3000.0, f"1LHAASO {lid}", 0.0))
        clbl = f"1LHAASO {lid} ({info['assoc']})" if info["assoc"] else f"1LHAASO {lid} UHE Source"
        reg_t = _register_target(key_s, ra, dec, clbl, "UHE_LHAASO_PEV", d_def[0])
        if reg_t is None:
            continue
        st, is_br, msep = reg_t
        lhaaso_picked += 1
        for inst_l, band_l, sufx in [("LHAASO_WCDA", "1-25TeV", "WCDA"), ("LHAASO_KM2A", "25-1000TeV_1PeV", "KM2A")]:
            dp = f"1LHAASO_{lid}_{sufx}"
            assert dp not in excl_all_dp
            _emit_row(
                inst_l, st, is_br, msep, dp, lid, band_l, "HE_ISOTROPIC",
                f"{inst_l}/1lhaaso_catalog.fits", VIZIER_1LHAASO_FITS_URL,
                [], [], 50000,
            )

    # 4. Freeze ALMA Band 2 Science Verification (Arp 220 X36 86.45-108.83 GHz + X52 112.25-114.12 GHz)
    print("4. Freezing ALMA Band 2 SV Arp 220 spectral scans...", flush=True)
    for dp_id, band_s, url, est_b in [
        ("ALMA_B2_SV_ARP220_X36", "B2_86p45_108p83GHz", ALMA_X36_URL, 2440000000),
        ("ALMA_B2_SV_ARP220_X52", "B2_112p25_114p12GHz", ALMA_X52_URL, 1389000000),
    ]:
        assert dp_id not in excl_all_dp
        _emit_row(
            "ALMA_B2_3MM", "ARP220", True, 0.0, dp_id, "2011.0.00026.SV", band_s, "BEAMED_UV_OPT_IR_MM",
            f"ALMA_B2_3MM/ARP220/{dp_id}.tgz", url, [], [], est_b,
        )

    cohort_rows.sort(key=lambda r: (r["instrument"], r["canonical_target"], r["dp_id"]))
    unique_stars = sorted({r["canonical_target"] for r in cohort_rows})
    bridge_stars = sorted({r["canonical_target"] for r in cohort_rows if r["is_prior_bridge"] == "True"})
    new_stars = sorted({r["canonical_target"] for r in cohort_rows if r["is_prior_bridge"] == "False"})
    by_inst = defaultdict(int)
    for r in cohort_rows:
        by_inst[r["instrument"]] += 1

    assert by_inst["INTEGRAL_IBIS_ISGRI"] >= 25
    assert by_inst["INTEGRAL_JEMX"] >= 12
    assert by_inst["INTEGRAL_SPI"] >= 10
    assert by_inst["LHAASO_WCDA"] >= 20
    assert by_inst["LHAASO_KM2A"] >= 20
    assert by_inst["ALMA_B2_3MM"] == 2
    assert len(bridge_stars) >= 20
    assert len(new_stars) >= 25
    assert all(new_target_meta[s]["min_prior_sep_arcsec"] >= 600.0 for s in new_stars)
    assert all(r["dp_id"] not in excl_all_dp and r["obs_id"] not in excl_all_dp for r in cohort_rows)

    proj_bytes = sum(int(r["est_bytes"]) for r in cohort_rows)

    # Write Stage-1 files (RAW_DIR MUST STILL NOT EXIST)
    with (WS / "FROZEN_COHORT_D112.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COHORT_COLS)
        w.writeheader()
        for r in cohort_rows:
            w.writerow(r)

    (WS / "PRIOR_V6_9_PHASES_SNAPSHOT.json").write_text(json.dumps(snap, separators=(",", ":")) + "\n", encoding="utf-8")

    pex_out = {
        "schema": "D112_PRIOR_EXCLUSION_VERIFICATION",
        "phase_id": "D112",
        "verified_utc": datetime.now(timezone.utc).isoformat(),
        "prior_phases_covered": "D001-D111 (Companion Archives A-AK)",
        "n_prior_excluded_coords": len(prior_coords),
        "n_prior_excluded_dp_ids": len(prior_dp_ids),
        "n_format_check_excluded_dp_ids": len(fmt_probes),
        "d112_total_stars": len(unique_stars),
        "d112_brand_new_unique_stars": len(new_stars),
        "d112_prior_bridge_stars": len(bridge_stars),
        "d112_total_observations": len(cohort_rows),
        "d112_dp_id_overlap_count": 0,
        "brand_new_min_prior_sep_arcsec": min(new_target_meta[s]["min_prior_sep_arcsec"] for s in new_stars),
        "format_check_excluded_dp_ids": fmt_probes,
        "excluded_dp_ids": sorted(prior_dp_ids),
        "excluded_targets_coordinate_registry": prior_coords,
    }
    (WS / "PRIOR_EXCLUSION_VERIFICATION.json").write_text(json.dumps(pex_out, indent=2) + "\n", encoding="utf-8")

    cfg = {
        "schema": "D112_HIGH_ENERGY_PEV_ALMAB2_CONFIG",
        "phase_id": "D112",
        "new_spectrographs_added": ["INTEGRAL_IBIS_ISGRI", "INTEGRAL_JEMX", "INTEGRAL_SPI", "LHAASO_WCDA", "LHAASO_KM2A"],
        "new_spectral_arms_added": ["INTEGRAL_IBIS_ISGRI", "INTEGRAL_JEMX", "INTEGRAL_SPI", "LHAASO_WCDA", "LHAASO_KM2A", "ALMA_B2_3MM"],
        "new_spectrographs_total_post_d112": 72,
        "new_spectral_arms_total_post_d112": 104,
        "alma_bands_complete": ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10"],
        "lhaaso_max_energy_tev": 1000.0,
        "lhaaso_min_wave_um": det.LHAASO_MIN_WAVE_UM,
        "shared_downloads": {
            "jmx2_rmf": {"relpath": "SHARED/jmx2_rmf_grp_0005.fits", "url": HEASARC_JMX2_RMF_URL, "min_bytes": 50000},
            "1lhaaso_fits": {"relpath": "SHARED/1lhaaso_catalog.fits", "url": VIZIER_1LHAASO_FITS_URL, "min_bytes": 20000},
            "lhaaso_j2108_sed_tar": {"relpath": "SHARED/LHAASO_J2108_data_release_v1.0.0.tar.gz", "url": ZENODO_J2108_URL, "min_bytes": 1000000},
            "lhaaso_13uhe_zip": {"relpath": "SHARED/JHEAp_zenodo_data_20261111.zip", "url": ZENODO_LHAASO13_URL, "min_bytes": 5000},
        },
        "instruments": {k: {"count": int(v)} for k, v in sorted(by_inst.items())},
        "brand_new_targets": {st: new_target_meta[st] for st in new_stars},
    }
    (WS / "HIGH_ENERGY_PEV_ALMAB2_CONFIG.json").write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")

    assert not RAW_DIR.exists(), f"{RAW_DIR} appeared before Stage-1 seal!"
    now_epoch = time.time()
    now_utc = datetime.fromtimestamp(now_epoch, tz=timezone.utc).isoformat()
    stage1_names = [
        "v7_0_detector.py",
        "build_cohort.py",
        "download_inputs.py",
        "FROZEN_COHORT_D112.csv",
        "PRIOR_EXCLUSION_VERIFICATION.json",
        "HIGH_ENERGY_PEV_ALMAB2_CONFIG.json",
        "PRIOR_V6_9_PHASES_SNAPSHOT.json",
    ]
    stage1_hashes = {fn: _sha256_file(WS / fn) for fn in stage1_names}

    ml = {
        "schema": "D112_METHOD_LOCK",
        "phase_id": "D112",
        "detector": "TECHNOSIGNATURE_V7_0_INTEGRAL_LHAASO_PEV_AND_ALMA_BAND2",
        "locked_utc": now_utc,
        "locked_unix_epoch": round(now_epoch, 4),
        "d112_total_stars": len(unique_stars),
        "d112_brand_new_stars": len(new_stars),
        "d112_prior_bridges": len(bridge_stars),
        "d112_total_observations": len(cohort_rows),
        "d112_instruments_counts": dict(sorted(by_inst.items())),
        "d112_projected_download_mib": round(proj_bytes / (1024.0 * 1024.0), 3),
        "calibration_suites_new": {
            "V70_INTEGRAL_511KEV_ISGRI_JEMX_240": 240,
            "V70_LHAASO_PEV_KM2A_WCDA_240": 240,
            "V70_ALMA_BAND2_INTERFEROMETRIC_120": 120,
        },
        "stage_1_files": stage1_hashes,
    }
    (WS / "METHOD_LOCK.json").write_text(json.dumps(ml, indent=2) + "\n", encoding="utf-8")
    ml_sha = _sha256_file(WS / "METHOD_LOCK.json")

    lr = {
        "schema": "D112_LOCK_RECEIPT",
        "phase_id": "D112",
        "status": "STAGE-1 SEALED",
        "locked_utc": now_utc,
        "locked_unix_epoch": round(now_epoch, 4),
        "inputs_dir_exists_at_seal": RAW_DIR.exists(),
        "method_lock_sha256": ml_sha,
    }
    (WS / "LOCK_RECEIPT.json").write_text(json.dumps(lr, indent=2) + "\n", encoding="utf-8")
    print(
        f"STAGE-1 SEALED: stars={len(unique_stars)} (bridges={len(bridge_stars)}, new={len(new_stars)}), "
        f"obs={len(cohort_rows)}, by_inst={dict(by_inst)}, overlap=0, inputs_at_seal={RAW_DIR.exists()}, "
        f"min_new_sep={pex_out['brand_new_min_prior_sep_arcsec']}\""
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
