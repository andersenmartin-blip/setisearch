"""Retrospective M43Z native shapes and stage transitions; no new detector rule."""
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
from m43s_profile_sensitivity import endpoint
from m43v_component_diagnostic import coordinate, probes
from m43z_joint_controls import WINDOW, validate_freeze
from seti_repeater import search_v0p6 as core, detector_m43u as detector
from seti_repeater.injection_m43r import ScoreStore
from seti_repeater.injection_m43s import fractional_profile, restore_calibration
from seti_repeater.injection_m43u import JointOverlay
from seti_repeater.transfer_m43g import array_hash
from seti_repeater.confirmation_m43z import apply_controls
from seti_repeater.mask_m43u import bind_calibration

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results_m43aa_native_response'
CONFIG = ROOT / 'config/m43aa_native_response.json'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def shape(values, first_index):
    """First global maximum and its contiguous half-height lobe, zero baseline.

    This is a descriptive filtered-response width, not a fitted source width.
    A lobe touching either boundary is explicitly marked censored.
    """
    v = np.asarray(values, dtype=float)
    if v.ndim != 1 or not len(v) or not np.isfinite(v).all():
        raise ValueError('finite response vector required')
    peak = int(np.argmax(v)); height = float(v[peak])
    if height <= 0:
        return dict(peak_index=first_index+peak, peak=height, half_height_width_bins=None,
                    half_height_left=None, half_height_right=None, boundary_censored=None)
    lo = hi = peak
    while lo > 0 and v[lo-1] >= height/2: lo -= 1
    while hi+1 < len(v) and v[hi+1] >= height/2: hi += 1
    return dict(peak_index=first_index+peak, peak=height, half_height_width_bins=hi-lo+1,
                half_height_left=first_index+lo, half_height_right=first_index+hi,
                boundary_censored=lo == 0 or hi == len(v)-1)

def similarity(a, b):
    """Unshifted mean-subtracted cosine; undefined for a constant vector."""
    a = np.asarray(a, dtype=float); b = np.asarray(b, dtype=float)
    a = a-a.mean(); b = b-b.mean()
    denom = float(np.linalg.norm(a)*np.linalg.norm(b))
    return None if denom == 0 else float(np.dot(a,b)/denom)

def native_parts(overlay, components):
    """Reconstruct point/sinc profiles and verify every original receipt hash."""
    parts = {}; receipt_index = 0
    for c in components:
        truth = c['truth']; factors = core.template_factors_from_basis(overlay.basis, truth)
        q = float(overlay.grid.score_hz[truth['score_index']] + truth['fractional_proxy_bin']*overlay.grid.channel_width_hz)
        for epoch in c['epochs']:
            label = f"epoch{epoch+1}_{c['kind']}"
            src = overlay.receiver.cache(label, 1).source
            f = np.asarray([factors[i] for i,x in enumerate(overlay.basis.labels) if x.scan_label == label])
            positions = (q*f-src.geometry.raw_zero_hz)/src.geometry.channel_width_hz
            if c['snap_native']: positions = np.rint(positions)
            profiles = ([(int(x), np.ones(1,dtype='<f8')) for x in positions]
                        if c['shape'] == 'point' else fractional_profile(positions,smear_channels=c['smear_channels'])[0])
            strength = float(c['strength']/math.sqrt(src.integration_count))
            receipt = overlay.overlay_receipt['sources'][receipt_index]; receipt_index += 1
            assert receipt['component_id'] == c['component_id'] and receipt['scan'] == label
            assert receipt['per_row_total_strength'] == strength
            assert receipt['profiles'] == [dict(start=lo,sha256=array_hash(p)) for lo,p in profiles]
            parts.setdefault((c['kind'],epoch),[]).append((profiles,strength))
    assert receipt_index == len(overlay.overlay_receipt['sources'])
    return parts

def raw_window_score(src, indices, parts, width):
    """Independent explicit native windows with ordered float32 additions."""
    total = np.float32(0); rows = []; footprints = []
    for row, index in enumerate(indices):
        lo = int(index)-width//2; hi = lo+width
        if lo < 0 or hi > src.values.shape[1]: raise ValueError('incomplete native window')
        raw = src.values[row,lo:hi].copy(); masses = []
        for profiles,strength in parts:
            start,profile = profiles[row]; left=max(lo,start); right=min(hi,start+len(profile))
            masses.append(float(profile[max(0,left-start):max(0,right-start)].sum()) if left < right else 0.)
            if left < right:
                raw[left-lo:right-lo] += (profile[left-start:right-start]*strength).astype('<f4')
        value = np.float32(np.sum(raw,dtype=np.float32)/np.sqrt(width))
        total += value; rows.append(float(value)); footprints.append(masses)
    total /= np.float32(math.sqrt(src.integration_count))
    return dict(score=float(total), native_center_indices=np.asarray(indices).tolist(),
                filtered_row_values=rows, component_mass_in_window=footprints)

