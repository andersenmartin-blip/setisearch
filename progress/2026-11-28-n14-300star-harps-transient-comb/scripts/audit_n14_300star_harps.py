#!/usr/bin/env python3
"""12-Point Pure-Stdlib Audit for Spor N14 (300-Star Unified HARPS Transient Laser & Comb)."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS14 = ROOT / "analysis_workspace/work_n14_20261128_300star_harps_transient_comb"
INP14 = ROOT / "inputs_n14_20261128"
REPO = ROOT / "setisearch"
GIT14 = REPO / "progress/2026-11-28-n14-300star-harps-transient-comb"
ZIP14 = ROOT / "archives_n14/SETI_N14_300STAR_HARPS_TRANSIENT_COMB_2026-11-28.zip"

EXPECTED_ANALYZER_SHA256 = "a122fd506f9511c16e0436d6e1462774c4092833c5e460fb548b2d7390e42dc7"
EXPECTED_METHOD_SHA256 = "eb0596ddb65c9fdf571845d733a7f46bc2ebc1ff891eafda9a4d5ed4f4c4fc6f"
EXPECTED_CATALOG_SHA256 = "e0039b7c426e386497812d165129a938a79687cfd2b27d98204893c31b4ac112"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def norm_name(s: str) -> str:
    return "".join(ch for ch in (s or "").upper() if ch.isalnum())


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def main() -> int:
    passed = 0

    def run_check(cid: str, fn) -> None:
        nonlocal passed
        fn()
        passed += 1
        print(f"[PASS] {cid}")

    # N14_1: Locks & SHA-256
    def c1() -> None:
        ml = json.loads((WS14 / "results/METHOD_LOCK.json").read_text(encoding="utf-8"))
        il = json.loads((WS14 / "results/IMPLEMENTATION_LOCK.json").read_text(encoding="utf-8"))
        check(il.get("pre_acquisition_blind_lock") is True, "IMPLEMENTATION_LOCK not blind")
        check(ml.get("locked_utc") == il.get("sealed_utc") and len(ml.get("primary_stars", [])) == 268, "METHOD_LOCK mismatch")
        check(il.get("analyzer_sha256") == EXPECTED_ANALYZER_SHA256, "impl analyzer sha mismatch")
        check(il.get("method_lock_sha256") == EXPECTED_METHOD_SHA256, "impl method sha mismatch")
        check(il.get("target_catalog_sha256") == EXPECTED_CATALOG_SHA256, "impl catalog sha mismatch")
        check(sha256_file(WS14 / "scripts/n14_300star_harps_streaming_analyzer.py") == EXPECTED_ANALYZER_SHA256, "analyzer modified")
        check(sha256_file(WS14 / "results/METHOD_LOCK.json") == EXPECTED_METHOD_SHA256, "METHOD_LOCK modified")
        check(sha256_file(INP14 / "n14_target_catalog.json") == EXPECTED_CATALOG_SHA256, "catalog modified")

    run_check("N14_1_locks_and_sealed_analyzer_sha256", c1)

    # N14_2: Catalog, receipts & zero overlap with N11B+N12
    def c2() -> None:
        s14 = json.loads((WS14 / "results/N14_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
        check(s14["stars_analyzed"] == 268, f"stars={s14['stars_analyzed']}")
        check(s14["epochs_analyzed"] == 2144, f"epochs={s14['epochs_analyzed']}")
        check(s14["unified_stars_total"] == 300, f"u_stars={s14['unified_stars_total']}")
        check(s14["unified_epochs_total"] == 2784, f"u_epochs={s14['unified_epochs_total']}")
        check(s14["unified_exoplanets_total"] == 508, f"u_planets={s14['unified_exoplanets_total']}")
        with (WS14 / "results/N14_STAR_SUMMARY.csv").open("r", encoding="utf-8") as fh:
            r14 = list(csv.DictReader(fh))
        with (INP14 / "n14_epoch_receipts.csv").open("r", encoding="utf-8") as fh:
            e14 = list(csv.DictReader(fh))
        check(len(r14) == 268, f"star_summary rows={len(r14)}")
        check(len(e14) == 2144, f"receipt rows={len(e14)}")
        with (ROOT / "analysis_workspace/work_n11b_20261128_harps_single_epoch_transient_laser/results/N11B_STAR_SUMMARY.csv").open("r", encoding="utf-8") as fh:
            n11_names = {norm_name(r["star"]) for r in csv.DictReader(fh)}
        with (ROOT / "analysis_workspace/work_n12_20261128_scaled_harps_transient_laser_comb/results/N12_STAR_SUMMARY.csv").open("r", encoding="utf-8") as fh:
            n12_names = {norm_name(r["star"]) for r in csv.DictReader(fh)}
        n14_names = {norm_name(r["star"]) for r in r14}
        check(len(n14_names & (n11_names | n12_names)) == 0, "overlap with N11B/N12")

    run_check("N14_2_catalog_receipts_and_zero_overlap", c2)

    # N14_3: Streaming RAM volume & zero bulk FITS saved
    def c3() -> None:
        s14 = json.loads((WS14 / "results/N14_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
        check(s14["total_fits_bytes_streamed"] == 11286069120, "bytes streamed mismatch")
        check(round(s14["total_fits_mib_streamed"], 2) == 10763.23, "MiB streamed mismatch")
        check(not any(WS14.rglob("*.fits")), "bulk FITS found in WS14")
        check(not any((WS14 / "results").glob("n14_checkpoint_*.jsonl")), "uncleaned checkpoints in WS14")

    run_check("N14_3_ram_streaming_and_zero_bulk_fits", c3)

    # N14_4: 1,200-trial injection benchmark
    def c4() -> None:
        s14 = json.loads((WS14 / "results/N14_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
        inj = s14["injections"]
        check(inj["trials_total"] == 1200, "trials != 1200")
        check(inj["laser_completeness"] == 0.9275, "T1 != 0.9275")
        check(inj["subthreshold_comb_completeness"] == 0.8875, "T2 != 0.8875")
        check(inj["classical_median_stack_completeness"] == 0.0, "classical != 0.0")
        check(inj["cosmic_ray_fpr"] == 0.0 and inj["broad_flare_fpr"] == 0.0, "nonzero FPR")
        with (WS14 / "results/N14_INJECTION_BENCHMARK.csv").open("r", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        check(len(rows) == 1200, f"inj csv rows={len(rows)}")

    run_check("N14_4_benchmark_1200_trials", c4)

    # N14_5: Stage 2 & Stage 3 vetting -> 0 ETI
    def c5() -> None:
        v14 = json.loads((WS14 / "results/N14_STAGE3_VETTING.json").read_text(encoding="utf-8"))
        check(v14["peaks_z10_before_shape_veto"] == 5472, "peaks != 5472")
        check(v14["stage2_triggers_vetted"] == 923, "triggers != 923")
        check(sum(v14["veto_breakdown"].values()) == 923, "veto sum != 923")
        check(v14["verified_eti_candidates"] == 0, "verified_eti != 0")
        check(v14["external_contacts"] == 0, "external_contacts != 0")
        with (WS14 / "results/N14_CANDIDATES_VETTED.csv").open("r", encoding="utf-8") as fh:
            vet = list(csv.DictReader(fh))
        check(len(vet) == 923, f"vetted csv rows={len(vet)}")
        check(all(r["eti_status"] != "UNRESOLVED_ETI_CANDIDATE" for r in vet), "unresolved row remains")

    run_check("N14_5_stage3_forensic_vetting_zero_eti", c5)

    # N14_6: Sub-1% Bayesian bounds
    def c6() -> None:
        s14 = json.loads((WS14 / "results/N14_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
        zb = s14["provisional_zero_eti_bayesian_bounds"]
        check(zb["unified_300stars_raw"]["jeffreys_f95_pct"] == 0.6377, "u300 raw J mismatch")
        check(zb["unified_300stars_eff"]["jeffreys_f95_pct"] == 0.6854, "u300 eff J mismatch")
        check(zb["unified_300stars_raw"]["uniform_f95_pct"] == 0.9903, "u300 raw U mismatch")
        check(zb["unified_2784epochs_eff"]["jeffreys_f95_pct"] == 0.0739, "u2784 ep eff J mismatch")

    run_check("N14_6_sub1pct_bayesian_bounds", c6)

    # N14_7: 6 PNGs + VISUAL_REVIEW_N14.json
    def c7() -> None:
        vr = json.loads((WS14 / "results/VISUAL_REVIEW_N14.json").read_text(encoding="utf-8"))
        check(vr.get("status") == "PASSED", "visual review not PASSED")
        figs = vr.get("figures_verified", [])
        check(len(figs) == 6, f"fig count={len(figs)}")
        for fn in figs:
            p = WS14 / "figures" / fn
            check(p.exists() and p.stat().st_size > 20_000, f"missing/small fig {fn}")

    run_check("N14_7_figures_and_visual_review", c7)

    # N14_8: 4 identical reports + continuation md
    def c8() -> None:
        paths = [
            WS14 / "RESULTS_REPORT.md",
            GIT14 / "RESULTS_REPORT.md",
            REPO / "docs/N14_300STAR_HARPS_TRANSIENT_LASER_COMB_REPORT.md",
            ROOT / "reports/N14_300STAR_HARPS_TRANSIENT_LASER_COMB_REPORT.md",
        ]
        digs = {sha256_file(p) for p in paths}
        check(len(digs) == 1, f"reports not byte-identical: {digs}")
        check((ROOT / "FORTSAET_FRA_N14_300STAR_HARPS_TRANSIENT.md").exists(), "missing FORTSAET_FRA_N14 md")

    run_check("N14_8_four_identical_reports", c8)

    # N14_9: README, CONTINUE_SETI, no setisearch/reports
    def c9() -> None:
        rd = (REPO / "README.md").read_text(encoding="utf-8")
        cs = (REPO / "CONTINUE_SETI.md").read_text(encoding="utf-8")
        check("| **20. Spor N14" in rd, "README missing Row 20")
        check("31. **Spor N14" in cs, "CONTINUE_SETI missing item 31")
        check(not (REPO / "reports").exists(), "forbidden setisearch/reports exists")

    run_check("N14_9_repo_index_updates", c9)

    # N14_10: SETI_ACTIVE_CONTINUATION.json invariants
    def c10() -> None:
        sc = json.loads((ROOT / "SETI_ACTIVE_CONTINUATION.json").read_text(encoding="utf-8"))
        check(len(sc) == 519, f"len={len(sc)} != 519")
        check(sc.get("active_phase") == "D097", "active_phase changed")
        check(sc.get("current_table_cells") == 107105, "current_table_cells changed")
        check(sc.get("old90_and_Rubin_stay_stopped") is True, "old90_and_Rubin_stay_stopped changed")
        check("updated_utc" not in sc, "forbidden updated_utc present")
        check(sc["n14_300star_harps_transient_comb_completed"]["stars_analyzed"] == 268, "n14 json block missing")

    run_check("N14_10_continuation_json_invariants", c10)

    # N14_11: WS14 vs GIT14 parity + git file hygiene + ZIP integrity
    def c11() -> None:
        for sub in ("scripts", "results", "figures"):
            ws_files = {p.name: sha256_file(p) for p in (WS14 / sub).iterdir() if p.is_file()}
            gt_files = {p.name: sha256_file(p) for p in (GIT14 / sub).iterdir() if p.is_file()}
            check(ws_files == gt_files, f"parity mismatch in {sub}")
        for p in GIT14.rglob("*"):
            if p.is_file():
                check(p.suffix.lower() not in {".fits", ".h5", ".npy", ".jsonl"}, f"forbidden ext in git: {p}")
                check(p.stat().st_size < 48 * 1024 * 1024, f"oversized git file: {p}")
        check(ZIP14.exists() and ZIP14.stat().st_size > 100_000, "ZIP14 missing")
        with zipfile.ZipFile(ZIP14, "r") as zf:
            check(zf.testzip() is None, "corrupt ZIP14")
            check(not any(n.lower().endswith(".fits") for n in zf.namelist()), "FITS inside ZIP14")

    run_check("N14_11_git_parity_hygiene_and_zip", c11)

    # N14_12: Non-recursive N13 audit checks (1..9, 11, 12; check 10 intentionally superseded by N14 len=519)
    def c12() -> None:
        n13_audit = ROOT / "analysis_workspace/work_n13_20261128_scaled_waterhole_plasma_dechirp_comb/scripts/audit_n13_scaled_waterhole.py"
        res = subprocess.run(["/usr/bin/python3", "-S", str(n13_audit)], capture_output=True, text=True)
        for i in (1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12):
            check(f"[PASS] N13_{i}_" in res.stdout, f"N13 check {i} failed")

    run_check("N14_12_n13_nonrecursive_regression", c12)

    print(f"\nN14_300STAR_HARPS_AUDIT: {passed}/12 PASSED")
    return 0 if passed == 12 else 1


if __name__ == "__main__":
    raise SystemExit(main())
