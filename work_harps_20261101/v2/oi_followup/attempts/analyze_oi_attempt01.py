"""Fixed, descriptive three-line follow-up. Never modifies source catalogs."""
from pathlib import Path
import csv,json,hashlib,datetime,tarfile,io,subprocess,gc
import numpy as np
from astropy.io import fits

OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1]
PLAN=json.loads((OUT/'PLAN.json').read_text())
ARR=OUT/'arrays';ARR.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,data):
    (OUT/name).write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')
def finite(x):return float(x) if np.isfinite(x) else None
def poly(h,prefix,degree,order,x):
    return np.polynomial.polynomial.polyval(x,[h[prefix+str(order*(degree+1)+j)] for j in range(degree+1)])
def wave(h,order):return poly(h,'ESO DRS CAL TH COEFF LL',int(h['ESO DRS CAL TH DEG LL']),order,np.arange(4096))
def header_context(h):
    return {k:v for k,v in h.items() if any(x in k for x in ['DPR','LAMP','INS OPTI','INS2 OPTI','CAL TH FILE','CAL LOC FILE','CAL FLAT FILE','DRIFT','BERV']) and isinstance(v,(str,int,float,bool))}
def fit_line(w,f,center,stem):
    sel=np.isfinite(w)&np.isfinite(f)&(abs(w-center)<=.4);x=np.asarray(w[sel]-center,dtype=float);y=np.asarray(f[sel],dtype=float)
    side=(abs(x)>=.15)&(abs(x)<=.35);core=abs(x)<=.08
    if side.sum()<10 or core.sum()<4:return dict(status='INSUFFICIENT_SUPPORT',side_samples=int(side.sum()),core_samples=int(core.sum()))
    design=np.column_stack([np.ones(side.sum()),x[side]]);coef=np.linalg.lstsq(design,y[side],rcond=None)[0]
    baseline=coef[0]+coef[1]*x;resid=y-baseline;sigma=center/115000/np.sqrt(8*np.log(2));grid=np.arange(-16,17)*.0025
    trials=[]
    for offset in grid:
        g=np.exp(-.5*((x[core]-offset)/sigma)**2);a=float(g@resid[core]/(g@g));ss=float(np.sum((resid[core]-a*g)**2));trials.append(dict(offset_angstrom=float(offset),amplitude_adu=a,core_residual_sum_squares=ss))
    best=min(trials,key=lambda r:r['core_residual_sum_squares']);fixed=trials[16]
    residual_side=resid[side];mad=float(1.4826*np.median(abs(residual_side-np.median(residual_side))))
    path=ARR/(stem+'.npz');np.savez_compressed(path,offset_angstrom=x,flux_adu=y,baseline_adu=baseline,side_mask=side,core_mask=core)
    return dict(status='MEASURED',reference_air_angstrom=center,side_samples=int(side.sum()),core_samples=int(core.sum()),
        continuum_intercept_adu=float(coef[0]),continuum_slope_adu_per_angstrom=float(coef[1]),side_residual_mad_adu=mad,
        fixed_amplitude_adu=fixed['amplitude_adu'],fixed_amplitude_over_continuum=finite(fixed['amplitude_adu']/coef[0]) if coef[0]!=0 else None,
        fixed_model_area_adu_angstrom=float(fixed['amplitude_adu']*sigma*np.sqrt(2*np.pi)),best_offset_angstrom=best['offset_angstrom'],
        best_amplitude_adu=best['amplitude_adu'],best_core_residual_sum_squares=best['core_residual_sum_squares'],
        best_center_at_grid_boundary=abs(best['offset_angstrom'])>=.04,core_residual_direct_area_adu_angstrom=float(np.trapezoid(resid[core],x[core])),
        trials=trials,array=str(path.relative_to(OUT)))

for rel,digest in PLAN['original_hashes'].items():assert sha(BASE/rel)==digest
meta=[]
for rel in ['acquisition/DOWNLOAD_MANIFEST.json','v2/acquisition/DOWNLOAD_MANIFEST.json']:
    for r in json.loads((BASE/rel).read_text()):
        r['relative_path']=r.get('relative_path',str(Path(r['path']).relative_to(BASE)))
        if '/main/' in r['relative_path']:meta.append(r)
byid={r['dp_id']:r for r in meta}
products=[]
for rel in ['v2/triage_batch01/products/MANIFEST.json','v2/triage_batch02/products/MANIFEST.json']:
    products+=json.loads((BASE/rel).read_text())['products']

