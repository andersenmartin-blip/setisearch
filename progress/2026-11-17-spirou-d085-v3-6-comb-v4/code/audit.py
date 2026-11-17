#!/usr/bin/env python3
"""Independent pure-stdlib (/usr/bin/python3 -S) verifier for Phase D085 (SPIROU_V3_6_AND_COMB_V4).

Zero third-party imports (only Python standard library modules). Performs 14 quantitative,
mathematical, cryptographic, and integrity audits on:
  C1.  Prospective lock chronology (LOCK_RECEIPT vs FIRST_SCIENCE_DOWNLOAD_RECEIPT) & hashes
  C2.  Prior exclusion & 29-star (25 brand-new + 4 northern bridge) / 177-exposure cohort integrity
  C3.  Bounded offline bundle size (< 25 MiB) & schema integrity
  C4.  177 SPIRou exposure provenance & independent pure-stdlib Maunakea BERV check (<= 0.50 km/s)
  C5.  2,124 NIST vacuum atomic RV anchors (12 lines spanning YJHK) & 29 star RV summaries
  C6.  1,971 single-line/Keplerian/H4RG calibration trials (T, P, Keplerian, G4/G5 dual-fiber+IPC)
  C7.  240-trial head-to-head Gate G6_V36 sparse vs G6_V35 dense benchmark
  C8.  381-trial Channel 5 V4 COMB calibration (6-tooth recovery, 1-line & topo ro-vib veto)
  C9.  Four-generation single-line cascade (V2->V3.6) & Channel 5 V4 COMB search parity
  C10. Forensic candidate audit (FORENSIC_CANDIDATE_AUDIT_D085.json) & zero verified ETI detections
  C11. 10 SPIRou orbital campaigns independent Keplerian Kp recomputation (<= 0.05 km/s)
  C12. 300 science YJHK upper-limit cells independent 3-band Cohen+2003 2MASS J/H/Ks Planck inversion
  C13. 8-star optical-to-K bridge, 73-star < 10 pc census, & 150-star (1,009-exp) unified synthesis
  C14. 160-system multi-messenger synthesis (14 direct overlaps incl. rho CrB) & strict zero-NaN CSV/JSON
"""

from __future__ import annotations

import csv
import datetime as dt
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any

HERE = Path(__file__).resolve().parent

C_KMS = 299792.458
G_SI = 6.67430e-11
M_SUN_KG = 1.98847e30
DAY_S = 86400.0
PC_CM = 3.0856775814913673e18
HC_OVER_K_A_K = 1.438776877e8
FWHM_FACTOR = 2.0 * math.sqrt(2.0 * math.log(2.0))

# Cohen, Wheaton & Megeath (2003) 2MASS zero points
TWOMASS_J_PIVOT_A, TWOMASS_J_ZP_FLAM = 12350.0, 3.129e-10
TWOMASS_H_PIVOT_A, TWOMASS_H_ZP_FLAM = 16620.0, 1.133e-10
TWOMASS_KS_PIVOT_A, TWOMASS_KS_ZP_FLAM = 21590.0, 4.283e-11
MAUNAKEA_LAT_DEG, MAUNAKEA_LON_DEG = 19.8253, -155.4689


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def stdlib_maunakea_berv_kms(ra_deg: float, dec_deg: float, mjd_utc: float) -> float:
    t_jd = float(mjd_utc) + 2400000.5
    t_c = (t_jd - 2451545.0) / 36525.0
    l0 = math.radians((280.46646 + (36000.76983 - 1.396971) * t_c) % 360.0)
    m_sun = math.radians((357.52911 + 35999.05029 * t_c) % 360.0)
    e_orb = 0.016708634 - 0.000042037 * t_c
    c_eq = math.radians((1.914602 - 0.004817 * t_c) * math.sin(m_sun) + 0.019993 * math.sin(2.0 * m_sun) + 0.000289 * math.sin(3.0 * m_sun))
    lam_sun, nu = l0 + c_eq, m_sun + c_eq
    eps = math.radians(23.4392911)
    v_orb = 29.7847 / math.sqrt(1.0 - e_orb * e_orb)
    vx = v_orb * (math.sin(lam_sun) + e_orb * math.sin(lam_sun - nu))
    vy_ecl = -v_orb * (math.cos(lam_sun) + e_orb * math.cos(lam_sun - nu))
    vy, vz = vy_ecl * math.cos(eps), vy_ecl * math.sin(eps)
    for amp, l_deg in ((0.01246, 34.3515 + 3034.9057 * t_c), (0.00276, 50.0774 + 1222.1138 * t_c), (0.01242, 218.3165 + 481267.8813 * t_c)):
        lr = math.radians(l_deg % 360.0)
        vx += -amp * math.sin(lr)
        vy += amp * math.cos(lr) * math.cos(eps)
        vz += amp * math.cos(lr) * math.sin(eps)
    gmst_deg = (280.46061837 + 360.98564736629 * (t_jd - 2451545.0)) % 360.0
    lst = math.radians((gmst_deg + MAUNAKEA_LON_DEG) % 360.0)
    v_eq = 0.46510 * math.cos(math.radians(MAUNAKEA_LAT_DEG))
    vx += -v_eq * math.sin(lst)
    vy += v_eq * math.cos(lst)
    ra, dec = math.radians(ra_deg), math.radians(dec_deg)
    return float(vx * math.cos(dec) * math.cos(ra) + vy * math.cos(dec) * math.sin(ra) + vz * math.sin(dec))


