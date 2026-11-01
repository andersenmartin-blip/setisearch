"""Candidate-excluded local continuum-position audit, no origin classifier."""
import numpy as np
from scipy.ndimage import median_filter
from registration import trace_polynomial

def evaluate_local_trace(raw,native,header,order,k,best,candidates):
    windows=[]
    for lo,hi in [(-280,-80),(81,281)]:
        x=np.arange(max(0,k+lo),min(4096,k+hi))
        for hit in candidates:
            if hit['order']==order:x=x[abs(x-hit['native_pixel'])>80]
        yy=4095-x if best['row_flip'] else x
        tc=trace_polynomial(header,order,x,best['argument_flip'])
        if best['column_flip']:tc=4095-tc
        cx=np.rint(tc).astype(int)
        valid=(cx>=5)&(cx<4091);x=x[valid];yy=yy[valid];cx=cx[valid]
        r=dict(relative_interval_half_open=[lo,hi],samples=len(x),peak_offset=None,correlation=None,profile=None)
        if len(x)>=60:
            profile=np.median(np.stack([raw[yy,cx+j] for j in range(-5,6)]),axis=1)
            peak=int(np.argmax(profile));offset=float(peak-5)
            if 0<peak<10:
                a,b,c=profile[peak-1:peak+2];den=a-2*b+c
                if den!=0:offset+=float(.5*(a-c)/den)
            ref=native[order,x];val=np.stack([raw[yy,cx+j] for j in range(-3,4)]).sum(axis=0)
            ref=ref-median_filter(ref,size=31,mode='nearest');val=val-median_filter(val,size=31,mode='nearest')
            cc=float(np.corrcoef(ref,val)[0,1])
            r.update(peak_offset=offset,correlation=cc if np.isfinite(cc) else None,profile=profile.tolist())
        windows.append(r)
    usable=all(r['peak_offset'] is not None and abs(r['peak_offset'])<=1 for r in windows)
    return dict(windows=windows,local_mapping_usable=usable,visual_local_mapping_warning=not usable)
