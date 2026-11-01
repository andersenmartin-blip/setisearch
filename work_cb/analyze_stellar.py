"""CB: descriptive native-resolution spectral and temporal feature search."""
from pathlib import Path
import argparse,csv,hashlib,json,math,os,signal,time
import numpy as np
from scipy.ndimage import median_filter,label,find_objects

ROOT=Path(__file__).resolve().parents[1]
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save_json(p,d):
    with Path(p).open('x') as f:json.dump(d,f,indent=2,allow_nan=False);f.write('\n')

def spectral_analysis(spectrum,window,excluded_each_edge):
    baseline=median_filter(spectrum,size=window,mode='nearest')
    assert np.isfinite(baseline).all() and np.all(baseline>0),'Invalid spectral baseline'
    residual=np.divide(spectrum,baseline,out=np.full_like(spectrum,np.nan),where=baseline>0)-1
    center=median_filter(residual,size=window,mode='nearest')
    scale=1.4826*median_filter(np.abs(residual-center),size=window,mode='nearest')
    valid=np.isfinite(residual)&np.isfinite(center)&np.isfinite(scale)&(scale>0)
    h=excluded_each_edge;valid[:h]=False;valid[-h:]=False
    score=np.divide(residual-center,scale,out=np.full_like(spectrum,np.nan),where=valid)
    assert np.isfinite(score[valid]).all(),'Invalid spectral scores'
    return baseline,residual,center,scale,valid,score

def groups_1d(mask,score,spectrum,freq,normalized):
    labels,n=label(mask);groups=[]
    for i,slices in enumerate(find_objects(labels),start=1):
        sl=slices[0];start,stop=sl.start,sl.stop
        peak=start+int(np.argmax(score[sl]));col=normalized[:,peak]
        groups.append({'component':i,'first_channel':start,'last_channel':stop-1,
            'channels':stop-start,'peak_channel':peak,'peak_frequency_MHz':float(freq[peak]),
            'peak_score':float(score[peak]),'peak_normalized_power':float(spectrum[peak]),
            'median_peak_power':float(np.median(col))})
    return groups

def groups_2d(mask,scores,freq,dt):
    labels,n=label(mask,structure=np.ones((3,3),dtype=np.int8));groups=[]
    for i,slices in enumerate(find_objects(labels),start=1):
        t,f=slices;local=labels[t,f]==i;selected=np.where(local,scores[t,f],-np.inf)
        ti,fi=np.unravel_index(np.argmax(selected),selected.shape);ti=int(ti)+t.start;fi=int(fi)+f.start
        groups.append({'component':i,'pixels':int(local.sum()),'first_row':t.start,'last_row':t.stop-1,
            'first_channel':f.start,'last_channel':f.stop-1,'peak_row':ti,'peak_channel':fi,
            'peak_time_seconds':float(ti*dt),'peak_frequency_MHz':float(freq[fi]),
            'peak_score':float(scores[ti,fi])})
    return groups

