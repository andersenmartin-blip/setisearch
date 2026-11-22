#!/usr/bin/env python3
"""Pure-stdlib (C1-C16) independent cryptographic & scientific audit for Phase D099 (V5.7)."""

import argparse
import ast
import csv
import gzip
import hashlib
import json
import math
import pathlib
import sys
import zipfile

C12_PC_TO_CM = 3.085677581e18
C12_D_M_CM = 1000.0
METHOD_LOCK_SHA256 = "a7d41c95620b2f550767f9920438a7276db9232d9293d51b294e0df2bcba7bf0"
BUNDLE_SHA256 = "abbc808357061ae63a084b2e11b4f61771845d85117f4e712fd4316a8b87c8b4"
BUNDLE_BYTES = 11554273
BUNDLE_CAP_BYTES = int(18.5 * 1024 * 1024)

RETRO_ARCHIVES = [
    (
        "X",
        "SETI_D098_V5_6_SOFIA_GREAT_ISO_SWS_FORCAST_OPTICAL_JERK_RESULTS_2026-11-22.zip",
        "f57f48355df2b92257f39d76e83f2d850ae6d9164ea10ef1539bede1ca8fb838",
        "d098_bounded_bundle.json.gz",
        "468c3416778f37f335e990147dc3fecd41ae3281f64b6bbf9873dbe9b3396938",
    ),
    (
        "W",
        "SETI_D097_V5_5_HERSCHEL_THZ_FARIR_STIS_E140H_OPTICAL_JERK_RESULTS_2026-11-22.zip",
        "aa296f9c72faefcacbd4f4fedb73c7c3f2b1377823fad3e308fd6a9844f6fed8",
        "d097_bounded_bundle.json.gz",
        "05b9d096a76082f9b2bca30ab73a01329a20c1b40c651ce2a76bf0647626f41a",
    ),
    (
        "V",
        "SETI_D096_V5_4_SOFIA_EXES_MIDIR_ECHELLE_COHERENT_DRIFT_JWST_RESULTS_2026-11-21.zip",
        "a134e4d5d0b6e0cb4e17763dc729203218cac9265c7db75db719135cb01c5158",
        "d096_bounded_bundle.json.gz",
        "319f4cd7b6fe1bcc24f5bb74fc6a432019c0ed30a55d04f075b1c78fc9057e91",
    ),
    (
        "U",
        "SETI_D095_V5_3_CURVED_PERIODIC_DRIFT_GHOST_SPITZER_IRS_APOGEE2_RESULTS_2026-11-21.zip",
        "24f5a73a4299d697a198e91e3e15b5b7ddce838f6d055cebe66ddd812520c21d",
        "d095_bounded_bundle.json.gz",
        "db0ab9adc9f3067909af2cefafb9e0b56095d87107a9510a6cce0a9406ca59b8",
    ),
    (
        "T",
        "SETI_D094_V5_2_MULTIEPOCH_DRIFT_APOGEE2_CRIRESJH_MIRILRS_RESULTS_2026-11-21.zip",
        "fea863077ae837b6741d5837990fd357158e00f6a5e3d9adde51f0c81e8ccefc",
        "d094_bounded_bundle.json.gz",
        "d6601113eec302bfb393874ffb48d32aa90d073f4bae7b6b37e256ad0cb89c42",
    ),
]


def _sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1 << 20)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _read_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _median(vals):
    s = sorted(vals)
    n = len(s)
    mid = n // 2
    if n % 2 == 1:
        return s[mid]
    return 0.5 * (s[mid - 1] + s[mid])


def _resolve_archives_dir(ws, explicit):
    candidates = []
    if explicit is not None:
        candidates.append(explicit)
    candidates.extend([
        ws.parent.parent / "archives",
        ws.parent / "archives",
        ws / "archives",
        pathlib.Path("/home/martin/SETI_Fortsaettelse_2026-11-14/archives"),
    ])
    for cand in candidates:
        if cand is not None and cand.is_dir():
            if all((cand / row[1]).is_file() for row in RETRO_ARCHIVES):
                return cand
    for cand in candidates:
        if cand is not None and cand.is_dir():
            return cand
    return ws.parent.parent / "archives"


