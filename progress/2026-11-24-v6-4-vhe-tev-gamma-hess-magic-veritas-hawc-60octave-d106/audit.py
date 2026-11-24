#!/usr/bin/python3 -S
"""
Phase D106 (V6.4) Pure-Stdlib End-to-End Audit Suite (C1-C16).
Runs under `/usr/bin/python3 -S` with zero third-party imports.
"""
from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import math
import pathlib
import sys
import zipfile
from typing import Any

PC_CM = 3.085677581491367e18

STAGE1_LOCKED = {
    "v6_4_detector.py": "fdf039be3c2d9df45ad6e98b66d0e9396651fe2315c1c5b3204e46f1cffa00f2",
    "build_cohort.py": "0495be1b6d702f9726b213df5e0c41d0a20a7d0c1b1ac9b0cdca76987e8df21f",
    "download_inputs.py": "002d43b9d6cc7e188b476eb24d95db49ace16ed156cc1984ba4c478f834557e4",
    "FROZEN_COHORT_D106.csv": "e4a981720fb1fa78874f61359e2b58ec004a7006e20f1fc8fa239b0dc0ee04c2",
    "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json": "579eacb1cc01f8bb60e9b33d388087833d258b7a4a0ca29805cc92d7d682accd",
    "PRIOR_EXCLUSION_VERIFICATION.json": "5eff44791a47cf1af3d0bb4434e1bc89fcfd7b095a27afbf7c995b359a7f2bcc",
    "PRIOR_V6_3_PHASES_SNAPSHOT.json": "c3a03e8bc51aa809418d117136760bf9f00f431ef7709ca80003083fac6fba20",
}

