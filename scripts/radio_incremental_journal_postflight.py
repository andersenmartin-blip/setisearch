"""Independent downstream Git/JSON/byte audit of the closed incremental live run.

Uses only stdlib and Git, not the publisher, reader, journal or codec modules.
No live service mutation, RNG, lease reconstruction or experiment replay.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess


def canonical(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--rpc',required=True)
    p.add_argument('--output',required=True);args=p.parse_args()
    repo=Path(__file__).resolve().parents[1]
    prefix='results_radio_incremental_journal_2026-09-29'
    result=json.loads((repo/prefix/'run01/result.json').read_bytes())
    transport=json.loads((repo/prefix/'run01/transport_receipts.json').read_bytes())
    def git(*args):return subprocess.check_output(['git',*args],cwd=repo)
    def blob(commit,path):return git('show',commit+':'+path)
    freeze=result['freeze_commit'];reports=[];receipts=[]
    for items in result['publication_receipts']:
        receipts += [x for x in items if 'phase' in x]
    assert len(receipts)==4
    parent=freeze
    for rec in receipts:
        commit=rec['candidate'];assert rec['parent']==parent
        assert git('show','-s','--format=%P',commit).decode().strip()==parent
        assert git('show','-s','--format=%T',commit).decode().strip()==rec['tree']
        actual=set(git('diff','--name-only',parent,commit).decode().splitlines())
        assert actual==set(rec['files'])
        size=0
        for name,expected_git_sha in rec['files'].items():
            raw=blob(commit,name);size+=len(raw)
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==expected_git_sha
        assert size==rec['publication_bytes']
        parent=commit
    assert git('rev-list','--reverse',freeze+'..'+parent).decode().splitlines()==[r['candidate'] for r in receipts]

    for short,expected_events in [('complete01',['consume','artifact','finish']),('lost01',['consume'])]:
        summary=result[short];commit=summary['commit'];ns=prefix+'/'+short
        raw=blob(commit,ns+'/genesis.json');doc=json.loads(raw)
        assert canonical(doc)==raw and not doc['events'] and doc['manifest']['mode']=='engineering'
        assert doc['manifest_sha256']==sha(canonical(doc['manifest']))
        assert len(doc['manifest']['cases'])==1
        genesis=raw;revisions=[raw];chunk_sizes=[];artifact_total=0
        pointer_commits=[freeze]+[r['candidate'] for r in receipts if any(k.startswith(ns+'/') for k in r['files'])]
        pointer_sizes=[len(blob(c,ns+'/head.json')) for c in pointer_commits]
        previous_event='0'*64;previous_chunk='0'*64
        nonce=None;seen_artifacts={};expected_names={'genesis.json','head.json'}
        for index,kind in enumerate(expected_events):
            name=f'events/{index:04d}.json';expected_names.add(name)
            raw=blob(commit,ns+'/'+name);rec=json.loads(raw);assert canonical(rec)==raw
            assert rec['index']==index and rec['previous_chunk_sha256']==previous_chunk
            assert rec['before_sha256']==sha(canonical(doc))
            row=rec['record'];event=row['event']
            assert row['index']==index and row['previous']==previous_event
            assert row['sha256']==sha(canonical({k:v for k,v in row.items() if k!='sha256'}))
            assert event['kind']==kind
            if kind=='consume':
                assert event['binding']==doc['manifest']['cases'][0]
                assert event['milliseconds']==120000 and event['artifact_bytes']==4096
                nonce=event['nonce']
            else:
                assert event['nonce']==nonce
                if kind=='artifact':
                    name='artifacts/'+doc['manifest']['cases'][0]['case_identity']+'/'+event['name']
                    expected_names.add(name);payload=blob(commit,ns+'/'+name)
                    assert len(payload)==event['size'] and sha(payload)==event['sha256']
                    seen_artifacts[event['name']]=payload;artifact_total+=len(payload)
                else:
                    assert event['outcome']=='completed'
                    assert set(seen_artifacts)==set(doc['manifest']['required_artifacts'])
                    assert 0<=event['elapsed_milliseconds']<=120000
            doc['events'].append(row);after=canonical(doc)
            assert len(after)==rec['after_bytes'] and sha(after)==rec['after_sha256']
            revisions.append(after);chunk_sizes.append(len(raw))
            previous_event=row['sha256'];previous_chunk=sha(raw)
            pointer=json.loads(blob(pointer_commits[index+1],ns+'/head.json'))
            assert pointer=={'schema':rec['schema'],'genesis_sha256':sha(genesis),
                'event_count':index+1,'last_chunk_sha256':previous_chunk,
                'revision_sha256':sha(after),'revision_bytes':len(after),
                'restoration_only':True,'execution_restart_authorized':False}
        actual=set(git('ls-tree','-r','--name-only',commit,'--',ns).decode().splitlines())
        assert actual=={ns+'/'+x for x in expected_names}
        assert [sha(x) for x in revisions]==summary['revision_sha256s']
        assert list(map(len,revisions))==summary['revision_bytes']
        ledger=len(genesis)+sum(chunk_sizes)+sum(pointer_sizes)
        assert ledger==summary['ledger_bytes'] and ledger<=65536
        assert artifact_total==summary['artifact_bytes'] and artifact_total<=4096
        assert ledger+artifact_total<=131072
        assert summary['end_to_end_seconds']<=120
        reports.append({'namespace':short,'commit':commit,'original_versions_verified':len(revisions),
            'full_snapshot_bytes':sum(map(len,revisions)),'genesis_bytes':len(genesis),
            'event_bytes':sum(chunk_sizes),'all_pointer_versions_bytes':sum(pointer_sizes),
            'ledger_bytes':ledger,'artifact_bytes':artifact_total,
            'exact_namespace_inventory_verified':True,'end_to_end_seconds':summary['end_to_end_seconds']})

    rpc=Path(args.rpc);calls=len(transport);request_bytes=0;response_bytes=0
    assert calls==85 and calls==result['transport']['calls']
    method_counts={};update_indices=[]
    for index,event in enumerate(transport,1):
        request=json.loads((rpc/f'request{index:04d}.json').read_bytes())
        response=json.loads((rpc/f'response{index:04d}.json').read_bytes())
        assert request['id']==response['id']==event['index']==index
        assert request['method']==event['method'] and response['ok'] is True
        req=canonical(request['params']);reply=canonical(response['result'])
        assert len(req)==event['request_bytes'] and sha(req)==event['request_sha256']
        assert len(reply)==event['response_bytes'] and sha(reply)==event['response_sha256']
        assert len(reply)<=event['response_reserved_bytes']
        request_bytes+=len(req);response_bytes+=len(reply)
        assert index<=240 and request_bytes<=4*1024**2 and response_bytes<=16*1024**2
        assert event['ended_seconds']<=600
        method_counts[event['method']]=method_counts.get(event['method'],0)+1
        if event['method']=='update_ref':
            assert request['params']['force'] is False and response['result']['success'] is True
            update_indices.append(index)
    assert len(update_indices)==4
    assert request_bytes==result['transport']['request_bytes'] and response_bytes==result['transport']['response_bytes']
    # The lost acknowledgement was injected above the actual transport. Its
    # genuine success reply remains retained. All subsequent requests are reads.
    final_update=update_indices[-1]
    assert all(e['read_only'] and e['method'] in ('fetch','fetch_file') for e in transport[final_update:])
    extra={}
    for path in rpc.glob('*.tmp'):
        target=path.with_suffix('');assert target.is_file() and target.read_bytes()==path.read_bytes()
        extra[path.name]={'bytes':path.stat().st_size,'sha256':sha(path.read_bytes()),'matches_delivered_reply':True}
    frame_bytes=sum(p.stat().st_size for p in rpc.iterdir() if p.is_file())
    assert frame_bytes<=16*1024**2
    assert result['elapsed_seconds']<=600 and result['peak_rss_bytes']<=512*1024**2
    assert result['status']=='CLOSED_ENGINEERING_PASS'
    assert all(result[k]==0 for k in ('automatic_retries','rng_constructions','source_requests','telescope_values','scientific_allocations'))
    assert result['lost01']['states']==['consumed'] and result['lost01']['writer_stopped']
    output={'schema':'radio-incremental-independent-postflight-v1','status':'PASS',
        'freeze_commit':freeze,'live_final_commit':parent,'own_branch_deltas_verified':4,
        'namespaces':reports,'original_versions_verified':sum(x['original_versions_verified'] for x in reports),
        'all_ledgers_bytes':sum(x['ledger_bytes'] for x in reports),'all_artifacts_bytes':sum(x['artifact_bytes'] for x in reports),
        'full_snapshot_comparison_bytes':sum(x['full_snapshot_bytes'] for x in reports),
        'transport_calls':calls,'request_json_bytes':request_bytes,'response_json_bytes':response_bytes,
        'method_counts':method_counts,'last_update_sequence':final_update,
        'only_reads_after_lost_acknowledgement':True,'actual_fault_is_application_injection':True,
        'all_rpc_frame_bytes_including_temp_duplicates':frame_bytes,'retained_temp_duplicates':extra,
        'both_case_time_caps_pass':True,'total_time_cap_pass':True,'scientific_timing_qualified':False,
        'scientific_127_24_status':'NOT_ACTIVATED','prior_science_unchanged_by_live_deltas':True,
        'no_experiment_replayed':True}
    Path(args.output).write_bytes(canonical(output));print(json.dumps(output,indent=2))


if __name__=='__main__':main()
