#!/usr/bin/env python3
"""Two fixed storage fixtures over archived bytes. No native calculation or RNG."""
import base64
import hashlib
import io
import json
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time
import traceback
from unittest.mock import patch

from seti_repeater import physical_evidence_radio as e
from seti_repeater.empty_null_radio import canonical
from seti_repeater.pipeline_receiver_radio import NativeRun

ROOT=Path(__file__).resolve().parents[1]
BASE='results_radio_physical_evidence_2026-09-29'
OUT=ROOT/BASE
OLD=ROOT/'results_radio_native_chain_engineering_2026-09-29'
COMMIT='43fa09b11c0586c47538d2a8ebfc6060e3d5248e'
SOURCE='live01/partial_physical_or_retention.json'
SOURCE_SHA='6a205b43d53f0a582d73d6d88c1501a0d4d8cd992a974dc8ff6328d300296dfd'
SCOPE='RADIO_PHYSICAL_EVIDENCE_2026-09-29_SCOPE.md'


def write(path,value):e.durable_write(path,canonical(value))


def read_inputs():
    # One immutable Git batch for published metadata; no old calculation runs.
    paths=['results_radio_native_chain_engineering_2026-09-29/archive_manifest.json',
           'results_radio_native_chain_engineering_2026-09-29/plans.json']
    raw=subprocess.check_output(['git','cat-file','--batch'],cwd=ROOT,
        input=''.join(COMMIT+':'+p+'\n' for p in paths).encode())
    off=0;values=[]
    for p in paths:
        end=raw.index(b'\n',off);header=raw[off:end].split();off=end+1
        if len(header)!=3 or header[1]!=b'blob':raise ValueError('Immutable input metadata absent: '+p)
        n=int(header[2]);data=raw[off:off+n];off+=n+1;values.append(json.loads(data))
    if off!=len(raw):raise ValueError('Git batch framing differs')
    manifest,plans=values;inventory={r['path']:r for r in manifest['files']}
    source=(OLD/SOURCE).read_bytes()
    if e.sha(source)!=SOURCE_SHA or len(source)!=14979354 or inventory[SOURCE]['sha256']!=SOURCE_SHA:
        raise ValueError('Exact closed report required')
    existing={}
    for name,row in inventory.items():
        if name.startswith('live01/case4/'):
            data=(OLD/name).read_bytes()
            if len(data)!=row['bytes'] or e.sha(data)!=row['sha256']:raise ValueError('Old artifact pin differs: '+name)
            existing[Path(name).name]=data
    if len(existing)!=7 or sum(map(len,existing.values()))!=2004352:raise ValueError('Complete seven-artifact inventory required')
    return source,json.loads(source),plans[4],existing


def snapshots(source):
    # These are constructed serialization views, not reconstructed historic times.
    d=json.loads(canonical(source));d.pop('failure');d['matched_off']=[];d['adjacent_off']=[]
    yield 'empty_stage_lists',canonical(d)
    stops=list(range(1024,9792,1024))+[9792]
    for n in stops:
        d['matched_off']=source['matched_off'][:n];yield 'matched_off_prefix_'+str(n),canonical(d)
    for n in stops:
        d['adjacent_off']=source['adjacent_off'][:n];yield 'adjacent_off_prefix_'+str(n),canonical(d)
    yield 'original_failed_report',canonical(source)


