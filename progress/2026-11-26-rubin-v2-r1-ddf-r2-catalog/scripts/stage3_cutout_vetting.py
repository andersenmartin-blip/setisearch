#!/usr/bin/env python3
"""
Stage 3: Download official Science, Template, and Difference FITS cutouts via
Fink LSST /api/v1/cutouts for top R1 triggers (up to 12) + all direct <=2.0" R2 matches,
compute quantitative stamp metrics (SNR, centroid offset, 1px CR concentration,
negative dipole lobe ratio, NaN fraction), cross-match triggered stars against
SIMBAD TAP, and emit final candidate triage without touching locked detector.
"""
from __future__ import annotations

import csv
import datetime
import hashlib
import io
import json
import math
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import numpy as np
from astropy.io import fits

WS = Path("/home/martin/SETI_Fortsaettelse_2026-11-14/analysis_workspace/work_rubin_v2_20261126_r1_ddf_and_r2_catalog")
INPUTS = Path("/home/martin/SETI_Fortsaettelse_2026-11-14/inputs_rubin_v2_20261126")
RESULTS = WS / "results"
FINK_BASE = "https://api.lsst.fink-portal.org"
SIMBAD_TAP = "https://simbad.cds.unistra.fr/simbad/sim-tap/sync"


def now_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def get_bytes_with_retry(url: str, save_path: Path, max_attempts: int = 5, timeout: int = 35) -> bytes:
    if save_path.exists():
        return save_path.read_bytes()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    last_err = None
    for attempt in range(1, max_attempts + 1):
        t0 = time.monotonic()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SETI-Rubin-V2/1.0"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                rec = {
                    "utc": now_utc(),
                    "url": url,
                    "attempt": attempt,
                    "http_status": r.status,
                    "elapsed_s": round(time.monotonic() - t0, 3),
                    "bytes": len(raw),
                    "sha256": sha256_bytes(raw),
                }
                save_path.write_bytes(raw)
                save_path.with_suffix(save_path.suffix + ".receipt.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
                return raw
        except Exception as exc:
            last_err = repr(exc)
            time.sleep(min(20, 1.5 * (2 ** (attempt - 1))))
    raise RuntimeError(f"Failed cutout {url}: {last_err}")


def analyze_fits_stamp(fits_bytes: bytes) -> dict[str, Any]:
    with fits.open(io.BytesIO(fits_bytes)) as hdul:
        img = None
        for hdu in hdul:
            if hdu.data is not None and hdu.data.ndim >= 2:
                img = np.array(hdu.data, dtype=float)
                break
        if img is None:
            return {"valid_fits": False}
        h, w = img.shape[-2], img.shape[-1]
        if img.ndim > 2:
            img = img.reshape((-1, h, w))[0]
        finite = np.isfinite(img)
        nan_frac = float(1.0 - np.mean(finite))
        if np.sum(finite) < 25:
            return {"valid_fits": True, "shape": [int(h), int(w)], "nan_frac": round(nan_frac, 4), "too_many_nans": True}
        cy, cx = h // 2, w // 2
        yy, xx = np.mgrid[0:h, 0:w]
        rr = np.hypot(xx - cx, yy - cy)
        bg_mask = finite & (rr >= min(8.0, 0.25 * min(h, w))) & (rr <= min(18.0, 0.48 * min(h, w)))
        if np.sum(bg_mask) < 10:
            bg_mask = finite
        bg_vals = img[bg_mask]
        bg_med = float(np.median(bg_vals))
        bg_mad = float(np.median(np.abs(bg_vals - bg_med)))
        bg_sigma = max(1e-12, 1.4826 * bg_mad)

        box5 = img[max(0, cy - 2):min(h, cy + 3), max(0, cx - 2):min(w, cx + 3)] - bg_med
        box5_fin = np.where(np.isfinite(box5), box5, 0.0)
        abs5 = np.abs(box5_fin)
        max_pos = float(np.max(box5_fin))
        min_neg = float(np.min(box5_fin))
        peak_abs = float(np.max(abs5))
        peak_snr = float(peak_abs / bg_sigma)
        pos_sum = float(np.sum(np.maximum(0.0, box5_fin)))
        abs_sum = float(np.sum(abs5))
        cr_conc = float(peak_abs / abs_sum) if abs_sum > 0 else 0.0
        # Signed dipole ratio: min(|neg|, pos) / max(|neg|, pos) in 5x5 when both lobes significant
        pos_max = max(0.0, max_pos)
        neg_max = max(0.0, -min_neg)
        dipole_ratio = float(min(pos_max, neg_max) / max(pos_max, neg_max, 1e-12))

        # Flux-weighted centroid offset inside 7x7 box
        y0, y1 = max(0, cy - 3), min(h, cy + 4)
        x0, x1 = max(0, cx - 3), min(w, cx + 4)
        sub = np.abs(np.where(np.isfinite(img[y0:y1, x0:x1] - bg_med), img[y0:y1, x0:x1] - bg_med, 0.0))
        s_tot = float(np.sum(sub))
        if s_tot > 0:
            sy, sx = np.mgrid[y0:y1, x0:x1]
            cx_est = float(np.sum(sx * sub) / s_tot)
            cy_est = float(np.sum(sy * sub) / s_tot)
            centroid_offset_px = float(math.hypot(cx_est - cx, cy_est - cy))
        else:
            centroid_offset_px = float("nan")

        return {
            "valid_fits": True,
            "shape": [int(h), int(w)],
            "nan_frac": round(nan_frac, 4),
            "bg_med": round(bg_med, 4),
            "bg_sigma": round(bg_sigma, 4),
            "max_pos": round(max_pos, 3),
            "min_neg": round(min_neg, 3),
            "peak_snr": round(peak_snr, 2),
            "cr_1px_conc": round(cr_conc, 4),
            "dipole_lobe_ratio": round(dipole_ratio, 4),
            "centroid_offset_px": round(centroid_offset_px, 3) if math.isfinite(centroid_offset_px) else None,
        }


def query_simbad_cone(ra: float, dec: float, radius_deg: float = 0.001) -> list[dict[str, str]]:
    adql = (
        "SELECT main_id, otype, sp_type, ra, dec "
        f"FROM basic WHERE CONTAINS(POINT('ICRS', ra, dec), CIRCLE('ICRS', {ra:.7f}, {dec:.7f}, {radius_deg:.6f})) = 1"
    )
    data = urllib.parse.urlencode({"REQUEST": "doQuery", "LANG": "ADQL", "FORMAT": "csv", "QUERY": adql}).encode()
    req = urllib.request.Request(SIMBAD_TAP, data=data, headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "SETI-Rubin-V2/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            txt = r.read().decode("utf-8", errors="replace")
        return list(csv.DictReader(io.StringIO(txt)))
    except Exception:
        return []


def main() -> int:
    dim_trigs = json.loads((RESULTS / "R1_SOURCES_TRIGGERS_DIM.json").read_text(encoding="utf-8"))
    fl_trigs = json.loads((RESULTS / "R1_SOURCES_TRIGGERS_FLASH.json").read_text(encoding="utf-8"))
    triage = json.loads((RESULTS / "R1_SOURCES_TRIAGE.json").read_text(encoding="utf-8"))
    triage_map = {str(t["diaObjectId"]): t for t in triage}

    # Select up to 11 unique dimming objects + up to 6 unique flash objects (up to 12+ R1 triggered candidates)
    chosen: list[dict[str, Any]] = []
    seen_oid: set[str] = set()
    for ch_name, tlist, lim in [("R1_DIM", dim_trigs, 11), ("R1_FLASH", fl_trigs, 6)]:
        cnt = 0
        for tr in tlist:
            oid = str(tr["diaObjectId"])
            sid = str(tr["obs_id"])
            if oid in seen_oid or not sid:
                continue
            seen_oid.add(oid)
            chosen.append({
                "label": ch_name,
                "diaObjectId": oid,
                "diaSourceId": sid,
                "band": tr["band"],
                "mjd": tr["mjd"],
                "z_score": tr["z_dim"] if ch_name == "R1_DIM" else tr["z_flash"],
                "flux_ratio": tr["flux_ratio"],
                "star_tag": triage_map.get(oid, {}).get("field", ""),
            })
            cnt += 1
            if cnt >= lim:
                break

    # Add ALL direct <= 2.0" R2 catalog matches (plus the 1 companion match if <= 10" so R2 visual audit is complete)
    r2_matches = list(csv.DictReader((RESULTS / "R2_CATALOG_MATCHES.csv").open(encoding="utf-8")))
    r2_raw_src: list[dict[str, Any]] = []
    for p in sorted((INPUTS / "r2_catalog").glob("r2_sources_*.json")):
        if not p.name.endswith(".receipt.json"):
            r2_raw_src.extend(json.loads(p.read_text(encoding="utf-8"), parse_int=str))
    r2_by_oid: dict[str, list[dict[str, Any]]] = {}
    for row in r2_raw_src:
        r2_by_oid.setdefault(str(row.get("r:diaObjectId") or ""), []).append(row)

    for m in r2_matches:
        oid = str(m["diaObjectId"])
        if oid in seen_oid:
            continue
        srows = r2_by_oid.get(oid, [])
        if not srows:
            continue
        srows.sort(key=lambda x: float(x.get("r:midpointMjdTai") or 0.0), reverse=True)
        top_s = srows[0]
        seen_oid.add(oid)
        chosen.append({
            "label": f"R2_{m['star']}",
            "diaObjectId": oid,
            "diaSourceId": str(top_s.get("r:diaSourceId") or ""),
            "band": str(top_s.get("r:band") or ""),
            "mjd": float(top_s.get("r:midpointMjdTai") or 0.0),
            "z_score": float(top_s.get("r:snr") or 0.0),
            "flux_ratio": 1.0,
            "star_tag": m["star"],
        })

    print(f"Downloading FITS cutouts (Science/Template/Difference) for {len(chosen)} targets...", flush=True)
    cutout_results = []
    for item in chosen:
        sid = item["diaSourceId"]
        stamps = {}
        for kind in ("Science", "Template", "Difference"):
            url = f"{FINK_BASE}/api/v1/cutouts?diaSourceId={sid}&kind={kind}&output-format=FITS"
            out_p = INPUTS / "fink_cutouts" / f"{sid}_{kind}.fits"
            try:
                raw = get_bytes_with_retry(url, out_p)
                stamps[kind] = analyze_fits_stamp(raw)
                stamps[kind]["fits_bytes"] = len(raw)
                stamps[kind]["fits_path"] = str(out_p)
            except Exception as exc:
                stamps[kind] = {"valid_fits": False, "error": str(exc)}
        diff = stamps.get("Difference", {})
        is_dipole_stamp = (diff.get("dipole_lobe_ratio", 0.0) >= 0.55) and (diff.get("peak_snr", 0.0) >= 5.0)
        is_cr_stamp = diff.get("cr_1px_conc", 0.0) >= 0.65
        is_offcenter = (diff.get("centroid_offset_px") or 0.0) >= 2.2
        cutout_results.append({
            **item,
            "stamps": stamps,
            "stamp_dipole_flag": is_dipole_stamp,
            "stamp_cr_flag": is_cr_stamp,
            "stamp_offcenter_flag": is_offcenter,
        })

    # SIMBAD TAP cross-check for ALL R1 triggered objects
    print(f"Checking SIMBAD TAP for {len(triage)} R1 triggered objects...", flush=True)
    simbad_hits: dict[str, list[dict[str, str]]] = {}
    for t in triage:
        oid = t["diaObjectId"]
        ra = float(t["ra_deg"])
        dec = float(t["dec_deg"])
        hits = query_simbad_cone(ra, dec, radius_deg=0.0009)
        simbad_hits[oid] = hits
        time.sleep(0.15)

    # Load R1 raw /sources and /fp to compute cross-stream same-epoch/same-night fp consistency & diff-flux sign
    r1_raw_src: list[dict[str, Any]] = []
    for p in sorted((INPUTS / "fink_sources").glob("r1_sources_*.json")):
        if not p.name.endswith(".receipt.json"):
            r1_raw_src.extend(json.loads(p.read_text(encoding="utf-8"), parse_int=str))
    r1_raw_fp: list[dict[str, Any]] = []
    for p in sorted((INPUTS / "fink_fp").glob("r1_fp_*.json")):
        if not p.name.endswith(".receipt.json"):
            r1_raw_fp.extend(json.loads(p.read_text(encoding="utf-8"), parse_int=str))

    src_by_sid: dict[str, dict[str, Any]] = {str(r.get("r:diaSourceId") or ""): r for r in r1_raw_src if r.get("r:diaSourceId")}
    fp_by_oid_band: dict[tuple[str, str], list[tuple[float, float]]] = {}
    for fr in r1_raw_fp:
        oid_f = str(fr.get("r:diaObjectId") or "")
        b_f = str(fr.get("r:band") or "").strip()
        try:
            mjd_f = float(fr["r:midpointMjdTai"])
            fl_f = float(fr["r:scienceFlux"])
            if oid_f and b_f and math.isfinite(mjd_f) and math.isfinite(fl_f):
                fp_by_oid_band.setdefault((oid_f, b_f), []).append((mjd_f, fl_f))
        except (TypeError, ValueError, KeyError):
            pass

    top_trig_by_oid: dict[str, dict[str, Any]] = {}
    for tr in dim_trigs + fl_trigs:
        oid_t = str(tr["diaObjectId"])
        z_t = max(float(tr.get("z_dim", 0.0)), float(tr.get("z_flash", 0.0)))
        if oid_t not in top_trig_by_oid or z_t > top_trig_by_oid[oid_t]["_z"]:
            top_trig_by_oid[oid_t] = {**tr, "_z": z_t}

    cutout_by_oid = {c["diaObjectId"]: c for c in cutout_results}
    final_triage_rows = []
    class_counts: dict[str, int] = {}
    for t in triage:
        oid = str(t["diaObjectId"])
        cinfo = cutout_by_oid.get(oid)
        shits = simbad_hits.get(oid, [])
        sim_str = ";".join(f"{h.get('main_id','')}({h.get('otype','')})" for h in shits)
        sim_otypes = " ".join(h.get("otype", "") for h in shits).upper()

        tr0 = top_trig_by_oid.get(oid, {})
        tr_band = str(tr0.get("band") or "")
        tr_mjd = float(tr0.get("mjd") or 0.0)
        tr_sid = str(tr0.get("obs_id") or "")
        raw_srow = src_by_sid.get(tr_sid, {})
        diff_psf_flux = raw_srow.get("r:psfFlux")
        rel_val = raw_srow.get("r:reliability")
        try:
            diff_psf_val = float(diff_psf_flux) if diff_psf_flux not in (None, "") else float("nan")
        except (TypeError, ValueError):
            diff_psf_val = float("nan")
        try:
            rel_flt = float(rel_val) if rel_val not in (None, "") else float("nan")
        except (TypeError, ValueError):
            rel_flt = float("nan")
        try:
            s_ra = float(raw_srow.get("r:ra") or "nan")
            s_dec = float(raw_srow.get("r:dec") or "nan")
            o_ra = float(t["ra_deg"])
            o_dec = float(t["dec_deg"])
            src_offset_arcsec = math.hypot((s_ra - o_ra) * math.cos(math.radians(o_dec)), s_dec - o_dec) * 3600.0
        except (TypeError, ValueError):
            src_offset_arcsec = float("nan")

        fp_pts = fp_by_oid_band.get((oid, tr_band), [])
        fp_med = float(np.median([p[1] for p in fp_pts])) if len(fp_pts) >= 5 else float("nan")
        near_fp = [p for p in fp_pts if abs(p[0] - tr_mjd) <= 0.5]
        same_epoch_fp = [p for p in fp_pts if abs(p[0] - tr_mjd) <= 0.02]
        fp_ratio_near = float(near_fp[0][1] / fp_med) if (near_fp and math.isfinite(fp_med) and fp_med > 0) else float("nan")
        fp_ratio_exact = float(same_epoch_fp[0][1] / fp_med) if (same_epoch_fp and math.isfinite(fp_med) and fp_med > 0) else float("nan")
        fp_confirms_dim = (math.isfinite(fp_ratio_exact) and fp_ratio_exact <= 0.85) or (math.isfinite(fp_ratio_near) and fp_ratio_near <= 0.85)
        fp_unitary_no_dim = (math.isfinite(fp_ratio_exact) and fp_ratio_exact >= 0.90) or (math.isfinite(fp_ratio_near) and fp_ratio_near >= 0.90)

        prov = t["provisional_class"]
        if cinfo and (cinfo["stamp_dipole_flag"] or cinfo["stamp_cr_flag"] or cinfo["stamp_offcenter_flag"]):
            final_disp = "INSTRUMENTAL_ARTIFACT_CUTOUT_VETO"
        elif t.get("periodic_flag"):
            final_disp = "ASTROPHYSICAL_VARIABLE_PERIODIC_LS"
        elif any(k in sim_otypes for k in ("EB", "ECL", "RR", "CEP", "PUL", "BY", "RS", "VAR", "V*")):
            final_disp = "ASTROPHYSICAL_KNOWN_VARIABLE_OR_BINARY"
        elif any(k in sim_otypes for k in ("QSO", "AGN", "BLL", "SEYF")):
            final_disp = "EXTRAGALACTIC_AGN_QSO_CONTAMINANT"
        elif "MDWARF" in prov:
            final_disp = "ASTROPHYSICAL_FLARE_MDWARF_CANDIDATE"
        elif int(t["n_trig_dim"]) >= 1 and not fp_confirms_dim and (fp_unitary_no_dim or (math.isfinite(diff_psf_val) and diff_psf_val > 0.0)):
            final_disp = "INSTRUMENTAL_DIA_CENTROID_PSF_BIAS"
        elif (math.isfinite(src_offset_arcsec) and src_offset_arcsec >= 0.50) and (math.isfinite(rel_flt) and rel_flt < 0.35):
            final_disp = "INSTRUMENTAL_CENTROID_HOP_LOW_REL"
        elif int(t["n_trig_dim"]) >= 1 and len(t["dim_bands"]) >= 2:
            final_disp = "UNRESOLVED_MULTIBAND_DIM_CANDIDATE"
        elif int(t["n_trig_flash"]) >= 1 and int(t["n_trig_dim"]) == 0:
            final_disp = "SINGLE_OR_TRANSIENT_OPTICAL_FLARE_VETTED"
        else:
            final_disp = "SINGLE_OR_APERIODIC_DIM_NEEDS_FOLLOWUP"

        class_counts[final_disp] = class_counts.get(final_disp, 0) + 1
        final_triage_rows.append({
            **t,
            "simbad_matches": sim_str,
            "diff_psf_flux": round(diff_psf_val, 2) if math.isfinite(diff_psf_val) else "",
            "src_reliability": round(rel_flt, 4) if math.isfinite(rel_flt) else "",
            "src_offset_arcsec": round(src_offset_arcsec, 4) if math.isfinite(src_offset_arcsec) else "",
            "fp_same_night_ratio": round(fp_ratio_near, 4) if math.isfinite(fp_ratio_near) else "",
            "fp_same_epoch_ratio": round(fp_ratio_exact, 4) if math.isfinite(fp_ratio_exact) else "",
            "cutout_vetted": cinfo is not None,
            "cutout_diff_peak_snr": cinfo["stamps"].get("Difference", {}).get("peak_snr", "") if cinfo else "",
            "cutout_dipole_ratio": cinfo["stamps"].get("Difference", {}).get("dipole_lobe_ratio", "") if cinfo else "",
            "cutout_cr_conc": cinfo["stamps"].get("Difference", {}).get("cr_1px_conc", "") if cinfo else "",
            "cutout_centroid_px": cinfo["stamps"].get("Difference", {}).get("centroid_offset_px", "") if cinfo else "",
            "final_disposition": final_disp,
        })

    with (RESULTS / "R1_FINAL_CANDIDATE_TRIAGE.csv").open("w", newline="", encoding="utf-8") as fh:
        if final_triage_rows:
            w = csv.DictWriter(fh, fieldnames=list(final_triage_rows[0].keys()))
            w.writeheader()
            for r in final_triage_rows:
                w.writerow(r)

    out_json = {
        "utc": now_utc(),
        "cutouts_fetched": len(cutout_results),
        "r1_triggered_objects_total": len(final_triage_rows),
        "final_disposition_counts": class_counts,
        "cutout_details": cutout_results,
    }
    (RESULTS / "STAGE3_CUTOUT_AND_SIMBAD_VETTING.json").write_text(json.dumps(out_json, indent=2) + "\n", encoding="utf-8")
    print(f"STAGE3 COMPLETE: cutouts={len(cutout_results)}, triage_counts={class_counts}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
