"""Independent scalar C031 profile/context arithmetic, no I/O or production imports."""
import bisect
import math
import statistics
import numpy as np
C=299792.458
CB=3868.1499999999996
ANCHOR_BERV=5.77068898867443
CT=CB/(1+ANCHOR_BERV/C)
X=[i/100 for i in range(-300,301)]
CORE=[abs(x)<=.25 for x in X]
BROAD=[.25<abs(x)<=3 for x in X]
def nullable(x):return float(x)if math.isfinite(x)else None
def median(values):return statistics.median(values)if values else math.nan
def profile(wave,flux,error,berv,frame,spacing):
    wave=list(map(float,wave));flux=list(map(float,flux));error=list(map(float,error))
    center=CB if frame=='barycentric'else CT
    scale=1. if frame=='barycentric'else 1+berv/C
    off=[w/scale-center for w in wave]
    requested=[(center+x)*scale for x in X]
    raw=[];outside=[];gaps=[]
    for query in requested:
        right=min(max(bisect.bisect_left(wave,query),1),len(wave)-1);left=right-1
        out=query<wave[0]or query>wave[-1];gap=wave[right]-wave[left]>1.51*spacing
        outside.append(out);gaps.append(gap)
        if out or gap:value=math.nan
        elif query==wave[left]:value=flux[left]
        elif query==wave[right]:value=flux[right]
        else:value=flux[left]+(flux[right]-flux[left])*(query-wave[left])/(wave[right]-wave[left])
        raw.append(value)
    left=[-3<=x<=-1.5 for x in off];right=[1.5<=x<=3 for x in off]
    lf=[v and math.isfinite(f)for v,f in zip(left,flux)];rf=[v and math.isfinite(f)for v,f in zip(right,flux)]
    reference=median([f for f,l,r in zip(flux,lf,rf)if l or r]);problems=[]
    if not any(left):problems.append('MISSING_LEFT_FLANK_COVERAGE')
    elif sum(lf)<20:problems.append('INSUFFICIENT_FINITE_LEFT_FLANK')
    if not any(right):problems.append('MISSING_RIGHT_FLANK_COVERAGE')
    elif sum(rf)<20:problems.append('INSUFFICIENT_FINITE_RIGHT_FLANK')
    if not problems:
        if not math.isfinite(reference):problems.append('NO_FINITE_FLANK_REFERENCE')
        elif reference<=0:problems.append('NONPOSITIVE_FLANK_REFERENCE')
    diffs=[flux[i+1]-flux[i]for i in range(len(wave)-1)
           if ((lf[i]and lf[i+1])or(rf[i]and rf[i+1]))and wave[i+1]-wave[i]<=1.51*spacing]
    middle=median(diffs);noise=1.4826*median([abs(x-middle)for x in diffs])/math.sqrt(2)if diffs else math.nan
    normalized=[x/reference for x in raw]if not problems else[math.nan]*601
    inside=[-3<=x<=3 and math.isfinite(f)for x,f in zip(off,flux)]
    def nonpositive(mask):
        values=[f for f,m in zip(flux,mask)if m]
        return sum(x<=0 for x in values)/len(values)if values else None
    metrics=dict(normalization_status='USABLE_POSITIVE_FLANK_REFERENCE'if not problems else'RAW_ONLY',
        normalization_reasons=problems,flank_reference=nullable(reference)if sum(lf)>=20 and sum(rf)>=20 else None,
        available_flank_median=nullable(reference),left_flank_native_samples=sum(left),right_flank_native_samples=sum(right),
        left_flank_finite_samples=sum(lf),right_flank_finite_samples=sum(rf),
        left_flank_median=nullable(median([f for f,m in zip(flux,lf)if m])),right_flank_median=nullable(median([f for f,m in zip(flux,rf)if m])),
        left_flank_nonpositive_fraction=nonpositive(lf),right_flank_nonpositive_fraction=nonpositive(rf),window_nonpositive_fraction=nonpositive(inside),
        window_native_finite_samples=sum(inside),positive_finite_ERR_samples=sum(m and math.isfinite(e)and e>0 for m,e in zip(inside,error)),
        noise_pairs=len(diffs),first_difference_noise_proxy=nullable(noise),low_flank_reference=None if problems or not math.isfinite(noise)else bool(reference<=3*noise),
        raw_grid_finite_samples=sum(math.isfinite(x)for x in raw),normalized_grid_finite_samples=sum(math.isfinite(x)for x in normalized),
        outside_native_coverage_grid_samples=sum(outside),gap_masked_grid_samples=sum(g and not o for g,o in zip(gaps,outside)),
        frame_center=center,barycentric_query_scale=scale)
    arrays=dict(offset=np.array(X),requested_bary_wave=np.array(requested),signed_raw_flux=np.array(raw),normalized_flux=np.array(normalized))
    return arrays,metrics
def comparison(a,b,mask):
    count=sum(mask);minimum=(4*count+4)//5
    raw=[(float(x),float(y))for x,y,m in zip(a['signed_raw_flux'],b['signed_raw_flux'],mask)if m and math.isfinite(x)and math.isfinite(y)]
    normalized=[(float(x),float(y))for x,y,m in zip(a['normalized_flux'],b['normalized_flux'],mask)if m and math.isfinite(x)and math.isfinite(y)]
    corr=None;reason=None
    if len(raw)<minimum:reason='INSUFFICIENT_COMMON_RAW_COVERAGE'
    elif min(x for x,y in raw)==max(x for x,y in raw)or min(y for x,y in raw)==max(y for x,y in raw):reason='ZERO_RAW_VARIANCE'
    else:
        meanx=math.fsum(x for x,y in raw)/len(raw);meany=math.fsum(y for x,y in raw)/len(raw)
        aa=[x-meanx for x,y in raw];bb=[y-meany for x,y in raw]
        corr=math.fsum(x*y for x,y in zip(aa,bb))/math.sqrt(math.fsum(x*x for x in aa)*math.fsum(y*y for y in bb))
    rms=math.sqrt(math.fsum((x-y)**2 for x,y in normalized)/len(normalized))if len(normalized)>=minimum else None
    return dict(nominal_grid_samples=count,minimum_common_samples=minimum,common_finite_raw_samples=len(raw),raw_pearson=corr,raw_pearson_block_reason=reason,
                common_finite_normalized_samples=len(normalized),normalized_rms=rms,normalized_rms_block_reason=None if rms is not None else'INVALID_REFERENCE_OR_INSUFFICIENT_NORMALIZED_COVERAGE')
