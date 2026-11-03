#!/usr/bin/env python3
"""Compact synthetic-only checks; never open observational arrays."""
from pathlib import Path
import ast,hashlib,importlib.util,json,math
import numpy as np
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
def module(p):
    spec=importlib.util.spec_from_file_location('c011_synthetic_target',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=module(HERE/'compare_group.py');checks=[]
def check(test,label):
    if not test:raise AssertionError(label)
    checks.append(label)
def funcs(p):return{n.name:ast.dump(n,include_attributes=False)for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef)}
a=funcs(HERE/'compare_group.py');b=funcs(REPO/'work_harps_20261103_c012_context/analysis/compare_group.py')
for name in ['sampling_parameters','profile','comparison']:check(a[name]==b[name],name+' function unchanged from C012')
check(int(m.CORE.sum())==51 and int(m.BROAD.sum())==550,'51 core / 550 surrounding centers')
check(len(m.EVENTS)==1 and len(m.REFERENCES)==1,'One record / one fixed reference product')
check(m.COVERING_ORDERS=={'ADP.2025-05-29T01:01:14.389':[2,3]},'Freshly confirmed both native covering orders 2 and 3 retained')
check(m.ANCHOR_BERV==-5.48386283255014 and m.REFERENCES[0]=='ADP.2025-05-29T01:01:14.389','C011 uses its own May 2025 HD112410 discovery and recomputed wavelength anchor')
w=m.CB+np.arange(-700,701)/100;f=200+15*np.sin(np.arange(len(w))*.1);e=np.full(len(w),np.nan)
for berv in [3.40485846065643,-5.48386283255014,-17.8979901476463]:
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
flow=np.random.default_rng(110089).normal(0,10,len(w));flanks=(np.abs(w-m.CB)>=1.5)&(np.abs(w-m.CB)<=3);flow+=1-np.median(flow[flanks])
p,q=m.profile(w,flow,e,m.ANCHOR_BERV,'barycentric',.01);check(q['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE' and q['low_flank_reference']is True,'Positive but low reference retains explicit true flag and signed negative samples')
p={'signed_raw_flux':np.ones(601)*.1,'normalized_flux':np.ones(601)};check(m.comparison(p,p,m.CORE)['raw_pearson_block_reason']=='ZERO_RAW_VARIANCE','Exact constant zero-range guard')
for mask,minimum in [(m.CORE,41),(m.BROAD,440)]:
    for count in [minimum-1,minimum]:
        f=np.full(601,np.nan);f[np.flatnonzero(mask)[:count]]=np.arange(count,dtype=float);p={'signed_raw_flux':f,'normalized_flux':f}
        r=m.comparison(p,p,mask);check((r['raw_pearson']is not None)==(count>=minimum),'Common support boundary '+str(count)+'/'+str(minimum))
plan=json.loads((HERE/'PLAN.json').read_text())
handoff=json.loads((REPO/'work_harps_20261103_c012_context/NEXT_ACTION.json').read_text())
check(m.CB==3865.6775000000002 and plan['group_center_bary_air_angstrom']==m.CB,'Exact catalog float retained without input rounding')
check(plan['target']=='HD112410','New target is explicitly HD112410')
check(plan['merged_dp_ids']==[r['dp_id'] for r in handoff['existing_cohort_epochs']] and len(set(plan['merged_dp_ids']))==7,'Own seven HD112410 products retained exactly')
bervs=[r['berv_km_s'] for r in handoff['existing_cohort_epochs']]
check(max(bervs)-min(bervs)==21.30284860830273,'Own target BERV span retained, not previous target span')
check(plan['historical_review_disagreement']['primary_code']=='U' and plan['historical_review_disagreement']['secondary_code']=='U' and plan['historical_review_disagreement']['root_adopted_code']=='U','Historical U/U/U reviews retained')
for item in plan['native_fixed_frame_header_geometry']:
    for frame,geometry in item['fixed_frame_header_geometry'].items():
        lo,hi=geometry['offset_endpoints_from_frame_center_angstrom'];covered=(m.X>=lo)&(m.X<=hi)
        expected=601
        check(item['order']in [2,3] and int(covered.sum())==expected,'Header-only native geometry '+str(item['order'])+' '+frame+' '+str(expected))
mapping=plan['historical_mapping_stages'];fields=['original_grid_mapping_usable','original_local_mapping_usable','original_baseline_mapping_verified','final_reference_mapping_supported']
check(len(mapping)==2 and all(r['order']in[2,3] and all(r[k]is True for k in fields) for r in mapping),'Own May-discovery order2/3 historical mapping stages all true')
prior=plan['prior_bounded_window_geometry'];shared=[r for r in prior if r['shared_source_pixels']]
check(len(shared)==1 and shared[0]['group']=='C012' and shared[0]['overlap_bary_air_angstrom']==[3866.2675,3868.6775000000002],'Same-target C012 overlap and shared source pixels explicit')
check(plan['anchor_dp_id']=='ADP.2025-05-29T01:01:14.389' and plan['anchor_dp_id']!='ADP.2025-04-30T01:01:50.866','May discovery reference replaces April reference without new observations')
for path,h in plan['source_hashes'].items():check(hashlib.sha256((REPO/path).read_bytes()).hexdigest()==h,'Frozen source exact: '+path)
r={'status':'PASS_COMPACT_SYNTHETIC_PREFLIGHT','checks':checks,'observational_arrays_read':False,'network_requests':0,'script_sha256':hashlib.sha256((HERE/'compare_group.py').read_bytes()).hexdigest(),'plan_sha256':hashlib.sha256((HERE/'PLAN.json').read_bytes()).hexdigest()}
(HERE/'SYNTHETIC_PREFLIGHT.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k!='checks'}));print('checks',len(checks))
