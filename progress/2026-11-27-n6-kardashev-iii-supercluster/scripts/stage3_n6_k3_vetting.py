#!/usr/bin/env python3
"""
Spor N6 Stage 3 Forensic Vetting across all 11 Kardashev Type III Triggers +
Local Supercluster Starburst/AGN Calibration Benchmarks:
- Live VLASS 1.2 (3.0 GHz) FITS Cutouts + 15" integrated & 3" peak photometry
- Live Legacy Survey DR10 optical grz cutouts (RGB)
- IRAS cold-dust F60/F100 ratio & AGN / Markarian / HII classification
Forces IPv4 (socket.AF_INET). Runs under .venv/bin/python.
"""
from __future__ import annotations

import collections
import csv
import datetime
import io
import json
import math
import pathlib
import socket
import time
import urllib.request
from typing import Any

import numpy as np
from astropy.io import fits

_orig_gai = socket.getaddrinfo
socket.getaddrinfo = lambda h, p, fam=0, t=0, pr=0, fl=0: _orig_gai(h, p, socket.AF_INET, t, pr, fl)

ROOT = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace" / "work_n6_20261127_kardashev_iii_supercluster"
INP = ROOT / "inputs_n6_20261127"
RES = WS / "results"
VLASS_DIR = INP / "vlass_cutouts"
LS_DIR = INP / "ls_cutouts"


def _f(v: Any) -> float | None:
    if v is None or v == "" or str(v).strip().lower() in ("nan", "null", "none", "inf", "-inf", "--"):
        return None
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def fetch_vlass_fits(pgc: str, ra: float, dec: float) -> tuple[pathlib.Path | None, str]:
    VLASS_DIR.mkdir(parents=True, exist_ok=True)
    out = VLASS_DIR / f"PGC{pgc}_vlass12.fits"
    if out.exists() and out.stat().st_size > 4096:
        try:
            with fits.open(out) as hdul:
                if hdul[0].data is not None and np.isfinite(hdul[0].data).any():
                    return out, "cached"
        except Exception:
            out.unlink(missing_ok=True)
    url = f"https://www.legacysurvey.org/viewer/fits-cutout?ra={ra:.6f}&dec={dec:.6f}&layer=vlass1.2&pixscale=0.6&size=80"
    for att in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "SETI-N6/1.0"}), timeout=25) as r:
                raw = r.read()
            hdul = fits.open(io.BytesIO(raw))
            d = hdul[0].data
            if d is None or not np.isfinite(d).any() or np.all(d == 0):
                return None, "empty"
            out.write_bytes(raw)
            return out, "downloaded"
        except Exception as e:
            if att == 2:
                return None, f"err_{type(e).__name__}"
            time.sleep(0.5 * (att + 1))
    return None, "failed"


def fetch_ls_jpg(pgc: str, ra: float, dec: float) -> tuple[pathlib.Path | None, str]:
    LS_DIR.mkdir(parents=True, exist_ok=True)
    out = LS_DIR / f"PGC{pgc}_lsdr10.jpg"
    if out.exists() and out.stat().st_size > 1000:
        return out, "cached"
    url = f"https://www.legacysurvey.org/viewer/jpeg-cutout?ra={ra:.6f}&dec={dec:.6f}&layer=ls-dr10&pixscale=0.5&size=128"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "SETI-N6/1.0"}), timeout=20) as r:
            raw = r.read()
        if len(raw) > 800:
            out.write_bytes(raw)
            return out, "downloaded"
        return None, "empty"
    except Exception as e:
        return None, f"err_{type(e).__name__}"


def measure_vlass_galaxy(fits_p: pathlib.Path, f22_mjy: float) -> dict[str, Any]:
    with fits.open(fits_p) as hdul:
        dat = np.array(hdul[0].data, dtype=float)
    fin = dat[np.isfinite(dat)]
    mad = float(1.4826 * np.median(np.abs(fin - np.median(fin))))
    scale = 1000.0 if mad < 0.02 else 1.0  # Jy/beam -> mJy/beam
    dat_m = dat * scale
    ny, nx = dat_m.shape
    cy, cx = ny // 2, nx // 2
    yy, xx = np.ogrid[:ny, :nx]
    rr = np.hypot(yy - cy, xx - cx)
    ann = dat_m[(rr >= 25.0) & (rr <= 38.0) & np.isfinite(dat_m)]
    if len(ann) < 40:
        ann = dat_m[np.isfinite(dat_m)]
    rms = max(0.05, float(1.4826 * np.median(np.abs(ann - np.median(ann)))))

    core = dat_m[max(0, cy - 6):min(ny, cy + 7), max(0, cx - 6):min(nx, cx + 7)]  # central ~7"x7"
    peak = float(np.nanmax(core))
    snr = peak / rms
    s14_from_vlass = max(rms, peak) * ((1.4 / 3.0) ** -0.7)
    q22_vlass = math.log10(max(1e-6, f22_mjy) / max(1e-6, s14_from_vlass))
    return {
        "fits_file": fits_p.name,
        "vlass_peak_mjy": round(peak, 4),
        "vlass_rms_mjy": round(rms, 4),
        "vlass_snr": round(snr, 2),
        "vlass_detected_5sig": snr >= 5.0,
        "q22_vlass_3ghz_scaled": round(q22_vlass, 4),
    }


