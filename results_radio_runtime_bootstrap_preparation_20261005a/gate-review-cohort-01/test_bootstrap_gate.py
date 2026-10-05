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

HERE=Path(__file__).resolve().parent
G={ '__name__':'_synthetic_bootstrap_gate', '__file__':str(HERE/'bootstrap_gate.py') }
exec(compile((HERE/'bootstrap_gate.py').read_bytes(),G['__file__'],'exec'),G)


def pin(path,raw=b'x'):
    return {'path':str(path),'bytes':len(raw),'sha256':G['digest'](raw),'mode':'0644'}


def fixture(root):
    python=str(Path(sys.executable).resolve())
    sources=sorted([pin(HERE/'bootstrap_gate.py'),pin(root/'capture_basis.py'),pin(root/'wheel_io.py'),pin(root/'plan.json')],key=lambda p:p['path'])
    seed=pin(root/'seed'/'pip'/'__main__.py')|{'relative_path':'pip/__main__.py'}
    wheels=[]
    for name,version in G['EXPECTED_VERSIONS'].items():
        wheels.append({'name':name,'version':version,'filename':name+'-'+version+'-py3-none-any.whl',
            'url':'https://files.pythonhosted.org/packages/'+name+'.whl','bytes':16,'sha256':hashlib.sha256(name.encode()).hexdigest(),'tags':['py3-none-any']})
    st=root.stat()
    return {'schema':G['SCHEMA'],'bootstrap_identity':'7'*64,'evidence_domain':'synthetic-test-fixture',
        'source_pins':sources,'runtime_pins':sorted([pin(python),{k:seed[k] for k in G['PIN_KEYS']}],key=lambda p:p['path']),
        'seed_pins':[seed],'python_executable':python,'python_sha256':pin(python)['sha256'],
        'attribution_basis_path':str(root/'capture_basis.py'),'wheel_io_path':str(root/'wheel_io.py'),
        'plan_path':str(root/'plan.json'),'plan_sha256':pin(root/'plan.json')['sha256'],
        'wheel_lock_utf8':''.join(w['name']+'=='+w['version']+' --hash=sha256:'+w['sha256']+'\n' for w in wheels),
        'output_root':str(root),'output_root_identity':{'device':st.st_dev,'inode':st.st_ino,'mode':'0700'},
        'spent_path':str(root/'spent.json'),'activation_path':str(root/'config'/Path(G['ACTIVATION_REPOSITORY_PATH']).name),
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
        p=pin(self.root/'seed'/'pip-26.2.1.dist-info/METADATA')|{'relative_path':'pip-26.2.1.dist-info/METADATA'}
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
    def test_precharge_stops_before_read(self):
        self.budget.limits['parent_read_bytes']=3
        self.budget.debit_read(3)
        with self.assertRaises(G['Refusal']): self.budget.debit_read(1)
        self.assertEqual(self.budget.bytes,3)
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
    def test_wrong_expected_executable_refuses_attribution(self):
        self.c['_verified_python_object']={'device':0,'inode':1}
        report=self.run_child('import time;time.sleep(.35)')
        self.assertIsNotNone(report['failure']); self.assertEqual(report['authenticated_procfs_samples'],0); self.assertTrue(report['child_reaped'])
    def test_replay_existing_raw_evidence_dispatches_no_child(self):
        (self.root/'child.stdout.raw').write_bytes(b'first')
        report=self.run_child('import time;time.sleep(.35)')
        self.assertEqual(report['engineering_child_dispatches'],0); self.assertEqual((self.root/'child.stdout.raw').read_bytes(),b'first')


if __name__=='__main__': unittest.main(verbosity=2)
