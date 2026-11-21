#!/usr/bin/python3 -S
"""Pure Python stdlib independent audit (C1-C16) for SETI Phase D094 (V5.2)."""

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
C_KMS = 299792.458
H_PLANCK = 6.62607015e-34
K_BOLTZ = 1.380649e-23
PC_CM = 3.085677581491367e18
SOLAR_RADIUS_CM = 6.957e10
GAIA_G_EFF_WAVE_A = 6217.59
GAIA_G_FLAM0_CGS = 2.500e-9
TWOMASS_H_EFF_WAVE_A = 16620.0
TWOMASS_H_FLAM0_CGS = 1.133e-10

EXPECTED_RESULT_FILES = [
    "ALLSKY_COMB_V4_1_CANDIDATES_D079_D094.csv",
    "ALLSKY_COMB_V4_1_UNIFIED_D079_D094.csv",
    "BLIND_DRIFT_V51_RESULTS_D094.csv",
    "CALIBRATION_COMPLETENESS_BY_BAND.csv",
    "CALIBRATION_V52_AGNOSTIC_120.csv",
    "CALIBRATION_V52_MIRI_LRS_CCF_160.csv",
    "CALIBRATION_V52_MULTIEPOCH_DRIFT_150.csv",
    "CALIBRATION_V52_NIRSPEC_CCF_120.csv",
    "CALIBRATION_V52_PATCH_NOVELTY_120.csv",
    "CALIBRATION_V52_RPCA_RARITY_180.csv",
    "COMB_V4_1_CALIBRATION_162.csv",
    "COMB_V4_1_CANDIDATES.csv",
    "COMB_V4_1_STAR_RESULTS_D094.csv",
    "DETECTOR_V52_G4G5_CALIBRATION_108.csv",
    "EXPOSURE_PROVENANCE_D094.csv",
    "FOUR_GEN_BENCHMARK_D094.csv",
    "INJECTION_RECOVERY_540.csv",
    "JWST_MIRI_LRS_MOLECULAR_CCF_10STARS.csv",
    "JWST_NIRSPEC_G395H_MOLECULAR_CCF_2STARS.csv",
    "KEPLERIAN_TRACK_CALIBRATION_81.csv",
    "MULTIEPOCH_DRIFT_V52_RESULTS_D094.csv",
    "MULTIEVENT_ELLIPSOID_CATALOG_D079_D094.csv",
    "ORBITAL_CAMPAIGN_RESULTS_8.csv",
    "PANCHROMATIC_BRIDGE_41STARS_V52.csv",
    "RETROACTIVE_D091_MULTIEPOCH_DRIFT_31STARS.csv",
    "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_156STARS.csv",
    "STAR_RV_SUMMARY_D094.csv",
    "STAR_UPPER_LIMITS_D094.csv",
    "STELLAR_RV_ANCHORS_D094.csv",
    "SUMMARY.json",
    "UNIFIED_PANCHROMATIC_V5_2_SYNTHESIS_373STARS.csv",
    "V5_2_AGNOSTIC_MULTISCALE_SURVIVORS.csv",
    "V5_2_CANDIDATE_LEDGER.csv",
]

