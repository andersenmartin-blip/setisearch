"""Factorized M43L oracle: independent native windows, absolute native indexing."""
from dataclasses import dataclass
import hashlib
import numpy as np
from seti_repeater import search_v0p6 as core
from seti_repeater.transfer_m43g import immutable, integer, array_hash


@dataclass(frozen=True)
class NativeReference:
    geometry: core.NativeFrequencyGeometry
    width: int
    values: np.ndarray
    filtered_payload_sha256: str
    row_sha256: tuple


def build_reference(normalized,geometry,width,*,chunk_centers=2048):
    integer(width,'width');integer(chunk_centers,'reference chunk')
    if width not in core.M37_SPECTRAL_WIDTHS:raise ValueError('unsupported width')
    n=geometry.channel_count;half=width//2
    if (normalized.dtype!=np.dtype('<f4') or normalized.ndim!=2 or normalized.shape[1]!=n
            or not normalized.flags.c_contiguous or n<=2*half or not np.isfinite(normalized).all()):
        raise ValueError('invalid normalized reference input')
    # Keep absolute native coordinates. NaN guards must never be sampled.
    out=np.full(normalized.shape,np.nan,dtype='<f4');row_hashes=[];payload=hashlib.sha256()
    offsets=np.arange(-half,half+1)
    for row in range(len(normalized)):
        h=hashlib.sha256()
        for start in range(half,n-half,chunk_centers):
            stop=min(start+chunk_centers,n-half)
            centers=np.arange(start,stop)
            windows=normalized[row,centers[:,None]+offsets]
            values=(np.sum(windows,axis=1,dtype=np.float32)/np.sqrt(width)).astype('<f4')
            if not np.isfinite(values).all():raise ValueError('nonfinite reference filter')
            out[row,start:stop]=values;h.update(memoryview(values).cast('B'));payload.update(memoryview(values).cast('B'))
        row_hashes.append(h.hexdigest())
    return NativeReference(geometry,width,immutable(out),payload.hexdigest(),tuple(row_hashes))


def integrate_reference(reference,factors,grid,start,stop):
    """Independent absolute-coordinate gather, maintaining row-wise float32 sum."""
    integer(start,'carrier start',0);integer(stop,'carrier stop')
    if stop<=start or stop>grid.support_bin_count:raise ValueError('invalid reference carrier slice')
    f=np.asarray(factors)
    if f.dtype!=np.dtype('<f8') or f.ndim!=2 or f.shape[1]!=len(reference.values):raise ValueError('invalid reference factors')
    centers=np.rint((f[:,:,None]*grid.support_hz[None,None,start:stop]
                    -reference.geometry.raw_zero_hz)/reference.geometry.channel_width_hz).astype(np.int64)
    h=reference.width//2
    if centers.min()<h or centers.max()>=reference.geometry.channel_count-h:
        raise ValueError('reference sampled a filter guard')
    out=np.zeros((len(f),stop-start),dtype='<f4')
    for row in range(len(reference.values)):
        out+=reference.values[row,centers[:,row,:]]
    out/=np.float32(np.sqrt(len(reference.values)))
    if not np.isfinite(out).all():raise ValueError('nonfinite integrated reference')
    return out
