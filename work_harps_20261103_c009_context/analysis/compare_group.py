#!/usr/bin/env python3
"""Frozen C009 group context; fixed frames, signed flux, no fitted continuum."""
from pathlib import Path
import argparse,csv,datetime,hashlib,json,math,re
import numpy as np
from astropy.io import fits
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
C=299792.458;CB=6802.02;ANCHOR_BERV=3.26509772194068;CT=CB/(1+ANCHOR_BERV/C)
X=np.arange(-300,301,dtype=float)/100
CORE=np.abs(X)<=.25;BROAD=(np.abs(X)>.25)&(np.abs(X)<=3)
FRAMES=['barycentric','topocentric']
EVENTS={'V2E2-0050':'ADP.2023-03-23T01:02:04.831'}
REFERENCES=list(dict.fromkeys(EVENTS.values()))
COVERING_ORDERS={dp:[70] for dp in REFERENCES}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def dump(p,v):
    with p.open('x')as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
def location(p):
    q=(REPO/p).resolve()
    if not q.is_relative_to(REPO.resolve()):raise ValueError('Input outside repository')
    return q
def value(x):return float(x)if np.isfinite(x)else None
def normalized_name(x):return re.sub('[^A-Z0-9]','',str(x).upper())
def validate(release_path):
    plan=read(HERE/'PLAN.json');release=read(release_path)
    if release.get('schema')!='HARPS_C009_GROUP_RELEASE_V1':raise ValueError('Wrong release schema')
    if release.get('publication_readback_verified')is not True or not re.fullmatch('[0-9a-f]{40}',release.get('publication_commit','')):raise ValueError('Verified public method freeze required')
    if release.get('plan_sha256')!=sha(HERE/'PLAN.json')or release.get('script_sha256')!=sha(Path(__file__)):raise ValueError('Method changed')
    if release.get('inventory_path')!=plan['inventory_path']or release.get('inventory_sha256')!=plan['source_hashes'][plan['inventory_path']]:raise ValueError('Inventory release mismatch')
    for f,h in plan['source_hashes'].items():
        if sha(location(f))!=h:raise ValueError('Frozen source changed: '+f)
    inv=read(location(plan['inventory_path']))
    if inv['target']!='HD106515A'or inv['events']!=EVENTS:raise ValueError('Group identities changed')
    if [r['dp_id']for r in inv['merged_spectra']]!=plan['merged_dp_ids']or len(inv['merged_spectra'])!=7:raise ValueError('Seven fixed epochs required')
    if [r['dp_id']for r in inv['native_products']]!=REFERENCES:raise ValueError('One fixed March 2023 discovery native product required')
    if len(inv['saved_native_raw_cutouts'])!=1:raise ValueError('One event-specific preserved raw-order panel required')
    included=[{'dp_id':dp,'order':order}for dp in REFERENCES for order in COVERING_ORDERS[dp]]
    excluded=[]
    if plan['included_native_order_pairs']!=included or plan['excluded_native_order_pairs']!=excluded:raise ValueError('Native order scope changed')
    if {r['dp_id']:r['covering_orders']for r in inv['native_products']}!=COVERING_ORDERS:raise ValueError('Historical covering orders changed')
    if inv['native_order_coverage']!=plan['native_order_coverage']or inv['excluded_native_orders']!=plan['excluded_native_order_evidence']:raise ValueError('Header coverage evidence changed')
    actual_included=[{'dp_id':dp,'order':order} for dp,order in dict.fromkeys((r['dp_id'],r['order']) for r in inv['native_order_coverage']if r['selected_for_profile'])]
    actual_excluded=[{'dp_id':dp,'order':order} for dp,order in dict.fromkeys((r['dp_id'],r['order']) for r in inv['native_order_coverage']if not r['selected_for_profile'])]
    if actual_included!=included or actual_excluded!=excluded:raise ValueError('Coverage inclusion/exclusion mismatch')
    for r in inv['native_order_coverage']:
        lo,hi=r['header_endpoint_topocentric_air_angstrom'];center=r['original_topocentric_feature_center_air_angstrom'];cover=lo<=center<=hi
        if cover!=r['selected_for_profile']or r['status']!=('COVERING_LINE'if cover else'NOT_COVERING_LINE'):raise ValueError('Historical line coverage inconsistent')
    if [{'event':r['event'],'dp_id':EVENTS[r['event']],'order':r['order']}for r in inv['saved_native_raw_cutouts']]!=plan['preserved_event_raw_pairs']:raise ValueError('Event-specific raw context pairs changed')
    return plan,release,inv

