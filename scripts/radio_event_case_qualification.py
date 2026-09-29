#!/usr/bin/env python3
"""One exclusive parent-allocation fixture over retained public report bytes."""
import json
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import traceback
from unittest.mock import patch

from seti_repeater import physical_case_radio as p
from seti_repeater import whole_cadence_event_store_radio as event_store
from seti_repeater import physical_evidence_radio as e
from seti_repeater import whole_cadence_journal_radio as j
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_reference_radio import digest
from seti_repeater.pipeline_receiver_radio import NativeRun
from radio_physical_evidence_qualification import snapshots

ROOT=Path(__file__).resolve().parents[1]
BASE='results_radio_event_case_2026-09-29'
OUT=ROOT/BASE
NAMESPACE='radio-event-case-integration-20260929e'
SOURCE_COMMIT='43fa09b11c0586c47538d2a8ebfc6060e3d5248e'
STORAGE_COMMIT='165cefc141e56ddbb4739652ca109234feb9c863'


def write(path,value):j.durable_write(path,canonical(value))


def inputs():
    paths=[SOURCE_COMMIT+':results_radio_native_chain_engineering_2026-09-29/'+n for n in ('archive_manifest.json','plans.json')]
    paths.append(STORAGE_COMMIT+':results_radio_physical_evidence_2026-09-29/qualification01/fixed_before_storage.json')
    raw=subprocess.check_output(['git','cat-file','--batch'],cwd=ROOT,input=''.join(n+'\n' for n in paths).encode())
    values=[];off=0
    for path in paths:
        end=raw.index(b'\n',off);header=raw[off:end].split();off=end+1
        if len(header)!=3 or header[1]!=b'blob':raise ValueError('Immutable metadata absent: '+path)
        size=int(header[2]);values.append(json.loads(raw[off:off+size]));off+=size+1
    if off!=len(raw):raise ValueError('Git framing differs')
    archive,plans,fixed=values;old=ROOT/'results_radio_native_chain_engineering_2026-09-29'
    source=(old/'live01/partial_physical_or_retention.json').read_bytes()
    if len(source)!=fixed['source_bytes'] or e.sha(source)!=fixed['source_sha256']:
        raise ValueError('Closed source report differs')
    base={}
    for row in archive['files']:
        if row['path'].startswith('live01/case4/'):
            data=(old/row['path']).read_bytes()
            if len(data)!=row['bytes'] or e.sha(data)!=row['sha256']:raise ValueError('Closed base artifact differs')
            base[Path(row['path']).name]=data
    if len(base)!=7 or sum(map(len,base.values()))!=2004352:raise ValueError('Exact seven original artifacts required')
    return source,base,plans[4],fixed['schedule']


