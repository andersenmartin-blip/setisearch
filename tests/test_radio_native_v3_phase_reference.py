"""Tiny real files exercise reference storage, with deep execution auth mocked.

No project marker, claim, journal, dispatch, full-size source or workload is
created. These checks cover bytes and fixed reference paths, not execution
authority or the provenance of a real activation.
"""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import types
import unittest
from unittest import mock

import radio_native_v3_worker_admission as worker
import radio_native_v3_process_tree_supervisor as supervisor


def digest(value):
    return hashlib.sha256(worker.canonical(value)).hexdigest()


class PhaseReferenceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='v3-tiny-phase-reference-')
        self.addCleanup(self.directory.cleanup)
        self.scope = Path(self.directory.name) / 'scope'
        self.root = self.scope / 'cases' / 'case00'
        self.root.mkdir(parents=True)
        self.base_path = self.root / 'worker-admission.json'
        context = {name: {'tiny_shared_context': name} for name in worker.SHARED_CONTEXT_KEYS}
        self.base = {'schema': worker.SCHEMA, 'namespace': worker.NAMESPACE,
            'case_ordinal': 0, 'execution_scope': str(self.scope),
            'invocation_repository_root': self.directory.name,
            'code_root': str(self.root / 'frozen-code'),
            'derived_root': str(self.root / 'derived'), **context}
        self.base.update({name + '_sha256': digest(value) for name, value in context.items()})
        self.assertEqual(set(self.base), worker.BUNDLE_KEYS)
        self.write_json(self.base_path, self.base)
        # The tests retain real tiny bytes and use the actual fixed-path,
        # canonical, nofollow and hashing code. No real custody is asserted.
        self.prepare_validation = mock.patch.object(worker, '_validate_prepare_bundle',
            side_effect=lambda value, ordinal: str(self.root))
        self.prepare_validation.start()
        self.addCleanup(self.prepare_validation.stop)

    def write_json(self, path, value):
        path.write_bytes(worker.canonical(value) + b'\n')
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def descriptor(self, name):
        return {'path': str(self.root / name), 'bytes': 1, 'sha256': '1' * 64}

    def full_bundle(self, role='command'):
        if role == 'command':
            inputs = {'prepared_json': self.descriptor('prepared.json'),
                'label': 'command-0', 'command': 'tiny-command-literal',
                'source_wire': self.descriptor('store/items/request-000001/part')}
        elif role == 'caller':
            inputs = {'prepared_json': self.descriptor('prepared.json')}
        elif role == 'lossless-project':
            inputs = {'prepared_json': self.descriptor('prepared.json'),
                'arguments_json': self.descriptor('project-arguments.json'),
                'caller_transcript': self.descriptor('caller-result.json'),
                'preparation_bundle': self.descriptor('worker-admission.json')}
        elif role == 'lossless-verify-retained':
            inputs = {'prepared_json': self.descriptor('prepared.json'),
                'arguments_json': self.descriptor('projection-verify-arguments.json'),
                'projection': self.descriptor('public-evidence/caller-transcript-compact-lossless.json'),
                'source_wire': self.descriptor('store/items/request-000001/part'),
                'deterministic_source': self.descriptor('deterministic-source.bin'),
                'preparation_bundle': self.descriptor('worker-admission.json')}
        else:
            raise AssertionError(role)
        return {**copy.deepcopy(self.base), 'schema': worker.ROLE_SCHEMA,
            'role': role, 'phase_inputs': inputs}

    def retain(self, role='command'):
        bundle = self.full_bundle(role)
        raw = worker.bundle_bytes(bundle)
        name = 'command-0' if role == 'command' else role
        path = self.root / (name + '-admission.json')
        path.write_bytes(raw)
        return bundle, path, hashlib.sha256(raw).hexdigest(), worker._canonical_bundle_value(raw)

    def test_all_case_roles_reopen_one_full_preparation_context(self):
        for role in sorted(worker.CASE_ROLES):
            with self.subTest(role=role):
                full, path, pin, reference = self.retain(role)
                self.assertEqual(reference['schema'], worker.PHASE_REFERENCE_SCHEMA)
                self.assertEqual(set(reference), worker.PHASE_REFERENCE_KEYS)
                self.assertFalse(worker.SHARED_CONTEXT_KEYS & set(reference))
                self.assertEqual(reference['base_preparation_bundle']['path'], str(self.base_path))
                self.assertEqual(worker.load_bundle(path, expected_bundle_sha256=pin), full)

    def test_full_preparation_serialization_stays_exact(self):
        self.assertEqual(worker.bundle_bytes(self.base), self.base_path.read_bytes())
        self.assertEqual(worker.load_bundle(self.base_path,
            expected_bundle_sha256=hashlib.sha256(self.base_path.read_bytes()).hexdigest()), self.base)

    def test_mutated_context_bytes_never_use_cached_expansion(self):
        full, path, pin, _ = self.retain()
        self.assertEqual(worker.load_bundle(path, expected_bundle_sha256=pin), full)
        changed = copy.deepcopy(self.base)
        changed['complete_freeze']['extra'] = 'changed'
        self.write_json(self.base_path, changed)
        with self.assertRaisesRegex(ValueError, 'original preparation bytes'):
            worker.load_bundle(path, expected_bundle_sha256=pin)

    def test_context_changed_during_validation_fails_final_reopen(self):
        _, path, pin, _ = self.retain()
        changed = copy.deepcopy(self.base)
        changed['complete_freeze']['changed_during_validation'] = True
        def mutate_context(value, ordinal):
            self.write_json(self.base_path, changed)
            return str(self.root)
        with mock.patch.object(worker, '_validate_prepare_bundle', side_effect=mutate_context):
            with self.assertRaisesRegex(ValueError, 'context unchanged after validation'):
                worker.load_bundle(path, expected_bundle_sha256=pin)

    def test_missing_context_is_closed(self):
        _, path, pin, _ = self.retain()
        self.base_path.unlink()
        with self.assertRaises(FileNotFoundError):
            worker.load_bundle(path, expected_bundle_sha256=pin)

    def test_symlink_context_and_descriptor_alias_are_closed(self):
        _, path, pin, reference = self.retain()
        ordinary = self.root / 'renamed-context.json'
        self.base_path.rename(ordinary)
        self.base_path.symlink_to(ordinary)
        with self.assertRaises(OSError):
            worker.load_bundle(path, expected_bundle_sha256=pin)
        self.base_path.unlink()
        ordinary.rename(self.base_path)
        reference['base_preparation_bundle']['path'] = str(self.root / 'other-context.json')
        pin = self.write_json(path, reference)
        with self.assertRaisesRegex(ValueError, 'fixed preparation path'):
            worker.load_bundle(path, expected_bundle_sha256=pin)

    def test_hardlink_context_is_closed(self):
        _, path, pin, _ = self.retain()
        import os
        os.link(self.base_path, self.root / 'context-alias.json')
        with self.assertRaisesRegex(ValueError, 'sole-link regular'):
            worker.load_bundle(path, expected_bundle_sha256=pin)

    def test_ancestor_symlink_is_closed(self):
        _, path, pin, _ = self.retain()
        original = self.root.with_name('case00-original')
        self.root.rename(original)
        self.root.symlink_to(original, target_is_directory=True)
        with self.assertRaises(OSError):
            worker.load_bundle(path, expected_bundle_sha256=pin)

    def test_reference_raw_digest_is_checked_before_context_read(self):
        _, path, pin, _ = self.retain()
        self.base_path.unlink()
        with self.assertRaisesRegex(ValueError, 'bundle bytes changed'):
            worker.load_bundle(path, expected_bundle_sha256='0' * 64)

    def test_whole_role_ordinal_and_retained_path_relabel_are_closed(self):
        for change in ({'role': 'control'}, {'case_ordinal': 1}, {'case_ordinal': True}):
            with self.subTest(change=change):
                _, path, _, reference = self.retain()
                reference.update(change)
                pin = self.write_json(path, reference)
                with self.assertRaises((ValueError, FileNotFoundError)):
                    worker.load_bundle(path, expected_bundle_sha256=pin)
        _, path, pin, _ = self.retain()
        alias = self.root / 'command-1-admission.json'
        path.rename(alias)
        with self.assertRaisesRegex(ValueError, 'fixed retained role path'):
            worker.load_bundle(alias, expected_bundle_sha256=pin)

    def test_reference_recursion_and_noncanonical_context_are_closed(self):
        _, path, _, reference = self.retain()
        self.write_json(self.base_path, reference)
        reference['base_preparation_bundle'].update(
            bytes=self.base_path.stat().st_size, sha256=hashlib.sha256(self.base_path.read_bytes()).hexdigest())
        pin = self.write_json(path, reference)
        with self.assertRaisesRegex(ValueError, 'recursion refused'):
            worker.load_bundle(path, expected_bundle_sha256=pin)
        self.base_path.write_bytes(worker.canonical(self.base))
        reference['base_preparation_bundle'].update(
            bytes=self.base_path.stat().st_size, sha256=hashlib.sha256(self.base_path.read_bytes()).hexdigest())
        pin = self.write_json(path, reference)
        with self.assertRaisesRegex(ValueError, 'canonical admission'):
            worker.load_bundle(path, expected_bundle_sha256=pin)

    def test_changed_logical_context_cannot_be_serialized(self):
        changed = self.full_bundle()
        changed['public_preread']['changed'] = True
        with self.assertRaisesRegex(ValueError, 'shared preparation context'):
            worker.bundle_bytes(changed)

    def test_full_bundle_serialization_and_loading_have_fixed_2mib_limit(self):
        self.assertEqual(worker.MAX_FULL_BUNDLE_BYTES,2*1024**2)
        raw=worker.canonical(self.base)+b'\n'
        with mock.patch.object(worker,'MAX_FULL_BUNDLE_BYTES',len(raw)):
            self.assertEqual(worker.bundle_bytes(self.base),raw)
            self.assertEqual(worker.load_bundle(self.base_path,
                expected_bundle_sha256=hashlib.sha256(raw).hexdigest()),self.base)
        with mock.patch.object(worker,'MAX_FULL_BUNDLE_BYTES',len(raw)-1):
            with self.assertRaisesRegex(ValueError,'2MiB capacity'):
                worker.bundle_bytes(self.base)
            with self.assertRaisesRegex(ValueError,'Bounded'):
                worker.load_bundle(self.base_path,expected_bundle_sha256=hashlib.sha256(raw).hexdigest())

    def test_reference_descriptor_over_2mib_is_rejected_before_context_read(self):
        _,path,_,reference=self.retain()
        reference['base_preparation_bundle']['bytes']=worker.MAX_FULL_BUNDLE_BYTES+1
        digest=self.write_json(path,reference)
        with mock.patch.object(worker,'_validate_prepare_bundle') as validation:
            with self.assertRaisesRegex(ValueError,'bounded full preparation reference'):
                worker.load_bundle(path,expected_bundle_sha256=digest)
            validation.assert_not_called()

    def test_phase_wire_capacity_is_checked_by_serializer_and_loader(self):
        full,path,digest,_=self.retain()
        raw=path.read_bytes()
        self.assertEqual(worker.MAX_SMALL_PHASE_REFERENCE_BYTES,4096)
        self.assertEqual(worker.MAX_TAIL_PHASE_REFERENCE_BYTES,68*1024)
        with mock.patch.object(worker,'MAX_SMALL_PHASE_REFERENCE_BYTES',len(raw)):
            self.assertEqual(worker.bundle_bytes(full),raw)
            self.assertEqual(worker.load_bundle(path,expected_bundle_sha256=digest),full)
        with mock.patch.object(worker,'MAX_SMALL_PHASE_REFERENCE_BYTES',len(raw)-1):
            with self.assertRaisesRegex(ValueError,'phase reference wire capacity'):
                worker.bundle_bytes(full)
            with self.assertRaisesRegex(ValueError,'phase reference wire capacity'):
                worker.load_bundle(path,expected_bundle_sha256=digest)

    def test_supervisor_bootstraps_actual_reference_loader_before_bundle_paths(self):
        full, path, pin, _ = self.retain()
        own_pin = {'bytes': 7, 'sha256': '7' * 64}
        worker_pin = {'bytes': 8, 'sha256': '8' * 64}
        fixture_pin = {'bytes': 9, 'sha256': '9' * 64}
        self.base['plan']['code_files'] = {
            worker.SELF: worker_pin, worker.FIXTURE: fixture_pin,
            'scripts/radio_native_v3_process_tree_supervisor.py': own_pin}
        self.base['plan']['runtime_executables'] = {'python': {'path': '/usr/bin/python3'}}
        self.base['plan_sha256'] = digest(self.base['plan'])
        self.write_json(self.base_path, self.base)
        full, path, pin, _ = self.retain()
        actual_loader = mock.Mock(wraps=worker.load_bundle)
        admission = types.SimpleNamespace(load_bundle=actual_loader,
            expected_worker_argv=mock.Mock(return_value=['tiny', 'checked']),
            validate_worker_admission=mock.Mock(return_value={'tiny': 'structural'}),
            worker_role_layout=lambda value, **kwargs: worker.worker_role_layout(value, **kwargs))
        fixture = types.SimpleNamespace(EXECUTION_STATUS='BLOCKED_PREPARATION_REVIEW')
        module_loads = []
        def source_module(selected, name, expected):
            module_loads.append((Path(selected), expected))
            return admission if name == 'pinned_worker_admission' else fixture
        with mock.patch.object(supervisor, 'source_module', side_effect=source_module), \
                mock.patch.object(supervisor, 'pin_file', return_value=own_pin), \
                mock.patch.object(supervisor, 'BOOTSTRAP_SOURCE_PINS', {
                    worker.SELF: worker_pin, worker.FIXTURE: fixture_pin}):
            checked, _ = supervisor.check_admitted_worker(path, role='command', ordinal=0,
                expected_bundle_sha256=pin)
        self.assertEqual(checked['activation_evidence']['plan'], full['plan'])
        actual_loader.assert_called_once_with(path, expected_bundle_sha256=pin)
        self.assertEqual(module_loads[0][0], Path(supervisor.__file__).absolute().parents[1] / worker.SELF)
        self.assertEqual(module_loads[1][0], Path(full['code_root']) / worker.FIXTURE)

    def source_shaped_checked_role(self, role):
        ordinal = None if role in worker.WHOLE_ROLES else 0
        root = self.scope if ordinal is None else self.root
        label = 'command-0' if role == 'command' else None
        path = root / ('worker-admission.json' if role == 'prepare' else
            (label if role == 'command' else role) + '-admission.json')
        bundle = copy.deepcopy(self.base)
        bundle.update(role=role,case_ordinal=ordinal,code_root=str(root/'frozen-code'),
            derived_root=str(root/'derived'),phase_inputs={'label':label,
                'command':'tiny-exact-command','arguments_json':{'path':str(root/'arguments.json')}})
        own_pin = {'bytes':7,'sha256':'7'*64}
        worker_pin = {'bytes':8,'sha256':'8'*64}
        fixture_pin = {'bytes':9,'sha256':'9'*64}
        bundle['plan']={'runtime_executables':{'python':{'path':'/usr/bin/python3'},
            'node':{'path':'/usr/bin/node'}},'code_files':{
                worker.SELF:worker_pin,worker.FIXTURE:fixture_pin,
                'scripts/radio_native_v3_process_tree_supervisor.py':own_pin},
            'cases':[{'source_case_id':worker.NAMESPACE+f'/case{i:02d}',
                'archive_prefix':'tiny-archive/case'+str(i)} for i in range(8)]}
        bundle['public_preread']={'preparation_commit':'f'*40}
        for field in ('plan_sha256','complete_freeze_sha256','public_preread_sha256'):
            bundle[field]='f'*64
        actual_digest=self.write_json(path,bundle)
        expression = next(n.value for n in ast.walk(next(n for n in
            ast.parse(Path(worker.__file__).read_text()).body if isinstance(n,ast.FunctionDef)
            and n.name=='_validate_worker_admission')) if isinstance(n,ast.Return)
            and isinstance(n.value,ast.Dict))
        def structural_check(bundle_path, **kwargs):
            layout=worker.worker_role_layout(bundle,role=role,ordinal=ordinal)
            phase={}
            if role!='prepare':
                phase={'phase_input_pins':{},'role_identity_metadata_checked':True,
                    'full_source_domain_content_verified':False,
                    'complete_retained_transport_semantics_verified':False}
            if role=='command':
                phase['command_binding']={'kind':'prepared_source_reader','reader_ordinal':0,
                    'selected_output_sha256':'f'*64}
            return eval(compile(ast.Expression(expression),worker.__file__,'eval'),worker.__dict__,
                dict(role=role,ordinal=ordinal,plan=bundle['plan'],bundle=bundle,
                    bundle_path=str(path),expected_bundle_sha256=actual_digest,custody_sha256='f'*64,
                    running_caller=False,layout=layout,loaded_self=worker_pin,phase=phase))
        admission=types.SimpleNamespace(load_bundle=lambda *args,**kwargs:bundle,
            expected_worker_argv=worker.expected_worker_argv,
            validate_worker_admission=structural_check,worker_role_layout=worker.worker_role_layout)
        fixture=types.SimpleNamespace(EXECUTION_STATUS='BLOCKED_PREPARATION_REVIEW')
        with mock.patch.object(worker,'_validate_bundle',return_value=str(root)), \
                mock.patch.object(supervisor,'source_module',side_effect=lambda selected,name,expected:
                    admission if name=='pinned_worker_admission' else fixture), \
                mock.patch.object(supervisor,'pin_file',return_value=own_pin), \
                mock.patch.object(supervisor,'BOOTSTRAP_SOURCE_PINS',{
                    worker.SELF:worker_pin,worker.FIXTURE:fixture_pin}):
            checked,_=supervisor.check_admitted_worker(path,role=role,ordinal=ordinal,
                expected_bundle_sha256=actual_digest)
        return checked

    def test_all_seven_source_shaped_roles_reach_compact_receipt_capacity(self):
        for role in sorted(worker.ROLES):
            with self.subTest(role=role):
                checked=self.source_shaped_checked_role(role)
                attestation=supervisor.compact_admitted_attestation(checked)
                self.assertEqual(set(attestation['structural_admission']['worker_role_layout']),
                    supervisor.ADMITTED_LAYOUT_KEYS|{'bundle_path','role','ordinal',
                        'seconds_limit','shared_storage_limit_bytes'})
                controls=supervisor.admitted_role_controls(role,120 if role=='command' else
                    4800 if role in worker.WHOLE_ROLES else 600)
                if role=='prepare':
                    controls={'schema':supervisor.SCHEMA+'-admitted-prepare-controls',
                        'seconds':600,'output_bytes':supervisor.MAX_OUTPUT_BYTES,
                        'reaped_children':supervisor.MAX_REAPED_CHILDREN,
                        'case_storage_bytes':supervisor.CASE_STORAGE_BYTES,
                        'rss_bytes':supervisor.MAX_RSS_BYTES,'worker_role':role}
                input_pin={'kind':'admission-bound-prepare-worker' if role=='prepare' else
                    'admission-bound-role-worker','bundle_sha256':checked['bundle_sha256'],'role':role,
                    'ordinal':checked['ordinal']}
                _,bound=supervisor.receipt_capacity_bound(controls,code_pin={'bytes':7,'sha256':'7'*64},
                    runtime_pin={'bytes':1,'sha256':'1'*64},input_pin=input_pin,checked=checked,
                    shared_storage_root=Path(checked['shared_storage_root']))
                self.assertLessEqual(bound,supervisor.RECEIPT_RESERVATION_BYTES)

    def test_full_structural_layout_mutations_are_closed_before_receipt(self):
        checked=self.source_shaped_checked_role('command')
        for field,value in (('role','caller'),('seconds_limit',600),
                ('seconds_limit',120.0),('shared_storage_limit_bytes',supervisor.RUN_STORAGE_BYTES),
                ('receipt_scope',str(self.root/'other-supervisor'))):
            with self.subTest(field=field,value=value):
                changed=copy.deepcopy(checked)
                changed['structural_admission']['worker_role_layout'][field]=value
                with self.assertRaisesRegex(ValueError,'Structural admission layout'):
                    supervisor.compact_admitted_attestation(changed)


