#!/usr/bin/python3 -S
"""Pure Python stdlib independent audit (C1-C16) for SETI Phase D096 (V5.4)."""

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
    "ALLSKY_COMB_V4_1_CANDIDATES_D079_D096.csv",
    "ALLSKY_COMB_V4_1_UNIFIED_D079_D096.csv",
    "BLIND_DRIFT_V51_RESULTS_D096.csv",
    "CALIBRATION_COMPLETENESS_BY_BAND.csv",
    "CALIBRATION_G8_V54_120.csv",
    "CALIBRATION_V54_AGNOSTIC_120.csv",
    "CALIBRATION_V54_COHERENT_SHIFT_STACK_240.csv",
    "CALIBRATION_V54_JWST_SOSS_G140H_120.csv",
    "CALIBRATION_V54_RPCA_RARITY_180.csv",
    "CALIBRATION_V54_SOFIA_EXES_180.csv",
    "COMB_V4_1_CALIBRATION_162.csv",
    "COMB_V4_1_CANDIDATES.csv",
    "COMB_V4_1_STAR_RESULTS_D096.csv",
    "DETECTOR_V54_G4G5_CALIBRATION_108.csv",
    "DRIFT_V53_CURVED_PERIODIC_D096.csv",
    "DRIFT_V54_COHERENT_CANDIDATE_LEDGER.csv",
    "DRIFT_V54_COHERENT_SHIFT_STACK_20CAMPAIGNS.csv",
    "EIRP_UPPER_LIMITS_D096.csv",
    "EXPOSURE_PROVENANCE_D096.csv",
    "FOUR_GEN_BENCHMARK_D096.csv",
    "INJECTION_RECOVERY_540.csv",
    "JWST_NIRISS_SOSS_AND_G140H_6STARS.csv",
    "KEPLERIAN_TRACK_CALIBRATION_81.csv",
    "MULTIEPOCH_DRIFT_V52_RESULTS_D096.csv",
    "MULTIEVENT_ELLIPSOID_425STARS.csv",
    "ORBITAL_CAMPAIGN_RESULTS_5.csv",
    "PANCHROMATIC_BRIDGE_52STARS_V54.csv",
    "RETROACTIVE_D094_D095_COHERENT_SHIFT_STACK.csv",
    "SOFIA_EXES_MIDIR_ECHELLE_17STARS.csv",
    "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_165STARS.csv",
    "STAR_RV_SUMMARY_D096.csv",
    "STELLAR_RV_ANCHORS_D096.csv",
    "SUMMARY.json",
    "UNIFIED_PANCHROMATIC_V5_4_SYNTHESIS_425STARS.csv",
    "V5_4_AGNOSTIC_MULTISCALE_SURVIVORS.csv",
    "V5_4_CANDIDATE_LEDGER.csv",
]

