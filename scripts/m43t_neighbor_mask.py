#!/usr/bin/env python3
"""Frozen mask repair, fresh paired nulls, and native regression experiment."""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import subprocess
import time
import numpy as np
from m43e_economical_bank import read_sealed,write_sealed
from m43f_source_cache_preflight import build_context
from m43q_integrated_detector import AnchorStore,NativeReceiver
from m43r_joint_calibration import ROOT,grid_context,sha,compact
from m43s_profile_sensitivity import endpoint
from seti_repeater import search_v0p6 as core
from seti_repeater import detector_m43t as detector
from seti_repeater.mask_m43t import POLICIES,build_mask,reference_mask
from seti_repeater.injection_m43r import ScoreStore
from seti_repeater.injection_m43s import ProfileOverlay

CONFIG=ROOT/'config/m43t_neighbor_mask.json'
OUT=ROOT/'results_m43t_neighbor_mask'


def frozen(commit):
    cfg=json.loads(CONFIG.read_text())
    if subprocess.check_output(['git','show',commit+':config/m43t_neighbor_mask.json'],cwd=ROOT)!=CONFIG.read_bytes():
        raise ValueError('configuration differs from public freeze')
    for name,h in cfg['pinned_sha256'].items():
        if sha(ROOT/name)!=h:raise ValueError('frozen dependency changed: '+name)
    if np.__version__!=cfg['numpy_version'] or platform.python_version()!=cfg['python_version']:
        raise ValueError('numerical runtime changed')
    if cfg['policies']!=POLICIES:raise ValueError('policy differs from freeze')
    return cfg


def mask_anchors(store,template_count):
    rows=[]
    for kind in ('on','off'):
        for t in range(template_count):
            arrays={w:store.get(kind,t,w)[0] for w in core.M37_SPECTRAL_WIDTHS}
            masks={p:build_mask(arrays.__getitem__,p) for p in POLICIES}
            for p,m in masks.items():
                if not np.array_equal(m,reference_mask(arrays.__getitem__,p)):
                    raise ValueError('independent mask anchor mismatch')
            if np.any(masks['neighbor2']&~masks['legacy']):raise ValueError('mask subset property failed')
            rows.append({'kind':kind,'template_index':t,'bits_per_policy':masks['legacy'].size,
                'masked_bits':{p:int(m.sum()) for p,m in masks.items()},
                'mask_sha256s':{p:hashlib.sha256(m.tobytes()).hexdigest() for p,m in masks.items()},
                'reference_exact':True,'neighbor2_subset_of_legacy':True})
    return {'rows':rows,'bits_per_policy':sum(r['bits_per_policy'] for r in rows),'complete':True}


