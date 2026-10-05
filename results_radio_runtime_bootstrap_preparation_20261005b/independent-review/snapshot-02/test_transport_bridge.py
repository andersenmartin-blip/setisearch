"""Focused B admission/bridge tests; no socket, SSLContext, install or scientific import."""
import base64
import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock

from test_bootstrap_gate import G, HERE, fixture, pin, proof_fixture, MockedPipelineGuards


def descriptor(contract):
    trust=pin(Path(contract['plan_path']).parent/'synthetic-trust.pem',b'synthetic trust')
    contract['runtime_pins']=sorted(contract['runtime_pins']+[trust],key=lambda row:row['path'])
    return {'schema':G['TRANSPORT_SCHEMA'],
        'proxy_selection':{'environment_name':'PIP_PROXY','policy':'canonical-credential-free-loopback-http-v1'},
        'trust_binding':{key:trust[key] for key in ('path','bytes','sha256')},
        'tunnel_destination':{'host':'files.pythonhosted.org','port':443}}


class TransportAdmission(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)/'fresh'
        self.root.mkdir(mode=0o700); self.c=fixture(self.root)
    def tearDown(self): self.temp.cleanup()
    def validate(self,c):
        raw=G['canonical'](c); return G['validate_contract'](raw,G['digest'](raw))
    def test_retired_A_identity_is_rejected_before_any_transport(self):
        self.c['bootstrap_identity']=next(iter(G['RETIRED_BOOTSTRAP_IDENTITIES']))
        with self.assertRaisesRegex(G['Refusal'],'retired'): self.validate(self.c)
    def test_all_transport_sources_and_detached_descriptor_pin_are_required(self):
        for key in ('proxy_contract_path','proxy_opener_path','native_bindings_path','transport_descriptor_path'):
            c=copy.deepcopy(self.c); c['source_pins']=[p for p in c['source_pins'] if p['path']!=c[key]]
            with self.assertRaises(G['Refusal']): self.validate(c)
        c=copy.deepcopy(self.c); c['transport_descriptor_sha256']='0'*64
        with self.assertRaises(G['Refusal']): self.validate(c)
    def test_selected_inputs_cannot_live_inside_fresh_artifact_root(self):
        c=copy.deepcopy(self.c); c['runtime_pins'].append(pin(self.root/'bad'))
        c['runtime_pins'].sort(key=lambda p:p['path'])
        with self.assertRaisesRegex(G['Refusal'],'overlap'): self.validate(c)
    def test_descriptor_requires_exact_policy_and_selected_trust_pin(self):
        d=descriptor(self.c); raw=G['canonical'](d)
        self.assertEqual(G['validate_transport_descriptor'](raw,G['digest'](raw),self.c),d)
        for mutation in (lambda o:o['proxy_selection'].update(port=12345),
                         lambda o:o['proxy_selection'].update(environment_name='HTTPS_PROXY'),
                         lambda o:o['trust_binding'].update(sha256='0'*64),
                         lambda o:o['tunnel_destination'].update(host='other.example')):
            bad=copy.deepcopy(d); mutation(bad); raw=G['canonical'](bad)
            with self.assertRaises(G['Refusal']): G['validate_transport_descriptor'](raw,G['digest'](raw),self.c)
    def modules(self):
        keys=('wheel_io_path','proxy_contract_path','proxy_opener_path','native_bindings_path')
        for key in keys: self.c[key]=str(HERE/Path(self.c[key]).name)
        verified={self.c[key]:Path(self.c[key]).read_bytes() for key in keys}
        return G['compile_transport_modules'](verified,self.c)
    def test_pinned_module_bridge_ignores_hostile_ambient_local_modules_and_is_inert(self):
        original_import=G['builtins'].__import__; native_imports=[]
        def forbid_native(name,*args,**kwargs):
            if name in ('socket','ssl','h5py','numpy','hdf5plugin'):
                native_imports.append(name); raise AssertionError('native import during inert compilation')
            return original_import(name,*args,**kwargs)
        hostile=types.SimpleNamespace(WheelIOError=object,HOST='evil.invalid')
        with mock.patch.dict(sys.modules,{'wheel_io':hostile,'proxy_contract':hostile,'proxy_opener':hostile}), mock.patch.object(G['builtins'],'__import__',side_effect=forbid_native):
            modules=self.modules()
        self.assertEqual(native_imports,[])
        self.assertIs(modules['proxy_opener'].WheelIOError,modules['wheel_io'].WheelIOError)
        self.assertIs(modules['proxy_opener'].proxy_contract,modules['proxy_contract'])
        self.assertEqual(modules['native_bindings'].HOST,'files.pythonhosted.org')
        self.assertIsNot(sys.modules.get('wheel_io'),modules['wheel_io'])
    def test_dynamic_proxy_is_read_exactly_once_and_never_replaced(self):
        d=descriptor(self.c); modules=self.modules(); calls=[]
        def selected(name):
            calls.append(name); return 'http://127.0.0.1:37445' if len(calls)==1 else 'http://127.0.0.1:45781'
        selected_receipt=G['select_proxy_endpoint'](d,self.c,modules,selected)
        self.assertEqual(calls,['PIP_PROXY'])
        self.assertEqual(selected_receipt['selected_proxy_url'],'http://127.0.0.1:37445')
        self.assertEqual(selected_receipt['endpoint']['port'],37445)
        for value in (None,'http://127.0.0.1:00123','http://u:p@127.0.0.1:12345','https://127.0.0.1:12345','http://localhost:12345','http://127.0.0.1:12345/'):
            with self.assertRaises(Exception): G['select_proxy_endpoint'](d,self.c,modules,lambda name:value)
    def test_actual_receipt_binds_scope_retains_raw_and_keeps_native_qualification_false(self):
        raw=b'HTTP/1.1 407 Refused\r\n\r\n'
        original={'schema':'radio-proxy-injected-integration-v1','status':'CLOSED_FAILED',
            'evidence_domain':'SIMULATION_ONLY','received_connect_prefix_base64':base64.b64encode(raw).decode(),
            'peer_verification_native_qualified':False,'tls_resource_custody_qualified':False,
            'runtime_qualification':'PENDING_ACTUAL_NATIVE_CUSTODY'}
        opener=types.SimpleNamespace(receipt=original)
        receipt=G['retained_transport_receipt'](opener,self.c['wheels'][0],self.c,'1'*64,'2'*64,{'selected_proxy_url':'http://127.0.0.1:12345'})
        self.assertEqual(receipt['evidence_domain'],'ACTUAL_PACKAGE_BOOTSTRAP_ONLY')
        self.assertEqual(receipt['adapter_emitted_evidence_domain'],'SIMULATION_ONLY')
        self.assertEqual(base64.b64decode(receipt['received_connect_prefix_base64']),raw)
        self.assertFalse(receipt['peer_verification_native_qualified']); self.assertFalse(receipt['tls_resource_custody_qualified'])
        self.assertEqual(original['evidence_domain'],'SIMULATION_ONLY')
        self.assertEqual(G['CEILINGS']['artifact_bytes'],1536*1024**2)
        self.assertGreater(G['TRANSPORT_RECEIPT_BYTES'],len(G['canonical'](receipt|{'refused_body_receive_base64':base64.b64encode(b'x'*1024**2).decode()})))