def _c12_pkw(dist_pc, flux_lim, wave_a):
    l_iso_mw = 4.0 * math.pi * ((dist_pc * C12_PC_TO_CM) ** 2) * flux_lim * 1e-7 / 1e6
    gain = (math.pi * C12_D_M_CM / (wave_a * 1e-8)) ** 2
    return (l_iso_mw * 1e3) / gain


def run_audit(ws, archives_dir=None):
    res = ws / "results"
    arch_dir = _resolve_archives_dir(ws, archives_dir)
    results = []

    def rec(cid, ok, msg):
        results.append((cid, bool(ok), msg))
        status = "PASS" if ok else "FAIL"
        print(f"[{cid}] {status}: {msg}")

    # C1: Stage-1 Prospective Seal & Lock Invariance
    lr_path = ws / "LOCK_RECEIPT.json"
    ml_path = ws / "METHOD_LOCK.json"
    fdr_path = ws / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json"
    lr = _read_json(lr_path)
    fdr = _read_json(fdr_path)
    ml_hash = _sha256_file(ml_path)
    lr_hash = _sha256_file(lr_path)
    locked_s1 = lr.get("locked_files", {})
    diffs_s1 = [
        rel
        for rel, h in locked_s1.items()
        if not (ws / rel).is_file() or _sha256_file(ws / rel) != h
    ]
    c1_ok = (
        lr.get("phase_id") == "D099"
        and lr.get("inputs_dir_exists_at_seal") is False
        and ml_hash == METHOD_LOCK_SHA256
        and lr.get("method_lock_sha256") == METHOD_LOCK_SHA256
        and len(locked_s1) == 7
        and len(diffs_s1) == 0
        and float(fdr.get("chronology_lag_seconds", -1.0)) > 0.0
        and fdr.get("lock_receipt_sha256") == lr_hash
        and fdr.get("method_lock_sha256") == METHOD_LOCK_SHA256
    )
    rec(
        "C1",
        c1_ok,
        f"METHOD_LOCK 7/7 Stage-1 diffs={len(diffs_s1)}, lag={fdr.get('chronology_lag_seconds')}s",
    )

    # C2: Prior Exclusion & Spatial Uniqueness
    pe = _read_json(ws / "PRIOR_EXCLUSION_VERIFICATION.json")
    cohort = _read_csv(ws / "FROZEN_COHORT_D099.csv")
    cohort_stars = {r["canonical_target"] for r in cohort}
    c2_ok = (
        pe.get("n_prior_excluded_coords") == 539
        and pe.get("n_prior_excluded_dp_ids") == 2983
        and pe.get("d099_dp_id_overlap_count") == 0
        and float(pe.get("min_brand_new_sky_separation_arcsec", 0.0)) >= 1660.0
        and float(pe.get("min_intra_d099_separation_arcsec", 0.0)) >= 6668.0
        and len(cohort) == 97
        and len(cohort_stars) == 60
    )
    rec(
        "C2",
        c2_ok,
        f"prior={pe.get('n_prior_excluded_coords')} coords/{pe.get('n_prior_excluded_dp_ids')} dp_ids, overlap={pe.get('d099_dp_id_overlap_count')}, unique_stars={len(cohort_stars)}",
    )

    # C3: Cohort & Provenance Closure + Bounded Bundle
    ep = _read_csv(res / "EXPOSURE_PROVENANCE_D099.csv")
    tot_h = sum(float(r["t_exptime_s"]) for r in ep) / 3600.0
    gz = ws / "bounded_inputs/d099_bounded_bundle.json.gz"
    gz_bytes = gz.stat().st_size if gz.is_file() else -1
    gz_sha = _sha256_file(gz) if gz.is_file() else ""
    gz_ok = False
    if gz.is_file():
        with gzip.open(gz, "rt", encoding="utf-8") as gf:
            bundle_obj = json.load(gf)
        gz_ok = isinstance(bundle_obj, dict) and bundle_obj.get("phase_id") == "D099"
    c3_ok = (
        len(cohort) == 97
        and len(cohort_stars) == 60
        and len(ep) == 97
        and gz_bytes == BUNDLE_BYTES
        and gz_bytes <= BUNDLE_CAP_BYTES
        and gz_sha == BUNDLE_SHA256
        and gz_ok
    )
    rec(
        "C3",
        c3_ok,
        f"60 stars, {len(ep)} exp ({tot_h:.4f}h), bundle={gz_bytes} B (<=18.5 MiB), sha={gz_sha[:12]}",
    )

    # C4: 2,151-Trial 11-Suite Calibration Scorecard
    suites = [
        ("CALIBRATION_V57_JCMT_MM_180.csv", 180, 180, lambda r: r["passed"] == "1"),
        ("CALIBRATION_V57_SOFIA_EXES_180.csv", 179, 180, lambda r: r["passed"] == "1"),
        ("CALIBRATION_V57_IRTF_SPEX_180.csv", 180, 180, lambda r: r["passed"] == "1"),
        ("CALIBRATION_V57_KEPLERIAN_JERK_300.csv", 300, 300, lambda r: r["passed"] == "1"),
        ("CALIBRATION_G8_V57_120.csv", 117, 120, lambda r: r["passed"] == "1"),
        ("CALIBRATION_V57_RPCA_RARITY_180.csv", 179, 180, lambda r: r["passed"] == "1"),
        ("CALIBRATION_V57_AGNOSTIC_120.csv", 120, 120, lambda r: r["passed"] == "1"),
        ("DETECTOR_V57_G4G5_CALIBRATION_108.csv", 108, 108, lambda r: r["passed"] == "1"),
        ("INJECTION_RECOVERY_540.csv", 538, 540, lambda r: r["pass_p"] == "1"),
        ("COMB_V4_1_CALIBRATION_162.csv", 161, 162, lambda r: r["passed"] == "1"),
        (
            "KEPLERIAN_TRACK_CALIBRATION_81.csv",
            81,
            81,
            lambda r: r["tdiff_fa"] == "0" and r["kplanet_rec"] == "1",
        ),
    ]
    tot_passed = 0
    tot_trials = 0
    cal_ok = True
    for fn, exp_p, exp_t, pred in suites:
        rows = _read_csv(res / fn)
        n_t = len(rows)
        n_p = sum(1 for r in rows if pred(r))
        if n_t != exp_t or n_p != exp_p:
            cal_ok = False
        tot_passed += n_p
        tot_trials += n_t
    k300 = _read_csv(res / "CALIBRATION_V57_KEPLERIAN_JERK_300.csv")
    mr = [r for r in k300 if r.get("class") == "MULTI_REV_KEPLERIAN_2_10YR"]
    mr_kep = sum(1 for r in mr if r["passed"] == "1")
    mr_tay = sum(1 for r in mr if r["taylor_only_obs"] == "1")
    c4_ok = cal_ok and tot_trials == 2151 and tot_passed == 2143 and mr_kep == 60 and mr_tay == 36
    rec(
        "C4",
        c4_ok,
        f"{tot_passed}/{tot_trials} trials across 11 V5.7 suites (multi-rev Keplerian {mr_kep}/60 vs Taylor {mr_tay}/60)",
    )

    # C5: Stream 1A JCMT Millimeter/Submm Heterodyne
    jcmt = _read_csv(res / "JCMT_MM_HETERODYNE_18STARS.csv")
    j_by = {r["star"]: r for r in jcmt}
    j_cubes = sum(int(r["n_cubes"]) for r in jcmt)
    j_raw = sum(int(r["raw_peaks"]) for r in jcmt)
    j_eti = sum(int(r["stage2_verified_eti"]) for r in jcmt)
    c5_ok = (
        len(jcmt) == 18
        and j_cubes == 23
        and j_raw == 23
        and j_eti == 0
        and abs(float(j_by["LKCA15"]["best_p_beam_10m_kw"]) - 2040500.05755668) < 0.01
        and abs(float(j_by["HD163296"]["best_p_beam_10m_kw"]) - 4222791.0855968) < 0.01
    )
    rec(
        "C5",
        c5_ok,
        f"JCMT {len(jcmt)} stars/{j_cubes} cubes, {j_raw} raw->{j_eti} ETI, HARP best={float(j_by['LKCA15']['best_p_beam_10m_kw']):.2f} kW, 230GHz best={float(j_by['HD163296']['best_p_beam_10m_kw']):.2f} kW",
    )

    # C6: Stream 1B/1C SOFIA_EXES & IRTF_SPEX + Space/mm/IR Ledger
    exes = _read_csv(res / "SOFIA_EXES_MIDIR_13STARS.csv")
    spex = _read_csv(res / "IRTF_SPEX_NIR_26STARS.csv")
    sled = _read_csv(res / "V5_7_SPACE_CANDIDATE_LEDGER.csv")
    e_by = {r["star"]: r for r in exes}
    s_by = {r["star"]: r for r in spex}
    e_raw = sum(int(r["raw_peaks"]) for r in exes)
    s_raw = sum(int(r["raw_peaks"]) for r in spex)
    c6_ok = (
        len(exes) == 13
        and e_raw == 88
        and sum(int(r["stage2_verified_eti"]) for r in exes) == 0
        and len(spex) == 26
        and s_raw == 1
        and sum(int(r["stage2_verified_eti"]) for r in spex) == 0
        and len(sled) == 112
        and abs(float(e_by["MUUMA"]["best_p_beam_10m_kw"]) - 33883.11020633) < 0.01
        and abs(float(s_by["DXCNC"]["best_p_beam_10m_kw"]) - 57.04399686) < 0.01
    )
    rec(
        "C6",
        c6_ok,
        f"EXES 13 stars ({e_raw}->0, MUUMA={float(e_by['MUUMA']['best_p_beam_10m_kw']):.2f} kW); SpeX 26 stars ({s_raw}->0, DXCNC={float(s_by['DXCNC']['best_p_beam_10m_kw']):.2f} kW); SpaceLedger={len(sled)}->0",
    )

    # C7: Stream 2 ESO Optical 4-Gen, Orbits #144-#145, & Empirical RVs
    fg = _read_csv(res / "FOUR_GEN_BENCHMARK_D099.csv")
    orb = _read_csv(res / "ORBITAL_CAMPAIGN_RESULTS_2.csv")
    rvs = _read_csv(res / "STAR_RV_SUMMARY_D099.csv")
    vled = _read_csv(res / "V5_7_CANDIDATE_LEDGER.csv")
    eirp = _read_csv(res / "EIRP_UPPER_LIMITS_D099.csv")
    fg_g1 = sum(int(r["g1_seeds"]) for r in fg)
    fg_g8 = sum(int(r["g8_pass"]) for r in fg)
    fg_eti = sum(int(r["stage2_verified_eti"]) for r in fg)
    orb_ids = sorted(int(r["campaign_index"]) for r in orb)
    min_uves = min(float(r["p_beam_10m_kw"]) for r in eirp if r["instrument"] == "ESO_UVES")
    min_harps = min(float(r["p_beam_10m_kw"]) for r in eirp if r["instrument"] == "ESO_HARPS")
    c7_ok = (
        fg_g1 == 11
        and fg_g8 == 0
        and fg_eti == 0
        and orb_ids == [144, 145]
        and all(int(r["verified_eti"]) == 0 for r in orb)
        and len(rvs) == 6
        and all(math.isfinite(float(r["rv_median_kms"])) for r in rvs)
        and len(vled) == 0
        and abs(min_uves - 40.18792826) < 0.01
        and abs(min_harps - 104.46713649) < 0.01
    )
    rec(
        "C7",
        c7_ok,
        f"ESO 4-Gen 11->{fg_g8}->0; Orbits #144-#145=0; 6 RVs finite; UVES={min_uves:.2f} kW, HARPS={min_harps:.2f} kW",
    )

    # C8: Stream 3 DRIFT_V57 36-Campaign Coherent Keplerian + 3D Jerk Search
    d36 = _read_csv(res / "DRIFT_V57_KEPLERIAN_JERK_36CAMPAIGNS.csv")
    r30 = _read_csv(res / "RETROACTIVE_D094_D098_KEPLERIAN_JERK.csv")
    kled = _read_csv(res / "DRIFT_V57_KEPLERIAN_CANDIDATE_LEDGER.csv")
    tot_ep = sum(int(r["n_epochs"]) for r in d36)
    tot_traj = sum(int(r["n_trajectories_evaluated"]) for r in d36)
    tot_px = sum(int(r["n_pixel_trajectory_integrals"]) for r in d36)
    tot_raw = sum(int(r["raw_coherent_survivors"]) for r in d36)
    tot_eti = sum(int(r["stage2_verified_eti"]) for r in d36)
    c8_ok = (
        len(d36) == 36
        and len(r30) == 30
        and tot_ep == 323
        and tot_traj == 56270
        and tot_px == 3566447968
        and tot_raw == 10852
        and len(kled) == 10852
        and tot_eti == 0
        and all(str(r["verified_eti"]).strip().lower() in ("0", "false") for r in kled)
    )
    rec(
        "C8",
        c8_ok,
        f"36 campaigns (30 retro), {tot_traj} traj, {tot_px:,} px, {tot_raw}->0 ETI",
    )

    # C9: Retroactive Companion Archives X/W/V/U/T + Internal Bundles SHA-256
    c9_ok = True
    c9_notes = []
    for code, fname, exp_asha, bname, exp_bsha in RETRO_ARCHIVES:
        ap = arch_dir / fname
        if not ap.is_file():
            c9_ok = False
            c9_notes.append(f"{code}=MISSING")
            continue
        asha = _sha256_file(ap)
        b_found = False
        bsha = ""
        with zipfile.ZipFile(ap, "r") as zf:
            for zn in zf.namelist():
                if zn.endswith("/" + bname) or zn == bname:
                    bsha = _sha256_bytes(zf.read(zn))
                    b_found = True
                    break
        ok_one = asha == exp_asha and b_found and bsha == exp_bsha
        if not ok_one:
            c9_ok = False
        c9_notes.append(f"{code}={'OK' if ok_one else 'DIFF'}")
    rec("C9", c9_ok, f"Archives X/W/V/U/T + internal bundles ({', '.join(c9_notes)})")

    # C10: Stream 4 Unified 516-Star Panchromatic V5.7 Synthesis
    summ = _read_json(res / "SUMMARY.json")
    u516 = _read_csv(res / "UNIFIED_PANCHROMATIC_V5_7_SYNTHESIS_516STARS.csv")
    s175 = _read_csv(res / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_175STARS.csv")
    br71 = _read_csv(res / "PANCHROMATIC_BRIDGE_71STARS_V57.csv")
    u_sci = sum(1 for r in u516 if r["role"] == "SCIENCE")
    u_ctl = sum(1 for r in u516 if r["role"] == "CONTROL")
    u_hosts = sum(1 for r in u516 if int(float(r["n_exoplanets"] or 0)) > 0)
    u_pl = sum(int(float(r["n_exoplanets"] or 0)) for r in u516)
    vals_10pc = [float(r["min_panchromatic_10m_kw"]) for r in s175 if r["min_panchromatic_10m_kw"].strip()]
    med_10pc = _median(vals_10pc)
    br_stars = len({r["star"] for r in br71})
    syn = summ.get("unified_516star_panchromatic_v5_7_synthesis", {})
    c10_ok = (
        len(u516) == 516
        and u_sci == 399
        and u_ctl == 117
        and u_hosts == 214
        and u_pl == 411
        and len(s175) == 175
        and len(vals_10pc) == 153
        and abs(med_10pc - 1.4627) < 0.001
        and br_stars == 71
        and len(br71) == 827
        and syn.get("spectrographs") == 36
        and syn.get("spectral_arms") == 57
        and abs(float(syn.get("max_wave_um", 0.0)) - 1401.36089) < 1e-4
        and abs(float(syn.get("octave_span", 0.0)) - 13.919) < 1e-3
        and syn.get("verified_eti_detections_total") == 0
    )
    rec(
        "C10",
        c10_ok,
        f"516 stars ({u_sci}/{u_ctl}, {u_hosts}/{u_pl}), 175 <10pc ({med_10pc:.4f} kW), {br_stars} bridges/{len(br71)} cells, 36/57, {syn.get('octave_span')} oct",
    )

    # C11: COMB_V4_1, Multievent Ellipsoid, & Agnostic Closure
    comb_s = _read_csv(res / "COMB_V4_1_STAR_RESULTS_D099.csv")
    comb_u = _read_csv(res / "ALLSKY_COMB_V4_1_UNIFIED_D079_D099.csv")
    ellip = _read_csv(res / "MULTIEVENT_ELLIPSOID_516STARS.csv")
    agn = _read_csv(res / "V5_7_AGNOSTIC_MULTISCALE_SURVIVORS.csv")
    n_cfg = sum(int(r["n_comb_configs"]) for r in comb_s)
    etz = sum(1 for r in ellip if r["etz_qualified"] in ("1", "True", "true"))
    e180 = sum(1 for r in ellip if r["ellipsoid_qualified_180d"] in ("1", "True", "true"))
    c11_ok = (
        n_cfg == 1548664
        and sum(int(r["verified_eti_combs"]) for r in comb_s) == 0
        and len(comb_u) == 464
        and sum(int(r["verified_eti_combs"]) for r in comb_u) == 0
        and len(ellip) == 516
        and etz == 48
        and e180 == 36
        and len(agn) == 281
        and all(math.isfinite(float(r["z_multi"])) and abs(float(r["z_multi"])) > 0.0 for r in agn)
        and summ.get("raw_hits_and_triage", {}).get("verified_eti_detections_total") == 0
    )
    rec(
        "C11",
        c11_ok,
        f"{n_cfg:,} comb configs->0 ({len(comb_u)} stacks); Ellipsoid=516 ({etz} ETZ, {e180}<=180d); Agnostic={len(agn)}->0",
    )

    # C12: Radiometric Consistency Across D099 (165) & Bridge (813 non-empty) Rows
    mre_d099 = 0.0
    for r in eirp:
        pkw = _c12_pkw(float(r["dist_pc"]), float(r["flux_lim_erg_cm2_s"]), float(r["wave_bary_a"]))
        ref = float(r["p_beam_10m_kw"])
        mre_d099 = max(mre_d099, abs(pkw - ref) / max(ref, 1e-30))
    mre_br = 0.0
    nonempty_br = [r for r in br71 if r.get("flux_lim_erg_cm2_s", "").strip() != ""]
    for r in nonempty_br:
        pkw = _c12_pkw(float(r["dist_pc"]), float(r["flux_lim_erg_cm2_s"]), float(r["wave_A"]))
        ref = float(r["p_beam_10m_kw"])
        mre_br = max(mre_br, abs(pkw - ref) / max(ref, 1e-30))
    mre = max(mre_d099, mre_br)
    c12_ok = len(eirp) == 165 and len(nonempty_br) == 813 and mre < 0.002
    rec(
        "C12",
        c12_ok,
        f"{len(eirp)}+{len(nonempty_br)}={len(eirp) + len(nonempty_br)} EIRP rows consistent, max_rel_err={mre:.10f} < 0.002",
    )

    # C13: Results Manifest & Implementation Lock
    man = _read_json(ws / "RESULTS_MANIFEST_SHA256.json")
    ilock = _read_json(ws / "IMPLEMENTATION_LOCK.json")
    man_files = man.get("files", {})
    actual_res_files = sorted(
        p.relative_to(res).as_posix() for p in res.rglob("*") if p.is_file()
    )
    man_diffs = [
        rel
        for rel, meta in man_files.items()
        if not (res / rel).is_file()
        or _sha256_file(res / rel) != meta["sha256"]
        or (res / rel).stat().st_size != meta["bytes"]
    ]
    extra_res = sorted(set(actual_res_files) - set(man_files.keys()))
    il_files = ilock.get("locked_files", {})
    il_diffs = [
        rel
        for rel, h in il_files.items()
        if not (ws / rel).is_file() or _sha256_file(ws / rel) != h
    ]
    c13_ok = (
        len(man_files) == 46
        and len(man_diffs) == 0
        and len(extra_res) == 0
        and len(il_files) >= 14
        and len(il_diffs) == 0
    )
    rec(
        "C13",
        c13_ok,
        f"manifest={len(man_files)} files (diffs={len(man_diffs)}, extra={len(extra_res)}), impl_lock={len(il_files)} files (diffs={len(il_diffs)})",
    )

    # C14: 6/6 Visual Figures & Review Verification
    vr = _read_json(ws / "VISUAL_REVIEW.json")
    vr_figs = vr.get("figures_reviewed", [])
    png_ok = True
    for item in vr_figs:
        fp = ws / item["filename"]
        if not fp.is_file() or fp.stat().st_size != item["bytes"]:
            png_ok = False
            continue
        with open(fp, "rb") as pf:
            if pf.read(8) != b"\x89PNG\r\n\x1a\n":
                png_ok = False
    c14_ok = vr.get("status") == "PASS (6/6)" and len(vr_figs) == 6 and png_ok
    rec("C14", c14_ok, f"VISUAL_REVIEW {vr.get('status')} with {len(vr_figs)}/6 verified PNG headers & bytes")

    # C15: Documentation & SOURCES Provenance
    rep = (ws / "RESULTS_REPORT.md").read_text(encoding="utf-8")
    src_j = _read_json(res / "SOURCES.json")
    n_src_exp = len(src_j.get("exposures", []))
    c15_ok = (
        len(rep) > 1000
        and "516" in rep
        and "13.919" in rep
        and "1,401.36" in rep
        and "71" in rep
        and n_src_exp == 97
    )
    rec("C15", c15_ok, f"RESULTS_REPORT.md ({len(rep)} chars) + SOURCES.json ({n_src_exp} exposures)")

    # C16: Pure-Stdlib Purity Gate on audit.py Itself
    tree = ast.parse(pathlib.Path(__file__).read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    non_stdlib = sorted(m for m in imported if m not in sys.stdlib_module_names)
    c16_ok = len(non_stdlib) == 0
    rec("C16", c16_ok, f"Pure stdlib check imports={sorted(imported)}, non_stdlib={non_stdlib}")

    n_pass = sum(1 for _, ok, _ in results if ok)
    n_tot = len(results)
    print(f"SUMMARY: {n_pass}/{n_tot} PASSED")
    return n_pass, n_tot


def main():
    ap = argparse.ArgumentParser(description="Phase D099 pure-stdlib C1-C16 audit")
    ap.add_argument("--workspace", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent)
    ap.add_argument("--archives-dir", type=pathlib.Path, default=None)
    args = ap.parse_args()
    n_pass, n_tot = run_audit(args.workspace.resolve(), args.archives_dir)
    return 0 if n_pass == n_tot else 1


if __name__ == "__main__":
    raise SystemExit(main())
