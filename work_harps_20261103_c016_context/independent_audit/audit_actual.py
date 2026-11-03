"""Independent C016 reconstruction after the parent confirms completed execution."""
import argparse,bisect,csv,datetime,hashlib,json,math,statistics
from pathlib import Path
import numpy as np
from astropy.io import fits
import independent_math as ref
OUT=Path(__file__).resolve().parent;A=OUT.parent/'analysis';RESULT=A/'results';ROOT=OUT.parents[1]
checks=0;scalars=0;differences=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def ck(v,label):
 global checks
 if not v:raise AssertionError(label)
 checks+=1
def difference(a,b):
 global scalars
 if isinstance(b,dict):
  if set(a)!=set(b):raise AssertionError('Different dictionary keys')
  return max([difference(a[k],v)for k,v in b.items()]+[0.])
 if isinstance(b,(str,bool))or b is None:
  if a!=b:raise AssertionError((a,b))
  return 0.
 if isinstance(b,list)and b and isinstance(b[0],(str,dict)):
  if len(a)!=len(b):raise AssertionError('Different list lengths')
  return max([difference(x,y)for x,y in zip(a,b)]+[0.])
 aa=np.asarray(a,dtype=float);bb=np.asarray(b,dtype=float);scalars+=aa.size
 if aa.shape!=bb.shape or not np.allclose(aa,bb,rtol=3e-9,atol=3e-8,equal_nan=True):raise AssertionError('Numerical mismatch')
 finite=np.isfinite(aa)&np.isfinite(bb)
 return float(np.max(np.abs(aa[finite]-bb[finite])))if finite.any()else 0.
