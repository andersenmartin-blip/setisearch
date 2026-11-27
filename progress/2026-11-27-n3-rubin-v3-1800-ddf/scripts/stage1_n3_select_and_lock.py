#!/usr/bin/env python3
"""
Stage 1: Extract all 530 previously used Rubin diaObjectIds + Gaia IDs (read-only from Rubin V2),
reconstruct the zero-overlap Gaia-isolated DDF stellar pool from read-only metadata, freeze
1,800 brand-new stars in N3_COHORT_1800_FROZEN.csv, and seal METHOD_LOCK.json +
IMPLEMENTATION_LOCK.json BEFORE any Stage 2 photometry download.
"""
from __future__ import annotations

import collections
import csv
import datetime
import hashlib
import json
import math
from pathlib import Path
from typing import Any

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace" / "work_n3_20261127_rubin_v3_1800ddf"
INP = ROOT / "inputs_n3_20261127"
RES = WS / "results"
RV2_RES = ROOT / "analysis_workspace" / "work_rubin_v2_20261126_r1_ddf_and_r2_catalog" / "results"
RV2_INP = ROOT / "inputs_rubin_v2_20261126"
PROG = ROOT / "setisearch" / "progress" / "2026-11-27-n3-rubin-v3-1800-ddf"

EPOCH_GAIA_JYEAR = 2016.0
EPOCH_RUBIN_JYEAR = 2026.85
DDFS = ("COSMOS", "EDFS_B", "ELAIS_S1")


def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _f(v: Any) -> float | None:
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def angsep_arcsec(ra1: float, dec1: float, ra2: float, dec2: float) -> float:
    r1, d1, r2, d2 = map(math.radians, (ra1, dec1, ra2, dec2))
    cos_a = math.sin(d1) * math.sin(d2) + math.cos(d1) * math.cos(d2) * math.cos(r1 - r2)
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_a)))) * 3600.0


