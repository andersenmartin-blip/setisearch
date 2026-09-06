#!/usr/bin/env python3
"""Frozen weaker/profile sensitivity extension of the unchanged M43R detector."""
import argparse
import json
import platform
from pathlib import Path
import subprocess
import time
import numpy as np
from m43e_economical_bank import read_sealed,write_sealed
from m43f_source_cache_preflight import build_context
from m43q_integrated_detector import AnchorStore,NativeReceiver
from m43r_joint_calibration import ROOT,WINDOW,grid_context,sha,compact
from seti_repeater import search_v0p6 as core
from seti_repeater import detector_m43r as detector
from seti_repeater.injection_m43r import ScoreStore
from seti_repeater.injection_m43s import ProfileOverlay,restore_calibration,truth_on_factors,association_distances

CONFIG=ROOT/'config/m43s_profile_sensitivity.json'
OUT=ROOT/'results_m43s_profile_sensitivity'


def geometry_summary(truth,grid,on_factors,basis):
    factors=truth_on_factors(basis,truth)
    q=float(grid.score_hz[truth['score_index']]+truth['fractional_proxy_bin']*grid.channel_width_hz)
    maximum=np.zeros((on_factors.shape[0],grid.score_bin_count),dtype='<f8')
    for e in truth['active_epochs']:
        for row in range(factors.shape[1]):
            maximum=np.maximum(maximum,np.abs(on_factors[:,e,row,None]*grid.score_hz-q*factors[e,row]))
    t,i=np.unravel_index(np.argmin(maximum),maximum.shape)
    return {'closest_template_index':int(t),'closest_score_index':int(i),'maximum_active_row_residual_hz':float(maximum[t,i]),
        'has_center_track_match_within_20hz':bool(maximum[t,i]<=20.),'truth_on_factors_sha256':core.factor_table_sha256(factors)}


def frozen(commit):
    cfg=json.loads(CONFIG.read_text())
    if subprocess.check_output(['git','show',commit+':config/m43s_profile_sensitivity.json'],cwd=ROOT)!=CONFIG.read_bytes():
        raise ValueError('config differs from public freeze')
    for name,h in cfg['pinned_sha256'].items():
        if sha(ROOT/name)!=h:raise ValueError('frozen dependency changed: '+name)
    if np.__version__!=cfg['numpy_version'] or platform.python_version()!=cfg['python_version']:
        raise ValueError('numerical runtime changed')
    return cfg


def endpoint(audit,truth,grid,on_factors,basis,amplitude,artifact):
    distances=association_distances(audit['members'],truth,grid,on_factors,truth_on_factors(basis,truth))
    matched=[m for m in audit['members'] if distances.get(m['record_id'],float('inf'))<=20.]
    physical=[m for m in matched if m['passes_evaluated_physical_vetoes']]
    final=[m for m in physical if m['meets_diagnostic_rank_cut']]
    exact=None
    if truth['profile']=='ideal-native-bin':
        exact=any(m['template_index']==truth['local_template'] and m['proxy_carrier_index']==truth['score_index'] for m in final)
    return {'truth':truth,'nominal_total_epoch_strength':amplitude,'artifact':artifact,
        'association_endpoint':'exact activity subset and <=20 Hz max center-track error over every active ON row',
        'retained':bool(matched),'passes_physical_vetoes':bool(physical),'recovered':bool(final),
        'ideal_exact_grid_recovered':exact,'associated_members':len(matched),'associated_physical_survivors':len(physical),
        'associated_final_survivors':len(final),'associated_record_ids':[m['record_id'] for m in matched],
        'best_final_residual_hz':min((distances[m['record_id']] for m in final),default=None),
        'associated_dispositions':{k:sum(m['physical_disposition']==k for m in matched) for k in sorted({m['physical_disposition'] for m in matched})},
        'zero_level_reuses_m43r_baseline':amplitude==0}


