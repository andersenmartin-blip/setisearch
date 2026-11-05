#!/usr/bin/env python3
"""Compact synthetic-only checks; never open observational arrays."""
from pathlib import Path
import ast,hashlib,importlib.util,json,math
import numpy as np
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
def module(p):
    spec=importlib.util.spec_from_file_location('c035_synthetic_target',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=module(HERE/'compare_group.py');checks=[]
def check(test,label):
    if not test:raise AssertionError(label)
    checks.append(label)
def funcs(p):return{n.name:ast.dump(n,include_attributes=False)for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef)}
a=funcs(HERE/'compare_group.py');b=funcs(REPO/'work_harps_20261103_c015_context/analysis/compare_group.py')
for name in ['sampling_parameters','profile','comparison']:check(a[name]==b[name],name+' function unchanged from C015')
check(int(m.CORE.sum())==51 and int(m.BROAD.sum())==550,'51 core / 550 surrounding centers')
check(len(m.EVENTS)==1 and len(m.REFERENCES)==1,'One original record and own fixed reference')
check(m.COVERING_ORDERS=={'ADP.2025-03-31T01:04:04.493': [54]},'Own all72-header-confirmed order54 retained')
check(m.ANCHOR_BERV==18.1525360721304 and m.REFERENCES[0]=='ADP.2025-03-31T01:04:04.493','C035 uses its own March30 2025 HD128582 discovery and recomputed wavelength anchor')
w=m.CB+np.arange(-700,701)/100;f=200+15*np.sin(np.arange(len(w))*.1);e=np.full(len(w),np.nan)
for berv in [18.1525360721304,-24.8175760325439,26.7544256646121]:
    for frame in m.FRAMES:
        p,q=m.profile(w,f,e,berv,frame,.01)
        check(q['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE' and q['raw_grid_finite_samples']==601,'Full positive synthetic '+str(berv)+' '+frame)
        p2,q2=m.profile(w,7*f,e,berv,frame,.01)
        check(np.allclose(p['normalized_flux'],p2['normalized_flux'],rtol=1e-13,atol=1e-13),'Positive scaling invariance '+str(berv)+' '+frame)
        for mask,minimum in [(m.CORE,41),(m.BROAD,440)]:
            c=m.comparison(p,p,mask);check(c['minimum_common_samples']==minimum and abs(c['raw_pearson']-1)<1e-14 and c['normalized_rms']==0,'Self support Pearson RMS '+str(berv)+' '+frame+' '+str(minimum))
    center,scale=m.sampling_parameters(berv,'topocentric');check(center==m.CT and np.allclose((center+m.X)*scale/(1+berv/m.C),m.CT+m.X,rtol=0,atol=1e-12),'One native topocentric anchor '+str(berv))
wshort=m.CB+np.arange(-300,101)/100;p,q=m.profile(wshort,np.ones(len(wshort))*10,np.full(len(wshort),np.nan),m.ANCHOR_BERV,'barycentric',.01)
check(q['normalization_status']=='RAW_ONLY' and 'MISSING_RIGHT_FLANK_COVERAGE'in q['normalization_reasons'] and np.isfinite(p['signed_raw_flux'][m.CORE]).all(),'Missing right flank remains raw-only with core support')
wpartial=m.CB+np.arange(-300,117)/100
fpartial=10+np.sin(np.arange(len(wpartial))*.1)
p,q=m.profile(wpartial,fpartial,np.full(len(wpartial),np.nan),m.ANCHOR_BERV,'barycentric',.01)
check(q['raw_grid_finite_samples']==417 and q['normalized_grid_finite_samples']==0 and q['right_flank_native_samples']==0,'Synthetic truncated endpoint preserves 417 raw samples and missing right flank')
cc=m.comparison(p,p,m.CORE);bc=m.comparison(p,p,m.BROAD)
check(cc['common_finite_raw_samples']==51 and cc['raw_pearson']is not None and cc['normalized_rms']is None,'Synthetic partial order retains raw core Pearson but not normalized RMS')
check(bc['common_finite_raw_samples']==366 and bc['raw_pearson_block_reason']=='INSUFFICIENT_COMMON_RAW_COVERAGE' and bc['normalized_rms']is None,'Synthetic partial order retains 366 surrounding samples below fixed 440 gate')
p,q=m.profile(w,-f,e,m.ANCHOR_BERV,'barycentric',.01);check(q['normalization_status']=='RAW_ONLY' and 'NONPOSITIVE_FLANK_REFERENCE'in q['normalization_reasons'],'Negative reference never sign-flipped')
p,q=m.profile(w,np.zeros(len(w)),e,m.ANCHOR_BERV,'barycentric',.01);check(q['normalization_status']=='RAW_ONLY' and 'NONPOSITIVE_FLANK_REFERENCE'in q['normalization_reasons'] and q['low_flank_reference']is None,'Zero reference remains raw-only with null low flag')
fmissing=np.ones(len(w))*10;off=w-m.CB;fmissing[(off>=1.5)&(off<=3)]=np.nan
p,q=m.profile(w,fmissing,e,m.ANCHOR_BERV,'barycentric',.01);check(q['normalization_status']=='RAW_ONLY' and 'INSUFFICIENT_FINITE_RIGHT_FLANK'in q['normalization_reasons'] and q['right_flank_native_samples']>0 and q['right_flank_finite_samples']==0,'Geometric flank and finite flank support remain distinct')
flow=np.random.default_rng(150095).normal(0,10,len(w));flanks=(np.abs(w-m.CB)>=1.5)&(np.abs(w-m.CB)<=3);flow+=1-np.median(flow[flanks])
p,q=m.profile(w,flow,e,m.ANCHOR_BERV,'barycentric',.01);check(q['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE' and q['low_flank_reference']is True,'Positive but low reference retains explicit true flag and signed negative samples')
p={'signed_raw_flux':np.ones(601)*.1,'normalized_flux':np.ones(601)};check(m.comparison(p,p,m.CORE)['raw_pearson_block_reason']=='ZERO_RAW_VARIANCE','Exact constant zero-range guard')
for mask,minimum in [(m.CORE,41),(m.BROAD,440)]:
    for count in [minimum-1,minimum]:
        f=np.full(601,np.nan);f[np.flatnonzero(mask)[:count]]=np.arange(count,dtype=float);p={'signed_raw_flux':f,'normalized_flux':f}
        r=m.comparison(p,p,mask);check((r['raw_pearson']is not None)==(count>=minimum),'Common support boundary '+str(count)+'/'+str(minimum))
wedge=m.CB+np.arange(-300,257)/100;fedge=10+np.sin(np.arange(len(wedge))*.1)
p,q=m.profile(wedge,fedge,np.full(len(wedge),np.nan),m.ANCHOR_BERV,'barycentric',.01)
check(q['raw_grid_finite_samples']==557 and q['normalized_grid_finite_samples']==557 and q['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE','Partial broad endpoint can retain both valid flanks and positive normalization without extrapolation')
c=m.comparison(p,p,m.BROAD)
check(c['common_finite_raw_samples']==506 and c['raw_pearson']is not None and c['normalized_rms']==0,'Partially covered surrounding region remains measurable above fixed440gate')
plan=json.loads((HERE/'PLAN.json').read_text())
check(plan['target']=='HD128582' and plan['events']==m.EVENTS and plan['anchor_berv_km_s']==m.ANCHOR_BERV,'Own target, event and anchor in fixed plan')
check(plan['slots']['all_profiles']==14 and plan['slots']['all_comparisons']==28,'14 profile / 28 comparison slots')
check(plan['wavelength_dependency']['same_six_existing_observations_reused'] is True,'Six reused observations and prior epoch/raw exposure retained')
check(len(plan['event_markers'])==1 and len({r['event']for r in plan['event_markers']})==1,'Own exact original marker identity')
check(sum(r['common_core_covers_original_member_core']for r in plan['event_markers'])==1 and all(r['original_core_inside_broad_context']for r in plan['event_markers']),'Singleton barycentric core matches common core; own-frame bounds retained')
handoff=json.loads((REPO/'work_harps_20261105_c032_context/NEXT_ACTION.json').read_bytes());context={r['candidate_id']:r for r in handoff['existing_context']};epochs={r['dp_id']:r for r in handoff['existing_cohort_epochs']}
for mark in plan['event_markers']:
    center=float(context[mark['event']]['center_bary_air_angstrom']);factor=1+epochs[m.EVENTS[mark['event']]]['berv_km_s']/m.C
    check(mark['center_bary_air_angstrom']==center and mark['original_core_bary_air_angstrom']==[center-.25,center+.25] and mark['barycentric_offset_angstrom']==center-m.CB and mark['discovery_topocentric_offset_angstrom']==center/factor-m.CT and mark['member_core_half_width_topo_angstrom']==.25/factor,'Exact original center and discovery-frame core '+mark['event'])
for path,h in plan['source_hashes'].items(): check(hashlib.sha256((REPO/path).read_bytes()).hexdigest()==h,'Frozen source exact: '+path)
r={'status':'PASS_COMPACT_SYNTHETIC_PREFLIGHT','checks':checks,'observational_arrays_read':False,'network_requests':0,'script_sha256':hashlib.sha256((HERE/'compare_group.py').read_bytes()).hexdigest(),'plan_sha256':hashlib.sha256((HERE/'PLAN.json').read_bytes()).hexdigest()}
(HERE/'SYNTHETIC_PREFLIGHT.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='checks'}));print('checks',len(checks))
