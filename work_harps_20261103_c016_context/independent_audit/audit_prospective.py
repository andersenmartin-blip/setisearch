"""Compact C016 source and analytic synthetic preflight; no observed arrays."""
import ast,datetime,hashlib,importlib.util,json,math
from pathlib import Path
import tempfile
import numpy as np
from astropy.io import fits
import independent_math as ref
OUT=Path(__file__).resolve().parent;A=OUT.parent/'analysis';ROOT=OUT.parents[1]
count=0;scalars=0;maxerr=0.
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def ck(v,label):
 global count
 if not v:raise AssertionError(label)
 count+=1
def same(a,b):
 global scalars,maxerr
 if isinstance(b,dict):return set(a)==set(b)and all(same(a[k],v)for k,v in b.items())
 if isinstance(b,(str,bool))or b is None:return a==b
 if isinstance(b,list)and b and isinstance(b[0],(str,dict)):return len(a)==len(b)and all(same(x,y)for x,y in zip(a,b))
 aa=np.asarray(a,dtype=float);bb=np.asarray(b,dtype=float);scalars+=aa.size
 if aa.shape!=bb.shape or not np.allclose(aa,bb,rtol=2e-9,atol=2e-9,equal_nan=True):return False
 good=np.isfinite(aa)&np.isfinite(bb)
 if good.any():maxerr=max(maxerr,float(np.max(np.abs(aa[good]-bb[good]))))
 return True