def run(work,source_root,freeze):
    cfg=frozen(freeze);started=time.monotonic();OUT.mkdir(exist_ok=True)
    if (OUT/'result.json').exists():raise ValueError('completed result already exists; preserve it')
    try:
        _,_,_,metadata,basis,parent,parent_table,_=build_context()
        bank,table,bridge=detector.catalogue_bridge(parent,cfg['parent_template_indices'],basis)
        if bridge!=cfg['bridge']:raise ValueError('catalogue bridge changed')
        original,grid,start=grid_context()
        old=AnchorStore(work,{'parent_template_indices':cfg['parent_template_indices'],'support_carriers':original.support_bin_count})
        arrays={key:old.get(*key)[0][:,start:start+grid.support_bin_count] for key in old.expected_ids}
        provenance={'family':'M43P-exact-central-slice','parent_inventory_sha256':detector.digest(old.inventory),
            'parent_score_ids_sha256':detector.digest([[*k,v] for k,v in sorted(old.expected_ids.items())]),
            'support_start':start,'support_count':grid.support_bin_count,'grid_sha256':core.proxy_carrier_grid_sha256(grid)}
        baseline=ScoreStore(arrays,provenance)
        record=read_sealed(ROOT/'results_m43r_joint_calibration/calibration.json')
        if provenance!=record['baseline_provenance']:raise ValueError('persisted calibration background differs')
        calibration,threshold=restore_calibration(record,cfg['calibration_artifact_sha256'],cfg['threshold_certificate_sha256'])
        background=read_sealed(ROOT/'results_m43r_joint_calibration/baseline.json')
        input_root=detector.digest([[*key,baseline.expected_ids[key]] for key in sorted(baseline.expected_ids)])
        if background['input_inventory_sha256']!=input_root or background['threshold']!=threshold.as_record():
            raise ValueError('reused baseline handoff differs')
        receiver=NativeReceiver(source_root,metadata,basis,parent,parent_table,original)
        overlay=ProfileOverlay(baseline,receiver,bank,table,basis,grid,progress=lambda m:print(m,flush=True))
        previous=read_sealed(ROOT/'results_m43r_joint_calibration/native_anchors.json')
        if overlay.cache_inventory!=previous['cache_inventory']:raise ValueError('native gather anchor identities changed')
        on_factors=np.stack([core.factor_table_for_scan(table,basis,f'epoch{e+1}_on') for e in range(3)],axis=1)
        write_sealed(OUT/'input_reuse.json',{'freeze_commit':freeze,'config_sha256':sha(CONFIG),'baseline_provenance':provenance,
            'calibration_artifact_sha256':record['result_sha256'],'threshold':threshold.as_record(),
            'native_anchor_artifact_sha256':previous['result_sha256'],'cache_inventory':overlay.cache_inventory,
            'new_null_calibration':False,'all_reused_identities_exact':True})
        print('M43R threshold 10 and native anchors restored exactly; no repeated null calculation',flush=True)
        fixed=dict(window=WINDOW,grid=grid,bank=bank,table=table,basis=basis,scans=metadata['scans'],
            calibration=calibration,threshold=threshold,receiver_factory=overlay,maximum_records=cfg['maximum_records'])
        endpoints=[]
        for truth in cfg['truths']:
            if geometry_summary(truth,grid,on_factors,basis)!=cfg['geometry'][str(truth['truth_index'])]:
                raise ValueError('frozen truth geometry changed')
            endpoints.append(endpoint(background,truth,grid,on_factors,basis,0,'../results_m43r_joint_calibration/baseline.json'))
            for amplitude in cfg['amplitudes'][1:]:
                t0=time.monotonic();name=f'truth{truth["truth_index"]:02d}.strength{amplitude:03d}.json';path=OUT/name
                if path.exists():
                    saved=read_sealed(path)
                    if (saved['freeze_commit']!=freeze or saved['config_sha256']!=sha(CONFIG)
                            or saved['endpoint']['truth']!=truth or saved['endpoint']['nominal_total_epoch_strength']!=amplitude):
                        raise ValueError('restart checkpoint scope differs')
                    outcome=saved['endpoint'];print(f'reused sealed checkpoint {name}',flush=True)
                else:
                    store=overlay.trial(truth,amplitude);result=detector.execute(**fixed,store=store)
                    audit=compact(result,overlay.overlay_receipt)
                    outcome=endpoint(audit,truth,grid,on_factors,basis,amplitude,name)
                    write_sealed(path,{'freeze_commit':freeze,'config_sha256':sha(CONFIG),'audit':audit,'endpoint':outcome,
                        'wall_seconds':round(time.monotonic()-t0,3)})
                endpoints.append(outcome)
                write_sealed(OUT/'progress.json',{'completed_endpoints':len(endpoints),'planned_endpoints':112,
                    'endpoints':endpoints,'complete':False})
                print(f'truth {truth["truth_index"]} {truth["profile"]} strength {amplitude}: retained={outcome["retained"]} physical={outcome["passes_physical_vetoes"]} recovered={outcome["recovered"]}; {time.monotonic()-t0:.1f}s',flush=True)
        if len(endpoints)!=112:raise ValueError('incomplete endpoint denominator')
        summary=[{'profile':p,'nominal_total_epoch_strength':a,'denominator':sum(e['truth']['profile']==p and e['nominal_total_epoch_strength']==a for e in endpoints),
            **{k:sum(e[k] for e in endpoints if e['truth']['profile']==p and e['nominal_total_epoch_strength']==a) for k in ('retained','passes_physical_vetoes','recovered')}}
            for p in cfg['profiles'] for a in cfg['amplitudes']]
        write_sealed(OUT/'result.json',{'milestone':'M43S','status':'profile-sensitivity-pilot-complete','freeze_commit':freeze,
            'config_sha256':sha(CONFIG),'wall_seconds':round(time.monotonic()-started,3),'summary':summary,'endpoints':endpoints,
            'threshold_certificate_sha256':threshold.certificate_sha256,'new_detector_executions':96,'reused_zero_level_endpoints':16,
            'new_null_count':0,'telescope_requests':0,'full_bank_search':False,'scientific_candidate_selection_authorized':False})
        write_sealed(OUT/'progress.json',{'completed_endpoints':112,'planned_endpoints':112,'complete':True})
        print(json.dumps(summary,indent=2),flush=True)
    except BaseException as error:
        write_sealed(OUT/'failure.json',{'milestone':'M43S','freeze_commit':freeze,'error':repr(error),'complete':False})
        raise


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--freeze-commit',required=True);p.add_argument('--anchor-root',type=Path,required=True)
    p.add_argument('--source-root',type=Path,required=True);a=p.parse_args();run(a.anchor_root,a.source_root,a.freeze_commit)
