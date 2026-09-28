"""Single preregistered live publication case; tool transport via bounded file RPC.

No credentials, direct network requests, astronomical arrays, PRNG or scientific
allocation. A supervising caller executes only the five pinned GitHub methods.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time
import traceback
from seti_repeater import whole_cadence_remote_radio as r
from seti_repeater import whole_cadence_journal_radio as j
from seti_repeater.whole_cadence_reference_radio import digest
from seti_repeater.whole_cadence_runtime_radio import PublishedFreeze
from seti_repeater.empty_null_radio import canonical

ROOT=Path(__file__).resolve().parents[1]
RECIPE='config/radio_whole_cadence_remote_recipe02_20260928.json'
FREEZE='config/radio_whole_cadence_remote_runtime02_20260928.json'
SPEC='config/radio_whole_cadence_remote_store02_20260928.json'


def definitions(freeze_sha,recipe):
    sha=lambda label:digest({'namespace':recipe['namespace'],'label':label})
    m={'schema':j.SCHEMA,'mode':'engineering','namespace':recipe['namespace'],
        'execution_binding_sha256':freeze_sha,'allocation_sha256':digest(recipe),
        'cases':[{k:sha(k) for k in j.BINDING_KEYS if k!='role'}|{'role':'engineering'}],
        'caps':{**j.CAPS,'active_milliseconds':1800000,'evidence_bytes':32*1024**2,'ledger_reserve_bytes':1024**2},
        'required_artifacts':['witness.json','payload.bin']}
    spec={'schema':'radio-whole-cadence-github-store-v1','mode':'engineering','repository':r.REPO,
        'branch':r.BRANCH,'prefix':r.PREFIX,'manifest_sha256':digest(m),'genesis_sha256':digest(j.genesis(m)),
        'case_reservations':[{'case_identity':m['cases'][0]['case_identity'],
            'milliseconds':recipe['case_milliseconds'],'artifact_bytes':recipe['case_artifact_bytes']}]}
    return m,spec


class FileRPC:
    def __init__(self,path):
        self.path=Path(path);self.path.mkdir(parents=True,exist_ok=False);self.sequence=0

    def __call__(self,method,params):
        self.sequence+=1;n=self.sequence
        j.durable_write(self.path/f'request{n:04d}.json',canonical({'id':n,'method':method,'params':params}))
        print('RPC',n,flush=True);target=self.path/f'response{n:04d}.json';started=time.monotonic()
        while not target.exists():
            if time.monotonic()-started>120:raise TimeoutError('GitHub tool response absent; stop without retry')
            time.sleep(.025)
        reply=json.loads(target.read_bytes())
        if reply.get('id')!=n or reply.get('ok') is not True:raise RuntimeError('Tool broker error: '+str(reply.get('error')))
        return reply['result']


def main():
    p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--freeze-sha256',required=True)
    p.add_argument('--rpc',required=True);p.add_argument('--output',required=True);args=p.parse_args()
    output=Path(args.output);output.mkdir(parents=True,exist_ok=False)
    started=time.monotonic();client=None;store=None;lease=None
    result={'mode':'ENGINEERING_ONLY','scientific_execution_authorized':False,
        'source_requests':0,'proposed_prng_constructions':0,'scientific_allocations':0,'scope_retries':0,'attempt':'live02','prior_failed_attempt':'live01'}
    try:
        freeze=PublishedFreeze(ROOT,args.commit,FREEZE,args.freeze_sha256)
        recipe=json.loads((ROOT/RECIPE).read_bytes());m,spec=definitions(args.freeze_sha256,recipe)
        raw=(ROOT/SPEC).read_bytes()
        if raw!=canonical(spec):raise ValueError('Published store differs from independently derived recipe/freeze')
        result['execution_preflight']=freeze.verify(m)
        if any((ROOT/x).read_bytes()!=__import__('subprocess').check_output(['git','show',args.commit+':'+x],cwd=ROOT)
                for x in (SPEC,r.PREFIX+'/ledger.json')):raise ValueError('Published specification/genesis differs')
        client=r.Client(FileRPC(args.rpc),prior_usage=recipe['prior_usage']);store=r.GitStore(client,raw,hashlib.sha256(raw).hexdigest(),execution_verifier=freeze.verify)
        cp=store.read()
        if cp.document!=j.genesis(m):raise ValueError('Fresh genesis required; no resume or reset')
        quota=spec['case_reservations'][0]
        lease=j.consume(store,expected_revision=cp.revision,expected_manifest_sha256=digest(m),binding=m['cases'][0],
            milliseconds=quota['milliseconds'],artifact_bytes=quota['artifact_bytes'],directory=output/'case')
        witness=canonical(recipe['witness']);payload=bytes((i*17+23)%256 for i in range(262161))
        for name,data in (('witness.json',witness),('payload.bin',payload)):
            if hashlib.sha256(data).hexdigest()!=recipe['artifacts'][name]['sha256'] or len(data)!=recipe['artifacts'][name]['bytes']:
                raise ValueError('Fixed artifact recipe changed')
            lease.write_artifact(name,data)
        final=lease.finish()
        # A new store discards ALL object caches; the same bounded client keeps
        # cumulative requests, bytes and transport time charged.
        fresh=r.GitStore(client,raw,hashlib.sha256(raw).hexdigest(),execution_verifier=freeze.verify)
        remote=fresh.read()
        if remote!=final:raise ValueError('Independent final checkpoint differs')
        fresh.verify_completed_evidence(remote)
        result.update(status='PASS_ENGINEERING_ONLY',final_checkpoint=remote.document,final_ledger_blob=remote.revision,
            final_branch_head=fresh.last_head,external_artifacts_read_with_fresh_object_cache=True,
            archive=j.verify_archive(remote,output/'case',case_index=0))
        before=client.calls
        try:
            j.append(remote.document,{'kind':'consume','binding':m['cases'][0],
                'milliseconds':quota['milliseconds'],'artifact_bytes':quota['artifact_bytes'],
                'nonce':'00000000-0000-4000-8000-000000000001'})
        except ValueError as error:result['closed_case_reconsumption_rejected']=str(error)
        else:raise AssertionError('Closed case unexpectedly admitted')
        result['reconsumption_check_tool_calls']=client.calls-before
        result['execution_postflight']=freeze.verify(m)
    except BaseException as error:
        result.update(status='STOPPED_ENGINEERING',error=repr(error),traceback=traceback.format_exc(),
            automatic_retry=False,consumed_case_must_not_restart=True)
    result.update(elapsed_seconds=time.monotonic()-started,cumulative_elapsed_seconds=time.monotonic()-started+60,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        publication_receipts=[] if store is None else store.receipts,
        tool_calls=0 if client is None else client.calls,returned_json_bytes=0 if client is None else client.response_bytes,
        completion_event_excludes_its_own_future_publication_latency=True,
        complete_transport_and_finalization_time_in_elapsed_seconds=True)
    if result['cumulative_elapsed_seconds']>1800 or result['peak_rss_bytes']>512*1024**2:
        result['status']='STOPPED_ENGINEERING';result['resource_limit_exceeded']=True
    if client:j.durable_write(output/'transport_receipts.json',canonical(client.events))
    j.durable_write(output/'result.json',canonical(result))
    print(json.dumps({k:result[k] for k in ('status','elapsed_seconds','tool_calls','returned_json_bytes')}),flush=True)
    return 0 if result['status']=='PASS_ENGINEERING_ONLY' else 1

if __name__=='__main__':sys.exit(main())
