#!/usr/bin/env python3
"""Measure a retained OFFLINE transcript verification replay, independently.

No native case, RNG, SDK, network, Git or tail saver is executed. The original
trace is read only. Fresh scopes exclusively retain code pins, phase checkpoints,
parent procfs/VmHWM observations and an explicit resource acceptance/failure.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import time

SCHEMA = 'radio-native-v2-python-verifier-resource-replay-v1'
REPO = Path(__file__).resolve().parents[1]
DEFAULT_TRACE = Path('/workspace/scratch/f3b7c4d77b54/qualified-courier-offline-full03/caller-result.json')
DEFAULT_RSS = DEFAULT_TRACE.parent/'independent-rss-final.json'
DEFAULT_SCOPE = REPO/'results_radio_native_v2_integrated_control_2026-10-01/verifier_scope01'
LIMITS = {'rss_bytes':512*1024**2,'seconds':600,'case_receipt_storage_bytes':192*1024**2}
AUTHORITY = {'execution_authorized':False,'reservation_authorized':False,
 'scientific_execution_authorized':False,'native_case_executions':0,'scientific_cases_run':0,
 'rng_draws':0,'telescope_reads':0,'actual_functions_sdk_calls':0,'actual_connector_calls':0,
 'network_fetches':0,'real_public_github_mutations':0,'automatic_retry':False}


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


def write_exclusive(path,value):
    payload=value if isinstance(value,bytes) else canonical(value)+b'\n'
    with Path(path).open('xb') as stream:
        stream.write(payload);stream.flush();os.fsync(stream.fileno())


def file_pin(path):
    digest=hashlib.sha256();count=0
    with Path(path).open('rb') as stream:
        while True:
            block=stream.read(65536)
            if not block:break
            count+=len(block);digest.update(block)
    return {'bytes':count,'sha256':digest.hexdigest()}


def proc_memory(pid):
    fields={}
    for line in (Path('/proc')/str(pid)/'status').read_text().splitlines():
        if ':' in line:
            key,value=line.split(':',1);fields[key]=value.strip()
    return {'at_epoch_ms':time.time_ns()//1000000,'rss_bytes':int(fields.get('VmRSS','0 kB').split()[0])*1024,
      'kernel_vm_hwm_bytes':int(fields.get('VmHWM','0 kB').split()[0])*1024}


def inventory(root):
    rows=[]
    for path in sorted(Path(root).rglob('*')):
        if path.is_file():
            stat=path.stat();rows.append({'path':str(path.relative_to(root)),'bytes':stat.st_size,'allocated_bytes':stat.st_blocks*512})
    return {'files':len(rows),'logical_bytes':sum(r['bytes'] for r in rows),
      'allocated_bytes':sum(r['allocated_bytes'] for r in rows),'rows':rows}


def replay_retained_contract(trace,rss_path,contract,*,bounded=False,checkpoint=lambda phase:None):
    """Verify exact retained envelopes while controlling unnecessary custody.

    The bounded path calls the unchanged full validators and append/receipt
    APIs. It discards append's unused defensive-copy return, computes the small
    bindings, then releases the original parse before obtaining the full receipt.
    No evidence field or validation is omitted; only duplicate object lifetimes
    and an avoidable full-file checksum buffer change.
    """
    checkpoint('before_full_transcript_parse')
    value=json.loads(Path(trace).read_bytes());rss=json.loads(Path(rss_path).read_bytes())
    checkpoint('after_full_transcript_parse')
    ledger=contract.RunTranscript();case=None;error=None
    try:
        if bounded:
            ledger.append(0,value['qualified']['client'],value['qualified']['persistence'],
              client_peak_rss_bytes=rss['client_peak_rss_bytes'])
        else:
            case=ledger.append(0,value['qualified']['client'],value['qualified']['persistence'],
              client_peak_rss_bytes=rss['client_peak_rss_bytes'])
    except BaseException as failure:
        error=repr(failure)
    checkpoint('after_full_run_transcript_append')
    if bounded:
        client_binding=contract.client_binding_sha256(value['qualified']['client'])
        tail_binding=hashlib.sha256(contract.caller_tail_payload(value['qualified']['client'])).hexdigest()
        del value
        checkpoint('original_full_parse_released_before_receipt')
    receipt=ledger.receipt()
    checkpoint('after_full_run_transcript_receipt')
    result={'schema':SCHEMA,'mode':'NON_SCIENTIFIC_RETAINED_OFFLINE_VERIFICATION_REPLAY',
      'verification_mode':'BOUNDED_OBJECT_CUSTODY' if bounded else 'ORIGINAL_HELPER_OBJECT_CUSTODY',
      'contract_status':'PASSED' if error is None else 'CLOSED_FAILED','error':error,
      'run_transcript_stopped':ledger.stopped,'case_count':receipt['case_count'],'receipt_status':receipt['status'],
      'calls':receipt['calls'],'request_bytes':receipt['request_bytes'],'response_bytes':receipt['response_bytes'],
      'shared_case_elapsed_seconds':receipt['elapsed_seconds'],'one_case_replayed_only':True,
      'eight_case_verification_complete':False,**AUTHORITY}
    if bounded:
        result.update(client_binding_sha256=client_binding,caller_tail_payload_sha256=tail_binding,
          retained_transcript_sha256=file_pin(trace)['sha256'])
    else:
        result.update(client_binding_sha256=contract.client_binding_sha256(value['qualified']['client']),
          caller_tail_payload_sha256=hashlib.sha256(contract.caller_tail_payload(value['qualified']['client'])).hexdigest(),
          retained_transcript_sha256=hashlib.sha256(Path(trace).read_bytes()).hexdigest())
    checkpoint('after_original_checksum_and_binding_stages')
    return result


def verify_worker(scope,trace,rss_path,mode='original'):
    scope=Path(scope);sys.path.insert(0,str(scope/'frozen-code/src'))
    started=time.monotonic();proc_pid=int(os.readlink('/proc/self'))
    write_exclusive(scope/'worker-identity.json',{'proc_pid':proc_pid,'namespace_pid':os.getpid(),
      'identity':'python-proc:'+str(proc_pid),'started_at_epoch_ms':time.time_ns()//1000000})
    checkpoint_file=(scope/'worker-checkpoints.jsonl').open('xb',buffering=0)
    def checkpoint(phase):
        row={'phase':phase,'elapsed_seconds':time.monotonic()-started,**proc_memory(proc_pid),
          'python_resource_usage_max_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
        checkpoint_file.write(canonical(row)+b'\n');os.fsync(checkpoint_file.fileno())
    try:
        checkpoint('before_contract_import')
        from seti_repeater import native_v2_transport_contract_radio as contract
        result=replay_retained_contract(trace,rss_path,contract,bounded=mode=='bounded',checkpoint=checkpoint)
        result['python_resource_usage_max_rss_bytes']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        result['elapsed_seconds']=time.monotonic()-started
        write_exclusive(scope/'worker-result.json',result)
        checkpoint('worker_result_durable')
    finally:
        checkpoint_file.close()


def run_resource_fixture(scope,trace=DEFAULT_TRACE,rss_path=DEFAULT_RSS,*,mode="original",contract_code_root=None):
    scope=Path(scope).absolute();trace=Path(trace).absolute();rss_path=Path(rss_path).absolute()
    scope.mkdir(mode=0o700,parents=True,exist_ok=False)
    started=time.monotonic();pins={}
    files=('scripts/radio_native_v2_python_verifier_resource_fixture.py',
      'src/seti_repeater/__init__.py','src/seti_repeater/empty_null_radio.py',
      'src/seti_repeater/native_v2_transport_contract_radio.py')
    for relative in files:
        source=(REPO if relative.startswith('scripts/') else Path(contract_code_root or REPO))/relative
        destination=scope/'frozen-code'/relative
        destination.parent.mkdir(parents=True,exist_ok=True);raw=source.read_bytes();write_exclusive(destination,raw)
        pins[relative]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    trace_pin=file_pin(trace);rss_pin=file_pin(rss_path)
    write_exclusive(scope/'prospective-replay-pins.json',{'schema':SCHEMA,'code':pins,
      'retained_trace':{'path':str(trace),**trace_pin},'retained_caller_rss':{'path':str(rss_path),**rss_pin},
      'original_limits':LIMITS,'verification_mode':mode,
      'contract_snapshot_source':str(Path(contract_code_root or REPO).absolute()),
      'python_runtime':{'invocation':sys.executable,'resolved':str(Path(sys.executable).resolve()),
        'version':sys.version,**file_pin(Path(sys.executable).resolve())},'replay_only':True,**AUTHORITY})
    stdout=(scope/'worker-stdout.log').open('xb');stderr=(scope/'worker-stderr.log').open('xb')
    observed_start=time.time_ns()//1000000
    child=subprocess.Popen([sys.executable,'-I','-S','-B',str(scope/'frozen-code/scripts/radio_native_v2_python_verifier_resource_fixture.py'),
      '--worker',str(scope),str(trace),str(rss_path),mode],stdout=stdout,stderr=stderr,
      env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'})
    proc_pid=None;samples=[];peak_rss=0;peak_hwm=0;deadline_failure=None
    try:
        while child.poll() is None:
            identity_path=scope/'worker-identity.json'
            if proc_pid is None and identity_path.exists():proc_pid=json.loads(identity_path.read_bytes())['proc_pid']
            if proc_pid is not None:
                try:
                    row=proc_memory(proc_pid);samples.append(row);peak_rss=max(peak_rss,row['rss_bytes']);peak_hwm=max(peak_hwm,row['kernel_vm_hwm_bytes'])
                except (FileNotFoundError,ProcessLookupError):pass
            if time.time_ns()//1000000-observed_start>LIMITS['seconds']*1000:
                deadline_failure='Original 600-second verifier replay interval exceeded';child.kill()
            time.sleep(0.005)
        exit_code=child.wait()
    finally:stdout.close();stderr.close()
    observed_end=time.time_ns()//1000000
    observation={'schema':'radio-native-v2-independent-python-verifier-rss-v1',
      'observer_source':'independent_parent_procfs','observer_runtime_identity':'python-proc:'+os.readlink('/proc/self'),
      'verifier_runtime_identity':'python-proc:'+str(proc_pid),'interval_start_epoch_ms':observed_start,
      'interval_end_epoch_ms':observed_end,'sample_count':len(samples),'sampled_peak_rss_bytes':peak_rss,
      'kernel_vm_hwm_bytes':peak_hwm,'verifier_peak_rss_bytes':max(peak_rss,peak_hwm),
      'includes_transcript_parse_append_receipt_and_child_termination':True,'exit_code':exit_code,'samples':samples}
    write_exclusive(scope/'independent-rss-observation.json',observation)
    worker_result=json.loads((scope/'worker-result.json').read_bytes()) if (scope/'worker-result.json').exists() else None
    storage=inventory(scope);failures=[]
    measured=max(peak_rss,peak_hwm,(worker_result or {}).get('python_resource_usage_max_rss_bytes',0))
    if measured<=0:failures.append('Python verifier RSS remained unmeasured')
    if measured>LIMITS['rss_bytes']:failures.append('Original 512MiB Python verifier RSS cap exceeded')
    if (observed_end-observed_start)/1000>LIMITS['seconds']:failures.append('Original 600-second Python verifier cap exceeded')
    if storage['logical_bytes']+trace_pin['bytes']>LIMITS['case_receipt_storage_bytes'] or storage['allocated_bytes']+trace.stat().st_blocks*512>LIMITS['case_receipt_storage_bytes']:
        failures.append('Original 192MiB case receipt storage cap exceeded including retained input')
    if exit_code!=0 or worker_result is None or worker_result['contract_status']!='PASSED':failures.append('Complete Python replay contract verification failed')
    result={'schema':SCHEMA,'mode':'NON_SCIENTIFIC_RETAINED_OFFLINE_VERIFICATION_REPLAY',
      'status':'PASSED' if not failures and not deadline_failure else 'CLOSED_FAILED','failures':failures,
      'deadline_failure':deadline_failure,'independent_observation':{k:v for k,v in observation.items() if k!='samples'},
      'worker_result':worker_result,'storage_before_summary':storage,
      'storage_with_preexisting_readonly_input':{'logical_bytes':storage['logical_bytes']+trace_pin['bytes'],
        'allocated_bytes':storage['allocated_bytes']+trace.stat().st_blocks*512},'original_limits':LIMITS,
      'elapsed_seconds':time.monotonic()-started,'replayed_source':'retained offline_full03 original caller trace',
      'original_full03_scope_unchanged':True,'no_old_scope_resume':True,'reconstruction_verification_only':True,**AUTHORITY}
    write_exclusive(scope/'measured-summary.json',result)
    write_exclusive(scope/'storage-inventory.json',{'scope':inventory(scope),'inventory_file_itself_excluded':True})
    return result


def self_test():
    """Small semantic regressions; complete maximum-size RSS is measured separately."""
    import tempfile
    import unittest
    sys.path.insert(0,str(REPO/'src'));sys.path.insert(0,str(REPO/'tests'))
    from seti_repeater import native_v2_transport_contract_radio as contract
    from test_radio_native_v2_transport_contract import client,persistence
    class ReplayTests(unittest.TestCase):
        def run_fixture(self,mutate=None):
            value=client(polls=0,source_reads=2);proof=persistence(value)
            if mutate:mutate(value,proof)
            with tempfile.TemporaryDirectory(prefix='seti-verifier-semantic-') as directory:
                trace=Path(directory)/'trace.json';rss=Path(directory)/'rss.json'
                write_exclusive(trace,{'qualified':{'client':value,'persistence':proof}})
                write_exclusive(rss,{'client_peak_rss_bytes':1024*1024})
                original=replay_retained_contract(trace,rss,contract,bounded=False)
                bounded=replay_retained_contract(trace,rss,contract,bounded=True)
                for result in (original,bounded):
                    self.assertEqual(result['retained_transcript_sha256'],file_pin(trace)['sha256'])
                comparable=lambda r:{k:v for k,v in r.items() if k!='verification_mode'}
                self.assertEqual(comparable(original),comparable(bounded))
                self.assertLess(len(canonical(bounded)),4096)
                return bounded
        def test_exact_contract_results_and_bindings_are_preserved(self):
            result=self.run_fixture();self.assertEqual(result['contract_status'],'PASSED')
            self.assertEqual(result['case_count'],1);self.assertEqual(result['receipt_status'],'INCOMPLETE')
            self.assertFalse(result['execution_authorized']);self.assertEqual(result['scientific_cases_run'],0)
        def test_changed_raw_envelope_remains_closed_failed(self):
            result=self.run_fixture(lambda value,proof:value['records'][0]['raw_result'].update(ok=False))
            self.assertEqual(result['contract_status'],'CLOSED_FAILED');self.assertTrue(result['run_transcript_stopped'])
            self.assertEqual(result['case_count'],0);self.assertIn('raw caller result',result['error'])
        def test_changed_tail_readback_remains_closed_failed(self):
            result=self.run_fixture(lambda value,proof:proof.update(durable=False))
            self.assertEqual(result['contract_status'],'CLOSED_FAILED');self.assertTrue(result['run_transcript_stopped'])
            self.assertEqual(result['case_count'],0);self.assertIn('tail persistence',result['error'])
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(ReplayTests)
    outcome=unittest.TextTestRunner(verbosity=2).run(suite)
    if not outcome.wasSuccessful():raise SystemExit(1)


def main():
    if len(sys.argv)>1 and sys.argv[1]=='--worker':
        if len(sys.argv)!=6:raise ValueError('Exact worker scope/trace/RSS/mode arguments required')
        verify_worker(*sys.argv[2:]);return
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--scope',type=Path,default=DEFAULT_SCOPE)
    parser.add_argument('--trace',type=Path,default=DEFAULT_TRACE);parser.add_argument('--caller-rss',type=Path,default=DEFAULT_RSS)
    parser.add_argument('--mode',choices=('original','bounded'),default='original')
    parser.add_argument('--self-test',action='store_true')
    parser.add_argument('--contract-code-root',type=Path)
    args=parser.parse_args()
    if args.self_test:return self_test()
    result=run_resource_fixture(args.scope,args.trace,args.caller_rss,mode=args.mode,contract_code_root=args.contract_code_root)
    print(json.dumps({'status':result['status'],'failures':result['failures'],
      'independent_peak_rss_bytes':result['independent_observation']['verifier_peak_rss_bytes'],
      'resource_max_rss_bytes':(result['worker_result'] or {}).get('python_resource_usage_max_rss_bytes'),
      'summary_path':str(args.scope/'measured-summary.json')},sort_keys=True))


if __name__=='__main__':main()
