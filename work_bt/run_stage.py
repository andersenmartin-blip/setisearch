"""One exclusive BT execution, gated on public freeze and fixture review."""
from pathlib import Path
import argparse
import json
import platform
import sys
import time
import zipfile

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parent
sys.path.insert(0,str(REPO/'work_bo/src'))
sys.path.insert(0,str(ROOT))
import capture
import isolated_worker as worker


def verified_plan(kind):
    plan=json.loads((ROOT/'BT_ISOLATED_PLAN.json').read_text())
    freeze=json.loads((ROOT/'PUBLIC_FREEZE_RECEIPT_BT.json').read_text())
    if not freeze['before_execution'] or not freeze['exact_readback_verified']:
        raise ValueError('Public freeze was not verified')
    if capture.sha(ROOT/'BT_ISOLATED_PLAN.json')!=freeze['plan_sha256']:
        raise ValueError('Plan changed after public freeze')
    if platform.python_version()!=plan['runtime']['python_version'] or capture.sha(sys.executable)!=plan['runtime']['python_executable_sha256']:
        raise ValueError('Runtime differs')
    pins={str(REPO/p['path']):p['sha256'] for p in plan['source_pins']+plan['historical_pins']}
    pins[str(ROOT/'BT_ISOLATED_PLAN.json')]=freeze['plan_sha256']
    pins[str(ROOT/'PUBLIC_FREEZE_RECEIPT_BT.json')]=capture.sha(ROOT/'PUBLIC_FREEZE_RECEIPT_BT.json')
    capture.verify_pins(pins)
    gate=None
    if kind=='a04':
        review_path=ROOT/'review/FIXTURE_REVIEW_BT.json'
        review=json.loads(review_path.read_text())
        fixture_root=ROOT/'execution/BT_ISOLATED_V1/fixture'
        if review['status']!='PASS_ISOLATED_FIXTURE' or review['records_verified']!=90000:
            raise ValueError('Independent fixture review did not qualify')
        if review['terminal_sha256']!=capture.sha(fixture_root/'TERMINAL_BT.json'):
            raise ValueError('Fixture terminal changed after review')
        if review['archive_sha256']!=capture.sha(fixture_root/'payload/EVIDENCE.zip'):
            raise ValueError('Fixture archive changed after review')
        if review['plan_sha256']!=freeze['plan_sha256']:
            raise ValueError('Fixture review belongs to another plan')
        pins[str(review_path)]=capture.sha(review_path)
        pins[str(fixture_root/'TERMINAL_BT.json')]=review['terminal_sha256']
        pins[str(fixture_root/'payload/EVIDENCE.zip')]=review['archive_sha256']
        gate={'path':str(review_path),'sha256':pins[str(review_path)],'status':review['status']}
    return plan,freeze,pins,gate


def archive_semantics(archive_path,result,kind,plan):
    checked=worker.verify_archive(archive_path,result['archive']['members'])
    if checked['bytes']!=result['archive']['bytes'] or checked['sha256']!=result['archive']['sha256']:
        raise ValueError('Exported archive differs from child receipt')
    with zipfile.ZipFile(archive_path) as z:
        expected_names=({'RESULT.json','FILE_MONITOR.json','payload/fixture_0.jsonl','payload/fixture_1.jsonl','BT_SOURCE_INPUT_BINDINGS.json'} if kind=='fixture' else
                        {'ASSESSMENT.json','BT_CLOSURE_CHECK.json','current_associations.jsonl','legacy_associations.jsonl','BT_SOURCE_INPUT_BINDINGS.json'})
        if set(z.namelist())!=expected_names|{'ARCHIVE_MANIFEST.json'}:
            raise ValueError('Unexpected isolated payload members')
        bindings=json.loads(z.read('BT_SOURCE_INPUT_BINDINGS.json'))
        for key in ['source_pins_before','source_pins_after','input_pins_before','input_pins_after',
                    'source_pins_verified_before','source_pins_verified_after','input_pins_verified_before','input_pins_verified_after']:
            if bindings[key]!=result[key]:raise ValueError('Archived bindings differ from worker result')
        for key in ['source_pins_verified_before','source_pins_verified_after','input_pins_verified_before','input_pins_verified_after']:
            if bindings[key] is not True:raise ValueError('A source/input binding check failed')
        if not result['final_pins_verified_after_export'] or result['final_source_pins_after_export']!=bindings['source_pins_before'] or result['final_input_pins_after_export']!=bindings['input_pins_before']:
            raise ValueError('Final export fence changed source/input bindings')
        if kind=='fixture':
            inner=json.loads(z.read('RESULT.json'));monitor=json.loads(z.read('FILE_MONITOR.json'))
            if inner['status']!='PASS' or not monitor['complete'] or monitor['violations']:
                raise ValueError('Fixture monitor or computation failed')
            members={x['path']:x for x in checked['members']}
            for expected in plan['expected_fixture_streams']:
                actual=members['payload/fixture_'+str(expected['stream'])+'.jsonl']
                if actual['bytes']!=expected['bytes'] or actual['sha256']!=expected['sha256']:
                    raise ValueError('Fixture archive differs from prospective expected bytes')
        else:
            inner=json.loads(z.read('ASSESSMENT.json'));closure=json.loads(z.read('BT_CLOSURE_CHECK.json'))
            if inner['status']!='PASS' or closure['effective_status']!='PASS':
                raise ValueError('A04 isolated computation or closure failed')
            members={x['path']:x for x in checked['members']}
            for method,expected in plan['expected_A04_streams'].items():
                item=inner['method_results'][method];declared=item['association_stream']
                actual=members[method+'_associations.jsonl']
                if item['source_ON_hits']!=expected['records'] or declared['records']!=expected['records']:
                    raise ValueError('A04 record count differs')
                if declared['complete'] is not True or declared['bytes']!=expected['bytes'] or declared['sha256']!=expected['sha256'] or actual['sha256']!=expected['sha256'] or actual['bytes']!=expected['bytes']:
                    raise ValueError('A04 exported stream differs from fixed deterministic prediction')
                if item['flags']!=0:
                    raise ValueError('Unexpected A04 flag')
    return checked