def main():
    started=time.monotonic();target=OUT/'integration01';target.mkdir(exist_ok=False)
    case=None;lease=None;store=None
    def deadline(signum,frame):raise TimeoutError('Fixed parent byte-fixture deadline')
    signal.signal(signal.SIGALRM,deadline);signal.setitimer(signal.ITIMER_REAL,240)
    try:
        source,base,old_plan,schedule=inputs();document=json.loads(source)
        config=e.configuration(NAMESPACE+'/source-evidence',old_plan['case']['identity'],old_plan['plan_sha256'],base,
            budget_bytes=24*1024**2-sum(p.CLOSURE_RESERVES.values()))
        binding={'case_identity':digest({'namespace':NAMESPACE,'case':'integration01','not_a_signal_case':True}),
            'plan_sha256':digest({'namespace':NAMESPACE,'source_sha256':e.sha(source),'physical_config':config}),
            'context_sha256':old_plan['case']['context_sha256'],
            'source_contract_sha256':old_plan['case']['source_contract_sha256'],
            'noise_law_sha256':digest({'domain':'retained-byte-serialization-only','random_values':0}),'role':'engineering'}
        assert binding['case_identity']!=config['case_identity']
        manifest={'schema':j.SCHEMA,'mode':'engineering','namespace':NAMESPACE,
            'execution_binding_sha256':digest({'source_commit':SOURCE_COMMIT,'schedule_commit':STORAGE_COMMIT}),
            'allocation_sha256':digest({'namespace':NAMESPACE,'case':binding,'case_bytes':24*1024**2,'milliseconds':180000}),
            'cases':[binding],'caps':{**j.CAPS,'active_milliseconds':180000,'evidence_bytes':32*1024**2},
            'required_artifacts':[*base,p.SEAL,p.OUTCOME],'artifact_groups':p.policy(config)}
        j.validate_manifest(manifest)
        names=['RADIO_EVENT_CASE_2026-09-29_SCOPE.md','src/seti_repeater/whole_cadence_event_store_radio.py','src/seti_repeater/whole_cadence_journal_radio.py',
            'src/seti_repeater/physical_evidence_radio.py','src/seti_repeater/physical_case_radio.py',
            'src/seti_repeater/empty_null_radio.py','src/seti_repeater/whole_cadence_reference_radio.py',
            'scripts/radio_event_case_qualification.py','scripts/radio_physical_evidence_qualification.py',
            'tests/test_radio_event_store.py','tests/test_radio_physical_case.py',BASE+'/preflight01.log']
        fixed={'namespace':NAMESPACE,'manifest':manifest,'physical_config':config,'schedule':schedule,
            'source_commit':SOURCE_COMMIT,'schedule_commit':STORAGE_COMMIT,'source_sha256':e.sha(source),
            'source_bytes':len(source),'source_identity_is_provenance_not_new_reservation':True,
            'code_scope_test_sha256s':{n:e.sha((ROOT/n).read_bytes()) for n in names},'python':sys.version,
            'case_byte_cap':24*1024**2,'case_milliseconds':180000,'whole_seconds':240,
            'new_random_values':0,'new_native_scores':0,'new_physical_decisions':0}
        write(target/'fixed_before_consumption.json',fixed)
        with patch('numpy.random.Generator',side_effect=AssertionError('RNG forbidden')), \
             patch('numpy.random.SeedSequence',side_effect=AssertionError('RNG forbidden')), \
             patch.object(NativeRun,'__init__',side_effect=AssertionError('Native construction forbidden')), \
             patch.object(NativeRun,'build_store',side_effect=AssertionError('Scoring forbidden')), \
             patch.object(NativeRun,'receiver',side_effect=AssertionError('Receiver forbidden')):
            store=event_store.EventDirectoryStore.create(target/'journal',manifest);cp=store.read()
            lease=j.consume(store,expected_revision=cp.revision,expected_manifest_sha256=digest(manifest),
                binding=binding,milliseconds=180000,artifact_bytes=24*1024**2,directory=target/'case')
            for name,data in base.items():lease.write_artifact(name,data)
            case=p.PhysicalCase(lease,config,existing_artifacts=base)
            t=time.monotonic()
            for index,(stage,raw) in enumerate(snapshots(document)):
                expected=schedule[index]
                if len(raw)!=expected['bytes'] or e.sha(raw)!=expected['sha256']:raise ValueError('Fixed view differs')
                if index==21:case.writer.close('failed',stage,'historical failed input; byte storage only',snapshot=json.loads(raw))
                else:case.writer.checkpoint(stage,json.loads(raw))
            cp=case.finish(reason='source physical outcome remains failed; storage fixture only')
            storage_seconds=time.monotonic()-t;t=time.monotonic()
            view,check=p.inspect_case(cp,lease.directory)
            for row in schedule:
                raw=view.snapshot(row['index'])
                if len(raw)!=row['bytes'] or e.sha(raw)!=row['sha256']:raise ValueError('Restored view differs')
            head=(target/'journal/HEAD').read_text().strip()
            recovered=event_store.read_history(target/'journal',expected_genesis_sha256=store.genesis_sha256,expected_pointer_sha256=head)
            history=[]
            for index,raw in enumerate(recovered.revision_bytes):
                doc=json.loads(raw);j.replay(doc)
                if len(doc['events'])!=index or doc['events']!=cp.document['events'][:index]:
                    raise ValueError('Original journal revision differs from exact final prefix')
                history.append({'revision':e.sha(raw),'bytes':len(raw),'events':index})
            if recovered.revision_bytes[-1]!=canonical(cp.document) or len(history)!=len(cp.document['events'])+1:
                raise ValueError('Complete event journal history missing')
            ledger_bytes=sum(x.stat().st_size for x in (target/'journal').rglob('*') if x.is_file())
            all_bytes=sum(x.stat().st_size for x in target.rglob('*') if x.is_file())
            peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024;total=time.monotonic()-started
            if ledger_bytes>8*1024**2 or check['artifact_bytes']>24*1024**2 or all_bytes>40*1024**2 or peak>512*1024**2 or total>240:
                raise ValueError('Fixed whole integration budget exceeded')
            if check['status']!='failed' or view.summary()['status']!='failed':raise ValueError('Historical failure incorrectly relabelled')
            result={'schema':'radio-event-case-integration-result-v1','status':'CLOSED_EVENT_BYTE_INTEGRATION_PASS',
                'parent_case_status':'failed','source_physical_status':'failed','restored_views':len(schedule),
                'archive_check':check,'journal_versions':len(history),'journal_history_bytes':ledger_bytes,'event_history':recovered.summary(),
                'registered_case_plus_journal_bytes':check['artifact_bytes']+ledger_bytes,
                'outer_footer_bytes':(lease.directory/p.OUTCOME).stat().st_size,
                'physical_footer_bytes':len(view.footer_bytes),'seal_bytes':(lease.directory/p.SEAL).stat().st_size,
                'storage_and_parent_closure_seconds':storage_seconds,'restore_and_history_audit_seconds':time.monotonic()-t,
                'whole_seconds':total,'case_elapsed_milliseconds':j.replay(cp.document)['cases'][0]['elapsed_milliseconds'],
                'peak_rss_bytes':peak,'total_fixture_bytes_before_result':all_bytes,'immutable_input_git_batch_calls':1,
                'new_random_values':0,'new_native_scores':0,'new_physical_decisions':0,
                'new_engineering_storage_cases':1,'old_case_identity_reused_for_execution':False,
                'remote_adapter_qualified':False,'scientific_127_24_activated':False,
                'history':history,'last_journal_revision':cp.revision,
                'physical_config_sha256':case.writer.config_sha,'last_physical_checkpoint_sha256':case.writer.previous}
            write(target/'result.json',result)
            print(json.dumps({k:v for k,v in result.items() if k!='history'},indent=2),flush=True)
        signal.setitimer(signal.ITIMER_REAL,0)
    except BaseException as error:
        signal.setitimer(signal.ITIMER_REAL,0)
        failure={'status':'CLOSED_EVENT_BYTE_INTEGRATION_FAILURE','error':repr(error)[:4096],
            'traceback':traceback.format_exc()[-12000:],'whole_seconds':time.monotonic()-started,
            'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'new_random_values':0,'automatic_retry':False,'large_failure_dump_written':False}
        if case is not None and not case.closed:
            try:failure['closure']=case.fail(error)
            except BaseException as nested:failure['closure_error']=repr(nested)[:2048]
        elif lease is not None and not lease.closed and not lease.broken:
            try:lease.finish('failed',repr(error)[:4096])
            except BaseException as nested:failure['closure_error']=repr(nested)[:2048]
        if store is not None:
            failure['case_and_journal_bytes']=sum(x.stat().st_size for x in target.rglob('*') if x.is_file())
        raw=canonical(failure)
        if len(raw)>65536:raise RuntimeError('Bounded failure record exceeded') from error
        j.durable_write(target/'failure.json',raw);raise


if __name__=='__main__':main()
