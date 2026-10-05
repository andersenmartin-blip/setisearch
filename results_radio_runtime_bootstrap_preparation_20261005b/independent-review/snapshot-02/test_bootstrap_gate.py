"""Synthetic guards/processes only: no genuine pip, wheel, download or bootstrap."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest import mock

HERE=Path(__file__).resolve().parent
G={ '__name__':'_synthetic_bootstrap_gate', '__file__':str(HERE/'bootstrap_gate.py') }
exec(compile((HERE/'bootstrap_gate.py').read_bytes(),G['__file__'],'exec'),G)


def pin(path,raw=b'x'):
    return {'path':str(path),'bytes':len(raw),'sha256':G['digest'](raw),'mode':'0644'}


def fixture(root):
    python=str(Path(sys.executable).resolve())
    input_root=root.parent/(root.name+'-inputs')
    sources=sorted([pin(HERE/'bootstrap_gate.py')]+[pin(input_root/name) for name in ('capture_basis.py','wheel_io.py','plan.json','proxy_contract.py','proxy_opener.py','native_bindings.py','transport-descriptor.json')],key=lambda p:p['path'])
    seed=pin(input_root/'seed'/'pip'/'__main__.py')|{'relative_path':'pip/__main__.py'}
    wheels=[]
    for name,version in G['EXPECTED_VERSIONS'].items():
        wheels.append({'name':name,'version':version,'filename':name+'-'+version+'-py3-none-any.whl',
            'url':'https://files.pythonhosted.org/packages/'+name+'.whl','bytes':16,'sha256':hashlib.sha256(name.encode()).hexdigest(),'tags':['py3-none-any']})
    st=root.stat()
    return {'schema':G['SCHEMA'],'bootstrap_identity':'7'*64,'evidence_domain':'synthetic-test-fixture',
        'source_pins':sources,'runtime_pins':sorted([pin(python),{k:seed[k] for k in G['PIN_KEYS']}],key=lambda p:p['path']),
        'seed_pins':[seed],'python_executable':python,'python_sha256':pin(python)['sha256'],
        'attribution_basis_path':str(input_root/'capture_basis.py'),'wheel_io_path':str(input_root/'wheel_io.py'),
        'plan_path':str(input_root/'plan.json'),'plan_sha256':pin(input_root/'plan.json')['sha256'],
        'proxy_contract_path':str(input_root/'proxy_contract.py'),'proxy_opener_path':str(input_root/'proxy_opener.py'),
        'native_bindings_path':str(input_root/'native_bindings.py'),'transport_descriptor_path':str(input_root/'transport-descriptor.json'),
        'transport_descriptor_sha256':pin(input_root/'transport-descriptor.json')['sha256'],
        'wheel_lock_utf8':''.join(w['name']+'=='+w['version']+' --hash=sha256:'+w['sha256']+'\n' for w in wheels),
        'output_root':str(root),'output_root_identity':{'device':st.st_dev,'inode':st.st_ino,'mode':'0700'},
        'spent_path':str(root/'spent.json'),'activation_path':str(input_root/'config'/Path(G['ACTIVATION_REPOSITORY_PATH']).name),
        'wheels':wheels,'limits':dict(G['CEILINGS']),'expected_versions':dict(G['EXPECTED_VERSIONS'])}


def proof_fixture(contract):
    ch=G['digest'](G['canonical'](contract))
    marker={'schema':G['MARKER_SCHEMA'],'bootstrap_identity':contract['bootstrap_identity'],'prepared_commit':'1'*40,
        'prepared_tree':'2'*40,'contract_sha256':ch,'engineering_only':True,'single_use':True}
    marker_raw=G['canonical'](marker)
    rows=[]
    for p in contract['source_pins']:
        raw=b'x'
        rows.append(p|{'content_base64':base64.b64encode(raw).decode(),
            'git_blob':hashlib.sha1(b'blob 1\0'+raw).hexdigest(),'repository_path':Path(p['path']).name})
    proof={'schema':G['PROOF_SCHEMA'],'repository':'andersenmartin-blip/setisearch','branch':'m43-support-qualification',
        'prepared_commit':'1'*40,'prepared_tree':'2'*40,'activation_commit':'3'*40,'activation_tree':'4'*40,
        'activation_parent':'1'*40,'activation_changed_path':G['ACTIVATION_REPOSITORY_PATH'],'contract_sha256':ch,
        'publication_files':rows,'activation_sha256':G['digest'](marker_raw),'bootstrap_identity':contract['bootstrap_identity'],
        'plan_sha256':contract['plan_sha256'],'provenance':'Synthetic immutable-body fixture; no network Git readback or scientific CAS certificate.'}
    return ch,proof,marker


class PureGuards(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name); os.chmod(self.root,0o700); self.c=fixture(self.root)
    def tearDown(self): self.temp.cleanup()
    def validate(self,c=None):
        raw=G['canonical'](self.c if c is None else c)
        return G['validate_contract'](raw,G['digest'](raw))
    def rejected(self,mutate):
        c=copy.deepcopy(self.c); mutate(c)
        with self.assertRaises(G['Refusal']): self.validate(c)
    def test_exact_synthetic_contract_accepted(self): self.assertEqual(self.validate(),self.c)
    def test_duplicate_json_refused(self):
        raw=b'{"schema":1,"schema":2}'
        with self.assertRaises(G['Refusal']): G['pinned_json'](raw,G['digest'](raw))
    def test_raw_pin_mismatch_refused(self):
        with self.assertRaises(G['Refusal']): G['validate_contract'](G['canonical'](self.c),'0'*64)
    def test_nonfinite_json_refused(self):
        raw=b'{"x":NaN}'
        with self.assertRaises(G['Refusal']): G['pinned_json'](raw,G['digest'](raw))
    def test_extra_contract_key_refused(self): self.rejected(lambda c:c.update(extra=True))
    def test_old_activation_path_refused(self): self.rejected(lambda c:c.update(activation_path=str(self.root/'config/radio_runtime_metadata_capture_20261004b.activate.json')))
    def test_nonroot_spent_refused(self): self.rejected(lambda c:c.update(spent_path=str(self.root/'other/spent.json')))
    def test_weak_root_mode_refused(self): self.rejected(lambda c:c['output_root_identity'].update(mode='0755'))
    def test_boolean_resource_limit_refused(self): self.rejected(lambda c:c['limits'].update(wall_seconds=True))
    def test_raised_child_reservation_refused(self): self.rejected(lambda c:c['limits'].update(child_read_reserve_bytes=2*1024**3))
    def test_lower_joined_limit_refused(self): self.rejected(lambda c:c['limits'].update(joined_read_bytes=3*1024**3))
    def test_insufficient_wall_reap_refused(self): self.rejected(lambda c:c['limits'].update(wall_seconds=270))
    def test_duplicate_selected_pin_refused(self): self.rejected(lambda c:c['runtime_pins'].append(c['source_pins'][0]))
    def test_reordered_source_inventory_refused(self): self.rejected(lambda c:c['source_pins'].reverse())
    def test_missing_supervisor_pin_refused(self): self.rejected(lambda c:c.update(source_pins=[p for p in c['source_pins'] if p['path']!=str(HERE/'bootstrap_gate.py')]))
    def test_seed_bytecode_refused(self): self.rejected(lambda c:c['seed_pins'][0].update(relative_path='pip/__main__.pyc'))
    def test_unpinned_seed_refused(self): self.rejected(lambda c:c['seed_pins'][0].update(sha256='0'*64))
    def test_seed_other_package_refused(self): self.rejected(lambda c:c['seed_pins'][0].update(relative_path='numpy/__main__.py'))
    def test_seed_exact_dist_info_allowed(self):
        p=pin((self.root.parent/(self.root.name+'-inputs'))/'seed'/'pip-26.2.1.dist-info/METADATA')|{'relative_path':'pip-26.2.1.dist-info/METADATA'}
        self.c['seed_pins'].append(p); self.c['runtime_pins'].append({k:p[k] for k in G['PIN_KEYS']}); self.c['runtime_pins'].sort(key=lambda p:p['path']); self.c['seed_pins'].sort(key=lambda p:p['relative_path'])
        self.assertEqual(self.validate()['seed_pins'],self.c['seed_pins'])
    def test_seed_other_version_dist_info_refused(self): self.rejected(lambda c:c['seed_pins'][0].update(relative_path='pip-25.0.dist-info/METADATA'))
    def test_wrong_package_version_refused(self): self.rejected(lambda c:c['wheels'][0].update(version='9.0'))
    def test_lock_without_hash_refused(self): self.rejected(lambda c:c.update(wheel_lock_utf8='numpy==2.3.5\n'))
    def test_real_domain_requires_exact_basis(self): self.rejected(lambda c:c.update(evidence_domain='package-bootstrap-only'))
    def test_pip_command_offline_isolated_no_site(self):
        command=G['pip_command'](self.c)
        self.assertEqual(command[1:4],['-I','-B','-S'])
        for item in ('--isolated','--no-index','--no-deps','--no-cache-dir','--require-hashes','--only-binary=:all:','--no-compile','--target','--find-links'):
            self.assertIn(item,command[-1])
        self.assertIn("runpy.run_module('pip',run_name='__main__')",command[-1])
    def test_scientific_authority_sixteen_false(self):
        self.assertEqual(len(G['AUTHORITY']),16); self.assertTrue(all(v is False for v in G['AUTHORITY'].values()))
    def verify(self,p=None,m=None):
        ch,proof,marker=proof_fixture(self.c); proof=proof if p is None else p; marker=marker if m is None else m
        pr=G['canonical'](proof); mr=G['canonical'](marker)
        return G['verify_publication'](self.c,ch,pr,G['digest'](pr),mr,G['digest'](mr))
    def test_fullbody_detached_proof_accepted(self): self.assertEqual(self.verify()['bootstrap_identity'],self.c['bootstrap_identity'])
    def test_preparation_reused_as_activation_refused(self):
        _,p,_=proof_fixture(self.c); p['activation_commit']=p['prepared_commit']
        with self.assertRaises(G['Refusal']): self.verify(p=p)
    def test_activation_nonsole_parent_refused(self):
        _,p,_=proof_fixture(self.c); p['activation_parent']='a'*40
        with self.assertRaises(G['Refusal']): self.verify(p=p)
    def test_old_proof_activation_path_refused(self):
        _,p,_=proof_fixture(self.c); p['activation_changed_path']='config/old.activate.json'
        with self.assertRaises(G['Refusal']): self.verify(p=p)
    def test_forged_fullcontent_refused(self):
        _,p,_=proof_fixture(self.c); p['publication_files'][0]['content_base64']=base64.b64encode(b'y').decode()
        with self.assertRaises(G['Refusal']): self.verify(p=p)
    def test_wrong_intrinsic_git_blob_refused(self):
        _,p,_=proof_fixture(self.c); p['publication_files'][0]['git_blob']='a'*40
        with self.assertRaises(G['Refusal']): self.verify(p=p)
    def test_promoted_marker_refused(self):
        _,_,m=proof_fixture(self.c); m['engineering_only']=False
        with self.assertRaises(G['Refusal']): self.verify(m=m)


class StorageAndReadGuards(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name); os.chmod(self.root,0o700)
        self.fd,self.fds,self.bindings=G['hold_root'](str(self.root)); st=self.root.stat()
        self.limits=dict(G['CEILINGS']); self.limits.update(artifact_bytes=2*1024**2,terminal_reserve_bytes=4096,file_bytes=1024**2,file_count=32,directory_count=16,parent_read_bytes=4*1024**2)
        self.identity={'device':st.st_dev,'inode':st.st_ino,'mode':'0700'}
        self.budget=G['Budget'](self.limits,str(self.root),self.fd,self.identity,time.monotonic_ns()+20*10**9,bindings=self.bindings)
    def tearDown(self):
        for fd in reversed(self.fds): os.close(fd)
        self.temp.cleanup()
    def test_exclusive_write_no_replacement(self):
        G['write_new'](self.fd,'spent.json',b'original',self.budget)
        with self.assertRaises(FileExistsError): G['write_new'](self.fd,'spent.json',b'replacement',self.budget)
        self.assertEqual((self.root/'spent.json').read_bytes(),b'original')
    def test_spent_entry_fsyncs_file_and_containing_directory(self):
        kinds=[]; real=os.fsync
        def observed(fd):
            kinds.append('directory' if __import__('stat').S_ISDIR(os.fstat(fd).st_mode) else 'file'); return real(fd)
        with mock.patch.object(G['os'],'fsync',side_effect=observed): G['write_new'](self.fd,'spent.json',b'original',self.budget)
        self.assertEqual(kinds[-2:],['file','directory'])
    def test_exact_executable_seed_mode_preserved_under_strict_umask(self):
        old=os.umask(0o077)
        try: G['write_new'](self.fd,'installer/pip/test.py',b'pure seed',self.budget,0o755)
        finally: os.umask(old)
        self.assertEqual((self.root/'installer/pip/test.py').stat().st_mode&0o7777,0o755)
    def test_symlink_file_refused(self):
        (self.root/'target').write_bytes(b'x'); (self.root/'link').symlink_to('target')
        with self.assertRaises(OSError): G['held_file'](str(self.root/'link'),1)
    def test_hardlink_regular_refused(self):
        (self.root/'target').write_bytes(b'x'); os.link(self.root/'target',self.root/'link')
        with self.assertRaises(G['Refusal']): G['held_file'](str(self.root/'target'),1)
    def test_seed_guard_hash_mismatch(self):
        path=self.root/'seed.py'; path.write_bytes(b'bad'); os.chmod(path,0o644)
        with self.assertRaises(G['Refusal']): G['pin_read'](pin(path,b'good'),self.budget)
    def test_read_precharge_and_received_separate(self):
        path=self.root/'plain'; path.write_bytes(b'abc'); os.chmod(path,0o644)
        G['pin_read'](pin(path,b'abc'),self.budget)
        self.assertEqual(self.budget.bytes,4); self.assertEqual(self.budget.received['regular'],3)
    def test_short_regular_reads_precharge_each_request_and_eof(self):
        path=self.root/'plain'; path.write_bytes(b'abcde'); real=os.read
        def short(fd,n): return real(fd,min(n,2))
        requests=[]; received=[]
        with mock.patch.object(G['os'],'read',side_effect=short):
            raw,_=G['held_file'](str(path),5,lambda n:requests.append(n),lambda n,kind:received.append(n))
        self.assertEqual(raw,b'abcde'); self.assertEqual(requests,[5,3,1,1]); self.assertEqual(sum(requests),10); self.assertEqual(sum(received),5)
    def test_precharge_stops_before_read(self):
        self.budget.limits['parent_read_bytes']=3
        self.budget.debit_read(3)
        with self.assertRaises(G['Refusal']): self.budget.debit_read(1)
        self.assertEqual(self.budget.bytes,3)
    def test_proc_requests_are_precharged_with_eof_without_refund(self):
        (self.root/'status').write_bytes(b'abc')
        self.assertEqual(self.budget.proc_at(self.fd,'status',16),b'abc')
        self.assertEqual(self.budget.categories['proc'],31); self.assertEqual(self.budget.received['proc'],3)
    def test_proc_overcap_preserves_raw_prefix_and_charge(self):
        (self.root/'status').write_bytes(b'abcde')
        with self.assertRaises(G['Refusal']) as caught: self.budget.proc_at(self.fd,'status',3)
        receipt=caught.exception.proc_read_evidence
        self.assertEqual(base64.b64decode(receipt['raw_received_base64']),b'abcd'); self.assertEqual(receipt['charged_bytes'],4); self.assertEqual(receipt['received_bytes'],4)
    def test_proc_fault_preserves_prefix_and_precharged_failed_request(self):
        (self.root/'status').write_bytes(b'abc'); real=os.read; calls=0
        def fault(fd,n):
            nonlocal calls
            calls+=1
            if calls>1: raise OSError(5,'synthetic read fault')
            return real(fd,n)
        with mock.patch.object(G['os'],'read',side_effect=fault):
            with self.assertRaises(OSError) as caught: self.budget.proc_at(self.fd,'status',16)
        receipt=caught.exception.proc_read_evidence
        self.assertEqual(base64.b64decode(receipt['raw_received_base64']),b'abc'); self.assertEqual(receipt['charged_bytes'],31); self.assertEqual(receipt['received_bytes'],3)
    def test_proc_missing_leaf_preserves_empty_evidence(self):
        with self.assertRaises(OSError) as caught: self.budget.proc_at(self.fd,'status',16)
        self.assertEqual(caught.exception.proc_read_evidence['raw_received_base64'],''); self.assertEqual(caught.exception.proc_read_evidence['charged_bytes'],0)
    def test_invalid_proc_leaf_refused(self):
        with self.assertRaises(G['Refusal']): self.budget.proc_at(self.fd,'../status',16)
    def test_terminal_floor_includes_two_pidfd_requests(self):
        self.budget.reserve_terminal(100)
        self.assertEqual(self.budget.terminal_pidfd_reserved_bytes,32770)
    def test_protected_terminal_space(self):
        with self.assertRaises(G['Refusal']): self.budget.before_write(self.limits['artifact_bytes']-4096)
        self.assertEqual(os.listdir(self.fd),[])
    def test_recursive_manifest_hashes_all_regular_objects(self):
        G['write_new'](self.fd,'nested/data',b'abc',self.budget)
        manifest=G['inventory'](self.fd,self.limits,self.budget.deadline,hashes=True,budget=self.budget)
        row=next(r for r in manifest['entries'] if r['path']=='nested/data')
        self.assertEqual(row['sha256'],G['digest'](b'abc')); self.assertEqual(row['bytes'],3)
        self.assertEqual(manifest['directories'],2); self.assertGreaterEqual(manifest['logical_bytes'],3)
    def test_recursive_symlink_refused_partial_manifest_retained(self):
        (self.root/'link').symlink_to('/tmp')
        with self.assertRaises(G['Refusal']) as caught: G['inventory'](self.fd,self.limits,self.budget.deadline,hashes=True,budget=self.budget)
        self.assertFalse(caught.exception.partial_inventory['complete'])
    def test_file_count_cap(self):
        self.limits['file_count']=1
        (self.root/'a').write_bytes(b''); (self.root/'b').write_bytes(b'')
        with self.assertRaises(G['Refusal']): G['inventory'](self.fd,self.limits,self.budget.deadline)
    def test_file_size_cap(self):
        self.limits['file_bytes']=2; (self.root/'a').write_bytes(b'abc')
        with self.assertRaises(G['Refusal']): G['inventory'](self.fd,self.limits,self.budget.deadline)
    def test_unregistered_directory_fd_refused(self):
        foreign=os.open('/tmp',os.O_RDONLY|os.O_DIRECTORY)
        try:
            with self.assertRaises(G['Refusal']): self.budget.check_directory(foreign)
        finally: os.close(foreign)
    def test_root_mode_drift_refused(self):
        os.chmod(self.root,0o755)
        with self.assertRaises(G['Refusal']): self.budget.check()
        os.chmod(self.root,0o700)
    def test_named_root_replacement_refused(self):
        replacement=self.root.with_name(self.root.name+'-old'); self.root.rename(replacement); self.root.mkdir(mode=0o700)
        try:
            with self.assertRaises(G['Refusal']): self.budget.check()
        finally:
            self.root.rmdir(); replacement.rename(self.root)
    def test_expired_deadline_refused(self):
        self.budget.deadline=time.monotonic_ns()-1
        with self.assertRaises(G['Refusal']): self.budget.check()
    def test_static_payload_cap_refused(self):
        c=fixture(self.root); c['limits']=dict(G['CEILINGS'])
        self.budget.limits=dict(G['CEILINGS'])
        inspections=[{'status':'STATIC_WHEEL_PREFLIGHT_VERIFIED','payload_bytes':G['MAX_PAYLOAD']+1,'members':[]}, {'status':'STATIC_WHEEL_PREFLIGHT_VERIFIED','payload_bytes':0,'members':[]},{'status':'STATIC_WHEEL_PREFLIGHT_VERIFIED','payload_bytes':0,'members':[]}]
        with self.assertRaises(G['Refusal']): G['prospective_install'](c,inspections,self.budget,0,0)
    def test_static_temp_envelope_refused(self):
        c=fixture(self.root); c['limits']=dict(G['CEILINGS']); self.budget.limits=dict(G['CEILINGS'])
        inspections=[{'status':'STATIC_WHEEL_PREFLIGHT_VERIFIED','payload_bytes':G['MAX_PAYLOAD'],'members':[]}, {'status':'STATIC_WHEEL_PREFLIGHT_VERIFIED','payload_bytes':0,'members':[]},{'status':'STATIC_WHEEL_PREFLIGHT_VERIFIED','payload_bytes':0,'members':[]}]
        with self.assertRaises(G['Refusal']): G['prospective_install'](c,inspections,self.budget,0,0)
    def test_cross_wheel_destination_collision(self):
        c=fixture(self.root); self.budget.limits=dict(G['CEILINGS'])
        row={'status':'STATIC_WHEEL_PREFLIGHT_VERIFIED','payload_bytes':1,'members':[{'path':'shared.py','bytes':1,'sha256':'0'*64,'kind':'file'}]}
        with self.assertRaises(G['Refusal']): G['prospective_install'](c,[row,row,{'status':'STATIC_WHEEL_PREFLIGHT_VERIFIED','payload_bytes':0,'members':[]}],self.budget,0,0)
    def test_data_mapping_refused_before_child(self):
        c=fixture(self.root); self.budget.limits=dict(G['CEILINGS'])
        row={'status':'STATIC_WHEEL_PREFLIGHT_VERIFIED','payload_bytes':1,'members':[{'path':'numpy-2.3.5.data/scripts/f2py','bytes':1,'sha256':'0'*64,'kind':'file'}]}
        with self.assertRaises(G['Refusal']): G['prospective_install'](c,[row,{'status':'STATIC_WHEEL_PREFLIGHT_VERIFIED','payload_bytes':0,'members':[]},{'status':'STATIC_WHEEL_PREFLIGHT_VERIFIED','payload_bytes':0,'members':[]}],self.budget,0,0)
    def test_joined_file_prefix_collision(self):
        with self.assertRaises(G['Refusal']): G['joined_destinations'](['site/package','site/package/module.py'],[])
    def test_joined_directory_file_prefix_collision(self):
        with self.assertRaises(G['Refusal']): G['joined_destinations'](['site/package'],['site/package/module'])
    def test_joined_case_alias_collision(self):
        with self.assertRaises(G['Refusal']): G['joined_destinations'](['site/Package.py','site/package.py'],[])
    def test_joined_unicode_alias_collision(self):
        with self.assertRaises(G['Refusal']): G['joined_destinations'](['site/caf\u00e9.py','site/cafe\u0301.py'],[])
    def test_joined_shared_directories_allowed(self):
        files,dirs=G['joined_destinations'](['site/shared/one.py','site/shared/two.py'],['site/shared'])
        self.assertEqual(len(files),2); self.assertEqual(dirs,{'site','site/shared'})
    def test_preflight_predicted_file_count_overflow(self):
        c=fixture(self.root); c['limits']['file_count']=130; self.budget.limits=dict(G['CEILINGS'])
        rows=[{'status':'STATIC_WHEEL_PREFLIGHT_VERIFIED','payload_bytes':1,'members':[{'path':'package.py','kind':'file','bytes':1,'sha256':'0'*64}]},{'status':'STATIC_WHEEL_PREFLIGHT_VERIFIED','payload_bytes':0,'members':[]},{'status':'STATIC_WHEEL_PREFLIGHT_VERIFIED','payload_bytes':0,'members':[]}]
        with self.assertRaises(G['Refusal']): G['prospective_install'](c,rows,self.budget,1,1)
    def test_preflight_nested_directory_count_overflow(self):
        c=fixture(self.root); c['limits']['directory_count']=270; self.budget.limits=dict(G['CEILINGS'])
        rows=[{'status':'STATIC_WHEEL_PREFLIGHT_VERIFIED','payload_bytes':1,'members':[{'path':'one/two/three/four/five/package.py','kind':'file','bytes':1,'sha256':'0'*64}]},{'status':'STATIC_WHEEL_PREFLIGHT_VERIFIED','payload_bytes':0,'members':[]},{'status':'STATIC_WHEEL_PREFLIGHT_VERIFIED','payload_bytes':0,'members':[]}]
        with self.assertRaises(G['Refusal']): G['prospective_install'](c,rows,self.budget,1,1)
    def test_preflight_explicit_directory_entries_and_scripts(self):
        c=fixture(self.root); self.budget.limits=dict(G['CEILINGS'])
        rows=[{'status':'STATIC_WHEEL_PREFLIGHT_VERIFIED','payload_bytes':1,'members':[{'path':'package/','kind':'directory','bytes':0,'sha256':'0'*64},{'path':'package/module.py','kind':'file','bytes':1,'sha256':'0'*64}],
            'metadata':{'dist_info':'numpy-2.3.5.dist-info','entry_points_utf8':'[console_scripts]\nsynthetic = package:main\n'}},{'status':'STATIC_WHEEL_PREFLIGHT_VERIFIED','payload_bytes':0,'members':[]},{'status':'STATIC_WHEEL_PREFLIGHT_VERIFIED','payload_bytes':0,'members':[]}]
        result=G['prospective_install'](c,rows,self.budget,1,1)
        self.assertEqual(result['generated_scripts'],['site/bin/synthetic']); self.assertGreater(result['predicted_files_with_temp_allowance'],128)
    def test_preflight_duplicate_crosswheel_scripts_refused(self):
        c=fixture(self.root); self.budget.limits=dict(G['CEILINGS'])
        row={'status':'STATIC_WHEEL_PREFLIGHT_VERIFIED','payload_bytes':0,'members':[],
            'metadata':{'entry_points_utf8':'[console_scripts]\nsynthetic = package:main\n'}}
        with self.assertRaises(G['Refusal']): G['prospective_install'](c,[row,row,{'status':'STATIC_WHEEL_PREFLIGHT_VERIFIED','payload_bytes':0,'members':[]}],self.budget,0,0)


class SyntheticProcessGuards(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Read only exact reviewed source, not runtime cohort or genuine wheels.
        path=HERE/'capture_basis.py'; raw=path.read_bytes()
        if G['digest'](raw)!=G['BASIS_SHA256']: raise AssertionError('basis source differs')
        cls.basis=G['compile_verified'](raw,str(path),'_synthetic_process_basis')
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name); os.chmod(self.root,0o700); (self.root/'tmp').mkdir(mode=0o700)
        self.fd,self.fds,self.bindings=G['hold_root'](str(self.root)); self.c=fixture(self.root)
        self.c['limits'].update(wall_seconds=30,child_seconds=5,reap_seconds=2,artifact_bytes=32*1024**2,terminal_reserve_bytes=1024**2)
        self.budget=G['Budget'](self.c['limits'],str(self.root),self.fd,self.c['output_root_identity'],time.monotonic_ns()+30*10**9,bindings=self.bindings)
        self.budget.basis_reads=self.basis['Reads'](self.c['limits']['parent_read_bytes'])
        # Genuine executable custody for a synthetic sleeping child; no native
        # package import, genuine pip module, selected runtime pass or bootstrap.
        st=os.stat(self.c['python_executable']); self.c['_verified_python_object']={'device':st.st_dev,'inode':st.st_ino}
    def tearDown(self):
        for fd in reversed(self.fds): os.close(fd)
        self.temp.cleanup()
    def run_child(self,code): return G['supervise']([self.c['python_executable'],'-I','-B','-S','-c',code],self.c,self.budget,self.basis)
    def test_authenticated_success_and_lossless_streams(self):
        report=self.run_child("import time,sys;time.sleep(.35);sys.stdout.write('synthetic-out\\n');sys.stderr.write('synthetic-err\\n')")
        self.assertIsNone(report['failure']); self.assertEqual(report['engineering_child_dispatches'],1); self.assertTrue(report['child_reaped'])
        self.assertGreater(report['authenticated_procfs_samples'],0); self.assertEqual((self.root/'child.stdout.raw').read_bytes(),b'synthetic-out\n'); self.assertEqual((self.root/'child.stderr.raw').read_bytes(),b'synthetic-err\n')
        self.assertFalse(report['aggregate_descendant_absence_certified']); self.assertTrue(report['process_attribution']['pidfd_terminal_observed'])
    def test_nonzero_preserves_exit_and_raw_stderr(self):
        report=self.run_child("import time,sys;time.sleep(.35);sys.stderr.write('synthetic failure\\n');sys.exit(7)")
        self.assertEqual(report['failure'],'PIP_NONZERO'); self.assertEqual(report['child_exit_code'],7); self.assertEqual((self.root/'child.stderr.raw').read_bytes(),b'synthetic failure\n')
    def test_stream_limit_received_prefix_preserved(self):
        self.c['limits']['stream_bytes']=64
        report=self.run_child("import time,sys;time.sleep(.35);sys.stdout.write('a'*4096);sys.stdout.flush();time.sleep(.1)")
        self.assertEqual(report['failure'],'RAW_STREAM_CAP'); self.assertEqual((self.root/'child.stdout.raw').stat().st_size,65); self.assertTrue(report['child_reaped'])
    def test_immediate_exit_never_fabricates_live_sample(self):
        report=self.run_child('raise SystemExit(4)')
        self.assertTrue(report['child_reaped']); self.assertEqual(report['child_exit_code'],4); self.assertFalse(report['aggregate_descendant_absence_certified'])
    def test_immediate_startup_failure_raw_stderr_retained(self):
        report=self.run_child("import sys;sys.stderr.write('synthetic startup failed\\n');sys.stderr.flush();raise SystemExit(9)")
        self.assertTrue(report['child_reaped']); self.assertEqual((self.root/'child.stderr.raw').read_bytes(),b'synthetic startup failed\n')
    def test_wrong_expected_executable_refuses_attribution(self):
        self.c['_verified_python_object']={'device':0,'inode':1}
        report=self.run_child('import time;time.sleep(.35)')
        self.assertIsNotNone(report['failure']); self.assertEqual(report['authenticated_procfs_samples'],0); self.assertTrue(report['child_reaped'])
    def test_pipe_storage_refusal_occurs_before_read(self):
        original=self.budget.before_write
        def no_pipe_room(n):
            if n==65536: raise G['Refusal']('synthetic pipe artifact reserve refusal')
            return original(n)
        self.budget.before_write=no_pipe_room
        report=self.run_child("import time,sys;time.sleep(.35);sys.stdout.write('synthetic stream');sys.stdout.flush();time.sleep(.1)")
        self.assertIsNotNone(report['failure']); self.assertEqual(self.budget.received['pipe'],0)
        self.assertEqual((self.root/'child.stdout.raw').read_bytes(),b''); self.assertTrue(report['child_reaped'])
    def test_partial_pipe_write_retains_full_received_bytes_and_prefix_length(self):
        real=os.write
        def partial(fd,raw):
            if raw==b'synthetic stream': return real(fd,raw[:3])
            if raw==b'thetic stream': raise OSError(5,'synthetic partial stream write')
            return real(fd,raw)
        with mock.patch.object(G['os'],'write',side_effect=partial):
            report=self.run_child("import time,sys;time.sleep(.35);sys.stdout.write('synthetic stream');sys.stdout.flush();time.sleep(.1)")
        self.assertIsNotNone(report['failure']); self.assertEqual((self.root/'child.stdout.raw').read_bytes(),b'syn')
        evidence=next(r for r in report['raw_retention_error_evidence'] if r['kind']=='pipe-stdout')
        self.assertEqual(base64.b64decode(evidence['raw_received_base64']),b'synthetic stream')
        self.assertEqual(evidence['reported_written_prefix_bytes'],3); self.assertEqual(evidence['file_size_at_selected_failure'],3)
        self.assertEqual(report['raw_stdout_bytes'],len(b'synthetic stream')); self.assertTrue(report['child_reaped'])
    def test_replay_existing_raw_evidence_dispatches_no_child(self):
        (self.root/'child.stdout.raw').write_bytes(b'first')
        report=self.run_child('import time;time.sleep(.35)')
        self.assertEqual(report['engineering_child_dispatches'],0); self.assertEqual((self.root/'child.stdout.raw').read_bytes(),b'first')


class MockedPipelineGuards(unittest.TestCase):
    """Every runtime/source/transport dependency is fixture-local or mocked."""
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.base=Path(self.temp.name); self.root=self.base/'fresh'
        self.root.mkdir(mode=0o700); self.c=fixture(self.root)
        self.c['activation_path']=str(self.base/'config'/Path(G['ACTIVATION_REPOSITORY_PATH']).name)
        ch,p,m=proof_fixture(self.c); self.cr=G['canonical'](self.c); self.ch=ch; self.pr=G['canonical'](p); self.mr=G['canonical'](m)
        Path(self.c['activation_path']).parent.mkdir(); Path(self.c['activation_path']).write_bytes(self.mr)
        self.acquired=0; self.dispatched=0
    def tearDown(self): self.temp.cleanup()
    def fake_pin(self,pin,budget=None):
        return b'x',{'device':27,'inode':1},dict(pin)
    def fake_compile(self,raw,path,name):
        if path==self.c['attribution_basis_path']:
            return {'Reads':lambda limit:object()}
        def fail(wheel,held,budget,deadline,opener=None):
            self.acquired+=1
            exc=G['Refusal']('synthetic acquisition failure without network')
            exc.receipt={'status':'CLOSED_FAILED','fixture':True,'received_body_bytes':0}; raise exc
        return {'acquire_wheel':fail,'inspect_wheel':lambda *a: (_ for _ in ()).throw(AssertionError('inspection must not occur'))}
    def fake_transport_modules(self,*args):
        from types import SimpleNamespace
        wheel=SimpleNamespace(**self.fake_compile(b'',self.c['wheel_io_path'],'fake'))
        proxy=SimpleNamespace(make_opener=lambda *a,**kw:SimpleNamespace(receipt={'schema':'synthetic-only','status':'PENDING','evidence_domain':'SIMULATION_ONLY'}),bounded_http_binding=lambda *a:None)
        return {'wheel_io':wheel,'proxy_opener':proxy,'proxy_contract':SimpleNamespace(endpoint=lambda value:{'host':'127.0.0.1','port':12345,'scheme':'http'})}
    def run_fixture(self):
        return G['run'](self.cr,self.ch,self.pr,G['digest'](self.pr),self.mr,G['digest'](self.mr))
    def test_spent_acquisition_failure_preserved_and_same_root_replay_refused(self):
        with mock.patch.dict(G,{'pin_read':self.fake_pin,'compile_verified':self.fake_compile,'validate_transport_descriptor':lambda *a:{'proxy_selection':{'environment_name':'PIP_PROXY'},'trust_binding':{}},'compile_transport_modules':self.fake_transport_modules,'native_transport_bindings':lambda *a:(lambda *a:None,lambda *a:None)}):
            result=self.run_fixture()
            with self.assertRaises(G['Refusal']): self.run_fixture()
        self.assertEqual(result['report']['status'],'CLOSED_FAILED'); self.assertEqual(self.acquired,1)
        self.assertIsNone(result['report']['pip_child']); self.assertTrue((self.root/'spent.json').exists())
        self.assertTrue((self.root/'admission-witness.json').exists()); self.assertTrue((self.root/'supervisor-result.json').exists())
        receipt=json.loads((self.root/'acquisition-numpy.json').read_text())
        self.assertTrue(receipt['fixture']); self.assertEqual(receipt['received_body_bytes'],0)
        spent=json.loads((self.root/'spent.json').read_text()); self.assertFalse(spent['retry_allowed']); self.assertTrue(spent['irreversible'])
    def test_terminal_after_pin_inventory_is_hashed_before_manifest(self):
        with mock.patch.dict(G,{'pin_read':self.fake_pin,'compile_verified':self.fake_compile,'validate_transport_descriptor':lambda *a:{'proxy_selection':{'environment_name':'PIP_PROXY'},'trust_binding':{}},'compile_transport_modules':self.fake_transport_modules,'native_transport_bindings':lambda *a:(lambda *a:None,lambda *a:None)}): result=self.run_fixture()
        manifest=json.loads((self.root/'artifact-manifest.json').read_text())['manifest']
        after=next(r for r in manifest['entries'] if r['path']=='selected-runtime-after.json')
        self.assertEqual(after['sha256'],G['digest']((self.root/'selected-runtime-after.json').read_bytes()))
        self.assertFalse(result['report']['joined_full_scope_io_qualified'])
        self.assertIsNone(result['report']['child_read_observed_bytes']); self.assertEqual(result['report']['child_read_reserved_bytes'],1024**3)
    def test_pre_spend_source_drift_refuses_before_acquisition_or_dispatch(self):
        def drift(pin,budget=None): raise G['Refusal']('synthetic source drift')
        with mock.patch.dict(G,{'pin_read':drift,'compile_verified':self.fake_compile}):
            with self.assertRaises(G['Refusal']): self.run_fixture()
        self.assertEqual(self.acquired,0); self.assertEqual(list(self.root.iterdir()),[])
    def cli_fixture(self):
        paths=[]
        for name in ('cli-contract','cli-proof','cli-activation'):
            path=self.base/name; path.write_bytes(b'abcde'); paths.append(str(path))
        return __import__('argparse').Namespace(contract=paths[0],contract_sha256='1'*64,
            publication_proof=paths[1],publication_proof_sha256='2'*64,activation=paths[2],activation_sha256='3'*64)
    def test_cli_short_reads_forward_actual_requested_and_received_counts(self):
        args=self.cli_fixture(); real=os.read; output=__import__('io').BytesIO(); calls=[]
        def short(fd,n): return real(fd,min(n,2))
        def fake_run(*a,**kw): calls.append(kw); return {'synthetic_cli_only':True}
        with mock.patch.object(G['argparse'].ArgumentParser,'parse_args',return_value=args), mock.patch.object(G['os'],'read',side_effect=short), mock.patch.dict(G,{'run':fake_run}), mock.patch.object(G['sys'],'stdout',__import__('types').SimpleNamespace(buffer=output)):
            G['main']()
        self.assertEqual(calls[0]['initial_read_bytes'],30); self.assertEqual(calls[0]['initial_read_received_bytes'],15)
        self.assertEqual(json.loads(output.getvalue()),{'synthetic_cli_only':True})
    def test_cli_deadline_refuses_before_regular_read(self):
        args=self.cli_fixture()
        with mock.patch.object(G['argparse'].ArgumentParser,'parse_args',return_value=args), mock.patch.object(G['time'],'monotonic_ns',side_effect=[1,300*10**9+2]), mock.patch.object(G['os'],'read') as reader:
            with self.assertRaises(G['Refusal']): G['main']()
        reader.assert_not_called()


if __name__=='__main__': unittest.main(verbosity=2)