PRIOR_31_ARCHIVES = [
    ("A",  "SETI_D069_D074_FEROS_VELOCITY_CONTEXT_RESULTS_2026-11-13.zip",                 45920303, "b9bd142de7bdbf98b88d87dd5889cee3b1f1b43d93c17c4e711e6ed8a2e11820"),
    ("B",  "SETI_D075_D076_FEROS_ORDERS_AND_DIRECTION_RESULTS_2026-11-13.zip",              28329072, "2b7c5b48ee2f3b62ec7c3b6b65c150af4fed80b1930355d4d6b212b0d262fa31"),
    ("C",  "SETI_D077_FEROS_WLC_METADATA_GATE_RESULTS_2026-11-14.zip",                        659654, "828466e2c8ede7897be98d38d247fb18def0e5acdb40754656c8d2517c27c818"),
    ("D",  "SETI_D078_FEROS_RESTFRAME_AND_HD43629_SYNTHESIS_RESULTS_2026-11-14.zip",        11427944, "83132e0a43903a26ba6808b8bcca34f39850088d0aee05f0bdfb93b5d5ea6069"),
    ("E",  "SETI_D079_V3_CALIBRATED_OPTICAL_SEARCH_RESULTS_2026-11-14.zip",                  5770342, "ae7ec48fc51522c823c06940c60b661725430f632ba6f048402d9cf66ce07af3"),
    ("F",  "SETI_D080_V3_1_EXOPLANET_AND_HARPS_ESPRESSO_RESULTS_2026-11-14.zip",             7736372, "0c663b2b65e340deedf629cea069cee5092230a954ad56b6c39bf79684f00133"),
    ("G",  "SETI_D081_V3_2_TRANSIT_KINEMATICS_AND_10PC_RESULTS_2026-11-15.zip",              8045722, "12b951d77993cae116b8b7e8968866c13a374a23bd06ac1e96610ac63ee713a9"),
    ("H",  "SETI_D082_V3_3_NIRPS_NEAR_IR_AND_PANCHROMATIC_RESULTS_2026-11-15.zip",          29473205, "d5f73f0c93e6e6381441896e0457ea18d3baa05fadd7a8c569b60361f88a2457"),
    ("I",  "SETI_D083_V3_4_CRIRES_KBAND_AND_100STAR_RESULTS_2026-11-15.zip",                 5549428, "f60cf9d63b457c5246dcb14c5b4064376ef709118b5b325360d0d6c1686adf19"),
    ("J",  "SETI_D084_V3_5_NORTHERN_10PC_AND_125STAR_RESULTS_2026-11-16.zip",               10117107, "d13c6f409047d9b8a16c74f26098c44d4808d9f6a96a2e79dba34395f99d77cc"),
    ("K",  "SETI_D085_V3_6_SPIROU_YJHK_AND_COMB_V4_RESULTS_2026-11-17.zip",                 17448033, "2d27e24d9b943af3ff8d4796155ab0bbf97e87540b265f7cef5df56dba0685cb"),
    ("L",  "SETI_D086_V3_7_UVES_NUV_PANCHROM_AND_COMB_V4_1_RESULTS_2026-11-17.zip",         22587203, "b37d27ac6269e6671fb341b98514b27edad5b2dbbc392bec75eaeaa63073aea1"),
    ("M",  "SETI_D087_V3_8_SPACE_UV_STIS_FARRED_AND_200STAR_RESULTS_2026-11-18.zip",        19262628, "95b35e2a8b93b536c07b3c47c6c70f2ab1712455613059d66c7a00fe9591671c"),
    ("N",  "SETI_D088_V3_9_NORTHERN_RADIO23_AND_ALLSKY_COMB_V4_1_RESULTS_2026-11-18.zip",    9492762, "c0210250b925df3bebb1710c2bf7333a64ed767ebdc1f38a496d6a9454f7d45d"),
    ("O",  "SETI_D089_V4_0_SPACE_LYMAN_FUV_NUV_RESULTS_2026-11-19.zip",                      4262551, "4864dd3b5c0e958e428e1af815e1a378a37824d6bc87a89de9c223d89bccd723"),
    ("P",  "SETI_D090_V4_1_JWST_SPACE_THERMAL_IR_RESULTS_2026-11-19.zip",                    8610790, "2940839e8613b0d388c9b922743ba8244852806411f28586696e59eb8d73841a"),
    ("Q",  "SETI_D091_V4_2_ESO_TRIPLE_3ARM_RESULTS_2026-11-20.zip",                         22923782, "9da4739bdb413d675b9bc1f17dc9d60d5abc7944622714017cf1889a097b51d0"),
    ("R",  "SETI_D092_V5_0_RPCA_RARITY_ELLIPSOID_PPO_MIRI_CCF_RESULTS_2026-11-20.zip",      27934528, "845f0186a6a793ece2b62f9a2e7caaca5181a9b5a12f8db39326376a58a1d8dd"),
    ("S",  "SETI_D093_V5_1_DEDOPPLER_DRIFT_ELLIPSOID_GRACES_CORALIE_CARMENES_RESULTS_2026-11-21.zip", 25934814, "2588057cbd611686d50ced7f4432dce623b16609bc62de01d6460c91c504979a"),
    ("T",  "SETI_D094_V5_2_MULTIEPOCH_DRIFT_APOGEE2_CRIRESJH_MIRILRS_RESULTS_2026-11-21.zip", 16641712, "fea863077ae837b6741d5837990fd357158e00f6a5e3d9adde51f0c81e8ccefc"),
    ("U",  "SETI_D095_V5_3_CURVED_PERIODIC_DRIFT_GHOST_SPITZER_IRS_APOGEE2_RESULTS_2026-11-21.zip", 16898458, "24f5a73a4299d697a198e91e3e15b5b7ddce838f6d055cebe66ddd812520c21d"),
    ("V",  "SETI_D096_V5_4_SOFIA_EXES_MIDIR_ECHELLE_COHERENT_DRIFT_JWST_RESULTS_2026-11-21.zip", 15941580, "a134e4d5d0b6e0cb4e17763dc729203218cac9265c7db75db719135cb01c5158"),
    ("W",  "SETI_D097_V5_5_HERSCHEL_THZ_FARIR_STIS_E140H_OPTICAL_JERK_RESULTS_2026-11-22.zip", 11687103, "aa296f9c72faefcacbd4f4fedb73c7c3f2b1377823fad3e308fd6a9844f6fed8"),
    ("X",  "SETI_D098_V5_6_SOFIA_GREAT_ISO_SWS_FORCAST_OPTICAL_JERK_RESULTS_2026-11-22.zip", 22898406, "f57f48355df2b92257f39d76e83f2d850ae6d9164ea10ef1539bede1ca8fb838"),
    ("Y",  "SETI_D099_V5_7_JCMT_MM_SOFIA_EXES_IRTF_SPEX_KEPLERIAN_DRIFT_RESULTS_2026-11-22.zip", 15546915, "77b187f3509a704978096c14b97f83a13d3eebb6b2fc9d53a8c3b296b362df0b"),
    ("Z",  "SETI_D100_V5_8_JCMT_3MM_SOFIA_FIFILS_IUE_ECCENTRIC_KEPLERIAN_RESULTS_2026-11-22.zip", 13186766, "f8900c1aee6db352b6317c1dd6bf308d286bab2c0c0b367e8863383438446bd2"),
    ("AA", "SETI_D101_V5_9_ALMA_MM_BAND1_GAP_CLOSURE_DRIFTING_COMB_RESULTS_2026-11-23.zip", 18094897, "848a2ade7fdb46ed4e4f067e729ccf796a5181501f6e0ed18f573ff871fa8b20"),
    ("AB", "SETI_D102_V6_0_XRAY_EUV_POISSON_CHANDRA_EUVE_ALMA_UNBROKEN_MM_RESULTS_2026-11-23.zip", 22236761, "684d6828063cf17b8adcd666932633c07196e8764038dbbdd3a48bdd5433ca2c"),
    ("AC", "SETI_D103_V6_1_HARD_XRAY_NUSTAR_XMM_RGS_ALMA_B9B10_700STAR_RESULTS_2026-11-23.zip", 20006424, "d0155c0b3c98625c0e8f9cff5f55ccb89d7477e6ada6b3fd18a0ba8cc6615de4"),
    ("AD", "SETI_D104_V6_2_SOFT_GAMMA_SUZAKU_GSO_XRISM_NICER_200STAR_10PC_RESULTS_2026-11-24.zip", 18980731, "08169d98eb4313ea15610b8c4367f85a717cacdc10263ebd0a21e2a503cfad06"),
    ("AE", "SETI_D105_V6_3_MEV_GEV_GAMMA_OSSE_COMPTEL_FERMI_LAT_800STAR_RESULTS_2026-11-24.zip", 21288611, "74ee4b760a0b585ba6b6d7a2e0edbfe623258aa170a507fe577189247749778a"),
]


