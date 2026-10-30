"""Fixed deterministic capture fault matrix; no telescope powers/RNG/scores."""
from pathlib import Path
import argparse
import hashlib
import json
import sys

WORK=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(WORK/'src'))
from capture import capture_child, inventory, publish_json, ReservationConflict, sha, verify_pins

CASE_CONTRACT={
    'gate':'E05','engineering_only':True,'real_telescope_powers_authorized':False,
    'rng_authorized':False,'scientific_scores_authorized':False,
    'positive_cases':['valid'],
    'fault_cases':['nonzero','timeout','truncated_stdout','truncated_result','missing_eof','pin_change','existing_output'],
    'fixture_cpu_seconds':2,'fixture_rss_bytes':67108864,'fixture_stored_bytes':4194304,
    'fixture_stdout_limit_bytes':65536,'ordinary_fixture_wall_seconds':2,
    'timeout_fixture_wall_seconds':.35,'missing_eof_fixture_wall_seconds':.40,
    'no_automatic_retry_or_overwrite':True,
}

FIXTURE_SOURCE=r'''from pathlib import Path
import hashlib,json,subprocess,sys,time
mode=sys.argv[1];out=Path(sys.argv[2]);pin=Path(sys.argv[3])
if mode=='timeout':time.sleep(5)
out.mkdir()
value={'status':'PASS','fixture':'BO_E05_FIXED_BYTES_V1','mode':mode}
full=(json.dumps(value,sort_keys=True)+'\n').encode()
(out/'RESULT.json').write_bytes(b'{"status":' if mode=='truncated_result' else full)
if mode=='pin_change':pin.write_bytes(b'AFTER\n')
if mode=='missing_eof':
    subprocess.Popen([sys.executable,'-B','-c','import time; time.sleep(5)'],stdout=sys.stdout,stderr=sys.stderr)
terminal={'event':'GATE_TERMINAL_EOF','status':'PASS','result_sha256':hashlib.sha256(full).hexdigest()}
sys.stdout.write(json.dumps(terminal,sort_keys=True)+('' if mode=='truncated_stdout' else '\n'));sys.stdout.flush()
if mode=='nonzero':sys.exit(7)
'''


