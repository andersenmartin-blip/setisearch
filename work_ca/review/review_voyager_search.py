"""Independent direct scalar search of sealed original Voyager hit stamps.

Wire decode uses struct-only parser. Template rounding is integer rational
ties-to-even; track powers use math.fsum; row medians use statistics.median.
No production analysis functions are imported.
"""
from pathlib import Path
import hashlib
import json
import math
import statistics
import sys
import numpy as np
from decode_voyager_independent import decode, RAW_SHA, GIT_SHA

def rounded_fraction(n,d):
    q,r=divmod(n,d)
    return q+(2*r>d or (2*r==d and q%2==1))

def independent_search(a,meta,production_arrays):
    nt,nc=a.shape
    rows=a.tolist()
    baseline=math.fsum(statistics.median(row) for row in rows)
    seen=set(); count=0; valid_patterns=0; duplicate_patterns=0
    best=None; bestscore=-math.inf; bestties=0; totalpatterns=0
    max_sum_error=0.0
    medians=[statistics.median(row) for row in rows]
    assert np.array_equal(production_arrays['row_medians'],medians)
    for numerator in range(-8*(nc-1),8*(nc-1)+1):
        endpoint=numerator/8
        rate=endpoint*meta['foff']*1e6/((nt-1)*meta['tsamp'])
        if abs(rate)>4: continue
        totalpatterns+=1
        offsets=tuple(rounded_fraction(numerator*t,8*(nt-1)) for t in range(nt))
        np_offsets=np.rint(np.arange(nt,dtype=np.float64)*(numerator/8)/(nt-1)).astype(int)
        assert tuple(np_offsets)==offsets, 'Floating and exact-rational roundings disagree'
        if offsets in seen:
            duplicate_patterns+=1;continue
        seen.add(offsets)
        pattern_index=len(seen)-1
        assert int(production_arrays['endpoint_shift_eighth'][pattern_index])==numerator
        assert tuple(production_arrays['shifts'][pattern_index])==offsets
        lo=max(0,-min(offsets));hi=min(nc,nc-max(offsets))
        assert int(production_arrays['valid_counts'][pattern_index])==max(hi-lo,0)
        assert np.isnan(production_arrays['raw_sums'][pattern_index,:lo]).all()
        assert np.isnan(production_arrays['raw_sums'][pattern_index,hi:]).all()
        if lo>=hi: continue
        valid_patterns+=1
        for start in range(lo,hi):
            power=math.fsum(rows[t][start+o] for t,o in enumerate(offsets))
            error=abs(power-float(production_arrays['raw_sums'][pattern_index,start]))
            assert error==0, 'Direct scalar sum does not match production'
            max_sum_error=max(max_sum_error,error)
            score=power-baseline
            count+=1
            if score>bestscore:
                bestscore=score;bestties=1
                best={'start_channel':start,'endpoint_shift_channels':endpoint,
                      'endpoint_numerator_eighths':numerator,'offsets':list(offsets),
                      'drift_rate_hz_s':rate,'track_raw_power_sum':power,
                      'row_median_baseline_sum':baseline,'excess_sum':score,
                      'start_frequency_mhz':meta['fch1']+start*meta['foff']}
            elif score==bestscore: bestties+=1
    assert len(seen)==len(production_arrays['endpoint_shift_eighth'])
    return {'best':best,'track_count':count,'unique_offset_patterns':len(seen),
            'valid_patterns':valid_patterns,'input_endpoint_values':totalpatterns,
            'duplicate_patterns':duplicate_patterns,'best_tied_tracks':bestties,
            'maximum_scalar_production_sum_error':max_sum_error}

