#!/usr/bin/env python3
"""Compact synthetic-only checks; never open observational arrays."""
from pathlib import Path
import ast,hashlib,importlib.util,json,math
import numpy as np
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
def module(p):
    spec=importlib.util.spec_from_file_location('c022_synthetic_target',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=module(HERE/'compare_group.py');checks=[]
def check(test,label):
    if not test:raise AssertionError(label)
    checks.append(label)
def funcs(p):return{n.name:ast.dump(n,include_attributes=False)for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef)}
a=funcs(HERE/'compare_group.py');b=funcs(REPO/'work_harps_20261103_c021_context/analysis/compare_group.py')
for name in [k for k in a if k not in ['validate','main']]:check(a[name]==b[name],name+' function unchanged from C021')
check(int(m.CORE.sum())==51 and int(m.BROAD.sum())==550,'51 core / 550 surrounding centers')
check(len(m.EVENTS)==3 and len(m.REFERENCES)==3,'Three records / three distinct fixed reference products')
expected_events={'V2E2-0117':'ADP.2022-01-22T01:09:14.958','V2E2-0127':'ADP.2022-05-06T01:04:00.123','V2E2-0131':'ADP.2023-01-17T01:07:48.581'}
check(m.EVENTS==expected_events and m.COVERING_ORDERS=={dp:[19] for dp in expected_events.values()},'Fresh three discovery/order19 contexts retained with January/May/January references')
check(m.ANCHOR_BERV==29.658729150824 and m.REFERENCES[0]=='ADP.2022-01-22T01:09:14.958','Own first-queue January common anchor retained separately from three references')

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
flow=np.random.default_rng(210116).normal(0,10,len(w));flanks=(np.abs(w-m.CB)>=1.5)&(np.abs(w-m.CB)<=3);flow+=1-np.median(flow[flanks])
p,q=m.profile(w,flow,e,m.ANCHOR_BERV,'barycentric',.01);check(q['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE' and q['low_flank_reference']is True,'Positive but low reference retains explicit true flag and signed negative samples')
p={'signed_raw_flux':np.ones(601)*.1,'normalized_flux':np.ones(601)};check(m.comparison(p,p,m.CORE)['raw_pearson_block_reason']=='ZERO_RAW_VARIANCE','Exact constant zero-range guard')
for mask,minimum in [(m.CORE,41),(m.BROAD,440)]:
    for count in [minimum-1,minimum]:
        f=np.full(601,np.nan);f[np.flatnonzero(mask)[:count]]=np.arange(count,dtype=float);p={'signed_raw_flux':f,'normalized_flux':f}
        r=m.comparison(p,p,mask);check((r['raw_pearson']is not None)==(count>=minimum),'Common support boundary '+str(count)+'/'+str(minimum))
plan=json.loads((HERE/'PLAN.json').read_text())
handoff=json.loads((REPO/'work_harps_20261103_c021_context/NEXT_ACTION.json').read_text())
check(m.CB==4312.241249999999 and plan['group_center_bary_air_angstrom']==m.CB,'Exact catalog midpoint float retained without input rounding')
check(m.CT==4311.814678415948,'Own wavelength-specific January anchor exact')
check(plan['target']=='HD114783','Target explicitly HD114783')
check(plan['merged_dp_ids']==[r['dp_id'] for r in handoff['existing_cohort_epochs']] and len(set(plan['merged_dp_ids']))==7,'Same seven target products retained exactly')
bervs=[r['berv_km_s'] for r in handoff['existing_cohort_epochs']]
check(max(bervs)-min(bervs)==59.073251754930496,'Own target BERV span retained')
history=plan['historical_review_disagreement']['per_event_history'];special=next(r for r in history if r['candidate_id']=='V2E2-0131')
check(len(history)==3 and all(r['current_adopted_code']=='U' for r in history),'All three current C022 labels U')
check(all(r['original_primary_code']==r['original_secondary_code']==r['original_adopted_code']=='U' for r in history if r['candidate_id']!='V2E2-0131'),'Two batch03 original U/U/U chains retained')
check(special['original_primary_code']=='I' and special['original_secondary_code']=='M' and special['original_secondary_normalized_code']==special['original_adopted_baseline_code']=='I' and special['later_mapping_followup_primary_code']==special['later_mapping_followup_secondary_code']=='U' and special['coordinates_changed']is False,'0131 original I/M-normalized-I/baseline-I and later unchanged-coordinate U/U/currentU remain separate')
for item in plan['native_fixed_frame_header_geometry']:
 for frame,g in item['fixed_frame_header_geometry'].items():
  lo,hi=g['offset_endpoints_from_frame_center_angstrom'];covered=(m.X>=lo)&(m.X<=hi)
  check(item['order']==19 and int(covered.sum())==601 and g['negative_reference_flank_geometrically_covered'] and g['positive_reference_flank_geometrically_covered'],'Fresh order19 full header geometry '+item['dp_id']+' '+frame)
mapping=plan['historical_mapping_stages'];fields=['original_grid_mapping_usable','original_local_mapping_usable','original_baseline_mapping_verified','final_reference_mapping_supported']
check(len(mapping)==3 and all([r[k] for k in fields]==[True,False,False,True] for r in mapping),'All three failed original local/baseline stages retained separately from true global/later support')
check(all(r['baseline_field_basis']==('mapping_verified in original raw_followup mapping' if r['event']=='V2E2-0131' else 'explicit baseline_mapping_verified in batch03 mapping') for r in mapping),'Source-specific original baseline field provenance retained')
check(plan['discovery_dp_ids']==list(expected_events.values()),'Exact three January21/May5/January16 reference identities retained')
check(plan['slots']['all_profiles']==20 and plan['slots']['all_comparisons']==96 and plan['slots']['identical_product_self_comparisons']==12 and plan['slots']['expected_bounded_input_windows']==10,'Joint accounting20profiles/96comparisons/12self/10sourcewindows')
check(plan['slots']['merged_comparisons']==84 and plan['slots']['native_comparisons']==12,'All-reference merged comparisons and own-exposure native comparisons remain separate')
check(plan['joint_reference_dependence']['nonself_directed_rows_per_frame_region']==18 and plan['joint_reference_dependence']['distinct_unordered_nonself_observation_pairs_per_frame_region']==15 and plan['joint_reference_dependence']['reciprocal_directed_duplicates_per_frame_region']==3,'18 directed nonself/15 unordered/3 reciprocal dependence over seven observations')
expected_centers={'V2E2-0117':4312.245,'V2E2-0127':4312.245,'V2E2-0131':4312.237499999999}
check(plan['individual_event_centers_bary_air_angstrom']==expected_centers,'Exact original member floats retained')
check(len(plan['event_markers'])==3 and [r['event'] for r in plan['event_markers']]==list(expected_events),'All three exact member/discovery marker identities retained')
for mark in plan['event_markers']:
 check(abs(mark['barycentric_offset_angstrom'])<.00375000001 and mark['discovery_dp_id']==expected_events[mark['event']],'Exact member marker offset/discovery '+mark['event'])
for event,core in plan['individual_event_cores_bary_air_angstrom'].items():
 center=expected_centers[event]
 check(core==[center-.25,center+.25] and (core[0]<m.CB-.25 or core[1]>m.CB+.25),'Common core distinct from original member core '+event)
check(plan['plot_pagination']['native_pages']==plan['plot_pagination']['raw_pages']==1 and plan['plot_pagination']['total_figures']==4,'All sources retained in four complete figures with three native/raw rows')
check(plan['plot_pagination']['native_contexts']==plan['plot_pagination']['raw_contexts']==3,'All three native and raw context rows retained')
check(plan['completed_mapping_followup_dependency']['candidate_id']=='V2E2-0131' and plan['completed_mapping_followup_dependency']['no_replay']is True,'Completed0131 wider mapping preserved without replay or distinct-history transfer')
prior=plan['prior_bounded_window_geometry'];shared=[r for r in prior if r['shared_source_pixels']]
check(len(prior)==17 and [r['group'] for r in shared]==['C021'],'Only priorC021 has same-target bounded spectral overlap')
dep=plan['prior_C021_shared_structured_flank_dependency']
oldlo,oldhi=dep['current_C021_window_bary_air_angstrom'];newlo,newhi=m.CB-3,m.CB+3
overlap=[max(oldlo,newlo),min(oldhi,newhi)]
check(overlap==dep['numeric_and_same_source_overlap_bary_air_angstrom'] and overlap[1]-overlap[0]==3.585000000000946,'Direct C021 shared-source overlap exact3.585000000000946Angstrom')
newcore=[m.CB-.25,m.CB+.25];oldcore=dep['current_C021_core_bary_air_angstrom'];oldflank=dep['current_C021_positive_reference_flank_bary_air_angstrom'];newflank=[m.CB-3,m.CB-1.5]
check(oldflank[0]<=newcore[0]<newcore[1]<=oldflank[1] and newflank[0]<=oldcore[0]<oldcore[1]<=newflank[1],'Each complete core lies in the opposite group fixed reference flank without masks')
check(newcore[0]>oldcore[1] and dep['same_observing_products_as_C021'] and dep['shared_bounded_spectral_source_pixels_with_C021'],'Distinct cores retain directly reused pixels and structured-flank dependence')
oldinv=json.loads((REPO/'work_harps_20261103_c021_context/inputs/INPUT_INVENTORY.json').read_text())
inv=json.loads((REPO/plan['inventory_path']).read_text())
for kind in ['merged_spectra','native_products']:
 oldhash={r['dp_id']:r['file']['sha256'] for r in oldinv[kind]}
 check(all(oldhash[r['dp_id']]==r['file']['sha256'] for r in inv[kind]),'Identical reused C021 '+kind+' source identities and full-file hashes')
for path in ['work_harps_20261103_c021_context/inputs/INPUT_INVENTORY.json','work_harps_20261103_c021_context/analysis/results/BOUNDED_INPUT_INDEX.json']:
 check(path in plan['source_hashes'],'Prior C021 source-index custody bound: '+path)
check(not(HERE/'results').exists(),'No observed result directory before root release')
for path,h in plan['source_hashes'].items():check(hashlib.sha256((REPO/path).read_bytes()).hexdigest()==h,'Frozen source exact: '+path)
r={'status':'PASS_COMPACT_SYNTHETIC_PREFLIGHT','checks':checks,'observational_arrays_read':False,'network_requests':0,'script_sha256':hashlib.sha256((HERE/'compare_group.py').read_bytes()).hexdigest(),'plan_sha256':hashlib.sha256((HERE/'PLAN.json').read_bytes()).hexdigest()}
(HERE/'SYNTHETIC_PREFLIGHT.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items()if k!='checks'}));print('checks',len(checks))
