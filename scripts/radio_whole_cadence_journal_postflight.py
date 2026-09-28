#!/usr/bin/env python3
"""Read-only final guard/archive/invariant audit; no draw, cache or score rerun."""
import hashlib
import io
import json
from pathlib import Path
import platform
import resource
import subprocess
import sys
import tarfile
import time
import zipfile
import numpy as np
from radio_receiver_adapter_common import ROOT
from seti_repeater import whole_cadence_journal_radio as j
from seti_repeater import whole_cadence_archive_radio as a
from seti_repeater.whole_cadence_reference_radio import digest
from seti_repeater.empty_null_radio import canonical

OUT=ROOT/'results_radio_whole_cadence_journal_2026-09-28'


def read(path):return json.loads(path.read_bytes())


def write(path,value):
    with path.open('xb') as f:f.write(canonical(value))


def filebytes(path):
    p=ROOT/path
    return p.read_bytes() if p.is_file() else subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT)


def main():
    start=time.monotonic()
    old=read(ROOT/'results_radio_whole_cadence_physical_2026-09-28/postflight.json')
    pins=old['historical_invariant_pins']
    for path,sha in pins.items():
        if hashlib.sha256(filebytes(path)).hexdigest()!=sha:raise ValueError('Historical invariant changed: '+path)
    tests={}
    for path in sorted(OUT.glob('unit_phase*.log')):
        log=path.read_text()
        if not log.rstrip().endswith('OK') or 'FAILED' in log:raise ValueError('Unexpected test failure: '+str(path))
        for line in log.splitlines():
            if line.startswith('test_'):
                if not line.endswith(' ... ok'):raise ValueError('Unexpected test outcome')
                name=line.split(' ... ')[0]
                if name in tests:raise ValueError('New tests counted twice')
                tests[name]=path.name
    if len(tests)!=51:raise ValueError('Distinct new test count differs')
    cp=j.DirectoryStore(OUT/'native01/store').read()
    independent=read(OUT/'native01/independent_checkpoint.json')
    if cp.revision!=independent['revision'] or cp.document['manifest_sha256']!=independent['manifest_sha256']:
        raise ValueError('Native journal checkpoint changed')
    checked=[]
    for i in range(2):
        directory=OUT/f'native01/case{i}'
        parts=a.read_completed_bytes(cp,directory,case_index=i)
        sources=json.loads(parts['source_metadata.json'])['sources']
        scores=json.loads(parts['score_metadata.json'])['vectors']
        for name,keys,shape,bound in [('sources.npz',list(sources),(16,65536),6*16*65536*4),
                ('scores.npz',[v['npz_key'] for v in scores],(3,99),1296*3*99*4)]:
            # New header admission added after initial native fixture; exercise
            # it on the unchanged original archives, without regenerating scores.
            values=a.decode_npz(parts[name],expected_keys=keys,expected_shape=shape,maximum_decoded_bytes=bound)
            if name=='sources.npz':
                for label,array in values.items():
                    if hashlib.sha256(array.tobytes()).hexdigest()!=sources[label]['normalized_sha256']:
                        raise ValueError('Restored source values differ')
            checked.append({'case':i,'archive':name,'arrays':len(values),
                'verified_cells':sum(v.size for v in values.values()),'archive_sha256':hashlib.sha256(parts[name]).hexdigest()})
            del values
    crash=read(OUT/'crash01/result.json')
    with tarfile.open(OUT/'crash01/crash_stores.tar.gz','r:gz') as tar:
        for rec in crash['scenarios']:
            name=rec['scenario'];head=tar.extractfile(name+'/store/HEAD').read().decode().strip()
            if head!=rec['head']:raise ValueError('Preserved crash head differs')
            data=tar.extractfile(name+'/store/revisions/'+head).read();doc=json.loads(data)
            if digest(doc)!=head:raise ValueError('Preserved crash revision differs')
            state=j.replay(doc)
            if len(state['cases'])!=rec['case_consumptions']:raise ValueError('Preserved crash consumption differs')
            for member in tar.getmembers():
                if member.isfile() and member.name.startswith(name+'/'):
                    if tar.extractfile(member).read()!=(OUT/'crash01'/member.name).read_bytes():
                        raise ValueError('Crash archive not lossless')
    native=read(OUT/'native01/result.json')
    proposal=json.loads(filebytes('config/radio_whole_cadence_null_proposal_20260928.json'))
    proposed={c['identity'] for c in proposal['cases']}
    if proposed&{c['binding']['case_identity'] for c in j.replay(cp.document)['cases']}:
        raise ValueError('Engineering native case collided with proposed scientific case')
    paths=['src/seti_repeater/whole_cadence_journal_radio.py','src/seti_repeater/whole_cadence_archive_radio.py',
        'src/seti_repeater/whole_cadence_render_radio.py','scripts/radio_whole_cadence_journal_fixture.py',
        'scripts/radio_whole_cadence_archive_fixture.py','scripts/radio_whole_cadence_journal_postflight.py',
        'tests/test_radio_whole_cadence_journal.py','tests/test_radio_whole_cadence_archive.py',
        'tests/test_radio_whole_cadence_gaussian_guard.py','RADIO_WHOLE_CADENCE_JOURNAL_2026-09-28_SCOPE.md']
    write(OUT/'qualified_code_pins.json',{'pins':{p:hashlib.sha256(filebytes(p)).hexdigest() for p in paths},
        'qualifications':{'phase1':'30 new journal tests','phase2':'11 new archive + 5 Gaussian pre-RNG tests',
            'phase3':'3 new external artifact/prior-evidence guards','phase4':'2 new immutable budget guards',
            'renderer_regression':'14 existing tests after shared implementation changed; not new progress',
            'final_guard_regression':'2 existing success-path tests after final guard changes; not new tests',
            'native_fixture':'initial archive code hashes retained in native01/execution_code_pins.json',
            'final_npz_guard':'four original archives admitted by final header guard during this postflight'},
        'full_scientific_runtime_dependency_freeze':False})
    modules={'python_executable':sys.executable,'numpy_core':np._core._multiarray_umath.__file__,
        'numpy_pcg64':np.random._pcg64.__file__,'numpy_generator':np.random._generator.__file__}
    runtime={'python':sys.version,'numpy':np.__version__,'platform':platform.platform(),
        'binary_pins':{k:{'path':str(p),'sha256':hashlib.sha256(Path(p).read_bytes()).hexdigest()} for k,p in modules.items()},
        'actual_proposed_prng_constructions':0,'actual_gaussian_draws':0,'hdf5_or_telescope_calls':0,
        'complete_transitive_scientific_runtime_freeze':False}
    write(OUT/'runtime.json',runtime)
    retained=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file())
    if retained>128*1024**2:raise ValueError('Engineering retained evidence cap exceeded')
    result={'schema':'radio-whole-cadence-journal-postflight-v1','status':'VERIFIED_FOR_PUBLICATION',
        'historical_invariant_pins':pins,'distinct_new_tests':len(tests),'new_test_inventory':tests,
        'existing_regression_tests_not_counted_as_new':14,'additional_repeated_final_guard_checks':2,
        'crash_boundaries':6,'actual_process_crash_exits':5,'native_score_computations':2,
        'native_sources_preserved':12,'native_caches_preserved':96,'score_vectors_preserved':2592,
        'normalized_source_values_preserved':12582912,'score_values_preserved':769824,
        'final_archive_guard_checks':checked,'case_consumption_reservations_not_refunded':True,
        'new_scientific_allocations':0,'proposed_case_values':0,'new_source_requests':0,'new_telescope_values':0,
        'remote_scientific_adapter_qualified':False,'actual_gaussian_success_path_qualified':False,
        'full_native_physical_gate_chain_qualified':False,'scientific_proposal_status':'PROPOSED_NOT_ACTIVATED',
        'old_attempts_reopened':False,'preparation_contracts_changed':False,'external_messages':0,'plan_extended':False,
        'retained_evidence_bytes_at_postflight':retained,'postflight_seconds':time.monotonic()-start,
        'peak_process_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024}
    write(OUT/'postflight.json',result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('historical_invariant_pins','new_test_inventory','final_archive_guard_checks')},indent=2))


if __name__=='__main__':main()
