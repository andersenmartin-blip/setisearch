"""Reconstruct every C035 output with scalar formulas in a fresh process.

This is a separate numerical implementation run by the same assistant, not an
independent agent or human review. It never imports production code.
"""
from pathlib import Path
import argparse,bisect,hashlib,json,math,statistics,csv
import numpy as np
from astropy.io import fits
import independent_math as ref
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];A=HERE.parent/'analysis';OUT=A/'results'
checks=0;scalars=0;differences=[]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ck(v,s):
 global checks
 if not v:raise AssertionError(s)
 checks+=1
def diff(a,b):
 global scalars
 if isinstance(b,dict):
  ck(set(a)==set(b),'dictionary keys');return max([diff(a[k],v) for k,v in b.items()]+[0.])
 if isinstance(b,(str,bool)) or b is None or isinstance(b,list) and (not b or isinstance(b[0],str)):
  ck(a==b,'exact metadata');return 0.
 aa=np.asarray(a,dtype=float);bb=np.asarray(b,dtype=float);scalars+=aa.size
 ck(aa.shape==bb.shape and np.allclose(aa,bb,rtol=3e-9,atol=3e-8,equal_nan=True),'numeric equivalence')
 finite=np.isfinite(aa)&np.isfinite(bb);return float(np.max(np.abs(aa[finite]-bb[finite]))) if finite.any() else 0.
