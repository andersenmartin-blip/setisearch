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

import test_bootstrap_gate as inherited
from test_bootstrap_gate import G, HERE, fixture, pin, proof_fixture


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
    def test_publication_source_paths_cannot_alias_or_include_activation(self):
        ch,proof,marker=proof_fixture(self.c); mr=G['canonical'](marker)
        for path in (proof['publication_files'][0]['repository_path'],G['ACTIVATION_REPOSITORY_PATH']):
            changed=copy.deepcopy(proof); changed['publication_files'][1]['repository_path']=path
            raw=G['canonical'](changed)
            with self.assertRaises(G['Refusal']): G['verify_publication'](self.c,ch,raw,G['digest'](raw),mr,G['digest'](mr))
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
    def test_same_pinned_error_class_merges_full_transport_refusal_into_wheel_receipt(self):
        import test_proxy_opener as fake
        modules=self.modules(); raw=b'HTTP/1.1 407 Proxy refused\r\nX-Synthetic: retained\r\n\r\n'
        h=fake.Harness(connect_raw=raw)
        opener=modules['proxy_opener'].make_simulation_opener(fake.FIXTURE,fake.ORIGINAL,'http://127.0.0.1:8080',fake.TRUST_BINDING,
            trust_read=h.trust_read,connect=h.connect,tls_wrap=h.tls_wrap,
            http_binding=modules['proxy_opener'].bounded_http_binding,budget=h.budget,deadline_callback=h.deadline)
        with tempfile.TemporaryDirectory() as directory:
            fd=os.open(directory,os.O_RDONLY|os.O_DIRECTORY)
            try:
                with self.assertRaises(modules['wheel_io'].WheelIOError) as caught:
                    modules['wheel_io'].acquire_wheel(fake.SPEC,fd,h.budget,h.deadline,opener=opener)
                self.assertEqual(Path(directory,fake.SPEC['filename']).read_bytes(),b'')
            finally: os.close(fd)
        self.assertEqual(base64.b64decode(caught.exception.receipt['received_connect_prefix_base64']),raw)
        self.assertEqual(caught.exception.receipt['received_connect_prefix_bytes'],len(raw))
        self.assertEqual(len(h.connect_calls),1); self.assertEqual(h.tls_calls,[])
        self.assertEqual(h.raw.close_count,1)
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
    def test_repeated_short_trust_requests_are_precharged_beyond_once_used_allowance(self):
        path=Path(self.temp.name)/'synthetic-trust'; path.write_bytes(b'abcde')
        requested=[]; charges=[6]; returned=[]; original=os.read
        budget=types.SimpleNamespace(operation_deadline=G['time'].monotonic_ns()+10**9,
            check=lambda:None,debit_read=charges.append,record_received=lambda n,kind:returned.append((n,kind)))
        def short(fd,n): requested.append(n); return original(fd,min(n,2))
        with mock.patch.object(G['os'],'read',side_effect=short):
            raw=G['read_precharged_trust'](str(path),6,budget)
        self.assertEqual(raw,b'abcde'); self.assertEqual(requested,[5,3,1,1])
        self.assertEqual(sum(charges),sum(requested)); self.assertEqual(sum(n for n,kind in returned),5)
    def test_plus_one_trust_object_includes_its_extra_eof_request(self):
        path=Path(self.temp.name)/'synthetic-trust'; path.write_bytes(b'abcdef')
        charges=[6]
        budget=types.SimpleNamespace(operation_deadline=G['time'].monotonic_ns()+10**9,
            check=lambda:None,debit_read=charges.append,record_received=lambda n,kind:None)
        self.assertEqual(G['read_precharged_trust'](str(path),6,budget),b'abcdef')
        self.assertEqual(charges,[6,1])


class ThreeWheelDispatch(unittest.TestCase):
    setUp=inherited.MockedPipelineGuards.setUp
    tearDown=inherited.MockedPipelineGuards.tearDown
    fake_pin=inherited.MockedPipelineGuards.fake_pin
    fake_compile=inherited.MockedPipelineGuards.fake_compile
    run_fixture=inherited.MockedPipelineGuards.run_fixture
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
    def test_expired_operation_preserves_raw_receipts_and_result_inside_original_whole_wall(self):
        current=[100_000_000_000]; raw=b'bounded refused raw body'
        def make_opener(*args,**kwargs):
            return types.SimpleNamespace(receipt={'status':'CLOSED_FAILED','evidence_domain':'SIMULATION_ONLY',
                'refused_body_receive_base64':base64.b64encode(raw).decode(),'refused_body_receive_bytes':len(raw)})
        def acquire(wheel,held,budget,deadline,opener=None):
            current[0]+=271*10**9
            try: deadline()
            except Exception as exc:
                exc.receipt={'status':'CLOSED_FAILED','synthetic_raw_base64':base64.b64encode(raw).decode()}
                raise
            raise AssertionError('operation deadline must refuse')
        def modules(*args):
            return {'wheel_io':types.SimpleNamespace(acquire_wheel=acquire),
                'proxy_opener':types.SimpleNamespace(make_opener=make_opener,bounded_http_binding=lambda *a:None),
                'proxy_contract':types.SimpleNamespace(endpoint=lambda value:{'host':'127.0.0.1','port':12345,'scheme':'http'})}
        with mock.patch.object(G['time'],'monotonic_ns',side_effect=lambda:current[0]), mock.patch.dict(G,{
            'pin_read':self.fake_pin,'compile_verified':self.fake_compile,
            'validate_transport_descriptor':lambda *a:{'proxy_selection':{'environment_name':'PIP_PROXY'},'trust_binding':{}},
            'compile_transport_modules':modules,'native_transport_bindings':lambda *a:(lambda *a:None,lambda *a:None)}):
            result=self.run_fixture()
        self.assertEqual(result['report']['status'],'CLOSED_FAILED')
        self.assertEqual(result['report']['selected_elapsed_before_final_report_seconds'],271)
        self.assertEqual(result['report']['terminal_wall_reserve_seconds'],30)
        self.assertTrue((self.root/'supervisor-result.json').is_file())
        transport=json.loads((self.root/'transport-numpy.json').read_bytes())
        acquisition=json.loads((self.root/'acquisition-numpy.json').read_bytes())
        self.assertEqual(base64.b64decode(transport['refused_body_receive_base64']),raw)
        self.assertEqual(base64.b64decode(acquisition['synthetic_raw_base64']),raw)


if __name__=='__main__': unittest.main(verbosity=2)
