"""Frozen M43Z four-endpoint joint-control trial on shared base executions."""
import argparse
import gzip
import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path
import numpy as np
from m43e_economical_bank import read_sealed,write_sealed
from m43f_source_cache_preflight import build_context
from m43q_integrated_detector import AnchorStore,NativeReceiver
from m43r_joint_calibration import grid_context,compact
from m43s_profile_sensitivity import endpoint
from seti_repeater import search_v0p6 as core,detector_m43u as detector
from seti_repeater.injection_m43r import ScoreStore
from seti_repeater.injection_m43u import JointOverlay
from seti_repeater.mask_m43u import bind_calibration
from seti_repeater.confirmation_m43z import POLICIES,apply_controls

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results_m43z_joint_controls'
CONFIG=ROOT/'config/m43z_joint_controls.json';WINDOW='m43z-shared-pre-veto-joint-controls'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def validate_freeze(freeze):
    cfg=json.loads(CONFIG.read_text())
    assert subprocess.check_output(['git','show',freeze+':config/m43z_joint_controls.json'],cwd=ROOT)==CONFIG.read_bytes()
    assert platform.python_version()==cfg['python_version'] and np.__version__==cfg['numpy_version']
    for p,h in cfg['pinned_sha256'].items():assert sha(ROOT/p)==h,p
    return cfg

def decisions(endpoints,heldout):
    ref={e['case_index']:e for e in endpoints if e['policy']=='neighbor9'};out={}
    for policy in POLICIES[1:]:
        rows=[e for e in endpoints if e['policy']==policy];gains=[];losses=[];added=[];removed=[]
        for e in rows:
            old=ref[e['case_index']]
            if e['signal_present']:
                a,b=old['truth_association']['recovered'],e['truth_association']['recovered']
                if b and not a:gains.append(e['case_index'])
                if a and not b:losses.append(e['case_index'])
            else:
                a,b=old['final_members']>0,e['final_members']>0
                if b and not a:added.append(e['case_index'])
                if a and not b:removed.append(e['case_index'])
        cond={'no_signal_case_loss':not losses,'no_increased_leaking_control_count':len(added)<=len(removed),
            'zero_ON_OFF_final_members':all(e['final_members']==0 for e in rows if e['case_type']=='ON-OFF'),
            'zero_interferer_only_false_associations':all(not e['truth_association']['recovered'] for e in rows if e['case_type']=='interferer-only'),
            'strict_control_leak_reduction':len(removed)>len(added),
            'zero_interferer_only_final_members':all(e['final_members']==0 for e in rows if e['case_type']=='interferer-only'),
            'zero_OFF_only_final_members':all(e['final_members']==0 for e in rows if e['case_type']=='OFF-only'),
            'zero_supported_spike_final_members':all(e['final_members']==0 for e in rows if e['case_type']=='supported-spike'),
            'zero_shared_heldout_pre_veto_exceedances':heldout['at_or_above_threshold']==0}
        out[policy]={'signal_gains':gains,'signal_losses':losses,'added_leaking_controls':added,'removed_leaking_controls':removed,
            'conditions':cond,'development_gate_passed':all(cond.values())}
    return out

def matched_comparison(endpoints,cases):
    lookup={(e['case_index'],e['policy']):e for e in endpoints}
    base={(c['pair_group'],c['case_type']):c['case_index'] for c in cases}
    out=[]
    for c in cases:
        if not c['matched_signal_only_type']:continue
        origin=base[c['pair_group'],c['matched_signal_only_type']]
        for p in POLICIES:
            a=lookup[origin,p]['truth_association']['recovered'];b=lookup[c['case_index'],p]['truth_association']['recovered']
            ref=lookup[c['case_index'],'neighbor9']['truth_association']['recovered']
            out.append(dict(case_index=c['case_index'],signal_only_case_index=origin,case_type=c['case_type'],policy=p,
                signal_only_recovered=a,with_interference_recovered=b,paired_loss=a and not b,paired_gain=b and not a,
                added_policy_loss_on_interference_input=ref and not b))
    return out

