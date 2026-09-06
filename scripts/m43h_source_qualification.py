#!/usr/bin/env python3
"""Frozen source-chain fixture qualification and explicit live readiness receipt."""
import argparse
import json
from pathlib import Path
import numpy as np
from m43h_fixture import FixtureHandle,fixture_values
from m43g_reference import sorted_reference
from seti_repeater import source_m43h as src

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_m43h_widened_source'


def run(work_root):
    cfg,contract,metadata,preflight=src.frozen_inputs(ROOT)
    records=[]
    for anchor in cfg['anchors']:
        label=anchor['scan'];window=anchor['window']
        definition=next(s for s in metadata['scans'] if s['label']==label)
        interval=next(w['proposed_interval'] for w in preflight['windows'] if w['window_id']==window)
        scope=src.make_scope(definition,window,interval,contract,'local-fixture')
        directory=work_root/'fixtures'/label/window
        # Work root must be new: retain the intentionally interrupted first run.
        if directory.exists():raise RuntimeError('fresh fixture directory required; choose a new work root')
        interrupted=FixtureHandle(definition,fail_after=cfg['interrupt_after_rows'])
        try:src._extract_rows(interrupted,scope,directory)
        except InterruptedError:pass
        else:raise RuntimeError('intentional interruption was not reached')
        if (directory/'source.json').exists():raise RuntimeError('partial product was marked complete')
        resumed_handle=FixtureHandle(definition)
        rows,resumed=src._extract_rows(resumed_handle,scope,directory)
        if resumed!=cfg['interrupt_after_rows']:raise RuntimeError('resume count differs')
        if [q[0] for q in resumed_handle.dataset.requests]!=list(range(resumed,16)):
            raise RuntimeError('resume reread or skipped wrong rows')
        receipt=src._complete(directory,scope,rows,{'kind':'explicit-local-dataset-facade','network_requests':0,'hdf5_decode_exercised':False})
        src.rehydrate(directory,receipt['receipt_sha256'],required_kind='local-fixture')
        for row in range(16):
            raw=fixture_values(row,*interval)
            expected=sorted_reference(raw[::-1].reshape(1,-1))[0]
            actual=np.load(directory/f'row{row:02d}.normalized.npy',allow_pickle=False)
            if not np.array_equal(actual,expected):raise RuntimeError('full-size sort oracle mismatch')
        completed=FixtureHandle(definition)
        again,reused=src._extract_rows(completed,scope,directory)
        if reused!=16 or completed.dataset.requests:raise RuntimeError('completed restart reread fixture')
        if src._complete(directory,scope,again,receipt['transport'])!=receipt:raise RuntimeError('restart changed receipt')
        OUT.mkdir(exist_ok=True)
        name=label+'_'+window+'.fixture-source.json'
        src.atomic_json(OUT/name,receipt)
        records.append({'scan':label,'window':window,'kind':'local-fixture','source_receipt_sha256':receipt['receipt_sha256'],
            'receipt_path':str((OUT/name).relative_to(ROOT)),'native_channels':interval[1]-interval[0],
            'rows':16,'interrupted_after_rows':resumed,'completed_restart_reused_rows':reused,
            'sorted_reference_rows_exact':16,'modelled_buffer_bound_bytes':src.resource_bound(interval[1]-interval[0]),
            'hdf5_decode_exercised':False})
        print(label+' '+window+' full-size fixture and restart verified',flush=True)
    dependencies=src.dependency_status()
    if cfg['hdf5_integration_qualified'] is not False:
        raise RuntimeError('this fixture-only protocol requires the live integration gate to stay closed')
    attempts=[]
    # This entry runs every frozen guard before any I/O. The current published
    # integration gate is false because the HDF5 backend could not be qualified.
    for anchor in cfg['anchors']:
        try:
            src.extract_remote(ROOT,anchor['scan'],anchor['window'],work_root/'live'/anchor['scan']/anchor['window'],
                               work_root/'mirrors',spectral_access_authorized=True)
        except (ModuleNotFoundError,RuntimeError) as error:
            attempts.append({'scan':anchor['scan'],'window':anchor['window'],'status':'blocked-before-remote-contact',
                             'error_type':type(error).__name__,'reason':str(error)})
        else:raise RuntimeError('unexpected live gate passage')
    result=src.seal({'milestone':'M43H','status':'source-chain-fixtures-qualified-live-hdf5-blocked',
        'contract_sha256':contract,'m43g_result_sha256':cfg['m43g_result_sha256'],
        'm43f_result_sha256':cfg['m43f_result_sha256'],'fixtures':records,'dependencies':dependencies,
        'live_attempts':attempts,'telescope_requests':0,'telescope_spectral_rows_read':0,
        'attested_telescope_products':0,'hdf5_integration_qualified':False,
        'score_calculation_performed':False,'source_restart_fixture_gate_passed':True},'result_sha256')
    src.atomic_json(OUT/'qualification.json',result)
    print(json.dumps({'status':result['status'],'result_sha256':result['result_sha256'],'dependencies':dependencies},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--work-root',required=True,type=Path);run(p.parse_args().work_root)
