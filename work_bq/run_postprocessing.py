"""New BQ identity: finish saved A04 association only; BP remains failed."""
from pathlib import Path
import argparse
import json
import os
import platform
import sys
import time
import traceback
import numpy as np

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(REPO/'work_bo/src'))
sys.path.insert(0,str(ROOT))
import capture
import stream_association


def verify():
    if sys.flags.optimize:raise ValueError('Assertions must be enabled')
    plan=json.loads((ROOT/'BQ_POSTPROCESSING_PLAN.json').read_text())
    freeze=json.loads((ROOT/'PUBLIC_FREEZE_RECEIPT_BQ.json').read_text())
    assert freeze['exact_readback_verified'] and freeze['before_execution']
    assert freeze['plan_sha256']==capture.sha(ROOT/'BQ_POSTPROCESSING_PLAN.json')
    assert plan['schema']=='SETI_BQ_SAVED_A04_POSTPROCESSING_V1'
    assert plan['stream_specification']==stream_association.specification()
    assert not plan['RNG_authorized'] and not plan['new_scan_scores_authorized']
    assert not plan['astronomical_powers_authorized']
    assert platform.python_version()==plan['runtime']['python_version']
    assert np.__version__==plan['runtime']['numpy_version']
    assert capture.sha(sys.executable)==plan['runtime']['python_executable_sha256']
    assert all(os.environ.get(k)=='1' for k in capture.THREAD_KEYS)
    pins={str(REPO/p['path']):p['sha256'] for p in plan['source_pins']+plan['input_pins']}
    pins[str(ROOT/'BQ_POSTPROCESSING_PLAN.json')]=freeze['plan_sha256']
    pins[str(ROOT/'PUBLIC_FREEZE_RECEIPT_BQ.json')]=capture.sha(ROOT/'PUBLIC_FREEZE_RECEIPT_BQ.json')
    capture.verify_pins(pins)
    bp=json.loads((REPO/'work_bp/BP_FIXED24_PLAN.json').read_text())
    terminal=json.loads((REPO/'work_bp/execution/BP_FIXED24_V1/TERMINAL.json').read_text())
    assert terminal['status']=='FAIL' and terminal['passed_cases']==23 and terminal['completed_cases']==24
    assert plan['case']==bp['cases'][-1] and plan['case']['id']=='A04'
    return plan,freeze,pins


def child(payload):
    plan,freeze,pins=verify()
    scan_dirs=[REPO/p for p in plan['scan_dirs']]
    base_dirs=[REPO/p for p in plan['base_scan_dirs']]
    input_pins=[dict(path=str(REPO/p['path']),bytes=p['bytes'],sha256=p['sha256']) for p in plan['input_pins']+plan['source_pins']]
    try:
        result=stream_association.run_stream_assessment(scan_dirs,plan['case'],payload,base_dirs,input_pins)
        result.update(public_freeze_commit=freeze['public_commit_sha'],
                      BP_original_status='FAIL',BP_original_passed_cases=23,
                      BP_failed_identity='A04',new_RNG_calls=0,new_scan_searches=0,
                      astronomical_powers_opened=0)
        capture.verify_pins(pins)
        capture.publish_json(payload/'RESULT.json',result)
        print(json.dumps(dict(event='GATE_TERMINAL_EOF',status=result['status'],result_sha256=capture.sha(payload/'RESULT.json'))),flush=True)
        return 0 if result['status']=='PASS' else 2
    except BaseException as exc:
        payload.mkdir(exist_ok=True)
        result=dict(status='FAIL',exception=type(exc).__name__+': '+str(exc),traceback=traceback.format_exc(),BP_original_status='FAIL')
        if not (payload/'RESULT.json').exists():capture.publish_json(payload/'RESULT.json',result)
        print(json.dumps(dict(event='GATE_TERMINAL_EOF',status='FAIL',result_sha256=capture.sha(payload/'RESULT.json'))),flush=True)
        return 2


def parent():
    plan,freeze,pins=verify()
    root=ROOT/'execution/BQ_A04_ASSOC_V1';root.parent.mkdir(exist_ok=True);root.mkdir()
    reserve=capture.FailureReserve(root/'FAILURE_RESERVE.bin',1<<20)
    capture.publish_json(root/'RESERVATION.json',dict(plan_sha256=freeze['plan_sha256'],public_commit_sha=freeze['public_commit_sha'],identity='BQ_A04_ASSOC_V1',no_retry=True,BP_status_preserved='FAIL'))
    folder=root/'A04_POSTPROCESSING';payload=folder/'payload'
    receipt=capture.capture_child([sys.executable,str(Path(__file__).resolve()),'--child','--payload',str(payload)],folder,payload/'RESULT.json',plan['caps'],pins,
      context=dict(identity='BQ_A04_ASSOC_V1',operation='saved association postprocessing only'),poll_seconds=.1,
      group=dict(storage_roots=[root],stored_bytes=plan['caps']['stored_bytes'],rss_bytes=plan['caps']['rss_bytes']))
    terminal=dict(schema='SETI_BQ_CLOSED_POSTPROCESSING_V1',status=receipt['status'],actual_exit_code=receipt['actual_exit_code'],
      receipt_path=str(folder/'ACTUAL_RECEIPT.json'),receipt_sha256=capture.sha(folder/'ACTUAL_RECEIPT.json'),
      result_sha256=receipt['result_sha256'],resources=receipt['resources'],BP_original_status='FAIL',
      new_RNG_calls=0,new_scan_searches=0,astronomical_powers_opened=0)
    terminal['failure_reserve']=reserve.commit(dict(status=receipt['status']))
    terminal['files']=[dict(path=str(p.relative_to(root)),bytes=p.stat().st_size,sha256=capture.sha(p)) for p in sorted(root.rglob('*')) if p.is_file()]
    capture.publish_json(root/'TERMINAL_BQ.json',terminal)
    print(json.dumps(terminal),flush=True)
    return 0 if receipt['status']=='PASS' else 2


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--child',action='store_true');p.add_argument('--payload',type=Path)
    a=p.parse_args();sys.exit(child(a.payload) if a.child else parent())
