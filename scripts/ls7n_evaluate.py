#!/usr/bin/env python3
"""Frozen LS7N native comparison and downstream PRF pulse protection."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import platform

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from seti_repeater.tess_prf_response import PRFCatalog
from seti_repeater.tess_calibrated_motion import side_indices,side_state,plane_basis,source_fit,protected_plane,sample_positions,corrections,response_metrics
from seti_repeater.tess_background import common_energy

OUT=ROOT/'results_ls7n_response'
METHODS=['static','motion','plane','combined']


def read(path):return json.loads(path.read_text())
def rows(path):return [json.loads(x) for x in gzip.decompress(path.read_bytes()).splitlines()]
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def serial(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,dict):return {k:serial(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [serial(v) for v in value]
    return value
def save(path,value):path.write_text(json.dumps(serial(value),indent=2,allow_nan=False)+'\n')
def save_rows(path,records):path.write_bytes(gzip.compress(b''.join((json.dumps(serial(r),separators=(',',':'),allow_nan=False)+'\n').encode() for r in records),mtime=0))


def summarize(native,pulses):
    cells=[]
    for sector in [29,32]:
        for offset in [0,-44]:
            selected=[r for r in native if r['sector']==sector and r['column_offset']==offset]
            methods={}
            for method in METHODS:
                available=[r for r in selected if r['energies'][method] is not None]
                backgrounds=[]
                for anchor in range(10):
                    rr=[r for r in available if r['anchor']==anchor]
                    baseline=sum(r['energies']['static'] for r in rr);energy=sum(r['energies'][method] for r in rr)
                    backgrounds.append({'anchor':anchor,'windows':len(rr),'ratio':energy/baseline if baseline>0 else None})
                static=sum(r['energies']['static'] for r in available);energy=sum(r['energies'][method] for r in available)
                ratio=energy/static if static>0 else None
                gates={'all_210_available':len(available)==210,'aggregate_not_increased':ratio is not None and ratio<=1,
                       'six_backgrounds_improve':sum(b['ratio'] is not None and b['ratio']<1 for b in backgrounds)>=6,
                       'no_background_doubled':all(b['ratio'] is not None and b['ratio']<=2 for b in backgrounds)}
                methods[method]={'windows':len(available),'static_energy':static,'energy':energy,'ratio':ratio,
                                 'backgrounds':backgrounds,'gates':gates,'pass':all(gates.values())}
            protection={}
            for variant,limit in [('nominal',.01),('minus_entries',.05),('plus_entries',.05)]:
                pp=[p for p in pulses if p['sector']==sector and p['column_offset']==offset and p['variant']==variant]
                vv=[p for p in pp if p['metrics'] is not None]
                protection[variant]={'cases':len(pp),'available':len(vv),'distortion_limit':limit,
                                     'maximum_distortion':max((p['metrics']['relative_distortion'] for p in vv),default=None),
                                     'gain_range':[min((p['metrics']['gain'] for p in vv),default=None),max((p['metrics']['gain'] for p in vv),default=None)],
                                     'failed_cases':sum(p['metrics'] is None or p['metrics']['relative_distortion']>limit for p in pp)}
            passed=methods['combined']['pass'] and all(p['cases']==1050 and p['failed_cases']==0 for p in protection.values())
            cells.append({'sector':sector,'column_offset':offset,'methods':methods,'protection':protection,'pass':passed})
    return {'cells':cells,'joint_feasibility_pass':all(c['pass'] for c in cells)}


def main():
    assert not OUT.exists(),'refuse to overwrite completed LS7N results'
    cfg=read(ROOT/'config/ls7n_response.json')
    for p,sha in cfg['input_sha256'].items():assert digest(ROOT/p)==sha,p
    raw={}
    for d in read(ROOT/'results_ls7i_inputs/datasets.json'):
        with np.load(ROOT/d['contexts'],allow_pickle=False) as archive:
            raw[d['sector']]={k:archive[k] for k in ['native','aperture']}
    auxiliary={s:np.load(ROOT/f'results_ls7j_auxiliary/auxiliary_s{s:03d}.npz',allow_pickle=False)['position_yx'][...,::-1] for s in [29,32]}
    windows=rows(ROOT/'results_ls7i_background/native_windows.jsonl.gz')
    baselines={r['fold_id']:r for r in read(ROOT/'results_ls7j_auxiliary/baselines.json')}
    inv=read(ROOT/'results_ls7k_inputs/inventory.json');catalog=PRFCatalog(ROOT)
    models={};sources={}
    for sector in [29,32]:
        d=next(d for d in inv['light_curves'] if d['sector']==sector);sources[sector]=np.array(d['geometry']['nominal_target_cutout_xy'])
        for offset in cfg['column_offsets']:
            models[(sector,offset)]=catalog.local(d['ccd'],d['geometry']['nominal_target_detector_xy'],calibration_column_offset=offset)[0]
    yy,xx=np.indices((11,11));pixels=np.stack([xx,yy],axis=-1);support=xx>=1;plane=plane_basis((11,11))
    OUT.mkdir();native=[];pulses=[]
    for wi,w in enumerate(windows):
        s,a,lo,hi=w['sector'],w['anchor'],w['start'],w['stop'];side=side_indices(lo,hi);event=np.arange(lo,hi)
        selected=np.r_[side,event];cube=raw[s]['native'][a];ap=raw[s]['aperture'];outside=support&~ap
        assert not np.any(ap&~support)
        state=side_state(cube,ap,lo,hi,support)
        zero=np.median(auxiliary[s][a,side],axis=0);position=auxiliary[s][a]-zero
        series={};protected=[]
        for offset in cfg['column_offsets']:
            series[offset]=sample_positions(models[(s,offset)],pixels,sources[s],position[selected])
            for shift in cfg['protected_shifts_xy']:
                p,_=sample_positions(models[(s,offset)],pixels,sources[s],position[event],shift)
                protected.append(p.mean(0))
        protection=protected_plane(np.array(protected),plane,state['pixel_noise'],outside)
        delta=cube[event].mean(0)-state['reference'];y=delta[ap]/state['sigma']
        np.testing.assert_allclose(y,w['y'],rtol=1e-12,atol=1e-12)
        baseline=baselines[w['fold_id']];residual=y-baseline['mean'];cov=np.array(baseline['covariance'])
        static=common_energy(residual,cov);np.testing.assert_allclose(static,w['energies']['static'],rtol=1e-10,atol=1e-9)
        for offset in cfg['column_offsets']:
            images,entries=series[offset];median_prf=np.median(images[:len(side)],axis=0)
            event_prf=images[len(side):].mean(0)
            fit=source_fit(state['reference'],median_prf,plane,state['pixel_noise'],support)
            motion=fit['beta'][0]*(event_prf-median_prf) if fit['valid'] else None
            envelope=fit['beta'][0]*(entries[len(side):].mean(0)+entries[:len(side)].max(0)) if fit['valid'] else None
            pred=corrections(delta,motion,plane,outside,protection['operator']);energies={'static':static}
            accounting={}
            for method in METHODS[1:]:
                correction=pred[method]
                energies[method]=None if correction is None else common_energy(residual-correction[ap]/state['sigma'],cov)
                if correction is not None:
                    v=correction[ap]/state['sigma'];size=common_energy(v,cov)
                    alignment=(static+size-energies[method])/2
                    accounting[method]={'correction_energy':size,'alignment':alignment}
            case=f"{w['window_id']}/offset{offset}"
            record={'case_id':case,'window_id':w['window_id'],'sector':s,'anchor':a,'start':lo,'stop':hi,'fold_id':w['fold_id'],
                    'column_offset':offset,'position_reference_xy':zero,'source_fit':fit,'plane_valid':protection['valid'],
                    'protected_rank':protection['source_rank'],'plane_rank':protection['plane_rank'],'plane_condition':protection['condition'],
                    'sigma':state['sigma'],'variance_floor':state['variance_floor'],'energies':energies,'accounting':accounting,
                    'correction_aperture':{m:None if v is None else v[ap] for m,v in pred.items()},
                    'uncertainty_entry_envelope_aperture':None if envelope is None else envelope[ap]}
            native.append(record)
            for si,shift in enumerate(cfg['injected_shifts_xy']):
                p,u=sample_positions(models[(s,offset)],pixels,sources[s],position[event],shift)
                p,u=p.mean(0),u.mean(0)
                for variant,profile in [('nominal',p),('minus_entries',np.maximum(p-u,0)),('plus_entries',p+u)]:
                    added=corrections(delta+profile,motion,plane,outside,protection['operator'])['combined']
                    actual=None if added is None else profile[ap]-(added-pred['combined'])[ap]
                    metric=None if actual is None else response_metrics(profile[ap],actual)
                    pulses.append({'case_id':case+f'/pulse{si}/{variant}','window_id':w['window_id'],'sector':s,'column_offset':offset,
                                   'shift_index':si,'variant':variant,'metrics':metric})
        if (wi+1)%70==0:print(f'Native windows: {wi+1}/420; paired coordinate rows: {len(native)}; pulse rows: {len(pulses)}',flush=True)
    assert len(native)==840 and len(pulses)==12600
    save_rows(OUT/'native.jsonl.gz',native);save_rows(OUT/'pulses.jsonl.gz',pulses)
    result={'study':'LS7N cadence-level calibrated native response','source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            'python':platform.python_version(),'config_sha256':digest(ROOT/'config/ls7n_response.json'),
            'native_windows':420,'model_window_rows':840,'pulse_response_rows':12600,'backgrounds':20,
            'native_pixel_response_evaluated':True,'quaternion_response_evaluated':False,'new_detector_decisions':0,'added_observing_days':0,
            **summarize(native,pulses)}
    save(OUT/'summary.json',result)
    print(json.dumps({'joint_feasibility_pass':result['joint_feasibility_pass'],'combined_ratios':[(c['sector'],c['column_offset'],c['methods']['combined']['ratio']) for c in result['cells']]},indent=2),flush=True)


if __name__=='__main__':main()
