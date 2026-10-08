#!/usr/bin/env python3
"""One previously ungenerated B case; operational correction only, no import RNG."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import signal
import sys
import time
import traceback

STARTED = time.monotonic()
BASE = Path(__file__).resolve().parent.parent
CLAIMS = BASE / 'pilot_protocol_20261008/validation_b_claims'
FROZEN = {
    'detector': '1df20d639ededb342ca6d3669ed1c5c75a0229ea23512feea1e38dfe02937b45',
    'dev_helpers': 'd64aa962c585f536ea969fb09bcc6e16df4289f6fd4e69f396684b94bd995f49',
    'generator': '3864bd49766f71771ac48cb517eaa516fab0768d3c39f2ed8f07b8f1eed21693',
    'contract': '44854605dbbe40a2c8aa7805433437e7ef03de31db3c76326d235baa88d7406c',
    'development_cases': '1f72ab1086a2220da1617aca6dadedc66a6d121359129c90db54ede294fd41df',
    'validation_a_cases': '1edb1ab43c0ff025662de6ce7f6bd5a00cb3c902e275fa5e38d56794c1b86ad1',
    'validation_b_cases': '93b425038ef9ec178610a1f17856258b0bf726b2e326430db85d4240e48ce46c',
    'summarizer': '6f9153d8c598eb6bb897d0a00dc632906a00ed203c876902fca955b1b7e4b361',
    'runtime_cases': '2bef79ec3c17568243672c1ec65c9ca2baeb8066dcc4ab6842039f6d4f2a94d1',
    'a_summary': '6e270a49b9094eac26e4d02e152990869374c7f056dc4e0b63d61675d443f67c',
    'a_outcomes': '234c10b30162165e1d34c6e95a889c36e3bbb7796ac14b562f40754f14faed0c',
}

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def durable_json(path, value, exclusive=False):
    path = Path(path)
    tmp = path.with_name(path.name + '.tmp')
    with (path if exclusive else tmp).open('x' if exclusive else 'w') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
    if not exclusive:
        tmp.replace(path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, Path(path))
    if spec is None or spec.loader is None: raise ValueError('Unimportable frozen module')
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

def check_bank(cases, panel, count):
    if len(cases) != count or any(c['panel'] != panel for c in cases):
        raise ValueError('Complete fixed panel required: ' + panel)
    ids, seeds = {c['case_id'] for c in cases}, {c['seed_sha256'] for c in cases}
    if len(ids) != count or len(seeds) != count: raise ValueError('Duplicate panel identity/seed')
    for c in cases:
        if f'_{panel}:' not in c['case_id'] or hashlib.sha256(c['case_id'].encode('ascii')).hexdigest() != c['seed_sha256']:
            raise ValueError('Identity/seed binding differs')
    return ids, seeds

def admission(admission_path):
    """Read/pin prerequisites only; calling this creates no case arrays."""
    admission_path = Path(admission_path)
    a = json.loads(admission_path.read_text())
    if a.get('status') not in ('ADMITTED_VAL_B_ROLLING', 'ADMITTED_VAL_B_SINGLE_CASE'):
        raise ValueError('Root B-only operational admission required')
    if a.get('correction_number') != 1 or a.get('scientific_change') is not False:
        raise ValueError('Only one operational correction; science remains fixed')
    if not re.fullmatch('[0-9a-f]{40}', a.get('public_commit_sha', '')):
        raise ValueError('Public source freeze required')
    paths = {k: (Path(v) if Path(v).is_absolute() else admission_path.parent / v).resolve()
             for k, v in a['paths'].items()}
    hashes = {k: digest(p) for k, p in paths.items()}
    for key, value in hashes.items():
        if a['sha256'].get(key) != value or (key in FROZEN and FROZEN[key] != value):
            raise ValueError('Frozen prerequisite hash differs: ' + key)
    if a['sha256'].get('runner') != digest(Path(__file__)):
        raise ValueError('B worker source is not bound')
    expected_science_paths = {'detector': BASE/'pilot_engine_20261008/detector.py',
                              'dev_helpers': BASE/'pilot_engine_20261008/run_dev.py',
                              'generator': BASE/'pilot_controls_20261008/generator.py',
                              'contract': BASE/'pilot_controls_20261008/control_contract.json',
                              'summarizer': BASE/'pilot_controls_20261008/summarize.py'}
    if any(paths[k] != v for k, v in expected_science_paths.items()):
        raise ValueError('Use original scientific modules at their exact absolute paths')
    banks = {key: json.loads(paths[key].read_text()) for key in
             ('development_cases', 'validation_a_cases', 'validation_b_cases', 'runtime_cases')}
    bank_sets = [check_bank(banks[k], panel, count) for k, panel, count in
                 (('development_cases','DEV',24),('validation_a_cases','VAL_A',142),
                  ('validation_b_cases','VAL_B',142),('runtime_cases','DEV_RUNTIME',2))]
    for i in range(len(bank_sets)):
        for j in range(i+1,len(bank_sets)):
            if bank_sets[i][0] & bank_sets[j][0] or bank_sets[i][1] & bank_sets[j][1]:
                raise ValueError('Fresh banks overlap in identities or seeds')
    summarizer = load(paths['summarizer'], 'frozen_runtime_b_summarizer')
    old_outcomes = json.loads(paths['a_outcomes'].read_text())
    old_summary = json.loads(paths['a_summary'].read_text())
    if summarizer.summarize(banks['validation_a_cases'],old_outcomes,'VAL_A') != old_summary:
        raise ValueError('Closed A evidence disagrees')
    if old_summary['scientific_gate'] != 'FAIL_CLOSED' or old_summary['case_count_observed'] != 142:
        raise ValueError('All A identities stay closed as failed, never retried')
    expected_failures = {banks['validation_a_cases'][128]['case_id'],banks['validation_a_cases'][129]['case_id']}
    if set(old_summary['failed_case_ids']) != expected_failures:
        raise ValueError('The original A timeout outcome changed')
    proof = json.loads(paths['runtime_proof'].read_text())
    runtime_ids = bank_sets[3][0]
    if (proof.get('status') != 'PASS_OPERATIONAL_DEVELOPMENT_ONLY' or proof.get('panel') != 'DEV_RUNTIME'
        or proof.get('case_count_expected') != 2 or proof.get('case_count_observed') != 2
        or proof.get('complete') is not True or proof.get('scientific_files_unchanged') is not True
        or set(proof.get('case_ids',[])) != runtime_ids or proof.get('case_bank_sha256') != FROZEN['runtime_cases']
        or proof.get('failed_validation_a_summary_sha256') != FROZEN['a_summary']
        or proof.get('failed_validation_a_outcomes_sha256') != FROZEN['a_outcomes']):
        raise ValueError('Complete fresh two-case runtime proof must PASS before B generation')
    for key in ('detector','dev_helpers','generator','contract','summarizer'):
        if proof['scientific_sha256'].get(key) != FROZEN[key]: raise ValueError('Runtime proof changed science')
    records = proof.get('case_results',[])
    if len(records) != 2 or {r['case_id'] for r in records} != runtime_ids:
        raise ValueError('Exact two runtime commits required')
    for record in records:
        if (record.get('status') != 'COMPLETED_CASE_ONLY' or record.get('panel') != 'DEV_RUNTIME'
            or record.get('caps_passed') is not True or record.get('no_retry_or_redraw') is not True):
            raise ValueError('Runtime aggregate record lacks a successful once-only commit')
        output = Path(record['output_directory']).resolve()
        runtime_index = next(i for i, c in enumerate(banks['runtime_cases']) if c['case_id'] == record['case_id'])
        if output != BASE/'results/radio_pilot_dev_runtime_20261008'/f'case_{runtime_index:03d}':
            raise ValueError('Runtime proof must retain its canonical output directory')
        marker = json.loads((output/'COMMITTED.json').read_text())
        if (marker.get('status') != 'COMPLETED_CASE_ONLY' or marker.get('panel') != 'DEV_RUNTIME'
            or marker.get('case_id') != record['case_id'] or marker.get('caps_passed') is not True
            or marker.get('no_retry_or_redraw') is not True
            or marker.get('artifact_manifest_SHA256') != digest(output/'artifact_manifest.json')
            or marker.get('artifact_manifest_SHA256') != record['artifact_manifest_SHA256']):
            raise ValueError('Runtime result is not durably committed')
        manifest = json.loads((output/'artifact_manifest.json').read_text())
        for name, body in manifest.items():
            if digest(output/name) != body['SHA256']: raise ValueError('Runtime committed artifact changed')
        required = [f'scan_{i:02d}_full_map.npz' for i in range(6)] + ['localized_recovery.json','outcome.json','resource_receipt.json']
        if any(name not in manifest for name in required): raise ValueError('Incomplete runtime maps/recovery/resources')
    ledger = json.loads(paths['correction_ledger'].read_text())
    if ledger.get('correction_number') != 1 or ledger.get('scientific_files_unchanged') is not True:
        raise ValueError('An explicit unchanged-science correction ledger is required')
    if float(a['budget']['global_cpu_ceiling_seconds']) != 43200:
        raise ValueError('Global scientific budget remains 43200 CPU seconds')
    return a, paths, hashes, banks, summarizer

def main():
    def watchdog(_sig,_frame): raise TimeoutError('Whole-job runtime/CPU watchdog; no redraw')
    for variable in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        os.environ[variable]='1'
    resource.setrlimit(resource.RLIMIT_AS,(4*1024**3,4*1024**3))
    resource.setrlimit(resource.RLIMIT_CPU,(1800,1800))
    signal.signal(signal.SIGALRM,watchdog); signal.signal(signal.SIGPROF,watchdog)
    signal.setitimer(signal.ITIMER_REAL,max(.01,1790-(time.monotonic()-STARTED)))
    r0=resource.getrusage(resource.RUSAGE_SELF)
    signal.setitimer(signal.ITIMER_PROF,max(.01,1785-(r0.ru_utime+r0.ru_stime)))
    parser = argparse.ArgumentParser()
    parser.add_argument('--admission',type=Path,required=True)
    parser.add_argument('--case',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    a, paths, hashes, banks, summarizer = admission(args.admission)
    if a['status'] != 'ADMITTED_VAL_B_SINGLE_CASE' or a['allowed_case_ids'] != [args.case]:
        raise ValueError('One exclusive B case admission required')
    selected = [c for c in banks['validation_b_cases'] if c['case_id'] == args.case]
    if len(selected) != 1: raise ValueError('Unknown B identity')
    case = selected[0]
    case_index = banks['validation_b_cases'].index(case)
    if (Path(a['claim_directory']).resolve() != CLAIMS or args.output.exists()
        or args.output.resolve() != BASE/'results/radio_pilot_val_b_20261008'/f'case_{case_index:03d}'):
        raise ValueError('Canonical fresh B claim/output required')
    budget = a['budget']
    if (float(budget['exclusive_cpu_allocation_seconds']) != 1800 or
        float(budget['max_wall_seconds_per_job']) != 1800 or int(budget['max_rss_bytes']) != 4*1024**3):
        raise ValueError('Whole-child fixed corrected resource caps required')
    reservation = json.loads(Path(a['reservation_path']).read_text())
    if (reservation['case_id'] != args.case or reservation['status'] != 'RESERVED_BEFORE_CHILD_SUBMIT'
        or reservation['cpu_reserved_seconds'] != 1800 or Path(reservation['output_directory']).resolve() != args.output.resolve()):
        raise ValueError('Exclusive rolling reservation must precede the child')
    if Path(a['closure_path']).exists():
        raise ValueError('Closed reservation cannot rearm this identity')
    if (Path(a['reservation_path']).resolve() != BASE/'results/radio_pilot_val_b_20261008'/f'reservation_{case_index:03d}.json'
        or Path(a['closure_path']).resolve() != BASE/'results/radio_pilot_val_b_20261008'/f'closure_{case_index:03d}.json'):
        raise ValueError('Canonical exclusive reservation and closure paths required')
    CLAIMS.mkdir(parents=True,exist_ok=True)
    claim_path = CLAIMS/(hashlib.sha256(args.case.encode('ascii')).hexdigest()+'.json')
    claim = {'case_id':args.case,'panel':'VAL_B','status':'CLAIMED_BEFORE_ARRAY_GENERATION',
             'admission_SHA256':digest(args.admission),'exclusive_cpu_allocation_seconds':1800,
             'output_directory':str(args.output.resolve()),'no_retry_or_redraw':True}
    durable_json(claim_path,claim,exclusive=True)
    args.output.mkdir(parents=True,exist_ok=False)
    outcome = {'case_id':args.case,'panel':'VAL_B','family':case['family'],'data_integrity_ok':False,
               'all_active_on_recovered':False,'any_localized_on_recovered':False,
               'pre_OFF_all_active_recovery':False,'pre_OFF_any_active_recovery':False,
               'survivor_count':0,'failure':None}
    failed = True
    try:
        detector = load(paths['detector'],'detector')
        helpers = load(paths['dev_helpers'],'frozen_runtime_b_helpers')
        generator = load(paths['generator'],'frozen_runtime_b_generator')
        import numpy as np
        import scipy
        if np.__version__!='2.3.5' or scipy.__version__!='1.17.0' or sys.platform!='linux':
            raise ValueError('Original admitted scientific package environment required')
        durable_json(args.output/'admission.json',{'admission':a,'observed_SHA256':hashes,'selected_case_id':args.case})
        durable_json(args.output/'case_definition.json',case)
        arrays,truth = generator.generate_case(case,json.loads(paths['contract'].read_text()))
        durable_json(args.output/'truth.json',truth)
        durable_json(args.output/'synthetic_array_hashes.json',[
            {'scan_id':h['scan_id'],'shape':list(v.shape),'dtype':str(v.dtype),
             'C_order_bytes_SHA256':hashlib.sha256(v.tobytes(order='C')).hexdigest()}
            for v,h in zip(arrays,json.loads(paths['contract'].read_text())['geometry']['scan_metadata'])])
        scans,frequencies = detector.control_inputs(arrays,json.loads(paths['contract'].read_text()))
        result = detector.search_cadence(scans,frequencies,detector.Config())
        helpers.save_result(args.output,result)
        if truth['active_ON_scan_ids']:
            recovery = detector.recovery_matches(result,truth)
            durable_json(args.output/'localized_recovery.json',recovery)
            outcome.update(all_active_on_recovered=recovery['final_all_active_recovery'],
                any_localized_on_recovered=recovery['final_any_active_recovery'],
                pre_OFF_all_active_recovery=recovery['pre_OFF_all_active_recovery'],
                pre_OFF_any_active_recovery=recovery['pre_OFF_any_active_recovery'])
        else:
            durable_json(args.output/'localized_recovery.json',{'recovery_applicable':False,'reason':'No injected ON'})
        measured = helpers.snapshot(STARTED,0.)
        if measured['wall_s']>1800 or measured['cpu_s']>1800 or measured['peak_rss_bytes']>4*1024**3:
            raise ValueError('Measured corrected whole-case resource cap exceeded')
        outcome.update(measured,data_integrity_ok=True,survivor_count=result['surviving_ON_threshold_carrier_count'],
                       ON_threshold_carrier_count=len(result['all_ON_threshold_carriers']))
        durable_json(args.output/'outcome.json',outcome)
        durable_json(args.output/'outcomes.json',[outcome])
        durable_json(args.output/'resource_receipt.json',{**measured,'caps_passed':True,
            'caps':{'wall_s':1800,'cpu_s_available':1800,'exclusive_cpu_allocation_seconds':1800,'peak_rss_bytes':4*1024**3}})
        durable_json(args.output/'single_case_status.json',{'status':'CLOSED_PENDING_DURABLE_COMMIT','panel':'VAL_B','case_id':args.case,'no_retry_or_redraw':True})
        manifest={}
        for file in sorted(args.output.iterdir()):
            if file.is_file():
                with file.open('rb') as handle: os.fsync(handle.fileno())
                manifest[file.name]={'SHA256':digest(file),'size_bytes':file.stat().st_size}
        durable_json(args.output/'artifact_manifest.json',manifest)
        claim.update(status='CLOSED_PENDING_DURABLE_COMMIT',whole_job_cpu_s=measured['cpu_s'])
        durable_json(claim_path,claim)
        durable_json(args.output/'COMMITTED.json',{'status':'COMPLETED_CASE_ONLY','case_id':args.case,'panel':'VAL_B',
            'artifact_manifest_SHA256':digest(args.output/'artifact_manifest.json'),'caps_passed':True,
            'no_retry_or_redraw':True,'complete_panel_gate_evaluated':False})
        failed=False
    except BaseException as error:
        signal.setitimer(signal.ITIMER_REAL,0); signal.setitimer(signal.ITIMER_PROF,0)
        (args.output/'COMMITTED.json').unlink(missing_ok=True)
        r=resource.getrusage(resource.RUSAGE_SELF)
        outcome.update(data_integrity_ok=False,failure={'type':type(error).__name__,'message':str(error)},
                       wall_s=time.monotonic()-STARTED,cpu_s=r.ru_utime+r.ru_stime,peak_rss_bytes=r.ru_maxrss*1024)
        try:
            durable_json(args.output/'outcome.json',outcome); durable_json(args.output/'outcomes.json',[outcome])
            (args.output/'failure_traceback.txt').write_text(traceback.format_exc())
            claim.update(status='FAILED_CLOSED'); durable_json(claim_path,claim)
        except BaseException:
            pass
    finally:
        signal.setitimer(signal.ITIMER_REAL,0); signal.setitimer(signal.ITIMER_PROF,0)
    print(json.dumps({k:outcome.get(k) for k in ('case_id','data_integrity_ok','all_active_on_recovered',
          'pre_OFF_all_active_recovery','survivor_count','wall_s','cpu_s','peak_rss_bytes','failure')}),flush=True)
    return 1 if failed else 0

if __name__=='__main__': raise SystemExit(main())
