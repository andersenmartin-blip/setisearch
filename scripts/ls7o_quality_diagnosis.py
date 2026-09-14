#!/usr/bin/env python3
"""Post-evaluation attribution of the fixed LS7O availability gate.

No quality policy, reference membership, fits, response or thresholds change.
"""
from collections import Counter
import gzip
import json
from pathlib import Path

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_ls7o_response'


def read_rows(path):return [json.loads(x) for x in gzip.decompress(path.read_bytes()).splitlines()]
def save(path,data):path.write_text(json.dumps(data,indent=2,allow_nan=False)+'\n')


def main():
    windows=read_rows(ROOT/'results_ls7i_background/native_windows.jsonl.gz')
    estimates={r['window_id']:r for r in read_rows(OUT/'reference_motion.jsonl.gz')}
    sectors=[];all_windows=[]
    for sector in [29,32]:
        z=np.load(ROOT/f'results_ls7o_inputs/references_s{sector:03d}.npz',allow_pickle=False)
        q=z['quality'];c=z['centroid_xy'];e=z['error_xy']
        finite=np.isfinite(c).all(-1)&np.isfinite(e).all(-1)&(e>0).all(-1)
        valid=finite&(q==0)
        refrows=[]
        for j,tic in enumerate(z['tic']):
            hist={str(k):v for k,v in sorted(Counter(int(v) for v in q[j].ravel()).items())}
            bits={str(1<<k):int(np.count_nonzero(q[j]&(1<<k))) for k in range(16) if np.any(q[j]&(1<<k))}
            refrows.append({'tic':int(tic),'context_rows':4010,'finite_positive_error_rows':int(finite[j].sum()),
                            'quality_zero_rows':int((q[j]==0).sum()),'valid_rows':int(valid[j].sum()),
                            'quality_histogram':hist,'nonexclusive_bit_counts':bits})
        records=[]
        for w in windows:
            if w['sector']!=sector:continue
            a,lo,hi=w['anchor'],w['start'],w['stop']
            side=list(range(lo-60,lo-5))+list(range(hi+5,hi+60));event=list(range(lo,hi));selected=side+event
            record={'window_id':w['window_id'],'sector':sector,'anchor':a,
                    'all_six_finite_positive_errors':bool(finite[:,a,selected].all()),
                    'all_six_quality_zero_sideband':bool((q[:,a,side]==0).all()),
                    'all_six_quality_zero_event':bool((q[:,a,event]==0).all()),
                    'all_six_valid_selected':bool(valid[:,a,selected].all()),
                    'actual_reference_prediction_available':estimates[w['window_id']]['valid'],
                    'per_reference':[{'tic':int(tic),'bad_sideband_quality_rows':int(np.count_nonzero(q[j,a,side])),
                                      'bad_event_quality_rows':int(np.count_nonzero(q[j,a,event])),
                                      'bad_numeric_selected_rows':int(np.count_nonzero(~finite[j,a,selected]))}
                                     for j,tic in enumerate(z['tic'])]}
            if not record['all_six_valid_selected']:assert not record['actual_reference_prediction_available']
            records.append(record)
        all_windows.extend(records)
        counts=np.sum(valid,axis=0)
        sectors.append({'sector':sector,'reference_rows':int(q.size),'context_cadences':4010,
                        'references':refrows,'simultaneous_valid_reference_count_histogram':{str(k):int(np.count_nonzero(counts==k)) for k in range(7)},
                        'window_denominator':210,
                        'window_counts':{k:sum(r[k] for r in records) for k in ['all_six_finite_positive_errors','all_six_quality_zero_sideband','all_six_quality_zero_event','all_six_valid_selected','actual_reference_prediction_available']},
                        'minimum_quality_zero_sideband_rows_per_reference_window':min(110-p['bad_sideband_quality_rows'] for r in records for p in r['per_reference'])})
    report={'kind':'post-evaluation attribution only; no alternative predictor evaluated','sectors':sectors,
            'quality_bit_primary_reference':'https://archive.stsci.edu/files/live/sites/mast/files/home/missions-and-data/active-missions/tess/_documents/EXP-TESS-ARC-ICD-TM-0014-Rev-F.pdf',
            'quality_bit_table':32,
            'observed_bit_meanings':{'64':'cosmic ray in an optimal-aperture pixel','512':'impulsive outlier removed before cotrending','1024':'cosmic ray detected on a collateral row or column','4096':'scattered-light exclusion'},
            'flag_counts_are_nonexclusive':True}
    observed={bit for s in sectors for r in s['references'] for bit in r['nonexclusive_bit_counts']}
    report['uninterpreted_observed_bits']=sorted(observed-set(report['observed_bit_meanings']),key=int)
    save(OUT/'quality_diagnosis.json',report)
    OUT.joinpath('quality_windows.jsonl.gz').write_bytes(gzip.compress(b''.join((json.dumps(r,separators=(',',':'))+'\n').encode() for r in all_windows),mtime=0))
    print(json.dumps({'sectors':[{k:s[k] for k in ['sector','window_counts','simultaneous_valid_reference_count_histogram']} for s in sectors]},indent=2))


if __name__=='__main__':main()