def main():
    start=time.monotonic();target=OUT/'qualification01';target.mkdir(exist_ok=False)
    results=[];active=None
    def deadline(signum,frame):raise TimeoutError('Fixed byte-fixture deadline')
    signal.signal(signal.SIGALRM,deadline)
    try:
        source_raw,source,plan,existing=read_inputs()
        code_paths=[SCOPE,'src/seti_repeater/physical_evidence_radio.py',
            'src/seti_repeater/whole_cadence_physical_radio.py','src/seti_repeater/native_chain_engineering_radio.py',
            'scripts/radio_physical_evidence_qualification.py','tests/test_radio_physical_evidence.py',
            BASE+'/preflight_tests.log']
        schedule=[{'index':i,'stage':stage,'bytes':len(raw),'sha256':e.sha(raw)} for i,(stage,raw) in enumerate(snapshots(source))]
        if len(schedule)!=22 or schedule[-1]['sha256']!=SOURCE_SHA:raise ValueError('Fixed 22-view schedule differs')
        conf=e.configuration('physical-evidence-qualification-20260929c/representation01',
             plan['case']['identity'],plan['plan_sha256'],existing)
        smaller=e.configuration('physical-evidence-qualification-20260929c/capacity01',
             plan['case']['identity'],plan['plan_sha256'],existing,budget_bytes=16*1024**2)
        fixed={'schema':'radio-physical-evidence-fixed-byte-input-v1','public_source_commit':COMMIT,
               'source_path':SOURCE,'source_bytes':len(source_raw),'source_sha256':SOURCE_SHA,'schedule':schedule,
               'reservation':conf,'smaller_reservation':smaller,'python':sys.version,
               'code_and_scope_sha256s':{p:e.sha((ROOT/p).read_bytes()) for p in code_paths},
               'new_random_values':0,'new_scientific_case_reservations':0,
               'intermediate_views_are_constructed_serialization_fixtures':True}
        write(target/'fixed_before_storage.json',fixed)
        with patch('numpy.random.Generator',side_effect=AssertionError('RNG prohibited')), \
             patch('numpy.random.SeedSequence',side_effect=AssertionError('RNG prohibited')), \
             patch.object(NativeRun,'__init__',side_effect=AssertionError('Native construction prohibited')), \
             patch.object(NativeRun,'build_store',side_effect=AssertionError('Score calculation prohibited')), \
             patch.object(NativeRun,'receiver',side_effect=AssertionError('Receiver replay prohibited')):
            t=time.monotonic();signal.setitimer(signal.ITIMER_REAL,180)
            active=e.Writer.create(target/'representation01',conf,existing_artifacts=existing)
            written=[]
            for i,(stage,raw) in enumerate(snapshots(source)):
                expected=schedule[i]
                if e.sha(raw)!=expected['sha256'] or len(raw)!=expected['bytes']:raise ValueError('Predeclared snapshot differs')
                if i==21:active.close('failed',stage,'historical failed input; representation only',snapshot=json.loads(raw))
                else:active.checkpoint(stage,json.loads(raw))
                written.append(active.receipt())
            stored_seconds=time.monotonic()-t;t2=time.monotonic()
            view=e.inspect(target/'representation01',expected_config_sha256=active.config_sha,
                           expected_last_checkpoint_sha256=active.previous)
            for i,(_,raw) in enumerate(snapshots(source)):
                if view.snapshot(i)!=raw:raise ValueError('Original view not restored exactly')
            row={'name':'representation01','storage_status':'PASS_ALL_22_VIEWS_EXACT',
                 'source_physical_status_still_failed':True,**view.summary(),
                 'footer_bytes':len(view.footer_bytes),'virtual_snapshot_bytes':sum(r['bytes'] for r in schedule),
                 'storage_seconds':stored_seconds,'restore_audit_seconds':time.monotonic()-t2,
                 'total_seconds':time.monotonic()-t,'reservation_sha256':active.config_sha,
                 'incremental_receipts':written}
            results.append(row);write(target/'representation_result.json',row);signal.setitimer(signal.ITIMER_REAL,0)
            active=None;del view,written
            print(json.dumps({k:v for k,v in row.items() if k!='incremental_receipts'}),flush=True)
            t=time.monotonic();signal.setitimer(signal.ITIMER_REAL,180)
            active=e.Writer.create(target/'capacity01',smaller,existing_artifacts=existing)
            first=next(snapshots(source))[1];active.checkpoint('initial',json.loads(first))
            before=e._inventory(active.path)
            try:active.checkpoint('cannot_fit_full_report',source)
            except e.EvidenceCapacity:pass
            else:raise ValueError('Fixed smaller budget unexpectedly accepted full report')
            if e._inventory(active.path)!=before:raise ValueError('Capacity failure wrote extra files')
            failed=active.close('failed','cannot_fit_full_report','expected prospective capacity stop',snapshot=source)
            if failed['final_snapshot_saved'] is not False:raise ValueError('Uncommitted state falsely marked saved')
            view=e.inspect(active.path,expected_config_sha256=active.config_sha,expected_last_checkpoint_sha256=active.previous)
            if len(view.checkpoint_bytes)!=1 or view.snapshot(0)!=first:raise ValueError('Prior committed prefix changed')
            row={'name':'capacity01','storage_status':'PASS_EXPECTED_CAPACITY_REFUSAL',**view.summary(),
                 'footer_bytes':len(view.footer_bytes),'full_snapshot_archived_in_this_store':False,
                 'refused_snapshot_available_in_original_public_archive':True,
                 'total_seconds':time.monotonic()-t,'reservation_sha256':active.config_sha}
            results.append(row);write(target/'capacity_result.json',row);signal.setitimer(signal.ITIMER_REAL,0);active=None
            print(json.dumps(row),flush=True)
        total=time.monotonic()-start;peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        size=sum(p.stat().st_size for p in target.rglob('*') if p.is_file())
        if total>480 or peak>512*1024**2 or size>96*1024**2:raise ValueError('Whole byte-qualification resource bound exceeded')
        result={'schema':'radio-physical-evidence-qualification-result-v1','status':'CLOSED_STORAGE_QUALIFICATION_PASS',
                'fixtures':[{k:v for k,v in r.items() if k!='incremental_receipts'} for r in results],
                'elapsed_seconds':total,'peak_rss_bytes':peak,'new_output_bytes_before_summary':size,
                'new_random_values':0,'new_native_scores':0,'new_physical_decisions':0,'local_git_batch_invocations':1,
                'old_experiment_disposition_changed':False,'scientific_127_24_activated':False,
                'remote_scientific_adapter_qualified':False,'complete_native_physical_run_qualified':False,
                'original_input_bytes_unchanged':(OLD/SOURCE).read_bytes()==source_raw}
        write(target/'result.json',result);print(json.dumps(result,indent=2),flush=True)
    except BaseException as error:
        signal.setitimer(signal.ITIMER_REAL,0);failure={'status':'CLOSED_STORAGE_QUALIFICATION_FAILURE',
            'error':repr(error),'traceback':traceback.format_exc(),'completed_fixtures':results,
            'elapsed_seconds':time.monotonic()-start,'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            'new_random_values':0,'old_experiment_disposition_changed':False,'automatic_retry':False}
        if active is not None and not active.closed:
            try:failure['storage_closure']=active.close('failed','qualification',repr(error))
            except BaseException as nested:failure['closure_error']=repr(nested)
        write(target/'error.json',failure);raise


if __name__=='__main__':main()
