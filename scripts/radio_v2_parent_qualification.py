#!/usr/bin/env python3
"""One publicly frozen v2/event parent byte integration, never a native rerun."""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import resource
import signal
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from seti_repeater import physical_case_v2_radio as p
from seti_repeater import physical_evidence_v2_radio as e
from seti_repeater import whole_cadence_event_store_radio as s
from seti_repeater import whole_cadence_journal_radio as j
from seti_repeater.empty_null_radio import canonical
from radio_physical_evidence_v2_qualification import load_sources

OUT=ROOT/'results_radio_v2_parent_2026-09-30'
NAMESPACE='radio-v2-event-parent-20260930a'
CASE_CAP=18*1024**2
CODE_PATHS=['src/seti_repeater/physical_case_v2_radio.py',
    'src/seti_repeater/physical_evidence_v2_radio.py',
    'src/seti_repeater/physical_evidence_radio.py',
    'src/seti_repeater/whole_cadence_journal_radio.py',
    'src/seti_repeater/whole_cadence_event_store_radio.py',
    'src/seti_repeater/empty_null_radio.py',
    'src/seti_repeater/whole_cadence_reference_radio.py',
    'scripts/radio_v2_parent_qualification.py',
    'scripts/radio_physical_evidence_v2_qualification.py',
    'scripts/radio_receiver_evidence_capacity.py',
    'scripts/radio_v2_parent_remote.py',
    'scripts/radio_lossless_handoff.py',
    'scripts/radio_v2_parent_handoff.py',
    'scripts/radio_v2_parent_broker.js',
    'src/seti_repeater/event_archive_remote_radio.py',
    'tests/test_radio_physical_case_v2.py',
    'tests/test_radio_event_archive_remote.py']

def sha(data):return hashlib.sha256(data).hexdigest()

def save(path,value):
    with path.open('xb') as f:f.write(canonical(value))

def contract(pins):
    code={name:sha((ROOT/name).read_bytes()) for name in CODE_PATHS}
    recipe={'pair_repetitions':[1,20,20],'source_status':'FAILED/incomplete',
        'existing_artifacts':'all seven immutable original files, exact bytes',
        'source_report_and_profile_files':'exact original UTF-8 including whitespace and LF',
        'footer':'failed','closure':'seal failed physical evidence and failed parent',
        'remote':'separate bounded atomic snapshot archive; not an automatic scientific publisher'}
    case_id=sha((NAMESPACE+'/case1').encode())
    plan_id=sha(canonical({'namespace':NAMESPACE,'sources':pins,'recipe':recipe}))
    binding={'case_identity':case_id,'plan_sha256':plan_id,
        'context_sha256':sha(canonical(pins)),
        'source_contract_sha256':sha(canonical({'exact_original_bytes':pins})),
        'noise_law_sha256':sha(b'byte-only-no-random-values'),'role':'engineering'}
    config=e._config({'schema':e.SCHEMA,'namespace':NAMESPACE,'case_identity':case_id,
        'plan_sha256':plan_id,'engineering_only':True,'budget_bytes':CASE_CAP-sum(p.CLOSURE_RESERVES.values()),
        'footer_reserve_bytes':e.FOOTER_RESERVE,'part_bytes':e.PART_BYTES,
        'rows_per_group':e.ROWS_PER_GROUP,'checkpoint_limit':3,
        'existing_artifacts':pins['existing_artifacts'],
        'logical_value_limit_bytes':e.MAX_VALUE_BYTES,'logical_snapshot_limit_bytes':e.MAX_SNAPSHOT_BYTES})
    manifest={'schema':j.SCHEMA,'mode':'engineering','namespace':NAMESPACE,
        'execution_binding_sha256':sha(canonical(code)),
        'allocation_sha256':sha(canonical({'namespace':NAMESPACE,'case_bytes':CASE_CAP,'milliseconds':180000})),
        'cases':[binding],'caps':{**j.CAPS,'active_milliseconds':180000,'evidence_bytes':32*1024**2},
        'required_artifacts':[*sorted(pins['existing_artifacts']),p.SEAL,p.OUTCOME],
        'artifact_groups':p.policy(config)}
    j.validate_manifest(manifest)
    return {'schema':'radio-v2-event-parent-byte-freeze-v1','namespace':NAMESPACE,
        'engineering_only':True,'manifest':manifest,'physical_config':config,
        'sources':pins,'code_sha256':code,'recipe':recipe,
        'project_python_sha256':{str(path.relative_to(ROOT)):sha(path.read_bytes())
            for path in sorted((ROOT/'src').rglob('*.py'))},
        'caps':{'case_bytes':CASE_CAP,'journal_bytes':8*1024**2,'active_seconds':180,
            'peak_rss_bytes':512*1024**2,'whole_local_seconds':240,'checkpoints':3},
        'runtime':{'python':sys.version,'executable_sha256':sha(Path(sys.executable).read_bytes())},
        'stop_rule':'One exclusive parent consumption; any failure remains spent; no retry/replacement.',
        'new_random_values':0,'new_receiver_measurements':0,'new_telescope_reads':0,
        'historical_cases_reexecuted':False,'scientific_127_24_activated':False}

