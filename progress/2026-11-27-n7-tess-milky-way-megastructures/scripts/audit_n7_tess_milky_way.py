#!/usr/bin/env python3
"""Pure-stdlib 12-point audit for Spor N7 (SPOR_N7_TESS_MEGASTRUCTURE_AND_OPTICAL_BEACON_MILKY_WAY)."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n7_20261127_tess_milky_way_megastructures"
INP = ROOT / "inputs_n7_20261127"
GIT_REPO = ROOT / "setisearch"
GIT_PROG = GIT_REPO / "progress/2026-11-27-n7-tess-milky-way-megastructures"
ZIP_PATH = ROOT / "archives_n7/SETI_N7_TESS_MILKY_WAY_MEGASTRUCTURES_2026-11-27.zip"

EXPECTED_ANALYZER_SHA = "613128aca582392ce711c043138f4d677a507333bd9597f0408b3915e9863b4d"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def main() -> int:
    checks: list[tuple[str, bool, str]] = []
    res = WS / "results"
    ml = json.loads((res / "METHOD_LOCK.json").read_text(encoding="utf-8"))
    il = json.loads((res / "IMPLEMENTATION_LOCK.json").read_text(encoding="utf-8"))
    s2 = json.loads((res / "N7_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    s3 = json.loads((res / "N7_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    vr = json.loads((res / "VISUAL_REVIEW_N7.json").read_text(encoding="utf-8"))
    s1 = json.loads((INP / "STAGE1_MANIFEST.json").read_text(encoding="utf-8"))

    # N7_1: Prospective blind lock
    an_sha = sha256_file(WS / "scripts/n7_tess_megastructure_analyzer.py")
    ml_sha = sha256_file(res / "METHOD_LOCK.json")
    c1 = (
        an_sha == EXPECTED_ANALYZER_SHA
        and il.get("analyzer_sha256") == EXPECTED_ANALYZER_SHA
        and il.get("method_lock_sha256") == ml_sha
        and il.get("pre_acquisition_blind_lock") is True
        and ml.get("locked_utc", "") < s2.get("generated_utc", "")
    )
    checks.append(("N7_1_BLIND_LOCK", c1, f"sha_ok={an_sha == EXPECTED_ANALYZER_SHA}, locked={ml.get('locked_utc')} < gen={s2.get('generated_utc')}"))

    # N7_2: Stage 1 acquisition & local FITS presence
    man_rows = csv_rows(INP / "catalogs/n7_milky_way_tess_manifest.csv")
    fits_ok = sum(1 for r in man_rows if (INP / "tess_lc" / r["primary_fits_file"]).exists())
    c2 = (
        s1.get("tess_primary_fits_downloaded") == 565
        and len(man_rows) == 565
        and fits_ok == 565
        and (INP / "catalogs/nasa_exoplanets_pscomppars.csv").exists()
        and (INP / "catalogs/mast_tess_spoc_2min_index.csv").exists()
    )
    checks.append(("N7_2_STAGE1_TESS_ACQUISITION", c2, f"manifest={len(man_rows)}, fits_on_disk={fits_ok}/565"))

    # N7_3: Stage 2 analyzer outputs
    cat_rows = csv_rows(res / "N7_TESS_MILKY_WAY_CATALOG.csv")
    trig_rows = csv_rows(res / "N7_STAGE2_TRIGGERS.csv")
    c3 = (
        len(cat_rows) == 565
        and len(trig_rows) == 123
        and s2["stars_analyzed_total"] == 565
        and s2["total_valid_cadences"] == 8638983
    )
    checks.append(("N7_3_STAGE2_ANALYZER_OUTPUTS", c3, f"cat={len(cat_rows)}, trig={len(trig_rows)}, cadences={s2['total_valid_cadences']}"))

    # N7_4: 1,200-trial injection calibration
    inj = s2["injections"]
    c4 = (
        inj["trials_total"] == 1200
        and inj["completeness_b_ge_500ppm"] >= 0.90
        and inj["completeness_overall_supra_threshold"] >= 0.60
    )
    checks.append(("N7_4_INJECTION_CALIBRATION", c4, f"trials={inj['trials_total']}, comp_b={inj['completeness_b_ge_500ppm']}, comp_all={inj['completeness_overall_supra_threshold']}"))

    # N7_5: Stage 3 forensic vetting & strict Milky Way purity
    vet_rows = csv_rows(res / "N7_CANDIDATES_VETTED.csv")
    sec2_files = list((INP / "tess_lc_sec2").glob("*.fits"))
    c5 = (
        len(vet_rows) == 123
        and s3["stage2_triggers_vetted"] == 123
        and s3["pure_milky_way_stars_analyzed"] == 558
        and s3["pure_milky_way_master_stars"] == 555
        and s3["extragalactic_controls_excluded_for_pure_mw"] == 6
        and s3["independent_sec2_tess_checks"] >= 15
        and len(sec2_files) >= 15
        and s3["verified_eti_candidates"] == 0
        and not any(r["eti_status"] == "UNRESOLVED_ETI_CANDIDATE" for r in vet_rows)
    )
    checks.append(("N7_5_STAGE3_VETTING_ZERO_ETI", c5, f"mw_stars={s3['pure_milky_way_stars_analyzed']}, sec2={len(sec2_files)}, verified_eti={s3['verified_eti_candidates']}"))

    # N7_6: Pure Milky Way Bayesian bounds
    bl = s3["bayesian_limits_pure_milky_way_zero_eti"]
    c6 = (
        abs(bl["all_pure_mw_master_raw"]["jeffreys_f95_pct"] - 0.3453) < 1e-4
        and abs(bl["all_pure_mw_master_eff"]["jeffreys_f95_pct"] - 0.5115) < 1e-4
        and abs(bl["within_10pc"]["jeffreys_f95_pct"] - 0.8529) < 1e-4
        and abs(bl["exoplanet_hosts"]["jeffreys_f95_pct"] - 0.6462) < 1e-4
    )
    checks.append(("N7_6_PURE_MW_BAYESIAN_LIMITS", c6, f"raw={bl['all_pure_mw_master_raw']['jeffreys_f95_pct']}%, eff={bl['all_pure_mw_master_eff']['jeffreys_f95_pct']}%"))

    # N7_7: 6 PNGs + visual review SHA parity
    figs = [
        "figN7_01_milky_way_tess_sky_and_distance.png",
        "figN7_02_megastructure_dip_and_asymmetry_plane.png",
        "figN7_03_coherent_optical_beacon_fft_and_flashes.png",
        "figN7_04_tess_lightcurve_gallery_and_veto_funnel.png",
        "figN7_05_injection_recovery_and_bayesian_f95.png",
        "figN7_06_milky_way_unified_seti_landscape.png",
    ]
    fig_sync = all(
        (WS / "figures" / f).exists()
        and (GIT_PROG / "figures" / f).exists()
        and sha256_file(WS / "figures" / f) == sha256_file(GIT_PROG / "figures" / f)
        for f in figs
    )
    c7 = fig_sync and vr.get("status") == "PASSED" and len(vr.get("figures_reviewed", [])) == 6
    checks.append(("N7_7_FIGURES_AND_VISUAL_REVIEW", c7, f"fig_sync={fig_sync}, visual_review={vr.get('status')}"))

    # N7_8: Reports synced, scripts/results synced, no setisearch/reports/, all < 48 MB
    r_ws = WS / "RESULTS_REPORT.md"
    r_gp = GIT_PROG / "RESULTS_REPORT.md"
    r_dc = GIT_REPO / "docs/N7_TESS_MILKY_WAY_MEGASTRUCTURES_REPORT.md"
    r_rt = ROOT / "reports/N7_TESS_MILKY_WAY_MEGASTRUCTURES_REPORT.md"
    rep_hashes = {sha256_file(p) for p in (r_ws, r_gp, r_dc, r_rt) if p.exists()}
    scr_ok = all(
        (GIT_PROG / "scripts" / s).exists() and sha256_file(WS / "scripts" / s) == sha256_file(GIT_PROG / "scripts" / s)
        for s in ("n7_tess_megastructure_analyzer.py", "stage1_n7_acquire_tess_milky_way.py", "stage3_n7_forensic_vetting.py", "plot_n7_figures.py", "audit_n7_tess_milky_way.py")
    )
    res_ok = all(
        (GIT_PROG / "results" / p.name).exists() and sha256_file(p) == sha256_file(GIT_PROG / "results" / p.name)
        for p in res.iterdir() if p.is_file()
    )
    oversized = [str(p.relative_to(GIT_REPO)) for p in list(GIT_PROG.rglob("*")) + [r_dc] if p.is_file() and p.stat().st_size >= 48 * 1024 * 1024]
    c8 = len(rep_hashes) == 1 and all(p.exists() for p in (r_ws, r_gp, r_dc, r_rt)) and scr_ok and res_ok and not (GIT_REPO / "reports").exists() and not oversized
    checks.append(("N7_8_REPORTS_SYNC_AND_GIT_PROG", c8, f"rep_sync={len(rep_hashes)==1}, scr_ok={scr_ok}, res_ok={res_ok}, oversized={len(oversized)}"))

    # N7_9: Docs & continuation markdown
    f_n7 = ROOT / "FORTSAET_FRA_N7_TESS_MILKY_WAY.md"
    readme_txt = (GIT_REPO / "README.md").read_text(encoding="utf-8")
    cont_txt = (GIT_REPO / "CONTINUE_SETI.md").read_text(encoding="utf-8")
    c9 = (
        f_n7.exists()
        and "N7_TESS_MILKY_WAY_MEGASTRUCTURES_REPORT.md" in readme_txt
        and "Spor N7" in readme_txt
        and "N7_TESS_MILKY_WAY_MEGASTRUCTURES_REPORT.md" in cont_txt
        and "Spor N7" in cont_txt
    )
    checks.append(("N7_9_DOCS_AND_CONTINUATION_MD", c9, f"fortsaet_exists={f_n7.exists()}, docs_updated={c9}"))

    # N7_10: Continuation ledger (len == 511)
    led = json.loads((ROOT / "SETI_ACTIVE_CONTINUATION.json").read_text(encoding="utf-8"))
    n7_led = led.get("n7_tess_milky_way_completed", {})
    c10 = (
        len(led) == 511
        and led.get("active_phase") == "D097"
        and led.get("current_table_cells") == 107105
        and led.get("old90_and_Rubin_stay_stopped") is True
        and "updated_utc" not in led
        and "n6_kardashev_iii_supercluster_completed" in led
        and n7_led.get("verified_eti_candidates") == 0
        and n7_led.get("external_contacts") == 0
    )
    checks.append(("N7_10_CONTINUATION_LEDGER", c10, f"len={len(led)}, external_contacts={n7_led.get('external_contacts')}"))

    # N7_11: Local ZIP archive integrity
    zip_ok = False
    z_members = 0
    if ZIP_PATH.exists():
        with zipfile.ZipFile(ZIP_PATH, "r") as zf:
            names = set(zf.namelist())
            z_members = len(names)
            req_z = {"RESULTS_REPORT.md", "results/METHOD_LOCK.json", "results/IMPLEMENTATION_LOCK.json", "results/N7_ANALYZER_SUMMARY.json", "results/N7_STAGE3_VETTING.json", "results/VISUAL_REVIEW_N7.json"}
            req_z |= {f"figures/{f}" for f in figs}
            zip_ok = (zf.testzip() is None) and req_z.issubset(names)
    checks.append(("N7_11_LOCAL_ZIP_ARCHIVE", zip_ok, f"zip_ok={zip_ok}, members={z_members}"))

    # N7_12: Regression across sealed N6, N5, N3, and Spor 5
    r_n6 = subprocess.run(["/usr/bin/python3", "-S", str(ROOT / "analysis_workspace/work_n6_20261127_kardashev_iii_supercluster/scripts/audit_n6_kardashev_iii.py")], capture_output=True, text=True)
    n6_ok = all(f"[PASS] N6_{i}_" in r_n6.stdout for i in (1, 2, 3, 4, 5, 6, 7, 8, 9, 11))
    r_n5 = subprocess.run(["/usr/bin/python3", "-S", str(ROOT / "analysis_workspace/work_n5_20261127_secular_ir_optical_1083/scripts/audit_n5_secular_bridge.py")], capture_output=True, text=True)
    n5_ok = all(f"[PASS] N5_{i}_" in r_n5.stdout for i in (1, 2, 3, 4, 5, 6, 7, 8, 9, 11))
    r_n3 = subprocess.run(["/usr/bin/python3", "-S", str(ROOT / "analysis_workspace/work_n3_20261127_rubin_v3_1800ddf/scripts/audit_n3_rubin_v3.py")], capture_output=True, text=True)
    r_sp5 = subprocess.run(["/usr/bin/python3", "-S", str(GIT_REPO / "zenodo_package/verify_publication_package.py"), "--archives-dir", str(ROOT / "archives")], capture_output=True, text=True)
    c12 = n6_ok and n5_ok and ("12/12 PASSED" in r_n3.stdout) and ("12/12 PASSED" in r_sp5.stdout)
    checks.append(("N7_12_REGRESSION_AND_SEALED_INVARIANT", c12, f"n6_ok={n6_ok}, n5_ok={n5_ok}, n3_rc={r_n3.returncode}, sp5_rc={r_sp5.returncode}"))

    passed = sum(1 for _, ok, _ in checks if ok)
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\nN7_TESS_MILKY_WAY_AUDIT: {passed}/{len(checks)} PASSED")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
