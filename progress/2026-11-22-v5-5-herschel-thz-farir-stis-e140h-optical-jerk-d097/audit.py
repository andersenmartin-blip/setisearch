#!/usr/bin/env /usr/bin/python3 -S
"""Pure Python Standard-Library Audit Suite for Phase D097 (V5.5) — 16/16 Independent Checks.

Zero third-party imports (must pass cleanly under `/usr/bin/python3 -S audit.py`).
"""

from __future__ import annotations

import base64
import csv
import gzip
import hashlib
import json
import math
import os
import pathlib
import sys
import zipfile
from typing import Any

WS = pathlib.Path(__file__).resolve().parent
ROOT = WS.parent.parent
RES = WS / "results"

# Exact physical constants matching v5_5_detector.py / D096 audit.py
C_KMS = 299792.458
C_ANGSTROM_PER_S = 2.99792458e18
C1_CGS = 1.1910429723971884e27  # 2 h c^2 in erg cm^-2 s^-1 A^-1 * A^5
C2_A_K = 1.4387768775039337e8   # h c / k_B in A * K
PC_TO_CM = 3.085677581491367e18
AU_TO_CM = 1.495978707e13
RSUN_CM = 6.957e10
FWHM_FACTOR = 2.3548200450309493
ZERO_FLUX_VEGA_G = 2.50e-9
ZERO_FLUX_2MASS_H = 1.133e-10
HIFI_APERTURE_JY_PER_K = 468.0


def _sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            b = fh.read(65536)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _planck_a(wave_a: float, teff_k: float) -> float:
    x = min(700.0, C2_A_K / max(1e-6, wave_a * max(100.0, teff_k)))
    return C1_CGS / ((wave_a ** 5) * math.expm1(x))


def _gaia_g_flam(wave_a: float, teff_k: float, g_mag: float) -> float:
    teff = max(1200.0, teff_k)
    b0 = _planck_a(6217.59, teff)
    return ZERO_FLUX_VEGA_G * (10.0 ** (-0.4 * g_mag)) * (_planck_a(wave_a, teff) / max(1e-300, b0))


def _twomass_h_flam(wave_a: float, teff_k: float, h_mag: float) -> float:
    teff = max(800.0, teff_k)
    b0 = _planck_a(16620.0, teff)
    return ZERO_FLUX_2MASS_H * (10.0 ** (-0.4 * h_mag)) * (_planck_a(wave_a, teff) / max(1e-300, b0))


def _pure_stdlib_pbeam_kw(row: dict[str, str]) -> float:
    anc = row["radiometric_anchor"]
    wa = float(row["wave_bary_a"])
    dist_pc = float(row["dist_pc"])
    teff = float(row["teff_k"])
    rp = float(row["resolving_power"])
    amp = float(row["amp_rel_8sigma_lim"])
    if anc in ("HERSCHEL_HIFI_DIRECT_CGS", "HERSCHEL_SPIRE_DIRECT_CGS", "HERSCHEL_PACS_DIRECT_CGS", "HST_STIS_DIRECT_CGS") or (row.get("direct_flam_cgs") or "").strip():
        cont_flam = float(row["direct_flam_cgs"])
    elif anc in ("GAIA_G_PLANCK", "GAIA_G_PLANCK_CGS"):
        cont_flam = _gaia_g_flam(wa, teff, float(row["phot_g_mag"]))
    elif anc in ("2MASS_H_PLANCK", "2MASS_H_PLANCK_CGS"):
        cont_flam = _twomass_h_flam(wa, teff, float(row["h_mag"]))
    else:
        flam_surf = math.pi * _planck_a(wa, teff)
        r_cm = 0.5 * RSUN_CM
        d_cm = max(dist_pc, 0.01) * PC_TO_CM
        cont_flam = flam_surf * ((r_cm / d_cm) ** 2)
    ew_a = math.sqrt(math.pi / (4.0 * math.log(2.0))) * amp * (wa / rp)
    flux_lim = cont_flam * ew_a
    d_cm = max(dist_pc, 0.01) * PC_TO_CM
    l_iso = 4.0 * math.pi * (d_cm ** 2) * flux_lim
    w_cm = wa * 1e-8
    g_10m = (math.pi * 1000.0 / w_cm) ** 2
    p_w = (l_iso / g_10m) * 1e-7
    return p_w / 1000.0


