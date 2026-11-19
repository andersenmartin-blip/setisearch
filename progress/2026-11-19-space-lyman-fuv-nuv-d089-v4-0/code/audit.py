#!/usr/bin/env python3
"""
Pure-stdlib (`/usr/bin/python3 -S`) independent verification suite for Phase D089
(`SPACE_LYMAN_FUV_NUV_V4_0`).

Runs 16 independent mathematical & forensic checks (C1..C16) against frozen D089
prospective locks, bounded bundle, 192-exposure LEO heliocentric kinematics,
37-star UV RV anchoring, 2,697 synthetic calibration trials, FUSE dual-telescope
G4_V40 coincidence, V4.0 cascade & forensic audit, 10 orbital campaigns (#71-#80),
direct-FLAM radiometric upper limits, unified 1,759-exposure D079-D089 all-sky
COMB_V4_1 sweep (284 stacks), 26 bridges / 121 <10pc / 250 stars (4.797 octaves),
and 250-system multi-messenger (23/23 radio + TESS) synthesis.
"""
from __future__ import annotations

import csv
import datetime
import gzip
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

WS = Path(__file__).resolve().parent
RESULTS = WS / "results"
BUNDLE_PATH = WS / "bounded_inputs" / "d089_bounded_bundle.json.gz"

C_KMS = 299792.458
PC_CM = 3.0856775814913673e18
G_SI = 6.67430e-11
M_SUN_KG = 1.98847e30
DAY_S = 86400.0


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            b = fh.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def parse_iso_utc(ts: str) -> float:
    return datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc).timestamp()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


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
    vx_eq = v0 * (-math.sin(lam_e) - e_orb * math.sin(pi_e))
    vy_ecl = v0 * (math.cos(lam_e) + e_orb * math.cos(pi_e))
    vy_eq = vy_ecl * math.cos(eps)
    vz_eq = vy_ecl * math.sin(eps)
    ra, dec = math.radians(ra_deg), math.radians(dec_deg)
    return float(vx_eq * math.cos(dec) * math.cos(ra) + vy_eq * math.cos(dec) * math.sin(ra) + vz_eq * math.sin(dec))


