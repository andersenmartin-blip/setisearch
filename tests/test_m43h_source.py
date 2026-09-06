import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from m43h_fixture import FixtureHandle
from m43g_reference import sorted_reference
from seti_repeater import source_m43h as src
from seti_repeater import transport_m43h as net
from seti_repeater import http_range_v0p6 as old


def definition():
    return {'label':'fixture_on','url':'https://example.invalid/fixture.h5','expected_remote_size_bytes':10000,
        'expected_etag':'"fixture"','expected_header':{'source_name':'fixture','src_raj_hours':1.,'src_dej_deg':2.,
        'tstart_mjd':50000.,'tsamp_s':3.,'dataset_shape':[3,1,20000],'dataset_dtype':'float32','fch1_mhz':1.,'foff_mhz':-0.000001}}


def scope():return src.make_scope(definition(),'fixture',(501,4604),'1'*64,'local-fixture')


class SourceTests(unittest.TestCase):
    def test_missing_dependencies_or_unqualified_hdf5_blocks_live_entry(self):
        frozen=({'hdf5_integration_qualified':False},'1'*64,{'scans':[definition()]},
                {'windows':[{'window_id':'fixture','proposed_interval':[501,4604]}]})
        with patch.object(src,'frozen_inputs',return_value=frozen),patch.object(net,'live_identity',side_effect=AssertionError('network touched')):
            with patch.object(src,'dependency_status',return_value={'h5py':False,'hdf5plugin':False}):
                with self.assertRaises(ModuleNotFoundError):src.extract_remote('/fixture','fixture_on','fixture','/fixture','/fixture',spectral_access_authorized=True)
            with patch.object(src,'dependency_status',return_value={'h5py':True,'hdf5plugin':True}):
                with self.assertRaisesRegex(RuntimeError,'integration gate'):src.extract_remote('/fixture','fixture_on','fixture','/fixture','/fixture',spectral_access_authorized=True)

    def test_exact_hyperslab_reversal_sort_normalization_and_rehydration(self):
        with tempfile.TemporaryDirectory() as d:
            h=FixtureHandle(definition());rows,resumed=src._extract_rows(h,scope(),d)
            self.assertEqual(resumed,0);self.assertEqual(h.dataset.requests,[(i,0,501,4604) for i in range(3)])
            receipt=src._complete(d,scope(),rows,{'kind':'fixture-no-network'})
            for i in range(3):
                raw=np.load(Path(d)/f'row{i:02d}.native.npy');actual=np.load(Path(d)/f'row{i:02d}.normalized.npy')
                np.testing.assert_array_equal(actual,sorted_reference(raw[::-1].reshape(1,-1))[0])
            self.assertEqual(src.rehydrate(d,receipt['receipt_sha256'],required_kind='local-fixture'),receipt)
            with self.assertRaises(ValueError):src.rehydrate(d,receipt['receipt_sha256'])
            with self.assertRaises(ValueError):src.rehydrate(d,'0'*64,required_kind='local-fixture')

    def test_interruption_resumes_only_complete_rows(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(InterruptedError):src._extract_rows(FixtureHandle(definition(),fail_after=1),scope(),d)
            self.assertFalse((Path(d)/'source.json').exists())
            h=FixtureHandle(definition());rows,resumed=src._extract_rows(h,scope(),d)
            self.assertEqual(resumed,1);self.assertEqual([r[0] for r in h.dataset.requests],[1,2])
            first=src._complete(d,scope(),rows,{'kind':'fixture-no-network'})
            h=FixtureHandle(definition());rows,resumed=src._extract_rows(h,scope(),d)
            self.assertEqual(resumed,3);self.assertEqual(h.dataset.requests,[])
            self.assertEqual(src._complete(d,scope(),rows,{'kind':'fixture-no-network'}),first)

    def test_corrupt_row_file_or_receipt_is_rejected_on_restart(self):
        for target in ('row00.native.npy','row00.normalized.npy','row00.json'):
            with tempfile.TemporaryDirectory() as d:
                src._extract_rows(FixtureHandle(definition()),scope(),d)
                p=Path(d)/target;b=bytearray(p.read_bytes());b[-2]^=1;p.write_bytes(b)
                with self.assertRaises((ValueError,json.JSONDecodeError)):src._extract_rows(FixtureHandle(definition()),scope(),d)

    def test_same_byte_wrong_dtype_and_wrong_shape_rejected(self):
        for value in (np.arange(20,dtype='<u4'),np.ones((1,20),dtype='<f4')):
            with self.assertRaises(ValueError):src.normalize_native_row(value)
        for value in (np.full(20,np.nan,dtype='<f4'),np.full(20,np.inf,dtype='<f4')):
            with self.assertRaises(ValueError):src.normalize_native_row(value)

    def test_header_shape_chunk_and_scope_mismatches_fail_before_rows(self):
        for change in ('header','shape','chunk'):
            with tempfile.TemporaryDirectory() as d:
                h=FixtureHandle(definition())
                if change=='header':h.attrs['fch1']+=1
                if change=='shape':h.dataset.shape=(3,2,20000)
                if change=='chunk':h.dataset.chunks=(1,1,10_000_000)
                with self.assertRaises(ValueError):src._extract_rows(h,scope(),d)
                self.assertEqual(h.dataset.requests,[])
        with tempfile.TemporaryDirectory() as d:
            src._extract_rows(FixtureHandle(definition()),scope(),d)
            s=scope();s['window']='other'
            with self.assertRaises(ValueError):src._extract_rows(FixtureHandle(definition()),s,d)

    def test_incomplete_or_reordered_inventory_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            rows,_=src._extract_rows(FixtureHandle(definition()),scope(),d)
            for bad in (rows[:2],rows[::-1]):
                with self.assertRaises(ValueError):src._complete(d,scope(),bad,{'kind':'fixture'})

    def test_bad_dimensions_and_unapproved_entry_fail_before_network(self):
        for interval in ((-1,100),(100,100),(0,20001),(True,10)):
            with self.assertRaises(ValueError):src.make_scope(definition(),'x',interval,'1'*64,'local-fixture')
        with patch.object(net,'live_identity',side_effect=AssertionError('network touched')):
            with self.assertRaises(ValueError):src.extract_remote('/missing','x','x','/missing','/missing')

    def test_completed_receipt_survives_growth_of_verified_mirror(self):
        with tempfile.TemporaryDirectory() as d:
            rows,_=src._extract_rows(FixtureHandle(definition()),scope(),d)
            segment={'start':0,'stop':100,'sha256':'2'*64}
            identity={'url':'https://example.invalid/fixture','size':1000,'etag':'"fixture"'}
            def checkpoint(segments):
                b={'artifact_type':old.CHECKPOINT_ARTIFACT,'schema_version':1,'remote':identity,'segments':segments}
                return {**b,'checkpoint_sha256':old._sha256_bytes(old._canonical_json_bytes(b))}
            proof={'kind':'live-identity-bound-http-ranges','identity':identity,'range_plan_file_sha256':'3'*64,
                   'checkpoint':checkpoint([segment])}
            first=src._complete(d,scope(),rows,proof)
            grown=copy.deepcopy(proof);grown['checkpoint']=checkpoint([segment,{'start':100,'stop':200,'sha256':'4'*64}])
            self.assertEqual(src._complete(d,scope(),rows,grown),first)


class Response(io.BytesIO):
    def __init__(self,payload,headers,status=206):
        super().__init__(payload);self.headers=headers;self.status=status;self.read_sizes=[]
    def getcode(self):return self.status
    def read(self,n=-1):self.read_sizes.append(n);return super().read(n)


class TransportTests(unittest.TestCase):
    def test_bounded_requests_and_restart_hashes(self):
        payload=bytes(range(256))*100000;calls=[]
        def server(req,timeout):
            a,b=map(int,req.headers['Range'].removeprefix('bytes=').split('-'));calls.append((a,b+1))
            return Response(payload[a:b+1],{'Content-Range':f'bytes {a}-{b}/{len(payload)}','ETag':'"x"'})
        identity=old.RemoteIdentity('https://example.invalid/x',len(payload),'"x"')
        with tempfile.TemporaryDirectory() as d,patch.object(net,'urlopen',side_effect=server):
            path=Path(d)/'mirror'
            with net.BoundedMirror(path,identity) as mirror:
                mirror.prefetch((old.ByteRange(0,len(payload)),))
                self.assertTrue(all(b-a<=net.MAX_REQUEST for a,b in calls))
                self.assertEqual(mirror.downloaded_bytes,len(payload))
                with self.assertRaises(ValueError):mirror.read()
                with self.assertRaises(ValueError):mirror.read(net.MAX_READ+1)
            first=len(calls)
            with net.BoundedMirror(path,identity) as mirror:mirror.prefetch((old.ByteRange(0,len(payload)),))
            self.assertEqual(first,len(calls))
            with path.open('r+b') as f:f.seek(100);f.write(b'wrong')
            with self.assertRaises(RuntimeError):net.BoundedMirror(path,identity)

    def test_wrong_identity_rejected_before_body_and_length_is_bounded(self):
        identity=old.RemoteIdentity('https://example.invalid/x',1000,'"x"')
        with tempfile.TemporaryDirectory() as d,net.BoundedMirror(Path(d)/'x',identity) as mirror:
            for headers,status in (({'Content-Range':'bytes 0-9/1000','ETag':'"other"'},206),({},200)):
                response=Response(b'x'*1000,headers,status)
                with patch.object(net,'urlopen',return_value=response):
                    with self.assertRaises(ValueError):mirror._request(old.ByteRange(0,10))
                self.assertEqual(response.read_sizes,[])
            response=Response(b'x'*1000,{'Content-Range':'bytes 0-9/1000','ETag':'"x"'})
            with patch.object(net,'urlopen',return_value=response):
                with self.assertRaises(ValueError):mirror._request(old.ByteRange(0,10))
            self.assertEqual(response.read_sizes,[11])


if __name__=='__main__':unittest.main()
