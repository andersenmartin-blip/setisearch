#!/usr/bin/env python3
"""One prospective synthetic calibration/evaluation attempt; no restart replay."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import resource
import sys
import subprocess
import time
import traceback

import numpy as np

import radio_receiver_adapter_common as common
from seti_repeater import pipeline_receiver_radio as pipeline
from seti_repeater import receiver_panel_radio as panel
from seti_repeater import transfer_m43g as native

ROOT=common.ROOT
BASE=ROOT/'results_radio_hd189733_panel_2026-09-28'
CONFIG='config/radio_hd189733_panel_20260928.json'


def write(path,value,exclusive=True):
    with path.open('x' if exclusive else 'w') as f:
        json.dump(value,f,indent=2,sort_keys=True,allow_nan=False)
        f.write('\n');f.flush();os.fsync(f.fileno())


def archive_scores(out,name,store):
    keys=sorted(store.arrays)
    path=out/(name+'_scores.npz')
    with path.open('xb') as f:
        np.savez_compressed(f,**{str(i):store.arrays[k] for i,k in enumerate(keys)})
        f.flush();os.fsync(f.fileno())
    return {'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'keys':[list(k) for k in keys], 'vectors':[{'key':list(k),'id':store.expected_ids[k],
            'payload_sha256':native.array_hash(store.arrays[k])} for k in keys],
        'score_provenance':store.provenance,'all_score_values_retained':True,
        'raw_native_arrays_retained':False}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--freeze-commit',required=True)
    args=parser.parse_args();cfg=json.loads((ROOT/CONFIG).read_text())
    for p,h in cfg['pins'].items():
        raw=(ROOT/p).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=h or raw!=subprocess.check_output(['git','show',args.freeze_commit+':'+p],cwd=ROOT):
            raise ValueError('Published panel freeze mismatch: '+p)
    if (ROOT/CONFIG).read_bytes()!=subprocess.check_output(['git','show',args.freeze_commit+':'+CONFIG],cwd=ROOT):
        raise ValueError('Panel config differs from publication')
    if (platform.python_version()!=cfg['runtime']['python'] or np.__version__!=cfg['runtime']['numpy']
            or hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest()!=cfg['runtime']['python_executable_sha256']):
        raise ValueError('Pinned runtime changed')
    reservation=json.loads(common.read_inputs()[list(common.PINS)[3]])
    cases={role:[x for x in reservation['identities'] if x['role']==role] for role in ('calibration','evaluation')}
    for role in cases:
        if [x['identity'] for x in cases[role]]!=cfg[role+'_identities']:raise ValueError('Panel identity inventory changed')
    out=BASE/'attempt01';out.mkdir(exist_ok=False)
    started=time.monotonic()
    ledger={'schema':'radio-receiver-panel-consumption-v1','freeze_commit':args.freeze_commit,
        'status':'RUNNING_CALIBRATION','calibration_spent':[],'calibration_completed':[],
        'evaluation_spent':[],'evaluation_completed':[],'evaluation_runs':0,
        'development_cases_closed_previously':6,'remedies':0,'pilot_runs':0,
        'source_requests':0,'published_calibration_attempt_slots_charged':3,
        'published_evaluation_run_slots_charged':1,'published_evaluation_case_slots_reserved':24}
    write(out/'consumption.json',ledger)
    def budget():
        if time.monotonic()-started>cfg['limits']['active_seconds']:raise RuntimeError('Panel active-time cap')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>cfg['limits']['process_rss_bytes']:raise RuntimeError('Panel RSS cap')
        if sum(p.stat().st_size for p in out.iterdir() if p.is_file())>cfg['limits']['retained_bytes']:raise RuntimeError('Panel retained-evidence cap')
    calibration=[];cal_receipts=[];outcomes=[]
    try:
        ccal=common.context('calibration');cval=common.context('validation')
        proof_path=cfg['score_map_proof'];proof=(ROOT/proof_path).read_bytes()
        for case in cases['calibration']:
            budget();i=case['index'];print('begin calibration',i,flush=True)
            ledger['calibration_spent'].append(case['identity']);write(out/'consumption.json',ledger,False)
            sources,render=panel.render_case(ccal,case,budget=budget)
            run=pipeline.NativeRun(ccal,sources);store=run.build_store();run.validate_store(store)
            if run.modelled_bytes>cfg['limits']['modelled_array_bytes']:raise RuntimeError('Panel modelled array cap')
            archive=archive_scores(out,f'calibration{i:02d}',store)
            translated,transfer=panel.translate_calibration_scores(run,store,cval,proof,cfg['pins'][proof_path])
            acc,support=panel.accumulate(cval,translated,np.asarray(cfg['scramble_tables'][i],dtype='<i8'),budget=budget)
            cal=None if acc is None else panel.bind_calibration(cval,acc,support,transfer)
            evidence={'case':case,'render':render,'scores':archive,'translation':transfer,
                'support':support,'calibration':None if cal is None else cal.receipt,
                'calibration_receipt_sha256':None if cal is None else cal.receipt_sha256}
            write(out/f'calibration{i:02d}.json',evidence)
            calibration.append(cal);cal_receipts.append({'index':i,'identity':case['identity'],
                'status':support['status'],'finite_null_count':support['finite_null_count'],
                'null_count':support['null_count'],'observed_maximum':support['observed_maximum']})
            ledger['calibration_completed'].append(case['identity']);write(out/'consumption.json',ledger,False)
            print('complete calibration',i,support['status'],support['finite_null_count'],flush=True)
            del sources,run,store,translated,evidence;budget()
        if all(cal is not None for cal in calibration):
            # Fixed before exposure: identity index 0 supplies the primary
            # threshold; indices 1 and 2 are independent-realization diagnostics.
            # They never select, pool, increase or lower the primary threshold.
            primary=calibration[0]
            ledger['status']='RUNNING_EVALUATION';ledger['evaluation_runs']=1;write(out/'consumption.json',ledger,False)
            for case in cases['evaluation']:
                budget();i=case['index'];print('begin evaluation',i,case['recipe']['case_id'],flush=True)
                ledger['evaluation_spent'].append(case['identity']);write(out/'consumption.json',ledger,False)
                sources,render=panel.render_case(cval,case,budget=budget)
                run=pipeline.NativeRun(cval,sources);store=run.build_store();run.validate_store(store)
                archive=archive_scores(out,f'evaluation{i:02d}',store)
                # Persist complete input evidence before downstream capacity or integrity failures.
                write(out/f'evaluation{i:02d}_input.json',{'case':case,'render':render,'scores':archive})
                report=run.execute(store,primary)
                write(out/f'evaluation{i:02d}_detector.json',report)
                outcome=panel.classify(report,cval,case);write(out/f'evaluation{i:02d}_outcome.json',outcome)
                outcomes.append({k:v for k,v in outcome.items() if k!='association'})
                ledger['evaluation_completed'].append(case['identity']);write(out/'consumption.json',ledger,False)
                print('complete evaluation',i,'gate',outcome['gate_pass'],outcome['counts'],flush=True)
                del sources,run,store,report;budget()
            status='PANEL_PASS' if all(x['gate_pass'] for x in outcomes) else 'PANEL_FAILED_CLOSED'
        else:
            status='CALIBRATION_FAILED_EVALUATIONS_UNOPENED'
        result={'schema':'radio-receiver-panel-result-v1','status':status,'freeze_commit':args.freeze_commit,
            'calibrations':cal_receipts,'evaluation_outcomes':outcomes,
            'calibration_realizations_spent':len(ledger['calibration_spent']),
            'evaluation_cases_spent':len(ledger['evaluation_spent']),'evaluation_runs_executed':ledger['evaluation_runs'],
            'development_cases_spent_previously':6,'calibration_attempt_budget_closed':True,
            'evaluation_attempt_allocation_may_be_reused':False,'remedy_attempts':0,'pilot_runs':0,
            'new_source_requests':0,'telescope_values_opened':False,'external_messages_sent':0,
            'synthetic_only':True,'real_noise_exchangeability_qualified':False,
            'source_codec_handoff_qualified':False,'telescope_spectral_access_authorized':False,
            'active_seconds':time.monotonic()-started,
            'peak_process_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'retained_bytes_before_summary':sum(p.stat().st_size for p in out.iterdir() if p.is_file()),
            'runtime':cfg['runtime']}
        write(out/'result.json',result);ledger['status']=status;write(out/'consumption.json',ledger,False)
        print(json.dumps(result,indent=2),flush=True)
    except BaseException as error:
        ledger['status']='STOPPED_ERROR_NO_REPLAY';ledger['error']=repr(error)
        write(out/'consumption.json',ledger,False)
        write(out/'error.json',{'exception':repr(error),'traceback':traceback.format_exc(),
            'active_seconds':time.monotonic()-started,'ledger':ledger})
        raise


if __name__=='__main__':main()
