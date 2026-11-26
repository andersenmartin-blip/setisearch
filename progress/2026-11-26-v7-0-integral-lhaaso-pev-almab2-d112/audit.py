#!/usr/bin/python3 -S
"""
Phase D112 Pure-Stdlib Independent Audit (`C1–C16`, `#!/usr/bin/python3 -S`):
Verifies Stage-1 lock integrity, chronology, 0-overlap exclusion, bounded bundle <= 35.0 MiB,
all 37 prior companion archives (`A–Z, AA–AK`), all 43 calibration suites (`9,111` D112 -> `113,967` cum.),
62 INTEGRAL spectra (incl. 511 keV), 58 1LHAASO tracks up to 1.000 PeV, 3 ALMA Band 2 SV cubes
completing 10/10 ALMA bands, 62.582 EM octaves (45.682 unbroken HE octaves), 1,083 stars,
strict physical scale separation (33 IceCube-only / 126 empty bridge cells), pure-stdlib C12
radiometric closure, Bayesian f_tx, CWTFM, 6 inspected visuals, and SHA-256 locks.
"""
from __future__ import annotations

import argparse
import ast
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys
import zipfile

STDLIB_ALLOWED = {
    "__future__", "argparse", "ast", "csv", "gzip",
    "hashlib", "json", "math", "pathlib", "sys", "zipfile",
}

PC_CM = 3.0856775814913673e18
BUNDLE_CAP_BYTES = int(35.0 * 1024 * 1024)

HE_INSTRUMENTS_SET = {
    "INTEGRAL_IBIS_ISGRI", "INTEGRAL_JEMX", "INTEGRAL_SPI", "LHAASO_WCDA", "LHAASO_KM2A",
    "EROSITA_DR1", "IXPE_GPD", "RXTE_PCA", "RXTE_HEXTE",
    "SWIFT_BAT", "SWIFT_XRT", "HESS_TEV", "MAGIC_TEV", "VERITAS_TEV", "HAWC_TEV",
    "CGRO_OSSE", "CGRO_COMPTEL", "FERMI_LAT", "SUZAKU_HXD_GSO", "XRISM_RESOLVE",
    "NICER_XTI", "NUSTAR_FPMA_FPMB", "XMM_RGS", "CHANDRA_HETG", "CHANDRA_LETG", "EUVE_DS_S",
}
NEUTRINO_INSTRUMENTS_SET = {"ICECUBE_10YR"}