def inspect_headers(item,kind):
    checks={}
    with fits.open(location(item['file']['path']),memmap=True,lazy_load_hdus=False)as hd:
        h=hd[0].header
        for key,expected in item['primary_header'].items():
            got=h.get(key)
            checks['recorded_'+key]=(isinstance(got,(int,float))and not isinstance(got,bool)and abs(got-expected)<=1e-8)if isinstance(expected,(int,float))and not isinstance(expected,bool)else got==expected
        checks['HARPS']=h.get('INSTRUME')=='HARPS';checks['target']=normalized_name(h.get('OBJECT'))=='HD106515A'
        berv=h.get('ESO DRS BERV');checks['finite_numeric_BERV']=isinstance(berv,(int,float))and not isinstance(berv,bool)and math.isfinite(berv)
        if kind=='merged':
            e=hd[1].header if len(hd)>1 else fits.Header()
            fields=[e.get('TTYPE'+str(i))for i in range(1,int(e.get('TFIELDS',0))+1)]
            checks['unique_nonblank_fields']=all(isinstance(k,str)and k.strip()for k in fields)and len(set(str(k).strip().casefold()for k in fields))==len(fields)
            checks['required_columns']=all(k in fields for k in ['WAVE','FLUX','ERR'])
            def unit(name,prefix):return e.get(prefix+str(fields.index(name)+1))if name in fields else None
            checks['barycentric_air_angstrom']=h.get('SPECSYS')=='BARYCENT'and str(unit('WAVE','TUNIT')).lower()=='angstrom'and'obs.atmos'in str(unit('WAVE','TUCD'))
            checks['ADU']=str(unit('FLUX','TUNIT')).lower()=='adu';checks['one_row']=e.get('NAXIS2')==1
            checks['single_exposure']=h.get('NCOMBINE')==1 and not isinstance(h.get('NCOMBINE'),bool)
        else:
            checks['shape_72_4096']=h.get('NAXIS1')==4096 and h.get('NAXIS2')==72
            checks['degree_unchanged']=h.get('ESO DRS CAL TH DEG LL')==item['wavelength_polynomial_degree']
            degree=item['wavelength_polynomial_degree']
            for order in item['header_orders_available']:
                coeff=item['orders'][str(order)]['wavelength_coefficients_ascending']
                checks['order_'+str(order)+'_coefficients']=all(h.get('ESO DRS CAL TH COEFF LL'+str(order*(degree+1)+i))==c for i,c in enumerate(coeff))
    failures=[k for k,v in checks.items()if not v]
    return {'kind':kind,'dp_id':item['dp_id'],'status':'PASS_HEADERS'if not failures else'BLOCKED_HEADERS','checks':checks,'failures':failures}

def sampling_parameters(berv,frame):
    return (CB,1.)if frame=='barycentric'else(CT,1+berv/C)

