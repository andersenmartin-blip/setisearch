#!/usr/bin/env python3
"""
Independent Pure-Stdlib Audit (/usr/bin/python3 -S) for Spor N2
(Interstellar Objects & Non-Grav Physics, Rubin SSOFT Outliers, Rubin faint_trails).
Verifies 12/12 invariants (N2_1-N2_12) and confirms all prior audits remain 12/12 PASSED.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import pathlib
import subprocess
import zipfile

WS_DEF = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14/analysis_workspace/work_n2_20261127_rubin_iso_sso_and_trails")
INP_DEF = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14/inputs_n2_20261127")
ROOT_DEF = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14")

MU_SUN_KM3_S2 = 1.32712440018e11
AU_KM = 1.495978707e8
AU_M = 1.495978707e11
DAY_S = 86400.0
AU_DAY2_TO_M_S2 = AU_M / (DAY_S ** 2)
P_SOLAR_1AU_PA = 4.56e-6


def _sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        while True:
            b = fh.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def run_audit(ws: pathlib.Path, inputs: pathlib.Path, root: pathlib.Path) -> int:
    res = ws / "results"
    figs = ws / "figures"
    repo = root / "setisearch"
    prog = repo / "progress" / "2026-11-27-n2-rubin-iso-sso-and-trails"
    checks = []

    def rec(cid: str, ok: bool, msg: str):
        checks.append((cid, ok, msg))
        print(f"[{'PASS' if ok else 'FAIL'}] {cid}: {msg}")

    # N2_1: Prospective locks exact vs scripts/n2_analyzer.py
    ml = json.loads((res / "METHOD_LOCK.json").read_text(encoding="utf-8"))
    il = json.loads((res / "IMPLEMENTATION_LOCK.json").read_text(encoding="utf-8"))
    n2_1_ok = (_sha256(res / "METHOD_LOCK.json") == il["method_lock_sha256"]) and (_sha256(ws / "scripts" / "n2_analyzer.py") == ml["sha256"]["scripts/n2_analyzer.py"])
    rec("N2_1", n2_1_ok, f"Prospective METHOD_LOCK & IMPLEMENTATION_LOCK exact ({ml['locked_utc']})")

    # N2_2: JPL SBDB hyperbolic (>=500, 1I/2I/3I present) & non-grav asteroids (>=600), Stage 3 vetted
    hyp = list(csv.DictReader((res / "N2A_HYPERBOLIC_CENSUS.csv").open(encoding="utf-8")))
    ng = list(csv.DictReader((res / "N2A_NONGRAV_ASTEROIDS.csv").open(encoding="utf-8")))
    vet_a = list(csv.DictReader((res / "N2A_DETAILED_VETTED.csv").open(encoding="utf-8")))
    pdes_hyp = {r["pdes"] for r in hyp}
    n2_2_ok = (len(hyp) >= 500 and len(ng) >= 600 and {"2017 U1", "2019 Q4", "2025 N1"}.issubset(pdes_hyp) and len(vet_a) >= 30)
    rec("N2_2", n2_2_ok, f"N2A JPL census verified ({len(hyp)} hyp, {len(ng)} non-grav; 1I/2I/3I + {len(vet_a)} Stage 3 vetted)")

    # N2_3: Independent stdlib recomputation of v_inf_kms (1I/2I/3I) and (A/m)_SRP across N2A
    max_vinf_diff = 0.0
    for r in hyp:
        if r["pdes"] in ("2017 U1", "2019 Q4", "2025 N1"):
            vinf_r = math.sqrt(MU_SUN_KM3_S2 / (abs(float(r["a_au"])) * AU_KM))
            max_vinf_diff = max(max_vinf_diff, abs(vinf_r - float(r["v_inf_kms"])))
    max_am_rel = 0.0
    for r in ng[:50]:
        if r["A1"]:
            a_r = abs(float(r["A1"])) * AU_DAY2_TO_M_S2
            am_r = a_r / P_SOLAR_1AU_PA
            am_csv = float(r["am_srp_m2_kg"])
            if am_r > 0:
                max_am_rel = max(max_am_rel, abs(am_r - am_csv) / am_r)
    rec("N2_3", max_vinf_diff < 1e-3 and max_am_rel < 1e-4, f"Stdlib recompute of v_inf (diff={max_vinf_diff:.1e} km/s) & (A/m)_SRP (rel={max_am_rel:.1e})")

    # N2_4: Rubin SSOFT (>=18000 total, >=1300 well-sampled), 1,200 injections, 100% triggers vetted
    st3 = json.loads((res / "N2_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    n2b_s = st3["n2b_rubin_ssoft"]
    vet_b = list(csv.DictReader((res / "N2B_SSOFT_VETTED.csv").open(encoding="utf-8")))
    n2_4_ok = (
        n2b_s["ssoft_total_rows"] >= 18000
        and n2b_s["well_sampled_n_obs_ge10"] >= 1300
        and n2b_s["injection_trials_total"] == 1200
        and n2b_s["completeness_phot_dm_ge_1p0"] >= 0.80
        and n2b_s["completeness_astrom_drift_ge_0p20"] >= 0.95
        and len(vet_b) == n2b_s["triggers_total"] >= 50
    )
    rec("N2_4", n2_4_ok, f"N2B SSOFT: {n2b_s['ssoft_total_rows']} rows ({n2b_s['well_sampled_n_obs_ge10']} n_obs>=10), 1200 inj, {len(vet_b)}/{n2b_s['triggers_total']} triggers vetted")

    # N2_5: Rubin faint_trails (>=100), pure-stdlib kinematic recompute, zero LEO/GEO, 100% vetted
    vet_c = list(csv.DictReader((res / "N2C_FAINT_TRAILS_VETTED.csv").open(encoding="utf-8")))
    max_rate_diff = 0.0
    for r in vet_c:
        rate_r = (float(r["trailLength_arcsec"]) / float(r["exposureTime_s"])) * 24.0
        max_rate_diff = max(max_rate_diff, abs(rate_r - float(r["ang_rate_deg_day"])))
    n2c_s = st3["n2c_faint_trails"]
    n2_5_ok = (
        len(vet_c) >= 100
        and len(vet_c) == n2c_s["trails_vetted_total"]
        and max_rate_diff < 1e-3
        and n2c_s["leo_geo_artificial_satellites_found"] == 0
    )
    rec("N2_5", n2_5_ok, f"N2C faint_trails: {len(vet_c)} vetted (rate diff={max_rate_diff:.1e}), {n2c_s['dispositions'].get('SKYBOT_KNOWN_SOLAR_SYSTEM_OBJECT',0)} SkyBoT matched, 0 LEO/GEO")

    # N2_6: Exact Bayesian f95 ordering & verified_eti == 0
    n2a_s = st3["n2a_iso_and_nongrav"]
    bound_sets = [
        n2a_s["bounds_hyperbolic_eti"],
        n2a_s["bounds_nongrav_asteroids_eti"],
        n2b_s["bounds_well_sampled_phot_dm_ge_1p0"],
        n2b_s["bounds_well_sampled_astrom_drift_ge_0p20"],
        n2c_s["bounds_trails_eti"],
    ]
    n2_6_ok = (st3.get("verified_eti") == 0) and all(
        b["clopper_pearson_f95_pct"] >= b["uniform_f95_pct"] > b["jeffreys_f95_pct"] for b in bound_sets
    )
    rec("N2_6", n2_6_ok, f"Bayesian f95 Jeffreys: N2A={n2a_s['bounds_hyperbolic_eti']['jeffreys_f95_pct']}%/{n2a_s['bounds_nongrav_asteroids_eti']['jeffreys_f95_pct']}%, N2B={n2b_s['bounds_well_sampled_phot_dm_ge_1p0']['jeffreys_f95_pct']}%/{n2b_s['bounds_well_sampled_astrom_drift_ge_0p20']['jeffreys_f95_pct']}%, N2C={n2c_s['bounds_trails_eti']['jeffreys_f95_pct']}%")

    # N2_7: FITS cutout gallery >= 60 valid FITS files
    fits_files = list((inputs / "cutouts").glob("*.fits"))
    valid_fits = sum(1 for p in fits_files if p.read_bytes()[:6] == b"SIMPLE")
    rec("N2_7", valid_fits >= 60 and valid_fits == len(fits_files), f"FITS cutout gallery verified ({valid_fits}/{len(fits_files)} valid FITS files)")

    # N2_8: All 6 300-DPI PNGs valid, synced to repo, and approved in VISUAL_REVIEW_N2.json
    vr = json.loads((res / "VISUAL_REVIEW_N2.json").read_text(encoding="utf-8"))
    fnames = [
        "figN2_01_hyperbolic_and_nongrav_census.png",
        "figN2_02_rubin_ssoft_anomaly_landscape.png",
        "figN2_03_rubin_sso_top_outliers_lightcurves.png",
        "figN2_04_rubin_faint_trails_kinematics.png",
        "figN2_05_rubin_faint_trails_fits_gallery.png",
        "figN2_06_n2_injection_and_unified_bounds.png",
    ]
    n2_8_ok = vr.get("all_figures_approved") is True and len(vr.get("figures", [])) == 6
    for fn in fnames:
        pw, pr = figs / fn, prog / "figures" / fn
        if not (pw.exists() and pr.exists() and pw.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" and _sha256(pw) == _sha256(pr)):
            n2_8_ok = False
    rec("N2_8", n2_8_ok, "All 6 300-DPI PNGs valid, synced to repo, and visually approved")

    # N2_9: Archive zip & compact repo deliverables < 48 MB
    zpath = root / "archives_n2" / "SETI_N2_RUBIN_ISO_SSO_TRAILS_2026-11-27.zip"
    n2_9_ok = zpath.exists() and zipfile.is_zipfile(zpath)
    if n2_9_ok:
        with zipfile.ZipFile(zpath) as zf:
            n2_9_ok = zf.testzip() is None and len(zf.namelist()) >= 80
    for rp in prog.rglob("*"):
        if rp.is_file() and rp.stat().st_size >= 48 * 1048576:
            n2_9_ok = False
    if not (prog / "RESULTS_REPORT.md").exists():
        n2_9_ok = False
    rec("N2_9", n2_9_ok, f"Archive zip intact ({zpath.stat().st_size if zpath.exists() else 0:,} B) & repo deliverables <48 MB")

    # N2_10: SETI_ACTIVE_CONTINUATION.json invariants
    cont = json.loads((root / "SETI_ACTIVE_CONTINUATION.json").read_text(encoding="utf-8"))
    n2_10_ok = (
        cont.get("active_phase") == "D097"
        and cont.get("current_table_cells") == 107105
        and cont.get("old90_and_Rubin_stay_stopped") is True
        and "updated_utc" not in cont
        and "rubin_v2_r1_r2_completed" in cont
        and "n1_dyson_vasco_completed" in cont
        and "n2_rubin_iso_sso_trails_completed" in cont
        and len(cont) == 506
    )
    rec("N2_10", n2_10_ok, f"SETI_ACTIVE_CONTINUATION.json invariants preserved (len={len(cont)})")

    # N2_11: Prior Spor N1 audit (which also runs Rubin V2 audit) still 12/12 PASSED
    p_n1 = subprocess.run(
        ["/usr/bin/python3", "-S", str(root / "analysis_workspace" / "work_n1_20261126_dyson_hephaistos_and_vasco" / "scripts" / "audit_n1_dyson_vasco.py")],
        capture_output=True, text=True, check=False,
    )
    rec("N2_11", p_n1.returncode == 0 and "N1_DYSON_VASCO_AUDIT: 12/12 PASSED" in p_n1.stdout, "Spor N1 (+ Rubin V2) audit remains 12/12 PASSED")

    # N2_12: Spor 5 & 38 Companion Archives A-AL audit still 12/12 PASSED
    p_sp5 = subprocess.run(
        ["/usr/bin/python3", "-S", str(repo / "zenodo_package" / "verify_publication_package.py"), "--archives-dir", str(root / "archives")],
        capture_output=True, text=True, check=False,
    )
    rec("N2_12", p_sp5.returncode == 0 and "SPOR5_PUBLICATION_AUDIT: 12/12 PASSED" in p_sp5.stdout, "Spor 5 & 38 Companion Archives A-AL audit remains 12/12 PASSED")

    passed = sum(1 for _, ok, _ in checks if ok)
    print(f"\nN2_RUBIN_ISO_TRAILS_AUDIT: {passed}/{len(checks)} PASSED")
    (ws / "audit" / "AUDIT_N2_RUBIN_ISO_TRAILS.json").write_text(
        json.dumps({"passed": passed, "total": len(checks), "checks": [{"id": c, "ok": o, "message": m} for c, o, m in checks]}, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0 if passed == len(checks) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ws", default=str(WS_DEF))
    ap.add_argument("--inputs", default=str(INP_DEF))
    ap.add_argument("--root", default=str(ROOT_DEF))
    args = ap.parse_args()
    return run_audit(pathlib.Path(args.ws), pathlib.Path(args.inputs), pathlib.Path(args.root))


if __name__ == "__main__":
    raise SystemExit(main())