PRIOR_37_ARCHIVES = [
    ("A", "SETI_D069_D074_FEROS_VELOCITY_CONTEXT_RESULTS_2026-11-13.zip", 45920303, "b9bd142de7bdbf98b88d87dd5889cee3b1f1b43d93c17c4e711e6ed8a2e11820"),
    ("B", "SETI_D075_D076_FEROS_ORDERS_AND_DIRECTION_RESULTS_2026-11-13.zip", 28329072, "2b7c5b48ee2f3b62ec7c3b6b65c150af4fed80b1930355d4d6b212b0d262fa31"),
    ("C", "SETI_D077_FEROS_WLC_METADATA_GATE_RESULTS_2026-11-14.zip", 659654, "828466e2c8ede7897be98d38d247fb18def0e5acdb40754656c8d2517c27c818"),
    ("D", "SETI_D078_FEROS_RESTFRAME_AND_HD43629_SYNTHESIS_RESULTS_2026-11-14.zip", 11427944, "83132e0a43903a26ba6808b8bcca34f39850088d0aee05f0bdfb93b5d5ea6069"),
    ("E", "SETI_D079_V3_CALIBRATED_OPTICAL_SEARCH_RESULTS_2026-11-14.zip", 5770342, "ae7ec48fc51522c823c06940c60b661725430f632ba6f048402d9cf66ce07af3"),
    ("F", "SETI_D080_V3_1_EXOPLANET_AND_HARPS_ESPRESSO_RESULTS_2026-11-14.zip", 7736372, "0c663b2b65e340deedf629cea069cee5092230a954ad56b6c39bf79684f00133"),
    ("G", "SETI_D081_V3_2_TRANSIT_KINEMATICS_AND_10PC_RESULTS_2026-11-15.zip", 8045722, "12b951d77993cae116b8b7e8968866c13a374a23bd06ac1e96610ac63ee713a9"),
    ("H", "SETI_D082_V3_3_NIRPS_NEAR_IR_AND_PANCHROMATIC_RESULTS_2026-11-15.zip", 29473205, "d5f73f0c93e6e6381441896e0457ea18d3baa05fadd7a8c569b60361f88a2457"),
    ("I", "SETI_D083_V3_4_CRIRES_KBAND_AND_100STAR_RESULTS_2026-11-15.zip", 5549428, "f60cf9d63b457c5246dcb14c5b4064376ef709118b5b325360d0d6c1686adf19"),
    ("J", "SETI_D084_V3_5_NORTHERN_10PC_AND_125STAR_RESULTS_2026-11-16.zip", 10117107, "d13c6f409047d9b8a16c74f26098c44d4808d9f6a96a2e79dba34395f99d77cc"),
    ("K", "SETI_D085_V3_6_SPIROU_YJHK_AND_COMB_V4_RESULTS_2026-11-17.zip", 17448033, "2d27e24d9b943af3ff8d4796155ab0bbf97e87540b265f7cef5df56dba0685cb"),
    ("L", "SETI_D086_V3_7_UVES_NUV_PANCHROM_AND_COMB_V4_1_RESULTS_2026-11-17.zip", 22587203, "b37d27ac6269e6671fb341b98514b27edad5b2dbbc392bec75eaeaa63073aea1"),
    ("M", "SETI_D087_V3_8_SPACE_UV_STIS_FARRED_AND_200STAR_RESULTS_2026-11-18.zip", 19262628, "95b35e2a8b93b536c07b3c47c6c70f2ab1712455613059d66c7a00fe9591671c"),
    ("N", "SETI_D088_V3_9_NORTHERN_RADIO23_AND_ALLSKY_COMB_V4_1_RESULTS_2026-11-18.zip", 9492762, "c0210250b925df3bebb1710c2bf7333a64ed767ebdc1f38a496d6a9454f7d45d"),
    ("O", "SETI_D089_V4_0_SPACE_LYMAN_FUV_NUV_RESULTS_2026-11-19.zip", 4262551, "4864dd3b5c0e958e428e1af815e1a378a37824d6bc87a89de9c223d89bccd723"),
    ("P", "SETI_D090_V4_1_JWST_SPACE_THERMAL_IR_RESULTS_2026-11-19.zip", 8610790, "2940839e8613b0d388c9b922743ba8244852806411f28586696e59eb8d73841a"),
    ("Q", "SETI_D091_V4_2_ESO_TRIPLE_3ARM_RESULTS_2026-11-20.zip", 22923782, "9da4739bdb413d675b9bc1f17dc9d60d5abc7944622714017cf1889a097b51d0"),
    ("R", "SETI_D092_V5_0_RPCA_RARITY_ELLIPSOID_PPO_MIRI_CCF_RESULTS_2026-11-20.zip", 27934528, "845f0186a6a793ece2b62f9a2e7caaca5181a9b5a12f8db39326376a58a1d8dd"),
    ("S", "SETI_D093_V5_1_DEDOPPLER_DRIFT_ELLIPSOID_GRACES_CORALIE_CARMENES_RESULTS_2026-11-21.zip", 25934814, "2588057cbd611686d50ced7f4432dce623b16609bc62de01d6460c91c504979a"),
    ("T", "SETI_D094_V5_2_MULTIEPOCH_DRIFT_APOGEE2_CRIRESJH_MIRILRS_RESULTS_2026-11-21.zip", 16641712, "fea863077ae837b6741d5837990fd357158e00f6a5e3d9adde51f0c81e8ccefc"),
    ("U", "SETI_D095_V5_3_CURVED_PERIODIC_DRIFT_GHOST_SPITZER_IRS_APOGEE2_RESULTS_2026-11-21.zip", 16898458, "24f5a73a4299d697a198e91e3e15b5b7ddce838f6d055cebe66ddd812520c21d"),
    ("V", "SETI_D096_V5_4_SOFIA_EXES_MIDIR_ECHELLE_COHERENT_DRIFT_JWST_RESULTS_2026-11-21.zip", 15941580, "a134e4d5d0b6e0cb4e17763dc729203218cac9265c7db75db719135cb01c5158"),
    ("W", "SETI_D097_V5_5_HERSCHEL_THZ_FARIR_STIS_E140H_OPTICAL_JERK_RESULTS_2026-11-22.zip", 11687103, "aa296f9c72faefcacbd4f4fedb73c7c3f2b1377823fad3e308fd6a9844f6fed8"),
    ("X", "SETI_D098_V5_6_SOFIA_GREAT_ISO_SWS_FORCAST_OPTICAL_JERK_RESULTS_2026-11-22.zip", 22898406, "f57f48355df2b92257f39d76e83f2d850ae6d9164ea10ef1539bede1ca8fb838"),
    ("Y", "SETI_D099_V5_7_JCMT_MM_SOFIA_EXES_IRTF_SPEX_KEPLERIAN_DRIFT_RESULTS_2026-11-22.zip", 15546915, "77b187f3509a704978096c14b97f83a13d3eebb6b2fc9d53a8c3b296b362df0b"),
    ("Z", "SETI_D100_V5_8_JCMT_3MM_SOFIA_FIFILS_IUE_ECCENTRIC_KEPLERIAN_RESULTS_2026-11-22.zip", 13186766, "f8900c1aee6db352b6317c1dd6bf308d286bab2c0c0b367e8863383438446bd2"),
    ("AA", "SETI_D101_V5_9_ALMA_MM_BAND1_GAP_CLOSURE_DRIFTING_COMB_RESULTS_2026-11-23.zip", 18094897, "848a2ade7fdb46ed4e4f067e729ccf796a5181501f6e0ed18f573ff871fa8b20"),
    ("AB", "SETI_D102_V6_0_XRAY_EUV_POISSON_CHANDRA_EUVE_ALMA_UNBROKEN_MM_RESULTS_2026-11-23.zip", 22236761, "684d6828063cf17b8adcd666932633c07196e8764038dbbdd3a48bdd5433ca2c"),
    ("AC", "SETI_D103_V6_1_HARD_XRAY_NUSTAR_XMM_RGS_ALMA_B9B10_700STAR_RESULTS_2026-11-23.zip", 20006424, "d0155c0b3c98625c0e8f9cff5f55ccb89d7477e6ada6b3fd18a0ba8cc6615de4"),
    ("AD", "SETI_D104_V6_2_SOFT_GAMMA_SUZAKU_GSO_XRISM_NICER_200STAR_10PC_RESULTS_2026-11-24.zip", 18980731, "08169d98eb4313ea15610b8c4367f85a717cacdc10263ebd0a21e2a503cfad06"),
    ("AE", "SETI_D105_V6_3_MEV_GEV_GAMMA_OSSE_COMPTEL_FERMI_LAT_800STAR_RESULTS_2026-11-24.zip", 21288611, "74ee4b760a0b585ba6b6d7a2e0edbfe623258aa170a507fe577189247749778a"),
    ("AF", "SETI_D106_V6_4_VHE_TEV_GAMMA_HESS_MAGIC_VERITAS_HAWC_60OCTAVE_RESULTS_2026-11-24.zip", 22232278, "5a5a04924333472d1775f5d6fd843e4712e1d39da824f2a8c6555741a09e0553"),
    ("AG", "SETI_D107_V6_5_ICECUBE_NEUTRINO_SWIFT_BAT_XRT_900STAR_RESULTS_2026-11-25.zip", 21105677, "125c4db22ff7d8fcdaabe50b929df44f9a6a3f5384738fe77c5ce4e28c201272"),
    ("AH", "SETI_D108_V6_6_IXPE_POLARIMETRY_EROSITA_DR1_RXTE_1000STAR_RESULTS_2026-11-25.zip", 18673537, "b66922487b86763fce56def95b360aa8b1dae0c7e05e1a4553d77000a3d133bf"),
    ("AI", "SETI_D109_V6_7_10PC_DRIFT_CLOSURE_BAYESIAN_FTX_CWTFM_RESULTS_2026-11-25.zip", 37047683, "7f681525dc74be7c2f80a464b47f947960f8c0206e31fce2cdbe0a69ed76215c"),
    ("AJ", "SETI_D110_V6_8_OPTICAL_NIR_SPECTROPOLARIMETRY_RESULTS_2026-11-26.zip", 42385734, "11b2ba8cdb2a8b7aeaa97687fc75bf5d30ab82d7b92a880c5d29509f96e621dd"),
    ("AK", "SETI_D111_V6_9_LM_MIDIR_QCL_MOLECULAR_CCF_RESULTS_2026-11-26.zip", 17616117, "36cf7b892972845db68a623216778e7213f519bf21b59b652a8d1e3af3a79802"),
]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(1048576)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _c12_check(dist_pc: float, flux_cgs: float, wave_a: float) -> tuple[float, float]:
    d_cm = float(dist_pc) * PC_CM
    l_iso_w = 4.0 * math.pi * d_cm * d_cm * float(flux_cgs) * 1e-7
    lam_m = max(1e-22, float(wave_a) * 1e-10)
    theta = (math.pi * 10.0) / lam_m
    return l_iso_w / 1e6, (l_iso_w / (theta * theta)) / 1000.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", type=Path, default=Path(__file__).resolve().parent)
    ap.add_argument("--archives-dir", type=Path, default=None)
    args = ap.parse_args()

    ws = args.workspace.resolve()
    res_dir = ws / "results"
    archives_dir = args.archives_dir.resolve() if args.archives_dir else (ws.parent.parent / "archives")
    passed = 0
    results: list[tuple[str, bool, str]] = []

    def _rec(cid: str, ok: bool, msg: str) -> None:
        nonlocal passed
        if ok:
            passed += 1
        results.append((cid, ok, msg))
        print(f"[{'PASS' if ok else 'FAIL'}] {cid}: {msg}")

    # C1: Pure stdlib AST check
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    imps = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imps.update(n.name.split(".")[0] for n in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imps.add(node.module.split(".")[0])
    extra = imps - STDLIB_ALLOWED
    _rec("C1_STDLIB_ONLY", len(extra) == 0, f"imports={sorted(imps)}, extra={sorted(extra)}")

    # C2: Stage-1 lock & chronology lag
    lr = json.loads((ws / "LOCK_RECEIPT.json").read_text(encoding="utf-8"))
    ml = json.loads((ws / "METHOD_LOCK.json").read_text(encoding="utf-8"))
    fdr = json.loads((ws / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json").read_text(encoding="utf-8"))
    pe = json.loads((ws / "PRIOR_EXCLUSION_VERIFICATION.json").read_text(encoding="utf-8"))
    s1_ok = (
        lr.get("status") == "STAGE-1 SEALED"
        and lr.get("inputs_dir_exists_at_seal") is False
        and _sha256_file(ws / "METHOD_LOCK.json") == lr.get("method_lock_sha256")
        and all(_sha256_file(ws / fn) == sh for fn, sh in ml["stage_1_files"].items())
        and (float(fdr["first_download_unix_epoch"]) - float(lr["locked_unix_epoch"])) >= 10.0
        and int(pe["d112_dp_id_overlap_count"]) == 0
        and float(pe["brand_new_min_prior_sep_arcsec"]) >= 600.0
    )
    _rec("C2_STAGE1_LOCK_AND_LAG", s1_ok, f"lag={round(float(fdr['first_download_unix_epoch'])-float(lr['locked_unix_epoch']),3)}s, overlap={pe['d112_dp_id_overlap_count']}, sep={pe['brand_new_min_prior_sep_arcsec']}\"")

    # C3: Bounded bundle cap & content
    bp = ws / "bounded_inputs/d112_bounded_bundle.json.gz"
    bsz = bp.stat().st_size if bp.exists() else -1
    bobj = json.loads(gzip.decompress(bp.read_bytes()).decode("utf-8"))
    b_cubes = sum(len(o.get("alma_cubes", [])) for o in bobj.get("observations", []))
    _rec("C3_BOUNDED_BUNDLE_CAP", 0 < bsz <= BUNDLE_CAP_BYTES and len(bobj.get("observations", [])) == 122 and b_cubes == 3, f"bytes={bsz} ({bsz/1048576.0:.4f} MiB <= 35.0), obs=122, b2_cubes={b_cubes}")

    # C4: 37 prior companion archives A-AK SHA-256
    arch_ok = 0
    for code, fname, esz, esha in PRIOR_37_ARCHIVES:
        zp = archives_dir / fname
        if zp.exists() and zp.stat().st_size == esz and _sha256_file(zp) == esha:
            arch_ok += 1
    _rec("C4_PRIOR_37_ARCHIVES_SHA256", arch_ok == 37, f"{arch_ok}/37 prior companion archives verified")

    # C5: 43 calibration suites
    sumj = json.loads((res_dir / "SUMMARY.json").read_text(encoding="utf-8"))
    cals = sumj["synthetic_calibration_9111_trials"]
    all_ge = all((v["passed"] / v["total"]) >= 0.975 for v in cals["suites"].values())
    cum_cal = int(sumj["unified_panchromatic_v7_0_synthesis"]["total_calibration_trials_d079_d112"])
    _rec("C5_ALL_43_CALIBRATIONS", cals["n_suites"] == 43 and cals["total_trials"] == 9111 and all_ge and cum_cal == 113967, f"suites={cals['n_suites']}, passed={cals['total_passed']}/{cals['total_trials']}, cum={cum_cal}")

    # C6: INTEGRAL real survey
    int_s = _read_csv(res_dir / "INTEGRAL_SPECTRA_SUMMARY_D112.csv")
    int_5 = _read_csv(res_dir / "INTEGRAL_511KEV_UPPER_LIMITS_D112.csv")
    int_c = _read_csv(res_dir / "INTEGRAL_CANDIDATE_LEDGER_D112.csv")
    n_511 = sum(1 for r in int_5 if r["covers_511kev"] == "True")
    _rec("C6_INTEGRAL_511KEV_REAL_SURVEY", len(int_s) == 62 and len(int_5) == 62 and n_511 >= 40 and all(int(r["verified_eti"]) == 0 for r in int_c), f"spectra={len(int_s)}, 511keV_covered={n_511}, eti=0")

    # C7: LHAASO 1.000 PeV real survey
    lh_s = _read_csv(res_dir / "LHAASO_PEV_SUMMARY_D112.csv")
    max_e = max(float(r["max_energy_tev"]) for r in lh_s)
    min_w = min(float(r["min_wave_um"]) for r in lh_s)
    _rec("C7_LHAASO_1PEV_SURVEY", len(lh_s) == 58 and abs(max_e - 1000.0) < 1e-6 and min_w <= 1.24e-15 and all(int(r["verified_eti"]) == 0 for r in lh_s), f"tracks={len(lh_s)}, max_E={max_e} TeV, min_wave={min_w:.6e} um")

    # C8: ALMA Band 2 SV & 10/10 ALMA closure
    b2_s = _read_csv(res_dir / "ALMA_BAND2_SV_SUMMARY_D112.csv")
    sca = json.loads((res_dir / "SPECTRAL_COVERAGE_AUDIT_D112.json").read_text(encoding="utf-8"))
    bands10 = ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10"]
    _rec("C8_ALMA_B2_SV_AND_10_10_BANDS", len(b2_s) == 3 and sca["alma_bands_complete"] == bands10 and sca["alma_bands_count"] == "10/10", f"b2_cubes={len(b2_s)}, alma_bands={sca['alma_bands_count']} ({sca['alma_b2_sv_freq_ghz']} GHz)")

    # C9: Spectral continuity (62.582 octaves, 45.682 unbroken HE octaves)
    c9_ok = abs(float(sca["total_octave_span"]) - 62.582) < 0.005 and abs(float(sca["high_energy_unbroken_octaves"]) - 45.682) < 0.005 and abs(float(sca["lyman_to_mm_b4_low_octaves"]) - 14.693) < 0.005
    _rec("C9_CONTINUITY_62P582_OCTAVES", c9_ok, f"span={sca['total_octave_span']} oct, HE={sca['high_energy_unbroken_octaves']} oct, opt_mm={sca['lyman_to_mm_b4_low_octaves']} oct")

    # C10: Unified 1,083 stars & 72 spectrographs / 104 arms
    uni = _read_csv(res_dir / "UNIFIED_PANCHROMATIC_V7_0_SYNTHESIS_1083STARS.csv")
    usum = sumj["unified_panchromatic_v7_0_synthesis"]
    _rec("C10_UNIFIED_1083_STARS", len(uni) == 1083 and usum["spectrographs"] == 72 and usum["spectral_arms"] == 104 and usum["verified_eti_detections_total"] == 0, f"stars={len(uni)}, spectrographs={usum['spectrographs']}, arms={usum['spectral_arms']}, ETI=0")

    # C11: Physical scale separation & 33 IceCube zero-EM preserved
    sep = _read_csv(res_dir / "PHYSICAL_SCALE_SEPARATION_1083STARS_D112.csv")
    leaks = sum(1 for r in sep if r["best_beamed_instrument"] in HE_INSTRUMENTS_SET or r["best_beamed_instrument"] in NEUTRINO_INSTRUMENTS_SET)
    ic_only = sum(1 for r in sep if r["has_neutrino"] == "True" and r["has_beamed"] == "False" and r["has_he_em"] == "False")
    _rec("C11_SCALE_SEPARATION_EXACT", len(sep) == 1083 and leaks == 0 and ic_only == 33, f"rows={len(sep)}, leaks={leaks}, icecube_zero_em={ic_only}")

    # C12: 126 IceCube bridge cells strictly empty EM
    br = _read_csv(res_dir / usum["panchromatic_bridge_filename"])
    ic_br = [r for r in br if r["instrument"] == "ICECUBE_10YR"]
    ic_empty = sum(1 for r in ic_br if r["wave_A"] == "" and r["wave_um"] == "" and r["p_beam_10m_kw"] == "" and r["p_beam_10m_w"] == "")
    _rec("C12_ICECUBE_BRIDGE_CONSERVATION", len(ic_br) == 126 and ic_empty == 126, f"ic_bridge_rows={len(ic_br)}, strictly_empty_em={ic_empty}")

    # C13: Pure-stdlib C12 radiometric closure (< 5e-4) using exact cohort/provenance distances
    prov_dist = {r["dp_id"]: float(r["dist_pc"]) for r in _read_csv(res_dir / "EXPOSURE_PROVENANCE_D112.csv")}
    max_rel = 0.0
    for r in b2_s:
        d_pc = prov_dist[r["dp_id"]]
        li, pkw = _c12_check(d_pc, float(r["flux_lim_erg_cm2_s"]), float(r["wave_um"]) * 1e4)
        max_rel = max(max_rel, abs(li - float(r["l_iso_mw"])) / max(1e-30, float(r["l_iso_mw"])))
        max_rel = max(max_rel, abs(pkw - float(r["p_beam_10m_kw"])) / max(1e-30, float(r["p_beam_10m_kw"])))
    for r in int_s:
        d_pc = prov_dist[r["dp_id"]]
        li, _ = _c12_check(d_pc, float(r["flux_lim_erg_cm2_s"]), float(r["best_wave_um"]) * 1e4)
        max_rel = max(max_rel, abs(li - float(r["l_iso_mw"])) / max(1e-30, float(r["l_iso_mw"])))
    for r in lh_s:
        d_pc = prov_dist[r["dp_id"]]
        li, _ = _c12_check(d_pc, float(r["flux_lim_erg_cm2_s"]), float(r["best_wave_um"]) * 1e4)
        max_rel = max(max_rel, abs(li - float(r["l_iso_mw"])) / max(1e-30, float(r["l_iso_mw"])))
    _rec("C13_C12_RADIOMETRIC_CLOSURE", max_rel < 5e-4, f"max_rel_err={max_rel:.3e} < 5e-4 (ALMA B2 + INTEGRAL + LHAASO)")

    # C14: Bayesian f_tx & CWTFM
    ftx = _read_csv(res_dir / "BAYESIAN_FTX_OCCURRENCE_LIMITS_D112.csv")
    cw = _read_csv(res_dir / "CWTFM_COSMIC_HAYSTACK_BENCHMARK_D112.csv")
    all_sci = [float(r["f95_uniform_pct"]) for r in ftx if r["cohort"] == "ALL_SCIENCE_EM" and r["power_threshold"] == "ANY_CALIBRATED" and r["duty_cycle_eta"] == "1.0"]
    _rec("C14_BAYESIAN_FTX_AND_CWTFM", len(ftx) >= 60 and len(cw) >= 6 and len(all_sci) == 1 and 0.1 < all_sci[0] < 1.0, f"ftx_rows={len(ftx)}, cwtfm_rows={len(cw)}, f95_all_sci={all_sci[0]}%")

    # C15: 6 PNGs + VISUAL_REVIEW.json + RESULTS_REPORT.md
    vr = json.loads((res_dir / "VISUAL_REVIEW.json").read_text(encoding="utf-8"))
    pngs_ok = len(vr.get("figures", [])) == 6 and all((res_dir / f["filename"]).exists() and (res_dir / f["filename"]).stat().st_size > 100000 for f in vr["figures"])
    _rec("C15_VISUALS_AND_REPORT", vr.get("all_figures_inspected") is True and pngs_ok and (ws / "RESULTS_REPORT.md").exists(), f"pngs={len(vr.get('figures', []))}/6, inspected={vr.get('all_figures_inspected')}")

    # C16: IMPLEMENTATION_LOCK.json & RESULTS_MANIFEST_SHA256.json
    il = json.loads((ws / "IMPLEMENTATION_LOCK.json").read_text(encoding="utf-8"))
    rm = json.loads((ws / "RESULTS_MANIFEST_SHA256.json").read_text(encoding="utf-8"))
    s2_ok = all((ws / k).stat().st_size == v["bytes"] and _sha256_file(ws / k) == v["sha256"] for k, v in il["stage2_files"].items())
    rm_ok = all((ws / k).exists() and (ws / k).stat().st_size == v["bytes"] and _sha256_file(ws / k) == v["sha256"] for k, v in rm["files"].items())
    _rec("C16_IMPLEMENTATION_LOCK_AND_MANIFEST", s2_ok and rm_ok and rm["n_files"] == len(rm["files"]), f"stage2_lock={s2_ok}, manifest_files={len(rm['files'])} verified={rm_ok}")

    print(f"AUDIT_SUMMARY: {passed}/16 PASSED")
    return 0 if passed == 16 else 1


if __name__ == "__main__":
    raise SystemExit(main())
