#!/usr/bin/env python3
"""Pure-stdlib 12-point audit for Spor N13 (SPOR_N13_SCALED_33STAR_WATERHOLE_PLASMA_DECHIRP_COMB)."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace/work_n13_20261128_scaled_waterhole_plasma_dechirp_comb"
INP = ROOT / "inputs_n13_20261128"
GIT_REPO = ROOT / "setisearch"
GIT_PROG = GIT_REPO / "progress/2026-11-28-n13-scaled-waterhole-plasma-dechirp-comb"
ZIP_PATH = ROOT / "archives_n13/SETI_N13_SCALED_WATERHOLE_BLINDSPOT_2026-11-28.zip"

EXPECTED_ANALYZER_SHA = "03638ed34550b8afb6ce6cd52da6e82482af21a4a8ae4c32bca4ac96c463e3e1"


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
    s2 = json.loads((res / "N13_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    s3 = json.loads((res / "N13_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    vr = json.loads((res / "VISUAL_REVIEW_N13.json").read_text(encoding="utf-8"))
    acq = json.loads((INP / "stage1_acquisition_log.json").read_text(encoding="utf-8"))

    # N13_1: Blind lock preserved & precedes Stage 1 acquisition and Stage 2 outputs
    an_sha = sha256_file(WS / "scripts/n13_scaled_waterhole_analyzer.py")
    ml_sha = sha256_file(res / "METHOD_LOCK.json")
    c1 = (
        an_sha == EXPECTED_ANALYZER_SHA
        and il.get("analyzer_sha256") == EXPECTED_ANALYZER_SHA
        and il.get("method_lock_sha256") == ml_sha
        and il.get("pre_acquisition_blind_lock") is True
        and ml.get("locked_utc", "") < acq.get("completed_utc", "")
        and ml.get("locked_utc", "") < s2.get("generated_utc", "")
    )
    checks.append(("N13_1_BLIND_LOCK", c1, f"sha_ok={an_sha == EXPECTED_ANALYZER_SHA}"))

    # N13_2: Stage 1 HTTP-Range waterhole slicing (144/144 scans across 24 non-N11A <9.1 pc stars)
    scans_csv = csv_rows(INP / "n13_waterhole_scans.csv")
    npy_count = len(list((INP / "slabs").rglob("*.npy")))
    n11a_targets = {"GJ411", "GJ65A", "GJ866", "GJ54.1", "GJ273", "GJ687", "GJ1245AC", "GJ1002", "HIP1242"}
    n13_targets = set(ml.get("targets_under_9_1pc_non_n11a", []))
    c2 = (
        acq.get("cadences") == 24
        and acq.get("scans_sliced") == 144
        and acq.get("bandwidth_saved_factor", 0) > 240.0
        and len(scans_csv) == 144
        and npy_count == 144
        and len(n13_targets) == 24
        and len(n13_targets & n11a_targets) == 0
    )
    checks.append(("N13_2_STAGE1_HTTP_RANGE", c2, f"scans={acq.get('scans_sliced')}/144, saved={acq.get('bandwidth_saved_factor')}x, overlap=0"))

    # N13_3: Stage 2 fine waterhole scan coverage (24/33 stars, 1,536/2,112 blocks, >=65 MHz new BW)
    cad_sum = csv_rows(res / "N13_CADENCE_SUMMARY.csv")
    trig = csv_rows(res / "N13_STAGE2_TRIGGERS.csv")
    c3 = (
        len(cad_sum) == 24
        and s2["stars_analyzed"] == 24
        and s2["unified_stars_total"] == 33
        and s2["blocks_clean_total"] == 1536
        and s2["unified_blocks_clean_total"] == 2112
        and s2["total_clean_bw_mhz"] >= 65.0
        and len(trig) == s2["stage2_triggers_total"] == 0
    )
    checks.append(("N13_3_STAGE2_COVERAGE", c3, f"stars=24(33), blks=1536(2112), bw={s2['total_clean_bw_mhz']}MHz, trig={len(trig)}"))

    # N13_4: 1,400-trial blind-spot v2 benchmark (G1/G2/G3 >= 90%, Classical 0%, Null FPR <= 2%)
    inj = s2["injections"]
    pm = inj["per_morphology"]
    c4 = (
        inj["trials_total"] == 1400
        and pm["GAJJAR_PLASMA_10_350HZ"]["n13_rate"] >= 0.90
        and pm["FINE_CURVED_ORBITAL"]["n13_rate"] >= 0.90
        and pm["FINE_HARMONIC_COMB"]["n13_rate"] >= 0.90
        and inj["classical_1bin_completeness"] == 0.0
        and inj["null_fpr"] <= 0.02
    )
    checks.append(("N13_4_V2_BLINDSPOT_BENCHMARK", c4, f"G1={pm['GAJJAR_PLASMA_10_350HZ']['n13_rate']*100:.2f}%, G2={pm['FINE_CURVED_ORBITAL']['n13_rate']*100:.2f}%, G3={pm['FINE_HARMONIC_COMB']['n13_rate']*100:.2f}%, FPR={inj['null_fpr']*100:.2f}%"))

    # N13_5: Stage 3 forensic vetting zero ETI
    vet = csv_rows(res / "N13_CANDIDATES_VETTED.csv")
    c5 = (
        len(vet) == s3["stage2_triggers_vetted"] == 0
        and s3["verified_eti_candidates"] == 0
        and s3["blocks_verified_quiet"] == 1536
    )
    checks.append(("N13_5_STAGE3_VETTING_ZERO_ETI", c5, f"quiet_blks={s3['blocks_verified_quiet']}, max_comb_rfi={s3['max_comb_on2_observed']}, eti=0"))

    # N13_6: Unified 33-star / 2,112-block Bayesian zero-ETI bounds & physical EIRP range
    bl = s2["provisional_zero_eti_bayesian_bounds"]
    c6 = (
        abs(bl["unified_33stars_raw"]["jeffreys_f95_pct"] - 5.6126) < 1e-3
        and abs(bl["unified_33stars_eff"]["jeffreys_f95_pct"] - 6.5490) < 1e-3
        and abs(bl["unified_2112blocks_eff"]["jeffreys_f95_pct"] - 0.1067) < 1e-3
        and 2.0 <= s2["min_eirp_w1_gw"] <= 4.0
        and 12.0 <= s2["median_eirp_w1_gw"] <= 25.0
    )
    checks.append(("N13_6_UNIFIED_33STAR_BAYESIAN_LIMITS", c6, f"33star_eff={bl['unified_33stars_eff']['jeffreys_f95_pct']}%, 2112blk_eff={bl['unified_2112blocks_eff']['jeffreys_f95_pct']}%"))

    # N13_7: 6 PNGs & visual review SHA parity
    figs = [
        "figN13_01_33star_waterhole_sample_and_eirp.png",
        "figN13_02_head_to_head_v2_benchmark.png",
        "figN13_03_iconic_star_abacad_waterfalls.png",
        "figN13_04_rfi_comb_and_stage3_diagnostics.png",
        "figN13_05_unified_33star_bayesian_f95.png",
        "figN13_06_milky_way_blindspot_pentalogy.png",
    ]
    fig_sync = all(
        (WS / "figures" / f).exists() and (GIT_PROG / "figures" / f).exists()
        and sha256_file(WS / "figures" / f) == sha256_file(GIT_PROG / "figures" / f)
        for f in figs
    )
    c7 = fig_sync and vr.get("status") == "PASSED" and len(vr.get("figures_reviewed", [])) == 6
    checks.append(("N13_7_FIGURES_AND_VISUAL_REVIEW", c7, f"fig_sync={fig_sync}, review={vr.get('status')}"))

    # N13_8: Synced reports/scripts/results, no .h5/.npy in repo or .fits in GIT_PROG, no setisearch/reports/, <48 MB
    r_ws = WS / "RESULTS_REPORT.md"
    r_gp = GIT_PROG / "RESULTS_REPORT.md"
    r_dc = GIT_REPO / "docs/N13_SCALED_33STAR_WATERHOLE_BLINDSPOT_REPORT.md"
    r_rt = ROOT / "reports/N13_SCALED_33STAR_WATERHOLE_BLINDSPOT_REPORT.md"
    rep_hashes = {sha256_file(p) for p in (r_ws, r_gp, r_dc, r_rt) if p.exists()}
    scr_ok = all(
        (GIT_PROG / "scripts" / s).exists() and sha256_file(WS / "scripts" / s) == sha256_file(GIT_PROG / "scripts" / s)
        for s in (
            "n13_scaled_waterhole_analyzer.py",
            "stage1_n13_fetch_waterhole_slices.py",
            "stage3_n13_forensic_vetting.py",
            "plot_n13_figures.py",
            "audit_n13_scaled_waterhole.py",
        )
    )
    res_ok = all(
        (GIT_PROG / "results" / p.name).exists() and sha256_file(p) == sha256_file(GIT_PROG / "results" / p.name)
        for p in res.iterdir() if p.is_file()
    )
    heavy_in_git = list(GIT_REPO.rglob("*.h5")) + list(GIT_REPO.rglob("*.npy")) + list(GIT_PROG.rglob("*.fits"))
    oversized = [str(p.relative_to(GIT_REPO)) for p in list(GIT_PROG.rglob("*")) + [r_dc] if p.is_file() and p.stat().st_size >= 48 * 1024 * 1024]
    c8 = len(rep_hashes) == 1 and all(p.exists() for p in (r_ws, r_gp, r_dc, r_rt)) and scr_ok and res_ok and not (GIT_REPO / "reports").exists() and not heavy_in_git and not oversized
    checks.append(("N13_8_REPORTS_AND_GIT_PROG", c8, f"rep_sync={len(rep_hashes)==1}, scr_ok={scr_ok}, res_ok={res_ok}, heavy={len(heavy_in_git)}"))

    # N13_9: Docs & continuation markdown
    c9 = (
        (ROOT / "FORTSAET_FRA_N13_SCALED_WATERHOLE_BLINDSPOT.md").exists()
        and "N13_SCALED_33STAR_WATERHOLE_BLINDSPOT_REPORT.md" in (GIT_REPO / "README.md").read_text(encoding="utf-8")
        and "N13_SCALED_33STAR_WATERHOLE_BLINDSPOT_REPORT.md" in (GIT_REPO / "CONTINUE_SETI.md").read_text(encoding="utf-8")
    )
    checks.append(("N13_9_DOCS_UPDATED", c9, f"docs_ok={c9}"))

    # N13_10: Continuation ledger (len == 518, invariants preserved)
    led = json.loads((ROOT / "SETI_ACTIVE_CONTINUATION.json").read_text(encoding="utf-8"))
    n13_led = led.get("n13_scaled_waterhole_blindspot_completed", {})
    c10 = (
        len(led) == 518
        and led.get("active_phase") == "D097"
        and led.get("current_table_cells") == 107105
        and led.get("old90_and_Rubin_stay_stopped") is True
        and "updated_utc" not in led
        and "n12_scaled_harps_transient_comb_completed" in led
        and n13_led.get("verified_eti_candidates") == 0
        and n13_led.get("external_contacts") == 0
    )
    checks.append(("N13_10_CONTINUATION_LEDGER", c10, f"len={len(led)}, ext={n13_led.get('external_contacts')}"))

    # N13_11: ZIP integrity
    zip_ok = False
    z_members = 0
    if ZIP_PATH.exists():
        with zipfile.ZipFile(ZIP_PATH, "r") as zf:
            names = set(zf.namelist())
            z_members = len(names)
            zip_ok = (zf.testzip() is None) and {
                "RESULTS_REPORT.md",
                "results/METHOD_LOCK.json",
                "results/N13_ANALYZER_SUMMARY.json",
                "results/N13_STAGE3_VETTING.json",
                "results/VISUAL_REVIEW_N13.json",
            }.issubset(names)
    checks.append(("N13_11_LOCAL_ZIP_ARCHIVE", zip_ok, f"zip_ok={zip_ok}, members={z_members}"))

    # N13_12: Non-recursive sealed regression across N12 (1..9, 11, 12) -> N11B -> N11A -> Spor 5
    r_n12 = subprocess.run(
        ["/usr/bin/python3", "-S", str(ROOT / "analysis_workspace/work_n12_20261128_scaled_harps_transient_laser_comb/scripts/audit_n12_scaled_harps.py")],
        capture_output=True,
        text=True,
    )
    n12_ok = all(f"[PASS] N12_{i}_" in r_n12.stdout for i in (1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12))
    checks.append(("N13_12_REGRESSION_N12_TO_SPOR5", n12_ok, f"n12_ok={n12_ok}, n12_rc={r_n12.returncode}"))

    passed = sum(1 for _, ok, _ in checks if ok)
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\nN13_SCALED_WATERHOLE_AUDIT: {passed}/{len(checks)} PASSED")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