def profile(wave_bary,flux,error,berv,frame,spacing):
    center,scale=sampling_parameters(berv,frame);off=wave_bary/scale-center;requested=(center+X)*scale
    raw=np.interp(requested,wave_bary,flux,left=np.nan,right=np.nan)
    right=np.clip(np.searchsorted(wave_bary,requested),1,len(wave_bary)-1)
    outside=(requested<wave_bary[0])|(requested>wave_bary[-1])
    gap=(wave_bary[right]-wave_bary[right-1])>1.51*spacing
    raw[gap|outside]=np.nan
    left=(off>=-3)&(off<=-1.5);rightside=(off>=1.5)&(off<=3)
    finite=np.isfinite(flux);L=left&finite;R=rightside&finite;side=L|R
    median=np.median(flux[side])if side.any()else np.nan
    problems=[]
    if not left.any():problems.append('MISSING_LEFT_FLANK_COVERAGE')
    elif L.sum()<20:problems.append('INSUFFICIENT_FINITE_LEFT_FLANK')
    if not rightside.any():problems.append('MISSING_RIGHT_FLANK_COVERAGE')
    elif R.sum()<20:problems.append('INSUFFICIENT_FINITE_RIGHT_FLANK')
    if not problems:
        if not np.isfinite(median):problems.append('NO_FINITE_FLANK_REFERENCE')
        elif median<=0:problems.append('NONPOSITIVE_FLANK_REFERENCE')
    pairs=((L[:-1]&L[1:])|(R[:-1]&R[1:]))&(np.diff(wave_bary)<=1.51*spacing)
    diff=np.diff(flux)[pairs]
    noise=1.4826*np.median(np.abs(diff-np.median(diff)))/np.sqrt(2)if len(diff)else np.nan
    normalized=raw/median if not problems else np.full(601,np.nan)
    inside=(off>=-3)&(off<=3)&finite
    errfinite=inside&np.isfinite(error)&(error>0)
    def nonpositive(mask):return float(np.count_nonzero(flux[mask]<=0)/np.count_nonzero(mask))if np.any(mask)else None
    metrics={'normalization_status':'USABLE_POSITIVE_FLANK_REFERENCE'if not problems else'RAW_ONLY','normalization_reasons':problems,'flank_reference':value(median)if L.sum()>=20 and R.sum()>=20 else None,'available_flank_median':value(median),'left_flank_native_samples':int(left.sum()),'right_flank_native_samples':int(rightside.sum()),'left_flank_finite_samples':int(L.sum()),'right_flank_finite_samples':int(R.sum()),'left_flank_median':value(np.median(flux[L]))if L.any()else None,'right_flank_median':value(np.median(flux[R]))if R.any()else None,'left_flank_nonpositive_fraction':nonpositive(L),'right_flank_nonpositive_fraction':nonpositive(R),'window_nonpositive_fraction':nonpositive(inside),'window_native_finite_samples':int(inside.sum()),'positive_finite_ERR_samples':int(errfinite.sum()),'noise_pairs':int(pairs.sum()),'first_difference_noise_proxy':value(noise),'low_flank_reference':None if problems or not np.isfinite(noise)else bool(median<=3*noise),'raw_grid_finite_samples':int(np.isfinite(raw).sum()),'normalized_grid_finite_samples':int(np.isfinite(normalized).sum()),'outside_native_coverage_grid_samples':int(outside.sum()),'gap_masked_grid_samples':int((gap&~outside).sum()),'frame_center':center,'barycentric_query_scale':scale}
    return {'offset':X,'requested_bary_wave':requested,'signed_raw_flux':raw,'normalized_flux':normalized},metrics

def comparison(a,b,mask):
    nominal=int(mask.sum());minimum=math.ceil(.8*nominal)
    rawok=mask&np.isfinite(a['signed_raw_flux'])&np.isfinite(b['signed_raw_flux'])
    normok=mask&np.isfinite(a['normalized_flux'])&np.isfinite(b['normalized_flux'])
    rawreason=None;corr=None
    if rawok.sum()<minimum:rawreason='INSUFFICIENT_COMMON_RAW_COVERAGE'
    elif np.ptp(a['signed_raw_flux'][rawok])==0 or np.ptp(b['signed_raw_flux'][rawok])==0:rawreason='ZERO_RAW_VARIANCE'
    else:corr=float(np.corrcoef(a['signed_raw_flux'][rawok],b['signed_raw_flux'][rawok])[0,1])
    rms=float(np.sqrt(np.mean((a['normalized_flux'][normok]-b['normalized_flux'][normok])**2)))if normok.sum()>=minimum else None
    return {'nominal_grid_samples':nominal,'minimum_common_samples':minimum,'common_finite_raw_samples':int(rawok.sum()),'raw_pearson':corr,'raw_pearson_block_reason':rawreason,'common_finite_normalized_samples':int(normok.sum()),'normalized_rms':rms,'normalized_rms_block_reason':None if rms is not None else'INVALID_REFERENCE_OR_INSUFFICIENT_NORMALIZED_COVERAGE'}