def run(scope_path,out):
    start=time.monotonic();scope=json.loads(scope_path.read_text());out.mkdir(parents=True,exist_ok=False)
    freeze=json.loads((ROOT/'work_cb/PUBLIC_FREEZE_CB.json').read_text())
    assert freeze['scope_sha256']==digest(scope_path)
    assert freeze['program_sha256']==digest(__file__)
    raw=ROOT/scope['input']['path'];before=digest(raw);assert before==scope['input']['sha256']
    assert digest(ROOT/scope['input']['header'])==scope['input']['header_sha256']
    h=json.loads((ROOT/scope['input']['header']).read_text());nt=h['complete_time_rows'];nc=h['nchans']
    assert raw.stat().st_size==h['header_bytes']+nt*nc*4,'Payload size differs'
    a=np.memmap(raw,mode='r',dtype='<f4',offset=h['header_bytes'],shape=(nt,nc))
    quality={'nonfinite_samples':int(np.count_nonzero(~np.isfinite(a))),
             'negative_samples':int(np.count_nonzero(a<0)),'zero_samples':int(np.count_nonzero(a==0)),
             'minimum':float(np.min(a)),'maximum':float(np.max(a))}
    assert quality['nonfinite_samples']==0 and quality['negative_samples']==0,'Input quality gate failed'
    row_med=np.median(a.astype(np.float64),axis=1);assert np.all(row_med>0),'Invalid row gain'
    norm=a.astype(np.float64)/row_med[:,None]
    assert np.isfinite(norm).all(),'Nonfinite normalized power'
    spectrum=np.median(norm,axis=0)
    baseline,residual,center,scale,valid,score=spectral_analysis(spectrum,scope['spectral']['window_channels'],scope['spectral']['excluded_each_edge'])
    spec_mask=valid&(score>=scope['spectral']['threshold'])
    freq=h['fch1']+np.arange(nc)*h['foff'];dt=h['tsamp']
    spec_groups=groups_1d(spec_mask,score,spectrum,freq,norm)
    tmed=np.median(norm,axis=0);tscale=1.4826*np.median(np.abs(norm-tmed),axis=0)
    tvalid=np.isfinite(tscale)&(tscale>0)&(tmed>0)
    tscores=np.divide(norm-tmed,tscale,out=np.full_like(norm,np.nan),where=tvalid[None,:])
    assert np.isfinite(tscores[:,tvalid]).all(),'Invalid temporal scores'
    tmask=tvalid[None,:]&(tscores>=scope['temporal']['threshold'])
    temporal_groups=groups_2d(tmask,tscores,freq,dt)
    row_center=float(np.median(row_med));row_scale=float(1.4826*np.median(np.abs(row_med-row_center)))
    row_scores=(row_med-row_center)/row_scale if row_scale>0 else np.full(nt,np.nan)
    hin=(freq>=scope['context_window_MHz'][0])&(freq<=scope['context_window_MHz'][1])&valid
    hi_idx=np.flatnonzero(hin);hi=hi_idx[np.argmax(residual[hi_idx])]
    arrays={'frequency_MHz':freq,'row_medians':row_med,'row_scores':row_scores,'median_normalized_spectrum':spectrum,
            'spectral_baseline':baseline,'spectral_residual':residual,'spectral_residual_center':center,
            'spectral_scale':scale,'spectral_valid':valid,'spectral_scores':score,'spectral_mask':spec_mask,
            'temporal_median':tmed,'temporal_scale':tscale,'temporal_valid_channels':tvalid,
            'temporal_mask_packed':np.packbits(tmask.ravel()),'temporal_mask_shape':np.array(tmask.shape),
            'temporal_count_by_row':tmask.sum(axis=1),'temporal_count_by_channel':tmask.sum(axis=0),
            'temporal_max_by_row':np.nanmax(tscores,axis=1),'temporal_max_by_channel':np.nanmax(tscores,axis=0)}
    np.savez_compressed(out/'STATISTICS_CB.npz',**arrays)
    for name,rows in [('SPECTRAL_FEATURES_CB.csv',spec_groups),('TEMPORAL_FEATURES_CB.csv',temporal_groups)]:
        with (out/name).open('x',newline='') as f:
            if rows:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    s={'schema':'SETI_CB_STELLAR_NATIVE_FEATURE_RESULT_V1','status':'COMPLETED_AWAITING_INDEPENDENT_REVIEW',
       'scope_sha256':digest(scope_path),'program_sha256':digest(__file__),'input_sha256':before,
       'public_scope_commit':freeze['public_commit'],'target':h['source_name'],'mjd':h['tstart'],
       'shape':[nt,nc],'samples':int(nt*nc),'quality':quality,'integration_seconds':float(nt*dt),
       'sample_span_seconds':float((nt-1)*dt),'channel_width_Hz':abs(h['foff'])*1e6,
       'input_bandwidth_MHz':abs(h['foff'])*nc,'center_frequency_range_MHz':[float(freq.min()),float(freq.max())],
       'spectral_eligible_channels':int(valid.sum()),'spectral_flagged_channels':int(spec_mask.sum()),
       'spectral_components':len(spec_groups),'spectral_top20':sorted(spec_groups,key=lambda x:-x['peak_score'])[:20],
       'temporal_supported_channels':int(tvalid.sum()),'temporal_flagged_pixels':int(tmask.sum()),
       'temporal_components':len(temporal_groups),'temporal_top20':sorted(temporal_groups,key=lambda x:-x['peak_score'])[:20],
       'broadband_row_median_min':float(row_med.min()),'broadband_row_median_max':float(row_med.max()),
       'broadband_row_score_supported':row_scale>0,'broadband_rows_above12':int(np.sum(row_scores>=12)),
       'fixed_HI_context_peak':{'channel':int(hi),'frequency_MHz':float(freq[hi]),
            'fractional_local_excess':float(residual[hi]),'score':float(score[hi]),
            'interpretation':'Peak in predefined1419.5–1421.5MHz context window; not independent source identification.'},
       'row_gain_removal_hides_broadband_changes':True,
       'max4Hz_s_drift_over_sample_span_channels':float(4*(nt-1)*dt/(abs(h['foff'])*1e6)),
       'new_stellar_observation_file_analyzed':1,'new_telescope_observations':0,
       'complete_ON_OFF_sequences':0,'SETI_candidates_qualified':0,
       'qualified_narrowband_drift_sensitivity':False,'original_BA_authority_unchanged':True,
       'limitations':scope['limitations'],'files_sha256':{p.name:digest(p) for p in out.iterdir() if p.is_file()},
       'wall_seconds':time.monotonic()-start}
    assert digest(raw)==before,'Input changed'
    save_json(out/'RESULT_CB.json',s)
    print(json.dumps({k:s[k] for k in ['target','samples','spectral_components','temporal_components','temporal_flagged_pixels','fixed_HI_context_peak','wall_seconds']}),flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--scope',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    def timed_out(s,f):raise TimeoutError('CB 600-second budget')
    signal.signal(signal.SIGALRM,timed_out);signal.alarm(600);run(a.scope,a.out);signal.alarm(0)
