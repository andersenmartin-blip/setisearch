"""Independent exact continuous-rounding family certification and numerical QA.

Geometry uses Fraction representations of the frozen binary64 constants. Candidate
native-bin tuples are generated from global first-row range and bounded row-bin
differences. Feasibility is certified by eliminating phase into an exact one-
dimensional drift interval, including open boundaries for odd native bins.
No producer imports, vertical-sweep implementation, or arbitrary parameter grid.
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import re
import resource
import signal
from fractions import Fraction as F
import hashlib
import itertools
import json
from pathlib import Path
import time

CPU_CAP,WALL_CAP,MEMORY_CAP=600,900,2*1024**3
ATOL,RTOL=1e-7,1e-10
OFFSETS=[0,-1024,-768,-512,-256,256,512,768,1024]
DC=[178782208,179830784,180879360]
STARTS=[0,2,4,6,8,10,12]
for _name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[_name]='1'

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
    require(isinstance(value,list) and len(value)==2,'Malformed exact rational witness')
    if all(type(v) is str for v in value):
        require(all(re.fullmatch(r'-?(0|[1-9][0-9]*)',v) for v in value),'Malformed rational decimal integers')
        ints=[int(v) for v in value]
        require(ints[1]>0,'Positive rational denominator required')
        result=F(*ints)
        require([str(result.numerator),str(result.denominator)]==value,'Witness fraction must be canonical/reduced')
    else:
        require(all(type(v) is int for v in value) and value[1]>0,'Malformed exact rational witness')
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


def witness_dimension(base,coefficients,d0,delta,phase,h):
    normals=[]
    if delta in (-h,h):
        normals.append((F(1),F(0)))
    if phase in (-HALF,HALF):
        normals.append((F(0),F(1)))
    ties=[]
    for row,a in enumerate(coefficients):
        value=base+phase+(d0+delta)*a
        if value-floor(value)==HALF:
            ties.append(row);normals.append((a,F(1)))
    rank=0 if not normals else 1
    if any(a*d-b*c!=0 for a,b in normals for c,d in normals):
        rank=2
    return 2-rank,ties


def audit_exact_geometry(saved,profile):
    track=profile['selected_track']
    require(saved['profile_id']==profile['profile_id'] and saved['origin_scan_id']==track['scan_id']
            and saved['context_scan_id']==profile['context_scan_id'] and saved['origin_rank']==track['rank']
            and saved['source_reference_channel']==track['source_reference_channel']
            and saved['original_drift_hz_s']==track['drift_hz_s']
            and saved['times_from_primary_reference_s']==profile['times_from_primary_reference_s'],
            'Saved exactgeometry profile anchors changed')
    require(len(saved['windows'])==7,'Exactgeometry window count differs')
    base=int(track['source_reference_channel']);d0=F(track['drift_hz_s']);h=F(H_FLOAT);df=F(DF_FLOAT)
    windows=[];candidate_total=0;tuple_total=0;boundary_witnesses=0
    for wi,(record,start) in enumerate(zip(saved['windows'],range(0,13,2))):
        require(record['window_index']==wi and record['window_start_row']==start
                and record['window_source_rows']==list(range(start,start+4)),'Saved exactgeometry window coordinates differ')
        independently,candidates=enumerate_tuples(profile,start)
        candidate_total+=candidates;tuple_total+=len(independently)
        paths=record['paths'];tuples=[tuple(p['channels']) for p in paths]
        require(tuples==list(independently),'Exhaustive feasible native-bin tuples differ from producer sweep')
        coefficients=[F(t)/df for t in profile['times_from_primary_reference_s'][start:start+4]]
        for path in paths:
            delta=decoded(path['delta_drift_fraction']);phase=decoded(path['phase_fraction'])
            require(-h<=delta<=h and -HALF<=phase<=HALF,'Saved exact witness outside frozen box')
            require(centers_at(base,coefficients,d0,delta,phase)==tuple(path['channels']),
                    'Saved rational witness does not reproduce exact nearest-even path')
            dimension,ties=witness_dimension(base,coefficients,d0,delta,phase,h)
            require(path['witness_stratum_dimension']==dimension
                    and path['tie_row_indices_in_window']==ties,'Exact witness dimension/ties metadata differs')
            require(path['sampling_slice'] in ('critical','open_slab')
                    and path['sampling_phase'] in ('cut','open_gap'),'Undocumented sweep witness classification')
            boundary_witnesses+=int(dimension<2)
        windows.append(independently)
    return windows,{'profile_id':profile['profile_id'],'candidate_tuples':candidate_total,
                    'feasible_native_paths':tuple_total,'saved_boundary_witnesses':boundary_witnesses}


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1048576),b''):
            h.update(chunk)
    return h.hexdigest()

def pairs(items):
    d={}
    for key,value in items:
        require(key not in d, 'Duplicate JSON key')
        d[key]=value
    return d

def decode(data):
    return json.loads(data,object_pairs_hook=pairs,
                      parse_constant=lambda value:(_ for _ in ()).throw(ValueError('Nonfinite JSON')))

def confined(root,name):
    path=root/name
    require(not Path(name).is_absolute() and '..' not in Path(name).parts
            and path.resolve().is_relative_to(root) and not path.is_symlink(), 'Input path escapes root')
    return path

def json_out(path,data):
    with path.open('xb') as f:
        f.write((json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+'\n').encode())
        f.flush();os.fsync(f.fileno())

def exact(a,b,why):
    a,b=np.asarray(a),np.asarray(b)
    require(a.shape==b.shape and np.array_equal(a,b),why)

def close(a,b,why):
    a,b=np.asarray(a),np.asarray(b)
    require(a.shape==b.shape,why+' (shape)')
    finite=np.isfinite(a)&np.isfinite(b)
    require(np.array_equal(np.isfinite(a),np.isfinite(b)) and np.array_equal(a[~finite],b[~finite]),why+' (nonfinite)')
    require(np.allclose(a[finite],b[finite],atol=ATOL,rtol=RTOL),why+' (numerical)')
    return float(np.max(np.abs(a[finite]-b[finite]))) if finite.any() else 0.

def direct_normalization(raw,core0,crop0):
    """Independent row-major direct501 medians on every original core cell."""
    require(raw.shape==(16,12096) and raw.dtype==np.dtype('<f4'), 'Raw crop dtype/shape differs')
    local=core0-crop0
    require(local==4000,'Expected authenticated halo origin')
    core=raw[:,local:local+4096].astype(np.float64)
    levels=np.median(core,axis=1)
    residual=np.empty((16,4096),dtype=np.float64)
    for row in range(16):
        ratio=raw[row].astype(np.float64)/levels[row]
        for first in range(0,4096,256):
            positions=np.arange(local+first,local+min(4096,first+256))
            samples=ratio[positions[:,None]+np.arange(-250,251)]
            residual[row,first:first+len(positions)]=ratio[positions]-np.median(samples,axis=1)
    centers=np.median(residual,axis=1)
    scales=1.4826*np.median(np.abs(residual-centers[:,None]),axis=1)
    clipped=np.clip(residual-centers[:,None],-5*scales[:,None],5*scales[:,None])
    locations=centers+clipped.mean(axis=1)
    require(np.all(levels>0) and np.all(scales>0), 'Normalization scales invalid')
    return {'row_power_median':levels,'row_residual_median':centers,
            'row_residual_MAD_scale':scales,'row_winsorized_residual_location':locations}

def audit_csv(data,records,why):
    rows=list(csv.DictReader(io.StringIO(data.decode())))
    require(len(rows)==len(records),why+' row count differs')
    for row,record in zip(rows,records):
        require(set(row)==set(record),why+' columns differ')
        for key,value in record.items():
            if isinstance(value,(list,dict)):
                require(decode(row[key])==value,why+' nested field differs')
            elif isinstance(value,bool):
                require(row[key] in (str(value),str(value).lower()),why+' bool field differs')
            else:
                require(row[key]==str(value),why+' scalar field differs')


def flatten_geometry(windows):
    bins=[];indices=[];rows=[];lookup={}
    for wi,patterns in enumerate(windows):
        for native in patterns:
            lookup[(wi,native)]=len(bins)
            bins.append(native);indices.append(wi);rows.append(list(range(STARTS[wi],STARTS[wi]+4)))
    return np.asarray(bins,dtype=np.int64),np.asarray(indices,dtype=np.int64),np.asarray(rows,dtype=np.int64),lookup


def direct_path_terms(raw,crop0,normal,channels,path_rows):
    """Independent direct501 medians for unique actual row/native-bin samples."""
    require(channels.ndim==3 and channels.shape[0]==9 and channels.shape[2]==4,'Flattened channel shape differs')
    terms=np.empty(channels.shape,dtype=np.float64)
    for row in range(16):
        path_indices,within_indices=np.where(path_rows==row)
        requested=channels[:,path_indices,within_indices]
        bins,inverse=np.unique(requested,return_inverse=True)
        local=bins-crop0
        require(len(local)>0 and local.min()>=250 and local.max()+250<12096,'Exact path lacks full501 halo')
        ratio=raw[row].astype(np.float64)/normal['row_power_median'][row]
        z=np.empty(len(local),dtype=np.float64)
        for first in range(0,len(local),256):
            sample=local[first:first+256]
            median=np.median(ratio[sample[:,None]+np.arange(-250,251)],axis=1)
            z[first:first+len(sample)]=(ratio[sample]-median-normal['row_winsorized_residual_location'][row])/normal['row_residual_MAD_scale'][row]
        terms[:,path_indices,within_indices]=z[inverse].reshape(requested.shape)
    return terms


def legacy_path_diagnostic(record,profile,windows):
    times=np.asarray(profile['times_from_primary_reference_s'],dtype=np.float64)
    d0=float(profile['selected_track']['drift_hz_s']);base=int(profile['selected_track']['source_reference_channel'])
    drifts=d0+np.linspace(-H_FLOAT,H_FLOAT,81)
    phase=np.asarray([-.5,-.25,0.,.25,.5])
    legacy=np.rint(base+np.tile(phase,81)[:,None]+np.repeat(drifts,5)[:,None]*times[None,:]/DF_FLOAT).astype(np.int64)
    for wi,saved in enumerate(record['windows']):
        start=STARTS[wi];unique=sorted(set(tuple(int(n) for n in row) for row in legacy[:,start:start+4]))
        only=[list(path) for path in unique if path not in windows[wi]]
        bad_indices=[i for i,row in enumerate(legacy[:,start:start+4]) if tuple(int(n) for n in row) not in windows[wi]]
        require(saved['legacy_unique_paths']==len(unique)
                and saved['legacy_paths_attainable_exact_count']==len(unique)-len(only)
                and saved['legacy_only_float_paths']==only
                and saved['legacy_hypothesis_indices_with_infeasible_exact_paths']==bad_indices,
                'Legacy float64 path inclusion diagnostic differs')
    return legacy


def robust_geometry(profile,window_index,native,offset,windows):
    require(offset%2==0,'Robust witness transport requires even offset')
    zero_native=tuple(int(n)-offset for n in native)
    require(zero_native in windows[window_index],'Selected winner not in independently certified exact set')
    cert=windows[window_index][zero_native]
    delta=decoded(cert['delta']);phase=decoded(cert['phase'])
    start=STARTS[window_index];times=profile['times_from_primary_reference_s'][start:start+4]
    coefficients=[F(t)/F(DF_FLOAT) for t in times]
    d0=F(profile['selected_track']['drift_hz_s']);base=int(profile['selected_track']['source_reference_channel'])
    values=[base+phase+(d0+delta)*a for a in coefficients]
    slacks=[slack for v,n in zip(values,zero_native) for slack in (v-(F(n)-HALF),(F(n)+HALF)-v)]
    h=F(H_FLOAT)
    return {'feasible_region_dimension':cert['feasible_dimension'],
            'positive_area_feasible':cert['feasible_dimension']==2,
            'independent_relative_interior_delta_fraction':cert['delta'],
            'independent_relative_interior_phase_fraction':cert['phase'],
            'independent_minimum_half_bin_margin_fraction':encoded(min(slacks)),
            'independent_minimum_half_bin_margin_channels':float(min(slacks)),
            'independent_drift_box_margin_fraction':encoded(min(delta+h,h-delta)),
            'independent_phase_box_margin_fraction':encoded(min(phase+HALF,HALF-phase)),
            'independent_drift_feasible_interval':cert['drift_interval'],
            'independent_drift_feasible_interval_open':cert['drift_interval_open']}


def audit_exact_winner(saved,values,profile,geometry,windows,bins,wi_array,offset_index,eligible_indices=None):
    eligible_indices=np.arange(len(bins)) if eligible_indices is None else np.asarray(eligible_indices)
    require(np.isfinite(values[eligible_indices]).any(),'No eligible exact path')
    pi=int(eligible_indices[np.argmax(values[eligible_indices])]);wi=int(wi_array[pi]);start=STARTS[wi]
    native=bins[pi]+OFFSETS[offset_index]
    local=pi-int(np.sum(wi_array<wi))
    path=geometry['windows'][wi]['paths'][local]
    delta=decoded(path['delta_drift_fraction']);phase=decoded(path['phase_fraction'])
    base=int(profile['selected_track']['source_reference_channel'])+OFFSETS[offset_index]
    d0=F(profile['selected_track']['drift_hz_s'])
    full16=centers_at(base,[F(t)/F(DF_FLOAT) for t in profile['times_from_primary_reference_s']],d0,delta,phase)
    expected={'path_index':pi,'window_index':wi,'window_start_row':start,
              'window_source_rows':list(range(start,start+4)),'offset_channels':OFFSETS[offset_index],
              'selected4_absolute_centers':native.tolist(),'absolute_channels':native.tolist(),
              'witness_delta_drift_fraction':path['delta_drift_fraction'],
              'witness_phase_fraction':path['phase_fraction'],
              'witness_stratum_dimension':path['witness_stratum_dimension'],
              'tie_row_indices_in_window':path['tie_row_indices_in_window'],
              'witness_full16_absolute_centers':list(full16),
              'selected4_dc_contact':bool(np.isin(native,DC).any()),
              'witness_full16_dc_contact':bool(np.isin(full16,DC).any()),
              'representative_witness_not_unique_drift_fit':True}
    for key,value in expected.items():
        require(saved[key]==value,'Exact winner '+key+' differs')
    error=max(close(saved['score'],values[pi],'Exact winner score differs'),
              close(saved['witness_delta_drift_hz_s_display'],float(delta),'Exact drift display differs'),
              close(saved['witness_phase_channels_display'],float(phase),'Exact phase display differs'))
    return pi,error,robust_geometry(profile,wi,native,OFFSETS[offset_index],windows)


def audit_legacy_winner(saved,legacy_scores,legacy_centers,profile,oi,fixed_wi=None):
    if fixed_wi is None:
        hi,wi=(int(v) for v in np.unravel_index(np.argmax(legacy_scores),legacy_scores.shape))
    else:
        hi=int(np.argmax(legacy_scores[:,fixed_wi]));wi=fixed_wi
    drift_grid=float(profile['selected_track']['drift_hz_s'])+np.linspace(-H_FLOAT,H_FLOAT,81)
    di,phase_index=divmod(hi,5);phase=[-.5,-.25,0.,.25,.5][phase_index]
    centers=legacy_centers[hi]+OFFSETS[oi];start=STARTS[wi]
    expected={'hypothesis_index':hi,'drift_index':di,'phase_index':phase_index,'window_index':wi,
              'window_start_row':start,'offset_channels':OFFSETS[oi],
              'selected4_absolute_centers':centers[start:start+4].tolist(),
              'selected4_dc_contact':bool(np.isin(centers[start:start+4],DC).any()),
              'full16_dc_contact':bool(np.isin(centers,DC).any())}
    for key,value in expected.items():
        require(saved[key]==value,'Legacy winner '+key+' differs')
    return max(close(saved['score'],legacy_scores[hi,wi],'Legacy winner score differs'),
               close(saved['drift_hz_s'],drift_grid[di],'Legacy drift differs'),
               close(saved['phase_channels'],phase,'Legacy phase differs'))


def audit_numerical_profile(saved,profile,geometry,windows,arrays,raw,crop0,normal,old_arrays):
    bins,wi,path_rows,lookup=flatten_geometry(windows);n=len(bins)
    absolute=bins[None,:,:]+np.asarray(OFFSETS)[:,None,None]
    terms=direct_path_terms(raw,crop0,normal,absolute,path_rows)
    scores=terms.sum(axis=2)/2.;row_dc=np.isin(absolute,DC);dc=row_dc.any(axis=2)
    clean=np.where(dc,-np.inf,scores)
    schema={'absolute_channels':('<i8',(9,n,4)),'residual_row_terms':('<f8',(9,n,4)),
            'scores':('<f8',(9,n)),'row_dc_mask':('|b1',(9,n,4)),'path_dc_mask':('|b1',(9,n)),
            'path_window_index':('<i8',(n,)),'path_source_rows':('<i8',(n,4)),
            'offset_channels':('<i8',(9,)),'row501_unique_center_counts':('<i8',(16,))}
    require(set(arrays)==set(schema),'Exact NPZ fields differ')
    for key,(dtype,shape) in schema.items():
        require(arrays[key].dtype==np.dtype(dtype) and arrays[key].shape==shape,'Exact NPZ '+key+' dtype/shape differs')
    counts=[len(np.unique(absolute[:,np.where(path_rows==row)[0],np.where(path_rows==row)[1]])) for row in range(16)]
    for key,value in [('absolute_channels',absolute),('path_window_index',wi),('path_source_rows',path_rows),
                      ('offset_channels',OFFSETS),('row_dc_mask',row_dc),('path_dc_mask',dc),('row501_unique_center_counts',counts)]:
        exact(arrays[key],value,'Exact NPZ '+key+' differs')
    row_error=close(arrays['residual_row_terms'],terms,'Exact all row residuals differ')
    score_error=close(arrays['scores'],scores,'Exact all path scores differ')
    legacy=legacy_path_diagnostic(geometry,profile,windows)
    legacy_indices=np.asarray([[lookup[(window_index,tuple(int(x) for x in legacy[hi,STARTS[window_index]:STARTS[window_index]+4]))]
                                for window_index in range(7)] for hi in range(405)],dtype=np.int64)
    mapped=scores[:,legacy_indices];legacy_dc=dc[:,legacy_indices]
    require(old_arrays['scores'].shape==(9,405,7) and old_arrays['rounded_absolute_centers'].shape==(9,405,16),
            'Authenticated old family shape differs')
    exact(old_arrays['rounded_absolute_centers'],legacy[None,:,:]+np.asarray(OFFSETS)[:,None,None],
          'Legacy float64 full16 coordinates changed')
    prior_error=close(mapped,old_arrays['scores'],'Every prior405tuple score differs on exact reachable path')
    legacy_clean=np.where(legacy_dc,-np.inf,mapped)
    original_wi=STARTS.index(profile['selected_track']['window_start_row'])
    original_score=float(mapped[0,202,original_wi])
    close(original_score,profile['fixed_four_row_score'],'Original frozen4 score changed')
    expected_meta={'profile_id':profile['profile_id'],'origin_scan_id':profile['selected_track']['scan_id'],
                   'context_scan_id':profile['context_scan_id'],'origin_rank':profile['selected_track']['rank'],
                   'original_window_start_row':STARTS[original_wi],'original_width_channels':1,
                   'times_from_primary_reference_s':profile['times_from_primary_reference_s'],
                   'coarse_zero_offset_full16_absolute_centers':legacy[202].tolist(),
                   'unique_path_counts_by_window':[len(w) for w in windows],'total_unique_paths_all7':n,
                   'legacy_only_float_paths':0,'raw_sensitivity_or_FAP_established':False}
    for key,value in expected_meta.items():
        require(saved[key]==value,'Exact profile summary '+key+' differs')
    close(saved['original_fixed_four_row_score'],profile['fixed_four_row_score'],'Original score metadata differs')
    close(saved['legacy_path_max_absolute_score_difference'],float(np.max(np.abs(mapped-old_arrays['scores']))),
          'Saved legacy score parity metric differs')
    require(len(saved['offset_results'])==9,'Exact offset summary count differs')
    fixed=[];all7=[];robust=[]
    for oi,record in enumerate(saved['offset_results']):
        require(record['offset_channels']==OFFSETS[oi],'Exact summary offset order differs')
        close(record['original_d0_phase0_original4_score'],mapped[oi,202,original_wi],'Original offset coarse score differs')
        eligible=np.where(wi==original_wi)[0]
        pi,error,witness=audit_exact_winner(record['exact_fixed_original4'],clean[oi],profile,geometry,windows,bins,wi,oi,eligible)
        pi7,error7,witness7=audit_exact_winner(record['exact_max7'],clean[oi],profile,geometry,windows,bins,wi,oi)
        score_error=max(score_error,error,error7,
                        audit_legacy_winner(record['legacy_fine_fixed_original4'],legacy_clean[oi],legacy,profile,oi,original_wi),
                        audit_legacy_winner(record['legacy_fine_max7'],legacy_clean[oi],legacy,profile,oi))
        require(record['excluded_selected4_paths']==int(dc[oi,eligible].sum())
                and record['excluded_all7_paths']==int(dc[oi].sum()),'Exact DC exclusion count differs')
        fixed.append(float(clean[oi,eligible].max()));all7.append(float(clean[oi].max()))
        robust.append({'offset_channels':OFFSETS[oi],'fixed_original4':witness,'max7':witness7})
        if oi==0:
            require(saved['exact_fixed4_zero_offset_witness_full16_absolute_centers']==record['exact_fixed_original4']['witness_full16_absolute_centers']
                    and saved['exact_max7_zero_offset_witness_full16_absolute_centers']==record['exact_max7']['witness_full16_absolute_centers'],
                    'Exact zero-offset witness full16 summary differs')
    ranks={}
    for name,vector in [('fixed_original4',fixed),('max7',all7)]:
        greater=sum(v>vector[0] for v in vector[1:]);equal=sum(v==vector[0] for v in vector[1:])
        ranks[name+'_control_strictly_greater_count']=greater;ranks[name+'_control_equal_count']=equal
        ranks[name+'_rank_among_target_plus8']=greater+1
    require(saved['control_ranks']==ranks,'Exact descriptive control ranks differ')
    return bins,wi,path_rows,scores,clean,dc,{'profile_id':profile['profile_id'],'path_count':n,
               'max_row_error':row_error,'max_score_error':score_error,'max_prior405_score_error':prior_error,
               'original4_score_error':abs(original_score-profile['fixed_four_row_score']),
               'control_ranks':ranks,'winner_robust_geometry':robust}


def audit_exact_injection(saved,prior,profile,geometry,windows,bins,wi,path_rows,scores,dc):
    host=OFFSETS.index(512);true=np.asarray(prior['true_absolute_centers'],dtype=np.int64)
    start=prior['true_window_start_row'];true_wi=STARTS.index(start);amplitude=prior['amplitude_per_active_standardized_single_bin']
    active=np.zeros(16,dtype=np.bool_);active[start:start+4]=True
    native=bins+512
    matches=((native==true[path_rows])&active[path_rows]).sum(axis=1)
    baseline=np.where(dc[host],-np.inf,scores[host]);injected=np.where(dc[host],-np.inf,scores[host]+amplitude*matches/2.)
    pi,error,_=audit_exact_winner(saved['exact_winner'],injected,profile,geometry,windows,bins,wi,host)
    signal=np.where(dc[host],-1,matches);best_signal=int(np.argmax(signal))
    d0=F(profile['selected_track']['drift_hz_s']);delta=F(prior['true_drift_fraction_of_half_original_step'])*F(H_FLOAT)
    phase=F(prior['true_phase_channels']);base=int(profile['selected_track']['source_reference_channel'])+512
    rational=centers_at(base,[F(t)/F(DF_FLOAT) for t in profile['times_from_primary_reference_s']],d0,delta,phase)
    expected={'profile_id':prior['profile_id'],'origin_scan_id':prior['origin_scan_id'],'context_scan_id':prior['context_scan_id'],
              'origin_rank':prior['origin_rank'],'host_offset_channels':512,
              'true_drift_fraction_of_half_original_step':prior['true_drift_fraction_of_half_original_step'],
              'true_drift_hz_s':prior['true_drift_hz_s'],'true_phase_channels':prior['true_phase_channels'],
              'true_window_index':true_wi,'true_window_start_row':start,'true_active_source_rows':list(range(start,start+4)),
              'canonical_float_truth_absolute_centers':true.tolist(),'canonical_rational_truth_absolute_centers':list(rational),
              'canonical_float_vs_rational_active4_different_channel_count':int(np.count_nonzero(true[start:start+4]!=np.asarray(rational[start:start+4]))),
              'canonical_float_truth_active4_path_attainable_exact':tuple(int(n)-512 for n in true[start:start+4]) in windows[true_wi],
              'amplitude_per_active_standardized_single_bin':amplitude,
              'exact_winner_matches_true_activity_window':int(wi[pi])==true_wi,
              'exact_winner_matching_active4_count':int(matches[pi]),
              'signal_only_exact_best_matching_active4_count':int(matches[best_signal]),
              'signal_only_exact_best_path_index':best_signal,'signal_only_exact_best_window_index':int(wi[best_signal]),
              'signal_only_exact_best_matches_true_activity_window':int(wi[best_signal])==true_wi,
              'legacy_fine_winner_matches_true_activity_window':prior['fine_winner_matches_true_activity_window'],
              'legacy_fine_winner_matching_active4_count':prior['fine_winner_matching_active4_count'],
              'model':'additive_standardized_residual_native_delta_bin_frozen_normalization',
              'raw_sensitivity_or_FAP_established':False}
    for key,value in expected.items():
        require(saved[key]==value,'Exact injection '+key+' differs')
    numbers={'exact_score':float(injected[pi]),'exact_zero_injection_max7_score':float(baseline.max()),
             'exact_max7_uplift':float(injected[pi]-baseline.max()),'exact_winner_matching_active4_fraction':float(matches[pi]/4.),
             'signal_only_exact_best_matched_row_fraction':float(matches[best_signal]/4.),
             'legacy_fine_score':prior['fine_score'],'legacy_fine_zero_injection_max7_score':prior['fine_zero_injection_max7_score'],
             'legacy_fine_max7_uplift':prior['fine_max7_uplift'],
             'legacy_signal_only_fine_best_matched_row_fraction':prior['signal_only_fine_best_matched_row_fraction'],
             'coarse_max7_score':prior['coarse_max7_score'],'coarse_truewindow_score':prior['coarse_truewindow_score'],
             'coarse_truewindow_signal_only_matched_row_fraction':prior['coarse_truewindow_signal_only_matched_row_fraction']}
    for key,value in numbers.items():
        error=max(error,close(saved[key],value,'Exact injection '+key+' differs'))
    return {'amplitude':amplitude,'max_score_error':error,'signal_only_full_capture':int(matches[best_signal])==4,
            'noisy_winner_full_capture':int(matches[pi])==4,'noisy_winner_activity_match':int(wi[pi])==true_wi,
            'old_signal_only_full_capture':prior['signal_only_fine_best_matching_active4_count']==4,
            'old_noisy_winner_full_capture':prior['fine_winner_matching_active4_count']==4}


def parse_args():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',required=True)
    parser.add_argument('--check-only',action='store_true')
    parser.add_argument('--geometry-self-test',action='store_true')
    parser.add_argument('--inputs-root')
    parser.add_argument('--portable-inputs',action='store_true')
    parser.add_argument('--output-dir',default='qa_results')
    for name in ('scope-sha256','qa-sha256','receipt-sha256','root-go-sha256'):
        parser.add_argument('--'+name)
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
    for digest in (args.scope_sha256,args.qa_sha256,args.receipt_sha256,args.root_go_sha256):
        require(digest is not None and re.fullmatch('[0-9a-f]{64}',digest),'Exact frozen SHA256 arguments required')
    require(sha(Path(__file__).resolve())==args.qa_sha256,'Independent QA code changed after freeze')
    run(Path(args.root).resolve(),args)


def validate_scope(scope):
    require(scope['schema']=='SETI_EXACT_CONTINUOUS_ROUNDING_FOLLOWUP_V1','Wrong exact followup scope')
    g=scope['geometry'];n=scope['normalization'];i=scope['injections'];b=scope['budget'];c=scope['counts']
    require(g['df_hz']==DF_FLOAT and g['drift_half_step_hz_s']==H_FLOAT and g['offset_channels']==OFFSETS
            and g['phase_box_channels']==[-.5,.5] and g['window_start_rows']==STARTS
            and g['width_channels']==1 and g['window_length_rows']==4 and g['dc_channels']==DC
            and g['tie_policy']=='windowstart ascending, native4path lexicographic; first maximum'
            and g['legacy_only_path_count']==0,'Frozen exact geometry differs')
    require(n['median_width']==501 and n['original_core_channels']==4096 and n['raw_crop_shape']==[16,12096]
            and n['reuse_original_normalization'] is True and n['absolute_tolerance']==ATOL
            and n['relative_tolerance']==RTOL,'Frozen normalization differs')
    require(i['amplitudes']==[2,8] and i['drift_fractions_of_half_step']==[-.73,.61]
            and i['phase_channels']==[-.37,.29] and i['host_offset_channels']==512
            and i['window_start_rows']==STARTS and i['cases']==3024
            and i['reuse_prior_canonical_float_truth_channels'] is True
            and i['physical_sensitivity'] is False,'Frozen canonical injection model differs')
    require(b['CPU_seconds']==CPU_CAP and b['wall_seconds']==WALL_CAP and b['memory_bytes']==MEMORY_CAP
            and b['DKK']==0,'Frozen bounded resource reservation differs')
    expected={'profiles':54,'windows':378,'exact_unique_paths_zero_offset':22235,
              'exact_path_scores_all_offsets':200115,'exact_row_terms_all_offsets':800460,
              'primary_fixed4_paths_zero_offset':3078,'primary_fixed4_paths_all_offsets':27702,
              'conditional_injections':3024,'distinct_injection_geometries':1512}
    require(all(c[k]==v for k,v in expected.items()),'Frozen exact family count forecast differs')
    require(len(scope['profile_ids'])==54 and len(set(scope['profile_ids']))==54,'Frozen profile identity count differs')
    require(scope['interpretation']['qualified_SETI_detection'] is False
            and scope['interpretation']['calibrated_SNR_FAP'] is False
            and scope['interpretation']['physical_sensitivity'] is False
            and scope['interpretation']['independent_replication'] is False,'Unsupported scientific interpretation')


def run(stage,args):
    global np
    started=time.monotonic();scope_path=stage/'SCOPE.json';go_path=stage/'QA_GO.json'
    receipt_path=stage/'results'/'EXECUTION_RECEIPT.json'
    require(sha(scope_path)==args.scope_sha256 and sha(go_path)==args.root_go_sha256
            and sha(receipt_path)==args.receipt_sha256,'Frozen exact numerical QA gate digest differs')
    scope=decode(scope_path.read_bytes());validate_scope(scope)
    go=decode(go_path.read_bytes())
    require(go['status']=='GO_INDEPENDENT_EXACT_ROUNDING_QA' and go['scope_sha256']==args.scope_sha256
            and go['qa_code_sha256']==args.qa_sha256 and go['producer_receipt_sha256']==args.receipt_sha256,
            'Root numerical QA GO does not authorize exact code/scope/receipt')
    receipt=decode(receipt_path.read_bytes())
    require(receipt['status']=='COMPLETE_BOUNDED_EXACT_CONTINUOUS_ROUNDING_PRODUCTION'
            and receipt['scope']['sha256']==args.scope_sha256,'Exact observed producer receipt mismatch')
    inputs=Path(args.inputs_root or scope['execution_input_root']).resolve()
    require(args.portable_inputs or inputs==Path(scope['execution_input_root']).resolve(),
            'Portable flag required to substitute frozen execution input root')
    out=confined(stage,args.output_dir);require(not out.exists() and out!=stage and out!=stage/'results',
                                             'Fresh separate QA output required')
    pins={p['path']:p for p in scope['input_pins']}
    require(len(pins)==len(scope['input_pins'])==180,'Exact input scope pin count differs')
    products={p['path']:p for p in receipt['outputs']}
    require(len(products)==len(receipt['outputs'])==58,'Producer output pin count differs')
    read_pins={}

    def authenticated(base,pin):
        path=confined(base,pin['path']);raw=path.read_bytes()
        require(len(raw)==pin['bytes'] and hashlib.sha256(raw).hexdigest()==pin['sha256'],
                'Frozen input/product bytes differ: '+pin['path'])
        read_pins[str(path)]={'bytes':len(raw),'sha256':pin['sha256']}
        return raw

    def input_pin(pin):
        require(pin['path'] in pins and all(pins[pin['path']][k]==pin[k] for k in ('path','bytes','sha256')),
                'Input not frozen by exact scope')
        return authenticated(inputs,pin)

    for pin in scope['input_pins']:
        authenticated(inputs,pin)
    result_root=stage/'results'
    names=('PROFILES.json','PROFILES.csv','INJECTIONS.json','INJECTIONS.csv')
    require(set(names)<=set(products),'Exact output summaries missing')
    summary={name:authenticated(result_root,products[name]) for name in names}
    profile_doc=decode(summary['PROFILES.json']);injection_doc=decode(summary['INJECTIONS.json'])
    require(profile_doc['schema']=='SETI_EXACT_CONTINUOUS_ROUNDING_OBSERVED_PROFILES_V1'
            and profile_doc['status']=='COMPLETE_54_EXACT_ATTAINABLE_PATH_PROFILES','Exact profile result schema/status differs')
    require(injection_doc['schema']=='SETI_EXACT_ROUNDING_RESIDUAL_DOMAIN_INJECTION_V1'
            and injection_doc['count']==3024,'Exact injection result schema/count differs')
    require(profile_doc['scope_sha256']==args.scope_sha256
            and profile_doc['geometry_sha256']==scope['geometry_pin']['sha256']
            and profile_doc['qualified_SETI_detection'] is False
            and profile_doc['calibrated_SNR_FAP'] is False,'Exact profile header scope/interpretation differs')
    saved_profiles=profile_doc['profiles'];saved_trials=injection_doc['trials']
    require(len(saved_profiles)==54 and [p['profile_id'] for p in saved_profiles]==scope['profile_ids']
            and len(profile_doc['normalization_authentication'])==54,'Exact observed profile count/identity differs')
    require(len(saved_trials)==3024,'Exact conditional injection count differs')
    audit_csv(summary['PROFILES.csv'],saved_profiles,'Exact profile CSV')
    audit_csv(summary['INJECTIONS.csv'],saved_trials,'Exact injection CSV')
    matrix=decode(input_pin(scope['matrix_pin']));geometry_doc=decode(input_pin(scope['geometry_pin']))
    old_profiles=decode(input_pin(scope['old_profiles_pin']))
    old_trials=decode(input_pin(scope['old_injections_pin']))['trials']
    require(len(old_trials)==3024 and len(old_profiles['profiles'])==54,'Canonical legacy result counts differ')
    require([p['profile_id'] for p in matrix['profiles']]==scope['profile_ids']
            and [p['profile_id'] for p in geometry_doc['profiles']]==scope['profile_ids'],
            'Exact geometry/source matrix profile identities differ')
    crops={c['crop_id']:c for c in matrix['normalization_crops']}
    old_family_pins={p['profile_id']:p for p in scope['legacy_family_pins']}
    require(len(crops)==54 and len(old_family_pins)==54,'Frozen crop/legacy family identities differ')
    source_prefix=scope['matrix_pin']['path'][:-len(scope['matrix_path'])]

    def crop_pin(pin):
        rewritten={**pin,'path':source_prefix+pin['path']}
        require(rewritten['path'] in pins and pins[rewritten['path']]==rewritten,'Original raw/norm pin not scope frozen')
        return rewritten

    def archive(base,pin):
        with np.load(io.BytesIO(authenticated(base,pin)),allow_pickle=False) as a:
            require(len(a.files)==len(set(a.files)),'Duplicate saved NPZ members')
            return {key:a[key] for key in a.files}

    def alarm(signum,frame):
        raise TimeoutError('Independent exact QA exceeded frozen wall bound')

    resource.setrlimit(resource.RLIMIT_AS,(MEMORY_CAP,MEMORY_CAP));resource.setrlimit(resource.RLIMIT_CPU,(CPU_CAP,CPU_CAP))
    signal.signal(signal.SIGALRM,alarm);signal.alarm(WALL_CAP)
    import numpy as numpy
    np=numpy
    out.mkdir();geometry_reports=[];normal_reports=[];score_reports=[];trial_reports=[]
    seen_crops=set();seen_trials=set();feasible_dimensions={0:0,1:0,2:0};primary_paths=0
    try:
        for index,(profile,geom,saved) in enumerate(zip(matrix['profiles'],geometry_doc['profiles'],saved_profiles)):
            windows,g_report=audit_exact_geometry(geom,profile);geometry_reports.append(g_report)
            for window in windows:
                for cert in window.values():
                    feasible_dimensions[cert['feasible_dimension']]+=1
            primary_paths+=len(windows[STARTS.index(profile['selected_track']['window_start_row'])])
            crop=crops[profile['normalization_crop_id']]
            require(crop['raw_crop']==profile['raw_normalization_crop'] and crop['normalization']==profile['normalization'],
                    'Original profile crop provenance mismatch')
            require(saved['input_raw_crop']==crop['raw_crop'] and saved['input_normalization']==crop['normalization'],
                    'Exact score product provenance mismatch')
            raw=archive(inputs,crop_pin(crop['raw_crop']))
            require(set(raw)=={'raw_power','source_channel0','normalization_source_channels','absolute_time_rows'},
                    'Saved raw12096 schema differs')
            require(raw['source_channel0'].dtype==np.dtype('<i8') and raw['source_channel0'].shape==()
                    and raw['normalization_source_channels'].dtype==np.dtype('<i8')
                    and raw['absolute_time_rows'].dtype==np.dtype('<i8'),'Original crop coordinate dtype differs')
            crop0=int(raw['source_channel0']);core0=crop['normalization_source_channel_interval_half_open'][0]
            require(crop['source_channel_interval_half_open']==[crop0,crop0+12096]
                    and crop['normalization_source_channel_interval_half_open']==[core0,core0+4096],'Original crop intervals differ')
            exact(raw['normalization_source_channels'],np.arange(core0,core0+4096),'Original core native channels differ')
            exact(raw['absolute_time_rows'],np.arange(16),'Original absolute time rows differ')
            require(np.isfinite(raw['raw_power']).all() and np.all(raw['raw_power']>=0),'Raw crop values invalid')
            auth=profile_doc['normalization_authentication'][index]
            require(auth['profile_id']==profile['profile_id'] and auth['reused_saved_parameters'] is True
                    and auth['original_core_local_interval_half_open']==[4000,8096],
                    'Saved normalization authentication metadata differs')
            original_normal=decode(input_pin(crop_pin(crop['normalization'])))
            normal=direct_normalization(raw['raw_power'],core0,crop0);normal_error=0.
            for key,value in normal.items():
                field_error=close(original_normal[key],value,'All direct501 normalization '+key+' differs')
                normal_error=max(normal_error,field_error)
                close(auth['max_absolute_errors'][key],field_error,'Saved normalization error metric differs')
            exact(original_normal['normalization_unmasked_counts'],np.full(16,4096),'Original normalization counts differ')
            exact(original_normal['normalization_source_channels'],np.arange(core0,core0+4096),'Original normalization core labels differ')
            require(profile['normalization_crop_id'] not in seen_crops,'Unexpected duplicate normalization core')
            seen_crops.add(profile['normalization_crop_id'])
            normal_reports.append({'crop_id':profile['normalization_crop_id'],'max_absolute_error':normal_error})
            path_pin=saved['path_arrays'];require(path_pin['path'] in products and products[path_pin['path']]==path_pin,
                                                'Exact numerical path product pin differs from receipt')
            arrays=archive(result_root,path_pin)
            old_pin=old_family_pins[profile['profile_id']];input_pin(old_pin);old_arrays=archive(inputs,old_pin)
            bins,wi,rows,scores,clean,dc,s_report=audit_numerical_profile(saved,profile,geom,windows,arrays,
                                                raw['raw_power'],crop0,normal,old_arrays)
            score_reports.append(s_report)
            profile_prior=[(ti,t) for ti,t in enumerate(old_trials) if t['profile_id']==profile['profile_id']]
            require(len(profile_prior)==56,'Canonical prior injection per-profile count differs')
            for trial_index,prior in profile_prior:
                require(trial_index not in seen_trials,'Canonical injection case repeated')
                seen_trials.add(trial_index)
                trial_reports.append(audit_exact_injection(saved_trials[trial_index],prior,profile,geom,windows,bins,wi,rows,scores,dc))
            if (index+1)%9==0:
                print(json.dumps({'QA_exact_profiles_complete':index+1,'wall_seconds':round(time.monotonic()-started,3)}),flush=True)
        require(len(seen_crops)==54 and len(seen_trials)==3024 and primary_paths==3078
                and sum(r['feasible_native_paths'] for r in geometry_reports)==22235,'Exact independent QA did not complete frozen family')
        for name,pin in read_pins.items():
            path=Path(name);require(path.stat().st_size==pin['bytes'] and sha(path)==pin['sha256'],
                                   'Authenticated exact QA input/product changed during run')
        require(sha(scope_path)==args.scope_sha256 and sha(go_path)==args.root_go_sha256
                and sha(receipt_path)==args.receipt_sha256 and sha(Path(__file__).resolve())==args.qa_sha256,
                'Exact authorization/code changed during numerical QA')
        elapsed=time.monotonic()-started;usage=resource.getrusage(resource.RUSAGE_SELF)
        require(elapsed<=WALL_CAP and usage.ru_utime+usage.ru_stime<=CPU_CAP and usage.ru_maxrss*1024<=MEMORY_CAP,
                'Exact numerical QA exceeded reserved budget')
        recovery={}
        for amplitude in (2,8):
            panel=[r for r in trial_reports if r['amplitude']==amplitude]
            recovery[str(amplitude)]={key:sum(r[key] for r in panel) for key in
                    ('signal_only_full_capture','noisy_winner_full_capture','noisy_winner_activity_match',
                     'old_signal_only_full_capture','old_noisy_winner_full_capture')}
            recovery[str(amplitude)]['cases']=len(panel)
        winner_dimensions={0:0,1:0,2:0}
        for report in score_reports:
            for offset in report['winner_robust_geometry']:
                for name in ('fixed_original4','max7'):
                    winner_dimensions[offset[name]['feasible_region_dimension']]+=1
        result={'schema':'SETI_INDEPENDENT_EXACT_CONTINUOUS_ROUNDING_NUMERICAL_QA_V1',
                'status':'PASS_INDEPENDENT_EXACT_NUMERICAL_54_CORES_378_COMPLETE_WINDOWS_22235_PATHS_200115_SCORES_3024_INJECTIONS',
                'scope_sha256':args.scope_sha256,'qa_code_sha256':args.qa_sha256,
                'producer_receipt_sha256':args.receipt_sha256,'root_go_sha256':args.root_go_sha256,
                'portable_inputs':args.portable_inputs,'actual_input_root':str(inputs),
                'original_scope_input_root':scope['execution_input_root'],'producer_imported':False,
                'independent_geometry_method':'nativefirstbin/difference candidates; exactphase elimination with openodd halfboundaries',
                'authenticated_scope_inputs':180,'profiles':54,'normalization_cores':54,'normalization_rows':864,
                'direct501_normalization_core_cells':54*16*4096,'exact_window_sets':378,
                'exact_unique_paths_zero_offset':22235,'exact_path_scores_all_offsets':200115,
                'exact_row_terms_all_offsets':800460,'primary_fixed4_paths_zero_offset':3078,
                'conditional_injections':3024,'offset_summaries':486,
                'independent_candidate_tuples':sum(r['candidate_tuples'] for r in geometry_reports),
                'feasible_region_dimension_counts':feasible_dimensions,'winner_feasible_region_dimension_counts':winner_dimensions,
                'max_normalization_error':max(r['max_absolute_error'] for r in normal_reports),
                'max_row_error':max(r['max_row_error'] for r in score_reports),
                'max_score_error':max(r['max_score_error'] for r in score_reports),
                'max_prior405_score_error':max(r['max_prior405_score_error'] for r in score_reports),
                'max_original4_score_error':max(r['original4_score_error'] for r in score_reports),
                'max_injection_score_error':max(r['max_score_error'] for r in trial_reports),
                'injection_recovery_by_amplitude':recovery,'CPU_seconds':usage.ru_utime+usage.ru_stime,
                'wall_seconds':elapsed,'peak_memory_bytes':usage.ru_maxrss*1024,
                'tolerance_abs':ATOL,'tolerance_rel':RTOL,'qualified_SETI_detection':False,
                'calibrated_FAP':False,'physical_sensitivity':False,'independent_replication':False,
                'geometry_reports':geometry_reports,'normalization_reports':normal_reports,'profile_reports':score_reports}
        json_out(out/'QA_RECEIPT.json',result)
        print(json.dumps({k:v for k,v in result.items() if k not in ('geometry_reports','normalization_reports','profile_reports')},sort_keys=True),flush=True)
    except BaseException as exc:
        json_out(out/'QA_FAILURE.json',{'status':'FAIL_CLOSED_INDEPENDENT_EXACT_NUMERICAL_QA',
                    'error_type':type(exc).__name__,'error':str(exc),'profiles_complete':len(score_reports),
                    'geometry_profiles_complete':len(geometry_reports),'injections_complete':len(trial_reports)})
        raise
    finally:
        signal.alarm(0)


if __name__=='__main__':
    main()
