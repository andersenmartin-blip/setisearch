#!/usr/bin/env python3
"""Separate scalar reconstruction; preflight and fixed observed-data checks."""
import argparse
import itertools
import json
import math
from pathlib import Path
import statistics

import numpy as np

from common import HERE, dump, gates, inputs, methods, sha

COUNT = 0
MAX_ABS = 0.


def close(actual, expected):
    global COUNT, MAX_ABS
    COUNT += 1
    assert math.isfinite(float(actual)) and math.isfinite(float(expected))
    MAX_ABS = max(MAX_ABS, abs(float(actual)-float(expected)))
    assert math.isclose(float(actual),float(expected),rel_tol=1e-9,abs_tol=1e-8),(actual,expected)


def scalar_fit(w, f, k):
    offsets=list(range(-50,-12))+list(range(13,51))
    sides=[float(f[k+x]) for x in offsets]
    slope=(statistics.median(sides[38:])-statistics.median(sides[:38]))/63.
    intercept=statistics.median(y-slope*x for x,y in zip(offsets,sides))
    residual=[y-intercept-slope*x for x,y in zip(offsets,sides)]
    med=statistics.median(residual)
    scale=1.4826*statistics.median(abs(x-med) for x in residual)
    core=list(range(-12,13))
    values=[float(f[k+x])-intercept-slope*x for x in core]
    step=statistics.median(float(w[j+1])-float(w[j]) for j in range(k-50,k+50))
    width=float(w[k])/115000.
    sigma=width/(2*math.sqrt(2*math.log(2)))
    best=None
    for phase in [-.5,-.25,0,.25,.5]:
        center=float(w[k])+phase*step
        g=[math.exp(-.5*((float(w[k+x])-center)/sigma)**2) for x in core]
        gg=math.fsum(x*x for x in g)
        rg=math.fsum(x*y for x,y in zip(g,values))
        amp=max(0.,rg/gg)
        explained=amp*amp*gg
        norm=math.fsum(x*x for x in values)
        cosine=rg/math.sqrt(gg*norm) if norm>0 else 0.
        record=dict(fitted_center_angstrom=center,phase=phase,amplitude_adu=amp,
                    profile_cosine=cosine,profile_explained_square_adu=explained)
        if best is None or explained>best["profile_explained_square_adu"]:
            best=record
    best.update(sideband_intercept_adu=intercept,sideband_slope_adu_per_pixel=slope,
                sideband_mad_adu=scale,fwhm_model_angstrom=width,
                amplitude_over_sideband_mad=best["amplitude_adu"]/scale if scale>0 else None)
    return best


def check_event(event,w,f):
    reconstructed=scalar_fit(w,f,event["seed_index"])
    for key,value in reconstructed.items():
        if value is None:
            assert event[key] is None
        else:
            close(event[key],value)


def preflight():
    gates(public=False)
    _,detect,cfg,detector=methods()
    for center_wave,negative in itertools.product([3807.13,3861.29,6617.31],[False,True]):
        w=center_wave+(np.arange(1001)-500)*.01
        background=100+np.sin(np.arange(1001)*.31)*.2+np.arange(1001)*.003
        if negative:
            background-=150
        for phase in [0,.25,.5]:
            center=float(w[500]+phase*.01)
            sigma=center/115000/(2*math.sqrt(2*math.log(2)))
            f=background+20*np.exp(-.5*((w-center)/sigma)**2)
            r,_=detect(w,f,cfg)
            accepted=[e for e in r["events"] if e["status"]=="PRELIMINARY_PROFILE_HIT" and abs(e["fitted_center_angstrom"]-center)<=.02000001]
            assert len(accepted)==1
            check_event(accepted[0],w,f)
        spike=background.copy();spike[500]+=20
        r,_=detect(w,spike,cfg)
        assert not any(e["status"]=="PRELIMINARY_PROFILE_HIT" and abs(e["fitted_center_angstrom"]-w[500])<=.02 for e in r["events"])
    dump(HERE / "PREFLIGHT.json",dict(status="PASS_SYNTHETIC_ONLY",scalar_value_checks=COUNT,
                                      max_abs_difference=MAX_ABS,gaussian_cases=18,single_pixel_rejection_cases=6,
                                      signed_negative_backgrounds_tested=True,science_arrays_opened=0,
                                      audit_code_sha256=sha(Path(__file__))))
    print(json.dumps(dict(status="PASS_SYNTHETIC_ONLY",scalar_value_checks=COUNT,max_abs_difference=MAX_ABS)))


