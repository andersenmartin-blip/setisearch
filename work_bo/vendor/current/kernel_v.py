"""Versioned saved-native candidate: local float64 sums with guarded sparse fsum."""
import math
import numpy as np

VERSION='v-native-streaming-f64-local-guarded-v1'
WIDTHS=(1,3,9,33)
TOLERANCE=5e-5

def boxcars(y,width):
    y=np.asarray(y)
    if y.dtype!=np.float32 or y.ndim!=2 or not np.isfinite(y).all():raise ValueError('Finite float32 normalized matrix required')
    if width not in WIDTHS or width>y.shape[1]:raise ValueError('Unsupported width')
    nr,nc=y.shape;unit=np.finfo(np.float64).eps/2;n=nr+width+2;gamma=n*unit/(1-n*unit)
    # Twice the pointwise-bound headroom, even if every term equals the global
    # maximum. A passing global bound can skip the absolute-magnitude matrix;
    # a failed bound never sends every point automatically to scalar fsum.
    global_bound=float(np.nextafter(16*gamma*nr*width*float(np.max(np.abs(y))),np.inf))
    if width==1:filtered=y
    else:
        filtered=np.zeros(y.shape,dtype=np.float64);h=width//2
        for t,row in enumerate(y):filtered[t,h:nc-h]=np.convolve(row.astype(np.float64),np.ones(width,dtype=np.float64),mode='valid')
    absolute=None
    if global_bound>TOLERANCE/4:
        absolute=np.zeros(y.shape,dtype=np.float64);h=width//2;dest=slice(h,nc-h if h else None)
        for t,row in enumerate(y):absolute[t,dest]=np.convolve(np.abs(row.astype(np.float64)),np.ones(width,dtype=np.float64),mode='valid')
    return filtered,absolute,global_bound,float(gamma)

def _validate(y,off,centers,width):
    off=np.asarray(off);centers=np.asarray(centers)
    if off.shape!=(len(y),) or off.dtype.kind not in 'iu' or centers.ndim!=1 or centers.dtype.kind not in 'iu':raise ValueError('Integer offsets and center vector required')
    if width not in WIDTHS:raise ValueError('Unsupported width')
    h=width//2
    if len(centers) and (int(centers.min())+int(off.min())-h<0 or int(centers.max())+int(off.max())+h>=y.shape[1]):raise ValueError('Requested track outside stored support')
    return off,centers

def _finish(y,off,centers,width,total,magnitude,global_bound,gamma):
    if magnitude is None:
        fallback=np.zeros(len(centers),dtype=np.bool_);maximum_bound=global_bound
    else:
        bound=np.nextafter(8*gamma*magnitude,np.inf)
        fallback=bound>TOLERANCE/4;maximum_bound=float(bound.max(initial=0.))
        h=width//2
        for k in np.flatnonzero(fallback):
            c=int(centers[k]);total[k]=math.fsum(float(y[t,c+int(o)+j]) for t,o in enumerate(off) for j in range(-h,h+1))
    if not np.isfinite(total).all():raise ValueError('Nonfinite track sum')
    return total,int(fallback.sum()),maximum_bound

def tracks_selected(y,prepared,off,centers,width):
    off,centers=_validate(y,off,centers,width);filtered,absolute,global_bound,gamma=prepared
    total=np.zeros(len(centers),dtype=np.float64);magnitude=None if absolute is None else np.zeros_like(total)
    for t,o in enumerate(off):
        idx=centers+int(o);total+=filtered[t,idx]
        if magnitude is not None:magnitude+=absolute[t,idx]
    return _finish(y,off,centers,width,total,magnitude,global_bound,gamma)

def tracks_grid(y,prepared,off,start,stop,stride,width):
    if not isinstance(stride,int) or stride<=0:raise ValueError('Positive integer stride required')
    centers=np.arange(start,stop,stride,dtype=np.int32);off,centers=_validate(y,off,centers,width)
    filtered,absolute,global_bound,gamma=prepared
    total=np.zeros(len(centers),dtype=np.float64);magnitude=None if absolute is None else np.zeros_like(total)
    for t,o in enumerate(off):
        total+=filtered[t,start+int(o):stop+int(o):stride]
        if magnitude is not None:magnitude+=absolute[t,start+int(o):stop+int(o):stride]
    return _finish(y,off,centers,width,total,magnitude,global_bound,gamma)
