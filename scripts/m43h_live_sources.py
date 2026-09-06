#!/usr/bin/env python3
"""Frozen two-anchor source extraction; publish success or precise blocked stage."""
import argparse
import json
from pathlib import Path
import numpy as np
from m43g_reference import sorted_reference
from seti_repeater import source_m43h as src
from seti_repeater import transport_m43h as net

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_m43h_widened_source'


def run(work_root):
    cfg,contract,metadata,preflight=src.frozen_inputs(ROOT)
    integration=src.verify(json.loads((OUT/'hdf5_integration.json').read_text()),'result_sha256')
    if integration['result_sha256']!=cfg['hdf5_integration_result_sha256'] or integration['status']!='local-hdf5-codec-integration-qualified':
        raise ValueError('HDF5 integration receipt changed')
    for p,h in integration['implementation_sha256'].items():
        if src.file_hash(ROOT/p)!=h:raise ValueError('qualified implementation differs')
    records=[]
    for anchor in cfg['anchors']:
        label=anchor['scan'];window=anchor['window'];directory=work_root/'live'/label/window
        before=dict(net.COUNTERS)
        print('begin '+label+' '+window,flush=True)
        try:
            receipt,detail=src.extract_remote(ROOT,label,window,directory,work_root/'mirrors',spectral_access_authorized=True)
            src.rehydrate(directory,receipt['receipt_sha256'])
            for row in range(16):
                native=np.load(directory/f'row{row:02d}.native.npy',allow_pickle=False,mmap_mode='r')
                actual=np.load(directory/f'row{row:02d}.normalized.npy',allow_pickle=False,mmap_mode='r')
                expected=sorted_reference(native[::-1].reshape(1,-1))[0]
                np.testing.assert_array_equal(actual,expected)
            path=OUT/(label+'_'+window+'.telescope-source.json');src.atomic_json(path,receipt)
            src.atomic_json(OUT/(label+'_'+window+'.range-plan.json'),detail['range_plan'])
            record={'scan':label,'window':window,'status':'telescope-source-attested',
                'source_receipt_sha256':receipt['receipt_sha256'],'receipt_path':str(path.relative_to(ROOT)),
                'telescope_rows':16,'sorted_reference_rows_exact':16,'resumed_rows':detail['resumed_rows']}
        except Exception as error:
            # Preserve the error and any committed partial rows. Never count a
            # failed normalization or transport attempt as a complete source.
            record={'scan':label,'window':window,'status':'source-attempt-failed','error_type':type(error).__name__,
                    'reason':str(error),'committed_partial_row_receipts':len(list(directory.glob('row??.json'))) if directory.exists() else 0}
        record['transport_counters']={k:net.COUNTERS[k]-before[k] for k in before}
        records.append(record)
        progress=src.seal({'milestone':'M43H','contract_sha256':contract,'anchors':records,
                          'complete_anchor_inventory':len(records)==len(cfg['anchors'])},'result_sha256')
        src.atomic_json(OUT/'live_progress.json',progress)
        print(json.dumps(record),flush=True)
    success=sum(r['status']=='telescope-source-attested' for r in records)
    result=src.seal({'milestone':'M43H','status':'live-source-gate-passed' if success==len(cfg['anchors']) else 'live-source-gate-incomplete',
        'contract_sha256':contract,'hdf5_integration_result_sha256':integration['result_sha256'],
        'anchors':records,'attested_telescope_products':success,'attested_telescope_rows':16*success,
        'transport_counters':dict(net.COUNTERS),'score_calculation_performed':False,
        'recovery_measured':False,'threshold_calibrated':False},'result_sha256')
    src.atomic_json(OUT/'live_result.json',result)
    print(json.dumps({'status':result['status'],'result_sha256':result['result_sha256'],'attested_sources':success}),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work-root',required=True,type=Path);run(p.parse_args().work_root)
