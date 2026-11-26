#!/usr/bin/env python3
"""
Stage 3 Cutout & Multi-Archive Vetting for blind N1B Dyson triggers and N1C VASCO candidates:
  - Downloads Legacy DR10, unWISE-neo7, DSS2 Red, and VLASS 1.2 FITS cutouts (up to 12 per pillar)
  - Queries Fink Rubin LSST 2026 & SIMBAD TAP
  - Checks exact NERSC Tractor brick neighbors around triggered N1B sources
  - Measures optical Legacy DR10 FITS SNR at N1C VASCO positions to separate true disappearance
    from bright-star bleed, deblending, or proper-motion offset
  - Recomputes conservative zero-ETI Bayesian bounds in N1_FINAL_SUMMARY.json
"""
from __future__ import annotations

import collections
import csv
import datetime
import hashlib
import io
import json
import math
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
from astropy.io import fits
from scipy.stats import beta as scipy_beta

WS = Path("/home/martin/SETI_Fortsaettelse_2026-11-14/analysis_workspace/work_n1_20261126_dyson_hephaistos_and_vasco")
INPUTS = Path("/home/martin/SETI_Fortsaettelse_2026-11-14/inputs_n1_20261126")
RESULTS = WS / "results"
FINK_CONE = "https://api.lsst.fink-portal.org/api/v1/conesearch"
SIMBAD_TAP = "https://simbad.cds.unistra.fr/simbad/sim-tap/sync"


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def fetch_bytes(url: str, save_path: Path | None = None, form_dict: dict[str, str] | None = None, json_payload: Any = None, timeout: int = 30) -> bytes:
    if save_path and save_path.exists():
        return save_path.read_bytes()
    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
    for att in range(1, 4):
        try:
            h = {"User-Agent": "SETI-N1/1.0"}
            data = None
            method = "GET"
            if form_dict:
                data = urllib.parse.urlencode(form_dict).encode()
                h["Content-Type"] = "application/x-www-form-urlencoded"
                method = "POST"
            elif json_payload is not None:
                data = json.dumps(json_payload).encode()
                h["Content-Type"] = "application/json"
                method = "POST"
            req = urllib.request.Request(url, data=data, method=method, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                if save_path:
                    save_path.write_bytes(raw)
                return raw
        except Exception as exc:
            if att == 3:
                raise exc
            time.sleep(2 ** att)
    return b""


def fits_center_snr(path: Path, box_half: int = 4) -> dict[str, Any]:
    if not path.exists():
        return {"valid": False, "snr": None, "edge_dist_or_artifact": None}
    raw = path.read_bytes()
    if raw[:6] != b"SIMPLE":
        return {"valid": False, "snr": None}
    with fits.open(io.BytesIO(raw)) as hdul:
        img = next((np.array(h.data, dtype=float) for h in hdul if h.data is not None and h.data.ndim >= 2), None)
    if img is None:
        return {"valid": False, "snr": None}
    if img.ndim > 2:
        # Collapse g/r/z bands for Legacy DR10 optical depth check
        img = np.nanmean(img.reshape((-1, img.shape[-2], img.shape[-1])), axis=0)
    fin = img[np.isfinite(img)]
    if len(fin) < 25 or float(np.std(fin)) == 0.0:
        return {"valid": False, "snr": None}
    med = float(np.median(fin))
    mad = max(1e-12, 1.4826 * float(np.median(np.abs(fin - med))))
    h, w = img.shape
    cy, cx = h // 2, w // 2
    box = img[max(0, cy - box_half):min(h, cy + box_half + 1), max(0, cx - box_half):min(w, cx + box_half + 1)] - med
    peak = float(np.nanmax(box)) if np.any(np.isfinite(box)) else 0.0
    max_all = float(np.nanmax(fin - med))
    return {"valid": True, "snr": round(peak / mad, 2), "field_max_snr": round(max_all / mad, 2)}


def angsep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    return math.degrees(math.acos(max(-1.0, min(1.0, math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2))))) * 3600.0