EXPECTED_FIGURES = [
    "fig01_d096_panchromatic_425stars_8p71octaves.png",
    "fig02_d096_sofia_exes_midir_echelle_17stars.png",
    "fig03_d096_coherent_shift_stack_drift_v54.png",
    "fig04_d096_jwst_niriss_soss_g140h_triage.png",
    "fig05_d096_carmenes_apogee2_orbits_and_comb.png",
    "fig06_d096_multievent_ellipsoid_425stars_cal.png",
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
    man = _read_json(ws_dir / "FULL_D096_INPUT_MANIFEST.json")
    pe = _read_json(ws_dir / "PRIOR_EXCLUSION_VERIFICATION.json")
    summary = _read_json(res_dir / "SUMMARY.json")
    cohort = _read_csv(ws_dir / "FROZEN_COHORT_D096.csv")

    # C1: Stage-1 METHOD_LOCK & LOCK_RECEIPT + chronology
    c1_bad = [fn for fn, exp in ml["locked_file_hashes"].items() if _sha256(ws_dir / fn) != exp]
    ml_sha = _sha256(ws_dir / "METHOD_LOCK.json")
    min_lag = float(ml["hard_caps"]["min_chronology_lag_seconds"])
    c1_ok = (
        len(c1_bad) == 0
        and len(ml["locked_file_hashes"]) == 7
        and lr["method_lock_sha256"] == ml_sha
        and lr["inputs_d096_v5_4_exists"] is False
        and float(dr["chronology_lag_seconds"]) >= min_lag
    )
    checks.append(("C1_STAGE1_LOCK_CHRONOLOGY", c1_ok, f"7/7 hashes intact, lag=+{dr['chronology_lag_seconds']}s (>={min_lag}s), bad={c1_bad}"))

    # C2: Stage-2 IMPLEMENTATION_LOCK integrity
    impl = _read_json(ws_dir / "IMPLEMENTATION_LOCK.json")
    c2_bad = [fn for fn, exp in impl["locked_file_hashes"].items() if _sha256(ws_dir / fn) != exp]
    c2_ok = (
        len(c2_bad) == 0
        and impl["method_lock_sha256"] == ml_sha
        and impl["stage1_v5_4_detector_sha256"] == ml["locked_file_hashes"]["v5_4_detector.py"]
    )
    checks.append(("C2_IMPLEMENTATION_LOCK", c2_ok, f"{len(impl['locked_file_hashes'])} sealed files verified, bad={c2_bad}"))

    # C3: Bounded bundle, input manifest & free disk caps
    bundle = ws_dir / "bounded_inputs" / "d096_bounded_bundle.json.gz"
    bundle_mib = bundle.stat().st_size / (1024.0 * 1024.0)
    raw_mib = float(man["total_mib"])
    free_gib = shutil.disk_usage(ws_dir).free / (1024.0 ** 3)
    c3_ok = (
        bundle_mib < float(ml["hard_caps"]["max_bounded_bundle_mib"])
        and int(man["n_files"]) == 39
        and raw_mib <= float(ml["hard_caps"]["max_download_mib"])
        and free_gib >= float(ml["hard_caps"]["min_free_disk_gib"])
    )
    checks.append(("C3_SIZE_AND_DISK_CAPS", c3_ok, f"bundle={bundle_mib:.2f}MiB<22, 39 files raw={raw_mib:.3f}MiB<=125, free={free_gib:.2f}GiB>=1.50"))

    # C4: Cohort & prior exclusion invariants
    stars_u = {r["canonical_target"]: r for r in cohort}
    n_new = sum(1 for r in stars_u.values() if r["is_prior_bridge"] != "True")
    n_br = sum(1 for r in stars_u.values() if r["is_prior_bridge"] == "True")
    n_new_10pc = sum(1 for r in stars_u.values() if r["is_prior_bridge"] != "True" and r["within_10pc"] == "True")
    n_ctrl = sum(1 for r in stars_u.values() if r["role"] == "CONTROL")
    n_sci = sum(1 for r in stars_u.values() if r["role"] == "SCIENCE")
    c4_ok = (
        int(pe["n_prior_excluded_coords"]) == 460
        and int(pe["d096_dp_id_overlap_count"]) == 0
        and float(pe["min_brand_new_sky_separation_arcsec"]) >= float(ml["hard_caps"]["min_brand_new_separation_arcsec"])
        and len(stars_u) == 30
        and n_new == 24
        and n_br == 6
        and n_ctrl == 6
        and n_sci == 24
        and n_new_10pc == 4
        and len(cohort) == 39
    )
    checks.append(("C4_COHORT_ZERO_OVERLAP", c4_ok, f"30 stars ({n_new} new/{n_br} br/{n_new_10pc}<10pc, {n_ctrl} ctrl/{n_sci} sci), 39 inputs, 0 overlap, min_sep={pe['min_brand_new_sky_separation_arcsec']}\""))

    # C5: Exposure provenance & empirical RVs
    prov = _read_csv(res_dir / "EXPOSURE_PROVENANCE_D096.csv")
    rv_sum = _read_csv(res_dir / "STAR_RV_SUMMARY_D096.csv")
    rv_anc = _read_csv(res_dir / "STELLAR_RV_ANCHORS_D096.csv")
    c5_ok = len(prov) == 131 and len(rv_sum) == 7 and len(rv_anc) >= 500 and all(math.isfinite(float(r["rv_median_kms"])) for r in rv_sum)
    checks.append(("C5_PROVENANCE_AND_RVS", c5_ok, f"{len(prov)} exposures, {len(rv_sum)} CARMENES/APOGEE2 RV summaries, {len(rv_anc)} anchor fits"))

    # C6: All 10 Synthetic Calibration Suites (1,851 trials)
    ex_cal = _read_csv(res_dir / "CALIBRATION_V54_SOFIA_EXES_180.csv")
    cs_cal = _read_csv(res_dir / "CALIBRATION_V54_COHERENT_SHIFT_STACK_240.csv")
    jw_cal = _read_csv(res_dir / "CALIBRATION_V54_JWST_SOSS_G140H_120.csv")
    g8_cal = _read_csv(res_dir / "CALIBRATION_G8_V54_120.csv")
    rp_cal = _read_csv(res_dir / "CALIBRATION_V54_RPCA_RARITY_180.csv")
    ag_cal = _read_csv(res_dir / "CALIBRATION_V54_AGNOSTIC_120.csv")
    g45 = _read_csv(res_dir / "DETECTOR_V54_G4G5_CALIBRATION_108.csv")
    inj = _read_csv(res_dir / "INJECTION_RECOVERY_540.csv")
    cmb = _read_csv(res_dir / "COMB_V4_1_CALIBRATION_162.csv")
    kep = _read_csv(res_dir / "KEPLERIAN_TRACK_CALIBRATION_81.csv")

    n_cal = len(ex_cal) + len(cs_cal) + len(jw_cal) + len(g8_cal) + len(rp_cal) + len(ag_cal) + len(g45) + len(inj) + len(cmb) + len(kep)
    ex_l = sum(1 for r in ex_cal if r["class"] == "CLEAN_LASER" and r["passed"] == "1")
    ex_v = sum(1 for r in ex_cal if r["class"] != "CLEAN_LASER" and r["passed"] == "1")
    cs_c = sum(1 for r in cs_cal if r["class"] == "SUBTHRESH_CURVED" and r["passed"] == "1")
    cs_p = sum(1 for r in cs_cal if r["class"] == "SUBTHRESH_PERIODIC" and r["passed"] == "1")
    cs_v = sum(1 for r in cs_cal if r["class"] in ("STATIONARY_VETO", "TRANSIENT_VETO", "BERV_SKY_VETO") and r["passed"] == "1")
    jw_l = sum(1 for r in jw_cal if r["class"] == "SPACE_LASER" and r["passed"] == "1")
    jw_v = sum(1 for r in jw_cal if r["class"] != "SPACE_LASER" and r["passed"] == "1")
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
        n_cal == 1851
        and ex_l >= 55 and ex_v == 120
        and cs_c >= 54 and cs_p >= 50 and cs_v == 120
        and jw_l >= 54 and jw_v == 60
        and g8_tp >= 36 and g8_tn == 80
        and rp_tp >= 55 and rp_tn == 120
        and ag_tp >= 114 and g45_p == 108 and inj_p >= 520
        and cmb_tp >= 50 and cmb_tn == 108
        and kp_rec >= 76 and kp_fa == 0
    )
    checks.append((
        "C6_CALIBRATION_1851_TRIALS",
        c6_ok,
        f"1851 trials: exes=({ex_l}/60,{ex_v}/120), css=({cs_c}/60,{cs_p}/60,{cs_v}/120), jwst=({jw_l}/60,{jw_v}/60), g8=({g8_tp}/40,{g8_tn}/80), rpca=({rp_tp}/60,{rp_tn}/120), inj={inj_p}/540, comb=({cmb_tp}/54,{cmb_tn}/108), kep={kp_rec}/81(fa={kp_fa})",
    ))

    # C7: Cascade benchmark & deterministic Stage-2 ledger triage (19 JWST hits -> 0 ETI)
    fgb = _read_csv(res_dir / "FOUR_GEN_BENCHMARK_D096.csv")
    led = _read_csv(res_dir / "V5_4_CANDIDATE_LEDGER.csv")
    raw_q = [r for r in led if r["qualified_v54"] == "True"]
    ver_q = [r for r in led if r["verified_eti"] == "True"]
    triaged_ok = (
        len(raw_q) == 19
        and all("JWST" in r["instrument"] for r in raw_q)
        and sum(1 for r in raw_q if r["stage2_triage_status"].startswith("STAGE2_VETO_JWST_")) == 19
        and len(ver_q) == 0
        and all(int(r["stage2_verified_eti"]) == 0 for r in fgb)
    )
    checks.append(("C7_CASCADE_STAGE2_TRIAGE", len(fgb) == 2 and triaged_ok, f"CARMENES/APOGEE2 4-gen=0; {len(raw_q)} raw JWST Stage-1 hits (J1-J5) -> {len(ver_q)} verified ETI"))

    # C8: DRIFT_V54_COHERENT_SHIFT_STACK across 20 N>=4 campaigns + V51/V52/V53
    css = _read_csv(res_dir / "DRIFT_V54_COHERENT_SHIFT_STACK_20CAMPAIGNS.csv")
    retro = _read_csv(res_dir / "RETROACTIVE_D094_D095_COHERENT_SHIFT_STACK.csv")
    css_led = _read_csv(res_dir / "DRIFT_V54_COHERENT_CANDIDATE_LEDGER.csv")
    dv51 = _read_csv(res_dir / "BLIND_DRIFT_V51_RESULTS_D096.csv")
    dv52 = _read_csv(res_dir / "MULTIEPOCH_DRIFT_V52_RESULTS_D096.csv")
    dv53 = _read_csv(res_dir / "DRIFT_V53_CURVED_PERIODIC_D096.csv")
    n_t = sum(1 for r in retro if r["phase_source"] == "D094_ARCHIVE_T")
    n_u = sum(1 for r in retro if r["phase_source"] == "D095_ARCHIVE_U")
    c8_ok = (
        len(css) == 20
        and len(retro) == 14
        and n_t == 5 and n_u == 9
        and all(int(r["stage2_verified_eti"]) == 0 for r in css)
        and all(r["verified_eti"] == "False" for r in css_led)
        and len(dv51) == 7 and all(int(r["survivors"]) == 0 for r in dv51)
        and len(dv52) == 6 and all(int(r["survivors"]) == 0 for r in dv52)
        and len(dv53) == 6 and all(int(r["total_survivors"]) == 0 for r in dv53)
    )
    checks.append(("C8_DRIFT_V54_20_CAMPAIGNS", c8_ok, f"20 N>=4 campaigns (6 D096 + {n_u} D095 U + {n_t} D094 T), {len(css_led)} raw CSS + V51/V52/V53 -> 0 ETI"))

    # C9: Companion Archives U (D095) & T (D094) SHA-256 verification
    arch_specs = ml["retroactive_reused_bundles"]
    arch_dirs = [ws_dir.parent.parent / "archives", pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14/archives")]
    u_ok = t_ok = False
    for ad in arch_dirs:
        pu = ad / arch_specs[0]["archive_name"]
        pt = ad / arch_specs[1]["archive_name"]
        if pu.is_file() and _sha256(pu) == arch_specs[0]["archive_sha256"]:
            u_ok = True
        if pt.is_file() and _sha256(pt) == arch_specs[1]["archive_sha256"]:
            t_ok = True
    checks.append(("C9_ARCHIVE_TU_SHA256", u_ok and t_ok, f"Archive U (D095)={u_ok}, Archive T (D094)={t_ok}"))

    # C10: SOFIA_EXES 17-star Mid-IR Search & Orbital Campaigns #134-#138
    ex17 = _read_csv(res_dir / "SOFIA_EXES_MIDIR_ECHELLE_17STARS.csv")
    orb = _read_csv(res_dir / "ORBITAL_CAMPAIGN_RESULTS_5.csv")
    ex_map = {r["star"]: r for r in ex17}
    c10_ok = (
        len(ex17) == 17
        and all(int(r["n_qualified_v54"]) == 0 for r in ex17)
        and abs(float(ex_map["SIRIUS"]["best_p_beam_10m_kw"]) - 202.381291) < 0.05
        and len(orb) == 5
        and sorted(int(r["campaign_index"]) for r in orb) == list(range(134, 139))
        and all(int(r["qualified_kplanet_cands"]) == 0 for r in orb)
    )
    checks.append(("C10_SOFIA_EXES_ORBITAL_134_138", c10_ok, f"17 SOFIA/EXES stars (Sirius={ex_map['SIRIUS']['best_p_beam_10m_kw']} kW) -> 0 ETI; campaigns #134-#138 -> 0 ETI"))

    # C11: JWST NIRISS/SOSS & NIRSpec/G140H 6-star search
    jw6 = _read_csv(res_dir / "JWST_NIRISS_SOSS_AND_G140H_6STARS.csv")
    jw_map = {r["star"]: r for r in jw6}
    c11_ok = (
        len(jw6) == 6
        and all(int(r["stage2_verified_eti"]) == 0 for r in jw6)
        and abs(float(jw_map["SIMP0136"]["best_p_beam_10m_kw"]) - 0.039712) < 0.001
        and abs(float(jw_map["VHS1256B"]["best_p_beam_10m_kw"]) - 34.509826) < 0.05
    )
    checks.append(("C11_JWST_SOSS_G140H_6_TARGETS", c11_ok, f"6 JWST targets: SIMP0136={jw_map['SIMP0136']['best_p_beam_10m_kw']} kW (39.7 W), VHS1256B={jw_map['VHS1256B']['best_p_beam_10m_kw']} kW -> 0 ETI"))

    # C12: Independent Pure-Stdlib Radiometric Recomputation
    ul = _read_csv(res_dir / "EIRP_UPPER_LIMITS_D096.csv")
    max_rel_err = 0.0
    for r in ul:
        wc = float(r["wave_bary_a"])
        teff = float(r["teff_k"])
        dist = float(r["dist_pc"])
        anc = r["radiometric_anchor"]
        if anc in ("SOFIA_EXES_DIRECT_CGS", "SPITZER_IRS_DIRECT_CGS"):
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
    c12_ok = len(ul) == 69 and max_rel_err < 0.002
    checks.append(("C12_STDLIB_RADIOMETRIC_LIMITS", c12_ok, f"{len(ul)} cells verified across 5 D096 instruments, max_rel_err={max_rel_err:.8f} < 0.002"))

    # C13: Ellipsoid 425 + All-Sky Comb D079-D096
    ell = _read_csv(res_dir / "MULTIEVENT_ELLIPSOID_425STARS.csv")
    c_u = _read_csv(res_dir / "ALLSKY_COMB_V4_1_UNIFIED_D079_D096.csv")
    cmb96 = _read_csv(res_dir / "COMB_V4_1_STAR_RESULTS_D096.csv")
    c13_ok = (
        len(ell) == 425
        and sum(1 for r in ell if r["etz_qualified"] == "True") == 15
        and sum(1 for r in ell if r["ellipsoid_qualified_180d"] == "True") == 36
        and len(cmb96) == 7
        and sum(int(r["v41_cands"]) for r in cmb96) == 0
        and len(c_u) == 441 + len(cmb96)
        and all(int(r["verified_eti_combs"]) == 0 for r in c_u)
    )
    checks.append(("C13_ELLIPSOID_425_ALLSKY_COMB", c13_ok, f"425 ellipsoid stars (15 ETZ, 36 <=180d); {len(c_u)} all-sky comb stacks -> 0 ETI"))

    # C14: Unified 425-Star 8.709-Octave Synthesis Invariants
    u425 = _read_csv(res_dir / "UNIFIED_PANCHROMATIC_V5_4_SYNTHESIS_425STARS.csv")
    s165 = _read_csv(res_dir / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_165STARS.csv")
    b52 = _read_csv(res_dir / "PANCHROMATIC_BRIDGE_52STARS_V54.csv")
    syn = summary["unified_425star_panchromatic_v5_4_synthesis"]
    c14_ok = (
        len(u425) == 425
        and len(s165) == 165
        and len({r["star"] for r in b52}) == 52
        and len(b52) == 719
        and all(int(r["verified_eti_detections"]) == 0 for r in u425)
        and syn["spectrographs"] == 27
        and syn["spectral_arms"] == 36
        and abs(float(syn["min_wave_um"]) - 0.0905) < 1e-6
        and abs(float(syn["max_wave_um"]) - 37.86356) < 1e-4
        and abs(float(syn["octave_span"]) - 8.709) < 1e-6
        and syn["multi_phase_targets_total"] == 53
        and syn["cumulative_orbital_campaigns"] == 138
        and syn["total_calibration_trials_d079_d096"] == 37911
        and syn["v2_false_alarms_eliminated_total"] == 313257
        and syn["verified_eti_detections_total"] == 0
    )
    checks.append(("C14_UNIFIED_425STAR_SYNTHESIS", c14_ok, f"425 stars (165<10pc, med={syn['within_10pc_median_limit_kw']}kW), 52 bridges (+1 ctrl=53)/{len(b52)} cells, 27 instr/36 arms, 8.709 oct, 138 orb, 37911 cal, 0 ETI"))

    # C15: Completeness of 36 result files, 6 valid PNGs, VISUAL_REVIEW, SOURCES & RESULTS_REPORT
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
        and len(src["exposures"]) == 39
        and (ws_dir / "RESULTS_REPORT.md").is_file()
    )
    checks.append(("C15_ARTIFACTS_FIGURES_COMPLETENESS", c15_ok, f"{len(actual_res)}/36 results, {len(actual_figs)}/6 PNGs (VISUAL_REVIEW PASS), SOURCES(39)+RESULTS_REPORT"))

    # C16: Stage-2 Transparency & Stage-1 Immutability
    rep_txt = (ws_dir / "RESULTS_REPORT.md").read_text(encoding="utf-8")
    notes = summary.get("stage2_pipeline_notes", {})
    req_notes = (
        "sofia_exes_berv_and_rows",
        "jwst_x1d_vector_ravel_and_mad",
        "carmenes_serval_rv_and_channel_p",
        "drift_v51_v52_v54_nan_safe_triage",
        "jwst_j1_j5_physical_triage",
    )
    req_targets = ("SIRIUS", "SIMP0136", "VHS1256B", "HNLIB", "LP73158", "WOLF1069", "2M17012756", "2M23032370")
    c16_ok = (
        notes.get("stage1_v5_4_detector_untouched") is True
        and all(k in notes for k in req_notes)
        and all(t in rep_txt for t in req_targets)
    )
    checks.append(("C16_STAGE2_TRANSPARENCY", c16_ok, "Stage-1 v5_4_detector.py & download_inputs.py untouched; Stage-2 notes & forensic vetoes documented"))

    return checks


def main() -> int:
    ws_arg = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else WS
    checks = run_audit(ws_arg)
    n_pass = sum(1 for _, ok, _ in checks if ok)
    print(f"=== D096 PURE-STDLIB AUDIT (/usr/bin/python3 -S) on {ws_arg.name} ===")
    for cid, ok, msg in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {cid}: {msg}")
    overall = n_pass == len(checks)
    print(f"OVERALL: {'PASS' if overall else 'FAIL'} ({n_pass}/{len(checks)})")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
