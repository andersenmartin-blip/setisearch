"""Import-safe, candidate-excluded HARPS native/raw reference registration.

No file I/O, output mutation, status threshold, or origin classification.
Call evaluate_reference_grid(raw, native, header, candidates) with candidates
containing order, native_pixel and optional review_id. Native/raw conventions
and all diagnostic values are returned, including failed region correlations.
"""
import itertools
import numpy as np
from scipy.ndimage import median_filter

REFERENCE_ORDERS = (10, 30, 50, 62, 63, 69)
REFERENCE_WINDOWS = ((600, 900), (1400, 1700), (2200, 2500), (3000, 3300))
CANDIDATE_EXCLUSION = 80
MIN_REFERENCE_SAMPLES = 100
ORIENTATIONS = tuple(itertools.product((False, True), repeat=3))

def trace_polynomial(header, order, native_pixels, argument_flip):
    x=np.asarray(native_pixels)
    if argument_flip: x=4095-x
    degree=int(header['ESO DRS CAL LOC DEG CTR'])
    coef=[header['ESO DRS CAL LOC CTR'+str(order*(degree+1)+j)] for j in range(degree+1)]
    return np.polynomial.polynomial.polyval(x,coef)

def evaluate_reference_grid(raw, native, header, candidates=()):
    """Rank the eight conventions by median independent-region correlation.

    Assumes 4096x4096 trimmed/joined raw and 72x4096 native arrays. All candidate
    positions must use zero-based native order and wavelength-array pixel.
    Returns descriptive summaries only. The original one-region >0.8 check
    should be retained separately; no validation/origin status is set here.
    """
    if raw.shape!=(4096,4096) or native.shape!=(72,4096):
        raise ValueError('Unexpected HARPS raw/native shape')
    regions=[]
    for order in REFERENCE_ORDERS:
        for lo,hi in REFERENCE_WINDOWS:
            x=np.arange(lo,hi);mask=np.ones(len(x),bool);excluded=[]
            for hit in candidates:
                if int(hit['order'])==order:
                    near=abs(x-int(hit['native_pixel']))<=CANDIDATE_EXCLUSION
                    if near.any():excluded.append(hit.get('review_id','UNKNOWN'))
                    mask&=~near
            samples=int(mask.sum());valid=samples>=MIN_REFERENCE_SAMPLES
            reg=dict(order=order,pixel_interval_half_open=[lo,hi],samples=samples,
                     excluded_candidate_ids=excluded,status='VALID' if valid else 'INSUFFICIENT_REFERENCE_SAMPLES',options=[])
            ref=np.asarray(native[order,x],dtype=float)
            ref=ref-median_filter(ref,size=31,mode='nearest')
            for rowflip,colflip,argflip in ORIENTATIONS:
                yy=4095-x if rowflip else x
                tc=trace_polynomial(header,order,x,argflip)
                if colflip:tc=4095-tc
                cx=np.rint(tc).astype(int)
                bounded=bool(np.all((cx>=8)&(cx<4088)))
                if valid and bounded:
                    val=np.stack([raw[yy,cx+j] for j in range(-3,4)]).sum(axis=0)
                    val=val-median_filter(val,size=31,mode='nearest')
                    cv=float(np.corrcoef(ref[mask],val[mask])[0,1])
                    cv=cv if np.isfinite(cv) else None
                    profile=np.median(np.stack([raw[yy,cx+j][mask] for j in range(-8,9)]),axis=1)
                    peak=int(np.argmax(profile))-8
                    profile=profile.tolist()
                else:cv=None;peak=None;profile=None
                reg['options'].append(dict(row_flip=rowflip,column_flip=colflip,argument_flip=argflip,
                    correlation=cv,continuum_peak_integer_offset=peak,continuum_profile=profile,
                    valid_spatial_support=bounded))
            regions.append(reg)
    summaries=[]
    for idx,(rf,cf,af) in enumerate(ORIENTATIONS):
        cs=[r['options'][idx]['correlation'] for r in regions if r['options'][idx]['correlation'] is not None]
        offsets=[r['options'][idx]['continuum_peak_integer_offset'] for r in regions if r['options'][idx]['correlation'] is not None]
        orders={r['order'] for r in regions if r['options'][idx]['correlation'] is not None}
        summaries.append(dict(row_flip=rf,column_flip=cf,argument_flip=af,
            median_correlation=float(np.median(cs)) if cs else None,
            min_correlation=float(min(cs)) if cs else None,max_correlation=float(max(cs)) if cs else None,
            regions_above_original_0p8_threshold=sum(v>.8 for v in cs),valid_regions=len(cs),valid_orders=len(orders),
            median_abs_continuum_peak_offset=float(np.median(np.abs(offsets))) if offsets else None,
            max_abs_continuum_peak_offset=int(max(abs(z) for z in offsets)) if offsets else None,
            regions_peak_within_one_pixel=sum(abs(z)<=1 for z in offsets)))
    summaries.sort(key=lambda r:r['median_correlation'] if r['median_correlation'] is not None else -2,reverse=True)
    return dict(orientation_summaries=summaries,reference_regions=regions,
        method='Fixed six-order, four-window grid; ±80 native-pixel candidate exclusion; seven-column raw aperture; 31-pixel median high-pass; rank by median Pearson correlation.')