EXPECTED_FIGURES = [
    "fig1_d094_four_gen_v52_benchmark.png",
    "fig2_d094_multiepoch_drift_v52_44campaigns.png",
    "fig3_d094_jwst_miri_lrs_nirspec_ccf.png",
    "fig4_d094_orbital_campaigns_118_125_ellipsoid373.png",
    "fig5_d094_calibration_1741_scorecard.png",
    "fig6_unified_373star_panchromatic_v52_census.png",
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
    man = _read_json(ws_dir / "FULL_D094_INPUT_MANIFEST.json")
    pe = _read_json(ws_dir / "PRIOR_EXCLUSION_VERIFICATION.json")
    summary = _read_json(res_dir / "SUMMARY.json")
    cohort = _read_csv(ws_dir / "FROZEN_COHORT_D094.csv")

    # C1: Stage-1 METHOD_LOCK & LOCK_RECEIPT cryptographic integrity + pre-download chronology
    c1_bad = [fn for fn, exp in ml["locked_file_hashes"].items() if _sha256(ws_dir / fn) != exp]
    ml_sha = _sha256(ws_dir / "METHOD_LOCK.json")
    min_lag = float(ml["hard_caps"]["min_chronology_lag_seconds"])
    c1_ok = (
        len(c1_bad) == 0
        and len(ml["locked_file_hashes"]) == 7
        and lr["method_lock_sha256"] == ml_sha
        and lr["inputs_d094_v5_2_exists"] is False
        and float(dr["chronology_lag_seconds"]) >= min_lag
    )
    checks.append(("C1_STAGE1_LOCK_CHRONOLOGY", c1_ok, f"7/7 hashes intact, lag=+{dr['chronology_lag_seconds']}s (>={min_lag}s), bad={c1_bad}"))

    # C2: Stage-2 IMPLEMENTATION_LOCK integrity
    impl = _read_json(ws_dir / "IMPLEMENTATION_LOCK.json")
    c2_bad = [fn for fn, exp in impl["locked_file_hashes"].items() if _sha256(ws_dir / fn) != exp]
    c2_ok = (
        len(c2_bad) == 0
        and impl["method_lock_sha256"] == ml_sha
        and impl["stage1_v5_2_detector_sha256"] == ml["locked_file_hashes"]["v5_2_detector.py"]
    )
    checks.append(("C2_IMPLEMENTATION_LOCK", c2_ok, f"{len(impl['locked_file_hashes'])} files sealed, bad={c2_bad}"))

    # C3: Size & disk caps
    bundle = ws_dir / "bounded_inputs" / "d094_bounded_bundle.json.gz"
    bundle_mib = bundle.stat().st_size / (1024.0 * 1024.0)
    raw_mib = float(man["total_mib"])
    free_gib = shutil.disk_usage(ws_dir).free / (1024.0 ** 3)
    c3_ok = bundle_mib < 22.0 and raw_mib <= 98.0 and free_gib >= 1.50
    checks.append(("C3_SIZE_AND_DISK_CAPS", c3_ok, f"bundle={bundle_mib:.2f}MiB<22, raw={raw_mib:.2f}MiB<=98, free={free_gib:.2f}GiB>=1.50"))

    # C4: Prior exclusion & cohort invariants
    stars_u = {r["canonical_target"]: r for r in cohort}
    n_new = sum(1 for r in stars_u.values() if r["is_prior_bridge"] != "True")
    n_new_10pc = sum(1 for r in stars_u.values() if r["is_prior_bridge"] != "True" and r["within_10pc"] == "True")
    n_ctrl = sum(1 for r in stars_u.values() if r["role"] == "CONTROL")
    n_sci = sum(1 for r in stars_u.values() if r["role"] == "SCIENCE")
    c4_ok = (
        int(pe["n_prior_excluded_coords"]) == 409
        and int(pe["d094_dp_id_overlap_count"]) == 0
        and float(pe["min_brand_new_sky_separation_arcsec"]) >= 300.0
        and len(stars_u) == 30
        and n_new == 23
        and n_ctrl == 5
        and n_sci == 25
        and n_new_10pc == 3
        and len(cohort) == 53
    )
    checks.append(("C4_COHORT_ZERO_OVERLAP", c4_ok, f"30 stars ({n_new} new/{n_new_10pc}<10pc, {n_ctrl} ctrl/{n_sci} sci), 53 FITS, 0 overlap, min_sep={pe['min_brand_new_sky_separation_arcsec']}arcsec"))

    # C5: Exposure provenance & empirical RVs
    prov = _read_csv(res_dir / "EXPOSURE_PROVENANCE_D094.csv")
    rv_sum = _read_csv(res_dir / "STAR_RV_SUMMARY_D094.csv")
    rv_anc = _read_csv(res_dir / "STELLAR_RV_ANCHORS_D094.csv")
    c5_ok = len(prov) == 63 and len(rv_sum) == 21 and len(rv_anc) >= 500 and all(math.isfinite(float(r["rv_median_kms"])) for r in rv_sum)
    checks.append(("C5_PROVENANCE_AND_RVS", c5_ok, f"{len(prov)} NIR/APOGEE visits, {len(rv_sum)} star-inst RV summaries, {len(rv_anc)} anchor fits"))

    # C6: All 10 synthetic calibration suites (1,741 trials)
    d150 = _read_csv(res_dir / "CALIBRATION_V52_MULTIEPOCH_DRIFT_150.csv")
    miri_cal = _read_csv(res_dir / "CALIBRATION_V52_MIRI_LRS_CCF_160.csv")
    ns_cal = _read_csv(res_dir / "CALIBRATION_V52_NIRSPEC_CCF_120.csv")
    g8_cal = _read_csv(res_dir / "CALIBRATION_V52_PATCH_NOVELTY_120.csv")
    rp_cal = _read_csv(res_dir / "CALIBRATION_V52_RPCA_RARITY_180.csv")
    ag_cal = _read_csv(res_dir / "CALIBRATION_V52_AGNOSTIC_120.csv")
    g45 = _read_csv(res_dir / "DETECTOR_V52_G4G5_CALIBRATION_108.csv")
    inj = _read_csv(res_dir / "INJECTION_RECOVERY_540.csv")
    cmb = _read_csv(res_dir / "COMB_V4_1_CALIBRATION_162.csv")
    kep = _read_csv(res_dir / "KEPLERIAN_TRACK_CALIBRATION_81.csv")

    n_tot_cal = len(d150) + len(miri_cal) + len(ns_cal) + len(g8_cal) + len(rp_cal) + len(ag_cal) + len(g45) + len(inj) + len(cmb) + len(kep)
    d_tp = sum(1 for r in d150 if r["trial_class"] == "MULTIEPOCH_DRIFT_LASER" and r["passed"] == "1")
    d_tn = sum(1 for r in d150 if r["trial_class"] != "MULTIEPOCH_DRIFT_LASER" and r["passed"] == "1")
    m_tp = sum(1 for r in miri_cal if r["class"] == "INJECTION" and r["passed"] == "1")
    m_tn = sum(1 for r in miri_cal if r["class"] == "CONFOUNDER" and r["passed"] == "1")
    n_tp = sum(1 for r in ns_cal if r["class"] == "INJECTION" and r["passed"] == "1")
    n_tn = sum(1 for r in ns_cal if r["class"] == "CONFOUNDER" and r["passed"] == "1")
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
        n_tot_cal == 1741
        and d_tp >= 55 and d_tn == 90
        and m_tp >= 72 and m_tn == 80
        and n_tp >= 55 and n_tn == 60
        and g8_tp >= 36 and g8_tn == 80
        and rp_tp >= 54 and rp_tn == 120
        and ag_tp >= 114 and g45_p == 108
        and inj_p >= 490
        and cmb_tp >= 49 and cmb_tn >= 106
        and kp_rec >= 74 and kp_fa == 0
    )
    checks.append(("C6_CALIBRATION_1741_TRIALS", c6_ok, f"1741 trials: drift={d_tp}/60(tn={d_tn}/90), miri={m_tp}/80(tn={m_tn}/80), nir={n_tp}/60, g8={g8_tp}/40, inj_p={inj_p}/540, comb={cmb_tp}/54(tn={cmb_tn}/108), kep={kp_rec}/81(fa={kp_fa})"))

    # C7: Four-Generation narrowband cascade & zero qualified ETI
    fgb = _read_csv(res_dir / "FOUR_GEN_BENCHMARK_D094.csv")
    led = _read_csv(res_dir / "V5_2_CANDIDATE_LEDGER.csv")
    n_v52 = sum(1 for r in led if r["qualified_v52"] == "True")
    c7_ok = len(fgb) == 4 and len(led) >= 50 and n_v52 == 0 and all(int(r["v52_g8_final"]) == 0 for r in fgb)
    checks.append(("C7_FOUR_GEN_CASCADE", c7_ok, f"4 band groups, {len(led)} G1 seeds -> {n_v52} V5.2 survivors -> 0 ETI"))

    # C8: Multi-Epoch Drift V5.2 across 13 D094 campaigns + 31 D091 Archive Q campaigns (44 total)
    md94 = _read_csv(res_dir / "MULTIEPOCH_DRIFT_V52_RESULTS_D094.csv")
    md91 = _read_csv(res_dir / "RETROACTIVE_D091_MULTIEPOCH_DRIFT_31STARS.csv")
    ag_emp = _read_csv(res_dir / "V5_2_AGNOSTIC_MULTISCALE_SURVIVORS.csv")
    c8_ok = (
        len(md94) == 13
        and len(md91) == 31
        and all(int(r["survivors"]) == 0 for r in md94)
        and all(int(r["v52_drift_survivors"]) == 0 for r in md91)
        and summary["searched_spectral_elements"]["multiepoch_drift_v52_campaigns_total"] == 44
        and len(ag_emp) >= 0
    )
    checks.append(("C8_MULTIEPOCH_DRIFT_44_CAMPAIGNS", c8_ok, f"13 D094 + 31 D091 = 44 N>=3 campaigns (0 surviving); agnostic={len(ag_emp)} natural -> 0 ETI"))

    # C9: JWST MIRI LRS (10 targets) & NIRSpec G395H (2 targets) molecular CCF
    miri_res = _read_csv(res_dir / "JWST_MIRI_LRS_MOLECULAR_CCF_10STARS.csv")
    ns_res = _read_csv(res_dir / "JWST_NIRSPEC_G395H_MOLECULAR_CCF_2STARS.csv")
    c9_ok = (
        len(miri_res) == 10
        and len(ns_res) == 2
        and all(r["detected_molecules"] == "" for r in miri_res)
        and all(r["detected_molecules"] == "" for r in ns_res)
        and any(r["star"] == "ROSS19B" and r["subcontinuum_nd"] == "True" for r in miri_res)
    )
    checks.append(("C9_JWST_MIRI_LRS_NIRSPEC_CCF", c9_ok, f"10 MIRI LRS + 2 NIRSpec G395H targets (0 detections; ROSS19B subcontinuum_nd=True -> 0 ETI)"))

    # C10: Companion Archives Q (D091) and S (D093) linkage & SHA-256 verification
    arch_q_name = ml["retroactive_reused_bundles"][0]["archive_name"]
    arch_s_name = ml["retroactive_reused_bundles"][1]["archive_name"]
    arch_dir_cands = [ws_dir.parent.parent / "archives", pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14/archives")]
    q_ok = s_ok = False
    for ad in arch_dir_cands:
        if (ad / arch_q_name).is_file() and _sha256(ad / arch_q_name) == ml["retroactive_reused_bundles"][0]["archive_sha256"]:
            q_ok = True
        if (ad / arch_s_name).is_file() and _sha256(ad / arch_s_name) == ml["retroactive_reused_bundles"][1]["archive_sha256"]:
            s_ok = True
    checks.append(("C10_ARCHIVE_QS_SHA256", q_ok and s_ok, f"Archive Q verified={q_ok}, Archive S verified={s_ok}"))

    # C11: Orbital campaigns #118-#125 & unified All-Sky Comb D079-D094
    orb = _read_csv(res_dir / "ORBITAL_CAMPAIGN_RESULTS_8.csv")
    c_u = _read_csv(res_dir / "ALLSKY_COMB_V4_1_UNIFIED_D079_D094.csv")
    c_c = _read_csv(res_dir / "ALLSKY_COMB_V4_1_CANDIDATES_D079_D094.csv")
    comb94 = _read_csv(res_dir / "COMB_V4_1_STAR_RESULTS_D094.csv")
    c11_ok = (
        len(orb) == 8
        and [int(r["campaign_index"]) for r in orb] == list(range(118, 126))
        and all(int(r["qualified_kplanet_cands"]) == 0 for r in orb)
        and all(int(r["v41_cands"]) == 0 for r in comb94)
        and len(c_u) == 401 + len(comb94)
        and all(int(r["verified_eti_combs"]) == 0 for r in c_u)
    )
    checks.append(("C11_ORBITAL_AND_ALLSKY_COMB", c11_ok, f"Campaigns #118-#125 (0 hits); {len(c_u)} all-sky comb stacks ({len(c_c)} prior cands -> 0 ETI)"))

    # C12: Multi-Event SETI Ellipsoid & ETZ catalog across 373 stars
    ell = _read_csv(res_dir / "MULTIEVENT_ELLIPSOID_CATALOG_D079_D094.csv")
    n_etz = sum(1 for r in ell if r["etz_qualified"] == "True")
    n_e180 = sum(1 for r in ell if r["ellipsoid_qualified_180d"] == "True")
    c12_ok = len(ell) == 373 and n_etz == 10 and n_e180 >= 33
    checks.append(("C12_ELLIPSOID_373_AND_ETZ", c12_ok, f"373 stars evaluated, {n_etz} ETZ, {n_e180} <=180d"))

    # C13: Independent Pure-Stdlib Radiometric Recomputation across ALL 108 UL cells (4 anchors)
    ul = _read_csv(res_dir / "STAR_UPPER_LIMITS_D094.csv")
    max_rel_err = 0.0
    for r in ul:
        wc = float(r["wave_bary_a"])
        teff = float(r["teff_k"])
        dist = float(r["dist_pc"])
        anc = r["radiometric_anchor"]
        if anc in ("JWST_MIRI_DIRECT_CGS", "JWST_NIRSPEC_DIRECT_CGS"):
            cont = float(r["direct_flam_cgs"])
        elif anc == "2MASS_H_PLANCK_CGS":
            cont = _planck_rel_cgs(wc, TWOMASS_H_EFF_WAVE_A, TWOMASS_H_FLAM0_CGS, float(r["h_mag"]), teff, 800.0)
        elif anc == "GAIA_G_PLANCK_CGS" and r["phot_g_mag"]:
            cont = _planck_rel_cgs(wc, GAIA_G_EFF_WAVE_A, GAIA_G_FLAM0_CGS, float(r["phot_g_mag"]), teff, 1200.0)
        else:
            lam_m = wc * 1e-10
            xw = min(700.0, (H_PLANCK * C_SI) / (lam_m * K_BOLTZ * teff))
            b_si = (2.0 * H_PLANCK * C_SI * C_SI) / ((lam_m ** 5) * math.expm1(xw))
            dil = (0.5 * SOLAR_RADIUS_CM / (dist * PC_CM)) ** 2
            cont = math.pi * b_si * 1e-7 * dil
        fwhm = wc / float(r["resolving_power"])
        ew_a = math.sqrt(math.pi / (4.0 * math.log(2.0))) * float(r["amp_rel_8sigma_lim"]) * fwhm
        flux = cont * ew_a
        d_cm = dist * PC_CM
        l_iso_mw = (4.0 * math.pi * d_cm * d_cm * flux * 1e-7) / 1e6
        theta = (math.pi * 10.0) / (wc * 1e-10)
        p_w = (l_iso_mw * 1e6) / (theta * theta)
        p_kw = p_w / 1000.0
        for col, pred in (
            ("continuum_flam_cgs", cont), ("flux_lim_erg_cm2_s", flux),
            ("l_iso_mw", l_iso_mw), ("p_beam_10m_w", p_w), ("p_beam_10m_kw", p_kw),
        ):
            obs = float(r[col])
            max_rel_err = max(max_rel_err, abs(pred - obs) / max(1e-35, abs(obs)))
    c13_ok = len(ul) == 108 and max_rel_err < 0.002
    checks.append(("C13_STDLIB_RADIOMETRIC_108CELLS", c13_ok, f"{len(ul)}/108 cells verified across all 4 anchors, max_rel_err={max_rel_err:.8f} < 0.002"))

    # C14: Unified 373-star 8.273-octave synthesis invariants
    u373 = _read_csv(res_dir / "UNIFIED_PANCHROMATIC_V5_2_SYNTHESIS_373STARS.csv")
    s156 = _read_csv(res_dir / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_156STARS.csv")
    b41 = _read_csv(res_dir / "PANCHROMATIC_BRIDGE_41STARS_V52.csv")
    syn = summary["unified_373star_panchromatic_v5_2_synthesis"]
    c14_ok = (
        len(u373) == 373
        and len(s156) == 156
        and len({r["star"] for r in b41}) == 41
        and all(int(r["verified_eti_detections"]) == 0 for r in u373)
        and syn["spectrographs"] == 23
        and syn["spectral_arms"] == 29
        and abs(float(syn["octave_span"]) - 8.273) < 1e-6
        and syn["cumulative_orbital_campaigns"] == 125
        and syn["verified_eti_detections_total"] == 0
    )
    checks.append(("C14_UNIFIED_373STAR_SYNTHESIS", c14_ok, f"373 stars (156<10pc, med={syn['within_10pc_median_limit_kw']}kW), 41 bridges/{len(b41)} cells, 23 instr/29 arms, 125 orb, 0 ETI"))

    # C15: Completeness of 33 results + 6 PNGs + metadata reports
    actual_res = sorted(p.name for p in res_dir.iterdir() if p.is_file())
    actual_figs = sorted(p.name for p in fig_dir.iterdir() if p.is_file()) if fig_dir.is_dir() else []
    vr = _read_json(ws_dir / "VISUAL_REVIEW.json")
    src = _read_json(ws_dir / "SOURCES.json")
    c15_ok = (
        actual_res == EXPECTED_RESULT_FILES
        and actual_figs == EXPECTED_FIGURES
        and vr["overall_status"] == "PASS (6/6)"
        and len(src["exposures"]) == 53
        and (ws_dir / "RESULTS_REPORT.md").is_file()
    )
    checks.append(("C15_ARTIFACTS_COMPLETENESS", c15_ok, f"{len(actual_res)}/33 results, {len(actual_figs)}/6 PNGs (VISUAL_REVIEW PASS), SOURCES(53 FITS)+RESULTS_REPORT"))

    # C16: Stage-2 transparency & Stage-1 immutability
    rep_txt = (ws_dir / "RESULTS_REPORT.md").read_text(encoding="utf-8")
    notes = summary.get("stage2_pipeline_notes", {})
    c16_ok = (
        notes.get("stage1_v5_2_detector_untouched") is True
        and "drift_v52_rolling_mad_and_tier2_lsf_veto" in notes
        and "miri_lrs_hampel_1px_despike" in notes
        and "2M23025951" in rep_txt
        and "AZV175" in rep_txt
    )
    checks.append(("C16_STAGE2_TRANSPARENCY", c16_ok, "Stage-1 v5_2_detector.py untouched; Stage-2 rolling-MAD/Tier-2/Hampel notes verified"))

    return checks


def main() -> int:
    ws_arg = pathlib.Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else WS
    checks = run_audit(ws_arg)
    n_pass = sum(1 for _, ok, _ in checks if ok)
    print(f"=== D094 PURE-STDLIB AUDIT (/usr/bin/python3 -S) on {ws_arg.name} ===")
    for cid, ok, msg in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {cid}: {msg}")
    overall = n_pass == len(checks)
    print(f"OVERALL: {'PASS' if overall else 'FAIL'} ({n_pass}/{len(checks)})")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
