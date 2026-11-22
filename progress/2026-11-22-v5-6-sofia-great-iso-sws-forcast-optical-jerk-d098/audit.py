#!/usr/bin/env python3
"""Pure-stdlib (C1-C16) independent cryptographic & scientific audit for Phase D098 (V5.6)."""

from __future__ import annotations

import argparse
import ast
import collections
import csv
import hashlib
import json
import math
import os
import pathlib
import sys
import zipfile

WS_DEFAULT = pathlib.Path(__file__).resolve().parent
METHOD_LOCK_SHA256 = "47c7c08a538b6debb980904dafe47c39a50c3063f4ce05e86764a2bc1480b84f"
BUNDLE_GZ_SHA256 = "468c3416778f37f335e990147dc3fecd41ae3281f64b6bbf9873dbe9b3396938"
BUNDLE_GZ_BYTES = 17809870
PC_TO_CM = 3.085677581e18

RETRO_ARCHIVES = [
    (
        "D097",
        "SETI_D097_V5_5_HERSCHEL_THZ_FARIR_STIS_E140H_OPTICAL_JERK_RESULTS_2026-11-22.zip",
        11687103,
        "aa296f9c72faefcacbd4f4fedb73c7c3f2b1377823fad3e308fd6a9844f6fed8",
        "work_v5_5_20261122_d097_herschel_thz_farir_stis_e140h_optical_jerk/bounded_inputs/d097_bounded_bundle.json.gz",
        "05b9d096a76082f9b2bca30ab73a01329a20c1b40c651ce2a76bf0647626f41a",
    ),
    (
        "D096",
        "SETI_D096_V5_4_SOFIA_EXES_MIDIR_ECHELLE_COHERENT_DRIFT_JWST_RESULTS_2026-11-21.zip",
        15941580,
        "a134e4d5d0b6e0cb4e17763dc729203218cac9265c7db75db719135cb01c5158",
        "work_v5_4_20261121_d096_sofia_exes_midir_echelle_coherent_drift_jwst/bounded_inputs/d096_bounded_bundle.json.gz",
        "319f4cd7b6fe1bcc24f5bb74fc6a432019c0ed30a55d04f075b1c78fc9057e91",
    ),
    (
        "D095",
        "SETI_D095_V5_3_CURVED_PERIODIC_DRIFT_GHOST_SPITZER_IRS_APOGEE2_RESULTS_2026-11-21.zip",
        16898458,
        "24f5a73a4299d697a198e91e3e15b5b7ddce838f6d055cebe66ddd812520c21d",
        "bounded_inputs/d095_bounded_bundle.json.gz",
        "db0ab9adc9f3067909af2cefafb9e0b56095d87107a9510a6cce0a9406ca59b8",
    ),
    (
        "D094",
        "SETI_D094_V5_2_MULTIEPOCH_DRIFT_APOGEE2_CRIRESJH_MIRILRS_RESULTS_2026-11-21.zip",
        16641712,
        "fea863077ae837b6741d5837990fd357158e00f6a5e3d9adde51f0c81e8ccefc",
        "bounded_inputs/d094_bounded_bundle.json.gz",
        "d6601113eec302bfb393874ffb48d32aa90d073f4bae7b6b37e256ad0cb89c42",
    ),
]


def _sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(65536)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _read_csv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _resolve_archives_dir(ws: pathlib.Path, explicit: pathlib.Path | None) -> pathlib.Path:
    candidates: list[pathlib.Path] = []
    if explicit is not None:
        candidates.append(explicit)
    env_dir = os.environ.get("SETI_ARCHIVES_DIR")
    if env_dir:
        candidates.append(pathlib.Path(env_dir))
    candidates.extend([ws.parent.parent / "archives", ws.parent / "archives", ws / "archives"])
    for cand in candidates:
        if cand.is_dir() and (cand / RETRO_ARCHIVES[0][1]).is_file():
            return cand
    return candidates[0]


