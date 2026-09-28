"""Lossless native source/score archives bound to a completed consumption ledger.

Restoration grants no lease and does not call a renderer or rebuild a cache.
Raw hashes remain provenance claims bound to the original source receipt;
normalized and score values are revalidated from the actual archived bytes.
"""
from dataclasses import asdict
import hashlib
import io
import json
import zipfile
import numpy as np

from . import transfer_m43g as native
from . import search_v0p6 as core
from .empty_null_radio import canonical
from .injection_m43r import ScoreStore
from .pipeline_receiver_radio import NativeRun
from .whole_cadence_reference_radio import digest, reduce_native_run
from .whole_cadence_journal_radio import replay, verify_archive

ARTIFACTS = ('sources.npz','source_metadata.json','scores.npz','score_metadata.json','maximum.json')


def npz_bytes(arrays):
    buffer=io.BytesIO();np.savez_compressed(buffer,**arrays);return buffer.getvalue()


def snapshot(lease,run,store,*,case_identity,noise_law_sha256):
    """Save all original values and identities; finish remains the caller's step."""
    lease.budget(run.modelled_bytes)
    b=lease.case['binding']
    if (b['case_identity']!=case_identity or b['noise_law_sha256']!=noise_law_sha256
            or b['context_sha256']!=run.context.identity):
        raise ValueError('Archive lease/source binding differs')
    unit=reduce_native_run(run,store,case_identity=case_identity,noise_law_sha256=noise_law_sha256)
    source_metadata={'schema':'radio-whole-cadence-native-source-archive-v1',
        'context_sha256':run.context.identity,'case_identity':case_identity,
        'noise_law_sha256':noise_law_sha256,'sources':{}}
    for label,s in run.sources.items():
        native.validate_source(s)
        source_metadata['sources'][label]={'geometry':asdict(s.geometry),'integration_count':s.integration_count,
            'scope':json.loads(s.scope_json),'raw_sha256':s.raw_sha256,
            'normalized_sha256':s.normalized_sha256,'identity':s.identity}
    score_metadata={'schema':'radio-whole-cadence-score-archive-v1','provenance':store.provenance,
        'vectors':[{'key':list(k),'npz_key':f'{k[0]}_{k[1]:03d}_{k[2]:03d}','identity':store.expected_ids[k]}
            for k in sorted(store.arrays)]}
    lease.write_artifact('sources.npz',npz_bytes({k:s.values for k,s in run.sources.items()}))
    lease.write_artifact('source_metadata.json',canonical(source_metadata))
    lease.write_artifact('scores.npz',npz_bytes({r['npz_key']:store.arrays[tuple(r['key'])] for r in score_metadata['vectors']}))
    lease.write_artifact('score_metadata.json',canonical(score_metadata))
    lease.write_artifact('maximum.json',unit.payload)
    lease.budget(run.modelled_bytes)
    return unit


def read_completed_bytes(checkpoint,directory,*,case_index):
    from pathlib import Path
    state=replay(checkpoint.document);case=state['cases'][case_index]
    if case['status']!='completed':raise ValueError('Completed case required; no restart permission')
    verify_archive(checkpoint,directory,case_index=case_index)
    result={}
    for name,meta in case['artifacts'].items():
        data=(Path(directory)/name).read_bytes()
        if len(data)!=meta['size'] or hashlib.sha256(data).hexdigest()!=meta['sha256']:
            raise ValueError('Archive changed while taking immutable snapshot')
        result[name]=data
    return result


def decode_npz(payload,*,expected_keys,expected_shape,maximum_decoded_bytes):
    expected=set(expected_keys)
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        entries=z.infolist()
        if len(entries)!=len(expected) or {x.filename for x in entries}!={k+'.npy' for k in expected}:
            raise ValueError('NPZ inventory missing, duplicated or extra')
        if sum(x.file_size for x in entries)>maximum_decoded_bytes+len(entries)*512:
            raise ValueError('NPZ decompressed capacity exceeded')
        # Inspect headers before np.load can allocate an array. ZIP length alone
        # does not bound a forged NPY shape stored in a short member.
        for entry in entries:
            with z.open(entry) as stream:
                version=np.lib.format.read_magic(stream)
                if version==(1,0):shape,fortran,dtype=np.lib.format.read_array_header_1_0(stream)
                elif version==(2,0):shape,fortran,dtype=np.lib.format.read_array_header_2_0(stream)
                else:raise ValueError('Unsupported native NPY version')
                if shape!=expected_shape or dtype!=np.dtype('<f4') or fortran:
                    raise ValueError('Native NPY header shape/dtype/order differs')
    arrays={}
    with np.load(io.BytesIO(payload),allow_pickle=False) as saved:
        for key in expected:
            a=saved[key]
            if a.dtype!=np.dtype('<f4') or a.shape!=expected_shape or not np.isfinite(a).all():
                raise ValueError('Native archive shape/dtype/finite values differ')
            arrays[key]=native.immutable(a)
    return arrays