def run(work,source_root,freeze):
    cfg=frozen(freeze);started=time.monotonic();OUT.mkdir(exist_ok=True)
    if (OUT/'result.json').exists():raise ValueError('completed result exists; preserve it')
    try:
        _,_,_,metadata,basis,parent,parent_table,_=build_context()
        bank,table,bridge=detector.catalogue_bridge(parent,cfg['parent_template_indices'],basis)
        if bridge!=cfg['bridge']:raise ValueError('catalogue bridge changed')
        original,grid,start=grid_context()
        if core.proxy_carrier_grid_sha256(grid)!=cfg['grid_sha256']:raise ValueError('grid changed')
        old=AnchorStore(work,{'parent_template_indices':cfg['parent_template_indices'],'support_carriers':original.support_bin_count})
        arrays={key:old.get(*key)[0][:,start:start+grid.support_bin_count] for key in old.expected_ids}
        provenance={'family':'M43P-exact-central-slice','parent_inventory_sha256':detector.digest(old.inventory),
            'parent_score_ids_sha256':detector.digest([[*k,v] for k,v in sorted(old.expected_ids.items())]),
            'support_start':start,'support_count':grid.support_bin_count,'grid_sha256':cfg['grid_sha256']}
        baseline=ScoreStore(arrays,provenance)
        historical_calibration=read_sealed(ROOT/'results_m43r_joint_calibration/calibration.json')
        if provenance!=historical_calibration['baseline_provenance']:raise ValueError('baseline provenance changed')
        anchors=mask_anchors(baseline,len(bank))
        write_sealed(OUT/'mask_anchors.json',{'freeze_commit':freeze,'baseline_provenance':provenance,**anchors})
        print(f'Independent mask anchors exact: {anchors["bits_per_policy"]} bits per policy',flush=True)
        common=dict(grid=grid,bank=bank,table=table,basis=basis,scans=metadata['scans'])
        calibrations={};thresholds={};null_results={}
        for policy in POLICIES:
            window='m43t-mask-'+policy
            cal,summary=detector.calibrate(**common,policy=policy,window=window,store=baseline,
                shifts=np.asarray(cfg['calibration_shifts'],dtype=np.int64),minimum_shift_bins=cfg['minimum_shift_bins'])
            threshold=core.calibrated_threshold((cal,),expected_window_ids=(window,),reference_floor=10.,quantile=1.,scientific_p_ceiling=.01)
            calibrations[policy]=cal;thresholds[policy]=threshold
            write_sealed(OUT/(policy+'.calibration.json'),{'freeze_commit':freeze,'baseline_provenance':provenance,
                'calibration':summary,'null_maxima':cal.null_maxima.tolist(),'threshold':threshold.as_record()})
            print(f'{policy}: training maximum {max(cal.null_maxima):.6f}; fixed threshold {threshold.operational_threshold_snr}',flush=True)
            held,summary=detector.calibrate(**common,policy=policy,window=window,store=baseline,
                shifts=np.asarray(cfg['heldout_shifts'],dtype=np.int64),minimum_shift_bins=cfg['minimum_shift_bins'])
            values=held.null_maxima;cut=threshold.operational_threshold_snr
            null_results[policy]={'freeze_commit':freeze,'calibration':summary,'null_maxima':values.tolist(),
                'denominator':len(values),'at_or_above_threshold':int(np.count_nonzero(values>=cut)),
                'threshold_certificate_sha256':threshold.certificate_sha256,
                'scope':'correlated within-sequence pre-veto resamples; not physical false-alarm probability'}
            write_sealed(OUT/(policy+'.heldout.json'),null_results[policy])
            print(f'{policy}: held-out maximum {max(values):.6f}; exceedances {null_results[policy]["at_or_above_threshold"]}/{len(values)}',flush=True)
        receiver=NativeReceiver(source_root,metadata,basis,parent,parent_table,original)
        overlay=ProfileOverlay(baseline,receiver,bank,table,basis,grid,progress=lambda m:print(m,flush=True))
        previous=read_sealed(ROOT/'results_m43r_joint_calibration/native_anchors.json')
        if overlay.cache_inventory!=previous['cache_inventory']:raise ValueError('native cache identities changed')
        write_sealed(OUT/'native_anchors.json',{'freeze_commit':freeze,'cache_inventory':overlay.cache_inventory,
            'ancestor_artifact_sha256':previous['result_sha256'],'all_native_identities_exact':True})
        fixed=dict(**common,policy='neighbor2',window='m43t-mask-neighbor2',calibration=calibrations['neighbor2'],
            threshold=thresholds['neighbor2'],receiver_factory=overlay,maximum_records=cfg['maximum_records'])
        background=compact(detector.execute(**fixed,store=baseline),overlay.overlay_receipt)
        write_sealed(OUT/'baseline.json',background)
        print(f'Neighbor2 baseline: ON {background["on_retained"]}, OFF {background["off_retained"]}',flush=True)
        on_factors=np.stack([core.factor_table_for_scan(table,basis,f'epoch{e+1}_on') for e in range(3)],axis=1)
        pairs=[];rank_checks=[]
        for truth in cfg['truths']:
            for amplitude in cfg['amplitudes']:
                t0=time.monotonic();name=f'truth{truth["truth_index"]:02d}.strength{amplitude:03d}.json';path=OUT/name
                historical=read_sealed(ROOT/'results_m43s_profile_sensitivity'/name)
                store=overlay.trial(truth,amplitude)
                input_root=detector.digest([[*key,store.expected_ids[key]] for key in sorted(store.expected_ids)])
                if input_root!=historical['audit']['input_inventory_sha256']:raise ValueError('paired native input differs from M43S')
                if path.exists():
                    saved=read_sealed(path)
                    if (saved['freeze_commit']!=freeze or saved['config_sha256']!=sha(CONFIG)
                        or saved['audit']['input_inventory_sha256']!=input_root or saved['endpoint']['truth']!=truth
                        or saved['endpoint']['nominal_total_epoch_strength']!=amplitude):raise ValueError('restart scope changed')
                    outcome=saved['endpoint']
                else:
                    audit=compact(detector.execute(**fixed,store=store),overlay.overlay_receipt)
                    outcome=endpoint(audit,truth,grid,on_factors,basis,amplitude,name)
                    write_sealed(path,{'freeze_commit':freeze,'config_sha256':sha(CONFIG),'mask_policy':'neighbor2',
                        'historical_artifact_sha256':historical['result_sha256'],'paired_input_inventory_exact':True,
                        'audit':audit,'endpoint':outcome,'wall_seconds':round(time.monotonic()-t0,3)})
                pairs.append({'truth_index':truth['truth_index'],'profile':truth['profile'],'strength':amplitude,
                    'historical_legacy':historical['endpoint'],'neighbor2':outcome,'input_inventory_sha256':input_root})
                for member in historical['audit']['members']:
                    p=(1+int(np.count_nonzero(calibrations['legacy'].null_maxima>=member['snr'])))/129
                    rank_checks.append((p<=.01)==member['meets_diagnostic_rank_cut'])
                write_sealed(OUT/'progress.json',{'completed_pairs':len(pairs),'planned_pairs':32,'complete':False})
                print(f'truth {truth["truth_index"]} strength {amplitude}: legacy={historical["endpoint"]["recovered"]} neighbor2={outcome["recovered"]}; {time.monotonic()-t0:.1f}s',flush=True)
        if len(pairs)!=32:raise ValueError('incomplete endpoint denominator')
        summary=[]
        for profile in cfg['profiles']:
            for amplitude in cfg['amplitudes']:
                selected=[p for p in pairs if p['profile']==profile and p['strength']==amplitude]
                summary.append({'profile':profile,'strength':amplitude,'denominator':len(selected),
                    **{policy:sum(p[policy]['recovered'] for p in selected) for policy in ('historical_legacy','neighbor2')},
                    'gained':sum(p['neighbor2']['recovered'] and not p['historical_legacy']['recovered'] for p in selected),
                    'lost':sum(p['historical_legacy']['recovered'] and not p['neighbor2']['recovered'] for p in selected)})
        write_sealed(OUT/'result.json',{'milestone':'M43T','status':'targeted-mask-regression-complete','freeze_commit':freeze,
            'config_sha256':sha(CONFIG),'wall_seconds':round(time.monotonic()-started,3),'summary':summary,'pairs':pairs,
            'thresholds':{p:t.as_record() for p,t in thresholds.items()},
            'heldout_exceedances':{p:{k:v[k] for k in ('denominator','at_or_above_threshold')} for p,v in null_results.items()},
            'legacy_calibration_comparison':{'same_threshold':thresholds['legacy'].operational_threshold_snr==historical_calibration['threshold']['operational_threshold_snr'],
                'historical_members_checked':len(rank_checks),'all_rank_eligibility_equal':all(rank_checks)},
            'new_native_trials':32,'new_baseline_executions':1,'reused_historical_trials':32,'unique_new_shift_rows':256,
            'policy_shift_evaluations':512,'telescope_requests':0,'full_bank_search':False,
            'independent_completeness_test':False,'physical_false_alarm_probability_measured':False,
            'scientific_candidate_selection_authorized':False})
        write_sealed(OUT/'progress.json',{'completed_pairs':32,'planned_pairs':32,'complete':True})
        print(json.dumps(summary,indent=2),flush=True)
    except BaseException as error:
        write_sealed(OUT/'failure.json',{'milestone':'M43T','freeze_commit':freeze,'error':repr(error),'complete':False})
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--freeze-commit',required=True);p.add_argument('--anchor-root',type=Path,required=True)
    p.add_argument('--source-root',type=Path,required=True);a=p.parse_args();run(a.anchor_root,a.source_root,a.freeze_commit)
