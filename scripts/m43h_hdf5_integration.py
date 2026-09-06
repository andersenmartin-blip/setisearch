#!/usr/bin/env python3
"""Actual local HDF5/codec integration over the bounded file interface.

HTTP replies are in-process fixtures, explicitly not telescope responses.
"""
import importlib.metadata
import json
from pathlib import Path
import tempfile
from unittest.mock import patch
import h5py
import hdf5plugin
import numpy as np
from m43h_fixture import fixture_values
from m43g_reference import sorted_reference
from seti_repeater import source_m43h as src
from seti_repeater import transport_m43h as net
from seti_repeater import http_range_v0p6 as old

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results_m43h_widened_source'


class Response:
    def __init__(self,data,headers):self.data=data;self.headers=headers;self.status=206
    def getcode(self):return self.status
    def read(self,n):return self.data[:n]
    def __enter__(self):return self
    def __exit__(self,*args):pass


def run():
    records=[]
    for name,compression in [('gzip',{'compression':'gzip','compression_opts':1}),
                             ('bitshuffle_lz4',dict(hdf5plugin.Bitshuffle(cname='lz4')))]:
        with tempfile.TemporaryDirectory() as td:
            directory=Path(td)
            definition={'label':'codec_fixture','url':'https://example.invalid/m43h-'+name+'.h5',
                'expected_remote_size_bytes':0,'expected_etag':'"local-'+name+'"',
                'expected_header':{'source_name':'local_fixture','src_raj_hours':1.,'src_dej_deg':2.,
                'tstart_mjd':50000.,'tsamp_s':3.,'dataset_shape':[3,1,20000],
                'dataset_dtype':'float32','fch1_mhz':1.,'foff_mhz':-0.000001}}
            original=np.stack([fixture_values(r,0,20000) for r in range(3)])[:,None,:]
            file=directory/'source.h5'
            with h5py.File(file,'w') as h:
                h.create_dataset('data',data=original,chunks=(1,1,4096),**compression)
                h.attrs.update({'source_name':'local_fixture','src_raj':1.,'src_dej':2.,'tstart':50000.,'tsamp':3.,'fch1':1.,'foff':-0.000001})
            payload=file.read_bytes();definition['expected_remote_size_bytes']=len(payload)
            identity=old.RemoteIdentity(definition['url'],len(payload),definition['expected_etag'])
            scope=src.make_scope(definition,'codec_fixture',(501,4604),'1'*64,'local-fixture')
            calls=[]
            def server(req,timeout):
                a,b=map(int,req.headers['Range'].removeprefix('bytes=').split('-'));calls.append((a,b+1))
                return Response(payload[a:b+1],{'Content-Range':f'bytes {a}-{b}/{len(payload)}','ETag':identity.etag})
            real_atomic=src.atomic_json
            def interrupt_after_row(path,record):
                real_atomic(path,record)
                if Path(path).name=='row00.json':raise InterruptedError('intentional codec fixture interruption')
            store=directory/'rows';mirror_path=directory/'mirror'
            with patch.object(net,'urlopen',side_effect=server):
                with net.BoundedMirror(mirror_path,identity) as mirror:
                    with h5py.File(mirror,'r',rdcc_nbytes=src.HDF5_CACHE_BYTES) as h:
                        dataset=src.validate_dataset(h,scope)
                        ranges=old.discover_hdf5_chunk_ranges(dataset,((501,4604),))
                        filter_ids=[dataset.id.get_create_plist().get_filter(i)[0] for i in range(dataset.id.get_create_plist().get_nfilters())]
                        with patch.object(src,'atomic_json',side_effect=interrupt_after_row):
                            try:src._extract_rows(h,scope,store)
                            except InterruptedError:pass
                            else:raise RuntimeError('codec interruption not reached')
                if (store/'source.json').exists():raise RuntimeError('incomplete codec source was completed')
                with net.BoundedMirror(mirror_path,identity) as mirror:
                    mirror.prefetch(ranges);mirror.seek(0)
                    with h5py.File(mirror,'r',rdcc_nbytes=src.HDF5_CACHE_BYTES) as h:
                        rows,resumed=src._extract_rows(h,scope,store)
                    if resumed!=1:raise RuntimeError('codec restart count differs')
                    receipt=src._complete(store,scope,rows,{'kind':'local-HDF5-over-simulated-HTTP','codec':name})
                request_count=len(calls)
                with net.BoundedMirror(mirror_path,identity) as mirror:
                    with h5py.File(mirror,'r',rdcc_nbytes=src.HDF5_CACHE_BYTES) as h:
                        rows,reused=src._extract_rows(h,scope,store)
                        bad_scope=json.loads(json.dumps(scope));bad_scope['definition']['expected_header']['fch1_mhz']+=1
                        try:src.validate_dataset(h,bad_scope)
                        except ValueError:pass
                        else:raise RuntimeError('changed header accepted')
                if reused!=3 or len(calls)!=request_count:raise RuntimeError('completed codec restart made new requests')
            src.rehydrate(store,receipt['receipt_sha256'],required_kind='local-fixture')
            for row in range(3):
                native=np.load(store/f'row{row:02d}.native.npy',allow_pickle=False)
                norm=np.load(store/f'row{row:02d}.normalized.npy',allow_pickle=False)
                np.testing.assert_array_equal(native,original[row,0,501:4604])
                np.testing.assert_array_equal(norm,sorted_reference(native[::-1].reshape(1,-1))[0])
            records.append({'codec':name,'filter_ids':filter_ids,'hdf5_rows':3,'native_channels':4103,
                'interrupted_after_rows':1,'resumed_rows':resumed,'completed_restart_reused_rows':reused,
                'completed_restart_new_http_requests':len(calls)-request_count,'native_and_sorted_normalization_exact':True,
                'wrong_header_rejected':True,'actual_hdf5_decode':True,'http_is_local_fixture':True,
                'source_receipt_sha256':receipt['receipt_sha256']})
    runtime={'numpy':np.__version__,'h5py':h5py.__version__,'hdf5':h5py.version.hdf5_version,'hdf5plugin':importlib.metadata.version('hdf5plugin')}
    paths=['src/seti_repeater/source_m43h.py','src/seti_repeater/transport_m43h.py','scripts/m43h_hdf5_integration.py']
    result=src.seal({'status':'local-hdf5-codec-integration-qualified','runtime':runtime,'checks':records,
        'implementation_sha256':{p:src.file_hash(ROOT/p) for p in paths},'telescope_requests':0},'result_sha256')
    OUT.mkdir(exist_ok=True);src.atomic_json(OUT/'hdf5_integration.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':run()