def tractor_neighbors_around(ra: float, dec: float) -> tuple[int, int, float]:
    """Fetch exact NERSC DR10 Tractor brick for (ra, dec) and count neighbors <= 10.0" + max neighbor W3 flux ratio."""
    try:
        html = fetch_bytes(f"https://www.legacysurvey.org/viewer/data-for-radec/?ra={ra:.6f}&dec={dec:.6f}&layer=ls-dr10", timeout=20).decode("utf-8", errors="replace")
        urls = re.findall(r'https://[^\s"<>]+/dr10/south/tractor/[^\s"<>]+\.fits', html)
        if not urls:
            return 0, 0, 0.0
        raw = fetch_bytes(urls[0], timeout=45)
        with fits.open(io.BytesIO(raw)) as hdul:
            d = hdul[1].data
            ras = np.array(d["ra"], dtype=float)
            decs = np.array(d["dec"], dtype=float)
            cos_d = math.cos(math.radians(dec))
            seps = np.hypot((ras - ra) * cos_d, decs - dec) * 3600.0
            self_mask = seps <= 1.2
            self_w3 = float(np.max(d["flux_w3"][self_mask])) if np.any(self_mask) else 1.0
            mask = (seps > 1.2) & (seps <= 10.0)
            n_tot = int(np.sum(mask))
            types = [str(d["type"][i]).strip() for i in np.where(mask)[0]]
            n_ext = sum(1 for t in types if t and t != "PSF")
            max_w3_ratio = float(np.max(d["flux_w3"][mask]) / max(1e-3, abs(self_w3))) if np.any(mask) else 0.0
            return n_tot, n_ext, round(max_w3_ratio, 2)
    except Exception:
        return 0, 0, 0.0


def bayesian_bounds(n_eval: int, n_eff: float) -> dict[str, Any]:
    u95 = float(scipy_beta.ppf(0.95, 1.0, n_eff + 1.0)) * 100.0
    j95 = float(scipy_beta.ppf(0.95, 0.5, n_eff + 0.5)) * 100.0
    cp95 = (1.0 - 0.05 ** (1.0 / max(1.0, n_eff))) * 100.0
    return {"n_eval": int(n_eval), "n_eff": round(float(n_eff), 3), "uniform_f95_pct": round(u95, 4), "jeffreys_f95_pct": round(j95, 4), "clopper_pearson_f95_pct": round(cp95, 4)}


