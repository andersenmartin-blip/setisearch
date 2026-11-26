#!/usr/bin/python3 -S
"""
Phase D110 Pure-Stdlib Independent Audit (`C1–C16`, `#!/usr/bin/python3 -S`):
Verifies Stage-1 lock integrity, chronology, 0-overlap exclusion, bounded bundle <= 35.0 MiB,
all 35 prior companion archives (`A–Z, AA–AI`), all 37 calibration suites (`7,911` trials -> `96,345` cumulative),
87 valid optical/NIR polarimetric exposures, 16 paired (Q, U) MDP99 bounds, 16 Cyg B Penta-Regime,
Archive AH regression anchors, strict physical scale separation (0 HE/nu in beamed), exact C12
radiometric closure (< 1e-5), Bayesian f_tx monotonicity, CWTFM benchmark, visuals, and SHA-256 locks.
"""
from __future__ import annotations

import argparse
import ast
import base64
import csv
import gzip
import hashlib
import json
import lzma
import math
from pathlib import Path
import sys
import zipfile

STDLIB_ALLOWED = {
    "__future__", "argparse", "ast", "base64", "csv", "gzip",
    "hashlib", "json", "lzma", "math", "pathlib", "sys", "zipfile",
}

PC_CM = 3.0856775814913673e18
BUNDLE_CAP_BYTES = int(35.0 * 1024 * 1024)

HE_INSTRUMENTS_SET = {
    "EROSITA_DR1", "IXPE_GPD", "RXTE_PCA", "RXTE_HEXTE",
    "SWIFT_BAT", "SWIFT_XRT", "HESS_TEV", "MAGIC_TEV", "VERITAS_TEV", "HAWC_TEV",
    "CGRO_OSSE", "CGRO_COMPTEL", "FERMI_LAT", "SUZAKU_HXD_GSO", "XRISM_RESOLVE",
    "NICER_XTI", "NUSTAR_FPMA_FPMB", "XMM_RGS", "CHANDRA_HETG", "CHANDRA_LETG", "EUVE_DS_S",
}
NEUTRINO_INSTRUMENTS_SET = {"ICECUBE_10YR"}

