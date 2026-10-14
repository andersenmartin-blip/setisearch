"""Independent exact continuous-rounding family certification and numerical QA.

Geometry uses Fraction representations of the frozen binary64 constants. Candidate
native-bin tuples are generated from global first-row range and bounded row-bin
differences. Feasibility is certified by eliminating phase into an exact one-
dimensional drift interval, including open boundaries for odd native bins.
No producer imports, vertical-sweep implementation, or arbitrary parameter grid.
"""
from __future__ import annotations

import argparse
from fractions import Fraction as F
import hashlib
import itertools
import json
from pathlib import Path
import time

H_FLOAT=4/158
DF_FLOAT=-2.7939677238464355
HALF=F(1,2)


def require(condition,message):
    if not condition:
        raise ValueError(message)


def rational_float(value):
    require(isinstance(value,(int,float)) and not isinstance(value,bool),'Expected frozen finite numeric constant')
    return F(value)


def floor(value):
    return value.numerator//value.denominator


def ceil(value):
    return -((-value.numerator)//value.denominator)


def nearest_even(value):
    lower=floor(value);fraction=value-lower
    if fraction<HALF:
        return lower
    if fraction>HALF:
        return lower+1
    return lower if lower%2==0 else lower+1


def encoded(value):
    return [value.numerator,value.denominator]


def decoded(value):
    require(isinstance(value,list) and len(value)==2 and all(type(v) is int for v in value)
            and value[1]>0,'Malformed exact rational witness')
    result=F(value[0],value[1])
    require(encoded(result)==value,'Witness fraction must be canonical/reduced')
    return result


def centers_at(base,coefficients,d0,delta,phase):
    return tuple(nearest_even(base+phase+(d0+delta)*a) for a in coefficients)


def feasible_tuple(native_bins,base,coefficients,d0,h):
    """Eliminate phase: every lower_i(delta) <= every upper_j(delta).

    A nearest-even bin n includes both half boundaries iff n is even; odd
    n excludes both. Pair inequalities are strict if either participating
    boundary is strict. The retained drift interval can be open, closed,
    half-open, or a single included point; no epsilon is used.
    """
    require(len(native_bins)==len(coefficients)==4,'Four-row geometry required')
    lower=[(-HALF,F(0),False)]
    upper=[(HALF,F(0),False)]
    for native,a in zip(native_bins,coefficients):
        intercept=base+d0*a
        strict=native%2!=0
        lower.append((F(native)-HALF-intercept,-a,strict))
        upper.append((F(native)+HALF-intercept,-a,strict))
    lo,hi=-h,h;lo_open=hi_open=False
    for lc,lm,ls in lower:
        for uc,um,us in upper:
            constant=lc-uc;slope=lm-um;strict=ls or us
            if slope==0:
                if constant>0 or (constant==0 and strict):
                    return None
                continue
            bound=-constant/slope
            if slope>0:
                if bound<hi:
                    hi=bound;hi_open=strict
                elif bound==hi:
                    hi_open=hi_open or strict
            else:
                if bound>lo:
                    lo=bound;lo_open=strict
                elif bound==lo:
                    lo_open=lo_open or strict
            if lo>hi or (lo==hi and (lo_open or hi_open)):
                return None
    delta=(lo+hi)/2 if lo<hi else lo
    lower_values=[(c+m*delta,s) for c,m,s in lower]
    upper_values=[(c+m*delta,s) for c,m,s in upper]
    phase_lo=max(v for v,s in lower_values);phase_hi=min(v for v,s in upper_values)
    phase_lo_open=any(s for v,s in lower_values if v==phase_lo)
    phase_hi_open=any(s for v,s in upper_values if v==phase_hi)
    require(phase_lo<=phase_hi and not (phase_lo==phase_hi and (phase_lo_open or phase_hi_open)),
            'Eliminated feasibility and recovered phase interval disagree')
    phase=(phase_lo+phase_hi)/2 if phase_lo<phase_hi else phase_lo
    require(-h<=delta<=h and -HALF<=phase<=HALF,'Exact feasible witness outside box')
    require(centers_at(base,coefficients,d0,delta,phase)==tuple(native_bins),
            'Exact feasible witness fails native nearest-even rounding')
    dimension=int(lo<hi)+int(phase_lo<phase_hi)
    ties=[i for i,a in enumerate(coefficients) if (base+phase+(d0+delta)*a)-floor(base+phase+(d0+delta)*a)==HALF]
    return {'delta':encoded(delta),'phase':encoded(phase),
            'drift_interval':[encoded(lo),encoded(hi)],'drift_interval_open':[lo_open,hi_open],
            'phase_at_witness_interval':[encoded(phase_lo),encoded(phase_hi)],
            'phase_at_witness_interval_open':[phase_lo_open,phase_hi_open],
            'feasible_dimension':dimension,'witness_tie_rows':ties}


def candidate_ranges(base,coefficients,d0,h):
    """All possible first-row bins and all possible bin differences.

    Native rounding error is bounded by half a channel for every row. Hence
    row-bin difference minus its continuous channel difference is in [-1,1].
    Phase cancels in differences, retaining a small exhaustive candidate set.
    """
    a0=coefficients[0]
    first_center=base+d0*a0
    first_min=ceil(first_center-h*abs(a0)-1)
    first_max=floor(first_center+h*abs(a0)+1)
    differences=[]
    for a in coefficients[1:]:
        difference=a-a0
        center=d0*difference
        minimum=ceil(center-h*abs(difference)-1)
        maximum=floor(center+h*abs(difference)+1)
        differences.append(range(minimum,maximum+1))
    return range(first_min,first_max+1),differences


def enumerate_tuples(profile,window_start,offset=0):
    require(offset%2==0,'Even-offset transport is required for parity-invariant geometry')
    track=profile['selected_track']
    base=int(track['source_reference_channel'])+offset
    d0=rational_float(track['drift_hz_s']);h=F(H_FLOAT);df=F(DF_FLOAT)
    coefficients=[F(t)/df for t in profile['times_from_primary_reference_s'][window_start:window_start+4]]
    first,differences=candidate_ranges(base,coefficients,d0,h)
    result={};candidate_count=0
    for n0 in first:
        for differences_tuple in itertools.product(*differences):
            bins=(n0,)+tuple(n0+d for d in differences_tuple)
            candidate_count+=1
            witness=feasible_tuple(bins,base,coefficients,d0,h)
            if witness is not None:
                require(bins not in result,'Duplicate exhaustive tuple')
                result[bins]=witness
    return dict(sorted(result.items())),candidate_count


def parse_args():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True)
    parser.add_argument('--check-only',action='store_true')
    parser.add_argument('--geometry-self-test',action='store_true')
    return parser.parse_args()


