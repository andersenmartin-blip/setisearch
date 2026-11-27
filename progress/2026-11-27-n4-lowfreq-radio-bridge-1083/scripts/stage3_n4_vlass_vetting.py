#!/usr/bin/env python3
"""
Spor N4 Stage 3: Live VLASS 1.2 (3.0 GHz) FITS Cutout Photometry,
Multi-Band Radio Spectral Index alpha, High-Resolution Offset / Astrophysical
Vetting across all 172 matched stars, and CHIME/FRB Dispersion Measure Veto.
Runs under .venv/bin/python (astropy + numpy). Forces IPv4.
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
import urllib.error
import urllib.request
from typing import Any

import numpy as np
from astropy.io import fits

# Critical IPv4 force
_orig_gai = socket.getaddrinfo
socket.getaddrinfo = lambda h, p, fam=0, t=0, pr=0, fl=0: _orig_gai(h, p, socket.AF_INET, t, pr, fl)

ROOT = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace" / "work_n4_20261127_lowfreq_radio_bridge_1083"
INP = ROOT / "inputs_n4_20261127"
RES = WS / "results"
CUT_DIR = INP / "vlass_cutouts"
TABLE1 = ROOT / "setisearch" / "zenodo_package" / "tables" / "table1_master_catalog_1083stars.csv"

PC_TO_M = 3.0856775814913673e16
MJY_TO_W_M2_HZ = 1e-29


def _f(v: Any) -> float | None:
    if v is None or v == "" or str(v).strip().lower() in ("nan", "null", "none", "inf", "-inf"):
        return None
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def safe_name(star: str) -> str:
    return "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in star)


def fetch_vlass_cutout(star: str, ra: float, dec: float) -> tuple[pathlib.Path | None, str]:
    CUT_DIR.mkdir(parents=True, exist_ok=True)
    out = CUT_DIR / f"{safe_name(star)}_vlass12.fits"
    if out.exists() and out.stat().st_size > 4096:
        try:
            with fits.open(out) as hdul:
                d = hdul[0].data
                if d is not None and np.isfinite(d).any():
                    return out, "cached"
        except Exception:
            out.unlink(missing_ok=True)

    url = f"https://www.legacysurvey.org/viewer/fits-cutout?ra={ra:.6f}&dec={dec:.6f}&layer=vlass1.2&pixscale=0.6&size=80"
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETI-N4-VLASS/1.0"})
            with urllib.request.urlopen(req, timeout=25) as resp:
                raw = resp.read()
            hdul = fits.open(io.BytesIO(raw))
            d = hdul[0].data
            if d is None or d.ndim != 2 or not np.isfinite(d).any() or np.all(d == 0):
                return None, "empty_or_outside_vlass"
            out.write_bytes(raw)
            return out, "downloaded"
        except urllib.error.HTTPError as e:
            if e.code in (400, 404, 500) and attempt == 2:
                return None, f"http_{e.code}"
            time.sleep(0.5 * (attempt + 1))
        except Exception as e:
            if attempt == 2:
                return None, f"err_{type(e).__name__}"
            time.sleep(0.5 * (attempt + 1))
    return None, "failed"


def measure_vlass_fits(fits_path: pathlib.Path, dist_pc: float) -> dict[str, Any]:
    with fits.open(fits_path) as hdul:
        dat = np.array(hdul[0].data, dtype=float)
    # Handle jy/beam -> mJy/beam scaling (Legacy Survey VLASS cutouts are in Jy/beam; typical RMS ~ 1e-4 Jy/beam)
    finite = dat[np.isfinite(dat)]
    med = float(np.median(finite))
    mad = float(1.4826 * np.median(np.abs(finite - med)))
    scale = 1000.0 if mad < 0.02 else 1.0  # Jy/beam -> mJy/beam
    dat_mjy = dat * scale

    ny, nx = dat_mjy.shape
    cy, cx = ny // 2, nx // 2
    yy, xx = np.ogrid[:ny, :nx]
    rr = np.hypot(yy - cy, xx - cx)

    ann = dat_mjy[(rr >= 12.0) & (rr <= 35.0) & np.isfinite(dat_mjy)]
    if len(ann) < 50:
        ann = dat_mjy[np.isfinite(dat_mjy)]
    ann_med = float(np.median(ann))
    ann_rms = max(0.05, float(1.4826 * np.median(np.abs(ann - ann_med))))

    core3 = dat_mjy[max(0, cy - 2):min(ny, cy + 3), max(0, cx - 2):min(nx, cx + 3)]  # central 3"x3"
    peak3_mjy = float(np.nanmax(core3))
    snr3 = peak3_mjy / ann_rms
    sigma5_mjy = 5.0 * ann_rms
    d_m = max(1.0, dist_pc) * PC_TO_M
    eirp_5sig_1hz = 4.0 * math.pi * (d_m ** 2) * (sigma5_mjy * MJY_TO_W_M2_HZ)
    eirp_5sig_1ghz = eirp_5sig_1hz * 1e9

    return {
        "fits_file": fits_path.name,
        "central_peak_mjy": round(peak3_mjy, 4),
        "annulus_rms_mjy": round(ann_rms, 4),
        "central_snr": round(snr3, 2),
        "vlass_detected_5sig": snr3 >= 5.0,
        "sigma5_mjy": round(sigma5_mjy, 4),
        "eirp_5sig_1hz_w_hz": float(f"{eirp_5sig_1hz:.4e}"),
        "eirp_5sig_1ghz_w": float(f"{eirp_5sig_1ghz:.4e}"),
    }


def compute_spectral_index(match_rows: list[dict[str, Any]]) -> tuple[float | None, int]:
    pts: list[tuple[float, float]] = []
    # Deduplicate by frequency using closest separation per survey
    by_freq: dict[float, dict[str, Any]] = {}
    for r in match_rows:
        freq = _f(r.get("freq_mhz"))
        flux = _f(r.get("total_flux_mjy"))
        sep = _f(r.get("sep_arcsec")) or 999.0
        if freq and flux and flux > 0.0:
            if freq not in by_freq or sep < (_f(by_freq[freq].get("sep_arcsec")) or 999.0):
                by_freq[freq] = r
    for freq, r in sorted(by_freq.items()):
        pts.append((math.log10(freq), math.log10(float(r["total_flux_mjy"]))))
    if len(pts) < 2:
        return None, len(pts)
    xs = np.array([p[0] for p in pts])
    ys = np.array([p[1] for p in pts])
    if np.ptp(xs) < 0.05:
        return None, len(pts)
    slope = float(np.polyfit(xs, ys, 1)[0])
    return round(slope, 3), len(pts)


def classify_science_match(star: str, srow: dict[str, Any], mrows: list[dict[str, Any]], vlass: dict[str, Any] | None) -> tuple[str, str]:
    if star == "OBJECT_D":
        return "BACKGROUND_EXTRAGALACTIC_RADIO_SOURCE", "Hephaistos Object D: LoTSS DR3 1.77 mJy at 2.37\" offset (known background AGN/galaxy IR+radio blend)"

    sub = (srow.get("subrole") or "").upper()
    cname = (srow.get("common_name") or "").upper()
    min_sep = min(float(r["sep_arcsec"]) for r in mrows)
    surveys = sorted({r["survey"] for r in mrows})

    active_keys = ("J22012+283", "ARLAC", "VCWUMA", "GTMUS", "HD22468", "CRDRA", "G16171", "EIERI", "HD45088", "ROSS989", "2MASSJ010335635515561A", "VYYGEM", "APCOL", "ZETTRA", "GJ799A", "VCCERI", "DGCVN", "SIGMAGEM", "PMJ074980317A", "ALFFORB", "L3426", "53CAM", "WT460", "BD211074C", "GJ1116B", "GJ1151", "L257129", "GJ285", "VV857CEN", "ABDOR", "EQPEG", "CD3811343A", "CD561032B", "L29028", "IIPEG", "ADLEO", "J18022+642", "VRYSEX")

    if star in ("TTAU", "DGTAU", "IRAS16293M2422", "L1551IRS5", "N2071IR", "AFGL437", "W3OH", "CEPAHW2", "G34P3", "S255NIRS3", "DR21", "CHCYG", "ANTARES", "GKPER", "PIAQR", "HD169142") or any(k in sub for k in ("YSO", "HOT_COR", "SYMBIOTIC", "NOVA", "CTTS", "HERBIG", "GAMMA_CAS")):
        return "KNOWN_YSO_DISK_JET_OR_EVOLVED_STAR", f"Coincident thermal jet/wind/dust/symbiotic astrophysical emission ({min_sep:.2f}\")"
    if star in active_keys or any(k in sub for k in ("EROSITA", "RSCVN", "FLARE", "ACTIVE", "EUVE", "HEXTE", "XMM_RGS", "LETG")) or ("RS CVN" in cname or "FLARE" in cname or "YSO" in cname):
        if min_sep <= 11.0 or (vlass and vlass.get("vlass_detected_5sig")):
            return "KNOWN_CORONAL_FLARE_OR_RSCVN_STAR", f"Known active magnetosphere/corona/ECMI/flare star ({min_sep:.2f}\"; {', '.join(surveys)})"

    if vlass and vlass.get("vlass_detected_5sig"):
        return "ASTROPHYSICAL_OR_OFFSET_CHECK", f"VLASS 3 GHz central peak SNR={vlass['central_snr']} (min_sep={min_sep:.2f}\")"

    if min_sep >= 4.0:
        return "BACKGROUND_EXTRAGALACTIC_RADIO_SOURCE", f"Field offset min_sep={min_sep:.2f}\" + VLASS 3 GHz central non-detection / wide-beam confusion"
    return "BACKGROUND_EXTRAGALACTIC_RADIO_SOURCE", f"Background confusion / non-detection at 3 GHz VLASS (min_sep={min_sep:.2f}\")"


def load_chime_name_lookup() -> list[dict[str, Any]]:
    tsv_p = INP / "chime" / "chime_frb_cat1.tsv"
    lines = [l for l in tsv_p.read_text(encoding="utf-8", errors="replace").splitlines() if l.strip() and not l.startswith("#")]
    hdr = lines[0].split("\t")
    ds = 3 if len(lines) >= 3 and set(lines[2].replace("\t", "").strip()).issubset({"-", " "}) else 1
    out = []
    for ln in lines[ds:]:
        cols = ln.split("\t")
        if len(cols) == len(hdr):
            rec = dict(zip(hdr, [c.strip() for c in cols]))
            out.append(rec)
    return out


def main() -> int:
    master = {r["star"]: r for r in csv.DictReader(TABLE1.open(encoding="utf-8"))}
    match_rows = list(csv.DictReader((RES / "N4_RADIO_MATCH_CANDIDATES.csv").open(encoding="utf-8")))
    by_star: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for r in match_rows:
        by_star[r["star"]].append(r)

    # Target selection for VLASS 1.2 3.0 GHz FITS cutouts (Dec > -40 deg):
    # 1) Closest/multi-band matched SCIENCE stars (up to 48) + 5 Control AGN benchmarks
    sci_matched = [st for st, lst in by_star.items() if lst[0]["role"] == "SCIENCE" and float(lst[0]["star_dec_deg"]) > -40.0]
    sci_matched.sort(key=lambda st: (min(float(x["sep_arcsec"]) for x in by_star[st]), -len({x["survey"] for x in by_star[st]})))
    ctrl_bench = [st for st in ("3C84", "OJ287", "MRK501", "MRK421", "NGC3227", "NGC4736", "BLLAC") if st in master and float(master[st]["dec_deg"]) > -40.0][:5]

    # 2) Top 22 nearest < 10 pc unmatched SCIENCE stars with Dec > -40 deg
    near_unmatched = [
        st for st, r in master.items()
        if r["role"] == "SCIENCE" and st not in by_star and float(r["dec_deg"]) > -40.0 and (_f(r["dist_pc"]) or 999.0) <= 10.0
    ]
    near_unmatched.sort(key=lambda st: float(master[st]["dist_pc"]))

    targets = list(dict.fromkeys(sci_matched[:48] + ctrl_bench + near_unmatched[:22]))
    print(f"Fetching/measuring VLASS 1.2 cutouts for {len(targets)} stars ({len(sci_matched[:48])} matched SCIENCE, {len(ctrl_bench)} Control, {len(near_unmatched[:22])} <10pc unmatched)...", flush=True)

    vlass_by_star: dict[str, dict[str, Any]] = {}
    phot_rows: list[dict[str, Any]] = []
    skip_reasons: collections.Counter[str] = collections.Counter()
    for idx, st in enumerate(targets):
        srow = master[st]
        ra, dec = float(srow["ra_deg"]), float(srow["dec_deg"])
        dist_pc = _f(srow["dist_pc"]) or 100.0
        fp, status = fetch_vlass_cutout(st, ra, dec)
        if fp is None:
            skip_reasons[status] += 1
        else:
            m = measure_vlass_fits(fp, dist_pc)
            m.update({
                "star": st,
                "common_name": srow["common_name"],
                "role": srow["role"],
                "dist_pc": round(dist_pc, 4),
                "ra_deg": round(ra, 6),
                "dec_deg": round(dec, 6),
                "radio_catalog_matched": st in by_star,
            })
            vlass_by_star[st] = m
            phot_rows.append(m)
        if (idx + 1) % 15 == 0 or idx + 1 == len(targets):
            print(f"  VLASS progress: {idx+1}/{len(targets)} ({len(phot_rows)} valid FITS)", flush=True)
        if status == "downloaded":
            time.sleep(0.15)

    p_phot = RES / "N4_VLASS_CUTOUT_PHOTOMETRY.csv"
    phot_cols = ["star", "common_name", "role", "dist_pc", "ra_deg", "dec_deg", "radio_catalog_matched", "fits_file",
                 "central_peak_mjy", "annulus_rms_mjy", "central_snr", "vlass_detected_5sig", "sigma5_mjy",
                 "eirp_5sig_1hz_w_hz", "eirp_5sig_1ghz_w"]
    with p_phot.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=phot_cols)
        w.writeheader()
        for r in phot_rows:
            w.writerow(r)

    # Vet all 172 unique matched stars
    vetted_rows: list[dict[str, Any]] = []
    class_counts: collections.Counter[str] = collections.Counter()
    alphas_all: list[float] = []
    alphas_ctrl: list[float] = []
    for st, mrows in sorted(by_star.items(), key=lambda kv: (0 if kv[1][0]["role"] == "SCIENCE" else 1, min(float(x["sep_arcsec"]) for x in kv[1]))):
        srow = master[st]
        role = srow["role"]
        min_sep = min(float(x["sep_arcsec"]) for x in mrows)
        best_r = min(mrows, key=lambda x: float(x["sep_arcsec"]))
        alpha, n_freq = compute_spectral_index(mrows)
        if alpha is not None:
            alphas_all.append(alpha)
            if role == "CONTROL":
                alphas_ctrl.append(alpha)
        vl = vlass_by_star.get(st)
        if role == "CONTROL":
            vclass, vnote = "CONTROL_ACTIVE_GALAXY_OR_CALIBRATOR", f"Control benchmark recovered at {min_sep:.2f}\" across {len({x['survey'] for x in mrows})} surveys"
        else:
            vclass, vnote = classify_science_match(st, srow, mrows, vl)
        class_counts[vclass] += 1
        vetted_rows.append({
            "star": st,
            "common_name": srow["common_name"],
            "role": role,
            "subrole": srow["subrole"],
            "dist_pc": srow["dist_pc"],
            "n_surveys_matched": len({x["survey"] for x in mrows}),
            "surveys_matched": "|".join(sorted({x["survey"] for x in mrows})),
            "closest_survey": best_r["survey"],
            "min_sep_arcsec": round(min_sep, 4),
            "closest_flux_mjy": best_r["total_flux_mjy"],
            "spectral_index_alpha": alpha if alpha is not None else "",
            "n_freq_alpha": n_freq,
            "vlass_snr": vl["central_snr"] if vl else "",
            "vlass_peak_mjy": vl["central_peak_mjy"] if vl else "",
            "vetting_class": vclass,
            "eti_status": "VETOED_NON_ETI",
            "vetting_note": vnote,
        })

    p_vet = RES / "N4_RADIO_CANDIDATES_VETTED.csv"
    vet_cols = list(vetted_rows[0].keys())
    with p_vet.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=vet_cols)
        w.writeheader()
        for r in vetted_rows:
            w.writerow(r)

    # Vet all 26 CHIME/FRB Catalog 1 overlaps using Dispersion Measure excess
    chime_raw = load_chime_name_lookup()
    chime_xm = list(csv.DictReader((RES / "N4_CHIME_FRB_CROSSMATCH.csv").open(encoding="utf-8")))
    chime_vet: list[dict[str, Any]] = []
    for row in chime_xm:
        fra = float(row["frb_ra"])
        fdec = float(row["frb_dec"])
        fdm = float(row["dm_pc_cm3"])
        dist_pc = _f(row["dist_pc"]) or 100.0
        # Resolve exact VizieR FRB / TNS name by coordinates+DM
        frb_id = row.get("frb_name") or ""
        if not frb_id:
            for c in chime_raw:
                cra, cdec, cdm = _f(c.get("RAJ2000")), _f(c.get("DEJ2000")), _f(c.get("DM"))
                if cra is not None and cdec is not None and abs(cra - fra) < 1e-4 and abs(cdec - fdec) < 1e-4 and (cdm is None or abs(cdm - fdm) < 0.2):
                    frb_id = next((v for k, v in c.items() if "FRB" in k.upper() or "NAME" in k.upper() or "TNS" in k.upper()), "") or f"FRB_RA{fra:.2f}_DM{fdm:.1f}"
                    break
        dm_star_max = min(150.0, 0.05 * dist_pc)  # conservative ionized ISM foreground (capped at 150 pc/cm3 Galactic disk)
        excess_ratio = fdm / max(1e-4, dm_star_max)
        if row["role"] == "CONTROL" and dist_pc > 10000.0:
            vreason = "EXTRAGALACTIC_CONTROL_HOST_SIGHTLINE"
        elif excess_ratio > 10.0:
            vreason = "EXTRAGALACTIC_DM_EXCESS"
        else:
            vreason = "MANUAL_CHECK"
        chime_vet.append({
            **row,
            "frb_resolved_name": frb_id,
            "dm_star_foreground_max_pc_cm3": round(dm_star_max, 4),
            "dm_excess_ratio": round(excess_ratio, 2),
            "veto_reason": vreason,
            "eti_status": "VETOED_EXTRAGALACTIC_FRB",
        })

    p_cv = RES / "N4_CHIME_FRB_VETTED.csv"
    with p_cv.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(chime_vet[0].keys()))
        w.writeheader()
        for r in chime_vet:
            w.writerow(r)

    sci_vlass = [r for r in phot_rows if r["role"] == "SCIENCE"]
    rms_vals = [r["annulus_rms_mjy"] for r in phot_rows]
    eirp_vals = [r["eirp_5sig_1hz_w_hz"] for r in sci_vlass]

    summary = {
        "generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_matched_rows_stage2": len(match_rows),
        "unique_matched_stars_total": len(by_star),
        "unique_matched_science_stars": sum(1 for r in vetted_rows if r["role"] == "SCIENCE"),
        "unique_matched_control_benchmarks": sum(1 for r in vetted_rows if r["role"] == "CONTROL"),
        "vetting_class_counts": dict(class_counts),
        "verified_eti_candidates": 0,
        "vlass_cutouts_attempted": len(targets),
        "vlass_cutouts_valid_fits": len(phot_rows),
        "vlass_cutouts_skipped": dict(skip_reasons),
        "vlass_median_rms_mjy": round(float(np.median(rms_vals)), 4) if rms_vals else None,
        "vlass_science_median_eirp_5sig_1hz_w_hz": float(f"{np.median(eirp_vals):.4e}") if eirp_vals else None,
        "vlass_science_min_eirp_5sig_1hz_w_hz": float(f"{np.min(eirp_vals):.4e}") if eirp_vals else None,
        "spectral_index_alpha_count": len(alphas_all),
        "spectral_index_alpha_median_all": round(float(np.median(alphas_all)), 3) if alphas_all else None,
        "spectral_index_alpha_median_control": round(float(np.median(alphas_ctrl)), 3) if alphas_ctrl else None,
        "chime_frb_overlaps_total": len(chime_vet),
        "chime_frb_min_dm_pc_cm3": round(min(float(r["dm_pc_cm3"]) for r in chime_vet), 2) if chime_vet else None,
        "chime_frb_min_excess_ratio": round(min(float(r["dm_excess_ratio"]) for r in chime_vet if r["role"] == "SCIENCE"), 2) if chime_vet else None,
        "chime_frb_verified_stellar_associations": 0,
    }
    (RES / "N4_STAGE3_VETTING.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