PRIOR_35_ARCHIVES = [
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


def _read_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def run_audit(ws: Path, archives_dir: Path) -> tuple[int, int, list[tuple[str, bool, str]]]:
    res = ws / "results"
    checks: list[tuple[str, bool, str]] = []

    def _rec(cid: str, ok: bool, msg: str) -> None:
        checks.append((cid, ok, msg))

    # C1: Pure-stdlib AST check on self
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                mods.add(n.name.split(".", 1)[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            mods.add(node.module.split(".", 1)[0])
    bad_mods = mods - STDLIB_ALLOWED
    _rec("C1_STDLIB_ONLY", not bad_mods, f"imports={sorted(mods)}, disallowed={sorted(bad_mods)}")

    # C2: Stage-1 lock integrity
    lr = _read_json(ws / "LOCK_RECEIPT.json")
    ml = _read_json(ws / "METHOD_LOCK.json")
    s1_bad = []
    if lr.get("inputs_dir_exists_at_seal") is not False:
        s1_bad.append("inputs_dir_exists_at_seal!=False")
    if _sha256_file(ws / "METHOD_LOCK.json") != lr.get("method_lock_sha256"):
        s1_bad.append("method_lock_sha256 mismatch")
    for fn, exp_h in ml.get("stage_1_files", {}).items():
        act_h = _sha256_file(ws / fn)
        if act_h != exp_h:
            s1_bad.append(f"{fn}:{act_h[:10]}!={exp_h[:10]}")
    _rec("C2_STAGE1_LOCK_INTEGRITY", not s1_bad and len(ml.get("stage_1_files", {})) == 7, f"7 files locked={ml.get('locked_utc')}, bad={s1_bad}")

    # C3: Chronology & Exclusion
    fdr = _read_json(ws / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json")
    man = _read_json(ws / "FULL_D110_INPUT_MANIFEST.json")
    px = _read_json(ws / "PRIOR_EXCLUSION_VERIFICATION.json")
    lag = float(fdr.get("chronology_lag_seconds", -1.0))
    n_obs = int(man.get("expected_observations", -1))
    c3_ok = (
        lag >= 10.0
        and n_obs == 87
        and int(man.get("valid_physical_files", -1)) == n_obs
        and int(man.get("failed_observations", -1)) == 0
        and int(px.get("d110_dp_id_overlap_count", -1)) == 0
        and int(px.get("n_prior_excluded_coords", -1)) == 1077
        and int(px.get("n_prior_excluded_dp_ids", -1)) == 4349
        and float(px.get("brand_new_min_prior_sep_arcsec", 0.0)) >= 600.0
    )
    _rec("C3_CHRONOLOGY_AND_EXCLUSION", c3_ok, f"lag={lag}s, obs={n_obs}/87, dp_overlap={px.get('d110_dp_id_overlap_count')}, min_new_sep={px.get('brand_new_min_prior_sep_arcsec')}\"")

    # C4: Bounded bundle <= 35.0 MiB + sbf16l stdlib decode sanity
    summary = _read_json(res / "SUMMARY.json")
    impl = _read_json(ws / "IMPLEMENTATION_LOCK.json")
    bp = ws / "bounded_inputs/d110_bounded_bundle.json.gz"
    b_sz = bp.stat().st_size if bp.exists() else -1
    b_sha = _sha256_file(bp) if bp.exists() else ""
    bobj = json.loads(gzip.decompress(bp.read_bytes()).decode("utf-8")) if bp.exists() else {}
    blobs = bobj.get("star_blobs", {})
    exps_b = bobj.get("exposures", [])
    c4_bad = []
    if not (0 < b_sz <= BUNDLE_CAP_BYTES):
        c4_bad.append(f"size={b_sz}>{BUNDLE_CAP_BYTES}")
    if b_sha != summary.get("cohort", {}).get("bounded_bundle_sha256") or b_sha != impl.get("bounded_bundle_sha256"):
        c4_bad.append("sha256 mismatch")
    if len(exps_b) != 87 or len(blobs) != 49:
        c4_bad.append(f"exps={len(exps_b)}, blobs={len(blobs)}")
    for st_k, enc_s in list(blobs.items())[:3]:
        if not (str(enc_s).startswith("sbf16l:") or str(enc_s).startswith("spol16l:")):
            c4_bad.append(f"bad prefix {st_k}")
        lzma.decompress(base64.b85decode(enc_s.split(":", 1)[1].encode("ascii")))
    _rec("C4_BOUNDED_BUNDLE", not c4_bad, f"bytes={b_sz} ({b_sz/(1024*1024):.3f} MiB <= 35.0), codec={bobj.get('packing_codec')}, bad={c4_bad}")

    # C5: All 35 prior archives A-Z, AA-AI
    bad_arch = []
    for code, zname, exp_sz, exp_sha in PRIOR_35_ARCHIVES:
        zp = archives_dir / zname
        if not zp.exists():
            bad_arch.append(f"{code}:MISSING")
            continue
        if zp.stat().st_size != exp_sz or _sha256_file(zp) != exp_sha:
            bad_arch.append(f"{code}:HASH_OR_SIZE")
    _rec("C5_PRIOR_35_ARCHIVES", not bad_arch and len(PRIOR_35_ARCHIVES) == 35, f"35/35 present, bad={bad_arch}")

    # C6: 37 calibration suites >= 97.5%, 7,911 trials -> 96,345 cumulative
    cal_blk = summary.get("synthetic_calibration_7911_trials", {})
    suites = cal_blk.get("suites", {})
    bad_cal = []
    tot_t = tot_p = 0
    for snm, sinfo in suites.items():
        cf = res / f"{snm}.csv"
        if not cf.exists():
            bad_cal.append(f"missing {snm}.csv")
            continue
        crows = _read_csv(cf)
        np_c = sum(int(r["passed"]) for r in crows)
        nt_c = len(crows)
        tot_t += nt_c
        tot_p += np_c
        if nt_c != int(sinfo["total"]) or np_c != int(sinfo["passed"]) or (np_c / max(1, nt_c)) < 0.975:
            bad_cal.append(f"{snm}:{np_c}/{nt_c}")
    c6_ok = (len(suites) == 37 and tot_t == 7911 and tot_p == int(cal_blk.get("total_passed", -1)) and not bad_cal)
    _rec("C6_CALIBRATION_37_SUITES", c6_ok, f"suites={len(suites)}, {tot_p}/{tot_t} passed, cum={summary['unified_1012star_panchromatic_v6_8_synthesis']['total_calibration_trials_d079_d110']}, bad={bad_cal}")

    # C7: POL_V68 & POL_COMB_V68 + AH Regression Anchors + 16 Cyg B Penta-Regime
    sp_sum = _read_csv(res / "POLARIMETRIC_SPECTRA_SUMMARY_D110.csv")
    cand_l = _read_csv(res / "POLARIMETRIC_CANDIDATE_LEDGER_D110.csv")
    comb_r = _read_csv(res / "POL_COMB_V68_RESULTS_D110.csv")
    tri = summary.get("polarimetric_search_and_triage", {})
    anch = tri.get("anchor_regression_passed", [])
    n_eti_bad = (
        sum(int(r["verified_eti"]) for r in sp_sum)
        + sum(int(r["verified_eti"]) for r in cand_l)
        + sum(int(r["verified_eti"]) for r in comb_r)
    )
    c7_ok = (
        len(sp_sum) == 87 and len(comb_r) == 87
        and tri.get("cygb16_pentaregime_verified") is True
        and any("GJ317(" in s for s in anch) and any("7CMA(" in s for s in anch)
        and n_eti_bad == 0
    )
    _rec("C7_POLARIMETRY_AND_ANCHORS", c7_ok, f"spectra=87, anchors={anch}, 16CYGB_penta={tri.get('cygb16_pentaregime_verified')}, eti={n_eti_bad}")

    # C8: Paired (Q, U) Linear Polarization MDP99
    pqu = _read_csv(res / "PAIRED_QU_LINEAR_POLARIZATION_D110.csv")
    c8_ok = (
        len(pqu) == 16
        and all(0.0 < float(r["mdp99_lin_pct"]) < 10.0 and int(r["verified_eti"]) == 0 for r in pqu)
    )
    _rec("C8_PAIRED_QU_MDP99", c8_ok, f"pairs={len(pqu)}, med_mdp99={tri.get('paired_qu_median_mdp99_pct')}%")

    # C9: Unified 1,012 stars (1,004 prior + 8 brand-new) & 33 IceCube-only preserved
    u1012 = _read_csv(res / "UNIFIED_PANCHROMATIC_V6_8_SYNTHESIS_1012STARS.csv")
    ic_only = [r for r in u1012 if not str(r["min_panchromatic_10m_kw"]).strip()]
    em_pop = [r for r in u1012 if str(r["min_panchromatic_10m_kw"]).strip()]
    c9_ok = (
        len(u1012) == 1012 and len(em_pop) == 979 and len(ic_only) == 33
        and all(int(float(r["n_exposures_icecube_10yr"] or 0)) > 0 for r in ic_only)
    )
    _rec("C9_UNIFIED_1012_COVERAGE", c9_ok, f"stars={len(u1012)}, em_pop={len(em_pop)}, ic_only={len(ic_only)}")

    # C10: Strict physical scale separation & 126 IceCube zero-EM bridges
    sep = _read_csv(res / "PHYSICAL_SCALE_SEPARATION_1012STARS_D110.csv")
    eirp = _read_csv(res / "POLARIZED_EIRP_UPPER_LIMITS_D110.csv")
    br_fname = summary["unified_1012star_panchromatic_v6_8_synthesis"]["panchromatic_bridge_filename"]
    br = _read_csv(res / br_fname)
    bad_b_inst = [r["best_beamed_instrument"] for r in u1012 if r["best_beamed_instrument"] in HE_INSTRUMENTS_SET or r["best_beamed_instrument"] in NEUTRINO_INSTRUMENTS_SET]
    bad_sep_inst = [r["best_beamed_instrument"] for r in sep if r["best_beamed_instrument"] in HE_INSTRUMENTS_SET or r["best_beamed_instrument"] in NEUTRINO_INSTRUMENTS_SET]
    ic_br = [r for r in br if r["instrument"] == "ICECUBE_10YR"]
    bad_ic_br = [r for r in ic_br if r["p_beam_10m_kw"].strip() or r["p_beam_10m_w"].strip() or r["wave_A"].strip() or r["wave_um"].strip()]
    c10_ok = len(sep) == 1012 and not bad_b_inst and not bad_sep_inst and len(ic_br) == 126 and not bad_ic_br
    _rec("C10_PHYSICAL_SCALE_SEPARATION", c10_ok, f"sep=1012, bad_b={bad_b_inst}, ic_br={len(ic_br)} (bad={len(bad_ic_br)})")

    # C11: Pure-Python C12 verification (< 1e-5) across POLARIZED_EIRP_UPPER_LIMITS_D110
    max_rel = 0.0
    for r in eirp:
        d_cm = float(r["dist_pc"]) * PC_CM
        li_w = 4.0 * math.pi * d_cm * d_cm * float(r["flux_lim_erg_cm2_s"]) * 1e-7
        th = (math.pi * 10.0) / (float(r["wave_bary_a"]) * 1e-10)
        pkw = (li_w / (th * th)) / 1000.0
        max_rel = max(max_rel, abs(pkw - float(r["p_beam_10m_kw"])) / max(1e-18, pkw))
    _rec("C11_C12_RADIOMETRIC_CLOSENESS", len(eirp) >= 400 and max_rel < 1e-5, f"checked {len(eirp)} rows, max_rel={max_rel:.3e}")

    # C12: Bayesian f_tx monotonicity & cohort completeness
    ftx = _read_csv(res / "BAYESIAN_FTX_OCCURRENCE_LIMITS_D110.csv")
    req_cohs = {"ALL_SCIENCE_EM", "SOLAR_10PC_SCIENCE", "EXOPLANET_HOSTS_300", "SOLAR_10PC_HOSTS_61", "OPT_NIR_POLARIMETRY_V68"}
    obs_cohs = {r["cohort"] for r in ftx}
    bad_ftx = []
    for r in ftx:
        fj, fu, neff = float(r["f95_jeffreys_pct"]), float(r["f95_uniform_pct"]), float(r["n_eff"])
        if not (0.0 < fj <= 100.0 and 0.0 < fu <= 100.0 and int(r["verified_eti"]) == 0):
            bad_ftx.append((r["cohort"], fj, fu))
        elif neff >= 4.0 and fj > fu + 1e-4:
            bad_ftx.append((r["cohort"], "n_eff>=4_fj>fu", neff))
    by_cp: dict[tuple[str, str], list[dict[str, str]]] = {}
    for r in ftx:
        by_cp.setdefault((r["cohort"], r["power_threshold"]), []).append(r)
    for k_cp, grp in by_cp.items():
        grp_s = sorted(grp, key=lambda x: float(x["duty_cycle_eta"]))
        for i in range(1, len(grp_s)):
            if float(grp_s[i]["f95_uniform_pct"]) > float(grp_s[i - 1]["f95_uniform_pct"]) + 1e-3:
                bad_ftx.append((k_cp, "non_monotonic_eta"))
    _rec("C12_BAYESIAN_FTX_COHERENCE", req_cohs <= obs_cohs and not bad_ftx, f"rows={len(ftx)}, cohorts={len(obs_cohs)}, bad={bad_ftx[:5]}")

    # C13: CWTFM benchmark completeness
    cwtfm = _read_csv(res / "CWTFM_COSMIC_HAYSTACK_BENCHMARK_D110.csv")
    c_ours = [r for r in cwtfm if r["is_this_work"] == "True"]
    c_lits = [r for r in cwtfm if r["is_this_work"] == "False"]
    c13_ok = len(c_ours) == 5 and len(c_lits) == 4 and all(float(r["cwtfm_eirp_score"]) > 0 for r in cwtfm)
    _rec("C13_CWTFM_HAYSTACK_BENCHMARK", c13_ok, f"ours={len(c_ours)}, lit={len(c_lits)}")

    # C14: Unified survey totals (67 spectrographs, 97 arms, 4,150 exposures)
    uni = summary.get("unified_1012star_panchromatic_v6_8_synthesis", {})
    sub10 = _read_csv(res / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_267STARS.csv")
    br_sci_u = {r["star"] for r in u1012 if r["role"] == "SCIENCE" and len(str(r["phases"]).split("+")) >= 2}
    c14_ok = (
        uni.get("phases") == "D079-D110"
        and int(uni.get("companion_archives_total", -1)) == 36
        and int(uni.get("spectrographs", -1)) == 67
        and int(uni.get("spectral_arms", -1)) == 97
        and int(uni.get("unique_stars_total", -1)) == 1012
        and len(sub10) == 267 and int(uni.get("within_10pc_unique_stars", -1)) == 267
        and int(uni.get("panchromatic_bridge_stars_total", -1)) == len(br_sci_u)
        and int(uni.get("panchromatic_bridge_cells_total", -1)) == len(br)
        and int(uni.get("total_exposures_d079_d110", -1)) == 4150
        and int(uni.get("verified_eti_detections_total", -1)) == 0
    )
    _rec("C14_UNIFIED_SURVEY_TOTALS", c14_ok, f"stars={uni.get('unique_stars_total')}, specs={uni.get('spectrographs')}, arms={uni.get('spectral_arms')}, exp={uni.get('total_exposures_d079_d110')}, bridges={len(br_sci_u)}, cells={len(br)}, eti={uni.get('verified_eti_detections_total')}")

    # C15: Visuals + VISUAL_REVIEW + RESULTS_REPORT.md
    vr = _read_json(res / "VISUAL_REVIEW.json")
    rep_p = ws / "RESULTS_REPORT.md"
    bad_vis = []
    if not (vr.get("all_passed") is True and len(vr.get("figures", [])) == 6):
        bad_vis.append("vr_metadata")
    for fe in vr.get("figures", []):
        fp = ws / fe["relpath"]
        if not fp.exists() or fp.stat().st_size <= 50000 or fp.stat().st_size != fe["bytes"]:
            bad_vis.append(f"{fe['filename']}:size")
        elif fp.read_bytes()[:4] != b"\x89PNG" or _sha256_file(fp) != fe["sha256"]:
            bad_vis.append(f"{fe['filename']}:png_or_sha")
    if not rep_p.exists() or rep_p.stat().st_size < 2000:
        bad_vis.append("RESULTS_REPORT.md")
    _rec("C15_VISUALS_AND_REPORT", not bad_vis, f"6 PNGs + VISUAL_REVIEW + RESULTS_REPORT, bad={bad_vis}")

    # C16: IMPLEMENTATION_LOCK & RESULTS_MANIFEST_SHA256
    rm_p = ws / "RESULTS_MANIFEST_SHA256.json"
    rm = _read_json(rm_p)
    bad_lock = []
    if impl.get("method_lock_sha256") != lr.get("method_lock_sha256"):
        bad_lock.append("impl.method_lock_sha256")
    for fn, meta in impl.get("stage2_files", {}).items():
        fp = ws / fn
        if not fp.exists() or fp.stat().st_size != meta["bytes"] or _sha256_file(fp) != meta["sha256"]:
            bad_lock.append(f"impl:{fn}")
    disk_ws = sorted(
        p.relative_to(ws).as_posix()
        for p in ws.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts and not p.name.endswith(".pyc") and p.name != "RESULTS_MANIFEST_SHA256.json"
    )
    man_files = rm.get("files", {})
    if sorted(man_files.keys()) != disk_ws:
        bad_lock.append(f"manifest_key_diff:{len(man_files)}!={len(disk_ws)}")
    for rp in disk_ws:
        fp = ws / rp
        m = man_files.get(rp, {})
        if fp.stat().st_size != m.get("bytes") or _sha256_file(fp) != m.get("sha256"):
            bad_lock.append(f"res_sha:{rp}")
    _rec("C16_LOCKS_AND_MANIFEST_SHA256", not bad_lock, f"manifest_files={len(disk_ws)}, bad={bad_lock}")

    passed = sum(1 for _, ok, _ in checks if ok)
    return passed, len(checks), checks


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--archives-dir", required=True)
    args = ap.parse_args()
    passed, total, checks = run_audit(Path(args.workspace).resolve(), Path(args.archives_dir).resolve())
    for cid, ok, msg in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {cid}: {msg}")
    print(f"AUDIT_SUMMARY: {passed}/{total} PASSED")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
