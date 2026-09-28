#!/usr/bin/env python3
"""Reconcile retained development evidence and published scope without rerunning data."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results_radio_hd189733_adapter_2026-09-28'


def main():
    read=lambda p:json.loads(p.read_text())
    attempt=BASE/'development_attempt01'
    result=read(attempt/'result.json');ledger=read(attempt/'consumption.json')
    reservation=read(BASE/'published_development_reservation.json')
    expected=reservation['development_identities']
    assert ledger['completed_case_ids']==ledger['spent_case_ids']==expected
    assert ledger['status']=='CLOSED_SIX_DEVELOPMENT_IDENTITIES_SPENT'
    cfg=read(ROOT/'config/radio_hd189733_adapter_development_20260928.json')
    assert hashlib.sha256((ROOT/'config/radio_hd189733_adapter_development_20260928.json').read_bytes()).hexdigest()==reservation['configuration_sha256']
    for p,h in cfg['code_and_protocol_sha256'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
        assert (ROOT/p).read_bytes()==subprocess.check_output(['git','show',result['freeze_commit']+':'+p],cwd=ROOT)
    cells=rows=vectors=checks=0
    for i,identity in enumerate(expected):
        c=read(attempt/f'case{i:02d}.json');assert c['case_identity']==identity
        assert c['bit_mismatches']==0 and c['max_absolute_difference']==0
        assert len(c['source_ids'])==6 and len(c['score_provenance']['native_caches'])==48
        assert len(c['score_vector_hashes'])==1296
        assert len(c['independent_score_checks'])==48
        for x in c['independent_score_checks']:
            assert x['mismatches']==0 and x['adapter_sha256']==x['oracle_sha256']
            assert x['cells']==81*99
            cells+=x['cells'];checks+=1
        rows+=sum(len(s['rows']) for s in c['row_receipts']);vectors+=len(c['score_vector_hashes'])
    assert (cells,rows,vectors,checks)==(2309472,576,7776,288)
    assert result['score_cells_compared']==cells
    map_result=read(ROOT/'results_radio_hd189733_score_map_2026-09-28/result.json')
    assert map_result['index_comparisons']==1539648
    assert len({x['relative_index_sha256'] for x in map_result['tables']})==1
    pins=read(ROOT/'results_radio_hd189733_receiver_2026-09-28/invariants.json')['old_pins_verified']
    for p,h in pins.items():
        b=subprocess.check_output(['git','show','HEAD:'+p],cwd=ROOT)
        assert hashlib.sha256(b).hexdigest()==h
        if (ROOT/p).exists():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    final={'schema':'radio-hd189733-adapter-postflight-v1','status':'RECONCILED',
        'freeze_commit':result['freeze_commit'],'closed_development_identities':6,
        'native_score_cells':cells,'row_receipts':rows,'score_vector_hashes':vectors,
        'independent_score_checks':checks,'cross_window_index_comparisons':1539648,
        'old_input_pins_unchanged':pins,'new_telescope_requests':0,'new_calibrations':0,
        'new_evaluation_cases':0,'recovery_qualification':False,
        'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    with (BASE/'postflight.json').open('x') as f:json.dump(final,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps({k:v for k,v in final.items() if k!='old_input_pins_unchanged'},indent=2))


if __name__=='__main__':main()
