#!/usr/bin/env python3
"""Consume the six published development identities once; never calibrate/evaluate."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import time
import traceback

import numpy as np

import radio_receiver_adapter_common as common
from seti_repeater import receiver_bank_radio as received
from seti_repeater import receiver_development_radio as renderer
from seti_repeater import pipeline_receiver_radio as pipeline
from seti_repeater import transfer_m43g as native
from seti_repeater import search_v0p6 as core

ROOT=common.ROOT
BASE=ROOT/'results_radio_hd189733_adapter_2026-09-28'
CONFIG='config/radio_hd189733_adapter_development_20260928.json'


def write(path,value,exclusive=True):
    with path.open('x' if exclusive else 'w') as f:
        json.dump(value,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n');f.flush();os.fsync(f.fileno())


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--freeze-commit',required=True);args=parser.parse_args()
    cfg=json.loads((ROOT/CONFIG).read_text())
    for p,h in cfg['code_and_protocol_sha256'].items():
        raw=(ROOT/p).read_bytes()
        published=subprocess.check_output(['git','show',args.freeze_commit+':'+p],cwd=ROOT)
        if hashlib.sha256(raw).hexdigest()!=h or raw!=published:raise ValueError('Published code freeze mismatch: '+p)
    if (ROOT/CONFIG).read_bytes()!=subprocess.check_output(['git','show',args.freeze_commit+':'+CONFIG],cwd=ROOT):
        raise ValueError('Development configuration differs from published freeze')
    raw=common.read_inputs();reservation=json.loads(raw[list(common.PINS)[3]])
    cases=[x for x in reservation['identities'] if x['role']=='development']
    if [x['identity'] for x in cases]!=cfg['development_identities']:raise ValueError('Reserved identities changed')
    out=BASE/'development_attempt01';out.mkdir(exist_ok=False)
    started=time.monotonic()
    ledger={'schema':'radio-hd189733-development-consumption-v1','freeze_commit':args.freeze_commit,
        'status':'RUNNING','reserved_case_ids':cfg['development_identities'],'spent_case_ids':[],
        'completed_case_ids':[],'calibration_realizations':0,'evaluation_cases':0,'evaluation_runs':0,
        'pilot_runs':0,'source_requests':0,'exhausted_acquisition_ledger_used':False}
    ledger_path=out/'consumption.json';write(ledger_path,ledger)
    try:
        c=common.context('validation')
        clock=received.clock(json.loads(raw[list(common.PINS)[0]]))
        summary=[];all_vectors=[]
        def budget():
            if time.monotonic()-started>cfg['limits']['active_seconds']:raise RuntimeError('Development time cap exceeded')
            if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>cfg['limits']['process_rss_bytes']:
                raise RuntimeError('Development RSS cap exceeded')
        for case in cases:
            budget();ledger['spent_case_ids'].append(case['identity']);write(ledger_path,ledger,False)
            print('reserved development',case['index'],case['identity'][:12],flush=True)
            rate=case['recipe']['rate_label_hz_s'];sources={};row_receipts=[];mass_error=0.
            q=c.grid.center_mhz*1e6;center=json.loads(c.factor_contract.factors.provenance_json)['center_hz']
            for scan_index,scan in enumerate(c.scans):
                rng=np.random.Generator(np.random.PCG64(np.random.SeedSequence([case['seed'],scan_index])))
                scan_receipts=[]
                def reader(row):
                    nonlocal mass_error
                    base=rng.normal(100.,1.,65536).astype('<f4')
                    value=base.astype('<f8')
                    if scan['kind']=='on':
                        times=clock[scan_index*16+row];t=float(times[1]);dt=float(times[2]-times[0])
                        frequency=q*(1+rate*t/center)
                        position=(frequency-c.geometry.raw_zero_hz)/c.geometry.channel_width_hz
                        sweep=q*rate/center*dt/c.geometry.channel_width_hz
                        indices,mass=renderer.pixel_masses(position,sweep,1.,65536)
                        mass_error=max(mass_error,abs(float(mass.sum())-1))
                        value[indices]+=500.*mass
                    result=value.astype('<f4')
                    scan_receipts.append({'row':row,'background_sha256':native.array_hash(base),
                                          'raw_with_signal_sha256':native.array_hash(result)})
                    return result
                source=native.normalize_synthetic_rows(reader,c.geometry,16,input_orientation='ascending',
                    scope={'kind':'synthetic','input_domain':'reserved-receiver-development',
                        'scan':scan['label'],'context_sha256':c.identity,'case_identity':case['identity'],
                        'receiver_factor_bank_sha256':c.factor_contract.factors.identity,
                        'telescope_provenance':False})
                for receipt,row in zip(scan_receipts,source.values):receipt['normalized_sha256']=native.array_hash(row)
                sources[scan['label']]=source
                row_receipts.append({'scan':scan['label'],'source_identity':source.identity,'rows':scan_receipts})
                budget()
            run=pipeline.NativeRun(c,sources)
            if run.modelled_bytes>cfg['limits']['modelled_array_bytes']:raise RuntimeError('Modelled array cap exceeded')
            store=run.build_store();run.validate_store(store)
            compared=0;mismatches=0;max_diff=0.;scores=[]
            for scan in c.scans:
                f=c.factor_contract.for_scan(scan['label'])
                for width in core.M37_SPECTRAL_WIDTHS:
                    oracle=renderer.score_oracle(sources[scan['label']],f,c.grid.support_hz,width)
                    actual=np.stack([store.arrays[scan['kind'],t,width][scan['epoch']-1] for t in range(81)])
                    count=int(np.count_nonzero(oracle.view('<u4')!=actual.view('<u4')))
                    mismatches+=count;compared+=actual.size
                    max_diff=max(max_diff,float(np.max(np.abs(actual.astype('<f8')-oracle))))
                    scores.append({'scan':scan['label'],'width':width,'cells':int(actual.size),
                        'adapter_sha256':native.array_hash(actual),'oracle_sha256':native.array_hash(oracle),
                        'mismatches':count,'maximum_score':float(actual.max()),'minimum_score':float(actual.min())})
                    budget()
            vectors=[{'key':list(k),'legacy_vector_identity':store.expected_ids[k],
                      'payload_sha256':native.array_hash(v)} for k,v in sorted(store.arrays.items())]
            record={'schema':'radio-receiver-development-case-result-v1','case_identity':case['identity'],
                'case_index':case['index'],'seed':case['seed'],'rate_label_hz_s':rate,'context_sha256':c.identity,
                'source_ids':run.source_ids,'row_receipts':row_receipts,'score_provenance':store.provenance,
                'score_vector_hashes':vectors,'independent_score_checks':scores,
                'score_cells_compared':compared,'bit_mismatches':mismatches,'max_absolute_difference':max_diff,
                'max_injection_mass_error':mass_error,'modelled_array_bytes':run.modelled_bytes,
                'detector_or_calibration_executed':False,'scientific_recovery_measured':False,
                'telescope_values_opened':False,'raw_and_score_values_retained':False,
                'reconstruction':'Pinned generator/runtime/seed/code; per-row and per-vector hashes retained'}
            write(out/f'case{case["index"]:02d}.json',record)
            summary.append({k:record[k] for k in ['case_identity','case_index','rate_label_hz_s','score_cells_compared','bit_mismatches','max_absolute_difference','max_injection_mass_error']})
            if mismatches:raise RuntimeError('Independent native score mismatch; spent identity cannot be replayed')
            ledger['completed_case_ids'].append(case['identity']);write(ledger_path,ledger,False)
            del source,sources,run,store,oracle,actual,vectors
            print('completed development',case['index'],'cells',compared,'mismatches',mismatches,flush=True)
        size=sum(p.stat().st_size for p in out.iterdir() if p.is_file())
        if size>cfg['limits']['retained_bytes']:raise RuntimeError('Retained evidence cap exceeded')
        result={'schema':'radio-receiver-adapter-development-result-v1','status':'SIX_DEVELOPMENT_CASES_NUMERICALLY_EXACT',
            'freeze_commit':args.freeze_commit,'cases':summary,'development_cases_consumed':6,
            'score_cells_compared':sum(x['score_cells_compared'] for x in summary),
            'bit_mismatches':sum(x['bit_mismatches'] for x in summary),'new_tests_passed':21,
            'calibration_realizations':0,'evaluation_cases':0,'evaluation_runs':0,'pilot_runs':0,
            'source_requests':0,'telescope_values_opened':False,'external_messages_sent':0,
            'mask_retention_veto_rank_stages_executed':False,'signal_recovery_qualified':False,
            'receiver_score_adapter_qualified':True,'source_codec_handoff_qualified':False,
            'cross_window_numeric_transfer_qualified':False,
            'runtime':{'python':platform.python_version(),'numpy':np.__version__,'generator':'PCG64'},
            'active_seconds':time.monotonic()-started,'peak_process_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'retained_bytes_before_summary':size,'development_budget_closed':True,'remedy_attempts':0}
        write(out/'result.json',result)
        ledger['status']='CLOSED_SIX_DEVELOPMENT_IDENTITIES_SPENT';write(ledger_path,ledger,False)
        print(json.dumps(result,indent=2),flush=True)
    except BaseException as error:
        ledger['status']='STOPPED_ERROR_NO_REPLAY';ledger['error']=repr(error)
        write(ledger_path,ledger,False)
        write(out/'error.json',{'exception':repr(error),'traceback':traceback.format_exc(),
            'active_seconds':time.monotonic()-started,'spent_case_ids':ledger['spent_case_ids']})
        raise


if __name__=='__main__':main()
