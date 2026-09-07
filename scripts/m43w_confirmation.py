"""Frozen M43W four-endpoint confirmation trial on shared base executions."""
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
from seti_repeater.confirmation_m43w import POLICIES,off_window,apply_controls

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results_m43w_confirmation'
CONFIG=ROOT/'config/m43w_confirmation.json';WINDOW='m43w-shared-pre-veto-confirmation'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def validate_freeze(freeze):
    cfg=json.loads(CONFIG.read_text())
    assert subprocess.check_output(['git','show',freeze+':config/m43w_confirmation.json'],cwd=ROOT)==CONFIG.read_bytes()
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
            'zero_shared_heldout_pre_veto_exceedances':heldout['at_or_above_threshold']==0}
        out[policy]={'signal_gains':gains,'signal_losses':losses,'added_leaking_controls':added,'removed_leaking_controls':removed,
            'conditions':cond,'development_gate_passed':all(cond.values())}
    return out

def run(anchor_root,source_root,checkpoint_root,freeze):
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
    anchors=[]
    for t in range(len(bank)):
        for w in core.M37_SPECTRAL_WIDTHS:
            values,_=baseline.get('off',t,w)
            for q in cfg['anchor_query_positions']:
                actual=off_window(values,grid,q,w,[0,1,2]);center=grid.score_slice.start+q
                reference=[max(float(values[e,j]) for j in range(center-w//2,center+w//2+1)) for e in range(3)]
                assert actual['maxima']==reference
                anchors.append({'template':t,'width':w,'q':q,'maxima':reference})
    assert len(anchors)*3==4440
    write_sealed(OUT/'anchors.json',{'freeze_commit':freeze,'all_96_arrays_exact':True,'all_48_native_gathers_exact':True,
        'OFF_window_scalar_comparisons':4440,'queries':anchors})
    print('All original arrays/gathers and 4,440 new OFF-window scalar anchors exact',flush=True)
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
            # identical scores, provenance and input receipts four times.
            rec=write_sealed(path,{'freeze_commit':freeze,'config_sha256':sha(CONFIG),'case':case,'binding':binding,
                'reference_audit':audits['neighbor9'],'confirmation_evidence':evidence,
                'policy_decisions':{p:[{k:m[k] for k in ('record_id','passes_evaluated_physical_vetoes','physical_disposition','m43w_rejections')} for m in a['members']] for p,a in audits.items()},
                'endpoints':rows})
        paths.append(path);endpoints.extend(rec['endpoints'])
        print(f'{len(paths)}/192 {case["case_type"]} S={case["strength"]}: '+str({e['policy']:(e['truth_association']['recovered'],e['final_members']) for e in rec['endpoints']}),flush=True)
        write_sealed(OUT/'progress.json',{'complete':False,'completed_inputs':len(paths),'policy_endpoints':len(endpoints)})
    assert len(paths)==192 and len(endpoints)==768
    raw=b''.join(p.read_bytes()+b'\n' for p in paths);packed=gzip.compress(raw,compresslevel=9,mtime=0)
    (OUT/'case_audits.jsonl.gz').write_bytes(packed)
    summary=[]
    for p in POLICIES:
        for s in (12.,32.):
            for kind in dict.fromkeys(c['case_type'] for c in cfg['cases']):
                rows=[e for e in endpoints if e['policy']==p and e['strength']==s and e['case_type']==kind]
                assert len(rows)==16
                summary.append({'policy':p,'strength':s,'case_type':kind,'inputs':16,
                    'truth_associations':sum(e['truth_association']['recovered'] for e in rows),
                    'cases_with_final_members':sum(e['final_members']>0 for e in rows),'final_members':sum(e['final_members'] for e in rows)})
    write_sealed(OUT/'result.json',{'milestone':'M43W','complete':True,'freeze_commit':freeze,'inputs':192,
        'base_detector_executions':192,'policy_endpoints':768,'separate_baseline_executions':1,
        'summary':summary,'endpoints':endpoints,'comparisons':decisions(endpoints,heldout),'heldout':heldout,
        'ledger_sha256':hashlib.sha256(packed).hexdigest(),'ledger_uncompressed_sha256':hashlib.sha256(raw).hexdigest(),
        'wall_seconds':round(time.monotonic()-started,3),'new_telescope_requests':0,'independent_observing_sequences':1,
        'general_adoption_qualified':False,'physical_false_alarm_probability_measured':False})
    write_sealed(OUT/'progress.json',{'complete':True,'completed_inputs':192,'policy_endpoints':768})
    print('M43W COMPLETE',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--freeze-commit',required=True)
    p.add_argument('--anchor-root',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--checkpoint-root',type=Path,required=True);a=p.parse_args()
    run(a.anchor_root,a.source_root,a.checkpoint_root,a.freeze_commit)
