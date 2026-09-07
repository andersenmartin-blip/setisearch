"""Frozen retrospective response probes; unchanged M43X detector execution."""
import argparse
import gzip
import hashlib
import json
import math
import subprocess
import time
from pathlib import Path
import numpy as np
from m43e_economical_bank import read_sealed, write_sealed
from m43f_source_cache_preflight import build_context
from m43q_integrated_detector import AnchorStore, NativeReceiver
from m43r_joint_calibration import grid_context, compact
from m43v_component_diagnostic import coordinate, probes
from m43x_confirmation import WINDOW, validate_freeze as validate_x
from seti_repeater import search_v0p6 as core, detector_m43u as detector
from seti_repeater.injection_m43r import ScoreStore
from seti_repeater.injection_m43u import JointOverlay
from seti_repeater.mask_m43u import build_mask, bind_calibration
from seti_repeater.confirmation_m43x import apply_controls

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_m43y_response_diagnostic'
CONFIG=ROOT/'config/m43y_response_diagnostic.json'
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def neighborhood(values, full_q, width, score_start):
    """Inclusive same-width response radius; no clipping or new veto decision."""
    if width not in core.M37_SPECTRAL_WIDTHS: raise ValueError('unknown width')
    lo,hi=full_q-width//2,full_q+width//2+1
    if lo<0 or hi>values.shape[1]: raise ValueError('incomplete response neighborhood')
    block=values[:,lo:hi]
    if block.shape!=(3,width) or not np.isfinite(block).all(): raise ValueError('invalid response array')
    winners=np.argmax(block,axis=1)
    return dict(first_proxy_index=lo-score_start,last_proxy_index=hi-1-score_start,
        values=block.tolist(),center=values[:,full_q].tolist(),maximum=block.max(axis=1).tolist(),
        first_maximum_proxy_index=(lo-score_start+winners).tolist())

def direct_point_score(overlay,kind,epoch,template,full_q,width):
    """Independent raw windows, ordered float32 point additions, then row sum."""
    src=overlay.receiver.cache(f'epoch{epoch+1}_{kind}',1).source
    indices=overlay.joint_indices[kind,epoch][template,:,full_q]
    sources=[s for s in overlay.overlay_receipt['sources'] if s['scan']==f'epoch{epoch+1}_{kind}']
    total=np.float32(0); row_values=[]
    for row,index in enumerate(indices):
        lo,hi=int(index)-width//2,int(index)+width//2+1
        if lo<0 or hi>src.values.shape[1]: raise ValueError('incomplete native window')
        raw=src.values[row,lo:hi].copy()
        for s in sources:
            position=s['profiles'][row]['start']
            if lo<=position<hi: raw[position-lo]+=np.float32(s['per_row_total_strength'])
        value=np.float32(np.sum(raw,dtype=np.float32)/np.sqrt(width))
        total+=value;row_values.append(float(value))
    total/=np.float32(math.sqrt(src.integration_count))
    return dict(score=float(total),native_center_indices=indices.tolist(),filtered_row_values=row_values)

def trace(result,store,overlay,grid,inventory):
    out=probes(result,store,grid,inventory,'neighbor9')
    masks={}
    for p,item in zip(inventory,out):
        t,q,w,active=coordinate(p);fq=grid.score_slice.start+q
        item['responses']=[]
        for kind in ('on','off'):
            key=(kind,t)
            if key not in masks:
                masks[key]=build_mask(lambda width:store.get(kind,t,width)[0],'neighbor9')
            for width in core.M37_SPECTRAL_WIDTHS:
                values=store.get(kind,t,width)[0]
                n=neighborhood(values,fq,width,grid.score_slice.start)
                lo=fq-width//2;hi=fq+width//2+1
                native=[]
                for e in range(3):
                    d=direct_point_score(overlay,kind,e,t,fq,width)
                    assert np.float32(d['score']).view('<u4')==values[e,fq].view('<u4'),(kind,t,q,width,e)
                    native.append(d)
                item['responses'].append(dict(kind=kind,width=width,**n,
                    mask=masks[key][:,lo:hi].tolist(),direct_native=native))
        ids={r['record_id'] for r in item['annotated_records']}
        item['adjacent_off_evidence']=[e for e in result['adjacent_off']['evidence'] if e['record_id'] in ids]
        item['retained_off_track_evidence']=[r for r in result['off_track']['records'] if r['record_id'] in ids]
    return out