def require(value,message):
    if not value:raise ValueError(message)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',required=True,type=Path);parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args();config_path=args.config.resolve();config=json.loads(config_path.read_text())
    require(config['engineering_only'] is True and config['real_telescope_powers_authorized'] is False
            and config['rng_authorized'] is False and config['scientific_scores_authorized'] is False,
            'Engineering-only admission differs')
    out=args.out.resolve()
    require(out==Path(config['gate_outputs']['E05']).resolve(),'Frozen E05 output binding differs')
    frozen={str((WORK/record['path']).resolve()):record['sha256'] for record in config['source_pins']}
    verify_pins(frozen)
    out.mkdir();(out/'cases').mkdir();(out/'pins').mkdir()
    fixture=out/'fixture_child.py'
    with fixture.open('x') as stream:stream.write(FIXTURE_SOURCE)
    expected_source_sha=hashlib.sha256(FIXTURE_SOURCE.encode()).hexdigest()
    require(sha(fixture)==expected_source_sha,'Fixed fixture source differs')
    cases=[]
    for mode in ['valid','nonzero','timeout','truncated_stdout','truncated_result','missing_eof','pin_change']:
        case_parent=out/'cases'/mode;case_parent.mkdir()
        pin=out/'pins'/(mode+'.txt')
        with pin.open('xb') as stream:stream.write(b'BEFORE\n')
        pins={str(fixture):expected_source_sha,str(pin):sha(pin)}
        wall=.35 if mode=='timeout' else .40 if mode=='missing_eof' else 2.
        caps=dict(wall_seconds=wall,cpu_seconds=2,rss_bytes=67108864,stored_bytes=4194304)
        folder=case_parent/'capture';result=folder/'payload/RESULT.json'
        actual=capture_child([sys.executable,'-B',str(fixture),mode,str(result.parent),str(pin)],
            folder,result,caps,pins,dict(gate_id='E05_FIXTURE_'+mode,engineering_only=True),
            stdout_limit=65536,poll_seconds=.01)
        require(actual['actual_exit_code']==(7 if mode=='nonzero' else -9 if mode=='timeout' else 0),
                'Unexpected actual fixture exit: '+mode)
        require(actual['child_wait_completed'] is True and actual['stdout_eof'] is True,
                'Fixture child/pipe did not close: '+mode)
        require(actual['log_sha256']==actual['observed_stdout_sha256']
                and actual['log_bytes']==actual['observed_stdout_bytes'],'Fixture log bytes differ')
        if mode=='valid':
            require(actual['status']=='PASS' and actual['natural_stdout_eof'] is True,'Valid capture refused')
        else:
            require(actual['status']=='FAIL','Fault unexpectedly accepted: '+mode)
            if mode in ['timeout','missing_eof']:
                require(actual['killed'] is True and any('WALL_' in r for r in actual['reasons']),
                        'Deadline fault lacked owned-group cleanup')
            if mode=='missing_eof':require(actual['natural_stdout_eof'] is False,'Held pipe was treated as natural EOF')
            if mode in ['truncated_stdout','truncated_result']:
                require(any(r.startswith('TERMINAL_OR_RESULT_VALIDATION_FAILED') for r in actual['reasons']),
                        'Truncated evidence was not rejected')
            if mode=='pin_change':
                require(actual['source_pins_verified_before'] is True and actual['source_pins_verified_after'] is False
                        and any(r.startswith('POST_CHILD_PIN_FAILURE') for r in actual['reasons']),
                        'Post-child pin change was not rejected')
        receipt_path=folder/'ACTUAL_RECEIPT.json'
        cases.append(dict(case=mode,expected_acceptance=mode=='valid',observed_capture_status=actual['status'],
            actual_exit_code=actual['actual_exit_code'],receipt_path=str(receipt_path),receipt_sha256=sha(receipt_path),
            natural_stdout_eof=actual['natural_stdout_eof'],reasons=actual['reasons']))
    existing=out/'cases/existing_output';existing.mkdir()
    marker=existing/'PRESERVED.bin'
    with marker.open('xb') as stream:stream.write(b'BO_EXISTING_OUTPUT_MUST_STAY_EXACT\n')
    before=inventory(existing);refused=False
    try:
        capture_child([sys.executable,'-B',str(fixture),'valid',str(existing/'payload'),str(out/'unused_pin')],
            existing,existing/'payload/RESULT.json',dict(wall_seconds=2,cpu_seconds=2,rss_bytes=67108864,stored_bytes=4194304),
            {str(fixture):expected_source_sha},dict(gate_id='E05_EXISTING_OUTPUT',engineering_only=True))
    except ReservationConflict:refused=True
    require(refused and inventory(existing)==before,'Existing output reservation was changed or accepted')
    cases.append(dict(case='existing_output',expected_acceptance=False,reservation_refused=True,
                      preexisting_artifact_sha256=before,preexisting_bytes_unchanged=True,child_started=False))
    require(len(cases)==8,'Fixed case count differs')
    verify_pins(frozen)
    result=dict(status='PASS',gate='E05',engineering_only=True,case_contract=CASE_CONTRACT,cases=cases,
        positive_captures=1,expected_fault_rejections=7,raw_telescope_reads=0,rng_draws=0,
        scientific_scores_computed=0,qualification='Deterministic capture/output/resource-protocol engineering only.')
    result_path=out/'RESULT.json';publish_json(result_path,result)
    print(json.dumps(dict(event='GATE_TERMINAL_EOF',status='PASS',result_sha256=sha(result_path)),sort_keys=True),flush=True)


if __name__=='__main__':main()