def check_no_nan_in_csv(rows: list[dict[str, str]], path: Path, allowed_blank_cols: set[str]) -> tuple[bool, str]:
    bad_vals = ("nan", "inf", "-inf", "null")
    for idx, row in enumerate(rows):
        for col, val in row.items():
            s = (val or "").strip()
            if s.lower() in bad_vals:
                return False, f"{path.name} row {idx} col {col} has invalid token {val!r}"
            if s == "" and col not in allowed_blank_cols:
                return False, f"{path.name} row {idx} col {col} is unexpectedly blank"
    return True, f"{path.name}: {len(rows)} rows clean (0 NaN/Inf)"


def main() -> int:
    checks: list[dict[str, Any]] = []

    def record(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")

    print("[audit.py] Starting 14-check stdlib verification (/usr/bin/python3 -S)...")

    # C1: Prospective lock chronology & SHA-256 verification
    try:
        mlock = json.loads((HERE / "METHOD_LOCK.json").read_text(encoding="utf-8"))
        lrcpt = json.loads((HERE / "LOCK_RECEIPT.json").read_text(encoding="utf-8"))
        dlrcpt = json.loads((HERE / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json").read_text(encoding="utf-8"))
        ml_sha = sha256_file(HERE / "METHOD_LOCK.json")
        ok_ml = ml_sha == lrcpt["method_lock_sha256"]

        amended: dict[str, str] = {}
        ilock_p = HERE / "IMPLEMENTATION_LOCK.json"
        if ilock_p.is_file():
            ilock = json.loads(ilock_p.read_text(encoding="utf-8"))
            if ilock.get("parent_method_lock_sha256") != ml_sha:
                raise RuntimeError("IMPLEMENTATION_LOCK parent hash mismatch")
            if ilock.get("cohort_modified") is not False:
                raise RuntimeError("IMPLEMENTATION_LOCK cohort_modified must be False")
            amended = dict(ilock.get("amended_file_hashes", {}))

        hash_mismatches = []
        for fn, locked_sha in mlock["locked_file_hashes"].items():
            fp = HERE / fn
            cur = sha256_file(fp) if fp.is_file() else "MISSING"
            if cur != locked_sha:
                if fn in amended and cur == amended[fn] and fn not in ("FROZEN_COHORT_D085.csv", "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json"):
                    continue
                hash_mismatches.append(fn)

        t_lock = dt.datetime.fromisoformat(lrcpt["lock_utc"].replace("Z", "+00:00"))
        t_dl = dt.datetime.fromisoformat(dlrcpt["first_download_utc"].replace("Z", "+00:00"))
        dt_sec = (t_dl - t_lock).total_seconds()
        ok1 = ok_ml and (not hash_mismatches) and (dt_sec > 0.0)
        record("C1_PROSPECTIVE_LOCK_AND_CHRONOLOGY", ok1, f"lock={lrcpt['lock_utc']}, first_dl={dlrcpt['first_download_utc']} (+{dt_sec:.1f}s), mismatches={len(hash_mismatches)}")
    except Exception as exc:
        record("C1_PROSPECTIVE_LOCK_AND_CHRONOLOGY", False, repr(exc))

    # C2: Prior exclusion & 29-star / 177-exposure cohort integrity
    cohort_rows = read_csv(HERE / "FROZEN_COHORT_D085.csv")
    pe = json.loads((HERE / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    orb_cat = json.loads((HERE / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").read_text(encoding="utf-8"))
    ok2_n, _ = check_no_nan_in_csv(cohort_rows, HERE / "FROZEN_COHORT_D085.csv", {"radio_mm_id"})
    stars_29 = {r["canonical_target"] for r in cohort_rows}
    new_stars = {r["canonical_target"] for r in cohort_rows if r["panchromatic_bridge"] != "True"}
    bridge_stars = {r["canonical_target"] for r in cohort_rows if r["panchromatic_bridge"] == "True"}
    new_10pc = {r["canonical_target"] for r in cohort_rows if r["panchromatic_bridge"] != "True" and r["within_10pc"] == "True"}
    excl_set = set(pe["excluded_dp_ids"]) | set(pe["format_check_excluded_dp_ids"])
    dp_ovlp = {r["dp_id"] for r in cohort_rows} & excl_set
    ok2 = (
        ok2_n
        and len(cohort_rows) == 177
        and len(stars_29) == 29
        and len(new_stars) == 25
        and len(bridge_stars) == 4
        and len(new_10pc) == 20
        and orb_cat["n_campaigns"] == 10
        and pe["d085_dp_id_overlap_count"] == 0
        and len(dp_ovlp) == 0
        and float(pe["min_brand_new_sky_separation_arcsec"]) >= 9800.0
    )
    record("C2_PRIOR_EXCLUSION_AND_COHORT_INTEGRITY", ok2, f"177 exp, 29 stars (25 new [{len(new_10pc)} <10pc] + 4 bridge), 10 campaigns, min_sep={pe['min_brand_new_sky_separation_arcsec']}\", dp_overlap={len(dp_ovlp)}")

    # C3: Bounded bundle size & schema
    bundle_p = HERE / "bounded_inputs" / "d085_bounded_bundle.json.gz"
    b_mib = bundle_p.stat().st_size / (1024.0 * 1024.0)
    with gzip.open(bundle_p, "rt", encoding="utf-8") as gz:
        bundle = json.load(gz)
    ok3 = (
        b_mib < 25.0
        and bundle.get("schema") == "SETI_D085_BOUNDED_REPRODUCIBLE_BUNDLE_V1"
        and len(bundle["provenance_rows"]) == 177
        and len(bundle["rv_anchor_bundle"]) == 177
        and len(bundle["calib_transient_patches"]) == 72
        and len(bundle["calib_persistent_patches"]) == 36
        and len(bundle["calib_keplerian_patches"]) == 9
        and len(bundle["calib_h4rg_2d_patches"]) == 72
        and len(bundle["calib_g6_patches"]) == 20
        and len(bundle["calib_comb_patches"]) == 16
    )
    record("C3_BUNDLE_SIZE_AND_SCHEMA", ok3, f"d085_bounded_bundle.json.gz = {b_mib:.2f} MiB (<25.0 MiB), patches=(72,36,9,72,20,16)")

    # C4: Exposure provenance & Maunakea BERV check
    prov_rows = read_csv(HERE / "results" / "EXPOSURE_PROVENANCE_177.csv")
    ok4_n, _ = check_no_nan_in_csv(prov_rows, HERE / "results" / "EXPOSURE_PROVENANCE_177.csv", {"radio_mm_id"})
    max_berv_diff = 0.0
    for pr in prov_rows:
        b_ref = stdlib_maunakea_berv_kms(float(pr["s_ra_deg"]), float(pr["s_dec_deg"]), float(pr["mjd_mid"]))
        max_berv_diff = max(max_berv_diff, abs(b_ref - float(pr["berv_kms"])))
    ok4 = ok4_n and len(prov_rows) == 177 and all(r["header_gate"] == "PASS" for r in prov_rows) and max_berv_diff <= 0.50
    record("C4_EXPOSURE_PROVENANCE_AND_MAUNAKEA_BERV", ok4, f"177 PASS rows, max |BERV_hdr - stdlib_Maunakea_BERV| = {max_berv_diff:.4f} km/s (<= 0.50)")

    # C5: 2,124 RV anchors & 29 star RV summaries
    rva_rows = read_csv(HERE / "results" / "STELLAR_RV_ANCHORS_2124.csv")
    rvs_rows = read_csv(HERE / "results" / "STAR_RV_SUMMARY_29.csv")
    ok5_a, _ = check_no_nan_in_csv(rva_rows, HERE / "results" / "STELLAR_RV_ANCHORS_2124.csv", {"best_rv_kms", "rel_depth", "min_sse"})
    ok5_s, _ = check_no_nan_in_csv(rvs_rows, HERE / "results" / "STAR_RV_SUMMARY_29.csv", {"radio_mm_id"})
    n_clean_anc = sum(1 for r in rva_rows if r["status"] == "CLEAN_ABSORPTION")
    abs_diffs = sorted(abs(float(r["empirical_minus_prior_kms"])) for r in rvs_rows)
    med_rv_diff = abs_diffs[len(abs_diffs) // 2]
    ok5 = ok5_a and ok5_s and len(rva_rows) == 2124 and len(rvs_rows) == 29 and n_clean_anc >= 1200 and med_rv_diff <= 2.0
    record("C5_RV_ANCHORING_2124_AND_29STARS", ok5, f"2124 anchors ({n_clean_anc} clean), 29 star summaries, median |emp - prior| = {med_rv_diff:.4f} km/s")

    # C6: 1,971 Single-Line, Keplerian & Dual-Fiber H4RG Calibration Trials
    inj_rows = read_csv(HERE / "results" / "INJECTION_RECOVERY_1620.csv")
    kep_rows = read_csv(HERE / "results" / "KEPLERIAN_TRACK_CALIBRATION_135.csv")
    h4rg_rows = read_csv(HERE / "results" / "DETECTOR_H4RG_G4G5_CALIBRATION_216.csv")
    cb_rows = read_csv(HERE / "results" / "CALIBRATION_COMPLETENESS_BY_BAND.csv")
    ok6_n = (
        check_no_nan_in_csv(inj_rows, HERE / "results" / "INJECTION_RECOVERY_1620.csv", {"fitted_fwhm_ratio"})[0]
        and check_no_nan_in_csv(kep_rows, HERE / "results" / "KEPLERIAN_TRACK_CALIBRATION_135.csv", {"kplanet_dedop_fwhm_ratio"})[0]
        and check_no_nan_in_csv(h4rg_rows, HERE / "results" / "DETECTOR_H4RG_G4G5_CALIBRATION_216.csv", {"primary_order", "primary_native_px", "fiber_ab_amp_ratio", "cos_1d_11px", "ipc_hotpx_ratio", "far_wing_34_ratio"})[0]
        and check_no_nan_in_csv(cb_rows, HERE / "results" / "CALIBRATION_COMPLETENESS_BY_BAND.csv", set())[0]
    )
    t8 = [r for r in inj_rows if r["mode"] == "CHANNEL_T_TRANSIENT_1EPOCH" and float(r["sigma_mult"]) >= 8.0]
    p9 = [r for r in inj_rows if r["mode"] == "CHANNEL_P_PERSISTENT_5EPOCH" and float(r["sigma_mult"]) >= 9.0]
    k65 = [r for r in kep_rows if float(r["exp_sigma_mult"]) >= 6.5]
    t8_r = sum(1 for r in t8 if r["recovered"] == "True") / max(1, len(t8))
    p9_r = sum(1 for r in p9 if r["recovered"] == "True") / max(1, len(p9))
    k_td_r = sum(1 for r in k65 if r["tdiff_uncomp_recovered"] == "True") / max(1, len(k65))
    k_kp_r = sum(1 for r in k65 if r["kplanet_dedop_recovered"] == "True") / max(1, len(k65))
    h_l_r = sum(1 for r in h4rg_rows if r["trial_class"] == "TRUE_DUALFIBER_LASER" and r["g45_pass"] == "True") / 72.0
    h_i_r = sum(1 for r in h4rg_rows if r["trial_class"] == "H4RG_IPC_HOT_PIXEL" and r["g5_pass"] == "False") / 72.0
    h_p_r = sum(1 for r in h4rg_rows if r["trial_class"] == "H4RG_PERSISTENCE_PLATEAU" and r["g5_pass"] == "False") / 72.0
    ok6 = ok6_n and (len(inj_rows) + len(kep_rows) + len(h4rg_rows) == 1971) and len(cb_rows) == 90 and t8_r >= 0.70 and p9_r >= 0.75 and k_kp_r > k_td_r and k_kp_r >= 0.25 and h_l_r >= 0.90 and h_i_r == 1.0 and h_p_r >= 0.95
    record("C6_SINGLELINE_KEPLERIAN_H4RG_CALIB_1971", ok6, f"1971 trials: T>=8s={t8_r:.3f}, P>=9s={p9_r:.3f}, Kep=({k_td_r:.3f}->{k_kp_r:.3f}), H4RG=({h_l_r:.3f},{h_i_r:.3f},{h_p_r:.3f})")

    # C7: 240-Trial Head-to-Head G6_V36 Sparse vs G6_V35 Dense Benchmark
    g6_rows = read_csv(HERE / "results" / "G6_SPARSE_VS_DENSE_CALIBRATION_240.csv")
    ok7_n, _ = check_no_nan_in_csv(g6_rows, HERE / "results" / "G6_SPARSE_VS_DENSE_CALIBRATION_240.csv", set())
    g6_t = [r for r in g6_rows if r["trial_class"] == "TRUE_BARYCENTRIC_STELLAR_LASER"]
    g6_oh = [r for r in g6_rows if r["trial_class"] == "UNLISTED_STATIONARY_SKY_OH_LINE"]
    g6_px = [r for r in g6_rows if r["trial_class"] == "STATIONARY_H4RG_WARM_PIXEL"]
    g6_in = [r for r in g6_rows if r["trial_class"] == "INTRA_STAR_BERV_STATIONARY_GHOST"]
    r_d_t = sum(1 for r in g6_t if r["g6_v35_dense_pass"] == "True") / max(1, len(g6_t))
    r_s_t = sum(1 for r in g6_t if r["g6_v36_sparse_pass"] == "True") / max(1, len(g6_t))
    r_s_oh = sum(1 for r in g6_oh if r["g6_v36_sparse_pass"] == "False") / max(1, len(g6_oh))
    r_s_px = sum(1 for r in g6_px if r["g6_v36_sparse_pass"] == "False") / max(1, len(g6_px))
    r_s_in = sum(1 for r in g6_in if r["g6_v36_sparse_pass"] == "False") / max(1, len(g6_in))
    r_d_in = sum(1 for r in g6_in if r["g6_v35_dense_pass"] == "False") / max(1, len(g6_in))
    ok7 = ok7_n and len(g6_rows) == 240 and r_s_t >= 0.85 and r_s_t >= r_d_t and r_s_oh >= 0.98 and r_s_px >= 0.98 and r_s_in == 1.0
    record("C7_G6_SPARSE_VS_DENSE_CALIB_240", ok7, f"240 trials: true_laser=(V35={r_d_t:.3f} -> V36={r_s_t:.3f}), OH={r_s_oh:.3f}, px={r_s_px:.3f}, intraBERV=(V35={r_d_in:.3f} -> V36={r_s_in:.3f})")

    # C8: 381-Trial V4 COMB Calibration
    comb_cal = read_csv(HERE / "results" / "COMB_V4_CALIBRATION_381.csv")
    ok8_n, _ = check_no_nan_in_csv(comb_cal, HERE / "results" / "COMB_V4_CALIBRATION_381.csv", set())
    c_hi = [r for r in comb_cal if r["trial_class"] == "TRUE_6TOOTH_STELLAR_COMB" and float(r["tooth_snr_inj"]) >= 3.8]
    c_1l = [r for r in comb_cal if r["trial_class"] == "SINGLE_BRIGHT_LINE_MASQUERADE"]
    c_ro = [r for r in comb_cal if r["trial_class"] == "STATIONARY_TOPO_ROVIB_PSEUDOCOMB"]
    c_rec = sum(1 for r in c_hi if r["comb_hit"] == "True") / max(1, len(c_hi))
    c_1l_fpr = sum(1 for r in c_1l if r["comb_hit"] == "True") / max(1, len(c_1l))
    c_ro_fpr = sum(1 for r in c_ro if r["comb_hit"] == "True") / max(1, len(c_ro))
    ok8 = ok8_n and len(comb_cal) == 381 and c_rec >= 0.80 and c_1l_fpr == 0.0 and c_ro_fpr <= 0.05
    record("C8_COMB_V4_CALIBRATION_381", ok8, f"381 trials: 6-tooth>=3.8sig={c_rec:.3f}, single_line_FPR={c_1l_fpr:.3f}, topo_rovib_FPR={c_ro_fpr:.3f}")

    # C9: Four-Generation Single-Line Cascade & V4 COMB Search Parity
    bench_rows = read_csv(HERE / "results" / "FOUR_GEN_BENCHMARK_177.csv")
    led_rows = read_csv(HERE / "results" / "V3_6_CANDIDATE_LEDGER.csv")
    comb_star = read_csv(HERE / "results" / "COMB_V4_STAR_RESULTS_29.csv")
    comb_cands = read_csv(HERE / "results" / "COMB_V4_CANDIDATES.csv")
    summary = json.loads((HERE / "results" / "SUMMARY.json").read_text(encoding="utf-8"))
    ok9_b, _ = check_no_nan_in_csv(bench_rows, HERE / "results" / "FOUR_GEN_BENCHMARK_177.csv", set())
    ok9_l, _ = check_no_nan_in_csv(led_rows, HERE / "results" / "V3_6_CANDIDATE_LEDGER.csv", {"fwhm_ratio", "primary_order", "primary_native_px", "primary_native_fn_pk3", "primary_template_dip_frac", "primary_eta_1px", "fiber_ab_tested", "fiber_ab_amp_ratio", "overlap_tested", "g5_cos11", "g5_ipc_hotpx_ratio", "g5_far_wing_ratio"})
    ok9_cs, _ = check_no_nan_in_csv(comb_star, HERE / "results" / "COMB_V4_STAR_RESULTS_29.csv", set())
    ok9_cc = check_no_nan_in_csv(comb_cands, HERE / "results" / "COMB_V4_CANDIDATES.csv", set())[0] if comb_cands else True
    fc = summary["false_alarm_cascade"]
    v2_fa = sum(int(r["v2_accepted_false_alarms"]) for r in bench_rows)
    n_pre_g6 = sum(1 for r in led_rows if r["pre_g6_qualified"] == "True")
    n_qual_ctrl = sum(1 for r in led_rows if r["role"] == "CONTROL" and r["qualified_v36_laser"] == "True")
    n_qual_sci = sum(1 for r in led_rows if r["role"] == "SCIENCE" and r["qualified_v36_laser"] == "True")
    ok9 = (
        ok9_b and ok9_l and ok9_cs and ok9_cc
        and len(bench_rows) == 177 and len(comb_star) == 29
        and v2_fa == fc["v2_legacy_false_alarms"] and v2_fa > 0
        and len(led_rows) == fc["v36_total_ledger_g1_candidates"]
        and n_pre_g6 == fc["v36_pre_g6_passed_g1_to_g5"]
        and n_qual_ctrl == fc["automated_qualified_control"]
        and n_qual_sci == fc["automated_qualified_science"]
        and len(comb_cands) == fc["comb_v4_automated_candidates"]
    )
    record("C9_CASCADE_AND_COMB_V4_PARITY", ok9, f"V2={v2_fa} -> V3.6 G1={len(led_rows)} -> preG6={n_pre_g6} -> qual=(ctrl={n_qual_ctrl},sci={n_qual_sci}), COMB_V4={len(comb_cands)}")

    # C10: Forensic Candidate Audit & Zero ETI
    for_doc = json.loads((HERE / "results" / "FORENSIC_SPIROU_CASCADE_DIAGNOSIS.json").read_text(encoding="utf-8"))
    for_aud = json.loads((HERE / "FORENSIC_CANDIDATE_AUDIT_D085.json").read_text(encoding="utf-8"))
    aud_sl_ids = {x["candidate_id"] for x in for_aud["post_g6_singleline_forensic_classifications"]}
    post_sl_ids = {x["candidate_id"] for x in for_doc["post_g6_qualified"]}
    aud_cb_ids = {x["comb_id"] for x in for_aud["comb_v4_forensic_classifications"]}
    post_cb_ids = {x["comb_id"] for x in for_doc["comb_v4_candidates"]}
    ok10 = (
        for_doc["pre_g6_count"] == n_pre_g6
        and aud_sl_ids == post_sl_ids
        and aud_cb_ids == post_cb_ids
        and all(x.get("eti_plausible") is False for x in for_aud["post_g6_singleline_forensic_classifications"])
        and all(x.get("eti_plausible") is False for x in for_aud["comb_v4_forensic_classifications"])
        and for_aud["verified_eti_detections"] == 0
        and fc["verified_eti_detections"] == 0
    )
    record("C10_FORENSIC_AUDIT_AND_ZERO_ETI", ok10, f"post-G6 single-line={len(aud_sl_ids)}, COMB={len(aud_cb_ids)} forensically audited, verified_eti_detections=0")

    # C11: 10 Orbital Campaigns Independent Kp Recomputation
    orb_rows = read_csv(HERE / "results" / "ORBITAL_CAMPAIGN_RESULTS_10.csv")
    ok11_n, _ = check_no_nan_in_csv(orb_rows, HERE / "results" / "ORBITAL_CAMPAIGN_RESULTS_10.csv", set())
    max_kp_err = 0.0
    for r in orb_rows:
        cm = orb_cat["campaigns"][r["star"]]
        kp_std = ((2.0 * math.pi * G_SI * float(cm["st_mass_msun"]) * M_SUN_KG / (float(cm["orbper_days"]) * DAY_S)) ** (1.0 / 3.0)) / math.sqrt(max(1e-6, 1.0 - float(cm["ecc"]) ** 2)) / 1000.0
        max_kp_err = max(max_kp_err, abs(kp_std - float(r["kp_kms"])))
    ok11 = ok11_n and len(orb_rows) == 10 and sum(1 for r in orb_rows if r["role"] == "CONTROL") == 2 and sum(1 for r in orb_rows if r["role"] == "SCIENCE") == 8 and max_kp_err <= 0.05 and all(int(r["n_in_window"]) == 4 and int(r["n_out_of_window"]) == 4 for r in orb_rows)
    record("C11_ORBITAL_CAMPAIGNS_10_CHECK", ok11, f"10 campaigns (2 ctrl + 8 sci, 4 IN + 4 OUT), max |Kp_stdlib - Kp_csv| = {max_kp_err:.5f} km/s")

    # C12: 300 Upper-Limit Cells Independent 3-Band 2MASS J/H/Ks Planck Recomputation
    ul_rows = read_csv(HERE / "results" / "STAR_UPPER_LIMITS_300.csv")
    ok12_n, _ = check_no_nan_in_csv(ul_rows, HERE / "results" / "STAR_UPPER_LIMITS_300.csv", {"radio_mm_id"})
    max_rel_p = 0.0
    for u in ul_rows:
        lam_a, amp, teff, dist_pc = float(u["wave_bary_vac_A"]), float(u["amp_rel_8sigma_lim"]), float(u["teff_k"]), float(u["dist_pc"])
        if lam_a < 14200.0:
            piv, zp, mag = TWOMASS_J_PIVOT_A, TWOMASS_J_ZP_FLAM, float(u["j_mag"])
        elif lam_a < 18800.0:
            piv, zp, mag = TWOMASS_H_PIVOT_A, TWOMASS_H_ZP_FLAM, float(u["h_mag"])
        else:
            piv, zp, mag = TWOMASS_KS_PIVOT_A, TWOMASS_KS_ZP_FLAM, float(u["ks_mag"])
        b_rat = ((piv / lam_a) ** 5) * math.expm1(HC_OVER_K_A_K / (piv * teff)) / math.expm1(HC_OVER_K_A_K / (lam_a * teff))
        flam = zp * (10.0 ** (-0.4 * mag)) * b_rat
        ew_a = math.sqrt(math.pi / (4.0 * math.log(2.0))) * amp * (lam_a / 70000.0)
        l_iso = 4.0 * math.pi * ((dist_pc * PC_CM) ** 2) * (flam * ew_a) * 1e-7
        p10_std = l_iso / ((math.pi * 10.0 / (lam_a * 1e-10)) ** 2)
        max_rel_p = max(max_rel_p, abs(p10_std - float(u["p_beam_10m_w"])) / max(1e-30, float(u["p_beam_10m_w"])))
    ok12 = ok12_n and len(ul_rows) == 300 and max_rel_p < 1e-5
    record("C12_UPPER_LIMITS_300_COHEN_2MASS_JHK", ok12, f"300 cells (25 sci x 12 YJHK bands, 0 NaN), max rel diff = {max_rel_p:.2e}")

    # C13: 8-Star Panchromatic Bridge, 73-Star < 10 pc Census, & 150-Star Unified Synthesis
    br8 = read_csv(HERE / "results" / "PANCHROMATIC_OPTICAL_NIR_K_BRIDGE_8STARS.csv")
    s73 = read_csv(HERE / "results" / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_73STARS.csv")
    u150 = read_csv(HERE / "results" / "UNIFIED_PANCHROMATIC_V3_SYNTHESIS_150STARS.csv")
    opt_b = {"j_mag", "h_mag", "ks_mag", "min_optical_10m_kw", "min_nir_yjh_10m_kw", "min_kband_10m_kw", "p_1064nm_10m_kw", "p_1550nm_10m_kw", "p_2040nm_tm_10m_kw", "p_2097nm_hoyag_10m_kw", "min_panchromatic_10m_kw"}
    ok13_b, _ = check_no_nan_in_csv(br8, HERE / "results" / "PANCHROMATIC_OPTICAL_NIR_K_BRIDGE_8STARS.csv", set())
    ok13_s, _ = check_no_nan_in_csv(s73, HERE / "results" / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_73STARS.csv", opt_b)
    ok13_u, _ = check_no_nan_in_csv(u150, HERE / "results" / "UNIFIED_PANCHROMATIC_V3_SYNTHESIS_150STARS.csv", opt_b)
    br_stars = {r["star"] for r in br8}
    tot_exp = sum(int(r["n_exposures_total"]) for r in u150)
    ok13 = ok13_b and ok13_s and ok13_u and len(br_stars) == 8 and len(u150) == 150 and len({r["star"] for r in u150}) == 150 and len(s73) == 73 and all(float(r["dist_pc"]) < 10.0 for r in s73) and tot_exp == 1009 and all(int(r["verified_eti_detections"]) == 0 for r in u150)
    record("C13_BRIDGE_8_10PC_73_UNIFIED_150STAR", ok13, f"8 bridge stars ({len(br8)} cells), 73 <10pc, 150 unique stars, {tot_exp} cumulative exposures")

    # C14: 160-System Multi-Messenger Synthesis (14 Direct Overlaps)
    mm160 = read_csv(HERE / "results" / "MULTIMESSENGER_ECHELLE_RADIO_TESS_160SYSTEMS.csv")
    ok14_n, _ = check_no_nan_in_csv(mm160, HERE / "results" / "MULTIMESSENGER_ECHELLE_RADIO_TESS_160SYSTEMS.csv", {"dist_pc", "within_10pc", "echelle_phases", "echelle_instruments", "min_echelle_10m_kw", "radio_milestone", "radio_facility", "radio_snr40_recovery", "lightsail_milestone"})
    n_ovlp = sum(1 for r in mm160 if r["multimessenger_overlap"] == "True")
    syn_mm = summary["multimessenger_160system_synthesis"]
    ok14 = ok14_n and len(mm160) == 160 and n_ovlp == 14 and syn_mm["distinct_stellar_systems_total"] == 160 and syn_mm["direct_multimessenger_overlap_count"] == 14 and syn_mm["verified_eti_detections_all_modalities"] == 0
    record("C14_MULTIMESSENGER_160SYSTEM_SYNTHESIS", ok14, f"160 distinct systems, {n_ovlp} direct overlaps (incl. RHOCRB), 0 verified ETI across all modalities")

    n_pass = sum(1 for c in checks if c["status"] == "PASS")
    audit_out = {
        "schema": "D085_STDLIB_AUDIT_SUMMARY",
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "audited_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "checks_passed": n_pass,
        "checks_total": len(checks),
        "overall_status": "PASS" if n_pass == len(checks) else "FAIL",
        "checks": checks,
    }
    (HERE / "results" / "AUDIT_SUMMARY.json").write_text(json.dumps(audit_out, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"[audit.py] {n_pass}/{len(checks)} checks PASSED -> {audit_out['overall_status']}")
    return 0 if n_pass == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
