#!/usr/bin/env python3
"""JSON-only design for new raw-power perturbations and normalization controls."""
import hashlib
import json
import math
import resource
import signal
import time
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

TASK = Path('/workspace/scratch/b83cfe20d6e1')
BASE = TASK / 'checkpoints/SETI_NATIVE_SPOR_2026-10-14/SETI_NATIVE_SPOR_2026-10-14'
OUT = TASK / 'raw_retention_design'
DF = Fraction.from_float(-2.7939677238464355)
TSAMP = Fraction.from_float(18.253611008)
H = Fraction.from_float(4 / 158)
HALF = Fraction(1, 2)
DC = {178782208, 179830784, 180879360}
PLACEMENTS = ((-640, 0, Fraction(-67,100), Fraction(-19,100)),
              (640, 12, Fraction(23,100), Fraction(33,100)))


def enc(q):
    return [str(q.numerator), str(q.denominator)]


def floor(q):
    return q.numerator // q.denominator


def ceil(q):
    return -floor(-q)


def nearest(q):
    n, rem = divmod(q.numerator, q.denominator)
    return n + int(2*rem > q.denominator or 2*rem == q.denominator and n % 2 != 0)


def cdf(x, sweep):
    """Exact CDF for intrinsic U[-1/2,1/2] plus exposure U[-sweep/2,sweep/2]."""
    if not sweep:
        return max(Fraction(0), min(Fraction(1), x+HALF))
    edge = (sweep+1)/2
    if x <= -edge:
        return Fraction(0)
    if x >= edge:
        return Fraction(1)
    sq = lambda q: max(q, Fraction(0)) ** 2
    return (sq(x+edge)-sq(x+(sweep-1)/2)-sq(x+(1-sweep)/2)+sq(x-edge))/(2*sweep)


def row_kernel(row, center, rounded, model, sweep, core, rawbounds):
    if model == 'delta':
        pairs = [(rounded, Fraction(1))]
    elif model == 'fixed3':
        pairs = [(rounded-1,Fraction(1,4)),(rounded,Fraction(1,2)),(rounded+1,Fraction(1,4))]
    else:
        edge = (1+sweep)/2
        pairs = []
        for channel in range(floor(center-edge-HALF), ceil(center+edge+HALF)+1):
            weight = cdf(Fraction(channel)+HALF-center,sweep)-cdf(Fraction(channel)-HALF-center,sweep)
            assert weight >= 0
            if weight:
                pairs.append((channel,weight))
    assert sum(w for c,w in pairs) == 1
    raw_weights = [float(w) for c,w in pairs]
    assert min(raw_weights) >= -1e-14
    clipped = [max(0.0,w) for w in raw_weights]
    total = math.fsum(clipped)
    weights = [w/total for w in clipped]
    assert abs(math.fsum(weights)-1.0) <= 2e-15
    channels = [c for c,w in pairs]
    assert min(channels) >= rawbounds[0] and max(channels) < rawbounds[1]
    assert not any(c in DC for c in channels)
    inside = [core[0] <= c < core[1] for c in channels]
    halo = [core[0]-250 <= c < core[1]+250 for c in channels]
    category = 'CORE_OVERLAP' if any(inside) else 'HALO_ONLY' if any(halo) else 'OUTSIDE_NORMALIZATION_SUPPORT'
    return dict(source_row=row,absolute_channels=channels,weights=weights,exact_weights=[enc(w) for c,w in pairs],
                prenormal_sum=total,negative_clipped_count=sum(w<0 for w in raw_weights),
                continuous_center_fraction=enc(center),central_native_channel=rounded,
                central_bin_weight=weights[channels.index(rounded)] if rounded in channels else 0.0,
                source_channel_support_inclusive=[min(channels),max(channels)],
                central_bin_in_normalization_core=core[0] <= rounded < core[1],
                kernel_channels_in_core=sum(inside),kernel_channels_in_core_halo=sum(halo),
                fraction_power_in_core=math.fsum(w for w,inside_i in zip(weights,inside) if inside_i),
                fraction_power_in_core_halo=math.fsum(w for w,halo_i in zip(weights,halo) if halo_i),
                normalization_support_class=category)


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def pin(p, root=TASK):
    return dict(path=p.relative_to(root).as_posix(),bytes=p.stat().st_size,sha256=digest(p))