def run(anchor_root,source_root,checkpoint_root,freeze,preflight_only=False):
    started=time.monotonic();cfg=validate_freeze(freeze)
    assert not (OUT/'result.json').exists(),'preserve completed result'
    OUT.mkdir(exist_ok=True);checkpoint_root.mkdir(parents=True,exist_ok=True)
    _,_,_,metadata,basis,parent,parent_table,_=build_context()
    bank,table,bridge=detector.catalogue_bridge(parent,cfg['parent_template_indices'],basis);assert bridge==cfg['bridge']
    original,grid,start=grid_context();assert core.proxy_carrier_grid_sha256(grid)==cfg['grid_sha256']
    old=AnchorStore(anchor_root,{'parent_template_indices':cfg['parent_template_indices'],'support_carriers':original.support_bin_count})
    arrays={k:old.get(*k)[0][:,start:start+grid.support_bin_count] for k in old.expected_ids}
    provenance={'family':'M43P-exact-central-slice','parent_inventory_sha256':detector.digest(old.inventory),
        'parent_score_ids_sha256':detector.digest([[*k,v] for k,v in sorted(old.expected_ids.items())]),
        'support_start':start,'support_count':grid.support_bin_count,'grid_sha256':cfg['grid_sha256']}
    assert provenance==read_sealed(ROOT/'results_m43r_joint_calibration/calibration.json')['baseline_provenance']
    baseline=ScoreStore(arrays,provenance)
    receiver=NativeReceiver(source_root,metadata,basis,parent,parent_table,original)
    overlay=JointOverlay(baseline,receiver,bank,table,basis,grid,progress=lambda m:print(m,flush=True))
    assert overlay.cache_inventory==read_sealed(ROOT/'results_m43u_signal_interference/input_anchors.json')['cache_inventory']
    write_sealed(OUT/'anchors.json',{'freeze_commit':freeze,'all_96_arrays_exact':True,'all_48_native_gathers_exact':True,
        'reused_unchanged_arithmetic_anchors':{p:sha(ROOT/p) for p in cfg['unchanged_arithmetic_anchors']}})
    print('Original arrays and native gathers exact; unchanged W/X arithmetic anchors reused',flush=True)
    if preflight_only:return
    common=dict(window=WINDOW,grid=grid,bank=bank,table=table,basis=basis,scans=metadata['scans'])
    cal,summary=detector.calibrate(**common,store=baseline,mask_policy='neighbor9',
        shifts=np.asarray(cfg['training_shifts'],dtype=np.int64),minimum_shift_bins=128)
    threshold=core.calibrated_threshold((cal,),expected_window_ids=(WINDOW,),reference_floor=10.,quantile=1.,scientific_p_ceiling=.01)
    binding=bind_calibration(cal,threshold,'neighbor9')
    write_sealed(OUT/'calibration.json',{'freeze_commit':freeze,'summary':summary,'null_maxima':cal.null_maxima.tolist(),
        'threshold':threshold.as_record(),'binding':binding,'shared_by_policies':list(POLICIES),'scope':'conservative shared >=3 pre-veto maxima'})
    print('Shared threshold sealed: '+str(threshold.operational_threshold_snr),flush=True)
    h,hs=detector.calibrate(**common,store=baseline,mask_policy='neighbor9',
        shifts=np.asarray(cfg['heldout_shifts'],dtype=np.int64),minimum_shift_bins=128)
    heldout={'count':128,'maximum':float(max(h.null_maxima)),'threshold':threshold.operational_threshold_snr,
        'at_or_above_threshold':int(np.count_nonzero(h.null_maxima>=threshold.operational_threshold_snr))}
    write_sealed(OUT/'heldout.json',{'freeze_commit':freeze,'summary':hs,'null_maxima':h.null_maxima.tolist(),'diagnostic':heldout})
    print('Heldout '+json.dumps(heldout),flush=True)
    def execute(store):
        result=detector.execute(**common,store=store,mask_policy='neighbor9',calibration=cal,threshold=threshold,
            calibration_binding=binding,receiver_factory=overlay,maximum_records=cfg['maximum_records'])
        audit=compact(result,overlay.overlay_receipt)
        audit['masked_cell_counts']=result['masked_cell_counts']
        audits,evidence=apply_controls(audit,store,grid)
        reference_ids={m['record_id'] for m in audit['members'] if m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut']}
        for policy,a in audits.items():
            final={m['record_id'] for m in a['members'] if m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut']}
            assert final<=reference_ids
            if policy=='neighbor9':assert final==reference_ids
        return audits,evidence
    overlay.trial([]);audits,evidence=execute(baseline)
    write_sealed(OUT/'baseline.json',{'freeze_commit':freeze,'audits':audits,'evidence':evidence})
    factors=np.stack([core.factor_table_for_scan(table,basis,f'epoch{e+1}_on') for e in range(3)],axis=1)
    paths=[];endpoints=[]
    for case in cfg['cases']:
        path=checkpoint_root/f'case{case["case_index"]:03d}.json'
        if path.exists():
            rec=read_sealed(path)
            assert rec['freeze_commit']==freeze and rec['config_sha256']==sha(CONFIG) and rec['case']==case and rec['binding']==binding
        else:
            store=overlay.trial(case['components']);audits,evidence=execute(store);rows=[]
            for policy,a in audits.items():
                association=endpoint(a,case['reference_truth'],grid,factors,basis,case['strength'],path.name)
                association.pop('zero_level_reuses_m43r_baseline')
                rows.append({'case_index':case['case_index'],'stratum':case['stratum'],'strength':case['strength'],
                    'case_type':case['case_type'],'policy':policy,'signal_present':case['signal_present'],
                    'final_members':a['final_diagnostic_survivors'],'truth_association':association})
            # Shared base audit plus complete per-policy decisions avoids copying
            # identical scores, provenance and input receipts three times.
            rec=write_sealed(path,{'freeze_commit':freeze,'config_sha256':sha(CONFIG),'case':case,'binding':binding,
                'reference_audit':audits['neighbor9'],'confirmation_evidence':evidence,
                'policy_decisions':{p:[{k:m[k] for k in ('record_id','passes_evaluated_physical_vetoes','physical_disposition','m43z_rejections')} for m in a['members']] for p,a in audits.items()},
                'endpoints':rows})
        paths.append(path);endpoints.extend(rec['endpoints'])
        print(f'{len(paths)}/320 {case["case_type"]} S={case["strength"]}: '+str({e['policy']:(e['truth_association']['recovered'],e['final_members']) for e in rec['endpoints']}),flush=True)
        write_sealed(OUT/'progress.json',{'complete':False,'completed_inputs':len(paths),'policy_endpoints':len(endpoints)})
    assert len(paths)==320 and len(endpoints)==1280
    raw=b''.join(p.read_bytes()+b'\n' for p in paths);packed=gzip.compress(raw,compresslevel=9,mtime=0)
    (OUT/'case_audits.jsonl.gz').write_bytes(packed)
    summary=[]
    for p in POLICIES:
        for s in (24.,48.):
            for kind in dict.fromkeys(c['case_type'] for c in cfg['cases']):
                rows=[e for e in endpoints if e['policy']==p and e['strength']==s and e['case_type']==kind]
                assert len(rows)==16
                summary.append({'policy':p,'strength':s,'case_type':kind,'inputs':16,
                    'truth_associations':sum(e['truth_association']['recovered'] for e in rows),
                    'cases_with_final_members':sum(e['final_members']>0 for e in rows),'final_members':sum(e['final_members'] for e in rows)})
    write_sealed(OUT/'result.json',{'milestone':'M43Z','complete':True,'freeze_commit':freeze,'inputs':320,
        'base_detector_executions':320,'policy_endpoints':1280,'separate_baseline_executions':1,
        'summary':summary,'endpoints':endpoints,'comparisons':decisions(endpoints,heldout),'heldout':heldout,
        'ledger_sha256':hashlib.sha256(packed).hexdigest(),'ledger_uncompressed_sha256':hashlib.sha256(raw).hexdigest(),
        'wall_seconds':round(time.monotonic()-started,3),'new_telescope_requests':0,'independent_observing_sequences':1,
        'general_adoption_qualified':False,'prior_M43X_losses_remain_unresolved':True,
        'matched_component_comparison':matched_comparison(endpoints,cfg['cases']),'physical_false_alarm_probability_measured':False})
    write_sealed(OUT/'progress.json',{'complete':True,'completed_inputs':320,'policy_endpoints':1280})
    print('M43Z COMPLETE',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--freeze-commit',required=True)
    p.add_argument('--preflight-only',action='store_true',help='verify baseline inputs and scalar anchors without new calibration or panel scoring')
    p.add_argument('--anchor-root',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--checkpoint-root',type=Path,required=True);a=p.parse_args()
    run(a.anchor_root,a.source_root,a.checkpoint_root,a.freeze_commit,a.preflight_only)
