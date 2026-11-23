#!/usr/bin/env python3
"""Pure-stdlib (C1-C16) independent cryptographic & scientific audit for Phase D101 (V5.9)."""

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
METHOD_LOCK_SHA256 = "78a2bc7979339b8fba7c45462de6933af3d49e2b3eaab6524c940ff39b927b66"
BUNDLE_SHA256 = "f3735b57ef170c3162fad61a825fad086c768e1a6662d48d3a4637c5eea51ec4"
BUNDLE_BYTES = 14562159
BUNDLE_CAP_BYTES = int(18.5 * 1024 * 1024)

RETRO_ARCHIVES = [
    (
        "Z",
        "SETI_D100_V5_8_JCMT_3MM_SOFIA_FIFILS_IUE_ECCENTRIC_KEPLERIAN_RESULTS_2026-11-22.zip",
        "f8900c1aee6db352b6317c1dd6bf308d286bab2c0c0b367e8863383438446bd2",
        "d100_bounded_bundle.json.gz",
        "4923b95a95da48ce036e1adbfa0402f0023afa23db32e874c3079083077b036d",
    ),
    (
        "Y",
        "SETI_D099_V5_7_JCMT_MM_SOFIA_EXES_IRTF_SPEX_KEPLERIAN_DRIFT_RESULTS_2026-11-22.zip",
        "77b187f3509a704978096c14b97f83a13d3eebb6b2fc9d53a8c3b296b362df0b",
        "d099_bounded_bundle.json.gz",
        "abbc808357061ae63a084b2e11b4f61771845d85117f4e712fd4316a8b87c8b4",
    ),
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

    # C1: Stage-1 Prospective Seal & Chronology Verification
    lr = _read_json(ws / "LOCK_RECEIPT.json")
    fdr = _read_json(ws / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json")
    ml_hash = _sha256_file(ws / "METHOD_LOCK.json")
    locked_s1 = lr.get("locked_files", {})
    diffs_s1 = [
        rel
        for rel, h in locked_s1.items()
        if not (ws / rel).is_file() or _sha256_file(ws / rel) != h
    ]
    c1_ok = (
        lr.get("phase_id") == "D101"
        and lr.get("inputs_dir_exists_at_seal") is False
        and ml_hash == METHOD_LOCK_SHA256
        and lr.get("method_lock_sha256") == METHOD_LOCK_SHA256
        and len(locked_s1) == 7
        and len(diffs_s1) == 0
        and fdr.get("phase_id") == "D101"
        and float(fdr.get("first_download_unix_epoch", 0.0)) - float(lr.get("locked_unix_epoch", 0.0)) >= 3.0
        and float(fdr.get("chronology_lag_seconds", -1.0)) >= 3.0
    )
    rec("C1", c1_ok, f"METHOD_LOCK 7/7 Stage-1 diffs={len(diffs_s1)}, lag={fdr.get('chronology_lag_seconds')}s")

    # C2: Full Input Manifest & Transparent SODA Exclusion
    man_in = _read_json(ws / "FULL_D101_INPUT_MANIFEST.json")
    valid_entries = [e for e in man_in.get("files", []) if e.get("status") in ("DOWNLOADED", "CACHED")]
    c2_ok = (
        man_in.get("phase_id") == "D101"
        and man_in.get("expected_files") == 102
        and man_in.get("downloaded_valid_files") == 101
        and len(valid_entries) == 101
        and man_in.get("error_count") == 1
        and any("NGC4038GAL" in str(err) and "400" in str(err) for err in man_in.get("errors", []))
        and man_in.get("total_bytes") == 3811417920
    )
    rec("C2", c2_ok, f"101/102 valid FITS ({man_in.get('total_bytes'):,} B), 1 SODA HTTP 400 exclusion (NGC4038GAL)")

    # C3: Bounded Bundle Size, Hash, & Provenance Closure
    ep = _read_csv(res / "EXPOSURE_PROVENANCE_D101.csv")
    tot_h = sum(float(r["t_exptime_s"]) for r in ep) / 3600.0
    gz = ws / "bounded_inputs/d101_bounded_bundle.json.gz"
    gz_bytes = gz.stat().st_size if gz.is_file() else -1
    gz_sha = _sha256_file(gz) if gz.is_file() else ""
    gz_ok = False
    if gz.is_file():
        with gzip.open(gz, "rt", encoding="utf-8") as gf:
            bundle_obj = json.load(gf)
        gz_ok = isinstance(bundle_obj, dict) and bundle_obj.get("phase_id") == "D101" and bundle_obj.get("n_exposures") == 101
    ep_stars = {r["star"] for r in ep}
    c3_ok = (
        len(ep) == 101
        and len(ep_stars) == 67
        and abs(tot_h - 202.8665) < 0.01
        and gz_bytes == BUNDLE_BYTES
        and gz_bytes <= BUNDLE_CAP_BYTES
        and gz_sha == BUNDLE_SHA256
        and gz_ok
    )
    rec("C3", c3_ok, f"67 stars, 101 exp ({tot_h:.4f}h), bundle={gz_bytes} B (<=18.5 MiB), sha={gz_sha[:12]}")

    # C4: Prior Exclusion & Spatial Separation Integrity
    pe = _read_json(ws / "PRIOR_EXCLUSION_VERIFICATION.json")
    cohort = _read_csv(ws / "FROZEN_COHORT_D101.csv")
    cohort_stars = {r["canonical_target"] for r in cohort}
    c4_ok = (
        pe.get("n_prior_excluded_coords") == 632
        and pe.get("n_prior_excluded_dp_ids") == 3159
        and pe.get("d101_dp_id_overlap_count") == 0
        and float(pe.get("min_brand_new_sky_separation_arcsec", 0.0)) >= 547.0
        and float(pe.get("min_intra_d101_separation_arcsec", 0.0)) >= 531.0
        and len(cohort) == 102
        and len(cohort_stars) == 68
    )
    rec("C4", c4_ok, f"prior=632 coords/3,159 dp_ids, overlap=0, min_sep={pe.get('min_brand_new_sky_separation_arcsec')} arcsec")

    # C5: 11-Suite 2,271-Trial Calibration Scorecard
    suites = [
        ("CALIBRATION_V59_ALMA_INTERFEROMETRIC_240.csv", 240, 240),
        ("CALIBRATION_V59_DRIFTING_COMB_240.csv", 240, 240),
        ("CALIBRATION_V58_ECCENTRIC_KEPLERIAN_360.csv", 359, 360),
        ("CALIBRATION_V58_G6_COINCIDENCE_120.csv", 120, 120),
        ("INJECTION_RECOVERY_540.csv", 540, 540),
        ("COMB_V4_1_CALIBRATION_162.csv", 161, 162),
        ("DETECTOR_V58_G4G5_CALIBRATION_108.csv", 108, 108),
        ("KEPLERIAN_TRACK_CALIBRATION_81.csv", 81, 81),
        ("CALIBRATION_V58_RPCA_RARITY_180.csv", 180, 180),
        ("CALIBRATION_V58_AGNOSTIC_120.csv", 118, 120),
        ("CALIBRATION_G8_V58_120.csv", 117, 120),
    ]
    tot_passed = 0
    tot_trials = 0
    cal_ok = True
    for fn, exp_p, exp_t in suites:
        rows = _read_csv(res / fn)
        n_t = len(rows)
        n_p = sum(1 for r in rows if r["passed"] == "1")
        if n_t != exp_t or n_p != exp_p:
            cal_ok = False
        tot_passed += n_p
        tot_trials += n_t
    dc240 = _read_csv(res / "CALIBRATION_V59_DRIFTING_COMB_240.csv")
    v41_dc = sum(int(r["v41_static_obs"]) for r in dc240[:120])
    c5_ok = cal_ok and tot_trials == 2271 and tot_passed == 2264 and v41_dc == 11
    rec("C5", c5_ok, f"{tot_passed}/{tot_trials} across 11 suites (ALMA 240/240, Comb-Drift 240/240 vs V4.1 {v41_dc}/120)")

    # C6: Stream A ALMA B1/B3/B4/B5 Gap Closure & Frontier
    alma = _read_csv(res / "ALMA_MM_INTERFEROMETRIC_58STARS.csv")
    sled = _read_csv(res / "V5_9_SPACE_CANDIDATE_LEDGER.csv")
    a_targets = {r["star"] for r in alma}
    a_bands = {r["instrument"] for r in alma}
    min_freq_a = min(float(r["min_freq_ghz"]) for r in alma)
    max_wave_a = max(float(r["max_wave_um"]) for r in alma)
    best_b3 = min(float(r["p_beam_10m_kw"]) for r in alma if r["instrument"] == "ALMA_B3_3MM")
    c6_ok = (
        len(alma) == 62
        and len(a_targets) == 58
        and a_bands == {"ALMA_B1_7MM", "ALMA_B3_3MM", "ALMA_B4_2MM", "ALMA_B5_2MM"}
        and abs(min_freq_a - 35.037144) < 1e-4
        and abs(max_wave_a - 8556.41831) < 1e-3
        and len(sled) == 22
        and all(int(r["verified_eti"]) == 0 for r in sled)
        and all(int(r["verified_eti"]) == 0 for r in alma)
        and abs(best_b3 - 186.99832754) < 0.01
    )
    rec("C6", c6_ok, f"ALMA 62 cubes / 58 targets (B1/B3/B4/B5), frontier={max_wave_a:.5f} um, AUMIC={best_b3:.2f} kW, 22->0 ETI")

    # C7: Stream B ESO ESPRESSO/HARPS 4-Gen & Orbits #151-#156
    fg = _read_csv(res / "FOUR_GEN_BENCHMARK_D101.csv")
    orb = _read_csv(res / "ORBITAL_CAMPAIGN_RESULTS_6.csv")
    vled = _read_csv(res / "V5_9_CANDIDATE_LEDGER.csv")
    eirp = _read_csv(res / "EIRP_UPPER_LIMITS_D101.csv")
    fg_g1 = sum(int(r["g1_seeds"]) for r in fg)
    fg_g8 = sum(int(r["g8_pass"]) for r in fg)
    orb_ids = sorted(int(r["campaign_index"]) for r in orb)
    min_harps = min(float(r["p_beam_10m_kw"]) for r in eirp if r["instrument"] == "ESO_HARPS")
    min_esp = min(float(r["p_beam_10m_kw"]) for r in eirp if r["instrument"] == "ESO_ESPRESSO")
    c7_ok = (
        fg_g1 == 43
        and fg_g8 == 0
        and sum(int(r["stage2_verified_eti"]) for r in fg) == 0
        and orb_ids == [151, 152, 153, 154, 155, 156]
        and all(int(r["verified_eti"]) == 0 for r in orb)
        and len(vled) == 0
        and abs(min_harps - 0.35502188) < 0.005
        and abs(min_esp - 8.11030272) < 0.01
    )
    rec("C7", c7_ok, f"ESO 4-Gen 43->{fg_g8}->0; Orbits #151-#156=0; HARPS={min_harps:.4f} kW, ESPRESSO={min_esp:.4f} kW")

    # C8: Stream C 48-Campaign DRIFT_V59 + COMB_DRIFT_V59 + Archives T-Z Verification
    ek48 = _read_csv(res / "DRIFT_V59_ECCENTRIC_KEPLERIAN_48CAMPAIGNS.csv")
    cd48 = _read_csv(res / "COMB_DRIFT_V59_48CAMPAIGNS.csv")
    ek_led = _read_csv(res / "DRIFT_V59_CANDIDATE_LEDGER.csv")
    cd_led = _read_csv(res / "COMB_DRIFT_V59_CANDIDATE_LEDGER.csv")
    tot_ek_t = sum(int(r["n_trajectories_evaluated"]) for r in ek48)
    tot_ek_px = sum(int(r["n_pixel_trajectory_integrals"]) for r in ek48)
    tot_cd_t = sum(int(r["comb_trajectories_evaluated"]) for r in cd48)
    arch_ok = True
    arch_notes = []
    for code, fname, exp_asha, bname, exp_bsha in RETRO_ARCHIVES:
        ap = arch_dir / fname
        if not ap.is_file():
            arch_ok = False
            arch_notes.append(f"{code}=MISSING")
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
            arch_ok = False
        arch_notes.append(f"{code}={'OK' if ok_one else 'DIFF'}")
    c8_ok = (
        len(ek48) == 48
        and len(cd48) == 48
        and tot_ek_t == 63809
        and tot_ek_px == 6088120032
        and tot_cd_t == 8277
        and all(int(r["stage2_verified_eti"]) == 0 for r in ek48)
        and all(int(r["stage2_verified_eti"]) == 0 for r in cd48)
        and all(int(r["verified_eti"]) == 0 for r in ek_led)
        and all(int(r["verified_eti"]) == 0 for r in cd_led)
        and arch_ok
    )
    rec("C8", c8_ok, f"48 campaigns: DRIFT_V59={tot_ek_t:,} ({tot_ek_px:,} px), COMB_DRIFT={tot_cd_t:,}->0 ETI; Archives Z-T 7/7 OK")

    # C9: Unified 613-Star Panchromatic V5.9 Synthesis & Bridges
    summ = _read_json(res / "SUMMARY.json")
    u613 = _read_csv(res / "UNIFIED_PANCHROMATIC_V5_9_SYNTHESIS_613STARS.csv")
    s180 = _read_csv(res / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_180STARS.csv")
    br76 = _read_csv(res / "PANCHROMATIC_BRIDGE_76STARS_V59.csv")
    ell = _read_csv(res / "MULTIEVENT_ELLIPSOID_613STARS.csv")
    u_sci = sum(1 for r in u613 if r["role"] == "SCIENCE")
    u_ctl = sum(1 for r in u613 if r["role"] == "CONTROL")
    u_hosts = sum(1 for r in u613 if int(float(r["n_exoplanets"] or 0)) > 0)
    u_pl = sum(int(float(r["n_exoplanets"] or 0)) for r in u613)
    vals_10pc = [float(r["min_panchromatic_10m_kw"]) for r in s180 if r["min_panchromatic_10m_kw"].strip()]
    med_10pc = _median(vals_10pc)
    syn = summ.get("unified_613star_panchromatic_v5_9_synthesis", {})
    etz = sum(1 for r in ell if r["etz_qualified"] in ("1", "True", "true"))
    e180 = sum(1 for r in ell if r["ellipsoid_qualified_180d"] in ("1", "True", "true"))
    c9_ok = (
        len(u613) == 613
        and u_sci == 472
        and u_ctl == 141
        and u_hosts == 226
        and u_pl == 429
        and len(s180) == 180
        and len(vals_10pc) == 158
        and abs(med_10pc - 1.4488) < 0.001
        and len(br76) == 873
        and len({r["star"] for r in br76}) == 79
        and len(ell) == 613
        and etz == 71
        and e180 == 37
        and syn.get("spectrographs") == 41
        and syn.get("spectral_arms") == 67
        and abs(float(syn.get("unbroken_max_wave_um", 0.0)) - 1401.36089) < 1e-4
        and abs(float(syn.get("unbroken_octave_span", 0.0)) - 13.919) < 1e-3
        and abs(float(syn.get("max_wave_um", 0.0)) - 8556.41831) < 1e-3
        and abs(float(syn.get("total_octave_span", 0.0)) - 16.529) < 1e-3
        and syn.get("total_calibration_trials_d079_d101") == 48726
    )
    rec("C9", c9_ok, f"613 stars ({u_sci}/{u_ctl}, {u_hosts}/{u_pl}), 180 <10pc ({med_10pc:.4f} kW), 76 mp-sci/79 stars (873 cells), 41/67, 16.529 oct")

    # C10: All-Sky COMB_V4_1 Unified Stacks
    comb_u = _read_csv(res / "ALLSKY_COMB_V4_1_UNIFIED_D079_D101.csv")
    comb_c = _read_csv(res / "ALLSKY_COMB_V4_1_CANDIDATES_D079_D101.csv")
    raw_s = summ.get("raw_hits_and_triage", {})
    c10_ok = (
        len(comb_u) == 479
        and sum(int(r["verified_eti_combs"]) for r in comb_u) == 0
        and len(comb_c) == 1248
        and raw_s.get("comb_v4_1_configs_evaluated") == 4919788
        and raw_s.get("comb_v4_1_candidates") == 1033
        and raw_s.get("comb_verified_eti") == 0
    )
    rec("C10", c10_ok, f"4,919,788 D101 comb configs -> 1,033 -> 0 ETI ({len(comb_u)} cumulative stacks)")

    # C11: Global Zero-ETI & V2 False Alarm Elimination
    c11_ok = (
        raw_s.get("verified_eti_detections_total") == 0
        and raw_s.get("alma_verified_eti") == 0
        and raw_s.get("orbital_campaigns_151_156_verified_eti") == 0
        and raw_s.get("drift_v59_48campaigns_verified_eti") == 0
        and raw_s.get("comb_drift_v59_48campaigns_verified_eti") == 0
        and raw_s.get("v2_false_alarms_eliminated_d101") == 89659
        and syn.get("v2_false_alarms_eliminated_total") == 805073
        and syn.get("verified_eti_detections_total") == 0
    )
    rec("C11", c11_ok, f"0 ETI across all D101+unified streams; V2 eliminated=89,659 D101 / 805,073 total")

    # C12: Independent Pure-Stdlib Radiometric Consistency (106 D101 + 859 Bridge Rows)
    mre_d101 = 0.0
    for r in eirp:
        pkw = _c12_pkw(float(r["dist_pc"]), float(r["flux_lim_erg_cm2_s"]), float(r["wave_bary_a"]))
        ref = float(r["p_beam_10m_kw"])
        mre_d101 = max(mre_d101, abs(pkw - ref) / max(ref, 1e-30))
    mre_br = 0.0
    nonempty_br = [r for r in br76 if r.get("flux_lim_erg_cm2_s", "").strip() != ""]
    for r in nonempty_br:
        pkw = _c12_pkw(float(r["dist_pc"]), float(r["flux_lim_erg_cm2_s"]), float(r["wave_A"]))
        ref = float(r["p_beam_10m_kw"])
        mre_br = max(mre_br, abs(pkw - ref) / max(ref, 1e-30))
    mre = max(mre_d101, mre_br)
    c12_ok = len(eirp) == 106 and len(nonempty_br) == 859 and mre < 0.002
    rec("C12", c12_ok, f"{len(eirp)}+{len(nonempty_br)}={len(eirp)+len(nonempty_br)} EIRP rows consistent, max_rel_err={mre:.10f} < 0.002")

    # C13: Results Manifest & Implementation Lock
    man = _read_json(ws / "RESULTS_MANIFEST_SHA256.json")
    ilock = _read_json(ws / "IMPLEMENTATION_LOCK.json")
    man_files = man.get("files", {})
    actual_res_files = sorted(p.relative_to(res).as_posix() for p in res.rglob("*") if p.is_file())
    man_diffs = [rel for rel, meta in man_files.items() if not (res / rel).is_file() or _sha256_file(res / rel) != meta["sha256"] or (res / rel).stat().st_size != meta["bytes"]]
    extra_res = sorted(set(actual_res_files) - set(man_files.keys()))
    il_files = ilock.get("locked_files", {})
    il_diffs = [rel for rel, h in il_files.items() if not (ws / rel).is_file() or _sha256_file(ws / rel) != h]
    c13_ok = len(man_files) == 37 and len(man_diffs) == 0 and len(extra_res) == 0 and len(il_files) >= 14 and len(il_diffs) == 0
    rec("C13", c13_ok, f"manifest={len(man_files)} files (diffs={len(man_diffs)}, extra={len(extra_res)}), impl_lock={len(il_files)} files (diffs={len(il_diffs)})")

    # C14: 6/6 Visual Figures & Review Verification
    vr = _read_json(ws / "VISUAL_REVIEW.json")
    vr_figs = vr.get("figures_reviewed", [])
    png_ok = True
    for item in vr_figs:
        fp = ws / item["filename"]
        if not fp.is_file() or fp.stat().st_size != item["bytes"] or _sha256_file(fp) != item["sha256"]:
            png_ok = False
            continue
        with open(fp, "rb") as pf:
            if pf.read(8) != b"\x89PNG\r\n\x1a\n":
                png_ok = False
    c14_ok = vr.get("status") == "PASS (6/6)" and len(vr_figs) == 6 and png_ok
    rec("C14", c14_ok, f"VISUAL_REVIEW {vr.get('status')} with {len(vr_figs)}/6 verified PNG headers, bytes, & SHA-256")

    # C15: Documentation & SOURCES Provenance
    rep = (ws / "RESULTS_REPORT.md").read_text(encoding="utf-8")
    src_j = _read_json(res / "SOURCES.json")
    n_src_exp = len(src_j.get("exposures", []))
    c15_ok = (
        len(rep) > 1000
        and "613" in rep
        and "13.919" in rep
        and "16.529" in rep
        and "8,556.41831" in rep
        and "NGC4038GAL" in rep
        and "COMB_DRIFT_V59" in rep
        and n_src_exp == 101
        and len(src_j.get("retroactive_companion_archives", [])) == 7
    )
    rec("C15", c15_ok, f"RESULTS_REPORT.md ({len(rep)} chars) + SOURCES.json ({n_src_exp} exposures, 7 retro archives)")

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
    ap = argparse.ArgumentParser(description="Phase D101 pure-stdlib C1-C16 audit")
    ap.add_argument("--workspace", "--workspace-dir", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent)
    ap.add_argument("--archives-dir", type=pathlib.Path, default=None)
    args = ap.parse_args()
    n_pass, n_tot = run_audit(args.workspace.resolve(), args.archives_dir)
    return 0 if n_pass == n_tot else 1


if __name__ == "__main__":
    raise SystemExit(main())