def _read_csv(name: str) -> list[dict[str, str]]:
    with (RES / name).open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def run_audit() -> tuple[int, int]:
    checks: list[tuple[str, bool, str]] = []

    def rec(cid: str, ok: bool, msg: str) -> None:
        checks.append((cid, ok, msg))
        print(f"  [{cid}] [{'PASS' if ok else 'FAIL'}] {msg}")

    ml = json.loads((WS / "METHOD_LOCK.json").read_text(encoding="utf-8"))
    lr = json.loads((WS / "LOCK_RECEIPT.json").read_text(encoding="utf-8"))
    dr = json.loads((WS / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json").read_text(encoding="utf-8"))
    pe = json.loads((WS / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    il = json.loads((WS / "IMPLEMENTATION_LOCK.json").read_text(encoding="utf-8"))
    sm = json.loads((RES / "SUMMARY.json").read_text(encoding="utf-8"))

    # C1: METHOD_LOCK & Chronology
    ml_sha = _sha256(WS / "METHOD_LOCK.json")
    c1 = (ml_sha == lr["method_lock_sha256"] and float(dr["chronology_lag_seconds"]) >= 3.0)
    rec("C1", c1, f"METHOD_LOCK sha256={ml_sha[:16]}..., lag={dr['chronology_lag_seconds']}s >= 3.0s")

    # C2: All 7 Stage-1 files byte-for-byte unmodified vs METHOD_LOCK.json
    st1_bad = []
    locked_s1 = ml["locked_file_hashes"]
    for k, meta in locked_s1.items():
        fp = WS / k
        exp = meta["sha256"] if isinstance(meta, dict) else meta
        if not fp.is_file() or _sha256(fp) != exp:
            st1_bad.append(k)
    rec("C2", len(st1_bad) == 0 and len(locked_s1) == 7, f"7 Stage-1 files unmodified (diffs={st1_bad})")

    # C3: IMPLEMENTATION_LOCK chains METHOD_LOCK + Stage-2 scripts + bounded bundle + results
    il_bad = []
    if il.get("method_lock_sha256") != ml_sha:
        il_bad.append("method_lock_sha256")
    for rel, exp in il.get("stage2_and_deliverable_files", {}).items():
        fp = WS / rel
        if not fp.is_file() or _sha256(fp) != exp:
            il_bad.append(rel)
    bnd_path = WS / "bounded_inputs" / "d097_bounded_bundle.json.gz"
    bnd_mib = bnd_path.stat().st_size / (1024.0 * 1024.0)
    rec("C3", not il_bad and bnd_mib <= 22.0, f"IMPLEMENTATION_LOCK verified ({len(il.get('stage2_and_deliverable_files', {}))} files, diffs={il_bad}); bundle={bnd_mib:.4f} MiB")

    # C4: Cohort prospective guarantees & zero prior overlap
    c4 = (
        int(pe["d097_dp_id_overlap_count"]) == 0
        and float(pe["min_brand_new_sky_separation_arcsec"]) >= 6000.0
        and int(pe["n_prior_excluded_coords"]) == 484
        and int(pe["n_prior_excluded_dp_ids"]) == 2806
    )
    rec("C4", c4, f"Zero overlap (0/{pe['n_prior_excluded_dp_ids']}), min_sep={pe['min_brand_new_sky_separation_arcsec']} arcsec")

    # C5 & C6: All 11 calibration suites (2,031 trials) & bounded bundle integrity
    cal = sm["synthetic_calibration_2031_trials"]
    cal_files = [
        ("CALIBRATION_V55_HERSCHEL_HIFI_180.csv", 180, 178),
        ("CALIBRATION_V55_SPIRE_PACS_180.csv", 180, 180),
        ("CALIBRATION_V55_HST_STIS_E140H_120.csv", 120, 120),
        ("CALIBRATION_V55_COHERENT_JERK_240.csv", 240, 240),
        ("CALIBRATION_G8_V55_120.csv", 120, 115),
        ("CALIBRATION_V55_RPCA_RARITY_180.csv", 180, 178),
        ("CALIBRATION_V55_AGNOSTIC_120.csv", 120, 115),
        ("DETECTOR_V55_G4G5_CALIBRATION_108.csv", 108, 108),
        ("COMB_V4_1_CALIBRATION_162.csv", 162, 162),
    ]
    c5_ok = int(cal["total_trials"]) == 2031
    tot_c = 0
    for fn, exp_n, min_p in cal_files:
        rows = _read_csv(fn)
        tot_c += len(rows)
        p_n = sum(1 for r in rows if r["passed"] == "1")
        if len(rows) != exp_n or p_n < min_p:
            c5_ok = False
    inj_rows = _read_csv("INJECTION_RECOVERY_540.csv")
    kep_rows = _read_csv("KEPLERIAN_TRACK_CALIBRATION_81.csv")
    tot_c += len(inj_rows) + len(kep_rows)
    if sum(1 for r in inj_rows if r["pass_p"] == "1") != 540 or sum(1 for r in kep_rows if r["kplanet_rec"] == "1") != 81:
        c5_ok = False
    rec("C5", c5_ok and tot_c == 2031, f"11 calibration suites: {tot_c}/2031 trials, G8={cal['g8_pass']}, RPCA={cal['rpca_pass']}")

    with gzip.open(bnd_path, "rt", encoding="utf-8") as gz:
        bnd_obj = json.load(gz)
    c6 = len(bnd_obj["exposures"]) == 78 and int(sm["unified_448star_panchromatic_v5_5_synthesis"]["total_calibration_trials_d079_d097"]) == 39942
    rec("C6", c6, f"Bounded bundle exposures={len(bnd_obj['exposures'])}, cumulative trials=39942")

    # C7: Stream 1 Space (HIFI, SPIRE, PACS, STIS E140H) -> 45 qualified -> 0 ETI
    spc = _read_csv("V5_5_SPACE_CANDIDATE_LEDGER.csv")
    n_sq = sum(1 for r in spc if r["qualified_v55"] == "True")
    n_sv = sum(1 for r in spc if r["verified_eti"] == "True")
    c7 = (len(spc) == 131 and n_sq == 45 and n_sv == 0)
    rec("C7", c7, f"Space HIFI/SPIRE/PACS/STIS: {len(spc)} raw -> {n_sq} qualified -> {n_sv} verified ETI")

    # C8: Stream 2 Optical FEROS/HARPS + Orbits #139-#140 -> 0 ETI
    fg = _read_csv("FOUR_GEN_BENCHMARK_D097.csv")
    orb = _read_csv("ORBITAL_CAMPAIGN_RESULTS_2.csv")
    opt = _read_csv("V5_5_CANDIDATE_LEDGER.csv")
    c8 = (
        sum(int(r["g1_seeds"]) for r in fg) == 771
        and sum(int(r["g8_pass"]) for r in fg) == 241
        and sum(int(r["stage2_verified_eti"]) for r in fg) == 0
        and len(orb) == 2
        and sum(int(r["verified_eti"]) for r in orb) == 0
        and sum(1 for r in opt if r["verified_eti"] == "True") == 0
    )
    rec("C8", c8, f"Optical 4-gen (771 G1 -> 241 G8 -> 0 ETI) + Orbits #139-#140 (0 ETI)")

    # C9: Companion Archives T/U/V byte/SHA-256 & 25-campaign Coherent Jerk (1.41B px integrals -> 0 ETI)
    req_tuv = ml["retroactive_reused_bundles"]
    cands = []
    if os.environ.get("SETI_ARCHIVES_DIR"):
        cands.append(pathlib.Path(os.environ["SETI_ARCHIVES_DIR"]))
    cands.extend([ROOT / "archives", WS.parent / "archives", pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14/archives")])
    arch_dir = next((c for c in cands if (c / req_tuv[0]["archive_name"]).is_file()), ROOT / "archives")
    tuv_ok = len(req_tuv) == 3
    for meta in req_tuv:
        ap = arch_dir / meta["archive_name"]
        if not ap.is_file() or _sha256(ap) != meta["archive_sha256"]:
            tuv_ok = False
            continue
        with zipfile.ZipFile(ap, "r") as zf:
            bm = meta["bundle_member"]
            matches = [n for n in zf.namelist() if n == bm or n.endswith("/" + bm)]
            if not matches or hashlib.sha256(zf.read(matches[0])).hexdigest() != meta["bundle_sha256"]:
                tuv_ok = False
    camps = _read_csv("DRIFT_V55_COHERENT_JERK_25CAMPAIGNS.csv")
    css_c = _read_csv("DRIFT_V55_COHERENT_CANDIDATE_LEDGER.csv")
    tot_int = sum(int(r["n_pixel_trajectory_integrals"]) for r in camps)
    c9 = (
        tuv_ok
        and len(camps) == 25
        and tot_int == 1410603112
        and sum(1 for r in css_c if r["verified_eti"] == "True") == 0
    )
    rec("C9", c9, f"Archives T/U/V verified={tuv_ok}; 25 CSS campaigns ({tot_int:,} px integrals, {len(css_c)} -> 0 ETI)")

    # C10 & C11: Unified 448-star, 169 <10pc, 58 bridges (60 multi-phase), 453 combs, 448 Ellipsoid
    syn = _read_csv("UNIFIED_PANCHROMATIC_V5_5_SYNTHESIS_448STARS.csv")
    ten = _read_csv("SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_169STARS.csv")
    br = _read_csv("PANCHROMATIC_BRIDGE_58STARS_V55.csv")
    ell = _read_csv("MULTIEVENT_ELLIPSOID_448STARS.csv")
    cmbu = _read_csv("ALLSKY_COMB_V4_1_UNIFIED_D079_D097.csv")
    s_un = sm["unified_448star_panchromatic_v5_5_synthesis"]
    c10 = (
        len(syn) == 448
        and len(ten) == 169
        and len({r["star"] for r in br}) == 58
        and len(br) == 728
        and int(s_un["multi_phase_targets_total"]) == 60
        and int(s_un["verified_eti_detections_total"]) == 0
        and abs(float(s_un["octave_span"]) - 12.855) < 1e-3
    )
    rec("C10", c10, f"448 stars (169 <10pc med={s_un['within_10pc_median_limit_kw']} kW), 58 bridges (728 cells), 12.855 octaves, 0 ETI")

    c11 = (
        len(cmbu) == 453
        and len(ell) == 448
        and sum(1 for r in ell if r["etz_qualified"] == "True") == 18
        and sum(1 for r in ell if r["ellipsoid_qualified_180d"] == "True") == 36
    )
    rec("C11", c11, "453 comb stacks (0 D097 ETI), 448 Ellipsoid (18 ETZ, 36 <= 180d)")

    # C12: Pure-stdlib Radiometric EIRP verification across ALL 95 D097 cells (< 0.002 rel err)
    eirp = _read_csv("EIRP_UPPER_LIMITS_D097.csv")
    max_rel = 0.0
    for row in eirp:
        recomp = _pure_stdlib_pbeam_kw(row)
        saved = float(row["p_beam_10m_kw"])
        rel = abs(recomp - saved) / max(1e-30, saved)
        if rel > max_rel:
            max_rel = rel
    c12 = (len(eirp) == 95 and max_rel < 0.002)
    rec("C12", c12, f"Radiometric recomputation across {len(eirp)} EIRP cells: max_rel_err={max_rel:.8f} (< 0.002)")

    # C13: All 40 result files present & non-empty
    res_files = sorted(p.name for p in RES.iterdir() if p.is_file())
    c13 = (len(res_files) == 40 and all((RES / f).stat().st_size > 10 for f in res_files))
    rec("C13", c13, f"40 result files present & non-empty ({len(res_files)}/40)")

    # C14: VISUAL_REVIEW.json PASS (6/6) & all 6 240-DPI PNGs non-empty
    vr = json.loads((WS / "VISUAL_REVIEW.json").read_text(encoding="utf-8"))
    figs_ok = all((WS / f["filename"]).is_file() and (WS / f["filename"]).stat().st_size > 50000 for f in vr.get("figures_reviewed", []))
    c14 = (vr.get("status") == "PASS (6/6)" and len(vr.get("figures_reviewed", [])) == 6 and figs_ok)
    rec("C14", c14, f"VISUAL_REVIEW status={vr.get('status')}, 6/6 PNG figures verified")

    # C15: RESULTS_REPORT.md & SOURCES.json completeness
    rep_txt = (WS / "RESULTS_REPORT.md").read_text(encoding="utf-8")
    src = json.loads((WS / "SOURCES.json").read_text(encoding="utf-8"))
    c15 = (len(rep_txt) > 3000 and "12.855" in rep_txt and src.get("raw_archives_ingested", {}).get("total_input_files") == 78)
    rec("C15", c15, f"RESULTS_REPORT.md ({len(rep_txt)} chars) & SOURCES.json (78 raw files) verified")

    # C16: Pure-stdlib self-verification (no non-stdlib module loaded)
    non_std = [m for m in sys.modules if m in ("numpy", "scipy", "astropy", "matplotlib")]
    c16 = (len(non_std) == 0)
    rec("C16", c16, f"Zero third-party imports under /usr/bin/python3 -S (forbidden_loaded={non_std})")

    passed = sum(1 for _, ok, _ in checks if ok)
    print(f"\nAUDIT SUMMARY: {passed}/{len(checks)} CHECKS PASSED")
    return passed, len(checks)


if __name__ == "__main__":
    p_cnt, t_cnt = run_audit()
    raise SystemExit(0 if p_cnt == t_cnt else 1)