def main():
 plan=read(A/'PLAN.json');code=A/'compare_group.py'
 for p,h in plan['source_hashes'].items():ck(sha(ROOT/p)==h,'Bound source '+p)
 spec=importlib.util.spec_from_file_location('c016_synthetic_only',code);prod=importlib.util.module_from_spec(spec);spec.loader.exec_module(prod)
 ck(np.array_equal(prod.X,ref.X)and np.array_equal(prod.CORE,ref.CORE)and np.array_equal(prod.BROAD,ref.BROAD),'Exact 601 / 51 / 550 geometry')
 ck(prod.CB==ref.CB and prod.CT==ref.CT and prod.ANCHOR_BERV==ref.ANCHOR_BERV,'Common fixed group frame anchors')
 tree=ast.parse(code.read_text());headers=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='inspect_headers')
 ck(not any(isinstance(n,ast.Attribute)and n.attr in ['data','section']for n in ast.walk(headers)),'Header inspection has no array access')
 ck('assert len(records)==22 and len(pairs)==128 and len(all_profiles)==22'in code.read_text(),'All 22 profile / 128 comparison slots asserted')
 ck('NATIVE_EXTRACTED_UNIT_UNSPECIFIED'in code.read_text(),'Native unit not silently equated to ADU')
 for path,label in [(OUT/'audit_actual.py','Actual audit'),(OUT/'independent_math.py','Independent scalar math')]:
  imports=[n for n in ast.walk(ast.parse(path.read_text()))if isinstance(n,(ast.Import,ast.ImportFrom))]
  names=[n.module or ''for n in imports if isinstance(n,ast.ImportFrom)]+[a.name for n in imports if isinstance(n,ast.Import)for a in n.names]
  ck(not any('compare_group'in n or 'plot_group'in n or 'importlib'in n for n in names),label+' imports no production functions')
 old_tree=ast.parse((ROOT/'work_harps_20261103_c011_context/analysis/compare_group.py').read_text())
 for name in ['sampling_parameters','profile','comparison']:
  old=next(n for n in old_tree.body if isinstance(n,ast.FunctionDef)and n.name==name);new=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==name)
  ck(ast.dump(old)==ast.dump(new),'Unchanged C011 estimator '+name)
 inventory=read(ROOT/plan['inventory_path']);handoff=read(ROOT/'work_harps_20261103_c011_context/NEXT_ACTION.json')
 expected_events={'V2E2-0094':'ADP.2022-03-08T01:01:37.348','V2E2-0096':'ADP.2022-05-17T01:02:16.724','V2E2-0098':'ADP.2023-01-03T01:08:17.803','V2E2-0110':'ADP.2023-08-29T01:02:07.487'}
 references=list(expected_events.values());event_centers={r['candidate_id']:float(r['center_bary_air_angstrom'])for r in handoff['existing_context']};epochs=handoff['existing_cohort_epochs']
 ck(inventory['target']=='HD114386'and [r['dp_id']for r in inventory['merged_spectra']]==[r['dp_id']for r in epochs],'Exact distinct HD114386 seven-product cohort')
 ck(len(epochs)==7 and math.isclose(max(r['berv_km_s']for r in epochs)-min(r['berv_km_s']for r in epochs),51.572001697156,rel_tol=0,abs_tol=1e-12),'Target-specific BERV span retained')
 for actual,expected in zip(inventory['merged_spectra'],epochs):ck(actual['date_obs']==expected['date_obs']and actual['berv_km_s']==expected['berv_km_s'],'Exact target epoch date and BERV '+actual['dp_id'])
 anchor=next(r for r in inventory['merged_spectra']if r['dp_id']==references[0])
 ck(ref.ANCHOR_BERV==anchor['berv_km_s']==19.1606928163471 and plan['anchor_dp_id']==references[0]and plan['anchor_berv_km_s']==ref.ANCHOR_BERV,'First queue March 2022 discovery anchors fixed group topocentric frame')
 ck(plan['events']==prod.EVENTS==expected_events and prod.REFERENCES==references,'All four event and fixed-reference identities retained')
 ck([r['dp_id']for r in inventory['native_products']]==references and len(set(references))==4,'Four distinct native discovery exposures')
 ck(set(event_centers)==set(expected_events)and [event_centers[e]for e in expected_events]==[4303.785,4303.785,4303.785,4303.79],'Every original catalog center retained exactly')
 ck(ref.CB==(min(event_centers.values())+max(event_centers.values()))/2==4303.7875 and ref.CT==4303.512448784194,'Group midpoint and March wavelength-specific anchor exactly fixed')
 coordinate=inventory['coordinate_anchor']
 ck(coordinate['discovery_dp_id']==references[0]and coordinate['discovery_berv_km_s']==ref.ANCHOR_BERV and coordinate['center_barycentric_air_angstrom']==ref.CB and coordinate['fixed_topocentric_air_angstrom']==ref.CT and coordinate['original_member_centers_barycentric_air_angstrom']==event_centers,'Fresh inventory separates common group anchor from all original member centers')
 markers={r['event']:r for r in plan['event_markers']};bervs={r['dp_id']:r['berv_km_s']for r in epochs}
 ck(set(markers)==set(expected_events)and all(markers[e]['center_bary_air_angstrom']==c and markers[e]['barycentric_offset_angstrom']==c-ref.CB and markers[e]['discovery_topocentric_offset_angstrom']==c/(1+bervs[expected_events[e]]/ref.C)-ref.CT for e,c in event_centers.items()),'Four event markers preserve each original center and its own discovery BERV')
 ck(sum(ref.CORE)==51 and sum(ref.BROAD)==550 and max(abs(c-ref.CB)for c in event_centers.values())<.002500000001,'Fixed group core differs from original member cores by at most 0.0025 Angstrom')
 ck(plan['individual_event_centers_bary_air_angstrom']==event_centers and plan['individual_event_cores_bary_air_angstrom']=={e:[c-.25,c+.25]for e,c in event_centers.items()},'Exact individual original core bounds remain separate from fixed common mask')
 chosen=[];native_coefficients={}
 for item in inventory['native_products']:
  berv=item['primary_header']['ESO DRS BERV'];candidates=[e for e,dp in expected_events.items()if dp==item['dp_id']]
  ck(item['original_event_centers_topocentric_air_angstrom']=={e:event_centers[e]/(1+berv/ref.C)for e in candidates},'Original source center uses its own discovery BERV rather than common group anchor '+item['dp_id'])
  ck(item['covering_orders']==[19],'Fresh native scope selects order 19 for '+item['dp_id'])
  for order in item['covering_orders']:
   coeff=item['orders'][str(order)]['wavelength_coefficients_ascending'];lo=coeff[0];hi=math.fsum(c*4095**i for i,c in enumerate(coeff))
   for event in candidates:ck(lo<event_centers[event]/(1+berv/ref.C)<hi,'Original member center covered in its own native exposure '+event)
   chosen.append((item['dp_id'],order));native_coefficients[(item['dp_id'],order)]=coeff
 ck(len(chosen)==4 and inventory['excluded_native_orders']==[],'Four selected native contexts and no metadata exclusions')
 ck([(r['dp_id'],r['order'])for r in plan['included_native_order_pairs']]==chosen and plan['excluded_native_order_pairs']==[],'Deduplicated planned native source slots')
 ck(len(inventory['saved_native_raw_cutouts'])==4 and {(r['event'],r['order'])for r in inventory['saved_native_raw_cutouts']}=={(e,19)for e in expected_events},'All four historical raw-order contexts retained')
 ck(7*4*2*2+4*2*2==128 and 4*2*2==16,'128 comparison slots including sixteen self-pairs')
 ck(plan['slots']['all_profiles']==22 and plan['slots']['all_comparisons']==128 and plan['slots']['identical_product_self_comparisons']==16 and plan['slots']['expected_bounded_input_windows']==11,'Declared plan counts match joint unique products')
 ck(plan['comparisons']['minimum_common_core']==41 and plan['comparisons']['minimum_common_broad']==440,'Plan common-support gates match grid geometry')
 dependency=handoff['wavelength_dependency']
 ck(dependency['overlaps_any_completed_bounded_group_window']is False and dependency['proposed_group_core_bary_air_angstrom']==[ref.CB-.25,ref.CB+.25]and dependency['proposed_group_window_bary_air_angstrom']==[ref.CB-3,ref.CB+3],'Disjoint group context and fixed group core match metadata handoff without new-data claim')
 mapping={(r['event'],r['dp_id'],r['order']):r for r in inventory['mapping_records']};keys=['original_grid_mapping_usable','original_local_mapping_usable','original_baseline_mapping_verified','final_reference_mapping_supported']
 ck(len(mapping)==4 and set(mapping)=={(e,dp,19)for e,dp in expected_events.items()}and all(all(r[k]is True for k in keys)and r['registration_changed']is False for r in mapping.values()),'Four all-true historical mapping chains retained by event/product/order')
 history=inventory['historical_raw_review_records']
 ck(all(len(history[stage])==4 for stage in ['primary','secondary','adopted','comparison']),'Four complete historical review chains')
 for stage in ['primary','secondary','adopted']:ck({r['candidate_id']for r in history[stage]}==set(expected_events)and all(r['code']=='U'for r in history[stage]),'All historical '+stage+' U reviews retained')
 ck({r['review_id']for r in history['comparison']}==set(expected_events)and all(r['primary']==r['secondary']==r['adopted']=='U'for r in history['comparison'])and all(r['evidence']and r['root_adoption_note']for r in history['adopted']),'Four exact unresolved-feature histories and original adoptions retained')
 scan=inventory['all_order_header_scan'];ck(len(scan)==288,'Four complete all-72-order header scans')
 for item in inventory['native_products']:
  dp=item['dp_id'];berv=item['primary_header']['ESO DRS BERV'];header=fits.getheader(ROOT/item['file']['path'],0);degree=header['ESO DRS CAL TH DEG LL'];rows=[r for r in scan if r['dp_id']==dp]
  ck(degree==3,'Cubic wavelength header permits exact derivative minimum check '+dp)
  ck([r['order']for r in rows]==list(range(72)),'Each native order included once for '+dp)
  original_centers=[event_centers[e]/(1+berv/ref.C)for e,refdp in expected_events.items()if refdp==dp];selected=[]
  for row in rows:
   order=row['order'];coeff=[header['ESO DRS CAL TH COEFF LL'+str(order*(degree+1)+i)]for i in range(degree+1)];lo=coeff[0];hi=math.fsum(c*4095**i for i,c in enumerate(coeff));covered=any(lo<=c<=hi for c in original_centers)
   positions=[0.,4095.]
   if coeff[3]and 0<-coeff[2]/(3*coeff[3])<4095:positions.append(-coeff[2]/(3*coeff[3]))
   positive=min(math.fsum(i*c*x**(i-1)for i,c in enumerate(coeff)if i)for x in positions)>0
   ck(positive and row['positive_wavelength_derivative_on_full_order']is True and np.allclose([lo,hi],row['header_endpoint_topocentric_air_angstrom'],rtol=0,atol=1e-9)and row['covers_any_original_event_center']==row['selected_for_profile']==covered,'Independent monotonic-header covering-order decision '+dp+'/'+str(order))
   if covered:selected.append(order)
  ck(selected==[19],'Fresh native header independently selects only order 19 for '+dp)
 for (dp,order),coeff in native_coefficients.items():
  berv=next(item['primary_header']['ESO DRS BERV']for item in inventory['native_products']if item['dp_id']==dp);start=coeff[0];end=math.fsum(c*4095**i for i,c in enumerate(coeff))
  for lo,hi in [(start*(1+berv/ref.C)-ref.CB,end*(1+berv/ref.C)-ref.CB),(start-ref.CT,end-ref.CT)]:ck(lo<-3 and hi>3 and sum(lo<=x<=hi for x in ref.X)==601,'Fresh order 19 covers fixed group core/window/flanks geometrically '+dp)
 for berv in [26.7544256646121,-24.8175760325439]:
  center,scale=prod.sampling_parameters(berv,'topocentric')
  ck(center==ref.CT and abs((center+3)*scale/(1+berv/ref.C)-(ref.CT+3))<1e-12,'Both BERV extremes preserve common topocentric frame')
 wave=np.linspace(ref.CB-4,ref.CB+4,1601);x=wave-ref.CB
 base=20+.3*np.sin(8*x)+3*np.exp(-.5*(x/.07)**2)
 fixtures=[('positive',np.ones(len(wave),bool),base),('gap_and_nan',~((x>.10)&(x<.20)),base.copy()),('missing_left',x>-.8,base),('missing_right',x<.5,base),('nonpositive',np.ones(len(wave),bool),-base)]
 fixtures[1][2][35]=np.nan
 for label,mask,flux in fixtures:
  w=wave[mask];f=flux[mask];e=np.full(len(w),np.nan);spacing=float(np.median(np.diff(w)))
  for frame in ['barycentric','topocentric']:
   arrays,metric=prod.profile(w,f,e,-24.8175760325439,frame,spacing);wanted,wmetric=ref.profile(w,f,e,-24.8175760325439,frame,spacing)
   ck(same(arrays,wanted)and same(metric,wmetric),'Independent profile '+label+'/'+frame)
   for region,pmask,rmask in [('core',prod.CORE,ref.CORE),('broad',prod.BROAD,ref.BROAD)]:
    ck(same(prod.comparison(arrays,arrays,pmask),ref.comparison(wanted,wanted,rmask)),'Independent comparison '+label+'/'+frame+'/'+region)
   if label=='missing_left':ck(metric['normalization_status']=='RAW_ONLY'and'MISSING_LEFT_FLANK_COVERAGE'in metric['normalization_reasons'],'Coverage failure retained independently of sign')
   if label=='missing_right':ck(metric['normalization_status']=='RAW_ONLY'and'MISSING_RIGHT_FLANK_COVERAGE'in metric['normalization_reasons'],'Right coverage failure retained independently of sign')
   if label=='nonpositive':ck('NONPOSITIVE_FLANK_REFERENCE'in metric['normalization_reasons'],'Negative reference not divided by absolute value')
   if frame=='topocentric':ck(np.allclose(arrays['requested_bary_wave']/(1+-24.8175760325439/ref.C),ref.CT+np.array(ref.X),rtol=0,atol=1e-12),'Native fixed topocentric request')
 # Header-derived coordinates with analytic synthetic flux only, both covering orders.
 for (dp,order),native_coeff in native_coefficients.items():
  berv=next(item['primary_header']['ESO DRS BERV']for item in inventory['native_products']if item['dp_id']==dp)
  synthetic_native=np.array([math.fsum(c*i**k for k,c in enumerate(native_coeff)) for i in range(4096)])*(1+berv/ref.C)
  synthetic_flux=20+.3*np.sin(8*(synthetic_native-ref.CB))
  for frame in ['barycentric','topocentric']:
   spacing=float(np.median(np.diff(synthetic_native)));error=np.full(len(synthetic_native),np.nan)
   arrays,metric=prod.profile(synthetic_native,synthetic_flux,error,berv,frame,spacing)
   wanted,wmetric=ref.profile(synthetic_native,synthetic_flux,error,berv,frame,spacing)
   ck(same(arrays,wanted)and same(metric,wmetric),'Independent header-derived synthetic order '+str(order)+'/'+frame)
   core=prod.comparison(arrays,arrays,prod.CORE);broad=prod.comparison(arrays,arrays,prod.BROAD)
   ck(metric['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE'and metric['normalization_reasons']==[]and metric['left_flank_finite_samples']>=20 and metric['right_flank_finite_samples']>=20,'Synthetic positive order '+str(order)+' reference has both fixed flanks '+frame)
   ck(core['common_finite_raw_samples']==51 and broad['common_finite_raw_samples']==550 and core['raw_pearson']is not None and broad['raw_pearson']is not None,'Synthetic order '+str(order)+' complete core/broad support '+frame)
   ck(core['normalized_rms']==0 and broad['normalized_rms']==0,'Synthetic order '+str(order)+' normalized self RMS exactly zero '+frame)
 # Finite flank sample count is a separate gate from geometric availability.
 for n in [19,20]:
  flux=base.copy();side_positions=np.flatnonzero((x>=-3)&(x<=-1.5));flux[side_positions[n:]]=np.nan
  error=np.resize(np.array([np.nan,-1.,0.,1.]),len(wave))
  arrays,metric=prod.profile(wave,flux,error,ref.ANCHOR_BERV,'barycentric',float(np.median(np.diff(wave))))
  wanted,wmetric=ref.profile(wave,flux,error,ref.ANCHOR_BERV,'barycentric',float(np.median(np.diff(wave))))
  ck(same(arrays,wanted) and same(metric,wmetric),'Independent finite-flank boundary '+str(n))
  ck(metric['left_flank_finite_samples']==n and metric['normalization_status']==('RAW_ONLY'if n==19 else'USABLE_POSITIVE_FLANK_REFERENCE'),'Exactly 20 finite samples needed on each flank')
 # Zero reference, finite-support absence and low positive reference are separate outcomes.
 zero=np.zeros(len(wave));missing=base.copy();missing[(x>=1.5)&(x<=3)]=np.nan
 low=np.random.default_rng(120087).normal(0,10,len(wave));flanks=(np.abs(x)>=1.5)&(np.abs(x)<=3);low+=1-np.median(low[flanks])
 for label,flux in [('zero_reference',zero),('zero_finite_right_flank',missing),('positive_low_reference',low)]:
  error=np.full(len(wave),np.nan);spacing=float(np.median(np.diff(wave)))
  arrays,metric=prod.profile(wave,flux,error,ref.ANCHOR_BERV,'barycentric',spacing)
  wanted,wmetric=ref.profile(wave,flux,error,ref.ANCHOR_BERV,'barycentric',spacing)
  ck(same(arrays,wanted)and same(metric,wmetric),'Independent distinct reference outcome '+label)
  if label=='zero_reference':ck(metric['normalization_status']=='RAW_ONLY'and metric['normalization_reasons']==['NONPOSITIVE_FLANK_REFERENCE']and metric['low_flank_reference']is None,'Zero reference remains distinct from a low positive reference')
  elif label=='zero_finite_right_flank':ck(metric['normalization_status']=='RAW_ONLY'and metric['normalization_reasons']==['INSUFFICIENT_FINITE_RIGHT_FLANK']and metric['right_flank_native_samples']>0 and metric['right_flank_finite_samples']==0,'Geometric flank can have no finite support')
  else:ck(metric['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE'and metric['low_flank_reference']is True and np.nanmin(arrays['normalized_flux'])<0,'Low positive reference remains flagged with signed flux intact')
 for mask,rmask in [(prod.CORE,ref.CORE),(prod.BROAD,ref.BROAD)]:
  constant={'signed_raw_flux':np.full(601,.1),'normalized_flux':np.full(601,.1)}
  ck(prod.comparison(constant,constant,mask)['raw_pearson_block_reason']=='ZERO_RAW_VARIANCE','Exact constant noninteger zero-range guard')
  nominal=int(mask.sum());minimum=math.ceil(.8*nominal)
  for n in [minimum-1,minimum]:
   z=np.full(601,np.nan);positions=np.flatnonzero(mask)[:n];z[positions]=np.arange(n,dtype=float)
   a={'signed_raw_flux':z,'normalized_flux':z.copy()}
   ck(same(prod.comparison(a,a,mask),ref.comparison(a,a,rmask)),'80percent common-support boundary')
 with tempfile.TemporaryDirectory(prefix='release_fixture_',dir=OUT)as td:
  p=Path(td)/'release.json';release=dict(schema='HARPS_C016_GROUP_RELEASE_V1',publication_readback_verified=True,publication_commit='a'*40,plan_sha256=sha(A/'PLAN.json'),script_sha256=sha(code),inventory_path=plan['inventory_path'],inventory_sha256=plan['source_hashes'][plan['inventory_path']]);p.write_text(json.dumps(release));prod.validate(p);ck(True,'Valid metadata-only release contract')
  for key,bad in [('schema','BAD'),('publication_readback_verified',False),('publication_commit','x'),('plan_sha256','0'*64),('script_sha256','0'*64),('inventory_path','wrong'),('inventory_sha256','0'*64)]:
   p.write_text(json.dumps(dict(release,**{key:bad})))
   try:prod.validate(p)
   except ValueError:ck(True,'Release refusal '+key)
   else:raise AssertionError('Invalid release accepted '+key)
 for p,h in plan['source_hashes'].items():ck(sha(ROOT/p)==h,'Frozen source unchanged '+p)
 report=dict(status='PASS_COMPACT_PROSPECTIVE_C016_AUDIT',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),checks_passed=count,synthetic_scalar_values_compared=scalars,maximum_synthetic_absolute_difference=maxerr,plan_sha256=sha(A/'PLAN.json'),analysis_script_sha256=sha(code),independent_math_sha256=sha(OUT/'independent_math.py'),audit_script_sha256=sha(Path(__file__)),actual_audit_script_sha256=sha(OUT/'audit_actual.py'),source_hashes_verified=len(plan['source_hashes']),observational_arrays_read=0,network_requests=0,production_import_scope='Synthetic function harness only; independent math imports no production code; actual audit imports no production functions.',scope=['Four original HD114386 records and exact centers4303.785/4303.785/4303.785/4303.79 retained; fixed group midpoint4303.7875 and first-queue March discovery anchor4303.512448784194.','601-point grid; 51 group-core / 550 surrounding points; exact41/440 common supports. Group core differs from individual original cores by0.0025 Angstrom at each relevant edge.','Signed pooled-flank median and20 finite samples per flank; missing coverage, insufficient finite support, nonpositive reference and low positive references remain distinct. No fitted shift, width or background.','Exact22 profiles/128 comparisons/11 bounded inputs/4 raw contexts/16 identical-product self comparisons. Every merged epoch is compared with all four fixed references; each native context only with its own same-exposure merged product. Per frame and region, 24 nonself rows are four sets of six comparisons on seven epochs, including six reciprocal discovery pairs, not 24 independent epochs.','Four independent all-72-order header scans select order19 per product with geometric full-window and both-flank coverage. Each member uses its own historical center and BERV for source coverage; group frame uses one fixed March anchor.','Four original global/local/baseline/five-window mapping histories remain all true without changed registration; primary/secondary/adopted labels remain U for each record.','Target-specific seven January2022–August2023 epochs span51.572001697156 km/s BERV. Original epoch/raw and blue normalization contexts already used these observations. Disjoint group wavelengths do not establish blind or independent evidence.'],limitations=['Source/synthetic preflight only; actual arrays await root public release and stable completed-run ledger.','No origin, significance, uncertainty calibration, new observing time, classification change or normalization-pipeline replay follows.'])
 with (OUT/'PROSPECTIVE_AUDIT.json').open('x')as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
