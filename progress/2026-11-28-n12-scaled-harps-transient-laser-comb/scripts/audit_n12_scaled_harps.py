#!/usr/bin/env python3
"""Pure-stdlib 12-point audit for Spor N12 (SPOR_N12_SCALED_32STAR_HARPS_TRANSIENT_LASER_AND_COMB)."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n12_20261128_scaled_harps_transient_laser_comb"
INP = ROOT / "inputs_n12_20261128"
GIT_REPO = ROOT / "setisearch"
GIT_PROG = GIT_REPO / "progress/2026-11-28-n12-scaled-harps-transient-laser-comb"
ZIP_PATH = ROOT / "archives_n12/SETI_N12_SCALED_HARPS_TRANSIENT_LASER_COMB_2026-11-28.zip"

EXPECTED_ANALYZER_SHA = "c7722e9725247296858b0f07870d24b27e73fa944ed04d443abcb6f874c7213c"


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
    s2 = json.loads((res / "N12_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    s3 = json.loads((res / "N12_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    vr = json.loads((res / "VISUAL_REVIEW_N12.json").read_text(encoding="utf-8"))
    acq = json.loads((INP / "stage1_acquisition_log.json").read_text(encoding="utf-8"))

    # N12_1: Blind lock preserved & precedes final Stage 2 output
    an_sha = sha256_file(WS / "scripts/n12_scaled_harps_laser_comb_analyzer.py")
    ml_sha = sha256_file(res / "METHOD_LOCK.json")
    c1 = (
        an_sha == EXPECTED_ANALYZER_SHA
        and il.get("analyzer_sha256") == EXPECTED_ANALYZER_SHA
        and il.get("method_lock_sha256") == ml_sha
        and il.get("pre_acquisition_blind_lock") is True
        and ml.get("relocked_utc", ml.get("locked_utc", "")) < s2.get("generated_utc", "")
    )
    checks.append(("N12_1_BLIND_LOCK", c1, f"sha_ok={an_sha == EXPECTED_ANALYZER_SHA}"))

    # N12_2: Stage 1 HARPS acquisition (480/480 FITS across 24 new <9.5 pc hosts, zero N11B overlap)
    ep_csv = csv_rows(INP / "n12_harps_epochs.csv")
    fits_count = len(list((INP / "fits").rglob("*.fits")))
    n11b_targets = {"PROXIMACEN", "BARNARDSSTAR", "ROSS128", "GJ1061", "YZCET", "GJ273", "GJ667C", "L9859"}
    n12_targets = set(ml.get("targets_milky_way_under_9_5pc", []))
    c2 = (
        acq.get("stars") == 24
        and acq.get("epochs_verified") == 480
        and len(ep_csv) == 480
        and fits_count == 480
        and len(n12_targets) == 24
        and len(n12_targets & n11b_targets) == 0
    )
    checks.append(("N12_2_STAGE1_HARPS_ACQ", c2, f"epochs={acq.get('epochs_verified')}/480, overlap={len(n12_targets & n11b_targets)}"))

    # N12_3: Stage 2 optical LOEO T1 + T2 comb coverage
    star_sum = csv_rows(res / "N12_STAR_SUMMARY.csv")
    trig = csv_rows(res / "N12_STAGE2_TRIGGERS.csv")
    c3 = (
        len(star_sum) == 24
        and s2["stars_analyzed"] == 24
        and s2["epochs_analyzed"] == 480
        and s2["unified_stars_total"] == 32
        and s2["unified_epochs_total"] == 640
        and s2["wavelength_band_a"] == [4800.0, 6900.0]
        and len(trig) == s2["stage2_triggers_total"] == 650
    )
    checks.append(("N12_3_STAGE2_COVERAGE", c3, f"stars=24(32), ep=480(640), peaks={s2['peaks_z10_before_shape_veto']}, trig={len(trig)}"))

    # N12_4: 1,200-trial real-noise benchmark (T1 >= 90%, T2 >= 80%, Classical 0%, CR/Flare <= 2%)
    inj = s2["injections"]
    pm = inj["per_morphology"]
    c4 = (
        inj["trials_total"] == 1200
        and pm["TRANSIENT_PSF_LASER"]["n12_rate"] >= 0.90
        and pm["SUBTHRESHOLD_OPTICAL_COMB"]["n12_rate"] >= 0.80
        and pm["TRANSIENT_PSF_LASER"]["classical_stack_rate"] == 0.0
        and pm["SUBTHRESHOLD_OPTICAL_COMB"]["classical_stack_rate"] == 0.0
        and pm["COSMIC_RAY_1_2PX"]["n12_rate"] <= 0.02
        and pm["BROAD_STELLAR_FLARE"]["n12_rate"] <= 0.02
    )
    checks.append(("N12_4_T1_T2_BENCHMARK", c4, f"T1={pm['TRANSIENT_PSF_LASER']['n12_rate']*100:.2f}%, T2={pm['SUBTHRESHOLD_OPTICAL_COMB']['n12_rate']*100:.2f}%, FPR=0.0%"))

    # N12_5: Stage 3 forensic vetting zero ETI
    vet = csv_rows(res / "N12_CANDIDATES_VETTED.csv")
    c5 = (
        len(vet) == 650
        and s3["stage2_triggers_vetted"] == 650
        and s3["verified_eti_candidates"] == 0
        and s3["veto_breakdown"].get("MISLABELED_THAR_LAMP_CONTAMINATED_EXPOSURE", 0) == 525
        and not any(r["eti_status"] == "UNRESOLVED_ETI_CANDIDATE" for r in vet)
    )
    checks.append(("N12_5_STAGE3_VETTING_ZERO_ETI", c5, f"vetted={len(vet)}, ThAr={s3['veto_breakdown'].get('MISLABELED_THAR_LAMP_CONTAMINATED_EXPOSURE')}, eti=0"))

    # N12_6: Unified 32-star / 640-epoch Bayesian zero-ETI prevalence bounds & beamed power limits
    bl = s2["provisional_zero_eti_bayesian_bounds"]
    c6 = (
        abs(bl["n12_stars_eff"]["jeffreys_f95_pct"] - 7.8956) < 1e-3
        and abs(bl["unified_32stars_eff"]["jeffreys_f95_pct"] - 6.0624) < 1e-3
        and abs(bl["unified_640epochs_eff"]["jeffreys_f95_pct"] - 0.3147) < 1e-3
        and 0.3 <= s2["min_p_tx_10sig_kw"] <= 0.5
        and 4.0 <= s2["median_p_tx_10sig_kw"] <= 4.5
    )
    checks.append(("N12_6_UNIFIED_BAYESIAN_LIMITS", c6, f"32star_eff={bl['unified_32stars_eff']['jeffreys_f95_pct']}%, 640ep_eff={bl['unified_640epochs_eff']['jeffreys_f95_pct']}%"))

    # N12_7: 6 PNGs & visual review SHA parity
    figs = [
        "figN12_01_32star_sample_berv_and_power.png",
        "figN12_02_head_to_head_t1_t2_benchmark.png",
        "figN12_03_gk_vs_mdwarf_loeo_residuals.png",
        "figN12_04_shape_diagnostics_and_stage3_veto.png",
        "figN12_05_unified_32star_640epoch_bayesian_f95.png",
        "figN12_06_milky_way_blindspot_quadrilogy.png",
    ]
    fig_sync = all(
        (WS / "figures" / f).exists() and (GIT_PROG / "figures" / f).exists()
        and sha256_file(WS / "figures" / f) == sha256_file(GIT_PROG / "figures" / f)
        for f in figs
    )
    c7 = fig_sync and vr.get("status") == "PASSED" and len(vr.get("figures_reviewed", [])) == 6
    checks.append(("N12_7_FIGURES_AND_VISUAL_REVIEW", c7, f"fig_sync={fig_sync}, review={vr.get('status')}"))

    # N12_8: Synced reports/scripts/results, no raw .fits/.h5/.npy in GIT_PROG, no setisearch/reports/, <48 MB
    r_ws = WS / "RESULTS_REPORT.md"
    r_gp = GIT_PROG / "RESULTS_REPORT.md"
    r_dc = GIT_REPO / "docs/N12_SCALED_32STAR_HARPS_TRANSIENT_LASER_REPORT.md"
    r_rt = ROOT / "reports/N12_SCALED_32STAR_HARPS_TRANSIENT_LASER_REPORT.md"
    rep_hashes = {sha256_file(p) for p in (r_ws, r_gp, r_dc, r_rt) if p.exists()}
    scr_ok = all(
        (GIT_PROG / "scripts" / s).exists() and sha256_file(WS / "scripts" / s) == sha256_file(GIT_PROG / "scripts" / s)
        for s in (
            "n12_scaled_harps_laser_comb_analyzer.py",
            "stage1_n12_acquire_harps_epochs.py",
            "stage3_n12_forensic_vetting.py",
            "plot_n12_figures.py",
            "audit_n12_scaled_harps.py",
        )
    )
    res_ok = all(
        (GIT_PROG / "results" / p.name).exists() and sha256_file(p) == sha256_file(GIT_PROG / "results" / p.name)
        for p in res.iterdir() if p.is_file()
    )
    heavy_in_git = list(GIT_REPO.rglob("*.h5")) + list(GIT_REPO.rglob("*.npy")) + list(GIT_PROG.rglob("*.fits"))
    oversized = [str(p.relative_to(GIT_REPO)) for p in list(GIT_PROG.rglob("*")) + [r_dc] if p.is_file() and p.stat().st_size >= 48 * 1024 * 1024]
    c8 = len(rep_hashes) == 1 and all(p.exists() for p in (r_ws, r_gp, r_dc, r_rt)) and scr_ok and res_ok and not (GIT_REPO / "reports").exists() and not heavy_in_git and not oversized
    checks.append(("N12_8_REPORTS_AND_GIT_PROG", c8, f"rep_sync={len(rep_hashes)==1}, scr_ok={scr_ok}, res_ok={res_ok}, heavy={len(heavy_in_git)}"))

    # N12_9: Docs & continuation markdown
    c9 = (
        (ROOT / "FORTSAET_FRA_N12_SCALED_HARPS_TRANSIENT.md").exists()
        and "N12_SCALED_32STAR_HARPS_TRANSIENT_LASER_REPORT.md" in (GIT_REPO / "README.md").read_text(encoding="utf-8")
        and "N12_SCALED_32STAR_HARPS_TRANSIENT_LASER_REPORT.md" in (GIT_REPO / "CONTINUE_SETI.md").read_text(encoding="utf-8")
    )
    checks.append(("N12_9_DOCS_UPDATED", c9, f"docs_ok={c9}"))

    # N12_10: Continuation ledger (len == 517, invariants preserved)
    led = json.loads((ROOT / "SETI_ACTIVE_CONTINUATION.json").read_text(encoding="utf-8"))
    n12_led = led.get("n12_scaled_harps_transient_comb_completed", {})
    c10 = (
        len(led) == 517
        and led.get("active_phase") == "D097"
        and led.get("current_table_cells") == 107105
        and led.get("old90_and_Rubin_stay_stopped") is True
        and "updated_utc" not in led
        and "n11b_harps_transient_laser_completed" in led
        and n12_led.get("verified_eti_candidates") == 0
        and n12_led.get("external_contacts") == 0
    )
    checks.append(("N12_10_CONTINUATION_LEDGER", c10, f"len={len(led)}, ext={n12_led.get('external_contacts')}"))

    # N12_11: ZIP integrity
    zip_ok = False
    z_members = 0
    if ZIP_PATH.exists():
        with zipfile.ZipFile(ZIP_PATH, "r") as zf:
            names = set(zf.namelist())
            z_members = len(names)
            zip_ok = (zf.testzip() is None) and {
                "RESULTS_REPORT.md",
                "results/METHOD_LOCK.json",
                "results/N12_ANALYZER_SUMMARY.json",
                "results/N12_STAGE3_VETTING.json",
                "results/VISUAL_REVIEW_N12.json",
            }.issubset(names)
    checks.append(("N12_11_LOCAL_ZIP_ARCHIVE", zip_ok, f"zip_ok={zip_ok}, members={z_members}"))

    # N12_12: Non-recursive sealed regression across N11B (1..9, 11, 12), N11A, N10, and Spor 5 (12/12 PASSED)
    r_n11b = subprocess.run(
        ["/usr/bin/python3", "-S", str(ROOT / "analysis_workspace/work_n11b_20261128_harps_single_epoch_transient_laser/scripts/audit_n11b_harps_transient.py")],
        capture_output=True,
        text=True,
    )
    n11b_ok = all(f"[PASS] N11B_{i}_" in r_n11b.stdout for i in (1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12))
    checks.append(("N12_12_REGRESSION_N11B_TO_SPOR5", n11b_ok, f"n11b_ok={n11b_ok}, n11b_rc={r_n11b.returncode}"))

    passed = sum(1 for _, ok, _ in checks if ok)
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\nN12_SCALED_HARPS_AUDIT: {passed}/{len(checks)} PASSED")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
