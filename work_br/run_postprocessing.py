"""New BR identity: atomic publication and independent child/parent closure; BP/BQ remain failed."""
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
import closed_association
import stream_closure


def verify():
    if sys.flags.optimize:raise ValueError('Assertions must be enabled')
    plan=json.loads((ROOT/'BR_POSTPROCESSING_PLAN.json').read_text())
    freeze=json.loads((ROOT/'PUBLIC_FREEZE_RECEIPT_BR.json').read_text())
    assert freeze['exact_readback_verified'] and freeze['before_execution']
    assert freeze['plan_sha256']==capture.sha(ROOT/'BR_POSTPROCESSING_PLAN.json')
    assert plan['schema']=='SETI_BR_CLOSED_A04_POSTPROCESSING_V1'
    assert plan['stream_specification']==closed_association.specification()
    assert not plan['RNG_authorized'] and not plan['new_scan_scores_authorized']
    assert not plan['astronomical_powers_authorized']
    assert platform.python_version()==plan['runtime']['python_version']
    assert np.__version__==plan['runtime']['numpy_version']
    assert capture.sha(sys.executable)==plan['runtime']['python_executable_sha256']
    assert all(os.environ.get(k)=='1' for k in capture.THREAD_KEYS)
    pins={str(REPO/p['path']):p['sha256'] for p in plan['source_pins']+plan['input_pins']}
    pins[str(ROOT/'BR_POSTPROCESSING_PLAN.json')]=freeze['plan_sha256']
    pins[str(ROOT/'PUBLIC_FREEZE_RECEIPT_BR.json')]=capture.sha(ROOT/'PUBLIC_FREEZE_RECEIPT_BR.json')
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
        result=closed_association.run_closed_assessment(scan_dirs,plan['case'],payload,base_dirs,input_pins)
        result.update(public_freeze_commit=freeze['public_commit_sha'],
                      BP_original_status='FAIL',BP_original_passed_cases=23,BQ_effective_status='EVIDENCE_FAIL',
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
    start=time.monotonic();parent_cpu_start=time.process_time()
    root=ROOT/'execution/BR_A04_ASSOC_V1';root.parent.mkdir(exist_ok=True);root.mkdir()
    reserve=capture.FailureReserve(root/'FAILURE_RESERVE.bin',1<<20)
    capture.publish_json(root/'RESERVATION.json',dict(plan_sha256=freeze['plan_sha256'],public_commit_sha=freeze['public_commit_sha'],identity='BR_A04_ASSOC_V1',no_retry=True,BP_status_preserved='FAIL'))
    folder=root/'A04_POSTPROCESSING';payload=folder/'payload'
    receipt=capture.capture_child([sys.executable,str(Path(__file__).resolve()),'--child','--payload',str(payload)],folder,payload/'RESULT.json',plan['caps'],pins,
      context=dict(identity='BR_A04_ASSOC_V1',operation='saved association postprocessing only'),poll_seconds=.1,
      group=dict(storage_roots=[root],stored_bytes=plan['caps']['stored_bytes'],rss_bytes=plan['caps']['rss_bytes']))
    closure_checks=[];effective_status=receipt['status'];closing_errors=[]
    try:
        if receipt['status']!='PASS':raise ValueError('Child capture did not pass')
        if capture.sha(payload/'RESULT.json')!=receipt['result_sha256']:raise ValueError('Captured result changed before parent closure')
        result=json.loads((payload/'RESULT.json').read_text())
        previous=result['child_stream_closure']
        first=stream_closure.evaluate_closure(payload,result,'parent_end',previous_check=previous)
        closure_checks.append(first)
        if first['effective_status']!='PASS':raise ValueError('First parent stream closure failed')
        between_inventory=capture.inventory(payload)
        second=stream_closure.evaluate_closure(payload,result,'parent_end',previous_check=first)
        closure_checks.append(second)
        if second['effective_status']!='PASS':raise ValueError('Second parent stream closure failed')
        if capture.inventory(payload)!=between_inventory:raise ValueError('Payload changed during parent closure')
        capture.verify_pins(pins)
    except BaseException as exc:
        effective_status='FAIL';closing_errors.append(type(exc).__name__+': '+str(exc))
    total_cpu=time.process_time()-parent_cpu_start+sum(float(receipt['resources'][k] or 0) for k in ['child_user_cpu_seconds','child_system_cpu_seconds'])
    if total_cpu>plan['caps']['cpu_seconds'] or time.monotonic()-start>plan['caps']['wall_seconds']:
        effective_status='FAIL';closing_errors.append('Parent-inclusive closure resource limit exceeded')
    terminal=dict(schema='SETI_BR_CLOSED_POSTPROCESSING_V1',status=effective_status,capture_status=receipt['status'],actual_exit_code=receipt['actual_exit_code'],
      receipt_path=str(folder/'ACTUAL_RECEIPT.json'),receipt_sha256=capture.sha(folder/'ACTUAL_RECEIPT.json'),
      result_sha256=receipt['result_sha256'],resources=receipt['resources'],BP_original_status='FAIL',BQ_effective_status='EVIDENCE_FAIL',
      parent_stream_closure=closure_checks,closing_errors=closing_errors,total_cpu_seconds_including_parent_closure=total_cpu,wall_seconds_including_parent_closure=time.monotonic()-start,
      new_RNG_calls=0,new_scan_searches=0,astronomical_powers_opened=0)
    terminal['files']=[dict(path=str(p.relative_to(root)),bytes=p.stat().st_size,sha256=capture.sha(p)) for p in sorted(root.rglob('*')) if p.is_file() and p.name!='FAILURE_RESERVE.bin']
    try:
        if effective_status!='PASS':raise ValueError('Earlier closure did not pass')
        final_map={x['path']:x for x in terminal['files']}
        for method in ('current','legacy'):
            declared=result['method_results'][method]['association_stream']
            actual=final_map['A04_POSTPROCESSING/payload/'+declared['path']]
            if actual['bytes']!=declared['bytes'] or actual['sha256']!=declared['sha256']:
                raise ValueError('Final terminal inventory contradicts '+method+' stream receipt')
        if final_map['A04_POSTPROCESSING/payload/RESULT.json']['sha256']!=receipt['result_sha256']:
            raise ValueError('Final terminal inventory contradicts captured RESULT')
        terminal['final_inventory_matches_result_manifests']=True
    except BaseException as exc:
        effective_status='FAIL';closing_errors.append(type(exc).__name__+': '+str(exc))
        terminal['final_inventory_matches_result_manifests']=False
    total_cpu=time.process_time()-parent_cpu_start+sum(float(receipt['resources'][k] or 0) for k in ['child_user_cpu_seconds','child_system_cpu_seconds'])
    if total_cpu>plan['caps']['cpu_seconds'] or time.monotonic()-start>plan['caps']['wall_seconds']:
        effective_status='FAIL';closing_errors.append('Final inventory resource limit exceeded')
    terminal.update(status=effective_status,total_cpu_seconds_including_parent_closure=total_cpu,wall_seconds_including_parent_closure=time.monotonic()-start)
    terminal['failure_reserve']=reserve.commit(dict(status=effective_status,closing_errors=closing_errors))
    terminal['files'].append(dict(path='FAILURE_RESERVE.bin',bytes=reserve.path.stat().st_size,sha256=capture.sha(reserve.path)))
    terminal['files'].sort(key=lambda x:x['path'])
    capture.publish_json(root/'TERMINAL_BR.json',terminal)
    print(json.dumps(terminal),flush=True)
    return 0 if effective_status=='PASS' else 2


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--child',action='store_true');p.add_argument('--payload',type=Path)
    a=p.parse_args();sys.exit(child(a.payload) if a.child else parent())
