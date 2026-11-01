"""Frozen descriptive all-epoch profiles; never changes detector or dispositions."""
from pathlib import Path
import json,csv,hashlib,datetime,collections,itertools
import numpy as np
from astropy.io import fits

OUT=Path(__file__).resolve().parent;BASE=OUT.parents[1]
PLAN=json.loads((OUT/'PLAN.json').read_text());GROUPS=PLAN['groups_definition'];INPUTS=PLAN['input_manifest']
C=299792.458;X=np.linspace(-1.,1.,201);CORE=abs(X)<=.250000001;SIDE=(abs(X)>=.599999999)
ARRAYS=OUT/'profiles';ARRAYS.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def number(x):return float(x) if np.isfinite(x) else None
def mad(v):
    v=np.asarray(v);v=v[np.isfinite(v)]
    return float(1.4826*np.median(abs(v-np.median(v)))) if len(v) else float('nan')
def fit_profile(y,center):
    fit={};ok=CORE&np.isfinite(y)
    for name,factor in [('narrow',1.),('broad3',3.)]:
        fwhm=center/115000.*factor;g=np.exp(-.5*(X/(fwhm/2.3548200450309493))**2)
        if ok.sum()<20:fit[name]=None;continue
        a=np.column_stack([np.ones(ok.sum()),X[ok],g[ok]])
        coef=np.linalg.lstsq(a,y[ok],rcond=None)[0];r=y[ok]-a@coef
        fit[name]=dict(fwhm_angstrom=fwhm,amplitude=float(coef[2]),intercept=float(coef[0]),slope=float(coef[1]),
                       residual_rms=float(np.sqrt(np.mean(r*r))),fitted_samples=int(ok.sum()))
    return fit
def corr(a,b):
    ok=CORE&np.isfinite(a)&np.isfinite(b)
    if ok.sum()<20 or np.std(a[ok])==0 or np.std(b[ok])==0:return None
    return number(np.corrcoef(a[ok],b[ok])[0,1])
def stats(a):
    a=np.array([x for x in a if x is not None and np.isfinite(x)])
    if not len(a):return dict(n=0,median=None,q25=None,q75=None,min=None,max=None)
    return dict(n=len(a),median=float(np.median(a)),q25=float(np.quantile(a,.25)),q75=float(np.quantile(a,.75)),min=float(a.min()),max=float(a.max()))
assert sha(BASE/'v2/triage_batch02/CUMULATIVE_DISPOSITIONS.csv')==PLAN['source_dispositions_sha256']
allhits=list(csv.DictReader((BASE/'v2/review/REVIEW_INDEX.csv').open()))
rows=[];source_checks=[];profile_data={}
for m in INPUTS:
    p=BASE/m['relative_path'];assert sha(p)==m['sha256'],p
    with fits.open(p) as h:
        ph=h[0].header;eh=h[1].header;w=np.array(h[1].data['WAVE'][0],dtype=float);f=np.array(h[1].data['FLUX'][0],dtype=float);e=np.array(h[1].data['ERR'][0],dtype=float)
        assert ph['SPECSYS']=='BARYCENT' and eh['TUNIT1']=='angstrom'
        assert ph['DATE-OBS']==m['date_obs'] and abs(ph['ESO DRS BERV']-m['berv_km_s'])<1e-8
        assert ph['NCOMBINE']==1 and 'obs.atmos' in eh['TUCD1']
    assert np.isfinite(w).all() and np.all(np.diff(w)>0)
    spacing=float(np.median(np.diff(w)));berv=m['berv_km_s'];source_checks.append(dict(**m,hash_verified=True,samples=len(w),finite_flux_samples=int(np.isfinite(f).sum()),finite_positive_error_samples=int((np.isfinite(e)&(e>0)).sum()),median_wave_step_angstrom=spacing))
    for g in [g for g in GROUPS if g['target']==m['target']]:
        members=[h for h in allhits if h['review_id'] in g['member_ids'] and h['dp_id']==m['dp_id']]
        near=[h['review_id'] for h in allhits if h['dp_id']==m['dp_id'] and abs(float(h['fitted_center_bary_air_angstrom'])-g['center_bary_air_angstrom'])<=.1]
        for frame in ['barycentric','topocentric']:
            center=g['center_bary_air_angstrom'] if frame=='barycentric' else g['center_topocentric_air_angstrom']
            scale=1 if frame=='barycentric' else (1+berv/C)
            requested=(center+X)*scale;center_bary=center*scale
            flux=np.interp(requested,w,f,left=np.nan,right=np.nan)
            right=np.clip(np.searchsorted(w,requested),1,len(w)-1);gap=(w[right]-w[right-1])>1.51*spacing;flux[gap]=np.nan
            normmask=(abs(w-center_bary)<=2)&np.isfinite(f);local=f[normmask];normalization=float(np.median(local)) if len(local) else float('nan')
            local_pairs=(abs(w[:-1]-center_bary)<=2)&np.isfinite(f[:-1])&np.isfinite(f[1:])&(np.diff(w)<1.51*spacing)
            noise=mad(np.diff(f)[local_pairs])/np.sqrt(2)
            validnorm=np.isfinite(normalization) and normalization>0
            y=flux/normalization if validnorm else np.full(len(X),np.nan)
            ok=SIDE&np.isfinite(y)
            if ok.sum()>=20:
                coef=np.linalg.lstsq(np.column_stack([np.ones(ok.sum()),X[ok]]),y[ok],rcond=None)[0]
                bg=coef[0]+coef[1]*X;res=y-bg
            else:bg=np.full(len(X),np.nan);res=bg.copy()
            fit=fit_profile(y,center)
            filename=g['group_id']+'_'+m['dp_id'].replace(':','_')+'_'+frame+'.npz'
            np.savez_compressed(ARRAYS/filename,offset_air_angstrom=X,requested_bary_air_angstrom=requested,raw_flux=flux,normalized_flux=y,linear_background=bg,residual=res)
            r=dict(group_id=g['group_id'],target=g['target'],dp_id=m['dp_id'],cohort=m['cohort'],date_obs=m['date_obs'],mjd_obs=m['mjd_obs'],berv_km_s=berv,exptime=m['exptime'],frame=frame,
                center_in_frame_air_angstrom=center,center_sampled_bary_air_angstrom=center_bary,normalization_adu=number(normalization),normalization_samples=int(normmask.sum()),
                first_difference_noise_proxy_adu=number(noise),local_continuum_low=bool(not validnorm or (np.isfinite(noise) and normalization<=3*noise)),
                valid_samples=int(np.isfinite(y).sum()),gap_masked_samples=int(gap.sum()),finite_positive_ERR_samples=int((np.isfinite(e[right])&(e[right]>0)).sum()),
                source_unresolved_event_ids=json.dumps([h['review_id'] for h in members]),nearby_saved_v2_event_ids=json.dumps(near),
                v2_search_run_on_exposure=m['cohort']=='V2_new',normalization_status='USABLE_POSITIVE_MEDIAN' if validnorm else 'NONPOSITIVE_OR_MISSING_MEDIAN',profile_path='profiles/'+filename,
                narrow_amplitude=fit['narrow']['amplitude'] if fit['narrow'] else None,narrow_residual_rms=fit['narrow']['residual_rms'] if fit['narrow'] else None,
                broad3_amplitude=fit['broad3']['amplitude'] if fit['broad3'] else None,broad3_residual_rms=fit['broad3']['residual_rms'] if fit['broad3'] else None,
                core_flux_integral_over_linear_background=number(np.trapezoid(res[CORE],X[CORE])),leave_one_out_profile_correlation=None)
            rows.append(r);profile_data[(g['group_id'],m['dp_id'],frame)]=res
    print(json.dumps(dict(dp_id=m['dp_id'],target=m['target'],groups=sum(g['target']==m['target'] for g in GROUPS))),flush=True)