def _sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _read_csv(p: pathlib.Path) -> list[dict[str, str]]:
    with p.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _read_json(p: pathlib.Path) -> Any:
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent)
    ap.add_argument("--archives-dir", type=pathlib.Path, default=pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14/archives"))
    args = ap.parse_args()

    ws = args.workspace.resolve()
    res = ws / "results"
    ad = args.archives_dir.resolve()
    summary = _read_json(res / "SUMMARY.json")
    syn = summary["unified_852star_panchromatic_v6_4_synthesis"]
    checks: list[tuple[str, bool, str]] = []

    def rec(name: str, ok: bool, detail: str) -> None:
        checks.append((name, bool(ok), detail))

    # C1: Cohort invariant
    cohort = _read_csv(ws / "FROZEN_COHORT_D106.csv")
    c_meta = summary["cohort"]
    n_files_sum = len({r["f1_rel"] for r in cohort} | {x["rel"] for r in cohort for x in json.loads(r["extra_files"])})
    n_uniq = len({r["canonical_target"] for r in cohort})
    c1_ok = (
        len(cohort) == 99 and n_uniq == 70 and n_files_sum == 116
        and c_meta["analyzed_valid_observations_d106"] == 99
        and c_meta["valid_physical_files_d106"] == 116
        and c_meta["failed_observations_d106"] == 0
        and c_meta["stage2_quality_excluded_observations"] == 0
        and c_meta["brand_new_analyzed_d106"] == 46
        and c_meta["prior_bridges_d106"] == 24
        and c_meta["brand_new_within_10pc_d106"] == 14
    )
    rec("C1_D106_COHORT_INVARIANT", c1_ok, f"obs={len(cohort)}, uniq={n_uniq}, files={n_files_sum}")

    # C2: Stage-1 immutability & IMPLEMENTATION_LOCK
    ml = _read_json(ws / "METHOD_LOCK.json")
    lr = _read_json(ws / "LOCK_RECEIPT.json")
    s1_diffs = [fn for fn, h in STAGE1_LOCKED.items() if not (ws / fn).exists() or _sha256(ws / fn) != h]
    il_path = ws / "IMPLEMENTATION_LOCK.json"
    il_ok = False
    il_detail = "missing IMPLEMENTATION_LOCK.json"
    if il_path.exists():
        il = _read_json(il_path)
        bundle_p = ws / "bounded_inputs/d106_bounded_bundle.json.gz"
        b_ok = bundle_p.exists() and bundle_p.stat().st_size <= int(18.5 * 1024 * 1024) and _sha256(bundle_p) == il.get("bounded_bundle_sha256")
        s2_diffs = [fn for fn, sh in il.get("stage2_files", {}).items() if not (ws / fn).exists() or _sha256(ws / fn) != sh]
        il_ok = b_ok and not s2_diffs
        il_detail = f"bundle_ok={b_ok}, s2_diffs={s2_diffs}"
    c2_ok = (
        not s1_diffs
        and _sha256(ws / "METHOD_LOCK.json") == lr["method_lock_sha256"]
        and all(lr["locked_files"].get(k) == v for k, v in STAGE1_LOCKED.items())
        and all(ml["stage_1_files"].get(k) == v for k, v in STAGE1_LOCKED.items())
        and il_ok
    )
    rec("C2_STAGE1_AND_IMPLEMENTATION_LOCKS", c2_ok, f"s1_diffs={s1_diffs}; {il_detail}")

    # C3: Chronology lock before download
    fdr = _read_json(ws / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json")
    man_in = _read_json(ws / "FULL_D106_INPUT_MANIFEST.json")
    c3_ok = (
        lr.get("inputs_dir_exists_at_seal") is False
        and float(fdr["first_download_unix_epoch"]) > float(lr["locked_unix_epoch"])
        and float(fdr["chronology_lag_seconds"]) > 0.0
        and fdr["method_lock_sha256"] == lr["method_lock_sha256"]
        and man_in["valid_observations"] == 99
        and man_in["valid_physical_files"] == 116
        and man_in["failed_observations"] == 0
    )
    rec("C3_CHRONOLOGY_NO_DOWNLOAD_BEFORE_LOCK", c3_ok, f"lag=+{fdr.get('chronology_lag_seconds')}s, valid_files={man_in.get('valid_physical_files')}/116")

    # C4: Prior exclusion & separation
    pex = _read_json(ws / "PRIOR_EXCLUSION_VERIFICATION.json")
    c4_ok = (
        int(pex["n_prior_excluded_coords"]) == 879
        and int(pex["n_prior_excluded_dp_ids"]) == 3702
        and int(pex["n_format_check_excluded_dp_ids"]) == 46
        and int(pex["d106_dp_id_overlap_count"]) == 0
        and float(pex["min_brand_new_sky_separation_arcsec"]) >= 1000.0
        and float(pex["min_intra_d106_separation_arcsec"]) >= 1000.0
    )
    rec("C4_PRIOR_EXCLUSION_AND_SEPARATION", c4_ok, f"min_prior={pex['min_brand_new_sky_separation_arcsec']}'', min_intra={pex['min_intra_d106_separation_arcsec']}'', overlap={pex['d106_dp_id_overlap_count']}")

    # C5: 25 Calibration suites >= 95% (5,391 trials; 68,181 cumulative)
    cal = summary["synthetic_calibration_5391_trials"]
    suites = cal["suites"]
    bad_suites = []
    tot_tr = 0
    tot_ps = 0
    for sname, meta in suites.items():
        srows = _read_csv(res / f"{sname}.csv")
        ps = sum(int(r["passed"]) for r in srows)
        tr = len(srows)
        tot_tr += tr
        tot_ps += ps
        if tr != int(meta["total"]) or ps != int(meta["passed"]) or (ps / max(1, tr)) < 0.95:
            bad_suites.append((sname, ps, tr))
    c5_ok = (
        len(suites) == 25 and tot_tr == 5391 and not bad_suites
        and int(cal["total_trials"]) == 5391 and int(cal["total_passed"]) == tot_ps
        and int(syn["total_calibration_trials_d079_d106"]) == 68181
    )
    rec("C5_CALIBRATION_25_SUITES_GE_95PCT", c5_ok, f"{tot_ps}/{tot_tr} ({100.0*tot_ps/max(1,tot_tr):.2f}%), cum=68181, bad={bad_suites}")

    # C6: Four VHE TeV/PeV-edge observatories
    r_hess = _read_csv(res / "HESS_TEV_38TARGETS.csv")
    r_magic = _read_csv(res / "MAGIC_TEV_4TARGETS.csv")
    r_ver = _read_csv(res / "VERITAS_TEV_CRAB.csv")
    r_hawc = _read_csv(res / "HAWC_TEV_7TARGETS.csv")
    r_xcal = _read_csv(res / "VHE_TEV_CRAB_4OBS_CROSSCAL.csv")
    r_vhe_led = _read_csv(res / "V6_4_VHE_CANDIDATE_LEDGER.csv")
    c6_ok = (
        len(r_hess) == 38 and len(r_magic) == 4 and len(r_ver) == 1 and len(r_hawc) == 7
        and len(r_xcal) == 19 and len({r["observatory"] for r in r_xcal}) == 4
        and len(r_vhe_led) == 26
        and sum(int(r["verified_eti"]) for r in r_vhe_led) == 0
        and all(int(r["verified_eti"]) == 0 for r in r_hess + r_magic + r_ver + r_hawc)
    )
    rec("C6_VHE_FOUR_OBSERVATORY_INTEGRITY", c6_ok, f"hess={len(r_hess)}, magic={len(r_magic)}, veritas={len(r_ver)}, hawc={len(r_hawc)}, xcal={len(r_xcal)}, led={len(r_vhe_led)}->0 ETI")

    # C7: Spectral continuity
    sc_aud = _read_json(res / "SPECTRAL_COVERAGE_AUDIT_D106.json")
    c7_ok = (
        float(sc_aud["high_energy_unbroken_um"][0]) <= 4.1329e-15
        and abs(float(sc_aud["high_energy_unbroken_um"][1]) - 0.06998) < 1e-6
        and float(sc_aud["high_energy_unbroken_octaves"]) >= 43.94
        and float(sc_aud["lyman_to_mm_strict_zero_gap_octaves"]) >= 13.93
        and float(sc_aud["total_octave_span"]) >= 60.84
        and float(sc_aud["hawc_max_event_tev"]) >= 300.0
    )
    rec("C7_SPECTRAL_CONTINUITY_60P845_OCT", c7_ok, f"he={sc_aud['high_energy_unbroken_octaves']} oct, opt_mm={sc_aud['lyman_to_mm_strict_zero_gap_octaves']} oct, tot={sc_aud['total_octave_span']} oct")

    # C8: Optical/NIR Orbits #181-#186 & 244 <10 pc
    r_orb6 = _read_csv(res / "ORBITAL_CAMPAIGN_RESULTS_6_D106.csv")
    r_fg = _read_csv(res / "FOUR_GEN_BENCHMARK_D106.csv")
    r_244 = _read_csv(res / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_244STARS.csv")
    c8_ok = (
        len(r_orb6) == 6 and [int(r["campaign_index"]) for r in r_orb6] == [181, 182, 183, 184, 185, 186]
        and all(int(r["verified_eti"]) == 0 for r in r_orb6)
        and len(r_fg) == 6
        and len(r_244) == 244 and all(float(r["dist_pc"]) < 10.0 for r in r_244)
    )
    rec("C8_ORBITS_181_186_AND_244_LT10PC", c8_ok, f"orbits={len(r_orb6)}, fg={len(r_fg)}, <10pc={len(r_244)}")

    # C9: 78-Campaign DRIFT_V64 + COMB_DRIFT_V64
    r_dr78 = _read_csv(res / "DRIFT_V64_ECCENTRIC_KEPLERIAN_78CAMPAIGNS.csv")
    r_cd78 = _read_csv(res / "COMB_DRIFT_V64_78CAMPAIGNS.csv")
    traj_sum = sum(int(r["n_trajectories_evaluated"]) for r in r_dr78)
    pix_sum = sum(int(r["n_pixel_trajectory_integrals"]) for r in r_dr78)
    ctraj_sum = sum(int(r["comb_trajectories_evaluated"]) for r in r_cd78)
    c9_ok = (
        len(r_dr78) == 78 and len(r_cd78) == 78
        and traj_sum == 108044 and pix_sum == 12900273858 and ctraj_sum == 15705
        and sum(int(r["stage2_verified_eti"]) for r in r_dr78) == 0
        and sum(int(r["stage2_verified_eti"]) for r in r_cd78) == 0
    )
    rec("C9_DRIFT_V64_COMB_78_CAMPAIGNS", c9_ok, f"traj={traj_sum:,}, pix={pix_sum:,}, comb_traj={ctraj_sum:,} -> 0 ETI")

    # C10: Unified 852-Star & 119 SCIENCE Bridge Synthesis
    r_u852 = _read_csv(res / "UNIFIED_PANCHROMATIC_V6_4_SYNTHESIS_852STARS.csv")
    r_br119 = _read_csv(res / "PANCHROMATIC_BRIDGE_119STARS_V64.csv")
    r_ell = _read_csv(res / "MULTIEVENT_ELLIPSOID_852STARS.csv")
    r_comb = _read_csv(res / "ALLSKY_COMB_V4_1_UNIFIED_D079_D106.csv")
    n_sci = sum(1 for r in r_u852 if r["role"] == "SCIENCE")
    n_ctrl = sum(1 for r in r_u852 if r["role"] == "CONTROL")
    n_br_sci = sum(1 for r in r_u852 if len(str(r["phases"]).split("+")) >= 2 and r["role"] == "SCIENCE")
    n_mult_c = sum(1 for r in r_u852 if len(str(r["phases"]).split("+")) >= 2 and r["role"] == "CONTROL")
    c10_ok = (
        len(r_u852) == 852 and len(r_ell) == 852
        and n_sci == 618 and n_ctrl == 234
        and n_br_sci == 119 and n_mult_c == 27 and len(r_br119) == 1665
        and len(r_comb) == 564
        and int(summary["raw_hits_and_triage"]["verified_eti_detections_total"]) == 0
        and int(syn["verified_eti_detections_total"]) == 0
    )
    rec("C10_UNIFIED_852STAR_119BRIDGE", c10_ok, f"stars={len(r_u852)} (Sci={n_sci}/Ctrl={n_ctrl}), bridges={n_br_sci}, cells={len(r_br119)}, comb={len(r_comb)}")

    # C11: All 31 prior Companion Archives A-Z, AA-AE intact
    bad_arch = []
    for lbl, fname, exp_bytes, exp_sha in PRIOR_31_ARCHIVES:
        ap_f = ad / fname
        if not ap_f.exists() or ap_f.stat().st_size != exp_bytes or _sha256(ap_f) != exp_sha:
            bad_arch.append(lbl)
            continue
        with zipfile.ZipFile(ap_f) as zf:
            if zf.testzip() is not None:
                bad_arch.append(lbl)
    rec("C11_PRIOR_31_ARCHIVES_A_TO_AE", len(bad_arch) == 0, f"verified={31 - len(bad_arch)}/31, bad={bad_arch}")

    # C12: Pure-stdlib 4*pi*d^2 radiometric closure < 0.002
    r_eirp = _read_csv(res / "EIRP_UPPER_LIMITS_D106.csv")
    c12_n = 0
    c12_max_err = 0.0
    for fn_rows, w_col in ((r_eirp, "wave_bary_a"), (r_br119, "wave_A")):
        for row in fn_rows:
            fs = row.get("flux_lim_erg_cm2_s", "")
            ds = row.get("dist_pc", "")
            ws_a = row.get(w_col, "")
            ps = row.get("p_beam_10m_kw", "")
            if not (fs and ds and ws_a and ps):
                continue
            f_v, d_v, w_v, p_v = float(fs), float(ds), float(ws_a), float(ps)
            if not (f_v > 0.0 and d_v > 0.0 and w_v > 0.0 and p_v > 0.0):
                continue
            d_cm = d_v * PC_CM
            l_iso_w = 4.0 * math.pi * (d_cm * d_cm) * f_v * 1e-7
            theta = (math.pi * 10.0) / (w_v * 1e-10)
            p_exp_kw = (l_iso_w / (theta * theta)) / 1000.0
            rel_err = abs(p_exp_kw - p_v) / max(1e-35, p_v)
            c12_n += 1
            if rel_err > c12_max_err:
                c12_max_err = rel_err
    c12_ok = c12_n >= 2000 and c12_max_err < 0.002
    rec("C12_PURE_STDLIB_RADIOMETRIC_CLOSURE", c12_ok, f"rows={c12_n}, max_rel_err={c12_max_err:.10f} < 0.002")

    # C13: RESULTS_MANIFEST_SHA256 & zero ETI in ledgers
    man_p = ws / "RESULTS_MANIFEST_SHA256.json"
    c13_ok = False
    c13_detail = "missing RESULTS_MANIFEST_SHA256.json"
    if man_p.exists():
        man_r = _read_json(man_p)
        diffs_r = []
        for rel, meta in man_r.get("files", {}).items():
            fp = ws / rel
            if not fp.exists() or fp.stat().st_size != int(meta["bytes"]) or _sha256(fp) != meta["sha256"]:
                diffs_r.append(rel)
        led = _read_csv(res / "V6_4_CANDIDATE_LEDGER.csv")
        z_ok = all(int(r["verified_eti"]) == 0 for r in led)
        c13_ok = len(man_r.get("files", {})) >= 55 and len(diffs_r) == 0 and z_ok
        c13_detail = f"manifest_files={len(man_r.get('files', {}))}, diffs={len(diffs_r)}, zero_eti={z_ok}"
    rec("C13_RESULTS_MANIFEST_AND_ZERO_ETI", c13_ok, c13_detail)

    # C14: Visual review + 6 PNG figures
    vr_p = res / "VISUAL_REVIEW.json"
    c14_ok = False
    c14_detail = "missing VISUAL_REVIEW.json"
    if vr_p.exists():
        vr = _read_json(vr_p)
        figs = vr.get("figures", [])
        f_bad = []
        for fg in figs:
            fp = res / "figures" / fg["filename"]
            if not fp.exists() or fp.read_bytes()[:8] != b"\x89PNG\r\n\x1a\n" or _sha256(fp) != fg["sha256"]:
                f_bad.append(fg.get("filename"))
        c14_ok = int(vr.get("n_figures", 0)) == 6 and len(figs) == 6 and bool(vr.get("all_passed")) and not f_bad
        c14_detail = f"n_figures={len(figs)}, bad={f_bad}"
    rec("C14_VISUAL_REVIEW_AND_6_FIGURES", c14_ok, c14_detail)

    # C15: Reports present and cite exact verified totals
    rep_p = ws / "RESULTS_REPORT.md"
    c15_ok = False
    c15_detail = "missing RESULTS_REPORT.md"
    if rep_p.exists():
        txt = rep_p.read_text(encoding="utf-8")
        need = ["D106", "H.E.S.S.", "MAGIC", "VERITAS", "HAWC", "852", "244", "119", "43.945", "60.845", "78", "68,181", "verified_eti_detections_total = 0"]
        miss = [t for t in need if t not in txt]
        c15_ok = len(txt) >= 1500 and not miss
        c15_detail = f"bytes={len(txt)}, missing={miss}"
    rec("C15_REPORTS_PRESENT_AND_ACCURATE", c15_ok, c15_detail)

    # C16: Pure-stdlib AST import gate
    tree = ast.parse(pathlib.Path(__file__).read_text(encoding="utf-8"))
    allowed = set(sys.stdlib_module_names) | {"__future__"}
    non_std = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                top = a.name.split(".")[0]
                if top not in allowed:
                    non_std.add(top)
        elif isinstance(node, ast.ImportFrom) and node.module:
            top = node.module.split(".")[0]
            if top not in allowed:
                non_std.add(top)
    rec("C16_PURE_STDLIB_AST_IMPORT_GATE", len(non_std) == 0, f"non_stdlib={sorted(non_std)}")

    n_pass = sum(1 for _, ok, _ in checks if ok)
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    print(f"SUMMARY: {n_pass}/{len(checks)} PASSED")
    return 0 if n_pass == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
