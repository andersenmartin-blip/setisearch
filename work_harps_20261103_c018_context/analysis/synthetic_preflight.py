#!/usr/bin/env python3
"""Compact synthetic-only checks; never open observational arrays."""
from pathlib import Path
import ast,hashlib,importlib.util,json,math
import numpy as np
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
def module(p):
    spec=importlib.util.spec_from_file_location('c018_synthetic_target',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=module(HERE/'compare_group.py');checks=[]
def check(test,label):
    if not test:raise AssertionError(label)
    checks.append(label)
def funcs(p):return{n.name:ast.dump(n,include_attributes=False)for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef)}
a=funcs(HERE/'compare_group.py');b=funcs(REPO/'work_harps_20261103_c016_context/analysis/compare_group.py')
for name in ['sampling_parameters','profile','comparison']:check(a[name]==b[name],name+' function unchanged from C016')
check(int(m.CORE.sum())==51 and int(m.BROAD.sum())==550,'51 core / 550 surrounding centers')
check(len(m.EVENTS)==7 and len(m.REFERENCES)==7,'Seven records / seven distinct fixed reference products')
expected_events={'V2E2-0114': 'ADP.2022-01-22T01:09:14.958', 'V2E2-0119': 'ADP.2022-02-06T01:07:28.382', 'V2E2-0124': 'ADP.2022-05-06T01:04:00.123', 'V2E2-0128': 'ADP.2023-01-17T01:07:48.581', 'V2E2-0133': 'ADP.2023-03-23T01:02:04.833', 'V2E2-0134': 'ADP.2023-05-16T01:01:18.574', 'V2E2-0138': 'ADP.2023-07-02T01:01:43.311'}
check(m.EVENTS==expected_events and m.COVERING_ORDERS=={dp:[2,3] for dp in expected_events.values()},'Fresh seven discovery products with both original covering orders retained')
check(m.ANCHOR_BERV==29.658729150824 and m.REFERENCES[0]=='ADP.2022-01-22T01:09:14.958','Own Jan2022 first-queue common anchor remains separate from all seven references')