summaries=[]
for g in GROUPS:
    summary=dict(**g,epoch_count=len({r['dp_id'] for r in rows if r['group_id']==g['group_id']}),frames={})
    for frame in ['barycentric','topocentric']:
        selected=[r for r in rows if r['group_id']==g['group_id'] and r['frame']==frame]
        data=[profile_data[(r['group_id'],r['dp_id'],frame)] for r in selected]
        pairs=[]
        for i,j in itertools.combinations(range(len(selected)),2):pairs.append(dict(dp_i=selected[i]['dp_id'],dp_j=selected[j]['dp_id'],correlation=corr(data[i],data[j])))
        for i,r in enumerate(selected):
            template=np.nanmedian(np.stack([d for j,d in enumerate(data) if j!=i]),axis=0)
            r['leave_one_out_profile_correlation']=corr(data[i],template)
        summary['frames'][frame]=dict(valid_epochs=sum(r['valid_samples']>=181 for r in selected),low_continuum_epochs=sum(r['local_continuum_low'] for r in selected),
            pairwise_correlations=pairs,pairwise_correlation_summary=stats([r['correlation'] for r in pairs]),
            leave_one_out_correlation_summary=stats([r['leave_one_out_profile_correlation'] for r in selected]),
            narrow_amplitude_summary=stats([r['narrow_amplitude'] for r in selected]),broad3_amplitude_summary=stats([r['broad3_amplitude'] for r in selected]),
            integrated_excess_summary=stats([r['core_flux_integral_over_linear_background'] for r in selected]))
    summary['berv_range_km_s']=[min(r['berv_km_s'] for r in rows if r['group_id']==g['group_id']),max(r['berv_km_s'] for r in rows if r['group_id']==g['group_id'])]
    summaries.append(summary)
with (OUT/'ALL_EPOCH_MEASUREMENTS.csv').open('w',newline='') as h:
    w=csv.DictWriter(h,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
(OUT/'GROUP_RESULTS.json').write_text(json.dumps(summaries,indent=2,allow_nan=False)+'\n')
(OUT/'INPUT_CHECKS.json').write_text(json.dumps(source_checks,indent=2,allow_nan=False)+'\n')
result=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='DESCRIPTIVE_ALL_EPOCH_COMPARISON_COMPLETE',events=PLAN['events'],groups=len(GROUPS),targets=len({r['target'] for r in INPUTS}),input_exposures=len(INPUTS),group_epoch_pairs=len(rows)//2,frame_measurements=len(rows),profiles=len(list(ARRAYS.glob('*.npz'))),
    original_cohort_exposures=sum(m['cohort']=='V1_original' for m in INPUTS),new_cohort_exposures=sum(m['cohort']=='V2_new' for m in INPUTS),all_input_hashes_verified=True,
    all_errors_missing=all(m['finite_positive_error_samples']==0 for m in source_checks),missing_profile_count=sum(r['valid_samples']<181 for r in rows),low_continuum_measurements=sum(r['local_continuum_low'] for r in rows),
    original_dispositions_unchanged=sha(BASE/'v2/triage_batch02/CUMULATIVE_DISPOSITIONS.csv')==PLAN['source_dispositions_sha256'],plan_sha256=sha(OUT/'PLAN.json'),script_sha256=sha(Path(__file__)),limitations=PLAN['interpretation'])
(OUT/'SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