def write_csv(p,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r))
    with p.open('x',newline='')as f:w=csv.DictWriter(f,keys);w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--release',type=Path,default=HERE/'ROOT_RELEASE.json');args=ap.parse_args()
    plan,release,inv=validate(args.release);rh=sha(args.release);out=HERE/'results'
    if out.exists():raise RuntimeError('Preserve previous attempt')
    out.mkdir();(out/'profiles').mkdir();(out/'bounded_inputs').mkdir()
    dump(out/'STARTED.json',{'release_sha256':rh,'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'observed_array_values_read':False})
    dump(out/'NATIVE_ORDER_SCOPE.json',{'included_pairs':plan['included_native_order_pairs'],'excluded_pairs':plan['excluded_native_order_pairs'],'coverage_evidence':plan['native_order_coverage'],'excluded_order_evidence':plan['excluded_native_order_evidence'],'excluded_orders_measured':False})
    inputs=[('merged',r)for r in inv['merged_spectra']]+[('native',r)for r in inv['native_products']]
    headers=[]
    for kind,item in inputs:
        try:h=inspect_headers(item,kind)
        except Exception as e:h={'kind':kind,'dp_id':item['dp_id'],'status':'BLOCKED_HEADER_READ','failures':[repr(e)]}
        headers.append(h)
    dump(out/'HEADER_VALIDATION.json',headers)
    all_profiles={};records=[];bounded=[]
    for (kind,item),header in zip(inputs,headers):
        berv=item.get('berv_km_s',item['primary_header'].get('ESO DRS BERV'))
        for order in ([None]if kind=='merged'else COVERING_ORDERS[item['dp_id']]):
            key=kind+'_'+item['dp_id'].replace(':','_')+(''if order is None else'_o'+str(order))
            source_id=key;reason=None
            if header['status']!='PASS_HEADERS':reason=header['status']
            else:
                try:
                    with fits.open(location(item['file']['path']),memmap=True)as hd:
                        if kind=='merged':w=np.asarray(hd[1].data['WAVE'][0],float)
                        else:w=np.polynomial.polynomial.polyval(np.arange(4096),item['orders'][str(order)]['wavelength_coefficients_ascending'])*(1+berv/C)
                        if not np.isfinite(w).all()or not(np.diff(w)>0).all():raise ValueError('Nonmonotonic/nonfinite source wavelengths')
                        spacing=float(np.median(np.diff(w)));lo=min(CB-3,(CT-3)*(1+berv/C));hi=max(CB+3,(CT+3)*(1+berv/C))
                        a=max(0,int(np.searchsorted(w,lo))-1);b=min(len(w),int(np.searchsorted(w,hi,side='right'))+1)
                        if b-a<2:raise ValueError('Insufficient native coverage')
                        if kind=='merged':flux=np.array(hd[1].data['FLUX'][0][a:b],float);err=np.array(hd[1].data['ERR'][0][a:b],float)
                        else:flux=np.array(hd[0].section[order:order+1,a:b][0],float);err=np.full(len(flux),np.nan)
                        if flux.shape!=(b-a,)or err.shape!=(b-a,):raise ValueError('Selected flux/error shape differs from wavelength slice')
                        original_w=w[a:b]/(1+berv/C)if kind=='native'else w[a:b]
                        w=np.array(w[a:b],copy=True)
                    dest=out/'bounded_inputs'/(source_id+'.npz')
                    with dest.open('xb')as f:np.savez_compressed(f,source_indices=np.arange(a,b),source_wavelength=original_w,barycentric_wavelength=w,signed_source_flux=flux,source_error=err)
                    bounded.append({'source_id':source_id,'kind':kind,'dp_id':item['dp_id'],'order':order,'file':str(dest.relative_to(out)),'sha256':sha(dest),'source_file_sha256':item['file']['sha256'],'original_index_start':a,'original_index_stop':b,'native_samples':len(w),'full_source_median_spacing_bary_angstrom':spacing,'berv_km_s':berv,'source_wave_frame':('BARYCENT'if kind=='merged'else'TOPOCENTRIC_AIR_INHERITED'),'source_flux_unit':'ADU'if kind=='merged'else'NATIVE_EXTRACTED_UNIT_UNSPECIFIED'})
                except Exception as e:reason='BLOCKED_SOURCE_READ:'+repr(e)
            for frame in FRAMES:
                if reason:
                    arr={'offset':X,'requested_bary_wave':np.full(601,np.nan),'signed_raw_flux':np.full(601,np.nan),'normalized_flux':np.full(601,np.nan)};metric={'normalization_status':'BLOCKED','normalization_reasons':[reason],'raw_grid_finite_samples':0,'normalized_grid_finite_samples':0}
                else:arr,metric=profile(w,flux,err,berv,frame,spacing)
                file=out/'profiles'/(source_id+'_'+frame+'.npz')
                with file.open('xb')as f:np.savez_compressed(f,**arr)
                ident=(kind,item['dp_id'],order,frame);all_profiles[ident]=arr
                records.append({'source_id':source_id,'kind':kind,'dp_id':item['dp_id'],'order':order,'frame':frame,'status':'MEASURED_CONTEXT'if not reason else'BLOCKED','date_obs':item.get('date_obs',item['primary_header']['DATE-OBS']),'berv_km_s':berv,'source_input_sha256':item['file']['sha256'],'flux_unit':'ADU'if kind=='merged'else'NATIVE_EXTRACTED_UNIT_UNSPECIFIED','profile_path':str(file.relative_to(out)),'profile_sha256':sha(file),**metric})
    pairs=[]
    for r in records:
        refs=REFERENCES if r['kind']=='merged'else[r['dp_id']]
        for reference in refs:
            a=all_profiles[(r['kind'],r['dp_id'],r['order'],r['frame'])];b=all_profiles[('merged',reference,None,r['frame'])]
            for region,mask in [('core',CORE),('broad_pattern',BROAD)]:
                pairs.append({'relationship':'MERGED_EPOCH_TO_DISCOVERY'if r['kind']=='merged'else'SAME_EPOCH_NATIVE_TO_MERGED','source_id':r['source_id'],'dp_id':r['dp_id'],'order':r['order'],'reference_dp_id':reference,'frame':r['frame'],'region':region,'same_exposure':r['dp_id']==reference,'identical_product_self_pair':r['kind']=='merged'and r['dp_id']==reference,**comparison(a,b,mask)})
    assert len(records)==16 and len(pairs)==32 and len(all_profiles)==16
    assert sum(p['identical_product_self_pair']for p in pairs)==4
    dump(out/'PROFILE_METRICS.json',records);write_csv(out/'PROFILE_METRICS.csv',records);dump(out/'COMPARISONS.json',pairs);write_csv(out/'COMPARISONS.csv',pairs);dump(out/'BOUNDED_INPUT_INDEX.json',bounded)
    # Preserve the exact historical 0050 raw-order panel; existing evidence and shared observations are not independent.
    evidence=[]
    for row in inv['saved_native_raw_cutouts']:
        src=location(row['file']['path']);dest=out/'bounded_inputs'/src.name;dest.write_bytes(src.read_bytes())
        if sha(dest)!=row['file']['sha256']:raise ValueError('Old evidence copy changed')
        evidence.append({**row,'copied_path':str(dest.relative_to(out))})
    dump(out/'PRESERVED_RAW_CONTEXT.json',evidence)
    validate(args.release)
    if sha(args.release)!=rh:raise ValueError('Release changed')
    dump(out/'SUMMARY.json',{'status':'COMPLETE_FIXED_GROUP_CONTEXT'if all(r['status']=='MEASURED_CONTEXT'for r in records)else'PARTIAL_WITH_EXPLICIT_BLOCKED_SLOTS','completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'group':'C009','target':'HD106515A','events':list(EVENTS),'merged_epochs':7,'distinct_discovery_products':1,'discovery_records':1,'native_discovery_orders':1,'structurally_excluded_native_orders':0,'profile_slots':16,'comparison_slots':32,'identical_product_self_comparisons':4,'raw_only_normalization_slots':sum(r['normalization_status']=='RAW_ONLY'for r in records),'blocked_source_profile_slots':sum(r['status']=='BLOCKED'for r in records),'preserved_raw_context_panels':1,'group_center_bary_air_angstrom':CB,'topocentric_anchor_air_angstrom':CT,'anchor_berv_km_s':ANCHOR_BERV,'old_epoch_pipeline_rerun':False,'labels_changed':0,'origin_assignments':0,'release_sha256':rh,'plan_sha256':sha(HERE/'PLAN.json'),'script_sha256':sha(Path(__file__)),'limitations':plan['limitations']})
    dump(out/'OUTPUT_HASHES.json',{str(p.relative_to(out)):sha(p)for p in sorted(out.rglob('*'))if p.is_file()})
    print(json.dumps(read(out/'SUMMARY.json'),indent=2))
if __name__=='__main__':main()
