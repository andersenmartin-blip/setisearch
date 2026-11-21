#!/usr/bin/python3 -S
"""Pure Python stdlib independent audit (C1-C16) for SETI Phase D093 (V5.1)."""

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
RES = WS / "results"
FIG_DIR = RES / "figures"

C_SI = 299792458.0
C_KMS = 299792.458
H_PLANCK = 6.62607015e-34
K_BOLTZ = 1.380649e-23
PC_CM = 3.085677581491367e18
GAIA_G_EFF_WAVE_A = 6217.59
GAIA_G_FLAM0_CGS = 2.500e-9

EXPECTED_RESULT_FILES = [
    "ALLSKY_COMB_V4_1_CANDIDATES_D079_D093.csv",
    "ALLSKY_COMB_V4_1_UNIFIED_D079_D093.csv",
    "BLIND_DRIFT_V51_CANDIDATES.csv",
    "CALIBRATION_COMPLETENESS_BY_BAND.csv",
    "CALIBRATION_V51_AGNOSTIC_MULTISCALE_120.csv",
    "CALIBRATION_V51_BLIND_DRIFT_120.csv",
    "CALIBRATION_V51_NIRSPEC_MOL_CCF_160.csv",
    "CALIBRATION_V51_PATCH_NOVELTY_120.csv",
    "CALIBRATION_V51_RPCA_RARITY_180.csv",
    "COMB_V4_1_CALIBRATION_162.csv",
    "COMB_V4_1_CANDIDATES.csv",
    "COMB_V4_1_STAR_RESULTS_15.csv",
    "DETECTOR_V51_G4G5_CALIBRATION_108.csv",
    "EXPOSURE_PROVENANCE_D093.csv",
    "FORENSIC_CANDIDATE_AUDIT_D093.json",
    "FORENSIC_D093_CASCADE_DIAGNOSIS.json",
    "FOUR_GEN_BENCHMARK_D093.csv",
    "GEOMETRIC_SYNC_TRACKS_D093.csv",
    "INJECTION_RECOVERY_540.csv",
    "JWST_NIRSPEC_G395H_MOLECULAR_CCF_44CELLS.csv",
    "KEPLERIAN_TRACK_CALIBRATION_81.csv",
    "MULTIEVENT_ELLIPSOID_CATALOG_D079_D093.csv",
    "ORBITAL_CAMPAIGN_RESULTS_8.csv",
    "PANCHROMATIC_BRIDGE_37STARS_V51.csv",
    "RETROACTIVE_D088_NORTHERN_V51_REGRESSION.csv",
    "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_153STARS.csv",
    "STAR_RV_SUMMARY_15.csv",
    "STAR_UPPER_LIMITS_D093.csv",
    "STELLAR_RV_ANCHORS_D093.csv",
    "SUMMARY.json",
    "UNIFIED_PANCHROMATIC_V5_1_SYNTHESIS_350STARS.csv",
    "V5_1_AGNOSTIC_MULTISCALE_SURVIVORS.csv",
    "V5_1_CANDIDATE_LEDGER.csv",
]

