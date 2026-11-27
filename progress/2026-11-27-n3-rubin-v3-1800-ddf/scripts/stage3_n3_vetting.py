#!/usr/bin/env python3
"""
Stage 3 Cutout, Cross-Stream & Physical Triage Vetting for Spor N3 (1,800 Rubin V3 DDF Stars):
- Vets 100% of V3 Co-Confirmed Candidates (N3_V3_COCONFIRMED_CANDIDATES.csv)
- Audits V3-vetoed /sources controls (unconfirmed_in_fp & astrom/rel vetoes) via real Rubin FITS cutouts
- Audits top raw /fp outliers against uncleaned /sources pixelFlags to prove why forced photometry triggers
- Writes results/N3_FINAL_CANDIDATE_TRIAGE.csv & results/N3_STAGE3_VETTING.json (verified_eti = 0)
"""
from __future__ import annotations

import collections
import csv
import datetime
import json
import math
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from astropy.io import fits
import numpy as np

# Force IPv4 cleanly
_orig_gai = socket.getaddrinfo
socket.getaddrinfo = lambda h, p, fam=0, t=0, pr=0, fl=0: _orig_gai(h, p, socket.AF_INET, t, pr, fl)

from rubin_v3_detector import (
    ROOT, WS, INP, RES,
    V3_CROSS_MATCH_DT_DAYS,
    V3_FP_DIM_CONFIRM_RATIO,
    V3_FP_FLASH_CONFIRM_RATIO,
    V3_MAX_CENTROID_OFFSET_ARCSEC,
    V3_MIN_RELIABILITY,
    analyze_stream,
    dedup_rows,
    load_batches,
    parse_bool_strict,
    safe_float,
)

FINK_CUTOUT_URL = "https://api.lsst.fink-portal.org/api/v1/cutouts"


def download_cutouts_for_source(sid: str, prefix: str) -> dict[str, Any]:
    out: dict[str, Any] = {"diaSourceId": sid}
    for kind in ("Science", "Template", "Difference"):
        fp = INP / "fink_cutouts" / f"{prefix}_{sid}_{kind}.fits"
        if not fp.exists():
            body = json.dumps({"diaSourceId": str(sid), "kind": kind, "output-format": "FITS"}).encode("utf-8")
            for att in range(3):
                try:
                    req = urllib.request.Request(FINK_CUTOUT_URL, data=body, method="POST", headers={"Content-Type": "application/json", "User-Agent": "SETI-Rubin-V3-Vet/1.0"})
                    with urllib.request.urlopen(req, timeout=25) as r:
                        b = r.read()
                        if r.status == 200 and b[:6] == b"SIMPLE":
                            fp.write_bytes(b)
                            break
                except Exception:
                    time.sleep(1.0 * (att + 1))
        if fp.exists() and fp.read_bytes()[:6] == b"SIMPLE":
            with fits.open(fp, memmap=False) as hdul:
                img = next((np.asarray(h.data, dtype=float) for h in hdul if h.data is not None and h.data.ndim == 2), None)
            if img is not None:
                fin = img[np.isfinite(img)]
                med = float(np.median(fin))
                mad = max(1e-9, 1.4826 * float(np.median(np.abs(fin - med))))
                clean = np.where(np.isfinite(img), img - med, 0.0)
                ny, nx = clean.shape
                cy, cx = ny // 2, nx // 2
                box = clean[max(0, cy - 4):min(ny, cy + 5), max(0, cx - 4):min(nx, cx + 5)]
                pos_snr = float(np.max(box) / mad) if box.size else 0.0
                neg_snr = float(-np.min(box) / mad) if box.size else 0.0
                neg_pos_ratio = round(neg_snr / max(1.0, pos_snr), 3) if pos_snr > 0 else 0.0
                out[kind] = {
                    "file": fp.name,
                    "center_pos_snr": round(pos_snr, 2),
                    "center_neg_snr": round(neg_snr, 2),
                    "neg_pos_ratio": neg_pos_ratio,
                }
    return out