def run(anchor_root,source_root,checkpoint_root,freeze):
    started=time.monotonic();cfg=json.loads(CONFIG.read_text())
    assert subprocess.check_output(['git','show',freeze+':config/m43y_response_diagnostic.json'],cwd=ROOT)==CONFIG.read_bytes()
    for p,h in cfg['pinned_sha256'].items(): assert sha(ROOT/p)==h,p
    x=validate_x(cfg['m43x_scientific_freeze'])
    assert not (OUT/'result.json').exists(),'preserve completed result'
    checkpoint_root.mkdir(parents=True,exist_ok=True)
    historical={}
    with gzip.open(ROOT/'results_m43x_confirmation/case_audits.jsonl.gz','rt') as f:
        for line in f:
            if line.strip():
                r=json.loads(line)
                assert r['result_sha256']==detector.digest({k:v for k,v in r.items() if k!='result_sha256'})
                historical[r['case']['case_index']]=r
    _,_,_,metadata,basis,parent,parent_table,_=build_context()
    bank,table,bridge=detector.catalogue_bridge(parent,x['parent_template_indices'],basis)
    assert bridge==x['bridge']
    original,grid,start=grid_context();assert core.proxy_carrier_grid_sha256(grid)==x['grid_sha256']
    old=AnchorStore(anchor_root,{'parent_template_indices':x['parent_template_indices'],'support_carriers':original.support_bin_count})
    arrays={k:old.get(*k)[0][:,start:start+grid.support_bin_count] for k in old.expected_ids}
    provenance=dict(family='M43P-exact-central-slice',parent_inventory_sha256=detector.digest(old.inventory),
        parent_score_ids_sha256=detector.digest([[*k,v] for k,v in sorted(old.expected_ids.items())]),
        support_start=start,support_count=grid.support_bin_count,grid_sha256=x['grid_sha256'])
    assert provenance==read_sealed(ROOT/'results_m43r_joint_calibration/calibration.json')['baseline_provenance']
    baseline=ScoreStore(arrays,provenance)
    receiver=NativeReceiver(source_root,metadata,basis,parent,parent_table,original)
    overlay=JointOverlay(baseline,receiver,bank,table,basis,grid,progress=lambda m:print(m,flush=True))
    assert overlay.cache_inventory==read_sealed(ROOT/'results_m43u_signal_interference/input_anchors.json')['cache_inventory']
    common=dict(window=WINDOW,grid=grid,bank=bank,table=table,basis=basis,scans=metadata['scans'])
    cal,summary=detector.calibrate(**common,store=baseline,mask_policy='neighbor9',shifts=np.asarray(x['training_shifts'],dtype=np.int64),minimum_shift_bins=128)
    threshold=core.calibrated_threshold((cal,),expected_window_ids=(WINDOW,),reference_floor=10.,quantile=1.,scientific_p_ceiling=.01)
    binding=bind_calibration(cal,threshold,'neighbor9');previous=read_sealed(ROOT/'results_m43x_confirmation/calibration.json')
    assert summary==previous['summary'] and cal.null_maxima.tolist()==previous['null_maxima']
    assert threshold.as_record()==previous['threshold'] and binding==previous['binding']
    write_sealed(OUT/'anchors.json',dict(freeze_commit=freeze,all_96_arrays_exact=True,all_48_native_gathers_exact=True,
        m43x_calibration_replay_exact=True,new_null_rows=0,binding=binding))
    print('Original arrays, native gathers and X calibration exactly replayed',flush=True)
    records=[]
    for spec in cfg['inputs']:
        name=spec['name'];path=checkpoint_root/(name+'.json')
        if path.exists():
            rec=read_sealed(path);assert rec['freeze_commit']==freeze and rec['config_sha256']==sha(CONFIG) and rec['spec']==spec
        else:
            components=spec['components']
            assert all(c['shape']=='point' and c['snap_native'] for c in components)
            overlaid=overlay.trial(components);store=baseline if name=='baseline' else overlaid
            r=detector.execute(**common,store=store,mask_policy='neighbor9',calibration=cal,threshold=threshold,
                calibration_binding=binding,receiver_factory=overlay,maximum_records=x['maximum_records'])
            audit=compact(r,overlay.overlay_receipt);audit['masked_cell_counts']=r['masked_cell_counts']
            audits,evidence=apply_controls(audit,store,grid)
            pd={p:[{k:m[k] for k in ('record_id','passes_evaluated_physical_vetoes','physical_disposition','m43x_rejections')} for m in a['members']] for p,a in audits.items()}
            if name=='baseline':
                oldbase=read_sealed(ROOT/'results_m43x_confirmation/baseline.json')
                assert audits==oldbase['audits'] and evidence==oldbase['evidence']
            if spec['variant']=='original':
                oldcase=historical[spec['case_index']]
                assert audits['neighbor9']==oldcase['reference_audit']
                assert evidence==oldcase['confirmation_evidence'] and pd==oldcase['policy_decisions']
            rec=write_sealed(path,dict(freeze_commit=freeze,config_sha256=sha(CONFIG),spec=spec,
                reference_audit=audits['neighbor9'],policy_decisions=pd,confirmation_evidence=evidence,
                final_counts={p:a['final_diagnostic_survivors'] for p,a in audits.items()},
                trace=trace(r,store,overlay,grid,cfg['probes']),retained_off=r['retained']['off'],
                exact_historical_replay=spec['variant'] in ('baseline','original')))
        records.append(rec);print(f'{len(records)}/13 {name}: {rec["final_counts"]}',flush=True)
    assert len(records)==13
    raw=b''.join(core.canonical_json_bytes(r)+b'\n' for r in records);packed=gzip.compress(raw,compresslevel=9,mtime=0)
    (OUT/'case_audits.jsonl.gz').write_bytes(packed)
    groups={}
    for r in records:
        h=detector.digest(r['reference_audit']['overlay']['patch_payloads'])
        groups.setdefault(h,[]).append(r['spec']['name'])
    write_sealed(OUT/'result.json',dict(milestone='M43Y',complete=True,freeze_commit=freeze,base_executions=13,
        policy_endpoints=39,original_control_replays=6,separate_baseline_replays=1,new_component_inputs=6,
        distinct_native_patch_inventories=len(groups),patch_identity_groups=groups,probes_per_input=len(cfg['probes']),
        direct_native_scalar_comparisons=13*len(cfg['probes'])*48,
        summary=[dict(name=r['spec']['name'],final_counts=r['final_counts']) for r in records],
        ledger_sha256=hashlib.sha256(packed).hexdigest(),ledger_uncompressed_sha256=hashlib.sha256(raw).hexdigest(),
        wall_seconds=round(time.monotonic()-started,3),new_null_rows=0,new_telescope_requests=0,
        detector_changed=False,independent_validation=False,general_adoption_qualified=False))
    print('M43Y COMPLETE',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--freeze-commit',required=True)
    p.add_argument('--anchor-root',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--checkpoint-root',type=Path,required=True);a=p.parse_args()
    run(a.anchor_root,a.source_root,a.checkpoint_root,a.freeze_commit)
