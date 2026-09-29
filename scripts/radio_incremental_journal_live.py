"""Exactly one two-namespace engineering publication exercise; no RNG or spectra."""
import argparse
import json
from pathlib import Path
import resource
import subprocess
import sys
import time
import traceback

from seti_repeater import whole_cadence_incremental_radio as r
from seti_repeater import whole_cadence_journal_radio as j
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_reference_radio import digest
from seti_repeater.whole_cadence_runtime_radio import PublishedFreeze
from radio_batch_handoff import FileRPC, publish

ROOT = Path(__file__).resolve().parents[1]
RECIPE = r.ROOT+'/recipe.json'
FREEZE = r.ROOT+'/runtime_freeze.json'


def definitions(freeze_sha256, recipe, prefix):
    binding = {k:digest({'namespace':prefix,'recipe':digest(recipe),'field':k})
               for k in j.BINDING_KEYS if k != 'role'}
    binding['role'] = 'engineering'
    return canonical(j.genesis({'schema':j.SCHEMA,'mode':'engineering','namespace':prefix,
        'execution_binding_sha256':freeze_sha256, 'allocation_sha256':digest(recipe),
        'cases':[binding], 'caps':{**j.CAPS,'active_milliseconds':120000,
            'evidence_bytes':131072,'ledger_reserve_bytes':r.LEDGER_CAP},
        'required_artifacts':['witness.json']}))


def consume_event(raw, nonce):
    return {'kind':'consume','binding':json.loads(raw)['manifest']['cases'][0],
            'milliseconds':120000,'artifact_bytes':r.ARTIFACT_CAP,'nonce':nonce}


def main():
    p=argparse.ArgumentParser();p.add_argument('--commit',required=True)
    p.add_argument('--freeze-sha256',required=True);p.add_argument('--rpc',required=True)
    p.add_argument('--output',required=True);args=p.parse_args()
    started=time.monotonic();out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    rpc=FileRPC(args.rpc);meter=r.Meter();client=r.Client(rpc,meter=meter);sessions=[]
    result={'schema':'radio-incremental-live-result-v1','mode':'ENGINEERING_ONLY',
        'scientific_execution_authorized':False,'source_requests':0,'telescope_values':0,
        'rng_constructions':0,'scientific_allocations':0,'automatic_retries':0,
        'freeze_commit':args.commit,'freeze_sha256':args.freeze_sha256,
        'prior_scopes_unchanged':True}
    try:
        recipe=json.loads((ROOT/RECIPE).read_bytes())
        frozen=PublishedFreeze(ROOT,args.commit,FREEZE,args.freeze_sha256)
        bridge={'mode':'engineering','execution_binding_sha256':args.freeze_sha256}
        verify=lambda:frozen.verify(bridge)
        result['execution_preflight']=verify()
        raws=[definitions(args.freeze_sha256,recipe,prefix) for prefix in r.PREFIXES]
        for prefix,raw in zip(r.PREFIXES,raws,strict=True):
            for name,data in (('genesis.json',raw),('head.json',r.initial(raw).head)):
                published=subprocess.check_output(['git','show',args.commit+':'+prefix+'/'+name],cwd=ROOT)
                if data!=published:raise ValueError('Independently derived public genesis/pointer differs')

        normal=r.Session(client,r.PREFIXES[0],raws[0],freeze_commit=args.commit,execution_verifier=verify)
        sessions.append(normal);normal.begin();nonce=recipe['nonces'][0]
        normal.append(consume_event(raws[0],nonce))
        payload=canonical(recipe['witness'])
        if recipe['witness_sha256']!=r.sha(payload):raise ValueError('Frozen witness bytes differ')
        normal.append({'kind':'artifact','nonce':nonce,'name':'witness.json',
                       'size':len(payload),'sha256':r.sha(payload)},artifact=payload)
        normal.append({'kind':'finish','nonce':nonce,'outcome':'completed',
                       'elapsed_milliseconds':int((meter.clock()-normal.started)*1000),
                       'reason':'Fixed incremental durable storage witness'})
        reader=r.Reader(client.readonly_recovery(),r.PREFIXES[0],r.sha(raws[0]))
        history=reader.read(normal.head,expected_pointer_sha256=r.sha(normal.history.head))
        artifacts=reader.verify_artifacts(normal.head,history)
        if list(artifacts.values())!=[payload] or history.summary()['states']!=['completed']:
            raise ValueError('Complete-case external evidence differs')
        result['complete01']={'commit':normal.head,**history.summary(),
            'artifact_bytes':sum(map(len,artifacts.values())),
            'end_to_end_seconds':meter.clock()-normal.started}

        lost=r.Session(client,r.PREFIXES[1],raws[1],freeze_commit=args.commit,execution_verifier=verify)
        sessions.append(lost);lost.begin()
        try:
            lost.append(consume_event(raws[1],recipe['nonces'][1]),lose_acknowledgement=True)
            raise AssertionError('Injected acknowledgement loss did not stop')
        except OSError as error:
            if str(error)!='Injected loss of successful update response at session boundary':raise
            result['injected_failure']=repr(error)
        if not lost.stopped:raise ValueError('Uncertain session retained write authority')
        receipt=next(x for x in reversed(lost.receipts) if x.get('phase')=='injected_acknowledgement_loss')
        recovery_client=client.readonly_recovery()
        reader=r.Reader(recovery_client,r.PREFIXES[1],r.sha(raws[1]))
        actual_head=reader._head()
        if actual_head!=receipt['candidate']:raise ValueError('Recovery branch differs from immutable candidate')
        history=reader.read(actual_head,expected_pointer_sha256=receipt['expected_pointer_sha256'])
        if history.summary()['states']!=['consumed'] or reader.verify_artifacts(actual_head,history):
            raise ValueError('Incomplete consumed state was lost or gained artifacts')
        if hasattr(history,'append') or hasattr(history,'begin_gaussian') or not recovery_client.read_only:
            raise ValueError('Recovery gained execution authority')
        result['lost01']={'commit':actual_head,**history.summary(),'writer_stopped':True,
            'read_only_recovery':True,'artifact_bytes':0,'no_resume_attempted':True,
            'fault_boundary':'successful tool response suppressed before writer acknowledgement',
            'end_to_end_seconds':meter.clock()-lost.started}
        result['execution_postflight']=verify()
        result['status']='CLOSED_ENGINEERING_PASS'
    except BaseException as error:
        result.update(status='CLOSED_ENGINEERING_FAILED',error=repr(error),traceback=traceback.format_exc(),
                      automatic_retry=False,consumed_cases_must_not_restart=True)
    result.update(elapsed_seconds=time.monotonic()-started,transport=meter.summary(),
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        publication_receipts=[s.receipts for s in sessions],
        actual_live_branch_advances=sum(x.get('phase') in ('immutable_bytes_verified','injected_acknowledgement_loss')
                                       for s in sessions for x in s.receipts),
        both_namespaces_closed=True,scientific_127_24_status='NOT_ACTIVATED')
    if result['elapsed_seconds']>600 or result['peak_rss_bytes']>512*1024**2:
        result['status']='CLOSED_ENGINEERING_FAILED';result['resource_limit_exceeded']=True
    publish(out/'transport_receipts.json',meter.events)
    publish(out/'result.json',result)
    summary={k:result[k] for k in ('status','elapsed_seconds','transport','actual_live_branch_advances')}
    publish(rpc.path/'done.json',summary);print(json.dumps(summary),flush=True)
    return 0 if result['status']=='CLOSED_ENGINEERING_PASS' else 1


if __name__=='__main__':sys.exit(main())