def self_test():
    """Synthetic rational geometry only; no observation files or score arrays."""
    require(nearest_even(F(1,2))==0 and nearest_even(F(3,2))==2
            and nearest_even(F(-1,2))==0 and nearest_even(F(-3,2))==-2,'Nearest-even parity fails')
    a=[F(0)]*4
    require(feasible_tuple((0,0,0,0),0,a,F(0),F(1)) is not None,'Closed central tuple excluded')
    require(feasible_tuple((1,1,1,1),0,a,F(0),F(1)) is None,'Odd-only boundary tuple incorrectly admitted')
    require(feasible_tuple((-1,-1,-1,-1),0,a,F(0),F(1)) is None,'Negative odd-only boundary admitted')
    # A central even half tie remains feasible and its interior is sampled.
    w=feasible_tuple((2,2,2,2),F(3,2),a,F(0),F(1))
    require(w is not None and decoded(w['phase'])>0,'Even half-tie endpoint excluded')
    require(feasible_tuple((0,1,0,1),0,a,F(0),F(1)) is None,'Inconsistent identical-row tuple admitted')
    vertex=feasible_tuple((0,2,0,2),0,[F(0),F(1),F(0),F(1)],F(0),F(1))
    require(vertex is not None and decoded(vertex['delta'])==1 and decoded(vertex['phase'])==HALF
            and vertex['feasible_dimension']==0 and vertex['witness_tie_rows']==[0,1,2,3],
            'Boundary-only even-parity vertex was lost')
    print(json.dumps({'status':'PASS_SYNTHETIC_EXACT_RATIONAL_STRIP_FEASIBILITY',
                      'observation_values_read':False,'numpy_imported':False}))


def main():
    args=parse_args()
    if args.check_only:
        print(json.dumps({'status':'PASS_TEXT_ONLY_INDEPENDENT_EXACT_ROUNDING_QA_INTERFACE',
                          'observation_values_read':False,'numpy_imported':False,
                          'geometry_method':'exhaustive bin-difference candidates plus exact phase elimination',
                          'open_boundary_policy':'odd native bin excludes both half ties; even bin includes both',
                          'CPU_cap_s':600,'wall_cap_s':900,'memory_cap_bytes':2*1024**3}))
        return
    if args.geometry_self_test:
        self_test();return
    raise NotImplementedError('Frozen scope and producer contract pending; no observed score execution')


if __name__=='__main__':
    main()
