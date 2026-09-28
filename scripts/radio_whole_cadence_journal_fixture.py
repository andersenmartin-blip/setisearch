#!/usr/bin/env python3
"""Fresh deterministic crash fixtures; every durable state retained in one tar."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time
import traceback
from seti_repeater import whole_cadence_journal_radio as j
from seti_repeater.whole_cadence_reference_radio import digest
from seti_repeater.empty_null_radio import canonical

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_radio_whole_cadence_journal_2026-09-28/crash01'
MODES=('before_consume','after_consume','partial_artifact','after_artifact','after_finish_commit','complete')


def manifest(name):
    sha=lambda label:digest({'namespace':'journal-crash-fixture-20260928','scenario':name,'label':label})
    return {'schema':j.SCHEMA,'mode':'engineering','namespace':'journal-crash-fixture-20260928/'+name,
        'execution_binding_sha256':sha('code'),'allocation_sha256':sha('engineering-allocation'),
        'cases':[{'case_identity':sha(str(i)),'plan_sha256':sha('plan'+str(i)),
            'context_sha256':sha('context'),'source_contract_sha256':sha('source'),
            'noise_law_sha256':sha('no-rng-law'),'role':'engineering'} for i in range(2)],
        'caps':{**j.CAPS,'active_milliseconds':60000,'evidence_bytes':1048576,'ledger_reserve_bytes':65536},
        'required_artifacts':['result.json']}


def worker(mode):
    root=OUT/mode;store=j.DirectoryStore(root/'store');c=store.read();m=c.document['manifest']
    if mode=='before_consume':os._exit(17)
    class ExitAfterFinish:
        def read(self):return store.read()
        def publish(self,expected,document):
            store.publish(expected,document)
            if document['events'][-1]['event']['kind']=='finish':os._exit(17)
    target=ExitAfterFinish() if mode=='after_finish_commit' else store
    lease=j.consume(target,expected_revision=c.revision,expected_manifest_sha256=digest(m),
        binding=m['cases'][0],milliseconds=20000,artifact_bytes=1024,directory=root/'artifacts')
    if mode=='after_consume':os._exit(17)
    if mode=='partial_artifact':
        j.durable_write(root/'artifacts/result.json',b'{"partial":');os._exit(17)
    lease.write_artifact('result.json',canonical({'engineering':True,'rng_calls':0}))
    if mode=='after_artifact':os._exit(17)
    lease.finish();return 0


def main():
    started=time.monotonic();OUT.mkdir(exist_ok=False)
    summaries=[]
    try:
        (OUT/'fixed_scenarios.json').write_bytes(canonical({'scenarios':MODES,'expected_crash_exit_code':17,
            'scientific_cases':0,'proposed_generators_called':False}))
        for mode in MODES:
            root=OUT/mode;root.mkdir();m=manifest(mode);store=j.DirectoryStore.create(root/'store',m)
            process=subprocess.run([sys.executable,__file__,'--worker',mode],cwd=ROOT,capture_output=True)
            (root/'process.log').write_bytes(process.stdout+process.stderr)
            expected=0 if mode=='complete' else 17
            if process.returncode!=expected:raise ValueError('Unexpected worker exit: '+mode)
            c=store.read();state=j.replay(c.document)
            entry={'scenario':mode,'process_returncode':process.returncode,'events':len(c.document['events']),
                'case_consumptions':len(state['cases']),'reserved_milliseconds':state['reserved_milliseconds'],
                'reserved_artifact_bytes':state['reserved_artifact_bytes'],'head':c.revision}
            if mode=='before_consume':
                if state['cases']:raise ValueError('Crash before consumption spent a case')
                entry['next_unconsumed_case_available']=True
            else:
                if len(state['cases'])!=1:raise ValueError('Consumed case count differs')
                case=state['cases'][0];entry['status']=case['status']
                try:entry['archive']=j.verify_archive(c,root/'artifacts',case_index=0)
                except ValueError as error:
                    if mode!='partial_artifact':raise
                    entry['archive_rejection']=str(error)
                complete=mode in ('after_finish_commit','complete')
                if (case['status']=='completed')!=complete:raise ValueError('Crash state wrongly completed')
                try:
                    j.consume(store,expected_revision=c.revision,expected_manifest_sha256=digest(m),binding=m['cases'][0],
                        milliseconds=20000,artifact_bytes=1024,directory=root/'forbidden-replay')
                except ValueError as error:entry['same_case_replay_rejected']=str(error)
                else:raise ValueError('Crash enabled duplicate execution')
                if not complete:
                    try:
                        j.consume(store,expected_revision=c.revision,expected_manifest_sha256=digest(m),binding=m['cases'][1],
                            milliseconds=20000,artifact_bytes=1024,directory=root/'forbidden-next')
                    except ValueError as error:entry['incomplete_attempt_next_case_rejected']=str(error)
                    else:raise ValueError('Incomplete attempt continued')
            summaries.append(entry)
        # Preserve all six original stores, revision histories and partial bytes.
        archive=OUT/'crash_stores.tar.gz'
        with tarfile.open(archive,'x:gz') as tar:
            for mode in MODES:tar.add(OUT/mode,arcname=mode)
        result={'schema':'radio-whole-cadence-consumption-crash-result-v1','status':'SIX_CRASH_BOUNDARIES_PASS',
            'scenarios':summaries,'real_process_terminations':5,'retries_of_consumed_cases':0,
            'scientific_allocations':0,'gaussian_values':0,'source_requests':0,
            'active_seconds':time.monotonic()-started,'local_engineering_store_only':True,
            'remote_scientific_adapter_qualified':False}
        (OUT/'result.json').write_bytes(canonical(result));print(json.dumps(result,indent=2))
    except BaseException as error:
        (OUT/'error.json').write_bytes(canonical({'error':repr(error),'traceback':traceback.format_exc(),'automatic_retry_authorized':False}));raise


if __name__=='__main__':
    if len(sys.argv)==3 and sys.argv[1]=='--worker':sys.exit(worker(sys.argv[2]))
    main()
