#!/usr/bin/env python3
"""One-shot fixed V2 controls and a separate fifty-exposure main search."""
import argparse
from collections import Counter
import json
import math

import numpy as np

from common import HERE, csvout, dump, inputs, methods, now, sha


def nearest(wave, center):
    distance = np.abs(wave-center)
    return int(np.flatnonzero(distance <= distance.min()+1e-9)[0])


def matched(result, center):
    return any(e["status"] == "PRELIMINARY_PROFILE_HIT" and
               abs(e["fitted_center_angstrom"]-center) <= .02000001 for e in result["events"])


def base_trial(bi, row, anchor, phase, amplitude):
    return dict(background=bi, dp_id=row["dp_id"], target=row["canonical_target"], anchor_angstrom=anchor,
                phase=phase, amplitude=amplitude, status="NOT_EVALUATED", center_angstrom=None,
                original_std_adu=None, peak_added_adu=None, fwhm_angstrom=None,
                v2_recovered=None, unmodified_control_match=None, recovered_without_control_match=None,
                patch_file=None, trial_file=None, original_nonpositive_samples=None)


def controls():
    freeze, selected, acquired = inputs()
    read, detect, cfg, _ = methods()
    plan = freeze["controls"]
    out = HERE / "controls"
    out.mkdir(exist_ok=False)
    background_rows = [r for r in selected if r["role"] == "fresh_control_only"]
    trials, control_rows, full_rows = [], [], []
    dump(out / "RUN_INPUTS.json", dict(started_utc=now(), freeze_sha256=sha(HERE / "FREEZE.json"),
                                       acquisition_manifest_sha256=sha(HERE / "acquisition/MANIFEST.json")))
    for bi, row in enumerate(background_rows):
        a = acquired[row["dp_id"]]
        admitted = a.get("header_status") == "PASS_METADATA_ONLY"
        if admitted:
            w, f, meta = read(HERE / a["relative_path"])
            assert meta["SPECSYS"] == "BARYCENT" and meta["wavelength_ucd"] == "em.wl;obs.atmos"
            full, _ = detect(w, f, cfg)
            dump(out / f"background{bi}_full.json", full)
            full_rows.append(dict(background=bi, dp_id=row["dp_id"], target=row["canonical_target"],
                                  status="COMPLETED_CONTROL_ONLY", hits=full["preliminary_hit_count"],
                                  searched_samples=full["searched_samples"]))
        else:
            full_rows.append(dict(background=bi, dp_id=row["dp_id"], target=row["canonical_target"],
                                  status="NOT_EVALUABLE_NO_ADMITTED_INPUT", hits=None, searched_samples=0))
        for ai, anchor in enumerate(plan["anchors_air_bary_angstrom"]):
            status, patch_name = "NOT_EVALUABLE_NO_ADMITTED_INPUT", None
            nonpositive = None
            if admitted:
                center_index = nearest(w, anchor)
                start, end = center_index-500, center_index+501
                ww, ff = w[max(0,start):min(len(w),end)], f[max(0,start):min(len(w),end)]
                patch_name = f"background{bi}_anchor{ai}.npz"
                np.savez_compressed(out / patch_name, wave=ww, flux=ff,
                                    original_indices=np.arange(max(0,start),min(len(w),end)),
                                    input_sha256=np.array(a["sha256"]))
                nonpositive = int(np.count_nonzero(np.isfinite(ff) & (ff<=0)))
                status = "EVALUATED"
                if len(ww) != 1001:
                    status = "NOT_EVALUABLE_PARTIAL_PATCH"
                elif not np.all(np.isfinite(ww)) or not np.all(np.abs(np.diff(ww)-.01)<1e-8):
                    status = "NOT_EVALUABLE_FIXED_GRID"
                elif not np.all(np.isfinite(ff)) or np.any(ff==0):
                    status = "NOT_EVALUABLE_NONFINITE_OR_ZERO_FILL"
                if status == "EVALUATED":
                    unmodified, _ = detect(ww, ff, cfg)
                    dump(out / f"background{bi}_anchor{ai}_unmodified.json", unmodified)
            for phase in plan["phases"]:
                center, noise, control = None, None, None
                phase_status = status
                if status == "EVALUATED":
                    center = float(ww[500]+phase*.01)
                    k = nearest(ww, center)
                    noise = float(np.std(ff[k-50:k+51], ddof=0))
                    if not math.isfinite(noise) or noise<=0:
                        phase_status, noise = "NOT_EVALUABLE_NO_POSITIVE_SCALE", None
                    else:
                        control = matched(unmodified, center)
                control_rows.append(dict(background=bi, dp_id=row["dp_id"], target=row["canonical_target"],
                                         anchor_angstrom=anchor, phase=phase, status=phase_status,
                                         center_angstrom=center, matching_v2_hit=control))
                for amplitude in plan["amplitudes_original101_population_std"]:
                    trial = base_trial(bi,row,anchor,phase,amplitude)
                    trial.update(status=phase_status, center_angstrom=center, original_std_adu=noise,
                                 unmodified_control_match=control, patch_file=patch_name,
                                 original_nonpositive_samples=nonpositive)
                    if phase_status == "EVALUATED":
                        sigma = center/115000/(2*np.sqrt(2*np.log(2)))
                        added = amplitude*noise*np.exp(-.5*((ww-center)/sigma)**2)
                        result, _ = detect(ww, ff+added, cfg)
                        recovered = matched(result, center)
                        trial.update(peak_added_adu=amplitude*noise, fwhm_angstrom=center/115000,
                                     v2_recovered=recovered, recovered_without_control_match=recovered and not control)
                        trial["trial_file"] = f"trial_{len(trials)+1:03d}.json"
                        dump(out / trial["trial_file"],dict(trial=trial,result=result))
                    trials.append(trial)
    assert len(background_rows)==4 and len(trials)==288 and len(control_rows)==72
    csvout(out / "TRIALS.csv", trials)
    dump(out / "TRIALS.json", trials)
    dump(out / "UNMODIFIED_CONTROLS.json", control_rows)
    dump(out / "FULL_BACKGROUND_COUNTS.json", full_rows)
    recovery=[]
    for target in sorted({r["canonical_target"] for r in background_rows})+["ALL_CONTROL_TARGETS"]:
        for anchor in plan["anchors_air_bary_angstrom"]:
            for amp in plan["amplitudes_original101_population_std"]:
                group=[t for t in trials if t["anchor_angstrom"]==anchor and t["amplitude"]==amp and
                       (target=="ALL_CONTROL_TARGETS" or t["target"]==target)]
                valid=[t for t in group if t["status"]=="EVALUATED"]
                recovery.append(dict(target=target,anchor_angstrom=anchor,amplitude=amp,registered=len(group),
                                     evaluated=len(valid),not_evaluable=len(group)-len(valid),
                                     recovered=sum(t["v2_recovered"] for t in valid),
                                     recovered_without_control_match=sum(t["recovered_without_control_match"] for t in valid)))
    csvout(out / "RECOVERY_BY_TARGET_ANCHOR_STRENGTH.csv", recovery)
    valid=[t for t in trials if t["status"]=="EVALUATED"]
    summary=dict(status="COMPLETE_FIXED_CONTROL_DESIGN_NO_TUNING", registered=288,evaluated=len(valid),
                 not_evaluable=288-len(valid),unique_background_stars=2,registered_unique_patches=24,
                 registered_geometries=72,status_counts=dict(Counter(t["status"] for t in trials)),
                 unmodified_matching_control_queries=sum(t["matching_v2_hit"] is True for t in control_rows),
                 by_amplitude=[dict(amplitude=amp,registered=72,
                                    evaluated=sum(t["amplitude"]==amp for t in valid),
                                    recovered=sum(t["v2_recovered"] for t in valid if t["amplitude"]==amp),
                                    recovered_without_control_match=sum(t["recovered_without_control_match"] for t in valid if t["amplitude"]==amp))
                               for amp in plan["amplitudes_original101_population_std"]],
                 any_signed_source_samples_retained=any((t["original_nonpositive_samples"] or 0)>0 for t in trials),
                 limitation="Conditional recovery in two fresh stars' reduced1D spectra; shared backgrounds/phases/strengths are dependent; not instrument completeness, physical power or a global false-alarm rate.")
    dump(out / "SUMMARY.json",summary)
    print(json.dumps(summary),flush=True)


