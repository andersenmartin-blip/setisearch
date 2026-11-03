"""Compact C015 source and analytic synthetic preflight; no observed arrays."""
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
 spec=importlib.util.spec_from_file_location('c015_synthetic_only',code);prod=importlib.util.module_from_spec(spec);spec.loader.exec_module(prod)
 ck(np.array_equal(prod.X,ref.X)and np.array_equal(prod.CORE,ref.CORE)and np.array_equal(prod.BROAD,ref.BROAD),'Exact 601 / 51 / 550 geometry')
 ck(prod.CB==ref.CB and prod.CT==ref.CT and prod.ANCHOR_BERV==ref.ANCHOR_BERV,'Common fixed frame anchors')
 tree=ast.parse(code.read_text());headers=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='inspect_headers')
 ck(not any(isinstance(n,ast.Attribute)and n.attr in ['data','section']for n in ast.walk(headers)),'Header inspection has no array access')
 ck('assert len(records)==16 and len(pairs)==32 and len(all_profiles)==16'in code.read_text(),'All 16 profile / 32 comparison slots asserted')
 ck('NATIVE_EXTRACTED_UNIT_UNSPECIFIED'in code.read_text(),'Native unit not silently equated to ADU')
 actual_ast=ast.parse((OUT/'audit_actual.py').read_text());math_ast=ast.parse((OUT/'independent_math.py').read_text())
 for audit_ast,label in [(actual_ast,'Actual audit'),(math_ast,'Independent scalar math')]:
  imports=[n for n in ast.walk(audit_ast)if isinstance(n,(ast.Import,ast.ImportFrom))]
  names=[n.module or '' for n in imports if isinstance(n,ast.ImportFrom)]+[alias.name for n in imports if isinstance(n,ast.Import)for alias in n.names]
  ck(not any('compare_group'in n or 'plot_group'in n or 'importlib'in n for n in names),label+' imports no production functions')

 # Scientific estimator functions must remain identical to completed C016.
 old_tree=ast.parse((ROOT/'work_harps_20261103_c016_context/analysis/compare_group.py').read_text())
 for name in ['sampling_parameters','profile','comparison']:
  old=next(n for n in old_tree.body if isinstance(n,ast.FunctionDef)and n.name==name)
  new=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==name)
  ck(ast.dump(old)==ast.dump(new),'Unchanged C016 estimator '+name)
 inventory=read(ROOT/plan['inventory_path']);handoff=read(ROOT/'work_harps_20261103_c016_context/NEXT_ACTION.json')
 event_centers={r['candidate_id']:float(r['center_bary_air_angstrom'])for r in handoff['existing_context']}
 expected_events={'V2E2-0095':'ADP.2022-05-17T01:02:16.724'}
 references=list(dict.fromkeys(expected_events.values()))
 expected_epochs=handoff['existing_cohort_epochs']
 ck(inventory['target']=='HD114386' and [r['dp_id']for r in inventory['merged_spectra']]==[r['dp_id']for r in expected_epochs],'Exact distinct HD114386 seven-product cohort')
 ck(len(expected_epochs)==7 and math.isclose(max(r['berv_km_s']for r in expected_epochs)-min(r['berv_km_s']for r in expected_epochs),51.572001697156,rel_tol=0,abs_tol=1e-13),'Target-specific BERV span retained')
 for actual,expected in zip(inventory['merged_spectra'],expected_epochs):
  ck(actual['date_obs']==expected['date_obs'] and actual['berv_km_s']==expected['berv_km_s'],'Exact target epoch date and BERV '+actual['dp_id'])
 anchor=next(r for r in inventory['merged_spectra'] if r['dp_id']==references[0])
 ck(references[0]=='ADP.2022-05-17T01:02:16.724' and ref.ANCHOR_BERV==anchor['berv_km_s']==-10.767337430651 and plan['anchor_dp_id']==references[0] and plan['anchor_berv_km_s']==ref.ANCHOR_BERV,'First discovery May 2022 anchor independently matches exact metadata')
 coordinate=inventory['coordinate_anchor']
 ck(coordinate['discovery_dp_id']==references[0]and coordinate['discovery_berv_km_s']==ref.ANCHOR_BERV and coordinate['center_barycentric_air_angstrom']==ref.CB and coordinate['fixed_topocentric_air_angstrom']==ref.CT==3870.0539967497375,'C015 wavelength-specific May anchor exactly matches fresh inventory')
 ck(plan['events']==expected_events and prod.EVENTS==expected_events,'Preserve singleton C015 event identity')
 ck(prod.REFERENCES==references and len(references)==1,'Exactly one May 2022 discovery reference')
 ck([r['dp_id']for r in inventory['native_products']]==references,'One unique native exposure')
 ck(ref.CB==event_centers['V2E2-0095'] and sum(ref.CORE)==51 and sum(ref.BROAD)==550,'Metadata center and complete original core')
 markers=plan['event_markers']
 ck(len(markers)==1 and markers[0]['event']=='V2E2-0095'and markers[0]['center_bary_air_angstrom']==ref.CB and markers[0]['barycentric_offset_angstrom']==markers[0]['discovery_topocentric_offset_angstrom']==0,'Original singleton marker coincides with its own fixed frame centers')
 for center in event_centers.values():ck(ref.CB-.25<=center-.25+1e-11 and ref.CB+.25>=center+.25-1e-11,'Original event core equals fixed context core')
 chosen=[]
 for item in inventory['native_products']:
  berv=item['primary_header']['ESO DRS BERV']
  candidates=[event for event,dp in expected_events.items()if dp==item['dp_id']]
  ck(item['covering_orders']==[3],'Fresh covering scope selects only native order 3')
  for order in item['covering_orders']:
   c=item['orders'][str(order)]['wavelength_coefficients_ascending'];lo=c[0];hi=math.fsum(v*4095**i for i,v in enumerate(c))
   for event in candidates:ck(lo<event_centers[event]/(1+berv/ref.C)<hi,'Exact event header coverage '+event+'/order '+str(order))
   chosen.append((item['dp_id'],order))
 ck(len(chosen)==1 and inventory['excluded_native_orders']==[],'Exact one selected/no metadata-excluded orders')
 ck([(r['dp_id'],r['order'])for r in plan['included_native_order_pairs']]==chosen and plan['excluded_native_order_pairs']==[],'Deduplicated planned native source slots')
 ck(len(inventory['saved_native_raw_cutouts'])==1 and {r['event']for r in inventory['saved_native_raw_cutouts']}==set(expected_events) and {r['order']for r in inventory['saved_native_raw_cutouts']}=={3},'Keep the original historical raw-order context')
 ck(7*1*2*2+1*2*2==32 and 1*2*2==4,'32 comparison slots including four self-pairs')
 ck(plan['slots']['all_profiles']==16 and plan['slots']['all_comparisons']==32 and plan['slots']['identical_product_self_comparisons']==4 and plan['slots']['expected_bounded_input_windows']==8,'Declared plan counts match unique products')
 ck(plan['comparisons']['minimum_common_core']==41 and plan['comparisons']['minimum_common_broad']==440,'Plan common-support gates match grid geometry')
 dependency=handoff['wavelength_dependency']
 ck(dependency['overlaps_current_C016_same_target_window']is False and dependency['overlaps_completed_same_target_normalization_windows']is False,'Current C016 and completed same-target normalization windows are disjoint')
 ck(all(r['prior_target']!='HD114386'and r['same_observing_products']is False and r['shared_source_pixels']is False for r in dependency['numeric_wavelength_overlaps_on_other_target']),'Numerical wavelength overlap on other targets does not share observations or source pixels')
 ck(dependency['C015_original_core_bary_air_angstrom']==[ref.CB-.25,ref.CB+.25]and dependency['proposed_C015_window_bary_air_angstrom']==[ref.CB-3,ref.CB+3],'Original singleton core and proposed context bounds match metadata handoff')
 mapping={r['order']:r for r in inventory['mapping_records']}
 keys=['original_grid_mapping_usable','original_local_mapping_usable','original_baseline_mapping_verified','final_reference_mapping_supported']
 ck(len(mapping)==len(inventory['mapping_records'])==1 and {r['event']for r in mapping.values()}==set(expected_events),'Original order 3 mapping history retained')
 ck([mapping[3][k]for k in keys]==[True,True,True,True] and all(r['registration_changed']is False for r in mapping.values()),'Global/local/baseline/five-window mapping stages remain unchanged')
 history=inventory['historical_raw_review_records']
 ck(len(history['primary'])==len(history['secondary'])==len(history['adopted'])==len(history['comparison'])==1,'One complete historical review chain')
 ck(history['primary'][0]['code']==history['secondary'][0]['code']==history['adopted'][0]['code']=='U','Historical primary/secondary/adopted U retained')
 ck(history['comparison'][0]['primary']==history['comparison'][0]['secondary']==history['comparison'][0]['adopted']=='U' and 'Native peak extends over many dispersion samples' in history['adopted'][0]['evidence'] and history['adopted'][0]['root_adoption_note'],'Preserve unresolved broad structure and agreeing U reviews')
 # Independently rescan all 72 order polynomials from the exact native primary header.
 native=inventory['native_products'][0];header=fits.getheader(ROOT/native['file']['path'],0)
 degree=header['ESO DRS CAL TH DEG LL'];scan=inventory['all_order_header_scan']
 ck(degree==3,'Cubic wavelength header permits exact derivative minimum check')
 ck(len(scan)==72 and [r['order']for r in scan]==list(range(72))and all(r['dp_id']==native['dp_id']for r in scan),'Fresh all-order scan includes each own-product native order once')
 independently_selected=[]
 for row in scan:
  order=row['order'];coeff=[header['ESO DRS CAL TH COEFF LL'+str(order*(degree+1)+i)]for i in range(degree+1)]
  lo=coeff[0];hi=math.fsum(c*4095**i for i,c in enumerate(coeff))
  covered=lo<=ref.CT<=hi
  positions=[0.,4095.]
  if coeff[3]and 0<-coeff[2]/(3*coeff[3])<4095:positions.append(-coeff[2]/(3*coeff[3]))
  positive=min(math.fsum(i*c*x**(i-1)for i,c in enumerate(coeff)if i)for x in positions)>0
  ck(positive and row['positive_wavelength_derivative_on_full_order']is True and np.allclose([lo,hi],row['header_endpoint_topocentric_air_angstrom'],rtol=0,atol=1e-9) and row['covers_any_original_event_center']==row['selected_for_profile']==covered,'Independent monotonic-header covering-order decision '+str(order))
  if covered:independently_selected.append(order)
 ck(independently_selected==[3],'Fresh native header independently yields only order 3')
 native_coefficients={order:native['orders'][str(order)]['wavelength_coefficients_ascending']for order in [3]}
 for order,coeff in native_coefficients.items():
  start=coeff[0];end=math.fsum(c*4095**i for i,c in enumerate(coeff))
  for lo,hi in [(start*(1+ref.ANCHOR_BERV/ref.C)-ref.CB,end*(1+ref.ANCHOR_BERV/ref.C)-ref.CB),(start-ref.CT,end-ref.CT)]:
   ck(lo<-3 and hi>3 and sum(lo<=x<=hi for x in ref.X)==601,'Fresh header order '+str(order)+' covers complete fixed core/window/flanks geometrically')
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
 for order,native_coeff in native_coefficients.items():
  synthetic_native=np.array([math.fsum(c*i**k for k,c in enumerate(native_coeff)) for i in range(4096)])*(1+ref.ANCHOR_BERV/ref.C)
  synthetic_flux=20+.3*np.sin(8*(synthetic_native-ref.CB))
  for frame in ['barycentric','topocentric']:
   spacing=float(np.median(np.diff(synthetic_native)));error=np.full(len(synthetic_native),np.nan)
   arrays,metric=prod.profile(synthetic_native,synthetic_flux,error,ref.ANCHOR_BERV,frame,spacing)
   wanted,wmetric=ref.profile(synthetic_native,synthetic_flux,error,ref.ANCHOR_BERV,frame,spacing)
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
  p=Path(td)/'release.json';release=dict(schema='HARPS_C015_GROUP_RELEASE_V1',publication_readback_verified=True,publication_commit='a'*40,plan_sha256=sha(A/'PLAN.json'),script_sha256=sha(code),inventory_path=plan['inventory_path'],inventory_sha256=plan['source_hashes'][plan['inventory_path']]);p.write_text(json.dumps(release));prod.validate(p);ck(True,'Valid metadata-only release contract')
  for key,bad in [('schema','BAD'),('publication_readback_verified',False),('publication_commit','x'),('plan_sha256','0'*64),('script_sha256','0'*64),('inventory_path','wrong'),('inventory_sha256','0'*64)]:
   p.write_text(json.dumps(dict(release,**{key:bad})))
   try:prod.validate(p)
   except ValueError:ck(True,'Release refusal '+key)
   else:raise AssertionError('Invalid release accepted '+key)
 for p,h in plan['source_hashes'].items():ck(sha(ROOT/p)==h,'Frozen source unchanged '+p)
 report=dict(status='PASS_COMPACT_PROSPECTIVE_C015_AUDIT',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),checks_passed=count,synthetic_scalar_values_compared=scalars,maximum_synthetic_absolute_difference=maxerr,plan_sha256=sha(A/'PLAN.json'),analysis_script_sha256=sha(code),independent_math_sha256=sha(OUT/'independent_math.py'),audit_script_sha256=sha(Path(__file__)),actual_audit_script_sha256=sha(OUT/'audit_actual.py'),source_hashes_verified=len(plan['source_hashes']),observational_arrays_read=0,network_requests=0,production_import_scope='Synthetic function harness only; independent math imports no production code; actual audit imports no production functions.',scope=['Exact common 3869.915 Å barycentric anchor and fixed 0095 May 2022 topocentric BERV anchor; native-to-bary transform unchanged.','601-point grid; 51 core / 550 broad points and exact 41 / 440 minimum common supports.','Pooled signed-flank median with 20 finite samples required separately per flank; no fitted background, shift or width.','Raw-only missing-coverage and nonpositive-reference outcomes remain explicit; raw Pearson and normalized RMS are separately gated.','Header-before-array source structure, exact 16 profiles / 32 comparisons, inventory/release/source bindings.','Fresh all-72-order header scan selects only order 3 with geometric full-window and both-flank coverage in both frames. Finite flux/reference support awaits release; the original four mapping diagnostics remain all true without changed registration.','One record, one native order/raw panel and one May 2022 discovery reference in the exact HD114386 cohort. The original core equals the fixed singleton core. Prior 0095 epoch/raw evidence and completed blue normalization contexts already used the observations. C016 and same-target normalization windows are disjoint; numerical overlaps on older targets share no source pixels. No blind or independent validation claim.'],inherited_zero_variance_guard='The previously corrected exact zero-range guard is preserved; constant noninteger profiles cannot acquire a Pearson value from rounding-scale standard deviations.',limitations=['This is source/synthetic preflight only; actual input/profile arithmetic awaits root release and completed run.','No physical-origin assignment, independent detection, calibrated uncertainty or classification change follows.'])
 with (OUT/'PROSPECTIVE_AUDIT.json').open('x')as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