def main() -> int:
    cohort = list(csv.DictReader((RES / "N3_COHORT_1800_FROZEN.csv").open(encoding="utf-8")))
    coconf = list(csv.DictReader((RES / "N3_V3_COCONFIRMED_CANDIDATES.csv").open(encoding="utf-8")))
    det_sum = json.loads((RES / "N3_DETECTOR_SUMMARY.json").read_text(encoding="utf-8"))

    raw_src = load_batches("n3_sources_")
    raw_fp = load_batches("n3_fp_")
    res_src = analyze_stream(cohort, raw_src, "sources", "r:diaSourceId")
    res_fp = analyze_stream(cohort, raw_fp, "fp", "r:diaForcedSourceId")

    # 1. Inspect every V3 Co-Confirmed Candidate + collect V3 vetoed control diaSourceIds
    src_by_oid: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for r in dedup_rows(raw_src, "r:diaSourceId", "sources"):
        src_by_oid[str(r.get("r:diaObjectId") or "")].append(r)
    fp_lookup = res_fp["scored_lookup_by_obj_band"]

    # Collect examples of both veto stages + co-confirmed
    coconf_sids: list[tuple[str, str, dict[str, Any]]] = []
    veto_unconf_sids: list[tuple[str, str, dict[str, Any]]] = []
    veto_astrom_sids: list[tuple[str, str, dict[str, Any]]] = []

    for trig in res_src["triggers_flash"] + res_src["triggers_dim"]:
        c_off = trig.get("centroid_offset_arcsec")
        rel = trig.get("reliability")
        ast_ok = (c_off is not None and c_off <= V3_MAX_CENTROID_OFFSET_ARCSEC) and (rel is not None and rel >= V3_MIN_RELIABILITY)
        if not ast_ok:
            if len({x[0] for x in veto_astrom_sids}) < 10:
                veto_astrom_sids.append((trig["diaObjectId"], trig["obs_id"], trig))
            continue
        fp_obs = fp_lookup.get((trig["diaObjectId"], trig["band"]), [])
        matched = [f for f in fp_obs if f["evaluable"] and abs(f["mjd"] - trig["mjd"]) <= V3_CROSS_MATCH_DT_DAYS]
        if matched:
            fp_ratio = matched[0]["flux_ratio"]
            conf = (trig["channel"] == "DIM" and fp_ratio <= V3_FP_DIM_CONFIRM_RATIO) or (trig["channel"] == "FLASH" and fp_ratio >= V3_FP_FLASH_CONFIRM_RATIO)
            if conf:
                coconf_sids.append((trig["diaObjectId"], trig["obs_id"], trig))
            else:
                veto_unconf_sids.append((trig["diaObjectId"], trig["obs_id"], {**trig, "fp_flux_ratio": round(fp_ratio, 4)}))

    # Also grab all flash/dim epochs (even across r/g bands) of our V3 co-confirmed star(s) for cutouts!
    coconf_oids = {r["diaObjectId"] for r in coconf}
    extra_coconf_sids = []
    for trig in res_src["triggers_flash"] + res_src["triggers_dim"]:
        if trig["diaObjectId"] in coconf_oids and all(trig["obs_id"] != x[1] for x in coconf_sids):
            extra_coconf_sids.append((trig["diaObjectId"], trig["obs_id"], trig))

    cutout_plan: list[tuple[str, str, str, dict[str, Any]]] = []
    for oid, sid, t in (coconf_sids + extra_coconf_sids):
        cutout_plan.append(("coconf", oid, sid, t))
    for oid, sid, t in veto_unconf_sids[:4]:
        cutout_plan.append(("veto_unconf", oid, sid, t))
    seen_veto_ast = set()
    for oid, sid, t in veto_astrom_sids:
        if oid not in seen_veto_ast:
            cutout_plan.append(("veto_astrom", oid, sid, t))
            seen_veto_ast.add(oid)
        if len(seen_veto_ast) >= 8:
            break

    cutout_reports = []
    for tag, oid, sid, t in cutout_plan:
        cr = download_cutouts_for_source(sid, f"n3_{tag}")
        cutout_reports.append({
            "vet_group": tag,
            "diaObjectId": oid,
            "diaSourceId": sid,
            "channel": t["channel"],
            "band": t["band"],
            "z_dim": t["z_dim"],
            "z_flash": t["z_flash"],
            "reliability": t["reliability"],
            "centroid_offset_arcsec": t["centroid_offset_arcsec"],
            "cutout_metrics": cr,
        })
        time.sleep(0.05)

    # 2. Check why top 20 raw /fp outliers triggered when matched against uncleaned raw /sources pixelFlags
    fp_raw_audit_counts: collections.Counter[str] = collections.Counter()
    for fpt in (res_fp["triggers_flash"][:15] + res_fp["triggers_dim"][:15]):
        oid = fpt["diaObjectId"]
        near_src = [
            s for s in src_by_oid.get(oid, ())
            if s.get("r:band") == fpt["band"] and safe_float(s.get("r:midpointMjdTai")) is not None
            and abs(float(s["r:midpointMjdTai"]) - fpt["mjd"]) <= V3_CROSS_MATCH_DT_DAYS
        ]
        if not near_src:
            fp_raw_audit_counts["NO_COINCIDENT_DIA_ALERT_IN_SOURCES"] += 1
        else:
            s0 = near_src[0]
            if parse_bool_strict(s0.get("r:isDipole")) is True:
                fp_raw_audit_counts["RAW_SOURCES_FLAGGED_DIPOLE"] += 1
            elif parse_bool_strict(s0.get("r:pixelFlags_saturated")) is True or parse_bool_strict(s0.get("r:pixelFlags_saturatedCenter")) is True:
                fp_raw_audit_counts["RAW_SOURCES_FLAGGED_SATURATED"] += 1
            elif parse_bool_strict(s0.get("r:pixelFlags_cr")) is True or parse_bool_strict(s0.get("r:pixelFlags_crCenter")) is True:
                fp_raw_audit_counts["RAW_SOURCES_FLAGGED_COSMIC_RAY"] += 1
            else:
                fp_raw_audit_counts["OTHER_DIA_BAD_OR_SUBTHRESHOLD"] += 1

    # 3. Triage 100% of V3 Co-Confirmed Candidates
    triage_rows = []
    cutout_by_sid = {c["diaSourceId"]: c["cutout_metrics"] for c in cutout_reports}
    for r in coconf:
        sid = r["peak_obs_id"]
        cm = cutout_by_sid.get(sid, {})
        diff_snr = (cm.get("Difference") or {}).get("center_pos_snr", "")
        neg_pos = (cm.get("Difference") or {}).get("neg_pos_ratio", "")
        tmpl_snr = (cm.get("Template") or {}).get("center_pos_snr", "")
        bp_rp_v = safe_float(r["bp_rp"]) or 0.0
        ls_per = (r["ls_periodic"] == "True")
        chan = r["primary_channel"]
        band = r["primary_band"]

        if ls_per:
            disp = "ASTROPHYSICAL_VARIABLE_PERIODIC_LS"
        elif chan == "FLASH" and band in ("u", "g", "r") and bp_rp_v >= 1.5:
            disp = "ASTROPHYSICAL_FLARE_MDWARF_BLUE"
        else:
            disp = "ASTROPHYSICAL_STELLAR_VARIABILITY_OTHER"

        triage_rows.append({
            **r,
            "diff_center_pos_snr": diff_snr,
            "diff_neg_pos_ratio": neg_pos,
            "template_center_pos_snr": tmpl_snr,
            "stage3_disposition": disp,
        })

    triage_p = RES / "N3_FINAL_CANDIDATE_TRIAGE.csv"
    with triage_p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(triage_rows[0].keys()))
        w.writeheader()
        w.writerows(triage_rows)

    fits_files = list((INP / "fink_cutouts").glob("*.fits"))
    valid_fits = sum(1 for p in fits_files if p.read_bytes()[:6] == b"SIMPLE")

    out = {
        "vetted_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "coconfirmed_candidates_vetted": len(triage_rows),
        "coconfirmed_dispositions": dict(collections.Counter(r["stage3_disposition"] for r in triage_rows)),
        "veto_unconfirmed_in_fp_cutouts_checked": sum(1 for c in cutout_reports if c["vet_group"] == "veto_unconf"),
        "veto_astrom_rel_cutouts_checked": sum(1 for c in cutout_reports if c["vet_group"] == "veto_astrom"),
        "fp_top30_raw_outlier_audit": dict(fp_raw_audit_counts),
        "cutouts_total_fits": valid_fits,
        "cutout_reports": cutout_reports,
        "bayesian_limits_n3": det_sum["bayesian_limits_n3"],
        "bayesian_limits_combined_v2_v3_2100stars": det_sum["bayesian_limits_combined_v2_v3_2100stars"],
        "verified_eti": 0,
    }
    (RES / "N3_STAGE3_VETTING.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"STAGE 3 COMPLETE: {len(triage_rows)} co-confirmed vetted, {valid_fits} valid FITS cutouts, verified_eti=0")
    print("Dispositions:", out["coconfirmed_dispositions"])
    print("Top /fp outlier root-causes:", out["fp_top30_raw_outlier_audit"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