def main_search():
    freeze, selected, acquired=inputs()
    assert (HERE / "controls/SUMMARY.json").exists(), "Execute fixed controls before main; no adaptation"
    read, detect, cfg, _=methods()
    out=HERE / "production"
    out.mkdir(exist_ok=False)
    (out / "spectra").mkdir()
    (out / "hit_windows").mkdir()
    exposures,hits,screened=[],[],[]
    dump(out / "RUN_INPUTS.json",dict(started_utc=now(),freeze_sha256=sha(HERE / "FREEZE.json"),
                                      acquisition_manifest_sha256=sha(HERE / "acquisition/MANIFEST.json"),
                                      controls_summary_sha256=sha(HERE / "controls/SUMMARY.json"),no_adaptation=True))
    for index,row in enumerate((r for r in selected if r["role"]=="fresh_main_unopened"),1):
        a=acquired[row["dp_id"]]
        exposure=dict(selection_index=index,target=row["canonical_target"],dp_id=row["dp_id"],
                      raw_progenitor_id=row["raw_progenitor_id"],input_sha256=a.get("sha256"),
                      status="NOT_ANALYZED_NO_ADMITTED_INPUT",exposure_seconds=None,searched_samples=0,
                      sum_searched_bin_widths_angstrom=0,screened_events=0,accepted_hits=0,
                      observation_utc=a.get("primary_header",{}).get("DATE-OBS"),result_file=None)
        if a.get("header_status")=="PASS_METADATA_ONLY":
            w,f,meta=read(HERE / a["relative_path"])
            assert meta["SPECSYS"]=="BARYCENT" and meta["wavelength_ucd"]=="em.wl;obs.atmos"
            result,arrays=detect(w,f,cfg)
            result_name="spectra/"+row["dp_id"].replace(":","_")+".json"
            dump(out / result_name,result)
            exposure.update(status="COMPLETED",exposure_seconds=a["primary_header"]["EXPTIME"],
                            searched_samples=result["searched_samples"],
                            sum_searched_bin_widths_angstrom=result["sum_searched_bin_widths_angstrom"],
                            screened_events=result["screened_events"],accepted_hits=result["preliminary_hit_count"],
                            result_file=result_name)
            for event in result["events"]:
                record=dict(selection_index=index,dp_id=row["dp_id"],target=row["canonical_target"],
                            input_sha256=a["sha256"],raw_id=row["raw_progenitor_id"],**event)
                screened.append(record)
                if event["status"]=="PRELIMINARY_PROFILE_HIT":
                    event_id=f"D002-{len(hits)+1:04d}"
                    k=event["seed_index"]
                    first,last=max(0,k-100),min(len(w),k+101)
                    window="hit_windows/"+event_id+".npz"
                    np.savez_compressed(out / window,wave=np.asarray(w[first:last]),flux=np.asarray(f[first:last]),
                                        original_indices=np.arange(first,last),searched=arrays["searched"][first:last],
                                        input_sha256=np.array(a["sha256"]))
                    hits.append(dict(candidate_id=event_id,**record,origin_status="UNREVIEWED_1D_TRIGGER",
                                     observation_utc=a["primary_header"]["DATE-OBS"],
                                     berv_km_s=a["primary_header"]["HIERARCH ESO DRS BERV"],
                                     evidence_window=window,raw_review_completed=False,qualified_laser=False))
        exposures.append(exposure)
        print(json.dumps({k:exposure[k] for k in ("selection_index","target","status","accepted_hits")}),flush=True)
    assert len(exposures)==50
    csvout(out / "EXPOSURES.csv",exposures)
    dump(out / "ALL_SCREENED_EVENTS.json",screened)
    dump(out / "HITS.json",hits)
    csvout(out / "HITS.csv",hits,fields=list(hits[0]) if hits else ["candidate_id","dp_id","target","origin_status"])
    completed=[e for e in exposures if e["status"]=="COMPLETED"]
    summary=dict(status="COMPLETE_BOUNDED_SEARCH_ALL_TRIGGERS_UNREVIEWED",selected=50,completed=len(completed),
                 not_analyzed=50-len(completed),selected_target_labels=10,completed_target_labels=len({e["target"] for e in completed}),
                 completed_exposure_seconds=sum(e["exposure_seconds"] for e in completed),
                 searched_samples=sum(e["searched_samples"] for e in completed),
                 sum_searched_bin_widths_angstrom=sum(e["sum_searched_bin_widths_angstrom"] for e in completed),
                 screened_events=len(screened),screened_status_counts=dict(Counter(e["status"] for e in screened)),
                 accepted_trigger_rows=len(hits),raw_review_completed=0,qualified_laser_candidates=0,
                 incomplete_physical_review=True,V1_applied=False,V2_unchanged=True,new_telescope_observations=0,
                 limitation="New archive exposures in a bounded alphabetical cohort. All triggers retained; no raw-origin review, global sensitivity/FAP, continuous monitoring or calibrated survey null.")
    dump(out / "SUMMARY.json",summary)
    print(json.dumps(summary),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=["controls","main"])
    phase=parser.parse_args().phase
    controls() if phase=="controls" else main_search()
