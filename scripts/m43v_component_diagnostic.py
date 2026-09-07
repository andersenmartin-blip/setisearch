"""Frozen retrospective component interventions; M43U numerical path unchanged."""
import argparse
import gzip
import hashlib
import json
import subprocess
import time
from pathlib import Path
import numpy as np
from m43u_signal_interference import frozen as u_frozen, WINDOW
from m43e_economical_bank import read_sealed, write_sealed
from m43f_source_cache_preflight import build_context
from m43q_integrated_detector import AnchorStore, NativeReceiver
from m43r_joint_calibration import grid_context, compact
from m43s_profile_sensitivity import endpoint
from seti_repeater import search_v0p6 as core, detector_m43u as detector
from seti_repeater.injection_m43r import ScoreStore
from seti_repeater.injection_m43u import JointOverlay
from seti_repeater.mask_m43u import POLICIES, bind_calibration, build_mask

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_m43v_component_diagnostic'
CONFIG=ROOT/'config/m43v_component_diagnostic.json'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def coordinate(m):
    return (m['template_index'],m['proxy_carrier_index'],m['spectral_width_channels'],tuple(m['active_epochs_zero_based']))

def final_keys(audit):
    return {coordinate(m) for m in audit['members'] if m['passes_evaluated_physical_vetoes'] and m['meets_diagnostic_rank_cut']}

def set_comparison(both,first,second):
    union=first|second
    return {'both':len(both),'first':len(first),'second':len(second),'component_union':len(union),
        'both_only':len(both-union),'shared_with_component_union':len(both&union),'component_union_only':len(union-both),
        'both_only_coordinates':sorted(both-union),'component_union_only_coordinates':sorted(union-both)}

def probes(result,store,grid,probe_inventory,policy):
    out=[]
    for probe in probe_inventory:
        key=coordinate(probe);t,q,w,active=key
        arrays={width:store.get('on',t,width)[0] for width in core.M37_SPECTRAL_WIDTHS}
        full_q=grid.score_slice.start+q
        mask=build_mask(arrays.__getitem__,policy)
        seeds=[]
        for width,values in arrays.items():
            for e in active:
                for j in range(max(0,full_q-9),min(values.shape[1],full_q+10)):
                    other=np.arange(3)!=e
                    isolated=bool(values[e,j]>=10. and np.all(values[other,j]<3.))
                    if not isolated:continue
                    support={radius:float(values[other,max(0,j-radius):min(values.shape[1],j+radius+1)].max()) for radius in (2,9)}
                    remains=policy=='legacy' or support[2 if policy=='neighbor2' else 9]<3.
                    seeds.append({'width':width,'epoch':e,'score_index':j-grid.score_slice.start,
                        'epoch_values':values[:,j].tolist(),'other_max_radius2':support[2],'other_max_radius9':support[9],
                        'seed_retained_by_policy':remains})
        predicted=[any(s['epoch']==e and s['seed_retained_by_policy'] for s in seeds) for e in active]
        assert predicted==mask[list(active),full_q].tolist()
        matches=[r for r in result['receiver_alias']['records'] if coordinate(r)==key]
        ids={r['record_id'] for r in matches}
        out.append({'coordinate':list(key),'on_scores':arrays[w][:,full_q].tolist(),
            'off_scores':store.get('off',t,w)[0][:,full_q].tolist(),
            'active_mask':predicted,'isolation_seed_trace':seeds,'retained':bool(matches),
            'annotated_records':matches,'receiver_signatures':{k:v for k,v in result['receiver_signatures'].items() if k in ids},
            'rank_evidence':[r for r in result['rank']['evidence'] if r['record_id'] in ids]})
    return out

