"""Analytic finite-exposure fixtures and independent native-score arithmetic."""
import math
import numpy as np


def pixel_masses(center_channel, sweep_channels, intrinsic_width_channels, channel_count):
    values=(center_channel,sweep_channels,intrinsic_width_channels)
    if not all(math.isfinite(x) for x in values) or intrinsic_width_channels <= 0:
        raise ValueError('Finite centre/sweep and positive intrinsic width required')
    a,b=sorted((abs(sweep_channels),float(intrinsic_width_channels)),reverse=True)
    left=center_channel-(a+b)/2
    right=center_channel+(a+b)/2
    indices=np.arange(math.floor(left-.5),math.ceil(right+.5)+1,dtype=np.int64)
    def cdf(z):
        z=np.asarray(z,dtype=np.float64)
        if b==0:
            return np.clip(z/a,0,1)
        out=np.zeros_like(z)
        lower=(z>0)&(z<b);middle=(z>=b)&(z<a);upper=(z>=a)&(z<a+b)
        out[lower]=z[lower]**2/(2*a*b)
        out[middle]=(z[middle]-b/2)/a
        out[upper]=1-(a+b-z[upper])**2/(2*a*b)
        out[z>=a+b]=1
        return out
    masses=cdf(indices+.5-left)-cdf(indices-.5-left)
    keep=masses>0;indices,masses=indices[keep],masses[keep]
    if (not len(indices) or indices.min()<0 or indices.max()>=channel_count
            or np.any(masses<0) or abs(float(masses.sum())-1)>1e-12):
        raise ValueError('Finite exposure support incomplete or mass not conserved')
    return indices,masses


def nearest_even(values):
    """Independent floor/fraction implementation; no production rint call."""
    low=np.floor(values).astype(np.int64)
    frac=values-low
    return low+((frac>.5)|((frac==.5)&((low%2)==1)))


def score_oracle(source, factors, support_hz, width):
    """Select raw normalized windows, independent of cached filtering/gathering."""
    g=source.geometry
    out=np.zeros((len(factors),len(support_hz)),dtype='<f4')
    offsets=np.arange(-width//2+1,width//2+1) if width>1 else np.array([0])
    assert len(offsets)==width
    for row in range(source.integration_count):
        frequency=factors[:,row,None]*support_hz[None,:]
        indices=nearest_even((frequency-g.raw_zero_hz)/g.channel_width_hz)
        if indices.min()+offsets.min()<0 or indices.max()+offsets.max()>=g.channel_count:
            raise ValueError('Independent score window outside extraction')
        samples=source.values[row,indices[:,:,None]+offsets]
        filtered=(np.sum(samples,axis=2,dtype=np.float32).astype('<f8')/math.sqrt(width)).astype('<f4')
        out+=filtered
    out/=np.float32(math.sqrt(source.integration_count))
    return out