def run_audit(ws: pathlib.Path, archives_dir: pathlib.Path | None = None) -> tuple[int, int]:
    res = ws / "results"
    arch_dir = _resolve_archives_dir(ws, archives_dir)
    results: list[tuple[str, bool, str]] = []

    def rec(cid: str, ok: bool, msg: str) -> None:
        results.append((cid, ok, msg))

    # C1: Stage-1 Prospective Seal & Lock Invariance
    ml_path = ws / "METHOD_LOCK.json"
    ml = json.loads(ml_path.read_text(encoding="utf-8"))
    ml_sha = _sha256_file(ml_path)
    lr = json.loads((ws / "LOCK_RECEIPT.json").read_text(encoding="utf-8"))
    fdr = json.loads((ws / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json").read_text(encoding="utf-8"))
    diffs_s1 = [
        fn for fn, exp in ml["locked_file_hashes"].items() if _sha256_file(ws / fn) != exp
    ]
    c1_ok = (
        ml_sha == METHOD_LOCK_SHA256
        and len(ml["locked_file_hashes"]) == 7
        and not diffs_s1
        and lr["locked_utc"] == "2026-11-22T11:45:30Z"
        and lr["method_lock_sha256"] == METHOD_LOCK_SHA256
        and float(fdr["chronology_lag_seconds"]) >= 3.0
        and fdr["first_dp_id"] == "GREAT.75_0050_Betelgeuse_OI_averaged"
    )
    rec("C1", c1_ok, f"METHOD_LOCK 7/7 Stage-1 diffs={len(diffs_s1)}, lag={fdr['chronology_lag_seconds']}s")

    # C2: Prior Exclusion & Spatial Uniqueness
    pe = json.loads((ws / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    c2_ok = (
        pe["n_prior_excluded_coords"] == 507
        and pe["n_prior_excluded_dp_ids"] == 2884
        and pe["d098_dp_id_overlap_count"] == 0
        and float(pe["min_brand_new_sky_separation_arcsec"]) >= 5000.0
        and float(pe["min_intra_d098_separation_arcsec"]) >= 20000.0
    )
    rec("C2", c2_ok, f"prior={pe['n_prior_excluded_coords']} coords/{pe['n_prior_excluded_dp_ids']} dp_ids, overlap={pe['d098_dp_id_overlap_count']}")

    # C3: Cohort & Provenance Closure + Bounded Bundle
    summary = json.loads((res / "SUMMARY.json").read_text(encoding="utf-8"))
    coh = summary["cohort"]
    prov = _read_csv(res / "EXPOSURE_PROVENANCE_D098.csv")
    inst_counts = collections.Counter(r["instrument"] for r in prov)
    tot_h = sum(float(r["t_exptime_s"]) for r in prov) / 3600.0
    gz = ws / "bounded_inputs" / "d098_bounded_bundle.json.gz"
    c3_ok = (
        summary["phase_id"] == "D098"
        and coh["total_stars"] == 38
        and coh["brand_new_unique_stars"] == 25
        and coh["prior_bridge_stars"] == 13
        and len(coh["newly_promoted_science_bridges"]) == 8
        and len(coh["deepened_science_bridges"]) == 4
        and coh["revisited_controls"] == ["NGC7027"]
        and coh["control_stars"] == 8
        and coh["brand_new_within_10pc"] == 4
        and coh["total_input_files"] == 99
        and len(prov) == 99
        and inst_counts["SOFIA_GREAT"] == 27
        and inst_counts["ISO_SWS"] == 17
        and inst_counts["SOFIA_FORCAST"] == 35
        and inst_counts["CARMENES_VIS"] == 20
        and abs(tot_h - 148.7684) < 0.001
        and gz.is_file()
        and gz.stat().st_size == BUNDLE_GZ_BYTES
        and _sha256_file(gz) == BUNDLE_GZ_SHA256
    )
    rec("C3", c3_ok, f"38 stars, 99 exp ({tot_h:.4f}h), bundle={gz.stat().st_size} B")

    # C4: 2,031-Trial 11-Suite Calibration Scorecard
    cal_specs = [
        ("CALIBRATION_V56_SOFIA_GREAT_180.csv", "passed", 180, 180),
        ("CALIBRATION_V56_ISO_SWS_180.csv", "passed", 180, 180),
        ("CALIBRATION_V56_SOFIA_FORCAST_120.csv", "passed", 120, 120),
        ("CALIBRATION_V56_COHERENT_JERK_240.csv", "passed", 240, 240),
        ("CALIBRATION_G8_V56_120.csv", "passed", 120, 117),
        ("CALIBRATION_V56_RPCA_RARITY_180.csv", "passed", 180, 180),
        ("CALIBRATION_V56_AGNOSTIC_120.csv", "passed", 120, 117),
        ("DETECTOR_V56_G4G5_CALIBRATION_108.csv", "passed", 108, 108),
        ("INJECTION_RECOVERY_540.csv", "pass_p", 540, 539),
        ("COMB_V4_1_CALIBRATION_162.csv", "passed", 162, 162),
        ("KEPLERIAN_TRACK_CALIBRATION_81.csv", "kplanet_rec", 81, 81),
    ]
    tot_trials = 0
    tot_passed = 0
    c4_ok = True
    for fn, col, exp_n, exp_p in cal_specs:
        rows = _read_csv(res / fn)
        p = sum(1 for r in rows if str(r[col]).strip().lower() in ("1", "true", "yes", "pass"))
        tot_trials += len(rows)
        tot_passed += p
        if len(rows) != exp_n or p != exp_p:
            c4_ok = False
    c4_ok = c4_ok and tot_trials == 2031 and tot_passed == 2024
    rec("C4", c4_ok, f"{tot_passed}/{tot_trials} trials across 11 V5.6 suites")

    # C5: Stream 1A SOFIA/GREAT
    great = _read_csv(res / "SOFIA_GREAT_SUPERTHZ_12STARS.csv")
    hd14 = [r for r in great if r["star"] == "HD141569"][0]
    c5_ok = (
        len(great) == 12
        and sum(int(r["n_cubes"]) for r in great) == 27
        and sum(int(r["raw_peaks"]) for r in great) == 23
        and sum(int(r["qualified_v56"]) for r in great) == 0
        and sum(int(r["stage2_verified_eti"]) for r in great) == 0
        and abs(float(hd14["best_p_beam_10m_kw"]) - 19268981.04064) < 0.01
    )
    rec("C5", c5_ok, f"SOFIA_GREAT 12 stars/27 cubes, 23 raw->0 ETI, best={float(hd14['best_p_beam_10m_kw']):.2f} kW")

    # C6: Stream 1B/1C ISO_SWS & SOFIA_FORCAST + Space Ledger
    sws = _read_csv(res / "ISO_SWS_MIDIR_GAPCLOSURE_17STARS.csv")
    fcast = _read_csv(res / "SOFIA_FORCAST_4GRISM_11STARS.csv")
    sp_led = _read_csv(res / "V5_6_SPACE_CANDIDATE_LEDGER.csv")
    hd21 = [r for r in sws if r["star"] == "HD219134"][0]
    hd16 = [r for r in fcast if r["star"] == "HD166191"][0]
    c6_ok = (
        len(sws) == 17
        and sum(int(r["raw_peaks"]) for r in sws) == 52
        and sum(int(r["qualified_v56"]) for r in sws) == 0
        and sum(int(r["stage2_verified_eti"]) for r in sws) == 0
        and all(str(r["ccf_detected"]).strip() in ("", "0", "False", "false") for r in sws)
        and all(str(r["dyson_stage1_flag"]).strip() in ("0", "False", "false") for r in sws)
        and abs(float(hd21["best_p_beam_10m_kw"]) - 2781.394779) < 0.01
        and len(fcast) == 11
        and sum(int(r["n_grisms"]) for r in fcast) == 35
        and sum(int(r["raw_peaks"]) for r in fcast) == 33
        and sum(int(r["qualified_v56"]) for r in fcast) == 0
        and sum(int(r["stage2_verified_eti"]) for r in fcast) == 0
        and abs(float(hd16["best_p_beam_10m_kw"]) - 21388408.733542) < 0.01
        and len(sp_led) == 108
        and all(str(r["verified_eti"]).lower() == "false" for r in sp_led)
    )
    rec("C6", c6_ok, f"ISO_SWS 52 raw->0 (2781.39 kW); FORCAST 33 raw->0 (21.39 GW); Space=108->0")

    # C7: Stream 2 CARMENES_VIS 4-Gen & Orbits #141-#143
    fg = _read_csv(res / "FOUR_GEN_BENCHMARK_D098.csv")[0]
    orb = _read_csv(res / "ORBITAL_CAMPAIGN_RESULTS_3.csv")
    c_led = _read_csv(res / "V5_6_CANDIDATE_LEDGER.csv")
    best_opt = summary["best_10m_eirp_limits_kw"]["CARMENES_VIS"]
    c7_ok = (
        int(fg["n_stars"]) == 5
        and int(fg["n_exposures"]) == 20
        and int(fg["g1_seeds"]) == 514
        and int(fg["g2_pass"]) == 486
        and int(fg["g3_pass"]) == 484
        and int(fg["g45_pass"]) == 2
        and int(fg["g6_pass"]) == 0
        and int(fg["g7_pass"]) == 0
        and int(fg["g8_pass"]) == 0
        and int(fg["stage2_verified_eti"]) == 0
        and len(orb) == 3
        and {int(r["campaign_index"]) for r in orb} == {141, 142, 143}
        and sum(int(r["verified_eti"]) for r in orb) == 0
        and len(c_led) == 0
        and best_opt["star"] == "GJ1286"
        and best_opt["band_id"] == "M1_5320"
        and abs(float(best_opt["p_beam_10m_kw"]) - 0.45553819) < 1e-4
    )
    rec("C7", c7_ok, f"CARMENES 514->486->484->2->0, Orbits #141-#143=0 ETI, GJ1286={best_opt['p_beam_10m_kw']:.5f} kW")

    # C8: Stream 3 DRIFT_V56 30-Campaign Coherent 3D Jerk Search
    c30 = _read_csv(res / "DRIFT_V56_COHERENT_JERK_30CAMPAIGNS.csv")
    r25 = _read_csv(res / "RETROACTIVE_D094_D097_COHERENT_JERK.csv")
    dled = _read_csv(res / "DRIFT_V56_COHERENT_CANDIDATE_LEDGER.csv")
    disp_cnt = collections.Counter(r["stage2_triage_status"] for r in dled)
    by_id = {r["cand_id"]: r for r in dled}
    c8_ok = (
        len(c30) == 30
        and len(r25) == 25
        and sum(int(r["n_trajectories_evaluated"]) for r in c30) == 38226
        and sum(int(r["n_pixel_trajectory_integrals"]) for r in c30) == 2298916322
        and sum(int(r["raw_coherent_survivors"]) for r in c30) == 8344
        and sum(int(r["jerk_survivors"]) for r in c30) == 5198
        and sum(int(r["curved_survivors"]) for r in c30) == 3141
        and sum(int(r["periodic_survivors"]) for r in c30) == 5
        and sum(int(r["stage2_verified_eti"]) for r in c30) == 0
        and len(dled) == 8344
        and disp_cnt["STAGE2_VETO_SUBPHOTOSPHERIC_TROUGH"] == 6948
        and disp_cnt["STAGE2_VETO_STATIONARY_OR_ABSORPTION_BAND"] == 714
        and disp_cnt["STAGE2_VETO_OH_SKY_OR_TELLURIC"] == 675
        and disp_cnt["STAGE2_VETO_NON_LSF_SHAPE"] == 6
        and disp_cnt["STAGE2_VETO_LOWCONT_CR_RINGING"] == 1
        and by_id["CSS56_D097_GJ1005_003"]["stage2_triage_status"] == "STAGE2_VETO_LOWCONT_CR_RINGING"
        and by_id["CSS56_D096_WOLF1069_931"]["stage2_triage_status"] == "STAGE2_VETO_STATIONARY_OR_ABSORPTION_BAND"
        and all(str(r["verified_eti"]).lower() == "false" for r in dled)
    )
    rec("C8", c8_ok, "30 campaigns, 38,226 traj, 2,298,916,322 px, 8,344->0 ETI (incl GJ1005 & Wolf 1069)")

    # C9: Retroactive Companion Archives W/V/U/T Pin & Bundle SHA-256
    c9_ok = True
    c9_notes: list[str] = []
    for ph, zname, zbytes, zsha, member, bsha in RETRO_ARCHIVES:
        zp = arch_dir / zname
        if not (zp.is_file() and zp.stat().st_size == zbytes and _sha256_file(zp) == zsha):
            c9_ok = False
            c9_notes.append(f"{ph}:ZIP_FAIL")
            continue
        with zipfile.ZipFile(zp, "r") as zf:
            got_bsha = hashlib.sha256(zf.read(member)).hexdigest()
        if got_bsha != bsha:
            c9_ok = False
            c9_notes.append(f"{ph}:BUNDLE_FAIL")
        else:
            c9_notes.append(f"{ph}:OK")
    rec("C9", c9_ok, f"Archives W/V/U/T + internal bundles verified ({', '.join(c9_notes)})")

    # C10: Stream 4 Unified 473-Star Panchromatic Synthesis
    u473 = _read_csv(res / "UNIFIED_PANCHROMATIC_V5_6_SYNTHESIS_473STARS.csv")
    u173 = _read_csv(res / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_173STARS.csv")
    b66 = _read_csv(res / "PANCHROMATIC_BRIDGE_66STARS_V56.csv")
    u_syn = summary["unified_473star_panchromatic_v5_6_synthesis"]
    med10 = sorted(float(r["min_panchromatic_10m_kw"]) for r in u173 if r["min_panchromatic_10m_kw"])
    med_val = med10[len(med10) // 2] if len(med10) % 2 else 0.5 * (med10[len(med10) // 2 - 1] + med10[len(med10) // 2])
    c10_ok = (
        len(u473) == 473
        and sum(1 for r in u473 if r["role"] == "SCIENCE") == 363
        and sum(1 for r in u473 if r["role"] == "CONTROL") == 110
        and sum(1 for r in u473 if r["role"] == "SCIENCE" and int(float(r["n_exoplanets"])) > 0) == 210
        and sum(int(float(r["n_exoplanets"])) for r in u473 if r["role"] == "SCIENCE") == 405
        and len(u173) == 173
        and sum(1 for r in u173 if r["role"] == "SCIENCE") == 129
        and sum(1 for r in u173 if r["role"] == "CONTROL") == 44
        and sum(1 for r in u173 if r["role"] == "SCIENCE" and int(float(r["n_exoplanets"])) > 0) == 61
        and sum(int(float(r["n_exoplanets"])) for r in u173 if r["role"] == "SCIENCE") == 121
        and abs(med_val - 1.45576462) < 1e-4
        and len(b66) == 780
        and len({r["star"] for r in b66}) == 66
        and u_syn["spectrographs"] == 33
        and u_syn["spectral_arms"] == 51
        and abs(float(u_syn["octave_span"]) - 12.855) < 1e-4
        and u_syn["multi_phase_targets_total"] == 68
        and u_syn["total_exposures_d079_d098"] == 2700
        and abs(float(u_syn["total_integration_hours_d079_d098"]) - 921.5744) < 0.01
        and u_syn["total_calibration_trials_d079_d098"] == 41973
        and u_syn["v2_false_alarms_eliminated_total"] == 423988
        and u_syn["cumulative_orbital_campaigns"] == 143
        and u_syn["cumulative_comb_stacks"] == 458
        and u_syn["coherent_3d_drift_campaigns"] == 30
        and u_syn["verified_eti_detections_total"] == 0
    )
    rec("C10", c10_ok, "473 stars (363/110, 210/405), 173 <10pc (1.4558 kW), 66 bridges/780 cells, 33/51, 12.855 oct")

    # C11: COMB_V4_1, Multievent Ellipsoid, & Agnostic
    comb_s = _read_csv(res / "COMB_V4_1_STAR_RESULTS_D098.csv")
    comb_c = _read_csv(res / "COMB_V4_1_CANDIDATES.csv")
    comb_u = _read_csv(res / "ALLSKY_COMB_V4_1_UNIFIED_D079_D098.csv")
    comb_ac = _read_csv(res / "ALLSKY_COMB_V4_1_CANDIDATES_D079_D098.csv")
    ell = _read_csv(res / "MULTIEVENT_ELLIPSOID_473STARS.csv")
    agn = _read_csv(res / "V5_6_AGNOSTIC_MULTISCALE_SURVIVORS.csv")
    utz = {r["star"] for r in ell if str(r["etz_qualified"]).lower() in ("1", "true")}
    e180 = sum(1 for r in ell if str(r["ellipsoid_qualified_180d"]).lower() in ("1", "true"))
    c11_ok = (
        sum(int(r["n_comb_configs"]) for r in comb_s) == 1214360
        and sum(int(r["v41_cands"]) for r in comb_s) == 100
        and len(comb_c) == 100
        and all(r["stage2_triage_status"] == "STAGE2_VETO_MDWARF_TIO_FOREST" for r in comb_c)
        and all(str(r["verified_eti"]).lower() == "false" for r in comb_c)
        and len(comb_u) == 458
        and len(comb_ac) == 212
        and len(ell) == 473
        and len(utz) == 19
        and e180 == 36
        and "HD166191" in utz
        and "IRC10216" in utz
        and len(agn) == 150
    )
    rec("C11", c11_ok, f"1,214,360 comb configs->100->0 (458 stacks); Ellipsoid=473 ({len(utz)} ETZ, {e180}<=180d); Agnostic=150")

    # C12: Radiometric Consistency Across All 159 Rows
    eirp = _read_csv(res / "EIRP_UPPER_LIMITS_D098.csv")
    mre = 0.0
    for r in eirp:
        d_cm = float(r["dist_pc"]) * PC_TO_CM
        flux = float(r["flux_lim_erg_cm2_s"])
        l_iso_mw = float(r["l_iso_mw"])
        l_calc = 4.0 * math.pi * (d_cm ** 2) * flux * 1e-7 / 1e6
        re1 = abs(l_calc - l_iso_mw) / max(abs(l_iso_mw), 1e-30)
        lam_cm = float(r["wave_bary_a"]) * 1e-8
        gain = (math.pi * 1000.0 / lam_cm) ** 2
        p_calc_kw = (l_calc * 1e3) / gain
        p_kw = float(r["p_beam_10m_kw"])
        re2 = abs(p_calc_kw - p_kw) / max(abs(p_kw), 1e-30)
        mre = max(mre, re1, re2)
    c12_ok = len(eirp) == 159 and mre < 0.002
    rec("C12", c12_ok, f"159/159 EIRP rows consistent, max_rel_err={mre:.10f} < 0.002")

    # C13: Results Manifest & Implementation Lock
    man = json.loads((ws / "RESULTS_MANIFEST_SHA256.json").read_text(encoding="utf-8"))
    ilock = json.loads((ws / "IMPLEMENTATION_LOCK.json").read_text(encoding="utf-8"))
    man_files = man.get("files", man)
    if "files" not in man:
        man_files = {k: v for k, v in man.items() if k not in ("schema", "phase_id", "generated_utc", "file_count")}
    man_diffs = [
        fn for fn, meta in man_files.items()
        if not (res / fn).is_file()
        or _sha256_file(res / fn) != (meta["sha256"] if isinstance(meta, dict) else meta)
    ]
    il_files = ilock.get("locked_files", ilock.get("files", {}))
    il_diffs = [
        fn for fn, meta in il_files.items()
        if not (ws / fn).is_file()
        or _sha256_file(ws / fn) != (meta["sha256"] if isinstance(meta, dict) else meta)
    ]
    c13_ok = len(man_files) == 40 and not man_diffs and len(il_files) >= 5 and not il_diffs
    rec("C13", c13_ok, f"manifest={len(man_files)} files (diffs={len(man_diffs)}), impl_lock={len(il_files)} files (diffs={len(il_diffs)})")

    # C14: 6/6 Visual Figures & Review Verification
    vr = json.loads((ws / "VISUAL_REVIEW.json").read_text(encoding="utf-8"))
    figs = vr.get("figures_reviewed", [])
    fig_ok = len(figs) == 6
    for ent in figs:
        fp = ws / ent["filename"]
        if not fp.is_file() or fp.stat().st_size != int(ent["bytes"]):
            fig_ok = False
        else:
            with fp.open("rb") as fh:
                if fh.read(8) != b"\x89PNG\r\n\x1a\n":
                    fig_ok = False
    c14_ok = vr.get("status") == "PASS (6/6)" and vr.get("overall_status") == "PASS (6/6)" and fig_ok
    rec("C14", c14_ok, f"VISUAL_REVIEW {vr.get('status')} with 6/6 verified PNG headers & exact bytes")

    # C15: Documentation & SOURCES Provenance
    rep = (ws / "RESULTS_REPORT.md").read_text(encoding="utf-8")
    srcs = json.loads((res / "SOURCES.json").read_text(encoding="utf-8"))
    c15_ok = (
        len(rep) > 2000
        and "D098" in rep
        and "40/40" in rep
        and srcs.get("total_input_files") == 99
        and len(srcs.get("exposures", [])) == 99
        and float(srcs.get("chronology", {}).get("chronology_lag_seconds", 0.0)) >= 3.0
    )
    rec("C15", c15_ok, f"RESULTS_REPORT.md ({len(rep)} chars) + SOURCES.json (99 exposures)")

    # C16: Pure-Stdlib Purity Gate on audit.py Itself
    tree = ast.parse(pathlib.Path(__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    non_stdlib = sorted(m for m in imported if m not in sys.stdlib_module_names)
    c16_ok = not non_stdlib
    rec("C16", c16_ok, f"Pure stdlib check imports={sorted(imported)}, non_stdlib={non_stdlib}")

    n_pass = sum(1 for _, ok, _ in results if ok)
    print(f"=== Phase D098 (V5.6) Pure-Stdlib Audit ({ws}) ===")
    for cid, ok, msg in results:
        print(f"  [{cid}] [{'PASS' if ok else 'FAIL'}] {msg}")
    print(f"SUMMARY: {n_pass}/{len(results)} CHECKS PASSED")
    return n_pass, len(results)


def main() -> None:
    ap = argparse.ArgumentParser(description="Phase D098 pure-stdlib C1-C16 audit")
    ap.add_argument("--workspace", type=pathlib.Path, default=WS_DEFAULT)
    ap.add_argument("--archives-dir", type=pathlib.Path, default=None)
    args = ap.parse_args()
    n_pass, n_tot = run_audit(args.workspace.resolve(), args.archives_dir)
    if n_pass != n_tot:
        sys.exit(1)


if __name__ == "__main__":
    main()
