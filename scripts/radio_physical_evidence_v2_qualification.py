#!/usr/bin/env python3
"""One frozen byte-only capacity qualification; no closed physical case replay.

The historical partial report is retained as its exact UTF-8 string, including
whitespace. Repeated saved software receiver pairs are a serialization stress
load, never new measurements or independent scientific members.
"""
import argparse
import base64
from contextlib import ExitStack
import hashlib
import io
import json
import lzma
from pathlib import Path
import resource
import signal
import sys
import tarfile
import time
from unittest.mock import patch
import zlib

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from seti_repeater import physical_evidence_v2_radio as evidence
from seti_repeater.empty_null_radio import canonical
from radio_receiver_evidence_capacity import git_blobs,BASE,ARCHIVE,SOURCE,SOURCE_SHA

NAMESPACE='radio-physical-v2-byte-20260930a'
RESULTS=ROOT/'results_radio_physical_v2_2026-09-30'
CODE_PATHS=['src/seti_repeater/physical_evidence_v2_radio.py',
            'src/seti_repeater/physical_evidence_radio.py',
            'src/seti_repeater/whole_cadence_physical_radio.py',
            'scripts/radio_physical_evidence_v2_qualification.py',
            'scripts/radio_receiver_evidence_capacity.py',
            'tests/test_radio_physical_evidence_v2.py']
PROFILE='results_radio_receiver_batch_2026-09-29/profile01/'
PROFILE_PINS={
    'width1_identical_outputs.json.zlib.b64':
        ('31f630c99938434a0fa4c13ffa1093dd4903e03d37a3ee56c63aca6f0ee82034',
         '5a31126fe31bc897338f6ce56fbc8f31ddec7067d0e2669b8f0b1b27e3038844',625618),
    'width129_identical_outputs.json.zlib.b64':
        ('be28d4f4c99823aba74679928aa1abf0e05b54c49cc293875b408ea432802c28',
         'b5da8a64a1afcb67395546a06f4b91af434406fc828ca591b7242626284d6004',625158)}


def sha(raw):return hashlib.sha256(raw).hexdigest()


def write_new(path,value):
    with path.open('xb') as f:f.write(canonical(value))


def load_sources():
    manifest=json.loads(git_blobs([ARCHIVE+'archive_manifest.json'])[ARCHIVE+'archive_manifest.json'])
    paths=[ARCHIVE+r['path'] for r in manifest['chunks']]
    inputs=git_blobs(paths+[PROFILE+n for n in PROFILE_PINS])
    chunks=[]
    for r in manifest['chunks']:
        data=inputs[ARCHIVE+r['path']]
        if len(data)!=r['bytes'] or sha(data)!=r['sha256']:raise ValueError('Transport chunk differs')
        chunks.append(data)
    encoded=b''.join(chunks)
    if len(encoded)!=manifest['base64_bytes']:raise ValueError('Base64 length differs')
    xz=base64.b64decode(encoded,validate=True)
    if len(xz)!=manifest['xz_bytes'] or sha(xz)!=manifest['xz_sha256']:raise ValueError('Archive pin differs')
    tar_raw=lzma.decompress(xz)
    if len(tar_raw)!=manifest['tar_bytes']:raise ValueError('Archive expansion differs')
    wanted={SOURCE}|{r['path'] for r in manifest['files'] if r['path'].startswith('live01/case4/')}
    originals={}
    with tarfile.open(fileobj=io.BytesIO(tar_raw),mode='r:') as archive:
        for m in archive.getmembers():
            if m.name in wanted:
                if m.name in originals or not m.isfile():raise ValueError('Unique regular original required')
                originals[m.name]=archive.extractfile(m).read()
    if set(originals)!=wanted:raise ValueError('Missing original member')
    pins={r['path']:r for r in manifest['files']}
    for name,data in originals.items():
        if sha(data)!=pins[name]['sha256'] or len(data)!=pins[name]['bytes']:raise ValueError('Original differs')
    source=originals.pop(SOURCE)
    if sha(source)!=SOURCE_SHA or len(source)!=14979354:raise ValueError('Partial report pin differs')
    base={Path(name).name:data for name,data in originals.items()}
    if len(base)!=7 or sum(map(len,base.values()))!=2004352:raise ValueError('Original seven artifacts required')
    pairs=[];profiles={};profile_texts={}
    for name,(encoded_sha,raw_sha,size) in PROFILE_PINS.items():
        data=inputs[PROFILE+name]
        if sha(data)!=encoded_sha:raise ValueError('Saved software profile differs')
        raw=zlib.decompress(base64.b64decode(data,validate=True))
        if len(raw)!=size or sha(raw)!=raw_sha:raise ValueError('Saved pair bytes differ')
        rows=json.loads(raw)
        if len(rows)!=1024 or canonical(rows)+b'\n'!=raw:raise ValueError('Original canonical pair array plus newline required')
        pairs.extend(rows)
        profile_texts[name]=raw.decode('utf-8')
        profiles[PROFILE+name]={'encoded_sha256':encoded_sha,'logical_sha256':raw_sha,'logical_bytes':size,'pairs':1024}
    source_pins={'evidence_commit':BASE,'archive_xz_sha256':manifest['xz_sha256'],
                 'partial_report':{'archive_member':SOURCE,'bytes':len(source),'sha256':sha(source)},
                 'existing_artifacts':{name:{'bytes':len(data),'sha256':sha(data)} for name,data in base.items()},
                 'profiles':profiles}
    return source,base,pairs,source_pins,profile_texts


