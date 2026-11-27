#!/usr/bin/env python3
"""Pure-stdlib 12-point audit for Spor N6 (SPOR_N6_KARDASHEV_III_LOCAL_SUPERCLUSTER)."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n6_20261127_kardashev_iii_supercluster"
INP = ROOT / "inputs_n6_20261127"
GIT_REPO = ROOT / "setisearch"
GIT_PROG = GIT_REPO / "progress/2026-11-27-n6-kardashev-iii-supercluster"
ZIP_PATH = ROOT / "archives_n6/SETI_N6_KARDASHEV_III_LOCAL_SUPERCLUSTER_2026-11-27.zip"

EXPECTED_ANALYZER_SHA = "b32db7a77b00effae1ad2940e0ee5d2063ed1a7341a91faf3a47edbc9e123bf5"


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
    s2 = json.loads((res / "N6_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    s3 = json.loads((res / "N6_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    vr = json.loads((res / "VISUAL_REVIEW_N6.json").read_text(encoding="utf-8"))

    # N6_1: Prospective blind lock
    an_sha = sha256_file(WS / "scripts/n6_k3_analyzer.py")
    ml_sha = sha256_file(res / "METHOD_LOCK.json")
    c1 = (
        an_sha == EXPECTED_ANALYZER_SHA
        and il.get("analyzer_sha256") == EXPECTED_ANALYZER_SHA
        and il.get("method_lock_sha256") == ml_sha
        and il.get("pre_acquisition_blind_lock") is True
        and ml.get("locked_utc", "") < s2.get("generated_utc", "")
    )
    checks.append(("N6_1_BLIND_LOCK", c1, f"sha_ok={an_sha == EXPECTED_ANALYZER_SHA}, locked={ml.get('locked_utc')} < gen={s2.get('generated_utc')}"))

    # N6_2: Stage 1 live acquisition CSVs
    req_inp = [
        INP / "hecate/hecate_local_supercluster.csv",
        INP / "radio/nvss_1400mhz_galaxies.csv",
        INP / "radio/racs_low_888mhz_galaxies.csv",
        INP / "radio/racs_mid_1367mhz_galaxies.csv",
        INP / "radio/lotss_dr3_144mhz_galaxies.csv",
        INP / "radio/lotss_dr3_144_footprint.csv",
    ]
    hec_rows = csv_rows(req_inp[0]) if req_inp[0].exists() else []
    c2 = all(p.exists() and p.stat().st_size > 100 for p in req_inp) and len(hec_rows) == 1381
    checks.append(("N6_2_STAGE1_ACQUISITION", c2, f"files={sum(p.exists() for p in req_inp)}/6, hecate_rows={len(hec_rows)}"))

    # N6_3: Stage 2 locked analyzer outputs
    cat_rows = csv_rows(res / "N6_SUPERCLUSTER_K3_CATALOG.csv")
    trig_rows = csv_rows(res / "N6_K3_TRIGGERS.csv")
    c3 = (
        len(cat_rows) == 1381
        and len(trig_rows) == 11
        and s2["galaxies_total"] == 1381
        and s2["milky_way_mass_galaxies"] == 627
        and s2["nearby_20mpc_galaxies"] == 373
        and s2["radio_coverage_counts"]["radio_detected"] == 839
        and s2["min_radio_surveys_per_galaxy"] >= 1
    )
    checks.append(("N6_3_STAGE2_ANALYZER_OUTPUTS", c3, f"cat={len(cat_rows)}, trig={len(trig_rows)}, mw={s2['milky_way_mass_galaxies']}, det={s2['radio_coverage_counts']['radio_detected']}"))

    # N6_4: 1,200-trial injection recovery
    ig = s2["injection_grid"]
    c4 = (
        s2["injection_trials_total"] == 1200
        and s2["injection_completeness_ge_0p30"] >= 0.90
        and ig["0.3"]["completeness"] <= ig["0.5"]["completeness"] <= ig["0.75"]["completeness"]
    )
    checks.append(("N6_4_INJECTION_CALIBRATION", c4, f"trials={s2['injection_trials_total']}, comp_ge_0p30={s2['injection_completeness_ge_0p30']}"))

    # N6_5: Stage 3 cutouts & physical veto (0 ETI)
    vet_rows = csv_rows(res / "N6_K3_CANDIDATES_VETTED.csv")
    phot_rows = csv_rows(res / "N6_VLASS_GALAXY_PHOTOMETRY.csv")
    fits_ok = sum(1 for r in phot_rows if (INP / "vlass_cutouts" / r["fits_file"]).exists())
    jpg_ok = sum(1 for r in phot_rows if (INP / "ls_cutouts" / r["ls_jpg"]).exists())
    c5 = (
        len(vet_rows) == 11
        and len(phot_rows) == 12
        and s3["vlass_cutouts_valid_fits"] == 12
        and s3["legacy_dr10_jpg_cutouts"] == 12
        and fits_ok == 12
        and jpg_ok == 12
        and s3["k3_triggers_with_live_radio_detection"] == 11
        and s3["verified_k3_eti_candidates"] == 0
        and all(r["k3_eti_status"] == "VETOED_ASTROPHYSICAL_NON_K3" for r in vet_rows)
    )
    checks.append(("N6_5_STAGE3_CUTOUTS_AND_VETTING", c5, f"fits={fits_ok}/12, jpg={jpg_ok}/12, verified_k3_eti={s3['verified_k3_eti_candidates']}"))

    # N6_6: Bayesian null bounds
    bl_all = s2["bayesian_limits_zero_k3"]["all_local_supercluster_galaxies"]
    c6 = (
        abs(bl_all["jeffreys_f95_pct"] - 0.1499) < 1e-6
        and abs(bl_all["uniform_f95_pct"] - 0.2336) < 1e-6
        and abs(bl_all["clopper_pearson_f95_pct"] - 0.2338) < 1e-6
        and s2["per_star_k3_jeffreys_f95"] < 5e-14
    )
    checks.append(("N6_6_BAYESIAN_NULL_BOUNDS", c6, f"jeffreys={bl_all['jeffreys_f95_pct']}%, per_star={s2['per_star_k3_jeffreys_f95']}"))

    # N6_7: 6 PNGs & Visual Review SHA parity
    figs = [
        "figN6_01_local_supercluster_allsky_map.png",
        "figN6_02_garrett_q22_radio_ir_correlation.png",
        "figN6_03_ghat_waste_heat_and_wise_colors.png",
        "figN6_04_vlass_optical_cutouts_and_veto_funnel.png",
        "figN6_05_k3_injection_recovery_and_bayesian_f95.png",
        "figN6_06_kardashev_scale_synthesis_k1_to_k3.png",
    ]
    fig_sync = all(
        (WS / "figures" / f).exists()
        and (GIT_PROG / "figures" / f).exists()
        and sha256_file(WS / "figures" / f) == sha256_file(GIT_PROG / "figures" / f)
        for f in figs
    )
    c7 = fig_sync and vr.get("status") == "PASSED" and len(vr.get("figures_reviewed", [])) == 6
    checks.append(("N6_7_FIGURES_AND_VISUAL_REVIEW", c7, f"fig_sync={fig_sync}, visual_review={vr.get('status')}"))

    # N6_8: Synced reports, scripts, results, no setisearch/reports/, < 48 MB
    r_ws = WS / "RESULTS_REPORT.md"
    r_gp = GIT_PROG / "RESULTS_REPORT.md"
    r_dc = GIT_REPO / "docs/N6_KARDASHEV_III_SUPERCLUSTER_REPORT.md"
    r_rt = ROOT / "reports/N6_KARDASHEV_III_SUPERCLUSTER_REPORT.md"
    rep_hashes = {sha256_file(p) for p in (r_ws, r_gp, r_dc, r_rt) if p.exists()}
    scr_ok = all(
        (GIT_PROG / "scripts" / s).exists() and sha256_file(WS / "scripts" / s) == sha256_file(GIT_PROG / "scripts" / s)
        for s in ("n6_k3_analyzer.py", "stage1_n6_acquire_supercluster.py", "stage3_n6_k3_vetting.py", "plot_n6_figures.py", "audit_n6_kardashev_iii.py")
    )
    res_ok = all(
        (GIT_PROG / "results" / p.name).exists() and sha256_file(p) == sha256_file(GIT_PROG / "results" / p.name)
        for p in res.iterdir() if p.is_file()
    )
    oversized = [str(p.relative_to(GIT_REPO)) for p in list(GIT_PROG.rglob("*")) + [r_dc] if p.is_file() and p.stat().st_size >= 48 * 1024 * 1024]
    c8 = len(rep_hashes) == 1 and all(p.exists() for p in (r_ws, r_gp, r_dc, r_rt)) and scr_ok and res_ok and not (GIT_REPO / "reports").exists() and not oversized
    checks.append(("N6_8_REPORTS_SYNC_AND_GIT_PROG", c8, f"rep_sync={len(rep_hashes)==1}, scr_ok={scr_ok}, res_ok={res_ok}, oversized={len(oversized)}"))

    # N6_9: Docs & continuation markdown
    f_n6 = ROOT / "FORTSAET_FRA_N6_KARDASHEV_III_SUPERCLUSTER.md"
    readme_txt = (GIT_REPO / "README.md").read_text(encoding="utf-8")
    cont_txt = (GIT_REPO / "CONTINUE_SETI.md").read_text(encoding="utf-8")
    c9 = (
        f_n6.exists()
        and "N6_KARDASHEV_III_SUPERCLUSTER_REPORT.md" in readme_txt
        and "Spor N6" in readme_txt
        and "N6_KARDASHEV_III_SUPERCLUSTER_REPORT.md" in cont_txt
        and "Spor N6" in cont_txt
    )
    checks.append(("N6_9_DOCS_AND_CONTINUATION_MD", c9, f"fortsaet_exists={f_n6.exists()}, docs_updated={c9}"))

    # N6_10: Continuation ledger invariants
    led = json.loads((ROOT / "SETI_ACTIVE_CONTINUATION.json").read_text(encoding="utf-8"))
    n6_led = led.get("n6_kardashev_iii_supercluster_completed", {})
    c10 = (
        len(led) == 510
        and led.get("active_phase") == "D097"
        and led.get("current_table_cells") == 107105
        and led.get("old90_and_Rubin_stay_stopped") is True
        and "updated_utc" not in led
        and "n5_secular_ir_optical_completed" in led
        and n6_led.get("verified_k3_eti_candidates") == 0
        and n6_led.get("external_contacts") == 0
    )
    checks.append(("N6_10_CONTINUATION_LEDGER", c10, f"len={len(led)}, external_contacts={n6_led.get('external_contacts')}"))

    # N6_11: Local ZIP archive integrity
    zip_ok = False
    z_members = 0
    if ZIP_PATH.exists():
        with zipfile.ZipFile(ZIP_PATH, "r") as zf:
            names = set(zf.namelist())
            z_members = len(names)
            req_z = {"RESULTS_REPORT.md", "results/METHOD_LOCK.json", "results/IMPLEMENTATION_LOCK.json", "results/N6_ANALYZER_SUMMARY.json", "results/N6_STAGE3_VETTING.json", "results/VISUAL_REVIEW_N6.json"}
            req_z |= {f"figures/{f}" for f in figs}
            zip_ok = (zf.testzip() is None) and req_z.issubset(names)
    checks.append(("N6_11_LOCAL_ZIP_ARCHIVE", zip_ok, f"zip_ok={zip_ok}, members={z_members}"))

    # N6_12: Regression across sealed N5, N4, N3, and Spor 5
    r_n5 = subprocess.run(["/usr/bin/python3", "-S", str(ROOT / "analysis_workspace/work_n5_20261127_secular_ir_optical_1083/scripts/audit_n5_secular_bridge.py")], capture_output=True, text=True)
    n5_ok = all(f"[PASS] N5_{i}_" in r_n5.stdout for i in (1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12))
    r_n4 = subprocess.run(["/usr/bin/python3", "-S", str(ROOT / "analysis_workspace/work_n4_20261127_lowfreq_radio_bridge_1083/scripts/audit_n4_radio_bridge.py")], capture_output=True, text=True)
    n4_ok = all(f"[PASS] N4_{i}_" in r_n4.stdout for i in (1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12))
    r_n3 = subprocess.run(["/usr/bin/python3", "-S", str(ROOT / "analysis_workspace/work_n3_20261127_rubin_v3_1800ddf/scripts/audit_n3_rubin_v3.py")], capture_output=True, text=True)
    r_sp5 = subprocess.run(["/usr/bin/python3", "-S", str(GIT_REPO / "zenodo_package/verify_publication_package.py"), "--archives-dir", str(ROOT / "archives")], capture_output=True, text=True)
    c12 = n5_ok and n4_ok and ("12/12 PASSED" in r_n3.stdout) and ("12/12 PASSED" in r_sp5.stdout)
    checks.append(("N6_12_REGRESSION_AND_SEALED_INVARIANT", c12, f"n5_ok={n5_ok}, n4_ok={n4_ok}, n3_rc={r_n3.returncode}, sp5_rc={r_sp5.returncode}"))

    passed = sum(1 for _, ok, _ in checks if ok)
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\nN6_KARDASHEV_III_AUDIT: {passed}/{len(checks)} PASSED")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
