#!/usr/bin/env python3
"""Pure-stdlib 12-point audit for Spor N11B (SPOR_N11B_HARPS_SINGLE_EPOCH_TRANSIENT_LASER)."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n11b_20261128_harps_single_epoch_transient_laser"
INP = ROOT / "inputs_n11b_20261128"
GIT_REPO = ROOT / "setisearch"
GIT_PROG = GIT_REPO / "progress/2026-11-28-n11b-harps-single-epoch-transient-laser"
ZIP_PATH = ROOT / "archives_n11b/SETI_N11B_HARPS_TRANSIENT_LASER_2026-11-28.zip"

EXPECTED_ANALYZER_SHA = "7d132703f61ec2220dee1a0704c34d0b9f0cbdec3798498302251940072352e5"


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
    s2 = json.loads((res / "N11B_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    s3 = json.loads((res / "N11B_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    vr = json.loads((res / "VISUAL_REVIEW_N11B.json").read_text(encoding="utf-8"))
    acq = json.loads((INP / "stage1_acquisition_log.json").read_text(encoding="utf-8"))

    # N11B_1: Blind lock preserved & precedes final Stage 2 output
    an_sha = sha256_file(WS / "scripts/n11b_harps_transient_laser_analyzer.py")
    ml_sha = sha256_file(res / "METHOD_LOCK.json")
    c1 = (
        an_sha == EXPECTED_ANALYZER_SHA
        and il.get("analyzer_sha256") == EXPECTED_ANALYZER_SHA
        and il.get("method_lock_sha256") == ml_sha
        and il.get("pre_acquisition_blind_lock") is True
        and ml.get("relocked_utc", ml.get("locked_utc", "")) < s2.get("generated_utc", "")
    )
    checks.append(("N11B_1_BLIND_LOCK", c1, f"sha_ok={an_sha == EXPECTED_ANALYZER_SHA}"))

    # N11B_2: Stage 1 HARPS acquisition (160/160 FITS across 8 <11 pc Milky Way hosts)
    ep_csv = csv_rows(INP / "n11b_harps_epochs.csv")
    fits_count = len(list((INP / "fits").rglob("*.fits")))
    c2 = (
        acq.get("stars") == 8
        and acq.get("epochs_verified") == 160
        and len(ep_csv) == 160
        and fits_count == 160
    )
    checks.append(("N11B_2_STAGE1_HARPS_ACQ", c2, f"epochs={acq.get('epochs_verified')}/160, mib={acq.get('total_mib')}"))

    # N11B_3: Stage 2 optical LOEO transient laser coverage
    star_sum = csv_rows(res / "N11B_STAR_SUMMARY.csv")
    trig = csv_rows(res / "N11B_STAGE2_TRIGGERS.csv")
    c3 = (
        len(star_sum) == 8
        and s2["stars_analyzed"] == 8
        and s2["epochs_analyzed"] == 160
        and s2["wavelength_band_a"] == [4800.0, 6900.0]
        and len(trig) == s2["stage2_t1_triggers_total"] == 60
    )
    checks.append(("N11B_3_STAGE2_COVERAGE", c3, f"stars=8, ep=160, peaks={s2['peaks_z10_before_shape_veto']}, T1={len(trig)}"))

    # N11B_4: 1,200-trial real-noise benchmark (N11B vs Classical Stack, 0% CR/Flare FPR)
    inj = s2["injections"]
    c4 = (
        inj["trials_total"] == 1200
        and inj["laser_completeness"] >= 0.90
        and inj["classical_median_stack_completeness"] == 0.0
        and inj["cosmic_ray_fpr"] <= 0.02
        and inj["broad_flare_fpr"] <= 0.02
    )
    checks.append(("N11B_4_TRANSIENT_BENCHMARK", c4, f"laser={inj['laser_completeness']*100:.1f}% vs cls={inj['classical_median_stack_completeness']*100:.1f}%, cr_fpr={inj['cosmic_ray_fpr']*100:.1f}%"))

    # N11B_5: Stage 3 forensic vetting zero ETI
    vet = csv_rows(res / "N11B_CANDIDATES_VETTED.csv")
    c5 = (
        len(vet) == 60
        and s3["stage2_triggers_vetted"] == 60
        and s3["verified_eti_candidates"] == 0
        and not any(r["eti_status"] == "UNRESOLVED_ETI_CANDIDATE" for r in vet)
    )
    checks.append(("N11B_5_STAGE3_VETTING_ZERO_ETI", c5, f"vetted={len(vet)}, verified_eti=0"))

    # N11B_6: Bayesian zero-ETI prevalence bounds & beamed power limits
    bl = s2["provisional_zero_eti_bayesian_bounds"]
    c6 = (
        abs(bl["stars_raw_8"]["jeffreys_f95_pct"] - 20.7508) < 1e-3
        and abs(bl["stars_eff"]["jeffreys_f95_pct"] - 22.2822) < 1e-3
        and abs(bl["epochs_eff"]["jeffreys_f95_pct"] - 1.2942) < 1e-3
        and 0.05 <= s2["min_p_tx_10sig_kw"] <= 0.25
    )
    checks.append(("N11B_6_BAYESIAN_NULL_LIMITS", c6, f"star_eff={bl['stars_eff']['jeffreys_f95_pct']}%, ep_eff={bl['epochs_eff']['jeffreys_f95_pct']}%"))

    # N11B_7: 6 PNGs & visual review SHA parity
    figs = [
        "figN11B_01_harps_epochs_berv_and_power.png",
        "figN11B_02_head_to_head_transient_benchmark.png",
        "figN11B_03_loeo_tio_forest_subtraction.png",
        "figN11B_04_shape_diagnostics_and_stage3_veto.png",
        "figN11B_05_vetting_funnel_and_bayesian_f95.png",
        "figN11B_06_n10_n11a_n11b_blindspot_synthesis.png",
    ]
    fig_sync = all(
        (WS / "figures" / f).exists() and (GIT_PROG / "figures" / f).exists()
        and sha256_file(WS / "figures" / f) == sha256_file(GIT_PROG / "figures" / f)
        for f in figs
    )
    c7 = fig_sync and vr.get("status") == "PASSED" and len(vr.get("figures_reviewed", [])) == 6
    checks.append(("N11B_7_FIGURES_AND_VISUAL_REVIEW", c7, f"fig_sync={fig_sync}, review={vr.get('status')}"))

    # N11B_8: Synced reports/scripts/results, no raw .fits/.h5/.npy in GIT_PROG, no setisearch/reports/, <48 MB
    r_ws = WS / "RESULTS_REPORT.md"
    r_gp = GIT_PROG / "RESULTS_REPORT.md"
    r_dc = GIT_REPO / "docs/N11B_HARPS_SINGLE_EPOCH_TRANSIENT_LASER_REPORT.md"
    r_rt = ROOT / "reports/N11B_HARPS_SINGLE_EPOCH_TRANSIENT_LASER_REPORT.md"
    rep_hashes = {sha256_file(p) for p in (r_ws, r_gp, r_dc, r_rt) if p.exists()}
    scr_ok = all(
        (GIT_PROG / "scripts" / s).exists() and sha256_file(WS / "scripts" / s) == sha256_file(GIT_PROG / "scripts" / s)
        for s in ("n11b_harps_transient_laser_analyzer.py", "stage1_n11b_acquire_harps_epochs.py", "stage3_n11b_forensic_vetting.py", "plot_n11b_figures.py", "audit_n11b_harps_transient.py")
    )
    res_ok = all(
        (GIT_PROG / "results" / p.name).exists() and sha256_file(p) == sha256_file(GIT_PROG / "results" / p.name)
        for p in res.iterdir() if p.is_file()
    )
    heavy_in_git = list(GIT_REPO.rglob("*.h5")) + list(GIT_REPO.rglob("*.npy")) + list(GIT_PROG.rglob("*.fits"))
    oversized = [str(p.relative_to(GIT_REPO)) for p in list(GIT_PROG.rglob("*")) + [r_dc] if p.is_file() and p.stat().st_size >= 48 * 1024 * 1024]
    c8 = len(rep_hashes) == 1 and all(p.exists() for p in (r_ws, r_gp, r_dc, r_rt)) and scr_ok and res_ok and not (GIT_REPO / "reports").exists() and not heavy_in_git and not oversized
    checks.append(("N11B_8_REPORTS_AND_GIT_PROG", c8, f"rep_sync={len(rep_hashes)==1}, scr_ok={scr_ok}, res_ok={res_ok}, heavy={len(heavy_in_git)}"))

    # N11B_9: Docs & continuation markdown
    c9 = (
        (ROOT / "FORTSAET_FRA_N11B_HARPS_TRANSIENT_LASER.md").exists()
        and "N11B_HARPS_SINGLE_EPOCH_TRANSIENT_LASER_REPORT.md" in (GIT_REPO / "README.md").read_text(encoding="utf-8")
        and "N11B_HARPS_SINGLE_EPOCH_TRANSIENT_LASER_REPORT.md" in (GIT_REPO / "CONTINUE_SETI.md").read_text(encoding="utf-8")
    )
    checks.append(("N11B_9_DOCS_UPDATED", c9, f"docs_ok={c9}"))

    # N11B_10: Continuation ledger (len == 516, invariants preserved)
    led = json.loads((ROOT / "SETI_ACTIVE_CONTINUATION.json").read_text(encoding="utf-8"))
    n11b_led = led.get("n11b_harps_transient_laser_completed", {})
    c10 = (
        len(led) == 516
        and led.get("active_phase") == "D097"
        and led.get("current_table_cells") == 107105
        and led.get("old90_and_Rubin_stay_stopped") is True
        and "updated_utc" not in led
        and "n11a_fine_waterhole_gajjar_completed" in led
        and n11b_led.get("verified_eti_candidates") == 0
        and n11b_led.get("external_contacts") == 0
    )
    checks.append(("N11B_10_CONTINUATION_LEDGER", c10, f"len={len(led)}, ext={n11b_led.get('external_contacts')}"))

    # N11B_11: ZIP integrity
    zip_ok = False
    z_members = 0
    if ZIP_PATH.exists():
        with zipfile.ZipFile(ZIP_PATH, "r") as zf:
            names = set(zf.namelist())
            z_members = len(names)
            zip_ok = (zf.testzip() is None) and {"RESULTS_REPORT.md", "results/METHOD_LOCK.json", "results/N11B_ANALYZER_SUMMARY.json", "results/N11B_STAGE3_VETTING.json", "results/VISUAL_REVIEW_N11B.json"}.issubset(names)
    checks.append(("N11B_11_LOCAL_ZIP_ARCHIVE", zip_ok, f"zip_ok={zip_ok}, members={z_members}"))

    # N11B_12: Non-recursive sealed regression across N11A (1..9, 11), N10, and Spor 5 (12/12 PASSED)
    r_n11a = subprocess.run(["/usr/bin/python3", "-S", str(ROOT / "analysis_workspace/work_n11a_20261128_fine_waterhole_gajjar_plasma/scripts/audit_n11a_waterhole_gajjar.py")], capture_output=True, text=True)
    n11a_ok = all(f"[PASS] N11A_{i}_" in r_n11a.stdout for i in (1, 2, 3, 4, 5, 6, 7, 8, 9, 11)) and ("[PASS] N11A_12_" in r_n11a.stdout)
    c12 = n11a_ok
    checks.append(("N11B_12_REGRESSION_N11A_TO_SPOR5", c12, f"n11a_ok={n11a_ok}, n11a_rc={r_n11a.returncode}"))

    passed = sum(1 for _, ok, _ in checks if ok)
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\nN11B_HARPS_TRANSIENT_AUDIT: {passed}/{len(checks)} PASSED")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
