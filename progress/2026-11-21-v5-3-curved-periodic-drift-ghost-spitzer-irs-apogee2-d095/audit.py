#!/usr/bin/python3 -S
"""Pure Python stdlib independent audit (C1-C16) for SETI Phase D095 (V5.3)."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import pathlib
import shutil
import sys
from typing import Any

WS = pathlib.Path(__file__).resolve().parent

C_SI = 299792458.0
H_PLANCK = 6.62607015e-34
K_BOLTZ = 1.380649e-23
PC_CM = 3.085677581491367e18
SOLAR_RADIUS_CM = 6.957e10
GAIA_G_EFF_WAVE_A = 6217.59
GAIA_G_FLAM0_CGS = 2.500e-9
TWOMASS_H_EFF_WAVE_A = 16620.0
TWOMASS_H_FLAM0_CGS = 1.133e-10

EXPECTED_RESULT_FILES = [
    "ALLSKY_COMB_V4_1_CANDIDATES_D079_D095.csv",
    "ALLSKY_COMB_V4_1_UNIFIED_D079_D095.csv",
    "BLIND_DRIFT_V51_RESULTS_D095.csv",
    "CALIBRATION_COMPLETENESS_BY_BAND.csv",
    "CALIBRATION_G8_V53_120.csv",
    "CALIBRATION_V53_AGNOSTIC_120.csv",
    "CALIBRATION_V53_CURVED_PERIODIC_DRIFT_240.csv",
    "CALIBRATION_V53_GHOST_SKY_FIBER_120.csv",
    "CALIBRATION_V53_RPCA_RARITY_180.csv",
    "CALIBRATION_V53_SPITZER_IRS_CCF_AND_DYSON_240.csv",
    "COMB_V4_1_CALIBRATION_162.csv",
    "COMB_V4_1_CANDIDATES.csv",
    "COMB_V4_1_STAR_RESULTS_D095.csv",
    "DETECTOR_V53_G4G5_CALIBRATION_108.csv",
    "DRIFT_V53_CURVED_PERIODIC_RESULTS.csv",
    "EIRP_UPPER_LIMITS_D095.csv",
    "EXPOSURE_PROVENANCE_D095.csv",
    "FOUR_GEN_BENCHMARK_D095.csv",
    "GHOST_SKY_FIBER_VETO_SUMMARY.csv",
    "INJECTION_RECOVERY_540.csv",
    "KEPLERIAN_TRACK_CALIBRATION_81.csv",
    "MULTIEPOCH_DRIFT_V52_RESULTS_D095.csv",
    "MULTIEVENT_ELLIPSOID_401STARS.csv",
    "ORBITAL_CAMPAIGN_RESULTS_8.csv",
    "PANCHROMATIC_BRIDGE_47STARS_V53.csv",
    "RETROACTIVE_D091_D094_CURVED_PERIODIC_DRIFT.csv",
    "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_161STARS.csv",
    "SPITZER_IRS_CCF_AND_DYSON_18STARS.csv",
    "STAR_RV_SUMMARY_D095.csv",
    "STELLAR_RV_ANCHORS_D095.csv",
    "SUMMARY.json",
    "UNIFIED_PANCHROMATIC_V5_3_SYNTHESIS_401STARS.csv",
    "V5_3_AGNOSTIC_MULTISCALE_SURVIVORS.csv",
    "V5_3_CANDIDATE_LEDGER.csv",
]

EXPECTED_FIGURES = [
    "fig01_d095_panchromatic_401stars_8p71octaves.png",
    "fig02_d095_curved_periodic_drift_v53.png",
    "fig03_d095_ghost_sky_fiber_veto_and_orbits.png",
    "fig04_d095_spitzer_irs_dyson_vs_silicate.png",
    "fig05_d095_spitzer_irs_greenhouse_ccf_and_eirp.png",
    "fig06_d095_multievent_ellipsoid_401stars_cal.png",
]


def _sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(65536)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _read_csv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _read_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _planck_rel_cgs(wave_a: float, ref_wave_a: float, zero_flam0: float, mag: float, teff_k: float, t_floor: float) -> float:
    lam_w = wave_a * 1e-10
    lam_r = ref_wave_a * 1e-10
    teff = max(t_floor, teff_k)
    xw = min(700.0, (H_PLANCK * C_SI) / (lam_w * K_BOLTZ * teff))
    xr = min(700.0, (H_PLANCK * C_SI) / (lam_r * K_BOLTZ * teff))
    bw = (2.0 * H_PLANCK * C_SI * C_SI) / ((lam_w ** 5) * math.expm1(xw))
    br = (2.0 * H_PLANCK * C_SI * C_SI) / ((lam_r ** 5) * math.expm1(xr))
    fr = zero_flam0 * (10.0 ** (-0.4 * mag))
    return fr * (bw / max(1e-30, br))


def run_audit(ws_dir: pathlib.Path = WS) -> list[tuple[str, bool, str]]:
    res_dir = ws_dir / "results"
    fig_dir = res_dir / "figures"
    checks: list[tuple[str, bool, str]] = []

    ml = _read_json(ws_dir / "METHOD_LOCK.json")
    lr = _read_json(ws_dir / "LOCK_RECEIPT.json")
    dr = _read_json(ws_dir / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json")
    man = _read_json(ws_dir / "FULL_D095_INPUT_MANIFEST.json")
    pe = _read_json(ws_dir / "PRIOR_EXCLUSION_VERIFICATION.json")
    summary = _read_json(res_dir / "SUMMARY.json")
    cohort = _read_csv(ws_dir / "FROZEN_COHORT_D095.csv")

    # C1: Stage-1 METHOD_LOCK & LOCK_RECEIPT + chronology
    c1_bad = [fn for fn, exp in ml["locked_file_hashes"].items() if _sha256(ws_dir / fn) != exp]
    ml_sha = _sha256(ws_dir / "METHOD_LOCK.json")
    min_lag = float(ml["hard_caps"]["min_chronology_lag_seconds"])
    c1_ok = (
        len(c1_bad) == 0
        and len(ml["locked_file_hashes"]) == 7
        and lr["method_lock_sha256"] == ml_sha
        and lr["inputs_d095_v5_3_exists"] is False
        and float(dr["chronology_lag_seconds"]) >= min_lag
    )
    checks.append(("C1_STAGE1_LOCK_CHRONOLOGY", c1_ok, f"7/7 hashes intact, lag=+{dr['chronology_lag_seconds']}s (>={min_lag}s), bad={c1_bad}"))

    # C2: Stage-2 IMPLEMENTATION_LOCK integrity
    impl = _read_json(ws_dir / "IMPLEMENTATION_LOCK.json")
    c2_bad = [fn for fn, exp in impl["locked_file_hashes"].items() if _sha256(ws_dir / fn) != exp]
    c2_ok = (
        len(c2_bad) == 0
        and impl["method_lock_sha256"] == ml_sha
        and impl["stage1_v5_3_detector_sha256"] == ml["locked_file_hashes"]["v5_3_detector.py"]
    )
    checks.append(("C2_IMPLEMENTATION_LOCK", c2_ok, f"{len(impl['locked_file_hashes'])} sealed files verified, bad={c2_bad}"))

    # C3: Bounded bundle, input manifest & free disk caps
    bundle = ws_dir / "bounded_inputs" / "d095_bounded_bundle.json.gz"
    bundle_mib = bundle.stat().st_size / (1024.0 * 1024.0)
    raw_mib = float(man["total_mib"])
    free_gib = shutil.disk_usage(ws_dir).free / (1024.0 ** 3)
    c3_ok = (
        bundle_mib < float(ml["hard_caps"]["max_bounded_bundle_mib"])
        and int(man["n_files"]) == 54
        and raw_mib <= float(ml["hard_caps"]["max_download_mib"])
        and free_gib >= float(ml["hard_caps"]["min_free_disk_gib"])
    )
    checks.append(("C3_SIZE_AND_DISK_CAPS", c3_ok, f"bundle={bundle_mib:.2f}MiB<22, 54 files raw={raw_mib:.2f}MiB<=125, free={free_gib:.2f}GiB>=1.50"))

    # C4: Cohort & prior exclusion invariants
    stars_u = {r["canonical_target"]: r for r in cohort}
    n_new = sum(1 for r in stars_u.values() if r["is_prior_bridge"] != "True")
    n_br = sum(1 for r in stars_u.values() if r["is_prior_bridge"] == "True")
    n_new_10pc = sum(1 for r in stars_u.values() if r["is_prior_bridge"] != "True" and r["within_10pc"] == "True")
    n_ctrl = sum(1 for r in stars_u.values() if r["role"] == "CONTROL")
    n_sci = sum(1 for r in stars_u.values() if r["role"] == "SCIENCE")
    c4_ok = (
        int(pe["n_prior_excluded_coords"]) == 432
        and int(pe["d095_dp_id_overlap_count"]) == 0
        and float(pe["min_brand_new_sky_separation_arcsec"]) >= float(ml["hard_caps"]["min_brand_new_separation_arcsec"])
        and len(stars_u) == 35
        and n_new == 28
        and n_br == 7
        and n_ctrl == 6
        and n_sci == 29
        and n_new_10pc == 5
        and len(cohort) == 54
    )
    checks.append(("C4_COHORT_ZERO_OVERLAP", c4_ok, f"35 stars ({n_new} new/{n_br} br/{n_new_10pc}<10pc, {n_ctrl} ctrl/{n_sci} sci), 54 inputs, 0 overlap, min_sep={pe['min_brand_new_sky_separation_arcsec']}\""))

    # C5: Exposure provenance & empirical RVs
    prov = _read_csv(res_dir / "EXPOSURE_PROVENANCE_D095.csv")
    rv_sum = _read_csv(res_dir / "STAR_RV_SUMMARY_D095.csv")
    rv_anc = _read_csv(res_dir / "STELLAR_RV_ANCHORS_D095.csv")
    c5_ok = len(prov) == 136 and len(rv_sum) == 17 and len(rv_anc) >= 500 and all(math.isfinite(float(r["rv_median_kms"])) for r in rv_sum)
    checks.append(("C5_PROVENANCE_AND_RVS", c5_ok, f"{len(prov)} APOGEE-2/GHOST exps, {len(rv_sum)} star-inst RV summaries, {len(rv_anc)} anchor fits"))

    # C6: All 10 Synthetic Calibration Suites (1,911 trials)
    cp = _read_csv(res_dir / "CALIBRATION_V53_CURVED_PERIODIC_DRIFT_240.csv")
    sp_cal = _read_csv(res_dir / "CALIBRATION_V53_SPITZER_IRS_CCF_AND_DYSON_240.csv")
    gs_cal = _read_csv(res_dir / "CALIBRATION_V53_GHOST_SKY_FIBER_120.csv")
    g8_cal = _read_csv(res_dir / "CALIBRATION_G8_V53_120.csv")
    rp_cal = _read_csv(res_dir / "CALIBRATION_V53_RPCA_RARITY_180.csv")
    ag_cal = _read_csv(res_dir / "CALIBRATION_V53_AGNOSTIC_120.csv")
    g45 = _read_csv(res_dir / "DETECTOR_V53_G4G5_CALIBRATION_108.csv")
    inj = _read_csv(res_dir / "INJECTION_RECOVERY_540.csv")
    cmb = _read_csv(res_dir / "COMB_V4_1_CALIBRATION_162.csv")
    kep = _read_csv(res_dir / "KEPLERIAN_TRACK_CALIBRATION_81.csv")

    n_cal = len(cp) + len(sp_cal) + len(gs_cal) + len(g8_cal) + len(rp_cal) + len(ag_cal) + len(g45) + len(inj) + len(cmb) + len(kep)
    cp_c = sum(1 for r in cp if r["trial_class"] == "CURVED_QUADRATIC" and r["passed"] == "1")
    cp_p = sum(1 for r in cp if r["trial_class"] == "PERIODIC_ORBITAL" and r["passed"] == "1")
    cp_vn = sum(1 for r in cp if r["trial_class"] in ("STATIONARY_STELLAR", "SINGLE_EPOCH_TRANSIENT", "BERV_SKY_CONFOUNDER") and r["passed"] == "1")
    sp_g = sum(1 for r in sp_cal if r["trial_class"] == "GAS_INJECTION" and r["passed"] == "1")
    sp_d = sum(1 for r in sp_cal if r["trial_class"] == "DYSON_WASTE_BB" and r["passed"] == "1")
    sp_vn = sum(1 for r in sp_cal if r["trial_class"] in ("SPECTRAL_CONFOUNDER", "SILICATE_DEBRIS_DISK") and r["passed"] == "1")
    gs_c = sum(1 for r in gs_cal if r["trial_class"] == "STAR_ONLY_CLEAN" and r["passed"] == "1")
    gs_v = sum(1 for r in gs_cal if r["trial_class"] == "SKY_AIRGLOW_CONTAMINATED" and r["passed"] == "1")
    g8_tp = sum(1 for r in g8_cal if r["class"] == "ISOLATED_LASER" and r["passed"] == "1")
    g8_tn = sum(1 for r in g8_cal if r["class"] != "ISOLATED_LASER" and r["passed"] == "1")
    rp_tp = sum(1 for r in rp_cal if r["class"] == "ISOLATED" and r["passed"] == "1")
    rp_tn = sum(1 for r in rp_cal if r["class"] != "ISOLATED" and r["passed"] == "1")
    ag_tp = sum(1 for r in ag_cal if r["passed"] == "1")
    g45_p = sum(1 for r in g45 if r["passed"] == "1")
    inj_p = sum(1 for r in inj if r["pass_p"] == "1")
    cmb_tp = sum(1 for r in cmb if r["class"] == "TRUE_COMB_V41" and r["passed"] == "1")
    cmb_tn = sum(1 for r in cmb if r["class"] != "TRUE_COMB_V41" and r["passed"] == "1")
    kp_rec = sum(1 for r in kep if r["kplanet_rec"] == "1")
    kp_fa = sum(1 for r in kep if r["tdiff_fa"] == "1")

    c6_ok = (
        n_cal == 1911
        and cp_c >= 54 and cp_p >= 52 and cp_vn == 120
        and sp_g >= 42 and sp_d >= 54 and sp_vn == 120
        and gs_c >= 52 and gs_v >= 57
        and g8_tp >= 38 and g8_tn == 80
        and rp_tp >= 55 and rp_tn == 120
        and ag_tp >= 114 and g45_p == 108 and inj_p >= 520
        and cmb_tp >= 50 and cmb_tn == 108
        and kp_rec >= 76 and kp_fa == 0
    )
    checks.append((
        "C6_CALIBRATION_1911_TRIALS",
        c6_ok,
        f"1911 trials: cp_drift=({cp_c}/60 cur, {cp_p}/60 per, {cp_vn}/120 veto), spitzer=({sp_g}/60 gas, {sp_d}/60 dys, {sp_vn}/120 veto), ghost=({gs_c}/60, {gs_v}/60), g8=({g8_tp}/40, {g8_tn}/80), inj={inj_p}/540, comb=({cmb_tp}/54, {cmb_tn}/108), kep={kp_rec}/81(fa={kp_fa})",
    ))

    # C7: Cascade benchmark & deterministic Stage-2 GHOST triage
    fgb = _read_csv(res_dir / "FOUR_GEN_BENCHMARK_D095.csv")
    led = _read_csv(res_dir / "V5_3_CANDIDATE_LEDGER.csv")
    raw_q = [r for r in led if r["qualified_v53"] == "True"]
    ver_q = [r for r in led if r["verified_eti"] == "True"]
    triaged_ok = (
        len(raw_q) == 4
        and all(r["instrument"] == "GEMINI_GHOST" for r in raw_q)
        and sum(1 for r in raw_q if r["star"] == "LTT9779" and r["stage2_triage_status"] == "STAGE2_VETO_SUBPHOTOSPHERIC_TROUGH") == 2
        and sum(1 for r in raw_q if r["star"] == "MASCARA1" and r["stage2_triage_status"] == "STAGE2_VETO_1EP_DRAGONS_NOCR_SPLIT_CR") == 2
        and len(ver_q) == 0
        and all(int(r["stage2_verified_eti"]) == 0 for r in fgb)
    )
    checks.append(("C7_CASCADE_STAGE2_TRIAGE", len(fgb) == 2 and triaged_ok, f"4 raw Stage-1 GHOST hits (2 LTT9779 trough + 2 MASCARA1 CR) -> {len(ver_q)} verified ETI"))

    # C8: DRIFT_V53_CURVED_AND_PERIODIC across 26 N>=4 campaigns (9 D095 + 12 Archive Q + 5 Archive T)
    dv53 = _read_csv(res_dir / "DRIFT_V53_CURVED_PERIODIC_RESULTS.csv")
    retro = _read_csv(res_dir / "RETROACTIVE_D091_D094_CURVED_PERIODIC_DRIFT.csv")
    dv52 = _read_csv(res_dir / "MULTIEPOCH_DRIFT_V52_RESULTS_D095.csv")
    n_q = sum(1 for r in retro if r["phase_source"] == "D091_ARCHIVE_Q")
    n_t = sum(1 for r in retro if r["phase_source"] == "D094_ARCHIVE_T")
    c8_ok = (
        len(dv53) == 26
        and len(retro) == 17
        and n_q == 12 and n_t == 5
        and len(dv52) == 11
        and all(int(r["total_survivors"]) == 0 for r in dv53)
        and all(int(r["survivors"]) == 0 for r in dv52)
    )
    checks.append(("C8_DRIFT_V53_26_CAMPAIGNS", c8_ok, f"26 N>=4 campaigns (9 D095 + {n_q} D091 Q + {n_t} D094 T) + 9 D095 V5.2 linear -> 0 survivors"))

    # C9: Companion Archives Q & T SHA-256 verification
    arch_specs = ml["retroactive_reused_bundles"]
    arch_dirs = [ws_dir.parent.parent / "archives", pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14/archives")]
    q_ok = t_ok = False
    for ad in arch_dirs:
        pq = ad / arch_specs[0]["archive_name"]
        pt = ad / arch_specs[1]["archive_name"]
        if pq.is_file() and _sha256(pq) == arch_specs[0]["archive_sha256"]:
            q_ok = True
        if pt.is_file() and _sha256(pt) == arch_specs[1]["archive_sha256"]:
            t_ok = True
    checks.append(("C9_ARCHIVE_QT_SHA256", q_ok and t_ok, f"Archive Q verified={q_ok}, Archive T verified={t_ok}"))

    # C10: GEMINI_GHOST Sky-IFU veto & Orbital Campaigns #126-#133
    gsky = _read_csv(res_dir / "GHOST_SKY_FIBER_VETO_SUMMARY.csv")
    orb = _read_csv(res_dir / "ORBITAL_CAMPAIGN_RESULTS_8.csv")
    c10_ok = (
        len(gsky) == 7
        and all(int(r["v53_qualified"]) == 0 for r in gsky)
        and sum(int(r["sky_fiber_vetoed_standalone"]) for r in gsky) >= 1
        and len(orb) == 8
        and [int(r["campaign_index"]) for r in orb] == list(range(126, 134))
        and all(int(r["qualified_kplanet_cands"]) == 0 for r in orb)
    )
    checks.append(("C10_GHOST_SKY_ORBITAL_126_133", c10_ok, f"7 GHOST stars ({sum(int(r['sky_fiber_vetoed_standalone']) for r in gsky)} sky-IFU vetoed); campaigns #126-#133 -> 0 ETI"))

    # C11: Spitzer IRS 18-target Greenhouse CCF & Dyson vs Silicate Disk Discrimination
    sp18 = _read_csv(res_dir / "SPITZER_IRS_CCF_AND_DYSON_18STARS.csv")
    sp_map = {r["star"]: r for r in sp18}
    sil_ok = (
        float(sp_map["HD69830"]["silicate_excess_sigma"]) >= 50.0
        and float(sp_map["HR8799"]["silicate_excess_sigma"]) >= 15.0
        and float(sp_map["FOMALHAUT"]["silicate_excess_sigma"]) >= 10.0
    )
    c11_ok = (
        len(sp18) == 18
        and all(r["detected_molecules"] == "" and r["dyson_candidate"] == "False" for r in sp18)
        and sil_ok
    )
    checks.append(("C11_SPITZER_IRS_18_TARGETS", c11_ok, f"18 Spitzer IRS targets: 0 gas detections, 0 Dyson candidates; HD69830/HR8799/FOMALHAUT silicate={sp_map['HD69830']['silicate_excess_sigma']}/{sp_map['HR8799']['silicate_excess_sigma']}/{sp_map['FOMALHAUT']['silicate_excess_sigma']} sigma"))

    # C12: Independent Pure-Stdlib Radiometric Recomputation
    ul = _read_csv(res_dir / "EIRP_UPPER_LIMITS_D095.csv")
    max_rel_err = 0.0
    for r in ul:
        wc = float(r["wave_bary_a"])
        teff = float(r["teff_k"])
        dist = float(r["dist_pc"])
        anc = r["radiometric_anchor"]
        if anc == "SPITZER_IRS_DIRECT_CGS":
            cont = float(r["direct_flam_cgs"])
            amp_eff = 1.0
        elif anc == "2MASS_H_PLANCK_CGS" and r["h_mag"]:
            cont = _planck_rel_cgs(wc, TWOMASS_H_EFF_WAVE_A, TWOMASS_H_FLAM0_CGS, float(r["h_mag"]), teff, 800.0)
            amp_eff = float(r["amp_rel_8sigma_lim"])
        elif anc == "GAIA_G_PLANCK_CGS" and r["phot_g_mag"]:
            cont = _planck_rel_cgs(wc, GAIA_G_EFF_WAVE_A, GAIA_G_FLAM0_CGS, float(r["phot_g_mag"]), teff, 1200.0)
            amp_eff = float(r["amp_rel_8sigma_lim"])
        else:
            lam_m = wc * 1e-10
            xw = min(700.0, (H_PLANCK * C_SI) / (lam_m * K_BOLTZ * teff))
            b_si = (2.0 * H_PLANCK * C_SI * C_SI) / ((lam_m ** 5) * math.expm1(xw))
            dil = (0.5 * SOLAR_RADIUS_CM / (dist * PC_CM)) ** 2
            cont = math.pi * b_si * 1e-7 * dil
            amp_eff = float(r["amp_rel_8sigma_lim"])
        fwhm = wc / float(r["resolving_power"])
        ew_a = math.sqrt(math.pi / (4.0 * math.log(2.0))) * amp_eff * fwhm
        flux = cont * ew_a
        d_cm = dist * PC_CM
        l_iso_mw = (4.0 * math.pi * d_cm * d_cm * flux * 1e-7) / 1e6
        theta = (math.pi * 10.0) / (wc * 1e-10)
        p_w = (l_iso_mw * 1e6) / (theta * theta)
        p_kw = p_w / 1000.0
        for col, pred in (
            ("continuum_flam_cgs", cont),
            ("flux_lim_erg_cm2_s", flux),
            ("l_iso_mw", l_iso_mw),
            ("p_beam_10m_w", p_w),
            ("p_beam_10m_kw", p_kw),
        ):
            obs = float(r[col])
            max_rel_err = max(max_rel_err, abs(pred - obs) / max(1e-35, abs(obs)))
    c12_ok = len(ul) >= 150 and max_rel_err < 0.002
    checks.append(("C12_STDLIB_RADIOMETRIC_LIMITS", c12_ok, f"{len(ul)} cells verified across APOGEE-2/GHOST/Spitzer IRS, max_rel_err={max_rel_err:.8f} < 0.002"))

    # C13: Ellipsoid 401 + All-Sky Comb D079-D095
    ell = _read_csv(res_dir / "MULTIEVENT_ELLIPSOID_401STARS.csv")
    c_u = _read_csv(res_dir / "ALLSKY_COMB_V4_1_UNIFIED_D079_D095.csv")
    cmb95 = _read_csv(res_dir / "COMB_V4_1_STAR_RESULTS_D095.csv")
    c13_ok = (
        len(ell) == 401
        and sum(1 for r in ell if r["etz_qualified"] == "True") >= 10
        and len(cmb95) == 17
        and sum(int(r["v41_cands"]) for r in cmb95) == 3
        and len(c_u) == 424 + len(cmb95)
        and all(int(r["verified_eti_combs"]) == 0 for r in c_u)
    )
    checks.append(("C13_ELLIPSOID_401_ALLSKY_COMB", c13_ok, f"401 ellipsoid stars ({sum(1 for r in ell if r['etz_qualified']=='True')} ETZ); {len(c_u)} all-sky comb stacks -> 0 ETI"))

    # C14: Unified 401-Star 8.709-Octave Synthesis Invariants
    u401 = _read_csv(res_dir / "UNIFIED_PANCHROMATIC_V5_3_SYNTHESIS_401STARS.csv")
    s161 = _read_csv(res_dir / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_161STARS.csv")
    b47 = _read_csv(res_dir / "PANCHROMATIC_BRIDGE_47STARS_V53.csv")
    syn = summary["unified_401star_panchromatic_v5_3_synthesis"]
    c14_ok = (
        len(u401) == 401
        and len(s161) == 161
        and len({r["star"] for r in b47}) == 47
        and all(int(r["verified_eti_detections"]) == 0 for r in u401)
        and syn["spectrographs"] == 25
        and syn["spectral_arms"] == 33
        and abs(float(syn["min_wave_um"]) - 0.0905) < 1e-6
        and abs(float(syn["max_wave_um"]) - 37.86356) < 1e-4
        and abs(float(syn["octave_span"]) - 8.709) < 1e-6
        and syn["cumulative_orbital_campaigns"] == 133
        and syn["total_calibration_trials_d079_d095"] == 36060
        and syn["verified_eti_detections_total"] == 0
    )
    checks.append(("C14_UNIFIED_401STAR_SYNTHESIS", c14_ok, f"401 stars (161<10pc, med={syn['within_10pc_median_limit_kw']}kW), 47 bridges/{len(b47)} cells, 25 instr/33 arms, 8.709 oct, 133 orb, 36060 cal, 0 ETI"))

    # C15: Completeness of 34 result files, 6 valid PNGs, VISUAL_REVIEW, SOURCES & RESULTS_REPORT
    actual_res = sorted(p.name for p in res_dir.iterdir() if p.is_file())
    actual_figs = sorted(p.name for p in fig_dir.iterdir() if p.is_file()) if fig_dir.is_dir() else []
    png_ok = all((fig_dir / fn).is_file() and (fig_dir / fn).stat().st_size > 10000 and (fig_dir / fn).read_bytes()[:8] == b"\x89PNG\r\n\x1a\n" for fn in EXPECTED_FIGURES)
    vr = _read_json(ws_dir / "VISUAL_REVIEW.json")
    src = _read_json(ws_dir / "SOURCES.json")
    c15_ok = (
        actual_res == EXPECTED_RESULT_FILES
        and actual_figs == EXPECTED_FIGURES
        and png_ok
        and vr["overall_status"] == "PASS (6/6)"
        and len(src["exposures"]) == 54
        and (ws_dir / "RESULTS_REPORT.md").is_file()
    )
    checks.append(("C15_ARTIFACTS_FIGURES_COMPLETENESS", c15_ok, f"{len(actual_res)}/34 results, {len(actual_figs)}/6 PNGs (VISUAL_REVIEW PASS), SOURCES(54)+RESULTS_REPORT"))

    # C16: Stage-2 Transparency & Stage-1 Immutability
    rep_txt = (ws_dir / "RESULTS_REPORT.md").read_text(encoding="utf-8")
    notes = summary.get("stage2_pipeline_notes", {})
    c16_ok = (
        notes.get("stage1_v5_3_detector_untouched") is True
        and "download_inputs_spitzer_header_518" in notes
        and "ghost_dragons_barycentric_wcs_awav_log" in notes
        and "spitzer_irs_bright_pedestal_guard" in notes
        and "stage2_ghost_physical_triage" in notes
        and "LTT9779" in rep_txt
        and "MASCARA1" in rep_txt
        and "S20240702S0271" in rep_txt
        and "HD38393" in rep_txt
        and "HD69830" in rep_txt
    )
    checks.append(("C16_STAGE2_TRANSPARENCY", c16_ok, "Stage-1 v5_3_detector.py & download_inputs.py untouched; Stage-2 notes & forensic vetoes documented"))

    return checks


def main() -> int:
    ws_arg = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else WS
    checks = run_audit(ws_arg)
    n_pass = sum(1 for _, ok, _ in checks if ok)
    print(f"=== D095 PURE-STDLIB AUDIT (/usr/bin/python3 -S) on {ws_arg.name} ===")
    for cid, ok, msg in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {cid}: {msg}")
    overall = n_pass == len(checks)
    print(f"OVERALL: {'PASS' if overall else 'FAIL'} ({n_pass}/{len(checks)})")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
