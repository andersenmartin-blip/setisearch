#!/usr/bin/env python3
"""Freeze and run one fresh complete-search engineering traversal.

All actual scientific detector and independent QA functions keep their original
rules. This dispatcher creates no scientific bank, calibration or admission.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import traceback

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1]
WORKSPACE = SOURCE.parent
IDENTITY = 'SETI_FULLSEARCH_PAYLOAD_ENGINEERING_20261016_V1'
MODE = 'ENGINEERING_FIXTURES_ONLY'
SCHEMA = 'SETI_COMPLETE_SEARCH_ENGINEERING_SCOPE_V1'
MIB = 1024 ** 2
PAYLOAD_CAP = 768 * MIB
PRIMARY_CAP = 800 * MIB
QA_CAP = 64 * MIB
SUMMARY_CAP = 800 * MIB
LOG_SLOT = MIB
METADATA_CAP = MIB
OUTPUT_CAP = 2 * 1024 ** 3
CPU_CAP = 1400
GUARD_SHA = 'd02505861e9a5b3883708836e39b6a8712d56f983c740897857bb0f6e201e492'
PIN_PATHS = (
    'tools/fullsearch_integration_20261016/run.py',
    'tools/fullsearch_integration_20261016/fixture.py',
    'tools/fullsearch_integration_20261016/producer.py',
    'tools/fullsearch_integration_20261016/verifier.py',
    'tools/fullsearch_integration_20261016/summary_check.py',
    'tools/science_payload_20261016/payload.py',
    'tools/science_payload_20261016/phase_budget.py',
    'tools/bounded_payload_20261015/payload_store.py',
    'tools/fullcase_payload_20261015/array_adapter.py',
    'tools/whole_child_guard_20261015/guard.py',
    'analysis/sixscan_burst_20261015/worker.py',
    'analysis/sixscan_burst_20261015/detector.py',
    'analysis/sixscan_burst_20261015/qa.py',
    'analysis/sixscan_burst_20261015/summarize.py',
    'analysis/sixscan_burst_20261015/contract.json',
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(MIB), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    data = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    require(len(data) <= METADATA_CAP // 2, 'Individual parent metadata cap exceeded')
    with Path(path).open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def size_tree(path):
    path = Path(path)
    if not path.exists():
        return 0
    if path.is_file():
        require(not path.is_symlink(), 'Symlink output rejected')
        return path.stat().st_size
    total = 0
    for child in path.rglob('*'):
        require(not child.is_symlink(), 'Symlink output rejected')
        if child.is_file():
            total += child.stat().st_size
    return total


def load_module(name, relative):
    path = SOURCE / relative
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def source_pins():
    return [dict(path=p, bytes=(SOURCE / p).stat().st_size, sha256=sha(SOURCE / p))
            for p in PIN_PATHS]


def once_path():
    return WORKSPACE / 'work' / 'FULLSEARCH_ENGINEERING_CLAIMS_20261016' / (IDENTITY + '.json')


def freeze(scope_path, output_root):
    scope_path = Path(scope_path).resolve()
    output_root = Path(output_root).resolve()
    require(scope_path.parent.is_dir(), 'Existing scope parent required')
    require(not output_root.exists() and output_root.parent.is_dir(), 'Fresh output path required')
    require(not once_path().exists(), 'Engineering identity already attempted; no retry')
    require(sha(SOURCE / 'tools/whole_child_guard_20261015/guard.py') == GUARD_SHA,
            'Original whole-child guard changed')
    scope = dict(schema=SCHEMA, identity=IDENTITY, mode=MODE,
        output_root=str(output_root), source_pins=source_pins(),
        resources=dict(primary_CPU_s=600, qa_CPU_s=600, summary_CPU_s=120,
            metadata_CPU_s=80, reserved_total_CPU_s=CPU_CAP,
            primary_QA_wall_s=1800, summary_wall_s=300,
            child_address_space_bytes=1024**3, payload_cap_bytes=PAYLOAD_CAP,
            primary_phase_bytes=PRIMARY_CAP, qa_phase_bytes=QA_CAP,
            summary_projection_phase_bytes=SUMMARY_CAP,
            per_phase_log_receipt_bytes=LOG_SLOT, metadata_bytes=METADATA_CAP,
            total_output_cap_bytes=OUTPUT_CAP),
        phase_mapping={'primary': 'actual_complete_detector_and_transport',
            'qa': 'independent_complete_streamed_search',
            'exposed': 'engineering_summary_projection_no_telescope_exposure',
            'exposed_qa': 'zero_slots'},
        fixture=dict(shape=[6,16,12096], core_channels=4096,
            widths=[1,3,9,33], window_starts=[0,2,4,6,8,10,12],
            maximum_drift_Hz_s=4, normalization_channels=4096,
            running_median_channels=501, original_OFF_inventory_cap=2000000,
            base='Counter avalanche uint64 -> low20 bits, raw=0.75+q*2^-21 as float32; exact formula in pinned fixture.py',
            fixed_lines=[dict(scans=[0,1], core_offset=1024, rows=[6,7,8,9], raw_excess=2.0),
                         dict(scans=[2], core_offset=3072, rows=[6,7,8,9], raw_excess=2.0)],
            primary_truth='Only isolated ON scan2, core+3072, zero drift, rows6..9, width1',
            random_APIs_or_random_state_used=False,
            statistical_noise_law_or_independence_claimed=False),
        expected_exercise='Full search, complete maps/aliases/OFF inventories, matched and surviving ON hits; exercise failure is retained rather than retuned',
        rank_status='NOT_APPLIED_NO_CALIBRATION',
        scientific_bank_admission=False, old_scientific_mains_called=False,
        retired_identities_or_closed_banks_reused=False,
        physical_FAP_or_sensitivity_established=False,
        qualified_SETI_detection=False, original_A_B='FAIL_CLOSED',
        new_telescope_requests=0, new_telescope_bytes=0, cost_DKK=0,
        checkpoint='2026-10-20',
        conditional_bounds='Physical payload/projection caps; metadata expansion and process limits remain hard acceptance requirements, not a guarantee every possible case completes.',
        logs='Python output is bounded by child wrappers. Native stdout/stderr size is an acceptance check after reaping, not a universal hard writer quota.')
    save(scope_path, scope)
    return dict(status='FROZEN_ENGINEERING_ONLY', scope=str(scope_path), scope_sha256=sha(scope_path))


def run(scope_path):
    scope_path = Path(scope_path).resolve()
    scope = json.loads(scope_path.read_text())
    require(scope['schema'] == SCHEMA and scope['identity'] == IDENTITY and scope['mode'] == MODE,
            'Frozen engineering identity/schema required')
    require(scope['source_pins'] == source_pins(), 'Frozen source pins differ')
    require(scope['resources']['reserved_total_CPU_s'] == CPU_CAP and
            scope['resources']['total_output_cap_bytes'] == OUTPUT_CAP, 'Resource declaration changed')
    require(sha(SOURCE / 'tools/whole_child_guard_20261015/guard.py') == GUARD_SHA, 'Guard pin differs')
    root = Path(scope['output_root'])
    require(not root.exists() and root.parent.is_dir(), 'Fresh exclusive output path required')
    ledger_module = load_module('fullsearch_phase_budget', 'tools/science_payload_20261016/phase_budget.py')
    guard = load_module('fullsearch_guard', 'tools/whole_child_guard_20261015/guard.py')
    plan = ledger_module.plan_budget(primary_count=1, primary_bound_bytes=PRIMARY_CAP, primary_cpu_s=600,
        qa_count=1, qa_bound_bytes=QA_CAP, qa_cpu_s=600,
        exposed_count=1, exposed_bound_bytes=SUMMARY_CAP, exposed_cpu_s=120,
        exposed_qa_count=0, exposed_qa_bound_bytes=1, exposed_qa_cpu_s=2,
        metadata_reserve_bytes=METADATA_CAP, metadata_cpu_s=80,
        log_receipt_overhead_bytes=LOG_SLOT, output_limit_bytes=OUTPUT_CAP,
        disk_headroom_bytes=shutil.disk_usage(root.parent).free, cpu_limit_s=CPU_CAP, mode=MODE)
    require(plan['admitted'], 'Complete three-phase engineering reservation did not fit')
    claim = once_path()
    claim.parent.mkdir(parents=True, exist_ok=True)
    save(claim, dict(identity=IDENTITY, status='CLAIMED_ONCE_BEFORE_NUMERICAL_CHILD_IMPORTS',
        scope_sha256=sha(scope_path), output_root=str(root), no_retry=True))
    root.mkdir()
    save(root / 'FROZEN_SCOPE.json', scope)
    ledger = ledger_module.PhaseLedger.create(root / 'ledger', plan)
    state = dict(status='RUNNING_ENGINEERING_ONLY', identity=IDENTITY,
        scope_sha256=sha(scope_path), phase_mapping=scope['phase_mapping'], phases=[],
        scientific_bank_admission=False, rank_status='NOT_APPLIED_NO_CALIBRATION',
        qualified_SETI_detection=False, original_A_B='FAIL_CLOSED')
    producer_folder = root / 'fixture'
    qa_report = root / 'QA_REPORT.json'
    summary_root = root / 'summary_projection'
    summary_report = root / 'SUMMARY_REPORT.json'
    commands = (
        ('primary', 600, 1800, [sys.executable,str(HERE/'producer.py'),'--folder',str(producer_folder),
            '--payload-cap',str(PAYLOAD_CAP),'--scope',str(scope_path),'--scope-sha256',sha(scope_path)],
            [producer_folder]),
        ('qa',600,1800,[sys.executable,str(HERE/'verifier.py'),'--folder',str(producer_folder),
            '--report',str(qa_report)],[qa_report]),
        ('exposed',120,300,[sys.executable,str(HERE/'summary_check.py'),
            '--payload',str(producer_folder/'payload'),
            '--producer-receipt',str(root/'process_primary'/'WAIT4_RECEIPT.json'),
            '--qa-report',str(qa_report),'--qa-receipt',str(root/'process_qa'/'WAIT4_RECEIPT.json'),
            '--scope',str(scope_path),'--projection-root',str(summary_root),
            '--report',str(summary_report),'--payload-cap',str(PAYLOAD_CAP),
            '--projection-cap',str(SUMMARY_CAP)],[summary_root,summary_report]))
    for phase,cpu,wall,command,outputs in commands:
        phase_claim = ledger.claim(phase, IDENTITY+'_'+phase)
        attempt = root / ('process_'+phase)
        receipt = None
        try:
            require(scope['source_pins'] == source_pins(), 'Source changed before phase')
            receipt = guard.run_once(command, attempt, guard.policy(cpu,wall,1024**3))
            report_path, expected_status = {
                'primary': (producer_folder/'PRODUCER.json','PRODUCED_COMPLETE_SEARCH_ENGINEERING_ONLY'),
                'qa': (qa_report,'PASS_COMPLETE_SEARCH_ENGINEERING_ONLY'),
                'exposed': (summary_report,'PASS_COMPLETE_CASE_SUMMARY_ENGINEERING_ONLY')}[phase]
            require(receipt.get('resource_acceptance') is True,
                    'Whole-child resource/process closure did not pass')
            child_report = json.loads(report_path.read_text())
            require(child_report.get('status') == expected_status and
                    child_report.get('scientific_bank_admission') is False,
                    'Child completion/provenance report did not pass')
            measured = sum(size_tree(p) for p in outputs)
            event = ledger.complete(phase_claim['claim_id'], receipt=receipt,
                payload_bytes=measured, log_receipt_bytes=size_tree(attempt))
            accepted = event['data']['accepted']
            state['phases'].append(dict(phase=phase, accepted=accepted, receipt=receipt,
                payload_bytes=measured, log_receipt_bytes=size_tree(attempt)))
            save(root/('PHASE_'+phase+'.json'),state['phases'][-1])
            if not accepted:
                state['status']='STOPPED_RETAINED_NO_RETRY'
                break
        except BaseException as error:
            if ledger.snapshot()['pending']:
                ledger.partial_error(phase_claim['claim_id'], error=repr(error), receipt=receipt,
                    payload_bytes=sum(size_tree(p) for p in outputs), log_receipt_bytes=size_tree(attempt))
            state['status']='STOPPED_RETAINED_NO_RETRY'
            state['parent_error']=dict(type=type(error).__name__,message=str(error)[:512])
            break
    try:
        if state['status']=='RUNNING_ENGINEERING_ONLY':
            require(scope['source_pins']==source_pins(),'Sources changed during execution')
            for label,p in [('producer',producer_folder/'PRODUCER.json'),('qa',qa_report),('summary',summary_report)]:
                document=json.loads(p.read_text())
                require(document.get('scientific_bank_admission',document.get('scientific_admission',False)) is False,
                        'Engineering child cannot grant scientific admission')
                state[label+'_report_sha256']=sha(p)
            require(all(p['accepted'] for p in state['phases']) and len(state['phases'])==3,
                    'Every reserved phase must pass')
            state['status']='PASS_COMPLETE_SEARCH_ENGINEERING_ONLY'
    except BaseException as error:
        state['status']='STOPPED_RETAINED_NO_RETRY'
        state['finalization_error']=dict(type=type(error).__name__,message=str(error)[:512])
    ledger.close()
    state['ledger_snapshot']=ledger.snapshot()
    state['actual_output_bytes_before_final_receipt']=size_tree(root)
    state['whole_children_CPU_s']=sum(p['receipt']['whole_child_CPU_s'] for p in state['phases'])
    if state['actual_output_bytes_before_final_receipt']+METADATA_CAP>OUTPUT_CAP:
        state['status']='STOPPED_RETAINED_NO_RETRY'
        state['output_budget_failure']=True
    save(root/'RESULT.json',state)
    return dict(status=state['status'],identity=IDENTITY,
        scientific_bank_admission=False,whole_children_CPU_s=state['whole_children_CPU_s'])


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('freeze');p.add_argument('--scope',type=Path,required=True);p.add_argument('--output-root',type=Path,required=True)
    p=sub.add_parser('run');p.add_argument('--scope',type=Path,required=True)
    args=ap.parse_args()
    result=freeze(args.scope,args.output_root) if args.command=='freeze' else run(args.scope)
    print(json.dumps(result,sort_keys=True),flush=True)
    return 0 if result['status'] in ('FROZEN_ENGINEERING_ONLY','PASS_COMPLETE_SEARCH_ENGINEERING_ONLY') else 1


if __name__=='__main__':
    raise SystemExit(main())