EXPECTED_FIGURES = [
    "fig1_d093_blind_drift_and_graces_transits.png",
    "fig2_d093_rpca_rarity_g8_patch_and_d088_regression.png",
    "fig3_d093_nirspec_g395h_molecular_ccf_and_agnostic.png",
    "fig4_d093_multievent_ellipsoid_and_etz_synchronization.png",
    "fig5_d093_upper_limits_and_350star_8p27octave_atlas.png",
    "fig6_d093_five_stream_cascade_and_1591_calibration.png",
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


def _gaia_g_planck_flam_cgs(wave_a: float, phot_g_mag: float, teff_k: float) -> float:
    lam_w = wave_a * 1e-10
    lam_g = GAIA_G_EFF_WAVE_A * 1e-10
    teff = max(1200.0, teff_k)
    xw = min(700.0, (H_PLANCK * C_SI) / (lam_w * K_BOLTZ * teff))
    xg = min(700.0, (H_PLANCK * C_SI) / (lam_g * K_BOLTZ * teff))
    bw = (2.0 * H_PLANCK * C_SI * C_SI) / ((lam_w ** 5) * math.expm1(xw))
    bg = (2.0 * H_PLANCK * C_SI * C_SI) / ((lam_g ** 5) * math.expm1(xg))
    fg = GAIA_G_FLAM0_CGS * (10.0 ** (-0.4 * phot_g_mag))
    return fg * (bw / max(1e-30, bg))


def run_audit(ws_dir: pathlib.Path = WS) -> list[tuple[str, bool, str]]:
    res_dir = ws_dir / "results"
    fig_dir = res_dir / "figures"
    checks: list[tuple[str, bool, str]] = []

    ml = _read_json(ws_dir / "METHOD_LOCK.json")
    lr = _read_json(ws_dir / "LOCK_RECEIPT.json")
    dr = _read_json(ws_dir / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json")
    man = _read_json(ws_dir / "FULL_D093_INPUT_MANIFEST.json")
    pe = _read_json(ws_dir / "PRIOR_EXCLUSION_VERIFICATION.json")
    summary = _read_json(res_dir / "SUMMARY.json")
    diag = _read_json(res_dir / "FORENSIC_D093_CASCADE_DIAGNOSIS.json")
    faudit = _read_json(res_dir / "FORENSIC_CANDIDATE_AUDIT_D093.json")
    cohort = _read_csv(ws_dir / "FROZEN_COHORT_D093.csv")

    # C1: Stage-1 METHOD_LOCK & LOCK_RECEIPT cryptographic integrity + pre-download chronology
    c1_bad = [fn for fn, exp in ml["locked_file_hashes"].items() if _sha256(ws_dir / fn) != exp]
    ml_sha = _sha256(ws_dir / "METHOD_LOCK.json")
    c1_ok = (
        len(c1_bad) == 0
        and len(ml["locked_file_hashes"]) == 7
        and lr["method_lock_sha256"] == ml_sha
        and lr["inputs_d093_v5_1_exists"] is False
        and float(dr["chronology_lag_seconds"]) >= float(ml["hard_caps"]["min_chronology_lag_s"])
    )
    checks.append(("C1_STAGE1_LOCK_CHRONOLOGY", c1_ok, f"7/7 hashes intact, lag=+{dr['chronology_lag_seconds']}s, bad={c1_bad}"))

    # C2: Stage-2 IMPLEMENTATION_LOCK integrity
    impl = _read_json(ws_dir / "IMPLEMENTATION_LOCK.json")
    c2_bad = [fn for fn, exp in impl["locked_file_hashes"].items() if _sha256(ws_dir / fn) != exp]
    c2_ok = len(c2_bad) == 0 and impl["method_lock_sha256"] == ml_sha and impl["stage1_v5_1_detector_sha256"] == ml["locked_file_hashes"]["v5_1_detector.py"]
    checks.append(("C2_IMPLEMENTATION_LOCK", c2_ok, f"{len(impl['locked_file_hashes'])} files sealed, bad={c2_bad}"))

    # C3: Size & disk caps
    bundle = ws_dir / "bounded_inputs" / "d093_bounded_bundle.json.gz"
    bundle_mib = bundle.stat().st_size / (1024.0 * 1024.0)
    raw_mib = float(man["total_mib"])
    free_gib = shutil.disk_usage(ws_dir).free / (1024.0 ** 3)
    c3_ok = bundle_mib < 25.0 and raw_mib <= 225.0 and free_gib >= 6.5
    checks.append(("C3_SIZE_AND_DISK_CAPS", c3_ok, f"bundle={bundle_mib:.2f}MiB<25, raw={raw_mib:.2f}MiB<=225, free={free_gib:.2f}GiB>=6.5"))

    # C4: Prior exclusion & cohort invariants
    stars_u = {r["canonical_target"]: r for r in cohort}
    c4_ok = (
        int(pe["n_prior_excluded_coords"]) == 394
        and int(pe["d093_dp_id_overlap_count"]) == 0
        and float(pe["min_brand_new_sky_separation_arcsec"]) >= 60.0
        and len(stars_u) == 15
        and sum(1 for r in stars_u.values() if r["role"] == "CONTROL") == 5
        and sum(1 for r in stars_u.values() if r["role"] == "SCIENCE") == 10
        and sum(1 for r in stars_u.values() if r["within_10pc"] == "True") == 7
        and len(cohort) == 30
    )
    checks.append(("C4_COHORT_ZERO_OVERLAP", c4_ok, f"15 brand-new stars (5 ctrl/10 sci, 7<10pc), 30 exps, 0 dp_id overlap, min_sep={pe['min_brand_new_sky_separation_arcsec']}arcsec"))

    # C5: Exposure provenance & empirical RVs
    prov = _read_csv(res_dir / "EXPOSURE_PROVENANCE_D093.csv")
    rv_sum = _read_csv(res_dir / "STAR_RV_SUMMARY_15.csv")
    rv_anc = _read_csv(res_dir / "STELLAR_RV_ANCHORS_D093.csv")
    n_clean_anc = sum(1 for r in rv_anc if r["status"] == "CLEAN_ABSORPTION")
    c5_ok = (
        len(prov) == 30
        and all(r["header_gate"] == "PASS" for r in prov)
        and len(rv_sum) == 15
        and len(rv_anc) == 270
        and len({r["dp_id"] for r in rv_anc}) == 30
        and n_clean_anc >= 150
    )
    checks.append(("C5_PROVENANCE_AND_RVS", c5_ok, f"30/30 PASS headers, 15 star RVs, {len(rv_anc)} anchor fits ({n_clean_anc} CLEAN_ABSORPTION) across 30 dp_ids"))

    # C6: 9 synthetic calibration suites (1,591 trials)
    dr_cal = _read_csv(res_dir / "CALIBRATION_V51_BLIND_DRIFT_120.csv")
    g8_cal = _read_csv(res_dir / "CALIBRATION_V51_PATCH_NOVELTY_120.csv")
    rp_cal = _read_csv(res_dir / "CALIBRATION_V51_RPCA_RARITY_180.csv")
    ag_cal = _read_csv(res_dir / "CALIBRATION_V51_AGNOSTIC_MULTISCALE_120.csv")
    ni_cal = _read_csv(res_dir / "CALIBRATION_V51_NIRSPEC_MOL_CCF_160.csv")
    inj = _read_csv(res_dir / "INJECTION_RECOVERY_540.csv")
    kep = _read_csv(res_dir / "KEPLERIAN_TRACK_CALIBRATION_81.csv")
    g45 = _read_csv(res_dir / "DETECTOR_V51_G4G5_CALIBRATION_108.csv")
    cmb = _read_csv(res_dir / "COMB_V4_1_CALIBRATION_162.csv")

    n_tot_cal = len(dr_cal) + len(g8_cal) + len(rp_cal) + len(ag_cal) + len(ni_cal) + len(inj) + len(kep) + len(g45) + len(cmb)
    dr_rec = sum(1 for r in dr_cal if r["trial_class"] == "DRIFTING_LASER" and r["detected"] == "True")
    dr_fa = sum(1 for r in dr_cal if r["trial_class"] != "DRIFTING_LASER" and r["detected"] == "True")
    g8_rec = sum(1 for r in g8_cal if r["trial_class"] == "ISOLATED_LSF_LASER" and r["g8_pass"] == "True")
    g8_fa = sum(1 for r in g8_cal if r["trial_class"] != "ISOLATED_LSF_LASER" and r["g8_pass"] == "True")
    rp_rec = sum(1 for r in rp_cal if r["trial_class"] == "ISOLATED_LASER" and r["g7_pass"] == "True")
    rp_fa = sum(1 for r in rp_cal if r["trial_class"] != "ISOLATED_LASER" and r["g7_pass"] == "True")
    ag_rec = sum(1 for r in ag_cal if r["recovered"] == "True")
    ni_rec = sum(1 for r in ni_cal if r["expected_detection"] == "True" and r["passes_ccf"] == "True")
    ni_fa = sum(1 for r in ni_cal if r["expected_detection"] != "True" and r["any_mol_detected"] == "True")
    inj_t = sum(1 for r in inj if r["mode"] == "CHANNEL_T_TRANSIENT_1EPOCH" and float(r["sigma_mult"]) >= 8.0 and r["recovered"] == "True")
    inj_p = sum(1 for r in inj if r["mode"] == "CHANNEL_P_STATIC_COADD" and float(r["sigma_mult"]) >= 8.0 and r["recovered"] == "True")
    kep_td = sum(1 for r in kep if r["tdiff_uncomp_recovered"] == "True")
    kep_kp = sum(1 for r in kep if r["kplanet_dedop_recovered"] == "True")
    g45_tr = sum(1 for r in g45 if r["trial_class"] == "TRUE_LSF_LASER" and r["g45_pass"] == "True")
    g45_fa = sum(1 for r in g45 if r["trial_class"] != "TRUE_LSF_LASER" and r["g45_pass"] == "True")
    cmb_tr = sum(1 for r in cmb if r["trial_class"] == "TRUE_6TOOTH_STELLAR_COMB" and float(r["tooth_snr_inj"]) >= 3.8 and r["comb_v41_hit"] == "True")
    cmb_fa = sum(1 for r in cmb if r["trial_class"] != "TRUE_6TOOTH_STELLAR_COMB" and r["comb_v41_hit"] == "True")
    c6_ok = (
        n_tot_cal == 1591
        and dr_rec == 60 and dr_fa == 0
        and g8_rec >= 36 and g8_fa == 0
        and rp_rec >= 54 and rp_fa == 0
        and ag_rec >= 114
        and ni_rec >= 72 and ni_fa == 0
        and inj_t >= 145 and inj_p >= 145
        and kep_td == 0 and kep_kp >= 75
        and g45_tr == 36 and g45_fa == 0
        and cmb_tr == 36 and cmb_fa == 0
    )
    checks.append(("C6_CALIBRATION_1591_TRIALS", c6_ok, f"1591 trials: drift={dr_rec}/60(fa={dr_fa}), g8={g8_rec}/40(fa={g8_fa}), rpca={rp_rec}/60(fa={rp_fa}), ag={ag_rec}/120, nir={ni_rec}/80(fa={ni_fa}), kep={kep_kp}/81(td={kep_td}), comb={cmb_tr}/36(fa={cmb_fa})"))

    # C7: 4-Generation benchmark & narrowband cascade
    fgb = _read_csv(res_dir / "FOUR_GEN_BENCHMARK_D093.csv")
    led = _read_csv(res_dir / "V5_1_CANDIDATE_LEDGER.csv")
    n_v42 = sum(1 for r in led if r["qualified_v42_laser"] == "True")
    n_v50 = sum(1 for r in led if r["qualified_v50_laser"] == "True")
    n_v51 = sum(1 for r in led if r["qualified_v51_laser"] == "True")
    c7_ok = (
        len(fgb) == 30 and len(led) == 668
        and n_v42 == 83 and n_v50 == 8 and n_v51 == 4
        and int(faudit["verified_eti_total"]) == 0
        and diag["cascade"]["v2_legacy_false_alarms"] == 1008
    )
    checks.append(("C7_NARROWBAND_CASCADE", c7_ok, f"1008 V2 -> 668 G1 -> {n_v42} V4.2 -> {n_v50} V5.0 -> {n_v51} V5.1 -> 0 ETI"))

    # C8: Blind Drift V5.1 & Agnostic Multi-Scale streams
    dr_emp = _read_csv(res_dir / "BLIND_DRIFT_V51_CANDIDATES.csv")
    ag_emp = _read_csv(res_dir / "V5_1_AGNOSTIC_MULTISCALE_SURVIVORS.csv")
    c8_ok = (
        len(dr_emp) == 135
        and len(ag_emp) == 3
        and summary["searched_spectral_elements"]["drift_v51_shift_bin_evals"] == 111520615
        and diag["forensic_5stream_counts"]["drift_v51_candidates"]["G8_PATCH_REJECTED_ARTIFACT"] == 109
    )
    checks.append(("C8_DRIFT_AND_AGNOSTIC", c8_ok, f"111520615 drift evals -> 135 (109 G8-vetoed); agnostic -> 3; 0 ETI"))

    # C9: Retroactive Northern D088 regression
    d88 = _read_csv(res_dir / "RETROACTIVE_D088_NORTHERN_V51_REGRESSION.csv")
    d88_v39 = sum(1 for r in d88 if r["qualified_v39_laser"] == "True")
    d88_v50 = sum(1 for r in d88 if r["qualified_v50_retro"] == "True")
    d88_v51 = sum(1 for r in d88 if r["qualified_v51_retro"] == "True")
    supp = 1.0 - d88_v51 / max(1, d88_v39)
    c9_ok = len(d88) == 4727 and d88_v39 == 20 and d88_v50 == 13 and d88_v51 == 1 and abs(supp - 0.95) < 1e-9
    checks.append(("C9_RETRO_D088_SUPPRESSION", c9_ok, f"4727 G1 -> {d88_v39} V3.9 -> {d88_v50} V5.0 -> {d88_v51} V5.1 ({supp*100:.1f}%)"))

    # C10: Retroactive D090 JWST NIRSpec G395H molecular CCF
    nir = _read_csv(res_dir / "JWST_NIRSPEC_G395H_MOLECULAR_CCF_44CELLS.csv")
    nir_ctrl_flags = sum(1 for r in nir if r["role"] == "CONTROL" and r["passes_ccf"] == "True")
    nir_flags = [r for r in nir if r["passes_ccf"] == "True"]
    c10_ok = (
        len(nir) == 44
        and nir_ctrl_flags == 0
        and len(nir_flags) == 1
        and nir_flags[0]["star"] == "GJ504"
        and nir_flags[0]["molecule"] == "CH4_C2H6"
    )
    checks.append(("C10_JWST_NIRSPEC_CCF", c10_ok, f"44 cells, 0/12 ctrl flags, 1/44 physical (GJ504 CH4_C2H6 {nir_flags[0]['ccf_sigma_abs']}s -> 0 ETI)"))

    # C11: Orbital campaigns #110-#117 & All-Sky Comb V4.1
    orb = _read_csv(res_dir / "ORBITAL_CAMPAIGN_RESULTS_8.csv")
    c15 = _read_csv(res_dir / "COMB_V4_1_STAR_RESULTS_15.csv")
    c401 = _read_csv(res_dir / "ALLSKY_COMB_V4_1_UNIFIED_D079_D093.csv")
    c401_v4 = sum(int(r["comb_v4_candidates"]) for r in c401)
    c401_v41 = sum(int(r["comb_v41_candidates"]) for r in c401)
    c11_ok = (
        len(orb) == 8
        and all(int(r["qualified_v51_tdiff"]) == 0 and int(r["qualified_v51_kplanet"]) == 0 and int(r["verified_eti"]) == 0 for r in orb)
        and len(c15) == 15
        and sum(int(r["comb_v41_candidates"]) for r in c15) == 0
        and len(c401) == 401
        and c401_v4 == 22694 and c401_v41 == 109
    )
    checks.append(("C11_ORBITAL_AND_ALLSKY_COMB", c11_ok, f"8 campaigns 0 ETI; 401 all-sky comb stacks: {c401_v4} V4 -> {c401_v41} V4.1 -> 0 ETI"))

    # C12: Multi-Event Seti Ellipsoid & ETZ catalog
    ell = _read_csv(res_dir / "MULTIEVENT_ELLIPSOID_CATALOG_D079_D093.csv")
    geo = _read_csv(res_dir / "GEOMETRIC_SYNC_TRACKS_D093.csv")
    n_etz = sum(1 for r in ell if r["etz_qualified"] == "True")
    n_e180 = sum(1 for r in ell if r["ellipsoid_qualified_180d"] == "True")
    c12_ok = len(ell) == 350 and len(geo) == 15 and n_etz == 10 and n_e180 == 33
    checks.append(("C12_ELLIPSOID_AND_ETZ", c12_ok, f"350 stars evaluated, {n_etz} ETZ, {n_e180} <=180d"))

    # C13: Independent Pure-Stdlib Radiometric Recomputation across all 60 cells
    ul = _read_csv(res_dir / "STAR_UPPER_LIMITS_D093.csv")
    rv_map = {r["star"]: float(r["empirical_rv_med_kms"]) for r in rv_sum}
    gmag_map = {r["canonical_target"]: float(r["phot_g_mag"]) for r in cohort}
    max_rel_err = 0.0
    for r in ul:
        st = r["star"]
        wc_rest = float(r["wave_bary_a"]) / (1.0 + rv_map[st] / C_KMS)
        cont = _gaia_g_planck_flam_cgs(wc_rest, gmag_map[st], float(r["teff_k"]))
        fwhm = wc_rest / float(r["resolving_power"])
        ew_ma = math.sqrt(math.pi / (4.0 * math.log(2.0))) * float(r["amp_rel_8sigma_lim"]) * fwhm * 1000.0
        flux = cont * (ew_ma / 1000.0)
        d_cm = float(r["dist_pc"]) * PC_CM
        l_iso_mw = (4.0 * math.pi * d_cm * d_cm * flux * 1e-7) / 1e6
        theta = (math.pi * 10.0) / (wc_rest * 1e-10)
        p_w = (l_iso_mw * 1e6) / (theta * theta)
        p_kw = p_w / 1000.0
        for col, pred in (
            ("fwhm_lsf_a", fwhm), ("ew_lim_mA", ew_ma), ("continuum_flam_cgs", cont),
            ("flux_lim_erg_cm2_s", flux), ("l_iso_mw", l_iso_mw), ("p_beam_10m_w", p_w), ("p_beam_10m_kw", p_kw),
        ):
            obs = float(r[col])
            max_rel_err = max(max_rel_err, abs(pred - obs) / max(1e-30, abs(obs)))
    c13_ok = len(ul) == 60 and max_rel_err < 0.002
    checks.append(("C13_STDLIB_RADIOMETRIC", c13_ok, f"60/60 cells verified, max_rel_err={max_rel_err:.7f} < 0.002"))

    # C14: Unified 350-star 8.273-octave synthesis invariants
    u350 = _read_csv(res_dir / "UNIFIED_PANCHROMATIC_V5_1_SYNTHESIS_350STARS.csv")
    s153 = _read_csv(res_dir / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_153STARS.csv")
    b631 = _read_csv(res_dir / "PANCHROMATIC_BRIDGE_37STARS_V51.csv")
    syn = summary["unified_350star_panchromatic_v5_1_synthesis"]
    c14_ok = (
        len(u350) == 350 and len(s153) == 153 and len(b631) == 631
        and len({r["star"] for r in b631}) == 37
        and all(int(r["verified_eti_detections"]) == 0 for r in u350)
        and syn["total_exposures_d079_d093"] == 2163
        and syn["total_calibration_trials_d079_d093"] == 32408
        and syn["v2_false_alarms_eliminated_total"] == 302198
        and syn["cumulative_orbital_campaigns"] == 117
    )
    checks.append(("C14_UNIFIED_350STAR_SYNTHESIS", c14_ok, f"350 stars (153<10pc, med={syn['within_10pc_median_limit_kw']}kW), 37 bridges/631 cells, 2163 exps, 32408 cal, 0 ETI"))

    # C15: Completeness of 33 results + 6 PNGs + metadata reports
    actual_res = sorted(p.name for p in res_dir.iterdir() if p.is_file())
    actual_figs = sorted(p.name for p in fig_dir.iterdir() if p.is_file())
    vr = _read_json(ws_dir / "VISUAL_REVIEW.json")
    src = _read_json(ws_dir / "SOURCES.json")
    c15_ok = (
        actual_res == EXPECTED_RESULT_FILES
        and actual_figs == EXPECTED_FIGURES
        and vr["overall_status"] == "PASS (6/6)"
        and len(src["exposures"]) == 30
        and (ws_dir / "RESULTS_REPORT.md").is_file()
    )
    checks.append(("C15_ARTIFACTS_COMPLETENESS", c15_ok, f"33/33 results, 6/6 PNGs (VISUAL_REVIEW PASS), SOURCES+RESULTS_REPORT present"))

    # C16: Stage-2 refinement transparency
    rep_txt = (ws_dir / "RESULTS_REPORT.md").read_text(encoding="utf-8")
    ref = summary.get("stage2_calibration_refinements", {})
    c16_ok = (
        ref.get("stage1_v5_1_detector_untouched") is True
        and "refinement_1_g8_v51b_standardized_patch_novelty" in ref
        and "refinement_2_nirspec_v51b_joint_multicomp_ccf" in ref
        and "G8_V51b" in rep_txt
        and "nirspec_v51b_joint_multicomp_ccf" in rep_txt
    )
    checks.append(("C16_STAGE2_TRANSPARENCY", c16_ok, "Stage-1 v5_1_detector.py untouched; Stage-2 G8_V51b & nirspec_v51b documented cleanly"))

    return checks


def main() -> int:
    ws_arg = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else WS
    checks = run_audit(ws_arg)
    n_pass = sum(1 for _, ok, _ in checks if ok)
    print(f"=== D093 PURE-STDLIB AUDIT (/usr/bin/python3 -S) on {ws_arg.name} ===")
    for cid, ok, msg in checks:
        print(f"  [{ 'PASS' if ok else 'FAIL' }] {cid}: {msg}")
    overall = n_pass == len(checks)
    print(f"OVERALL: {'PASS' if overall else 'FAIL'} ({n_pass}/{len(checks)})")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
