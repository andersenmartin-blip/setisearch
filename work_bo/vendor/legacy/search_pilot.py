#!/usr/bin/env python3
"""Transparent finite-grid archival SETI engineering/discovery pilot.

No sky-origin inference or Gaussian false-alarm calibration is implemented.
Frequencies are topocentric as supplied by the SIGPROC header. See PROTOCOL.md.
"""
from __future__ import annotations
import argparse, hashlib, json, math, os, resource, time
from pathlib import Path
import numpy as np
from scipy.ndimage import maximum_filter1d

VERSION = 'newarchive-linear-ess-v1'
DEFAULTS = dict(max_abs_drift_hz_s=4.0, widths_channels=[1,3,9,33],
                frequency_strides=[1,1,2,8], threshold_ess=10.0,
                off_flag_threshold_ess=5.0, bandpass_block_channels=4096,
                maximum_saved_local_hits=1000000, top_diagnostics_per_width=4,
                boundary_halo_channels=4096)

def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1024*1024), b''): h.update(b)
    return h.hexdigest()

def write_json(path,obj):
    Path(path).write_text(json.dumps(obj,indent=2,sort_keys=True,allow_nan=False)+'\n')

def normalize(raw, block=4096):
    """Rowwise piecewise-constant spectral median/MAD; no time subtraction.

    Each row/block gets its own median and 1.4826 MAD. All stored columns,
    including halo, contribute to normalization; only the fixed core is searched.
    Invalid values/scales are fatal rather than silently losing trial coverage.
    """
    x=np.asarray(raw,dtype=np.float32)
    if x.ndim!=2 or x.shape[0]<2: raise ValueError('Require >=2 time rows and one frequency dimension')
    if not np.isfinite(x).all(): raise ValueError('Non-finite raw power')
    y=np.empty_like(x); rows=[]
    for lo in range(0,x.shape[1],block):
        hi=min(lo+block,x.shape[1]); a=x[:,lo:hi]
        med=np.median(a,axis=1)
        sig=np.median(np.abs(a-med[:,None]),axis=1)*np.float32(1.4826)
        if np.any(sig<=0) or not np.isfinite(sig).all(): raise ValueError('Non-positive spectral MAD scale')
        y[:,lo:hi]=(a-med[:,None])/sig[:,None]
        rows.append(dict(channel_lo=lo,channel_hi_exclusive=hi,median=med.tolist(),mad_scale=sig.tolist()))
    return y,rows

def centered_boxcar(y,width):
    if width==1: return y
    # Float64 cumulative sum avoids accumulating large float32 subtraction error.
    cs=np.cumsum(y,axis=1,dtype=np.float64)
    cs=np.concatenate((np.zeros((y.shape[0],1)),cs),axis=1)
    sums=cs[:,width:]-cs[:,:-width]
    out=np.zeros_like(y)
    h=width//2
    out[:,h:y.shape[1]-h]=sums.astype(np.float32)
    return out

def drift_grid(nrows,dt,df,maxdrift):
    exposure_span=nrows*dt
    nside=int(math.ceil(maxdrift*exposure_span/abs(df)))
    rates=np.linspace(-maxdrift,maxdrift,2*nside+1,dtype=np.float64)
    return rates

def track_sum(y,offsets,start,stop,stride):
    """Contiguous/strided slice accumulation; exact nearest-channel tracks."""
    n=(stop-start+stride-1)//stride
    out=np.zeros(n,dtype=np.float32)
    for row,off in zip(y,offsets):
        out += row[start+int(off):stop+int(off):stride]
    return out

def oracle_sum(y,offsets,centers,width=1):
    # Independent explicit indexing and double summation for validation only.
    result=[]; h=width//2
    for c in centers:
        result.append(sum(float(y[t,int(c)+int(off)+j])
                          for t,off in enumerate(offsets)
                          for j in range(-h,h+1)))
    return np.asarray(result)