def run(receipt_path):
    started=time.monotonic();freeze_raw=(OUT/'freeze.json').read_bytes();freeze=json.loads(freeze_raw)
    receipt=json.loads(receipt_path.read_bytes())
    if (canonical(freeze)!=freeze_raw or receipt.get('verified') is not True
            or receipt.get('freeze_sha256')!=sha(freeze_raw)):
        raise ValueError('Independent public freeze verification required before consumption')
    def expired(signum,frame):raise TimeoutError('Frozen 240-second local integration alarm')
    signal.signal(signal.SIGALRM,expired);signal.alarm(240)
    target=OUT/'integration01';target.mkdir(exist_ok=False)
    case=None;lease=None
    try:
        if any(name in sys.modules for name in ('seti_repeater.pipeline_radio',
                'seti_repeater.pipeline_receiver_radio','seti_repeater.whole_cadence_physical_radio')):
            raise ValueError('Native modules forbidden in byte worker')
        import numpy as np
        with ExitStack() as guards:
            for name in ('default_rng','RandomState','seed','random','random_sample','rand','randn',
                    'normal','standard_normal','uniform','randint','choice','permutation','shuffle'):
                guards.enter_context(patch.object(np.random,name,side_effect=AssertionError('RNG forbidden')))
            source,base,pairs,pins,texts=load_sources()
            if freeze!=contract(pins):raise ValueError('Frozen code, input, runtime or recipe changed')
            if json.loads(source)['complete'] is not False:raise ValueError('Original failure must remain incomplete')
            store=s.EventDirectoryStore.create(target/'journal',freeze['manifest']);cp=store.read()
            lease=j.consume(store,expected_revision=cp.revision,
                expected_manifest_sha256=sha(canonical(freeze['manifest'])),
                binding=freeze['manifest']['cases'][0],milliseconds=180000,
                artifact_bytes=CASE_CAP,directory=target/'case')
            for name,data in base.items():lease.write_artifact(name,data)
            case=p.PhysicalCase(lease,freeze['physical_config'],existing_artifacts=base)
            expected=[];timings=[]
            for index,repetitions in enumerate((1,20,20)):
                t=time.monotonic()
                doc={'retention':{'case_identity':freeze['physical_config']['case_identity']},
                    'complete':False,'archived_partial_report_utf8':source.decode('utf-8'),
                    'original_software_profile_files_utf8':texts,'software_receiver_outputs':pairs*repetitions}
                raw=canonical(doc);expected.append({'bytes':len(raw),'sha256':sha(raw),'pair_count':len(pairs)*repetitions});del raw
                if index==2:case.writer.close('failed','retained-incomplete-source',
                    'Archived-byte integration only; historical source remains failed.',snapshot=doc)
                else:case.writer.checkpoint('byte-load-'+str(index),doc)
                del doc
                timings.append(time.monotonic()-t)
                print(json.dumps({'checkpoint':index,'logical':expected[-1],'receipt':case.writer.receipt()}),flush=True)
            cp=case.finish(reason='Archived source and parent remain failed; exact storage integration only.')
            view,check=p.inspect_case(cp,lease.directory)
            for index,row in enumerate(expected):
                h=hashlib.sha256();size=0
                for piece in view.iter_snapshot(index):h.update(piece);size+=len(piece)
                if h.hexdigest()!=row['sha256'] or size!=row['bytes']:
                    raise ValueError('Complete original snapshot stream differs')
            head=(store.path/'HEAD').read_text().strip()
            history=s.read_history(store.path,expected_genesis_sha256=store.genesis_sha256,
                expected_pointer_sha256=head)
            for index,raw in enumerate(history.revision_bytes):
                original={**cp.document,'events':cp.document['events'][:index]}
                if raw!=canonical(original):raise ValueError('Original journal revision differs')
            if len(history.revision_bytes)!=len(cp.document['events'])+1:
                raise ValueError('Incomplete journal version history')
            if check['status']!='failed' or view.summary()['status']!='failed':
                raise ValueError('Original failed evidence relabelled')
            elapsed=time.monotonic()-started;rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
            journal_bytes=history.summary()['stored_bytes']
            case_elapsed=j.replay(cp.document)['cases'][-1]['elapsed_milliseconds']
            if (check['artifact_bytes']>CASE_CAP or journal_bytes>8*1024**2
                    or case_elapsed>180000 or elapsed>240 or rss>512*1024**2):
                raise ValueError('Frozen integration capacity exceeded')
            result={'schema':'radio-v2-event-parent-byte-result-v1','status':'LOCAL_PARENT_EVENT_BYTE_PASS',
                'freeze_sha256':sha(freeze_raw),'public_freeze_commit':receipt['commit'],
                'source_physical_status':'failed','parent_case_status':'failed',
                'restored_snapshots':expected,'case':check,'journal':history.summary(),
                'journal_versions':len(history.revision_bytes),'journal_genesis_sha256':store.genesis_sha256,
                'journal_pointer_sha256':head,'physical_config_sha256':case.writer.config_sha,
                'physical_last_checkpoint_sha256':case.writer.previous,
                'registered_case_plus_journal_bytes':check['artifact_bytes']+journal_bytes,
                'snapshot_write_seconds':timings,'local_worker_seconds':elapsed,'peak_rss_bytes':rss,
                'case_elapsed_milliseconds':case_elapsed,
                'runtime_remote_publication_qualified':False,'remote_archive_status':'PENDING',
                'new_random_values':0,'new_receiver_measurements':0,'new_telescope_reads':0,
                'scientific_127_24_activated':False,'historical_cases_reexecuted':False}
            save(target/'result.json',result)
            print(json.dumps(result,sort_keys=True,indent=2),flush=True)
    except BaseException as error:
        failure={'status':'LOCAL_PARENT_EVENT_BYTE_FAILED','error':repr(error),'no_retry':True,
            'freeze_sha256':sha(freeze_raw),'elapsed_seconds':time.monotonic()-started}
        if case is not None and not case.closed:
            try:failure['closure']=case.fail(error)
            except BaseException as nested:failure['closure_error']=repr(nested)
        elif lease is not None and not lease.closed and not lease.broken:
            try:lease.finish('failed',repr(error)[:4096])
            except BaseException as nested:failure['closure_error']=repr(nested)
        save(target/'failed.json',failure);raise
    finally:signal.alarm(0)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--freeze',action='store_true')
    parser.add_argument('--receipt',type=Path);args=parser.parse_args()
    if args.freeze:
        OUT.mkdir(exist_ok=True);_,_,_,pins,_=load_sources();save(OUT/'freeze.json',contract(pins))
        print(sha((OUT/'freeze.json').read_bytes()))
    else:
        if args.receipt is None:parser.error('--receipt is required')
        run(args.receipt)