class EscapeGuardThreadingTests(unittest.TestCase):
    """Fresh source-pinned guarded children; imports and tiny threads only."""
    @classmethod
    def setUpClass(cls):
        cls.repo=Path(__file__).resolve().parents[1]
        previous=cls.repo/'results_radio_native_v3_portable_custody_20261003a/preparation-attempt-3'
        plan=json.loads((previous/'plan.json').read_bytes())
        freeze=json.loads((previous/'complete-freeze.json').read_bytes())
        spec=importlib.util.spec_from_file_location('tiny_guard_environment',
            cls.repo/'scripts/radio_native_v3_activation_environment.py')
        environment=importlib.util.module_from_spec(spec);spec.loader.exec_module(environment)
        cls.environment=environment.expected_environment(plan,freeze)
        cls.python=plan['runtime_executables']['python']['path']
        cls.source=Path(supervisor.__file__).absolute()
        cls.digest=hashlib.sha256(cls.source.read_bytes()).hexdigest()

    def guarded(self, payload):
        bootstrap="""import hashlib,os,sys,types
from pathlib import Path
source=Path(sys.argv[1]);raw=source.read_bytes()
assert hashlib.sha256(raw).hexdigest()==sys.argv[2]
assert len(os.environ)==10
guard=types.ModuleType('tiny_pinned_guard');guard.__file__=str(source)
exec(compile(raw,str(source),'exec'),guard.__dict__)
guard.install_child_escape_guard()
"""
        result=subprocess.run([self.python,'-I','-S','-B','-c',bootstrap+payload,
            str(self.source),self.digest],env=self.environment,capture_output=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stderr.decode(errors='replace'))
        self.assertEqual(result.stderr,b'')
        self.assertEqual(len(self.environment),10)
        return result.stdout

    def test_tiny_thread_runs_under_actual_inherited_guard(self):
        output=self.guarded("""import threading
values=[]
thread=threading.Thread(target=lambda:values.append('completed'))
thread.start();thread.join(2)
assert not thread.is_alive() and values==['completed']
print('thread-ok')
""")
        self.assertEqual(output,b'thread-ok\n')

    def test_actual_numpy_import_with_purelib_and_exact_environment(self):
        output=self.guarded("""import json,sysconfig
sys.path.append(sysconfig.get_paths()['purelib'])
import numpy
assert isinstance(numpy.__version__,str)
assert len(os.environ)==10
print(json.dumps({'status':'numpy-import-ok','threads':len(list(Path('/proc/self/task').iterdir()))},sort_keys=True))
""")
        observed=json.loads(output)
        self.assertEqual(observed['status'],'numpy-import-ok')
        self.assertGreaterEqual(observed['threads'],1)
        self.numpy_import_threads=observed['threads']

    def test_clone3_fallback_errno_and_legacy_escape_flags_stay_closed(self):
        output=self.guarded("""import ctypes,errno,json,signal
contract=guard._SECCOMP_ARCH[os.uname().machine]
library=ctypes.CDLL(None,use_errno=True)
unshare=272 if os.uname().machine=='x86_64' else 97
observed={}
for label,number,args,expected in (
 ('clone3',contract['clone3'],(0,0),errno.ENOSYS),
 ('unshare',unshare,(0x20000000,),errno.EPERM),
 ('clone-parent',contract['clone'],(0x00008000|signal.SIGCHLD,0,0,0,0),errno.EPERM),
 ('clone-new-user',contract['clone'],(0x10000000|signal.SIGCHLD,0,0,0,0),errno.EPERM),
 ('clone-new-pid',contract['clone'],(0x20000000|signal.SIGCHLD,0,0,0,0),errno.EPERM)):
 ctypes.set_errno(0);result=library.syscall(number,*args)
 observed[label]=ctypes.get_errno()
 assert result==-1 and observed[label]==expected,(label,result,observed[label])
status=dict(line.split(':',1) for line in Path('/proc/self/status').read_text().splitlines() if ':' in line)
if os.uname().machine=='x86_64':
 for label,number in (('x32-clone3',0x40000000|contract['clone3']),('x32-clone',0x40000000|contract['clone'])):
  ctypes.set_errno(0);result=library.syscall(number,0,0,0,0,0)
  observed[label]=ctypes.get_errno();assert result==-1 and observed[label]==errno.EPERM
assert status['NoNewPrivs'].strip()=='1' and status['Seccomp'].strip()=='2'
print(json.dumps(observed,sort_keys=True))
""")
        expected={'clone3':38,'unshare':1,'clone-parent':1,'clone-new-user':1,'clone-new-pid':1}
        if supervisor.os.uname().machine=='x86_64':
            expected.update({'x32-clone3':1,'x32-clone':1})
        self.assertEqual(json.loads(output),expected)


if __name__ == '__main__':
    unittest.main()
