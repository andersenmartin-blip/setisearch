"""Independent C005 reconstruction after the parent confirms completed execution."""
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
 ck(summary['status']=='COMPLETE_FIXED_GROUP_CONTEXT','Complete production profile slots')
 ck(release['schema']=='HARPS_C005_GROUP_RELEASE_V1'and release['publication_readback_verified']is True,'Exact released phase')
 ck(release['plan_sha256']==sha(A/'PLAN.json')and release['script_sha256']==sha(A/'compare_group.py')and summary['release_sha256']==sha(A/'ROOT_RELEASE.json'),'Release/code/plan/result bindings')
 ck(release['inventory_path']==plan['inventory_path']and release['inventory_sha256']==sha(ROOT/plan['inventory_path']),'Exact input inventory binding')
 for p,h in plan['source_hashes'].items():ck(sha(ROOT/p)==h,'Source '+p)
 for p,h in hashes.items():ck(sha(RESULT/p)==h,'Production output '+p)
 initial={str(p.relative_to(ROOT)):sha(p)for p in [A/'PLAN.json',A/'ROOT_RELEASE.json',RESULT/'OUTPUT_HASHES.json',OUT/'independent_math.py']}
 records=read(RESULT/'PROFILE_METRICS.json');pairs=read(RESULT/'COMPARISONS.json');bounded=read(RESULT/'BOUNDED_INPUT_INDEX.json')
 ck(len(records)==34 and len(pairs)==180 and len(bounded)==17,'Exact34/180/17 accounting')
 index={(r['kind'],r['dp_id'],r['order']):r for r in bounded};record_index={(r['kind'],r['dp_id'],r['order'],r['frame']):r for r in records}
 ck(len(index)==17 and len(record_index)==34,'No duplicate source/frame slots')
 included=[(r['dp_id'],o)for r in inv['native_products']for o in r['covering_orders']]
 excluded=[]
 ck(len(included)==10 and [(r['dp_id'],r['order'])for r in plan['included_native_order_pairs']]==included and [(r['dp_id'],r['order'])for r in plan['excluded_native_order_pairs']]==excluded,'Exact prospective included and excluded native pairs')
 ck({(r['dp_id'],r['order'])for r in records if r['kind']=='native'}==set(included)and not(set(included)&set(excluded)),'No excluded order read or substituted')
 scope=read(RESULT/'NATIVE_ORDER_SCOPE.json')
 ck(scope['included_pairs']==plan['included_native_order_pairs']and scope['excluded_pairs']==plan['excluded_native_order_pairs']and scope['excluded_orders_measured']is False,'Metadata exclusions retained explicitly')
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
 expected_pairs=[];references=['ADP.2022-01-06T01:08:04.689','ADP.2022-03-08T01:01:37.342','ADP.2022-05-08T01:01:37.876','ADP.2023-03-23T01:02:04.831','ADP.2023-07-05T01:02:00.053']
 for row in reconstructed:
  reference_ids=references if row['kind']=='merged'else[row['dp_id']]
  for reference in reference_ids:
   left=expected_profiles[(row['kind'],row['dp_id'],row['order'],row['frame'])];right=expected_profiles[('merged',reference,None,row['frame'])]
   for region,mask in [('core',ref.CORE),('broad_pattern',ref.BROAD)]:
    expected_pairs.append(dict(relationship='MERGED_EPOCH_TO_DISCOVERY'if row['kind']=='merged'else'SAME_EPOCH_NATIVE_TO_MERGED',source_id=row['source_id'],dp_id=row['dp_id'],order=row['order'],reference_dp_id=reference,frame=row['frame'],region=region,same_exposure=row['dp_id']==reference,identical_product_self_pair=row['kind']=='merged'and row['dp_id']==reference,**ref.comparison(left,right,mask)))
 ck(len(expected_pairs)==180,'All180 independent relationships')
 ck(sum(r['identical_product_self_pair']for r in expected_pairs)==20,'Exactly20 self comparisons retained and labeled')
 for i,(actual,expected)in enumerate(zip(pairs,expected_pairs)):close(actual,expected,'Comparison '+str(i),'comparison')
 raw_only=[dict(kind=r['kind'],dp_id=r['dp_id'],order=r['order'],frame=r['frame'],reasons=r['normalization_reasons'])for r in reconstructed if r['normalization_status']=='RAW_ONLY']
 ck(summary['raw_only_normalization_slots']==len(raw_only)and summary['blocked_source_profile_slots']==0,'Exact raw-only versus blocked accounting')
 preserved=read(RESULT/'PRESERVED_RAW_CONTEXT.json');ck(len(preserved)==10,'All ten historical raw-order panels retained')
 for row in preserved:ck(sha(RESULT/row['copied_path'])==row['file']['sha256']==sha(ROOT/row['file']['path']),'Historical raw context byte identity')
 ck(summary['labels_changed']==summary['origin_assignments']==0 and summary['old_epoch_pipeline_rerun']is False,'Unchanged classifications and old pipeline')
 for p,h in plan['source_hashes'].items():ck(sha(ROOT/p)==h,'Source unchanged '+p)
 for p,h in hashes.items():ck(sha(RESULT/p)==h,'Output unchanged '+p)
 for p,h in initial.items():ck(sha(ROOT/p)==h,'Audit binding unchanged '+p)
 maxima={kind:max(r['maximum_absolute_difference']for r in differences if r['kind']==kind)for kind in sorted({r['kind']for r in differences})}
 report=dict(status='PASS_INDEPENDENT_C005_NUMERICAL_RECONSTRUCTION',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),checks_passed=checks,scalar_values_compared=scalars,profiles_reconstructed=34,comparisons_reconstructed=180,bounded_input_records_reconstructed=17,preserved_raw_context_files_verified=10,identical_product_self_comparisons=20,metadata_excluded_native_orders=0,source_hashes_verified=len(plan['source_hashes']),raw_only_slots=raw_only,native_input_counts=input_counts,maximum_absolute_differences_by_kind=maxima,production_functions_imported=False,network_requests=0,prior_epoch_pipeline_rerun=False,classifications_changed=0,source_hashes=initial,audit_script_sha256=sha(Path(__file__)),limitations=['Independent bounded input/profile arithmetic and lineage verification only; no origin, significance or classifier conclusion.','Raw-only coverage failures remain distinct from nonpositive continuum. Raw Pearson and normalized RMS retain separate support gates.','Seven archival epochs and five nearby discovery records are correlated; this audit adds no independent observations.'])
 with (OUT/'NUMERICAL_AUDIT.json').open('x')as f:json.dump(report,f,indent=2);f.write('\n')
 with (OUT/'NUMERICAL_DIFFERENCES.csv').open('x',newline='')as f:w=csv.DictWriter(f,fieldnames=['name','kind','scalar_values','maximum_absolute_difference']);w.writeheader();w.writerows(differences)
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
