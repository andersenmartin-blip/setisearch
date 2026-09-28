#!/usr/bin/env python3
"""First score archive for two retained mocks; no source generation or RNG.

The restore worker consumes only saved bytes and an independent ledger head.
It is prohibited from calling NativeRun.build_store/cache or NumPy RNG.
"""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import time
import traceback
from unittest.mock import patch
import numpy as np
from radio_receiver_adapter_common import ROOT,context
from seti_repeater import transfer_m43g as native
from seti_repeater.pipeline_receiver_radio import NativeRun
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_reference_radio import digest
from seti_repeater import whole_cadence_journal_radio as j
from seti_repeater import whole_cadence_archive_radio as a

OUT=ROOT/'results_radio_whole_cadence_journal_2026-09-28/native01'
OLD=ROOT/'results_radio_whole_cadence_physical_2026-09-28'


def write(path,value):
    with path.open('xb') as f:f.write(canonical(value))


def read(path):return json.loads(path.read_bytes())


def restore_worker():
    expected=read(OUT/'independent_checkpoint.json');store=j.DirectoryStore(OUT/'store');cp=store.read()
    if cp.revision!=expected['revision'] or digest(cp.document['manifest'])!=expected['manifest_sha256']:
        raise ValueError('Independent restore checkpoint differs')
    receipts=[]
    with patch('numpy.random.Generator',side_effect=AssertionError('No RNG during archive restoration')), \
         patch.object(NativeRun,'build_store',side_effect=AssertionError('No score recomputation')), \
         patch.object(NativeRun,'cache',side_effect=AssertionError('No cache recomputation')):
        for index in range(2):
            c=context('calibration' if index==0 else 'validation')
            run,store,unit,receipt=a.restore(cp,OUT/f'case{index}',c,case_index=index)
            if len(run.source_ids)!=6 or len(store.arrays)!=1296:raise ValueError('Restored inventories differ')
            receipts.append(receipt);del run,store,unit
    write(OUT/'independent_restore.json',{'status':'COMPLETE_NATIVE_ARCHIVES_RESTORED_WITHOUT_RNG_OR_CACHE',
        'cases':receipts,'normalized_values_verified':sum(r['source_values'] for r in receipts),
        'score_values_verified':sum(r['score_values'] for r in receipts),
        'process_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        'new_execution_leases':0,'scientific_attempts':0})


def main():
    start=time.monotonic();OUT.mkdir(exist_ok=False)
    lease=None
    try:
        originals=read(OLD/'publication_manifest.json')
        # Pin all source archives, receipts and existing rehydration metadata.
        inputs=['source_rehydration.json']+[f'render01/case{i}_{suffix}' for i in range(2)
            for suffix in ('normalized_sources.npz','source_scopes.json','receipt.json','plan.json')]
        pins={}
        for relative in inputs:
            p=OLD/relative;pins[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
        # Independent checks against Git-published bytes, not a fresh data draw.
        for p,h in pins.items():
            published=subprocess.check_output(['git','show','4360136e3e083f1567a9dc449c09b1a85b788acd:'+p],cwd=ROOT)
            if hashlib.sha256(published).hexdigest()!=h:raise ValueError('Retained published input differs: '+p)
        write(OUT/'input_pins.json',pins)
        meta=read(OLD/'source_rehydration.json');bindings=[]
        for i in range(2):
            p=read(OLD/f'render01/case{i}_plan.json');r=read(OLD/f'render01/case{i}_receipt.json')
            bindings.append({'case_identity':r['case_identity'],'plan_sha256':p['plan_sha256'],
                'context_sha256':p['context_sha256'],'source_contract_sha256':p['case']['source_contract_sha256'],
                'noise_law_sha256':r['noise_law_sha256'],'role':'engineering'})
        codepaths=['src/seti_repeater/whole_cadence_journal_radio.py','src/seti_repeater/whole_cadence_archive_radio.py',
            'scripts/radio_whole_cadence_archive_fixture.py']
        codepins={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in codepaths}
        write(OUT/'execution_code_pins.json',codepins)
        m={'schema':j.SCHEMA,'mode':'engineering','namespace':'retained-mock-score-archive-20260928',
            'execution_binding_sha256':digest({'input_pins':pins,'code_pins':codepins}),
            'allocation_sha256':digest({'engineering_scope':'RADIO_WHOLE_CADENCE_JOURNAL_2026-09-28_SCOPE.md',
                'scope_sha256':hashlib.sha256((ROOT/'RADIO_WHOLE_CADENCE_JOURNAL_2026-09-28_SCOPE.md').read_bytes()).hexdigest(),
                'scientific_allocation':False,'new_values':0}),
            'cases':bindings,'caps':{**j.CAPS,'active_milliseconds':1200000,'evidence_bytes':128*1024**2,
                'ledger_reserve_bytes':1024**2},'required_artifacts':list(a.ARTIFACTS)}
        store=j.DirectoryStore.create(OUT/'store',m);summaries=[]
        with patch('numpy.random.Generator',side_effect=AssertionError('No new Gaussian source')):
            for i in range(2):
                cp=store.read();lease=j.consume(store,expected_revision=cp.revision,expected_manifest_sha256=digest(m),
                    binding=bindings[i],milliseconds=500000,artifact_bytes=60*1024**2,directory=OUT/f'case{i}')
                c=context('calibration' if i==0 else 'validation');scopes=read(OLD/f'render01/case{i}_source_scopes.json')
                sources={}
                with np.load(OLD/f'render01/case{i}_normalized_sources.npz',allow_pickle=False) as arrays:
                    for row in [x for x in meta['sources'] if x['case']==i]:
                        label=row['scan']
                        if row['geometry']!=asdict(c.geometry):raise ValueError('Retained geometry differs')
                        sources[label]=native.SyntheticSource(c.geometry,16,canonical(scopes[label]).decode(),
                            row['raw_sha256'],row['normalized_sha256'],row['source_identity'],native.immutable(arrays[label]))
                run=NativeRun(c,sources);lease.budget(run.modelled_bytes)
                score=run.build_store();lease.budget(run.modelled_bytes)
                unit=a.snapshot(lease,run,score,case_identity=bindings[i]['case_identity'],noise_law_sha256=bindings[i]['noise_law_sha256'])
                lease.finish();summaries.append({'case_index':i,'case_identity':bindings[i]['case_identity'],
                    'maximum':unit.record()['maximum'],'eligible_cells':unit.record()['eligible_cells'],
                    'source_ids':run.source_ids,'cache_receipts':len(score.provenance['native_caches']),
                    'score_vectors':len(score.arrays),'score_cells':sum(v.size for v in score.arrays.values()),
                    'modelled_array_bytes':run.modelled_bytes})
                del run,score,unit,sources;lease=None
                print('Archived retained mock case '+str(i),flush=True)
        cp=store.read();write(OUT/'independent_checkpoint.json',{'revision':cp.revision,'manifest_sha256':digest(m),
            'location':cp.location,'head':j.replay(cp.document)['head']})
        worker=subprocess.run([sys.executable,__file__,'--restore'],cwd=ROOT,capture_output=True)
        with (OUT/'restore_process.log').open('xb') as f:f.write(worker.stdout+worker.stderr)
        if worker.returncode:raise RuntimeError('Independent archive restore failed: '+str(worker.returncode))
        write(OUT/'result.json',{'status':'TWO_RETAINED_NATIVE_SOURCE_SCORE_ARCHIVES_PASS','cases':summaries,
            'source_score_computations':2,'new_source_realizations':0,'scientific_allocations':0,'gaussian_values':0,
            'source_requests':0,'telescope_values':0,'native_physical_chain_qualified':False,
            'ledger_cumulative':j.replay(cp.document),'independent_restore':read(OUT/'independent_restore.json'),
            'active_seconds':time.monotonic()-start,'peak_process_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024})
        print(json.dumps({'cases':summaries,'active_seconds':time.monotonic()-start},indent=2))
    except BaseException as error:
        write(OUT/'error.json',{'error':repr(error),'traceback':traceback.format_exc(),'automatic_retry_authorized':False})
        if lease is not None and not lease.closed and not lease.broken:
            lease.finish('failed',repr(error))
        raise


if __name__=='__main__':
    if sys.argv[1:]==['--restore']:restore_worker()
    else:main()
