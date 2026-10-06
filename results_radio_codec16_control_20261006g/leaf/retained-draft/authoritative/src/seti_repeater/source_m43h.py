"""M43H widened source receipts and bounded row-wise extraction.

Only extract_remote owns the live remote/header/hyperslab path. Private fixture
helpers can exercise persistence without being telescope provenance. Rehydration
requires an independently retained receipt SHA, not a self-selected file hash.
No source created here is a legacy M37 or M43G synthetic cache product.
"""
from dataclasses import asdict
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import numpy as np
from . import search_v0p6 as core
from . import source_v0p6 as legacy
from . import http_range_v0p6 as old_transport

VERSION='m43h-widened-source-v1'
BLOCK=4096
MAX_CHANNELS=1_135_670
MAX_ROWS=16
MAX_MODELLED_BYTES=256*1024**2
MAX_HDF5_CHUNK_BYTES=16*1024**2
HDF5_CACHE_BYTES=8*1024**2


def digest(value):return hashlib.sha256(core.canonical_json_bytes(value)).hexdigest()


def array_hash(value):return hashlib.sha256(memoryview(value).cast('B')).hexdigest()


def file_hash(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        while chunk:=f.read(1024*1024):h.update(chunk)
    return h.hexdigest()


def seal(value,key='receipt_sha256'):
    return {**value,key:digest(value)}


def verify(record,key='receipt_sha256'):
    if record.get(key)!=digest({k:v for k,v in record.items() if k!=key}):
        raise ValueError('receipt identity mismatch')
    return record


def verify_transport_checkpoint(record,identity):
    # The inherited transport uses its own canonical encoding (no newline).
    basis={k:v for k,v in record.items() if k!='checkpoint_sha256'}
    if (record.get('checkpoint_sha256')!=old_transport._sha256_bytes(old_transport._canonical_json_bytes(basis))
            or record.get('remote')!=identity
            or record.get('artifact_type')!=old_transport.CHECKPOINT_ARTIFACT
            or record.get('schema_version')!=1):
        raise ValueError('transport checkpoint identity mismatch')
    return record


def atomic_json(path,record):
    old_transport._write_atomic(Path(path),core.canonical_json_bytes(record))


def atomic_npy(path,values):
    path=Path(path);tmp=path.with_name(path.name+'.partial')
    with tmp.open('wb') as f:
        np.save(f,values,allow_pickle=False);f.flush();os.fsync(f.fileno())
    os.replace(tmp,path)
    fd=os.open(path.parent,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)


def resource_bound(channels):
    # Row/normalization/verification arrays, bounded HTTP buffers, bounded
    # HDF5 reads/cache/decoded chunk. Excludes native-library/OS overhead.
    return 32*channels + (4*8+32+8+16+4)*1024**2


def normalize_native_row(raw):
    if raw.dtype!=np.dtype('<f4') or raw.ndim!=1 or not raw.flags.c_contiguous or not 0<raw.size<=MAX_CHANNELS:
        raise ValueError('one bounded C-order native float32 row required')
    if not np.isfinite(raw).all():raise ValueError('nonfinite raw row')
    ascending=np.ascontiguousarray(raw[::-1]);out=np.empty_like(ascending)
    for start in range(0,raw.size,BLOCK):
        out[start:start+BLOCK]=legacy.normalize_float32_blocks_v0p6(ascending[start:start+BLOCK].reshape(1,-1))[0]
    return ascending,out


def make_scope(definition,window,interval,contract_sha256,kind):
    if kind not in ('local-fixture','telescope-remote'):raise ValueError('unknown source kind')
    start,stop=interval;header=definition['expected_header'];n=stop-start
    if (type(start) is not int or type(stop) is not int or start<0 or stop<=start
            or stop>header['dataset_shape'][2] or n>MAX_CHANNELS
            or header['dataset_shape'][1]!=1 or not 0<header['dataset_shape'][0]<=MAX_ROWS
            or header['dataset_dtype']!='float32' or header['foff_mhz']>=0):
        raise ValueError('invalid descending source dimensions')
    if resource_bound(n)>MAX_MODELLED_BYTES:raise ValueError('modelled buffer cap exceeded')
    core._frozen_sha256(contract_sha256,'source contract')
    geometry=core.native_geometry_from_extraction(fch1_mhz=header['fch1_mhz'],foff_mhz=header['foff_mhz'],channel_start=start,channel_stop=stop)
    return {'version':VERSION,'kind':kind,'contract_sha256':contract_sha256,'definition':definition,
            'window':window,'archive_interval':[start,stop],'geometry':asdict(geometry),
            'normalization':'ascending new-extraction origin; float32 median/MAD; blocks 4096',
            'modelled_buffer_bound_bytes':resource_bound(n)}


def observed_header(handle):
    dataset=handle['data'];attrs={**dict(handle.attrs),**dict(dataset.attrs)}
    def scalar(x):
        if isinstance(x,bytes):return x.decode('utf-8')
        return x.item() if isinstance(x,np.generic) else x
    return {'source_name':str(scalar(attrs['source_name'])),
        'src_raj_hours':float(attrs['src_raj']),'src_dej_deg':float(attrs['src_dej']),
        'tstart_mjd':float(attrs['tstart']),'tsamp_s':float(attrs['tsamp']),
        'dataset_shape':list(dataset.shape),'dataset_dtype':str(dataset.dtype),
        'fch1_mhz':float(attrs['fch1']),'foff_mhz':float(attrs['foff'])}


def validate_dataset(handle,scope):
    dataset=handle['data']
    if observed_header(handle)!=scope['definition']['expected_header']:
        raise ValueError('HDF5 header differs from frozen source')
    if (dataset.chunks is None or tuple(dataset.chunks[:2])!=(1,1)
            or np.prod(dataset.chunks)*np.dtype(dataset.dtype).itemsize>MAX_HDF5_CHUNK_BYTES):
        raise ValueError('unsupported or oversized HDF5 chunks')
    return dataset


def _check_row(directory,scope,row):
    path=Path(directory)/f'row{row:02d}.json'
    record=verify(json.loads(path.read_text()))
    if record['scope_sha256']!=digest(scope) or record['row']!=row:
        raise ValueError('row scope/order mismatch')
    n=scope['geometry']['channel_count'];arrays=[]
    for key in ('native','normalized'):
        p=Path(directory)/f'row{row:02d}.{key}.npy'
        if file_hash(p)!=record[key+'_file_sha256']:raise ValueError('row file hash mismatch')
        a=np.load(p,allow_pickle=False,mmap_mode='r')
        if a.dtype!=np.dtype('<f4') or a.shape!=(n,) or not a.flags.c_contiguous:
            raise ValueError('row dtype/shape/layout mismatch')
        if array_hash(a)!=record[key+'_sha256']:raise ValueError('row payload mismatch')
        arrays.append(a)
    ascending,normalized=normalize_native_row(arrays[0])
    if (array_hash(ascending)!=record['ascending_raw_sha256']
            or not np.array_equal(normalized,arrays[1])):
        raise ValueError('normalization reproduction mismatch')
    return record


def _extract_rows(handle,scope,directory):
    """Caller owns validated transport; never accepts caller-normalized arrays."""
    dataset=validate_dataset(handle,scope);directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    scope_path=directory/'scope.json'
    if scope_path.exists():
        if scope_path.read_bytes()!=core.canonical_json_bytes(scope):raise ValueError('restart scope changed')
    else:atomic_json(scope_path,scope)
    rows=[];resumed=0;start,stop=scope['archive_interval']
    for row in range(scope['definition']['expected_header']['dataset_shape'][0]):
        receipt=directory/f'row{row:02d}.json'
        if receipt.exists():
            rows.append(_check_row(directory,scope,row));resumed+=1;continue
        # Exact hyperslab and float32 dtype checked before any coercion.
        raw=dataset[row,0,start:stop]
        if not isinstance(raw,np.ndarray) or raw.dtype!=np.dtype('<f4') or raw.shape!=(stop-start,):
            raise ValueError('native hyperslab dtype/shape differs')
        raw=np.ascontiguousarray(raw)
        ascending,normalized=normalize_native_row(raw)
        record={'scope_sha256':digest(scope),'row':row,'native_sha256':array_hash(raw),
                'ascending_raw_sha256':array_hash(ascending),'normalized_sha256':array_hash(normalized)}
        for key,a in (('native',raw),('normalized',normalized)):
            p=directory/f'row{row:02d}.{key}.npy';atomic_npy(p,a);record[key+'_file_sha256']=file_hash(p)
        record=seal(record);atomic_json(receipt,record);rows.append(record)
        del raw,ascending,normalized
    return rows,resumed


def _complete(directory,scope,rows,transport_record):
    if len(rows)!=scope['definition']['expected_header']['dataset_shape'][0]:raise ValueError('incomplete row inventory')
    for i,r in enumerate(rows):
        verify(r)
        if r['row']!=i or r['scope_sha256']!=digest(scope):raise ValueError('row order/scope changed')
    if transport_record.get('kind')=='live-identity-bound-http-ranges':
        verify_transport_checkpoint(transport_record['checkpoint'],transport_record['identity'])
    receipt=seal({'scope':scope,'rows':rows,'transport':transport_record,'complete':True})
    path=Path(directory)/'source.json'
    if path.exists() and path.read_bytes()!=core.canonical_json_bytes(receipt):
        previous=verify(json.loads(path.read_text()))
        old=previous['transport'];new=transport_record
        if previous['scope']!=scope or previous['rows']!=rows or previous['complete'] is not True:
            raise ValueError('completed source receipt differs from restart')
        if (old.get('kind')!='live-identity-bound-http-ranges'
                or old.get('identity')!=new.get('identity')
                or old.get('range_plan_file_sha256')!=new.get('range_plan_file_sha256')):
            raise ValueError('completed transport identity differs')
        verify_transport_checkpoint(old['checkpoint'],old['identity'])
        if any(s not in new['checkpoint']['segments'] for s in old['checkpoint']['segments']):
            raise ValueError('restart lost an original checkpoint segment')
        # Other windows may extend this mirror. Retain the original published
        # product identity when its exact row inventory and transport ancestry survive.
        return previous
    atomic_json(path,receipt)
    return receipt


def rehydrate(directory,trusted_receipt_sha256,*,required_kind='telescope-remote'):
    core._frozen_sha256(trusted_receipt_sha256,'independently retained receipt')
    record=verify(json.loads((Path(directory)/'source.json').read_text()))
    if record['receipt_sha256']!=trusted_receipt_sha256 or record['scope']['kind']!=required_kind or record['complete'] is not True:
        raise ValueError('untrusted or wrong-kind source receipt')
    scope=record['scope']
    rebuilt=make_scope(scope['definition'],scope['window'],scope['archive_interval'],scope['contract_sha256'],scope['kind'])
    if scope!=rebuilt:raise ValueError('source scope is not canonical')
    if len(record['rows'])!=scope['definition']['expected_header']['dataset_shape'][0]:raise ValueError('missing rows')
    for i,row in enumerate(record['rows']):
        if row!=_check_row(directory,scope,i):raise ValueError('source row inventory differs')
    return record


def frozen_inputs(root):
    root=Path(root);path=root/'config/m43h_widened_source.json';cfg=json.loads(path.read_text())
    if np.__version__!=cfg['numpy_version']:raise ValueError('frozen NumPy runtime differs')
    for name,h in cfg['pinned_sha256'].items():
        if file_hash(root/name)!=h:raise ValueError('frozen source changed: '+name)
    metadata=json.loads((root/'config/hd156668b_m37_preflight.json').read_text())
    legacy.validate_m37_source_scan_definitions(metadata['scans'])
    preflight=verify(json.loads((root/'results_m43f_source_cache_preflight/preflight.json').read_text()),'result_sha256')
    qualified=verify(json.loads((root/'results_m43g_synthetic_transfer/qualification.json').read_text()),'result_sha256')
    if (qualified['result_sha256']!=cfg['m43g_result_sha256']
            or qualified['status']!='synthetic-numerical-transfer-qualified'
            or preflight['result_sha256']!=cfg['m43f_result_sha256']):raise ValueError('ancestor qualification changed')
    return cfg,file_hash(path),metadata,preflight


def dependency_status():
    return {name:importlib.util.find_spec(name) is not None for name in ('h5py','hdf5plugin')}


def extract_remote(root,scan_label,window,directory,mirror_root,*,spectral_access_authorized=False):
    if spectral_access_authorized is not True:raise ValueError('spectral access not authorized')
    cfg,contract,metadata,preflight=frozen_inputs(root)
    definition=next((d for d in metadata['scans'] if d['label']==scan_label),None)
    interval=next((d['proposed_interval'] for d in preflight['windows'] if d['window_id']==window),None)
    if definition is None or interval is None:raise ValueError('unknown scan/window')
    scope=make_scope(definition,window,interval,contract,'telescope-remote')
    missing=[k for k,v in dependency_status().items() if not v]
    if missing:raise ModuleNotFoundError('HDF5 dependencies unavailable: '+', '.join(missing))
    if cfg.get('hdf5_integration_qualified') is not True:
        raise RuntimeError('HDF5 integration gate is not qualified; no remote request made')
    from .transport_m43h import BoundedMirror, live_identity
    import h5py
    import hdf5plugin  # Registers the archive compression filter.
    import importlib.metadata
    runtime={'numpy':np.__version__,'h5py':h5py.__version__,'hdf5':h5py.version.hdf5_version,
             'hdf5plugin':importlib.metadata.version('hdf5plugin')}
    if runtime!=cfg['hdf5_runtime']:raise ValueError('qualified HDF5 runtime differs')
    identity=live_identity(definition['url'])
    if identity.size!=definition['expected_remote_size_bytes'] or identity.etag!=definition['expected_etag']:
        raise ValueError('live remote size/ETag mismatch')
    mirror_root=Path(mirror_root);mirror_root.mkdir(parents=True,exist_ok=True)
    with BoundedMirror(mirror_root/(scan_label+'.h5.sparse'),identity) as mirror:
        mirror.prefetch((old_transport.ByteRange(0,min(identity.size,old_transport.HDF5_METADATA_PREFIX_BYTES)),))
        mirror.seek(0)
        with h5py.File(mirror,'r',rdcc_nbytes=HDF5_CACHE_BYTES) as handle:
            dataset=validate_dataset(handle,scope)
            creation=dataset.id.get_create_plist()
            filters=[list(creation.get_filter(i)[:3]) for i in range(creation.get_nfilters())]
            ranges=old_transport.discover_hdf5_chunk_ranges(dataset,(tuple(interval),))
            plan=old_transport.range_plan_record(identity,dataset_shape=dataset.shape,dataset_chunks=dataset.chunks,channel_intervals=(tuple(interval),),ranges=ranges)
        plan_path=mirror_root/(scan_label+'.'+window+'.range-plan.json')
        plan_sha=old_transport.publish_range_plan(plan_path,plan)
        mirror.prefetch(ranges);mirror.seek(0)
        with h5py.File(mirror,'r',rdcc_nbytes=HDF5_CACHE_BYTES) as handle:
            rows,resumed=_extract_rows(handle,scope,directory)
        if any(old_transport._subtract_covered(r,mirror.covered_ranges) for r in ranges):raise ValueError('planned chunks not checkpointed')
        checkpoint=json.loads(mirror.checkpoint_path.read_text())
        proof={'kind':'live-identity-bound-http-ranges','identity':identity.record(),
               'range_plan_file_sha256':plan_sha,'checkpoint':checkpoint,'hdf5_runtime':runtime,
               'dataset_filters':filters}
        receipt=_complete(directory,scope,rows,proof)
    rehydrate(directory,receipt['receipt_sha256'])
    return receipt,{'resumed_rows':resumed,'range_plan':plan,'source_directory':str(directory)}
