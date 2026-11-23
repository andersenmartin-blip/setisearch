#!/usr/bin/env python3
"""Pure-stdlib (C1-C16) independent cryptographic & scientific audit for Phase D102 (V6.0)."""

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
METHOD_LOCK_SHA256 = "6e4739f06f04768a49ad8e578448d33cc317a5894d6e790a8ae6d3d1ecd87db7"
BUNDLE_SHA256 = "b1979cde20276543ed30d9ca99098374050530b5934490c44c8b765dffc6d8bf"
BUNDLE_BYTES = 18285469
BUNDLE_CAP_BYTES = int(18.5 * 1024 * 1024)

RETRO_ARCHIVES = [
    (
        "AA",
        "SETI_D101_V5_9_ALMA_MM_BAND1_GAP_CLOSURE_DRIFTING_COMB_RESULTS_2026-11-23.zip",
        "848a2ade7fdb46ed4e4f067e729ccf796a5181501f6e0ed18f573ff871fa8b20",
        "d101_bounded_bundle.json.gz",
        "f3735b57ef170c3162fad61a825fad086c768e1a6662d48d3a4637c5eea51ec4",
    ),
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

    # C1: Stage-1 Prospective Seal, Chronology & Prior-Exclusion Integrity
    lr = _read_json(ws / "LOCK_RECEIPT.json")
    fdr = _read_json(ws / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json")
    pe = _read_json(ws / "PRIOR_EXCLUSION_VERIFICATION.json")
    cohort = _read_csv(ws / "FROZEN_COHORT_D102.csv")
    ml_hash = _sha256_file(ws / "METHOD_LOCK.json")
    locked_s1 = lr.get("locked_files", {})
    diffs_s1 = [
        rel
        for rel, h in locked_s1.items()
        if not (ws / rel).is_file() or _sha256_file(ws / rel) != h
    ]
    cohort_stars = {r["canonical_target"] for r in cohort}
    c1_ok = (
        lr.get("phase_id") == "D102"
        and lr.get("inputs_dir_exists_at_seal") is False
        and ml_hash == METHOD_LOCK_SHA256
        and lr.get("method_lock_sha256") == METHOD_LOCK_SHA256
        and len(locked_s1) == 7
        and len(diffs_s1) == 0
        and fdr.get("phase_id") == "D102"
        and float(fdr.get("first_download_unix_epoch", 0.0)) - float(lr.get("locked_unix_epoch", 0.0)) >= 3.0
        and float(fdr.get("chronology_lag_seconds", -1.0)) >= 3.0
        and pe.get("n_prior_excluded_coords") == 686
        and pe.get("n_prior_excluded_dp_ids") == 3261
        and pe.get("d102_dp_id_overlap_count") == 0
        and float(pe.get("min_brand_new_sky_separation_arcsec", 0.0)) >= 385.0
        and float(pe.get("min_intra_d102_separation_arcsec", 0.0)) >= 6900.0
        and len(cohort) == 107
        and len(cohort_stars) == 67
    )
    rec("C1", c1_ok, f"METHOD_LOCK 7/7 diffs={len(diffs_s1)}, lag={fdr.get('chronology_lag_seconds')}s, min_sep={pe.get('min_brand_new_sky_separation_arcsec')} arcsec")

    # C2: Bounded Bundle <= 18.5 MiB, Manifest 107/107 & Companion Archives T-Z, AA (8/8)
    man_in = _read_json(ws / "FULL_D102_INPUT_MANIFEST.json")
    ep = _read_csv(res / "EXPOSURE_PROVENANCE_D102.csv")
    tot_h = sum(float(r["t_exptime_s"]) for r in ep) / 3600.0
    gz = ws / "bounded_inputs/d102_bounded_bundle.json.gz"
    gz_bytes = gz.stat().st_size if gz.is_file() else -1
    gz_sha = _sha256_file(gz) if gz.is_file() else ""
    gz_ok = False
    if gz.is_file():
        with gzip.open(gz, "rt", encoding="utf-8") as gf:
            bundle_obj = json.load(gf)
        gz_ok = isinstance(bundle_obj, dict) and bundle_obj.get("phase_id") == "D102" and bundle_obj.get("n_exposures") == 107
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
    c2_ok = (
        man_in.get("phase_id") == "D102"
        and man_in.get("expected_files") == 107
        and man_in.get("valid_files") == 107
        and man_in.get("failed_files") == 0
        and man_in.get("total_bytes") == 1093982328
        and len(ep) == 107
        and len({r["star"] for r in ep}) == 67
        and abs(tot_h - 2259.6639) < 0.01
        and gz_bytes == BUNDLE_BYTES
        and gz_bytes <= BUNDLE_CAP_BYTES
        and gz_sha == BUNDLE_SHA256
        and gz_ok
        and arch_ok
    )
    rec("C2", c2_ok, f"107/107 valid ({tot_h:.2f}h), bundle={gz_bytes} B (<=18.5 MiB), Archives T-Z,AA 8/8={arch_ok}")

    # C3: 13-Suite 2,691-Trial Calibration Scorecard (All >=95%, 0 FA Chandra/EUVE Vetoes)
    suites = [
        ("CALIBRATION_V60_CHANDRA_POISSON_240.csv", 238, 240),
        ("CALIBRATION_V60_EUVE_180.csv", 180, 180),
        ("CALIBRATION_V59_ALMA_INTERFEROMETRIC_240.csv", 239, 240),
        ("CALIBRATION_V59_DRIFTING_COMB_240.csv", 236, 240),
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
        if n_t != exp_t or n_p != exp_p or (n_p / max(1, n_t)) < 0.95:
            cal_ok = False
        tot_passed += n_p
        tot_trials += n_t
    ch_cal = _read_csv(res / "CALIBRATION_V60_CHANDRA_POISSON_240.csv")
    eu_cal = _read_csv(res / "CALIBRATION_V60_EUVE_180.csv")
    ch_veto_fa = sum(1 for r in ch_cal if r["class"] != "CLEAN_XRAY_BEACON" and r["passed"] != "1")
    eu_veto_fa = sum(1 for r in eu_cal if r["class"] != "CLEAN_EUV_BEACON" and r["passed"] != "1")
    dc240 = _read_csv(res / "CALIBRATION_V59_DRIFTING_COMB_240.csv")
    v41_dc = sum(int(r["v41_static_obs"]) for r in dc240[:120])
    c3_ok = cal_ok and tot_trials == 2691 and tot_passed == 2677 and ch_veto_fa == 0 and eu_veto_fa == 0 and v41_dc == 11
    rec("C3", c3_ok, f"{tot_passed}/{tot_trials} across 13 suites (Chandra FA={ch_veto_fa}/180, EUVE FA={eu_veto_fa}/120, V4.1={v41_dc}/120)")

    # C4: Stream A Chandra X-Ray Gratings (24 ObsIDs = 12 HETG + 12 LETG)
    ch_obs = _read_csv(res / "CHANDRA_XRAY_POISSON_24OBS.csv")
    sled = _read_csv(res / "V6_0_SPACE_CANDIDATE_LEDGER.csv")
    summ = _read_json(res / "SUMMARY.json")
    raw_s = summ.get("raw_hits_and_triage", {})
    ch_led = [r for r in sled if r["instrument"].startswith("CHANDRA_")]
    hetg_n = sum(1 for r in ch_obs if r["instrument"] == "CHANDRA_HETG")
    letg_n = sum(1 for r in ch_obs if r["instrument"] == "CHANDRA_LETG")
    best_ch = min(float(r["p_beam_10m_kw"]) for r in ch_obs)
    best_letg = min(float(r["p_beam_10m_kw"]) for r in ch_obs if r["instrument"] == "CHANDRA_LETG")
    c4_ok = (
        len(ch_obs) == 24
        and hetg_n == 12
        and letg_n == 12
        and sum(int(r["n_raw"]) for r in ch_obs) == 596
        and raw_s.get("chandra_raw_candidates") == 596
        and len(ch_led) == 589
        and all(int(r["verified_eti"]) == 0 for r in ch_obs)
        and all(int(r["verified_eti"]) == 0 for r in ch_led)
        and abs(best_ch - 6e-7) < 1e-8
        and abs(best_letg - 3.567e-5) < 1e-6
    )
    rec("C4", c4_ok, f"Chandra 24 ObsIDs ({hetg_n} HETG + {letg_n} LETG), 596 raw / 589 ledger -> 0 ETI; EVLAC={best_ch:.2e} kW")

    # C5: Stream B NASA EUVE Extreme-UV (24 Targets) + 9.186 Unbroken High-Energy Octaves
    eu_obs = _read_csv(res / "EUVE_EXTREME_UV_24OBS.csv")
    eu_led = [r for r in sled if r["instrument"] == "EUVE_DS_S"]
    spec_a = _read_json(res / "SPECTRAL_COVERAGE_AUDIT_D102.json")
    best_eu = min(float(r["p_beam_10m_kw"]) for r in eu_obs)
    c5_ok = (
        len(eu_obs) == 24
        and sum(int(r["n_raw"]) for r in eu_obs) == 64
        and raw_s.get("euve_raw_candidates") == 64
        and len(eu_led) == 62
        and all(int(r["verified_eti"]) == 0 for r in eu_obs)
        and all(int(r["verified_eti"]) == 0 for r in eu_led)
        and abs(best_eu - 0.0004101) < 1e-5
        and spec_a.get("high_energy_unbroken_um") == [0.00012, 0.06998]
        and abs(float(spec_a.get("high_energy_unbroken_octaves", 0.0)) - 9.186) < 0.005
    )
    rec("C5", c5_ok, f"EUVE 24 targets, 64 raw / 62 ledger -> 0 ETI; PROXIMA={best_eu:.4e} kW; he_oct={spec_a.get('high_energy_unbroken_octaves')}")

    # C6: Stream C ALMA_V60 (22 Cubes B3-B8 incl. NGC7469 B8) & Spectral Continuity (26.086 Octaves)
    alma = _read_csv(res / "ALMA_MM_SEAMS_D102.csv")
    al_led = [r for r in sled if r["instrument"].startswith("ALMA_")]
    al_bands = {r["instrument"] for r in alma}
    ngc_b8 = [r for r in alma if r["instrument"] == "ALMA_B8_0P7MM"]
    best_b7 = min(float(r["p_beam_10m_kw"]) for r in alma if r["instrument"] == "ALMA_B7_0P9MM")
    best_b6 = min(float(r["p_beam_10m_kw"]) for r in alma if r["instrument"] == "ALMA_B6_1MM")
    c6_ok = (
        len(alma) == 22
        and len({r["star"] for r in alma}) == 18
        and al_bands == {"ALMA_B3_3MM", "ALMA_B4_2MM", "ALMA_B5_2MM", "ALMA_B6_1MM", "ALMA_B7_0P9MM", "ALMA_B8_0P7MM"}
        and len(ngc_b8) == 1
        and ngc_b8[0]["star"] == "NGC7469"
        and abs(float(ngc_b8[0]["min_freq_ghz"]) - 481.683929) < 0.01
        and sum(int(r["n_raw"]) for r in alma) == 25
        and raw_s.get("alma_raw_candidates") == 25
        and len(al_led) == 24
        and all(int(r["verified_eti"]) == 0 for r in alma)
        and all(int(r["verified_eti"]) == 0 for r in al_led)
        and abs(best_b7 - 47.68746826) < 0.01
        and abs(best_b6 - 178.78471628) < 0.01
        and abs(float(spec_a.get("lyman_to_mm_strict_zero_gap_octaves", 0.0)) - 13.935) < 0.005
        and abs(float(spec_a.get("lyman_to_mm_b4_low_octaves", 0.0)) - 14.693) < 0.005
        and abs(float(spec_a.get("global_max_wave_um", 0.0)) - 8556.41831) < 1e-3
        and abs(float(spec_a.get("total_octave_span", 0.0)) - 26.086) < 0.005
    )
    rec("C6", c6_ok, f"ALMA 22 cubes/6 bands (B8 NGC7469), 25 raw -> 0 ETI; tot={spec_a.get('total_octave_span')} oct")

    # C7: Stream D ESO ESPRESSO/HARPS 4-Gen & Orbits #157-#162
    fg = _read_csv(res / "FOUR_GEN_BENCHMARK_D102.csv")
    orb = _read_csv(res / "ORBITAL_CAMPAIGN_RESULTS_6.csv")
    vled = _read_csv(res / "V6_0_CANDIDATE_LEDGER.csv")
    eirp = _read_csv(res / "EIRP_UPPER_LIMITS_D102.csv")
    fg_g1 = sum(int(r["g1_seeds"]) for r in fg)
    fg_g8 = sum(int(r["g8_pass"]) for r in fg)
    orb_ids = sorted(int(r["campaign_index"]) for r in orb)
    min_esp = min(float(r["p_beam_10m_kw"]) for r in eirp if r["instrument"] == "ESO_ESPRESSO")
    min_harps = min(float(r["p_beam_10m_kw"]) for r in eirp if r["instrument"] == "ESO_HARPS")
    c7_ok = (
        fg_g1 == 88
        and fg_g8 == 3
        and sum(int(r["stage2_verified_eti"]) for r in fg) == 0
        and orb_ids == [157, 158, 159, 160, 161, 162]
        and all(int(r["verified_eti"]) == 0 for r in orb)
        and len(vled) == 3
        and all(int(r["verified_eti"]) == 0 for r in vled)
        and abs(min_esp - 0.11609311) < 0.005
        and abs(min_harps - 0.1404938) < 0.005
    )
    rec("C7", c7_ok, f"ESO 4-Gen {fg_g1}->{fg_g8}->0; Orbits #157-#162=0; ESPRESSO={min_esp:.4f} kW, HARPS={min_harps:.4f} kW")

    # C8: Stream E 54-Campaign DRIFT_V60 + COMB_DRIFT_V60
    ek54 = _read_csv(res / "DRIFT_V60_ECCENTRIC_KEPLERIAN_54CAMPAIGNS.csv")
    cd54 = _read_csv(res / "COMB_DRIFT_V60_54CAMPAIGNS.csv")
    ek_led = _read_csv(res / "DRIFT_V60_CANDIDATE_LEDGER.csv")
    cd_led = _read_csv(res / "COMB_DRIFT_V60_CANDIDATE_LEDGER.csv")
    tot_ek_t = sum(int(r["n_trajectories_evaluated"]) for r in ek54)
    tot_ek_px = sum(int(r["n_pixel_trajectory_integrals"]) for r in ek54)
    tot_cd_t = sum(int(r["comb_trajectories_evaluated"]) for r in cd54)
    c8_ok = (
        len(ek54) == 54
        and len(cd54) == 54
        and tot_ek_t == 71176
        and tot_ek_px == 7241613718
        and tot_cd_t == 8159
        and all(int(r["stage2_verified_eti"]) == 0 for r in ek54)
        and all(int(r["stage2_verified_eti"]) == 0 for r in cd54)
        and all(int(r["verified_eti"]) == 0 for r in ek_led)
        and all(int(r["verified_eti"]) == 0 for r in cd_led)
    )
    rec("C8", c8_ok, f"54 campaigns: DRIFT_V60={tot_ek_t:,} ({tot_ek_px:,} px), COMB_DRIFT={tot_cd_t:,} -> 0 ETI")

    # C9: Unified 656-Star Panchromatic V6.0 Synthesis & Bridges
    u656 = _read_csv(res / "UNIFIED_PANCHROMATIC_V6_0_SYNTHESIS_656STARS.csv")
    s183 = _read_csv(res / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_183STARS.csv")
    br84 = _read_csv(res / "PANCHROMATIC_BRIDGE_84STARS_V60.csv")
    ell = _read_csv(res / "MULTIEVENT_ELLIPSOID_656STARS.csv")
    u_sci = sum(1 for r in u656 if r["role"] == "SCIENCE")
    u_ctl = sum(1 for r in u656 if r["role"] == "CONTROL")
    u_hosts = sum(1 for r in u656 if int(float(r["n_exoplanets"] or 0)) > 0)
    u_pl = sum(int(float(r["n_exoplanets"] or 0)) for r in u656)
    vals_10pc = [float(r["min_panchromatic_10m_kw"]) for r in s183 if r["min_panchromatic_10m_kw"].strip()]
    med_10pc = _median(vals_10pc)
    syn = summ.get("unified_656star_panchromatic_v6_0_synthesis", {})
    etz = sum(1 for r in ell if r["etz_qualified"] in ("1", "True", "true"))
    e180 = sum(1 for r in ell if r["ellipsoid_qualified_180d"] in ("1", "True", "true"))
    c9_ok = (
        len(u656) == 656
        and u_sci == 492
        and u_ctl == 164
        and u_hosts == 232
        and u_pl == 442
        and len(s183) == 183
        and len(vals_10pc) == 163
        and abs(med_10pc - 1.0796) < 0.001
        and len(br84) == 943
        and syn.get("panchromatic_bridge_stars_total") == 84
        and syn.get("multi_phase_targets_total") == 95
        and len(ell) == 656
        and etz == 87
        and e180 == 38
        and syn.get("spectrographs") == 45
        and syn.get("spectral_arms") == 73
        and syn.get("total_calibration_trials_d079_d102") == 51417
        and syn.get("companion_archives_total") == 28
    )
    rec("C9", c9_ok, f"656 stars ({u_sci}/{u_ctl}, {u_hosts}/{u_pl}), 183 <10pc ({med_10pc:.4f} kW), 84 bridges/95 mp (943 cells), 45/73, 51,417 cal")

    # C10: All-Sky COMB_V4_1 Unified Stacks
    comb_u = _read_csv(res / "ALLSKY_COMB_V4_1_UNIFIED_D079_D102.csv")
    comb_c = _read_csv(res / "ALLSKY_COMB_V4_1_CANDIDATES_D079_D102.csv")
    c10_ok = (
        len(comb_u) == 487
        and sum(int(r["verified_eti_combs"]) for r in comb_u) == 0
        and len(comb_c) == 8455
        and raw_s.get("comb_v4_1_configs_evaluated") == 4563888
        and raw_s.get("comb_v4_1_candidates") == 7207
        and raw_s.get("comb_verified_eti") == 0
    )
    rec("C10", c10_ok, f"4,563,888 D102 comb configs -> 7,207 -> 0 ETI ({len(comb_u)} cumulative stacks)")

    # C11: Global Zero-ETI & V2 False Alarm Elimination
    c11_ok = (
        raw_s.get("verified_eti_detections_total") == 0
        and raw_s.get("chandra_verified_eti") == 0
        and raw_s.get("euve_verified_eti") == 0
        and raw_s.get("alma_verified_eti") == 0
        and raw_s.get("orbital_campaigns_157_162_verified_eti") == 0
        and raw_s.get("drift_v60_54campaigns_verified_eti") == 0
        and raw_s.get("comb_drift_v60_54campaigns_verified_eti") == 0
        and raw_s.get("v2_false_alarms_eliminated_d102") == 42939
        and syn.get("v2_false_alarms_eliminated_total") == 848012
        and syn.get("verified_eti_detections_total") == 0
    )
    rec("C11", c11_ok, "0 ETI across all D102+unified streams; V2 eliminated=42,939 D102 / 848,012 total")

    # C12: Independent Pure-Stdlib Radiometric Consistency (188 D102 + 929 Bridge Rows)
    mre_d102 = 0.0
    for r in eirp:
        pkw = _c12_pkw(float(r["dist_pc"]), float(r["flux_lim_erg_cm2_s"]), float(r["wave_bary_a"]))
        ref = float(r["p_beam_10m_kw"])
        mre_d102 = max(mre_d102, abs(pkw - ref) / max(ref, 1e-30))
    mre_br = 0.0
    nonempty_br = [r for r in br84 if r.get("flux_lim_erg_cm2_s", "").strip() != ""]
    for r in nonempty_br:
        pkw = _c12_pkw(float(r["dist_pc"]), float(r["flux_lim_erg_cm2_s"]), float(r["wave_A"]))
        ref = float(r["p_beam_10m_kw"])
        mre_br = max(mre_br, abs(pkw - ref) / max(ref, 1e-30))
    mre = max(mre_d102, mre_br)
    c12_ok = len(eirp) == 188 and len(nonempty_br) == 929 and mre < 0.002
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
    c13_ok = len(man_files) == 42 and len(man_diffs) == 0 and len(extra_res) == 0 and len(il_files) >= 14 and len(il_diffs) == 0
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
        and "656" in rep
        and "9.186" in rep
        and "26.086" in rep
        and "8,556.41831" in rep
        and "EVLAC" in rep
        and "NGC7469" in rep
        and "COMB_DRIFT_V60" in rep
        and n_src_exp == 107
        and len(src_j.get("retroactive_companion_archives", [])) == 8
    )
    rec("C15", c15_ok, f"RESULTS_REPORT.md ({len(rep)} chars) + SOURCES.json ({n_src_exp} exposures, 8 retro archives)")

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
    ap = argparse.ArgumentParser(description="Phase D102 pure-stdlib C1-C16 audit")
    ap.add_argument("--workspace", "--workspace-dir", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent)
    ap.add_argument("--archives-dir", type=pathlib.Path, default=None)
    args = ap.parse_args()
    n_pass, n_tot = run_audit(args.workspace.resolve(), args.archives_dir)
    return 0 if n_pass == n_tot else 1


if __name__ == "__main__":
    raise SystemExit(main())
