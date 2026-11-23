#!/usr/bin/env python3
"""
Phase D103 (V6.1) Independent Pure-Stdlib Verifier (`C1`–`C16`).
Must run cleanly under `/usr/bin/python3 -S audit.py --workspace ... --archives-dir ...`
with zero third-party imports (`non_stdlib == []`).
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import json
import math
import pathlib
import struct
import sys
import zipfile
from typing import Any

PC_CM = 3.085677581491367e18
BUNDLE_CAP_BYTES = int(18.5 * 1024 * 1024)

CALIBRATION_SUITES_D103 = [
    ("CALIBRATION_V61_NUSTAR_POISSON_240", 240, 235),
    ("CALIBRATION_V61_XMM_RGS_180", 180, 171),
    ("CALIBRATION_V60_CHANDRA_POISSON_240", 240, 228),
    ("CALIBRATION_V60_EUVE_180", 180, 171),
    ("CALIBRATION_V59_ALMA_INTERFEROMETRIC_240", 240, 228),
    ("CALIBRATION_V59_DRIFTING_COMB_240", 240, 228),
    ("CALIBRATION_V58_ECCENTRIC_KEPLERIAN_360", 360, 342),
    ("CALIBRATION_V58_G6_COINCIDENCE_120", 120, 114),
    ("INJECTION_RECOVERY_540", 540, 513),
    ("COMB_V4_1_CALIBRATION_162", 162, 154),
    ("DETECTOR_V58_G4G5_CALIBRATION_108", 108, 103),
    ("KEPLERIAN_TRACK_CALIBRATION_81", 81, 77),
    ("CALIBRATION_V58_RPCA_RARITY_180", 180, 171),
    ("CALIBRATION_V58_AGNOSTIC_120", 120, 114),
    ("CALIBRATION_G8_V58_120", 120, 114),
]


def _sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            blk = f.read(1 << 20)
            if not blk:
                break
            h.update(blk)
    return h.hexdigest()


def _read_json(path: pathlib.Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _iso_utc(s: str) -> dt.datetime:
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def _png_wh(path: pathlib.Path) -> tuple[int, int] | None:
    raw = path.read_bytes()
    if len(raw) < 24 or raw[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    if raw[12:16] != b"IHDR":
        return None
    w, h = struct.unpack(">II", raw[16:24])
    return int(w), int(h)


def run_audit(ws: pathlib.Path, archives_dir: pathlib.Path) -> dict[str, Any]:
    res = ws / "results"
    fig_dir = res / "figures"
    checks: list[dict[str, Any]] = []

    def add_check(cid: str, ok: bool, detail: str) -> None:
        checks.append({"id": cid, "status": "PASS" if ok else "FAIL", "detail": detail})

    summary = _read_json(res / "SUMMARY.json")
    sources = _read_json(res / "SOURCES.json")
    syn = summary["unified_709star_panchromatic_v6_1_synthesis"]

    # C1: Chronology Lock
    c1_ok = True
    c1_msg = []
    try:
        ml = _read_json(ws / "METHOD_LOCK.json")
        lr = _read_json(ws / "LOCK_RECEIPT.json")
        fdr = _read_json(ws / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json")
        il = _read_json(ws / "IMPLEMENTATION_LOCK.json")
        assert _sha256(ws / "METHOD_LOCK.json") == lr["method_lock_sha256"], "METHOD_LOCK sha mismatch"
        t_lock = _iso_utc(ml["locked_utc"])
        t_dl = _iso_utc(fdr["first_download_utc"])
        lag = (t_dl - t_lock).total_seconds()
        assert lag >= 10.0, f"chronology lag {lag:.2f}s < 10.0s"
        c1_msg.append(f"lag={lag:.2f}s, il_files={len(il.get('files', {}))}")
    except Exception as exc:
        c1_ok = False
        c1_msg.append(str(exc))
    add_check("C1_ChronologyLock", c1_ok, "; ".join(c1_msg))

    # C2: Cohort Freeze & Prior Exclusion
    c2_ok = True
    c2_msg = []
    try:
        coh = _read_csv(ws / "FROZEN_COHORT_D103.csv")
        pex = _read_json(ws / "PRIOR_EXCLUSION_VERIFICATION.json")
        ml = _read_json(ws / "METHOD_LOCK.json")
        assert _sha256(ws / "FROZEN_COHORT_D103.csv") == ml["stage_1_files"]["FROZEN_COHORT_D103.csv"], "FROZEN_COHORT sha mismatch"
        stars = {r["canonical_target"] for r in coh}
        n_bridges = sum(1 for r in coh if r["is_prior_bridge"] == "True")
        bridge_stars = {r["canonical_target"] for r in coh if r["is_prior_bridge"] == "True"}
        brand_stars = stars - bridge_stars
        assert len(coh) == 104, f"rows={len(coh)}"
        assert len(stars) == 70, f"unique_stars={len(stars)}"
        assert len(brand_stars) == 53 and len(bridge_stars) == 17, f"brand={len(brand_stars)}, bridge={len(bridge_stars)}"
        assert int(pex["d103_dp_id_overlap_count"]) == 0, "dp_id overlap != 0"
        assert float(pex["min_brand_new_sky_separation_arcsec"]) >= 300.0, "min_prior_sep < 300\""
        assert float(pex["min_intra_d103_separation_arcsec"]) >= 5.0, "min_intra_sep < 5\""
        c2_msg.append(f"obs={len(coh)}, stars={len(stars)} (53 new + 17 bridges, {n_bridges} bridge obs), min_prior_sep={pex['min_brand_new_sky_separation_arcsec']}\"")
    except Exception as exc:
        c2_ok = False
        c2_msg.append(str(exc))
    add_check("C2_CohortFreezeAndPriorExclusion", c2_ok, "; ".join(c2_msg))

    # C3: Manifest & Bounded Bundle + 9 Retroactive Bundles
    c3_ok = True
    c3_msg = []
    try:
        man = _read_json(ws / "FULL_D103_INPUT_MANIFEST.json")
        assert int(man["expected_observations"]) == 104
        assert int(man["valid_observations"]) == 104
        assert int(man["failed_observations"]) == 0
        assert int(man["valid_physical_files"]) == 204
        bpath = ws / "bounded_inputs/d103_bounded_bundle.json.gz"
        bsz = bpath.stat().st_size
        assert 1024 < bsz <= BUNDLE_CAP_BYTES, f"bundle size {bsz} > {BUNDLE_CAP_BYTES}"
        bsha = _sha256(bpath)
        assert bsha == summary["cohort"]["bounded_bundle_sha256"], "bundle sha mismatch vs SUMMARY"
        with gzip.open(bpath, "rb") as gz:
            bundle = json.loads(gz.read().decode("utf-8"))
        ex_q = bundle.get("excluded_quality_observations", [])
        assert len(bundle.get("exposures", [])) == 103, f"bundle exposures={len(bundle.get('exposures', []))}"
        assert len(ex_q) == 1, f"excluded_quality_observations={len(ex_q)}"
        assert len(bundle.get("exposures", [])) + len(ex_q) == 104
        retro = sources.get("retroactive_companion_archives", [])
        assert len(retro) == 9, f"retro archives count={len(retro)}"
        for ra in retro:
            zp = archives_dir / ra["name"]
            assert zp.exists(), f"missing {zp.name}"
            assert _sha256(zp) == ra["sha256"], f"zip sha mismatch {zp.name}"
            with zipfile.ZipFile(zp, "r") as zf:
                mem_sha = hashlib.sha256(zf.read(ra["bundle_member"])).hexdigest()
                assert mem_sha == ra["bundle_sha256"], f"member sha mismatch {ra['bundle_member']}"
        c3_msg.append(f"dl=104/104 (204 files), analyzed=103 (+1 quality excl), bundle={bsz/1048576:.2f}MiB <= 18.5MiB, retro_bundles=9/9")
    except Exception as exc:
        c3_ok = False
        c3_msg.append(str(exc))
    add_check("C3_ManifestAndBoundedBundle", c3_ok, "; ".join(c3_msg))

    # C4: 15-Suite Synthetic Calibration (3,111 Trials; 54,528 Cumulative)
    c4_ok = True
    c4_msg = []
    try:
        tot_t = tot_p = 0
        for nm, exp_n, min_p in CALIBRATION_SUITES_D103:
            rows = _read_csv(res / f"{nm}.csv")
            assert len(rows) == exp_n, f"{nm}: rows={len(rows)} != {exp_n}"
            p = sum(int(r["passed"]) for r in rows)
            assert p >= min_p and p / exp_n >= 0.95, f"{nm}: {p}/{exp_n} below threshold {min_p}"
            tot_t += exp_n
            tot_p += p
        assert tot_t == 3111
        cal_band = _read_csv(res / "CALIBRATION_COMPLETENESS_BY_BAND.csv")
        assert len(cal_band) >= 15
        assert int(syn["total_calibration_trials_d079_d103"]) == 54528
        c4_msg.append(f"suites=15/15, trials={tot_p}/{tot_t} ({100.0*tot_p/tot_t:.2f}%), cum=54528")
    except Exception as exc:
        c4_ok = False
        c4_msg.append(str(exc))
    add_check("C4_SyntheticCalibration15Suites", c4_ok, "; ".join(c4_msg))

    # C5: NuSTAR (19) & XMM-Newton RGS (26 dual-RGS analyzed) + 12.122 Unbroken High-Energy Octaves + 29.022 Total
    c5_ok = True
    c5_msg = []
    try:
        nu = _read_csv(res / "NUSTAR_HARD_XRAY_POISSON_19OBS.csv")
        xm = _read_csv(res / "XMM_NEWTON_RGS_26OBS.csv")
        sa = _read_json(res / "SPECTRAL_COVERAGE_AUDIT_D103.json")
        assert len(nu) == 19, f"nustar rows={len(nu)}"
        assert len(xm) == 26, f"xmm rows={len(xm)}"
        assert all(int(r["verified_eti"]) == 0 for r in nu + xm)
        assert min(float(r["e_min_kev"]) for r in nu) <= 3.01 and max(float(r["e_max_kev"]) for r in nu) >= 78.99
        he_iv = sa["high_energy_unbroken_um"]
        assert he_iv[0] <= 0.000016 and he_iv[1] >= 0.0699, f"he_iv={he_iv}"
        assert float(sa["high_energy_unbroken_octaves"]) >= 12.1, f"he_oct={sa['high_energy_unbroken_octaves']}"
        assert float(sa["total_octave_span"]) >= 29.0, f"tot_oct={sa['total_octave_span']}"
        c5_msg.append(f"NuSTAR=19, XMM_RGS=26, HE_oct={sa['high_energy_unbroken_octaves']}, tot_oct={sa['total_octave_span']}")
    except Exception as exc:
        c5_ok = False
        c5_msg.append(str(exc))
    add_check("C5_NuStarAndXmmRgsCoverage", c5_ok, "; ".join(c5_msg))

    # C6: ALMA Band 9 & Band 10 Complete 9-Band Closure (B1, B3-B10)
    c6_ok = True
    c6_msg = []
    try:
        al = _read_csv(res / "ALMA_B9_B10_CUBES_D103.csv")
        sa = _read_json(res / "SPECTRAL_COVERAGE_AUDIT_D103.json")
        assert len(al) == 20, f"alma rows={len(al)}"
        n_b9 = sum(1 for r in al if r["instrument"] == "ALMA_B9_0P4MM")
        n_b10 = sum(1 for r in al if r["instrument"] == "ALMA_B10_0P3MM")
        assert n_b9 == 10 and n_b10 == 10, f"B9={n_b9}, B10={n_b10}"
        assert sa["alma_bands_complete"] == ["B1", "B3", "B4", "B5", "B6", "B7", "B8", "B9", "B10"]
        assert all(int(r["verified_eti"]) == 0 for r in al)
        c6_msg.append(f"cubes=20 (B9={n_b9}, B10={n_b10}), bands=9/9 (B1,B3-B10), ETI=0")
    except Exception as exc:
        c6_ok = False
        c6_msg.append(str(exc))
    add_check("C6_AlmaB9B10UnbrokenClosure", c6_ok, "; ".join(c6_msg))

    # C7: DRIFT_V61 & COMB_DRIFT_V61 (60 Campaigns + Orbits #163-#168)
    c7_ok = True
    c7_msg = []
    try:
        o6 = _read_csv(res / "ORBITAL_CAMPAIGN_RESULTS_6_D103.csv")
        dr60 = _read_csv(res / "DRIFT_V61_ECCENTRIC_KEPLERIAN_60CAMPAIGNS.csv")
        cd60 = _read_csv(res / "COMB_DRIFT_V61_60CAMPAIGNS.csv")
        dkl = _read_csv(res / "DRIFT_V61_CANDIDATE_LEDGER.csv")
        ckl = _read_csv(res / "COMB_DRIFT_V61_CANDIDATE_LEDGER.csv")
        assert len(o6) == 6, f"o6={len(o6)}"
        assert [int(r["campaign_index"]) for r in o6] == [163, 164, 165, 166, 167, 168]
        assert len(dr60) == 60 and len(cd60) == 60
        assert [int(r["campaign_order"]) for r in dr60] == list(range(1, 61))
        assert [int(r["campaign_order"]) for r in cd60] == list(range(1, 61))
        assert all(int(r["stage2_verified_eti"]) == 0 for r in dr60 + cd60)
        assert all(int(r["verified_eti"]) == 0 for r in o6 + dkl + ckl)
        c7_msg.append(f"orbits=#163-#168, campaigns=60/60, dk_cands={len(dkl)}, comb_cands={len(ckl)}, ETI=0")
    except Exception as exc:
        c7_ok = False
        c7_msg.append(str(exc))
    add_check("C7_DriftV61AndCombDrift60Campaigns", c7_ok, "; ".join(c7_msg))

    # C8: ESO 4-Gen Optical & Cumulative All-Sky Comb
    c8_ok = True
    c8_msg = []
    try:
        fg = _read_csv(res / "FOUR_GEN_BENCHMARK_D103.csv")
        acu = _read_csv(res / "ALLSKY_COMB_V4_1_UNIFIED_D079_D103.csv")
        acc = _read_csv(res / "ALLSKY_COMB_V4_1_CANDIDATES_D079_D103.csv")
        assert len(fg) == 2, f"fg rows={len(fg)}"
        assert len(acu) >= 200 and len(acu) == int(syn["cumulative_comb_stacks"]), f"comb stacks {len(acu)} vs {syn['cumulative_comb_stacks']}"
        assert all(int(r["verified_eti_combs"]) == 0 for r in acu)
        assert all(int(r["stage2_verified_eti"]) == 0 for r in fg)
        assert int(summary["raw_hits_and_triage"]["comb_verified_eti"]) == 0
        c8_msg.append(f"fg={len(fg)} instruments, comb_stacks={len(acu)}, comb_cands={len(acc)}, ETI=0")
    except Exception as exc:
        c8_ok = False
        c8_msg.append(str(exc))
    add_check("C8_AllskyCombAndFourGenOptics", c8_ok, "; ".join(c8_msg))

    # C9: Candidate Ledgers & Strict Zero Verified ETI
    c9_ok = True
    c9_msg = []
    try:
        vl = _read_csv(res / "V6_1_CANDIDATE_LEDGER.csv")
        sl = _read_csv(res / "V6_1_SPACE_CANDIDATE_LEDGER.csv")
        pv = _read_csv(res / "EXPOSURE_PROVENANCE_D103.csv")
        assert len(pv) == 103, f"prov={len(pv)}"
        assert all(int(r["verified_eti"]) == 0 for r in vl + sl)
        for r in vl + sl:
            if r["qualified_v61"] == "True":
                assert r["stage2_triage_status"].startswith("STAGE2_VETO_"), f"unvetoed qualified hit: {r}"
        assert int(summary["raw_hits_and_triage"]["verified_eti_detections_total"]) == 0
        c9_msg.append(f"v61_cands={len(vl)}, space_cands={len(sl)}, prov={len(pv)}/103, ETI=0")
    except Exception as exc:
        c9_ok = False
        c9_msg.append(str(exc))
    add_check("C9_CandidateLedgersAndZeroEti", c9_ok, "; ".join(c9_msg))

    # C10: Unified 709-Star Synthesis & 188 <10 pc Solar Neighborhood
    c10_ok = True
    c10_msg = []
    try:
        u709 = _read_csv(res / "UNIFIED_PANCHROMATIC_V6_1_SYNTHESIS_709STARS.csv")
        s188 = _read_csv(res / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_188STARS.csv")
        ell = _read_csv(res / "MULTIEVENT_ELLIPSOID_709STARS.csv")
        br = _read_csv(res / syn["panchromatic_bridge_filename"])
        assert len(u709) == 709 and len({r["star"] for r in u709}) == 709
        assert len(s188) == 188 and all(float(r["dist_pc"]) <= 10.0001 for r in s188)
        assert len(ell) == 709
        n_sci = sum(1 for r in u709 if r["role"] == "SCIENCE")
        n_ctrl = sum(1 for r in u709 if r["role"] == "CONTROL")
        assert n_sci == int(syn["science_stars_total"]) and n_ctrl == int(syn["control_stars_total"])
        assert int(syn["spectrographs"]) == 49 and int(syn["spectral_arms"]) == 79
        assert all(int(r["verified_eti_detections"]) == 0 for r in u709)
        c10_msg.append(f"unified={len(u709)} (Sci={n_sci}, Ctrl={n_ctrl}), <10pc={len(s188)}, bridge_cells={len(br)}, 49spec/79arms")
    except Exception as exc:
        c10_ok = False
        c10_msg.append(str(exc))
    add_check("C10_Unified709AndSolarNeighborhood188", c10_ok, "; ".join(c10_msg))

    # C11: Six Figures (fig109-fig114) & Visual Review Pass
    c11_ok = True
    c11_msg = []
    try:
        vr = _read_json(res / "VISUAL_REVIEW.json")
        assert vr.get("overall_status") == "PASS", f"visual review status={vr.get('overall_status')}"
        figs_vr = vr.get("figures", {})
        assert len(figs_vr) == 6, f"vr figures count={len(figs_vr)}"
        expected_figs = [
            "fig109_d103_nustar_hard_xray_poisson_3_79kev.png",
            "fig110_d103_xmm_newton_rgs_high_res_xray.png",
            "fig111_d103_alma_band9_band10_complete_closure.png",
            "fig112_d103_drift_v61_and_comb_60campaigns.png",
            "fig113_d103_global_29p02_octave_709star_frontier.png",
            "fig114_d103_panchromatic_bridge_and_709star_synthesis.png",
        ]
        for fn in expected_figs:
            fp = fig_dir / fn
            assert fp.exists() and fp.stat().st_size > 25000, f"bad figure {fn}"
            wh = _png_wh(fp)
            assert wh is not None and wh[0] >= 1200 and wh[1] >= 800, f"bad PNG header {fn}: {wh}"
            assert fn in figs_vr and figs_vr[fn].get("status") == "PASS", f"VISUAL_REVIEW missing/fail {fn}"
        c11_msg.append("6/6 PNGs verified (>25KiB, valid IHDR, VISUAL_REVIEW=PASS)")
    except Exception as exc:
        c11_ok = False
        c11_msg.append(str(exc))
    add_check("C11_VisualReviewAndSixFigures", c11_ok, "; ".join(c11_msg))

    # C12: Pure-Stdlib Radiometric Aperture Closure Across EIRP_UPPER_LIMITS + Bridge Table
    c12_ok = True
    c12_msg = []
    try:
        eirp_rows = _read_csv(res / "EIRP_UPPER_LIMITS_D103.csv")
        br_rows = _read_csv(res / syn["panchromatic_bridge_filename"])
        max_err = 0.0
        n_checked = 0
        for row in eirp_rows:
            d_cm = float(row["dist_pc"]) * PC_CM
            fl_cgs = float(row["flux_lim_erg_cm2_s"])
            wa = float(row["wave_bary_a"])
            l_iso_w = 4.0 * math.pi * (d_cm * d_cm) * fl_cgs * 1e-7
            theta = (math.pi * 10.0) / (wa * 1e-10)
            p_kw = (l_iso_w / (theta * theta)) / 1000.0
            rep = float(row["p_beam_10m_kw"])
            if rep > 0:
                max_err = max(max_err, abs(p_kw - rep) / rep)
                n_checked += 1
        for row in br_rows:
            if not row.get("flux_lim_erg_cm2_s") or not row.get("wave_A") or not row.get("p_beam_10m_kw"):
                continue
            d_cm = float(row["dist_pc"]) * PC_CM
            fl_cgs = float(row["flux_lim_erg_cm2_s"])
            wa = float(row["wave_A"])
            l_iso_w = 4.0 * math.pi * (d_cm * d_cm) * fl_cgs * 1e-7
            theta = (math.pi * 10.0) / (wa * 1e-10)
            p_kw = (l_iso_w / (theta * theta)) / 1000.0
            rep = float(row["p_beam_10m_kw"])
            if rep > 0:
                max_err = max(max_err, abs(p_kw - rep) / rep)
                n_checked += 1
        assert n_checked >= 1000 and max_err < 0.002, f"n={n_checked}, max_err={max_err}"
        c12_msg.append(f"rows_checked={n_checked}, max_rel_err={max_err:.10f} (<0.002)")
    except Exception as exc:
        c12_ok = False
        c12_msg.append(str(exc))
    add_check("C12_RadiometricApertureClosure", c12_ok, "; ".join(c12_msg))

    # C13: Results Report & Prose Hygiene
    c13_ok = True
    c13_msg = []
    try:
        rp = (ws / "RESULTS_REPORT.md").read_text(encoding="utf-8")
        for tok in ("D103", "V6.1", "709", "188", "NuSTAR", "XMM", "RGS", "ALMA", "Band 9", "Band 10", "0 verified ETI"):
            assert tok in rp, f"RESULTS_REPORT missing token {tok!r}"
        for bad in ("TODO", "TBD", "FIXME", "placeholder"):
            assert bad not in rp, f"RESULTS_REPORT contains banned token {bad!r}"
        c13_msg.append(f"len={len(rp)} chars, required tokens present, clean prose")
    except Exception as exc:
        c13_ok = False
        c13_msg.append(str(exc))
    add_check("C13_ResultsReportAndProseHygiene", c13_ok, "; ".join(c13_msg))

    # C14: SHA-256 Results Manifest
    c14_ok = True
    c14_msg = []
    try:
        rm = _read_json(ws / "RESULTS_MANIFEST_SHA256.json")
        files_rec = rm.get("files", {})
        actual = sorted(str(p.relative_to(ws)) for p in res.rglob("*") if p.is_file())
        recorded = sorted(files_rec.keys())
        assert actual == recorded, f"manifest mismatch: extra={set(actual)-set(recorded)}, missing={set(recorded)-set(actual)}"
        for rel, meta in files_rec.items():
            fp = ws / rel
            assert fp.stat().st_size == int(meta["bytes"]), f"bytes mismatch {rel}"
            assert _sha256(fp) == meta["sha256"], f"sha256 mismatch {rel}"
        c14_msg.append(f"verified={len(recorded)}/{len(recorded)} results & figure files")
    except Exception as exc:
        c14_ok = False
        c14_msg.append(str(exc))
    add_check("C14_Sha256ResultsManifest", c14_ok, "; ".join(c14_msg))

    # C15: Implementation Lock Integrity
    c15_ok = True
    c15_msg = []
    try:
        il = _read_json(ws / "IMPLEMENTATION_LOCK.json")
        il_files = il.get("files", {})
        req_scripts = ("v6_1_detector.py", "build_cohort.py", "download_inputs.py", "analyze.py", "plot_figures.py", "audit.py")
        for sc in req_scripts:
            assert sc in il_files, f"missing {sc} in IMPLEMENTATION_LOCK"
            fp = ws / sc
            assert _sha256(fp) == il_files[sc]["sha256"], f"script sha mismatch {sc}"
        c15_msg.append(f"verified={len(req_scripts)}/6 scripts in IMPLEMENTATION_LOCK")
    except Exception as exc:
        c15_ok = False
        c15_msg.append(str(exc))
    add_check("C15_ImplementationLockIntegrity", c15_ok, "; ".join(c15_msg))

    # C16: Pure Stdlib & Clean Workspace
    c16_ok = True
    c16_msg = []
    try:
        std_names = getattr(sys, "stdlib_module_names", None)
        non_std = []
        if std_names is not None:
            for m_name, mod in list(sys.modules.items()):
                top = m_name.split(".")[0]
                if top in ("__main__", "audit", "_frozen_importlib", "_frozen_importlib_external", "encodings", "codecs"):
                    continue
                if top.startswith("_"):
                    continue
                if top not in std_names:
                    mfile = getattr(mod, "__file__", "") or ""
                    if "site-packages" in mfile or "dist-packages" in mfile:
                        non_std.append(m_name)
        assert non_std == [], f"non_stdlib={non_std}"
        stray = [p.name for p in ws.iterdir() if p.name.startswith("tmp") or p.name.endswith(".tmp")]
        assert stray == [], f"stray tmp files={stray}"
        c16_msg.append(f"non_stdlib={non_std}, clean_ws=True")
    except Exception as exc:
        c16_ok = False
        c16_msg.append(str(exc))
    add_check("C16_PureStdlibAndCleanEnvironment", c16_ok, "; ".join(c16_msg))

    n_pass = sum(1 for c in checks if c["status"] == "PASS")
    return {
        "schema": "D103_AUDIT_V61",
        "phase_id": "D103",
        "workspace": str(ws),
        "archives_dir": str(archives_dir),
        "checks_passed": n_pass,
        "checks_total": len(checks),
        "overall_status": "PASS" if n_pass == len(checks) else "FAIL",
        "checks": checks,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent)
    ap.add_argument("--archives-dir", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[2] / "archives")
    ap.add_argument("--json-out", type=pathlib.Path, default=None)
    args = ap.parse_args()

    rep = run_audit(args.workspace.resolve(), args.archives_dir.resolve())
    for c in rep["checks"]:
        print(f"  [{c['status']}] {c['id']}: {c['detail']}")
    print(f"AUDIT D103 SUMMARY: {rep['checks_passed']}/{rep['checks_total']} {rep['overall_status']}")
    if args.json_out is not None:
        args.json_out.write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")
    return 0 if rep["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
