#!/usr/bin/env python3
"""
Pure-stdlib 12-check audit for Spor N4 (SPOR_N4_LOWFREQ_RADIO_BRIDGE_1083).
Compatible with /usr/bin/python3 -S.
"""
from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import subprocess
import sys
import zipfile

ROOT = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = ROOT / "analysis_workspace" / "work_n4_20261127_lowfreq_radio_bridge_1083"
INP = ROOT / "inputs_n4_20261127"
RES = WS / "results"
GIT_REPO = ROOT / "setisearch"
GIT_PROG = GIT_REPO / "progress" / "2026-11-27-n4-lowfreq-radio-bridge-1083"
ZIP_PATH = ROOT / "archives_n4" / "SETI_N4_LOWFREQ_RADIO_BRIDGE_1083_2026-11-27.zip"
LEDGER = ROOT / "SETI_ACTIVE_CONTINUATION.json"


def sha256(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    # N4_1: Lock integrity & prospective precedence
    an_p = WS / "scripts" / "n4_radio_analyzer.py"
    ml_p = RES / "METHOD_LOCK.json"
    ml = json.loads(ml_p.read_text(encoding="utf-8"))
    il = json.loads((RES / "IMPLEMENTATION_LOCK.json").read_text(encoding="utf-8"))
    an_s = json.loads((RES / "N4_ANALYZER_SUMMARY.json").read_text(encoding="utf-8"))
    an_hash = sha256(an_p)
    ml_hash = sha256(ml_p)
    c1 = (
        ml.get("sha256", {}).get("scripts/n4_radio_analyzer.py") == an_hash
        and il.get("analyzer_sha256") == an_hash
        and il.get("method_lock_sha256") == ml_hash
        and an_s.get("analyzer_sha256") == an_hash
        and ml.get("locked_utc", "") < an_s.get("generated_utc", "")
    )
    checks.append(("N4_1_lock_integrity", c1, f"sha={an_hash[:12]}"))

    # N4_2: 1,083 stars >= 3 live surveys + non-empty ASTRON/CASDA/HEASARC/CHIME inputs
    req_inp = [
        INP / "astron" / "lolss_54mhz_matches.csv",
        INP / "astron" / "lotss_dr3_144mhz_matches.csv",
        INP / "astron" / "tgss_150mhz_matches.csv",
        INP / "casda" / "racs_low_888mhz_matches.csv",
        INP / "casda" / "racs_mid_1367mhz_matches.csv",
        INP / "heasarc" / "nvss_1400mhz_matches.csv",
        INP / "heasarc" / "first_1400mhz_matches.csv",
        INP / "heasarc" / "sumss_843mhz_matches.csv",
        INP / "heasarc" / "vlssr_74mhz_matches.csv",
        INP / "chime" / "chime_frb_cat1.tsv",
    ]
    non_empty_all = all(p.exists() and len(p.read_text(encoding="utf-8", errors="replace").splitlines()) > 3 for p in req_inp)
    c2 = (
        an_s.get("master_stars_total") == 1083
        and an_s.get("science_stars") == 787
        and an_s.get("within_10pc_stars") == 267
        and an_s.get("min_covering_surveys_per_star", 0) >= 3
        and non_empty_all
    )
    checks.append(("N4_2_all_1083_live_coverage", c2, f"min_cov={an_s.get('min_covering_surveys_per_star')}, non_empty={non_empty_all}"))

    # N4_3: Panchromatic span >= 71.9 EM octaves
    span = an_s.get("panchromatic_span", {})
    c3 = span.get("lowest_freq_mhz") == 54.0 and span.get("em_octaves", 0.0) >= 71.9
    checks.append(("N4_3_panchromatic_71_9_octaves", c3, f"octaves={span.get('em_octaves')}"))

    # N4_4: 1,200 synthetic radio injections (100% >= 2 mJy)
    c4 = an_s.get("injection_trials_total") == 1200 and an_s.get("injection_completeness_s_ge_2mjy") == 1.0
    checks.append(("N4_4_injections_1200", c4, f"comp>=2mJy={an_s.get('injection_completeness_s_ge_2mjy')}"))

    # N4_5: >= 40 valid VLASS 1.2 FITS cutouts on disk + photometry CSV
    fits_files = sorted((INP / "vlass_cutouts").glob("*.fits"))
    valid_fits = sum(1 for p in fits_files if p.stat().st_size > 4096 and p.read_bytes()[:6] == b"SIMPLE")
    vlass_csv_rows = list(csv.DictReader((RES / "N4_VLASS_CUTOUT_PHOTOMETRY.csv").open(encoding="utf-8")))
    c5 = valid_fits >= 40 and len(vlass_csv_rows) == valid_fits
    checks.append(("N4_5_vlass_fits_cutouts", c5, f"valid_fits={valid_fits}"))

    # N4_6: Stage 3 vetting complete, verified_eti == 0, CHIME overlaps 100% DM-vetoed
    s3 = json.loads((RES / "N4_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    ch_rows = list(csv.DictReader((RES / "N4_CHIME_FRB_VETTED.csv").open(encoding="utf-8")))
    c6 = (
        s3.get("verified_eti_candidates") == 0
        and s3.get("chime_frb_verified_stellar_associations") == 0
        and len(ch_rows) == an_s.get("chime_frb_ellipse_overlaps")
        and all(r["eti_status"] == "VETOED_EXTRAGALACTIC_FRB" and r["veto_reason"] != "MANUAL_CHECK" for r in ch_rows)
    )
    checks.append(("N4_6_stage3_zero_eti_and_chime", c6, f"eti={s3.get('verified_eti_candidates')}, chime={len(ch_rows)}"))

    # N4_7: Bayesian zero-ETI bounds consistency
    bl = an_s.get("bayesian_limits_zero_eti", {})
    c7 = (
        0.15 < bl.get("all_1083_stars_s_ge_2mjy", {}).get("jeffreys_f95_pct", 99) < 0.25
        and 0.20 < bl.get("science_787_stars_s_ge_2mjy", {}).get("jeffreys_f95_pct", 99) < 0.30
        and bl.get("all_1083_stars_s_ge_2mjy", {}).get("jeffreys_f95_pct", 99) < bl.get("all_1083_stars_s_ge_2mjy", {}).get("uniform_f95_pct", 0)
    )
    checks.append(("N4_7_bayesian_limits", c7, f"f95_1083_J={bl.get('all_1083_stars_s_ge_2mjy', {}).get('jeffreys_f95_pct')}%"))

    # N4_8: All 6 PNGs in WS and git + VISUAL_REVIEW_N4 PASSED
    vr = json.loads((RES / "VISUAL_REVIEW_N4.json").read_text(encoding="utf-8"))
    pngs = [
        "figN4_01_panchromatic_em_ladder_72oct.png",
        "figN4_02_allsky_radio_coverage_1083.png",
        "figN4_03_eirp_sensitivity_vs_distance.png",
        "figN4_04_vlass_cutouts_and_vetting_funnel.png",
        "figN4_05_injection_completeness_and_bayesian_f95.png",
        "figN4_06_spectral_index_and_chime_dm_veto.png",
    ]
    c8 = (
        vr.get("status") == "PASSED"
        and all(vr.get("figures", {}).get(f, {}).get("status") == "PASSED" for f in pngs)
        and all((WS / "figures" / f).exists() and (GIT_PROG / "figures" / f).exists() for f in pngs)
    )
    checks.append(("N4_8_figures_and_visual_review", c8, f"pngs=6/6"))

    # N4_9: Report synced across WS, progress, docs, ROOT/reports + FORTSAET file
    r_ws = WS / "RESULTS_REPORT.md"
    r_pr = GIT_PROG / "RESULTS_REPORT.md"
    r_dc = GIT_REPO / "docs" / "N4_LOWFREQ_RADIO_BRIDGE_1083_REPORT.md"
    r_rp = ROOT / "reports" / "N4_LOWFREQ_RADIO_BRIDGE_1083_REPORT.md"
    f_hd = ROOT / "FORTSAET_FRA_N4_RADIO_BRIDGE_1083.md"
    c9 = (
        r_ws.exists() and r_pr.exists() and r_dc.exists() and r_rp.exists() and f_hd.exists()
        and r_ws.read_text(encoding="utf-8") == r_pr.read_text(encoding="utf-8") == r_dc.read_text(encoding="utf-8") == r_rp.read_text(encoding="utf-8")
    )
    checks.append(("N4_9_reports_synced", c9, "ws=progress=docs=reports"))

    # N4_10: Continuation ledger len == 508 + strict invariants preserved
    led = json.loads(LEDGER.read_text(encoding="utf-8"))
    req_prior = ("rubin_v2_r1_r2_completed", "n1_dyson_vasco_completed", "n2_rubin_iso_sso_trails_completed", "n3_rubin_v3_1800_completed", "n4_lowfreq_radio_bridge_completed")
    c10 = (
        len(led) == 508
        and led.get("active_phase") == "D097"
        and led.get("current_table_cells") == 107105
        and led.get("old90_and_Rubin_stay_stopped") is True
        and "updated_utc" not in led
        and all(k in led for k in req_prior)
    )
    checks.append(("N4_10_ledger_len_508", c10, f"len={len(led)}"))

    # N4_11: Local zip archive valid + all Spor N4 setisearch deliverables < 48 MB
    zip_ok = False
    if ZIP_PATH.exists():
        with zipfile.ZipFile(ZIP_PATH, "r") as zf:
            zip_ok = zf.testzip() is None and len(zf.namelist()) >= 80
    n4_repo_files = list(GIT_PROG.rglob("*")) + [GIT_REPO / "docs" / "N4_LOWFREQ_RADIO_BRIDGE_1083_REPORT.md"]
    oversized = [str(p.relative_to(GIT_REPO)) for p in n4_repo_files if p.is_file() and p.stat().st_size >= 48 * 1024 * 1024]
    c11 = zip_ok and not oversized
    checks.append(("N4_11_zip_and_size_limit", c11, f"zip_ok={zip_ok}, oversized_new={len(oversized)}"))

    # N4_12: Regression audits (N3 12/12 + Spor 5 12/12)
    r_n3 = subprocess.run(["/usr/bin/python3", "-S", str(ROOT / "analysis_workspace/work_n3_20261127_rubin_v3_1800ddf/scripts/audit_n3_rubin_v3.py")], capture_output=True, text=True)
    r_sp5 = subprocess.run(["/usr/bin/python3", "-S", str(GIT_REPO / "zenodo_package/verify_publication_package.py"), "--archives-dir", str(ROOT / "archives")], capture_output=True, text=True)
    c12 = ("12/12 PASSED" in r_n3.stdout) and ("12/12 PASSED" in r_sp5.stdout or r_sp5.returncode == 0)
    checks.append(("N4_12_regression_n3_spor5", c12, f"n3_rc={r_n3.returncode}, sp5_rc={r_sp5.returncode}"))

    passed = sum(1 for _, ok, _ in checks if ok)
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"\nN4_RADIO_BRIDGE_AUDIT: {passed}/{len(checks)} PASSED")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
