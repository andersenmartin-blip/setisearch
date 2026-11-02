"""Compact C007 source and analytic synthetic preflight; no observed arrays."""
import ast,datetime,hashlib,importlib.util,json,math
from pathlib import Path
import tempfile
import numpy as np
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
 spec=importlib.util.spec_from_file_location('c007_synthetic_only',code);prod=importlib.util.module_from_spec(spec);spec.loader.exec_module(prod)
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

 # Scientific estimator functions must remain identical to completed C006.
 old_tree=ast.parse((ROOT/'work_harps_20261102_c006_context/analysis/compare_group.py').read_text())
 for name in ['sampling_parameters','profile','comparison']:
  old=next(n for n in old_tree.body if isinstance(n,ast.FunctionDef)and n.name==name)
  new=next(n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name==name)
  ck(ast.dump(old)==ast.dump(new),'Unchanged C006 estimator '+name)
 inventory=read(ROOT/plan['inventory_path']);handoff=read(ROOT/'work_harps_20261102_c006_context/NEXT_ACTION.json')
 event_centers={r['candidate_id']:float(r['center_bary_air_angstrom'])for r in handoff['existing_context']}
 expected_events={'V2E2-0026':'ADP.2022-01-06T01:08:04.689'}
 references=list(dict.fromkeys(expected_events.values()))
 ck(plan['events']==expected_events and prod.EVENTS==expected_events,'Preserve singleton identity')
 ck(prod.REFERENCES==references and len(references)==1,'Exactly one discovery product reference')
 ck([r['dp_id']for r in inventory['native_products']]==references,'No duplicate native exposure')
 ck(ref.CB==event_centers['V2E2-0026'] and sum(ref.CORE)==51 and sum(ref.BROAD)==550,'Metadata singleton center and complete original core')
 for center in event_centers.values():ck(ref.CB-.25<=center-.25+1e-11 and ref.CB+.25>=center+.25-1e-11,'Original event core equals fixed singleton core')
 chosen=[]
 for item in inventory['native_products']:
  berv=item['primary_header']['ESO DRS BERV']
  candidates=[event for event,dp in expected_events.items()if dp==item['dp_id']]
  order=19;c=item['orders'][str(order)]['wavelength_coefficients_ascending'];lo=c[0];hi=math.fsum(v*4095**i for i,v in enumerate(c))
  for event in candidates:ck(lo<event_centers[event]/(1+berv/ref.C)<hi,'Exact event19 header coverage '+event)
  ck(item['covering_orders']==[19],'Only selected historical order19 per unique product')
  chosen.append((item['dp_id'],order))
 ck(len(chosen)==1 and inventory['excluded_native_orders']==[],'Exact one selected/no metadata-excluded orders')
 ck([(r['dp_id'],r['order'])for r in plan['included_native_order_pairs']]==chosen and plan['excluded_native_order_pairs']==[],'Deduplicated planned native source slots')
 ck(len(inventory['saved_native_raw_cutouts'])==1 and {r['event']for r in inventory['saved_native_raw_cutouts']}==set(expected_events),'Keep singleton historical raw context')
 ck(7*1*2*2+1*2*2==32 and 1*2*2==4,'32 comparison slots including 4 self-pairs')
 ck(plan['slots']['all_profiles']==16 and plan['slots']['all_comparisons']==32 and plan['slots']['identical_product_self_comparisons']==4 and plan['slots']['expected_bounded_input_windows']==8,'Declared plan counts match unique products')
 ck(plan['comparisons']['minimum_common_core']==41 and plan['comparisons']['minimum_common_broad']==440,'Plan common-support gates match grid geometry')
 ck(handoff['wavelength_dependency']['C007_core_entirely_inside_C006_reference_flank'] is True,'Previously visible overlapping C006 core dependency retained')
 ck(len(inventory['mapping_records'])==1 and inventory['mapping_records'][0]['event']=='V2E2-0026' and inventory['mapping_records'][0]['original_local_mapping_usable'] is False and inventory['mapping_records'][0]['original_baseline_mapping_verified'] is False and inventory['mapping_records'][0]['original_grid_mapping_usable'] is True and inventory['mapping_records'][0]['final_reference_mapping_supported'] is True,'All historical mapping stages retained without retrospective promotion')
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
 for mask,rmask in [(prod.CORE,ref.CORE),(prod.BROAD,ref.BROAD)]:
  constant={'signed_raw_flux':np.full(601,.1),'normalized_flux':np.full(601,.1)}
  ck(prod.comparison(constant,constant,mask)['raw_pearson_block_reason']=='ZERO_RAW_VARIANCE','Exact constant noninteger zero-range guard')
  nominal=int(mask.sum());minimum=math.ceil(.8*nominal)
  for n in [minimum-1,minimum]:
   z=np.full(601,np.nan);positions=np.flatnonzero(mask)[:n];z[positions]=np.arange(n,dtype=float)
   a={'signed_raw_flux':z,'normalized_flux':z.copy()}
   ck(same(prod.comparison(a,a,mask),ref.comparison(a,a,rmask)),'80percent common-support boundary')
 with tempfile.TemporaryDirectory(prefix='release_fixture_',dir=OUT)as td:
  p=Path(td)/'release.json';release=dict(schema='HARPS_C007_GROUP_RELEASE_V1',publication_readback_verified=True,publication_commit='a'*40,plan_sha256=sha(A/'PLAN.json'),script_sha256=sha(code),inventory_path=plan['inventory_path'],inventory_sha256=plan['source_hashes'][plan['inventory_path']]);p.write_text(json.dumps(release));prod.validate(p);ck(True,'Valid metadata-only release contract')
  for key,bad in [('schema','BAD'),('publication_readback_verified',False),('publication_commit','x'),('plan_sha256','0'*64),('script_sha256','0'*64),('inventory_path','wrong'),('inventory_sha256','0'*64)]:
   p.write_text(json.dumps(dict(release,**{key:bad})))
   try:prod.validate(p)
   except ValueError:ck(True,'Release refusal '+key)
   else:raise AssertionError('Invalid release accepted '+key)
 for p,h in plan['source_hashes'].items():ck(sha(ROOT/p)==h,'Frozen source unchanged '+p)
 report=dict(status='PASS_COMPACT_PROSPECTIVE_C007_AUDIT',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),checks_passed=count,synthetic_scalar_values_compared=scalars,maximum_synthetic_absolute_difference=maxerr,plan_sha256=sha(A/'PLAN.json'),analysis_script_sha256=sha(code),independent_math_sha256=sha(OUT/'independent_math.py'),audit_script_sha256=sha(Path(__file__)),source_hashes_verified=len(plan['source_hashes']),observational_arrays_read=0,network_requests=0,production_import_scope='Synthetic function harness only; independent math imports no production code; actual audit imports no production functions.',scope=['Exact common 4312.700 Å barycentric anchor and fixed 0026 topocentric BERV anchor; native-to-bary transform unchanged.','601-point grid; 51 core / 550 broad points and exact 41 / 440 minimum common supports.','Pooled signed-flank median with20finite samples required separately per flank; no fitted background, shift or width.','Raw-only missing-coverage and nonpositive-reference outcomes remain explicit; raw Pearson and normalized RMS are separately gated.','Header-before-array source structure, exact 16 profiles / 32 comparisons, inventory/release/source bindings.','Singleton identity and one raw panel, one native product and merged discovery reference. C007 core overlaps already visible C006 values; no blind or independent validation claim.'],inherited_zero_variance_guard='The previously corrected exact zero-range guard is preserved; constant noninteger profiles cannot acquire a Pearson value from rounding-scale standard deviations.',limitations=['This is source/synthetic preflight only; actual input/profile arithmetic awaits root release and completed run.','No physical-origin assignment, independent detection, calibrated uncertainty or classification change follows.'])
 with (OUT/'PROSPECTIVE_AUDIT.json').open('x')as f:json.dump(report,f,indent=2);f.write('\n')
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
