"""Compact C022 source and analytic synthetic preflight; no observed arrays."""
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
 spec=importlib.util.spec_from_file_location('c022_synthetic_only',code);prod=importlib.util.module_from_spec(spec);spec.loader.exec_module(prod)
 ck(np.array_equal(prod.X,ref.X)and np.array_equal(prod.CORE,ref.CORE)and np.array_equal(prod.BROAD,ref.BROAD),'Exact 601 / 51 / 550 geometry')
 ck(prod.CB==ref.CB and prod.CT==ref.CT and prod.ANCHOR_BERV==ref.ANCHOR_BERV,'Common fixed group frame anchors')
 tree=ast.parse(code.read_text());headers=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='inspect_headers')
 ck(not any(isinstance(n,ast.Attribute)and n.attr in ['data','section']for n in ast.walk(headers)),'Header inspection has no array access')
 ck('assert len(records)==20 and len(pairs)==96 and len(all_profiles)==20'in code.read_text(),'All 20 profile / 96 comparison slots asserted')
 ck('NATIVE_EXTRACTED_UNIT_UNSPECIFIED'in code.read_text(),'Native unit not silently equated to ADU')
 for path,label in [(OUT/'audit_actual.py','Actual audit'),(OUT/'independent_math.py','Independent scalar math')]:
  imports=[n for n in ast.walk(ast.parse(path.read_text()))if isinstance(n,(ast.Import,ast.ImportFrom))]
  names=[n.module or ''for n in imports if isinstance(n,ast.ImportFrom)]+[a.name for n in imports if isinstance(n,ast.Import)for a in n.names]
  ck(not any('compare_group'in n or 'plot_group'in n or 'importlib'in n for n in names),label+' imports no production functions')
 old_tree=ast.parse((ROOT/'work_harps_20261103_c021_context/analysis/compare_group.py').read_text())
 for name in ['sampling_parameters','profile','comparison']:
  old=next(n for n in old_tree.body if isinstance(n,ast.FunctionDef)and n.name==name);new=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==name)
  ck(ast.dump(old)==ast.dump(new),'Unchanged C021 estimator '+name)
 inventory=read(ROOT/plan['inventory_path']);handoff=read(ROOT/'work_harps_20261103_c021_context/NEXT_ACTION.json')
 expected_events={'V2E2-0117': 'ADP.2022-01-22T01:09:14.958', 'V2E2-0127': 'ADP.2022-05-06T01:04:00.123', 'V2E2-0131': 'ADP.2023-01-17T01:07:48.581'}
 references=list(expected_events.values());event_centers={r['candidate_id']:float(r['center_bary_air_angstrom'])for r in handoff['existing_context']};epochs=handoff['existing_cohort_epochs']
 ck(inventory['target']=='HD114783'and [r['dp_id']for r in inventory['merged_spectra']]==[r['dp_id']for r in epochs],'Exact distinct HD114783 seven-product cohort')
 ck(len(epochs)==7 and math.isclose(max(r['berv_km_s']for r in epochs)-min(r['berv_km_s']for r in epochs),59.073251754930496,rel_tol=0,abs_tol=1e-12),'Target-specific BERV span retained')
 for actual,expected in zip(inventory['merged_spectra'],epochs):ck(actual['date_obs']==expected['date_obs']and actual['berv_km_s']==expected['berv_km_s'],'Exact target epoch date and BERV '+actual['dp_id'])
 anchor=next(r for r in inventory['merged_spectra']if r['dp_id']==references[0])
 ck(ref.ANCHOR_BERV==anchor['berv_km_s']==29.658729150824 and plan['anchor_dp_id']==references[0]and plan['anchor_berv_km_s']==ref.ANCHOR_BERV,'First queue January 2022 discovery anchors fixed group topocentric frame')
 ck(plan['events']==prod.EVENTS==expected_events and prod.REFERENCES==references,'All three event and fixed-reference identities retained')
 ck([r['dp_id']for r in inventory['native_products']]==references and len(set(references))==3,'Three distinct native discovery exposures')
 ck(set(event_centers)==set(expected_events)and [event_centers[e]for e in expected_events]==[4312.245, 4312.245, 4312.237499999999],'Every original catalog center retained exactly')
 ck(ref.CB==(min(event_centers.values())+max(event_centers.values()))/2==4312.241249999999 and ref.CT==4311.814678415948,'Group midpoint and January wavelength-specific anchor exactly fixed')
 coordinate=inventory['coordinate_anchor']
 ck(coordinate['discovery_dp_id']==references[0]and coordinate['discovery_berv_km_s']==ref.ANCHOR_BERV and coordinate['center_barycentric_air_angstrom']==ref.CB and coordinate['fixed_topocentric_air_angstrom']==ref.CT and coordinate['original_member_centers_barycentric_air_angstrom']==event_centers,'Fresh inventory separates common group anchor from all original member centers')
 markers={r['event']:r for r in plan['event_markers']};bervs={r['dp_id']:r['berv_km_s']for r in epochs}
 ck(set(markers)==set(expected_events)and all(markers[e]['center_bary_air_angstrom']==c and markers[e]['barycentric_offset_angstrom']==c-ref.CB and markers[e]['discovery_topocentric_offset_angstrom']==c/(1+bervs[expected_events[e]]/ref.C)-ref.CT for e,c in event_centers.items()),'Three event markers preserve each original center and its own discovery BERV')
 ck(sum(ref.CORE)==51 and sum(ref.BROAD)==550 and max(abs(c-ref.CB)for c in event_centers.values())<.003750000002,'Fixed group core differs from original member cores by at most 0.00375 Angstrom')
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
 ck(len(chosen)==3 and inventory['excluded_native_orders']==[],'Three selected native contexts and no metadata exclusions')
 ck([(r['dp_id'],r['order'])for r in plan['included_native_order_pairs']]==chosen and plan['excluded_native_order_pairs']==[],'Deduplicated planned native source slots')
 ck(len(inventory['saved_native_raw_cutouts'])==3 and {(r['event'],r['order'])for r in inventory['saved_native_raw_cutouts']}=={(e,19)for e in expected_events},'All three historical raw-order contexts retained')
 ck(7*3*2*2+3*2*2==96 and 3*2*2==12,'96 comparison slots including twelve self-pairs')
 ck(plan['slots']['all_profiles']==20 and plan['slots']['all_comparisons']==96 and plan['slots']['identical_product_self_comparisons']==12 and plan['slots']['expected_bounded_input_windows']==10,'Declared plan counts match joint unique products')
 ck(plan['comparisons']['minimum_common_core']==41 and plan['comparisons']['minimum_common_broad']==440,'Plan common-support gates match grid geometry')
 dependency=handoff['wavelength_dependency']
 ck(dependency['same_observing_products_as_C021']is True and dependency['shared_bounded_spectral_source_pixels_with_C021']is True,'Direct C021 shared observations and bounded source pixels remain explicit')
 ck(all(r['prior_target']!='HD114783'and r['same_observing_products']is False and r['shared_source_pixels']is False for r in dependency['numeric_wavelength_overlaps_on_other_target']),'Other-target numerical overlaps do not share observations or source pixels')
 ck(dependency['proposed_group_core_bary_air_angstrom']==[ref.CB-.25,ref.CB+.25]and dependency['proposed_group_window_bary_air_angstrom']==[ref.CB-3,ref.CB+3],'Fixed common group core and window match prior handoff')
 prior=ROOT/'work_harps_20261103_c021_context';prior_plan=read(prior/'analysis/PLAN.json');prior_inv=read(ROOT/prior_plan['inventory_path']);prior_cb=prior_plan['group_center_bary_air_angstrom']
 required_prior=[prior/'analysis/PLAN.json',prior/'inputs/INPUT_INVENTORY.json',prior/'analysis/results/BOUNDED_INPUT_INDEX.json']
 ck(all(str(p.relative_to(ROOT))in plan['source_hashes']for p in required_prior),'Prior C021 plan, inventory and bounded index are frozen source bindings')
 overlap=[max(ref.CB-3,prior_cb-3),min(ref.CB+3,prior_cb+3)]
 ck(dependency['numeric_and_same_source_overlap_bary_air_angstrom']==overlap and math.isclose(overlap[1]-overlap[0],3.585000000000946,rel_tol=0,abs_tol=1e-12),'Independent direct C021 overlap geometry')
 ck(prior_cb+1.5<=ref.CB-.25<=ref.CB+.25<=prior_cb+3 and ref.CB-3<=prior_cb-.25<=prior_cb+.25<=ref.CB-1.5 and prior_cb+.25<ref.CB-.25,'Both distinct common cores lie inside opposite fixed reference flanks')
 prior_merged={r['dp_id']:r['file']['sha256']for r in prior_inv['merged_spectra']};prior_native={r['dp_id']:r for r in prior_inv['native_products']}
 ck(prior_inv['target']==inventory['target']=='HD114783'and {r['dp_id']:r['file']['sha256']for r in inventory['merged_spectra']}==prior_merged,'All seven merged source hashes prove direct observation reuse')
 ck(all(r['file']['sha256']==prior_native[r['dp_id']]['file']['sha256']and 19 in prior_native[r['dp_id']]['covering_orders']for r in inventory['native_products']),'All three native source hashes/order identities prove direct extraction reuse')
 mapping={(r['event'],r['dp_id'],r['order']):r for r in inventory['mapping_records']};keys=['original_grid_mapping_usable','original_local_mapping_usable','original_baseline_mapping_verified','final_reference_mapping_supported']
 expected_mapping_flags={'V2E2-0117': [True, False, False, True], 'V2E2-0127': [True, False, False, True], 'V2E2-0131': [True, False, False, True]}
 ck(len(mapping)==3 and set(mapping)=={(e,dp,19)for e,dp in expected_events.items()}and all([r[k]for k in keys]==expected_mapping_flags[r['event']]and r['registration_changed']is False for r in mapping.values()),'All three original local/baseline failures remain false alongside true global/later support')
 history=inventory['historical_raw_review_records']
 batch=history['batch03_original'];batch_events=set(expected_events)-{'V2E2-0131'}
 ck(all(len(batch[k])==2 and {r['review_id']for r in batch[k]}==batch_events for k in ['primary','secondary','adopted','comparison']),'Two complete original batch03 review chains retained')
 ck(all(r['code']=='U'for stage in ['primary','secondary','adopted']for r in batch[stage])and all(r['primary']==r['secondary']==r['adopted']=='U'for r in batch['comparison']),'Two original batch03 primary/secondary/adopted U chains remain exact')
 legacy=history['separate_raw_followup_0131']
 ck(legacy['original_primary']['primary_code']=='I'and legacy['original_secondary_source_record'][0]=='M'and legacy['original_review_agreement']['second_code_normalized']=='I'and legacy['original_adopted_baseline']['baseline_code']=='I','0131 original I/M-normalized-I/baseline-I stages remain separate')
 ck(legacy['current_adopted_record']['current_code']==legacy['later_primary_source_record'][0]==legacy['later_secondary_source_record'][0]==legacy['later_disposition_record']['proposed_code']=='U','0131 later separate U/U/current-U stages retained without changing original stages')
 ck(legacy['later_disposition_record']['coordinates_changed']=='False'and legacy['later_disposition_record']['original_native_and_raw_pixels_preserved']=='True','0131 historical unchanged-coordinate and pixel-preservation declarations retained')
 declarations=legacy['later_preservation_declarations']
 ck(declarations['coordinates_changed']is False and all(declarations[k]is True for k in ['original_raw_pixels_and_native_samples_preserved','baseline_files_unchanged','original_catalogs_unchanged'])and legacy['later_wider_containers_are_distinct_from_original_baseline_panels']is True and legacy['new_pixel_equality_test_performed']is False,'Distinct later containers and original preservation declarations do not become a new pixel equality claim')
 later=legacy['later_mapping_records'];ck(len(later)==1 and {r['order']for r in later}=={19}and all(r['reference_mapping_supported']is True for r in later),'0131 completed later mapping support retained for the unchanged order19')
 for row in later:
  original=mapping[('V2E2-0131',expected_events['V2E2-0131'],row['order'])]
  ck(all(row[k]==original[k]for k in ['native_pixel','raw_row','raw_column']),'0131 later metadata retains original native/raw coordinates order '+str(row['order']))
 ck(len(history['current_adopted'])==3 and {r['review_id']for r in history['current_adopted']}==set(expected_events)and all(r['current_code']=='U'for r in history['current_adopted']),'All three current adopted U labels retained')
 ck(history['per_event_history']==handoff['historical_review_disagreement']['per_event_history'],'Canonical per-event staged history matches prior frozen handoff')
 ck(all(('raw_followup/NATIVE_MAPPING.json'if r['event']=='V2E2-0131'else'raw_followup_batch03/NATIVE_MAPPING.json')in r['original_mapping_source']for r in mapping.values()),'Original legacy versus batch03 mapping provenance retained')
 ck(all(r['container_stage']=='original baseline panel'and r['later_wider_container_substituted']is False for r in inventory['saved_native_raw_cutouts']if r['event']=='V2E2-0131'),'0131 original baseline panel containers retained without wider-container substitution')
 scan=inventory['all_order_header_scan'];ck(len(scan)==216,'Three complete all-72-order header scans')
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
  for lo,hi in [(start*(1+berv/ref.C)-ref.CB,end*(1+berv/ref.C)-ref.CB),(start-ref.CT,end-ref.CT)]:ck(lo<-3 and hi>3 and sum(lo<=x<=hi for x in ref.X)==601,'Fresh selected order covers fixed group core/window/flanks geometrically '+dp)
 for berv in [30.0089342598494,-29.0643174950811]:
  center,scale=prod.sampling_parameters(berv,'topocentric')
  ck(center==ref.CT and abs((center+3)*scale/(1+berv/ref.C)-(ref.CT+3))<1e-12,'Both BERV extremes preserve common topocentric frame')
 wave=np.linspace(ref.CB-4,ref.CB+4,1601);x=wave-ref.CB
 base=20+.3*np.sin(8*x)+3*np.exp(-.5*(x/.07)**2)
 fixtures=[('positive',np.ones(len(wave),bool),base),('gap_and_nan',~((x>.10)&(x<.20)),base.copy()),('missing_left',x>-.8,base),('missing_right',x<.5,base),('nonpositive',np.ones(len(wave),bool),-base)]
 fixtures[1][2][35]=np.nan
 for label,mask,flux in fixtures:
  w=wave[mask];f=flux[mask];e=np.full(len(w),np.nan);spacing=float(np.median(np.diff(w)))
  for frame in ['barycentric','topocentric']:
   arrays,metric=prod.profile(w,f,e,-29.0643174950811,frame,spacing);wanted,wmetric=ref.profile(w,f,e,-29.0643174950811,frame,spacing)
   ck(same(arrays,wanted)and same(metric,wmetric),'Independent profile '+label+'/'+frame)
   for region,pmask,rmask in [('core',prod.CORE,ref.CORE),('broad',prod.BROAD,ref.BROAD)]:
    ck(same(prod.comparison(arrays,arrays,pmask),ref.comparison(wanted,wanted,rmask)),'Independent comparison '+label+'/'+frame+'/'+region)
   if label=='missing_left':ck(metric['normalization_status']=='RAW_ONLY'and'MISSING_LEFT_FLANK_COVERAGE'in metric['normalization_reasons'],'Coverage failure retained independently of sign')
   if label=='missing_right':ck(metric['normalization_status']=='RAW_ONLY'and'MISSING_RIGHT_FLANK_COVERAGE'in metric['normalization_reasons'],'Right coverage failure retained independently of sign')
   if label=='nonpositive':ck('NONPOSITIVE_FLANK_REFERENCE'in metric['normalization_reasons'],'Negative reference not divided by absolute value')
   if frame=='topocentric':ck(np.allclose(arrays['requested_bary_wave']/(1+-29.0643174950811/ref.C),ref.CT+np.array(ref.X),rtol=0,atol=1e-12),'Native fixed topocentric request')
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
 # Signed pooled medians need not require both individual flanks to be positive.
 signed_wave=np.concatenate([ref.CB+np.linspace(-3,-1.5,300),ref.CB+np.linspace(-.25,.25,101),ref.CB+np.linspace(1.5,3,300)])
 for right_value,expected_reference in [(20.,5.),(5.,-2.5)]:
  signed_flux=np.concatenate([np.full(300,-10.),np.linspace(-2,2,101),np.full(300,right_value)]);error=np.full(len(signed_wave),np.nan);spacing=float(np.median(np.diff(signed_wave)))
  arrays,metric=prod.profile(signed_wave,signed_flux,error,ref.ANCHOR_BERV,'barycentric',spacing);wanted,wmetric=ref.profile(signed_wave,signed_flux,error,ref.ANCHOR_BERV,'barycentric',spacing)
  ck(same(arrays,wanted)and same(metric,wmetric),'Independent signed opposite-flank reference '+str(right_value))
  ck(metric['flank_reference']==expected_reference and metric['left_flank_median']==-10. and metric['right_flank_median']==right_value,'Signed pooled median is neither absolute-valued nor a per-flank positivity rule')
  ck(metric['normalization_status']==('USABLE_POSITIVE_FLANK_REFERENCE'if expected_reference>0 else'RAW_ONLY'),'Signed pooled positivity gate retained')
 negative_mask=x<.5;w=wave[negative_mask];f=-base[negative_mask];error=np.full(len(w),np.nan);spacing=float(np.median(np.diff(w)))
 arrays,metric=prod.profile(w,f,error,ref.ANCHOR_BERV,'barycentric',spacing);wanted,wmetric=ref.profile(w,f,error,ref.ANCHOR_BERV,'barycentric',spacing)
 ck(same(arrays,wanted)and same(metric,wmetric),'Independent negative available flank with missing right coverage')
 ck(metric['normalization_reasons']==['MISSING_RIGHT_FLANK_COVERAGE']and metric['available_flank_median']<0 and metric['flank_reference']is None and np.isnan(arrays['normalized_flux']).all(),'Coverage failure retains negative available flank without normalization or a fabricated nonpositive-reference decision')
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
  p=Path(td)/'release.json';release=dict(schema='HARPS_C022_GROUP_RELEASE_V1',publication_readback_verified=True,publication_commit='a'*40,plan_sha256=sha(A/'PLAN.json'),script_sha256=sha(code),inventory_path=plan['inventory_path'],inventory_sha256=plan['source_hashes'][plan['inventory_path']]);p.write_text(json.dumps(release));prod.validate(p);ck(True,'Valid metadata-only release contract')
  for key,bad in [('schema','BAD'),('publication_readback_verified',False),('publication_commit','x'),('plan_sha256','0'*64),('script_sha256','0'*64),('inventory_path','wrong'),('inventory_sha256','0'*64)]:
   p.write_text(json.dumps(dict(release,**{key:bad})))
   try:prod.validate(p)
   except ValueError:ck(True,'Release refusal '+key)
   else:raise AssertionError('Invalid release accepted '+key)
 for p,h in plan['source_hashes'].items():ck(sha(ROOT/p)==h,'Frozen source unchanged '+p)
 report=dict(status='PASS_COMPACT_PROSPECTIVE_C022_AUDIT',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),checks_passed=count,synthetic_scalar_values_compared=scalars,maximum_synthetic_absolute_difference=maxerr,plan_sha256=sha(A/'PLAN.json'),analysis_script_sha256=sha(code),independent_math_sha256=sha(OUT/'independent_math.py'),audit_script_sha256=sha(Path(__file__)),actual_audit_script_sha256=sha(OUT/'audit_actual.py'),source_hashes_verified=len(plan['source_hashes']),observational_arrays_read=0,network_requests=0,production_import_scope='Synthetic function harness only; independent math imports no production code; actual audit imports no production functions.',scope=['Three exact HD114783 discovery references over seven existing epochs; common midpoint4312.241249999999 and January anchor4311.814678415948. Exact member core edges differ by about0.00375 Angstrom.','Fixed601-point grid,51 common-core/550 surrounding points,41/440 common-support gates and signed pooled reference with20 finite samples per flank. All partial/nonpositive/low outcomes remain explicit.','All20 profiles/96 comparisons/10 bounded inputs/3 original raw panels/12 self rows. Three references yield18 directed nonself rows,15 unordered pairs and3 reciprocal pairs per frame/region.','All216 fresh header rows independently select order19 per product with complete geometric core/context/flank coverage; measured finite flux/reference quality await release.','Every original local/baseline flag remains false with global/later support true. Two original-U batch03 histories stay separate from0131 originalI/M-normalizedI/baselineI thencompletedwider/laterU/U/currentU.','C022 directly reuses3.585000000000946 Angstrom of C021 source pixels. The C022 core lies in the C021 positive reference flank; the C021 core lies in the C022 negative flank. Central evidence was already exposed; no blind or independent-data claim follows. Original raw crop containers remain distinct without a whole-crop equality or independence claim.'],limitations=['Source/synthetic preflight only; actual arrays await root public release and stable completed-run ledger.','No origin, significance, uncertainty calibration, new observing time, classification change or normalization-pipeline replay follows.'])
 with (OUT/'PROSPECTIVE_AUDIT.json').open('x')as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
