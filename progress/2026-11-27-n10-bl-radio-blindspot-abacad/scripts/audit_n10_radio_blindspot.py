#!/usr/bin/env python3
"""Pure-stdlib 12-point audit for Spor N10 (SPOR_N10_BL_RADIO_BLINDSPOT_ABACAD)."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n10_20261127_bl_radio_blindspot_abacad"
INP = ROOT / "inputs_n10_20261127"
GIT_REPO = ROOT / "setisearch"
GIT_PROG = GIT_REPO / "progress/2026-11-27-n10-bl-radio-blindspot-abacad"
ZIP_PATH = ROOT / "archives_n10/SETI_N10_BL_RADIO_BLINDSPOT_ABACAD_2026-11-27.zip"

EXPECTED_ANALYZER_SHA = "ca65404e9a315c2ca6d50452741c73499a29fc2d05508598a0f359321ae60a10"


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
    s2 = json.loads((res / "N10_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    s3 = json.loads((res / "N10_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    vr = json.loads((res / "VISUAL_REVIEW_N10.json").read_text(encoding="utf-8"))
    acq = json.loads((INP / "stage1_acquisition_log.json").read_text(encoding="utf-8"))

    # N10_1: Blind lock preserved & precedes Stage 2 outputs
    an_sha = sha256_file(WS / "scripts/n10_radio_blindspot_analyzer.py")
    ml_sha = sha256_file(res / "METHOD_LOCK.json")
    c1 = (
        an_sha == EXPECTED_ANALYZER_SHA
        and il.get("analyzer_sha256") == EXPECTED_ANALYZER_SHA
        and il.get("method_lock_sha256") == ml_sha
        and il.get("pre_acquisition_blind_lock") is True
        and ml.get("locked_utc", "") < s2.get("generated_utc", "")
    )
    checks.append(("N10_1_BLIND_LOCK", c1, f"sha_ok={an_sha == EXPECTED_ANALYZER_SHA}"))

    # N10_2: Stage 1 acquisition (36/36 MD5-verified .0002.h5 across 6 <5pc Milky Way M-dwarfs)
    scans_csv = csv_rows(INP / "n10_abacad_scans.csv")
    c2 = (
        acq.get("cadences") == 6
        and acq.get("files_verified") == 36
        and acq.get("md5_all_verified") is True
        and len(scans_csv) == 36
    )
    checks.append(("N10_2_STAGE1_ACQUISITION", c2, f"files={acq.get('files_verified')}/36, gib={acq.get('total_bytes',0)/(1<<30):.2f}"))

    # N10_3: Stage 2 multi-morphology scan coverage
    cad_sum = csv_rows(res / "N10_CADENCE_SUMMARY.csv")
    trig = csv_rows(res / "N10_STAGE2_TRIGGERS.csv")
    c3 = (
        len(cad_sum) == 6
        and s2["stars_analyzed"] == 6
        and s2["scans_analyzed"] == 36
        and s2["total_clean_bw_mhz"] >= 4000.0
        and len(trig) == s2["stage2_triggers_total"] == 136
    )
    checks.append(("N10_3_STAGE2_COVERAGE", c3, f"stars=6, tiles={s2['total_clean_tiles']}, bw={s2['total_clean_bw_mhz']}MHz, trig={len(trig)}"))

    # N10_4: 1,200-trial head-to-head blind-spot benchmark (N10 vs Classical 1-bin)
    inj = s2["injections"]
    pm = inj["per_morphology"]
    c4 = (
        inj["trials_total"] == 1200
        and inj["n10_mean_completeness"] >= 0.85
        and inj["classical_1bin_mean_completeness"] <= 0.05
        and all(pm[k]["n10_rate"] >= 0.80 for k in ("PLASMA_BROADENED", "CURVED_DRIFT", "SHORT_BURST", "FHSS_HOPPING"))
    )
    checks.append(("N10_4_HEAD_TO_HEAD_BENCHMARK", c4, f"n10={inj['n10_mean_completeness']*100:.2f}% vs cls={inj['classical_1bin_mean_completeness']*100:.2f}%"))

    # N10_5: Stage 3 forensic vetting zero ETI
    vet = csv_rows(res / "N10_CANDIDATES_VETTED.csv")
    c5 = (
        len(vet) == 136
        and s3["stage2_triggers_vetted"] == 136
        and s3["verified_eti_candidates"] == 0
        and not any(r["eti_status"] == "UNRESOLVED_ETI_CANDIDATE" for r in vet)
    )
    checks.append(("N10_5_STAGE3_VETTING_ZERO_ETI", c5, f"vetted={len(vet)}, verified_eti=0"))

    # N10_6: Bayesian zero-ETI prevalence bounds & physical EIRP limits
    bl = s2["provisional_zero_eti_bayesian_bounds"]
    c6 = (
        abs(bl["stars_raw_6"]["jeffreys_f95_pct"] - 26.4173) < 1e-3
        and abs(bl["stars_eff"]["jeffreys_f95_pct"] - 28.6813) < 1e-3
        and abs(bl["star_tiles_eff"]["jeffreys_f95_pct"] - 0.0751) < 1e-3
        and 100.0 <= s2["median_eirp_w1_gw"] <= 1000.0
    )
    checks.append(("N10_6_BAYESIAN_NULL_LIMITS", c6, f"star_eff={bl['stars_eff']['jeffreys_f95_pct']}%, tile_eff={bl['star_tiles_eff']['jeffreys_f95_pct']}%"))

    # N10_7: 6 PNGs & visual review SHA parity
    figs = [
        "figN10_01_lband_rfi_landscape_and_eirp.png",
        "figN10_02_head_to_head_blindspot_benchmark.png",
        "figN10_03_abacad_real_waterfalls.png",
        "figN10_04_entropy_kurtosis_and_ac2d_diagnostics.png",
        "figN10_05_vetting_funnel_and_bayesian_f95.png",
        "figN10_06_milky_way_blindspot_synthesis.png",
    ]
    fig_sync = all(
        (WS / "figures" / f).exists() and (GIT_PROG / "figures" / f).exists()
        and sha256_file(WS / "figures" / f) == sha256_file(GIT_PROG / "figures" / f)
        for f in figs
    )
    c7 = fig_sync and vr.get("status") == "PASSED" and len(vr.get("figures_reviewed", [])) == 6
    checks.append(("N10_7_FIGURES_AND_VISUAL_REVIEW", c7, f"fig_sync={fig_sync}, review={vr.get('status')}"))

    # N10_8: Synced reports/scripts/results, no raw .h5 or setisearch/reports/, <48 MB
    r_ws = WS / "RESULTS_REPORT.md"
    r_gp = GIT_PROG / "RESULTS_REPORT.md"
    r_dc = GIT_REPO / "docs/N10_BL_RADIO_BLINDSPOT_ABACAD_REPORT.md"
    r_rt = ROOT / "reports/N10_BL_RADIO_BLINDSPOT_ABACAD_REPORT.md"
    rep_hashes = {sha256_file(p) for p in (r_ws, r_gp, r_dc, r_rt) if p.exists()}
    scr_ok = all(
        (GIT_PROG / "scripts" / s).exists() and sha256_file(WS / "scripts" / s) == sha256_file(GIT_PROG / "scripts" / s)
        for s in ("n10_radio_blindspot_analyzer.py", "stage1_n10_acquire_bl_abacad.py", "stage3_n10_forensic_vetting.py", "plot_n10_figures.py", "audit_n10_radio_blindspot.py")
    )
    res_ok = all(
        (GIT_PROG / "results" / p.name).exists() and sha256_file(p) == sha256_file(GIT_PROG / "results" / p.name)
        for p in res.iterdir() if p.is_file()
    )
    h5_in_git = list(GIT_REPO.rglob("*.h5"))
    oversized = [str(p.relative_to(GIT_REPO)) for p in list(GIT_PROG.rglob("*")) + [r_dc] if p.is_file() and p.stat().st_size >= 48 * 1024 * 1024]
    c8 = len(rep_hashes) == 1 and all(p.exists() for p in (r_ws, r_gp, r_dc, r_rt)) and scr_ok and res_ok and not (GIT_REPO / "reports").exists() and not h5_in_git and not oversized
    checks.append(("N10_8_REPORTS_AND_GIT_PROG", c8, f"rep_sync={len(rep_hashes)==1}, scr_ok={scr_ok}, res_ok={res_ok}, h5_in_git={len(h5_in_git)}"))

    # N10_9: Docs & continuation markdown
    c9 = (
        (ROOT / "FORTSAET_FRA_N10_BL_RADIO_BLINDSPOT.md").exists()
        and "N10_BL_RADIO_BLINDSPOT_ABACAD_REPORT.md" in (GIT_REPO / "README.md").read_text(encoding="utf-8")
        and "N10_BL_RADIO_BLINDSPOT_ABACAD_REPORT.md" in (GIT_REPO / "CONTINUE_SETI.md").read_text(encoding="utf-8")
    )
    checks.append(("N10_9_DOCS_UPDATED", c9, f"docs_ok={c9}"))

    # N10_10: Continuation ledger (len == 514, invariants preserved)
    led = json.loads((ROOT / "SETI_ACTIVE_CONTINUATION.json").read_text(encoding="utf-8"))
    n10_led = led.get("n10_bl_radio_blindspot_abacad_completed", {})
    c10 = (
        len(led) == 514
        and led.get("active_phase") == "D097"
        and led.get("current_table_cells") == 107105
        and led.get("old90_and_Rubin_stay_stopped") is True
        and "updated_utc" not in led
        and "n9_gaia_dr3_dark_companion_completed" in led
        and n10_led.get("verified_eti_candidates") == 0
        and n10_led.get("external_contacts") == 0
    )
    checks.append(("N10_10_CONTINUATION_LEDGER", c10, f"len={len(led)}, ext={n10_led.get('external_contacts')}"))

    # N10_11: ZIP integrity
    zip_ok = False
    z_members = 0
    if ZIP_PATH.exists():
        with zipfile.ZipFile(ZIP_PATH, "r") as zf:
            names = set(zf.namelist())
            z_members = len(names)
            zip_ok = (zf.testzip() is None) and {"RESULTS_REPORT.md", "results/METHOD_LOCK.json", "results/N10_ANALYZER_SUMMARY.json", "results/N10_STAGE3_VETTING.json", "results/VISUAL_REVIEW_N10.json"}.issubset(names)
    checks.append(("N10_11_LOCAL_ZIP_ARCHIVE", zip_ok, f"zip_ok={zip_ok}, members={z_members}"))

    # N10_12: Sealed regression across N9 (1..9, 11), N8 (12/12), N3 (12/12), Spor 5 (12/12)
    r_n9 = subprocess.run(["/usr/bin/python3", "-S", str(ROOT / "analysis_workspace/work_n9_20261127_gaia_dr3_dark_companions/scripts/audit_n9_gaia_dark_companions.py")], capture_output=True, text=True)
    n9_ok = all(f"[PASS] N9_{i}_" in r_n9.stdout for i in (1, 2, 3, 4, 5, 6, 7, 8, 9, 11))
    r_n8 = subprocess.run(["/usr/bin/python3", "-S", str(ROOT / "analysis_workspace/work_n8_20261127_galactic_center_and_pulsars/scripts/audit_n8_galactic_center.py")], capture_output=True, text=True)
    r_n3 = subprocess.run(["/usr/bin/python3", "-S", str(ROOT / "analysis_workspace/work_n3_20261127_rubin_v3_1800ddf/scripts/audit_n3_rubin_v3.py")], capture_output=True, text=True)
    r_sp5 = subprocess.run(["/usr/bin/python3", "-S", str(GIT_REPO / "zenodo_package/verify_publication_package.py"), "--archives-dir", str(ROOT / "archives")], capture_output=True, text=True)
    c12 = n9_ok and ("12/12 PASSED" in r_n8.stdout) and ("12/12 PASSED" in r_n3.stdout) and ("12/12 PASSED" in r_sp5.stdout)
    checks.append(("N10_12_REGRESSION_N9_TO_SPOR5", c12, f"n9_ok={n9_ok}, n8_rc={r_n8.returncode}, n3_rc={r_n3.returncode}, sp5_rc={r_sp5.returncode}"))

    passed = sum(1 for _, ok, _ in checks if ok)
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\nN10_RADIO_BLINDSPOT_AUDIT: {passed}/{len(checks)} PASSED")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