def main():
    root=Path(__file__).resolve().parents[2]
    data=root/'work_ca/new_data';output=Path(__file__).parent/'VOYAGER_REVIEW_CA.json'
    raw=(data/'voyager.hits').read_bytes(); objects=decode(raw)
    bound=[data/'voyager.hits',data/'analyze_voyager.py',data/'SCOPE_CA_VOYAGER.json',data/'RESULT_CA_VOYAGER.json',
           data/'metadata.json',data/'hit.capnp',data/'hit.capnp.h']
    bound += [data/f'stamp_{i}.npy' for i in range(len(objects))]
    bound += [data/f'search_{i}.npz' for i in range(len(objects))]
    bound_sha={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in bound}
    production=json.loads((data/'RESULT_CA_VOYAGER.json').read_text())
    authored=json.loads((data/'metadata.json').read_text())
    records=[]
    for i,obj in enumerate(objects):
        a=obj['array'];m=obj['metadata'];ref=obj['reference']
        assert np.isfinite(a).all() and (a>0).all()
        assert authored[i]['filterbank']==m and authored[i]['reference_signal']==ref
        same=np.load(data/f'stamp_{i}.npy',allow_pickle=False)
        assert same.dtype==a.dtype and same.shape==a.shape and same.tobytes()==a.tobytes()
        with np.load(data/f'search_{i}.npz',allow_pickle=False) as z:
            arrays={key:z[key] for key in z.files}
        calc=independent_search(a,m,arrays)
        reference_start=(ref['frequency']-m['fch1'])/m['foff']
        reference_endpoint=ref['driftRate']*((m['numTimesteps']-1)*m['tsamp'])/(m['foff']*1e6)
        start_error=calc['best']['start_channel']-reference_start
        drift_error=calc['best']['endpoint_shift_channels']-reference_endpoint
        calc.update({'hit':i,'sample_count':int(a.size),'shape':list(a.shape),'data_sha256':obj['raw_data_sha256'],
                     'minimum':float(a.min()),'maximum':float(a.max()),
                     'reference_start_channel':reference_start,'reference_endpoint_channels':reference_endpoint,
                     'reference_start_error_channels':start_error,'reference_endpoint_error_channels':drift_error,
                     'consistent_with_stored_reference':abs(start_error)<=2 and abs(drift_error)<=2})
        prec=production['records'][i];pb=prec['best'];cb=calc['best']
        assert prec['shape']==calc['shape'] and prec['samples']==calc['sample_count']
        assert prec['sample_min']==calc['minimum'] and prec['sample_max']==calc['maximum']
        assert prec['unique_shift_sequences']==calc['unique_offset_patterns']
        assert prec['full_support_track_count']==calc['track_count']
        assert pb['start_channel']==cb['start_channel']
        assert pb['endpoint_shift_eighth']==cb['endpoint_numerator_eighths']
        assert pb['endpoint_shift_channels']==cb['endpoint_shift_channels']
        assert pb['selected_channels']==[cb['start_channel']+o for o in cb['offsets']]
        assert pb['drift_rate_Hz_s']==cb['drift_rate_hz_s']
        assert pb['f_start_MHz']==cb['start_frequency_mhz']
        assert pb['raw_sum']==cb['track_raw_power_sum']
        assert pb['excess_sum_above_row_medians']==cb['excess_sum']
        assert prec['baseline_sum_row_medians']==cb['row_median_baseline_sum']
        assert prec['within_predeclared_reference_tolerances']==calc['consistent_with_stored_reference']
        row_excess=[float(a[t,pb['selected_channels'][t]])-statistics.median(a[t].tolist()) for t in range(len(a))]
        assert row_excess==prec['selected_row_excess']
        assert sum(v>0 for v in row_excess)==prec['rows_above_own_median']==16
        records.append(calc)
    assert production['total_power_samples']==sum(x['sample_count'] for x in records)
    assert production['total_full_support_tracks']==sum(x['track_count'] for x in records)
    assert production['reference_consistent_stamps']==sum(x['consistent_with_stored_reference'] for x in records)
    assert production['integration_duration_seconds']==objects[0]['metadata']['tsamp']*16
    assert production['first_to_last_sample_span_seconds']==objects[0]['metadata']['tsamp']*15
    assert all(hashlib.sha256((root/p).read_bytes()).hexdigest()==digest for p,digest in bound_sha.items())
    result={'schema':'SETI_CA_VOYAGER_INDEPENDENT_REVIEW_V1','status':'PASS_INDEPENDENT_WIRE_AND_FULL_SCALAR_SEARCH_REVIEW',
            'raw_sha256':RAW_SHA,'git_blob_sha':GIT_SHA,'raw_bytes':len(raw),
            'hits':len(records),'exact_samples_verified':sum(x['sample_count'] for x in records),
            'total_independently_scored_tracks':sum(x['track_count'] for x in records),
            'single_observing_start':len(set(x['metadata']['tstart'] for x in objects))==1,
            'stored_reference_consistent_hits':sum(x['consistent_with_stored_reference'] for x in records),
            'records':records,'production_inputs_and_outputs_sha256':bound_sha,'bound_bytes_unchanged':True,
            'methods':['Bounded independent struct-only unpacked one-segment CapnProto wire decoder',
            'Exact integer-rational nearest-even template shifts; equality with NumPy rounding verified for every examined endpoint',
            'Every fully supported track independently scored using scalar math.fsum and statistics.median'],
            'limits':['Known human-transmitter selected hit stamps from one historical scan; not blind survey or ON/OFF validation.',
                     'Bounded decoder handles this SHA-bound fixture only; not a general validated CapnProto adapter.',
                     'Comparison is to author-selected metadata, not independent truth or sigma/FAP calibration.'],
            'source_sha256':{str(Path(__file__).relative_to(root)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                             'work_ca/review/decode_voyager_independent.py':hashlib.sha256((Path(__file__).parent/'decode_voyager_independent.py').read_bytes()).hexdigest()}}
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['status','hits','exact_samples_verified','total_independently_scored_tracks','stored_reference_consistent_hits']}))

if __name__=='__main__': main()