def response_profiles(store, baseline, overlay, parts, grid, inventory, radius):
    out = []; count = 0
    for t,q in sorted({coordinate(p)[:2] for p in inventory}):
        fq = grid.score_slice.start+q; lo=fq-radius; hi=fq+radius+1
        if lo < 0 or hi > grid.support_bin_count: raise ValueError('response boundary incomplete')
        widths = []
        for w in core.M37_SPECTRAL_WIDTHS:
            kinds = {}
            for kind in ('on','off'):
                values = store.get(kind,t,w)[0]; base = baseline.get(kind,t,w)[0]
                block = values[:,lo:hi]; b = base[:,lo:hi]
                direct = []
                for e in range(3):
                    src = overlay.receiver.cache(f'epoch{e+1}_{kind}',1).source
                    d = raw_window_score(src,overlay.joint_indices[kind,e][t,:,fq],parts.get((kind,e),[]),w)
                    assert np.float32(d['score']).view('<u4') == values[e,fq].view('<u4'),(kind,e,t,q,w)
                    direct.append(d); count += 1
                kinds[kind] = dict(values=block.tolist(),baseline_values=b.tolist(),
                    shape=[shape(v,q-radius) for v in block],
                    baseline_shape=[shape(v,q-radius) for v in b],
                    increment_shape=[shape(v.astype(float)-bv,q-radius) for v,bv in zip(block,b)],
                    direct_native=direct)
            correlations = dict(on_epoch_pairs={f'{a}:{b}':similarity(kinds['on']['values'][a],kinds['on']['values'][b])
                for a,b in ((0,1),(0,2),(1,2))},
                paired_on_off=[similarity(a,b) for a,b in zip(kinds['on']['values'],kinds['off']['values'])])
            widths.append(dict(width=w,**kinds,correlations=correlations))
        out.append(dict(template_index=t,proxy_carrier_index=q,first_proxy_index=q-radius,
                        last_proxy_index=q+radius,widths=widths))
    return out,count

