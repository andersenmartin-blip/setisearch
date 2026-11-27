#!/usr/bin/env python3
"""Pure-stdlib 12-point audit for Spor N8 (SPOR_N8_GALACTIC_CENTER_BEACON_AND_PULSAR_SURVEY)."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n8_20261127_galactic_center_and_pulsars"
INP = ROOT / "inputs_n8_20261127"
GIT_REPO = ROOT / "setisearch"
GIT_PROG = GIT_REPO / "progress/2026-11-27-n8-galactic-center-and-pulsars"
ZIP_PATH = ROOT / "archives_n8/SETI_N8_GALACTIC_CENTER_AND_PULSARS_2026-11-27.zip"

EXPECTED_ANALYZER_SHA = "3bc4e2d794ce3e6a36499fcadff9cc2515f7ef479a3e4d4105bdb08c937b2d6b"


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
    s2 = json.loads((res / "N8_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    s3 = json.loads((res / "N8_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    vr = json.loads((res / "VISUAL_REVIEW_N8.json").read_text(encoding="utf-8"))

    # N8_1: Blind lock
    an_sha = sha256_file(WS / "scripts/n8_galactic_center_analyzer.py")
    ml_sha = sha256_file(res / "METHOD_LOCK.json")
    c1 = (
        an_sha == EXPECTED_ANALYZER_SHA
        and il.get("analyzer_sha256") == EXPECTED_ANALYZER_SHA
        and il.get("method_lock_sha256") == ml_sha
        and il.get("pre_acquisition_blind_lock") is True
        and ml.get("locked_utc", "") < s2.get("generated_utc", "")
    )
    checks.append(("N8_1_BLIND_LOCK", c1, f"sha_ok={an_sha == EXPECTED_ANALYZER_SHA}"))

    # N8_2: Stage 1 acquisition
    psr_rows = csv_rows(INP / "atnf/atnf_milky_way_pulsars.csv")
    fer_rows = csv_rows(INP / "fermi/fermi_4fgl_galactic_bulge.csv")
    nv_rows = csv_rows(INP / "radio/nvss_galactic_center.csv")
    csc_rows = csv_rows(INP / "xray/csc2_galactic_center.csv")
    no_mc = not any("LMC" in (r.get("Assoc") or "").upper() or "SMC" in (r.get("Assoc") or "").upper() for r in psr_rows)
    c2 = len(psr_rows) == 2501 and len(fer_rows) == 222 and len(nv_rows) == 1780 and len(csc_rows) == 7457 and no_mc
    checks.append(("N8_2_STAGE1_GC_ACQUISITION", c2, f"psr={len(psr_rows)}, fermi={len(fer_rows)}, nvss={len(nv_rows)}, csc2={len(csc_rows)}"))

    # N8_3: Stage 2 outputs
    c3 = (
        len(csv_rows(res / "N8_MILKY_WAY_PULSARS_CATALOG.csv")) == 2501
        and len(csv_rows(res / "N8_BULGE_FERMI_CATALOG.csv")) == 222
        and len(csv_rows(res / "N8_STAGE2_TRIGGERS.csv")) == 4
        and s2["galactic_center_core_pulsars"] == 104
        and s2["fermi_bulge_unassociated"] == 168
    )
    checks.append(("N8_3_STAGE2_OUTPUTS", c3, f"gc_core={s2['galactic_center_core_pulsars']}, trig={s2['stage2_triggers_total']}"))

    # N8_4: 1,200 injections
    inj = s2["injections"]
    c4 = inj["trials_total"] == 1200 and inj["completeness_psr_mean"] >= 0.90 and inj["completeness_fermi_sig_ge_20"] >= 0.95
    checks.append(("N8_4_INJECTION_CALIBRATION", c4, f"trials={inj['trials_total']}, psr_mean={inj['completeness_psr_mean']}"))

    # N8_5: Stage 3 zero ETI
    vet = csv_rows(res / "N8_CANDIDATES_VETTED.csv")
    c5 = (
        len(vet) == 4
        and s3["verified_eti_candidates"] == 0
        and all(r["eti_status"] == "VETOED_ASTROPHYSICAL_OR_NOISE" for r in vet)
    )
    checks.append(("N8_5_STAGE3_VETTING_ZERO_ETI", c5, f"vetted={len(vet)}, verified_eti={s3['verified_eti_candidates']}"))

    # N8_6: Bayesian bounds
    bl = s2["bayesian_limits_zero_eti"]
    c6 = (
        abs(bl["all_mw_pulsars_raw"]["jeffreys_f95_pct"] - 0.0768) < 1e-4
        and abs(bl["all_mw_pulsars_eff"]["jeffreys_f95_pct"] - 0.0797) < 1e-4
        and abs(bl["fermi_bulge_all"]["jeffreys_f95_pct"] - 0.8605) < 1e-4
    )
    checks.append(("N8_6_BAYESIAN_NULL_LIMITS", c6, f"psr_eff={bl['all_mw_pulsars_eff']['jeffreys_f95_pct']}%"))

    # N8_7: Figures + visual review parity
    figs = [
        "figN8_01_milky_way_pulsar_and_bulge_sky.png",
        "figN8_02_pulsar_p_pdot_and_spinup_diagnostics.png",
        "figN8_03_fermi_bulge_and_gc_core_overlays.png",
        "figN8_04_bulge_variability_and_veto_funnel.png",
        "figN8_05_injection_recovery_and_bayesian_f95.png",
        "figN8_06_milky_way_gc_synthesis.png",
    ]
    fig_sync = all(
        (WS / "figures" / f).exists() and (GIT_PROG / "figures" / f).exists()
        and sha256_file(WS / "figures" / f) == sha256_file(GIT_PROG / "figures" / f)
        for f in figs
    )
    c7 = fig_sync and vr.get("status") == "PASSED" and len(vr.get("figures_reviewed", [])) == 6
    checks.append(("N8_7_FIGURES_AND_VISUAL_REVIEW", c7, f"fig_sync={fig_sync}, review={vr.get('status')}"))

    # N8_8: Reports synced & <48MB & no setisearch/reports
    r_ws = WS / "RESULTS_REPORT.md"
    r_gp = GIT_PROG / "RESULTS_REPORT.md"
    r_dc = GIT_REPO / "docs/N8_GALACTIC_CENTER_PULSARS_REPORT.md"
    r_rt = ROOT / "reports/N8_GALACTIC_CENTER_PULSARS_REPORT.md"
    rep_hashes = {sha256_file(p) for p in (r_ws, r_gp, r_dc, r_rt) if p.exists()}
    scr_ok = all(
        (GIT_PROG / "scripts" / s).exists() and sha256_file(WS / "scripts" / s) == sha256_file(GIT_PROG / "scripts" / s)
        for s in ("n8_galactic_center_analyzer.py", "stage1_n8_acquire_gc_pulsars.py", "stage3_n8_forensic_vetting.py", "plot_n8_figures.py", "audit_n8_galactic_center.py")
    )
    res_ok = all(
        (GIT_PROG / "results" / p.name).exists() and sha256_file(p) == sha256_file(GIT_PROG / "results" / p.name)
        for p in res.iterdir() if p.is_file()
    )
    oversized = [str(p.relative_to(GIT_REPO)) for p in list(GIT_PROG.rglob("*")) + [r_dc] if p.is_file() and p.stat().st_size >= 48 * 1024 * 1024]
    c8 = len(rep_hashes) == 1 and all(p.exists() for p in (r_ws, r_gp, r_dc, r_rt)) and scr_ok and res_ok and not (GIT_REPO / "reports").exists() and not oversized
    checks.append(("N8_8_REPORTS_AND_GIT_PROG", c8, f"rep_sync={len(rep_hashes)==1}, scr_ok={scr_ok}, res_ok={res_ok}"))

    # N8_9: Docs & continuation markdown
    c9 = (ROOT / "FORTSAET_FRA_N8_GALACTIC_CENTER_PULSARS.md").exists() and "N8_GALACTIC_CENTER_PULSARS_REPORT.md" in (GIT_REPO / "README.md").read_text(encoding="utf-8") and "N8_GALACTIC_CENTER_PULSARS_REPORT.md" in (GIT_REPO / "CONTINUE_SETI.md").read_text(encoding="utf-8")
    checks.append(("N8_9_DOCS_UPDATED", c9, f"docs_ok={c9}"))

    # N8_10: Continuation ledger (>=512, invariants preserved)
    led = json.loads((ROOT / "SETI_ACTIVE_CONTINUATION.json").read_text(encoding="utf-8"))
    n8_led = led.get("n8_galactic_center_pulsars_completed", {})
    c10 = (
        len(led) >= 512
        and led.get("active_phase") == "D097"
        and led.get("current_table_cells") == 107105
        and led.get("old90_and_Rubin_stay_stopped") is True
        and "updated_utc" not in led
        and "n7_tess_milky_way_completed" in led
        and n8_led.get("verified_eti_candidates") == 0
        and n8_led.get("external_contacts") == 0
    )
    checks.append(("N8_10_CONTINUATION_LEDGER", c10, f"len={len(led)}, ext={n8_led.get('external_contacts')}"))

    # N8_11: ZIP integrity
    zip_ok = False
    z_members = 0
    if ZIP_PATH.exists():
        with zipfile.ZipFile(ZIP_PATH, "r") as zf:
            names = set(zf.namelist())
            z_members = len(names)
            zip_ok = (zf.testzip() is None) and {"RESULTS_REPORT.md", "results/METHOD_LOCK.json", "results/N8_ANALYZER_SUMMARY.json", "results/N8_STAGE3_VETTING.json", "results/VISUAL_REVIEW_N8.json"}.issubset(names)
    checks.append(("N8_11_LOCAL_ZIP_ARCHIVE", zip_ok, f"zip_ok={zip_ok}, members={z_members}"))

    # N8_12: Regression across N7, N6, N3, Spor 5
    r_n7 = subprocess.run(["/usr/bin/python3", "-S", str(ROOT / "analysis_workspace/work_n7_20261127_tess_milky_way_megastructures/scripts/audit_n7_tess_milky_way.py")], capture_output=True, text=True)
    n7_ok = all(f"[PASS] N7_{i}_" in r_n7.stdout for i in (1, 2, 3, 4, 5, 6, 7, 8, 9, 11))
    r_n6 = subprocess.run(["/usr/bin/python3", "-S", str(ROOT / "analysis_workspace/work_n6_20261127_kardashev_iii_supercluster/scripts/audit_n6_kardashev_iii.py")], capture_output=True, text=True)
    n6_ok = all(f"[PASS] N6_{i}_" in r_n6.stdout for i in (1, 2, 3, 4, 5, 6, 7, 8, 9, 11))
    r_n3 = subprocess.run(["/usr/bin/python3", "-S", str(ROOT / "analysis_workspace/work_n3_20261127_rubin_v3_1800ddf/scripts/audit_n3_rubin_v3.py")], capture_output=True, text=True)
    r_sp5 = subprocess.run(["/usr/bin/python3", "-S", str(GIT_REPO / "zenodo_package/verify_publication_package.py"), "--archives-dir", str(ROOT / "archives")], capture_output=True, text=True)
    c12 = n7_ok and n6_ok and ("12/12 PASSED" in r_n3.stdout) and ("12/12 PASSED" in r_sp5.stdout)
    checks.append(("N8_12_REGRESSION_AND_SEALED_INVARIANT", c12, f"n7_ok={n7_ok}, n6_ok={n6_ok}, n3_rc={r_n3.returncode}, sp5_rc={r_sp5.returncode}"))

    passed = sum(1 for _, ok, _ in checks if ok)
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\nN8_GALACTIC_CENTER_AUDIT: {passed}/{len(checks)} PASSED")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