def restore(checkpoint,directory,context,*,case_index):
    """Read-only complete restoration, with independent caller-supplied context."""
    context.validate();parts=read_completed_bytes(checkpoint,directory,case_index=case_index)
    if set(parts)!=set(ARTIFACTS):raise ValueError('Exact native archive required')
    case=replay(checkpoint.document)['cases'][case_index];b=case['binding']
    meta=json.loads(parts['source_metadata.json']);scoremeta=json.loads(parts['score_metadata.json'])
    if (meta['schema']!='radio-whole-cadence-native-source-archive-v1'
            or meta['context_sha256']!=context.identity or b['context_sha256']!=context.identity
            or meta['case_identity']!=b['case_identity'] or meta['noise_law_sha256']!=b['noise_law_sha256']
            or scoremeta['schema']!='radio-whole-cadence-score-archive-v1'):
        raise ValueError('Native archive context/case/law differs')
    labels={s['label'] for s in context.scans}
    if set(meta['sources'])!=labels:raise ValueError('Six source metadata records required')
    arrays=decode_npz(parts['sources.npz'],expected_keys=labels,expected_shape=(16,65536),maximum_decoded_bytes=6*16*65536*4)
    sources={}
    for label in labels:
        m=meta['sources'][label]
        if m['geometry']!=asdict(context.geometry) or m['integration_count']!=16:
            raise ValueError('Archived geometry differs')
        scope=m['scope']
        if scope.get('case_identity')!=b['case_identity'] or scope.get('noise_law_sha256')!=b['noise_law_sha256']:
            raise ValueError('Archived source case/law differs')
        sources[label]=native.SyntheticSource(context.geometry,16,canonical(scope).decode(),
            m['raw_sha256'],m['normalized_sha256'],m['identity'],arrays[label])
    run=NativeRun(context,sources)
    vectors=scoremeta['vectors'];expected={(k,t,w) for k in ('on','off') for t in range(len(context.bank)) for w in core.M37_SPECTRAL_WIDTHS}
    if len(vectors)!=len(expected) or {tuple(v['key']) for v in vectors}!=expected:
        raise ValueError('Full archived score inventory required')
    keys=[v['npz_key'] for v in vectors]
    if len(set(keys))!=len(keys):raise ValueError('Duplicate score array key')
    values=decode_npz(parts['scores.npz'],expected_keys=keys,expected_shape=(3,context.grid.support_bin_count),
        maximum_decoded_bytes=len(expected)*3*context.grid.support_bin_count*4)
    store=ScoreStore({tuple(v['key']):values[v['npz_key']] for v in vectors},scoremeta['provenance'])
    if any(store.expected_ids[tuple(v['key'])]!=v['identity'] for v in vectors):raise ValueError('Archived score identities differ')
    run.validate_store(store)
    unit=reduce_native_run(run,store,case_identity=b['case_identity'],noise_law_sha256=b['noise_law_sha256'])
    if unit.payload!=parts['maximum.json']:raise ValueError('Restored complete maximum differs')
    receipt={'schema':'radio-whole-cadence-native-restore-v1','case_identity':b['case_identity'],
        'ledger_revision':checkpoint.revision,'source_ids':run.source_ids,'score_vectors':len(store.arrays),
        'source_values':sum(s.values.size for s in sources.values()),
        'score_values':sum(a.size for a in store.arrays.values()),'maximum_receipt_sha256':unit.record()['receipt_sha256'],
        'rng_calls':0,'cache_recomputations':0,'execution_restart_authorized':False}
    receipt['receipt_sha256']=digest(receipt)
    return run,store,unit,receipt