def run(runtime, freeze):
    started=time.monotonic(); cfg=json.loads(CONFIG.read_text())
    assert subprocess.check_output(['git','show',freeze+':config/m43aa_native_response.json'],cwd=ROOT)==CONFIG.read_bytes()
    for p,h in cfg['pinned_sha256'].items(): assert sha(ROOT/p)==h,p
    z=validate_freeze(cfg['m43z_execution_freeze'])
    assert not (OUT/'result.json').exists(),'preserve complete result'
    OUT.mkdir(exist_ok=True); (OUT/'inputs').mkdir(exist_ok=True)
    _,_,_,metadata,basis,parent,parent_table,_=build_context()
    bank,table,bridge=detector.catalogue_bridge(parent,z['parent_template_indices'],basis); assert bridge==z['bridge']
    original,grid,start=grid_context(); assert core.proxy_carrier_grid_sha256(grid)==z['grid_sha256']
    old=AnchorStore(runtime/'anchors',dict(parent_template_indices=z['parent_template_indices'],support_carriers=original.support_bin_count))
    arrays={k:old.get(*k)[0][:,start:start+grid.support_bin_count] for k in old.expected_ids}
    provenance=dict(family='M43P-exact-central-slice',parent_inventory_sha256=detector.digest(old.inventory),
        parent_score_ids_sha256=detector.digest([[*k,v] for k,v in sorted(old.expected_ids.items())]),
        support_start=start,support_count=grid.support_bin_count,grid_sha256=z['grid_sha256'])
    assert provenance==read_sealed(ROOT/'results_m43r_joint_calibration/calibration.json')['baseline_provenance']
    baseline=ScoreStore(arrays,provenance)
    receiver=NativeReceiver(runtime/'sources',metadata,basis,parent,parent_table,original)
    overlay=JointOverlay(baseline,receiver,bank,table,basis,grid,progress=lambda m:print(m,flush=True))
    assert overlay.cache_inventory==read_sealed(ROOT/'results_m43u_signal_interference/input_anchors.json')['cache_inventory']
    prior=read_sealed(ROOT/'results_m43z_joint_controls/calibration.json')
    cal,threshold=restore_calibration(prior,prior['result_sha256'],prior['threshold']['certificate_sha256'])
    binding=bind_calibration(cal,threshold,'neighbor9'); assert binding==prior['binding']
    write_sealed(OUT/'anchors.json',dict(freeze_commit=freeze,all_96_arrays_exact=True,all_48_native_gathers_exact=True,
        calibration_restored_exactly=True,calibration_sha256=prior['result_sha256'],binding=binding,new_null_rows=0))
    historical={}
    with gzip.open(ROOT/'results_m43z_joint_controls/case_audits.jsonl.gz','rt') as f:
        for line in f:
            if line.strip():
                r=json.loads(line)
                if r['case']['case_index'] in cfg['historical_cases']:
                    assert r['result_sha256']==detector.digest({k:v for k,v in r.items() if k!='result_sha256'})
                    historical[r['case']['case_index']]=r
    assert set(historical)==set(cfg['historical_cases'])
    common=dict(window=WINDOW,grid=grid,bank=bank,table=table,basis=basis,scans=metadata['scans'])
    factors=np.stack([core.factor_table_for_scan(table,basis,f'epoch{e+1}_on') for e in range(3)],axis=1)
    summaries=[]; checks=0
    for spec in cfg['inputs']:
        path=OUT/'inputs'/(spec['name']+'.json.gz')
        if path.exists():
            rec=json.loads(gzip.decompress(path.read_bytes()))
            assert rec['result_sha256']==detector.digest({k:v for k,v in rec.items() if k!='result_sha256'})
            assert rec['freeze_commit']==freeze and rec['spec']==spec
        else:
            store=overlay.trial(spec['components']); parts=native_parts(overlay,spec['components'])
            if spec['variant']=='baseline': store=baseline
            result=detector.execute(**common,store=store,mask_policy='neighbor9',calibration=cal,threshold=threshold,
                calibration_binding=binding,receiver_factory=overlay,maximum_records=z['maximum_records'])
            audit=compact(result,overlay.overlay_receipt); audit['masked_cell_counts']=result['masked_cell_counts']
            audits,evidence=apply_controls(audit,store,grid)
            decisions={p:[{k:m[k] for k in ('record_id','passes_evaluated_physical_vetoes','physical_disposition','m43z_rejections')}
                for m in a['members']] for p,a in audits.items()}
            if spec['variant']=='historical':
                previous=historical[spec['case_index']]
                assert audits['neighbor9']==previous['reference_audit'],spec['name']
                assert evidence==previous['confirmation_evidence'] and decisions==previous['policy_decisions']
            elif spec['variant']=='baseline':
                previous=read_sealed(ROOT/'results_m43z_joint_controls/baseline.json')
                assert audits==previous['audits'] and evidence==previous['evidence']
            inventory=cfg['probes'][spec['group']]
            stage=probes(result,store,grid,inventory,'neighbor9')
            for item in stage:
                ids={r['record_id'] for r in item['annotated_records']}
                item['off_track']=[r for r in result['off_track']['records'] if r['record_id'] in ids]
                item['adjacent_off']=[r for r in result['adjacent_off']['evidence'] if r['record_id'] in ids]
                item['policy_decisions']={p:[r for r in rows if r['record_id'] in ids] for p,rows in decisions.items()}
            responses,n=response_profiles(store,baseline,overlay,parts,grid,inventory,cfg['response_radius_bins'])
            associations={}
            if spec['case_index'] is not None:
                case=z['cases'][spec['case_index']]
                associations={p:endpoint(a,case['reference_truth'],grid,factors,basis,case['strength'],spec['name']) for p,a in audits.items()}
            rec=dict(freeze_commit=freeze,config_sha256=sha(CONFIG),spec=spec,reference_audit=audits['neighbor9'],
                policy_decisions=decisions,confirmation_evidence=evidence,associations=associations,
                stage_trace=stage,responses=responses,direct_native_comparisons=n,
                exact_historical_replay=spec['variant'] in ('baseline','historical'),
                final_counts={p:a['final_diagnostic_survivors'] for p,a in audits.items()})
            rec['result_sha256']=detector.digest(rec)
            path.write_bytes(gzip.compress(core.canonical_json_bytes(rec),compresslevel=6,mtime=0))
        checks+=rec['direct_native_comparisons']
        summaries.append(dict(name=spec['name'],group=spec['group'],final_counts=rec['final_counts'],
            associations={p:a['recovered'] for p,a in rec['associations'].items()},file=path.relative_to(ROOT).as_posix(),
            file_sha256=sha(path),record_sha256=rec['result_sha256']))
        print(f"{len(summaries)}/{len(cfg['inputs'])} {spec['name']}: {rec['final_counts']}",flush=True)
        write_sealed(OUT/'progress.json',dict(complete=False,completed_inputs=len(summaries),planned_inputs=len(cfg['inputs'])))
    write_sealed(OUT/'result.json',dict(milestone='M43AA',complete=True,retrospective=True,freeze_commit=freeze,
        inputs=len(summaries),policy_endpoints=4*len(summaries),summary=summaries,direct_native_comparisons=checks,
        new_null_rows=0,new_observing_sequences=0,detector_changed=False,general_adoption_qualified=False,
        physical_false_alarm_probability_measured=False,prior_X_Z_losses_remain=True,wall_seconds=round(time.monotonic()-started,3)))
    write_sealed(OUT/'progress.json',dict(complete=True,completed_inputs=len(summaries),planned_inputs=len(cfg['inputs'])))
    print('M43AA COMPLETE',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--runtime-root',type=Path,required=True);p.add_argument('--freeze-commit',required=True)
    a=p.parse_args();run(a.runtime_root,a.freeze_commit)