def contract(source_pins):
    return {'schema':'radio-physical-evidence-v2-byte-qualification-v1','namespace':NAMESPACE,
        'engineering_only':True,'case_identity':sha((NAMESPACE+'/case1').encode()),
        'sources':source_pins,'code_sha256':{p:sha((ROOT/p).read_bytes()) for p in CODE_PATHS},
        'caps':{'stored_case_bytes':evidence.MAX_BYTES,'logical_value_bytes':evidence.MAX_VALUE_BYTES,
                'logical_snapshot_bytes':evidence.MAX_SNAPSHOT_BYTES,'active_seconds':180,
                'peak_rss_bytes':512*1024**2,'checkpoints':3,'files':evidence.MAX_FILES},
        'recipe':{'snapshots':[{'pair_repetitions':1},{'pair_repetitions':20},{'pair_repetitions':20}],
                  'partial_report':'exact original UTF-8 string; no JSON rewriting',
                  'receiver_outputs':'flattened original width1 then width129 pairs, repeated in order',
                  'original_profile_files':'exact original UTF-8 strings, including final newlines',
                  'footer_status':'failed','expected_source_physical_complete':False},
        'stop_rule':'One exclusive fresh directory; any failure closes scope; no retry or smaller substitute.',
        'scope_limits':['Byte retention and streamed restoration only.',
            'Repeated pair bytes are not independent members, receiver measurements or closed-case completion.',
            'No native chain, parent lease, event journal, remote runtime, 80-second qualification or scientific admission.'],
        'scientific_127_24_activated':False,'historical_caps_changed':False}