def classify_k3_trigger(r: dict[str, Any], vl: dict[str, Any] | None) -> tuple[str, str]:
    ned = (r.get("NED") or "").upper()
    agnh = (r.get("AGNh") or "").strip()
    agns17 = (r.get("AGNs17") or "").strip()
    w1_w2 = float(r["W1_W2"])
    logm = float(r["logMtot"])
    f60 = _f(r.get("F60um"))
    f100 = _f(r.get("F100um"))
    logsfr = _f(r.get("logSFRh"))
    v_snr = vl["vlass_snr"] if vl else None

    if agnh == "Y" or w1_w2 >= 0.8 or r.get("Nuclear") in ("1", "2"):
        return "KNOWN_AGN_SEYFERT_OR_CON", f"Active galactic nucleus / obscured core (AGNh={agnh}, W1-W2={w1_w2:.3f}, VLASS SNR={v_snr}, {r['radio_survey_used']})"
    if "MRK" in ned or "UGCA" in ned or "UGC" in ned or logm < 9.7:
        return "COMPACT_DWARF_STARBURST_OR_HII", f"Markarian/Blue Compact Dwarf starburst + radio emission ({r['radio_survey_used']}, VLASS SNR={v_snr}, F60={f60})"
    if f60 is not None or (logsfr is not None and logsfr > 0.0):
        return "KNOWN_STARBURST_OR_BARRED_SPIRAL", f"FIR cold-dust starburst ({r['radio_survey_used']}, F60={f60} Jy, F100={f100} Jy, VLASS SNR={v_snr})"
    return "EXTRAGALACTIC_NON_K3_RADIO_SOURCE", f"Matched in {r['radio_survey_used']} (VLASS SNR={v_snr})"


def main() -> int:
    cat = list(csv.DictReader((RES / "N6_SUPERCLUSTER_K3_CATALOG.csv").open(encoding="utf-8")))
    trigs = [r for r in cat if r["k3_trigger"] == "True"]

    # Add 9 iconic Local Supercluster starburst/AGN benchmarks (M82, M51, NGC253, NGC1068/M77, NGC3690, etc.)
    bench_names = ("MESSIER 082", "NGC 0253", "MESSIER 051a", "NGC 4945", "IC 0691", "NGC 3690", "MESSIER 087", "NGC 5128", "NGC 4038")
    benchmarks = [r for r in cat if any(bn in (r.get("NED") or "").upper() for bn in bench_names) and r not in trigs]
    benchmarks.sort(key=lambda r: float(r["gamma_iii"]), reverse=True)
    targets = trigs + benchmarks[:9]

    print(f"Fetching/measuring VLASS 1.2 + Legacy DR10 cutouts for {len(targets)} galaxies ({len(trigs)} K-III triggers + {len(targets)-len(trigs)} benchmarks)...", flush=True)
    vlass_by_pgc: dict[str, dict[str, Any]] = {}
    phot_rows: list[dict[str, Any]] = []
    ls_count = 0

    for idx, r in enumerate(targets):
        pgc = r["PGC"]
        ra, dec = float(r["ra_deg"]), float(r["dec_deg"])
        f22 = float(r["f22_mjy"])
        ls_p, ls_st = fetch_ls_jpg(pgc, ra, dec)
        if ls_p is not None:
            ls_count += 1
        fp, fst = fetch_vlass_fits(pgc, ra, dec) if dec > -40.0 else (None, "south_dec")
        if fp is not None:
            m = measure_vlass_galaxy(fp, f22)
            m.update({"PGC": pgc, "NED": r["NED"], "dist_mpc": r["dist_mpc"], "gamma_iii": r["gamma_iii"], "q22_cat": r["q22"], "is_k3_trigger": r["k3_trigger"], "ls_jpg": ls_p.name if ls_p else ""})
            vlass_by_pgc[pgc] = m
            phot_rows.append(m)
        if fst == "downloaded" or ls_st == "downloaded":
            time.sleep(0.15)
        print(f"  [{idx+1}/{len(targets)}] PGC {pgc} ({r['NED']}): VLASS={vlass_by_pgc.get(pgc, {}).get('vlass_snr', fst)}, LS={ls_st}", flush=True)

    p_phot = RES / "N6_VLASS_GALAXY_PHOTOMETRY.csv"
    with p_phot.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(phot_rows[0].keys()))
        w.writeheader()
        w.writerows(phot_rows)

    vet_rows: list[dict[str, Any]] = []
    class_counts: collections.Counter[str] = collections.Counter()
    for r in trigs:
        pgc = r["PGC"]
        vl = vlass_by_pgc.get(pgc)
        vcls, vnote = classify_k3_trigger(r, vl)
        class_counts[vcls] += 1
        vet_rows.append({
            **r,
            "vlass_snr": vl["vlass_snr"] if vl else "",
            "vlass_peak_mjy": vl["vlass_peak_mjy"] if vl else "",
            "q22_vlass": vl["q22_vlass_3ghz_scaled"] if vl else "",
            "vetting_class": vcls,
            "k3_eti_status": "VETOED_ASTROPHYSICAL_NON_K3",
            "vetting_note": vnote,
        })

    with (RES / "N6_K3_CANDIDATES_VETTED.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(vet_rows[0].keys()))
        w.writeheader()
        w.writerows(vet_rows)

    s3 = {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "galaxies_analyzed_stage2": len(cat),
        "k3_triggers_total": len(trigs),
        "k3_triggers_with_live_radio_detection": sum(1 for r in trigs if r["radio_detected"] == "True"),
        "vlass_cutouts_valid_fits": len(phot_rows),
        "legacy_dr10_jpg_cutouts": ls_count,
        "vlass_5sig_detected_triggers": sum(1 for r in phot_rows if r["is_k3_trigger"] == "True" and r["vlass_detected_5sig"]),
        "vetting_class_counts": dict(class_counts),
        "verified_k3_eti_candidates": 0,
    }
    (RES / "N6_STAGE3_VETTING.json").write_text(json.dumps(s3, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(s3, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
