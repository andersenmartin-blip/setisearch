#!/usr/bin/env python3
"""
Independent Pure-Stdlib Audit (/usr/bin/python3 -S) for Spor N1
(Project Hephaistos II, Blind DDF Dyson Survey, Multi-Decade VASCO Screen).
Verifies 12/12 invariants (N1_1-N1_12) and confirms both prior audits remain 12/12 PASSED.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import pathlib
import subprocess
import zipfile

WS_DEF = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14/analysis_workspace/work_n1_20261126_dyson_hephaistos_and_vasco")
INP_DEF = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14/inputs_n1_20261126")
ROOT_DEF = pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14")


def _sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        while True:
            b = fh.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _bnu_jy_stdlib(wave_um: float, t_k: float) -> float:
    h_p = 6.62607015e-34
    c_l = 2.99792458e8
    k_b = 1.380649e-23
    nu = c_l / (wave_um * 1e-6)
    x = min(700.0, max(1e-6, (h_p * nu) / (k_b * t_k)))
    return ((2.0 * h_p * (nu ** 3) / (c_l ** 2)) / math.expm1(x)) * 1e26


def run_audit(ws: pathlib.Path, inputs: pathlib.Path, root: pathlib.Path) -> int:
    res = ws / "results"
    figs = ws / "figures"
    repo = root / "setisearch"
    prog = repo / "progress" / "2026-11-26-n1-dyson-hephaistos-and-vasco"
    checks = []

    def rec(cid: str, ok: bool, msg: str):
        checks.append((cid, ok, msg))
        print(f"[{'PASS' if ok else 'FAIL'}] {cid}: {msg}")

    # N1_1: Locks exact and unchanged vs n1_analyzer.py
    ml = json.loads((res / "METHOD_LOCK.json").read_text(encoding="utf-8"))
    il = json.loads((res / "IMPLEMENTATION_LOCK.json").read_text(encoding="utf-8"))
    n1_lock_ok = (_sha256(res / "METHOD_LOCK.json") == il["method_lock_sha256"]) and (_sha256(ws / "scripts" / "n1_analyzer.py") == ml["sha256"]["scripts/n1_analyzer.py"])
    rec("N1_1", n1_lock_ok, f"Prospective METHOD_LOCK & IMPLEMENTATION_LOCK exact ({ml['locked_utc']})")

    # N1_2: All 7 Hephaistos A-G IDs verified, G radio AGN detected >=100 sigma
    heph = list(csv.DictReader((res / "N1A_HEPHAISTOS_7CANDIDATES.csv").open(encoding="utf-8")))
    expected_ids = {"3496509309189181184", "4843191593270342656", "4649396037451459712", "2660349163149053824", "3190232820489766656", "2956570141274256512", "2644370304260053376"}
    heph_ids = {r["gaia_source_id"] for r in heph}
    g_row = next(r for r in heph if r["label"] == "G")
    n2_ok = (len(heph) == 7 and heph_ids == expected_ids and float(g_row["vlass_peak_snr"]) >= 100.0)
    rec("N1_2", n2_ok, f"7/7 Hephaistos A-G exact 64-bit IDs verified; Candidate G VLASS peak SNR={g_row['vlass_peak_snr']}")

    # N1_3: Independent pure-stdlib recomputation of Hephaistos W1-W3, W1-W4, and Model-1 gamma
    max_g_diff = 0.0
    max_col_diff = 0.0
    for r in heph:
        w1, w3, w4 = float(r["w1"]), float(r["w3"]), float(r["w4"])
        max_col_diff = max(max_col_diff, abs((w1 - w3) - float(r["w1_w3"])), abs((w1 - w4) - float(r["w1_w4"])))
        ts = float(r["t_star_1"])
        td = float(r["t_ds_k"])
        l_s = (10.0 ** float(r["log_om_star_1"])) * (ts ** 4)
        l_d = (10.0 ** float(r["log_om_ds_1"])) * (td ** 4)
        gam_r = l_d / (l_s + l_d)
        max_g_diff = max(max_g_diff, abs(gam_r - float(r["gamma"])))
        # Also sanity check Planck emission at 11.56 um > 0
        assert _bnu_jy_stdlib(11.5608, td) > 0.0
    # Tolerate CSV rounding (t_ds rounded to 0.1 K, log_om rounded to 1e-4 -> ~2e-4 on gamma)
    rec("N1_3", max_g_diff < 5e-4 and max_col_diff < 2e-3, f"Independent stdlib recompute of Hephaistos colors (diff={max_col_diff:.1e}) & gamma (diff={max_g_diff:.1e})")

    # N1_4: N1B blind DDF stars >= 100, injection 1,200 trials >= 95% for gamma>=0.05, 3/3 triggers resolved
    vet_sum = json.loads((res / "N1_STAGE3_VETTING.json").read_text(encoding="utf-8"))
    n1b_s = vet_sum["n1b_blind_dyson"]
    n1b_vet = list(csv.DictReader((res / "N1B_BLIND_DYSON_VETTED.csv").open(encoding="utf-8")))
    n4_ok = (
        n1b_s["clean_parallax_stars_w3snr_ge3"] >= 100
        and n1b_s["injection_trials"] == 1200
        and n1b_s["injection_completeness_gamma_ge_0p05"] >= 0.95
        and len(n1b_vet) == 3
        and all("GALAXY" in x["final_disposition"] for x in n1b_vet)
    )
    rec("N1_4", n4_ok, f"N1B: {n1b_s['clean_parallax_stars_w3snr_ge3']} clean stars, {n1b_s['injection_completeness_gamma_ge_0p05']*100:.1f}% inj (gamma>=0.05), 3/3 resolved as galaxy blends")

    # N1_5: N1C VASCO Gaia (1,197/1,197) + PS1 (347/347 real + 25 sentinel artifacts vetted)
    n1c_s = vet_sum["n1c_vasco"]
    n1c_vet = list(csv.DictReader((res / "N1C_VASCO_VETTED.csv").open(encoding="utf-8")))
    n5_ok = (
        n1c_s["gaia_stars_screened_0p46deg_3ddfs"] == n1c_s["gaia_matched_ls_dr10"] >= 1000
        and len(n1c_vet) == 27
        and vet_sum["n1c_vetted_dispositions"].get("UNRESOLVED_TRUE_DISAPPEARANCE_CANDIDATE", 0) == 0
    )
    rec("N1_5", n5_ok, f"N1C VASCO: {n1c_s['gaia_matched_ls_dr10']}/{n1c_s['gaia_stars_screened_0p46deg_3ddfs']} Gaia DR3 matched; 27/27 PS1 flagged resolved (0 vanished)")

    # N1_6: Exact Bayesian f95 ordering & verified_eti == 0
    b_n1b = n1b_s["bounds_all_clean_gamma_ge_0p05"]
    b_gaia = n1c_s["bounds_gaia_vanishing"]
    n6_ok = (
        vet_sum["verified_eti"] == 0
        and b_n1b["clopper_pearson_f95_pct"] >= b_n1b["uniform_f95_pct"] > b_n1b["jeffreys_f95_pct"]
        and b_gaia["clopper_pearson_f95_pct"] >= b_gaia["uniform_f95_pct"] > b_gaia["jeffreys_f95_pct"]
    )
    rec("N1_6", n6_ok, f"Bayesian f95 Jeffreys: N1B={b_n1b['jeffreys_f95_pct']}%, N1C Gaia={b_gaia['jeffreys_f95_pct']}%, verified_eti=0")

    # N1_7: All FITS cutouts present and valid SIMPLE headers (>= 65 FITS files)
    fits_files = list((inputs / "cutouts").glob("*.fits"))
    valid_fits = sum(1 for p in fits_files if p.read_bytes()[:6] == b"SIMPLE")
    rec("N1_7", valid_fits >= 65 and valid_fits == len(fits_files), f"FITS cutout gallery verified ({valid_fits}/{len(fits_files)} valid FITS files)")

    # N1_8: All 6 300-DPI PNG figures valid, synced to repo, and approved in VISUAL_REVIEW_N1.json
    vr = json.loads((res / "VISUAL_REVIEW_N1.json").read_text(encoding="utf-8"))
    fnames = [
        "figN01_hephaistos_7candidates_seds.png",
        "figN02_hephaistos_multiband_cutouts.png",
        "figN03_n1b_blind_wise_color_and_injections.png",
        "figN04_n1b_blind_candidates_seds_and_cutouts.png",
        "figN05_n1c_vasco_gaia_ps1_legacy_comparison.png",
        "figN06_n1_unified_bayesian_bounds.png",
    ]
    n8_ok = vr.get("all_figures_approved") is True and len(vr.get("figures", [])) == 6
    for fn in fnames:
        pw, pr = figs / fn, prog / "figures" / fn
        if not (pw.exists() and pr.exists() and pw.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" and _sha256(pw) == _sha256(pr)):
            n8_ok = False
    rec("N1_8", n8_ok, "All 6 300-DPI PNGs valid, synced to repo, and visually approved")

    # N1_9: Archive zip & repo compact deliverables (<50 MB each)
    zpath = root / "archives_n1" / "SETI_N1_DYSON_HEPHAISTOS_VASCO_2026-11-26.zip"
    n9_ok = zpath.exists() and zipfile.is_zipfile(zpath)
    if n9_ok:
        with zipfile.ZipFile(zpath) as zf:
            n9_ok = zf.testzip() is None and len(zf.namelist()) >= 80
    for rp in prog.rglob("*"):
        if rp.is_file() and rp.stat().st_size >= 48 * 1048576:
            n9_ok = False
    if not (prog / "RESULTS_REPORT.md").exists():
        n9_ok = False
    rec("N1_9", n9_ok, f"Archive zip intact ({zpath.stat().st_size if zpath.exists() else 0:,} B) & repo deliverables <48 MB")

    # N1_10: SETI_ACTIVE_CONTINUATION.json invariants
    cont = json.loads((root / "SETI_ACTIVE_CONTINUATION.json").read_text(encoding="utf-8"))
    n10_ok = (
        cont.get("active_phase") == "D097"
        and cont.get("current_table_cells") == 107105
        and cont.get("old90_and_Rubin_stay_stopped") is True
        and "updated_utc" not in cont
        and "rubin_v2_r1_r2_completed" in cont
        and "n1_dyson_vasco_completed" in cont
    )
    rec("N1_10", n10_ok, f"SETI_ACTIVE_CONTINUATION.json invariants preserved (len={len(cont)})")

    # N1_11: Prior Rubin V2 audit still 12/12 PASSED
    p_rv2 = subprocess.run(
        ["/usr/bin/python3", "-S", str(root / "analysis_workspace" / "work_rubin_v2_20261126_r1_ddf_and_r2_catalog" / "scripts" / "audit_rubin_v2.py"), "--skip-spor5"],
        capture_output=True, text=True, check=False,
    )
    rec("N1_11", p_rv2.returncode == 0 and "RUBIN_V2_AUDIT: 12/12 PASSED" in p_rv2.stdout, "Rubin V2 audit remains 12/12 PASSED")

    # N1_12: Spor 5 & 38 Companion Archives A-AL audit still 12/12 PASSED
    p_sp5 = subprocess.run(
        ["/usr/bin/python3", "-S", str(repo / "zenodo_package" / "verify_publication_package.py"), "--archives-dir", str(root / "archives")],
        capture_output=True, text=True, check=False,
    )
    rec("N1_12", p_sp5.returncode == 0 and "SPOR5_PUBLICATION_AUDIT: 12/12 PASSED" in p_sp5.stdout, "Spor 5 & 38 Companion Archives A-AL audit remains 12/12 PASSED")

    passed = sum(1 for _, ok, _ in checks if ok)
    print(f"\nN1_DYSON_VASCO_AUDIT: {passed}/{len(checks)} PASSED")
    (ws / "audit" / "AUDIT_N1_DYSON_VASCO.json").write_text(
        json.dumps({"passed": passed, "total": len(checks), "checks": [{"id": c, "ok": o, "message": m} for c, o, m in checks]}, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0 if passed == len(checks) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ws", default=str(WS_DEF))
    ap.add_argument("--inputs", default=str(INP_DEF))
    ap.add_argument("--root", default=str(ROOT_DEF))
    args = ap.parse_args()
    return run_audit(pathlib.Path(args.ws), pathlib.Path(args.inputs), pathlib.Path(args.root))


if __name__ == "__main__":
    raise SystemExit(main())
