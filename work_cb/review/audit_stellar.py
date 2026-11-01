"""Independent CB numerical audit: sorted medians and explicit graph traversal.

Does not import production analysis. Reads SIGPROC header independently, computes
normalization and all time/frequency masks in channel blocks, uses sorted-window
medians instead of SciPy median_filter, and audits component catalogs via BFS.
"""
from pathlib import Path
import argparse,csv,hashlib,json,math,time
from collections import deque
import numpy as np
from header_review import read_header,EXPECTED_SHA

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def median_sorted(a,axis):
    s=np.sort(a,axis=axis);n=a.shape[axis]
    if n%2:return np.take(s,n//2,axis=axis)
    return (np.take(s,n//2-1,axis=axis)+np.take(s,n//2,axis=axis))/2

def sliding_median(a,width):
    h=width//2;out=np.empty_like(a);padded=np.pad(a,(h,h),mode='edge')
    for lo in range(0,len(a),1024):
        hi=min(lo+1024,len(a))
        views=np.lib.stride_tricks.sliding_window_view(padded[lo:hi+2*h],width)
        out[lo:hi]=np.sort(views,axis=1)[:,h]
    return out

def csv_rows(path):
    with path.open(newline='') as f:return list(csv.DictReader(f))

def assert_fields(actual,expected):
    assert set(actual)==set(expected),(set(actual),set(expected))
    for k,v in actual.items():
        q=expected[k]
        if isinstance(v,(int,np.integer)):assert v==int(q),(k,v,q)
        else:assert v==float(q),(k,v,q)

def run(production,out):
    started=time.monotonic();root=Path(__file__).resolve().parents[2]
    scope_path=root/'work_cb/SCOPE_CB.json';scope=json.loads(scope_path.read_text())
    freeze=json.loads((root/'work_cb/PUBLIC_FREEZE_CB.json').read_text())
    assert freeze['scope_sha256']==sha(scope_path)
    assert freeze['program_sha256']==sha(root/'work_cb/analyze_stellar.py')
    source=root/scope['input']['path'];h=read_header(source)
    assert sha(source)==EXPECTED_SHA
    bound=[source,scope_path,root/'work_cb/PUBLIC_FREEZE_CB.json',root/'work_cb/analyze_stellar.py']+sorted(production.glob('*'))
    before={str(p.relative_to(root)):sha(p) for p in bound if p.is_file()}
    result=json.loads((production/'RESULT_CB.json').read_text())
    with np.load(production/'STATISTICS_CB.npz',allow_pickle=False) as z:stored={k:z[k] for k in z.files}
    nc=h['nchans'];nt=(source.stat().st_size-h['header_bytes'])//(4*nc)
    raw=np.memmap(source,mode='r',dtype='<f4',offset=h['header_bytes'],shape=(nt,nc))
    assert np.isfinite(raw).all() and (raw>=0).all()
    quality={'nonfinite_samples':int(np.count_nonzero(~np.isfinite(raw))),'negative_samples':int(np.count_nonzero(raw<0)),
             'zero_samples':int(np.count_nonzero(raw==0)),'minimum':float(raw.min()),'maximum':float(raw.max())}
    assert quality==result['quality']
    row_med=np.asarray([median_sorted(raw[t].astype(np.float64),0) for t in range(nt)])
    assert np.isfinite(row_med).all() and (row_med>0).all()
    spectrum=np.empty(nc);tscale=np.empty(nc);tvalid=np.zeros(nc,dtype=bool);tmask=np.empty((nt,nc),dtype=bool)
    tmaxrow=np.full(nt,-np.inf);tmaxcol=np.empty(nc)
    tscore_arrays=[]
    for lo in range(0,nc,1024):
        hi=min(lo+1024,nc)
        norm=raw[:,lo:hi].astype(np.float64)/row_med[:,None]
        assert np.isfinite(norm).all()
        med=median_sorted(norm,0);scale=1.4826*median_sorted(np.abs(norm-med),0)
        valid=np.isfinite(scale)&(scale>0)&(med>0)
        scores=np.full_like(norm,np.nan);scores[:,valid]=(norm[:,valid]-med[valid])/scale[valid]
        assert np.isfinite(scores[:,valid]).all()
        spectrum[lo:hi]=med;tscale[lo:hi]=scale;tvalid[lo:hi]=valid
        tmask[:,lo:hi]=valid[None,:]&(scores>=scope['temporal']['threshold'])
        # Only retain flagged scalar scores for independent component summaries.
        rr,cc=np.nonzero(tmask[:,lo:hi]);tscore_arrays.append((rr,cc+lo,scores[rr,cc]))
        tmaxrow=np.fmax(tmaxrow,np.nanmax(scores,axis=1));tmaxcol[lo:hi]=np.nanmax(scores,axis=0)
    tmaxrow[tmaxrow==-np.inf]=np.nan
    window=scope['spectral']['window_channels'];baseline=sliding_median(spectrum,window)
    assert np.isfinite(baseline).all() and (baseline>0).all()
    residual=spectrum/baseline-1;center=sliding_median(residual,window)
    scale=1.4826*sliding_median(np.abs(residual-center),window)
    valid=np.isfinite(residual)&np.isfinite(center)&np.isfinite(scale)&(scale>0)
    edge=scope['spectral']['excluded_each_edge'];valid[:edge]=False;valid[-edge:]=False
    scores=np.full(nc,np.nan);scores[valid]=(residual[valid]-center[valid])/scale[valid]
    assert np.isfinite(scores[valid]).all()
    mask=valid&(scores>=scope['spectral']['threshold'])
    freq=h['fch1']+np.arange(nc)*h['foff']
    row_center=float(median_sorted(row_med,0));row_scale=float(1.4826*median_sorted(np.abs(row_med-row_center),0))
    row_scores=(row_med-row_center)/row_scale if row_scale>0 else np.full(nt,np.nan)
    calculated={'frequency_MHz':freq,'row_medians':row_med,'row_scores':row_scores,'median_normalized_spectrum':spectrum,
      'spectral_baseline':baseline,'spectral_residual':residual,'spectral_residual_center':center,
      'spectral_scale':scale,'spectral_valid':valid,'spectral_scores':scores,'spectral_mask':mask,
      'temporal_median':spectrum,'temporal_scale':tscale,'temporal_valid_channels':tvalid,
      'temporal_mask_packed':np.packbits(tmask.ravel()),'temporal_mask_shape':np.array(tmask.shape),
      'temporal_count_by_row':tmask.sum(axis=1),'temporal_count_by_channel':tmask.sum(axis=0),
      'temporal_max_by_row':tmaxrow,'temporal_max_by_channel':tmaxcol}
    errors={}
    assert set(calculated)==set(stored)
    for key,a in calculated.items():
        b=stored[key];assert a.shape==b.shape
        assert np.array_equal(a,b,equal_nan=True),key
        errors[key]=0.0
    spectral=[]
    flagged=np.flatnonzero(mask)
    for sequence in np.split(flagged,np.flatnonzero(np.diff(flagged)>1)+1):
        if len(sequence)==0:continue
        start=int(sequence[0]);stop=int(sequence[-1])+1
        peak=start+int(np.argmax(scores[start:stop]))
        spectral.append({'component':len(spectral)+1,'first_channel':start,'last_channel':stop-1,
            'channels':stop-start,'peak_channel':peak,'peak_frequency_MHz':float(freq[peak]),'peak_score':float(scores[peak]),
            'peak_normalized_power':float(spectrum[peak]),'median_peak_power':float(median_sorted(raw[:,peak].astype(np.float64)/row_med,0))})
    expected_spectral=csv_rows(production/'SPECTRAL_FEATURES_CB.csv')
    assert len(expected_spectral)==len(spectral)
    for a,b in zip(spectral,expected_spectral):assert_fields(a,b)
    # No shared connected-component library: explicit 8-neighbour BFS.
    values={int(r)*nc+int(c):float(v) for rr,cc,vv in tscore_arrays for r,c,v in zip(rr,cc,vv)}
    unseen=set(values);temporal=[]
    for seed in sorted(values):
        if seed not in unseen:continue
        unseen.remove(seed);queue=deque([seed]);cells=[]
        while queue:
            x=queue.popleft();cells.append(x);r,c=divmod(x,nc)
            for dr in (-1,0,1):
                for dc in (-1,0,1):
                    nr,ncol=r+dr,c+dc
                    if (dr or dc) and 0<=nr<nt and 0<=ncol<nc:
                        y=nr*nc+ncol
                        if y in unseen:unseen.remove(y);queue.append(y)
        peak=max(cells,key=lambda p:(values[p],-p));pr,pc=divmod(peak,nc)
        rows=[p//nc for p in cells];cols=[p%nc for p in cells]
        temporal.append({'component':len(temporal)+1,'pixels':len(cells),'first_row':min(rows),'last_row':max(rows),
            'first_channel':min(cols),'last_channel':max(cols),'peak_row':pr,'peak_channel':pc,
            'peak_time_seconds':float(pr*h['tsamp']),'peak_frequency_MHz':float(freq[pc]),'peak_score':values[peak]})
    expected_temporal=csv_rows(production/'TEMPORAL_FEATURES_CB.csv')
    assert len(expected_temporal)==len(temporal)
    for a,b in zip(temporal,expected_temporal):assert_fields(a,b)
    hi_mask=(freq>=scope['context_window_MHz'][0])&(freq<=scope['context_window_MHz'][1])&valid
    candidates=np.flatnonzero(hi_mask);hi=int(candidates[np.argmax(residual[candidates])])
    assert result['fixed_HI_context_peak']['channel']==hi
    assert result['fixed_HI_context_peak']['frequency_MHz']==float(freq[hi])
    assert result['fixed_HI_context_peak']['fractional_local_excess']==float(residual[hi])
    assert result['fixed_HI_context_peak']['score']==float(scores[hi])
    assert result['samples']==nt*nc and result['shape']==[nt,nc]
    assert result['spectral_eligible_channels']==int(valid.sum())
    assert result['spectral_flagged_channels']==int(mask.sum()) and result['spectral_components']==len(spectral)
    assert result['temporal_flagged_pixels']==len(values) and result['temporal_components']==len(temporal)
    assert result['temporal_supported_channels']==int(tvalid.sum())
    assert result['spectral_top20']==sorted(spectral,key=lambda x:-x['peak_score'])[:20]
    assert result['temporal_top20']==sorted(temporal,key=lambda x:-x['peak_score'])[:20]
    assert result['broadband_row_median_min']==float(row_med.min()) and result['broadband_row_median_max']==float(row_med.max())
    assert result['broadband_rows_above12']==int(np.sum(row_scores>=12))
    assert all(sha(root/p)==digest for p,digest in before.items())
    report={'schema':'SETI_CB_INDEPENDENT_NUMERICAL_REVIEW_V1','status':'PASS_COMPLETE_NUMERICAL_REVIEW',
      'power_samples_checked':nt*nc,'all_statistics_arrays_exact':True,'array_maximum_absolute_errors':errors,
      'spectral_flagged_channels':int(mask.sum()),'spectral_components_verified':len(spectral),
      'temporal_flagged_pixels':len(values),'temporal_components_verified':len(temporal),
      'spectral_edge_exclusion_each_side':edge,'all_catalogue_fields_verified':True,
      'raw_file_sha256':EXPECTED_SHA,'bound_input_output_hashes':before,'bound_bytes_unchanged':True,
      'reviewer_sha256':sha(__file__),'independent_header_reader_sha256':sha(Path(__file__).parent/'header_review.py'),
      'methods':['Independent SIGPROC header parser; payload identity bound by Git blob and SHA256.',
        'Sorted medians in1024-channel blocks; explicit padded sorted windows instead of SciPy median_filter.',
        'Every spectral score,temporal mask cell,row/channel statistic independently regenerated.',
        'Explicit eight-neighbour BFS instead of SciPy label; all component fields and top20 ordering checked.'],
      'limits':['Shared NumPy float64 arithmetic and raw float32 representation.','Robust scores are descriptive,not calibrated sigma or false-alarm rates.',
        'One coarse-resolution historical stellar scan lacks OFF controls; no extraterrestrial candidate or narrowband sensitivity qualification.'],
      'wall_seconds':time.monotonic()-started}
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['status','power_samples_checked','spectral_components_verified','temporal_components_verified','wall_seconds']}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--production',required=True,type=Path);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();run(args.production.resolve(),args.out.resolve())
