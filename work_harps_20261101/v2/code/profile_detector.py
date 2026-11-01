"""Instrument-width emission profiles; exploratory scores, not Gaussian significance.

Independent implementation. V1 and its results are unchanged. All screened
events, including profile rejections and duplicate fits, remain in the output.
"""
from __future__ import annotations
import numpy as np
from scipy.ndimage import median_filter

DEFAULTS = dict(wave_min_angstrom=3800., wave_max_angstrom=6900., window_pixels=101,
    prescreen_local_mad=3., amplitude_over_sideband_mad=6., minimum_profile_cosine=0.8,
    resolving_power=115000., core_half_pixels=12, sideband_outer_pixels=50,
    fit_phases=[-0.5,-0.25,0.,0.25,0.5], mad_normalization=1.4826,
    gap_step_multiple=1.5)

def runs(mask):
    d=np.diff(np.r_[False,mask,False].astype(int))
    return list(zip(np.flatnonzero(d==1).tolist(),np.flatnonzero(d==-1).tolist()))

def fit_profile(w,f,k,cfg):
    """Robust sideband line and positive fixed-width profile, no core noise samples."""
    inner,outer=cfg['core_half_pixels'],cfg['sideband_outer_pixels']
    offsets=np.r_[np.arange(-outer,-inner),np.arange(inner+1,outer+1)]
    x=offsets.astype(float); side=f[k+offsets]
    left=x<0;right=x>0
    slope=(np.median(side[right])-np.median(side[left]))/(np.median(x[right])-np.median(x[left]))
    intercept=float(np.median(side-slope*x))
    residual_side=side-intercept-slope*x
    noise=float(cfg['mad_normalization']*np.median(np.abs(residual_side-np.median(residual_side))))
    core=np.arange(-inner,inner+1)
    residual=f[k+core]-intercept-slope*core
    step=float(np.median(np.diff(w[k-outer:k+outer+1])))
    fwhm=float(w[k]/cfg['resolving_power'])
    sigma=fwhm/(2*np.sqrt(2*np.log(2)))
    best=None
    for phase in cfg['fit_phases']:
        center=float(w[k]+phase*step)
        g=np.exp(-.5*((w[k+core]-center)/sigma)**2)
        gg=float(g@g);rg=float(residual@g)
        amp=max(0.,rg/gg)
        explained=amp*amp*gg
        cosine=rg/np.sqrt(gg*float(residual@residual)) if residual@residual>0 else 0.
        candidate=dict(fitted_center_angstrom=center,phase=float(phase),amplitude_adu=amp,
            profile_cosine=float(cosine),profile_explained_square_adu=explained)
        # First phase wins exact ties; phases are an explicitly ordered grid.
        if best is None or explained>best['profile_explained_square_adu']:best=candidate
    best.update(seed_index=int(k),seed_wave_angstrom=float(w[k]),sideband_intercept_adu=intercept,
        sideband_slope_adu_per_pixel=float(slope),sideband_mad_adu=noise,
        fwhm_model_angstrom=fwhm,amplitude_over_sideband_mad=best['amplitude_adu']/noise if noise>0 else None)
    reasons=[]
    if not np.isfinite(noise) or noise<=0:reasons.append('INVALID_SIDEBAND_SCALE')
    elif best['amplitude_over_sideband_mad']<cfg['amplitude_over_sideband_mad']:reasons.append('LOW_AMPLITUDE')
    if best['profile_cosine']<cfg['minimum_profile_cosine']:reasons.append('PROFILE_MISMATCH')
    best.update(status='REJECTED' if reasons else 'PRELIMINARY_PROFILE_HIT',reasons=reasons)
    return best

def analyze_arrays(wave,flux,config=None):
    cfg=DEFAULTS|(config or {})
    w=np.asarray(wave,dtype=float);f=np.asarray(flux,dtype=float)
    if w.ndim!=1 or f.shape!=w.shape or len(w)<cfg['window_pixels']:raise ValueError('Invalid array shape')
    if not np.all(np.isfinite(w)) or np.any(np.diff(w)<=0):raise ValueError('Wavelength must be finite and increasing')
    if cfg['window_pixels']!=101 or cfg['sideband_outer_pixels']!=50:raise ValueError('This implementation fixes the supported 101-pixel neighborhood')
    step=float(np.median(np.diff(w)))
    valid=np.isfinite(f)&(f!=0)&(w>=cfg['wave_min_angstrom'])&(w<=cfg['wave_max_angstrom'])
    cuts=set((np.flatnonzero(np.diff(w)>cfg['gap_step_multiple']*step)+1).tolist())
    searched=np.zeros(len(w),dtype=bool);continuum=np.full(len(w),np.nan);scale=continuum.copy()
    # The prescreen is two nested 101-sample filters, requiring a 100-bin
    # margin for complete support. The final fit itself uses +/-50 bins.
    events=[];margin=cfg['window_pixels']-1
    for a,b in runs(valid):
        edges=[a]+sorted(c for c in cuts if a<c<b)+[b]
        for start,end in zip(edges[:-1],edges[1:]):
            if end-start<2*margin+1:continue
            values=f[start:end]
            med=median_filter(values,size=101,mode='nearest')
            resid=values-med
            mad=cfg['mad_normalization']*median_filter(np.abs(resid),size=101,mode='nearest')
            continuum[start:end]=med;scale[start:end]=mad
            searched[start+margin:end-margin]=np.isfinite(mad[margin:-margin])&(mad[margin:-margin]>0)
            # Strict on left, non-strict on right: first point of a plateau.
            localmax=np.r_[False,(resid[1:-1]>resid[:-2])&(resid[1:-1]>=resid[2:]),False]
            seeds=np.flatnonzero(localmax&(resid>=cfg['prescreen_local_mad']*mad)&searched[start:end])
            for j in seeds:
                event=fit_profile(w,f,start+int(j),cfg)
                event['prescreen_residual_over_mad']=float(resid[j]/mad[j])
                events.append(event)
    # Suppress duplicate accepted fits within one model FWHM; retain audit rows.
    accepted=[]
    for e in sorted((e for e in events if e['status']=='PRELIMINARY_PROFILE_HIT'),
                    key=lambda e:(-e['amplitude_over_sideband_mad'],e['seed_index'])):
        parent=next((p for p in accepted if abs(e['fitted_center_angstrom']-p['fitted_center_angstrom'])<=max(e['fwhm_model_angstrom'],p['fwhm_model_angstrom'])),None)
        if parent is not None:
            e['status']='DUPLICATE_FIT';e['reasons']=['WITHIN_ONE_FWHM_OF_STRONGER_FIT'];e['parent_seed_index']=parent['seed_index']
        else:accepted.append(e)
    events.sort(key=lambda e:e['seed_index'])
    intervals=[dict(first_index=a,last_index_exclusive=b,first_center_angstrom=float(w[a]),last_center_angstrom=float(w[b-1]),centers=b-a) for a,b in runs(searched)]
    return dict(schema='HARPS_PROFILE_V2',config=cfg,total_samples=len(w),searched_samples=int(searched.sum()),
        sum_searched_bin_widths_angstrom=float(searched.sum()*step),searched_intervals=intervals,
        screened_events=len(events),preliminary_hit_count=len(accepted),events=events,
        interpretation='Profile and amplitude scores are exploratory, not calibrated significance/SNR/FAP; accepted events are not identified lasers.'),dict(wave=w,flux=f,searched=searched,continuum=continuum,prescreen_mad=scale)