def main() -> int:
    for d in [WS / "scripts", WS / "results", WS / "figures", WS / "cutouts", WS / "audit",
              INP / "fink_sources", INP / "fink_fp", INP / "fink_cutouts", INP / "vetting",
              PROG / "scripts", PROG / "results", PROG / "figures", PROG / "audit",
              ROOT / "archives_n3"]:
        d.mkdir(parents=True, exist_ok=True)

    # 1. Load all 530 excluded IDs read-only from RV2
    excl_rows = []
    excl_oids: set[str] = set()
    excl_gaia: set[str] = set()
    sources = [
        ("prior_210", RV2_RES / "EXCLUDED_PRIOR_RUBIN_210IDS.csv", "diaObjectId", "matched_gaia_source_id"),
        ("r1_300", RV2_RES / "R1_COHORT_FROZEN.csv", "diaObjectId", "gaia_source_id"),
        ("r1_ctrl_20", RV2_RES / "R1_CONTROLS_FROZEN.csv", "diaObjectId", "gaia_source_id"),
    ]
    for tag, path, okey, gkey in sources:
        for r in csv.DictReader(path.open(encoding="utf-8")):
            oid = str(r.get(okey) or "").strip()
            gid = str(r.get(gkey) or "").strip()
            if oid and oid not in excl_oids:
                excl_oids.add(oid)
                excl_rows.append({"diaObjectId": oid, "source_cohort": tag, "gaia_source_id": gid})
            if gid:
                excl_gaia.add(gid)

    assert len(excl_oids) == 530, f"Expected 530 prior IDs, got {len(excl_oids)}"
    with (RES / "EXCLUDED_PRIOR_530IDS.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["diaObjectId", "source_cohort", "gaia_source_id"])
        w.writeheader()
        w.writerows(excl_rows)

    # 2. Reconstruct exact Gaia-isolated candidate pool across DDFs from read-only metadata
    dt_yr = EPOCH_RUBIN_JYEAR - EPOCH_GAIA_JYEAR
    all_clean: list[dict[str, Any]] = []

    for fname in DDFS:
        fink_objs = json.loads((RV2_INP / "metadata" / f"fink_cone_{fname}.json").read_text(encoding="utf-8"), parse_int=str)
        gaia_rows = list(csv.DictReader((RV2_INP / "gaia" / f"gaia_dr3_{fname}.csv").open(encoding="utf-8")))

        grid: dict[tuple[int, int], list[tuple[float, float, dict[str, Any]]]] = collections.defaultdict(list)
        for g in gaia_rows:
            gra, gdec = float(g["ra"]), float(g["dec"])
            pmra, pmdec = _f(g.get("pmra")) or 0.0, _f(g.get("pmdec")) or 0.0
            cos_d = max(0.05, math.cos(math.radians(gdec)))
            ra_p = gra + (pmra * dt_yr) / (3600000.0 * cos_d)
            dec_p = gdec + (pmdec * dt_yr) / 3600000.0
            grid[(int(math.floor(ra_p * 100)), int(math.floor(dec_p * 100)))].append((ra_p, dec_p, g))

        depth_by_oid: dict[str, dict[str, Any]] = {}
        for mp in sorted((RV2_INP / "metadata").glob(f"fink_objects_meta_{fname}_*.json")):
            if mp.name.endswith(".receipt.json"):
                continue
            for row in json.loads(mp.read_text(encoding="utf-8"), parse_int=str):
                depth_by_oid[str(row.get("r:diaObjectId") or "")] = row

        for f in fink_objs:
            oid = str(f.get("r:diaObjectId") or "")
            gid_cand = ""
            if not oid or oid in excl_oids:
                continue
            fra, fdec = _f(f.get("r:ra")), _f(f.get("r:dec"))
            if fra is None or fdec is None:
                continue
            cx, cy = int(math.floor(fra * 100)), int(math.floor(fdec * 100))
            neighbors = []
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for r_p, d_p, g in grid.get((cx + dx, cy + dy), ()):
                        sep = angsep_arcsec(fra, fdec, r_p, d_p)
                        if sep <= 3.0:
                            neighbors.append((sep, g))
            if len(neighbors) != 1:
                continue
            sep0, g0 = neighbors[0]
            if sep0 > 1.0:
                continue
            gid_cand = str(g0["source_id"])
            if gid_cand in excl_gaia:
                continue
            gmag, ruwe = _f(g0.get("phot_g_mean_mag")), _f(g0.get("ruwe"))
            pstar = _f(g0.get("classprob_dsc_combmod_star")) or 0.0
            plx_snr, plx = _f(g0.get("parallax_over_error")) or 0.0, _f(g0.get("parallax")) or 0.0
            pmra, pmra_e = _f(g0.get("pmra")) or 0.0, _f(g0.get("pmra_error"))
            pmdec, pmdec_e = _f(g0.get("pmdec")) or 0.0, _f(g0.get("pmdec_error"))
            pm_sig = math.hypot(pmra / pmra_e, pmdec / pmdec_e) if (pmra_e and pmdec_e and pmra_e > 0 and pmdec_e > 0) else 0.0
            dup = str(g0.get("duplicated_source") or "").strip().lower() in ("true", "1")
            if gmag is None or not (16.0 <= gmag <= 21.0) or ruwe is None or ruwe >= 1.4 or dup:
                continue
            if not ((pstar >= 0.85) or (plx_snr >= 3.0 and plx > 0.0) or (pm_sig >= 3.0)):
                continue

            d = depth_by_oid.get(oid, {})
            band_counts = {b: int(d.get(f"r:{b}_psfFluxNdata") or 0) for b in ("u", "g", "r", "i", "z", "y")}
            max_band = max(band_counts.values()) if band_counts else 0
            n_dia = int(d.get("r:nDiaSources") or 0)
            if max_band < 8:
                continue
            all_clean.append({
                "diaObjectId": oid,
                "field": fname,
                "ra_deg": f"{fra:.7f}",
                "dec_deg": f"{fdec:.7f}",
                "gaia_source_id": gid_cand,
                "gaia_sep_arcsec": f"{sep0:.4f}",
                "phot_g_mean_mag": f"{gmag:.4f}",
                "bp_rp": g0.get("bp_rp") or "",
                "parallax_mas": g0.get("parallax") or "",
                "ruwe": f"{ruwe:.4f}",
                "classprob_star": f"{pstar:.4f}",
                "phot_variable_flag": g0.get("phot_variable_flag") or "",
                "nDiaSources": str(n_dia),
                "max_band_ndata": str(max_band),
                "band_ndata_summary": ";".join(f"{b}:{band_counts[b]}" for b in ("u", "g", "r", "i", "z", "y")),
            })

    # Deterministically balance up to 1,800 unique stars (all COSMOS <=900 then fill from EDFS_B)
    by_field = collections.defaultdict(list)
    for c in all_clean:
        by_field[c["field"]].append(c)
    for fn in by_field:
        by_field[fn].sort(key=lambda x: (-int(x["max_band_ndata"]), -int(x["nDiaSources"]), x["diaObjectId"]))

    selected: list[dict[str, Any]] = []
    used_o: set[str] = set()
    used_g: set[str] = set()
    for cap in (900, 1800):
        for fn in DDFS:
            taken = sum(1 for s in selected if s["field"] == fn)
            for cand in by_field.get(fn, []):
                if len(selected) >= 1800 or taken >= cap:
                    break
                if cand["diaObjectId"] in used_o or cand["gaia_source_id"] in used_g:
                    continue
                selected.append(cand)
                used_o.add(cand["diaObjectId"])
                used_g.add(cand["gaia_source_id"])
                taken += 1

    assert len(selected) == 1800, f"Expected 1800 stars, got {len(selected)}"
    assert len(used_o) == 1800 and len(used_g) == 1800
    assert used_o.isdisjoint(excl_oids) and used_g.isdisjoint(excl_gaia)

    cols = list(selected[0].keys())
    cohort_p = RES / "N3_COHORT_1800_FROZEN.csv"
    with cohort_p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(selected)

    # Seal METHOD_LOCK & IMPLEMENTATION_LOCK
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    det_p = WS / "scripts" / "rubin_v3_detector.py"
    det_sha = _sha256(det_p)
    coh_sha = _sha256(cohort_p)

    ml = {
        "spor": "SPOR_N3_RUBIN_V3_1800_DDF",
        "locked_utc": now,
        "cohort_size": len(selected),
        "by_field": {fn: sum(1 for s in selected if s["field"] == fn) for fn in DDFS if any(s["field"] == fn for s in selected)},
        "excluded_prior_ids": len(excl_oids),
        "thresholds": {
            "ratio_dim_max": 10.0 ** (-0.4 * 0.30),
            "z_dim_min": 5.0,
            "ratio_flash_min": 10.0 ** (0.4 * 0.50),
            "z_flash_min": 6.0,
            "baseline_window_days": 180.0,
            "min_base_visits": 5,
            "min_base_dates": 3,
            "min_base_snr": 10.0,
            "v3_max_centroid_offset_arcsec": 0.40,
            "v3_min_reliability": 0.50,
            "v3_cross_match_dt_days": 0.05,
            "v3_fp_dim_confirm_ratio": 0.80,
            "v3_fp_flash_confirm_ratio": 1.40,
        },
        "sha256": {
            "scripts/rubin_v3_detector.py": det_sha,
            "results/N3_COHORT_1800_FROZEN.csv": coh_sha,
        },
    }
    ml_p = RES / "METHOD_LOCK.json"
    ml_p.write_text(json.dumps(ml, indent=2) + "\n", encoding="utf-8")
    ml_sha = _sha256(ml_p)
    il = {
        "spor": "SPOR_N3_RUBIN_V3_1800_DDF",
        "locked_utc": now,
        "method_lock_sha256": ml_sha,
        "detector_sha256": det_sha,
        "cohort_sha256": coh_sha,
        "pre_stage2_blind_lock": True,
    }
    (RES / "IMPLEMENTATION_LOCK.json").write_text(json.dumps(il, indent=2) + "\n", encoding="utf-8")
    print(f"STAGE 1 LOCKED: 1,800 zero-overlap stars ({ml['by_field']}), ml_sha={ml_sha[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
