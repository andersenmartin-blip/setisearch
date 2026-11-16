#!/usr/bin/env python3
"""Independent pure-stdlib (/usr/bin/python3 -S) verifier for Phase D084 (NORTHERN_V3_5).

Zero third-party imports (only Python standard library modules). Performs 12 quantitative,
mathematical, cryptographic, and integrity audits on:
  - Prospective lock chronology (LOCK_RECEIPT vs FIRST_SCIENCE_DOWNLOAD_RECEIPT)
  - 25-star / 183-exposure northern cohort exclusion & non-overlap
  - Bounded offline bundle size (< 25 MiB) & schema integrity
  - Independent pure-stdlib BERV verification at La Palma (TNG) and Calar Alto
  - 2,196 NIST vacuum atomic RV anchor fits and 25 star RV summaries
  - 2,151 prospective synthetic control calibration trials (T, P, Keplerian, G5, G6)
  - Four-generation cascade & Gate G6 cross-star coincidence veto accounting
  - Forensic diagnosis JSON consistency & zero verified ETI detections
  - 10 northern orbital campaigns (independent Keplerian Kp & phase verification)
  - 189 science upper-limit cells (independent Gaia G + 2MASS J Planck radiative transfer)
  - Unified 125-star all-sky synthesis & 53-star < 10 pc census
  - Unified 136-system multi-messenger synthesis (13 direct overlap hosts)
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
GAIA_G_PIVOT_A = 6217.6
GAIA_G_ZP_FLAM = 2.50386e-9
TWOMASS_J_PIVOT_A = 12350.0
TWOMASS_J_ZP_FLAM = 3.129e-10
RADIOMETRIC_GJ_SPLIT_A = 8500.0
FWHM_FACTOR = 2.0 * math.sqrt(2.0 * math.log(2.0))


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


def stdlib_berv_kms(ra_deg: float, dec_deg: float, mjd_utc: float, instrument: str) -> float:
    """Independent pure-stdlib Keplerian Earth + Moon/Jupiter + observatory diurnal RV (km/s)."""
    t_jd = float(mjd_utc) + 2400000.5
    t_c = (t_jd - 2451545.0) / 36525.0
    l0 = math.radians((280.46646 + (36000.76983 - 1.396971) * t_c) % 360.0)
    m_sun = math.radians((357.52911 + 35999.05029 * t_c) % 360.0)
    e_orb = 0.016708634 - 0.000042037 * t_c
    c_eq = math.radians(
        (1.914602 - 0.004817 * t_c) * math.sin(m_sun)
        + 0.019993 * math.sin(2.0 * m_sun)
        + 0.000289 * math.sin(3.0 * m_sun)
    )
    lam_sun = l0 + c_eq
    nu = m_sun + c_eq
    eps = math.radians(23.4392911)
    v_orb = 29.7847 / math.sqrt(1.0 - e_orb * e_orb)
    vx_e = v_orb * (math.sin(lam_sun) + e_orb * math.sin(lam_sun - nu))
    vy_e_ecl = -v_orb * (math.cos(lam_sun) + e_orb * math.cos(lam_sun - nu))
    vy_e = vy_e_ecl * math.cos(eps)
    vz_e = vy_e_ecl * math.sin(eps)

    for amp, l_deg in ((0.01246, 34.3515 + 3034.9057 * t_c), (0.01242, 218.3165 + 481267.8813 * t_c)):
        lr = math.radians(l_deg % 360.0)
        vx_e += -amp * math.sin(lr)
        vy_e += amp * math.cos(lr) * math.cos(eps)
        vz_e += amp * math.cos(lr) * math.sin(eps)

    if instrument == "HARPS_N":
        lat_d, lon_d = 28.7540, -17.8891
    else:
        lat_d, lon_d = 37.2236, -2.5463
    gmst_deg = (280.46061837 + 360.98564736629 * (t_jd - 2451545.0)) % 360.0
    lst = math.radians((gmst_deg + lon_d) % 360.0)
    v_eq_obs = 0.4651 * math.cos(math.radians(lat_d))
    vx_d = -v_eq_obs * math.sin(lst)
    vy_d = v_eq_obs * math.cos(lst)

    ra = math.radians(ra_deg)
    dec = math.radians(dec_deg)
    sx = math.cos(dec) * math.cos(ra)
    sy = math.cos(dec) * math.sin(ra)
    sz = math.sin(dec)
    return float((vx_e + vx_d) * sx + (vy_e + vy_d) * sy + vz_e * sz)


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

    print("[audit.py] Starting 12-check stdlib verification (/usr/bin/python3 -S)...")

    # C1: Prospective lock chronology & SHA-256 verification
    try:
        mlock = json.loads((HERE / "METHOD_LOCK.json").read_text(encoding="utf-8"))
        lrcpt = json.loads((HERE / "LOCK_RECEIPT.json").read_text(encoding="utf-8"))
        dlrcpt = json.loads((HERE / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json").read_text(encoding="utf-8"))
        ml_sha = sha256_file(HERE / "METHOD_LOCK.json")
        ok_ml = (ml_sha == lrcpt["method_lock_sha256"])

        amended: dict[str, str] = {}
        ilock_p = HERE / "IMPLEMENTATION_LOCK.json"
        if ilock_p.is_file():
            ilock = json.loads(ilock_p.read_text(encoding="utf-8"))
            if ilock.get("parent_method_lock_sha256") != ml_sha:
                raise RuntimeError("IMPLEMENTATION_LOCK parent hash mismatch")
            amended = dict(ilock.get("amended_file_hashes", {}))

        hash_mismatches = []
        for fn, locked_sha in mlock["locked_file_hashes"].items():
            fp = HERE / fn
            cur = sha256_file(fp) if fp.is_file() else "MISSING"
            if cur != locked_sha:
                if fn in amended and cur == amended[fn] and fn not in ("v3_5_detector.py", "FROZEN_COHORT_D084.csv", "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json"):
                    continue
                hash_mismatches.append(fn)

        t_lock = dt.datetime.fromisoformat(lrcpt["lock_utc"].replace("Z", "+00:00"))
        t_dl = dt.datetime.fromisoformat(dlrcpt["first_download_utc"].replace("Z", "+00:00"))
        dt_sec = (t_dl - t_lock).total_seconds()
        ok1 = ok_ml and (not hash_mismatches) and (dt_sec > 0.0)
        record(
            "C1_PROSPECTIVE_LOCK_AND_CHRONOLOGY",
            ok1,
            f"lock_utc={lrcpt['lock_utc']}, first_dl={dlrcpt['first_download_utc']} (delta=+{dt_sec:.1f}s), mismatches={len(hash_mismatches)}",
        )
    except Exception as exc:
        record("C1_PROSPECTIVE_LOCK_AND_CHRONOLOGY", False, repr(exc))

    # C2: Prior exclusion & cohort integrity
    cohort_rows = read_csv(HERE / "FROZEN_COHORT_D084.csv")
    pe = json.loads((HERE / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    orb_cat = json.loads((HERE / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").read_text(encoding="utf-8"))
    ok2_nan, det2_nan = check_no_nan_in_csv(cohort_rows, HERE / "FROZEN_COHORT_D084.csv", {"radio_mm_id", "e2ds_url"})
    n_hn = sum(1 for r in cohort_rows if r["instrument"] == "HARPS_N")
    n_ca = sum(1 for r in cohort_rows if r["instrument"] == "CARMENES_VIS")
    n_ctrl = sum(1 for r in cohort_rows if r["role"] == "CONTROL")
    n_sci = sum(1 for r in cohort_rows if r["role"] == "SCIENCE")
    stars_25 = {r["canonical_target"] for r in cohort_rows}
    stars_10pc = {r["canonical_target"] for r in cohort_rows if r["within_10pc"] == "True"}
    excl_set = set(pe["excluded_dp_ids"]) | set(pe["format_check_excluded_dp_ids"])
    dp_overlap = {r["dp_id"] for r in cohort_rows} & excl_set
    ok2 = (
        ok2_nan
        and len(cohort_rows) == 183
        and n_hn == 64
        and n_ca == 119
        and n_ctrl == 34
        and n_sci == 149
        and len(stars_25) == 25
        and len(stars_10pc) == 18
        and orb_cat["n_campaigns"] == 10
        and pe["d084_dp_id_overlap_count"] == 0
        and len(dp_overlap) == 0
        and float(pe["min_brand_new_sky_separation_arcsec"]) >= 120.0
    )
    record(
        "C2_PRIOR_EXCLUSION_AND_COHORT_INTEGRITY",
        ok2,
        f"183 exp (64 HARPS-N + 119 CARMENES_VIS), 25 stars ({len(stars_10pc)} <10pc), 10 campaigns, min_sep={pe['min_brand_new_sky_separation_arcsec']}\", overlap={len(dp_overlap)}",
    )

    # C3: Bounded offline bundle size & structure
    bundle_p = HERE / "bounded_inputs" / "d084_bounded_bundle.json.gz"
    b_mib = bundle_p.stat().st_size / (1024.0 * 1024.0)
    with gzip.open(bundle_p, "rt", encoding="utf-8") as gz:
        bundle = json.load(gz)
    ok3 = (
        b_mib < 25.0
        and bundle.get("schema") == "SETI_D084_BOUNDED_REPRODUCIBLE_BUNDLE_V1"
        and len(bundle["provenance_rows"]) == 183
        and len(bundle["rv_anchor_bundle"]) == 183
        and len(bundle["calib_transient_patches"]) == 72
        and len(bundle["calib_persistent_patches"]) == 36
        and len(bundle["calib_keplerian_patches"]) == 9
        and len(bundle["calib_g5_2d_patches"]) == 72
        and len(bundle["calib_g6_patches"]) == 20
        and set(bundle["topo_excess_atlas_by_inst"].keys()) == {"HARPS_N", "CARMENES_VIS"}
    )
    record(
        "C3_BUNDLE_SIZE_AND_SCHEMA",
        ok3,
        f"d084_bounded_bundle.json.gz = {b_mib:.2f} MiB (<25.0 MiB), patches=(72,36,9,72,20)",
    )

    # C4: Exposure provenance & independent stdlib BERV check
    prov_rows = read_csv(HERE / "results" / "EXPOSURE_PROVENANCE_183.csv")
    ok4_nan, _ = check_no_nan_in_csv(prov_rows, HERE / "results" / "EXPOSURE_PROVENANCE_183.csv", {"radio_mm_id"})
    max_berv_diff = 0.0
    for pr in prov_rows:
        b_ref = stdlib_berv_kms(float(pr["s_ra_deg"]), float(pr["s_dec_deg"]), float(pr["mjd_mid"]), pr["instrument"])
        max_berv_diff = max(max_berv_diff, abs(b_ref - float(pr["berv_kms"])))
    ok4 = (
        ok4_nan
        and len(prov_rows) == 183
        and all(r["header_gate"] == "PASS" for r in prov_rows)
        and all(int(r["n_clean_rv_anchors"]) >= 2 for r in prov_rows)
        and max_berv_diff <= 0.60
    )
    record(
        "C4_EXPOSURE_PROVENANCE_AND_STDLIB_BERV",
        ok4,
        f"183 PASS rows, max |header_BERV - pure_stdlib_BERV| = {max_berv_diff:.4f} km/s (<= 0.60)",
    )

    # C5: RV anchors & star RV summaries
    rva_rows = read_csv(HERE / "results" / "STELLAR_RV_ANCHORS_2196.csv")
    rvs_rows = read_csv(HERE / "results" / "STAR_RV_SUMMARY_25.csv")
    ok5_a, _ = check_no_nan_in_csv(rva_rows, HERE / "results" / "STELLAR_RV_ANCHORS_2196.csv", {"best_rv_kms", "rel_depth", "min_sse"})
    ok5_s, _ = check_no_nan_in_csv(rvs_rows, HERE / "results" / "STAR_RV_SUMMARY_25.csv", {"radio_mm_id"})
    n_clean_anc = sum(1 for r in rva_rows if r["status"] == "CLEAN_ABSORPTION")
    abs_diffs = sorted(abs(float(r["empirical_minus_prior_kms"])) for r in rvs_rows)
    med_rv_diff = abs_diffs[len(abs_diffs) // 2]
    ok5 = (
        ok5_a
        and ok5_s
        and len(rva_rows) == 2196
        and len(rvs_rows) == 25
        and n_clean_anc >= 1500
        and med_rv_diff <= 1.5
    )
    record(
        "C5_RV_ANCHORING_AND_STAR_SUMMARY",
        ok5,
        f"2196 anchors ({n_clean_anc} clean), 25 star summaries, median |emp - prior| = {med_rv_diff:.4f} km/s",
    )

    # C6: 2,151 prospective synthetic calibration trials
    inj_rows = read_csv(HERE / "results" / "INJECTION_RECOVERY_1620.csv")
    kep_rows = read_csv(HERE / "results" / "KEPLERIAN_TRACK_CALIBRATION_135.csv")
    ccd_rows = read_csv(HERE / "results" / "DETECTOR_CCD_CALIBRATION_216.csv")
    g6_rows = read_csv(HERE / "results" / "G6_TOPO_COINCIDENCE_CALIBRATION_180.csv")
    cb_rows = read_csv(HERE / "results" / "CALIBRATION_COMPLETENESS_BY_BAND.csv")
    ok6_n = (
        check_no_nan_in_csv(inj_rows, HERE / "results" / "INJECTION_RECOVERY_1620.csv", {"fitted_fwhm_ratio"})[0]
        and check_no_nan_in_csv(kep_rows, HERE / "results" / "KEPLERIAN_TRACK_CALIBRATION_135.csv", {"kplanet_dedop_fwhm_ratio"})[0]
        and check_no_nan_in_csv(ccd_rows, HERE / "results" / "DETECTOR_CCD_CALIBRATION_216.csv", {"primary_order", "primary_native_px", "cos_1d_11px", "hotpx_ratio", "far_wing_34_ratio"})[0]
        and check_no_nan_in_csv(g6_rows, HERE / "results" / "G6_TOPO_COINCIDENCE_CALIBRATION_180.csv", set())[0]
        and check_no_nan_in_csv(cb_rows, HERE / "results" / "CALIBRATION_COMPLETENESS_BY_BAND.csv", set())[0]
    )
    t8 = [r for r in inj_rows if r["mode"] == "CHANNEL_T_TRANSIENT_1EPOCH" and float(r["sigma_mult"]) >= 8.0]
    p9 = [r for r in inj_rows if r["mode"] == "CHANNEL_P_PERSISTENT_5EPOCH" and float(r["sigma_mult"]) >= 9.0]
    k65 = [r for r in kep_rows if float(r["exp_sigma_mult"]) >= 6.5]
    k_td_rate = sum(1 for r in k65 if r["tdiff_uncomp_recovered"] == "True") / max(1, len(k65))
    k_kp_rate = sum(1 for r in k65 if r["kplanet_dedop_recovered"] == "True") / max(1, len(k65))
    g5_l = sum(1 for r in ccd_rows if r["trial_class"] == "TRUE_FIBER_LASER" and r["g5_pass"] == "True") / 72.0
    g5_h = sum(1 for r in ccd_rows if r["trial_class"] == "CCD_COSMIC_HOT_PIXEL" and r["g5_pass"] == "False") / 72.0
    g5_p = sum(1 for r in ccd_rows if r["trial_class"] == "BROAD_BANDHEAD_PLATEAU" and r["g5_pass"] == "False") / 72.0
    g6_t = sum(1 for r in g6_rows if r["trial_class"] == "TRUE_BARYCENTRIC_STELLAR_LASER" and r["g6_pass"] == "True") / 60.0
    g6_oh = sum(1 for r in g6_rows if r["trial_class"] == "UNLISTED_STATIONARY_SKY_OH_LINE" and r["g6_pass"] == "False") / 60.0
    g6_px = sum(1 for r in g6_rows if r["trial_class"] == "STATIONARY_CCD_WARM_PIXEL_DEFECT" and r["g6_pass"] == "False") / 60.0
    core_bands = {"H6_YELLOW_5800", "H7_CONT_6100", "H8_HENE_6329", "H9_RED_6702", "C1_NDYAG2X_5321", "C2_CONT_6100", "C3_HENE_6329"}
    t8_core = [r for r in t8 if r["band_id"] in core_bands]
    t8_core_rate = sum(1 for r in t8_core if r["recovered"] == "True") / max(1, len(t8_core))
    t8_rate = sum(1 for r in t8 if r["recovered"] == "True") / max(1, len(t8))
    p9_rate = sum(1 for r in p9 if r["recovered"] == "True") / max(1, len(p9))
    total_trials = len(inj_rows) + len(kep_rows) + len(ccd_rows) + len(g6_rows)
    ok6 = (
        ok6_n
        and total_trials == 2151
        and len(cb_rows) == 180
        and t8_core_rate >= 0.88
        and t8_rate >= 0.60
        and p9_rate >= 0.75
        and k_kp_rate > k_td_rate
        and k_kp_rate >= 0.18
        and g5_l >= 0.85
        and g5_h == 1.0
        and g5_p >= 0.95
        and g6_t >= 0.60
        and g6_oh == 1.0
        and g6_px == 1.0
    )
    record(
        "C6_CALIBRATION_2151_TRIALS",
        ok6,
        f"2151 trials: coreOptT>=8sig={t8_core_rate:.3f}, T>=8sig={t8_rate:.3f}, P>=9sig={p9_rate:.3f}, Kep(T_DIFF={k_td_rate:.3f}->K_PL={k_kp_rate:.3f}), G5=({g5_l:.3f},{g5_h:.3f},{g5_p:.3f}), G6=({g6_t:.3f},{g6_oh:.3f},{g6_px:.3f})",
    )

    # C7: Four-generation cascade & ledger parity
    bench_rows = read_csv(HERE / "results" / "FOUR_GEN_BENCHMARK_183.csv")
    led_rows = read_csv(HERE / "results" / "V3_5_CANDIDATE_LEDGER.csv")
    summary = json.loads((HERE / "results" / "SUMMARY.json").read_text(encoding="utf-8"))
    ok7_b, _ = check_no_nan_in_csv(bench_rows, HERE / "results" / "FOUR_GEN_BENCHMARK_183.csv", set())
    ok7_l, _ = check_no_nan_in_csv(
        led_rows,
        HERE / "results" / "V3_5_CANDIDATE_LEDGER.csv",
        {"fwhm_over_lsf", "primary_order", "primary_native_px", "primary_native_fn_pk3", "primary_template_dip_frac", "primary_eta_1px", "overlap_tested", "g5_cos11", "g5_hotpx_ratio", "g5_far_wing_ratio"},
    )
    fc = summary["false_alarm_cascade"]
    v2_fa = sum(int(r["v2_accepted_false_alarms"]) for r in bench_rows)
    n_pre_g6 = sum(1 for r in led_rows if r["pre_g6_qualified"] == "True")
    n_g6_veto = sum(1 for r in led_rows if r["pre_g6_qualified"] == "True" and r["g6_pass"] == "False")
    n_qual_ctrl = sum(1 for r in led_rows if r["role"] == "CONTROL" and r["qualified_v35_laser"] == "True")
    n_qual_sci = sum(1 for r in led_rows if r["role"] == "SCIENCE" and r["qualified_v35_laser"] == "True")
    ok7 = (
        ok7_b
        and ok7_l
        and len(bench_rows) == 183
        and v2_fa == fc["v2_legacy_false_alarms"]
        and v2_fa > 0
        and len(led_rows) == fc["v35_total_ledger_g1_candidates"]
        and n_pre_g6 == fc["v35_pre_g6_passed_g1_to_g5"]
        and n_g6_veto == fc["v35_vetoed_by_g6_coincidence_gate"]
        and n_qual_ctrl == fc["automated_qualified_control"]
        and n_qual_sci == fc["automated_qualified_science"]
    )
    record(
        "C7_FOUR_GEN_BENCHMARK_AND_CASCADE",
        ok7,
        f"V2={v2_fa} -> V3.5 G1={len(led_rows)} -> preG6={n_pre_g6} -> G6_vetoed={n_g6_veto} -> qual=(ctrl={n_qual_ctrl}, sci={n_qual_sci})",
    )

    # C8: Forensic diagnosis JSON & zero verified ETI detections
    for_doc = json.loads((HERE / "results" / "FORENSIC_NORTHERN_CASCADE_DIAGNOSIS.json").read_text(encoding="utf-8"))
    for_aud = json.loads((HERE / "FORENSIC_CANDIDATE_AUDIT_D084.json").read_text(encoding="utf-8"))
    aud_cands = for_aud["post_g6_candidates_forensic_classifications"]
    aud_ids = {x["candidate_id"] for x in aud_cands}
    post_ids = {x["candidate_id"] for x in for_doc["post_g6_qualified"]}
    ok8 = (
        for_doc["pre_g6_count"] == len(for_doc["vetoed_by_g6"]) + len(for_doc["post_g6_qualified"])
        and for_doc["pre_g6_count"] == n_pre_g6
        and aud_ids == post_ids
        and all(x.get("eti_plausible") is False for x in aud_cands)
        and for_aud["verified_eti_detections"] == 0
        and fc["verified_eti_detections"] == 0
    )
    record(
        "C8_FORENSIC_CASCADE_DIAGNOSIS_AND_ZERO_ETI",
        ok8,
        f"pre_g6={for_doc['pre_g6_count']} (G6 vetoed={len(for_doc['vetoed_by_g6'])}, post-G6 audited={len(aud_cands)}), verified_eti_detections=0",
    )

    # C9: 10 orbital campaigns independent Keplerian Kp verification
    orb_rows = read_csv(HERE / "results" / "ORBITAL_CAMPAIGN_RESULTS_10.csv")
    ok9_n, _ = check_no_nan_in_csv(orb_rows, HERE / "results" / "ORBITAL_CAMPAIGN_RESULTS_10.csv", set())
    max_kp_err = 0.0
    for r in orb_rows:
        st = r["star"]
        c_meta = orb_cat["campaigns"][st]
        m_st = float(c_meta["st_mass_msun"])
        p_d = float(c_meta["orbper_days"])
        ecc = float(c_meta["ecc"])
        kp_std = ((2.0 * math.pi * G_SI * m_st * M_SUN_KG / (p_d * DAY_S)) ** (1.0 / 3.0)) / math.sqrt(max(1e-6, 1.0 - ecc ** 2)) / 1000.0
        max_kp_err = max(max_kp_err, abs(kp_std - float(r["kp_kms"])))
    ok9 = (
        ok9_n
        and len(orb_rows) == 10
        and sum(1 for r in orb_rows if r["role"] == "CONTROL") == 2
        and sum(1 for r in orb_rows if r["role"] == "SCIENCE") == 8
        and max_kp_err <= 0.05
        and all(int(r["n_in_window"]) >= 2 and int(r["n_out_of_window"]) >= 2 for r in orb_rows)
    )
    record(
        "C9_ORBITAL_CAMPAIGNS_10_CHECK",
        ok9,
        f"10 campaigns (2 ctrl + 8 sci), max |Kp_stdlib - Kp_csv| = {max_kp_err:.5f} km/s",
    )

    # C10: 189 science upper-limit cells independent Planck/Gaia/2MASS recomputation
    ul_rows = read_csv(HERE / "results" / "STAR_UPPER_LIMITS_189.csv")
    ok10_n, _ = check_no_nan_in_csv(ul_rows, HERE / "results" / "STAR_UPPER_LIMITS_189.csv", {"radio_mm_id"})
    max_rel_p_err = 0.0
    for u in ul_rows:
        lam_a = float(u["wave_bary_vac_A"])
        amp = float(u["amp_rel_8sigma_lim"])
        res = 115000.0 if u["instrument"] == "HARPS_N" else 94600.0
        teff = float(u["teff_k"])
        dist_pc = float(u["dist_pc"])
        if lam_a < RADIOMETRIC_GJ_SPLIT_A:
            piv, zp, mag = GAIA_G_PIVOT_A, GAIA_G_ZP_FLAM, float(u["phot_g_mag"])
        else:
            piv, zp, mag = TWOMASS_J_PIVOT_A, TWOMASS_J_ZP_FLAM, float(u["j_mag"])
        b_rat = ((piv / lam_a) ** 5) * math.expm1(HC_OVER_K_A_K / (piv * teff)) / math.expm1(HC_OVER_K_A_K / (lam_a * teff))
        flam = zp * (10.0 ** (-0.4 * mag)) * b_rat
        ew_a = math.sqrt(math.pi / (4.0 * math.log(2.0))) * amp * (lam_a / res)
        l_iso = 4.0 * math.pi * ((dist_pc * PC_CM) ** 2) * (flam * ew_a) * 1e-7
        p10_std = l_iso / ((math.pi * 10.0 / (lam_a * 1e-10)) ** 2)
        p10_csv = float(u["p_beam_10m_w"])
        max_rel_p_err = max(max_rel_p_err, abs(p10_std - p10_csv) / max(1e-30, p10_csv))
    ok10 = ok10_n and len(ul_rows) == 189 and max_rel_p_err < 1e-5
    record(
        "C10_UPPER_LIMITS_189_GAIA_2MASS_RECOMPUTATION",
        ok10,
        f"189 cells (0 NaNs), max relative diff vs pure-stdlib Gaia/2MASS Planck inversion = {max_rel_p_err:.2e}",
    )

    # C11: Unified 125-star & 53-star < 10 pc synthesis
    s53 = read_csv(HERE / "results" / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_53STARS.csv")
    u125 = read_csv(HERE / "results" / "UNIFIED_PANCHROMATIC_V3_SYNTHESIS_125STARS.csv")
    opt_blank = {"j_mag", "h_mag", "ks_mag", "min_optical_10m_kw", "min_nir_yjh_10m_kw", "min_kband_10m_kw", "p_1064nm_10m_kw", "p_1550nm_10m_kw", "p_2040nm_tm_10m_kw", "p_2097nm_hoyag_10m_kw", "min_panchromatic_10m_kw"}
    ok11_53, _ = check_no_nan_in_csv(s53, HERE / "results" / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_53STARS.csv", opt_blank)
    ok11_125, _ = check_no_nan_in_csv(u125, HERE / "results" / "UNIFIED_PANCHROMATIC_V3_SYNTHESIS_125STARS.csv", opt_blank)
    u_stars = [r["star"] for r in u125]
    tot_exp_all = sum(int(r["n_exposures_total"]) for r in u125)
    ok11 = (
        ok11_53
        and ok11_125
        and len(u125) == 125
        and len(set(u_stars)) == 125
        and len(s53) == 53
        and all(float(r["dist_pc"]) < 10.0 for r in s53)
        and tot_exp_all == 832
        and all(int(r["verified_eti_detections"]) == 0 for r in u125)
    )
    record(
        "C11_UNIFIED_125STAR_AND_53_10PC_SYNTHESIS",
        ok11,
        f"125 unique stars (100 South + 25 North), 53 < 10 pc, 832 exposures, 0 ETI detections",
    )

    # C12: Unified 136-system multi-messenger synthesis & strict zero-NaN JSON
    mm136 = read_csv(HERE / "results" / "MULTIMESSENGER_ECHELLE_RADIO_TESS_136SYSTEMS.csv")
    ok12_n, _ = check_no_nan_in_csv(
        mm136,
        HERE / "results" / "MULTIMESSENGER_ECHELLE_RADIO_TESS_136SYSTEMS.csv",
        {"dist_pc", "within_10pc", "echelle_phases", "echelle_instruments", "min_echelle_10m_kw", "radio_milestone", "radio_facility", "radio_snr40_recovery", "lightsail_milestone"},
    )
    n_ovlp = sum(1 for r in mm136 if r["multimessenger_overlap"] == "True")
    syn_mm = summary["multimessenger_136system_synthesis"]
    ok12 = (
        ok12_n
        and len(mm136) == 136
        and n_ovlp == 13
        and syn_mm["distinct_stellar_systems_total"] == 136
        and syn_mm["direct_multimessenger_overlap_count"] == 13
        and syn_mm["verified_eti_detections_all_modalities"] == 0
    )
    record(
        "C12_MULTIMESSENGER_136SYSTEM_SYNTHESIS",
        ok12,
        f"136 distinct systems, {n_ovlp} direct echelle+radio/TESS overlaps, 0 ETI detections",
    )

    n_pass = sum(1 for c in checks if c["status"] == "PASS")
    audit_out = {
        "schema": "D084_STDLIB_AUDIT_SUMMARY",
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
