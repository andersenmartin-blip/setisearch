#!/usr/bin/env python3
"""Frozen terminal archive publication over tool RPC; never an execution lease."""
import argparse
import hashlib
import json
from pathlib import Path
import resource
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'scripts')]
from seti_repeater import event_archive_remote_radio as remote
from seti_repeater import physical_evidence_v2_radio as e
from seti_repeater import whole_cadence_event_store_radio as events
from seti_repeater.empty_null_radio import canonical
from radio_lossless_handoff import FileRPC,publish

OUT=ROOT/'results_radio_v2_parent_2026-09-30'
CODE=['scripts/radio_v2_parent_remote.py','scripts/radio_lossless_handoff.py',
    'scripts/radio_v2_parent_handoff.py',
    'scripts/radio_v2_parent_broker.js',
    'src/seti_repeater/event_archive_remote_radio.py',
    'src/seti_repeater/physical_case_v2_radio.py',
    'src/seti_repeater/physical_evidence_v2_radio.py',
    'src/seti_repeater/physical_evidence_radio.py',
    'src/seti_repeater/whole_cadence_event_store_radio.py',
    'src/seti_repeater/whole_cadence_journal_radio.py',
    'src/seti_repeater/whole_cadence_reference_radio.py',
    'src/seti_repeater/empty_null_radio.py']

def sha(data):return hashlib.sha256(data).hexdigest()

def prepared(parent,tree):
    path=OUT/'integration01';result=json.loads((path/'result.json').read_bytes())
    if result['status']!='LOCAL_PARENT_EVENT_BYTE_PASS':raise ValueError('Closed local byte integration required')
    flat=e._inventory(path/'case')
    physical={e.nested_name(n):v for n,v in flat.items() if n.startswith('physical-')}
    base={n:v for n,v in flat.items() if not n.startswith('physical-')}
    return remote.prepare_bundle(physical,events.inventory(path/'journal'),base,
        expected_config_sha256=result['physical_config_sha256'],
        expected_last_checkpoint_sha256=result['physical_last_checkpoint_sha256'],
        expected_genesis_sha256=result['journal_genesis_sha256'],
        expected_pointer_sha256=result['journal_pointer_sha256'],
        expected_parent_sha=parent,expected_parent_tree_sha=tree,
        limits=remote.Limits(calls=512,request_bytes=16*1024**2,response_bytes=24*1024**2,
            stored_bytes=32*1024**2,files=200,seconds=900))

def freeze(bundle):
    return {'schema':'radio-v2-event-parent-remote-freeze-v1','bundle':json.loads(bundle.freeze_bytes),
        'bundle_sha256':bundle.sha256,'code_sha256':{n:sha((ROOT/n).read_bytes()) for n in CODE},
        'project_python_sha256':{str(path.relative_to(ROOT)):sha(path.read_bytes())
            for path in sorted((ROOT/'src').rglob('*.py'))},
        'peak_rss_bytes':512*1024**2,'scope':'terminal engineering snapshot publication only',
        'scientific_127_24_activated':False,'native_runtime_remote_qualified':False}

def run(receipt_path):
    started=time.monotonic();raw=(OUT/'remote_freeze.json').read_bytes();frozen=json.loads(raw)
    receipt=json.loads(receipt_path.read_bytes())
    if (canonical(frozen)!=raw or receipt.get('verified') is not True
            or receipt.get('freeze_sha256')!=sha(raw)):
        raise ValueError('Public independent remote freeze readback required')
    bundle=prepared(frozen['bundle']['parent'],frozen['bundle']['parent_tree'])
    if freeze(bundle)!=frozen:raise ValueError('Frozen archive, code or limits changed')
    target=OUT/'remote01';target.mkdir(exist_ok=False)
    rpc=FileRPC(target/'rpc');publisher=None
    result={'schema':'radio-v2-event-parent-remote-result-v1','public_freeze_commit':receipt['commit'],
        'remote_freeze_sha256':sha(raw),'bundle_sha256':bundle.sha256,
        'scientific_127_24_activated':False,'native_runtime_remote_qualified':False,
        'source_physical_status':'failed','parent_case_status':'failed','automatic_retry':False,
        'new_random_values':0,'new_receiver_measurements':0,'new_telescope_reads':0}
    try:
        publisher=remote.Publisher(bundle,rpc,expected_bundle_sha256=frozen['bundle_sha256'])
        result['publication']=publisher.publish();result['status']='TERMINAL_ENGINEERING_ARCHIVE_PASS'
    except BaseException as error:
        result.update(status='TERMINAL_ENGINEERING_ARCHIVE_STOPPED',error=repr(error),
            publication=None if publisher is None else publisher.receipt)
    result.update(worker_seconds=time.monotonic()-started,
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    if result['peak_rss_bytes']>frozen['peak_rss_bytes']:
        result['status']='TERMINAL_ENGINEERING_ARCHIVE_STOPPED';result['rss_cap_exceeded']=True
    if publisher:publish(target/'transport_receipts.json',publisher.events)
    publish(target/'result.json',result)
    summary={'status':result['status'],'worker_seconds':result['worker_seconds'],
        'usage':None if publisher is None else publisher.usage()}
    publish(rpc.path/'done.json',summary);print(json.dumps(summary),flush=True)
    return 0 if result['status']=='TERMINAL_ENGINEERING_ARCHIVE_PASS' else 1

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--parent');parser.add_argument('--tree');parser.add_argument('--receipt',type=Path)
    args=parser.parse_args()
    if args.prepare:
        if args.parent is None or args.tree is None:parser.error('--parent and --tree required')
        bundle=prepared(args.parent,args.tree);publish(OUT/'remote_freeze.json',freeze(bundle))
        print(json.dumps({'freeze_sha256':sha((OUT/'remote_freeze.json').read_bytes()),
            'files':len(bundle.files),'stored_bytes':sum(map(len,bundle.files.values())),
            'bundle_sha256':bundle.sha256}))
    else:
        if args.receipt is None:parser.error('--receipt required')
        sys.exit(run(args.receipt))
