"""Event-specific post-hoc epoch metrics, with no origin or repeat classifier."""
from pathlib import Path
import csv, datetime, hashlib, json, os
import numpy as np
from astropy.io import fits

OUT=Path(__file__).resolve().parent
BASE=OUT.parents[2]
C=299792.458
X=np.linspace(-1.,1.,201)
CORE=abs(X)<=.250000001
SIDE=abs(X)>=.599999999

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def val(x): return float(x) if np.isfinite(x) else None
def atomic_json(path,obj):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,indent=2,allow_nan=False)+'\n')
    os.replace(tmp,path)
def atomic_csv(path,rows):
    tmp=path.with_suffix('.csv.tmp')
    with tmp.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    os.replace(tmp,path)
def stats(a):
    a=np.array([v for v in a if v is not None and np.isfinite(v)])
    if not len(a): return dict(n=0,median=None,q25=None,q75=None,min=None,max=None)
    return dict(n=len(a),median=float(np.median(a)),q25=float(np.quantile(a,.25)),q75=float(np.quantile(a,.75)),min=float(a.min()),max=float(a.max()))
def mad(a):
    a=np.asarray(a);a=a[np.isfinite(a)]
    return float(1.4826*np.median(abs(a-np.median(a)))) if len(a) else float('nan')
def corr(a,b):
    ok=CORE&np.isfinite(a)&np.isfinite(b)
    if ok.sum()<20 or np.std(a[ok])==0 or np.std(b[ok])==0:return None
    return val(np.corrcoef(a[ok],b[ok])[0,1])
def fits_at_center(y,center):
    out={};ok=CORE&np.isfinite(y)
    for label,factor in [('narrow',1.),('broad3',3.)]:
        if ok.sum()<20:out[label]=None;continue
        fwhm=center/115000.*factor
        g=np.exp(-.5*(X/(fwhm/2.3548200450309493))**2)
        a=np.column_stack([np.ones(ok.sum()),X[ok],g[ok]])
        coef=np.linalg.lstsq(a,y[ok],rcond=None)[0]
        out[label]=dict(amplitude=float(coef[2]),residual_rms=float(np.sqrt(np.mean((y[ok]-a@coef)**2))))
    return out
def profile(w,f,e,center,scale):
    spacing=float(np.median(np.diff(w)))
    requested=(center+X)*scale;cb=center*scale
    flux=np.interp(requested,w,f,left=np.nan,right=np.nan)
    right=np.clip(np.searchsorted(w,requested),1,len(w)-1)
    gaps=(w[right]-w[right-1])>1.51*spacing
    flux[gaps]=np.nan
    normmask=(abs(w-cb)<=2)&np.isfinite(f)
    normalization=float(np.median(f[normmask])) if normmask.any() else float('nan')
    pairs=(abs(w[:-1]-cb)<=2)&np.isfinite(f[:-1])&np.isfinite(f[1:])&(np.diff(w)<1.51*spacing)
    noise=mad(np.diff(f)[pairs])/np.sqrt(2)
    usable=bool(np.isfinite(normalization) and normalization>0)
    y=flux/normalization if usable else np.full(201,np.nan)
    ok=SIDE&np.isfinite(y)
    if ok.sum()>=20:
        a=np.column_stack([np.ones(ok.sum()),X[ok]])
        coef=np.linalg.lstsq(a,y[ok],rcond=None)[0]
        bg=coef[0]+coef[1]*X
    else:bg=np.full(201,np.nan)
    residual=y-bg
    fit=fits_at_center(y,center)
    arr=dict(offset_air_angstrom=X,requested_bary_air_angstrom=requested,raw_flux=flux,normalized_flux=y,linear_background=bg,residual=residual)
    metrics=dict(center_in_frame_air_angstrom=center,center_sampled_bary_air_angstrom=cb,normalization_adu=val(normalization),normalization_samples=int(normmask.sum()),first_difference_noise_proxy_adu=val(noise),local_continuum_low=bool(not usable or(np.isfinite(noise) and normalization<=3*noise)),valid_samples=int(np.isfinite(y).sum()),gap_masked_samples=int(gaps.sum()),finite_positive_ERR_samples=int((np.isfinite(e[right])&(e[right]>0)).sum()),normalization_status='USABLE_POSITIVE_MEDIAN' if usable else 'NONPOSITIVE_OR_MISSING_MEDIAN',narrow_amplitude=fit['narrow']['amplitude'] if fit['narrow'] else None,narrow_residual_rms=fit['narrow']['residual_rms'] if fit['narrow'] else None,broad3_amplitude=fit['broad3']['amplitude'] if fit['broad3'] else None,broad3_residual_rms=fit['broad3']['residual_rms'] if fit['broad3'] else None,core_flux_integral_over_linear_background=val(np.trapezoid(residual[CORE],X[CORE])))
    return arr,metrics

