#!/usr/bin/env python3
"""One fixed cross-window address comparison; metadata/factors only."""
import hashlib
import json
from pathlib import Path
import resource
import time

import numpy as np
import radio_receiver_adapter_common as common
from seti_repeater import search_v0p6 as core
from seti_repeater import transfer_m43g as native


def main():
    start=time.monotonic()
    out=common.ROOT/'results_radio_hd189733_score_map_2026-09-28';out.mkdir(exist_ok=False)
    tables=[];records=[]
    for role in ('calibration','validation','pilot'):
        c=common.context(role)
        f=c.factor_contract.factors.factors[:,:,1]
        frequency=f[:,:,None]*c.grid.support_hz[None,None,:]
        table=core.nearest_native_indices(c.geometry,frequency)
        assert table.shape==(81,96,99)
        assert table.min()>=64 and table.max()<65536-64
        tables.append(table)
        records.append({'role':role,'context_sha256':c.identity,
            'bank_sha256':c.factor_contract.factors.identity,
            'relative_index_sha256':native.array_hash(np.ascontiguousarray(table)),
            'shape':list(table.shape),'geometry':c.geometry.__dict__,
            'widths':list(core.M37_SPECTRAL_WIDTHS),'native_normalization_blocks':16,
            'native_normalization_origin':0,'block_length':4096})
    comparison=[]
    for i in (1,2):
        mismatch=np.argwhere(tables[0]!=tables[i])
        entry={'reference':'calibration','other':records[i]['role'],
            'addresses_compared':int(tables[0].size),'different_addresses':len(mismatch)}
        if len(mismatch):
            at=tuple(mismatch.T);p=out/('all_'+records[i]['role']+'_mismatches.npz')
            np.savez_compressed(p,template_row_support=mismatch,
                calibration_indices=tables[0][at],other_indices=tables[i][at])
            entry.update({'all_mismatch_file':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
                'maximum_index_difference':int(np.max(np.abs(tables[0][at]-tables[i][at])))})
        comparison.append(entry)
    for r in records[1:]:
        assert r['geometry']['channel_count']==records[0]['geometry']['channel_count']==65536
        assert r['geometry']['channel_width_hz']==records[0]['geometry']['channel_width_hz']
        assert r['widths']==records[0]['widths']
    same=all(x['different_addresses']==0 for x in comparison)
    result={'schema':'radio-hd189733-cross-window-score-map-v1',
        'status':'SCORE_OPERATOR_IDENTICAL_ON_TRANSLATED_ARRAYS' if same else 'SCORE_OPERATOR_EQUIVALENCE_FAILED',
        'source_pins':common.PINS,'tables':records,'comparisons':comparison,
        'index_comparisons':sum(x['addresses_compared'] for x in comparison),
        'score_operator_equivalence_proved':same,'noise_distribution_transfer_qualified':False,
        'absolute_frequency_veto_transfer_qualified':False,'threshold_rebound':False,
        'source_requests':0,'development_realizations':0,'calibration_realizations':0,
        'evaluation_cases':0,'spectral_values_opened':False,'spectral_access_authorized':False,
        'elapsed_seconds':time.monotonic()-start,
        'peak_process_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        'input_code_sha256':{p:hashlib.sha256((common.ROOT/p).read_bytes()).hexdigest() for p in [
          'scripts/radio_hd189733_score_map.py','scripts/radio_receiver_adapter_common.py',
          'src/seti_repeater/receiver_bank_radio.py','src/seti_repeater/receiver_contract_radio.py',
          'src/seti_repeater/pipeline_receiver_radio.py','src/seti_repeater/search_v0p6.py',
          'RADIO_HD189733_SCORE_MAP_2026-09-28_SCOPE.md']}}
    with (out/'result.json').open('x') as f:json.dump(result,f,indent=2,sort_keys=True);f.write('\n')
    assert result['elapsed_seconds']<=120
    assert result['peak_process_rss_bytes']<=256*1024**2
    assert sum(p.stat().st_size for p in out.iterdir())<=16*1024**2
    print(json.dumps({k:result[k] for k in ['status','comparisons','index_comparisons','elapsed_seconds','peak_process_rss_bytes']},indent=2))


if __name__=='__main__':main()