def run(anchor_root,source_root,checkpoint_root,freeze):
    started=time.monotonic();cfg=json.loads(CONFIG.read_text())
    assert subprocess.check_output(['git','show',freeze+':config/m43v_component_diagnostic.json'],cwd=ROOT)==CONFIG.read_bytes()
    for p,h in cfg['pinned_sha256'].items():assert sha(ROOT/p)==h,p
    u=u_frozen(cfg['m43u_execution_freeze'])
    assert not (OUT/'result.json').exists(),'preserve completed result'
    OUT.mkdir(exist_ok=True);checkpoint_root.mkdir(exist_ok=True,parents=True)
    historical={}
    with gzip.open(ROOT/'results_m43u_signal_interference/case_audits.jsonl.gz','rt') as f:
        for line in f:
            if line.strip():
                r=json.loads(line);historical[r['case']['case_index']]=r
    _,_,_,metadata,basis,parent,parent_table,_=build_context()
    bank,table,bridge=detector.catalogue_bridge(parent,u['parent_template_indices'],basis)
    assert bridge==u['bridge']
    original,grid,start=grid_context()
    old=AnchorStore(anchor_root,{'parent_template_indices':u['parent_template_indices'],'support_carriers':original.support_bin_count})
    arrays={k:old.get(*k)[0][:,start:start+grid.support_bin_count] for k in old.expected_ids}
    provenance={'family':'M43P-exact-central-slice','parent_inventory_sha256':detector.digest(old.inventory),
        'parent_score_ids_sha256':detector.digest([[*k,v] for k,v in sorted(old.expected_ids.items())]),
        'support_start':start,'support_count':grid.support_bin_count,'grid_sha256':u['grid_sha256']}
    assert provenance==read_sealed(ROOT/'results_m43r_joint_calibration/calibration.json')['baseline_provenance']
    baseline=ScoreStore(arrays,provenance)
    common=dict(window=WINDOW,grid=grid,bank=bank,table=table,basis=basis,scans=metadata['scans'])
    calibrations={};thresholds={};bindings={}
    for policy in POLICIES:
        cal,summary=detector.calibrate(**common,store=baseline,mask_policy=policy,
            shifts=np.asarray(u['calibration_shifts'],dtype=np.int64),minimum_shift_bins=128)
        threshold=core.calibrated_threshold((cal,),expected_window_ids=(WINDOW,),reference_floor=10.,quantile=1.,scientific_p_ceiling=.01)
        binding=bind_calibration(cal,threshold,policy)
        previous=read_sealed(ROOT/f'results_m43u_signal_interference/{policy}.calibration.json')
        assert summary==previous['summary'] and cal.null_maxima.tolist()==previous['null_maxima']
        assert threshold.as_record()==previous['threshold'] and binding==previous['binding']
        calibrations[policy]=cal;thresholds[policy]=threshold;bindings[policy]=binding
        print(policy+' calibration exactly replayed',flush=True)
    receiver=NativeReceiver(source_root,metadata,basis,parent,parent_table,original)
    overlay=JointOverlay(baseline,receiver,bank,table,basis,grid,progress=lambda m:print(m,flush=True))
    assert overlay.cache_inventory==read_sealed(ROOT/'results_m43u_signal_interference/input_anchors.json')['cache_inventory']
    write_sealed(OUT/'anchors.json',{'freeze_commit':freeze,'all_96_arrays_exact':True,
        'all_48_native_gathers_exact':True,'calibration_replays_exact':list(POLICIES),'bindings':bindings})
    def execute(policy,store,probe_inventory):
        r=detector.execute(**common,store=store,mask_policy=policy,calibration=calibrations[policy],threshold=thresholds[policy],
            calibration_binding=bindings[policy],receiver_factory=overlay,maximum_records=u['maximum_records'])
        a=compact(r,overlay.overlay_receipt)
        a.update(mask_policy=policy,calibration_binding=bindings[policy],masked_cell_counts=r['masked_cell_counts'],
            final_diagnostic_survivors=len(final_keys(a)))
        assert a['final_diagnostic_survivors']==sum(d['passes_evaluated_physical_vetoes'] and d['meets_diagnostic_rank_cut'] for d in r['decisions'])
        return a,probes(r,store,grid,probe_inventory,policy)
    store=overlay.trial([])
    for policy in POLICIES:
        a,_=execute(policy,store,[])
        assert a==read_sealed(ROOT/f'results_m43u_signal_interference/{policy}.baseline.json')['audit']
    print('Three baseline replays exact',flush=True)
    factors=np.stack([core.factor_table_for_scan(table,basis,f'epoch{e+1}_on') for e in range(3)],axis=1)
    paths=[]
    for spec in cfg['inputs']:
        index=spec['case_index'];variant=spec['variant'];parent_case=u['cases'][index]
        components=[parent_case['components'][j] for j in spec['component_indices']]
        path=checkpoint_root/f'case{index:03d}.{variant}.json'
        if path.exists():
            rec=read_sealed(path)
            assert rec['freeze_commit']==freeze and rec['config_sha256']==sha(CONFIG) and rec['spec']==spec
        else:
            store=overlay.trial(components);audits={};trace={};association={}
            for policy in POLICIES:
                a,p=execute(policy,store,cfg['probes'].get(str(index),[]))
                if variant=='both':assert a==historical[index]['audits'][policy],f'historical replay differs {index} {policy}'
                audits[policy]=a;trace[policy]=p
                if parent_case['signal_truth'] is not None:
                    e=endpoint(a,parent_case['signal_truth'],grid,factors,basis,32,path.name)
                    e.pop('zero_level_reuses_m43r_baseline')
                    association[policy]=e
            assert len({a['input_inventory_sha256'] for a in audits.values()})==1
            rec=write_sealed(path,{'freeze_commit':freeze,'config_sha256':sha(CONFIG),'spec':spec,
                'components':components,'audits':audits,'probes':trace,'truth_association':association,
                'historical_replay_exact':variant=='both'})
        paths.append(path)
        print(f'{len(paths)}/30 case {index} {variant}: '+str({p:a['final_diagnostic_survivors'] for p,a in rec['audits'].items()}),flush=True)
        write_sealed(OUT/'progress.json',{'complete':False,'completed_inputs':len(paths),'completed_endpoints':3*len(paths)})
    assert len(paths)==30
    raw=b''.join(p.read_bytes()+b'\n' for p in paths);packed=gzip.compress(raw,compresslevel=9,mtime=0)
    (OUT/'case_audits.jsonl.gz').write_bytes(packed)
    records=[read_sealed(p) for p in paths];lookup={(r['spec']['case_index'],r['spec']['variant']):r for r in records}
    summary=[]
    for i in cfg['selected_cases']:
        for policy in POLICIES:
            row={'case_index':i,'case_type':u['cases'][i]['case_type'],'policy':policy}
            row.update(set_comparison(*(final_keys(lookup[i,v]['audits'][policy]) for v in ('both','first','second'))))
            row['truth_association']={v:lookup[i,v]['truth_association'].get(policy,{}).get('recovered') for v in ('both','first','second')}
            summary.append(row)
    write_sealed(OUT/'result.json',{'milestone':'M43V','complete':True,'freeze_commit':freeze,'inputs':30,'endpoints':90,
        'exact_historical_endpoint_replays':30,'new_component_endpoints':60,'exact_baseline_replays':3,
        'ledger_sha256':hashlib.sha256(packed).hexdigest(),'ledger_uncompressed_sha256':hashlib.sha256(raw).hexdigest(),
        'summary':summary,'wall_seconds':round(time.monotonic()-started,3),'telescope_requests':0,
        'detector_changed':False,'independent_validation':False,'general_adoption_qualified':False})
    write_sealed(OUT/'progress.json',{'complete':True,'completed_inputs':30,'completed_endpoints':90})
    print('M43V COMPLETE',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--freeze-commit',required=True)
    ap.add_argument('--anchor-root',type=Path,required=True);ap.add_argument('--source-root',type=Path,required=True)
    ap.add_argument('--checkpoint-root',type=Path,required=True);a=ap.parse_args()
    run(a.anchor_root,a.source_root,a.checkpoint_root,a.freeze_commit)
