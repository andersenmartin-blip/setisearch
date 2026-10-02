"""Tiny isolated dedicated-supervisor tests; no pipeline/scientific execution."""
import hashlib
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/radio_native_v2_process_tree_supervisor.py'
SPEC = importlib.util.spec_from_file_location('tree_supervisor', SCRIPT)
supervisor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(supervisor)
PYTHON = str(Path(sys.executable).resolve())


class BoundedAdmissionReceiptTests(unittest.TestCase):
    """Metadata-only admission doubles; the sole executed workload is print()."""
    def metadata(self, scope):
        source = ROOT
        # Read only archived admission JSON when present. It contains metadata,
        # not telescope/source bytes. The scope is deliberately rebound to a
        # fresh test directory, so this is never a real activation admission.
        archived = source / 'results_radio_native_v2_compact_control_20261002b/control-admission.json'
        if archived.is_file():
            bundle = json.loads(archived.read_bytes())
            return {'plan': bundle['plan'], 'freeze': bundle['complete_freeze'],
                'preread': bundle['public_preread'], 'activation_receipt': bundle['activation_receipt'],
                'invocation_spending': bundle['invocation_spending'], 'execution_scope': str(scope),
                'repository_root': str(source)}
        return {'plan': json.loads((source / 'config/radio_native_v2_compact_eight_input_control_20261002n.plan.json').read_bytes()),
            'freeze': json.loads((source / 'config/radio_native_v2_ledger_launch_20261002a.runtime.json').read_bytes()),
            'preread': json.loads((source / 'config/radio_native_v2_compact_control_20261002b.execution-preread.json').read_bytes()),
            'activation_receipt': {'test_double': True}, 'invocation_spending': {'test_double': True},
            'execution_scope': str(scope), 'repository_root': str(source)}

    def checked(self, root, *, role='prepare', evidence=None):
        layout = {'worker_scope': str(root), 'receipt_scope': str(root / 'supervised'),
            'shared_storage_root': str(root), 'command_label': None, 'runtime_name': 'python'}
        ordinal = None if role in ('control', 'verifier') else 0
        structural = {key: False for key in supervisor.STRUCTURAL_BASE_KEYS}
        structural.update(schema='test-structural-double', status='TEST_DOUBLE',
            role=role, case_ordinal=ordinal, worker_role_layout=layout,
            loaded_validator_code={'bytes': 1, 'sha256': '1' * 64})
        if role != 'prepare':
            structural.update({key: False for key in supervisor.STRUCTURAL_PHASE_KEYS})
            structural['phase_input_pins'] = {'prepared_json': {'bytes': 1, 'sha256': '2' * 64}}
        if role == 'command':
            structural['command_binding'] = {'kind': 'prepared_source_reader',
                'reader_ordinal': 0, 'selected_output_sha256': '3' * 64}
        return {'schema': supervisor.SCHEMA + ('-admitted-prepare-check' if role == 'prepare' else '-admitted-worker-check'),
            'role': role, 'ordinal': ordinal,
            'argv': [PYTHON, '-I', '-S', '-B', '-c', "print('tiny repair probe')"],
            'bundle_path': str(root / 'metadata-only-admission.json'), 'bundle_sha256': '4' * 64,
            **layout, 'supervisor_python_path': PYTHON,
            'activation_evidence': evidence or self.metadata(root), 'structural_admission': structural,
            'materialized_fixture_execution_status': 'TEST_DOUBLE',
            'independent_immutable_publication_join_complete': False, **supervisor.AUTHORITY}

    def capacity(self, checked):
        role = checked['role']
        controls = supervisor.admitted_role_controls(role, 1)
        pin = {'kind': 'admission-bound-prepare-worker' if role == 'prepare' else 'admission-bound-role-worker',
            'role': role, 'ordinal': checked['ordinal'], 'bundle_sha256': checked['bundle_sha256']}
        return supervisor.receipt_capacity_bound(controls,
            code_pin=supervisor.pin_file(SCRIPT), runtime_pin=supervisor.pin_file(PYTHON),
            input_pin=pin, checked=checked, shared_storage_root=Path(checked['shared_storage_root']),
            shared_storage_cap=supervisor.ROLE_LIMITS[role]['shared_storage_bytes'], passthrough=role == 'command')

    def test_full_sized_metadata_compacts_and_all_seven_roles_fit_original_cap(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evidence = self.metadata(root)
            self.assertGreater(len(supervisor.canonical(evidence)), 1_000_000)
            for role in supervisor.ROLE_LIMITS:
                checked = self.checked(root, role=role, evidence=evidence)
                original = copy.deepcopy(checked)
                fixed, bound = self.capacity(checked)
                compact = fixed['admitted_worker_check']
                self.assertEqual(checked, original)
                self.assertNotIn('activation_evidence', compact)
                self.assertEqual(compact['structural_admission'], checked['structural_admission'])
                self.assertTrue(supervisor.verify_admitted_attestation(compact, checked))
                self.assertLess(bound, 131072)
                self.assertEqual(supervisor.RECEIPT_RESERVATION_BYTES, 131072)
                if role == 'prepare': self.assertEqual(fixed['admitted_preparation_check'], compact)
                else: self.assertIsNone(fixed['admitted_preparation_check'])

    def test_altered_reference_scope_bundle_argv_and_structural_fields_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            checked = self.checked(Path(directory))
            original = supervisor.compact_admitted_attestation(checked)
            for key in ('reference', 'scope', 'repository_root', 'bundle', 'argv', 'structural'):
                altered = copy.deepcopy(original)
                if key == 'reference': altered['activation_evidence_reference']['canonical_input_pins']['freeze']['sha256'] = '0' * 64
                elif key == 'scope': altered['activation_evidence_reference']['execution_scope'] += '/other'
                elif key == 'repository_root': altered['activation_evidence_reference']['repository_root'] += '/other'
                elif key == 'bundle': altered['bundle_sha256'] = '0' * 64
                elif key == 'argv': altered['argv'][-1] = "print('different tiny probe')"
                else: altered['structural_admission']['exact_worker_argv_checked'] = True
                with self.subTest(key=key), self.assertRaises(ValueError):
                    supervisor.verify_admitted_attestation(altered, checked)

    def test_complete_envelope_reserves_64_rows_and_final_only_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            checked = self.checked(Path(directory))
            fixed, bound = self.capacity(checked)
            row = {'namespace_pid': 2**63-1, 'kind': 'adopted_orphan', 'exit_code': -128,
                'wait4_ru_maxrss_bytes': 2**63-1, 'wait4_user_seconds': 1.7976931348623157e308,
                'wait4_system_seconds': 1.7976931348623157e308}
            receipt = {**fixed, **{key: None for key in supervisor.RUNTIME_FIELD_JSON_LIMITS},
                'reaped_processes': [row] * 64, 'reaped_process_count': 64,
                'reason': 'x' * 8190,
                'caller_accessor_observation': {'completed': True, 'request_sha256': '5' * 64,
                    'client_sha256': '6' * 64, 'response_pin': {'bytes': 65536, 'sha256': '7' * 64},
                    'accessor_peak_rss_bytes': 2**63-1, 'accessor_interval_end_epoch_ms': 2**63-1,
                    'additional_root_samples': 2**63-1},
                'root_identity': {'procfs_pid': 2**63-1, 'parent_procfs_pid': 2**63-1,
                    'namespace_pid': 2**63-1, 'namespace_pid_chain': [2**63-1] * 64,
                    'procfs_start_ticks': '9' * 32}}
            supervisor._validate_receipt_runtime_fields(receipt, fixed)
            self.assertLessEqual(len(supervisor.canonical(receipt)) + 1, bound)
            self.assertIn('filesystem_checks_completed_before_disposition', supervisor.RUNTIME_FIELD_JSON_LIMITS)
            self.assertEqual(supervisor.MAX_REAPED_CHILDREN, 64)
            receipt['reaped_processes'][0] = {**row, 'unbounded': 'x' * 1000}
            with self.assertRaises(RuntimeError): supervisor._validate_receipt_runtime_fields(receipt, fixed)

    def test_repository_root_reference_refuses_missing_relative_and_alias_spelling(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for value in (None, 'relative/repository', str(root) + '/..', str(root) + '//repository'):
                checked = self.checked(root)
                checked['activation_evidence']['repository_root'] = value
                with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'independent invocation repository root'):
                    supervisor.compact_admitted_attestation(checked)
            checked = self.checked(root)
            checked['activation_evidence'].pop('repository_root')
            with self.assertRaisesRegex(ValueError, 'activation evidence inventory'):
                supervisor.compact_admitted_attestation(checked)

    def test_bad_fixed_metadata_refuses_before_subreaper_scope_identity_or_child(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for mutation in ('escaped_argv', 'control', 'input', 'check', 'structural', 'nested'):
                checked = self.checked(root)
                controls = supervisor.admitted_role_controls('prepare', 1)
                pin = {'kind': 'admission-bound-prepare-worker', 'bundle_sha256': '4' * 64, 'role': 'prepare', 'ordinal': 0}
                if mutation == 'escaped_argv': checked['argv'][-1] = '\x00' * 30000
                elif mutation == 'control': controls['unknown_bulk'] = 'x' * 131072
                elif mutation == 'input': pin['unknown_bulk'] = 'x' * 131072
                elif mutation == 'check': checked['unknown_bulk'] = 'x' * 131072
                elif mutation == 'structural': checked['structural_admission']['unknown_bulk'] = 'x' * 131072
                else: checked['structural_admission']['source_case_id'] = {'bulk': 'x' * 100}
                fixture = types.SimpleNamespace(require_execution_ready=mock.Mock())
                with self.subTest(mutation=mutation), \
                        mock.patch.object(supervisor, 'require_isolated_supervisor_runtime'), \
                        mock.patch.object(supervisor, 'require_exact_supervisor_invocation'), \
                        mock.patch.object(supervisor, 'check_admitted_prepare_worker', return_value=(checked, fixture)), \
                        mock.patch.object(supervisor, 'set_subreaper') as subreaper, \
                        mock.patch.object(supervisor, 'durable_json') as write, \
                        mock.patch.object(supervisor.subprocess, 'Popen') as launch:
                    with self.assertRaises(ValueError):
                        supervisor.supervise_engineering_subprocess(checked['argv'], root / 'supervised', controls,
                            dedicated_process=True, input_pin=pin, _admitted_dispatch=checked)
                    subreaper.assert_not_called(); write.assert_not_called(); launch.assert_not_called()
                    self.assertFalse((root / 'supervised').exists())

    def test_actual_tiny_child_keeps_raw_guard_calls_and_persists_small_receipts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            checked = self.checked(root)
            metadata_path = root / 'test-metadata.json'
            metadata_path.write_bytes(supervisor.canonical(checked))
            driver = """import importlib.util,json,sys,types
from pathlib import Path
spec=importlib.util.spec_from_file_location('repair_supervisor',sys.argv[1]); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
checked=json.loads(Path(sys.argv[2]).read_bytes()); calls=[]
def raw_guard(**evidence):
 assert evidence == checked['activation_evidence'] and 'freeze' in evidence
 assert evidence['repository_root'] == checked['activation_evidence']['repository_root']
 calls.append(len(m.canonical(evidence)))
fixture=types.SimpleNamespace(require_execution_ready=raw_guard)
m.check_admitted_prepare_worker=lambda *args,**kwargs:(checked,fixture)
quota_state={'samples':0,'external_sha256':'8'*64}
def tiny_quota_double(): quota_state['samples']+=1
m.prepare_admitted_storage_monitor=lambda checked,fixture:(tiny_quota_double,quota_state)
# Structural admission and exact dispatcher prefix are deliberate test doubles;
# actual -I -S -B flags and complete three-variable environment are still checked.
m.require_exact_supervisor_invocation=lambda checked:None
receipt=m.dispatch_admitted_prepare_worker(checked['bundle_path'],checked['receipt_scope'],ordinal=0,expected_bundle_sha256=checked['bundle_sha256'],seconds=3)
assert calls == [calls[0],calls[0]] and calls[0]>1000000
assert receipt['status']=='ENGINEERING_SUBREAPER_SCOPE_COMPLETE',receipt['reason']
assert 'activation_evidence' not in receipt['admitted_worker_check']
assert m.verify_admitted_attestation(receipt['admitted_worker_check'],checked)
print(json.dumps({'calls':calls,'status':receipt['status']}))
"""
            result = subprocess.run([PYTHON, '-I', '-S', '-B', '-c', driver, str(SCRIPT), str(metadata_path)],
                env=supervisor.ENVIRONMENT, capture_output=True, timeout=8)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            summary = json.loads(result.stdout)
            self.assertEqual(len(summary['calls']), 2)
            for name in ('subreaper-measurements.json', 'subreaper-receipt.json'):
                raw = (root / 'supervised' / name).read_bytes()
                self.assertLess(len(raw), 131072)
                self.assertNotIn(b'"activation_evidence":', raw)
            self.assertEqual(checked['argv'][-1], "print('tiny repair probe')")

    def test_oversized_failure_text_has_exact_diagnostic_pin_and_stays_failure(self):
        reason = 'failed: ' + '\x00' * 10000
        bounded = supervisor._bounded_reason(reason)
        self.assertIn(hashlib.sha256(reason.encode()).hexdigest(), bounded)
        self.assertIn('bytes=' + str(len(reason.encode())), bounded)
        self.assertLess(len(supervisor.canonical(bounded)), supervisor.MAX_REASON_JSON_BYTES)
        with tempfile.TemporaryDirectory() as directory:
            scope = Path(directory) / 'failed-tiny-probe'
            driver = """import importlib.util,json,sys
from pathlib import Path
spec=importlib.util.spec_from_file_location('repair_supervisor',sys.argv[1]); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
def failing_launch(*args,**kwargs): raise RuntimeError('escaped failure: '+chr(0)*30000)
m.subprocess.Popen=failing_launch
controls={'schema':m.SCHEMA+'-controls','seconds':3,'output_bytes':65536,'reaped_children':64}
receipt=m.supervise_engineering_subprocess([str(Path(sys.executable).resolve()),'-I','-S','-B','-c',"print('never launched')"],Path(sys.argv[2]),controls,dedicated_process=True)
assert receipt['status']=='CLOSED_FAILED'
assert 'sha256=' in receipt['reason']
assert receipt['reaped_processes']==[]
print(json.dumps({'status':receipt['status']}))
"""
            result = subprocess.run([PYTHON, '-I', '-S', '-B', '-c', driver, str(SCRIPT), str(scope)],
                env=supervisor.ENVIRONMENT, capture_output=True, timeout=8)
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            self.assertEqual(json.loads(result.stdout)['status'], 'CLOSED_FAILED')
            for name in ('subreaper-measurements.json', 'subreaper-receipt.json'):
                self.assertLess((scope / name).stat().st_size, 131072)


class AdmittedJoinedStorageMonitorTests(unittest.TestCase):
    """Tiny files and supplied structural doubles, never a real c claim."""
    def material(self, root):
        relative = 'scripts/radio_native_v2_resource_finalization.py'
        spec = importlib.util.spec_from_file_location('monitor_allocator', ROOT/relative)
        finalizer = importlib.util.module_from_spec(spec); spec.loader.exec_module(finalizer)
        scope = root/'current'; scope.mkdir(); (scope/'cases').mkdir()
        for ordinal in range(8): (scope/'cases'/f'case{ordinal:02d}').mkdir()
        components = []; rows = []
        for index, role in enumerate(('historical_scope', 'historical_ledger', 'prospective_ledger')):
            path = root/role; path.mkdir(); (path/'record').write_bytes(b'tiny')
            sample = supervisor.sampled_storage_inventory(path)
            for source in sample['rows']:
                row = {**source, 'path': str(path) if source['path']=='.' else str(path/source['path']), 'component': role}
                if row['kind']=='file' and role!='prospective_ledger':
                    row['raw_pin']={'bytes':4,'sha256':hashlib.sha256(b'tiny').hexdigest()}
                rows.append(row)
            components.append({'role':role,'root':str(path),'observation_sha256':str(index+1)*64,
                'entry_count':sample['entry_count'],'logical_bytes':sample['logical_bytes'],
                'allocated_bytes':sample['allocated_bytes']})
        joined={'schema':finalizer.EXTERNAL_STORAGE_SCHEMA,'components':components,'rows':rows,
            'entry_count':len(rows),'logical_bytes':sum(row['bytes'] for row in rows),
            'allocated_bytes':sum(row['allocated_bytes'] for row in rows),'charged_once':True,
            'read_only':True,'execution_authorized':False,'whole_control_qualified':False,
            'lifetime_accounting_proved':False,'current_control_scope':str(scope)}
        evidence={'execution_scope':str(scope),'repository_root':str(root/'independent-original-root'),
            'plan':{'code_files':{relative:{'bytes':1,'sha256':'1'*64}}},
            'freeze':{},'activation_receipt':{},'invocation_spending':{}}
        checked={'role':'caller','ordinal':0,'activation_evidence':evidence}
        fixture=types.SimpleNamespace(__file__=str(root/'verified-material-code'/'scripts'/'fixture.py'),
            observe_authenticated_invocation_storage=mock.Mock(return_value=joined),
            pinned_component=mock.Mock(return_value=finalizer.__dict__))
        return scope, joined, checked, fixture, finalizer

    def test_monitor_uses_checked_material_source_and_samples_all_three_components(self):
        with tempfile.TemporaryDirectory() as directory:
            scope,joined,checked,fixture,_=self.material(Path(directory))
            monitor,state=supervisor.prepare_admitted_storage_monitor(checked,fixture)
            self.assertEqual(state['samples'],1)
            self.assertEqual(state['external_sha256'],hashlib.sha256(supervisor.canonical(joined)).hexdigest())
            self.assertEqual(fixture.observe_authenticated_invocation_storage.call_args.args[0],
                Path(fixture.__file__).parents[1])
            self.assertEqual(fixture.observe_authenticated_invocation_storage.call_args.kwargs['repository_root'],
                checked['activation_evidence']['repository_root'])
            (scope/'cases/case00/growing').write_bytes(b'bounded admitted fixture')
            monitor(); self.assertEqual(state['samples'],2)
            fixture.observe_authenticated_invocation_storage.assert_called_once()

    def test_each_external_content_metadata_membership_and_alias_mutation_refuses(self):
        for mutation in ('content','membership','symlink','hardlink'):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as directory:
                root=Path(directory);scope,joined,checked,fixture,_=self.material(root)
                monitor,_=supervisor.prepare_admitted_storage_monitor(checked,fixture)
                historical=root/'historical_scope'; target=historical/'record'
                if mutation=='content': target.write_bytes(b'tine')
                elif mutation=='membership': (historical/'extra').write_bytes(b'x')
                elif mutation=='symlink': (scope/'cases/case00/alias').symlink_to(target)
                else: os.link(target,scope/'cases/case00/alias')
                with self.assertRaises((ValueError,OSError)): monitor()

    def test_shared_history_and_future_supervisor_receipts_are_charged_during_poll(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);scope,joined,checked,fixture,finalizer=self.material(root)
            inventory=supervisor.sampled_storage_inventory(scope)
            row=next(row for row in inventory['rows'] if row['path']=='cases/case00')
            increase=supervisor.CASE_STORAGE_BYTES-150000-row['allocated_bytes']
            row['allocated_bytes']+=increase;inventory['allocated_bytes']+=increase
            allocation=finalizer.allocate_storage(inventory,external_inventory=joined)
            self.assertLess(allocation['cases'][0]['complete_allocated_bytes'],supervisor.CASE_STORAGE_BYTES)
            original=supervisor.sampled_storage_inventory
            def sample(path): return copy.deepcopy(inventory) if Path(path)==scope else original(path)
            with mock.patch.object(supervisor,'sampled_storage_inventory',side_effect=sample):
                with self.assertRaisesRegex(ValueError,'shared history and future supervisor receipts'):
                    supervisor.prepare_admitted_storage_monitor(checked,fixture)
            self.assertFalse((scope/'supervisor').exists())

    def test_latest_named_file_metadata_and_growth_are_charged(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);target=root/'watched';target.write_bytes(b'tiny')
            original=supervisor.os.stat;calls=0
            def changed(path,*args,**kwargs):
                nonlocal calls
                if path=='watched' and 'dir_fd' in kwargs:
                    calls+=1
                    if calls==2: target.write_bytes(b'latest named growth')
                return original(path,*args,**kwargs)
            with mock.patch.object(supervisor.os,'stat',side_effect=changed):
                sample=supervisor.sampled_storage_inventory(root)
            row=next(row for row in sample['rows'] if row['path']=='watched')
            self.assertEqual(calls,2)
            self.assertEqual(row['bytes'],target.lstat().st_size)
            self.assertEqual(row['mtime_ns'],target.lstat().st_mtime_ns)
            self.assertEqual(row['ctime_ns'],target.lstat().st_ctime_ns)


class DedicatedSubreaperTests(unittest.TestCase):
    def run_probe(self, name, *, seconds=3, output=65536, children=64):
        with tempfile.TemporaryDirectory() as directory:
            scope = Path(directory) / 'fresh-control'
            process = subprocess.run([PYTHON, '-I', '-S', '-B', str(SCRIPT), '--probe', name,
                '--scope', str(scope), '--seconds', str(seconds), '--output-bytes', str(output),
                '--reaped-children', str(children)], capture_output=True, timeout=8,
                env=supervisor.ENVIRONMENT)
            receipt = json.loads((scope / 'subreaper-receipt.json').read_bytes())
            self.assertEqual(process.stderr, b'', process.stderr.decode())
            self.assertEqual(set(path.name for path in scope.iterdir()),
                {'controls.json', 'supervisor-identity.json', 'subreaper-receipt.json', 'subreaper-measurements.json'} |
                    ({'caller-start.json', 'rss-observation-request.json', 'rss-observation.json'} if name == 'rss-handshake' else set()))
            measurements = json.loads((scope / 'subreaper-measurements.json').read_bytes())
            self.assertEqual(measurements['status'], 'PENDING_FILESYSTEM_DISPOSITION')
            self.assertTrue(receipt['measurements_fsynced_before_disposition'])
            self.assertTrue(receipt['filesystem_checks_completed_before_disposition'])
            self.assertLess(supervisor.storage_bytes(scope), supervisor.MAX_STORAGE_BYTES)
            self.assertFalse(receipt['raw_stdout_duplicate_written'])
            self.assertFalse(receipt['raw_stderr_duplicate_written'])
            self.assertTrue(receipt['subreaper_set_and_get_verified'])
            self.assertFalse(receipt['complete_process_tree_qualified'])
            self.assertFalse(receipt['supervisor_final_receipt_and_termination_independently_observed'])
            for key, value in supervisor.AUTHORITY.items():
                self.assertEqual(receipt[key], value, key)
            self.assertEqual(receipt['supervisor_code'], supervisor.pin_file(SCRIPT))
            self.assertEqual(receipt['engineering_input_pin']['source_sha256'],
                hashlib.sha256(supervisor.PROBES[name].encode()).hexdigest())
            self.assertTrue(receipt['sole_wait4_owner'])
            self.assertTrue(receipt['child_escape_guard_installed_before_exec'])
            self.assertTrue(receipt['child_escape_guard_no_new_privileges'])
            self.assertTrue(receipt['child_escape_guard_seccomp_filter'])
            return process, receipt

    def assert_complete(self, process, receipt):
        self.assertEqual(process.returncode, 0, process.stdout.decode())
        self.assertEqual(receipt['status'], 'ENGINEERING_SUBREAPER_SCOPE_COMPLETE')
        self.assertIsNone(receipt['reason'])
        self.assertEqual(receipt['root_exit_code'], 0)
        self.assertTrue(receipt['subreaper_scope_reaped_to_echild'])
        self.assertTrue(receipt['complete_descendant_wait_chain_verified'])
        self.assertEqual(receipt['tree_termination_coverage'], 'SUBREAPER_ECHILD_OBSERVED')

    def test_escape_guard_is_inherited_and_refuses_namespace_tracing_and_clone3(self):
        process, receipt = self.run_probe('escape-guard')
        self.assert_complete(process, receipt)
        self.assertGreater(receipt['observed_output_bytes']['stdout'], 0)
        self.assertEqual(receipt['retained_output_bytes']['stdout'], len(b'escape guard active\n'))
        self.assertEqual(receipt['reaped_process_count'], 1)
        self.assertIn('clone3', receipt['child_escape_guard_denied_operations'])
        self.assertIn('ptrace', receipt['child_escape_guard_denied_operations'])

    def test_proper_nested_wait_is_covered_by_root_kernel_receipt(self):
        process, receipt = self.run_probe('nested-wait')
        self.assert_complete(process, receipt)
        self.assertEqual(receipt['reaped_process_count'], 1)
        self.assertEqual(receipt['reaped_processes'][0]['kind'], 'launched_root')
        self.assertGreater(receipt['observed_output_bytes']['stdout'], 0)
        self.assertGreater(receipt['maximum_individual_process_rss_bytes'], 2 * 1024 * 1024)

    def test_orphan_is_adopted_reaped_and_required_before_echild(self):
        process, receipt = self.run_probe('orphan')
        self.assert_complete(process, receipt)
        self.assertEqual(receipt['reaped_process_count'], 2)
        self.assertEqual({row['kind'] for row in receipt['reaped_processes']},
            {'launched_root', 'adopted_orphan'})
        self.assertGreater(receipt['observed_output_bytes']['stdout'], 0)

    def test_double_fork_has_no_unreaped_daemon_in_subreaper_scope(self):
        process, receipt = self.run_probe('double-fork')
        self.assert_complete(process, receipt)
        self.assertEqual(receipt['reaped_process_count'], 2)
        self.assertEqual(sum(row['kind'] == 'adopted_orphan' for row in receipt['reaped_processes']), 1)

    def test_nonzero_adopted_exit_closes_even_when_root_exit_is_zero(self):
        process, receipt = self.run_probe('adopted-nonzero')
        self.assertEqual(process.returncode, 2)
        self.assertEqual(receipt['status'], 'CLOSED_FAILED')
        self.assertIn('nonzero', receipt['reason'])
        self.assertEqual(receipt['root_exit_code'], 0)
        self.assertTrue(receipt['subreaper_scope_reaped_to_echild'])
        self.assertTrue(any(row['kind'] == 'adopted_orphan' and row['exit_code'] == 7
            for row in receipt['reaped_processes']))

    def test_deadline_kills_root_then_adopted_children_by_pidfd_and_reaps(self):
        started = time.monotonic()
        process, receipt = self.run_probe('timeout', seconds=0.3)
        self.assertLess(time.monotonic() - started, 2)
        self.assertEqual(process.returncode, 2)
        self.assertIn('deadline', receipt['reason'])
        self.assertTrue(receipt['subreaper_scope_reaped_to_echild'])
        self.assertGreaterEqual(receipt['pidfd_cancellation_count'], 2)
        self.assertEqual(receipt['reaped_process_count'], 2)
        self.assertTrue(all(row['exit_code'] < 0 for row in receipt['reaped_processes']))

    def test_output_overflow_remains_bounded_and_is_never_written_as_raw_file(self):
        process, receipt = self.run_probe('output-overflow', output=4096)
        self.assertEqual(process.returncode, 2)
        self.assertIn('output cap', receipt['reason'])
        self.assertGreater(receipt['observed_output_bytes']['stdout'], 4096)
        self.assertEqual(receipt['retained_output_bytes']['stdout'], 4096)
        self.assertTrue(receipt['subreaper_scope_reaped_to_echild'])

    def test_storage_scan_is_bounded_and_rejects_nonregular_aliases(self):
        with tempfile.TemporaryDirectory() as directory:
            scope = Path(directory)
            for index in range(32):
                (scope / f'evidence-{index}').write_bytes(b'tiny')
            with mock.patch.object(supervisor, 'MAX_STORAGE_ENTRIES', 32):
                with self.assertRaisesRegex(ValueError, 'entry count'):
                    supervisor.storage_bytes(scope)
            self.assertGreater(supervisor.storage_bytes(scope), 0)
            (scope / 'unexpected-alias').symlink_to(scope / 'evidence-0')
            with self.assertRaisesRegex(ValueError, 'sole-link'):
                supervisor.storage_bytes(scope)

    def test_exact_raw_output_passthrough_has_no_json_summary_or_raw_file(self):
        process, receipt = self.run_probe('stdout-passthrough')
        self.assert_complete(process, receipt)
        self.assertEqual(process.stdout, b'tiny exact forwarded output\n')
        self.assertTrue(receipt['raw_output_passthrough_requested'])
        self.assertTrue(receipt['raw_output_passthrough_complete'])
        self.assertEqual(receipt['observed_output_bytes']['stdout'], len(process.stdout))

    def test_raw_output_backpressure_is_bounded_by_deadline(self):
        read_fd, write_fd = os.pipe()
        try:
            os.set_blocking(write_fd, False)
            while True:
                try: os.write(write_fd, b'x' * 65536)
                except BlockingIOError: break
            with os.fdopen(os.dup(write_fd), 'wb', buffering=0) as stream:
                started = time.monotonic()
                with self.assertRaisesRegex(RuntimeError, 'passthrough deadline'):
                    supervisor.bounded_output_passthrough(stream, b'bounded tiny payload', deadline=started + 0.04)
                self.assertLess(time.monotonic() - started, 0.2)
                self.assertFalse(os.get_blocking(stream.fileno()))
        finally:
            os.close(read_fd); os.close(write_fd)

    def test_caller_rss_accessor_is_bound_to_live_root_and_keeps_final_join_false(self):
        process, receipt = self.run_probe('rss-handshake')
        self.assert_complete(process, receipt)
        callback = receipt['caller_accessor_observation']
        self.assertTrue(callback['completed'])
        self.assertEqual(callback['client_sha256'], '1' * 64)
        self.assertGreater(callback['accessor_peak_rss_bytes'], 0)
        self.assertGreater(receipt['launched_root_procfs_sample_count'], 0)
        self.assertGreaterEqual(receipt['maximum_individual_process_rss_bytes'], callback['accessor_peak_rss_bytes'])
        self.assertTrue(receipt['complete_descendant_wait_chain_verified'])
        self.assertFalse(receipt['supervisor_final_receipt_and_termination_independently_observed'])

    def test_reaped_receipt_count_is_bounded_and_overflow_closes(self):
        process, receipt = self.run_probe('orphan', children=1)
        self.assertEqual(process.returncode, 2)
        self.assertIn('reaped-child count', receipt['reason'])
        self.assertEqual(len(receipt['reaped_processes']), 1)
        self.assertEqual(receipt['reaped_process_count'], 2)
        self.assertTrue(receipt['subreaper_scope_reaped_to_echild'])

    def test_generic_function_refuses_shared_process_before_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            scope = Path(directory) / 'uncreated'
            controls = {'schema': supervisor.SCHEMA + '-controls', 'seconds': 1,
                'output_bytes': 100, 'reaped_children': 2}
            with self.assertRaisesRegex(RuntimeError, 'dedicated-process'):
                supervisor.supervise_engineering_subprocess([PYTHON, '-c', 'pass'], scope, controls)
            self.assertFalse(scope.exists())

    def test_cli_does_not_accept_generic_argv_or_existing_worker_routes(self):
        with tempfile.TemporaryDirectory() as directory:
            scope = Path(directory) / 'uncreated'
            process = subprocess.run([PYTHON, '-I', '-S', '-B', str(SCRIPT), '--scope', str(scope),
                '--argv', PYTHON, '--control-worker', 'closed-existing-scope'],
                capture_output=True, timeout=3, env=supervisor.ENVIRONMENT)
            self.assertNotEqual(process.returncode, 0)
            self.assertFalse(scope.exists())

    def test_control_limits_reject_boolean_nonfinite_and_oversized_values(self):
        controls = {'schema': supervisor.SCHEMA + '-controls', 'seconds': 1,
            'output_bytes': 100, 'reaped_children': 2}
        for field, value in [('seconds', True), ('seconds', float('nan')),
                ('seconds', float('inf')), ('seconds', 11), ('output_bytes', True),
                ('output_bytes', 65537), ('reaped_children', 0), ('reaped_children', 65)]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                supervisor.validate_controls({**controls, field: value})

    def test_pipeline_controls_are_separate_and_keep_original_case_caps(self):
        controls = {'schema': supervisor.SCHEMA + '-admitted-prepare-controls',
            'seconds': 600, 'output_bytes': 65536, 'reaped_children': 64,
            'case_storage_bytes': 192 * 1024 * 1024, 'rss_bytes': 512 * 1024 * 1024,
            'worker_role': 'prepare'}
        supervisor.validate_admitted_prepare_controls(controls)
        with self.assertRaises(ValueError): supervisor.validate_controls(controls)
        for field, value in [('seconds', 601), ('seconds', True), ('seconds', float('nan')),
                ('output_bytes', 65537), ('reaped_children', 65), ('case_storage_bytes', 193 * 1024 * 1024),
                ('rss_bytes', 513 * 1024 * 1024), ('worker_role', 'arbitrary')]:
            with self.subTest(field=field), self.assertRaises(ValueError):
                supervisor.validate_admitted_prepare_controls({**controls, field: value})

    def test_all_role_controls_preserve_case_run_command_and_tiny_limits(self):
        for role, limits in supervisor.ROLE_LIMITS.items():
            controls = supervisor.admitted_role_controls(role, limits['seconds'])
            supervisor.validate_admitted_role_controls(controls)
            self.assertEqual(controls['shared_storage_bytes'],
                supervisor.RUN_STORAGE_BYTES if role in ('control', 'verifier') else supervisor.CASE_STORAGE_BYTES)
            self.assertEqual(controls['output_bytes'], 2 * 1024 * 1024 if role == 'command' else 65536)
            with self.subTest(role=role), self.assertRaises(ValueError):
                supervisor.validate_controls(controls)
            for name, changed in [('seconds', limits['seconds'] + 1), ('seconds', True),
                    ('output_bytes', limits['output_bytes'] + 1), ('shared_storage_bytes', limits['shared_storage_bytes'] + 1),
                    ('reaped_children', 65), ('rss_bytes', supervisor.MAX_RSS_BYTES + 1)]:
                with self.subTest(role=role, name=name), self.assertRaises(ValueError):
                    supervisor.validate_admitted_role_controls({**controls, name: changed})

    def test_generic_role_dispatch_checks_before_scope_creation_or_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            scope = Path(directory) / 'not-created'
            for role in supervisor.ROLE_LIMITS:
                if role == 'prepare': continue
                with self.subTest(role=role), \
                        mock.patch.object(supervisor, 'check_admitted_worker', side_effect=ValueError('Rejected role admission')) as check, \
                        mock.patch.object(supervisor.subprocess, 'Popen') as launch:
                    with self.assertRaisesRegex(ValueError, 'Rejected role admission'):
                        supervisor.dispatch_admitted_worker(scope / 'bundle.json', scope, role=role,
                            ordinal=None if role in ('control', 'verifier') else 0,
                            expected_bundle_sha256='0' * 64)
                    check.assert_called_once(); launch.assert_not_called()
                    self.assertFalse(scope.exists())

    def test_exact_supervisor_orig_argv_refuses_extra_flags_and_interpreter_alias(self):
        checked = {'supervisor_python_path': PYTHON}
        prefix = [PYTHON, '-I', '-S', '-B', str(SCRIPT)]
        with mock.patch.object(supervisor.sys, 'orig_argv', prefix + ['--admitted-worker']):
            supervisor.require_exact_supervisor_invocation(checked)
        for argv in ([PYTHON, '-I', '-S', '-B', '-X', 'utf8', str(SCRIPT)],
                ['python', '-I', '-S', '-B', str(SCRIPT)],
                [PYTHON, '-I', '-S', '-B', str(SCRIPT.parent / 'alias.py')]):
            with self.subTest(argv=argv), mock.patch.object(supervisor.sys, 'orig_argv', argv), \
                    self.assertRaisesRegex(RuntimeError, 'Exact supervisor interpreter invocation'):
                supervisor.require_exact_supervisor_invocation(checked)

    def test_caller_rss_handshake_rejects_forged_pid_without_writing_response(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); now = time.time_ns() // 1000000
            request = {'dispatch_at_epoch_ms': now, 'returned_at_epoch_ms': now, 'client_sha256': '1' * 64}
            supervisor.durable_json(root / 'rss-observation-request.json', request)
            supervisor.durable_json(root / 'caller-start.json', {'identity': 'node-proc:123',
                'pid': 999, 'proc_pid': 123, 'started_at_epoch_ms': now})
            with mock.patch.object(supervisor, 'sample_root_memory') as sample, \
                    self.assertRaisesRegex(ValueError, 'reported start differs'):
                supervisor.caller_rss_handshake(root,
                    root_identity={'procfs_pid': 123, 'namespace_pid': 456}, observer={'procfs_pid': 1},
                    launch_epoch_ms=now, sample_count=1, root_peak=1024, state={})
            sample.assert_not_called()
            self.assertFalse((root / 'rss-observation.json').exists())

    def test_caller_observation_json_refuses_duplicate_and_nonfinite_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'metadata.json'
            for raw in (b'{"client_sha256":"a","client_sha256":"b"}', b'{"timestamp":NaN}'):
                path.write_bytes(raw)
                with self.subTest(raw=raw), self.assertRaises(ValueError):
                    supervisor.read_json_evidence(path)

    def test_incomplete_live_rss_publication_retries_without_sampling_or_response(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'rss-observation-request.json').write_bytes(b'{')
            state = {}
            for failure in (json.JSONDecodeError('incomplete', '{', 1),
                    supervisor.EvidenceChangedDuringRead('live publication changed')):
                with self.subTest(failure=type(failure).__name__), \
                        mock.patch.object(supervisor, 'read_json_evidence', side_effect=failure), \
                        mock.patch.object(supervisor, 'sample_root_memory') as sample:
                    supervisor.caller_rss_handshake(root, root_identity={}, observer={},
                        launch_epoch_ms=1, sample_count=1, root_peak=1, state=state)
                    sample.assert_not_called()
                    self.assertEqual(state, {})
                    self.assertFalse((root / 'rss-observation.json').exists())

    def test_engineering_pin_reader_refuses_oversized_input_before_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'oversized'
            path.write_bytes(b'tiny bounded engineering evidence')
            with mock.patch.object(supervisor.os, 'read') as read:
                with self.assertRaisesRegex(ValueError, 'Bounded regular'):
                    supervisor.pin_file(path, maximum=4)
                read.assert_not_called()

    def test_admitted_dispatch_checks_before_creating_scope_or_spawning(self):
        with tempfile.TemporaryDirectory() as directory:
            scope = Path(directory) / 'not-created'
            with mock.patch.object(supervisor, 'check_admitted_prepare_worker',
                    side_effect=ValueError('Rejected admission')) as check, \
                    mock.patch.object(supervisor.subprocess, 'Popen') as launch:
                with self.assertRaisesRegex(ValueError, 'Rejected admission'):
                    supervisor.dispatch_admitted_prepare_worker(scope / 'missing.json', scope,
                        ordinal=0, expected_bundle_sha256='0' * 64)
                check.assert_called_once(); launch.assert_not_called()
                self.assertFalse(scope.exists())

    def test_materialized_fixture_gate_refuses_before_scope_and_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            scope = Path(directory) / 'preparation-supervisor'
            checked = {'receipt_scope': str(scope), 'argv': [PYTHON, '-c', 'pass'],
                'activation_evidence': {}}
            fixture = mock.Mock()
            fixture.require_execution_ready.side_effect = RuntimeError('BLOCKED_PREPARATION_REVIEW')
            with mock.patch.object(supervisor, 'check_admitted_prepare_worker', return_value=(checked, fixture)), \
                    mock.patch.object(supervisor.subprocess, 'Popen') as launch, \
                    mock.patch.object(supervisor.sys, 'flags',
                        types.SimpleNamespace(isolated=1, no_site=1, dont_write_bytecode=1)):
                with self.assertRaisesRegex(RuntimeError, 'BLOCKED_PREPARATION_REVIEW'):
                    supervisor.dispatch_admitted_prepare_worker(scope / 'bundle.json', scope,
                        ordinal=0, expected_bundle_sha256='0' * 64)
                fixture.require_execution_ready.assert_called_once()
                launch.assert_not_called(); self.assertFalse(scope.exists())

    def test_admitted_cli_requires_independently_retained_bundle_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            scope = Path(directory) / 'not-created'
            process = subprocess.run([PYTHON, '-I', '-S', '-B', str(SCRIPT),
                '--admitted-prepare-worker', '--admission-bundle', str(scope / 'bundle.json'),
                '--ordinal', '0', '--scope', str(scope)], capture_output=True, timeout=3,
                env=supervisor.ENVIRONMENT)
            self.assertNotEqual(process.returncode, 0)
            self.assertIn(b'retained SHA256', process.stderr)
            self.assertFalse(scope.exists())

    def test_admission_check_only_rejects_scope_and_checks_without_subprocess(self):
        with tempfile.TemporaryDirectory() as directory:
            scope = Path(directory) / 'not-created'
            process = subprocess.run([PYTHON, '-I', '-S', '-B', str(SCRIPT), '--admission-check-only',
                '--admission-bundle', str(scope / 'bundle.json'), '--bundle-sha256', '0' * 64,
                '--ordinal', '0', '--scope', str(scope)], capture_output=True, timeout=3,
                env=supervisor.ENVIRONMENT)
            self.assertNotEqual(process.returncode, 0)
            self.assertIn(b'no receipt scope', process.stderr)
            self.assertFalse(scope.exists())

    def test_bundle_hash_and_special_files_refuse_before_loading_worker(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = Path(directory) / 'bundle.json'; bundle.write_bytes(b'{}')
            with mock.patch.object(supervisor, 'source_module') as loader, \
                    mock.patch.object(supervisor.subprocess, 'Popen') as launch:
                with self.assertRaisesRegex(ValueError, 'retained byte hash'):
                    supervisor.check_admitted_prepare_worker(bundle, ordinal=0,
                        expected_bundle_sha256='0' * 64)
                loader.assert_not_called(); launch.assert_not_called()
                fifo = Path(directory) / 'fifo'; os.mkfifo(fifo)
                with self.assertRaisesRegex(ValueError, 'sole-link'):
                    supervisor.check_admitted_prepare_worker(fifo, ordinal=0,
                        expected_bundle_sha256='0' * 64)

    def test_source_module_ignores_bytecode_and_rejects_changed_source_pins(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'module.py'; source.write_bytes(b'value=7\n')
            expected = supervisor.pin_file(source)
            loaded = supervisor.source_module(source, 'tiny_source_module', expected)
            self.assertEqual(loaded.value, 7)
            source.write_bytes(b'value=8\n')
            with self.assertRaisesRegex(ValueError, 'source pin drift'):
                supervisor.source_module(source, 'tiny_source_module', expected)
            self.assertEqual(set(Path(directory).iterdir()), {source})

    def test_unverified_bundle_cannot_select_executable_admission_implementation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); bundle = root / 'bundle.json'
            own_key = 'scripts/radio_native_v2_process_tree_supervisor.py'
            module_key = 'scripts/radio_native_v2_worker_admission.py'
            supplied = {'plan': {'code_files': {own_key: supervisor.pin_file(SCRIPT),
                module_key: {'bytes': 10, 'sha256': '0' * 64}}}, 'code_root': str(root)}
            raw = supervisor.canonical(supplied) + b'\n'; bundle.write_bytes(raw)
            with mock.patch.object(supervisor, 'source_module') as loader:
                with self.assertRaisesRegex(ValueError, 'bootstrap pins'):
                    supervisor.check_admitted_prepare_worker(bundle, ordinal=0,
                        expected_bundle_sha256=hashlib.sha256(raw).hexdigest())
                loader.assert_not_called()
            self.assertEqual(set(root.iterdir()), {bundle})

    def test_admission_propagates_authenticated_root_without_selecting_plan_or_material_root(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); bundle_path = root / 'bundle.json'
            original_root = str(root / 'original-repository')
            material_root = str(root / 'control' / 'frozen-code')
            own_key = 'scripts/radio_native_v2_process_tree_supervisor.py'
            layout = {'worker_scope': str(root / 'case'), 'receipt_scope': str(root / 'case' / 'supervisor'),
                'shared_storage_root': str(root / 'case'), 'command_label': None, 'runtime_name': 'python'}
            # The worker is a deliberate structural double: this isolates the
            # dispatcher edge so a later refactor cannot replace the separately
            # authenticated bundle root with the plan or copied source root.
            supplied = {'plan': {'invocation_repository_root': str(root / 'untrusted-plan-root'),
                    'runtime_executables': {'python': {'path': PYTHON}},
                    'code_files': {own_key: supervisor.pin_file(SCRIPT), **supervisor.BOOTSTRAP_SOURCE_PINS}},
                'code_root': material_root, 'invocation_repository_root': original_root,
                'execution_scope': str(root / 'control'), 'complete_freeze': {}, 'public_preread': {},
                'activation_receipt': {}, 'invocation_spending': {}}
            raw = supervisor.canonical(supplied) + b'\n'; bundle_path.write_bytes(raw)
            admission = types.SimpleNamespace(expected_worker_argv=mock.Mock(return_value=[PYTHON, '-c', 'pass']),
                validate_worker_admission=mock.Mock(return_value={}),
                worker_role_layout=mock.Mock(return_value=layout))
            fixture = types.SimpleNamespace(EXECUTION_STATUS='BLOCKED_PREPARATION_REVIEW')
            with mock.patch.object(supervisor, 'source_module', side_effect=[admission, fixture]) as loader, \
                    mock.patch.object(supervisor.subprocess, 'Popen') as launch:
                checked, observed_fixture = supervisor.check_admitted_prepare_worker(bundle_path, ordinal=0,
                    expected_bundle_sha256=hashlib.sha256(raw).hexdigest())
                self.assertIs(observed_fixture, fixture)
                self.assertEqual(checked['activation_evidence']['repository_root'], original_root)
                self.assertNotEqual(checked['activation_evidence']['repository_root'],
                    checked['activation_evidence']['plan']['invocation_repository_root'])
                self.assertNotEqual(checked['activation_evidence']['repository_root'], material_root)
                self.assertEqual(Path(loader.call_args_list[0].args[0]).parent.parent, Path(material_root))
                launch.assert_not_called()
            self.assertEqual(set(root.iterdir()), {bundle_path})

    def test_actual_supervisor_interpreter_flags_are_checked_before_mutation(self):
        flags = types.SimpleNamespace(isolated=0, no_site=1, dont_write_bytecode=1)
        with tempfile.TemporaryDirectory() as directory:
            scope = Path(directory) / 'not-created'
            controls = {'schema': supervisor.SCHEMA + '-controls', 'seconds': 1,
                'output_bytes': 100, 'reaped_children': 2}
            with mock.patch.object(supervisor.sys, 'flags', flags), \
                    mock.patch.object(supervisor.subprocess, 'Popen') as launch, \
                    mock.patch.object(supervisor, 'set_subreaper') as setter:
                with self.assertRaisesRegex(RuntimeError, 'Actual isolated'):
                    supervisor.supervise_engineering_subprocess([PYTHON, '-c', 'pass'], scope,
                        controls, dedicated_process=True)
                setter.assert_not_called(); launch.assert_not_called()
                self.assertFalse(scope.exists())

    def test_bootstrap_pins_bind_current_reviewed_dependency_sources(self):
        for relative, expected in supervisor.BOOTSTRAP_SOURCE_PINS.items():
            self.assertEqual(supervisor.pin_file(ROOT / relative), expected, relative)

    def synthetic_admission_helpers(self):
        # Reuse tiny supplied-claim materials; no prospective generator runs.
        modules = {}
        for name in ('radio_native_v2_compact_eight_case_resource_fixture',
                'radio_native_v2_worker_admission'):
            relative = 'scripts/' + name + '.py'
            modules[name] = supervisor.source_module(ROOT / relative, name,
                supervisor.BOOTSTRAP_SOURCE_PINS[relative])
        worker = modules['radio_native_v2_worker_admission']
        fixture = modules['radio_native_v2_compact_eight_case_resource_fixture']
        for name, expected in (
                ('radio_native_v2_runtime_custody', worker.CUSTODY_IMPLEMENTATION_PIN),
                ('radio_native_v2_prospective_spending', worker.SPENDING_IMPLEMENTATION_PIN),
                ('radio_native_v2_historical_observation', fixture.HISTORICAL_OBSERVATION_IMPLEMENTATION_PIN)):
            modules[name] = supervisor.source_module(ROOT / ('scripts/' + name + '.py'), name, expected)
        with mock.patch.dict(sys.modules, modules):
            helpers = supervisor.source_module(ROOT / 'tests/test_radio_native_v2_worker_admission.py',
                'tiny_supplied_claim_helpers')
        return helpers

    def synthetic_admission_materials(self, root):
        return self.synthetic_admission_helpers().synthetic_worker_materials(root)

    def test_real_structural_check_is_read_only_and_large_dispatch_stays_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            materials = self.synthetic_admission_materials(Path(directory))
            before = sorted(str(path) for path in Path(directory).rglob('*'))
            with mock.patch.object(supervisor.subprocess, 'Popen') as launch, \
                    mock.patch.object(supervisor.sys, 'flags',
                        types.SimpleNamespace(isolated=1, no_site=1, dont_write_bytecode=1)):
                checked, fixture = supervisor.check_admitted_prepare_worker(materials['bundle_path'],
                    ordinal=0, expected_bundle_sha256=materials['bundle_sha256'])
                self.assertEqual(checked['argv'], materials['argv'])
                self.assertFalse(checked['independent_immutable_publication_join_complete'])
                self.assertEqual(checked['materialized_fixture_execution_status'], 'BLOCKED_PREPARATION_REVIEW')
                self.assertEqual(checked['structural_admission']['status'],
                    'LOCAL_SUPPLIED_PREREAD_VALIDATED_EXECUTION_BLOCKED')
                # This supplied test root is structurally valid metadata but
                # fails the new independently pinned historical root policy
                # before it can reach the actual dispatcher environment gate.
                with self.assertRaisesRegex(ValueError, 'independently authenticated original historical repository root'):
                    supervisor.dispatch_admitted_prepare_worker(materials['bundle_path'],
                        Path(checked['receipt_scope']), ordinal=0,
                        expected_bundle_sha256=materials['bundle_sha256'])
                launch.assert_not_called()
            self.assertEqual(before, sorted(str(path) for path in Path(directory).rglob('*')))
            self.assertFalse((materials['case_root'] / 'deterministic-source.bin').exists())

    def test_real_admission_check_cli_has_no_scope_or_generator_side_effects(self):
        with tempfile.TemporaryDirectory() as directory:
            materials = self.synthetic_admission_materials(Path(directory))
            before = sorted(str(path) for path in Path(directory).rglob('*'))
            process = subprocess.run([PYTHON, '-I', '-S', '-B', str(SCRIPT), '--admission-check-only',
                '--admission-bundle', str(materials['bundle_path']), '--bundle-sha256', materials['bundle_sha256'],
                '--ordinal', '0'], capture_output=True, timeout=8, env=supervisor.ENVIRONMENT)
            self.assertEqual(process.returncode, 0, process.stderr.decode())
            result = json.loads(process.stdout)
            self.assertFalse(result['execution_authorized'])
            self.assertEqual(result['argv'], materials['argv'])
            self.assertEqual(before, sorted(str(path) for path in Path(directory).rglob('*')))


    def test_real_role_checks_bind_case_and_whole_layouts_without_dispatch(self):
        helpers = self.synthetic_admission_helpers()
        for role in ('caller', 'command', 'lossless-project', 'control', 'verifier'):
            with self.subTest(role=role), tempfile.TemporaryDirectory() as directory:
                materials = helpers.synthetic_role_materials(Path(directory), role)
                worker = materials['role_materials']
                before = sorted(str(path) for path in Path(directory).rglob('*'))
                with mock.patch.object(supervisor.subprocess, 'Popen') as launch, \
                        mock.patch.object(supervisor.sys, 'flags',
                            types.SimpleNamespace(isolated=1, no_site=1, dont_write_bytecode=1)):
                    checked, _ = supervisor.check_admitted_worker(worker['bundle_path'], role=role,
                        ordinal=worker['ordinal'], expected_bundle_sha256=worker['bundle_sha256'])
                    self.assertEqual(checked['argv'], worker['argv'])
                    self.assertEqual(checked['role'], role)
                    self.assertFalse(checked['execution_authorized'])
                    expected_scope = materials['scope'] if role in ('control', 'verifier') else materials['case_root']
                    self.assertEqual(checked['worker_scope'], str(expected_scope))
                    self.assertEqual(checked['shared_storage_root'], str(expected_scope))
                    self.assertFalse(Path(checked['receipt_scope']).exists())
                    with self.assertRaisesRegex(ValueError, 'independently authenticated original historical repository root'):
                        supervisor.dispatch_admitted_worker(worker['bundle_path'], checked['receipt_scope'],
                            role=role, ordinal=worker['ordinal'], expected_bundle_sha256=worker['bundle_sha256'])
                    launch.assert_not_called()
                self.assertEqual(before, sorted(str(path) for path in Path(directory).rglob('*')))


if __name__ == '__main__':
    unittest.main()