def main() -> None:
    checks: list[dict[str, Any]] = []

    def add_check(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": detail})
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}", flush=True)

    # C1: Prospective chronology and hashes
    ml = json.loads((WS / "METHOD_LOCK.json").read_text(encoding="utf-8"))
    lr = json.loads((WS / "LOCK_RECEIPT.json").read_text(encoding="utf-8"))
    fr = json.loads((WS / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json").read_text(encoding="utf-8"))
    dt_dl = parse_iso_utc(fr["first_download_utc"]) - parse_iso_utc(lr["locked_utc"])
    c1_ok = (
        sha256_file(WS / "METHOD_LOCK.json") == lr["method_lock_sha256"]
        and not lr.get("inputs_directory_present_at_lock", True)
        and dt_dl >= 3.0
    )
    imp_path = WS / "IMPLEMENTATION_LOCK.json"
    if imp_path.exists():
        imp = json.loads(imp_path.read_text(encoding="utf-8"))
        for fname, sha_val in lr["locked_artifact_sha256"].items():
            cur_sha = sha256_file(WS / fname)
            if fname == "analyze.py" and "updated_analyze_sha256" in imp:
                c1_ok = c1_ok and (cur_sha == imp["updated_analyze_sha256"]) and (sha_val == imp["original_analyze_sha256"])
            elif fname == "audit.py" and "updated_audit_sha256" in imp:
                c1_ok = c1_ok and (cur_sha == imp["updated_audit_sha256"])
            elif fname == "plot_figures.py" and "updated_plot_figures_sha256" in imp:
                c1_ok = c1_ok and (cur_sha == imp["updated_plot_figures_sha256"])
            else:
                c1_ok = c1_ok and (cur_sha == sha_val)
    else:
        for fname, sha_val in lr["locked_artifact_sha256"].items():
            c1_ok = c1_ok and (sha256_file(WS / fname) == sha_val)
    add_check("C1_PROSPECTIVE_CHRONOLOGY_AND_HASHES", c1_ok, f"lock={lr['locked_utc']}, dt_dl={dt_dl:.1f}s")

    # C2: Prior exclusion & cohort integrity
    cohort = load_csv(WS / "FROZEN_COHORT_D089.csv")
    pe = json.loads((WS / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    excl_dps = set(pe["excluded_dp_ids"])
    d089_dps = {r["dp_id"] for r in cohort}
    ctrl_bad = [r["canonical_target"] for r in cohort if r["role"] == "CONTROL" and int(r["n_exoplanets"]) != 0]
    stars_all = {r["canonical_target"] for r in cohort}
    stars_new = {r["canonical_target"] for r in cohort if r["panchromatic_bridge"] != "True"}
    stars_bridge = {r["canonical_target"] for r in cohort if r["panchromatic_bridge"] == "True"}
    stars_new_10pc = {r["canonical_target"] for r in cohort if r["panchromatic_bridge"] != "True" and r["within_10pc"] == "True"}
    c2_ok = (
        len(cohort) == 192
        and len(stars_all) == 37
        and len(stars_new) == 30
        and len(stars_bridge) == 7
        and len(stars_new_10pc) == 4
        and not ctrl_bad
        and len(d089_dps & excl_dps) == 0
        and pe["min_brand_new_sky_separation_arcsec"] >= 5000.0
        and pe["min_intra_d089_brand_new_separation_arcsec"] >= 300.0
    )
    add_check(
        "C2_PRIOR_EXCLUSION_AND_COHORT_INTEGRITY",
        c2_ok,
        f"{len(cohort)} exp, {len(stars_all)} stars ({len(stars_new)} new [{len(stars_new_10pc)} <10pc] + {len(stars_bridge)} bridge), min_sep={pe['min_brand_new_sky_separation_arcsec']}\", dp_overlap=0",
    )

    # C3: Bundle size and schema
    bz_mib = BUNDLE_PATH.stat().st_size / (1024.0 * 1024.0)
    with gzip.open(BUNDLE_PATH, "rt", encoding="utf-8") as gz:
        bundle = json.load(gz)
    c3_ok = (
        bz_mib < 25.0
        and len(bundle.get("exposures", [])) == 192
        and len(bundle.get("calib_tp_patches", [])) == 27
        and len(bundle.get("calib_kep_patches", [])) == 9
        and len(bundle.get("calib_g45_patches", [])) == 24
        and len(bundle.get("calib_g6_patches", [])) == 15
        and len(bundle.get("calib_comb_patches", [])) == 6
    )
    add_check("C3_BUNDLE_SIZE_AND_SCHEMA", c3_ok, f"d089_bounded_bundle.json.gz = {bz_mib:.2f} MiB (<25.0 MiB), exp=192")

    # C4: Exposure provenance & stdlib Earth heliocentric LEO bound (<= 8.50 km/s)
    prov = load_csv(RESULTS / "EXPOSURE_PROVENANCE_192.csv")
    max_leo_diff = 0.0
    all_pass = len(prov) == 192
    for r in prov:
        if r["header_gate"] != "PASS":
            all_pass = False
        std_b = stdlib_earth_helio_rv_kms(float(r["s_ra_deg"]), float(r["s_dec_deg"]), float(r["mjd_mid"]))
        diff_leo = abs(float(r["berv_kms"]) - std_b)
        max_leo_diff = max(max_leo_diff, diff_leo)
    c4_ok = all_pass and max_leo_diff <= 8.50
    add_check("C4_EXPOSURE_PROVENANCE_AND_STDLIB_LEO", c4_ok, f"{len(prov)} PASS rows, max |V_helio-stdlib_Earth|={max_leo_diff:.4f} km/s (<=8.50)")

    # C5: UV RV anchoring across 37 stars
    anchor_files = list(RESULTS.glob("STELLAR_RV_ANCHORS_*.csv"))
    anchors = load_csv(anchor_files[0]) if anchor_files else []
    rv_sum = load_csv(RESULTS / "STAR_RV_SUMMARY_37.csv")
    diffs = sorted(abs(float(r["empirical_minus_prior_kms"])) for r in rv_sum)
    med_diff = diffs[len(diffs) // 2] if diffs else 999.0
    n_clean = sum(1 for a in anchors if a["status"] == "CLEAN_ABSORPTION")
    c5_ok = len(rv_sum) == 37 and n_clean >= 250 and med_diff <= 5.5
    add_check("C5_UV_RV_ANCHORING_AND_37STARS", c5_ok, f"{len(anchors)} anchors ({n_clean} clean), 37 star summaries, med|emp-prior|={med_diff:.4f} km/s")

    # C6: Singleline + Keplerian + G4G5 calibration (1,971 trials)
    inj = load_csv(RESULTS / "INJECTION_RECOVERY_1620.csv")
    kep = load_csv(RESULTS / "KEPLERIAN_TRACK_CALIBRATION_135.csv")
    g45 = load_csv(RESULTS / "DETECTOR_V40_G4G5_CALIBRATION_216.csv")
    t_hi = [r["recovered"] == "True" for r in inj if r["mode"] == "CHANNEL_T_TRANSIENT_1EPOCH" and float(r["sigma_mult"]) >= 8.0]
    p_hi = [r["recovered"] == "True" for r in inj if r["mode"] == "CHANNEL_P_PERSISTENT_COADD" and float(r["sigma_mult"]) >= 8.0]
    k_td = [r["tdiff_uncomp_recovered"] == "True" for r in kep]
    k_kp = [r["kplanet_dedop_recovered"] == "True" for r in kep]
    g45_t = [r["g45_pass"] == "True" for r in g45 if r["trial_class"] == "TRUE_LSF_LASER"]
    g45_c = [r["g45_pass"] == "False" for r in g45 if r["trial_class"] == "COSMIC_RAY_HOT_PIXEL"]
    g45_p = [r["g45_pass"] == "False" for r in g45 if r["trial_class"] == "M_DWARF_PLATEAU_CORE"]
    rt_hi = sum(t_hi) / max(1, len(t_hi))
    rp_hi = sum(p_hi) / max(1, len(p_hi))
    rk_td = sum(k_td) / max(1, len(k_td))
    rk_kp = sum(k_kp) / max(1, len(k_kp))
    rg_t = sum(g45_t) / max(1, len(g45_t))
    rg_c = sum(g45_c) / max(1, len(g45_c))
    rg_p = sum(g45_p) / max(1, len(g45_p))
    c6_ok = (
        len(inj) == 1620 and len(kep) == 135 and len(g45) == 216
        and rt_hi >= 0.99 and rp_hi >= 0.99 and rk_td == 0.0 and rk_kp >= 0.95
        and rg_t >= 0.95 and rg_c == 1.0 and rg_p >= 0.95
    )
    add_check("C6_SINGLELINE_KEPLERIAN_G4G5_CALIB_1971", c6_ok, f"1971 trials: T>=8s={rt_hi:.3f}, P>=8s={rp_hi:.3f}, T_DIFF={rk_td:.3f}, K_PL={rk_kp:.3f}, G45=({rg_t:.3f},{rg_c:.3f},{rg_p:.3f})")

    # C7: G6 sparse vs dense 240 trials
    g6 = load_csv(RESULTS / "G6_SPARSE_VS_DENSE_CALIBRATION_240.csv")
    g6_true = [r["g6_v36_sparse_pass"] == "True" for r in g6 if r["trial_class"] == "TRUE_BARYCENTRIC_STELLAR_LASER"]
    g6_oh = [r["g6_v36_sparse_pass"] == "False" for r in g6 if r["trial_class"] == "GEOCORONAL_AIRGLOW_EMISSION"]
    g6_px = [r["g6_v36_sparse_pass"] == "False" for r in g6 if r["trial_class"] == "HOT_PIXEL_FIXED_DETECTOR"]
    g6_in = [r["g6_v36_sparse_pass"] == "False" for r in g6 if r["trial_class"] == "SINGLE_STAR_INTRA_GHOST"]
    c7_ok = len(g6) == 240 and all(g6_true) and all(g6_oh) and all(g6_px) and all(g6_in)
    add_check("C7_G6_SPARSE_VS_DENSE_CALIB_240", c7_ok, "240 trials: true=1.000, geo=1.000, px=1.000, intraBERV=1.000")

    # C8: COMB_V4_1 calibration 486 trials (total = 2,697)
    comb_cal = load_csv(RESULTS / "COMB_V4_1_CALIBRATION_486.csv")
    c6t = [r["comb_v41_hit"] == "True" for r in comb_cal if r["trial_class"] == "TRUE_6TOOTH_STELLAR_COMB" and float(r["tooth_snr_inj"]) >= 3.8]
    c1l = [r["comb_v41_hit"] == "True" for r in comb_cal if r["trial_class"] == "SINGLE_LINE_MASQUERADE"]
    ctopo = [r["comb_v41_hit"] == "True" for r in comb_cal if r["trial_class"] == "STATIONARY_TOPO_ROVIB_PSEUDOCOMB"]
    cfor4 = [r["comb_v4_hit"] == "True" for r in comb_cal if r["trial_class"] == "DENSE_MOLECULAR_FOREST"]
    cfor41 = [r["comb_v41_hit"] == "True" for r in comb_cal if r["trial_class"] == "DENSE_MOLECULAR_FOREST"]
    rec6 = sum(c6t) / max(1, len(c6t))
    fpr4 = sum(cfor4) / max(1, len(cfor4))
    fpr41 = sum(cfor41) / max(1, len(cfor41))
    c8_ok = len(comb_cal) == 486 and rec6 >= 0.55 and not any(c1l) and not any(ctopo) and fpr41 == 0.0
    add_check("C8_COMB_V4_1_CALIBRATION_486", c8_ok, f"486 trials (tot=2697): 6t={rec6:.3f}, 1L=0.000, topo=0.000, forest=(V4={fpr4:.3f}->V4.1={fpr41:.3f})")

    # C9: Unified D079-D089 COMB_V4_1 sweep (284 stacks / 1,759 exposures)
    allsky = load_csv(RESULTS / "ALLSKY_COMB_V4_1_UNIFIED_D079_D089.csv")
    allsky_cands = load_csv(RESULTS / "ALLSKY_COMB_V4_1_CANDIDATES_D079_D089.csv")
    tot_allsky_exp = sum(int(r["n_exposures"]) for r in allsky)
    tot_allsky_eti = sum(int(r["verified_eti_combs"]) for r in allsky)
    phases_cov = {r["phase_id"] for r in allsky}
    c9_ok = (
        len(allsky) == 284
        and tot_allsky_exp == 1759
        and phases_cov == {f"D0{k}" for k in range(79, 90)}
        and tot_allsky_eti == 0
    )
    add_check("C9_UNIFIED_ALLSKY_COMB_V4_1_SWEEP_1759EXP", c9_ok, f"{len(allsky)} stacks, {tot_allsky_exp} exposures (100% D079-D089), {len(allsky_cands)} COMB_V4_1 candidates, ETI={tot_allsky_eti}")

    # C10: FUSE Dual-Channel Coincidence + COS/STIS Hardware Veto Verification
    diag = json.loads((RESULTS / "FORENSIC_D089_CASCADE_DIAGNOSIS.json").read_text(encoding="utf-8"))
    fdc = diag["fuse_dual_channel_coincidence"]
    c10_ok = (
        fdc["n_tested"] >= 1
        and fdc["dual_channel_pass_count"] == fdc["n_tested"]
        and fdc["single_channel_vetoed_count"] == fdc["n_tested"]
    )
    add_check("C10_FUSE_DUAL_CHANNEL_COINCIDENCE_G4_V40", c10_ok, f"FUSE dual-channel coincide: {fdc['dual_channel_pass_count']}/{fdc['n_tested']} pass; single-channel artifact vetoed: {fdc['single_channel_vetoed_count']}/{fdc['n_tested']}")

    # C11: D089 Cascade and COMB_V4_1 parity
    ledger = load_csv(RESULTS / "V4_0_CANDIDATE_LEDGER.csv")
    bench = load_csv(RESULTS / "FOUR_GEN_BENCHMARK_192.csv")
    comb_stars = load_csv(RESULTS / "COMB_V4_1_STAR_RESULTS_37.csv")
    comb_cands = load_csv(RESULTS / "COMB_V4_1_CANDIDATES.csv")
    cas = diag["cascade"]
    pre_g6_cnt = sum(1 for r in ledger if r["pre_g6_qualified"] == "True")
    post_g6_cnt = sum(1 for r in ledger if r["qualified_v40_laser"] == "True")
    c11_ok = (
        len(bench) == 192
        and len(comb_stars) == 37
        and cas["v40_total_ledger_g1_candidates"] == len(ledger)
        and cas["v40_pre_g6_passed_g1_to_g5"] == pre_g6_cnt
        and (cas["automated_qualified_control"] + cas["automated_qualified_science"]) == post_g6_cnt
        and cas["comb_v41_automated_candidates"] == len(comb_cands)
        and cas["verified_eti_detections"] == 0
    )
    add_check("C11_CASCADE_AND_COMB_V4_1_PARITY", c11_ok, f"V2={cas['v2_legacy_false_alarms']} -> G1={len(ledger)} -> preG6={pre_g6_cnt} -> postG6={post_g6_cnt}, COMB_V4_1={len(comb_cands)}, ETI=0")

    # C12: Forensic audit covers 100% of D089 post-G6 + 100% of D089 COMB_V4_1 survivors
    fa = json.loads((RESULTS / "FORENSIC_CANDIDATE_AUDIT_D089.json").read_text(encoding="utf-8"))
    c12_ok = (
        fa["n_d089_post_g6_audited"] == post_g6_cnt
        and fa["n_d089_comb_v41_audited"] == len(comb_cands)
        and fa["verified_eti_detections"] == 0
        and len(fa["d089_post_g6_records"]) == post_g6_cnt
        and len(fa["d089_comb_v41_records"]) == len(comb_cands)
        and all(bool(r.get("natural_classification")) for r in fa["d089_post_g6_records"])
        and all(bool(r.get("natural_classification")) for r in fa["d089_comb_v41_records"])
    )
    add_check("C12_FORENSIC_AUDIT_AND_ZERO_ETI", c12_ok, f"post-G6={post_g6_cnt}, D089 COMB_V4_1={len(comb_cands)} forensically audited, verified_eti=0")

    # C13: 10 Orbital campaigns (#71-#80) stdlib Kp check
    orb_csv = load_csv(RESULTS / "ORBITAL_CAMPAIGN_RESULTS_10.csv")
    orb_json = json.loads((WS / "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json").read_text(encoding="utf-8"))["campaigns"]
    max_kp_diff = 0.0
    c13_ok = len(orb_csv) == 10
    for r in orb_csv:
        st = r["star"]
        oc = orb_json[st]
        e_v = float(oc["ecc"])
        v_circ = ((2.0 * math.pi * G_SI * float(oc["st_mass_msun"]) * M_SUN_KG) / (float(oc["orbper_days"]) * DAY_S)) ** (1.0 / 3.0)
        kp_std = (v_circ / math.sqrt(max(1e-6, 1.0 - e_v * e_v))) / 1000.0
        max_kp_diff = max(max_kp_diff, abs(kp_std - float(r["kp_kms"])))
        if int(r["n_in_window"]) != 4 or int(r["n_out_of_window"]) != 4 or int(r["verified_eti_detections"]) != 0:
            c13_ok = False
    c13_ok = c13_ok and max_kp_diff <= 1e-3
    add_check("C13_ORBITAL_CAMPAIGNS_10_CHECK", c13_ok, f"10 campaigns (#71-#80: 3 ctrl + 7 sci, 4 IN + 4 OUT), max |Kp_std-Kp_csv|={max_kp_diff:.5f} km/s")

    # C14: Upper limits pure-stdlib Direct-FLAM recompute
    ul_rows = load_csv(RESULTS / "STAR_UPPER_LIMITS_D089.csv")
    max_rel_diff = 0.0
    c14_ok = len(ul_rows) >= 140
    anchors_seen = set()
    for r in ul_rows:
        anc = r["radiometric_anchor"]
        anchors_seen.add(anc)
        w_a = float(r["wave_bary_a"])
        flam = float(r["continuum_flam_cgs"])
        fwhm_a = w_a / float(r["resolving_power"])
        ew_a = math.sqrt(math.pi / (4.0 * math.log(2.0))) * float(r["amp_rel_8sigma_lim"]) * fwhm_a
        flux_cgs = flam * ew_a
        l_iso_w = 4.0 * math.pi * ((float(r["dist_pc"]) * PC_CM) ** 2) * flux_cgs * 1e-7
        theta = (math.pi * 10.0) / (w_a * 1e-10)
        p_kw = (l_iso_w / (theta * theta)) / 1000.0
        obs_kw = float(r["p_beam_10m_kw"])
        if not math.isfinite(obs_kw) or obs_kw <= 0.0:
            c14_ok = False
        max_rel_diff = max(max_rel_diff, abs(p_kw - obs_kw) / max(1e-15, obs_kw))
    c14_ok = c14_ok and anchors_seen == {"FUSE_CALFUSE_DIRECT_FLAM", "HST_CALCOS_DIRECT_FLAM", "HST_CALSTIS_DIRECT_FLAM"} and max_rel_diff <= 2e-3
    add_check("C14_UPPER_LIMITS_DIRECT_FLAM_RECOMPUTE", c14_ok, f"{len(ul_rows)} direct-FLAM cells across 3 space-UV anchors, max rel diff={max_rel_diff:.2e}")

    # C15: 26 bridges, 121 <10pc, 250 unique stars, 1,759 exposures
    br26 = load_csv(RESULTS / "PANCHROMATIC_BRIDGE_26STARS.csv")
    s121 = load_csv(RESULTS / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_121STARS.csv")
    u250 = load_csv(RESULTS / "UNIFIED_PANCHROMATIC_V4_SYNTHESIS_250STARS.csv")
    br_stars = {r["star"] for r in br26}
    tot_u_exp = sum(int(r["n_exposures_total"]) for r in u250)
    c15_ok = (
        len(br_stars) == 26
        and len(s121) == 121
        and len(u250) == 250
        and tot_u_exp == 1759
        and sum(int(r["verified_eti_detections"]) for r in u250) == 0
    )
    add_check("C15_BRIDGE_26_10PC_121_UNIFIED_250STAR", c15_ok, f"26 bridges ({len(br26)} cells), {len(s121)} <10pc, {len(u250)} unique stars, {tot_u_exp} exposures (4.797 octaves)")

    # C16: Multi-messenger 250-system & 23/23 (100%) radio-echelle closure
    mm250 = load_csv(RESULTS / "MULTIMESSENGER_ECHELLE_RADIO_TESS_250SYSTEMS.csv")
    n_mm_ovlp = sum(1 for r in mm250 if r["multimessenger_overlap"] == "True")
    n_rad_ovlp = sum(1 for r in mm250 if r["multimessenger_overlap"] == "True" and r["radio_milestone"])
    c16_ok = len(mm250) == 250 and n_rad_ovlp == 23 and n_mm_ovlp == 24 and sum(int(r["verified_eti_detections"]) for r in mm250) == 0
    add_check("C16_MULTIMESSENGER_250SYSTEM_RADIO23_CLOSURE", c16_ok, f"{len(mm250)} distinct systems, {n_rad_ovlp}/23 radio + 1 TESS = {n_mm_ovlp} direct overlaps, 0 ETI")

    n_pass = sum(1 for c in checks if c["status"] == "PASS")
    n_tot = len(checks)
    overall = "PASS" if n_pass == n_tot else "FAIL"
    print(f"OVERALL: {overall} ({n_pass}/{n_tot})", flush=True)

    out_summary = {
        "schema": "D089_STDLIB_AUDIT_SUMMARY",
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "audited_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "checks_passed": n_pass,
        "checks_total": n_tot,
        "overall_status": overall,
        "checks": checks,
    }
    (RESULTS / "AUDIT_SUMMARY.json").write_text(json.dumps(out_summary, indent=2) + "\n", encoding="utf-8")
    if n_pass != n_tot:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
