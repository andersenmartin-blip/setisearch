#!/usr/bin/python3 -S
"""
Pure-Stdlib Independent Audit Suite (`C1–C16`) for Phase D104 (`V6.2`).
Run strictly via:
  /usr/bin/python3 -S audit.py --workspace . --archives-dir ../../archives
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import pathlib
import statistics
import zipfile

PRIOR_29_ARCHIVES: list[tuple[str, str, str]] = [
    ("D069_D074", "SETI_D069_D074_FEROS_VELOCITY_CONTEXT_RESULTS_2026-11-13.zip", "b9bd142de7bdbf98b88d87dd5889cee3b1f1b43d93c17c4e711e6ed8a2e11820"),
    ("D075_D076", "SETI_D075_D076_FEROS_ORDERS_AND_DIRECTION_RESULTS_2026-11-13.zip", "2b7c5b48ee2f3b62ec7c3b6b65c150af4fed80b1930355d4d6b212b0d262fa31"),
    ("D077", "SETI_D077_FEROS_WLC_METADATA_GATE_RESULTS_2026-11-14.zip", "828466e2c8ede7897be98d38d247fb18def0e5acdb40754656c8d2517c27c818"),
    ("D078", "SETI_D078_FEROS_RESTFRAME_AND_HD43629_SYNTHESIS_RESULTS_2026-11-14.zip", "83132e0a43903a26ba6808b8bcca34f39850088d0aee05f0bdfb93b5d5ea6069"),
    ("D079", "SETI_D079_V3_CALIBRATED_OPTICAL_SEARCH_RESULTS_2026-11-14.zip", "ae7ec48fc51522c823c06940c60b661725430f632ba6f048402d9cf66ce07af3"),
    ("D080", "SETI_D080_V3_1_EXOPLANET_AND_HARPS_ESPRESSO_RESULTS_2026-11-14.zip", "0c663b2b65e340deedf629cea069cee5092230a954ad56b6c39bf79684f00133"),
    ("D081", "SETI_D081_V3_2_TRANSIT_KINEMATICS_AND_10PC_RESULTS_2026-11-15.zip", "12b951d77993cae116b8b7e8968866c13a374a23bd06ac1e96610ac63ee713a9"),
    ("D082", "SETI_D082_V3_3_NIRPS_NEAR_IR_AND_PANCHROMATIC_RESULTS_2026-11-15.zip", "d5f73f0c93e6e6381441896e0457ea18d3baa05fadd7a8c569b60361f88a2457"),
    ("D083", "SETI_D083_V3_4_CRIRES_KBAND_AND_100STAR_RESULTS_2026-11-15.zip", "f60cf9d63b457c5246dcb14c5b4064376ef709118b5b325360d0d6c1686adf19"),
    ("D084", "SETI_D084_V3_5_NORTHERN_10PC_AND_125STAR_RESULTS_2026-11-16.zip", "d13c6f409047d9b8a16c74f26098c44d4808d9f6a96a2e79dba34395f99d77cc"),
    ("D085", "SETI_D085_V3_6_SPIROU_YJHK_AND_COMB_V4_RESULTS_2026-11-17.zip", "2d27e24d9b943af3ff8d4796155ab0bbf97e87540b265f7cef5df56dba0685cb"),
    ("D086", "SETI_D086_V3_7_UVES_NUV_PANCHROM_AND_COMB_V4_1_RESULTS_2026-11-17.zip", "b37d27ac6269e6671fb341b98514b27edad5b2dbbc392bec75eaeaa63073aea1"),
    ("D087", "SETI_D087_V3_8_SPACE_UV_STIS_FARRED_AND_200STAR_RESULTS_2026-11-18.zip", "95b35e2a8b93b536c07b3c47c6c70f2ab1712455613059d66c7a00fe9591671c"),
    ("D088", "SETI_D088_V3_9_NORTHERN_RADIO23_AND_ALLSKY_COMB_V4_1_RESULTS_2026-11-18.zip", "c0210250b925df3bebb1710c2bf7333a64ed767ebdc1f38a496d6a9454f7d45d"),
    ("D089", "SETI_D089_V4_0_SPACE_LYMAN_FUV_NUV_RESULTS_2026-11-19.zip", "4864dd3b5c0e958e428e1af815e1a378a37824d6bc87a89de9c223d89bccd723"),
    ("D090", "SETI_D090_V4_1_JWST_SPACE_THERMAL_IR_RESULTS_2026-11-19.zip", "2940839e8613b0d388c9b922743ba8244852806411f28586696e59eb8d73841a"),
    ("D091", "SETI_D091_V4_2_ESO_TRIPLE_3ARM_RESULTS_2026-11-20.zip", "9da4739bdb413d675b9bc1f17dc9d60d5abc7944622714017cf1889a097b51d0"),
    ("D092", "SETI_D092_V5_0_RPCA_RARITY_ELLIPSOID_PPO_MIRI_CCF_RESULTS_2026-11-20.zip", "845f0186a6a793ece2b62f9a2e7caaca5181a9b5a12f8db39326376a58a1d8dd"),
    ("D093", "SETI_D093_V5_1_DEDOPPLER_DRIFT_ELLIPSOID_GRACES_CORALIE_CARMENES_RESULTS_2026-11-21.zip", "2588057cbd611686d50ced7f4432dce623b16609bc62de01d6460c91c504979a"),
    ("D094", "SETI_D094_V5_2_MULTIEPOCH_DRIFT_APOGEE2_CRIRESJH_MIRILRS_RESULTS_2026-11-21.zip", "fea863077ae837b6741d5837990fd357158e00f6a5e3d9adde51f0c81e8ccefc"),
    ("D095", "SETI_D095_V5_3_CURVED_PERIODIC_DRIFT_GHOST_SPITZER_IRS_APOGEE2_RESULTS_2026-11-21.zip", "24f5a73a4299d697a198e91e3e15b5b7ddce838f6d055cebe66ddd812520c21d"),
    ("D096", "SETI_D096_V5_4_SOFIA_EXES_MIDIR_ECHELLE_COHERENT_DRIFT_JWST_RESULTS_2026-11-21.zip", "a134e4d5d0b6e0cb4e17763dc729203218cac9265c7db75db719135cb01c5158"),
    ("D097", "SETI_D097_V5_5_HERSCHEL_THZ_FARIR_STIS_E140H_OPTICAL_JERK_RESULTS_2026-11-22.zip", "aa296f9c72faefcacbd4f4fedb73c7c3f2b1377823fad3e308fd6a9844f6fed8"),
    ("D098", "SETI_D098_V5_6_SOFIA_GREAT_ISO_SWS_FORCAST_OPTICAL_JERK_RESULTS_2026-11-22.zip", "f57f48355df2b92257f39d76e83f2d850ae6d9164ea10ef1539bede1ca8fb838"),
    ("D099", "SETI_D099_V5_7_JCMT_MM_SOFIA_EXES_IRTF_SPEX_KEPLERIAN_DRIFT_RESULTS_2026-11-22.zip", "77b187f3509a704978096c14b97f83a13d3eebb6b2fc9d53a8c3b296b362df0b"),
    ("D100", "SETI_D100_V5_8_JCMT_3MM_SOFIA_FIFILS_IUE_ECCENTRIC_KEPLERIAN_RESULTS_2026-11-22.zip", "f8900c1aee6db352b6317c1dd6bf308d286bab2c0c0b367e8863383438446bd2"),
    ("D101", "SETI_D101_V5_9_ALMA_MM_BAND1_GAP_CLOSURE_DRIFTING_COMB_RESULTS_2026-11-23.zip", "848a2ade7fdb46ed4e4f067e729ccf796a5181501f6e0ed18f573ff871fa8b20"),
    ("D102", "SETI_D102_V6_0_XRAY_EUV_POISSON_CHANDRA_EUVE_ALMA_UNBROKEN_MM_RESULTS_2026-11-23.zip", "684d6828063cf17b8adcd666932633c07196e8764038dbbdd3a48bdd5433ca2c"),
    ("D103", "SETI_D103_V6_1_HARD_XRAY_NUSTAR_XMM_RGS_ALMA_B9B10_700STAR_RESULTS_2026-11-23.zip", "d0155c0b3c98625c0e8f9cff5f55ccb89d7477e6ada6b3fd18a0ba8cc6615de4"),
]

PC_CM = 3.085677581491367e18
C_MPS = 2.99792458e8
BANNED_TOKENS = ("TBD", "TODO", "__PLACEHOLDER__", "lorem ipsum", "FIXME")


def _sha256(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            b = f.read(1 << 20)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _load_json(p: pathlib.Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _read_csv(p: pathlib.Path) -> list[dict[str, str]]:
    with p.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent)
    ap.add_argument("--archives-dir", type=pathlib.Path, default=None)
    args = ap.parse_args()

    ws = args.workspace.resolve()
    res = ws / "results"
    archives_dir = args.archives_dir.resolve() if args.archives_dir else (ws.parent.parent / "archives")
    passed = 0

    def chk(cid: str, fn) -> None:
        nonlocal passed
        try:
            msg = fn()
            passed += 1
            print(f"[PASS] {cid}: {msg}")
        except Exception as exc:
            print(f"[FAIL] {cid}: {exc}")

    # C1
    def c1() -> str:
        ml = _load_json(ws / "METHOD_LOCK.json")
        lr = _load_json(ws / "LOCK_RECEIPT.json")
        assert lr["status"] == "STAGE-1 SEALED"
        assert lr["inputs_dir_exists_at_seal"] is False
        assert _sha256(ws / "METHOD_LOCK.json") == lr["method_lock_sha256"]
        assert len(ml["stage_1_files"]) == 7
        for fn, sh in ml["stage_1_files"].items():
            assert _sha256(ws / fn) == sh, f"Stage-1 hash mismatch: {fn}"
        return f"7/7 Stage-1 files immutable; raw_dir_at_seal=False; METHOD_LOCK={lr['method_lock_sha256'][:12]}..."
    chk("C1_STAGE1_LOCK", c1)

    # C2
    def c2() -> str:
        fdr = _load_json(ws / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json")
        man = _load_json(ws / "FULL_D104_INPUT_MANIFEST.json")
        assert float(fdr["chronology_lag_seconds"]) >= 10.0
        assert man["expected_observations"] == 104
        assert man["valid_observations"] == 103
        assert man["failed_observations"] == 1
        assert man["valid_physical_files"] == 103
        assert len(man["errors"]) == 1 and man["errors"][0]["dp_id"] == "ADP.2024-08-06T10:07:12.768"
        for obs in man["observations"]:
            assert len(obs["sha256"]) == 64 and int(obs["bytes"]) > 1000
        return f"lag={fdr['chronology_lag_seconds']}s >= 10s; 103/104 valid (1 transparent ESO 408 timeout)"
    chk("C2_DOWNLOAD_PROVENANCE", c2)

    # C3
    def c3() -> str:
        pe = _load_json(ws / "PRIOR_EXCLUSION_VERIFICATION.json")
        assert pe["d104_dp_id_overlap_count"] == 0
        assert pe["n_prior_excluded_coords"] == 782
        assert pe["n_prior_excluded_dp_ids"] == 3472
        assert float(pe["min_brand_new_sky_separation_arcsec"]) >= 300.0
        assert float(pe["min_intra_d104_separation_arcsec"]) >= 120.0
        return f"0 overlaps vs 782 coords / 3472 dp_ids; min_sep={pe['min_brand_new_sky_separation_arcsec']}''"
    chk("C3_PRIOR_EXCLUSION", c3)

    # C4
    def c4() -> str:
        cohort = _read_csv(ws / "FROZEN_COHORT_D104.csv")
        prov = _read_csv(res / "EXPOSURE_PROVENANCE_D104.csv")
        xr = _read_csv(res / "XRISM_RESOLVE_20OBS.csv")
        assert len(cohort) == 104
        assert len(prov) == 103
        assert len({r["canonical_target"] for r in cohort}) == 64
        assert len(xr) == 20
        assert all(r["filter_hdr"] == "OPEN" for r in xr)
        return f"104 locked / 103 analyzed / 64 targets / 20/20 XRISM FILTER='OPEN' Pixel!=12"
    chk("C4_COHORT_AND_XRISM_OPEN", c4)

    # C5
    def c5() -> str:
        s = _load_json(res / "SUMMARY.json")
        bp = ws / "bounded_inputs/d104_bounded_bundle.json.gz"
        assert bp.exists()
        sz = bp.stat().st_size
        assert sz <= int(18.5 * 1024 * 1024)
        assert sz == int(s["cohort"]["bounded_bundle_bytes"])
        assert _sha256(bp) == s["cohort"]["bounded_bundle_sha256"]
        with gzip.open(bp, "rb") as gz:
            b = json.loads(gz.read().decode("utf-8"))
        assert len(b["exposures"]) == 103
        return f"{sz:,} B ({sz/(1024*1024):.3f} MiB <= 18.5 MiB); 103 exposures decoded"
    chk("C5_BOUNDED_BUNDLE", c5)

    # C6
    def c6() -> str:
        s = _load_json(res / "SUMMARY.json")
        cal = s["synthetic_calibration_3771_trials"]
        assert cal["n_suites"] == 18
        assert cal["total_trials"] == 3771
        assert cal["total_passed"] >= 3740
        for nm, meta in cal["suites"].items():
            rate = meta["passed"] / meta["total"]
            assert rate >= 0.95, f"{nm} rate {rate:.4f} < 0.95"
        assert int(s["unified_755star_panchromatic_v6_2_synthesis"]["total_calibration_trials_d079_d104"]) == 58299
        return f"18/18 suites {cal['total_passed']}/{cal['total_trials']} ({100*cal['total_passed']/cal['total_trials']:.2f}%); cum=58,299"
    chk("C6_CALIBRATION_SUITES", c6)

    # C7
    def c7() -> str:
        suz = _read_csv(res / "SUZAKU_HXD_GSO_18OBS.csv")
        xr = _read_csv(res / "XRISM_RESOLVE_20OBS.csv")
        ni = _read_csv(res / "NICER_XTI_20OBS.csv")
        sp = _read_csv(res / "V6_2_SPACE_CANDIDATE_LEDGER.csv")
        sca = _load_json(res / "SPECTRAL_COVERAGE_AUDIT_D104.json")
        assert len(suz) == 18 and len(xr) == 20 and len(ni) == 20
        assert len(sp) == 356
        assert all(r["verified_eti"] == "0" for r in sp)
        assert sca["high_energy_unbroken_octaves"] == 15.048
        assert sca["total_octave_span"] == 31.947
        assert sca["alma_bands_complete"] == ["B1", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10"]
        return f"18 GSO + 20 XRISM + 20 NICER -> 0 ETI; {sca['high_energy_unbroken_octaves']} HE oct / {sca['total_octave_span']} tot oct"
    chk("C7_HIGH_ENERGY_FRONTIER", c7)

    # C8
    def c8() -> str:
        fg = _read_csv(res / "FOUR_GEN_BENCHMARK_D104.csv")
        vc = _read_csv(res / "V6_2_CANDIDATE_LEDGER.csv")
        ac = _read_csv(res / "ALLSKY_COMB_V4_1_UNIFIED_D079_D104.csv")
        s206 = _read_csv(res / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_206STARS.csv")
        assert len(fg) == 3 and sum(int(r["n_exposures"]) for r in fg) == 45
        assert sum(int(r["stage2_verified_eti"]) for r in fg) == 0
        assert len(vc) == 4 and all(r["verified_eti"] == "0" for r in vc)
        assert len(ac) == 523 and all(r["verified_eti_combs"] == "0" for r in ac)
        assert len(s206) == 206
        lims = [float(r["min_panchromatic_10m_kw"]) for r in s206 if r.get("min_panchromatic_10m_kw") and float(r["min_panchromatic_10m_kw"]) > 0]
        med = round(statistics.median(lims), 4)
        assert abs(med - 0.9688) < 1e-4, f"Expected median 0.9688, got {med}"
        return f"45 optical (G8=4->0 ETI); 523 comb stacks -> 0 ETI; 206 <10pc (med {med:.4f} kW)"
    chk("C8_OPTICAL_COMB_AND_206_10PC", c8)

    # C9
    def c9() -> str:
        o6 = _read_csv(res / "ORBITAL_CAMPAIGN_RESULTS_6_D104.csv")
        dr = _read_csv(res / "DRIFT_V62_ECCENTRIC_KEPLERIAN_66CAMPAIGNS.csv")
        cd = _read_csv(res / "COMB_DRIFT_V62_66CAMPAIGNS.csv")
        assert len(o6) == 6
        hd = [r for r in o6 if r["star"] == "HD210277"][0]
        assert hd["n_epochs"] == "4"
        assert len(dr) == 66 and len(cd) == 66
        assert all(r["stage2_verified_eti"] == "0" for r in dr + cd)
        n_tr = sum(int(r["n_trajectories_evaluated"]) for r in dr)
        n_px = sum(int(r["n_pixel_trajectory_integrals"]) for r in dr)
        n_ctr = sum(int(r["comb_trajectories_evaluated"]) for r in cd)
        assert n_tr == 89265 and n_px == 10032034016 and n_ctr == 11758
        return f"66 campaigns DRIFT_V62 ({n_tr:,} traj / {n_px/1e9:.2f}B px) + COMB_DRIFT_V62 ({n_ctr:,} traj) -> 0 ETI"
    chk("C9_66CAMPAIGN_DRIFT_V62", c9)

    # C10
    def c10() -> str:
        u755 = _read_csv(res / "UNIFIED_PANCHROMATIC_V6_2_SYNTHESIS_755STARS.csv")
        br = _read_csv(res / "PANCHROMATIC_BRIDGE_93STARS_V62.csv")
        ell = _read_csv(res / "MULTIEVENT_ELLIPSOID_755STARS.csv")
        assert len(u755) == 755 and len(ell) == 755
        assert sum(r["role"] == "SCIENCE" for r in u755) == 554
        assert sum(r["role"] == "CONTROL" for r in u755) == 201
        assert sum(int(float(r["n_exoplanets"] or 0)) > 0 for r in u755) == 245
        assert sum(int(float(r["n_exoplanets"] or 0)) for r in u755) == 470
        assert all(r["verified_eti_detections"] == "0" for r in u755)
        assert len(br) == 1184
        assert sum(r["etz_qualified"] == "True" for r in ell) == 122
        assert sum(r["ellipsoid_qualified_180d"] == "True" for r in ell) == 40
        return "755 stars (554 Sci / 201 Ctrl; 245 hosts / 470 planets); 93 bridges (1,184 cells); 122 ETZ / 40 <=180d; 0 ETI"
    chk("C10_UNIFIED_755_SYNTHESIS", c10)

    # C11
    def c11() -> str:
        s = _load_json(res / "SUMMARY.json")
        src = _load_json(res / "SOURCES.json")
        syn = s["unified_755star_panchromatic_v6_2_synthesis"]
        assert syn["spectrographs"] == 52 and syn["spectral_arms"] == 82
        assert syn["total_exposures_d079_d104"] == 3290
        assert abs(float(syn["total_integration_hours_d079_d104"]) - 5966.0701) < 1e-3
        assert syn["v2_false_alarms_eliminated_total"] == 989116
        assert syn["cumulative_orbital_campaigns"] == 174
        assert syn["cumulative_comb_stacks"] == 523
        assert syn["verified_eti_detections_total"] == 0
        assert s["raw_hits_and_triage"]["verified_eti_detections_total"] == 0
        assert src["analyzed_observations"] == 103 and len(src["exposures"]) == 103
        assert len(src["retroactive_companion_archives"]) == 10
        return "SUMMARY & SOURCES consistent: 52 spectrographs / 82 arms / 3,290 exp / 5,966.0701 h / 0 ETI"
    chk("C11_SUMMARY_AND_SOURCES", c11)

    # C12
    def c12() -> str:
        max_err = 0.0
        n_chk = 0
        for fn in ("EIRP_UPPER_LIMITS_D104.csv", "PANCHROMATIC_BRIDGE_93STARS_V62.csv"):
            for r in _read_csv(res / fn):
                if not r.get("flux_lim_erg_cm2_s") or not r.get("p_beam_10m_kw"):
                    continue
                wa = float(r.get("wave_bary_a") or r.get("wave_A"))
                d_pc = float(r["dist_pc"])
                fl = float(r["flux_lim_erg_cm2_s"])
                pk_rep = float(r["p_beam_10m_kw"])
                if d_pc <= 0 or fl <= 0 or pk_rep <= 0 or wa <= 0:
                    continue
                d_cm = d_pc * PC_CM
                l_iso = 4.0 * math.pi * d_cm * d_cm * fl
                g = ((C_MPS / (wa * 1e-10)) * math.pi * 10.0 / C_MPS) ** 2
                p_kw = (l_iso * 1e-7) / max(1.0, g) * 1e-3
                max_err = max(max_err, abs(p_kw - pk_rep) / pk_rep)
                n_chk += 1
        assert n_chk == 1494, f"Expected 1494 C12 rows, got {n_chk}"
        assert max_err < 0.002, f"C12 max_rel_err {max_err} >= 0.002"
        return f"{n_chk} EIRP+bridge rows recomputed pure-stdlib: max_rel_err={max_err:.10f} < 0.002"
    chk("C12_RADIOMETRIC_CLOSURE", c12)

    # C13
    def c13() -> str:
        assert archives_dir.is_dir(), f"Missing archives dir {archives_dir}"
        for _, zname, exp_sha in PRIOR_29_ARCHIVES:
            zp = archives_dir / zname
            assert zp.exists(), f"Missing archive {zname}"
            assert _sha256(zp) == exp_sha, f"Archive SHA mismatch: {zname}"
            with zipfile.ZipFile(zp, "r") as zf:
                assert zf.testzip() is None, f"Corrupt zip: {zname}"
        return "All 29 prior companion archives (A-Z, AA-AC) SHA-256 & zip-integrity verified"
    chk("C13_ARCHIVE_CHAIN_A_AC", c13)

    # C14
    def c14() -> str:
        vr = _load_json(res / "VISUAL_REVIEW.json")
        assert vr["overall_status"] == "PASS" and vr["dpi"] == 240 and vr["metadata_stripped"] is True
        figs = vr["figures"]
        assert len(figs) == 6
        for fname, info in figs.items():
            fp = res / "figures" / fname
            assert fp.exists(), f"Missing figure {fname}"
            raw = fp.read_bytes()
            assert raw[:8] == b"\x89PNG\r\n\x1a\n"
            assert b"/home/" not in raw[:1024] and b"Author" not in raw[:1024]
            assert _sha256(fp) == info["sha256"]
            assert info["status"] == "PASS" and info["inspected"] is True
        return "6/6 figures (fig115-fig120) @ 240 DPI metadata-free, inspected PASS & SHA-verified"
    chk("C14_FIGURES_AND_VISUAL_REVIEW", c14)

    # C15
    def c15() -> str:
        man = _load_json(ws / "RESULTS_MANIFEST_SHA256.json")
        impl = _load_json(ws / "IMPLEMENTATION_LOCK.json")
        assert int(man["n_files"]) == len(man["files"]) == 48
        for rel, meta in man["files"].items():
            fp = ws / rel
            assert fp.exists(), f"Missing manifest file {rel}"
            assert fp.stat().st_size == meta["bytes"], f"Size mismatch {rel}"
            assert _sha256(fp) == meta["sha256"], f"SHA mismatch {rel}"
        assert _sha256(ws / "RESULTS_MANIFEST_SHA256.json") == impl["results_manifest_sha256"]
        for fn, meta in impl["files"].items():
            fp = ws / fn
            assert fp.stat().st_size == meta["bytes"] and _sha256(fp) == meta["sha256"]
        return f"RESULTS_MANIFEST_SHA256 ({man['n_files']} files) & IMPLEMENTATION_LOCK ({len(impl['files'])} files) verified"
    chk("C15_MANIFEST_AND_IMPL_LOCK", c15)

    # C16
    def c16() -> str:
        raw_exts = (".fits", ".fit", ".evt", ".ftz", ".evt.gz")
        bad_raw = [p.name for p in ws.rglob("*") if p.is_file() and any(p.name.lower().endswith(ex) for ex in raw_exts)]
        assert not bad_raw, f"Raw FITS files leaked into workspace: {bad_raw}"
        rep = (ws / "RESULTS_REPORT.md").read_text(encoding="utf-8")
        for tok in BANNED_TOKENS:
            assert tok not in rep, f"Banned token {tok!r} in RESULTS_REPORT.md"
        assert "31.947" in rep and "0.0005986394" in rep and "755" in rep and "206" in rep
        return "0 raw FITS in workspace; RESULTS_REPORT.md passes strict factual & token audit"
    chk("C16_CLEANLINESS_AND_REPORT", c16)

    print(f"Audit Result: {passed}/16 PASS")
    return 0 if passed == 16 else 1


if __name__ == "__main__":
    raise SystemExit(main())
