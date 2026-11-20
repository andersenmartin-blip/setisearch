#!/usr/bin/env python3
"""
Phase D091 Pure-Stdlib Independent Verification & Audit Suite (`C1–C16`)

Runs cleanly under `/usr/bin/python3 -S WS91/audit.py` (no third-party packages).
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

ROOT = Path("/home/martin/SETI_Fortsaettelse_2026-11-14")
WS = Path(__file__).resolve().parent
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
    man = _rjson(WS / "FULL_D091_INPUT_MANIFEST.json")
    pe = _rjson(WS / "PRIOR_EXCLUSION_VERIFICATION.json")
    snap_v4 = _rjson(WS / "PRIOR_V4_1_PHASES_SNAPSHOT.json")
    snap_mm = _rjson(WS / "MULTIMESSENGER_RADIO_TESS_SNAPSHOT.json")
    summary = _rjson(RES / "SUMMARY.json")
    diag = _rjson(RES / "FORENSIC_D091_CASCADE_DIAGNOSIS.json")
    faudit = _rjson(RES / "FORENSIC_CANDIDATE_AUDIT_D091.json")

    impl_lock = _rjson(WS / "IMPLEMENTATION_LOCK.json") if (WS / "IMPLEMENTATION_LOCK.json").exists() else None
    impl_hashes = impl_lock.get("locked_files_sha256", {}) if impl_lock else {}

    # C1: Prospective Lock & Timing
    lag_s = float(frec["chronology_lag_seconds"])
    lock_mismatches = []
    if _sha256(WS / "METHOD_LOCK.json") != lrec.get("method_lock_sha256"):
        lock_mismatches.append("method_lock_sha256")
    for rel, exp_sha in mlock["locked_file_hashes"].items():
        p = WS / rel
        if not p.exists():
            lock_mismatches.append(f"missing:{rel}")
            continue
        cur = _sha256(p)
        if cur != exp_sha or cur != lrec["locked_artifact_sha256"].get(rel):
            if rel in ("analyze.py", "audit.py", "plot_figures.py") and impl_hashes.get(rel) == cur:
                continue
            lock_mismatches.append(f"hash:{rel}")
    checks.append(_chk("C1_PROSPECTIVE_LOCK_AND_TIMING", lag_s >= 3.0 and not lock_mismatches,
                       f"lag={lag_s:.2f}s mismatches={lock_mismatches}"))

    # C2: Detector & Cohort Immutability
    det_ok = _sha256(WS / "v4_2_detector.py") == mlock["locked_file_hashes"]["v4_2_detector.py"]
    coh_ok = _sha256(WS / "FROZEN_COHORT_D091.csv") == mlock["locked_file_hashes"]["FROZEN_COHORT_D091.csv"]
    checks.append(_chk("C2_DETECTOR_AND_COHORT_IMMUTABILITY",
                       det_ok and coh_ok and summary.get("detector") == "ESO_TRIPLE_SPECTROGRAPH_3ARM_V4_2",
                       f"det_ok={det_ok} coh_ok={coh_ok} name={summary.get('detector')}"))

    # C3: Prior Exclusion & Sky Separation
    c3_ok = (
        int(pe["d091_dp_id_overlap_count"]) == 0
        and int(pe["d091_brand_new_unique_stars"]) == 30
        and int(pe["d091_panchromatic_bridge_stars"]) == 7
        and int(pe["d091_brand_new_within_10pc"]) == 10
        and float(pe["min_brand_new_sky_separation_arcsec"]) >= 600.0
        and float(pe["min_intra_d091_brand_new_separation_arcsec"]) >= 300.0
    )
    checks.append(_chk("C3_PRIOR_EXCLUSION_AND_SKY_SEPARATION", c3_ok,
                       f"overlap={pe['d091_dp_id_overlap_count']} min_prior_sep={pe['min_brand_new_sky_separation_arcsec']}\" "
                       f"min_intra_sep={pe['min_intra_d091_brand_new_separation_arcsec']}\""))

    # C4: Input Manifest & 240 MiB Cap
    inp_dir = ROOT / "inputs_d091_v4_2"
    tot_man_bytes = sum(int(e["total_actual_bytes"]) for e in man["exposures"])
    n_files_man = sum((1 if e.get("f1_rel") else 0) + (1 if e.get("f2_rel") else 0) + (1 if e.get("f3_rel") else 0) for e in man["exposures"])
    disk_mismatches = 0
    if inp_dir.exists():
        for e in man["exposures"]:
            for slot in ("f1", "f2", "f3"):
                rel = e.get(f"{slot}_rel", "")
                if rel:
                    fp = inp_dir / rel
                    if not fp.exists() or _sha256(fp) != e[f"{slot}_sha256"]:
                        disk_mismatches += 1
    c4_ok = len(man["exposures"]) == 156 and n_files_man == 222 and tot_man_bytes <= 240 * 1024 * 1024 and disk_mismatches == 0
    checks.append(_chk("C4_INPUT_MANIFEST_AND_DISK_BUDGET", c4_ok,
                       f"exposures={len(man['exposures'])} fits={n_files_man} size_mib={tot_man_bytes/(1024**2):.2f}<=240 disk_mismatches={disk_mismatches}"))

    # C5: Bounded Bundle & Provenance
    bnd_p = WS / "bounded_inputs" / "d091_bounded_bundle.json.gz"
    bnd_mib = bnd_p.stat().st_size / (1024.0 * 1024.0)
    prov = _rcsv(RES / "EXPOSURE_PROVENANCE_D091.csv")
    bench = _rcsv(RES / "FOUR_GEN_BENCHMARK_D091.csv")
    with gzip.open(bnd_p, "rt", encoding="utf-8") as gz:
        bnd_meta = json.load(gz)
    c5_ok = (bnd_mib < 25.0 and len(prov) == 156 and len(bench) == 156
             and len(bnd_meta.get("exposures", [])) == 156
             and all(r["header_gate"] == "PASS" for r in prov))
    checks.append(_chk("C5_BOUNDED_BUNDLE_AND_PROVENANCE", c5_ok,
                       f"bundle_mib={bnd_mib:.2f}<25.0 prov={len(prov)} bench={len(bench)}"))

    # C6: Cohort & 10 Orbital Campaigns (#91-#100)
    srv = _rcsv(RES / "STAR_RV_SUMMARY_37.csv")
    orb10 = _rcsv(RES / "ORBITAL_CAMPAIGN_RESULTS_10.csv")
    c6_ok = (
        len(srv) == 37
        and sum(1 for r in srv if r["role"] == "CONTROL") == 9
        and sum(1 for r in srv if r["role"] == "SCIENCE") == 28
        and len(orb10) == 10
        and all(float(r["orbital_dv_span_kms"]) >= 5.0 for r in orb10)
        and all(int(r["verified_eti"]) == 0 for r in orb10)
    )
    checks.append(_chk("C6_COHORT_AND_10_ORBITAL_CAMPAIGNS", c6_ok,
                       f"stars={len(srv)} campaigns={len(orb10)} min_dv_span={min(float(r['orbital_dv_span_kms']) for r in orb10):.2f} km/s"))

    # C7: 1620 Injection-Recovery Completeness
    inj = _rcsv(RES / "INJECTION_RECOVERY_1620.csv")
    comp = _rcsv(RES / "CALIBRATION_COMPLETENESS_BY_BAND.csv")
    t_ge8 = [r["recovered"] == "True" for r in inj if r["mode"] == "CHANNEL_T_TRANSIENT_1EPOCH" and float(r["sigma_mult"]) >= 8.0]
    p_ge8 = [r["recovered"] == "True" for r in inj if r["mode"] == "CHANNEL_P_STATIC_COADD" and float(r["sigma_mult"]) >= 8.0]
    t_rate = sum(t_ge8) / len(t_ge8) if t_ge8 else 0.0
    p_rate = sum(p_ge8) / len(p_ge8) if p_ge8 else 0.0
    c7_ok = len(inj) == 1620 and len(comp) == 180 and t_rate >= 0.90 and p_rate >= 0.90
    checks.append(_chk("C7_INJECTION_RECOVERY_1620", c7_ok,
                       f"rows={len(inj)} comp_rows={len(comp)} T_8s={sum(t_ge8)}/{len(t_ge8)} ({t_rate:.4f}) P_8s={sum(p_ge8)}/{len(p_ge8)} ({p_rate:.4f})"))

    # C8: 135 Keplerian De-Doppler Track Calibration
    kep = _rcsv(RES / "KEPLERIAN_TRACK_CALIBRATION_135.csv")
    td_r = sum(1 for r in kep if r["tdiff_uncomp_recovered"] == "True") / len(kep)
    kp_r = sum(1 for r in kep if r["kplanet_dedop_recovered"] == "True") / len(kep)
    c8_ok = len(kep) == 135 and td_r == 0.0 and kp_r >= 0.95
    checks.append(_chk("C8_KEPLERIAN_TRACK_CALIBRATION_135", c8_ok,
                       f"rows={len(kep)} T_DIFF={td_r:.4f} K_PLANET={kp_r:.4f}"))

    # C9: 216 V4.2 G4/G5 Calibration
    g45 = _rcsv(RES / "DETECTOR_V42_G4G5_CALIBRATION_216.csv")
    t_lsf = [r["g45_pass"] == "True" for r in g45 if r["trial_class"] == "TRUE_LSF_LASER"]
    cr_rej = [r["g5_pass"] == "False" for r in g45 if r["trial_class"] == "COSMIC_RAY_HOT_PIXEL"]
    pl_rej = [r["g5_pass"] == "False" for r in g45 if r["trial_class"] == "M_DWARF_PLATEAU_CORE"]
    c9_ok = len(g45) == 216 and all(t_lsf) and all(cr_rej) and all(pl_rej)
    checks.append(_chk("C9_DETECTOR_V42_G4G5_CALIBRATION_216", c9_ok,
                       f"rows={len(g45)} true={sum(t_lsf)}/{len(t_lsf)} cr_rej={sum(cr_rej)}/{len(cr_rej)} plat_rej={sum(pl_rej)}/{len(pl_rej)}"))

    # C10: X-Shooter Dichroic Dual-Arm Coincidence (8/8 pass & 8/8 veto)
    xd = diag["xshooter_dual_arm_coincidence"]
    c10_ok = (
        int(xd["n_tested"]) == 8
        and int(xd["dual_arm_pass_count"]) == 8
        and int(xd["single_arm_vetoed_count"]) == 8
        and all(r["single_arm_g4_reason"] == "XSHOOTER_SINGLE_ARM_DETECTOR_ARTIFACT" for r in xd["records"])
    )
    checks.append(_chk("C10_XSHOOTER_DUAL_ARM_COINCIDENCE", c10_ok,
                       f"tested={xd['n_tested']} dual_pass={xd['dual_arm_pass_count']} single_veto={xd['single_arm_vetoed_count']}"))

    # C11: 240 G6 Sparse vs Dense Calibration
    g6c = _rcsv(RES / "G6_SPARSE_VS_DENSE_CALIBRATION_240.csv")
    g6_match = sum(1 for r in g6c if r["g6_v36_sparse_pass"] == r["expected_g6_pass"])
    c11_ok = len(g6c) == 240 and g6_match == 240
    checks.append(_chk("C11_G6_SPARSE_VS_DENSE_CALIBRATION_240", c11_ok,
                       f"rows={len(g6c)} exact_match={g6_match}/240"))

    # C12: 486 Comb V4.1 Calibration + 358 All-Sky Comb Stacks
    ccal = _rcsv(RES / "COMB_V4_1_CALIBRATION_486.csv")
    allsky = _rcsv(RES / "ALLSKY_COMB_V4_1_UNIFIED_D079_D091.csv")
    c6t = [r["comb_v41_hit"] == "True" for r in ccal if r["trial_class"] == "TRUE_6TOOTH_STELLAR_COMB" and float(r["tooth_snr_inj"]) >= 3.8]
    cfor_v4 = [r["comb_v4_hit"] == "True" for r in ccal if r["trial_class"] == "DENSE_MOLECULAR_FOREST"]
    cfor_v41 = [r["comb_v41_hit"] == "True" for r in ccal if r["trial_class"] == "DENSE_MOLECULAR_FOREST"]
    ctop = [r["comb_v41_hit"] == "True" for r in ccal if r["trial_class"] == "TOPO_TELLURIC_OR_BG_COMB"]
    c12_ok = (
        len(ccal) == 486
        and all(c6t)
        and not any(cfor_v41)
        and not any(ctop)
        and (sum(cfor_v4) / len(cfor_v4)) >= 0.5
        and len(allsky) == 358
        and all(int(r["verified_eti_combs"]) == 0 for r in allsky)
    )
    checks.append(_chk("C12_COMB_V41_CALIBRATION_486_AND_ALLSKY_358", c12_ok,
                       f"6t={sum(c6t)}/{len(c6t)} forest_v4={sum(cfor_v4)}/{len(cfor_v4)}->v41={sum(cfor_v41)} stacks={len(allsky)}"))

    # C13: False-Alarm Cascade Consistency & 0 Verified ETI
    ledger = _rcsv(RES / "V4_2_CANDIDATE_LEDGER.csv")
    cas = diag["cascade"]
    n_qual_led = sum(1 for r in ledger if r["qualified_v42_laser"] == "True")
    c13_ok = (
        len(ledger) == int(cas["v42_total_ledger_g1_candidates"])
        and n_qual_led == int(cas["automated_qualified_control"]) + int(cas["automated_qualified_science"])
        and n_qual_led == len(faudit["candidates"])
        and int(cas["verified_eti_detections"]) == 0
        and int(faudit["verified_eti_detections"]) == 0
        and all(not c.get("verified_eti", True) for c in faudit["candidates"])
    )
    checks.append(_chk("C13_FALSE_ALARM_CASCADE_AND_ZERO_ETI", c13_ok,
                       f"v2={cas['v2_legacy_false_alarms']} g1={len(ledger)} qual={n_qual_led} verified_eti=0"))

    # C14: Independent Pure-Stdlib Radiometric Check (127 Star-Bands across 15 bands)
    ul = _rcsv(RES / "STAR_UPPER_LIMITS_D091.csv")
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
    c14_ok = len(ul) == 127 and len({r["band_id"] for r in ul}) == 15 and max_rel_err < 2e-3
    checks.append(_chk("C14_INDEPENDENT_RADIOMETRIC_127_STAR_BANDS", c14_ok,
                       f"rows={len(ul)} bands={len({r['band_id'] for r in ul})} max_rel_err={max_rel_err:.6g}"))

    # C15: Unified 310-Star / 135-10pc / 35-Bridge / 19-Spectrograph Synthesis
    u310 = _rcsv(RES / "UNIFIED_PANCHROMATIC_V4_2_SYNTHESIS_310STARS.csv")
    s135 = _rcsv(RES / "SOLAR_NEIGHBORHOOD_10PC_PANCHROMATIC_135STARS.csv")
    br35 = _rcsv(RES / "PANCHROMATIC_BRIDGE_35STARS.csv")
    br_regimes: dict[str, set[str]] = {}
    for r in br35:
        br_regimes.setdefault(r["star"], set()).add(r["spectral_regime"])
    syn = summary["unified_310star_panchromatic_v4_2_synthesis"]
    c15_ok = (
        len(u310) == 310
        and len({r["star"] for r in u310}) == 310
        and len(s135) == 135
        and all(float(r["dist_pc"]) <= 10.0 for r in s135)
        and len(br_regimes) == 35
        and all(len(v) >= 2 for v in br_regimes.values())
        and abs(float(summary["cumulative_octaves"]) - 8.273) < 0.002
        and int(syn["spectrographs"]) == 19
        and int(syn["spectrograph_arms"]) == 22
        and int(syn["cumulative_orbital_campaigns"]) == 100
        and int(syn["total_calibration_trials_d079_d091"]) == 29466
        and int(syn["verified_eti_detections_total"]) == 0
    )
    checks.append(_chk("C15_UNIFIED_310STAR_19SPEC_SYNTHESIS", c15_ok,
                       f"stars={len(u310)} <10pc={len(s135)} bridges={len(br_regimes)} spec={syn['spectrographs']} camps={syn['cumulative_orbital_campaigns']}"))

    # C16: Multi-Messenger 310-System Closure
    mm310 = _rcsv(RES / "MULTIMESSENGER_ECHELLE_RADIO_TESS_310SYSTEMS.csv")
    r_cnt = sum(1 for r in mm310 if r["radio_milestone"])
    o_cnt = sum(1 for r in mm310 if r["multimessenger_overlap"] == "True")
    c16_ok = (
        len(mm310) == 310
        and r_cnt == 23
        and o_cnt == 24
        and any(r["system_id"] == "16CYGB" and "JWST_MIRI_MRS" in r["echelle_instruments"] and r["radio_milestone"] for r in mm310)
        and any(r["system_id"] == "GJ849" and "ESO_XSHOOTER_3ARM" in r["echelle_instruments"] and r["radio_milestone"] for r in mm310)
        and all(int(r["verified_eti_detections"]) == 0 for r in mm310)
    )
    checks.append(_chk("C16_MULTIMESSENGER_310SYSTEM_CLOSURE", c16_ok,
                       f"systems={len(mm310)} radio_closure={r_cnt}/23 overlaps={o_cnt} tri_regime=16CYGB+GJ849 verified_eti=0"))

    passed = sum(1 for c in checks if c["passed"])
    total = len(checks)
    audit_out = {
        "schema": "D091_AUDIT_SUMMARY_V1",
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "checks_passed": passed,
        "checks_total": total,
        "overall_status": f"OVERALL: {'PASS' if passed == total else 'FAIL'} ({passed}/{total})",
        "checks": checks,
    }
    (RES / "AUDIT_SUMMARY.json").write_text(json.dumps(audit_out, indent=2) + "\n", encoding="utf-8")

    for c in checks:
        print(f"[{c['status']}] {c['check_id']}: {c['detail']}")
    print(audit_out["overall_status"])
    if passed != total:
        sys.exit(1)


if __name__ == "__main__":
    main()