def observed():
    _,selected,acquired=inputs()
    read,detect,cfg,_=methods()
    out=HERE / "numerical_review"
    out.mkdir(exist_ok=False)
    trials=json.loads((HERE / "controls/TRIALS.json").read_text())
    freeze=json.loads((HERE / "FREEZE.json").read_text())
    plan=freeze["controls"]
    expected=set(itertools.product(range(4),plan["anchors_air_bary_angstrom"],plan["phases"],plan["amplitudes_original101_population_std"]))
    assert len(trials)==288
    assert {(r["background"],r["anchor_angstrom"],r["phase"],r["amplitude"]) for r in trials}==expected
    backgrounds=[r for r in selected if r["role"]=="fresh_control_only"]
    cache={}
    patch_count=0
    for bi,row in enumerate(backgrounds):
        a=acquired[row["dp_id"]]
        if a.get("header_status")!="PASS_METADATA_ONLY":continue
        w,f,_=read(HERE / a["relative_path"])
        for ai,anchor in enumerate(plan["anchors_air_bary_angstrom"]):
            path=HERE / "controls" / f"background{bi}_anchor{ai}.npz"
            with np.load(path,allow_pickle=False) as z:
                ww,ff,ix=z["wave"],z["flux"],z["original_indices"]
                assert np.array_equal(ww,w[ix]) and np.array_equal(ff,f[ix],equal_nan=True)
                assert str(z["input_sha256"])==a["sha256"]
                cache[(bi,anchor)]=(ww,ff)
                patch_count+=1
    replayed=0
    for trial in trials:
        if trial["status"]!="EVALUATED":continue
        w,f=cache[(trial["background"],trial["anchor_angstrom"])]
        distances=[abs(float(x)-trial["center_angstrom"]) for x in w]
        smallest=min(distances)
        k=next(i for i,x in enumerate(distances) if x<=smallest+1e-9)
        values=[float(x) for x in f[k-50:k+51]]
        mean=math.fsum(values)/101
        noise=math.sqrt(math.fsum((x-mean)**2 for x in values)/101)
        close(trial["original_std_adu"],noise)
        sigma=trial["center_angstrom"]/115000/(2*math.sqrt(2*math.log(2)))
        injected=np.array([float(y)+trial["amplitude"]*noise*math.exp(-.5*((float(x)-trial["center_angstrom"])/sigma)**2) for x,y in zip(w,f)])
        result,_=detect(w,injected,cfg)
        recovered=any(e["status"]=="PRELIMINARY_PROFILE_HIT" and abs(e["fitted_center_angstrom"]-trial["center_angstrom"])<=.02000001 for e in result["events"])
        assert recovered==trial["v2_recovered"]
        saved=json.loads((HERE / "controls" / trial["trial_file"]).read_text())["result"]
        assert [(e["seed_index"],e["status"]) for e in saved["events"]]==[(e["seed_index"],e["status"]) for e in result["events"]]
        for event in saved["events"]:
            check_event(event,w,injected)
        replayed+=1
    main_rows=[r for r in selected if r["role"]=="fresh_main_unopened"]
    hits=json.loads((HERE / "production/HITS.json").read_text())
    full_reproductions=[]
    checked_hits=0
    for index,row in enumerate(main_rows):
        a=acquired[row["dp_id"]]
        if a.get("header_status")!="PASS_METADATA_ONLY":continue
        own=[h for h in hits if h["dp_id"]==row["dp_id"]]
        if not own and index not in [0,24,49]:continue
        w,f,_=read(HERE / a["relative_path"])
        for event in own:
            check_event(event,w,f)
            with np.load(HERE / "production" / event["evidence_window"],allow_pickle=False) as z:
                assert np.array_equal(z["flux"],f[z["original_indices"]],equal_nan=True)
                assert np.array_equal(z["wave"],w[z["original_indices"]])
            checked_hits+=1
        if index in [0,24,49]:
            saved=json.loads((HERE / "production/spectra" / (row["dp_id"].replace(":","_")+".json")).read_text())
            reproduced,_=detect(w,f,cfg)
            assert saved==reproduced
            full_reproductions.append(dict(selection_index=index+1,dp_id=row["dp_id"],status="EXACT_SEMANTIC_MATCH"))
    assert checked_hits==len(hits)
    summary=dict(status="PASS_SCALAR_RECONSTRUCTION_AND_FIXED_REPLAYS",scalar_value_checks=COUNT,max_abs_scalar_difference=MAX_ABS,
                 source_bound_control_patches=patch_count,registered_control_slots=288,reconstructed_evaluated_controls=replayed,
                 accepted_main_events_scalar_checked=checked_hits,full_main_reproductions=full_reproductions,
                 no_numeric_output_overwritten=True,same_assistant_review=True,independent_agent_or_researcher_review=False,
                 qualification="Scalar source/injection/fit reconstruction plus unchanged-detector control replays and three fixed complete main replays; not an independent instrument reduction or complete scalar scan of every rejected main seed.")
    dump(out / "SUMMARY.json",summary)
    print(json.dumps(summary),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=["preflight","observed"])
    preflight() if parser.parse_args().phase=="preflight" else observed()
