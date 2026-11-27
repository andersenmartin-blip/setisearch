#!/usr/bin/env python3
"""Pure-stdlib 12-point audit for Spor N9 (SPOR_N9_MILKY_WAY_GAIA_DR3_DARK_COMPANION_AND_ASTROMETRY)."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n9_20261127_gaia_dr3_dark_companions"
INP = ROOT / "inputs_n9_20261127"
GIT_REPO = ROOT / "setisearch"
GIT_PROG = GIT_REPO / "progress/2026-11-27-n9-gaia-dr3-dark-companions"
ZIP_PATH = ROOT / "archives_n9/SETI_N9_GAIA_DR3_DARK_COMPANIONS_2026-11-27.zip"

EXPECTED_ANALYZER_SHA = "f3824e4d4413452e221adb6deb8ea2ff4f6eb189d15bb6676eddc02d1f628025"


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
    s2 = json.loads((res / "N9_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    s3 = json.loads((res / "N9_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    vr = json.loads((res / "VISUAL_REVIEW_N9.json").read_text(encoding="utf-8"))

    # N9_1: Blind lock
    an_sha = sha256_file(WS / "scripts/n9_gaia_dark_companion_analyzer.py")
    ml_sha = sha256_file(res / "METHOD_LOCK.json")
    c1 = (
        an_sha == EXPECTED_ANALYZER_SHA
        and il.get("analyzer_sha256") == EXPECTED_ANALYZER_SHA
        and il.get("method_lock_sha256") == ml_sha
        and il.get("pre_acquisition_blind_lock") is True
        and ml.get("locked_utc", "") < s2.get("generated_utc", "")
    )
    checks.append(("N9_1_BLIND_LOCK", c1, f"sha_ok={an_sha == EXPECTED_ANALYZER_SHA}"))

    # N9_2: Stage 1 acquisition
    targs = csv_rows(INP / "milky_way_astrometry_targets.csv")
    mw_cnt = sum(1 for r in targs if r["is_bh_benchmark"] == "False")
    c2 = (
        mw_cnt == 996
        and (INP / "hgca/brandt_hgca.csv").exists()
        and (INP / "kervella/kervella_pma.csv").exists()
        and (INP / "gaia_nss/nss_tbooc.csv").exists()
    )
    checks.append(("N9_2_STAGE1_ACQUISITION", c2, f"mw={mw_cnt}, targets={len(targs)}"))

    # N9_3: Stage 2 outputs + BH1 positive benchmark
    cat = csv_rows(res / "N9_MILKY_WAY_ASTROMETRY_CATALOG.csv")
    trig = csv_rows(res / "N9_STAGE2_TRIGGERS.csv")
    c3 = (
        len(cat) == 999
        and len(trig) == 128
        and s2["pure_milky_way_stars_total"] == 996
        and s2["baseline_25yr_hgca_kervella_matched"] == 529
        and s2["bh_benchmarks_recovered_d1"] == 1
    )
    checks.append(("N9_3_STAGE2_AND_BH1_BENCHMARK", c3, f"mw=996, pma25yr={s2['baseline_25yr_hgca_kervella_matched']}, bh1={s2['bh_benchmarks_recovered_d1']}"))

    # N9_4: 1,200 injections
    inj = s2["injections"]
    c4 = inj["trials_total"] == 1200 and inj["completeness_d2_snr_ge_25"] >= 0.95 and inj["completeness_mean_astrometry"] >= 0.80
    checks.append(("N9_4_INJECTION_CALIBRATION", c4, f"trials={inj['trials_total']}, mean_eff={inj['completeness_mean_astrometry']}"))

    # N9_5: Stage 3 vetting zero dark ETI
    vet = csv_rows(res / "N9_CANDIDATES_VETTED.csv")
    c5 = (
        len(vet) == 128
        and s3["science_dark_mass_d1_triggers"] == 0
        and s3["verified_eti_candidates"] == 0
        and not any(r["eti_status"] == "UNRESOLVED_ETI_CANDIDATE" for r in vet)
    )
    checks.append(("N9_5_STAGE3_VETTING_ZERO_ETI", c5, f"vetted={len(vet)}, d1_sci={s3['science_dark_mass_d1_triggers']}, verified_eti=0"))

    # N9_6: Bayesian bounds
    bl = s2["bayesian_limits_zero_eti"]
    c6 = (
        abs(bl["all_pure_mw_996_raw"]["jeffreys_f95_pct"] - 0.1926) < 1e-4
        and abs(bl["all_pure_mw_eff"]["jeffreys_f95_pct"] - 0.2197) < 1e-4
        and abs(bl["pma_25yr_baseline"]["jeffreys_f95_pct"] - 0.3623) < 1e-4
    )
    checks.append(("N9_6_BAYESIAN_NULL_LIMITS", c6, f"mw_eff={bl['all_pure_mw_eff']['jeffreys_f95_pct']}%, pma25yr={bl['pma_25yr_baseline']['jeffreys_f95_pct']}%"))

    # N9_7: 6 PNGs + visual review SHA parity
    figs = [
        "figN9_01_milky_way_cmd_and_pma_mass_plane.png",
        "figN9_02_hgca_kervella_and_ruwe_diagnostics.png",
        "figN9_03_gaia_nss_dark_companion_mass_plane.png",
        "figN9_04_astrometric_vetting_funnel.png",
        "figN9_05_injection_recovery_and_bayesian_f95.png",
        "figN9_06_grand_milky_way_seti_synthesis.png",
    ]
    fig_sync = all(
        (WS / "figures" / f).exists() and (GIT_PROG / "figures" / f).exists()
        and sha256_file(WS / "figures" / f) == sha256_file(GIT_PROG / "figures" / f)
        for f in figs
    )
    c7 = fig_sync and vr.get("status") == "PASSED" and len(vr.get("figures_reviewed", [])) == 6
    checks.append(("N9_7_FIGURES_AND_VISUAL_REVIEW", c7, f"fig_sync={fig_sync}, review={vr.get('status')}"))

    # N9_8: Synced reports/scripts/results, no setisearch/reports/, <48 MB
    r_ws = WS / "RESULTS_REPORT.md"
    r_gp = GIT_PROG / "RESULTS_REPORT.md"
    r_dc = GIT_REPO / "docs/N9_GAIA_DR3_DARK_COMPANIONS_REPORT.md"
    r_rt = ROOT / "reports/N9_GAIA_DR3_DARK_COMPANIONS_REPORT.md"
    rep_hashes = {sha256_file(p) for p in (r_ws, r_gp, r_dc, r_rt) if p.exists()}
    scr_ok = all(
        (GIT_PROG / "scripts" / s).exists() and sha256_file(WS / "scripts" / s) == sha256_file(GIT_PROG / "scripts" / s)
        for s in ("n9_gaia_dark_companion_analyzer.py", "stage1_n9_acquire_gaia_astrometry.py", "stage3_n9_forensic_vetting.py", "plot_n9_figures.py", "audit_n9_gaia_dark_companions.py")
    )
    res_ok = all(
        (GIT_PROG / "results" / p.name).exists() and sha256_file(p) == sha256_file(GIT_PROG / "results" / p.name)
        for p in res.iterdir() if p.is_file()
    )
    oversized = [str(p.relative_to(GIT_REPO)) for p in list(GIT_PROG.rglob("*")) + [r_dc] if p.is_file() and p.stat().st_size >= 48 * 1024 * 1024]
    c8 = len(rep_hashes) == 1 and all(p.exists() for p in (r_ws, r_gp, r_dc, r_rt)) and scr_ok and res_ok and not (GIT_REPO / "reports").exists() and not oversized
    checks.append(("N9_8_REPORTS_AND_GIT_PROG", c8, f"rep_sync={len(rep_hashes)==1}, scr_ok={scr_ok}, res_ok={res_ok}"))

    # N9_9: Docs & continuation markdown
    c9 = (ROOT / "FORTSAET_FRA_N9_GAIA_DR3_DARK_COMPANIONS.md").exists() and "N9_GAIA_DR3_DARK_COMPANIONS_REPORT.md" in (GIT_REPO / "README.md").read_text(encoding="utf-8") and "N9_GAIA_DR3_DARK_COMPANIONS_REPORT.md" in (GIT_REPO / "CONTINUE_SETI.md").read_text(encoding="utf-8")
    checks.append(("N9_9_DOCS_UPDATED", c9, f"docs_ok={c9}"))

    # N9_10: Continuation ledger (len == 513)
    led = json.loads((ROOT / "SETI_ACTIVE_CONTINUATION.json").read_text(encoding="utf-8"))
    n9_led = led.get("n9_gaia_dr3_dark_companion_completed", {})
    c10 = (
        len(led) == 513
        and led.get("active_phase") == "D097"
        and led.get("current_table_cells") == 107105
        and led.get("old90_and_Rubin_stay_stopped") is True
        and "updated_utc" not in led
        and "n8_galactic_center_pulsars_completed" in led
        and n9_led.get("verified_eti_candidates") == 0
        and n9_led.get("external_contacts") == 0
    )
    checks.append(("N9_10_CONTINUATION_LEDGER", c10, f"len={len(led)}, ext={n9_led.get('external_contacts')}"))

    # N9_11: ZIP integrity
    zip_ok = False
    z_members = 0
    if ZIP_PATH.exists():
        with zipfile.ZipFile(ZIP_PATH, "r") as zf:
            names = set(zf.namelist())
            z_members = len(names)
            zip_ok = (zf.testzip() is None) and {"RESULTS_REPORT.md", "results/METHOD_LOCK.json", "results/N9_ANALYZER_SUMMARY.json", "results/N9_STAGE3_VETTING.json", "results/VISUAL_REVIEW_N9.json"}.issubset(names)
    checks.append(("N9_11_LOCAL_ZIP_ARCHIVE", zip_ok, f"zip_ok={zip_ok}, members={z_members}"))

    # N9_12: Direct regression check on N8 (which transitively audits N7->N6->N3->Sp5!)
    r_n8 = subprocess.run(["/usr/bin/python3", "-S", str(ROOT / "analysis_workspace/work_n8_20261127_galactic_center_and_pulsars/scripts/audit_n8_galactic_center.py")], capture_output=True, text=True)
    c12 = "12/12 PASSED" in r_n8.stdout
    checks.append(("N9_12_REGRESSION_N8_TO_SPOR5", c12, f"n8_12of12={c12}, rc={r_n8.returncode}"))

    passed = sum(1 for _, ok, _ in checks if ok)
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\nN9_GAIA_DARK_COMPANIONS_AUDIT: {passed}/{len(checks)} PASSED")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
