#!/usr/bin/python3 -S
"""
Zero-Dependency Pure-Stdlib C1-C16 Audit Suite for Phase D105 (V6.3):
Run strictly as: `/usr/bin/python3 -S audit.py --workspace <ws> --archives-dir <archives>`
Requires zero third-party packages (verified by AST gate C16).
"""
from __future__ import annotations

import argparse
import ast
import csv
import gzip
import hashlib
import json
import math
import pathlib
import sys

PC_CM = 3.0856775814913673e18

PRIOR_30_ARCHIVES: list[tuple[str, str, int, str]] = [
    ("A",  "SETI_D069_D074_FEROS_VELOCITY_CONTEXT_RESULTS_2026-11-13.zip",                  45920303, "b9bd142de7bdbf98b88d87dd5889cee3b1f1b43d93c17c4e711e6ed8a2e11820"),
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
]


def _sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def _rjson(p: pathlib.Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _rcsv(p: pathlib.Path) -> list[dict[str, str]]:
    with p.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent)
    ap.add_argument("--archives-dir", type=pathlib.Path, default=None)
    args = ap.parse_args()

    ws = args.workspace.resolve()
    res = ws / "results"
    archives_dir = args.archives_dir.resolve() if args.archives_dir else (ws.parent.parent / "archives")
    if not archives_dir.exists() and (ws.parent / "archives").exists():
        archives_dir = ws.parent / "archives"

    summary = _rjson(res / "SUMMARY.json")
    lr = _rjson(ws / "LOCK_RECEIPT.json")
    ml = _rjson(ws / "METHOD_LOCK.json")
    fdr = _rjson(ws / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json")
    man = _rjson(ws / "FULL_D105_INPUT_MANIFEST.json")
    excl = _rjson(ws / "PRIOR_EXCLUSION_VERIFICATION.json")
    vr = _rjson(res / "VISUAL_REVIEW.json")
    rm = _rjson(ws / "RESULTS_MANIFEST_SHA256.json")
    il = _rjson(ws / "IMPLEMENTATION_LOCK.json")

    checks: list[tuple[str, bool, str]] = []

    def add(cid: str, ok: bool, detail: str) -> None:
        checks.append((cid, bool(ok), detail))

    # C1: Stage-1 prospective lock immutability
    s1_files = ml["stage_1_files"]
    c1_hashes_ok = all(_sha256(ws / fn) == hx for fn, hx in s1_files.items())
    c1_ok = (
        lr.get("status") == "STAGE-1 SEALED"
        and lr.get("inputs_dir_exists_at_seal") is False
        and len(s1_files) == 7
        and _sha256(ws / "METHOD_LOCK.json") == lr.get("method_lock_sha256")
        and c1_hashes_ok
    )
    add("C1", c1_ok, f"7/7 Stage-1 files byte-identical, inputs_absent_at_seal={lr.get('inputs_dir_exists_at_seal')}")

    # C2: Chronology lag >= 10s + full valid manifest
    lag = float(fdr["chronology_lag_seconds"])
    c2_ok = (
        lag >= 10.0
        and man.get("expected_observations") == 126
        and man.get("valid_observations") == 126
        and man.get("failed_observations") == 0
        and man.get("expected_physical_files") == 82
        and man.get("valid_physical_files") == 82
        and man.get("failed_physical_files") == 0
    )
    add("C2", c2_ok, f"chronology_lag={lag:.3f}s >= 10.0s, obs=126/126, files=82/82")

    # C3: Bounded bundle size & hash
    bp = ws / "bounded_inputs/d105_bounded_bundle.json.gz"
    b_bytes = bp.stat().st_size
    b_sha = _sha256(bp)
    bundle_obj = json.loads(gzip.decompress(bp.read_bytes()).decode("utf-8"))
    c3_ok = (
        b_bytes <= int(18.5 * 1024 * 1024)
        and b_sha == summary["cohort"]["bounded_bundle_sha256"]
        and b_sha == il["bounded_bundle"]["sha256"]
        and len(bundle_obj["exposures"]) == 126
    )
    add("C3", c3_ok, f"bundle={b_bytes/(1024*1024):.3f} MiB <= 18.5 MiB, exps=126")

    # C4: Prior exclusion & sky separation
    c4_ok = (
        excl["n_prior_excluded_coords"] == 828
        and excl["n_prior_excluded_dp_ids"] == 3576
        and excl["d105_dp_id_overlap_count"] == 0
        and float(excl["min_brand_new_sky_separation_arcsec"]) >= 300.0
        and float(excl["min_intra_d105_separation_arcsec"]) >= 120.0
    )
    add("C4", c4_ok, f"0 dp_id overlaps / {excl['n_prior_excluded_dp_ids']} prior, min_sep={excl['min_brand_new_sky_separation_arcsec']:.1f} arcsec")

    # C5: 21 synthetic calibration suites (4,491 trials -> 62,790 cumulative)
    cs = summary["synthetic_calibration_4491_trials"]
    suites_ok = all(v["passed"] / v["total"] >= 0.95 for v in cs["suites"].values())
    c5_ok = (
        cs["n_suites"] == 21
        and cs["total_trials"] == 4491
        and cs["total_passed"] >= int(0.99 * 4491)
        and suites_ok
        and cs["suites"]["CALIBRATION_V63_CGRO_OSSE_240"]["passed"] == 240
        and cs["suites"]["CALIBRATION_V63_CGRO_COMPTEL_240"]["passed"] >= 238
        and cs["suites"]["CALIBRATION_V63_FERMI_LAT_240"]["passed"] == 240
    )
    add("C5", c5_ok, f"{cs['n_suites']} suites, {cs['total_passed']}/{cs['total_trials']} passed")

    # C6: High-energy MeV-GeV searches (OSSE 26, COMPTEL 20 real ARM, Fermi LAT 40)
    osse = _rcsv(res / "CGRO_OSSE_26OBS.csv")
    comp = _rcsv(res / "CGRO_COMPTEL_20TARGETS.csv")
    lat = _rcsv(res / "FERMI_LAT_40TARGETS.csv")
    comp_min_on = min(int(r["n_events_science"]) for r in comp)
    comp_raw = sum(int(r["n_raw"]) for r in comp)
    lat_raw = sum(int(r["n_raw"]) for r in lat)
    c6_ok = (
        len(osse) == 26
        and len(comp) == 20
        and len(lat) == 40
        and comp_min_on > 50000
        and comp_raw == summary["raw_hits_and_triage"]["cgro_comptel_raw_candidates"]
        and lat_raw == summary["raw_hits_and_triage"]["fermi_lat_raw_candidates"]
        and all(int(r["verified_eti"]) == 0 for r in osse + comp + lat)
    )
    add("C6", c6_ok, f"OSSE=26, COMPTEL=20 (min_on={comp_min_on:,}, raw={comp_raw}), LAT=40 (raw={lat_raw}) -> 0 ETI")

    # C7: Optical 4-Gen, Orbits #175-#180, & static COMB_V4_1
    o6 = _rcsv(res / "ORBITAL_CAMPAIGN_RESULTS_6_D105.csv")
    comb_u = _rcsv(res / "ALLSKY_COMB_V4_1_UNIFIED_D079_D105.csv")
    c7_ok = (
        len(o6) == 6
        and all(int(r["n_epochs"]) >= 5 and int(r["verified_eti"]) == 0 for r in o6)
        and len(comb_u) == 539
        and summary["raw_hits_and_triage"]["comb_verified_eti"] == 0
    )
    add("C7", c7_ok, f"6/6 live N=5 orbits, 539 static comb stacks, 0 ETI")

    # C8: 72-campaign DRIFT_V63 + COMB_DRIFT_V63
    dr72 = _rcsv(res / "DRIFT_V63_ECCENTRIC_KEPLERIAN_72CAMPAIGNS.csv")
    cd72 = _rcsv(res / "COMB_DRIFT_V63_72CAMPAIGNS.csv")
    c8_ok = (
        len(dr72) == 72
        and len(cd72) == 72
        and all(int(r["stage2_verified_eti"]) == 0 for r in dr72 + cd72)
    )
    add("C8", c8_ok, f"72 DRIFT_V63 ({summary['raw_hits_and_triage']['drift_v63_72campaigns_pixel_integrals']:,} px-int) + 72 COMB_DRIFT_V63 -> 0 ETI")

    # C9: Spectral continuity (33.979 HE octaves / 50.879 total octaves)
    sc = summary["spectral_continuity_v63"]
    syn = summary["unified_806star_panchromatic_v6_3_synthesis"]
    c9_ok = (
        float(sc["high_energy_unbroken_octaves"]) == 33.979
        and float(sc["total_octave_span"]) == 50.879
        and syn["spectrographs"] == 55
        and syn["spectral_arms"] == 85
    )
    add("C9", c9_ok, f"HE={sc['high_energy_unbroken_octaves']} oct, total={sc['total_octave_span']} oct, {syn['spectrographs']}/{syn['spectral_arms']} instr/arms")

    # C10: Unified 806-star + 230 <10 pc + 806-star Ellipsoid
    u806 = _rcsv(res / "UNIFIED_PANCHROMATIC_V6_3_SYNTHESIS_806STARS.csv")
    s230 = _rcsv(res / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_230STARS.csv")
    ell806 = _rcsv(res / "MULTIEVENT_ELLIPSOID_806STARS.csv")
    c10_ok = (
        len(u806) == 806
        and len(s230) == 230
        and len(ell806) == 806
        and syn["unique_stars_total"] == 806
        and syn["within_10pc_unique_stars"] == 230
    )
    add("C10", c10_ok, f"806 unique stars ({syn['science_stars_total']} Sci / {syn['control_stars_total']} Ctrl), 230 <10 pc")

    # C11: 107 SCIENCE Bridges / 129 multi-phase / 1,504 cells
    br = _rcsv(res / "PANCHROMATIC_BRIDGE_107STARS_V63.csv")
    c11_ok = (
        syn["panchromatic_bridge_stars_total"] == 107
        and syn["multi_phase_targets_total"] == 129
        and len(br) == 1504
        and syn["panchromatic_bridge_cells_total"] == 1504
    )
    add("C11", c11_ok, f"107 SCIENCE bridges / 129 multi-phase / {len(br)} cells")

    # C12: Pure-stdlib radiometric closure (max_rel_err < 0.002)
    eirp = _rcsv(res / "EIRP_UPPER_LIMITS_D105.csv")
    max_rel = 0.0
    n_c12 = 0
    for rows_set, wc in ((eirp, "wave_bary_a"), (br, "wave_A")):
        for r in rows_set:
            fls = r.get("flux_lim_erg_cm2_s", "")
            pks = r.get("p_beam_10m_kw", "")
            if not fls or not pks:
                continue
            fl = float(fls)
            pk_rep = float(pks)
            if fl <= 0.0 or pk_rep <= 0.0:
                continue
            d_cm = float(r["dist_pc"]) * PC_CM
            l_w = 4.0 * math.pi * d_cm * d_cm * fl * 1e-7
            th = (math.pi * 10.0) / (float(r[wc]) * 1e-10)
            pk_calc = (l_w / (th * th)) / 1000.0
            rel = abs(pk_calc - pk_rep) / pk_rep
            if rel > max_rel:
                max_rel = rel
            n_c12 += 1
    c12_ok = (n_c12 == len(eirp) + 1490 and max_rel < 0.002)
    add("C12", c12_ok, f"rows={n_c12}, max_rel_err={max_rel:.10f} < 0.002")

    # C13: Manifest SHA-256 & IMPLEMENTATION_LOCK verification
    m_files = rm.get("files", {})
    m_ok = len(m_files) >= 35 and all(_sha256(ws / k) == v["sha256"] and (ws / k).stat().st_size == v["bytes"] for k, v in m_files.items())
    il_files = il.get("files", {})
    il_ok = (
        len(il_files) >= 7
        and il.get("method_lock_sha256") == lr.get("method_lock_sha256")
        and il.get("results_manifest_sha256") == _sha256(ws / "RESULTS_MANIFEST_SHA256.json")
        and all(_sha256(ws / k) == v["sha256"] and (ws / k).stat().st_size == v["bytes"] for k, v in il_files.items())
    )
    add("C13", m_ok and il_ok, f"manifest={len(m_files)} files + IMPLEMENTATION_LOCK ({len(il_files)} files) exact")

    # C14: Visual review of 6 PNG figures
    figs_ok = (
        vr.get("n_figures") == 6
        and vr.get("all_passed") is True
        and all(_sha256(res / "figures" / e["filename"]) == e["sha256"] and e["visual_inspection"] == "PASS_NO_CLIPPING_NO_OVERLAP" for e in vr.get("figures", []))
    )
    add("C14", figs_ok, f"6/6 figures visual PASS + SHA-256 matched")

    # C15: Zero ETI + 30/30 Prior Companion Archives A-Z, AA-AD
    arch_ok = True
    arch_checked = 0
    for code, zname, zsize, zsha in PRIOR_30_ARCHIVES:
        zp = archives_dir / zname
        if not (zp.exists() and zp.stat().st_size == zsize and _sha256(zp) == zsha):
            arch_ok = False
        else:
            arch_checked += 1
    zero_eti = (
        summary["raw_hits_and_triage"]["verified_eti_detections_total"] == 0
        and syn["verified_eti_detections_total"] == 0
    )
    add("C15", arch_ok and zero_eti, f"verified_eti=0, prior archives verified={arch_checked}/30")

    # C16: Pure-stdlib AST import gate on audit.py
    tree = ast.parse(pathlib.Path(__file__).read_text(encoding="utf-8"))
    allowed = set(getattr(sys, "stdlib_module_names", set())) | {"__future__", "argparse", "ast", "csv", "gzip", "hashlib", "json", "math", "pathlib", "sys"}
    non_std = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for al in node.names:
                top = al.name.split(".")[0]
                if top not in allowed:
                    non_std.append(top)
        elif isinstance(node, ast.ImportFrom) and node.module:
            top = node.module.split(".")[0]
            if top not in allowed:
                non_std.append(top)
    add("C16", len(non_std) == 0, f"non_stdlib={non_std}")

    passed = sum(1 for _, ok, _ in checks if ok)
    for cid, ok, det_s in checks:
        print(f"[{cid}] {'PASS' if ok else 'FAIL'} -- {det_s}")
    print(f"SUMMARY: {passed}/{len(checks)} PASSED")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
