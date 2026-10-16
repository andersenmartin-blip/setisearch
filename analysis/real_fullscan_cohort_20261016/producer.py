#!/usr/bin/env python3
"""One frozen cohort full-search execution on an exposed, postselected2017 real band.

This independent descriptive namespace neither calls old study mains nor grants
admission to a retired bank. Parent resource closure is known only after reap.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1]
LEGACY = SOURCE / 'analysis/sixscan_burst_20261015'
sys.path.insert(0, str(HERE))
from reader import MODE, identity_for, decode, prepare

STARTED = time.monotonic()
LOG_CAP = 64 * 1024
RECEIPT_CAP = 4 * 1024**2
PAYLOAD_CAP = 768 * 1024**2


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while block := stream.read(1 << 20):
            value.update(block)
    return value.hexdigest()


def read(path):
    path = Path(path)
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= RECEIPT_CAP,
            'Bounded regular metadata file required')
    return json.loads(path.read_text())


def save(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n').encode()
    require(len(raw) <= RECEIPT_CAP, 'Descriptive producer receipt exceeds physical bound')
    with Path(path).open('xb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())


def load(path, name):
    spec = importlib.util.spec_from_file_location(name,path)
    module = importlib.util.module_from_spec(spec);sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class BoundedText:
    def __init__(self, stream):
        self.stream,self.remaining,self.overflow = stream,LOG_CAP,False
    def write(self, text):
        text = str(text);raw = text.encode('utf-8',errors='replace')
        kept = raw[:self.remaining];self.remaining -= len(kept)
        self.overflow |= len(kept) != len(raw)
        self.stream.write(kept.decode('utf-8',errors='ignore'));return len(text)
    def flush(self):
        self.stream.flush()
    def isatty(self):
        return False


def authenticate(scope_path, expected_sha256):
    require(sha(scope_path) == expected_sha256, 'Exact frozen new descriptive scope required')
    scope = read(scope_path)
    identity = identity_for(scope['canonical_index'])
    require(scope.get('mode') == MODE and scope.get('identity') == identity,
            'Separate correctly indexed descriptive identity and mode required')
    observed = {}
    for pin in scope['source_pins']:
        relative = Path(pin['path'])
        require(not relative.is_absolute() and '..' not in relative.parts,
                'Safe relative source pin required')
        path = (SOURCE/relative).resolve()
        require(SOURCE in path.parents and relative.as_posix() not in observed,
                'Unique source-checkout pin required')
        require(path.stat().st_size == pin['bytes'] and sha(path) == pin['sha256'],
                'Frozen source pin differs: '+relative.as_posix())
        observed[relative.as_posix()] = {'bytes':pin['bytes'],'sha256':pin['sha256']}
    required = {'analysis/real_fullscan_cohort_20261016/producer.py',
        'analysis/real_fullscan_cohort_20261016/reader.py','analysis/real_fullscan_cohort_20261016/verifier.py',
        'analysis/sixscan_burst_20261015/detector.py','analysis/sixscan_burst_20261015/worker.py',
        'analysis/sixscan_burst_20261015/qa.py','analysis/sixscan_burst_20261015/contract.json',
        'tools/science_payload_20261016/payload.py'}
    require(required <= observed.keys(), 'Complete source/QA/transport freeze required')
    acceptance_pin = scope['integration_acceptance']
    acceptance_path = Path(acceptance_pin['path'])
    require(acceptance_path.is_file() and not acceptance_path.is_symlink()
            and acceptance_path.stat().st_size == acceptance_pin['bytes']
            and sha(acceptance_path) == acceptance_pin['sha256'],
            'Exact complete-engineering integration acceptance required')
    acceptance = read(acceptance_path)
    require(acceptance['status'] == 'PASS_COMPLETE_SEARCH_ENGINEERING_ONLY'
            and len(acceptance['phases']) == 3 and all(p['accepted'] for p in acceptance['phases']),
            'Every complete engineering integration phase must have passed')
    require(acceptance.get('scientific_bank_admission',False) is False,
            'Engineering acceptance cannot admit an old scientific bank')
    return scope,observed


def census(result):
    hits = result['all_ON_threshold_hypotheses']
    return {'retained_top5_ON_ge10_count':len(hits),
        'OFF_compatible_retained_ON_count':sum(h['disposition']=='OFF_MATCHED' for h in hits),
        'no_compatible_OFF_ge8_retained_ON_count':sum(h['disposition']=='SURVIVOR_EXPLORATORY' for h in hits),
        'maximum_pre_OFF_ON_score':result['maximum_pre_OFF_ON_score'],
        'ON_ge10_is_retained_per_carrier_top5_not_exhaustive_threshold_census':True,
        'OFF_ge8_inventory_is_exhaustive_declared_native4_family':True,
        'drift_grid_count':len(result['geometry']['drift_grid_hz_s']),
        'OFF_halo_channels':result['geometry']['OFF_reference_halo_channels'],
        'scans':[{'scan_id':m['scan_id'],'role':m['role'],'retained_shape':list(m['scores'].shape),
            'original_grid_hypotheses':int(m['total_original_hypothesis_count'].sum()),
            'unique_native_hypotheses':int(m['total_unique_native_hypothesis_count'].sum()),
            'maximum_retained_score':float(m['scores'].max())} for m in result['scan_maps']],
        'OFF_inventory_rows':{name:cert['inventory_rows'] for name,cert in result['OFF_inventory_certificates'].items()},
        'rank_status':'NOT_APPLIED_NO_CALIBRATION'}


def produce(folder, *, payload_cap, scope_path, scope_sha256):
    scope,observed = authenticate(scope_path,scope_sha256)
    identity = scope['identity'];index = scope['canonical_index'];band = scope['band']
    require(type(payload_cap) is int and 0 < payload_cap <= PAYLOAD_CAP,
            'Positive bounded descriptive physical payload writer cap required')
    require(payload_cap == scope['resources']['payload_cap_bytes'],
            'Child writer quota must equal its exact frozen scope reservation')
    folder = Path(folder).resolve();folder.mkdir()
    save(folder/'DESCRIPTIVE_CLAIM.json',{'identity':identity,'mode':MODE,
        'scope_sha256':scope_sha256,'status':'CLAIMED_ONCE_BEFORE_RAW_VALUES',
        'no_retry_or_replacement':True,'scientific_bank_admission':False,
        'old_exposed_case_identifier_reused':False})
    original_contract = read(LEGACY/'contract.json')
    contract,raw_bytes,source_receipt = prepare(scope,original_contract)
    # All source code, original input members and metadata are authenticated
    # before the first numerical import or NPZ raw-array value is decoded.
    import numpy as np
    require(np.__version__ == '2.3.5', 'Frozen NumPy version differs')
    worker = load(LEGACY/'worker.py','real_descriptive_unchanged_worker_functions')
    detector = load(LEGACY/'detector.py','real_descriptive_unchanged_detector')
    transport = load(SOURCE/'tools/science_payload_20261016/payload.py','real_descriptive_pinned_payload')
    raw = decode(raw_bytes,contract,np);del raw_bytes
    metadata = contract['geometry']['scan_metadata']
    hashes = worker.authenticate_arrays(raw,metadata,contract['geometry'],np)
    scans,corefirst = worker.scan_inputs(raw,metadata,contract['geometry'],detector,np)
    admission = {'status':'SEPARATE_DESCRIPTIVE_POSTSELECTED_SCOPE_ONLY','identity':identity,'mode':MODE,
        'scope_sha256':scope_sha256,'observed_source_pins':observed,
        'source_receipt':source_receipt,'integration_acceptance':scope['integration_acceptance'],
        'checked_before_numerical_imports_and_raw_array_decode':True,
        'legacy_contract_is_coordinate_template_only':True,
        'old_GO_or_scientific_admission_reused':False,'old_scientific_identity_reused':False,
        'scientific_bank_admission':False,'scientific_admission':False,
        'postselected':True,'fresh_background':False,'qualified_SETI_detection':False,
        'original_A_B':'FAIL_CLOSED','protected_2016_closed':True,'unavailable_2019_closed':True,
        'new_observation':False,'new_telescope_requests':0,'new_telescope_bytes':0,
        'rank_status':'NOT_APPLIED_NO_CALIBRATION'}
    truth = {'case_id':identity,'family':'descriptive_postselected_2017','synthetic':False,
        'synthetic_injection':False,'active_ON_scan_ids':[],
        'authenticated_input_arrays':hashes,'injected_truth_or_recovery_oracle_exists':False,
        'postselected':True,'fresh_background':False,'new_observation':False}
    case = {'case_id':identity,'family':'descriptive_postselected_2017',
        'diagnostic_only':True,'synthetic_injection':False,'postselected':True,
        'native_chunk_index':band['native_chunk_index'],'core_q':band['core_q'],'selection_index':index,
        'canonical_index':index,
        'reference_source_channel_interval':scope['band']['reference_source_channel_interval'],
        'loaded_source_channel_interval':scope['band']['loaded_source_channel_interval'],
        'rank_status':'NOT_APPLIED_NO_CALIBRATION'}
    print(json.dumps({'stage':'ACTUAL_DESCRIPTIVE_COMPLETE_SEARCH_STARTED','identity':identity,
        'native_chunk_index':band['native_chunk_index'],'core_q':band['core_q'],'raw_shapes':[list(a.shape) for a in raw]}),flush=True)
    result = detector.search_cadence(scans,corefirst,detector.Config())
    worker.verify_result_inventory(result,metadata,corefirst,np)
    require(worker.authenticate_arrays(raw,metadata,contract['geometry'],np) == hashes,
            'Complete search changed authenticated real raw-array bytes')
    result['calibrationglobal_ON_max'] = result['maximum_pre_OFF_ON_score']
    result.update(case_index=index,canonical_index=index,exposed=True,case_id=identity,input_array_hashes=hashes,
        admission=admission,generation_call_count=0,synthetic_injection=False,
        postselected=True,fresh_background=False,new_observation=False,
        rank_status='NOT_APPLIED_NO_CALIBRATION',calibration_or_recovery_panel_run=False,
        calibrationglobal_ON_max_is_legacy_uncalibrated_statistic_alias=True)
    # Match the original worker's explicit empty-activity ABI. This records
    # non-applicability, not a measured failed recovery or a recovery trial.
    result['recovery'] = {'recovery_applicable':False,'active_ON_scan_ids':[],
        'reason':'No injected primary ON; no recovery trial applies to descriptive retained telescope data'}
    require(result['recovery']['recovery_applicable'] is False and truth['active_ON_scan_ids'] == [],
            'Real data cannot acquire an applicable injected recovery result')
    actual_census = census(result)
    require(actual_census['drift_grid_count'] == 5723,
            'Complete declared global cadence drift grid required')
    encoded,arrays,descriptors = worker.json_and_array_store(result,np)
    payload = {'worker_json':encoded,'worker_arrays':arrays,'legacy_descriptors':descriptors,
        'truth':truth,'admission':admission,'case':case,
        'inputs':{s['scan_id']:a for s,a in zip(metadata,raw)},'contract':contract}
    print(json.dumps({'stage':'ACTUAL_DESCRIPTIVE_SEARCH_FINISHED_SERIALIZING',
        'census':actual_census,'legacy_array_count':len(arrays)}),flush=True)
    payload_receipt = transport.write_payload(folder/'payload',payload,cap=payload_cap)
    require(sha(scope_path) == scope_sha256, 'Frozen descriptive scope changed during producer')
    authenticate(scope_path,scope_sha256)
    pins = {name:{'bytes':(LEGACY/name).stat().st_size,'sha256':sha(LEGACY/name)}
            for name in ('worker.py','detector.py','qa.py','summarize.py','contract.json')}
    receipt = {'schema':'SETI_POSTSELECTED_REAL_FULLSCAN_PRODUCER_V1','identity':identity,
        'status':'PRODUCED_DESCRIPTIVE_REAL_FULLSCAN_ONLY','mode':MODE,'canonical_index':index,
        'scope_sha256':scope_sha256,'legacy_code_pins':pins,'source_receipt':source_receipt,
        'payload_receipt':payload_receipt,'legacy_array_count':len(arrays),
        'input_hashes':hashes,'output_census':actual_census,
        'actual_full_search_performed':True,'actual_legacy_inventory_verifier_called':True,
        'complete_full_case_arrays_and_descriptors_retained':True,
        'raw_source_decode_count':6,'RNG_called':False,'generator_called':False,
        'old_scientific_mains_called':False,'old_exposed_prerequisites_called':False,
        'calibration_panel_run':False,'injection_or_recovery_panel_run':False,
        'rank_status':'NOT_APPLIED_NO_CALIBRATION','postselected':True,'fresh_background':False,
        'scientific_bank_admission':False,'scientific_admission':False,
        'qualified_SETI_detection':False,'telescope_FAP_or_sensitivity_established':False,
        'original_A_B':'FAIL_CLOSED','protected_2016_closed':True,'unavailable_2019_closed':True,
        'new_observation':False,'new_telescope_requests':0,'new_telescope_bytes':0,'cost_DKK':0,
        'wall_s_before_parent_reap':time.monotonic()-STARTED,
        'producer_self_measurement_is_not_parent_resource_acceptance':True,
        'closure_fields_left_for_exact_parent_guard':['status','data_integrity_ok','resource_receipt']}
    save(folder/'PRODUCER.json',receipt)
    print(json.dumps({'status':receipt['status'],'legacy_array_count':len(arrays),
        'payload_bytes':payload_receipt['payload_bytes'],'output_census':actual_census}),flush=True)
    return receipt


def main():
    stdout,stderr = BoundedText(sys.stdout),BoundedText(sys.stderr)
    sys.stdout,sys.stderr = stdout,stderr
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder',type=Path,required=True)
    parser.add_argument('--scope',type=Path,required=True)
    parser.add_argument('--scope-sha256',required=True)
    parser.add_argument('--payload-cap',type=int,required=True)
    args = parser.parse_args()
    produce(args.folder,payload_cap=args.payload_cap,scope_path=args.scope,scope_sha256=args.scope_sha256)
    require(not stdout.overflow and not stderr.overflow, 'Controlled producer log quota exceeded')


if __name__ == '__main__':
    main()
