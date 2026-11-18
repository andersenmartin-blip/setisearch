#!/usr/bin/env python3
"""
Pure-Stdlib Independent Audit Suite for Phase D087
(SPACE_UV_STIS_AND_FARRED_V3_8).

Runs strictly with `/usr/bin/python3 -S` (no third-party site-packages)
and executes 15 deterministic end-to-end checks C1..C15 across lock chronology,
SHA-256 integrity, bounded bundle size, stdlib BERV/LEO-HELIO kinematics,
2,697 synthetic calibration trials, D086 G4_V38 Fiber-B regression (577 -> 0),
cascade/COMB_V4_1/forensic parity, Keplerian Kp recomputation, direct CALSTIS
& dual G_RP/2MASS-J upper-limit recomputation, and cumulative 200-star /
103-<10pc / 17-bridge / 206-system multi-messenger synthesis.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WS = Path(__file__).resolve().parent
RESULTS = WS / "results"

C_KMS = 299792.458
PARANAL_LAT_DEG = -24.6272
PARANAL_LON_DEG = -70.4042
GAIA_G_PIVOT_A = 6217.6
GAIA_G_ZP_FLAM = 2.50386e-9
GAIA_GRP_PIVOT_A = 7769.0
GAIA_GRP_ZP_FLAM = 1.29303e-9
TWOMASS_J_PIVOT_A = 12350.0
TWOMASS_J_ZP_FLAM = 3.129e-10
HC_OVER_K = 1.438776877e8
PC_CM = 3.0856775814913673e18
G_SI = 6.67430e-11
M_SUN_KG = 1.98847e30
DAY_S = 86400.0


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def median_list(vals: list[float]) -> float:
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return 0.0
    m = n // 2
    return s[m] if (n % 2 == 1) else 0.5 * (s[m - 1] + s[m])


def stdlib_earth_helio_rv_kms(ra_deg: float, dec_deg: float, mjd_utc: float) -> float:
    jd = float(mjd_utc) + 2400000.5
    d = jd - 2451545.0
    t_c = d / 36525.0
    g = math.radians((357.5291092 + 35999.0502909 * t_c) % 360.0)
    l0 = math.radians((280.46646 + 36000.76983 * t_c) % 360.0)
    c_eq = math.radians((1.914602 - 0.004817 * t_c) * math.sin(g) + 0.019993 * math.sin(2.0 * g))
    lam_sun = l0 + c_eq
    e_orb = 0.016708634
    v_earth = 29.7847
    eps = math.radians(23.4392911 - 0.0130042 * t_c)
    pi_sun = math.radians((282.937348 + 1.71953 * t_c) % 360.0)
    lam_e = lam_sun + math.pi
    pi_e = pi_sun + math.pi
    v0 = v_earth / math.sqrt(1.0 - e_orb * e_orb)
    vx_ecl = v0 * (-math.sin(lam_e) - e_orb * math.sin(pi_e))
    vy_ecl = v0 * (math.cos(lam_e) + e_orb * math.cos(pi_e))
    vx_eq = vx_ecl
    vy_eq = vy_ecl * math.cos(eps)
    vz_eq = vy_ecl * math.sin(eps)
    ra, dec = math.radians(ra_deg), math.radians(dec_deg)
    return vx_eq * math.cos(dec) * math.cos(ra) + vy_eq * math.cos(dec) * math.sin(ra) + vz_eq * math.sin(dec)


def stdlib_observatory_berv_kms(ra_deg: float, dec_deg: float, mjd_utc: float, lat_deg: float = PARANAL_LAT_DEG, lon_deg: float = PARANAL_LON_DEG) -> float:
    jd = float(mjd_utc) + 2400000.5
    d = jd - 2451545.0
    t_c = d / 36525.0
    v_orb = stdlib_earth_helio_rv_kms(ra_deg, dec_deg, mjd_utc)
    gmst_deg = (280.46061837 + 360.98564736629 * d + 0.000387933 * t_c * t_c - (t_c ** 3) / 38710000.0) % 360.0
    lst = math.radians((gmst_deg + lon_deg) % 360.0)
    ha = lst - math.radians(ra_deg)
    v_eq_rot = 0.4651011
    return v_orb - v_eq_rot * math.cos(math.radians(lat_deg)) * math.cos(math.radians(dec_deg)) * math.sin(ha)


def stdlib_kp_kms(st_mass_msun: float, orbper_days: float, ecc: float = 0.0) -> float:
    p_s = orbper_days * DAY_S
    m_kg = st_mass_msun * M_SUN_KG
    v_orb = ((2.0 * math.pi * G_SI * m_kg / p_s) ** (1.0 / 3.0)) / 1000.0
    if 0.0 < ecc < 1.0:
        v_orb /= math.sqrt(1.0 - ecc * ecc)
    return v_orb


def run_audit() -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add_check(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    # Load core docs
    lock = json.loads((WS / "METHOD_LOCK.json").read_text(encoding="utf-8"))
    rec = json.loads((WS / "LOCK_RECEIPT.json").read_text(encoding="utf-8"))
    dl_rec = json.loads((WS / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json").read_text(encoding="utf-8"))
    summary = json.loads((RESULTS / "SUMMARY.json").read_text(encoding="utf-8"))
    excl = json.loads((WS / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    orb_doc = json.loads((WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").read_text(encoding="utf-8"))
    forensic = json.loads((WS / "FORENSIC_CANDIDATE_AUDIT_D087.json").read_text(encoding="utf-8"))

    # C1: Chronology & hashes
    impl_lock_p = WS / "IMPLEMENTATION_LOCK.json"
    hashes_ok = True
    if impl_lock_p.exists():
        il = json.loads(impl_lock_p.read_text(encoding="utf-8"))
        for k, sh in il["post_ingestion_hashes"].items():
            if not (WS / k).exists() or sha256_file(WS / k) != sh:
                hashes_ok = False
        # Verify frozen detector, cohort, and metadata still match original METHOD_LOCK exactly
        for k in ("v3_8_detector.py", "FROZEN_COHORT_D087.csv", "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json", "PRIOR_EXCLUSION_VERIFICATION.json", "PRIOR_V3_PHASES_SNAPSHOT.json", "MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json"):
            if sha256_file(WS / k) != lock["locked_file_hashes"][k]:
                hashes_ok = False
    else:
        for k, sh in lock["locked_file_hashes"].items():
            if not (WS / k).exists() or sha256_file(WS / k) != sh:
                hashes_ok = False
    t_lock = datetime.strptime(lock["locked_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    t_dl = datetime.strptime(dl_rec["first_science_download_utc"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    dt_dl = (t_dl - t_lock).total_seconds()
    c1_ok = (
        hashes_ok
        and (not lock["inputs_directory_existed_at_lock_time"])
        and (not rec["inputs_directory_present_at_lock"])
        and dt_dl >= 3.0
        and dl_rec["method_lock_sha256"] == sha256_file(WS / "METHOD_LOCK.json")
    )
    add_check("C1_PROSPECTIVE_CHRONOLOGY_AND_HASHES", c1_ok, f"lock={lock['locked_utc']}, dt_dl={dt_dl:.1f}s")

    # C2: Cohort & exclusion
    cohort = load_csv(WS / "FROZEN_COHORT_D087.csv")
    uves_j_ok = all(r["j_mag"] != "" for r in cohort if r["instrument"] == "UVES_RED")
    ctrl_exo_ok = all(int(r["n_exoplanets"]) == 0 for r in cohort if r["role"] == "CONTROL")
    c2_ok = (
        len(cohort) == 201
        and len({r["canonical_target"] for r in cohort}) == 33
        and excl["d087_brand_new_unique_stars"] == 25
        and excl["d087_panchromatic_bridge_stars"] == 8
        and excl["d087_brand_new_within_10pc"] == 13
        and excl["d087_dp_id_overlap_count"] == 0
        and excl["min_brand_new_sky_separation_arcsec"] >= 3000.0
        and "o45931020" in excl["excluded_dp_ids"]
        and any("BD+28D4211" in t for t in excl["format_check_excluded_targets"])
        and uves_j_ok
        and ctrl_exo_ok
    )
    add_check(
        "C2_PRIOR_EXCLUSION_AND_COHORT_INTEGRITY",
        c2_ok,
        f"{len(cohort)} exp, 33 stars (25 new [13 <10pc] + 8 bridge), min_sep={excl['min_brand_new_sky_separation_arcsec']:.2f}\", dp_overlap={excl['d087_dp_id_overlap_count']}",
    )

    # C3: Bundle size & schema
    bp = WS / "bounded_inputs" / "d087_bounded_bundle.json.gz"
    b_bytes = bp.stat().st_size
    b_mib = b_bytes / (1024.0 * 1024.0)
    with gzip.open(bp, "rt", encoding="utf-8") as f:
        bundle = json.load(f)
    pt = (
        len(bundle["calib_transient_patches"]),
        len(bundle["calib_persistent_patches"]),
        len(bundle["calib_keplerian_patches"]),
        len(bundle["calib_g4g5_patches"]),
        len(bundle["calib_g6_patches"]),
        len(bundle["calib_comb_patches"]),
    )
    c3_ok = b_mib < 25.0 and pt == (72, 36, 9, 72, 20, 18) and len(bundle["d086_fiberb_regression_577"]) == 577
    add_check("C3_BUNDLE_SIZE_AND_SCHEMA", c3_ok, f"d087_bounded_bundle.json.gz = {b_mib:.2f} MiB (<25.0 MiB), patches={pt}")

    # C4: Exposure provenance & stdlib BERV/LEO-HELIO
    prov = load_csv(RESULTS / "EXPOSURE_PROVENANCE_201.csv")
    max_ground_d = 0.0
    max_stis_d = 0.0
    max_recomp_err = 0.0
    for r in prov:
        ra, dec, mjd = float(r["s_ra_deg"]), float(r["s_dec_deg"]), float(r["mjd_mid"])
        berv = float(r["berv_kms"])
        if r["instrument"] == "HST_STIS":
            ref = stdlib_earth_helio_rv_kms(ra, dec, mjd)
            d = abs(berv - ref)
            max_stis_d = max(max_stis_d, d)
        else:
            ref = stdlib_observatory_berv_kms(ra, dec, mjd)
            d = abs(berv - ref)
            max_ground_d = max(max_ground_d, d)
        max_recomp_err = max(max_recomp_err, abs(d - float(r["berv_diff_stdlib_kms"])))
    c4_ok = (
        len(prov) == 201
        and all(r["header_gate"] == "PASS" for r in prov)
        and max_ground_d <= 0.50
        and max_stis_d <= 8.50
        and max_recomp_err <= 0.01
    )
    add_check(
        "C4_EXPOSURE_PROVENANCE_AND_STDLIB_BERV",
        c4_ok,
        f"201 PASS rows, max ground |BERV-stdlib|={max_ground_d:.4f} (<=0.50), STIS LEO={max_stis_d:.4f} km/s (<=8.50)",
    )

    # C5: RV anchoring 2596 & 33 stars
    rv_sum = load_csv(RESULTS / "STAR_RV_SUMMARY_33.csv")
    anc_p = RESULTS / f"STELLAR_RV_ANCHORS_{summary['rv_anchoring']['total_anchor_fits']}.csv"
    anc_rows = load_csv(anc_p)
    med_diff = median_list([abs(float(r["empirical_minus_prior_kms"])) for r in rv_sum])
    c5_ok = (
        len(anc_rows) == 2596
        and len(rv_sum) == 33
        and abs(med_diff - float(summary["rv_anchoring"]["median_abs_empirical_minus_prior_kms"])) <= 1e-3
    )
    add_check("C5_RV_ANCHORING_2596_AND_33STARS", c5_ok, f"{len(anc_rows)} anchors ({summary['rv_anchoring']['clean_absorption_fits']} clean), 33 star summaries, med|emp-prior|={med_diff:.4f} km/s")

    # C6: 1,971 single-line, Keplerian, G4G5 trials
    inj = load_csv(RESULTS / "INJECTION_RECOVERY_1620.csv")
    kep = load_csv(RESULTS / "KEPLERIAN_TRACK_CALIBRATION_135.csv")
    g45 = load_csv(RESULTS / "DETECTOR_V38_G4G5_CALIBRATION_216.csv")
    t_8 = [r for r in inj if r["mode"] == "CHANNEL_T_TRANSIENT_1EPOCH" and float(r["sigma_mult"]) >= 8.0]
    p_8 = [r for r in inj if r["mode"] == "CHANNEL_P_PERSISTENT_COADD" and float(r["sigma_mult"]) >= 8.0]
    t8_r = sum(1 for r in t_8 if r["recovered"] == "True") / len(t_8)
    p8_r = sum(1 for r in p_8 if r["recovered"] == "True") / len(p_8)
    g45_t = [r for r in g45 if r["trial_class"] == "TRUE_LSF_LASER"]
    g45_s = [r for r in g45 if r["trial_class"] == "COSMIC_SINGLE_PX_SPIKE"]
    g45_p = [r for r in g45 if r["trial_class"] == "WIDE_SCATTERING_PLATEAU"]
    g45_t_r = sum(1 for r in g45_t if r["g45_pass"] == "True") / len(g45_t)
    g45_s_r = sum(1 for r in g45_s if r["g45_pass"] == "False") / len(g45_s)
    g45_p_r = sum(1 for r in g45_p if r["g45_pass"] == "False") / len(g45_p)
    kep65 = [r for r in kep if float(r["exp_sigma_mult"]) >= 6.5]
    kp_r = sum(1 for r in kep65 if r["kplanet_dedop_recovered"] == "True") / len(kep65)
    c6_ok = (
        len(inj) == 1620 and len(kep) == 135 and len(g45) == 216
        and t8_r >= 0.80 and p8_r >= 0.80 and g45_t_r >= 0.90 and g45_s_r == 1.0 and g45_p_r == 1.0 and kp_r > 0.0
    )
    add_check("C6_SINGLELINE_KEPLERIAN_G4G5_CALIB_1971", c6_ok, f"1971 trials: T>=8s={t8_r:.3f}, P>=8s={p8_r:.3f}, K_PLANET={kp_r:.3f}, G4G5=({g45_t_r:.3f},{g45_s_r:.3f},{g45_p_r:.3f})")

    # C7: G6 240 trials
    g6 = load_csv(RESULTS / "G6_SPARSE_VS_DENSE_CALIBRATION_240.csv")
    g6_tr = [r for r in g6 if r["trial_class"] == "TRUE_BARYCENTRIC_STELLAR_LASER"]
    g6_oh = [r for r in g6 if r["trial_class"] == "UNLISTED_STATIONARY_SKY_OH_LINE"]
    g6_px = [r for r in g6 if r["trial_class"] == "STATIONARY_DETECTOR_WARM_PIXEL"]
    g6_in = [r for r in g6 if r["trial_class"] == "INTRA_STAR_BERV_STATIONARY_GHOST"]
    r_tr = sum(1 for r in g6_tr if r["g6_v36_sparse_pass"] == "True") / len(g6_tr)
    r_oh = sum(1 for r in g6_oh if r["g6_v36_sparse_pass"] == "False") / len(g6_oh)
    r_px = sum(1 for r in g6_px if r["g6_v36_sparse_pass"] == "False") / len(g6_px)
    r_in = sum(1 for r in g6_in if r["g6_v36_sparse_pass"] == "False") / len(g6_in)
    c7_ok = len(g6) == 240 and r_tr >= 0.95 and r_oh == 1.0 and r_px == 1.0 and r_in == 1.0
    add_check("C7_G6_SPARSE_VS_DENSE_CALIB_240", c7_ok, f"240 trials: true={r_tr:.3f}, OH={r_oh:.3f}, px={r_px:.3f}, intraBERV={r_in:.3f}")

    # C8: COMB_V4_1 486 trials + 2,697 sum
    ccal = load_csv(RESULTS / "COMB_V4_1_CALIBRATION_486.csv")
    c_1l = [r for r in ccal if r["trial_class"] == "SINGLE_BRIGHT_LINE_MASQUERADE"]
    c_tp = [r for r in ccal if r["trial_class"] == "STATIONARY_TOPO_ROVIB_PSEUDOCOMB"]
    c_df = [r for r in ccal if r["trial_class"] == "DENSE_MOLECULAR_FOREST_PSEUDOCOMB"]
    c_6t = [r for r in ccal if r["trial_class"] == "TRUE_6TOOTH_STELLAR_COMB" and float(r["tooth_snr_inj"]) >= 3.8]
    r_6t = sum(1 for r in c_6t if r["comb_v41_hit"] == "True") / len(c_6t)
    fpr_1l = sum(1 for r in c_1l if r["comb_v41_hit"] == "True") / len(c_1l)
    fpr_tp = sum(1 for r in c_tp if r["comb_v41_hit"] == "True") / len(c_tp)
    fpr_df41 = sum(1 for r in c_df if r["comb_v41_hit"] == "True") / len(c_df)
    fpr_df4 = sum(1 for r in c_df if r["comb_v4_hit"] == "True") / len(c_df)
    tot_cal = len(inj) + len(kep) + len(g45) + len(g6) + len(ccal)
    c8_ok = len(ccal) == 486 and tot_cal == 2697 and fpr_1l == 0.0 and fpr_tp == 0.0 and fpr_df41 == 0.0 and r_6t >= 0.45
    add_check("C8_COMB_V4_1_CALIBRATION_486", c8_ok, f"486 trials (tot={tot_cal}): 6t={r_6t:.3f}, 1L={fpr_1l:.3f}, topo={fpr_tp:.3f}, forest=(V4={fpr_df4:.3f}->V4.1={fpr_df41:.3f})")

    # C9: D086 G4_V38 Fiber-B 577->0 regression
    reg = load_csv(RESULTS / "D086_G4_V38_FIBERB_REGRESSION_577.csv")
    surv = 0
    for b_rec, r_row in zip(bundle["d086_fiberb_regression_577"], reg):
        ratio = float(b_rec["fb_pk"]) / max(1e-6, float(b_rec["fa_med"]))
        is_cal = any(t in b_rec["dpr_or_calsel"].upper() for t in ("WAVE", "FP", "THAR", "CAL"))
        retained = not (is_cal and ratio >= 1.5)
        if retained:
            surv += 1
        if r_row["g4_v38_retained"] != str(retained):
            surv += 999
    c9_ok = len(reg) == 577 and surv == 0
    add_check("C9_D086_G4_V38_FIBERB_REGRESSION_577", c9_ok, f"D086 Fiber-B 577 false alarms -> {surv} survivors under G4_V38")

    # C10: Cascade & COMB_V4_1 parity
    ledger = load_csv(RESULTS / "V3_8_CANDIDATE_LEDGER.csv")
    four_g = load_csv(RESULTS / "FOUR_GEN_BENCHMARK_201.csv")
    comb_st = load_csv(RESULTS / "COMB_V4_1_STAR_RESULTS_33.csv")
    comb_c = load_csv(RESULTS / "COMB_V4_1_CANDIDATES.csv")
    fc = summary["false_alarm_cascade"]
    q_cnt = sum(1 for r in ledger if r["qualified_v38_laser"] == "True")
    c10_ok = (
        sum(int(r["v2_accepted_false_alarms"]) for r in four_g) == fc["v2_legacy_false_alarms"]
        and sum(int(r["v38_g1_candidates"]) for r in four_g) == fc["v38_total_ledger_g1_candidates"]
        and sum(int(r["v38_pre_g6"]) for r in four_g) == fc["v38_pre_g6_passed_g1_to_g5"]
        and sum(int(r["v38_post_g6_qualified"]) for r in four_g) == q_cnt
        and len(comb_st) == 33
        and sum(int(r["comb_v41_candidates"]) for r in comb_st) == len(comb_c) == fc["comb_v41_automated_candidates"]
        and fc["verified_eti_detections"] == 0
    )
    add_check("C10_CASCADE_AND_COMB_V4_1_PARITY", c10_ok, f"V2={fc['v2_legacy_false_alarms']} -> G1={fc['v38_total_ledger_g1_candidates']} -> preG6={fc['v38_pre_g6_passed_g1_to_g5']} -> postG6={q_cnt}, COMB_V4_1={len(comb_c)}, ETI=0")

    # C11: Forensic audit & 0 ETI
    f_s = forensic["post_g6_singleline_forensic_classifications"]
    f_c = forensic["comb_v41_forensic_classifications"]
    c11_ok = (
        len(f_s) == q_cnt
        and len(f_c) == len(comb_c)
        and forensic["verified_eti_detections"] == 0
        and all((not r["eti_plausible"]) and r["forensic_classification"] and r["forensic_rationale"] for r in f_s + f_c)
    )
    add_check("C11_FORENSIC_AUDIT_AND_ZERO_ETI", c11_ok, f"post-G6={len(f_s)}, COMB_V4_1={len(f_c)} forensically audited, verified_eti=0")

    # C12: Orbital campaigns 10 check
    orb_csv = load_csv(RESULTS / "ORBITAL_CAMPAIGN_RESULTS_10.csv")
    max_kp_diff = 0.0
    for row in orb_csv:
        st = row["star"]
        camp = orb_doc["campaigns"][st]
        kp_std = stdlib_kp_kms(camp["st_mass_msun"], camp["orbper_days"], camp["ecc"])
        max_kp_diff = max(max_kp_diff, abs(kp_std - float(row["kp_kms"])))
    c12_ok = (
        len(orb_csv) == 10
        and sum(1 for r in orb_csv if r["role"] == "CONTROL") == 3
        and sum(1 for r in orb_csv if r["role"] == "SCIENCE") == 7
        and all(int(r["n_in_window"]) == 4 and int(r["n_out_of_window"]) == 4 and int(r["verified_eti_detections"]) == 0 for r in orb_csv)
        and max_kp_diff <= 0.01
    )
    add_check("C12_ORBITAL_CAMPAIGNS_10_CHECK", c12_ok, f"10 campaigns (3 ctrl + 7 sci, 4 IN + 4 OUT), max |Kp_std - Kp_csv| = {max_kp_diff:.5f} km/s")

    # C13: Upper limits independent pure-stdlib recomputation (direct CALSTIS + dual G_RP/2MASS-J + G)
    ul_csv = load_csv(RESULTS / "STAR_UPPER_LIMITS_D087.csv")
    max_rel_ul = 0.0
    for row in ul_csv:
        cw = float(row["wave_bary_a"])
        r_pow = float(row["resolving_power"])
        dist = float(row["dist_pc"])
        teff = float(row["teff_k"])
        amp_lim = float(row["amp_rel_8sigma_lim"])
        anchor = row["radiometric_anchor"]
        if anchor == "HST_CALSTIS_DIRECT_FLAM":
            flam = float(row["continuum_flam_cgs"])
        else:
            if anchor == "GAIA_DR3_GRP":
                piv, zp, mag = GAIA_GRP_PIVOT_A, GAIA_GRP_ZP_FLAM, float(row["phot_rp_mag"])
            elif anchor == "TWOMASS_J":
                piv, zp, mag = TWOMASS_J_PIVOT_A, TWOMASS_J_ZP_FLAM, float(row["j_mag"])
            else:
                piv, zp, mag = GAIA_G_PIVOT_A, GAIA_G_ZP_FLAM, float(row["phot_g_mag"])
            b_rat = ((piv / cw) ** 5) * math.expm1(HC_OVER_K / (piv * teff)) / math.expm1(HC_OVER_K / (cw * teff))
            flam = zp * (10.0 ** (-0.4 * mag)) * b_rat
        fwhm_a = cw / r_pow
        ew_a = math.sqrt(math.pi / (4.0 * math.log(2.0))) * amp_lim * fwhm_a
        flux_cgs = flam * ew_a
        l_iso_w = 4.0 * math.pi * ((dist * PC_CM) ** 2) * flux_cgs * 1e-7
        theta = (math.pi * 10.0) / (cw * 1e-10)
        p_w = l_iso_w / (theta * theta)
        max_rel_ul = max(max_rel_ul, abs(p_w - float(row["p_beam_10m_w"])) / max(1e-12, float(row["p_beam_10m_w"])))
    c13_ok = len(ul_csv) >= 180 and max_rel_ul <= 1e-3 and all(math.isfinite(float(r["p_beam_10m_w"])) for r in ul_csv)
    add_check("C13_UPPER_LIMITS_DIRECT_CALSTIS_DUAL_RP_J_RECOMPUTE", c13_ok, f"{len(ul_csv)} upper-limit cells (0 NaN), max rel diff = {max_rel_ul:.2e}")

    # C14: Bridge 17, 10pc 103, Unified 200-star synthesis
    br = load_csv(RESULTS / "PANCHROMATIC_BRIDGE_17STARS.csv")
    s10 = load_csv(RESULTS / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_103STARS.csv")
    u200 = load_csv(RESULTS / "UNIFIED_PANCHROMATIC_V3_SYNTHESIS_200STARS.csv")
    tot_exp_u = sum(int(r["n_exposures_total"]) for r in u200)
    c14_ok = (
        len({r["star"] for r in br}) == 17
        and len(s10) == 103
        and len(u200) == 200
        and tot_exp_u == 1391
        and summary["unified_200star_panchromatic_v3_synthesis"]["spectrographs"] == 9
        and summary["unified_200star_panchromatic_v3_synthesis"]["verified_eti_detections_total"] == 0
    )
    add_check("C14_BRIDGE_17_10PC_103_UNIFIED_200STAR", c14_ok, f"17 bridges ({len(br)} cells), 103 <10pc, 200 unique stars, {tot_exp_u} exposures")

    # C15: Multi-messenger 206-system synthesis
    mm = load_csv(RESULTS / "MULTIMESSENGER_ECHELLE_RADIO_TESS_206SYSTEMS.csv")
    n_ov = sum(1 for r in mm if r["multimessenger_overlap"] == "True")
    c15_ok = len(mm) == 206 and n_ov == 18 and all(int(r["verified_eti_detections"]) == 0 for r in mm)
    add_check("C15_MULTIMESSENGER_206SYSTEM_SYNTHESIS", c15_ok, f"{len(mm)} distinct systems, {n_ov} direct overlaps, 0 verified ETI")

    passed = sum(1 for c in checks if c["status"] == "PASS")
    doc = {
        "schema": "D087_STDLIB_AUDIT_SUMMARY",
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "audited_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "checks_passed": passed,
        "checks_total": len(checks),
        "overall_status": "PASS" if passed == len(checks) else "FAIL",
        "checks": checks,
    }
    (RESULTS / "AUDIT_SUMMARY.json").write_text(json.dumps(doc, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return doc


def main() -> None:
    doc = run_audit()
    for c in doc["checks"]:
        print(f"  [{c['status']}] {c['check']}: {c['detail']}")
    print(f"OVERALL: {doc['overall_status']} ({doc['checks_passed']}/{doc['checks_total']})")
    if doc["overall_status"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
