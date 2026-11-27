#!/usr/bin/env python3
"""
Pure-stdlib 12-check audit for Spor N5 (SPOR_N5_10YR_SECULAR_IR_OPTICAL_1083).
Compatible with /usr/bin/python3 -S.
"""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import subprocess
import zipfile

ROOT = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace" / "work_n5_20261127_secular_ir_optical_1083"
INP = ROOT / "inputs_n5_20261127"
RES = WS / "results"
GIT_REPO = ROOT / "setisearch"
GIT_PROG = GIT_REPO / "progress" / "2026-11-27-n5-secular-ir-optical-1083"
ZIP_PATH = ROOT / "archives_n5" / "SETI_N5_10YR_SECULAR_IR_OPTICAL_1083_2026-11-27.zip"
LEDGER = ROOT / "SETI_ACTIVE_CONTINUATION.json"


def sha256(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    # N5_1: Prospective lock integrity
    an_p = WS / "scripts" / "n5_secular_analyzer.py"
    ml_p = RES / "METHOD_LOCK.json"
    ml = json.loads(ml_p.read_text(encoding="utf-8"))
    il = json.loads((RES / "IMPLEMENTATION_LOCK.json").read_text(encoding="utf-8"))
    an_s = json.loads((RES / "N5_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    an_hash = sha256(an_p)
    ml_hash = sha256(ml_p)
    c1 = (
        ml.get("sha256", {}).get("scripts/n5_secular_analyzer.py") == an_hash
        and il.get("analyzer_sha256") == an_hash
        and il.get("method_lock_sha256") == ml_hash
        and an_s.get("analyzer_sha256") == an_hash
        and ml.get("locked_utc", "") < an_s.get("generated_utc", "")
    )
    checks.append(("N5_1_lock_integrity", c1, f"sha={an_hash[:12]}"))

    # N5_2: 1,083 Master + 13 Benchmarks across Gaia DR3, AllWISE, CatWISE2020, ZTF DR24 + Manifest
    req_inp = [
        INP / "n5_benchmarks_13.csv",
        INP / "gaia" / "gaia_dr3_1096.csv",
        INP / "allwise" / "allwise_1096.csv",
        INP / "catwise" / "catwise2020_1096.csv",
        INP / "ztf" / "ztf_dr24_1096.csv",
        INP / "STAGE1_MANIFEST.json",
    ]
    cov = an_s.get("coverage_counts", {})
    c2 = (
        all(p.exists() and p.stat().st_size > 100 for p in req_inp)
        and an_s.get("master_stars_total") == 1083
        and an_s.get("benchmarks_total") == 13
        and cov.get("gaia_dr3", 0) >= 1000
        and cov.get("wise_any", 0) >= 1000
        and cov.get("ztf_dr24", 0) >= 200
    )
    checks.append(("N5_2_allsky_1096_catalogs", c2, f"gaia={cov.get('gaia_dr3')}, wise={cov.get('wise_any')}, ztf={cov.get('ztf_dr24')}"))

    # N5_3: Tier-2 10-yr NEOWISE-R lightcurves (>=50 stars, >=10,000 exposures) + ASASSN_21QJ recovered
    s3 = json.loads((RES / "N5_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    neo_files = list((INP / "neowise_lc").glob("*_neowise.csv"))
    c3 = (
        len(neo_files) >= 50
        and s3.get("neowise_single_exposures_clean", 0) >= 10000
        and s3.get("benchmark_asassn21qj_recovered") is True
    )
    checks.append(("N5_3_neowise_10yr_and_asassn21qj", c3, f"lcs={len(neo_files)}, exp={s3.get('neowise_single_exposures_clean')}, asassn21qj={s3.get('benchmark_asassn21qj_recovered')}"))

    # N5_4: All 7 Hephaistos A-G 10-yr stability measured
    hephs = s3.get("hephaistos_10yr_stability", {})
    c4 = all(f"HEPH_{k}" in hephs and (hephs[f"HEPH_{k}"].get("visits") or 0) >= 18 for k in "ABCDEFG")
    checks.append(("N5_4_hephaistos_7_10yr_stable", c4, f"heph={len(hephs)}/7"))

    # N5_5: 1,200 secular injection-recovery trials
    ig = an_s.get("injection_grid", {})
    c5 = (
        an_s.get("injection_trials_total") == 1200
        and an_s.get("injection_completeness_ge_0p04_mag_yr", 0.0) >= 0.90
        and ig.get("0.15", {}).get("completeness", 0.0) >= 0.95
    )
    checks.append(("N5_5_injections_1200", c5, f"ge0.04={an_s.get('injection_completeness_ge_0p04_mag_yr')}, 0.15={ig.get('0.15', {}).get('completeness')}"))

    # N5_6: Complete Stage 3 vetting -> 0 ETI
    vet_rows = list(csv.DictReader((RES / "N5_CANDIDATES_VETTED.csv").open(encoding="utf-8")))
    c6 = (
        s3.get("verified_eti_candidates") == 0
        and s3.get("unexplained_secular_science_targets") == 0
        and len(vet_rows) >= an_s.get("tier1_triggers_total", 0)
    )
    checks.append(("N5_6_stage3_zero_eti", c6, f"eti={s3.get('verified_eti_candidates')}, vetted_rows={len(vet_rows)}"))

    # N5_7: Bayesian limits consistency
    bl = an_s.get("bayesian_limits_zero_eti", {})
    j_all = bl.get("all_1083_stars_gaia_ir", {}).get("jeffreys_f95_pct", 99.0)
    u_all = bl.get("all_1083_stars_gaia_ir", {}).get("uniform_f95_pct", 0.0)
    c7 = 0.15 < j_all < 0.25 and j_all < u_all
    checks.append(("N5_7_bayesian_limits", c7, f"f95_1083_J={j_all}%"))

    # N5_8: 6 PNGs in WS and git + VISUAL_REVIEW_N5 PASSED
    vr = json.loads((RES / "VISUAL_REVIEW_N5.json").read_text(encoding="utf-8"))
    pngs = [
        "figN5_01_allsky_10yr_coverage_and_ruwe.png",
        "figN5_02_10yr_ir_drift_vs_optical_trend.png",
        "figN5_03_neowise_10yr_benchmark_and_hephaistos.png",
        "figN5_04_science_triggers_neowise_ztf_vetting.png",
        "figN5_05_injection_recovery_and_bayesian_f95.png",
        "figN5_06_unified_5track_seti_landscape_n1_to_n5.png",
    ]
    c8 = (
        vr.get("status") == "PASSED"
        and all(vr.get("figures", {}).get(f, {}).get("status") == "PASSED" for f in pngs)
        and all((WS / "figures" / f).exists() and (GIT_PROG / "figures" / f).exists() for f in pngs)
    )
    checks.append(("N5_8_figures_and_visual_review", c8, "pngs=6/6"))

    # N5_9: Reports synced across WS, GIT_PROG, docs, ROOT/reports + FORTSAET
    r_ws = WS / "RESULTS_REPORT.md"
    r_pr = GIT_PROG / "RESULTS_REPORT.md"
    r_dc = GIT_REPO / "docs" / "N5_SECULAR_IR_OPTICAL_1083_REPORT.md"
    r_rp = ROOT / "reports" / "N5_SECULAR_IR_OPTICAL_1083_REPORT.md"
    f_hd = ROOT / "FORTSAET_FRA_N5_SECULAR_IR_OPTICAL_1083.md"
    c9 = (
        r_ws.exists() and r_pr.exists() and r_dc.exists() and r_rp.exists() and f_hd.exists()
        and r_ws.read_text(encoding="utf-8") == r_pr.read_text(encoding="utf-8") == r_dc.read_text(encoding="utf-8") == r_rp.read_text(encoding="utf-8")
    )
    checks.append(("N5_9_reports_synced", c9, "ws=progress=docs=reports"))

    # N5_10: Ledger len == 509 + invariants preserved
    led = json.loads(LEDGER.read_text(encoding="utf-8"))
    req_keys = ("rubin_v2_r1_r2_completed", "n1_dyson_vasco_completed", "n2_rubin_iso_sso_trails_completed", "n3_rubin_v3_1800_completed", "n4_lowfreq_radio_bridge_completed", "n5_secular_ir_optical_completed")
    c10 = (
        len(led) == 509
        and led.get("active_phase") == "D097"
        and led.get("current_table_cells") == 107105
        and led.get("old90_and_Rubin_stay_stopped") is True
        and "updated_utc" not in led
        and all(k in led for k in req_keys)
    )
    checks.append(("N5_10_ledger_len_509", c10, f"len={len(led)}"))

    # N5_11: Zip archive valid + all N5 setisearch files < 48 MB
    zip_ok = False
    if ZIP_PATH.exists():
        with zipfile.ZipFile(ZIP_PATH, "r") as zf:
            zip_ok = zf.testzip() is None and len(zf.namelist()) >= 90
    n5_repo = list(GIT_PROG.rglob("*")) + [r_dc]
    oversized = [str(p.relative_to(GIT_REPO)) for p in n5_repo if p.is_file() and p.stat().st_size >= 48 * 1024 * 1024]
    c11 = zip_ok and not oversized
    checks.append(("N5_11_zip_and_size_limit", c11, f"zip_ok={zip_ok}, oversized={len(oversized)}"))

    # N5_12: Regression cascade (N4_1..9,11,12 PASSED with N4_10 len==508 superseded by N5_10 len==509; N3 12/12 + Spor 5 12/12)
    r_n4 = subprocess.run(["/usr/bin/python3", "-S", str(ROOT / "analysis_workspace/work_n4_20261127_lowfreq_radio_bridge_1083/scripts/audit_n4_radio_bridge.py")], capture_output=True, text=True)
    n4_ok = all(f"[PASS] N4_{i}_" in r_n4.stdout for i in (1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12))
    r_n3 = subprocess.run(["/usr/bin/python3", "-S", str(ROOT / "analysis_workspace/work_n3_20261127_rubin_v3_1800ddf/scripts/audit_n3_rubin_v3.py")], capture_output=True, text=True)
    r_sp5 = subprocess.run(["/usr/bin/python3", "-S", str(GIT_REPO / "zenodo_package/verify_publication_package.py"), "--archives-dir", str(ROOT / "archives")], capture_output=True, text=True)
    c12 = n4_ok and ("12/12 PASSED" in r_n3.stdout) and ("12/12 PASSED" in r_sp5.stdout)
    checks.append(("N5_12_regression_n4_n3_spor5", c12, f"n4_11_12_ok={n4_ok}, n3_rc={r_n3.returncode}, sp5_rc={r_sp5.returncode}"))

    passed = sum(1 for _, ok, _ in checks if ok)
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\nN5_SECULAR_BRIDGE_AUDIT: {passed}/{len(checks)} PASSED")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
