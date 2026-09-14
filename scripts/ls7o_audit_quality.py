#!/usr/bin/env python3
"""Independent scalar raw-byte audit of posthoc LS7O quality/scope accounting."""
import gzip
import json
import math
from pathlib import Path
import struct
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_ls7o_response'


def read(path):return json.loads(path.read_text())
def rows(path):return [json.loads(x) for x in gzip.decompress(path.read_bytes()).splitlines()]


def main():
    quality=read(OUT/'quality_diagnosis.json');ledger=rows(OUT/'quality_windows.jsonl.gz')
    source=read(ROOT/'results_ls7o_inputs/sources.json');old=rows(ROOT/'results_ls7i_background/native_windows.jsonl.gz')
    model=rows(OUT/'reference_motion.jsonl.gz');model_by_id={r['window_id']:r for r in model}
    numeric=0;checked=0
    for sector in [29,32]:
        expected=next(s for s in quality['sectors'] if s['sector']==sector)
        q=[]
        for record in [r for r in source['records'] if r['sector']==sector]:
            raw=gzip.decompress((ROOT/'results_ls7o_inputs'/record['raw_path']).read_bytes())
            values=[]
            for i in range(4010):
                base=i*100
                # Independently fixed offsets from the archived 20-column LC layout.
                value=struct.unpack_from('>i',raw,base+40)[0]
                a=struct.unpack_from('>d',raw,base+68)[0];ae=struct.unpack_from('>f',raw,base+76)[0]
                b=struct.unpack_from('>d',raw,base+80)[0];be=struct.unpack_from('>f',raw,base+88)[0]
                assert all(math.isfinite(x) for x in [a,ae,b,be]) and ae>0 and be>0
                numeric+=4;values.append(value)
            saved=next(r for r in expected['references'] if r['tic']==record['tic'])
            assert {str(k):v for k,v in sorted(Counter(values).items())}==saved['quality_histogram']
            for bit,count in saved['nonexclusive_bit_counts'].items():assert sum(bool(v&int(bit)) for v in values)==count
            assert saved['finite_positive_error_rows']==4010
            assert sum(v==0 for v in values)==saved['quality_zero_rows']==saved['valid_rows']
            q.append(values)
        counts=Counter(sum(q[j][i]==0 for j in range(6)) for i in range(4010))
        assert {str(k):counts[k] for k in range(7)}==expected['simultaneous_valid_reference_count_histogram']
        totals=Counter()
        for w in [w for w in old if w['sector']==sector]:
            rec=next(r for r in ledger if r['window_id']==w['window_id'])
            a,lo,hi=w['anchor'],w['start'],w['stop']
            side=list(range(lo-60,lo-5))+list(range(hi+5,hi+60));event=list(range(lo,hi))
            ok_side=all(q[j][a*401+t]==0 for j in range(6) for t in side)
            ok_event=all(q[j][a*401+t]==0 for j in range(6) for t in event)
            assert rec['all_six_finite_positive_errors']
            assert rec['all_six_quality_zero_sideband']==ok_side
            assert rec['all_six_quality_zero_event']==ok_event
            assert rec['all_six_valid_selected']==(ok_side and ok_event)
            assert rec['actual_reference_prediction_available']==model_by_id[w['window_id']]['valid']
            for j,r in enumerate(rec['per_reference']):
                assert r['bad_sideband_quality_rows']==sum(q[j][a*401+t]!=0 for t in side)
                assert r['bad_event_quality_rows']==sum(q[j][a*401+t]!=0 for t in event)
                assert r['bad_numeric_selected_rows']==0
            for k in expected['window_counts']:totals[k]+=int(rec[k])
            checked+=1
        assert dict(totals)==expected['window_counts']
    scope=read(OUT/'scope_accounting.json')
    native=rows(OUT/'native.jsonl.gz');pulses=rows(OUT/'pulses.jsonl.gz')
    assert len(native)==840 and len(pulses)==12600
    assert scope['evaluated_combined_model_rows']==sum(r['energies']['combined'] is not None for r in native)==0
    assert scope['evaluated_pulse_responses']==sum(p['metrics'] is not None for p in pulses)==0
    assert scope['reference_windows_available']==sum(r['valid'] for r in model)==0
    assert not scope['native_correction_measured'] and not scope['downstream_pulse_transfer_measured']
    result={'status':'PASS','raw_numeric_fields_checked':numeric,'quality_rows_checked':48120,
            'window_attributions_checked':checked,'available_reference_windows':0,'evaluated_combined_model_rows':0,
            'evaluated_pulse_responses':0,'scope_accounting_verified':True,
            'frozen_producer_stage_flag_is_overbroad_for_this_blocked_run':True}
    OUT.joinpath('quality_audit.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))


if __name__=='__main__':main()
