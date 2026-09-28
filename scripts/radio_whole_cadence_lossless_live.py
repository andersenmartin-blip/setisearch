"""Two fresh fixed engineering witnesses; no source data or statistical RNG."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import time
import traceback
from seti_repeater import whole_cadence_lossless_radio as r
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_reference_radio import digest
from seti_repeater.whole_cadence_runtime_radio import PublishedFreeze
from radio_lossless_handoff import FileRPC,publish
ROOT=Path(__file__).resolve().parents[1]
RECIPE='config/radio_whole_cadence_lossless_recipe_20260928.json'
FREEZE='config/radio_whole_cadence_lossless_runtime_20260928.json'

def definitions(freeze_sha,recipe):
    return r.validate_manifest({'schema':r.SCHEMA,'mode':'ENGINEERING_ONLY','namespace':r.PREFIX,
        'execution_binding_sha256':freeze_sha,'recipe_sha256':digest(recipe),
        'cases':[{'ordinal':i,'case_identity':digest({'namespace':r.PREFIX,'recipe':digest(recipe),'ordinal':i}),
            'milliseconds':(300000,120000)[i],'physical_bytes':(1048576,256)[i],'failure_bytes':8192,
            'required_artifacts':(['witness.json','payload.bin'],['capacity_probe.bin'])[i]} for i in range(2)]})

def main():
    p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--freeze-sha256',required=True)
    p.add_argument('--rpc',required=True);p.add_argument('--output',required=True);p.add_argument('--prior',required=True);a=p.parse_args()
    started=time.monotonic();output=Path(a.output);output.mkdir(parents=True,exist_ok=False)
    rpc=FileRPC(a.rpc);client=None;store=None
    result={'mode':'ENGINEERING_ONLY','scientific_execution_authorized':False,'source_requests':0,
        'proposed_prng_constructions':0,'scientific_allocations':0,'scope_retries':0,'attempt':'lossless-live01'}
    try:
        recipe=json.loads((ROOT/RECIPE).read_bytes());m=definitions(a.freeze_sha256,recipe)
        freeze=PublishedFreeze(ROOT,a.commit,FREEZE,a.freeze_sha256)
        bridge={'mode':'engineering','execution_binding_sha256':a.freeze_sha256}
        result['execution_preflight']=freeze.verify(bridge)
        genesis=canonical(r.genesis(m))
        if subprocess.check_output(['git','show',a.commit+':'+r.PREFIX+'/ledger.json'],cwd=ROOT)!=genesis:
            raise ValueError('Independently derived genesis differs from immutable publication')
        prior=json.loads(Path(a.prior).read_bytes())
        client=r.Client(rpc,prior_usage=prior);store=r.Store(client,m,execution_verifier=freeze.verify)
        cp,_=store.read()
        if cp!=r.genesis(m):raise ValueError('Fresh genesis required; no resume or reset')
        cp,case,_=store.consume(0);work=time.monotonic()
        payloads={'witness.json':canonical(recipe['witness']),'payload.bin':bytes((i*29+11)%256 for i in range(524305))}
        for name,data in payloads.items():
            if recipe['artifacts'][name]!={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}:
                raise ValueError('Pinned deterministic artifact recipe differs')
        doc=store.seal(cp,payloads,'archived','Fixed lossless transport witness',int((time.monotonic()-work)*1000))
        cp,case,_=store.consume(1);work=time.monotonic()
        try:r.pack(case,{'capacity_probe.bin':b'x'*1024},'archived')
        except ValueError as error:
            failure=canonical({'schema':'radio-lossless-bounded-failure-v1','case_identity':case['case_identity'],
                'failure':'physical_normal_quota_exceeded','raw_attempted_bytes':1024,'normal_physical_cap':256,
                'normal_bytes_published':0,'separate_failure_cap':8192,'error':str(error),'not_EMPTY':True})
        else:raise AssertionError('Prospective capacity probe unexpectedly passed')
        doc=store.seal(cp,{'failure.json':failure},'failed','Expected normal-capacity refusal; bounded failure evidence',
            int((time.monotonic()-work)*1000))
        fresh=r.Store(client,m,execution_verifier=freeze.verify);remote,_=fresh.read()
        if remote!=doc:raise ValueError('Independent final journal differs')
        restored=fresh.read_archives(remote,fresh.last_head)
        expected={m['cases'][0]['case_identity']+'/'+k:v for k,v in payloads.items()}
        expected[m['cases'][1]['case_identity']+'/failure.json']=failure
        if restored!=expected:raise ValueError('Fresh external archive raw byte comparison differs')
        state=r.replay(remote)
        if [c['status'] for c in state['cases']]!=['archived','failed']:raise ValueError('Fixed case outcomes differ')
        result.update(status='PASS_ENGINEERING_EXPECTED_FAILURE_RETAINED',final_checkpoint=remote,
            final_branch_head=fresh.last_head,accounting=state,external_artifacts_read_with_fresh_object_cache=True,
            raw_artifacts={k:{'bytes':len(v),'sha256':hashlib.sha256(v).hexdigest()} for k,v in restored.items()},
            execution_postflight=freeze.verify(bridge))
    except BaseException as error:
        result.update(status='STOPPED_ENGINEERING',error=repr(error),traceback=traceback.format_exc(),
            automatic_retry=False,consumed_cases_must_not_restart=True)
    elapsed=time.monotonic()-started
    result.update(elapsed_seconds=elapsed,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        publication_receipts=[] if store is None else store.receipts,case_timings=[] if store is None else store.case_timings,
        tool_calls=0 if client is None else client.calls,returned_json_bytes=0 if client is None else client.response_bytes,
        cumulative_active_seconds=elapsed+(0 if client is None else prior['seconds']),
        prior_scope_usage=None if client is None else prior,completion_seal_excludes_future_publication_latency=True,
        complete_transport_and_finalization_time_in_elapsed_seconds=True)
    if result['cumulative_active_seconds']>900 or result['peak_rss_bytes']>512*1024**2:
        result['status']='STOPPED_ENGINEERING';result['resource_limit_exceeded']=True
    if client:publish(output/'transport_receipts.json',client.events)
    publish(output/'result.json',result)
    summary={k:result[k] for k in ('status','elapsed_seconds','tool_calls','returned_json_bytes')}
    publish(rpc.path/'done.json',summary);print(json.dumps(summary),flush=True)
    return 0 if result['status']=='PASS_ENGINEERING_EXPECTED_FAILURE_RETAINED' else 1

if __name__=='__main__':sys.exit(main())
