#!/usr/bin/python3 -S
"""
Independent C1-C16 Pure-Stdlib Audit Suite for Phase D108 (V6.6):
IXPE 2-8 keV Spectro-Polarimetry + SRG/eROSITA-DE DR1 + RXTE HEXTE/PCA + ESO Orbits #193-#198.
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

DETECTOR_NAME = "TECHNOSIGNATURE_V6_6_IXPE_POLARIMETRY_EROSITA_DR1_RXTE_HEXTE_PCA_1000STAR_SYNTHESIS"
METHOD_LOCK_SHA256 = "e85f3f8cda7bbe55bd25c86399b46021cd054211168a9037afd8f1e1eb5c77a8"
BOUNDED_BUNDLE_BYTES = 12199223
BOUNDED_BUNDLE_SHA256 = "a3382b436bf7d12af1288a52add30fc1efd1b39ed5d30aed2f0eb8465be28a23"

STAGE1_LOCKED = {
    "v6_6_detector.py": "026f6bada3e7f92817d89024b3f7c2d784eb23f8f6b234a467b70ac2a1d5f451",
    "build_cohort.py": "372dd83b0f3e39fb2d8eb7e8c40600908e160ea9f43862f3f6214839ae7f78fe",
    "download_inputs.py": "762323eacdf031508a235cd1a44d24139b6a1df7025c7c2b04df536a5a683fe2",
    "FROZEN_COHORT_D108.csv": "fac0ea1e8d618e8f21de96ab0ef783900a4cdb9add5d851df9daa964d03aa6f3",
    "ORBITAL_CAMPAIGNS_AND_KINEMATICS.json": "b133828562eb6009c307892aefb660f9ed357d449f758214ed6619ccfcc6f80c",
    "PRIOR_EXCLUSION_VERIFICATION.json": "bce55cf2dd1b20d6477481e14dc51091acea42d807bd96007bf3a0d973325bc0",
    "PRIOR_V6_5_PHASES_SNAPSHOT.json": "a5d0a29861d905d413f6aa713bc1238c0100137f72e98373876467596cf7111a",
}

PRIOR_33_ARCHIVES = [
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
    ("AG", "SETI_D107_V6_5_ICECUBE_NEUTRINO_SWIFT_BAT_XRT_900STAR_RESULTS_2026-11-25.zip",             21105677, "125c4db22ff7d8fcdaabe50b929df44f9a6a3f5384738fe77c5ce4e28c201272"),
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
    "CALIBRATION_V66_EROSITA_DR1_240.csv": (236, 240),
    "CALIBRATION_V66_IXPE_POLARIMETRY_240.csv": (237, 240),
    "CALIBRATION_V66_RXTE_HEXTE_180.csv": (180, 180),
    "CALIBRATION_V66_RXTE_PCA_180.csv": (179, 180),
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
    assert summary["phase_id"] == "D108"
    assert summary["detector"] == DETECTOR_NAME
    assert coh["locked_targets_d108"] == 145
    assert coh["brand_new_analyzed_d108"] == 100
    assert coh["prior_bridges_d108"] == 45
    assert coh["science_stars_d108"] == 116
    assert coh["control_stars_d108"] == 29
    assert coh["brand_new_within_10pc_d108"] == 5
    assert coh["analyzed_valid_observations_d108"] == 198
    assert coh["failed_observations_d108"] == 0
    assert coh["valid_physical_files_d108"] == 385
    assert coh["raw_input_bytes"] == 1852606839
    assert coh["bounded_bundle_bytes"] == BOUNDED_BUNDLE_BYTES
    assert coh["bounded_bundle_bytes"] <= 15 * 1024 * 1024
    assert coh["bounded_bundle_sha256"] == BOUNDED_BUNDLE_SHA256
    assert abs(float(coh["integration_hours_d108"]) - 2165.3943) < 1e-3

    prov = _read_csv(ws / "results" / "EXPOSURE_PROVENANCE_D108.csv")
    man = _read_json(ws / "FULL_D108_INPUT_MANIFEST.json")
    src = _read_json(ws / "results" / "SOURCES.json")
    assert len(prov) == 198
    assert man["expected_observations"] == 198 and man["valid_observations"] == 198
    assert man["expected_physical_files"] == 385 and man["valid_physical_files"] == 385
    assert src["total_observations"] == 198 and src["analyzed_observations"] == 198 and src["total_physical_files"] == 385
    return "198 obs / 145 targets (100 brand-new, 45 prior bridges, 5 <10pc), 385 physical files, 2165.3943 h"


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
    assert imp["schema"] == "D108_IMPLEMENTATION_LOCK"
    assert imp["phase_id"] == "D108"
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
    assert lr["locked_utc"] == "2026-11-25T11:13:29.994080+00:00"
    assert lr["inputs_dir_exists_at_seal"] is False
    assert lr["method_lock_sha256"] == METHOD_LOCK_SHA256
    assert fdr["first_download_utc"] == "2026-11-25T11:14:01.641117+00:00"
    assert float(fdr["chronology_lag_seconds"]) >= 10.0
    assert src["chronology"]["locked_utc"] == lr["locked_utc"]
    assert src["chronology"]["first_download_utc"] == fdr["first_download_utc"]
    return f"Prospective lock lag = +{fdr['chronology_lag_seconds']} s (inputs_dir_exists_at_seal=false)"


def check_c4(ws: pathlib.Path, _arch: pathlib.Path) -> str:
    px = _read_json(ws / "PRIOR_EXCLUSION_VERIFICATION.json")
    assert px["n_prior_excluded_coords"] == 977
    assert px["n_prior_excluded_dp_ids"] == 3935
    assert px["n_format_check_excluded_dp_ids"] == 46
    assert px["d108_dp_id_overlap_count"] == 0
    assert float(px["min_brand_new_sky_separation_arcsec"]) >= 1800.0
    assert float(px["min_intra_d108_separation_arcsec"]) >= 1800.0
    prov = _read_csv(ws / "results" / "EXPOSURE_PROVENANCE_D108.csv")
    dp_ids = [r["dp_id"] for r in prov]
    assert len(dp_ids) == len(set(dp_ids)) == 198
    return (
        f"977 coords / 3935 dp_ids excluded, 0 overlaps, "
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
    assert tot_p == 6854 and tot_n == 6891
    summary = _read_json(ws / "results" / "SUMMARY.json")
    cal = summary["synthetic_calibration_6891_trials"]
    assert cal["n_suites"] == 32 and cal["total_trials"] == 6891 and cal["total_passed"] == 6854
    assert summary["unified_1004star_panchromatic_v6_6_synthesis"]["total_calibration_trials_d079_d108"] == 81123
    return "32 suites, 6854/6891 passed (all >= 97.5%), 81123 cumulative"


def check_c6(ws: pathlib.Path, _arch: pathlib.Path) -> str:
    ix = _read_csv(ws / "results" / "IXPE_POLARIMETRY_17TARGETS.csv")
    ero = _read_csv(ws / "results" / "EROSITA_DR1_111TARGETS.csv")
    hx = _read_csv(ws / "results" / "RXTE_HEXTE_16TARGETS.csv")
    pca = _read_csv(ws / "results" / "RXTE_PCA_16TARGETS.csv")
    he = _read_csv(ws / "results" / "V6_6_HIGH_ENERGY_CANDIDATE_LEDGER.csv")
    v66 = _read_csv(ws / "results" / "V6_6_CANDIDATE_LEDGER.csv")

    assert len(ix) == 17
    assert sum(1 for r in ix if r["role"] == "CONTROL") == 17
    assert sum(int(r["n_raw_i"]) for r in ix) == 46
    assert sum(int(r["n_raw_pol"]) for r in ix) == 0
    assert sum(int(r["n_qualified_pre_stage2"]) for r in ix) == 2
    assert sum(int(r["n_events_on"]) for r in ix) == 2186715
    assert all(int(r["verified_eti"]) == 0 for r in ix)

    assert len(ero) == 111
    assert sum(1 for r in ero if r["role"] == "SCIENCE") == 106
    assert sum(1 for r in ero if r["role"] == "CONTROL") == 5
    assert sum(int(r["n_raw"]) for r in ero) == 62
    assert sum(int(r["n_qualified_pre_stage2"]) for r in ero) == 0
    assert all(int(r["verified_eti"]) == 0 for r in ero)

    assert len(hx) == 16
    assert sum(1 for r in hx if r["role"] == "SCIENCE") == 6
    assert sum(int(r["n_raw"]) for r in hx) == 6
    assert sum(int(r["n_qualified_pre_stage2"]) for r in hx) == 3
    assert all(int(r["verified_eti"]) == 0 for r in hx)

    assert len(pca) == 16
    assert sum(1 for r in pca if r["role"] == "SCIENCE") == 6
    assert sum(int(r["n_raw"]) for r in pca) == 31
    assert sum(int(r["n_qualified_pre_stage2"]) for r in pca) == 2
    assert all(int(r["verified_eti"]) == 0 for r in pca)

    assert len(he) == 143
    assert sum(1 for r in he if r["instrument"] == "IXPE_GPD") == 46
    assert sum(1 for r in he if r["instrument"] == "EROSITA_DR1") == 61
    assert sum(1 for r in he if r["instrument"] == "RXTE_HEXTE") == 6
    assert sum(1 for r in he if r["instrument"] == "RXTE_PCA") == 30
    assert all(int(r["verified_eti"]) == 0 for r in he)

    assert len(v66) == 6
    assert all(int(r["verified_eti"]) == 0 for r in v66)
    return "IXPE 17 (46 I/0 QU->2->0), eROSITA 111 (62->0), HEXTE 16 (6->3->0), PCA 16 (31->2->0), 143 HE+6 Opt->0 ETI"


def check_c7(ws: pathlib.Path, _arch: pathlib.Path) -> str:
    sc = _read_json(ws / "results" / "SPECTRAL_COVERAGE_AUDIT_D108.json")
    assert sc["high_energy_unbroken_um"] == [4.1328066e-15, 0.06998]
    assert abs(float(sc["high_energy_unbroken_octaves"]) - 43.945) < 1e-6
    assert abs(float(sc["lyman_to_mm_strict_zero_gap_max_um"]) - 1417.76119) < 1e-5
    assert abs(float(sc["lyman_to_mm_strict_zero_gap_octaves"]) - 13.935) < 1e-6
    assert abs(float(sc["lyman_to_mm_b4_low_edge_um"]) - 2397.28632) < 1e-5
    assert abs(float(sc["lyman_to_mm_b4_low_octaves"]) - 14.693) < 1e-6
    assert abs(float(sc["global_max_wave_um"]) - 8556.41831) < 1e-5
    assert abs(float(sc["total_octave_span"]) - 60.845) < 1e-6
    assert sc["ixpe_polarimetry_energy_kev"] == [2.0, 8.0]
    assert sc["erosita_dr1_energy_kev"] == [0.2, 8.0]
    assert sc["rxte_pca_energy_kev"] == [2.0, 60.0]
    assert sc["rxte_hexte_energy_kev"] == [15.0, 250.0]
    return "60.845 EM octaves (43.945 unbroken HE, 13.935 zero-gap Lyman-mm) + IXPE 2-8 keV polarimetry"


def check_c8(ws: pathlib.Path, _arch: pathlib.Path) -> str:
    orb = _read_csv(ws / "results" / "ORBITAL_CAMPAIGN_RESULTS_6_D108.csv")
    fg = _read_csv(ws / "results" / "FOUR_GEN_BENCHMARK_D108.csv")
    s10 = _read_csv(ws / "results" / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_267STARS.csv")
    summary = _read_json(ws / "results" / "SUMMARY.json")
    assert [int(r["campaign_index"]) for r in orb] == [193, 194, 195, 196, 197, 198]
    assert all(int(r["verified_eti"]) == 0 for r in orb)
    assert sum(int(r["g1_seeds"]) for r in fg) == 207
    assert sum(int(r["g8_pass"]) for r in fg) == 6
    assert all(int(r["stage2_verified_eti"]) == 0 for r in fg)
    assert len(s10) == 267
    assert sum(1 for r in s10 if r["role"] == "SCIENCE") == 212
    assert sum(1 for r in s10 if r["role"] == "CONTROL") == 55
    assert sum(1 for r in s10 if int(r["n_exoplanets"]) > 0) == 61
    assert sum(int(r["n_exoplanets"]) for r in s10) == 121
    assert all(int(r["verified_eti_detections"]) == 0 for r in s10)
    u = summary["unified_1004star_panchromatic_v6_6_synthesis"]
    assert abs(float(u["within_10pc_median_limit_kw"]) - 0.380594) < 1e-6
    assert abs(float(u["within_10pc_optical_ir_median_limit_kw"]) - 0.6058) < 1e-4
    return "Orbits #193-#198 (0 ETI), 207 G1->6 G8->0 ETI, 267 <10pc stars (212 Sci/55 Ctrl, med=0.380594 kW)"


def check_c9(ws: pathlib.Path, _arch: pathlib.Path) -> str:
    dr = _read_csv(ws / "results" / "DRIFT_V66_ECCENTRIC_KEPLERIAN_90CAMPAIGNS.csv")
    cd = _read_csv(ws / "results" / "COMB_DRIFT_V66_90CAMPAIGNS.csv")
    dl = _read_csv(ws / "results" / "DRIFT_V66_CANDIDATE_LEDGER.csv")
    cl = _read_csv(ws / "results" / "COMB_DRIFT_V66_CANDIDATE_LEDGER.csv")

    assert len(dr) == 90 and len(cd) == 90
    assert sum(int(r["n_trajectories_evaluated"]) for r in dr) == 125549
    assert sum(int(r["n_pixel_trajectory_integrals"]) for r in dr) == 15627501311
    assert sum(int(r["raw_coherent_survivors"]) for r in dr) == 33424
    assert sum(int(r["eccentric_keplerian_survivors"]) for r in dr) == 3590
    assert sum(int(r["stage2_verified_eti"]) for r in dr) == 0

    assert sum(int(r["comb_trajectories_evaluated"]) for r in cd) == 19201
    assert sum(int(r["comb_raw_candidates"]) for r in cd) == 5803
    assert sum(int(r["comb_qualified_v66"]) for r in cd) == 222
    assert sum(int(r["v41_static_hits"]) for r in cd) == 65
    assert sum(int(r["stage2_verified_eti"]) for r in cd) == 0

    assert len(dl) == 929 and len(cl) == 631
    assert all(int(r["verified_eti"]) == 0 for r in dl)
    assert all(int(r["verified_eti"]) == 0 for r in cl)
    return "90 campaigns: DRIFT 125549 traj / 15.63B pix->0 ETI; COMB_DRIFT 19201 traj / 222 pre-S2->0 ETI"


def check_c10(ws: pathlib.Path, _arch: pathlib.Path) -> str:
    un = _read_csv(ws / "results" / "UNIFIED_PANCHROMATIC_V6_6_SYNTHESIS_1004STARS.csv")
    br = _read_csv(ws / "results" / "PANCHROMATIC_BRIDGE_155STARS_V66.csv")
    el = _read_csv(ws / "results" / "MULTIEVENT_ELLIPSOID_1004STARS.csv")
    cu = _read_csv(ws / "results" / "ALLSKY_COMB_V4_1_UNIFIED_D079_D108.csv")
    cc = _read_csv(ws / "results" / "ALLSKY_COMB_V4_1_CANDIDATES_D079_D108.csv")
    summary = _read_json(ws / "results" / "SUMMARY.json")
    u = summary["unified_1004star_panchromatic_v6_6_synthesis"]

    assert len(un) == 1004 and len(el) == 1004
    assert sum(1 for r in un if r["role"] == "SCIENCE") == 753
    assert sum(1 for r in un if r["role"] == "CONTROL") == 251
    assert sum(1 for r in un if int(r["n_exoplanets"]) > 0) == 298
    assert sum(int(r["n_exoplanets"]) for r in un) == 543
    assert all(int(r["verified_eti_detections"]) == 0 for r in un)

    assert len(br) == 2334
    assert sum(1 for r in br if r["instrument"] == "ICECUBE_10YR") == 126
    assert len(cu) == 578 and len(cc) == 33627
    assert all(int(r["verified_eti_combs"]) == 0 for r in cu)

    assert u["companion_archives_total"] == 34
    assert u["spectrographs"] == 66 and u["spectral_arms"] == 96
    assert u["panchromatic_bridge_stars_total"] == 155
    assert u["revisited_control_multi_phase_stars"] == 44
    assert u["multi_phase_targets_total"] == 199
    assert u["panchromatic_bridge_cells_total"] == 2334
    assert u["total_exposures_d079_d108"] == 3847
    assert abs(float(u["total_integration_hours_d079_d108"]) - 121471.6962) < 1e-3
    assert u["v2_false_alarms_eliminated_total"] == 1118698
    assert u["cumulative_orbital_campaigns"] == 198 and u["cumulative_comb_stacks"] == 578
    assert u["verified_eti_detections_total"] == 0
    return "1004 stars, 155 Sci bridges (199 multi-phase, 2334 cells), 66 inst/96 arms, 578 comb, 0 ETI"


def check_c11(_ws: pathlib.Path, arch: pathlib.Path) -> str:
    for lbl, fn, exp_b, exp_sha in PRIOR_33_ARCHIVES:
        p = arch / fn
        assert p.exists(), f"Missing prior archive {lbl}: {fn}"
        assert p.stat().st_size == exp_b, f"Size mismatch {lbl}: {p.stat().st_size} != {exp_b}"
        assert _sha256(p) == exp_sha, f"SHA mismatch {lbl}"
        with zipfile.ZipFile(p, "r") as zf:
            assert zf.testzip() is None, f"Corrupt zip entry in {fn}"
    return "33/33 prior Companion Archives A-Z, AA-AG verified intact"


def check_c12(ws: pathlib.Path, _arch: pathlib.Path) -> str:
    pc_cm = 3.0856775814913673e18
    eirp = _read_csv(ws / "results" / "EIRP_UPPER_LIMITS_D108.csv")
    assert len(eirp) == 657
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

    br = _read_csv(ws / "results" / "PANCHROMATIC_BRIDGE_155STARS_V66.csv")
    ic_br = [r for r in br if r["instrument"] == "ICECUBE_10YR"]
    assert len(ic_br) == 126
    assert all(
        r["p_beam_10m_kw"] == "" and r["p_beam_10m_w"] == "" and r["wave_A"] == "" and r["wave_um"] == ""
        for r in ic_br
    ), "IceCube neutrino bridge cell contains EM beam/wave fields"

    summary = _read_json(ws / "results" / "SUMMARY.json")
    assert float(summary["raw_hits_and_triage"]["c12_radiometric_max_rel_err"]) == 0.0
    return f"657 EM max_rel={max_em_rel:.2e}; 126 IC zero-EM-beam clean"


def check_c13(ws: pathlib.Path, _arch: pathlib.Path) -> str:
    man = _read_json(ws / "RESULTS_MANIFEST_SHA256.json")
    assert man["schema"] == "D108_RESULTS_MANIFEST_SHA256" and man["phase_id"] == "D108"
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
    assert vr["schema"] == "D108_VISUAL_REVIEW" and vr["phase_id"] == "D108"
    assert vr["n_figures"] == 6 and vr["all_passed"] is True
    figs = vr["figures"]
    assert len(figs) == 6
    for fg in figs:
        p = ws / fg["relpath"]
        assert p.exists() and p.stat().st_size == fg["bytes"]
        assert _sha256(p) == fg["sha256"]
        assert p.open("rb").read(8) == b"\x89PNG\r\n\x1a\n"
        assert fg["inspected"] is True and fg["status"] == "PASS"
    return "6/6 D108 figures (fig139-fig144, 240 DPI PNG) visually inspected & SHA-256 verified"


def check_c15(ws: pathlib.Path, _arch: pathlib.Path) -> str:
    txt = (ws / "RESULTS_REPORT.md").read_text(encoding="utf-8")
    for tok in [
        "D108", "V6.6", "1,004", "267", "155", "199", "2,334", "60.845", "43.945",
        "6,854 / 6,891", "2.086%", "145", "143", "126", "0"
    ]:
        assert tok in txt, f"RESULTS_REPORT.md missing token {tok!r}"
    return "RESULTS_REPORT.md verified with accurate D108/IXPE/eROSITA/RXTE/1004-star metrics"


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
    ("C5", "32-Suite / 6891-Trial Calibration", check_c5),
    ("C6", "IXPE + eROSITA + RXTE + Opt/NIR Triage", check_c6),
    ("C7", "Spectral Continuity & Polarimetry Span", check_c7),
    ("C8", "Orbits #193-#198 & <10 pc Synthesis", check_c8),
    ("C9", "90-Campaign DRIFT_V66 & COMB_DRIFT_V66", check_c9),
    ("C10", "Unified 1004-Star / 155-Bridge Synthesis", check_c10),
    ("C11", "33 Prior Companion Archives A-Z, AA-AG", check_c11),
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
