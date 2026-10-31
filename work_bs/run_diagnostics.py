"""Execute a single preregistered non-scientific file-stability trial."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import sys
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
sys.path.insert(0, str(REPO/'work_bo/src'))
import capture
sys.path.insert(0,str(ROOT))
import diagnostic


def verified_plan():
    plan_path = ROOT/'BS_FILE_STABILITY_PLAN.json'
    plan = json.loads(plan_path.read_text())
    freeze = json.loads((ROOT/'PUBLIC_FREEZE_RECEIPT_BS.json').read_text())
    if not freeze['exact_readback_verified'] or not freeze['before_execution']:
        raise ValueError('Public freeze not verified')
    if capture.sha(plan_path) != freeze['plan_sha256']:
        raise ValueError('Plan changed after freeze')
    if plan['scientific_reexecution_authorized'] or plan['RNG_authorized']:
        raise ValueError('Only deterministic file fixtures are allowed')
    if platform.python_version()!=plan['runtime']['python_version'] or capture.sha(sys.executable)!=plan['runtime']['executable_sha256']:
        raise ValueError('Runtime changed after freeze')
    pins = {str(REPO/item['path']): item['sha256'] for item in plan['source_pins']+plan['historical_pins']}
    pins[str(plan_path)] = freeze['plan_sha256']
    pins[str(ROOT/'PUBLIC_FREEZE_RECEIPT_BS.json')] = capture.sha(ROOT/'PUBLIC_FREEZE_RECEIPT_BS.json')
    capture.verify_pins(pins)
    return plan, freeze, pins


def run(trial_id):
    plan, freeze, pins = verified_plan()
    trial = next(t for t in plan['trials'] if t['id'] == trial_id)
    root = ROOT/'execution'/plan['execution_identity']
    root.mkdir(parents=True, exist_ok=True)
    folder = root/trial_id
    payload = folder/'payload'
    command = [sys.executable, str(ROOT/'audited_worker.py'), '--audit', str(folder/'PYTHON_AUDIT.jsonl'),
               '--writer', trial['writer'], '--output-dir', str(payload),
               '--records', str(trial['records']), '--pace-ms', str(trial['pace_ms'])]
    started = time.monotonic();parent_cpu_started=time.process_time()
    receipt = capture.capture_child(command, folder, payload/'RESULT.json', plan['caps_per_trial'], pins,
        context={'identity':plan['execution_identity'], 'trial':trial_id,
                 'operation':'Unrelated deterministic JSONL fixtures; no saved scores or astronomical powers'},
        poll_seconds=.1,
        group={'storage_roots':[root], 'stored_bytes':plan['phase_storage_cap_bytes'],
               'rss_bytes':plan['caps_per_trial']['rss_bytes']})
    terminal = {'schema':'SETI_BS_DIAGNOSTIC_CAPTURE_V1', 'trial':trial_id,
        'status':receipt['status'], 'capture_status':receipt['status'], 'actual_exit_code':receipt['actual_exit_code'],
        'public_freeze_commit':freeze['public_commit_sha'], 'plan_sha256':freeze['plan_sha256'],
        'wall_seconds_including_capture':time.monotonic()-started,
        'capture_receipt_sha256':capture.sha(folder/'ACTUAL_RECEIPT.json'),
        'source_and_historical_pins_verified_after':False,
        'new_science_trials':0, 'RNG_calls':0, 'astronomical_powers_opened':0}
    terminal['closing_errors']=[]
    terminal['parent_stream_verification']=[]
    try:
        capture.verify_pins(pins)
        terminal['source_and_historical_pins_verified_after'] = True
        if receipt['status']!='PASS':
            raise ValueError('Child capture did not pass')
        if capture.sha(payload/'RESULT.json')!=receipt['result_sha256']:
            raise ValueError('Captured RESULT changed')
        result=json.loads((payload/'RESULT.json').read_text())
        if result['status']!='PASS' or len(result['streams'])!=2:
            raise ValueError('Incomplete fixture result')
        if not result['monitor_complete'] or result['monitor_violations']:
            raise ValueError('Monitor incomplete or observed a mutation')
        if capture.sha(payload/'FILE_MONITOR.json')!=result['monitor']['sha256']:
            raise ValueError('Monitor evidence changed')
        for expected,detail in zip(plan['expected_streams'],result['streams']):
            for key in ['stream','bytes','records','sha256']:
                if detail['expected'][key]!=expected[key]:
                    raise ValueError('Result differs from prospective expected fixture')
            checked=diagnostic.verify_file(payload/'payload'/detail['path'],detail['expected'])
            if checked!=detail['initial_independent_check'] or checked!=detail['final_independent_check']:
                raise ValueError('Stream changed after child validation')
            terminal['parent_stream_verification'].append(checked)
    except BaseException as exc:
        terminal['status']='FAIL'
        terminal['closing_errors'].append(type(exc).__name__+': '+str(exc))
    terminal['files'] = [{'path':str(p.relative_to(folder)), 'bytes':p.stat().st_size,
                          'sha256':capture.sha(p)} for p in sorted(folder.rglob('*')) if p.is_file()]
    try:
        if terminal['status']!='PASS':
            raise ValueError('Earlier closure failed')
        final={item['path']:item for item in terminal['files']}
        if final['payload/RESULT.json']['sha256']!=receipt['result_sha256']:
            raise ValueError('Final inventory contradicts captured RESULT')
        if final['payload/FILE_MONITOR.json']['sha256']!=result['monitor']['sha256']:
            raise ValueError('Final inventory contradicts monitor receipt')
        for detail,checked in zip(result['streams'],terminal['parent_stream_verification']):
            actual=final['payload/payload/'+detail['path']]
            if actual['bytes']!=checked['bytes'] or actual['sha256']!=checked['sha256']:
                raise ValueError('Final inventory contradicts fixture receipt')
        terminal['final_inventory_matches_manifests']=True
    except BaseException as exc:
        terminal['status']='FAIL'
        terminal['closing_errors'].append(type(exc).__name__+': '+str(exc))
        terminal['final_inventory_matches_manifests']=False
    terminal['wall_seconds_including_parent_closure']=time.monotonic()-started
    terminal['cpu_seconds_including_parent_closure']=time.process_time()-parent_cpu_started+sum(
        float(receipt['resources'][key] or 0) for key in ['child_user_cpu_seconds','child_system_cpu_seconds'])
    if terminal['wall_seconds_including_parent_closure']>plan['caps_per_trial']['wall_seconds'] or terminal['cpu_seconds_including_parent_closure']>plan['caps_per_trial']['cpu_seconds']:
        terminal['status']='FAIL'
        terminal['closing_errors'].append('Parent-inclusive time budget exceeded')
    capture.publish_json(folder/'TERMINAL_BS.json', terminal)
    print(json.dumps(terminal), flush=True)
    return 0 if terminal['status']=='PASS' else 2


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--trial', required=True)
    args = parser.parse_args()
    sys.exit(run(args.trial))
