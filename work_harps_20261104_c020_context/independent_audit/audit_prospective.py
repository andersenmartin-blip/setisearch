"""Source/synthetic-only cross-check against separate scalar arithmetic."""
from pathlib import Path
import ast, datetime, hashlib, importlib.util, json
import numpy as np
import independent_math as ref
HERE=Path(__file__).resolve().parent
A=HERE.parent/'analysis'
ROOT=HERE.parents[1]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
spec=importlib.util.spec_from_file_location('c020_production_for_synthetic_only',A/'compare_group.py')
prod=importlib.util.module_from_spec(spec);spec.loader.exec_module(prod)
checks=[];scalars=0
def ck(v,label):
    if not v: raise AssertionError(label)
    checks.append(label)
def compare(a,b,label):
    global scalars
    if isinstance(b,dict):
        ck(set(a)==set(b),label+' keys')
        for k in b: compare(a[k],b[k],label+'/'+k)
    elif isinstance(b,(str,bool)) or b is None or isinstance(b,list) and (not b or isinstance(b[0],str)):
        ck(a==b,label)
    else:
        aa=np.asarray(a);bb=np.asarray(b);scalars+=aa.size
        ck(aa.shape==bb.shape and np.allclose(aa,bb,rtol=3e-10,atol=3e-8,equal_nan=True),label)

def main():
    plan=read(A/'PLAN.json'); inv=read(ROOT/plan['inventory_path'])
    ck(prod.CB==ref.CB==4303.13 and prod.ANCHOR_BERV==ref.ANCHOR_BERV==-17.1985506565257,'Independent exact center/anchor constants')
    ck(prod.COVERING_ORDERS=={'ADP.2023-05-16T01:01:18.574':[19]},'Sole own covering order19')
    def functions(p): return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(p.read_text()).body if isinstance(n,ast.FunctionDef)}
    current=functions(A/'compare_group.py');previous=functions(ROOT/'work_harps_20261103_c015_context/analysis/compare_group.py')
    for name in ['sampling_parameters','profile','comparison']: ck(current[name]==previous[name],'Unchanged established numerical helper '+name)
    wavelength=prod.CB+np.arange(-700,701)/100
    flux=200+15*np.sin(np.arange(len(wavelength))*.1)
    noise=np.full(len(wavelength),np.nan)
    cases=[('positive',wavelength,flux,noise),('negative',wavelength,-flux,noise),('zero',wavelength,np.zeros(len(flux)),noise),('missing_right',wavelength[:850],flux[:850],noise[:850])]
    missing=flux.copy();missing[(wavelength-prod.CB>=1.5)&(wavelength-prod.CB<=3)]=np.nan
    cases.append(('nonfinite_right',wavelength,missing,noise))
    for name,w,f,e in cases:
        for berv in [-29.0643174950811,-17.1985506565257,30.0089342598494]:
            for frame in ['barycentric','topocentric']:
                a,ma=prod.profile(w,f,e,berv,frame,.01);b,mb=ref.profile(w,f,e,berv,frame,.01)
                compare(a,b,name+'/'+str(berv)+'/'+frame+'/arrays')
                compare(ma,mb,name+'/'+str(berv)+'/'+frame+'/metrics')
                for region,mask in [('core',ref.CORE),('broad',ref.BROAD)]: compare(prod.comparison(a,a,np.array(mask)),ref.comparison(b,b,mask),name+'/'+frame+'/'+region+'/self')
    ck(len(inv['all_order_header_scan'])==72 and len(inv['saved_native_raw_cutouts'])==1,'Complete header and saved-panel scope')
    ck([r['dp_id'] for r in inv['merged_spectra']]==plan['merged_dp_ids'] and len(plan['merged_dp_ids'])==7,'All own seven epochs retained')
    mapping={r['order']:r for r in inv['mapping_records']}
    keys=['original_grid_mapping_usable','original_local_mapping_usable','original_baseline_mapping_verified','final_reference_mapping_supported']
    ck([mapping[19][k] for k in keys]==[True,True,True,True],'Own order19 all-true historical mapping remains separate from physical origin')
    ck(read(HERE.parent/'scientific_review/NEXT_GROUP_METADATA.json')['selected_before_current_observed_values'] is True,'Next C028 route selected before C020 observed values')
    report={'status':'PASS_COMPACT_PROSPECTIVE_C020_AUDIT','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks_passed':len(checks),'synthetic_scalars_compared':scalars,'observational_arrays_read':0,'plan_sha256':sha(A/'PLAN.json'),'analysis_script_sha256':sha(A/'compare_group.py'),'independent_math_sha256':sha(HERE/'independent_math.py'),'audit_script_sha256':sha(Path(__file__)),'actual_audit_script_sha256':sha(HERE/'audit_actual.py'),'production_functions_used_for_observed_reconstruction':False,'reviewer_scope':'Same assistant, separate scalar implementation and fresh process; no separate-agent or human review.'}
    (HERE/'PROSPECTIVE_AUDIT.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__': main()