def run(freeze_path,receipt_path):
    started=time.monotonic()
    freeze_raw=freeze_path.read_bytes();frozen=json.loads(freeze_raw)
    receipt=json.loads(receipt_path.read_bytes())
    if canonical(frozen)!=freeze_raw or receipt.get('verified') is not True or receipt.get('freeze_sha256')!=sha(freeze_raw):
        raise ValueError('Verified independently read public freeze required')
    if any(name in sys.modules for name in ('seti_repeater.pipeline_radio','seti_repeater.pipeline_receiver_radio',
                                          'seti_repeater.whole_cadence_physical_radio')):
        raise ValueError('Byte worker must not import native execution modules')
    def check():
        if time.monotonic()-started>180:raise TimeoutError('Frozen active budget exceeded')
        if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>frozen['caps']['peak_rss_bytes']:
            raise MemoryError('Frozen peak RSS budget exceeded')
    def expired(signum,frame):raise TimeoutError('Frozen whole-worker alarm')
    signal.signal(signal.SIGALRM,expired);signal.alarm(180)
    import numpy as np
    writer=None
    with ExitStack() as guards:
        for name in ('default_rng','RandomState','seed','random','random_sample','rand','randn','normal',
                     'standard_normal','uniform','randint','choice','permutation','shuffle'):
            guards.enter_context(patch.object(np.random,name,side_effect=AssertionError('No RNG in byte qualification')))
        source,base,pairs,source_pins,profile_texts=load_sources();check()
        if frozen!=contract(source_pins):raise ValueError('Frozen code, source or recipe changed')
        source_text=source.decode('utf-8')
        if json.loads(source)['complete'] is not False:raise ValueError('Historical incomplete status required')
        config=evidence.configuration(NAMESPACE,frozen['case_identity'],sha(freeze_raw),base,checkpoint_limit=3)
        def document(repetitions):
            return {'retention':{'case_identity':frozen['case_identity']},'complete':False,
                    'archived_partial_report_utf8':source_text,'original_software_profile_files_utf8':profile_texts,
                    'software_receiver_outputs':pairs*repetitions}
        writer=evidence.Writer.create(RESULTS/'case1',config,existing_artifacts=base)
        expected=[];timings=[]
        try:
            for index,repetitions in enumerate((1,20,20)):
                t=time.monotonic();doc=document(repetitions);raw=canonical(doc)
                expected.append({'bytes':len(raw),'sha256':sha(raw),'pair_count':2048*repetitions})
                del raw
                if index==2:writer.close('failed','preserved-incomplete-source',
                    'Storage qualification only; historical physical run remains failed.',snapshot=doc)
                else:writer.checkpoint('byte-load-'+str(index),doc)
                del doc;check();timings.append(time.monotonic()-t)
                print(json.dumps({'checkpoint':index,'expected':expected[-1],'charged_bytes':writer.receipt()['charged_case_bytes']},sort_keys=True),flush=True)
            if expected[1]['bytes']<=29821434:raise ValueError('Frozen load does not exceed known lower bound')
            r=evidence.inspect(RESULTS/'case1',expected_config_sha256=writer.config_sha,
                expected_last_checkpoint_sha256=writer.previous)
            restored=[]
            for index in range(3):
                h=hashlib.sha256();size=0;maximum_chunk=0
                for chunk in r.iter_snapshot(index):h.update(chunk);size+=len(chunk);maximum_chunk=max(maximum_chunk,len(chunk));check()
                if size!=expected[index]['bytes'] or h.hexdigest()!=expected[index]['sha256']:
                    raise ValueError('Exact original snapshot differs')
                restored.append({'bytes':size,'sha256':h.hexdigest(),'max_yield_bytes':maximum_chunk})
            for checkpoint in r.checkpoint_bytes:
                field=json.loads(checkpoint)['fields']['archived_partial_report_utf8']
                value,_=evidence._raw(field,r.files,set());original=json.loads(value).encode('utf-8')
                if original!=source:raise ValueError('Original partial report bytes lost')
                field=json.loads(checkpoint)['fields']['original_software_profile_files_utf8']
                value,_=evidence._raw(field,r.files,set())
                if json.loads(value)!=profile_texts:raise ValueError('Original profile file bytes lost')
            check()
            result={'schema':'radio-physical-evidence-v2-byte-result-v1','status':'PASS','namespace':NAMESPACE,
                'freeze_sha256':sha(freeze_raw),'public_freeze_commit':receipt['commit'],
                'original_partial_report_sha256':sha(source),'original_partial_report_bytes':len(source),
                'snapshots':expected,'restored':restored,'case':r.summary(),
                'stored_case_limit_bytes':frozen['caps']['stored_case_bytes'],
                'existing_base_artifact_bytes':sum(map(len,base.values())),
                'write_seconds_per_snapshot':timings,'whole_worker_seconds':time.monotonic()-started,
                'peak_process_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                'source_physical_status':'FAILED','new_physical_execution':False,'new_receiver_measurements':0,
                'new_random_values':0,'new_telescope_reads':0,'closed_cases_reexecuted':False,
                'parent_remote_integration_qualified':False,'scientific_127_24_activated':False,
                'scope_limits':frozen['scope_limits']}
            write_new(RESULTS/'result.json',result)
            inventory={name:{'bytes':len(data),'sha256':sha(data)} for name,data in r.files.items()}
            write_new(RESULTS/'case_inventory.json',inventory)
            print(json.dumps(result,sort_keys=True,indent=2),flush=True)
        except BaseException as error:
            if writer is not None and not writer.closed:
                writer.close('failed','byte-qualification-error',str(error))
            write_new(RESULTS/'failed.json',{'status':'FAILED','error':repr(error),'no_retry':True,
                'freeze_sha256':sha(freeze_raw),'elapsed_seconds':time.monotonic()-started})
            raise
        finally:signal.alarm(0)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--freeze',action='store_true')
    parser.add_argument('--receipt',type=Path)
    args=parser.parse_args();freeze_path=RESULTS/'freeze.json'
    if args.freeze:
        _,_,_,pins,_=load_sources();write_new(freeze_path,contract(pins));print(sha(freeze_path.read_bytes()))
    else:
        if args.receipt is None:parser.error('--receipt required for the one frozen run')
        run(freeze_path,args.receipt)
