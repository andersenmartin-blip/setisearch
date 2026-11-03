"""Compact C009 source and analytic synthetic preflight; no observed arrays."""
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
 spec=importlib.util.spec_from_file_location('c009_synthetic_only',code);prod=importlib.util.module_from_spec(spec);spec.loader.exec_module(prod)
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

 # Scientific estimator functions must remain identical to completed C008.
 old_tree=ast.parse((ROOT/'work_harps_20261102_c008_context/analysis/compare_group.py').read_text())
 for name in ['sampling_parameters','profile','comparison']:
  old=next(n for n in old_tree.body if isinstance(n,ast.FunctionDef)and n.name==name)
  new=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==name)
  ck(ast.dump(old)==ast.dump(new),'Unchanged C008 estimator '+name)
 inventory=read(ROOT/plan['inventory_path']);handoff=read(ROOT/'work_harps_20261102_c008_context/NEXT_ACTION.json')
 event_centers={r['candidate_id']:float(r['center_bary_air_angstrom'])for r in handoff['existing_context']}
 expected_events={'V2E2-0050':'ADP.2023-03-23T01:02:04.831'}
 references=list(dict.fromkeys(expected_events.values()))
 anchor=next(r for r in inventory['merged_spectra'] if r['dp_id']==references[0])
 ck(references[0]=='ADP.2023-03-23T01:02:04.831' and ref.ANCHOR_BERV==anchor['berv_km_s']==3.26509772194068 and plan['anchor_dp_id']==references[0] and plan['anchor_berv_km_s']==ref.ANCHOR_BERV,'First discovery March 2023 anchor independently matches exact metadata')
 ck(plan['events']==expected_events and prod.EVENTS==expected_events,'Preserve singleton C009 event identity')
 ck(prod.REFERENCES==references and len(references)==1,'Exactly one March 2023 discovery reference')
 ck([r['dp_id']for r in inventory['native_products']]==references,'One unique native exposure')
 ck(ref.CB==event_centers['V2E2-0050'] and sum(ref.CORE)==51 and sum(ref.BROAD)==550,'Metadata center and complete original core')
 for center in event_centers.values():ck(ref.CB-.25<=center-.25+1e-11 and ref.CB+.25>=center+.25-1e-11,'Original event core equals fixed context core')
 chosen=[]
 for item in inventory['native_products']:
  berv=item['primary_header']['ESO DRS BERV']
  candidates=[event for event,dp in expected_events.items()if dp==item['dp_id']]
  ck(item['covering_orders']==[70],'Fresh covering scope selects only native order 70')
  for order in item['covering_orders']:
   c=item['orders'][str(order)]['wavelength_coefficients_ascending'];lo=c[0];hi=math.fsum(v*4095**i for i,v in enumerate(c))
   for event in candidates:ck(lo<event_centers[event]/(1+berv/ref.C)<hi,'Exact event header coverage '+event+'/order '+str(order))
   chosen.append((item['dp_id'],order))
 ck(len(chosen)==1 and inventory['excluded_native_orders']==[],'Exact one selected/no metadata-excluded orders')
 ck([(r['dp_id'],r['order'])for r in plan['included_native_order_pairs']]==chosen and plan['excluded_native_order_pairs']==[],'Deduplicated planned native source slots')
 ck(len(inventory['saved_native_raw_cutouts'])==1 and {r['event']for r in inventory['saved_native_raw_cutouts']}==set(expected_events) and {r['order']for r in inventory['saved_native_raw_cutouts']}=={70},'Keep the original historical raw-order context')
 ck(7*1*2*2+1*2*2==32 and 1*2*2==4,'32 comparison slots including four self-pairs')
 ck(plan['slots']['all_profiles']==16 and plan['slots']['all_comparisons']==32 and plan['slots']['identical_product_self_comparisons']==4 and plan['slots']['expected_bounded_input_windows']==8,'Declared plan counts match unique products')
 ck(plan['comparisons']['minimum_common_core']==41 and plan['comparisons']['minimum_common_broad']==440,'Plan common-support gates match grid geometry')
 dependency=handoff['wavelength_dependency']
 ck(dependency['overlaps_completed_or_current_C001_through_C008_bounded_windows'] is False,'Wavelength separation from completed windows retained without independent-observation claim')
 ck(dependency['C009_original_core_bary_air_angstrom']==[ref.CB-.25,ref.CB+.25] and dependency['proposed_C009_window_bary_air_angstrom']==[ref.CB-3,ref.CB+3],'Original core and proposed context bounds match metadata handoff')
 mapping={r['order']:r for r in inventory['mapping_records']}
 keys=['original_grid_mapping_usable','original_local_mapping_usable','original_baseline_mapping_verified','final_reference_mapping_supported']
 ck(len(mapping)==len(inventory['mapping_records'])==1 and {r['event']for r in mapping.values()}==set(expected_events),'Historical order 70 mapping history retained')
 ck([mapping[70][k]for k in keys]==[True,True,True,True] and mapping[70]['registration_changed'] is False,'Global/local/baseline/five-window mapping stages remain unchanged')
 history=inventory['historical_raw_review_records']
 ck(len(history['primary'])==len(history['secondary'])==len(history['adopted'])==len(history['comparison'])==1,'One complete historical review chain')
 ck(history['primary'][0]['code']=='A' and history['secondary'][0]['code']=='A' and history['adopted'][0]['code']=='U','Historical A/A votes remain distinct from adopted U')
 ck(history['comparison'][0]['primary']=='A' and history['comparison'][0]['secondary']=='A' and history['comparison'][0]['adopted']=='U' and 'artifact/spectral blend' in history['adopted'][0]['evidence'],'Preserve root-adopted possible artifact/spectral blend qualification')
 # Independently rescan all 72 order polynomials from the exact native primary header.
 native=inventory['native_products'][0];header=fits.getheader(ROOT/native['file']['path'],0)
 degree=header['ESO DRS CAL TH DEG LL'];scan=inventory['all_order_header_scan']
 ck(len(scan)==72 and [r['order']for r in scan]==list(range(72)),'Fresh all-order scan includes each native order once')
 independently_selected=[]
 for row in scan:
  order=row['order'];coeff=[header['ESO DRS CAL TH COEFF LL'+str(order*(degree+1)+i)]for i in range(degree+1)]
  lo=coeff[0];hi=math.fsum(c*4095**i for i,c in enumerate(coeff))
  covered=lo<=ref.CT<=hi
  ck(np.allclose([lo,hi],row['header_endpoint_topocentric_air_angstrom'],rtol=0,atol=1e-9) and row['covers_any_original_event_center']==row['selected_for_profile']==covered,'Independent header covering-order decision '+str(order))
  if covered:independently_selected.append(order)
 ck(independently_selected==[70],'Fresh native header independently yields only order 70')
 native_coeff=native['orders']['70']['wavelength_coefficients_ascending'];start=native_coeff[0];end=math.fsum(c*4095**i for i,c in enumerate(native_coeff))
 for lo,hi in [(start*(1+ref.ANCHOR_BERV/ref.C)-ref.CB,end*(1+ref.ANCHOR_BERV/ref.C)-ref.CB),(start-ref.CT,end-ref.CT)]:
  ck(lo<-3 and hi>3 and sum(lo<=x<=hi for x in ref.X)==601,'Header order 70 covers complete fixed core/window/flanks geometrically')
 for berv in [30.3750612537025,-29.2347518620376]:
  center,scale=prod.sampling_parameters(berv,'topocentric')
  ck(center==ref.CT and abs((center+3)*scale/(1+berv/ref.C)-(ref.CT+3))<1e-12,'Both BERV extremes preserve common topocentric frame')
 wave=np.linspace(ref.CB-4,ref.CB+4,1601);x=wave-ref.CB
 base=20+.3*np.sin(8*x)+3*np.exp(-.5*(x/.07)**2)
 fixtures=[('positive',np.ones(len(wave),bool),base),('gap_and_nan',~((x>.10)&(x<.20)),base.copy()),('missing_left',x>-.8,base),('missing_right',x<.5,base),('nonpositive',np.ones(len(wave),bool),-base)]
 fixtures[1][2][35]=np.nan
 for label,mask,flux in fixtures:
  w=wave[mask];f=flux[mask];e=np.full(len(w),np.nan);spacing=float(np.median(np.diff(w)))
  for frame in ['barycentric','topocentric']:
   arrays,metric=prod.profile(w,f,e,-29.2347518620376,frame,spacing);wanted,wmetric=ref.profile(w,f,e,-29.2347518620376,frame,spacing)
   ck(same(arrays,wanted)and same(metric,wmetric),'Independent profile '+label+'/'+frame)
   for region,pmask,rmask in [('core',prod.CORE,ref.CORE),('broad',prod.BROAD,ref.BROAD)]:
    ck(same(prod.comparison(arrays,arrays,pmask),ref.comparison(wanted,wanted,rmask)),'Independent comparison '+label+'/'+frame+'/'+region)
   if label=='missing_left':ck(metric['normalization_status']=='RAW_ONLY'and'MISSING_LEFT_FLANK_COVERAGE'in metric['normalization_reasons'],'Coverage failure retained independently of sign')
   if label=='missing_right':ck(metric['normalization_status']=='RAW_ONLY'and'MISSING_RIGHT_FLANK_COVERAGE'in metric['normalization_reasons'],'Right coverage failure retained independently of sign')
   if label=='nonpositive':ck('NONPOSITIVE_FLANK_REFERENCE'in metric['normalization_reasons'],'Negative reference not divided by absolute value')
   if frame=='topocentric':ck(np.allclose(arrays['requested_bary_wave']/(1+-29.2347518620376/ref.C),ref.CT+np.array(ref.X),rtol=0,atol=1e-12),'Native fixed topocentric request')
 # Header-derived order-70 coordinates with analytic synthetic flux only.
 synthetic_native=np.array([math.fsum(c*i**k for k,c in enumerate(native_coeff)) for i in range(4096)])*(1+ref.ANCHOR_BERV/ref.C)
 synthetic_flux=20+.3*np.sin(8*(synthetic_native-ref.CB))
 for frame in ['barycentric','topocentric']:
  spacing=float(np.median(np.diff(synthetic_native)));error=np.full(len(synthetic_native),np.nan)
  arrays,metric=prod.profile(synthetic_native,synthetic_flux,error,ref.ANCHOR_BERV,frame,spacing)
  wanted,wmetric=ref.profile(synthetic_native,synthetic_flux,error,ref.ANCHOR_BERV,frame,spacing)
  ck(same(arrays,wanted) and same(metric,wmetric),'Independent header-derived synthetic order 70 '+frame)
  ck(metric['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE' and metric['normalization_reasons']==[] and metric['left_flank_finite_samples']>=20 and metric['right_flank_finite_samples']>=20,'Synthetic positive order 70 reference has both fixed flanks '+frame)
  core=prod.comparison(arrays,arrays,prod.CORE);broad=prod.comparison(arrays,arrays,prod.BROAD)
  ck(core['common_finite_raw_samples']==51 and broad['common_finite_raw_samples']==550 and core['raw_pearson'] is not None and broad['raw_pearson'] is not None,'Synthetic order 70 complete core/broad support '+frame)
  ck(core['normalized_rms']==0 and broad['normalized_rms']==0,'Synthetic order 70 normalized self RMS exactly zero '+frame)
 # Finite flank sample count is a separate gate from geometric availability.
 for n in [19,20]:
  flux=base.copy();side_positions=np.flatnonzero((x>=-3)&(x<=-1.5));flux[side_positions[n:]]=np.nan
  error=np.resize(np.array([np.nan,-1.,0.,1.]),len(wave))
  arrays,metric=prod.profile(wave,flux,error,ref.ANCHOR_BERV,'barycentric',float(np.median(np.diff(wave))))
  wanted,wmetric=ref.profile(wave,flux,error,ref.ANCHOR_BERV,'barycentric',float(np.median(np.diff(wave))))
  ck(same(arrays,wanted) and same(metric,wmetric),'Independent finite-flank boundary '+str(n))
  ck(metric['left_flank_finite_samples']==n and metric['normalization_status']==('RAW_ONLY'if n==19 else'USABLE_POSITIVE_FLANK_REFERENCE'),'Exactly 20 finite samples needed on each flank')
 for mask,rmask in [(prod.CORE,ref.CORE),(prod.BROAD,ref.BROAD)]:
  constant={'signed_raw_flux':np.full(601,.1),'normalized_flux':np.full(601,.1)}
  ck(prod.comparison(constant,constant,mask)['raw_pearson_block_reason']=='ZERO_RAW_VARIANCE','Exact constant noninteger zero-range guard')
  nominal=int(mask.sum());minimum=math.ceil(.8*nominal)
  for n in [minimum-1,minimum]:
   z=np.full(601,np.nan);positions=np.flatnonzero(mask)[:n];z[positions]=np.arange(n,dtype=float)
   a={'signed_raw_flux':z,'normalized_flux':z.copy()}
   ck(same(prod.comparison(a,a,mask),ref.comparison(a,a,rmask)),'80percent common-support boundary')
 with tempfile.TemporaryDirectory(prefix='release_fixture_',dir=OUT)as td:
  p=Path(td)/'release.json';release=dict(schema='HARPS_C009_GROUP_RELEASE_V1',publication_readback_verified=True,publication_commit='a'*40,plan_sha256=sha(A/'PLAN.json'),script_sha256=sha(code),inventory_path=plan['inventory_path'],inventory_sha256=plan['source_hashes'][plan['inventory_path']]);p.write_text(json.dumps(release));prod.validate(p);ck(True,'Valid metadata-only release contract')
  for key,bad in [('schema','BAD'),('publication_readback_verified',False),('publication_commit','x'),('plan_sha256','0'*64),('script_sha256','0'*64),('inventory_path','wrong'),('inventory_sha256','0'*64)]:
   p.write_text(json.dumps(dict(release,**{key:bad})))
   try:prod.validate(p)
   except ValueError:ck(True,'Release refusal '+key)
   else:raise AssertionError('Invalid release accepted '+key)
 for p,h in plan['source_hashes'].items():ck(sha(ROOT/p)==h,'Frozen source unchanged '+p)
 report=dict(status='PASS_COMPACT_PROSPECTIVE_C009_AUDIT',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),checks_passed=count,synthetic_scalar_values_compared=scalars,maximum_synthetic_absolute_difference=maxerr,plan_sha256=sha(A/'PLAN.json'),analysis_script_sha256=sha(code),independent_math_sha256=sha(OUT/'independent_math.py'),audit_script_sha256=sha(Path(__file__)),source_hashes_verified=len(plan['source_hashes']),observational_arrays_read=0,network_requests=0,production_import_scope='Synthetic function harness only; independent math imports no production code; actual audit imports no production functions.',scope=['Exact common 6802.02 Å barycentric anchor and fixed 0050 March 2023 topocentric BERV anchor; native-to-bary transform unchanged.','601-point grid; 51 core / 550 broad points and exact 41 / 440 minimum common supports.','Pooled signed-flank median with 20 finite samples required separately per flank; no fitted background, shift or width.','Raw-only missing-coverage and nonpositive-reference outcomes remain explicit; raw Pearson and normalized RMS are separately gated.','Header-before-array source structure, exact 16 profiles / 32 comparisons, inventory/release/source bindings.','Fresh all-72-order header scan selects only order 70, with geometric full-window coverage in both frames; finite flux/reference support remains to be measured after release. All historical mapping stages retained.','One record, one native order/raw panel and one March 2023 discovery reference. C009 window is disjoint from completed C001–C008 bounded contexts, but prior epoch/raw evidence and shared observing products remain. No blind or independent validation claim.'],inherited_zero_variance_guard='The previously corrected exact zero-range guard is preserved; constant noninteger profiles cannot acquire a Pearson value from rounding-scale standard deviations.',limitations=['This is source/synthetic preflight only; actual input/profile arithmetic awaits root release and completed run.','No physical-origin assignment, independent detection, calibrated uncertainty or classification change follows.'])
 with (OUT/'PROSPECTIVE_AUDIT.json').open('x')as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