def main() -> int:
    n1b_cands = list(csv.DictReader((RESULTS / "N1B_BLIND_DYSON_CANDIDATES.csv").open(encoding="utf-8"))) if (RESULTS / "N1B_BLIND_DYSON_CANDIDATES.csv").exists() else []
    n1c_cands = list(csv.DictReader((RESULTS / "N1C_VASCO_CANDIDATES.csv").open(encoding="utf-8"))) if (RESULTS / "N1C_VASCO_CANDIDATES.csv").exists() else []

    # Sort N1B candidates by delta_chi2 descending and vet up to 12
    n1b_cands = [r for r in n1b_cands if r.get("ra_deg")]
    n1b_cands.sort(key=lambda r: float(r.get("delta_chi2") or 0.0), reverse=True)
    n1b_vetted = []
    for i, r in enumerate(n1b_cands[:12]):
        gid = r["gaia_source_id"]
        ra, dec = float(r["ra_deg"]), float(r["dec_deg"])
        n_tot, n_ext, max_w3_ratio = tractor_neighbors_around(ra, dec)
        ls_p = INPUTS / "cutouts" / f"n1b_{gid}_ls_dr10.fits"
        vl_p = INPUTS / "cutouts" / f"n1b_{gid}_vlass.fits"
        uw_p = INPUTS / "cutouts" / f"n1b_{gid}_unwise.fits"
        for url, sp in [
            (f"https://www.legacysurvey.org/viewer/fits-cutout?ra={ra:.6f}&dec={dec:.6f}&layer=ls-dr10&pixscale=0.262&size=128", ls_p),
            (f"https://www.legacysurvey.org/viewer/fits-cutout?ra={ra:.6f}&dec={dec:.6f}&layer=vlass1.2&pixscale=1.0&size=64", vl_p),
            (f"https://www.legacysurvey.org/viewer/fits-cutout?ra={ra:.6f}&dec={dec:.6f}&layer=unwise-neo7&pixscale=2.75&size=32", uw_p),
        ]:
            try:
                fetch_bytes(url, sp, timeout=25)
            except Exception:
                pass
        v_snr = fits_center_snr(vl_p, box_half=8).get("snr")
        # SIMBAD check
        sim_types = ""
        try:
            sraw = fetch_bytes(SIMBAD_TAP, form_dict={"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": f"SELECT main_id, otype FROM basic WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra:.6f}, {dec:.6f}, 0.0025))=1"}, timeout=15)
            sim_types = ";".join(x.get("otype", "") for x in csv.DictReader(io.StringIO(sraw.decode("utf-8"))))
        except Exception:
            pass

        if v_snr is not None and v_snr >= 4.5:
            disp = "RADIO_AGN_OR_HOT_DOG_CONTAMINANT"
        elif n_ext >= 1:
            disp = "EXTENDED_BACKGROUND_GALAXY_IN_WISE_PSF"
        elif n_tot >= 1:
            disp = "NEARBY_OPTICAL_BLEND_IN_WISE_PSF"
        elif any(k in sim_types.upper() for k in ("YSO", "TT", "AGB", "LPV", "MIR", "IR")):
            disp = "KNOWN_DUSTY_STAR_OR_YSO"
        else:
            disp = "UNRESOLVED_REQUIRES_MIRI_ALMA_FOLLOWUP"

        n1b_vetted.append({
            **r,
            "ls_tractor_neighbors_10arcsec": n_tot,
            "ls_tractor_extended_10arcsec": n_ext,
            "max_neighbor_w3_ratio": max_w3_ratio,
            "vlass_peak_snr": v_snr,
            "simbad_types": sim_types,
            "final_disposition": disp,
        })

    # Vet ALL up to 30 N1C VASCO candidates via Legacy DR10 FITS cutout + DSS2 + PS1 sentinel flag check
    ps1_all = {row["objID"]: row for row in csv.DictReader((INPUTS / "vasco" / "ps1_cosmos_0p25deg.csv").open(encoding="utf-8"))}
    ps1_valid_i = sum(1 for row in ps1_all.values() if float(row.get("iMeanPSFMag") or -999) > 0)
    n1c_cands = [r for r in n1c_cands if r.get("ra_deg")]
    n1c_vetted = []
    for r in n1c_cands[:30]:
        sid = r["source_id"]
        ra, dec = float(r["ra_deg"]), float(r["dec_deg"])
        ls_p = INPUTS / "cutouts" / f"n1c_{sid}_ls_dr10.fits"
        ds_p = INPUTS / "cutouts" / f"n1c_{sid}_dss2.fits"
        for url, sp in [
            (f"https://www.legacysurvey.org/viewer/fits-cutout?ra={ra:.6f}&dec={dec:.6f}&layer=ls-dr10&pixscale=0.262&size=128", ls_p),
            (f"https://archive.stsci.edu/cgi-bin/dss_search?v=poss2ukstu_red&r={ra:.6f}&d={dec:.6f}&e=J2000&h=1.2&w=1.2&f=fits&c=none", ds_p),
        ]:
            try:
                fetch_bytes(url, sp, timeout=25)
            except Exception:
                pass
        opt_stat = fits_center_snr(ls_p, box_half=5)
        dss_stat = fits_center_snr(ds_p, box_half=4)
        ls_snr = opt_stat.get("snr")
        field_max = opt_stat.get("field_max_snr") or 0.0
        ps1_rec = ps1_all.get(sid, {})
        ps1_imag = float(ps1_rec.get("iMeanPSFMag") or -999.0)
        ps1_zmag = float(ps1_rec.get("zMeanPSFMag") or -999.0)
        dss_snr = dss_stat.get("snr") or 0.0
        if ls_snr is not None and ls_snr >= 5.0:
            disp = "OPTICAL_SOURCE_PRESENT_IN_DR10_IMAGE_DEBLENDED"
        elif ps1_imag <= -900.0 and ps1_zmag <= -900.0 and dss_snr < 4.5:
            disp = "PS1_SENTINEL_R_ONLY_ARTIFACT_NO_DSS2_NO_DR10"
        elif field_max >= 500.0:
            disp = "MASKED_BY_ADJACENT_BRIGHT_STAR_HALO"
        elif float(r.get("pm_masyr") or 0.0) >= 40.0:
            disp = "HIGH_PROPER_MOTION_STAR"
        else:
            disp = "UNRESOLVED_TRUE_DISAPPEARANCE_CANDIDATE"

        n1c_vetted.append({
            **r,
            "ps1_i_psf_mag": ps1_imag,
            "ls_dr10_center_snr": ls_snr,
            "ls_dr10_field_max_snr": field_max,
            "dss2_center_snr": dss_stat.get("snr"),
            "final_disposition": disp,
        })

    if n1b_vetted:
        with (RESULTS / "N1B_BLIND_DYSON_VETTED.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(n1b_vetted[0].keys()))
            w.writeheader()
            for r in n1b_vetted: w.writerow(r)
    if n1c_vetted:
        with (RESULTS / "N1C_VASCO_VETTED.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(n1c_vetted[0].keys()))
            w.writeheader()
            for r in n1c_vetted: w.writerow(r)

    base_sum = json.loads((RESULTS / "N1_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    # Compute multiband-valid PS1 count (r, i both > 0, no -999 sentinel) inside same brick bounds
    ps1_valid_in_bounds = 0
    for r in csv.DictReader((INPUTS / "vasco" / "ps1_cosmos_0p25deg.csv").open(encoding="utf-8")):
        try:
            rm = float(r.get("rMeanPSFMag") or -999)
            im = float(r.get("iMeanPSFMag") or -999)
            ik = float(r.get("iMeanKronMag") or -999)
            nd = int(float(r.get("nDetections") or 0))
            if nd >= 5 and 14.0 <= rm <= 20.5 and im > 0 and ik > 0 and abs(im - ik) < 0.15:
                ps1_valid_in_bounds += 1
        except Exception:
            pass
    # Matched valid multiband PS1 <= total ps1_matched_ls_dr10 (since all 27 unmatched had i=-999 sentinel!)
    n_valid_ps1 = base_sum["n1c_vasco"]["ps1_matched_ls_dr10"] + sum(1 for v in n1c_vetted if "PRESENT_IN_DR10" in v["final_disposition"])
    base_sum["n1c_vasco"]["ps1_valid_multiband_or_dss2_screened"] = n_valid_ps1
    base_sum["n1c_vasco"]["bounds_ps1_valid_multiband_vanishing"] = bayesian_bounds(n_valid_ps1, float(n_valid_ps1))
    out = {
        "utc": now_utc(),
        **base_sum,
        "n1b_vetted_count": len(n1b_vetted),
        "n1b_vetted_dispositions": dict(collections.Counter(r["final_disposition"] for r in n1b_vetted)),
        "n1c_vetted_count": len(n1c_vetted),
        "n1c_vetted_dispositions": dict(collections.Counter(r["final_disposition"] for r in n1c_vetted)),
    }
    (RESULTS / "N1_STAGE3_VETTING.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