class ThreeWheelDispatch(MockedPipelineGuards):
    def test_three_fresh_single_use_openers_are_passed_and_retained_before_offline_child(self):
        openers=[]; calls=[]
        def make_opener(*args,**kwargs):
            item=types.SimpleNamespace(receipt={'status':'SIMULATION_ONLY','evidence_domain':'SIMULATION_ONLY',
                'peer_verification_native_qualified':False,'tls_resource_custody_qualified':False})
            openers.append(item); return item
        def acquire(wheel,held,budget,deadline,opener=None):
            self.assertIs(opener,openers[-1]); calls.append(opener)
            fd=os.open(wheel['filename'],os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600,dir_fd=held)
            try: os.write(fd,b'x'*16)
            finally: os.close(fd)
            return {'status':'SYNTHETIC_FIXTURE_ONLY','filename':wheel['filename']}
        def modules(*args):
            return {'wheel_io':types.SimpleNamespace(acquire_wheel=acquire,inspect_wheel=lambda *a:{'members':[]}),
                'proxy_opener':types.SimpleNamespace(make_opener=make_opener,bounded_http_binding=lambda *a:None),
                'proxy_contract':types.SimpleNamespace(endpoint=lambda value:{'host':'127.0.0.1','port':12345,'scheme':'http'})}
        with mock.patch.dict(G,{'pin_read':self.fake_pin,'compile_verified':self.fake_compile,
            'validate_transport_descriptor':lambda *a:{'proxy_selection':{'environment_name':'PIP_PROXY'},'trust_binding':{}},
            'compile_transport_modules':modules,'native_transport_bindings':lambda *a:(lambda *a:None,lambda *a:None),
            'prospective_install':lambda *a:{'synthetic_only':True},
            'supervise':lambda *a:{'failure':'synthetic stop before installer'}}):
            result=self.run_fixture()
        self.assertEqual(len(openers),3); self.assertEqual(len({id(item) for item in openers}),3)
        self.assertEqual(calls,openers); self.assertEqual(result['report']['transport_receipt_count'],3)
        self.assertEqual(result['report']['status'],'CLOSED_FAILED')
        for wheel in self.c['wheels']:
            raw=(self.root/('transport-'+wheel['name']+'.json')).read_bytes(); receipt=json.loads(raw)
            self.assertEqual(receipt['wheel_filename'],wheel['filename'])
            self.assertFalse(receipt['peer_verification_native_qualified'])
        self.assertFalse((self.root/'child.stdout.raw').exists())


if __name__=='__main__': unittest.main(verbosity=2)