def close(a,b,label,kind):
 before=scalars
 try:error=difference(a,b)
 except AssertionError as exc:raise AssertionError(label+': '+str(exc))from exc
 ck(True,label);differences.append(dict(name=label,kind=kind,scalar_values=scalars-before,maximum_absolute_difference=error))
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--authorized-after-root-run',action='store_true');args=parser.parse_args()
 if not args.authorized_after_root_run:raise SystemExit('Root completed-run signal and explicit flag required before observational arrays.')
 plan=read(A/'PLAN.json');release=read(A/'ROOT_RELEASE.json');summary=read(RESULT/'SUMMARY.json');hashes=read(RESULT/'OUTPUT_HASHES.json');inv=read(ROOT/plan['inventory_path'])
 prospective=read(OUT/'PROSPECTIVE_AUDIT.json')
 ck(prospective['status']=='PASS_COMPACT_PROSPECTIVE_C016_AUDIT'and prospective['observational_arrays_read']==0,'Passed prospective audit before observed reconstruction')
 ck(prospective['plan_sha256']==sha(A/'PLAN.json')and prospective['analysis_script_sha256']==sha(A/'compare_group.py')and prospective['independent_math_sha256']==sha(OUT/'independent_math.py')and prospective['audit_script_sha256']==sha(OUT/'audit_prospective.py')and prospective['actual_audit_script_sha256']==sha(Path(__file__)),'Exact prospective code remains frozen')
 ck(summary['status']=='COMPLETE_FIXED_GROUP_CONTEXT','Complete production profile slots')
 ck(release['schema']=='HARPS_C016_GROUP_RELEASE_V1'and release['publication_readback_verified']is True,'Exact released phase')
 ck(release['plan_sha256']==sha(A/'PLAN.json')and release['script_sha256']==sha(A/'compare_group.py')and summary['release_sha256']==sha(A/'ROOT_RELEASE.json'),'Release/code/plan/result bindings')
 ck(release['inventory_path']==plan['inventory_path']and release['inventory_sha256']==sha(ROOT/plan['inventory_path']),'Exact input inventory binding')
 for p,h in plan['source_hashes'].items():ck(sha(ROOT/p)==h,'Source '+p)
 for p,h in hashes.items():ck(sha(RESULT/p)==h,'Production output '+p)
 initial={str(p.relative_to(ROOT)):sha(p)for p in [A/'PLAN.json',A/'ROOT_RELEASE.json',RESULT/'OUTPUT_HASHES.json',OUT/'independent_math.py',OUT/'audit_prospective.py',OUT/'audit_actual.py',OUT/'PROSPECTIVE_AUDIT.json']}
 records=read(RESULT/'PROFILE_METRICS.json');pairs=read(RESULT/'COMPARISONS.json');bounded=read(RESULT/'BOUNDED_INPUT_INDEX.json')
 ck(plan['group_center_bary_air_angstrom']==ref.CB and plan['anchor_dp_id']=='ADP.2022-03-08T01:01:37.348' and plan['anchor_berv_km_s']==ref.ANCHOR_BERV==19.1606928163471,'Independent fixed center and first-queue March 2022 discovery anchor')
 ck(len(records)==22 and len(pairs)==128 and len(bounded)==11,'Exact 22 / 128 / 11 accounting')
 index={(r['kind'],r['dp_id'],r['order']):r for r in bounded};record_index={(r['kind'],r['dp_id'],r['order'],r['frame']):r for r in records}
 ck(len(index)==11 and len(record_index)==22,'No duplicate source/frame slots')
 expected_events={'V2E2-0094':'ADP.2022-03-08T01:01:37.348','V2E2-0096':'ADP.2022-05-17T01:02:16.724','V2E2-0098':'ADP.2023-01-03T01:08:17.803','V2E2-0110':'ADP.2023-08-29T01:02:07.487'}
 ck(plan['events']==expected_events,'Four complete event identities and distinct discovery products')
 handoff=read(ROOT/'work_harps_20261103_c011_context/NEXT_ACTION.json');epochs=handoff['existing_cohort_epochs']
 centers={r['candidate_id']:float(r['center_bary_air_angstrom'])for r in handoff['existing_context']}
 ck([centers[e]for e in expected_events]==[4303.785,4303.785,4303.785,4303.79]and ref.CB==(min(centers.values())+max(centers.values()))/2,'Four original member centers and fixed group midpoint retained')
 ck(inv['target']=='HD114386' and [r['dp_id']for r in inv['merged_spectra']]==[r['dp_id']for r in epochs],'Exact separate HD114386 cohort remains selected')
 ck(math.isclose(max(r['berv_km_s']for r in epochs)-min(r['berv_km_s']for r in epochs),51.572001697156,rel_tol=0,abs_tol=1e-13),'Correct target BERV span')
 ck(len({r['dp_id']for r in inv['native_products']})==4 and len(inv['native_products'])==4,'Native sources deduplicated by product')
 included=[(r['dp_id'],o)for r in inv['native_products']for o in r['covering_orders']]
 excluded=[]
 ck(included==[(dp,19)for dp in expected_events.values()]and [(r['dp_id'],r['order'])for r in plan['included_native_order_pairs']]==included and [(r['dp_id'],r['order'])for r in plan['excluded_native_order_pairs']]==excluded,'Exact prospective included and excluded native pairs')
 ck({(r['dp_id'],r['order'])for r in records if r['kind']=='native'}==set(included)and not(set(included)&set(excluded)),'No excluded order read or substituted')
 scope=read(RESULT/'NATIVE_ORDER_SCOPE.json')
 ck(scope['included_pairs']==plan['included_native_order_pairs']and scope['excluded_pairs']==plan['excluded_native_order_pairs']and scope['excluded_orders_measured']is False,'Metadata exclusions retained explicitly')
 mapping={(r['event'],r['dp_id'],r['order']):r for r in inv['mapping_records']};keys=['original_grid_mapping_usable','original_local_mapping_usable','original_baseline_mapping_verified','final_reference_mapping_supported']
 ck(len(mapping)==4 and set(mapping)=={(event,dp,19)for event,dp in expected_events.items()}and all(all(r[k]is True for k in keys)and r['registration_changed']is False for r in mapping.values()),'All four original order 19 mapping stages retained without changed registration')
 history=inv['historical_raw_review_records']
 ck(all(len(history[stage])==4 for stage in ['primary','secondary','adopted','comparison']),'Four complete historical review chains')
 for stage in ['primary','secondary','adopted']:
  ck({r['candidate_id']for r in history[stage]}==set(expected_events)and all(r['code']=='U'for r in history[stage]),'All historical '+stage+' U reviews retained exactly')
 ck({r['review_id']for r in history['comparison']}==set(expected_events)and all(r['primary']==r['secondary']==r['adopted']=='U'for r in history['comparison'])and all(r['evidence']and r['root_adoption_note']for r in history['adopted']),'Four unresolved broad-feature histories and original adoptions retained without new classification')
 expected_profiles={};reconstructed=[];input_counts=[]
 items=[('merged',x)for x in inv['merged_spectra']]+[('native',x)for x in inv['native_products']]
 for kind,item in items:
  berv=item.get('berv_km_s',item['primary_header'].get('ESO DRS BERV'))
  src=ROOT/item['file']['path'];ck(sha(src)==item['file']['sha256'],'Exact input '+item['dp_id']+'/'+kind)
  for order in ([None]if kind=='merged'else item['covering_orders']):
   key=(kind,item['dp_id'],order);bound=index[key]
   with fits.open(src,memmap=True)as hd:
    if kind=='merged':wave=np.array(hd[1].data['WAVE'][0],dtype=float)
    else:
     coeff=item['orders'][str(order)]['wavelength_coefficients_ascending']
     native=[math.fsum(c*i**k for k,c in enumerate(coeff))for i in range(4096)]
     wave=np.array([w*(1+berv/ref.C)for w in native])
    ck(np.isfinite(wave).all()and(np.diff(wave)>0).all(),'Independent source wavelength integrity')
    wave_list=wave.tolist();spacing=statistics.median([b-a for a,b in zip(wave_list,wave_list[1:])])
    requests=[ref.CB+x for x in ref.X]+[(ref.CT+x)*(1+berv/ref.C)for x in ref.X]
    first=max(0,bisect.bisect_left(wave_list,min(requests))-1);stop=min(len(wave),bisect.bisect_right(wave_list,max(requests))+1)
    if kind=='merged':flux=np.array(hd[1].data['FLUX'][0][first:stop],dtype=float);error=np.array(hd[1].data['ERR'][0][first:stop],dtype=float)
    else:flux=np.array(hd[0].section[order:order+1,first:stop][0],dtype=float);error=np.full(stop-first,np.nan)
   ck(bound['original_index_start']==first and bound['original_index_stop']==stop and bound['native_samples']==stop-first,'Exact independent bounded indices')
   close(bound['full_source_median_spacing_bary_angstrom'],spacing,'Full native spacing '+bound['source_id'],'input_metadata')
   w=wave[first:stop];original_wave=w/(1+berv/ref.C)if kind=='native'else w
   expected_input=dict(source_indices=np.arange(first,stop),source_wavelength=original_wave,barycentric_wavelength=w,signed_source_flux=flux,source_error=error)
   with np.load(RESULT/bound['file'],allow_pickle=False)as stored:
    ck(set(stored.files)==set(expected_input),'Exact bounded input array keys')
    for name,values in expected_input.items():close(stored[name],values,'Bounded '+bound['source_id']+'/'+name,'input_'+name)
   input_counts.append(dict(kind=kind,dp_id=item['dp_id'],order=order,samples=stop-first))
   for frame in ['barycentric','topocentric']:
    ident=key+(frame,);row=record_index[ident];arrays,metrics=ref.profile(w,flux,error,berv,frame,spacing)
    ck(row['status']=='MEASURED_CONTEXT'and row['source_input_sha256']==item['file']['sha256'],'Measured immutable source identity')
    ck(row['flux_unit']==('ADU'if kind=='merged'else'NATIVE_EXTRACTED_UNIT_UNSPECIFIED'),'Preserved source unit distinction')
    close({k:row[k]for k in metrics},metrics,'Metrics '+row['source_id']+'/'+frame,'profile_metric')
    with np.load(RESULT/row['profile_path'],allow_pickle=False)as stored:
     ck(set(stored.files)==set(arrays),'Exact four profile arrays')
     for name,values in arrays.items():close(stored[name],values,'Profile '+row['source_id']+'/'+frame+'/'+name,'profile_'+name)
    expected_profiles[ident]=arrays;reconstructed.append(dict(kind=kind,dp_id=item['dp_id'],order=order,frame=frame,source_id=row['source_id'],**metrics))
 expected_pairs=[];references=list(expected_events.values())
 for row in reconstructed:
  reference_ids=references if row['kind']=='merged'else[row['dp_id']]
  for reference in reference_ids:
   left=expected_profiles[(row['kind'],row['dp_id'],row['order'],row['frame'])];right=expected_profiles[('merged',reference,None,row['frame'])]
   for region,mask in [('core',ref.CORE),('broad_pattern',ref.BROAD)]:
    expected_pairs.append(dict(relationship='MERGED_EPOCH_TO_DISCOVERY'if row['kind']=='merged'else'SAME_EPOCH_NATIVE_TO_MERGED',source_id=row['source_id'],dp_id=row['dp_id'],order=row['order'],reference_dp_id=reference,frame=row['frame'],region=region,same_exposure=row['dp_id']==reference,identical_product_self_pair=row['kind']=='merged'and row['dp_id']==reference,**ref.comparison(left,right,mask)))
 ck(len(expected_pairs)==128,'All 128 independently reconstructed arithmetic relationships')
 ck(sum(r['identical_product_self_pair']for r in expected_pairs)==16,'Exactly sixteen self comparisons retained and labeled')
 for frame in ['barycentric','topocentric']:
  for region in ['core','broad_pattern']:
   rows=[r for r in expected_pairs if r['relationship']=='MERGED_EPOCH_TO_DISCOVERY'and r['frame']==frame and r['region']==region];nonself=[r for r in rows if not r['identical_product_self_pair']]
   ck(len(rows)==28 and len(nonself)==24 and len({r['dp_id']for r in rows})==7 and {r['reference_dp_id']for r in rows}==set(references),'Seven observing epochs generate 24 dependent nonself rows per frame/region')
   for reference in references:ck(sum(r['reference_dp_id']==reference for r in nonself)==6,'Each reference retains exactly six other epochs')
   directed={(r['dp_id'],r['reference_dp_id'])for r in nonself if r['dp_id']in references}
   ck(len(directed)==12 and all((right,left)in directed for left,right in directed),'Six reciprocal discovery pairs remain identified by directed source/reference identities')
 for i,(actual,expected)in enumerate(zip(pairs,expected_pairs)):close(actual,expected,'Comparison '+str(i),'comparison')
 raw_only=[dict(kind=r['kind'],dp_id=r['dp_id'],order=r['order'],frame=r['frame'],reasons=r['normalization_reasons'])for r in reconstructed if r['normalization_status']=='RAW_ONLY']
 ck(summary['raw_only_normalization_slots']==len(raw_only)and summary['blocked_source_profile_slots']==0,'Exact raw-only versus blocked accounting')
 preserved=read(RESULT/'PRESERVED_RAW_CONTEXT.json');ck(len(preserved)==4 and {(r['event'],r['order'])for r in preserved}=={(event,19)for event in expected_events},'All four original historical raw-order panels retained')
 ck({r['event']for r in preserved}==set(plan['events']) and summary['events']==list(plan['events']),'No historical record identity dropped during product deduplication')
 for row in preserved:ck(sha(RESULT/row['copied_path'])==row['file']['sha256']==sha(ROOT/row['file']['path']),'Historical raw context byte identity')
 ck(summary['labels_changed']==summary['origin_assignments']==0 and summary['old_epoch_pipeline_rerun']is False,'Unchanged classifications and old pipeline')
 for p,h in plan['source_hashes'].items():ck(sha(ROOT/p)==h,'Source unchanged '+p)
 for p,h in hashes.items():ck(sha(RESULT/p)==h,'Output unchanged '+p)
 for p,h in initial.items():ck(sha(ROOT/p)==h,'Audit binding unchanged '+p)
 maxima={kind:max(r['maximum_absolute_difference']for r in differences if r['kind']==kind)for kind in sorted({r['kind']for r in differences})}
 report=dict(status='PASS_INDEPENDENT_C016_NUMERICAL_RECONSTRUCTION',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),checks_passed=checks,scalar_values_compared=scalars,profiles_reconstructed=22,comparisons_reconstructed=128,bounded_input_records_reconstructed=11,preserved_raw_context_files_verified=4,identical_product_self_comparisons=16,metadata_excluded_native_orders=0,distinct_observing_epochs=7,merged_nonself_comparison_rows=96,merged_nonself_rows_per_frame_region=24,reciprocal_discovery_pairs_per_frame_region=6,repeated_reference_rows_are_independent_observations=False,source_hashes_verified=len(plan['source_hashes']),raw_only_slots=raw_only,native_input_counts=input_counts,maximum_absolute_differences_by_kind=maxima,production_functions_imported=False,network_requests=0,prior_epoch_pipeline_rerun=False,classifications_changed=0,source_hashes=initial,audit_script_sha256=sha(Path(__file__)),limitations=['Independent bounded input/profile arithmetic and lineage verification only; no origin, significance or classifier conclusion.','Raw-only coverage failures remain distinct from nonpositive continuum. Raw Pearson and normalized RMS retain separate support gates.','Seven original HD114386 archival epochs and four discovery records were already used in original epoch/raw investigations and completed blue normalization context. No earlier HD112410 or HD106515A cohort is transferred. This group wavelength is disjoint from completed bounded groups but reuses prior observing data; this audit adds no independent observations, blind validation, normalization replay or origin conclusion.'])
 with (OUT/'NUMERICAL_AUDIT.json').open('x')as f:json.dump(report,f,indent=2);f.write('\n')
 with (OUT/'NUMERICAL_DIFFERENCES.csv').open('x',newline='')as f:w=csv.DictWriter(f,fieldnames=['name','kind','scalar_values','maximum_absolute_difference']);w.writeheader();w.writerows(differences)
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
