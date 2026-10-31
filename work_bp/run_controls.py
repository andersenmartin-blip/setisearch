"""Finite BP paired synthetic controls. No work occurs during import."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import gc
import hashlib
import json
import os
import platform
import sys
import time
import traceback
import numpy as np

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
sys.path.insert(0, str(REPO / 'work_bo/src'))
sys.path.insert(0, str(ROOT))
import capture
import methods
import synthetic
import paired_search


def write(path, value):
    capture.publish_json(Path(path), value)


def verify(plan_path, receipt_path):
    if sys.flags.optimize != 0:
        raise ValueError('Assertions must remain enabled')
    plan = json.loads(plan_path.read_text())
    receipt = json.loads(receipt_path.read_text())
    assert plan['schema'] == 'SETI_BP_FIXED24_PLAN_V1'
    assert plan['synthetic_only'] and not plan['astronomical_powers_authorized']
    assert receipt['plan_sha256'] == capture.sha(plan_path)
    assert receipt['exact_readback_verified'] and receipt['before_execution']
    assert len(receipt['public_commit_sha']) == 40
    assert platform.python_version() == plan['runtime']['python_version']
    assert np.__version__ == plan['runtime']['numpy_version']
    assert capture.sha(sys.executable) == plan['runtime']['python_executable_sha256']
    if any(os.environ.get(k) != '1' for k in capture.THREAD_KEYS):
        raise ValueError('All numerical thread environment variables must be 1')
    pins = {str(REPO / p['path']):p['sha256'] for p in plan['source_pins']}
    pins.update({str(plan_path):capture.sha(plan_path),str(receipt_path):capture.sha(receipt_path)})
    capture.verify_pins(pins)
    methods.verify_sources()
    assert plan['synthetic_specification'] == synthetic.specification()
    assert plan['paired_search_specification'] == paired_search.specification()
    assert plan['cases'] == synthetic.cases()
    return plan, receipt, pins


def run_child(plan_path, receipt_path, index, payload, run_root):
    plan, freeze, pins = verify(plan_path, receipt_path)
    payload.mkdir()
    case = plan['cases'][index]
    start = time.monotonic()
    records = []
    scan_dirs = []
    try:
        base_seed = case['base_seed_index']
        bases = run_root / 'bases' / f'seed{base_seed:02d}'
        if case['kind'] == 'null':
            bases.mkdir(parents=True, exist_ok=False)
        for scan in range(6):
            base_path = bases / f'scan{scan}.npy'
            base_receipt_path = bases / f'scan{scan}.json'
            if case['kind'] == 'null':
                base_receipt = synthetic.generate_base_scan(base_seed, scan, base_path)
                write(base_receipt_path, base_receipt)
            else:
                base_receipt = json.loads(base_receipt_path.read_text())
            raw, injection_receipt = synthetic.prepare_injected_scan(
                base_path, case, scan, payload / f'delta_scan{scan}.npz')
            assert not raw.flags.writeable
            scan_dir = payload / f'scan{scan}'
            scan_summary = paired_search.analyze_scan(raw, scan_dir, scan)
            assert scan_summary['input_powers_sha256_before'] == injection_receipt['common_input_powers_sha256']
            assert scan_summary['input_powers_sha256_after'] == injection_receipt['common_input_powers_sha256']
            records.append(dict(scan=scan, base_receipt=base_receipt,
                                injection_receipt=injection_receipt,
                                scan_summary=scan_summary))
            scan_dirs.append(scan_dir)
            del raw
            gc.collect()
            print(json.dumps(dict(event='SCAN_COMPLETE',case=case['id'],scan=scan)),flush=True)
        base_scan_dirs = None
        if case['kind'] != 'null':
            base_case = next(c for c in plan['cases'] if c['kind']=='null' and c['base_seed_index']==base_seed)
            base_scan_dirs = [run_root/base_case['id']/'payload'/f'scan{s}' for s in range(6)]
        result = paired_search.assess_case(scan_dirs, case, base_scan_dirs=base_scan_dirs)
        result.update(schema='SETI_BP_CASE_RESULT_V1',case=case,records=records,
                      wall_seconds=time.monotonic()-start,
                      astronomical_powers_opened=0,new_archive_requests=0,
                      public_freeze_commit=freeze['public_commit_sha'])
        capture.verify_pins(pins)
        write(payload/'RESULT.json', result)
        print(json.dumps(dict(event='GATE_TERMINAL_EOF',status=result['status'],
                              result_sha256=capture.sha(payload/'RESULT.json'))),flush=True)
        return 0 if result['status']=='PASS' else 2
    except BaseException as exc:
        failure=dict(schema='SETI_BP_CASE_EXCEPTION_V1',status='FAIL',case=case,
                     exception=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),
                     completed_scan_records=records,astronomical_powers_opened=0)
        if not (payload/'RESULT.json').exists():write(payload/'RESULT.json',failure)
        print(json.dumps(dict(event='GATE_TERMINAL_EOF',status='FAIL',
                              result_sha256=capture.sha(payload/'RESULT.json'))),flush=True)
        return 2


def run_parent(plan_path, receipt_path):
    plan, freeze, pins = verify(plan_path, receipt_path)
    run_root = ROOT/'execution'/'BP_FIXED24_V1'
    run_root.parent.mkdir(exist_ok=True)
    run_root.mkdir()
    reserve=capture.FailureReserve(run_root/'FAILURE_RESERVE.bin',1<<20)
    start=time.monotonic()
    parent_start=time.process_time()
    child_cpu=0.0
    receipts=[]
    caps=plan['caps']
    write(run_root/'RESERVATION.json',dict(schema='SETI_BP_IRREVERSIBLE_RESERVATION_V1',
          case_ids=[c['id'] for c in plan['cases']],plan_sha256=capture.sha(plan_path),
          public_freeze_commit=freeze['public_commit_sha'],started_utc=datetime.now(timezone.utc).isoformat(),
          caps=caps,retry_allowed=False,astronomical_powers_authorized=False))
    for index, case in enumerate(plan['cases']):
        folder=run_root/case['id']
        payload=folder/'payload'
        command=[sys.executable,str(Path(__file__).resolve()),'--child',str(index),
                 '--plan',str(plan_path),'--receipt',str(receipt_path),
                 '--payload',str(payload),'--run-root',str(run_root)]
        remaining=caps['cpu_seconds']-child_cpu-(time.process_time()-parent_start)
        receipt=capture.capture_child(command,folder,payload/'RESULT.json',caps,pins,
          dict(stage='BP_FIXED24_V1',case_id=case['id'],index=index),
          group=dict(deadline_monotonic=start+caps['wall_seconds'],cpu_remaining=remaining,
                     storage_roots=[run_root],stored_bytes=caps['stored_bytes'],rss_bytes=caps['rss_bytes']),
          poll_seconds=0.1)
        receipts.append(receipt)
        child_cpu+=sum(float(receipt['resources'][k] or 0) for k in ['child_user_cpu_seconds','child_system_cpu_seconds'])
        print(json.dumps(dict(case=case['id'],status=receipt['status'],
                              exit_code=receipt['actual_exit_code'],wall_seconds=time.monotonic()-start)),flush=True)
        if receipt['status']!='PASS':break
    status='PASS' if len(receipts)==24 and all(r['status']=='PASS' for r in receipts) else 'FAIL'
    terminal=dict(schema='SETI_BP_FIXED24_TERMINAL_V1',status=status,
      completed_cases=len(receipts),passed_cases=sum(r['status']=='PASS' for r in receipts),
      case_receipts=[dict(case_id=r['context']['case_id'],status=r['status'],
                         receipt_path=str(Path(r['result_path']).parents[1]/'ACTUAL_RECEIPT.json'),
                         result_sha256=r['result_sha256']) for r in receipts],
      wall_seconds=time.monotonic()-start,total_cpu_seconds=child_cpu+time.process_time()-parent_start,
      astronomical_powers_opened=0,new_observations=0,new_archive_requests=0,new_coverage_credit=0,
      full839_authorized=False,historical_HIP45688_M_failures=24,historical_full_QA=False,
      interpretation='Limited paired synthetic controls only; not FAP, sensitivity or astronomical search.')
    terminal['failure_reserve']=reserve.commit(dict(status=status,completed_cases=len(receipts)))
    capture.verify_pins(pins)
    terminal['evidence_files']=[dict(path=str(p.relative_to(run_root)),bytes=p.stat().st_size,sha256=capture.sha(p))
                              for p in sorted(run_root.rglob('*')) if p.is_file()]
    write(run_root/'TERMINAL.json',terminal)
    print(json.dumps(dict(event='BP_FINISHED',status=status,completed_cases=len(receipts))),flush=True)
    return 0 if status=='PASS' else 2


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--plan',type=Path,default=ROOT/'BP_FIXED24_PLAN.json')
    parser.add_argument('--receipt',type=Path,default=ROOT/'PUBLIC_FREEZE_RECEIPT_BP.json')
    parser.add_argument('--child',type=int)
    parser.add_argument('--payload',type=Path)
    parser.add_argument('--run-root',type=Path)
    args=parser.parse_args()
    if args.child is not None:
        return run_child(args.plan.resolve(),args.receipt.resolve(),args.child,args.payload,args.run_root)
    return run_parent(args.plan.resolve(),args.receipt.resolve())


if __name__=='__main__':
    sys.exit(main())
