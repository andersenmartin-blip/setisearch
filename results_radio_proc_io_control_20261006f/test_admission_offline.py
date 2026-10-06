"""Pure immutable scope/admission refusal fixtures; no subprocess/actual root."""
import copy,hashlib,importlib.util,json
from pathlib import Path
import unittest
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('f_admission_gate',HERE/'runtime_gate.py')
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
def fixture():
    keys=('gate_source_path','launcher_source_path','supervisor_source_path','observer_source_path',
        'control_source_path','payload_path','phase2_path')
    paths={k:'/inert/'+k for k in keys}
    pins=[dict(path=p,bytes=1,sha256='a'*64,mode=0o644) for p in paths.values()]
    published={str(i):dict(local_path=p['path'],raw_bytes=p['bytes'],raw_sha256=p['sha256']) for i,p in enumerate(pins)}
    freeze=dict(paths,schema=gate.SCHEMA,identity=gate.IDENTITY,limits=gate.LIMITS,single_use=True,
        automatic_successor=False,engineering_only=True,network=False,install=False,hdf5_dataset_access=False,
        scientific_authority=False,source_pins=pins,published_sources=published,
        runtime_pins=[dict(path='/inert/'+k) for k in ('python','guard','seal')],
        python_executable='/inert/python',guard_path='/inert/guard',exec_seal_path='/inert/seal',marker_repository_path='config/F.activate.json')
    marker=dict(schema='radio-proc-io-control-activation-v1',identity=gate.IDENTITY,freeze_sha256='f'*64,
        single_use=True,automatic_successor=False,prepared_commit='b'*40,prepared_tree='c'*40)
    proof=dict(schema='radio-proc-io-control-publication-proof-v1',repository='andersenmartin-blip/setisearch',
        branch='m43-support-qualification',preparation_commit='b'*40,preparation_tree='c'*40,
        activation_commit='d'*40,sole_parent='b'*40,changed_paths=['config/F.activate.json'],
        marker_sha256='e'*64,full_preparation_readback_exact=True,marker_readback_exact=True,source_readbacks=published)
    return freeze,proof,marker
class Admission(unittest.TestCase):
    def admit(self,items):return gate.admit(*items,'f'*64,'e'*64)
    def test_exact_inert_scope_admits(self):self.admit(fixture())
    def test_authority_changed_or_scope_reused_refuses(self):
        for key in ('network','install','scientific_authority','hdf5_dataset_access','automatic_successor'):
            items=fixture();items[0][key]=True
            with self.subTest(key=key),self.assertRaises(gate.Refusal):self.admit(items)
        items=fixture();items[0]['identity']='radio-runtime-metadata-capture-20261005e'
        with self.assertRaises(gate.Refusal):self.admit(items)
    def test_changed_limits_refuse(self):
        items=fixture();items[0]['limits']=dict(gate.LIMITS,child_dispatches=2)
        with self.assertRaises(gate.Refusal):self.admit(items)
    def test_marker_only_chain_and_complete_readbacks_required(self):
        for key,value in (('sole_parent','x'*40),('preparation_tree','x'*40),('changed_paths',['other']),
            ('full_preparation_readback_exact',False),('marker_readback_exact',False),('source_readbacks',{})):
            items=fixture();items[1][key]=value
            with self.subTest(key=key),self.assertRaises(gate.Refusal):self.admit(items)
    def test_missing_executed_source_and_binary_refused(self):
        items=fixture();items[0]['source_pins']=items[0]['source_pins'][1:]
        with self.assertRaises(gate.Refusal):self.admit(items)
        items=fixture();items[0]['runtime_pins']=[]
        with self.assertRaises(gate.Refusal):self.admit(items)
    def test_duplicate_or_mismatched_publication_sources_refused(self):
        items=fixture();items[0]['source_pins'].append(items[0]['source_pins'][0])
        with self.assertRaises(gate.Refusal):self.admit(items)
        items=fixture();items[0]['published_sources']['0']['raw_sha256']='z'*64
        with self.assertRaises(gate.Refusal):self.admit(items)
    def test_raw_json_hash_and_duplicate_keys_refused(self):
        raw=b'{"a":1,"a":2}'
        with self.assertRaises(gate.Refusal):gate.json_checked(raw,hashlib.sha256(raw).hexdigest())
        with self.assertRaises(gate.Refusal):gate.json_checked(b'{}','0'*64)
if __name__=='__main__':unittest.main(verbosity=2)