native=[];inventory=[]
for dp in PLAN['native_exposure_ids']:
    tr=next(r for r in products if r['dp_id']==dp and r['kind']=='ANCILLARY');rr=next(r for r in products if r['dp_id']==dp and r['kind']=='RAW')
    assert sha(BASE/tr['relative_path'])==tr['sha256'];assert sha(BASE/rr['relative_path'])==rr['sha256']
    with fits.open(io.BytesIO(subprocess.run(['gzip','-cd',str(BASE/rr['relative_path'])],capture_output=True,check=True).stdout)) as h:
        rh=h[0].header.copy();assert rh['DATE-OBS']==byid[dp]['primary_header']['DATE-OBS']
    record=dict(dp_id=dp,target=byid[dp]['canonical_target'],date_obs=rh['DATE-OBS'],raw_context=header_context(rh),raw_sha256=rr['sha256'],ancillary_sha256=tr['sha256'])
    with tarfile.open(BASE/tr['relative_path']) as t:
        record['members']=t.getnames();record['fiber_headers']={}
        for fiber in ['A','B']:
            members=[m for m in t if m.name.endswith('_e2ds_'+fiber+'.fits')]
            if not members:record['fiber_headers'][fiber]=dict(status='MISSING');continue
            with fits.open(io.BytesIO(t.extractfile(members[0]).read())) as h:
                f=h[0].data.astype(float);head=h[0].header.copy()
            assert head['DATE-OBS']==rh['DATE-OBS'];record['fiber_headers'][fiber]=dict(status='PRESENT',shape=list(f.shape),context=header_context(head),member=members[0].name)
            waves=np.array([wave(head,o) for o in range(f.shape[0])])
            for label,center in PLAN['lines_air_angstrom'].items():
                orders=np.flatnonzero((waves[:,0]<center-.4)&(waves[:,-1]>center+.4)).tolist()
                for order in orders:
                    fit=fit_line(waves[order],f[order],center,dp.replace(':','_')+'_'+fiber+'_'+label+'_o'+str(order))
                    native.append(dict(dp_id=dp,target=byid[dp]['canonical_target'],date_obs=rh['DATE-OBS'],fiber=fiber,line=label,order=order,
                        berv_km_s=float(head['ESO DRS BERV']),**fit))
    record['independent_sky_fiber_available']=record['raw_context'].get('ESO DPR TYPE','').split(',')[1:2]==['SKY']
    inventory.append(record);print('native '+dp,flush=True);gc.collect()
save('ANCILLARY_FIBER_INVENTORY.json',inventory);save('NATIVE_MEASUREMENTS.json',native)

epochs=[]
for ep in PLAN['all_epoch_spectra']:
    path=BASE/ep['relative_path'];assert sha(path)==ep['sha256']
    with fits.open(path) as h:
        hdr=h[0].header;berv=float(hdr['ESO DRS BERV']);w=h[1].data['WAVE'][0].astype(float)/(1+berv/299792.458);f=h[1].data['FLUX'][0].astype(float)
        err=h[1].data['ERR'][0];error_finite=int(np.isfinite(err).sum());err_comment=h[1].header.get('TCOMM3','')
    for label,center in PLAN['lines_air_angstrom'].items():
        fit=fit_line(w,f,center,ep['dp_id'].replace(':','_')+'_merged_'+label)
        epochs.append(dict(dp_id=ep['dp_id'],target=ep['target'],date_obs=ep['date_obs'],berv_km_s=berv,line=label,
            source_sha256=ep['sha256'],error_samples_finite=error_finite,error_comment=err_comment,**fit))
save('ALL_EPOCH_MEASUREMENTS.json',epochs)
def write_table(name,rows):
    keys=list(dict.fromkeys(k for r in rows for k in r if k!='trials'))
    with (OUT/name).open('w',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=keys);wr.writeheader();wr.writerows({k:v for k,v in r.items() if k!='trials'} for r in rows)
write_table('NATIVE_MEASUREMENTS.csv',native);write_table('ALL_EPOCH_MEASUREMENTS.csv',epochs)
ratios=[]
for kind,rows in [('native_A',[r for r in native if r['fiber']=='A']),('merged_A',epochs)]:
    for dp in dict.fromkeys(r['dp_id'] for r in rows):
        subset={r['line']:r for r in rows if r['dp_id']==dp};a=subset['OI6300'];b=subset['OI6363']
        ratios.append(dict(product=kind,dp_id=dp,target=a['target'],date_obs=a['date_obs'],
            fixed_area_6300_adu_angstrom=a['fixed_model_area_adu_angstrom'],fixed_area_6363_adu_angstrom=b['fixed_model_area_adu_angstrom'],
            descriptive_area_ratio_6300_over_6363=finite(a['fixed_model_area_adu_angstrom']/b['fixed_model_area_adu_angstrom']) if b['fixed_model_area_adu_angstrom']!=0 else None,
            both_signed_areas_positive=a['fixed_model_area_adu_angstrom']>0 and b['fixed_model_area_adu_angstrom']>0,
            not_flux_calibrated=True,ratio_used_for_origin_veto=False))
write_table('DESCRIPTIVE_DOUBLET_RATIOS.csv',ratios);save('DESCRIPTIVE_DOUBLET_RATIOS.json',ratios)
for rel,digest in PLAN['original_hashes'].items():assert sha(BASE/rel)==digest
summary=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),native_exposures=len(inventory),native_measurements=len(native),all_epoch_exposures=len(PLAN['all_epoch_spectra']),all_epoch_measurements=len(epochs),
    independent_sky_fiber_exposures=sum(r['independent_sky_fiber_available'] for r in inventory),
    original_hashes_verified=True,source_script_sha256=sha(Path(__file__)),plan_sha256=sha(OUT/'PLAN.json'),
    calibration='All signed line fits and all center-grid trials retained. No fitted uncertainty or calibrated significance; archive ERR arrays are unavailable/NaN.',
    limitations='Three fixed lines in selected exposures, post-hoc. Uncalibrated ADU/blaze/response, stellar blends, continuum choices and imperfect profile model prevent definitive line ratios or origin assignment.')
save('MEASUREMENT_SUMMARY.json',summary);print(json.dumps(summary,indent=2))
