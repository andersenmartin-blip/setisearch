#!/usr/bin/env python3
"""Pure-stdlib 15-check audit for Phase D086 (`PANCHROM_NUV_OPT_V3_7_AND_COMB_V4_1`).

Run cleanly under `/usr/bin/python3 -S audit.py` with zero third-party packages.
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

HERE = Path(__file__).resolve().parent
INPUTS_DIR = HERE.parent.parent / "inputs_d086_v3_7"

C_KMS = 299792.458
GAIA_GBP_PIVOT_A = 5109.7121
GAIA_GBP_ZP_FLAM = 4.078518e-9
GAIA_G_PIVOT_A = 6217.6
GAIA_G_ZP_FLAM = 2.50386e-9
HC_OVER_K_A_K = 1.438776877e8
PC_CM = 3.0856775814913673e18
G_SI = 6.67430e-11
M_SUN_KG = 1.98847e30
DAY_S = 86400.0
PARANAL_LAT_DEG = -24.6272
PARANAL_LON_DEG = -70.4042
LA_SILLA_LAT_DEG = -29.2563
LA_SILLA_LON_DEG = -70.7380


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def check_no_nan(rows: list[dict[str, str]], path: Path, optional_cols: set[str]) -> tuple[bool, str]:
    for idx, r in enumerate(rows, start=1):
        for k, v in r.items():
            s = (v or "").strip()
            if s.lower() in ("nan", "inf", "-inf"):
                return False, f"{path.name} row {idx} col {k} is {s}"
            if not s and k not in optional_cols:
                return False, f"{path.name} row {idx} col {k} empty"
    return True, "OK"


def stdlib_obs_berv_kms(ra_deg: float, dec_deg: float, mjd_utc: float, obs: str) -> float:
    lat_deg = PARANAL_LAT_DEG if obs == "PARANAL" else LA_SILLA_LAT_DEG
    lon_deg = PARANAL_LON_DEG if obs == "PARANAL" else LA_SILLA_LON_DEG
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
    gmst_deg = (280.46061837 + 360.98564736629 * d + 0.000387933 * (t_c * t_c)) % 360.0
    lst = math.radians((gmst_deg + lon_deg) % 360.0)
    v_rot = 0.46510 * math.cos(math.radians(lat_deg))
    vx_eq += -v_rot * math.sin(lst)
    vy_eq += v_rot * math.cos(lst)
    ra, dec = math.radians(ra_deg), math.radians(dec_deg)
    return vx_eq * math.cos(dec) * math.cos(ra) + vy_eq * math.cos(dec) * math.sin(ra) + vz_eq * math.sin(dec)


def main() -> int:
    checks: list[dict[str, str]] = []

    def record(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}", flush=True)

    # C1: Prospective Lock, Implementation Lock & Download Chronology
    mlock = json.loads((HERE / "METHOD_LOCK.json").read_text(encoding="utf-8"))
    lrec = json.loads((HERE / "LOCK_RECEIPT.json").read_text(encoding="utf-8"))
    impl_p = HERE / "IMPLEMENTATION_LOCK.json"
    impl = json.loads(impl_p.read_text(encoding="utf-8")) if impl_p.is_file() else None
    lock_sha = sha256_file(HERE / "METHOD_LOCK.json")
    ok1 = lock_sha == lrec.get("method_lock_sha256")
    if impl is not None:
        ok1 = ok1 and (impl.get("parent_method_lock_sha256") == lock_sha)
    for rel, sha_exp in lrec.get("locked_artifact_sha256", {}).items():
        if impl is not None and rel in impl.get("amended_file_hashes", {}):
            v0_fp = HERE / impl["preserved_pre_ingestion_files"][rel]
            cur_fp = HERE / rel
            ok1 = ok1 and v0_fp.is_file() and sha256_file(v0_fp) == sha_exp and cur_fp.is_file() and sha256_file(cur_fp) == impl["amended_file_hashes"][rel]
        else:
            fp = HERE / rel
            ok1 = ok1 and fp.is_file() and sha256_file(fp) == sha_exp
    t_lock = dt.datetime.fromisoformat(lrec["locked_utc"].replace("Z", "+00:00"))
    dl_p = INPUTS_DIR / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json"
    dt_delta = None
    if dl_p.is_file():
        dl = json.loads(dl_p.read_text(encoding="utf-8"))
        t_dl = dt.datetime.fromisoformat(dl["first_download_utc"].replace("Z", "+00:00"))
        dt_delta = (t_dl - t_lock).total_seconds()
        ok1 = ok1 and (dt_delta >= 3.0)
    record("C1_PROSPECTIVE_CHRONOLOGY_AND_HASHES", ok1, f"lock={lrec['locked_utc']}, dt_dl={dt_delta if dt_delta is not None else 'cleanroom_offline'}s")

    # C2: Prior Exclusion & Cohort Integrity (31 stars, 181 exp)
    coh = read_csv(HERE / "FROZEN_COHORT_D086.csv")
    pe = json.loads((HERE / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    orb_cat = json.loads((HERE / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").read_text(encoding="utf-8"))
    ok2_n, _ = check_no_nan(coh, HERE / "FROZEN_COHORT_D086.csv", {"radio_mm_id", "twomass_id", "j_mag", "h_mag", "ks_mag", "aux_url", "aux_category"})
    s31 = {r["canonical_target"] for r in coh}
    new_s = {r["canonical_target"] for r in coh if r["panchromatic_bridge"] != "True"}
    br_s = {r["canonical_target"] for r in coh if r["panchromatic_bridge"] == "True"}
    n10 = {r["canonical_target"] for r in coh if r["panchromatic_bridge"] != "True" and r["within_10pc"] == "True"}
    excl = set(pe["excluded_dp_ids"]) | set(pe["format_check_excluded_dp_ids"])
    dp_ovlp = {r["dp_id"] for r in coh} & excl
    ok2 = ok2_n and len(coh) == 181 and len(s31) == 31 and len(new_s) == 25 and len(br_s) == 6 and len(n10) == 17 and orb_cat["n_campaigns"] == 10 and pe["d086_dp_id_overlap_count"] == 0 and len(dp_ovlp) == 0 and float(pe["min_brand_new_sky_separation_arcsec"]) >= 3000.0
    record("C2_PRIOR_EXCLUSION_AND_COHORT_INTEGRITY", ok2, f"181 exp, 31 stars (25 new [{len(n10)} <10pc] + 6 bridge), 10 orb, min_sep={pe['min_brand_new_sky_separation_arcsec']}\", dp_overlap={len(dp_ovlp)}")

    # C3: Bounded Bundle Size & Schema
    bp = HERE / "bounded_inputs" / "d086_bounded_bundle.json.gz"
    b_mib = bp.stat().st_size / (1024.0 * 1024.0)
    with gzip.open(bp, "rt", encoding="utf-8") as gz:
        bun = json.load(gz)
    ok3 = b_mib < 25.0 and bun.get("schema") == "SETI_D086_BOUNDED_REPRODUCIBLE_BUNDLE_V1" and len(bun["provenance_rows"]) == 181 and len(bun["rv_anchor_bundle"]) == 181 and len(bun["calib_transient_patches"]) == 72 and len(bun["calib_persistent_patches"]) == 36 and len(bun["calib_keplerian_patches"]) == 9 and len(bun["calib_g4g5_patches"]) == 72 and len(bun["calib_g6_patches"]) == 20 and len(bun["calib_comb_patches"]) == 18
    record("C3_BUNDLE_SIZE_AND_SCHEMA", ok3, f"d086_bounded_bundle.json.gz = {b_mib:.2f} MiB (<25.0 MiB), patches=(72,36,9,72,20,18)")

    # C4: Exposure Provenance & Pure-Stdlib Paranal/La Silla BERV
    prov = read_csv(HERE / "results" / "EXPOSURE_PROVENANCE_181.csv")
    ok4_n, _ = check_no_nan(prov, HERE / "results" / "EXPOSURE_PROVENANCE_181.csv", {"radio_mm_id", "aux_sha256"})
    max_b = 0.0
    for pr in prov:
        b_ref = stdlib_obs_berv_kms(float(pr["s_ra_deg"]), float(pr["s_dec_deg"]), float(pr["mjd_mid"]), pr["observatory"])
        max_b = max(max_b, abs(b_ref - float(pr["berv_kms"])))
    ok4 = ok4_n and len(prov) == 181 and all(r["header_gate"] == "PASS" for r in prov) and max_b <= 0.50
    record("C4_EXPOSURE_PROVENANCE_AND_STDLIB_BERV", ok4, f"181 PASS rows, max |BERV - stdlib_Observatory_BERV| = {max_b:.4f} km/s (<= 0.50)")

    # C5: 2,424 RV Anchors & 31 Star RV Summaries
    rva = read_csv(HERE / "results" / "STELLAR_RV_ANCHORS_2424.csv")
    rvs = read_csv(HERE / "results" / "STAR_RV_SUMMARY_31.csv")
    ok5_a, _ = check_no_nan(rva, HERE / "results" / "STELLAR_RV_ANCHORS_2424.csv", {"best_rv_kms", "rel_depth", "min_sse"})
    ok5_s, _ = check_no_nan(rvs, HERE / "results" / "STAR_RV_SUMMARY_31.csv", {"radio_mm_id"})
    n_cln = sum(1 for r in rva if r["status"] == "CLEAN_ABSORPTION")
    abs_d = sorted(abs(float(r["empirical_minus_prior_kms"])) for r in rvs)
    med_d = abs_d[len(abs_d) // 2]
    ok5 = ok5_a and ok5_s and len(rva) == 2424 and len(rvs) == 31 and n_cln >= 1000 and med_d <= 2.5
    record("C5_RV_ANCHORING_2424_AND_31STARS", ok5, f"2424 anchors ({n_cln} clean), 31 star summaries, median |emp - prior| = {med_d:.4f} km/s")

    # C6: 1,971 Single-Line, Keplerian & G4/G5 Calibration Trials
    inj = read_csv(HERE / "results" / "INJECTION_RECOVERY_1620.csv")
    kep = read_csv(HERE / "results" / "KEPLERIAN_TRACK_CALIBRATION_135.csv")
    g45 = read_csv(HERE / "results" / "DETECTOR_V37_G4G5_CALIBRATION_216.csv")
    cb = read_csv(HERE / "results" / "CALIBRATION_COMPLETENESS_BY_BAND.csv")
    t8 = [r for r in inj if r["mode"] == "CHANNEL_T_TRANSIENT_1EPOCH" and float(r["sigma_mult"]) >= 8.0]
    p9 = [r for r in inj if r["mode"] == "CHANNEL_P_PERSISTENT_MULTIEPOCH" and float(r["sigma_mult"]) >= 9.0]
    k65 = [r for r in kep if float(r["exp_sigma_mult"]) >= 6.5]
    t8r = sum(1 for r in t8 if r["recovered"] == "True") / max(1, len(t8))
    p9r = sum(1 for r in p9 if r["recovered"] == "True") / max(1, len(p9))
    ktdr = sum(1 for r in k65 if r["tdiff_uncomp_recovered"] == "True") / max(1, len(k65))
    kkpr = sum(1 for r in k65 if r["kplanet_dedop_recovered"] == "True") / max(1, len(k65))
    g45_l = sum(1 for r in g45 if r["trial_class"] == "TRUE_LSF_LASER" and r["g45_pass"] == "True") / 72.0
    g45_c = sum(1 for r in g45 if r["trial_class"] == "COSMIC_SINGLE_PX_SPIKE" and r["g5_pass"] == "False") / 72.0
    g45_p = sum(1 for r in g45 if r["trial_class"] == "WIDE_SCATTERING_PLATEAU" and r["g5_pass"] == "False") / 72.0
    ok6 = len(inj) == 1620 and len(kep) == 135 and len(g45) == 216 and len(cb) > 0 and t8r >= 0.70 and p9r >= 0.75 and kkpr > ktdr and g45_l >= 0.90 and g45_c == 1.0 and g45_p >= 0.95
    record("C6_SINGLELINE_KEPLERIAN_G4G5_CALIB_1971", ok6, f"1971 trials: T>=8s={t8r:.3f}, P>=9s={p9r:.3f}, Kep=({ktdr:.3f}->{kkpr:.3f}), G4G5=({g45_l:.3f},{g45_c:.3f},{g45_p:.3f})")

    # C7: 240-Trial G6 Sparse vs Dense
    g6 = read_csv(HERE / "results" / "G6_SPARSE_VS_DENSE_CALIBRATION_240.csv")
    gt = [r for r in g6 if r["trial_class"] == "TRUE_BARYCENTRIC_STELLAR_LASER"]
    goh = [r for r in g6 if r["trial_class"] == "UNLISTED_STATIONARY_SKY_OH_LINE"]
    gpx = [r for r in g6 if r["trial_class"] == "STATIONARY_DETECTOR_WARM_PIXEL"]
    gin = [r for r in g6 if r["trial_class"] == "INTRA_STAR_BERV_STATIONARY_GHOST"]
    rst = sum(1 for r in gt if r["g6_v36_sparse_pass"] == "True") / max(1, len(gt))
    rso = sum(1 for r in goh if r["g6_v36_sparse_pass"] == "False") / max(1, len(goh))
    rsp = sum(1 for r in gpx if r["g6_v36_sparse_pass"] == "False") / max(1, len(gpx))
    rsi = sum(1 for r in gin if r["g6_v36_sparse_pass"] == "False") / max(1, len(gin))
    ok7 = len(g6) == 240 and rst >= 0.85 and rso >= 0.98 and rsp >= 0.98 and rsi == 1.0
    record("C7_G6_SPARSE_VS_DENSE_CALIB_240", ok7, f"240 trials: true={rst:.3f}, OH={rso:.3f}, px={rsp:.3f}, intraBERV={rsi:.3f}")

    # C8: 486-Trial COMB_V4_1 Calibration
    cc = read_csv(HERE / "results" / "COMB_V4_1_CALIBRATION_486.csv")
    c_hi = [r for r in cc if r["trial_class"] == "TRUE_6TOOTH_STELLAR_COMB" and float(r["tooth_snr_inj"]) >= 3.8]
    c_1l = [r for r in cc if r["trial_class"] == "SINGLE_BRIGHT_LINE_MASQUERADE"]
    c_ro = [r for r in cc if r["trial_class"] == "STATIONARY_TOPO_ROVIB_PSEUDOCOMB"]
    c_fo = [r for r in cc if r["trial_class"] == "DENSE_MOLECULAR_FOREST_PSEUDOCOMB"]
    crec = sum(1 for r in c_hi if r["comb_v41_hit"] == "True") / max(1, len(c_hi))
    c1f = sum(1 for r in c_1l if r["comb_v41_hit"] == "True") / max(1, len(c_1l))
    crof = sum(1 for r in c_ro if r["comb_v41_hit"] == "True") / max(1, len(c_ro))
    cfof41 = sum(1 for r in c_fo if r["comb_v41_hit"] == "True") / max(1, len(c_fo))
    cfof4 = sum(1 for r in c_fo if r["comb_v4_hit"] == "True") / max(1, len(c_fo))
    ok8 = len(cc) == 486 and crec >= 0.75 and c1f == 0.0 and crof <= 0.05 and cfof41 <= 0.05 and cfof41 <= cfof4
    record("C8_COMB_V4_1_CALIBRATION_486", ok8, f"486 trials: 6-tooth>=3.8s={crec:.3f}, 1L={c1f:.3f}, topo={crof:.3f}, forest=(V4={cfof4:.3f}->V4.1={cfof41:.3f})")

    # C9: D085 COMB_V4_1 Read-Only Regression (19 -> 0)
    reg = read_csv(HERE / "results" / "D085_COMB_V4_1_REGRESSION_19.csv")
    n_surv85 = sum(1 for r in reg if r["comb_v41_retained"] == "True")
    ok9 = len(reg) == 19 and n_surv85 == 0
    record("C9_D085_COMB_V4_1_REGRESSION_19", ok9, f"D085 COMB_V4 19 false alarms -> {n_surv85} survivors under COMB_V4_1")

    # C10: Cascade & COMB_V4_1 Parity
    bnch = read_csv(HERE / "results" / "FOUR_GEN_BENCHMARK_181.csv")
    led = read_csv(HERE / "results" / "V3_7_CANDIDATE_LEDGER.csv")
    cs31 = read_csv(HERE / "results" / "COMB_V4_1_STAR_RESULTS_31.csv")
    cc_r = read_csv(HERE / "results" / "COMB_V4_1_CANDIDATES.csv")
    summ = json.loads((HERE / "results" / "SUMMARY.json").read_text(encoding="utf-8"))
    fc = summ["false_alarm_cascade"]
    v2f = sum(int(r["v2_accepted_false_alarms"]) for r in bnch)
    npg = sum(1 for r in led if r["pre_g6_qualified"] == "True")
    ok10 = len(bnch) == 181 and len(cs31) == 31 and v2f == fc["v2_legacy_false_alarms"] and len(led) == fc["v37_total_ledger_g1_candidates"] and npg == fc["v37_pre_g6_passed_g1_to_g5"] and len(cc_r) == fc["comb_v41_automated_candidates"] and fc["verified_eti_detections"] == 0
    record("C10_CASCADE_AND_COMB_V4_1_PARITY", ok10, f"V2={v2f} -> G1={len(led)} -> preG6={npg} -> COMB_V4_1={len(cc_r)}, verified_eti=0")

    # C11: Forensic Candidate Audit
    fd = json.loads((HERE / "results" / "FORENSIC_D086_CASCADE_DIAGNOSIS.json").read_text(encoding="utf-8"))
    fa = json.loads((HERE / "FORENSIC_CANDIDATE_AUDIT_D086.json").read_text(encoding="utf-8"))
    asl = {x["candidate_id"] for x in fa["post_g6_singleline_forensic_classifications"]}
    psl = {x["candidate_id"] for x in fd["post_g6_qualified"]}
    acb = {x["comb_id"] for x in fa["comb_v41_forensic_classifications"]}
    pcb = {x["comb_id"] for x in fd["comb_v41_candidates"]}
    ok11 = asl == psl and acb == pcb and all(x.get("eti_plausible") is False for x in fa["post_g6_singleline_forensic_classifications"]) and all(x.get("eti_plausible") is False for x in fa["comb_v41_forensic_classifications"]) and fa["verified_eti_detections"] == 0
    record("C11_FORENSIC_AUDIT_AND_ZERO_ETI", ok11, f"post-G6={len(asl)}, COMB_V4_1={len(acb)} forensically audited, verified_eti=0")

    # C12: 10 Orbital Campaigns Kp Recomputation
    orbs = read_csv(HERE / "results" / "ORBITAL_CAMPAIGN_RESULTS_10.csv")
    mkp = 0.0
    for r in orbs:
        cm = orb_cat["campaigns"][r["star"]]
        kp_s = ((2.0 * math.pi * G_SI * float(cm["st_mass_msun"]) * M_SUN_KG / (float(cm["orbper_days"]) * DAY_S)) ** (1.0 / 3.0)) / math.sqrt(max(1e-6, 1.0 - float(cm["ecc"]) ** 2)) / 1000.0
        mkp = max(mkp, abs(kp_s - float(r["kp_kms"])))
    ok12 = len(orbs) == 10 and sum(1 for r in orbs if r["role"] == "CONTROL") == 3 and sum(1 for r in orbs if r["role"] == "SCIENCE") == 7 and mkp <= 0.05 and all(int(r["n_in_window"]) == 4 and int(r["n_out_of_window"]) == 4 for r in orbs)
    record("C12_ORBITAL_CAMPAIGNS_10_CHECK", ok12, f"10 campaigns (3 ctrl + 7 sci, 4 IN + 4 OUT), max |Kp_std - Kp_csv| = {mkp:.5f} km/s")

    # C13: Gaia DR3 G_BP + G Planck Recomputation across ALL Upper Limit Cells
    uls = read_csv(HERE / "results" / "STAR_UPPER_LIMITS_D086.csv")
    ok13_n, _ = check_no_nan(uls, HERE / "results" / "STAR_UPPER_LIMITS_D086.csv", {"radio_mm_id", "j_mag", "h_mag", "ks_mag"})
    mrel = 0.0
    for u in uls:
        lam, amp, teff, dist, rp = float(u["wave_bary_air_A"]), float(u["amp_rel_8sigma_lim"]), float(u["teff_k"]), float(u["dist_pc"]), float(u["resolving_power"])
        if u["radiometric_anchor"] == "GAIA_DR3_GBP":
            piv, zp, mag = GAIA_GBP_PIVOT_A, GAIA_GBP_ZP_FLAM, float(u["phot_bp_mag"])
        else:
            piv, zp, mag = GAIA_G_PIVOT_A, GAIA_G_ZP_FLAM, float(u["phot_g_mag"])
        brat = ((piv / lam) ** 5) * math.expm1(HC_OVER_K_A_K / (piv * teff)) / math.expm1(HC_OVER_K_A_K / (lam * teff))
        flam = zp * (10.0 ** (-0.4 * mag)) * brat
        ew = math.sqrt(math.pi / (4.0 * math.log(2.0))) * amp * (lam / rp)
        liso = 4.0 * math.pi * ((dist * PC_CM) ** 2) * (flam * ew) * 1e-7
        p10 = liso / ((math.pi * 10.0 / (lam * 1e-10)) ** 2)
        mrel = max(mrel, abs(p10 - float(u["p_beam_10m_w"])) / max(1e-30, float(u["p_beam_10m_w"])))
    ok13 = ok13_n and len(uls) >= 120 and mrel < 1e-5
    record("C13_UPPER_LIMITS_GAIA_GBP_AND_G_RECOMPUTE", ok13, f"{len(uls)} upper-limit cells (0 NaN), max rel diff = {mrel:.2e}")

    # C14: 13-Star Bridge, 90-Star <10 pc, & 175-Star Unified Synthesis
    br13 = read_csv(HERE / "results" / "PANCHROMATIC_BRIDGE_13STARS.csv")
    s90 = read_csv(HERE / "results" / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_90STARS.csv")
    u175 = read_csv(HERE / "results" / "UNIFIED_PANCHROMATIC_V3_SYNTHESIS_175STARS.csv")
    tot_e = sum(int(r["n_exposures_total"]) for r in u175)
    ok14 = len({r["star"] for r in br13}) == 13 and len(u175) == 175 and len({r["star"] for r in u175}) == 175 and len(s90) == 90 and all(float(r["dist_pc"]) < 10.0 for r in s90) and tot_e == 1190 and all(int(r["verified_eti_detections"]) == 0 for r in u175)
    record("C14_BRIDGE_13_10PC_90_UNIFIED_175STAR", ok14, f"13 bridges ({len(br13)} cells), 90 <10pc, 175 unique stars, {tot_e} exposures")

    # C15: 181-System Multi-Messenger Synthesis (18 Direct Overlaps)
    mm181 = read_csv(HERE / "results" / "MULTIMESSENGER_ECHELLE_RADIO_TESS_181SYSTEMS.csv")
    nov = sum(1 for r in mm181 if r["multimessenger_overlap"] == "True")
    ok15 = len(mm181) == 181 and nov == 18 and all(int(r["verified_eti_detections"]) == 0 for r in mm181)
    record("C15_MULTIMESSENGER_181SYSTEM_SYNTHESIS", ok15, f"181 distinct systems, {nov} direct overlaps, 0 verified ETI")

    np_cnt = sum(1 for c in checks if c["status"] == "PASS")
    out = {
        "schema": "D086_STDLIB_AUDIT_SUMMARY",
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "audited_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "checks_passed": np_cnt,
        "checks_total": len(checks),
        "overall_status": "PASS" if np_cnt == len(checks) else "FAIL",
        "checks": checks,
    }
    (HERE / "results" / "AUDIT_SUMMARY.json").write_text(json.dumps(out, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"[audit.py] {np_cnt}/{len(checks)} checks PASSED -> {out['overall_status']}", flush=True)
    return 0 if np_cnt == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
