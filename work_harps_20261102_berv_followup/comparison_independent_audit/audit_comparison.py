"""Independent existing-profile and synthetic contract/header audit; no network."""
from pathlib import Path
import copy,csv,datetime,hashlib,importlib.util,io,json,math,shutil,sys,tempfile,zipfile
from unittest.mock import patch
import numpy as np

OUT=Path(__file__).resolve().parent;BASE=OUT.parent;REPO=BASE.parent
P=BASE/'prospective_comparison';E=REPO/'work_harps_20261101/v2/extension02/epoch_followup'
checks=[];scalar_checks=0

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def check(test,label):
    if not bool(test):raise AssertionError(label)
    checks.append(label)
def near(a,b,label,atol=2e-10):
    global scalar_checks
    aa=np.asarray(a,dtype=float);bb=np.asarray(b,dtype=float)
    check(aa.shape==bb.shape and np.allclose(aa,bb,rtol=2e-10,atol=atol,equal_nan=True),label);scalar_checks+=aa.size

def mod(path,name):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def write(path,obj):path.write_text(json.dumps(obj,indent=2)+'\n')

def main():
    start_hashes={'comparison':sha(P/'compare_verified_epochs.py'),'plan':sha(P/'PLAN.json')}
    comp=mod(P/'compare_verified_epochs.py','comparison_under_review')
    method,receipt=comp.verified_original_module();plan=read(P/'PLAN.json');events=read(P/'EVENTS.json')
    ids=['V2E2-0229','V2E2-0231','V2E2-0234','V2E2-0235','V2E2-0236','V2E2-0237','V2E2-0303','V2E2-0305','V2E2-0308','V2E2-0309']
    check([x['candidate_id']for x in events]==ids,'Exact10 frozen event order')
    check(sum(x['target']=='HD122640'for x in events)==6 and sum(x['target']=='HD135204'for x in events)==4,'Target6/4 event split')
    check(len(receipt['restored'])==20,'Exactly20 reference profiles')
    parts=read(E/'PROFILE_ARRAYS_PARTS.json');joined=bytearray()
    for part in parts['parts']:
        body=(E/part['path']).read_bytes();check(len(body)==part['bytes']and hashlib.sha256(body).hexdigest()==part['sha256'],'Archive part '+part['path']);joined.extend(body)
    check(len(joined)==parts['bytes']and hashlib.sha256(joined).hexdigest()==parts['sha256'],'Original multipart archive exact')
    original_rows={(r['candidate_id'],r['frame']):r for r in csv.DictReader((E/'ALL_EPOCH_MEASUREMENTS.csv').open())if r['is_discovery_exposure']=='True'}
    x=np.arange(201,dtype=float)/100-1;core=np.abs(x)<=.250000001;side=np.abs(x)>=.599999999
    with zipfile.ZipFile(io.BytesIO(joined))as archive:
        for event in events:
            for frame,ref in event['discovery_profiles'].items():
                path=P/'inputs'/ref['profile_path'];body=path.read_bytes()
                check(body==archive.read(ref['profile_path'])and sha(path)==ref['profile_sha256'],'Archived reference exact '+event['candidate_id']+frame)
                with np.load(io.BytesIO(body),allow_pickle=False)as data:arr={k:data[k].copy()for k in data.files}
                check(set(arr)=={'offset_air_angstrom','requested_bary_air_angstrom','raw_flux','normalized_flux','linear_background','residual'},'Exact profile arrays '+event['candidate_id']+frame)
                check(all(v.shape==(201,)for v in arr.values()),'201-point reference shapes '+event['candidate_id']+frame)
                near(arr['offset_air_angstrom'],x,'Independent reference offset grid '+event['candidate_id']+frame)
                row=original_rows[event['candidate_id'],frame];center=event['fitted_center_bary_air_angstrom']
                if frame=='topocentric':center/=1+event['discovery_berv_km_s']/299792.458
                scale=1 if frame=='barycentric'else 1+event['discovery_berv_km_s']/299792.458
                near(arr['requested_bary_air_angstrom'],(center+x)*scale,'Inherited frame transformation '+event['candidate_id']+frame,atol=2e-9)
                y=arr['raw_flux']/float(row['normalization_adu']);near(arr['normalized_flux'],y,'Stored normalization '+event['candidate_id']+frame)
                ok=side&np.isfinite(y);a=np.column_stack([np.ones(ok.sum()),x[ok]]);coef=np.linalg.solve(a.T@a,a.T@y[ok]);background=coef[0]+coef[1]*x
                near(arr['linear_background'],background,'Independent sideband fit '+event['candidate_id']+frame)
                near(arr['residual'],y-background,'Independent residual '+event['candidate_id']+frame)
                for label,factor in [('narrow',1),('broad3',3)]:
                    ok=core&np.isfinite(y);g=np.exp(-.5*(x/(center/115000*factor/2.3548200450309493))**2);a=np.column_stack([np.ones(ok.sum()),x[ok],g[ok]])
                    coef=np.linalg.solve(a.T@a,a.T@y[ok]);rms=np.sqrt(np.mean((y[ok]-a@coef)**2))
                    near(coef[2],float(row[label+'_amplitude']),'Independent '+label+' amplitude '+event['candidate_id']+frame)
                    near(rms,float(row[label+'_residual_rms']),'Independent '+label+' RMS '+event['candidate_id']+frame)
                near(np.trapezoid((y-background)[core],x[core]),float(row['core_flux_integral_over_linear_background']),'Independent integral '+event['candidate_id']+frame)
                near(method.corr(arr['residual'],arr['residual']),1,'Self correlation '+event['candidate_id']+frame)
    # Actual inherited numerical boundaries, no new observations.
    v=np.arange(201,dtype=float);mask=np.where(core)[0];few=np.full(201,np.nan);few[mask[:19]]=v[mask[:19]]
    check(method.corr(v,few)is None,'Correlation rejects19 finite common core samples')
    few[mask[19]]=v[mask[19]];near(method.corr(v,few),1,'Correlation accepts20 finite common core samples')
    check(method.corr(v,np.ones(201))is None,'Correlation rejects constant core')
    w=np.linspace(4997,5003,1201);f=np.full_like(w,10.);err=np.full_like(w,np.nan)
    a,m=method.profile(w,f,err,5000,1);check(m['normalization_status']=='USABLE_POSITIVE_MEDIAN'and m['finite_positive_ERR_samples']==0,'Missing ERR remains descriptive unweighted context')
    a,m=method.profile(w,-f,err,5000,1);check(m['normalization_status']=='NONPOSITIVE_OR_MISSING_MEDIAN'and not np.isfinite(a['normalized_flux']).any(),'Nonpositive normalization retained as unusable')
    a,m=method.profile(w,f,err,5100,1);check(m['valid_samples']==0,'No wavelength extrapolation')
    gap=abs(w-5000)>.06;a,m=method.profile(w[gap],f[gap],err[gap],5000,1);check(m['gap_masked_samples']>0,'Inherited gap masking retained')
    # Header-only mocks abort if any .data property is consulted.
    class Hdu:
        def __init__(self,header,data=None):self.header=header;self.value=data
        @property
        def data(self):raise AssertionError('Forbidden array access during header validation')
    class HD(list):
        def __enter__(self):return self
        def __exit__(self,*args):pass
    primary={'ARCFILE':'ADP.2099-01-01T00:00:00.000.fits','INSTRUME':'HARPS','OBJECT':'HD122640','SPECSYS':'BARYCENT','NCOMBINE':1,'SPEC_RES':115000,'ESO INS HEFS ST':False,'ESO DRS BERV':1.,'PROCSOFT':'HARPS_3.8','DATE-OBS':'2099-01-01','MJD-OBS':87703.,'EXPTIME':100.}
    extension={'NAXIS2':1,'TFIELDS':3,'TTYPE1':'WAVE','TTYPE2':'FLUX','TTYPE3':'ERR','TUNIT1':'angstrom','TUNIT2':'adu','TUNIT3':'adu','TUCD1':'em.wl;obs.atmos'}
    item={'status':'COMPLETE','local_path':'synthetic_nonexistent.fits','target':'HD122640','_recorded_header':{'inspection':{'primary_header':copy.deepcopy(primary),'berv_km_s':1.}}}
    def header_result(ph,eh,it=None):
        with patch.object(comp.fits,'open',return_value=HD([Hdu(ph),Hdu(eh)])):return comp.inspect_payload_headers(it or item)
    check(header_result(primary,extension)['status']=='PASS_COMPATIBLE_HEADERS','Compatible header passes without arrays')
    for key,value in [('INSTRUME','OTHER'),('OBJECT','HD135204'),('SPECSYS','TOPOCENT'),('NCOMBINE',True),('NCOMBINE',2),('SPEC_RES',80000),('ESO INS HEFS ST',True),('ESO INS HEFS ST',None),('ESO DRS BERV',True),('ESO DRS BERV',float('nan'))]:
        ph=copy.deepcopy(primary);ph[key]=value;check(header_result(ph,extension)['status'].startswith('BLOCKED'),'Reject header '+key+'='+str(value))
    for key,value in [('NAXIS2',2),('TUNIT1','nm'),('TUNIT2','Jy'),('TUCD1','em.wl'),('TTYPE3','OTHER')]:
        eh=copy.deepcopy(extension);eh[key]=value;check(header_result(primary,eh)['status'].startswith('BLOCKED'),'Reject layout '+key+'='+str(value))
    for name in ['WAVE','wave','']:
        eh=copy.deepcopy(extension);eh.update(TFIELDS=4,TTYPE4=name,TUNIT4='angstrom',TUCD4='em.wl;obs.atmos')
        check(header_result(primary,eh)['status'].startswith('BLOCKED'),'Reject duplicate/blank field '+repr(name))
    ph=copy.deepcopy(primary);ph['PROCSOFT']='HARPS_9.0';it=copy.deepcopy(item);it['_recorded_header']['inspection']['primary_header']=ph
    rr=header_result(ph,extension,it);check(rr['status']=='PASS_COMPATIBLE_HEADERS'and rr['pipeline_difference'],'Recorded pipeline difference retained, not silently corrected')
    for status in ['FAILED','NOT_ATTEMPTED']:
        with patch.object(comp.fits,'open',side_effect=AssertionError('No payload opening for failed slot')):
            rr=comp.inspect_payload_headers({'status':status,'reason':'synthetic bounded failure'})
        check(rr['status']=='ACQUISITION_'+status,'Failed selected slot retained '+status)
    # Full release bindings and exact min/max selection using synthetic byte fixtures.
    with tempfile.TemporaryDirectory(prefix='synthetic_',dir=OUT)as td:
        d=Path(td);relative=lambda p:str(p.relative_to(REPO))
        headers=[];inputrows=[]
        for i,(target,berv,status)in enumerate([('HD122640',-20.,'COMPLETE'),('HD122640',20.,'FAILED'),('HD135204',5.,'NOT_ATTEMPTED')],1):
            dp=f'ADP.2099-01-0{i}T00:00:00.000';body=d/f'header{i}.txt';body.write_text('SYNTHETIC HEADER NOT AN OBSERVATION\n');hr=d/f'header{i}.receipt.json';write(hr,{'synthetic':True})
            headers.append({'target':target,'dp_id':dp,'job_index':i,'body_path':body.name,'body_sha256':sha(body),'receipt_path':hr.name,'receipt_sha256':sha(hr),'inspection':{'status':'PASS_RECORDED_BERV','berv_km_s':berv,'raw_progenitor_ids':[f'HARPS.2099-01-0{i}T00:00:00.000'],'primary_header':dict(primary,OBJECT=target)}})
            row={'target':target,'dp_id':dp,'status':status}
            if status=='COMPLETE':
                payload=d/'synthetic_payload.bin';payload.write_bytes(b'SYNTHETIC BYTES, NOT A SCIENCE FITS');pr=d/'payload.receipt.json';write(pr,{'synthetic':True});row.update(local_path=relative(payload),bytes=payload.stat().st_size,sha256=sha(payload),acquisition_receipt_path=relative(pr),acquisition_receipt_sha256=sha(pr))
            else:row['reason']='synthetic failure/stop'
            inputrows.append(row)
        def freeze(hs=None,selected=None,inputs=None,extra=None):
            hs=copy.deepcopy(headers if hs is None else hs);inputs=copy.deepcopy(inputrows if inputs is None else inputs)
            h=d/'HEADERS.json';write(h,{'results':hs});s=d/'SELECTION.json';selected=selected or[{'target':h['target'],'dp_id':h['dp_id'],'header_result_job_index':h['job_index'],'berv_km_s':h['inspection']['berv_km_s']}for h in headers]
            write(s,{'selected':selected,'header_results_sha256':sha(h)});m=d/'MANIFEST.json';write(m,{'inputs':inputs});r={'schema':'HARPS_BERV_COMPARISON_RELEASE_V1','publication_commit':'a'*40,'publication_readback_verified':True,'comparison_script_sha256':sha(P/'compare_verified_epochs.py'),'prospective_plan_sha256':sha(P/'PLAN.json'),'inputs':inputs}
            for key,path in [('selection',s),('header_results',h),('acquisition_manifest',m)]:r[key+'_path']=relative(path);r[key+'_sha256']=sha(path)
            if extra:r.update(extra)
            rel=d/'RELEASE.json';write(rel,r);return rel
        rel=freeze();r,ins,links=comp.validate_release(rel);check(len(ins)==3 and[rr['status']for rr in ins]==['COMPLETE','FAILED','NOT_ATTEMPTED'],'Release preserves every selected status in order')
        def rejects(rel,label):
            try:comp.validate_release(rel)
            except (ValueError,KeyError):check(True,label)
            else:raise AssertionError('Accepted invalid release '+label)
        for key,value in [('schema','bad'),('publication_commit','bad'),('publication_readback_verified',False),('comparison_script_sha256','0'*64),('prospective_plan_sha256','0'*64),('selection_sha256','0'*64),('header_results_sha256','0'*64),('acquisition_manifest_sha256','0'*64)]:rejects(freeze(extra={key:value}),'Release rejects '+key)
        rejects(freeze(hs=headers+[headers[0]]),'Duplicate header identities rejected')
        altered=copy.deepcopy(inputrows);altered[0]['sha256']='0'*64;rejects(freeze(inputs=altered),'Acquired bytes hash bound')
        altered=copy.deepcopy(inputrows);altered[0]['acquisition_receipt_sha256']='0'*64;rejects(freeze(inputs=altered),'Acquisition receipt hash bound')
        altered=copy.deepcopy(headers);altered[1]['inspection']['raw_progenitor_ids']=altered[0]['inspection']['raw_progenitor_ids'];rejects(freeze(hs=altered),'Repeated new raw exposure rejected')
        old=list(csv.DictReader((comp.EXT/'next_followup_20261102/EXISTING_TARGET_EXPOSURES.csv').open()));altered=copy.deepcopy(headers);altered[0]['inspection']['raw_progenitor_ids']=[old[0]['raw_progenitor_id']];rejects(freeze(hs=altered),'Existing raw exposure rejected')
        sel=[{'target':h['target'],'dp_id':h['dp_id'],'header_result_job_index':h['job_index'],'berv_km_s':h['inspection']['berv_km_s']}for h in headers];sel[0],sel[1]=sel[1],sel[0];altered=[inputrows[1],inputrows[0],inputrows[2]];rejects(freeze(selected=sel,inputs=altered),'Min/max selected order cannot change')
        # End-to-end synthetic run: one compatible, one incompatible, one failed slot.
        fixture=d/'run';fixture.mkdir();shutil.copy(P/'EVENTS.json',fixture/'EVENTS.json');shutil.copy(P/'PLAN.json',fixture/'PLAN.json');shutil.copytree(P/'inputs',fixture/'inputs');rfile=fixture/'RELEASE.json';write(rfile,{'synthetic':True})
        inputs=[dict(item,dp_id='SYNTHETIC_VALID',target='HD122640'),dict(item,dp_id='SYNTHETIC_INVALID',target='HD122640'),{'status':'NOT_ATTEMPTED','dp_id':'SYNTHETIC_UNATTEMPTED','target':'HD135204','reason':'synthetic first failure stop'}]
        inputs[1]=copy.deepcopy(inputs[1]);inputs[1]['_recorded_header']['inspection']['primary_header']['SPECSYS']='TOPOCENT'
        inspected=[];data_reads=[];original_inspect=comp.inspect_payload_headers
        synthw=np.linspace(3800,5600,180001);synthf=100+np.sin(synthw*5);synthe=np.full_like(synthw,np.nan)
        class DataHdu(Hdu):
            @property
            def data(self):
                check(len(inspected)==3,'All selected headers checked before each synthetic data access');data_reads.append('synthetic');return {'WAVE':[synthw],'FLUX':[synthf],'ERR':[synthe]}
        current=[None]
        def inspect(it):
            current[0]=it;rr=original_inspect(it);inspected.append(it['dp_id']);return rr
        def fopen(path,**kw):
            if kw.get('memmap')is True:
                ph=copy.deepcopy(current[0]['_recorded_header']['inspection']['primary_header']);return HD([Hdu(ph),Hdu(extension)])
            return HD([Hdu(primary),DataHdu(extension)])
        with patch.object(comp,'HERE',fixture),patch.object(comp,'verified_original_module',return_value=(method,receipt)),patch.object(comp,'validate_release',return_value=({'synthetic':True},inputs,{})),patch.object(comp,'inspect_payload_headers',side_effect=inspect),patch.object(comp.fits,'open',side_effect=fopen),patch.object(sys,'argv',['audit','--release',str(rfile)]),patch('sys.stdout',new=io.StringIO()):comp.main()
        summary=read(fixture/'results/SUMMARY.json');rows=read(fixture/'results/ALL_COMPARISON_MEASUREMENTS.json')
        check(summary['events']==10 and summary['discovery_references_reused']==20,'End-to-end exact10/20 reference accounting')
        check(summary['frame_slots']==32 and summary['measured_profiles']==12 and summary['blocked_profiles']==20,'End-to-end all32 selected frame slots retained')
        check(summary['status']=='PARTIAL_FIXED_DESCRIPTIVE_COMPARISON_WITH_BLOCKED_SLOTS'and summary['events_with_measured_new_profiles']==6 and summary['new_epoch_products_measured']==1,'Partial result status and coverage remain explicit')
        check(len({(r['candidate_id'],r['dp_id'],r['frame'])for r in rows})==32,'No duplicate or missing selected event/frame slots')
        check(summary['U_labels_changed']==summary['origin_assignments']==summary['repeat_classifications']==0,'No classifier or origin assignments')
        check(len(data_reads)==3,'Only one synthetic compatible payload accessed')
        blocked=d/'all_blocked';blocked.mkdir();shutil.copy(P/'EVENTS.json',blocked/'EVENTS.json');shutil.copy(P/'PLAN.json',blocked/'PLAN.json');shutil.copytree(P/'inputs',blocked/'inputs');br=blocked/'RELEASE.json';write(br,{'synthetic':True})
        blocked_inputs=[dict(it,status='NOT_ATTEMPTED',reason='synthetic acquisition stop')for it in inputs]
        with patch.object(comp,'HERE',blocked),patch.object(comp,'verified_original_module',return_value=(method,receipt)),patch.object(comp,'validate_release',return_value=({'synthetic':True},blocked_inputs,{})),patch.object(comp.fits,'open',side_effect=AssertionError('All blocked: no payload opened')),patch.object(sys,'argv',['audit','--release',str(br)]),patch('sys.stdout',new=io.StringIO()):comp.main()
        bs=read(blocked/'results/SUMMARY.json');check(bs['status']=='ALL_SELECTED_SLOTS_BLOCKED_NO_NEW_COMPARISON'and bs['frame_slots']==32 and bs['blocked_profiles']==32 and bs['measured_profiles']==0,'All blocked result never claims a comparison')
    # Verify nothing in reviewed inputs changed during this audit.
    comp.verified_original_module()
    check(start_hashes=={'comparison':sha(P/'compare_verified_epochs.py'),'plan':sha(P/'PLAN.json')},'Reviewed code and plan unchanged across audit execution')
    report={'status':'PASS_CONDITIONAL_COMPARISON_AUDIT','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'checks_passed':len(checks),'scalar_values_compared':scalar_checks,'check_labels':checks,'reference_arrays':20,'reference_events':10,'existing_archive_bytes_verified':len(joined),'new_observational_arrays_read':0,'network_requests':0,'synthetic_science_arrays_only':True,'original_method_sha256':sha(E/'measure_epochs.py'),'comparison_script_sha256':sha(P/'compare_verified_epochs.py'),'plan_sha256':sha(P/'PLAN.json'),'audit_script_sha256':sha(__file__),'limits':['Conditional pre-execution review only; actual new payload headers, bytes and selected slots require review after root release.','Root publication attestation checked structurally and cryptographically against local files; remote commit not retrieved by this no-network audit.','Original descriptive metrics are unchanged; no origin classifier, line detection or significance calibration reviewed as newly established.']}
    write(OUT/'COMPARISON_AUDIT.json',report);print(json.dumps({k:v for k,v in report.items()if k!='check_labels'},indent=2))

if __name__=='__main__':main()