def main(kind):
    started=time.monotonic();cpu_started=time.process_time()
    plan,freeze,pins,gate=verified_plan(kind)
    root=ROOT/'execution/BT_ISOLATED_V1';root.mkdir(parents=True,exist_ok=True)
    folder=root/kind;payload=folder/'payload'
    isolated=Path(plan['isolation_root'])/kind
    if isolated.exists():
        raise FileExistsError('Isolated trial already exists')
    caps=plan['caps'][kind]
    receipt=capture.capture_child([sys.executable,str(ROOT/'isolated_worker.py'),'--kind',kind,
        '--output-dir',str(payload),'--isolated-dir',str(isolated)],folder,payload/'RESULT.json',caps,pins,
        context={'identity':'BT_ISOLATED_V1','kind':kind,'public_freeze_commit':freeze['public_commit_sha'],
                 'independent_fixture_gate':gate},poll_seconds=.1,
        group={'storage_roots':[root,Path(plan['isolation_root'])],
               'stored_bytes':plan['phase_storage_cap_bytes'],'rss_bytes':caps['rss_bytes']})
    terminal={'schema':'SETI_BT_CAPTURE_TERMINAL_V1','kind':kind,'status':receipt['status'],
        'capture_status':receipt['status'],'actual_exit_code':receipt['actual_exit_code'],
        'public_freeze_commit':freeze['public_commit_sha'],'plan_sha256':freeze['plan_sha256'],
        'independent_fixture_gate':gate,'errors':[],'archive_verified':False,
        'new_RNG_calls':0,'new_scan_scores':0,'astronomical_powers_opened':0,
        'original_failures_preserved':worker.preserved_statuses()}
    try:
        if receipt['status']!='PASS':raise ValueError('Captured child did not pass')
        if capture.sha(payload/'RESULT.json')!=receipt['result_sha256']:
            raise ValueError('Captured result changed')
        result=json.loads((payload/'RESULT.json').read_text())
        if result['status']!='PASS':raise ValueError('Isolated worker failed')
        terminal['archive_verification']=archive_semantics(payload/'EVIDENCE.zip',result,kind,plan)
        terminal['archive_verified']=True
        capture.verify_pins(pins)
        terminal['source_and_input_pins_verified_after']=True
    except BaseException as exc:
        terminal['status']='FAIL';terminal['errors'].append(type(exc).__name__+': '+str(exc))
    terminal['files']=[dict(path=str(p.relative_to(folder)),bytes=p.stat().st_size,sha256=capture.sha(p))
                       for p in sorted(folder.rglob('*')) if p.is_file()]
    try:
        if terminal['status']!='PASS':raise ValueError('Earlier closure failed')
        entries={x['path']:x for x in terminal['files']}
        if entries['payload/RESULT.json']['sha256']!=receipt['result_sha256']:
            raise ValueError('Final inventory contradicts RESULT')
        a=entries['payload/EVIDENCE.zip'];b=terminal['archive_verification']
        if a['sha256']!=b['sha256'] or a['bytes']!=b['bytes']:
            raise ValueError('Final inventory contradicts exported archive')
        terminal['final_inventory_matches_manifests']=True
    except BaseException as exc:
        terminal['status']='FAIL';terminal['errors'].append(type(exc).__name__+': '+str(exc))
        terminal['final_inventory_matches_manifests']=False
    terminal['wall_seconds_including_parent']=time.monotonic()-started
    terminal['cpu_seconds_including_parent']=time.process_time()-cpu_started+sum(float(receipt['resources'][k] or 0) for k in ['child_user_cpu_seconds','child_system_cpu_seconds'])
    terminal['group_stored_bytes_after_parent']=capture.stored_bytes([root,Path(plan['isolation_root'])])
    if terminal['wall_seconds_including_parent']>caps['wall_seconds'] or terminal['cpu_seconds_including_parent']>caps['cpu_seconds'] or terminal['group_stored_bytes_after_parent']>plan['phase_storage_cap_bytes']:
        terminal['status']='FAIL';terminal['errors'].append('Parent-inclusive resource cap exceeded')
    capture.publish_json(folder/'TERMINAL_BT.json',terminal)
    print(json.dumps(terminal),flush=True)
    return 0 if terminal['status']=='PASS' else 2


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--kind',required=True,choices=['fixture','a04'])
    args=p.parse_args();sys.exit(main(args.kind))