def close(a,b,label):
 before=scalars;err=diff(a,b);differences.append(dict(name=label,scalar_values=scalars-before,maximum_absolute_difference=err))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--authorized-after-root-run',action='store_true');args=ap.parse_args()
 if not args.authorized_after_root_run:raise SystemExit('Only after completed production execution')
 plan=read(A/'PLAN.json');inv=read(ROOT/plan['inventory_path']);release=read(A/'ROOT_RELEASE.json');pre=read(HERE/'PROSPECTIVE_AUDIT.json')
 ck(pre['status']=='PASS_COMPACT_PROSPECTIVE_C035_AUDIT' and pre['observational_arrays_read']==0,'prospective pass')
 for key,p in [('plan_sha256',A/'PLAN.json'),('analysis_script_sha256',A/'compare_group.py'),('independent_math_sha256',HERE/'independent_math.py'),('audit_script_sha256',HERE/'audit_prospective.py'),('actual_audit_script_sha256',Path(__file__))]:ck(pre[key]==sha(p),'frozen '+key)
 for p,h in plan['source_hashes'].items():ck(sha(ROOT/p)==h,'source '+p)
 output_hashes=read(OUT/'OUTPUT_HASHES.json')
 for p,h in output_hashes.items():ck(sha(OUT/p)==h,'output '+p)
 ck(release['plan_sha256']==sha(A/'PLAN.json') and release['script_sha256']==sha(A/'compare_group.py'),'release bindings')
 records=read(OUT/'PROFILE_METRICS.json');pairs=read(OUT/'COMPARISONS.json');bounded=read(OUT/'BOUNDED_INPUT_INDEX.json');summary=read(OUT/'SUMMARY.json')
 ck(len(records)==14 and len(pairs)==28 and len(bounded)==7,'exact14/28/7 accounting')
 ck(plan['events']=={'V2E2-0289':'ADP.2025-03-31T01:04:04.493'} and ref.CB==5758.2675 and ref.ANCHOR_BERV==18.1525360721304,'exact singleton and own positive March anchor')
 bound_index={(r['kind'],r['dp_id'],r['order']):r for r in bounded};record_index={(r['kind'],r['dp_id'],r['order'],r['frame']):r for r in records};expected_profiles={};reconstructed=[]
 for kind,item in [('merged',n) for n in inv['merged_spectra']]+[('native',n) for n in inv['native_products']]:
  berv=item.get('berv_km_s',item['primary_header'].get('ESO DRS BERV'));src=ROOT/item['file']['path'];ck(sha(src)==item['file']['sha256'],'own source byte identity')
  for order in [None] if kind=='merged' else item['covering_orders']:
   bound=bound_index[kind,item['dp_id'],order]
   with fits.open(src,memmap=True) as hd:
    if kind=='merged':wave=np.array(hd[1].data['WAVE'][0],float)
    else:
     coeff=item['orders'][str(order)]['wavelength_coefficients_ascending'];wave=np.array([math.fsum(c*i**k for k,c in enumerate(coeff))*(1+berv/ref.C) for i in range(4096)])
    ck(np.isfinite(wave).all() and (np.diff(wave)>0).all(),'source wave monotonic')
    wl=wave.tolist();spacing=statistics.median([b-a for a,b in zip(wl,wl[1:])]);requests=[ref.CB+x for x in ref.X]+[(ref.CT+x)*(1+berv/ref.C) for x in ref.X]
    first=max(0,bisect.bisect_left(wl,min(requests))-1);stop=min(len(wl),bisect.bisect_right(wl,max(requests))+1)
    if kind=='merged':flux=np.array(hd[1].data['FLUX'][0][first:stop],float);error=np.array(hd[1].data['ERR'][0][first:stop],float)
    else:flux=np.array(hd[0].section[order:order+1,first:stop][0],float);error=np.full(stop-first,np.nan)
   ck(bound['original_index_start']==first and bound['original_index_stop']==stop,'independent source indices')
   close(bound['full_source_median_spacing_bary_angstrom'],spacing,'spacing '+bound['source_id'])
   w=wave[first:stop];original=w/(1+berv/ref.C) if kind=='native' else w
   expected=dict(source_indices=np.arange(first,stop),source_wavelength=original,barycentric_wavelength=w,signed_source_flux=flux,source_error=error)
   with np.load(OUT/bound['file'],allow_pickle=False) as z:
    ck(set(z.files)==set(expected),'source arrays keys')
    for key,v in expected.items():close(z[key],v,'input '+bound['source_id']+'/'+key)
   for frame in ['barycentric','topocentric']:
    ident=kind,item['dp_id'],order,frame;r=record_index[ident];arrays,metrics=ref.profile(w,flux,error,berv,frame,spacing)
    ck(r['status']=='MEASURED_CONTEXT' and r['source_input_sha256']==item['file']['sha256'],'measured own source')
    close({k:r[k] for k in metrics},metrics,'metrics '+r['source_id']+'/'+frame)
    with np.load(OUT/r['profile_path'],allow_pickle=False) as z:
     ck(set(z.files)==set(arrays),'profile array keys')
     for key,v in arrays.items():close(z[key],v,'profile '+r['source_id']+'/'+frame+'/'+key)
    expected_profiles[ident]=arrays;reconstructed.append(dict(kind=kind,dp_id=item['dp_id'],order=order,frame=frame,source_id=r['source_id'],**metrics))
 expected_pairs=[]
 for r in reconstructed:
  for dp in plan['discovery_dp_ids'] if r['kind']=='merged' else [r['dp_id']]:
   left=expected_profiles[r['kind'],r['dp_id'],r['order'],r['frame']];right=expected_profiles['merged',dp,None,r['frame']]
   for region,mask in [('core',ref.CORE),('broad_pattern',ref.BROAD)]:expected_pairs.append(dict(relationship='MERGED_EPOCH_TO_DISCOVERY' if r['kind']=='merged' else 'SAME_EPOCH_NATIVE_TO_MERGED',source_id=r['source_id'],dp_id=r['dp_id'],order=r['order'],reference_dp_id=dp,frame=r['frame'],region=region,same_exposure=r['dp_id']==dp,identical_product_self_pair=r['kind']=='merged' and r['dp_id']==dp,**ref.comparison(left,right,mask)))
 ck(len(expected_pairs)==28 and sum(r['identical_product_self_pair'] for r in expected_pairs)==4,'all pairs and labeled self rows')
 for i,(actual,expected) in enumerate(zip(pairs,expected_pairs)):close(actual,expected,'comparison '+str(i))
 support=[]
 for ident,arrays in expected_profiles.items():
  for marker in plan['event_markers']:
   center=marker['barycentric_offset_angstrom'] if ident[3]=='barycentric' else marker['discovery_topocentric_offset_angstrom'];half=marker['member_core_half_width_bary_angstrom'] if ident[3]=='barycentric' else marker['member_core_half_width_topo_angstrom'];mask=np.array([center-half<=x<=center+half for x in ref.X]);raw=np.array(arrays['signed_raw_flux']);norm=np.array(arrays['normalized_flux'])
   support.append(dict(kind=ident[0],dp_id=ident[1],order=ident[2],frame=ident[3],event=marker['event'],original_core_offset_bounds=[center-half,center+half],nominal_grid_centers=int(mask.sum()),finite_raw_grid_centers=int((mask&np.isfinite(raw)).sum()),finite_normalized_grid_centers=int((mask&np.isfinite(norm)).sum()),grid_centers_outside_common_comparison_core=int((mask&~np.array(ref.CORE)).sum())))
 preserved=read(OUT/'PRESERVED_RAW_CONTEXT.json');ck(len(preserved)==1 and preserved[0]['event']=='V2E2-0289' and preserved[0]['order']==54,'own original raw panel')
 for r in preserved:ck(sha(OUT/r['copied_path'])==r['file']['sha256']==sha(ROOT/r['file']['path']),'raw panel byte identity')
 ck(len(support)==14,'all14 profiles retain own original core support')
 keys=['original_grid_mapping_usable','original_local_mapping_usable','original_baseline_mapping_verified','final_reference_mapping_supported']
 ck(len(inv['mapping_records'])==1 and [inv['mapping_records'][0][k] for k in keys]==[True,True,True,True],'own supported mapping stages')
 ck(inv['historical_raw_review_records']['secondary'][0]['additional_uncertainty'] is True and not inv['historical_raw_review_records']['secondary'][0]['contamination_or_blend_caution'],'own secondary ambiguity without transferred caution')
 prior_path=ROOT/'work_harps_20261105_c032_context/analysis/results/BOUNDED_INPUT_INDEX.json';prior={(r['kind'],r['dp_id'],r['order']):r for r in read(prior_path)};shared=[];additional=[]
 for r in bounded:
  key=r['kind'],r['dp_id'],r['order']
  if key not in prior:additional.append({k:r[k] for k in ['kind','dp_id','order']});continue
  p=prior[key];ck(r['source_file_sha256']==p['source_file_sha256'],'same physical source');overlap=max(0,min(r['original_index_stop'],p['original_index_stop'])-max(r['original_index_start'],p['original_index_start']));shared.append(dict(kind=r['kind'],dp_id=r['dp_id'],order=r['order'],shared_original_source_indices=overlap))
 ck(len(shared)==0 and len(additional)==7,'HD128582 sources differ from recent HD126093 context')
 dep=dict(status='PASS_C035_RECENT_SOURCE_IDENTITY_AUDIT',prior_phase='C032',prior_index_path=str(prior_path.relative_to(ROOT)),prior_index_sha256=sha(prior_path),shared_sources=shared,additional_existing_target_sources=additional,prior_array_values_read=0,source_pixel_independence_claim=False,qualification='Different target/source IDs relative to C032 do not make previously exposed HD128582 epochs blind or new observations.')
 ck(summary['raw_only_normalization_slots']==sum(r['normalization_status']=='RAW_ONLY' for r in reconstructed) and summary['blocked_source_profile_slots']==0,'all reference outcomes retained')
 ck(summary['labels_changed']==summary['origin_assignments']==0 and summary['old_epoch_pipeline_rerun'] is False,'unchanged physical label and earlier pipelines')
 for p,h in plan['source_hashes'].items():ck(sha(ROOT/p)==h,'unchanged frozen source')
 for p,h in output_hashes.items():ck(sha(OUT/p)==h,'unchanged numeric output')
 for name,v in [('MEMBER_CORE_SUPPORT.json',dict(status='FIXED_SUPPORT_ONLY_NO_NEW_COMPARISONS',records=support)),('SOURCE_PIXEL_DEPENDENCY_AUDIT.json',dep)]:
  with (HERE/name).open('x') as f:json.dump(v,f,indent=2);f.write('\n')
 report=dict(status='PASS_SEPARATE_C035_NUMERICAL_RECONSTRUCTION',checks_passed=checks,scalar_values_compared=scalars,profiles_reconstructed=14,comparisons_reconstructed=28,bounded_input_records_reconstructed=7,preserved_raw_context_files_verified=1,maximum_absolute_difference=max(d['maximum_absolute_difference'] for d in differences),production_functions_imported=False,network_requests=0,source_pixel_dependencies=dep,reviewer_scope='Same assistant, separate scalar implementation and fresh process; no independent agent or human review.',plan_sha256=sha(A/'PLAN.json'),script_sha256=sha(Path(__file__)))
 with (HERE/'NUMERICAL_AUDIT.json').open('x') as f:json.dump(report,f,indent=2);f.write('\n')
 with (HERE/'NUMERICAL_DIFFERENCES.csv').open('x',newline='') as f:w=csv.DictWriter(f,fieldnames=['name','scalar_values','maximum_absolute_difference']);w.writeheader();w.writerows(differences)
 print(json.dumps({k:v for k,v in report.items() if k!='source_pixel_dependencies'},indent=2))
if __name__=='__main__':main()
