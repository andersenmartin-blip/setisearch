#!/usr/bin/python3 -S
"""
Independent C1-C16 Pure-Stdlib Audit Suite for Phase D107 (V6.5):
IceCube 10-Yr Neutrinos + Swift-BAT 157m + Swift-XRT PC/WT + ESO Orbits #187-#192.
Runs cleanly under /usr/bin/python3 -S (zero third-party imports).
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

DETECTOR_NAME = "TECHNOSIGNATURE_V6_5_ICECUBE_NEUTRINO_SWIFT_BAT_XRT_900STAR_QUADMESSENGER_SYNTHESIS"
METHOD_LOCK_SHA256 = "bcd50d5040defa98c6f54630658537eb014ad5fe462f532e1141973522f20644"
BOUNDED_BUNDLE_BYTES = 14511917
BOUNDED_BUNDLE_SHA256 = "aad0b054982277375b6e1676e1edfdf3994f6e41a4f97964928a5e4aa6cc021a"

STAGE1_LOCKED = {
    "v6_5_detector.py": "4c6b1b43058d97ad103e722f74784428bad91c929e169ddd0328bcf0e35d573c",
    "build_cohort.py": "bf49823e9c5f18ee37abc061a83af1a01b7026ef4f36a67eedcb6c7c66fee33c",
    "download_inputs.py": "cdf2cf4bfd3a3577b624100707c1bdfd7938b365e3f1b700aeb1e73d7ffd713c",
    "FROZEN_COHORT_D107.csv": "c489cc0dd780b617177778783d749fa9556bcf20617f8f8d026cc3fa5b7906e2",
    "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json": "7138600515b54347b1c3860b03da0375bc5e7d074fb051ce56ce0759ae7e7fbf",
    "PRIOR_EXCLUSION_VERIFICATION.json": "cc3604766099a6aa20dabbc1d3bd19eea131abda917e1a0b8db8370778e1d5d0",
    "PRIOR_V6_4_PHASES_SNAPSHOT.json": "78dc4a2d426b662492248432efa292cb133f736b316f88ca50cc5949793fbe60",
}

PRIOR_32_ARCHIVES = [
    ("A",  "SETI_D069_D074_FEROS_VELOCITY_CONTEXT_RESULTS_2026-11-13.zip",                           45920303, "b9bd142de7bdbf98b88d87dd5889cee3b1f1b43d93c17c4e711e6ed8a2e11820"),
    ("B",  "SETI_D075_D076_FEROS_ORDERS_AND_DIRECTION_RESULTS_2026-11-13.zip",                        28329072, "2b7c5b48ee2f3b62ec7c3b6b65c150af4fed80b1930355d4d6b212b0d262fa31"),
    ("C",  "SETI_D077_FEROS_WLC_METADATA_GATE_RESULTS_2026-11-14.zip",                                  659654, "828466e2c8ede7897be98d38d247fb18def0e5acdb40754656c8d2517c27c818"),
    ("D",  "SETI_D078_FEROS_RESTFRAME_AND_HD43629_SYNTHESIS_RESULTS_2026-11-14.zip",                  11427944, "83132e0a43903a26ba6808b8bcca34f39850088d0aee05f0bdfb93b5d5ea6069"),
    ("E",  "SETI_D079_V3_CALIBRATED_OPTICAL_SEARCH_RESULTS_2026-11-14.zip",                            5770342, "ae7ec48fc51522c823c06940c60b661725430f632ba6f048402d9cf66ce07af3"),
    ("F",  "SETI_D080_V3_1_EXOPLANET_AND_HARPS_ESPRESSO_RESULTS_2026-11-14.zip",                       7736372, "0c663b2b65e340deedf629cea069cee5092230a954ad56b6c39bf79684f00133"),
    ("G",  "SETI_D081_V3_2_TRANSIT_KINEMATICS_AND_10PC_RESULTS_2026-11-15.zip",                        8045722, "12b951d77993cae116b8b7e8968866c13a374a23bd06ac1e96610ac63ee713a9"),
    ("H",  "SETI_D082_V3_3_NIRPS_NEAR_IR_AND_PANCHROMATIC_RESULTS_2026-11-15.zip",                    29473205, "d5f73f0c93e6e6381441896e0457ea18d3baa05fadd7a8c569b60361f88a2457"),
    ("I",  "SETI_D083_V3_4_CRIRES_KBAND_AND_100STAR_RESULTS_2026-11-15.zip",                           5549428, "f60cf9d63b457c5246dcb14c5b4064376ef709118b5b325360d0d6c1686adf19"),
    ("J",  "SETI_D084_V3_5_NORTHERN_10PC_AND_125STAR_RESULTS_2026-11-16.zip",                         10117107, "d13c6f409047d9b8a16c74f26098c44d4808d9f6a96a2e79dba34395f99d77cc"),
    ("K",  "SETI_D085_V3_6_SPIROU_YJHK_AND_COMB_V4_RESULTS_2026-11-17.zip",                           17448033, "2d27e24d9b943af3ff8d4796155ab0bbf97e87540b265f7cef5df56dba0685cb"),
    ("L",  "SETI_D086_V3_7_UVES_NUV_PANCHROM_AND_COMB_V4_1_RESULTS_2026-11-17.zip",                   22587203, "b37d27ac6269e6671fb341b98514b27edad5b2dbbc392bec75eaeaa63073aea1"),
    ("M",  "SETI_D087_V3_8_SPACE_UV_STIS_FARRED_AND_200STAR_RESULTS_2026-11-18.zip",                  19262628, "95b35e2a8b93b536c07b3c47c6c70f2ab1712455613059d66c7a00fe9591671c"),
    ("N",  "SETI_D088_V3_9_NORTHERN_RADIO23_AND_ALLSKY_COMB_V4_1_RESULTS_2026-11-18.zip",              9492762, "c0210250b925df3bebb1710c2bf7333a64ed767ebdc1f38a496d6a9454f7d45d"),
    ("O",  "SETI_D089_V4_0_SPACE_LYMAN_FUV_NUV_RESULTS_2026-11-19.zip",                                4262551, "4864dd3b5c0e958e428e1af815e1a378a37824d6bc87a89de9c223d89bccd723"),
    ("P",  "SETI_D090_V4_1_JWST_SPACE_THERMAL_IR_RESULTS_2026-11-19.zip",                              8610790, "2940839e8613b0d388c9b922743ba8244852806411f28586696e59eb8d73841a"),
    ("Q",  "SETI_D091_V4_2_ESO_TRIPLE_3ARM_RESULTS_2026-11-20.zip",                                   22923782, "9da4739bdb413d675b9bc1f17dc9d60d5abc7944622714017cf1889a097b51d0"),
    ("R",  "SETI_D092_V5_0_RPCA_RARITY_ELLIPSOID_PPO_MIRI_CCF_RESULTS_2026-11-20.zip",                27934528, "845f0186a6a793ece2b62f9a2e7caaca5181a9b5a12f8db39326376a58a1d8dd"),
    ("S",  "SETI_D093_V5_1_DEDOPPLER_DRIFT_ELLIPSOID_GRACES_CORALIE_CARMENES_RESULTS_2026-11-21.zip", 25934814, "2588057cbd611686d50ced7f4432dce623b16609bc62de01d6460c91c504979a"),
    ("T",  "SETI_D094_V5_2_MULTIEPOCH_DRIFT_APOGEE2_CRIRESJH_MIRILRS_RESULTS_2026-11-21.zip",         16641712, "fea863077ae837b6741d5837990fd357158e00f6a5e3d9adde51f0c81e8ccefc"),
    ("U",  "SETI_D095_V5_3_CURVED_PERIODIC_DRIFT_GHOST_SPITZER_IRS_APOGEE2_RESULTS_2026-11-21.zip",    16898458, "24f5a73a4299d697a198e91e3e15b5b7ddce838f6d055cebe66ddd812520c21d"),
    ("V",  "SETI_D096_V5_4_SOFIA_EXES_MIDIR_ECHELLE_COHERENT_DRIFT_JWST_RESULTS_2026-11-21.zip",      15941580, "a134e4d5d0b6e0cb4e17763dc729203218cac9265c7db75db719135cb01c5158"),
    ("W",  "SETI_D097_V5_5_HERSCHEL_THZ_FARIR_STIS_E140H_OPTICAL_JERK_RESULTS_2026-11-22.zip",        11687103, "aa296f9c72faefcacbd4f4fedb73c7c3f2b1377823fad3e308fd6a9844f6fed8"),
    ("X",  "SETI_D098_V5_6_SOFIA_GREAT_ISO_SWS_FORCAST_OPTICAL_JERK_RESULTS_2026-11-22.zip",          22898406, "f57f48355df2b92257f39d76e83f2d850ae6d9164ea10ef1539bede1ca8fb838"),
    ("Y",  "SETI_D099_V5_7_JCMT_MM_SOFIA_EXES_IRTF_SPEX_KEPLERIAN_DRIFT_RESULTS_2026-11-22.zip",       15546915, "77b187f3509a704978096c14b97f83a13d3eebb6b2fc9d53a8c3b296b362df0b"),
    ("Z",  "SETI_D100_V5_8_JCMT_3MM_SOFIA_FIFILS_IUE_ECCENTRIC_KEPLERIAN_RESULTS_2026-11-22.zip",      13186766, "f8900c1aee6db352b6317c1dd6bf308d286bab2c0c0b367e8863383438446bd2"),
    ("AA", "SETI_D101_V5_9_ALMA_MM_BAND1_GAP_CLOSURE_DRIFTING_COMB_RESULTS_2026-11-23.zip",            18094897, "848a2ade7fdb46ed4e4f067e729ccf796a5181501f6e0ed18f573ff871fa8b20"),
    ("AB", "SETI_D102_V6_0_XRAY_EUV_POISSON_CHANDRA_EUVE_ALMA_UNBROKEN_MM_RESULTS_2026-11-23.zip",     22236761, "684d6828063cf17b8adcd666932633c07196e8764038dbbdd3a48bdd5433ca2c"),
    ("AC", "SETI_D103_V6_1_HARD_XRAY_NUSTAR_XMM_RGS_ALMA_B9B10_700STAR_RESULTS_2026-11-23.zip",        20006424, "d0155c0b3c98625c0e8f9cff5f55ccb89d7477e6ada6b3fd18a0ba8cc6615de4"),
    ("AD", "SETI_D104_V6_2_SOFT_GAMMA_SUZAKU_GSO_XRISM_NICER_200STAR_10PC_RESULTS_2026-11-24.zip",     18980731, "08169d98eb4313ea15610b8c4367f85a717cacdc10263ebd0a21e2a503cfad06"),
    ("AE", "SETI_D105_V6_3_MEV_GEV_GAMMA_OSSE_COMPTEL_FERMI_LAT_800STAR_RESULTS_2026-11-24.zip",       21288611, "74ee4b760a0b585ba6b6d7a2e0edbfe623258aa170a507fe577189247749778a"),
    ("AF", "SETI_D106_V6_4_VHE_TEV_GAMMA_HESS_MAGIC_VERITAS_HAWC_60OCTAVE_RESULTS_2026-11-24.zip",     22232278, "5a5a04924333472d1775f5d6fd843e4712e1d39da824f2a8c6555741a09e0553"),
]

CAL_SUITES_EXPECTED = {
    "CALIBRATION_G8_V58_120.csv": (117, 120),
    "CALIBRATION_V58_AGNOSTIC_120.csv": (118, 120),
    "CALIBRATION_V58_ECCENTRIC_KEPLERIAN_360.csv": (359, 360),
    "CALIBRATION_V58_G6_COINCIDENCE_120.csv": (120, 120),
    "CALIBRATION_V58_RPCA_RARITY_180.csv": (180, 180),
    "CALIBRATION_V59_ALMA_INTERFEROMETRIC_240.csv": (239, 240),
    "CALIBRATION_V59_DRIFTING_COMB_240.csv": (236, 240),
    "CALIBRATION_V60_CHANDRA_POISSON_240.csv": (238, 240),
    "CALIBRATION_V60_EUVE_180.csv": (180, 180),
    "CALIBRATION_V61_NUSTAR_POISSON_240.csv": (240, 240),
    "CALIBRATION_V61_XMM_RGS_180.csv": (177, 180),
    "CALIBRATION_V62_NICER_XTI_180.csv": (180, 180),
    "CALIBRATION_V62_SUZAKU_GSO_240.csv": (235, 240),
    "CALIBRATION_V62_XRISM_RESOLVE_240.csv": (240, 240),
    "CALIBRATION_V63_CGRO_COMPTEL_240.csv": (239, 240),
    "CALIBRATION_V63_CGRO_OSSE_240.csv": (240, 240),
    "CALIBRATION_V63_FERMI_LAT_240.csv": (240, 240),
    "CALIBRATION_V64_HAWC_PEV_240.csv": (240, 240),
    "CALIBRATION_V64_HESS_TEV_240.csv": (240, 240),
    "CALIBRATION_V64_MAGIC_TEV_240.csv": (240, 240),
    "CALIBRATION_V64_VERITAS_TEV_180.csv": (180, 180),
    "CALIBRATION_V65_ICECUBE_NEUTRINO_240.csv": (237, 240),
    "CALIBRATION_V65_SWIFT_BAT_240.csv": (239, 240),
    "CALIBRATION_V65_SWIFT_XRT_180.csv": (178, 180),
    "COMB_V4_1_CALIBRATION_162.csv": (161, 162),
    "DETECTOR_V58_G4G5_CALIBRATION_108.csv": (108, 108),
    "INJECTION_RECOVERY_540.csv": (540, 540),
    "KEPLERIAN_TRACK_CALIBRATION_81.csv": (81, 81),
}

STDLIB_ALLOWED = {
    "__future__", "argparse", "ast", "csv", "hashlib", "json", "math", "pathlib", "sys", "zipfile"
}


def _sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _read_json(p: pathlib.Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _read_csv(p: pathlib.Path) -> list[dict[str, str]]:
    with p.open("r", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def check_c1(ws: pathlib.Path, _arch: pathlib.Path) -> str:
    summary = _read_json(ws / "results" / "SUMMARY.json")
    coh = summary["cohort"]
    assert summary["phase_id"] == "D107"
    assert summary["detector"] == DETECTOR_NAME
    assert coh["locked_targets_d107"] == 99
    assert coh["brand_new_analyzed_d107"] == 52
    assert coh["prior_bridges_d107"] == 47
    assert coh["science_stars_d107"] == 76
    assert coh["control_stars_d107"] == 23
    assert coh["brand_new_within_10pc_d107"] == 18
    assert coh["analyzed_valid_observations_d107"] == 134
    assert coh["failed_observations_d107"] == 0
    assert coh["valid_physical_files_d107"] == 59
    assert coh["raw_input_bytes"] == 999332310
    assert coh["bounded_bundle_bytes"] == BOUNDED_BUNDLE_BYTES
    assert coh["bounded_bundle_sha256"] == BOUNDED_BUNDLE_SHA256
    assert abs(float(coh["integration_hours_d107"]) - 92344.3857) < 1e-3

    prov = _read_csv(ws / "results" / "EXPOSURE_PROVENANCE_D107.csv")
    man = _read_json(ws / "FULL_D107_INPUT_MANIFEST.json")
    src = _read_json(ws / "results" / "SOURCES.json")
    assert len(prov) == 134
    assert man["expected_observations"] == 134 and man["valid_observations"] == 134
    assert src["total_observations"] == 134 and src["analyzed_observations"] == 134 and src["total_physical_files"] == 59
    return "134 obs / 99 targets (52 brand-new, 47 prior bridges, 18 <10pc), 59 physical files, 92344.3857 h"


def check_c2(ws: pathlib.Path, _arch: pathlib.Path) -> str:
    ml_path = ws / "METHOD_LOCK.json"
    assert _sha256(ml_path) == METHOD_LOCK_SHA256
    ml = _read_json(ml_path)
    assert ml["stage_1_files"] == STAGE1_LOCKED
    for rel, expected_sha in STAGE1_LOCKED.items():
        p = ws / rel
        assert p.exists(), f"Missing Stage-1 file {rel}"
        assert _sha256(p) == expected_sha, f"Stage-1 SHA mismatch for {rel}"

    imp = _read_json(ws / "IMPLEMENTATION_LOCK.json")
    assert imp["schema"] == "D107_IMPLEMENTATION_LOCK"
    assert imp["phase_id"] == "D107"
    assert imp["method_lock_sha256"] == METHOD_LOCK_SHA256
    assert imp["stage1_locked_files"] == STAGE1_LOCKED
    bundle = ws / imp["bounded_bundle_relpath"]
    assert bundle.exists() and bundle.stat().st_size == BOUNDED_BUNDLE_BYTES
    assert _sha256(bundle) == BOUNDED_BUNDLE_SHA256
    assert imp["bounded_bundle_bytes"] == BOUNDED_BUNDLE_BYTES
    assert imp["bounded_bundle_sha256"] == BOUNDED_BUNDLE_SHA256
    for rel, meta in imp["stage2_files"].items():
        p = ws / rel
        assert p.exists(), f"Missing Stage-2 file {rel}"
        assert p.stat().st_size == meta["bytes"], f"Bytes mismatch for {rel}"
        assert _sha256(p) == meta["sha256"], f"SHA mismatch for {rel}"
    return "Stage-1 (7 files) + METHOD_LOCK + bounded_bundle + IMPLEMENTATION_LOCK verified"


def check_c3(ws: pathlib.Path, _arch: pathlib.Path) -> str:
    lr = _read_json(ws / "LOCK_RECEIPT.json")
    fdr = _read_json(ws / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json")
    src = _read_json(ws / "results" / "SOURCES.json")
    assert lr["locked_utc"] == "2026-11-25T04:52:06.622933+00:00"
    assert lr["inputs_dir_exists_at_seal"] is False
    assert lr["method_lock_sha256"] == METHOD_LOCK_SHA256
    assert fdr["first_download_utc"] == "2026-11-25T04:52:27.897404+00:00"
    assert float(fdr["chronology_lag_seconds"]) > 20.0
    assert src["chronology"]["locked_utc"] == lr["locked_utc"]
    assert src["chronology"]["first_download_utc"] == fdr["first_download_utc"]
    return f"Prospective lock lag = +{fdr['chronology_lag_seconds']} s (inputs_dir_exists_at_seal=false)"


def check_c4(ws: pathlib.Path, _arch: pathlib.Path) -> str:
    px = _read_json(ws / "PRIOR_EXCLUSION_VERIFICATION.json")
    assert px["n_prior_excluded_coords"] == 925
    assert px["n_prior_excluded_dp_ids"] == 3801
    assert px["n_format_check_excluded_dp_ids"] == 46
    assert px["d107_dp_id_overlap_count"] == 0
    assert float(px["min_brand_new_sky_separation_arcsec"]) >= 1800.0
    assert float(px["min_intra_d107_separation_arcsec"]) >= 1800.0
    prov = _read_csv(ws / "results" / "EXPOSURE_PROVENANCE_D107.csv")
    dp_ids = [r["dp_id"] for r in prov]
    assert len(dp_ids) == len(set(dp_ids)) == 134
    return (
        f"925 coords / 3801 dp_ids excluded, 0 overlaps, "
        f"min_sep={px['min_brand_new_sky_separation_arcsec']:.2f} arcsec"
    )


def check_c5(ws: pathlib.Path, _arch: pathlib.Path) -> str:
    tot_p, tot_n = 0, 0
    for fn, (exp_p, exp_n) in CAL_SUITES_EXPECTED.items():
        rows = _read_csv(ws / "results" / fn)
        n = len(rows)
        p = sum(1 for r in rows if str(r["passed"]).strip().lower() in ("1", "true", "yes"))
        assert n == exp_n and p == exp_p, f"{fn}: {p}/{n} != {exp_p}/{exp_n}"
        assert p / n >= 0.975, f"{fn} below 97.5%"
        tot_p += p
        tot_n += n
    assert tot_p == 6022 and tot_n == 6051
    summary = _read_json(ws / "results" / "SUMMARY.json")
    cal = summary["synthetic_calibration_6051_trials"]
    assert cal["total_trials"] == 6051 and cal["total_passed"] == 6022
    assert summary["unified_904star_panchromatic_v6_5_synthesis"]["total_calibration_trials_d079_d107"] == 74232
    return "28 suites, 6022/6051 passed (all >= 97.5%), 74232 cumulative"


def check_c6(ws: pathlib.Path, _arch: pathlib.Path) -> str:
    ic = _read_csv(ws / "results" / "ICECUBE_10YR_54TARGETS.csv")
    bat = _read_csv(ws / "results" / "SWIFT_BAT_157M_30TARGETS.csv")
    xrt = _read_csv(ws / "results" / "SWIFT_XRT_20TARGETS.csv")
    mm = _read_csv(ws / "results" / "V6_5_MULTIMESSENGER_CANDIDATE_LEDGER.csv")
    qm = _read_csv(ws / "results" / "QUAD_MESSENGER_16CYGB_AND_CONTROLS_D107.csv")
    v65_l = _read_csv(ws / "results" / "V6_5_CANDIDATE_LEDGER.csv")

    assert len(ic) == 54
    assert sum(1 for r in ic if r["role"] == "SCIENCE") == 51
    assert sum(1 for r in ic if r["role"] == "CONTROL") == 3
    assert sum(1 for r in ic if r["within_10pc"] == "True") == 32
    assert sum(int(r["n_raw"]) for r in ic) == 21
    assert sum(int(r["n_qualified_pre_stage2"]) for r in ic) == 0
    assert all(int(r["verified_eti"]) == 0 for r in ic)

    assert len(bat) == 30
    assert sum(1 for r in bat if r["role"] == "SCIENCE") == 9
    assert sum(int(r["n_raw"]) for r in bat) == 38
    assert sum(int(r["n_qualified_pre_stage2"]) for r in bat) == 7
    assert all(int(r["verified_eti"]) == 0 for r in bat)

    assert len(xrt) == 20
    assert sum(1 for r in xrt if r["xrt_mode"] == "PC") == 15
    assert sum(1 for r in xrt if r["xrt_mode"] == "WT") == 5
    assert sum(int(r["n_raw"]) for r in xrt) == 63
    assert sum(int(r["n_qualified_pre_stage2"]) for r in xrt) == 0
    assert all(int(r["verified_eti"]) == 0 for r in xrt)

    assert len(mm) == 115
    assert sum(1 for r in mm if r["instrument"] == "ICECUBE_10YR") == 21
    assert sum(1 for r in mm if r["instrument"] == "SWIFT_BAT") == 38
    assert sum(1 for r in mm if r["instrument"] == "SWIFT_XRT") == 56
    assert all(int(r["verified_eti"]) == 0 for r in mm)

    assert len(qm) == 107 and any(r["star"] == "16CYGB" for r in qm)
    assert all(int(r["verified_eti"]) == 0 for r in qm)
    assert len(v65_l) == 0
    return "IC 54 (21 raw->0 ETI), BAT 30 (38->7->0), XRT 20 (63 pre-NMS/56 ledger->0), 115 MM ledger->0 ETI"


def check_c7(ws: pathlib.Path, _arch: pathlib.Path) -> str:
    sc = _read_json(ws / "results" / "SPECTRAL_COVERAGE_AUDIT_D107.json")
    assert sc["high_energy_unbroken_um"] == [4.1328066e-15, 0.06998]
    assert abs(float(sc["high_energy_unbroken_octaves"]) - 43.945) < 1e-6
    assert abs(float(sc["lyman_to_mm_strict_zero_gap_max_um"]) - 1417.76119) < 1e-5
    assert abs(float(sc["lyman_to_mm_strict_zero_gap_octaves"]) - 13.935) < 1e-6
    assert abs(float(sc["lyman_to_mm_b4_low_edge_um"]) - 2397.28632) < 1e-5
    assert abs(float(sc["lyman_to_mm_b4_low_octaves"]) - 14.693) < 1e-6
    assert abs(float(sc["global_max_wave_um"]) - 8556.41831) < 1e-5
    assert abs(float(sc["total_octave_span"]) - 60.845) < 1e-6
    assert sc["icecube_neutrino_energy_range_tev"] == [0.1, 10000.0]
    assert sc["swift_bat_energy_range_kev"] == [14.0, 195.0]
    assert sc["swift_xrt_energy_range_kev"] == [0.3, 10.0]
    return "60.845 EM octaves (43.945 unbroken HE, 13.935 zero-gap Lyman-mm) + 0.1 TeV-10 PeV neutrinos"


def check_c8(ws: pathlib.Path, _arch: pathlib.Path) -> str:
    orb = _read_csv(ws / "results" / "ORBITAL_CAMPAIGN_RESULTS_6_D107.csv")
    fg = _read_csv(ws / "results" / "FOUR_GEN_BENCHMARK_D107.csv")
    s10 = _read_csv(ws / "results" / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_262STARS.csv")
    summary = _read_json(ws / "results" / "SUMMARY.json")
    assert [int(r["campaign_index"]) for r in orb] == [187, 188, 189, 190, 191, 192]
    assert all(int(r["verified_eti"]) == 0 for r in orb)
    assert sum(int(r["g1_seeds"]) for r in fg) == 138
    assert sum(int(r["g8_pass"]) for r in fg) == 0
    assert len(s10) == 262
    assert sum(1 for r in s10 if r["role"] == "SCIENCE") == 208
    assert sum(1 for r in s10 if r["role"] == "CONTROL") == 54
    assert sum(1 for r in s10 if int(r["n_exoplanets"]) > 0) == 61
    assert sum(int(r["n_exoplanets"]) for r in s10) == 121
    assert all(int(r["verified_eti_detections"]) == 0 for r in s10)
    u = summary["unified_904star_panchromatic_v6_5_synthesis"]
    assert abs(float(u["within_10pc_median_limit_kw"]) - 0.491505) < 1e-6
    assert abs(float(u["within_10pc_optical_ir_median_limit_kw"]) - 0.6317) < 1e-4
    return "Orbits #187-#192 (0 ETI), 138 G1->0 G8, 262 <10pc stars (208 Sci/54 Ctrl, med=0.491505 kW)"


def check_c9(ws: pathlib.Path, _arch: pathlib.Path) -> str:
    dr = _read_csv(ws / "results" / "DRIFT_V65_ECCENTRIC_KEPLERIAN_84CAMPAIGNS.csv")
    cd = _read_csv(ws / "results" / "COMB_DRIFT_V65_84CAMPAIGNS.csv")
    dl = _read_csv(ws / "results" / "DRIFT_V65_CANDIDATE_LEDGER.csv")
    cl = _read_csv(ws / "results" / "COMB_DRIFT_V65_CANDIDATE_LEDGER.csv")

    assert len(dr) == 84 and len(cd) == 84
    assert sum(int(r["n_trajectories_evaluated"]) for r in dr) == 116865
    assert sum(int(r["n_pixel_trajectory_integrals"]) for r in dr) == 14267321081
    assert sum(int(r["raw_coherent_survivors"]) for r in dr) == 30605
    assert sum(int(r["eccentric_keplerian_survivors"]) for r in dr) == 3471
    assert sum(int(r["stage2_verified_eti"]) for r in dr) == 0

    assert sum(int(r["comb_trajectories_evaluated"]) for r in cd) == 17599
    assert sum(int(r["comb_raw_candidates"]) for r in cd) == 5554
    assert sum(int(r["comb_qualified_v65"]) for r in cd) == 216
    assert sum(int(r["v41_static_hits"]) for r in cd) == 63
    assert sum(int(r["stage2_verified_eti"]) for r in cd) == 0

    assert len(dl) == 858 and len(cl) == 613
    assert all(int(r["verified_eti"]) == 0 for r in dl)
    assert all(int(r["verified_eti"]) == 0 for r in cl)
    return "84 campaigns: DRIFT 116865 traj / 14.27B pix->0 ETI; COMB_DRIFT 17599 traj / 216 pre-S2->0 ETI"


def check_c10(ws: pathlib.Path, _arch: pathlib.Path) -> str:
    un = _read_csv(ws / "results" / "UNIFIED_PANCHROMATIC_V6_5_SYNTHESIS_904STARS.csv")
    br = _read_csv(ws / "results" / "PANCHROMATIC_BRIDGE_145STARS_V65.csv")
    el = _read_csv(ws / "results" / "MULTIEVENT_ELLIPSOID_904STARS.csv")
    cu = _read_csv(ws / "results" / "ALLSKY_COMB_V4_1_UNIFIED_D079_D107.csv")
    cc = _read_csv(ws / "results" / "ALLSKY_COMB_V4_1_CANDIDATES_D079_D107.csv")
    summary = _read_json(ws / "results" / "SUMMARY.json")
    u = summary["unified_904star_panchromatic_v6_5_synthesis"]

    assert len(un) == 904 and len(el) == 904
    assert sum(1 for r in un if r["role"] == "SCIENCE") == 659
    assert sum(1 for r in un if r["role"] == "CONTROL") == 245
    assert sum(1 for r in un if int(r["n_exoplanets"]) > 0) == 292
    assert sum(int(r["n_exoplanets"]) for r in un) == 532
    assert all(int(r["verified_eti_detections"]) == 0 for r in un)

    assert len(br) == 2067
    assert sum(1 for r in br if r["instrument"] == "ICECUBE_10YR") == 126
    assert len(cu) == 570 and len(cc) == 29673
    assert all(int(r["verified_eti_combs"]) == 0 for r in cu)

    assert u["companion_archives_total"] == 33
    assert u["spectrographs"] == 62 and u["spectral_arms"] == 92
    assert u["panchromatic_bridge_stars_total"] == 145
    assert u["revisited_control_multi_phase_stars"] == 32
    assert u["multi_phase_targets_total"] == 177
    assert u["panchromatic_bridge_cells_total"] == 2067
    assert u["total_exposures_d079_d107"] == 3649
    assert abs(float(u["total_integration_hours_d079_d107"]) - 119306.3019) < 1e-3
    assert u["v2_false_alarms_eliminated_total"] == 1092237
    assert u["cumulative_orbital_campaigns"] == 192 and u["cumulative_comb_stacks"] == 570
    assert u["verified_eti_detections_total"] == 0
    return "904 stars, 145 Sci bridges (177 multi-phase, 2067 cells), 62 inst/92 arms, 570 comb, 0 ETI"


def check_c11(_ws: pathlib.Path, arch: pathlib.Path) -> str:
    for lbl, fn, exp_b, exp_sha in PRIOR_32_ARCHIVES:
        p = arch / fn
        assert p.exists(), f"Missing prior archive {lbl}: {fn}"
        assert p.stat().st_size == exp_b, f"Size mismatch {lbl}: {p.stat().st_size} != {exp_b}"
        assert _sha256(p) == exp_sha, f"SHA mismatch {lbl}"
        with zipfile.ZipFile(p, "r") as zf:
            assert zf.testzip() is None, f"Corrupt zip entry in {fn}"
    return "32/32 prior Companion Archives A-Z, AA-AF verified intact"


def check_c12(ws: pathlib.Path, _arch: pathlib.Path) -> str:
    pc_cm = 3.0856775814913673e18
    eirp = _read_csv(ws / "results" / "EIRP_UPPER_LIMITS_D107.csv")
    assert len(eirp) == 368
    assert not any(r["instrument"] == "ICECUBE_10YR" for r in eirp), "ICECUBE_10YR leaked into EM EIRP table"

    max_em_rel = 0.0
    for r in eirp:
        fl = float(r["flux_lim_erg_cm2_s"])
        d_cm = float(r["dist_pc"]) * pc_cm
        w_m = float(r["wave_bary_a"]) * 1e-10
        l_exp = 4.0 * math.pi * (d_cm ** 2) * fl * 1e-13
        gain = (math.pi * 10.0 / w_m) ** 2
        p_exp_kw = (l_exp * 1e6 / gain) * 1e-3
        max_em_rel = max(
            max_em_rel,
            abs(float(r["l_iso_mw"]) - l_exp) / max(l_exp, 1e-300),
            abs(float(r["p_beam_10m_kw"]) - p_exp_kw) / max(p_exp_kw, 1e-300),
        )
    assert max_em_rel < 1e-5

    br = _read_csv(ws / "results" / "PANCHROMATIC_BRIDGE_145STARS_V65.csv")
    ic_br = [r for r in br if r["instrument"] == "ICECUBE_10YR"]
    assert len(ic_br) == 126
    assert all(
        r["p_beam_10m_kw"] == "" and r["p_beam_10m_w"] == "" and r["wave_A"] == "" and r["wave_um"] == ""
        for r in ic_br
    ), "IceCube neutrino bridge cell contains EM beam/wave fields"

    ic = _read_csv(ws / "results" / "ICECUBE_10YR_54TARGETS.csv")
    max_ic_rel = 0.0
    for r in ic:
        phi = float(r["phi_nu_lim_cm2_s"])
        e_tev = float(r["best_energy_tev"])
        ephi_exp = phi * e_tev
        flux_exp = ephi_exp * 1.602176634
        d_cm = float(r["dist_pc"]) * pc_cm
        l_w_exp = 4.0 * math.pi * (d_cm ** 2) * flux_exp * 1e-7
        max_ic_rel = max(
            max_ic_rel,
            abs(float(r["e_phi_nu_lim_tev_cm2_s"]) - ephi_exp) / ephi_exp,
            abs(float(r["flux_nu_lim_erg_cm2_s"]) - flux_exp) / flux_exp,
            abs(float(r["l_nu_iso_w"]) - l_w_exp) / l_w_exp,
        )
    assert max_ic_rel < 1e-4

    summary = _read_json(ws / "results" / "SUMMARY.json")
    assert float(summary["raw_hits_and_triage"]["c12_radiometric_max_rel_err"]) == 0.0
    return f"368 EM max_rel={max_em_rel:.2e}; 126 IC zero-EM-beam clean; 54 IC nu_closure max_rel={max_ic_rel:.2e}"


def check_c13(ws: pathlib.Path, _arch: pathlib.Path) -> str:
    man = _read_json(ws / "RESULTS_MANIFEST_SHA256.json")
    assert man["schema"] == "D107_RESULTS_MANIFEST_SHA256" and man["phase_id"] == "D107"
    files = man["files"]
    assert len(files) >= 65
    for rel, meta in files.items():
        p = ws / rel
        assert p.exists(), f"Manifest missing {rel}"
        assert p.stat().st_size == meta["bytes"], f"Manifest size mismatch {rel}"
        assert _sha256(p) == meta["sha256"], f"Manifest SHA mismatch {rel}"
    return f"RESULTS_MANIFEST_SHA256 verified ({len(files)} files)"


def check_c14(ws: pathlib.Path, _arch: pathlib.Path) -> str:
    vr = _read_json(ws / "results" / "VISUAL_REVIEW.json")
    assert vr["schema"] == "D107_VISUAL_REVIEW" and vr["phase_id"] == "D107"
    assert vr["n_figures"] == 6 and vr["all_passed"] is True
    figs = vr["figures"]
    assert len(figs) == 6
    for fg in figs:
        p = ws / fg["relpath"]
        assert p.exists() and p.stat().st_size == fg["bytes"]
        assert _sha256(p) == fg["sha256"]
        assert p.open("rb").read(8) == b"\x89PNG\r\n\x1a\n"
        assert fg["inspected"] is True and fg["status"] == "PASS"
    return "6/6 D107 figures (fig133-fig138, 240 DPI PNG) visually inspected & SHA-256 verified"


def check_c15(ws: pathlib.Path, _arch: pathlib.Path) -> str:
    txt = (ws / "RESULTS_REPORT.md").read_text(encoding="utf-8")
    for tok in [
        "D107", "V6.5", "904", "262", "145", "177", "2,067", "60.845", "43.945",
        "6,022 / 6,051", "63", "56", "115", "16CYGB", "1,392", "0"
    ]:
        assert tok in txt, f"RESULTS_REPORT.md missing token {tok!r}"
    return "RESULTS_REPORT.md verified with accurate D107/XRT-63-vs-56/Quad-Messenger metrics"


def check_c16(ws: pathlib.Path, _arch: pathlib.Path) -> str:
    tree = ast.parse((ws / "audit.py").read_text(encoding="utf-8"))
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                mods.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".")[0])
    disallowed = sorted(mods - STDLIB_ALLOWED)
    assert not disallowed, f"Disallowed non-stdlib imports: {disallowed}"
    return f"AST pure-stdlib check clean ({len(mods)} stdlib imports)"


CHECKS = [
    ("C1", "Cohort & Provenance Integrity", check_c1),
    ("C2", "Method Lock & Implementation Lock", check_c2),
    ("C3", "Prospective Chronology Lock", check_c3),
    ("C4", "Prior Coordinate & DP_ID Exclusion", check_c4),
    ("C5", "28-Suite / 6051-Trial Calibration", check_c5),
    ("C6", "IceCube + Swift BAT/XRT & Triage", check_c6),
    ("C7", "Spectral Continuity & Neutrino Span", check_c7),
    ("C8", "Orbits #187-#192 & <10 pc Synthesis", check_c8),
    ("C9", "84-Campaign DRIFT_V65 & COMB_DRIFT_V65", check_c9),
    ("C10", "Unified 904-Star / 145-Bridge Synthesis", check_c10),
    ("C11", "32 Prior Companion Archives A-Z, AA-AF", check_c11),
    ("C12", "EM + Strict Zero-Beam IceCube Closure", check_c12),
    ("C13", "RESULTS_MANIFEST_SHA256 Verification", check_c13),
    ("C14", "VISUAL_REVIEW & 6 PNG Figures", check_c14),
    ("C15", "RESULTS_REPORT.md Accuracy", check_c15),
    ("C16", "AST Pure-Stdlib Import Gate", check_c16),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", type=pathlib.Path, required=True)
    ap.add_argument("--archives-dir", type=pathlib.Path, required=True)
    args = ap.parse_args()

    ws = args.workspace.resolve()
    arch = args.archives_dir.resolve()
    passed = 0
    for code, title, fn in CHECKS:
        try:
            detail = fn(ws, arch)
            print(f"[PASS] {code:3s} {title:40s} :: {detail}")
            passed += 1
        except Exception as exc:
            print(f"[FAIL] {code:3s} {title:40s} :: {exc}")
    print(f"AUDIT_SUMMARY: {passed}/{len(CHECKS)} PASSED")
    return 0 if passed == len(CHECKS) else 1


if __name__ == "__main__":
    raise SystemExit(main())
