#!/usr/bin/env python3
"""
Phase D092 Pure-Stdlib Independent Verification & Audit Suite (`C1-C16`)

Runs cleanly under `/usr/bin/python3 -S WS92/audit.py` (zero third-party packages).
Writes `results/AUDIT_SUMMARY.json` and exits 0 iff `OVERALL: PASS (16/16)`.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import platform
import sys
from pathlib import Path
from typing import Any

WS = Path(__file__).resolve().parent
ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
RES = WS / "results"
PC_CM = 3.085677581491367e18


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            b = fh.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _rcsv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _rjson(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _chk(cid: str, ok: bool, detail: str) -> dict[str, Any]:
    return {"check_id": cid, "status": "PASS" if ok else "FAIL", "passed": bool(ok), "detail": detail}


def main() -> None:
    checks: list[dict[str, Any]] = []

    mlock = _rjson(WS / "METHOD_LOCK.json")
    lrec = _rjson(WS / "LOCK_RECEIPT.json")
    frec = _rjson(WS / "FIRST_SCIENCE_DOWNLOAD_RECEIPT.json")
    man = _rjson(WS / "FULL_D092_INPUT_MANIFEST.json")
    pe = _rjson(WS / "PRIOR_EXCLUSION_VERIFICATION.json")
    vrev = _rjson(WS / "VISUAL_REVIEW.json")
    summary = _rjson(RES / "SUMMARY.json")
    diag = _rjson(RES / "FORENSIC_D092_CASCADE_DIAGNOSIS.json")
    faudit = _rjson(RES / "FORENSIC_CANDIDATE_AUDIT_D092.json")
    impl_lock = _rjson(WS / "IMPLEMENTATION_LOCK.json")

    # C1: Prospective Lock & Chronology
    lag_s = float(frec["chronology_lag_seconds"])
    lock_mismatches: list[str] = []
    if _sha256(WS / "METHOD_LOCK.json") != lrec.get("method_lock_sha256"):
        lock_mismatches.append("method_lock_sha256")
    if lrec.get("inputs_d092_v5_0_exists", True) is not False:
        lock_mismatches.append("inputs_d092_v5_0_exists_not_false")
    if lrec.get("locked_utc", "") >= frec.get("first_download_utc", ""):
        lock_mismatches.append("chronology_order")
    for rel, exp_sha in mlock["locked_file_hashes"].items():
        p = WS / rel
        if not p.exists():
            lock_mismatches.append(f"missing:{rel}")
            continue
        cur = _sha256(p)
        if cur != exp_sha or cur != lrec["locked_artifact_sha256"].get(rel):
            lock_mismatches.append(f"hash:{rel}")
    checks.append(_chk(
        "C1_PROSPECTIVE_LOCK_AND_CHRONOLOGY",
        lag_s >= 3.0 and not lock_mismatches,
        f"lag={lag_s:.2f}s pre_absent={lrec.get('inputs_d092_v5_0_exists') is False} mismatches={lock_mismatches}",
    ))

    # C2: Cohort Integrity & Prior Exclusion
    srv = _rcsv(RES / "STAR_RV_SUMMARY_28.csv")
    prov = _rcsv(RES / "EXPOSURE_PROVENANCE_D092.csv")
    c2_ok = (
        len(srv) == 28
        and sum(1 for r in srv if r["role"] == "CONTROL") == 6
        and sum(1 for r in srv if r["role"] == "SCIENCE") == 22
        and len(prov) == 57
        and sum(1 for r in prov if r["instrument"] == "ESO_HARPS") == 24
        and sum(1 for r in prov if r["instrument"] == "ESO_FEROS") == 20
        and sum(1 for r in prov if r["instrument"] == "ESO_CRIRES") == 13
        and int(pe["d092_dp_id_overlap_count"]) == 0
        and int(pe["d092_brand_new_unique_stars"]) == 25
        and int(pe["d092_panchromatic_bridge_stars"]) == 3
        and int(pe["d092_brand_new_within_10pc"]) == 11
    )
    checks.append(_chk(
        "C2_COHORT_INTEGRITY_AND_PRIOR_EXCLUSION",
        c2_ok,
        f"stars={len(srv)} (6C/22S, 25+3br, 11<10pc) exps={len(prov)} (24H/20F/13C) dp_overlap={pe['d092_dp_id_overlap_count']}",
    ))

    # C3: Bounded Bundle & Input Manifest
    bnd_p = WS / "bounded_inputs" / "d092_bounded_bundle.json.gz"
    bnd_mib = bnd_p.stat().st_size / (1024.0 * 1024.0)
    with gzip.open(bnd_p, "rt", encoding="utf-8") as gz:
        bnd_meta = json.load(gz)
    tot_man_bytes = sum(int(e["f1_bytes"]) for e in man["exposures"])
    disk_mismatches = 0
    inp_dir = ROOT / "inputs_d092_v5_0"
    if inp_dir.exists():
        for e in man["exposures"]:
            fp = inp_dir / e["f1_rel"]
            if not fp.exists() or _sha256(fp) != e["f1_sha256"]:
                disk_mismatches += 1
    c3_ok = (
        bnd_mib < 25.0
        and len(bnd_meta.get("exposures", [])) == 57
        and len(man["exposures"]) == 57
        and tot_man_bytes <= 225 * 1024 * 1024
        and disk_mismatches == 0
        and all(r["header_gate"] == "PASS" for r in prov)
    )
    checks.append(_chk(
        "C3_BOUNDED_BUNDLE_AND_INPUT_MANIFEST",
        c3_ok,
        f"bundle_mib={bnd_mib:.2f}<25.0 raw_mib={tot_man_bytes/(1024**2):.2f}<=225 disk_mismatches={disk_mismatches}",
    ))

    # C4: Full 29 Result Artifact Completeness
    expected_29 = [
        "ALLSKY_COMB_V4_1_CANDIDATES_D079_D092.csv",
        "ALLSKY_COMB_V4_1_UNIFIED_D079_D092.csv",
        "CALIBRATION_COMPLETENESS_BY_BAND.csv",
        "CALIBRATION_V50_AGNOSTIC_MULTISCALE_120.csv",
        "CALIBRATION_V50_MIRI_GREENHOUSE_160.csv",
        "CALIBRATION_V50_RPCA_RARITY_180.csv",
        "COMB_V4_1_CALIBRATION_162.csv",
        "COMB_V4_1_CANDIDATES.csv",
        "COMB_V4_1_STAR_RESULTS_28.csv",
        "DETECTOR_V50_G4G5_CALIBRATION_108.csv",
        "EXPOSURE_PROVENANCE_D092.csv",
        "FORENSIC_CANDIDATE_AUDIT_D092.json",
        "FORENSIC_D092_CASCADE_DIAGNOSIS.json",
        "FOUR_GEN_BENCHMARK_D092.csv",
        "GEOMETRIC_SYNC_TRACKS_D092.csv",
        "INJECTION_RECOVERY_540.csv",
        "KEPLERIAN_TRACK_CALIBRATION_81.csv",
        "MIRI_GREENHOUSE_CCF_D090_15TARGETS.csv",
        "ORBITAL_CAMPAIGN_RESULTS_9.csv",
        "PANCHROMATIC_BRIDGE_35STARS_V50.csv",
        "RETROACTIVE_D091_RPCA_REGRESSION.csv",
        "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_146STARS.csv",
        "STAR_RV_SUMMARY_28.csv",
        "STAR_UPPER_LIMITS_D092.csv",
        "STELLAR_RV_ANCHORS_D092.csv",
        "SUMMARY.json",
        "UNIFIED_PANCHROMATIC_V5_0_SYNTHESIS_335STARS.csv",
        "V5_0_AGNOSTIC_MULTISCALE_SURVIVORS.csv",
        "V5_0_CANDIDATE_LEDGER.csv",
    ]
    missing_res = [n for n in expected_29 if not (RES / n).exists() or (RES / n).stat().st_size == 0]
    checks.append(_chk(
        "C4_29_RESULT_ARTIFACTS_COMPLETE",
        len(missing_res) == 0 and len(expected_29) == 29,
        f"present={29 - len(missing_res)}/29 missing={missing_res}",
    ))

    # C5: Calibration Suite 1 — RPCA + Rarity (180 trials)
    rp_rows = _rcsv(RES / "CALIBRATION_V50_RPCA_RARITY_180.csv")
    rp_iso = [r["g7_pass"] == "True" for r in rp_rows if r["trial_class"] == "ISOLATED_LASER"]
    rp_shr = [r["g7_pass"] == "False" for r in rp_rows if r["trial_class"] == "SHARED_PHOTOSPHERIC_LEAK"]
    rp_top = [r["g7_pass"] == "False" for r in rp_rows if r["trial_class"] == "TOPO_SKY_REPEAT"]
    r_iso = sum(rp_iso) / len(rp_iso) if rp_iso else 0.0
    r_shr = sum(rp_shr) / len(rp_shr) if rp_shr else 0.0
    r_top = sum(rp_top) / len(rp_top) if rp_top else 0.0
    c5_ok = len(rp_rows) == 180 and r_iso >= 0.90 and r_shr >= 0.95 and r_top >= 0.95
    checks.append(_chk(
        "C5_CALIBRATION_RPCA_RARITY_180",
        c5_ok,
        f"rows={len(rp_rows)} iso={sum(rp_iso)}/{len(rp_iso)} ({r_iso:.4f}) leak_rej={sum(rp_shr)}/{len(rp_shr)} topo_rej={sum(rp_top)}/{len(rp_top)}",
    ))

    # C6: Calibration Suite 2 — Agnostic Multi-Scale (120 trials)
    ag_cal = _rcsv(RES / "CALIBRATION_V50_AGNOSTIC_MULTISCALE_120.csv")
    ag_rate = sum(1 for r in ag_cal if r["recovered"] == "True") / len(ag_cal) if ag_cal else 0.0
    c6_ok = len(ag_cal) == 120 and ag_rate >= 0.90
    checks.append(_chk(
        "C6_CALIBRATION_AGNOSTIC_MULTISCALE_120",
        c6_ok,
        f"rows={len(ag_cal)} recovered={sum(1 for r in ag_cal if r['recovered']=='True')}/120 ({ag_rate:.4f})",
    ))

    # C7: Calibration Suite 3 — MIRI Greenhouse CCF (160 trials)
    m_cal = _rcsv(RES / "CALIBRATION_V50_MIRI_GREENHOUSE_160.csv")
    m_inj = [r["passes_ccf"] == "True" for r in m_cal if r["expected_detection"] == "True"]
    m_conf = [r["any_greenhouse_detected"] == "False" for r in m_cal if r["expected_detection"] == "False"]
    m_ir = sum(m_inj) / len(m_inj) if m_inj else 0.0
    m_cr = sum(m_conf) / len(m_conf) if m_conf else 0.0
    c7_ok = len(m_cal) == 160 and m_ir >= 0.90 and m_cr >= 0.95
    checks.append(_chk(
        "C7_CALIBRATION_MIRI_GREENHOUSE_160",
        c7_ok,
        f"rows={len(m_cal)} recov={sum(m_inj)}/{len(m_inj)} ({m_ir:.4f}) conf_veto={sum(m_conf)}/{len(m_conf)} ({m_cr:.4f})",
    ))

    # C8: Calibration Suite 4 — Injection Recovery (540 trials)
    inj = _rcsv(RES / "INJECTION_RECOVERY_540.csv")
    t_8 = [r["recovered"] == "True" for r in inj if r["mode"] == "CHANNEL_T_TRANSIENT_1EPOCH" and float(r["sigma_mult"]) >= 8.0]
    p_8 = [r["recovered"] == "True" for r in inj if r["mode"] == "CHANNEL_P_STATIC_COADD" and float(r["sigma_mult"]) >= 8.0]
    rt8 = sum(t_8) / len(t_8) if t_8 else 0.0
    rp8 = sum(p_8) / len(p_8) if p_8 else 0.0
    c8_ok = len(inj) == 540 and rt8 >= 0.90 and rp8 >= 0.90
    checks.append(_chk(
        "C8_CALIBRATION_INJECTION_RECOVERY_540",
        c8_ok,
        f"rows={len(inj)} ChT_8s={sum(t_8)}/{len(t_8)} ({rt8:.4f}) ChP_8s={sum(p_8)}/{len(p_8)} ({rp8:.4f})",
    ))

    # C9: Calibration Suites 5 & 6 — Keplerian Track (81) & G4/G5 (108)
    kep = _rcsv(RES / "KEPLERIAN_TRACK_CALIBRATION_81.csv")
    g45 = _rcsv(RES / "DETECTOR_V50_G4G5_CALIBRATION_108.csv")
    k_td = sum(1 for r in kep if r["tdiff_uncomp_recovered"] == "True") / len(kep) if kep else 1.0
    k_kp = sum(1 for r in kep if r["kplanet_dedop_recovered"] == "True") / len(kep) if kep else 0.0
    g_tr = [r["g45_pass"] == "True" for r in g45 if r["trial_class"] == "TRUE_LSF_LASER"]
    g_cr = [r["g5_pass"] == "False" for r in g45 if r["trial_class"] == "COSMIC_RAY_HOT_PIXEL"]
    g_pl = [r["g5_pass"] == "False" for r in g45 if r["trial_class"] == "M_DWARF_PLATEAU_CORE"]
    c9_ok = (
        len(kep) == 81 and k_td <= 0.10 and k_kp >= 0.95
        and len(g45) == 108
        and (sum(g_tr) / len(g_tr)) >= 0.95
        and (sum(g_cr) / len(g_cr)) >= 0.95
        and (sum(g_pl) / len(g_pl)) >= 0.95
    )
    checks.append(_chk(
        "C9_KEPLERIAN_81_AND_G4G5_108",
        c9_ok,
        f"kep={len(kep)} T_DIFF={k_td:.4f} K_PLANET={k_kp:.4f} g45={len(g45)} ({sum(g_tr)}/{len(g_tr)} true, {sum(g_cr)}/{len(g_cr)} cosmic, {sum(g_pl)}/{len(g_pl)} plat)",
    ))

    # C10: Calibration Suite 7 — COMB_V4_1 (162) & Exact Total 1,351
    ccal = _rcsv(RES / "COMB_V4_1_CALIBRATION_162.csv")
    c6 = [r["comb_v41_hit"] == "True" for r in ccal if r["trial_class"] == "TRUE_6TOOTH_STELLAR_COMB" and float(r["tooth_snr_inj"]) >= 3.8]
    cfor = [r["comb_v41_hit"] == "True" for r in ccal if r["trial_class"] == "DENSE_MOLECULAR_FOREST"]
    ctop = [r["comb_v41_hit"] == "True" for r in ccal if r["trial_class"] == "TOPO_TELLURIC_OR_BG_COMB"]
    tot_trials = len(rp_rows) + len(ag_cal) + len(m_cal) + len(inj) + len(kep) + len(g45) + len(ccal)
    c10_ok = (
        len(ccal) == 162
        and (sum(c6) / len(c6)) >= 0.95
        and (sum(cfor) / len(cfor)) <= 0.05
        and (sum(ctop) / len(ctop)) <= 0.05
        and tot_trials == 1351
    )
    checks.append(_chk(
        "C10_COMB_V41_162_AND_1351_TOTAL",
        c10_ok,
        f"rows={len(ccal)} 6t={sum(c6)}/{len(c6)} for_v41={sum(cfor)}/{len(cfor)} topo_v41={sum(ctop)}/{len(ctop)} total_trials={tot_trials}",
    ))

    # C11: Retroactive D091 RPCA + G7 Regression (2,362 candidates, >=95% suppression)
    retro = _rcsv(RES / "RETROACTIVE_D091_RPCA_REGRESSION.csv")
    n_pass_91 = sum(1 for r in retro if r["g7_pass"] == "True")
    sup_frac = 1.0 - (n_pass_91 / len(retro)) if retro else 0.0
    c11_ok = len(retro) == 2362 and sup_frac >= 0.95
    checks.append(_chk(
        "C11_RETROACTIVE_D091_REGRESSION",
        c11_ok,
        f"d091_in={len(retro)} v50_surv={n_pass_91} suppression={sup_frac*100.0:.3f}%",
    ))

    # C12: Retroactive D090 MIRI Greenhouse CCF (60 cells across 15 targets)
    miri = _rcsv(RES / "MIRI_GREENHOUSE_CCF_D090_15TARGETS.csv")
    quiet_targets = {"16CYGB", "ETACRV", "HD163466", "HD159222", "HD2811", "VMA2", "LAWD37", "49CET"}
    quiet_flags = [r for r in miri if r["star"] in quiet_targets and r["passes_ccf"] == "True"]
    n_miri_flag = sum(1 for r in miri if r["passes_ccf"] == "True")
    c12_ok = len(miri) == 60 and len({r["star"] for r in miri}) == 15 and len(quiet_flags) == 0 and int(faudit["verified_eti_total"]) == 0
    checks.append(_chk(
        "C12_RETROACTIVE_MIRI_GREENHOUSE_60CELLS",
        c12_ok,
        f"cells={len(miri)} targets={len({r['star'] for r in miri})} quiet_ctrl_flags={len(quiet_flags)} disk_dog_flags={n_miri_flag} eti=0",
    ))

    # C13: Independent Pure-Stdlib Radiometric Re-Verification across ALL 122 UL cells
    ul = _rcsv(RES / "STAR_UPPER_LIMITS_D092.csv")
    max_rel_err = 0.0
    for r in ul:
        wa = float(r["wave_bary_a"])
        r_pow = float(r["resolving_power"])
        amp = float(r["amp_rel_8sigma_lim"])
        cflam = float(r["continuum_flam_cgs"])
        d_cm = float(r["dist_pc"]) * PC_CM
        fwhm_a = wa / r_pow
        ew_a = math.sqrt(math.pi / (4.0 * math.log(2.0))) * amp * fwhm_a
        flux_cgs = cflam * ew_a
        l_iso_w = 4.0 * math.pi * d_cm * d_cm * flux_cgs * 1e-7
        theta = (math.pi * 10.0) / (wa * 1e-10)
        p_kw_chk = (l_iso_w / (theta * theta)) / 1000.0
        p_kw_rep = float(r["p_beam_10m_kw"])
        rel_e = abs(p_kw_chk - p_kw_rep) / max(1e-30, p_kw_rep)
        if rel_e > max_rel_err:
            max_rel_err = rel_e
    c13_ok = len(ul) == 122 and max_rel_err < 2e-3
    checks.append(_chk(
        "C13_INDEPENDENT_RADIOMETRIC_122_CELLS",
        c13_ok,
        f"cells={len(ul)} max_rel_err={max_rel_err:.6g}<0.002",
    ))

    # C14: Unified 335-Star Synthesis, 146 <10 pc, 37 Bridges, 9 Campaigns, 386 Comb Stacks
    u335 = _rcsv(RES / "UNIFIED_PANCHROMATIC_V5_0_SYNTHESIS_335STARS.csv")
    s146 = _rcsv(RES / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_146STARS.csv")
    br = _rcsv(RES / "PANCHROMATIC_BRIDGE_35STARS_V50.csv")
    orb9 = _rcsv(RES / "ORBITAL_CAMPAIGN_RESULTS_9.csv")
    allsky = _rcsv(RES / "ALLSKY_COMB_V4_1_UNIFIED_D079_D092.csv")
    syn = summary["unified_335star_panchromatic_v5_0_synthesis"]
    c14_ok = (
        len(u335) == 335
        and len({r["star"] for r in u335}) == 335
        and len(s146) == 146
        and all(float(r["dist_pc"]) <= 10.0 for r in s146)
        and len({r["star"] for r in br}) == 37
        and len(br) == 631
        and len(orb9) == 9
        and all(int(r["verified_eti"]) == 0 for r in orb9)
        and len(allsky) == 386
        and all(int(r["verified_eti_combs"]) == 0 for r in allsky)
        and int(syn["total_exposures_d079_d092"]) == 2133
        and int(syn["total_calibration_trials_d079_d092"]) == 30817
        and int(syn["cumulative_orbital_campaigns"]) == 109
        and all(int(r["verified_eti_detections"]) == 0 for r in u335)
    )
    checks.append(_chk(
        "C14_UNIFIED_335STAR_BRIDGE_ORBITAL_ALLSKY",
        c14_ok,
        f"stars={len(u335)} <10pc={len(s146)} br={len({r['star'] for r in br})}({len(br)}) orb={len(orb9)}/109 stacks={len(allsky)} eti=0",
    ))

    # C15: 4-Stream Forensic Candidate Audit Consistency
    ledger = _rcsv(RES / "V5_0_CANDIDATE_LEDGER.csv")
    ag_surv = _rcsv(RES / "V5_0_AGNOSTIC_MULTISCALE_SURVIVORS.csv")
    comb_c = _rcsv(RES / "COMB_V4_1_CANDIDATES.csv")
    n_v50_led = sum(1 for r in ledger if r["qualified_v50_laser"] == "True")
    c15_ok = (
        n_v50_led == int(faudit["n_v50_qualified"]) == len(faudit["candidates"])
        and len(ag_surv) == int(faudit["n_agnostic_survivors"]) == len(faudit["agnostic_survivors"])
        and len(comb_c) == int(faudit["n_comb_v41_candidates"]) == len(faudit["comb_v41_candidates"])
        and n_miri_flag == int(faudit["n_miri_flagged"]) == len(faudit["miri_flagged"])
        and int(faudit["verified_eti_total"]) == 0
        and all(not c.get("verified_eti", True) for stream in ("candidates", "agnostic_survivors", "comb_v41_candidates", "miri_flagged") for c in faudit[stream])
    )
    checks.append(_chk(
        "C15_FOUR_STREAM_FORENSIC_CONSISTENCY",
        c15_ok,
        f"v50={n_v50_led} ag={len(ag_surv)} comb={len(comb_c)} miri_flag={n_miri_flag} eti=0",
    ))

    # C16: 6 Publication Figures + VISUAL_REVIEW + IMPLEMENTATION_LOCK Verification
    fig_recs = vrev.get("figures", [])
    fig_ok = (
        len(fig_recs) == 6
        and all(r.get("visual_status") == "PASS" for r in fig_recs)
        and all((WS / r["file"]).exists() and (WS / r["file"]).stat().st_size >= 30000 for r in fig_recs)
    )
    impl_hashes = impl_lock.get("locked_files_sha256", {})
    impl_mismatches = [
        fn for fn, exp_h in impl_hashes.items()
        if not (WS / fn).exists() or _sha256(WS / fn) != exp_h
    ]
    c16_ok = fig_ok and len(impl_hashes) >= 6 and not impl_mismatches
    checks.append(_chk(
        "C16_FIGURES_VISUAL_AND_IMPLEMENTATION_LOCK",
        c16_ok,
        f"figs={len(fig_recs)}/6 PASS impl_files={len(impl_hashes)} impl_mismatches={impl_mismatches}",
    ))

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
    out = {
        "schema": "D092_AUDIT_SUMMARY_V1",
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "checks_passed": passed,
        "checks_total": total,
        "overall_status": f"OVERALL: {'PASS' if passed == total else 'FAIL'} ({passed}/{total})",
        "checks": checks,
    }
    (RES / "AUDIT_SUMMARY.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")

    for c in checks:
        print(f"[{c['status']}] {c['check_id']}: {c['detail']}")
    print(out["overall_status"])
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
