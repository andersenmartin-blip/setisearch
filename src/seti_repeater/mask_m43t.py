"""Named M43T comparison of exact-channel and neighboring-channel isolation."""
import numpy as np
from . import search_v0p6 as core
from .detector_m43q import digest

POLICIES={
    'legacy':{'schema':'m43t-mask-policy-v1','other_epoch_support_radius_bins':0,'strong_snr':10.,
        'other_epoch_support_snr':3.,'or_across_widths':True,'dilation_bins':9},
    'neighbor2':{'schema':'m43t-mask-policy-v1','other_epoch_support_radius_bins':2,'strong_snr':10.,
        'other_epoch_support_snr':3.,'or_across_widths':True,'dilation_bins':9},
}


def validate_scope(window,policy):
    if policy not in POLICIES or window!='m43t-mask-'+policy:
        raise ValueError('M43T policy and calibration window must agree')
    return digest(POLICIES[policy])


def build_mask(factory,policy):
    if policy not in POLICIES:raise ValueError('unknown M43T mask policy')
    if policy=='legacy':return core.build_m37_two_pass_template_mask(factory)
    combined=None
    for width in core.M37_SPECTRAL_WIDTHS:
        vectors=np.asarray(factory(width))
        if vectors.dtype!=np.dtype('<f4') or vectors.ndim!=2 or vectors.shape[0]!=3 or not np.isfinite(vectors).all():
            raise ValueError('three finite float32 epoch vectors required')
        supported=core.dilate_q_mask(vectors>=3.,2)
        flags=np.stack([(vectors[e]>=10.)&~np.any(supported[[j for j in range(3) if j!=e]],axis=0) for e in range(3)])
        if combined is None:combined=flags
        else:
            if combined.shape!=flags.shape:raise ValueError('mask width shape changed')
            combined|=flags
    return core.dilate_q_mask(combined,9)


def reference_mask(factory,policy):
    """Independent window-reduction support and prefix-count final dilation."""
    if policy not in POLICIES:raise ValueError('unknown M43T mask policy')
    radius=POLICIES[policy]['other_epoch_support_radius_bins'];combined=None
    for width in core.M37_SPECTRAL_WIDTHS:
        v=np.asarray(factory(width),dtype='<f4')
        padded=np.pad(v,((0,0),(radius,radius)),constant_values=-np.inf)
        maximum=np.lib.stride_tricks.sliding_window_view(padded,2*radius+1,axis=1).max(axis=-1)
        flags=np.stack([(v[e]>=10.)&(np.max(np.delete(maximum,e,axis=0),axis=0)<3.) for e in range(3)])
        combined=flags if combined is None else combined|flags
    n=combined.shape[1];prefix=np.pad(np.cumsum(combined,axis=1,dtype=np.int64),((0,0),(1,0)))
    left=np.maximum(np.arange(n)-9,0);right=np.minimum(np.arange(n)+10,n)
    return prefix[:,right]-prefix[:,left]>0
