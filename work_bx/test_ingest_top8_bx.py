"""Synthetic-only ingestion tests; no astronomical observations are opened."""
from pathlib import Path
import hashlib, importlib.util, pickle, tempfile, unittest
import numpy as np
spec=importlib.util.spec_from_file_location('ingest_top8_bx',Path(__file__).with_name('ingest_top8_bx.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def sample():
    return {'mlc'+str(i):{'data':np.ones((6,16,1,256),dtype=np.float32),
        'frequency':[1000.0,1001.0],'all_headers':[{'source_name':'synthetic','tstart':float(j),'nchans':256} for j in range(6)]}
        for i in range(1,9)}

class Evil:
    def __reduce__(self):return eval,('1+1',)

class IngestTests(unittest.TestCase):
    def test_synthetic_round_trip_and_opcode_only_inspection(self):
        raw=pickle.dumps(sample(),protocol=4)
        inspected=m.inspect_opcodes(raw)
        self.assertGreater(inspected['opcode_counts']['STACK_GLOBAL'],0)
        values=m.validate(m.unpickle_restricted(raw))
        self.assertEqual(set(values),{'mlc'+str(i) for i in range(1,9)})
        np.testing.assert_array_equal(values['mlc1'][0],np.ones((6,16,1,256),np.float32))
        self.assertTrue(values['mlc1'][2]['frequency_units_and_endpoint_semantics'].startswith('UNRESOLVED'))
    def test_forbidden_globals_and_object_dtype_fail_closed(self):
        with self.assertRaisesRegex(ValueError,'Forbidden pickle global'):
            m.unpickle_restricted(pickle.dumps(Evil(),protocol=4))
        with self.assertRaisesRegex(ValueError,'Unsafe dtype'):
            m.unpickle_restricted(pickle.dumps(np.array(['x'],dtype=object),protocol=4))
    def test_source_identity_and_trailing_payload(self):
        raw=pickle.dumps({'test':'synthetic'},protocol=4)
        expected={'bytes':len(raw),'git_blob_sha1':hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()}
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'fixture.pkl';p.write_bytes(raw)
            self.assertEqual(m.read_verified(p,expected)[0],raw)
            p.write_bytes(raw[:-1]+b'x')
            with self.assertRaisesRegex(ValueError,'Git blob differs'):m.read_verified(p,expected)
        with self.assertRaisesRegex(ValueError,'Trailing data'):m.inspect_opcodes(raw+b'x')
    def test_schema_nonfinite_negative_and_array_byte_guards(self):
        for value in (float('nan'),-1.):
            x=sample();x['mlc1']['data'][0,0,0,0]=value
            with self.assertRaisesRegex(ValueError,'finite and nonnegative'):
                m.validate(m.unpickle_restricted(pickle.dumps(x,protocol=4)))
        proxy=m.ArrayProxy()
        with self.assertRaisesRegex(ValueError,'byte count'):
            proxy.__setstate__((1,(1024,1024),np.dtype('f8'),False,b'1234'))
        with self.assertRaisesRegex(ValueError,'Unsafe dtype'):m.safe_dtype('O')
    def test_documented_header_variant_preserved_without_axis_inference(self):
        x=sample()
        for item in x.values():item['all_header']=item.pop('all_headers')
        y=m.validate(m.unpickle_restricted(pickle.dumps(x,protocol=4)))
        self.assertEqual(y['mlc8'][2]['header_key'],'all_header')
        self.assertEqual(y['mlc8'][2]['frequency_shape'],[2])

if __name__=='__main__':unittest.main()
