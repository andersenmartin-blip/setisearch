#!/usr/bin/env python3
"""Pure-stdlib 12-point audit for Spor N11A (SPOR_N11A_FINE_WATERHOLE_GAJJAR_PLASMA)."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n11a_20261128_fine_waterhole_gajjar_plasma"
INP = ROOT / "inputs_n11a_20261128"
GIT_REPO = ROOT / "setisearch"
GIT_PROG = GIT_REPO / "progress/2026-11-28-n11a-fine-waterhole-gajjar-plasma"
ZIP_PATH = ROOT / "archives_n11a/SETI_N11A_FINE_WATERHOLE_GAJJAR_PLASMA_2026-11-28.zip"

EXPECTED_ANALYZER_SHA = "a460ca9a6553082aabac2cd96a26a20d33f5f755f2e07a7c24ac3582a74ab5e7"


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
    s2 = json.loads((res / "N11A_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    s3 = json.loads((res / "N11A_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    vr = json.loads((res / "VISUAL_REVIEW_N11A.json").read_text(encoding="utf-8"))
    acq = json.loads((INP / "stage1_acquisition_log.json").read_text(encoding="utf-8"))

    # N11A_1: Blind lock preserved & precedes Stage 2 outputs
    an_sha = sha256_file(WS / "scripts/n11a_waterhole_gajjar_analyzer.py")
    ml_sha = sha256_file(res / "METHOD_LOCK.json")
    c1 = (
        an_sha == EXPECTED_ANALYZER_SHA
        and il.get("analyzer_sha256") == EXPECTED_ANALYZER_SHA
        and il.get("method_lock_sha256") == ml_sha
        and il.get("pre_acquisition_blind_lock") is True
        and ml.get("locked_utc", "") < s2.get("generated_utc", "")
    )
    checks.append(("N11A_1_BLIND_LOCK", c1, f"sha_ok={an_sha == EXPECTED_ANALYZER_SHA}"))

    # N11A_2: Stage 1 HTTP-Range waterhole slicing (54/54 scans across 9 <=6pc M-dwarfs)
    scans_csv = csv_rows(INP / "n11a_waterhole_scans.csv")
    npy_count = len(list((INP / "slabs").rglob("*.npy")))
    c2 = (
        acq.get("cadences") == 9
        and acq.get("scans_sliced") == 54
        and acq.get("bandwidth_saved_factor", 0) > 250.0
        and len(scans_csv) == 54
        and npy_count == 54
    )
    checks.append(("N11A_2_STAGE1_HTTP_RANGE", c2, f"scans={acq.get('scans_sliced')}/54, npy={npy_count}, saved={acq.get('bandwidth_saved_factor')}x"))

    # N11A_3: Stage 2 fine waterhole scan coverage
    cad_sum = csv_rows(res / "N11A_CADENCE_SUMMARY.csv")
    trig = csv_rows(res / "N11A_STAGE2_TRIGGERS.csv")
    c3 = (
        len(cad_sum) == 9
        and s2["stars_analyzed"] == 9
        and s2["remote_hdf5_scans_sliced"] == 54
        and s2["blocks_clean_total"] == 576
        and s2["total_clean_bw_mhz"] >= 26.0
        and len(trig) == s2["stage2_triggers_total"] == 0
    )
    checks.append(("N11A_3_STAGE2_COVERAGE", c3, f"stars=9, blocks={s2['blocks_clean_total']}, bw={s2['total_clean_bw_mhz']}MHz, trig={len(trig)}"))

    # N11A_4: 1,200-trial head-to-head blind-spot benchmark (Gajjar primary vs Classical 1-bin)
    inj = s2["injections"]
    pm = inj["per_morphology"]
    c4 = (
        inj["trials_total"] == 1200
        and pm["GAJJAR_PLASMA_10_350HZ"]["n11a_rate"] >= 0.90
        and pm["FINE_HARMONIC_COMB"]["n11a_rate"] >= 0.60
        and inj["classical_1bin_completeness"] == 0.0
    )
    checks.append(("N11A_4_GAJJAR_BENCHMARK", c4, f"gajjar={pm['GAJJAR_PLASMA_10_350HZ']['n11a_rate']*100:.1f}%, mean={inj['n11a_mean_completeness']*100:.2f}% vs cls=0.0%"))

    # N11A_5: Stage 3 forensic vetting zero ETI
    vet = csv_rows(res / "N11A_CANDIDATES_VETTED.csv")
    c5 = (
        len(vet) == 0
        and s3["stage2_triggers_vetted"] == 0
        and s3["verified_eti_candidates"] == 0
        and s3["blocks_verified_quiet"] == 576
        and s3["max_comb_on2_observed"] > 200.0
    )
    checks.append(("N11A_5_STAGE3_VETTING_ZERO_ETI", c5, f"quiet_blocks={s3['blocks_verified_quiet']}, max_comb_rfi={s3['max_comb_on2_observed']}"))

    # N11A_6: Bayesian zero-ETI prevalence bounds & physical EIRP limits
    bl = s2["bayesian_zero_eti_bounds"]
    c6 = (
        abs(bl["stars_raw"]["jeffreys_f95_pct"] - 18.7366) < 1e-3
        and abs(bl["stars_eff"]["jeffreys_f95_pct"] - 30.7435) < 1e-3
        and abs(bl["star_blocks_eff"]["jeffreys_f95_pct"] - 0.6022) < 1e-3
        and 5.0 <= s2["median_eirp_w1_gw"] <= 20.0
    )
    checks.append(("N11A_6_BAYESIAN_NULL_LIMITS", c6, f"star_eff={bl['stars_eff']['jeffreys_f95_pct']}%, blk_eff={bl['star_blocks_eff']['jeffreys_f95_pct']}%"))

    # N11A_7: 6 PNGs & visual review SHA parity
    figs = [
        "figN11A_01_fine_waterhole_and_eirp.png",
        "figN11A_02_head_to_head_gajjar_benchmark.png",
        "figN11A_03_abacad_fine_waterfalls.png",
        "figN11A_04_comb_and_noise_diagnostics.png",
        "figN11A_05_bayesian_f95_and_sensitivity.png",
        "figN11A_06_n10_n11a_radio_synthesis.png",
    ]
    fig_sync = all(
        (WS / "figures" / f).exists() and (GIT_PROG / "figures" / f).exists()
        and sha256_file(WS / "figures" / f) == sha256_file(GIT_PROG / "figures" / f)
        for f in figs
    )
    c7 = fig_sync and vr.get("status") == "PASSED" and len(vr.get("figures_reviewed", [])) == 6
    checks.append(("N11A_7_FIGURES_AND_VISUAL_REVIEW", c7, f"fig_sync={fig_sync}, review={vr.get('status')}"))

    # N11A_8: Synced reports/scripts/results, no .h5/.npy or setisearch/reports/, <48 MB
    r_ws = WS / "RESULTS_REPORT.md"
    r_gp = GIT_PROG / "RESULTS_REPORT.md"
    r_dc = GIT_REPO / "docs/N11A_FINE_WATERHOLE_GAJJAR_PLASMA_REPORT.md"
    r_rt = ROOT / "reports/N11A_FINE_WATERHOLE_GAJJAR_PLASMA_REPORT.md"
    rep_hashes = {sha256_file(p) for p in (r_ws, r_gp, r_dc, r_rt) if p.exists()}
    scr_ok = all(
        (GIT_PROG / "scripts" / s).exists() and sha256_file(WS / "scripts" / s) == sha256_file(GIT_PROG / "scripts" / s)
        for s in ("n11a_waterhole_gajjar_analyzer.py", "stage1_n11a_fetch_waterhole_slices.py", "stage3_n11a_forensic_vetting.py", "plot_n11a_figures.py", "audit_n11a_waterhole_gajjar.py")
    )
    res_ok = all(
        (GIT_PROG / "results" / p.name).exists() and sha256_file(p) == sha256_file(GIT_PROG / "results" / p.name)
        for p in res.iterdir() if p.is_file()
    )
    heavy_in_git = list(GIT_REPO.rglob("*.h5")) + list(GIT_REPO.rglob("*.npy")) + list(GIT_PROG.rglob("*.fits"))
    oversized = [str(p.relative_to(GIT_REPO)) for p in list(GIT_PROG.rglob("*")) + [r_dc] if p.is_file() and p.stat().st_size >= 48 * 1024 * 1024]
    c8 = len(rep_hashes) == 1 and all(p.exists() for p in (r_ws, r_gp, r_dc, r_rt)) and scr_ok and res_ok and not (GIT_REPO / "reports").exists() and not heavy_in_git and not oversized
    checks.append(("N11A_8_REPORTS_AND_GIT_PROG", c8, f"rep_sync={len(rep_hashes)==1}, scr_ok={scr_ok}, res_ok={res_ok}, heavy={len(heavy_in_git)}"))

    # N11A_9: Docs & continuation markdown
    c9 = (
        (ROOT / "FORTSAET_FRA_N11A_FINE_WATERHOLE_GAJJAR.md").exists()
        and "N11A_FINE_WATERHOLE_GAJJAR_PLASMA_REPORT.md" in (GIT_REPO / "README.md").read_text(encoding="utf-8")
        and "N11A_FINE_WATERHOLE_GAJJAR_PLASMA_REPORT.md" in (GIT_REPO / "CONTINUE_SETI.md").read_text(encoding="utf-8")
    )
    checks.append(("N11A_9_DOCS_UPDATED", c9, f"docs_ok={c9}"))

    # N11A_10: Continuation ledger (len == 515, invariants preserved)
    led = json.loads((ROOT / "SETI_ACTIVE_CONTINUATION.json").read_text(encoding="utf-8"))
    n11a_led = led.get("n11a_fine_waterhole_gajjar_completed", {})
    c10 = (
        len(led) == 515
        and led.get("active_phase") == "D097"
        and led.get("current_table_cells") == 107105
        and led.get("old90_and_Rubin_stay_stopped") is True
        and "updated_utc" not in led
        and "n10_bl_radio_blindspot_abacad_completed" in led
        and n11a_led.get("verified_eti_candidates") == 0
        and n11a_led.get("external_contacts") == 0
    )
    checks.append(("N11A_10_CONTINUATION_LEDGER", c10, f"len={len(led)}, ext={n11a_led.get('external_contacts')}"))

    # N11A_11: ZIP integrity
    zip_ok = False
    z_members = 0
    if ZIP_PATH.exists():
        with zipfile.ZipFile(ZIP_PATH, "r") as zf:
            names = set(zf.namelist())
            z_members = len(names)
            zip_ok = (zf.testzip() is None) and {"RESULTS_REPORT.md", "results/METHOD_LOCK.json", "results/N11A_ANALYZER_SUMMARY.json", "results/N11A_STAGE3_VETTING.json", "results/VISUAL_REVIEW_N11A.json"}.issubset(names)
    checks.append(("N11A_11_LOCAL_ZIP_ARCHIVE", zip_ok, f"zip_ok={zip_ok}, members={z_members}"))

    # N11A_12: Sealed regression across N10, N9, N8 locks/summaries/ZIPs + Spor 5 (12/12 PASSED)
    n10_s2 = json.loads((ROOT / "analysis_workspace/work_n10_20261127_bl_radio_blindspot_abacad/results/N10_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    n10_s3 = json.loads((ROOT / "analysis_workspace/work_n10_20261127_bl_radio_blindspot_abacad/results/N10_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    n10_il = json.loads((ROOT / "analysis_workspace/work_n10_20261127_bl_radio_blindspot_abacad/results/IMPLEMENTATION_LOCK.json").read_text(encoding="utf-8"))
    n10_zip = ROOT / "archives_n10/SETI_N10_BL_RADIO_BLINDSPOT_ABACAD_2026-11-27.zip"
    with zipfile.ZipFile(n10_zip, "r") as z10:
        n10_z_ok = (z10.testzip() is None)
    n9_s3 = json.loads((ROOT / "analysis_workspace/work_n9_20261127_gaia_dr3_dark_companions/results/N9_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    n8_s3 = json.loads((ROOT / "analysis_workspace/work_n8_20261127_galactic_center_and_pulsars/results/N8_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    n10_ok = (
        n10_il.get("analyzer_sha256") == "ca65404e9a315c2ca6d50452741c73499a29fc2d05508598a0f359321ae60a10"
        and n10_s2.get("injections", {}).get("n10_mean_completeness", 0) >= 0.90
        and n10_s3.get("verified_eti_candidates") == 0
        and n10_z_ok
        and n9_s3.get("verified_eti_candidates") == 0
        and n8_s3.get("verified_eti_candidates") == 0
    )
    r_sp5 = subprocess.run(["/usr/bin/python3", "-S", str(GIT_REPO / "zenodo_package/verify_publication_package.py"), "--archives-dir", str(ROOT / "archives")], capture_output=True, text=True)
    c12 = n10_ok and ("12/12 PASSED" in r_sp5.stdout)
    checks.append(("N11A_12_REGRESSION_N10_TO_SPOR5", c12, f"n10_n9_n8_ok={n10_ok}, sp5_rc={r_sp5.returncode}"))

    passed = sum(1 for _, ok, _ in checks if ok)
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\nN11A_WATERHOLE_GAJJAR_AUDIT: {passed}/{len(checks)} PASSED")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