def main():
    assert not (OUT/'SUMMARY.json').exists(),'Run only in an unused output directory or separate reproduction copy.'
    plan=json.loads((OUT/'PLAN.json').read_text())
    for rel,digest in plan['source_hashes'].items():assert sha(BASE/rel)==digest,rel
    inputs=plan['inputs'];bydp={m['dp_id']:m for m in inputs}
    hits=list(csv.DictReader((BASE/'v2/extension02/production/V2_HITS.csv').open()))
    assert [h['candidate_id'] for h in hits]==plan['event_ids']
    assert len(inputs)==100 and len(hits)==336 and len(set(plan['event_ids']))==336
    profiles=OUT/'profiles';profiles.mkdir(exist_ok=True)
    rows=[];checks=[];data={}
    for m in inputs:
        p=BASE/m['relative_path'];assert sha(p)==m['sha256'],p
        with fits.open(p) as hd:
            ph=hd[0].header;eh=hd[1].header
            assert ph['SPECSYS']=='BARYCENT' and eh['TUNIT1']=='angstrom' and 'obs.atmos' in eh['TUCD1']
            assert ph['DATE-OBS']==m['date_obs'] and abs(ph['ESO DRS BERV']-m['berv_km_s'])<1e-8 and ph['NCOMBINE']==1
            w=np.array(hd[1].data['WAVE'][0],float);f=np.array(hd[1].data['FLUX'][0],float);e=np.array(hd[1].data['ERR'][0],float)
        assert np.isfinite(w).all() and (np.diff(w)>0).all()
        checks.append(dict(**m,hash_verified=True,finite_flux_samples=int(np.isfinite(f).sum()),finite_positive_ERR_samples=int((np.isfinite(e)&(e>0)).sum())))
        selected=[h for h in hits if h['canonical_target']==m['target']]
        for h in selected:
            ref=bydp[h['dp_id']];cb=float(h['fitted_center_angstrom']);ct=cb/(1+ref['berv_km_s']/C)
            for frame,center,scale in [('barycentric',cb,1.),('topocentric',ct,1+m['berv_km_s']/C)]:
                arr,metrics=profile(w,f,e,center,scale)
                filename=h['candidate_id']+'_'+m['dp_id'].replace(':','_')+'_'+frame+'.npz'
                dest=profiles/filename;tmp=dest.with_suffix('.npz.tmp')
                with tmp.open('wb') as out:np.savez_compressed(out,**arr)
                os.replace(tmp,dest)
                r=dict(candidate_id=h['candidate_id'],target=m['target'],source_dp_id=h['dp_id'],dp_id=m['dp_id'],is_discovery_exposure=m['dp_id']==h['dp_id'],date_obs=m['date_obs'],mjd_obs=m['mjd_obs'],berv_km_s=m['berv_km_s'],source_berv_km_s=ref['berv_km_s'],berv_delta_from_source_km_s=m['berv_km_s']-ref['berv_km_s'],source_epoch_displacement_resolution_elements=abs(m['berv_km_s']-ref['berv_km_s'])/C*115000.,exptime=m['exptime'],frame=frame,profile_path='profiles/'+filename,profile_sha256=sha(dest),**metrics,correlation_to_discovery=None)
                rows.append(r);data[(h['candidate_id'],m['dp_id'],frame)]=arr['residual']
        print(m['dp_id'],len(selected),'events',flush=True)
    summaries=[]
    for h in hits:
        selected=[r for r in rows if r['candidate_id']==h['candidate_id']]
        epochs=sorted({r['dp_id'] for r in selected});ref=bydp[h['dp_id']]
        bervs=[bydp[dp]['berv_km_s'] for dp in epochs]
        span=max(bervs)-min(bervs)
        summary=dict(candidate_id=h['candidate_id'],target=h['canonical_target'],source_dp_id=h['dp_id'],fitted_center_bary_air_angstrom=float(h['fitted_center_angstrom']),comparison_epochs_including_discovery=len(epochs),other_epochs=len(epochs)-1,berv_min_km_s=min(bervs),berv_max_km_s=max(bervs),berv_span_km_s=span,berv_span_resolution_elements=span/C*115000.,frame_separation_below_one_resolution_element=span<C/115000.,frames={})
        for frame in ['barycentric','topocentric']:
            rr=[r for r in selected if r['frame']==frame]
            refprof=data[(h['candidate_id'],h['dp_id'],frame)]
            for r in rr:r['correlation_to_discovery']=corr(refprof,data[(h['candidate_id'],r['dp_id'],frame)])
            other=[r for r in rr if not r['is_discovery_exposure']]
            summary['frames'][frame]=dict(other_epoch_count=len(other),other_valid_profile_count=sum(r['valid_samples']>=181 for r in other),other_low_continuum_count=sum(r['local_continuum_low'] for r in other),other_correlation_to_discovery=stats([r['correlation_to_discovery'] for r in other]),other_narrow_amplitude=stats([r['narrow_amplitude'] for r in other]),other_broad3_amplitude=stats([r['broad3_amplitude'] for r in other]),other_integrated_excess=stats([r['core_flux_integral_over_linear_background'] for r in other]),discovery_narrow_amplitude=next(r['narrow_amplitude'] for r in rr if r['is_discovery_exposure']))
        a=summary['frames']['barycentric']['other_correlation_to_discovery']['median'];b=summary['frames']['topocentric']['other_correlation_to_discovery']['median']
        summary['median_correlation_bary_minus_topo']=a-b if a is not None and b is not None else None
        summaries.append(summary)
    assert len({(r['candidate_id'],r['dp_id'],r['frame']) for r in rows})==len(rows)
    assert all(sum(r['is_discovery_exposure'] for r in rows if r['candidate_id']==h['candidate_id'])==2 for h in hits)
    atomic_csv(OUT/'ALL_EPOCH_MEASUREMENTS.csv',rows)
    atomic_json(OUT/'EVENT_RESULTS.json',summaries)
    flat=[]
    for s in summaries:
        r={k:v for k,v in s.items() if k!='frames'}
        for frame in ['barycentric','topocentric']:
            for key,value in s['frames'][frame].items():
                if isinstance(value,dict):
                    for k,v in value.items():r[frame+'_'+key+'_'+k]=v
                else:r[frame+'_'+key]=value
        flat.append(r)
    atomic_csv(OUT/'EVENT_SUMMARY.csv',flat)
    atomic_json(OUT/'INPUT_CHECKS.json',checks)
    for rel,digest in plan['source_hashes'].items():assert sha(BASE/rel)==digest
    summary=dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='COMPLETE_DESCRIPTIVE_NO_ORIGIN_ASSIGNMENTS',events=len(summaries),event_targets=len({h['canonical_target'] for h in hits}),verified_input_exposures=len(checks),measured_input_exposures=len({r['dp_id'] for r in rows}),input_targets=len({m['target'] for m in inputs}),event_epoch_pairs=len(rows)//2,frame_measurements=len(rows),discovery_frame_measurements=sum(r['is_discovery_exposure'] for r in rows),other_epoch_frame_measurements=sum(not r['is_discovery_exposure'] for r in rows),profiles=len(list(profiles.glob('*.npz'))),invalid_normalization_measurements=sum(r['normalization_status']!='USABLE_POSITIVE_MEDIAN' for r in rows),profiles_with_fewer_than181_finite_samples=sum(r['valid_samples']<181 for r in rows),low_continuum_measurements=sum(r['local_continuum_low'] for r in rows),all_input_ERR_missing=all(r['finite_positive_ERR_samples']==0 for r in checks),events_without_other_epoch=sum(r['other_epochs']==0 for r in summaries),events_with_berv_span_below_one_resolution_element=sum(r['frame_separation_below_one_resolution_element'] for r in summaries),new_observations=0,origin_classifications=0,repeat_classifications=0,plan_sha256=sha(OUT/'PLAN.json'),script_sha256=sha(Path(__file__)),source_hashes_unchanged=True,limitations=plan['interpretation'])
    atomic_json(OUT/'SUMMARY.json',summary)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