w=m.CB+np.arange(-700,701)/100;f=200+15*np.sin(np.arange(len(w))*.1);e=np.full(len(w),np.nan)
for berv in [29.658729150824,-29.0643174950811,30.0089342598494]:
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
flow=np.random.default_rng(180114).normal(0,10,len(w));flanks=(np.abs(w-m.CB)>=1.5)&(np.abs(w-m.CB)<=3);flow+=1-np.median(flow[flanks])
p,q=m.profile(w,flow,e,m.ANCHOR_BERV,'barycentric',.01);check(q['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE' and q['low_flank_reference']is True,'Positive but low reference retains explicit true flag and signed negative samples')
p={'signed_raw_flux':np.ones(601)*.1,'normalized_flux':np.ones(601)};check(m.comparison(p,p,m.CORE)['raw_pearson_block_reason']=='ZERO_RAW_VARIANCE','Exact constant zero-range guard')
for mask,minimum in [(m.CORE,41),(m.BROAD,440)]:
    for count in [minimum-1,minimum]:
        f=np.full(601,np.nan);f[np.flatnonzero(mask)[:count]]=np.arange(count,dtype=float);p={'signed_raw_flux':f,'normalized_flux':f}
        r=m.comparison(p,p,mask);check((r['raw_pearson']is not None)==(count>=minimum),'Common support boundary '+str(count)+'/'+str(minimum))
plan=json.loads((HERE/'PLAN.json').read_text())
handoff=json.loads((REPO/'work_harps_20261103_c015_context/NEXT_ACTION.json').read_text())
check(m.CB==3869.33375 and plan['group_center_bary_air_angstrom']==m.CB,'Exact catalog float retained without input rounding')
check(plan['target']=='HD114783','New target is explicitly HD114783')
check(plan['merged_dp_ids']==[r['dp_id'] for r in handoff['existing_cohort_epochs']] and len(set(plan['merged_dp_ids']))==7,'Own seven HD114783 products retained exactly')
bervs=[r['berv_km_s'] for r in handoff['existing_cohort_epochs']]
check(max(bervs)-min(bervs)==59.073251754930496,'Own target BERV span retained, not previous target span')
history=plan['historical_review_disagreement']['per_event_history']
check(len(history)==7 and all(r['current_adopted_code']=='U' for r in history),'Seven current U labels retained without flattening original history')
special=next(r for r in history if r['candidate_id']=='V2E2-0128')
check(special['original_primary_code']=='I' and special['original_secondary_code']=='M' and special['original_secondary_normalized_code']=='I' and special['original_adopted_baseline_code']=='I' and special['later_mapping_followup_primary_code']==special['later_mapping_followup_secondary_code']=='U' and special['coordinates_changed']is False,'0128 original I/M-normalized-I/baseline-I and later unchanged-coordinate U/U/current U remain separate')
check(all(r['original_primary_code']==r['original_secondary_code']==r['original_adopted_code']=='U' for r in history if r['candidate_id']!='V2E2-0128'),'Six batch03 members retain original U/U/U histories')
for item in plan['native_fixed_frame_header_geometry']:
 for frame,g in item['fixed_frame_header_geometry'].items():
  lo,hi=g['offset_endpoints_from_frame_center_angstrom'];covered=(m.X>=lo)&(m.X<=hi)
  check(int(covered[m.CORE].sum())>=41,'Header-only native common core support '+item['dp_id']+' '+str(item['order'])+' '+frame)
  if item['order']==3:check(int(covered.sum())==601 and g['positive_reference_flank_geometrically_covered'],'Header-only order3 full geometry '+item['dp_id']+' '+frame)
  else:check(int(covered.sum())<601 and not g['positive_reference_flank_geometrically_covered'],'Header-only order2 partial geometry with absent positive reference flank '+item['dp_id']+' '+frame)
mapping=plan['historical_mapping_stages'];fields=['original_grid_mapping_usable','original_local_mapping_usable','original_baseline_mapping_verified','final_reference_mapping_supported']
check(len(mapping)==14 and all([r[k] for k in fields]==([True,False,False,True] if r['order']==2 else [True,True,True,True]) for r in mapping),'Original order2 and order3 stages remain distinct from later support')
check(len(plan['prior_bounded_window_geometry'])==14 and not any(r['shared_source_pixels'] for r in plan['prior_bounded_window_geometry']),'Prior numeric overlaps belong to different targets and share no pixels')
check(plan['discovery_dp_ids']==list(expected_events.values())==plan['merged_dp_ids'] and plan['anchor_dp_id']==list(expected_events.values())[0],'All seven observations remain fixed references with first-queue coordinate anchor')
check(plan['slots']['all_profiles']==42 and plan['slots']['all_comparisons']==252 and plan['slots']['identical_product_self_comparisons']==28,'Joint accounting42profiles/252comparisons/28self')
expected_centers={'V2E2-0114':3869.3349999999996,'V2E2-0119':3869.3325,'V2E2-0124':3869.3325,'V2E2-0128':3869.335,'V2E2-0133':3869.3349999999996,'V2E2-0134':3869.3325,'V2E2-0138':3869.335}
check(plan['individual_event_centers_bary_air_angstrom']==expected_centers,'Exact original float distinctions and seven member identities retained')
check(len(plan['event_markers'])==7 and [r['event'] for r in plan['event_markers']]==list(expected_events),'All seven member/discovery marker identities retained')
for mark in plan['event_markers']:
 check(abs(mark['barycentric_offset_angstrom'])<.001250000001 and mark['discovery_dp_id']==expected_events[mark['event']],'Exact member marker/common offset '+mark['event'])
for event,core in plan['individual_event_cores_bary_air_angstrom'].items():
 center=expected_centers[event]
 check(core==[center-.25,center+.25] and (core[0]<m.CB-.25 or core[1]>m.CB+.25),'Common core distinct from original member core '+event)
check(plan['plot_pagination']['native_pages']==4 and plan['plot_pagination']['raw_pages']==4 and plan['plot_pagination']['total_figures']==10,'All native/raw contexts retained across ten fixed figures')
check(plan['completed_mapping_followup_dependency']['no_replay']is True and plan['completed_mapping_followup_dependency']['original_order2_local_and_mapping_verified']is False and plan['completed_mapping_followup_dependency']['later_both_order_reference_support']is True,'Completed0128 mapping support does not repair failed original stage or require replay')
for path,h in plan['source_hashes'].items():check(hashlib.sha256((REPO/path).read_bytes()).hexdigest()==h,'Frozen source exact: '+path)
r={'status':'PASS_COMPACT_SYNTHETIC_PREFLIGHT','checks':checks,'observational_arrays_read':False,'network_requests':0,'script_sha256':hashlib.sha256((HERE/'compare_group.py').read_bytes()).hexdigest(),'plan_sha256':hashlib.sha256((HERE/'PLAN.json').read_bytes()).hexdigest()}
(HERE/'SYNTHETIC_PREFLIGHT.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k!='checks'}));print('checks',len(checks))