def ess_calibration(sums):
    med=float(np.median(sums))
    scale=float(1.4826*np.median(np.abs(sums-med)))
    if not math.isfinite(scale) or scale<=0: raise ValueError('Non-positive track-sum MAD')
    return med,scale

def search_array(raw,dt,df,config,output_prefix=None,save_hits=True):
    wall=time.perf_counter(); cpu=time.process_time()
    y,norm=normalize(raw,config['bandpass_block_channels'])
    nr,nc=y.shape; t=(np.arange(nr,dtype=np.float64)-(nr-1)/2)*dt
    rates=drift_grid(nr,dt,df,config['max_abs_drift_hz_s'])
    all_offsets=np.rint(rates[:,None]*t[None,:]/df).astype(np.int32)
    # Fixed margin determined prospectively, including frequency smoothing support.
    minimum_halo=int(np.max(np.abs(all_offsets)))+max(config['widths_channels'])//2
    halo=max(config['boundary_halo_channels'],minimum_halo)
    start,stop=halo,nc-halo
    if stop<=start: raise ValueError('No searched core after drift/smoothing halo')
    hits=[]; diagnostics=[]; calibration={}; maxima={}; stats=[]
    overflow=False; raw_hit_count=0; grid_exceedances=0; trials=0
    for width,stride in zip(config['widths_channels'],config['frequency_strides']):
        filtered=centered_boxcar(y,width)
        centers=np.arange(start,stop,stride,dtype=np.int32)
        best=np.full(len(centers),-np.inf,dtype=np.float32)
        best_rate=np.zeros(len(centers),dtype=np.int32)
        medscales=np.empty((len(rates),2),dtype=np.float64)
        width_hits=0; width_exceed=0; top=[]
        for ri,(rate,offsets) in enumerate(zip(rates,all_offsets)):
            sums=track_sum(filtered,offsets,start,stop,stride)
            med,scale=ess_calibration(sums); medscales[ri]=(med,scale)
            ess=(sums-med)/scale
            better=ess>best; best[better]=ess[better]; best_rate[better]=ri
            trials+=len(centers)
            width_exceed+=int(np.count_nonzero(ess>=config['threshold_ess']))
            # Local maxima in frequency. Drift-neighbor duplicates remain in the
            # complete hit list; later ranking consolidation does not affect search.
            local=maximum_filter1d(ess,size=max(3,2*int(math.ceil(width/stride))+1),mode='nearest')
            inds=np.flatnonzero((ess>=config['threshold_ess']) & (ess==local))
            width_hits+=len(inds)
            if save_hits:
                room=max(0,config['maximum_saved_local_hits']-len(hits))
                if len(inds)>room: overflow=True
                for k in inds[:room]:
                    hits.append(dict(channel_at_midpoint=int(centers[k]),drift_hz_s=float(rate),
                                     drift_index=ri,width_channels=width,ess=float(ess[k])))
            k=int(np.argmax(ess)); top.append((float(ess[k]),int(centers[k]),ri))
        for score,c,ri in sorted(top,reverse=True)[:config['top_diagnostics_per_width']]:
            diagnostics.append(dict(channel_at_midpoint=c,drift_hz_s=float(rates[ri]),
                                    drift_index=ri,width_channels=width,ess=score))
        calibration[str(width)]=medscales
        maxima[str(width)]=(centers,best,best_rate)
        raw_hit_count+=width_hits; grid_exceedances+=width_exceed
        stats.append(dict(width_channels=width,frequency_stride_channels=stride,
                          frequency_centers=len(centers),drift_trials=len(rates),
                          track_trials=len(centers)*len(rates),
                          grid_exceedances=width_exceed,local_maxima_above_threshold=width_hits,
                          maximum_ess=float(best.max())))
    if output_prefix:
        arrays={ 'drift_hz_s':rates }
        for w,a in calibration.items(): arrays['calibration_width_'+w]=a
        for w,(centers,best,best_rate) in maxima.items():
            arrays['centers_width_'+w]=centers; arrays['max_ess_width_'+w]=best; arrays['max_drift_index_width_'+w]=best_rate
        np.savez_compressed(str(output_prefix)+'_grid_summary.npz',**arrays)
    result=dict(version=VERSION,nrows=nr,nchannels_stored=nc,dt_seconds=dt,df_hz=df,
                elapsed_exposure_seconds=nr*dt,time_center_span_seconds=(nr-1)*dt,
                core_channel_start=start,core_channel_stop_exclusive=stop,
                core_channels=stop-start,core_bandwidth_hz=(stop-start)*abs(df),
                halo_channels=halo,minimum_drift_smoothing_halo=minimum_halo,
                drift_step_hz_s=float(rates[1]-rates[0]),drift_count=len(rates),
                zero_drift_included=True,width_searches=stats,track_trials=trials,
                grid_exceedances=grid_exceedances,local_hits_count=raw_hit_count,
                saved_local_hits=len(hits),hit_overflow=overflow,
                completion_status='HIT_OVERFLOW' if overflow else 'COMPLETE_FINITE_GRID',
                hits=hits,diagnostics=diagnostics,normalization=norm,
                wall_seconds=time.perf_counter()-wall,cpu_seconds=time.process_time()-cpu,
                peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return result,y,calibration,maxima,rates

def physical_injection(shape,dt,df,mid_channel,rate,amplitude=1,width=1):
    """Add nonnegative power from a uniformly emitting drift during each exposure.

    Top-hat intrinsic widths are represented as width equally spaced delta lines.
    Each delta's exposure-integrated fraction per channel is exact for linear drift.
    Amplitude is total injected normalized power per integration, not Jy or SNR.
    """
    nr,nc=shape; out=np.zeros(shape,dtype=np.float32)
    tc=(np.arange(nr)-(nr-1)/2)*dt
    for ti,t in enumerate(tc):
        for intrinsic in np.arange(width)-(width-1)/2:
            a=mid_channel+intrinsic+rate*(t-dt/2)/df
            b=mid_channel+intrinsic+rate*(t+dt/2)/df
            lo,hi=sorted([a,b])
            if hi-lo<1e-12:
                c=int(np.rint((a+b)/2))
                if 0<=c<nc: out[ti,c]+=amplitude/width
            else:
                for c in range(max(0,int(math.floor(lo-.5))),min(nc,int(math.ceil(hi+.5))+1)):
                    fraction=max(0.0,min(hi,c+.5)-max(lo,c-.5))/(hi-lo)
                    out[ti,c]+=amplitude*fraction/width
    return out

def validate_code(directory):
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(20261017)
    y=rng.normal(size=(16,4096)).astype(np.float32)
    checks=[]
    rates=[-4,-0.153,0,0.237,4]
    for width in [1,3,9,33]:
        filtered=centered_boxcar(y,width)
        for rate in rates:
            offsets=np.rint(rate*(np.arange(16)-7.5)*18.253611008/-2.7939677238464355).astype(int)
            got=track_sum(filtered,offsets,512,3584,3)
            centers=np.arange(512,3584,3)
            expected=oracle_sum(y,offsets,centers,width)
            err=float(np.max(np.abs(got-expected)))
            checks.append(dict(width=width,drift_hz_s=rate,max_abs_error=err,pass_=err<5e-5))
    # An odd row count and strided grids near both fixed core edges exercise
    # indexing cases not shared with the 16-row astronomical pilot.
    yodd=rng.normal(size=(17,4096)).astype(np.float32)
    for width,stride in [(1,1),(3,1),(9,2),(33,8)]:
        filtered=centered_boxcar(yodd,width)
        offsets=np.rint(4*(np.arange(17)-8)*18.253611008/-2.7939677238464355).astype(int)
        centers=np.arange(512,3584,stride)
        got=track_sum(filtered,offsets,512,3584,stride)
        expected=oracle_sum(yodd,offsets,centers,width)
        err=float(np.max(np.abs(got-expected)))
        checks.append(dict(width=width,drift_hz_s=4,nrows=17,stride=stride,
                           max_abs_error=err,pass_=err<5e-5))
    # Nulls are controls of code behavior; they are not astronomy false-alarm rates.
    testconfig={**DEFAULTS,'bandpass_block_channels':1024,'boundary_halo_channels':256,
                'maximum_saved_local_hits':10000}
    positive=[]
    for rate,width in [(0,1),(.05,1),(.153,1),(1,1),(-4,1),(4,3)]:
        raw=rng.normal(100,1,size=(16,4096)).astype(np.float32)
        signal=physical_injection(raw.shape,18.253611008,-2.7939677238464355,2048,rate,amplitude=80,width=width)
        r,*_=search_array(raw+signal,18.253611008,-2.7939677238464355,testconfig,save_hits=False)
        best=max(r['diagnostics'],key=lambda v:v['ess'])
        okay=(best['ess']>=10 and abs(best['channel_at_midpoint']-2048)<=33 and
              abs(best['drift_hz_s']-rate)<=.35)
        positive.append(dict(injected_rate_hz_s=rate,intrinsic_width_channels=width,
                             total_power_per_row=80, recovered=best,pass_=okay))
    phase_checks=[]
    # Random sub-channel phases and width-bank sampling phases; an arbitrary
    # source position is not restricted to a grid channel center.
    for nr,rate,phase,width in [(17,.501,.25,1),(16,-1.337,.5,3),(17,4,.75,1),
                               (16,3.991,.125,9)]:
        raw=rng.normal(100,1,size=(nr,4096)).astype(np.float32)
        mid=2048+phase
        signal=physical_injection(raw.shape,18.253611008,-2.7939677238464355,mid,rate,80,width)
        r,*_=search_array(raw+signal,18.253611008,-2.7939677238464355,testconfig,save_hits=False)
        best=max(r['diagnostics'],key=lambda v:v['ess'])
        okay=best['ess']>=10 and abs(best['channel_at_midpoint']-mid)<=33 and abs(best['drift_hz_s']-rate)<=.35
        phase_checks.append(dict(nrows=nr,injected_rate_hz_s=rate,injected_phase_channels=phase,
                                 intrinsic_width_channels=width,recovered=best,pass_=okay))
    raw=rng.normal(100,1,size=(16,8192)).astype(np.float32)
    null,*_=search_array(raw,18.253611008,-2.7939677238464355,testconfig,save_hits=False)
    mass=[]
    for r in rates:
        inj=physical_injection((16,4096),18.253611008,-2.7939677238464355,2048,r,7)
        err=float(np.max(np.abs(inj.sum(axis=1)-7)))
        mass.append(dict(drift_hz_s=r,per_row_power_error=err,pass_=err<1e-5))
    report=dict(independent_oracle=checks,positive_controls=positive,subchannel_and_width_stride_controls=phase_checks,
                exposure_integrated_injection_conservation=mass,
                null_control=dict(shape=[16,8192],seed=20261017,threshold=10,
                                  maximum_ess=max(a['maximum_ess'] for a in null['width_searches']),
                                  grid_exceedances=null['grid_exceedances'],track_trials=null['track_trials']),
                all_required_controls_pass=all(c['pass_'] for c in checks+positive+phase_checks+mass),
                caveat='Synthetic Gaussian noise validates implementation only; it does not establish astronomical false-alarm rates.')
    write_json(directory/'implementation_validation.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='independent_oracle'},indent=2))
    if not report['all_required_controls_pass']: raise RuntimeError('Validation failed')

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--validate',type=Path)
    a=p.parse_args()
    if a.validate: validate_code(a.validate)
