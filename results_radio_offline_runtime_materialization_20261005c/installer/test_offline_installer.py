"""Inert synthetic archives and local admission fixtures only; no installer runs."""
import base64
import copy
import csv
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import time
import unittest
import zipfile

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('offline_installer', ROOT/'offline_installer.py')
INSTALLER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSTALLER)
ORIGINAL_PATH = Path('/workspace/scratch/da6462abff17/package-source-preparation/results_radio_runtime_bootstrap_preparation_20261005b/original-plan.json')


def pin(path):
    st = path.stat()
    return {'path': str(path.resolve()), 'bytes': st.st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'mode': stat.S_IMODE(st.st_mode)}


def budget():
    return INSTALLER.ReadBudget(INSTALLER.CEILINGS, time.monotonic()+30)


def synthetic_archive(root, tamper_record=False, traversal=False, symlink=False, pth=False):
    filename = 'fake-1.0-py3-none-any.whl'
    dist = 'fake-1.0.dist-info'
    members = {'fake/__init__.py': b'# inert synthetic bytes; never imported\n',
               dist+'/METADATA': b'Metadata-Version: 2.1\nName: fake\nVersion: 1.0\n',
               dist+'/WHEEL': b'Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n'}
    if traversal:
        members['../escape'] = b'inert traversal bytes'
    if pth:
        members['fake.pth'] = b'# inert pth bytes\n'
    record = io.StringIO(newline='')
    writer = csv.writer(record)
    for path, raw in members.items():
        value = base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b'=').decode()
        if tamper_record and path == 'fake/__init__.py':
            value = '0'*43
        writer.writerow((path, 'sha256='+value, str(len(raw))))
    writer.writerow((dist+'/RECORD', '', ''))
    members[dist+'/RECORD'] = record.getvalue().encode()
    path = root/filename
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED, allowZip64=False) as archive:
        for name, raw in members.items():
            info = zipfile.ZipInfo(name)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = ((stat.S_IFLNK if symlink and name == 'fake/__init__.py' else stat.S_IFREG) | 0o644) << 16
            archive.writestr(info, raw)
    spec = {'name': 'fake', 'version': '1.0', 'filename': filename,
            'url': 'https://files.pythonhosted.org/packages/inert/'+filename,
            'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'tags': ['py3-none-any']}
    return path, spec


def inspect(path, spec):
    fd = os.open(path, os.O_RDONLY)
    reads = budget()
    try:
        return INSTALLER.inspect_wheel(fd, spec, reads, reads.check)
    finally:
        os.close(fd)


class StaticArchiveTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def test_complete_record_member_tags_and_hash_checked_without_import(self):
        path, spec = synthetic_archive(self.root)
        result = inspect(path, spec)
        self.assertEqual(result['status'], 'STATIC_WHEEL_PREFLIGHT_VERIFIED')
        self.assertEqual(result['archive_sha256'], spec['sha256'])
        self.assertEqual(result['metadata']['tags'], spec['tags'])
        self.assertEqual(len(result['members']), 4)
        self.assertFalse(result['packages_imported'])
        self.assertFalse(result['native_elf_parsed'])
        self.assertNotIn('fake', sys.modules)

    def test_wrong_whole_archive_hash_rejected_with_partial_receipt(self):
        path, spec = synthetic_archive(self.root)
        spec['sha256'] = '0'*64
        with self.assertRaises(INSTALLER.WheelIOError) as captured:
            inspect(path, spec)
        self.assertEqual(captured.exception.receipt['status'], 'CLOSED_FAILED')
        self.assertEqual(captured.exception.receipt['members'], [])

    def test_record_hash_failure_is_detected_after_correct_whole_archive_pin(self):
        path, spec = synthetic_archive(self.root, tamper_record=True)
        with self.assertRaisesRegex(INSTALLER.WheelIOError, 'RECORD member hash'):
            inspect(path, spec)

    def test_traversal_and_symlink_archive_members_rejected(self):
        for traversal, symlink in ((True, False), (False, True)):
            path, spec = synthetic_archive(self.root, traversal=traversal, symlink=symlink)
            with self.assertRaises(INSTALLER.WheelIOError):
                inspect(path, spec)

    def test_filename_tag_and_metadata_tag_disagreement_rejected(self):
        path, spec = synthetic_archive(self.root)
        spec['tags'] = ['cp312-cp312-manylinux_2_28_x86_64']
        with self.assertRaisesRegex(INSTALLER.WheelIOError, 'filename tags'):
            inspect(path, spec)

    def test_budget_refusal_precedes_payload_reads(self):
        path, spec = synthetic_archive(self.root)
        limits = dict(INSTALLER.CEILINGS, parent_read_bytes=1)
        reads = INSTALLER.ReadBudget(limits, time.monotonic()+30)
        fd = os.open(path, os.O_RDONLY)
        try:
            with self.assertRaises(INSTALLER.WheelIOError):
                INSTALLER.inspect_wheel(fd, spec, reads, reads.check)
        finally:
            os.close(fd)
        self.assertLessEqual(reads.charged, 1)

    def test_prospective_storage_member_collision_and_pth_rejected(self):
        path, spec = synthetic_archive(self.root)
        result = inspect(path, spec)
        with self.assertRaisesRegex(INSTALLER.Refusal, 'cross_wheel_member_collision'):
            INSTALLER.install_preflight([result, result], 0, 0, INSTALLER.CEILINGS)
        with self.assertRaisesRegex(INSTALLER.Refusal, 'prospective_payload_temp_evidence_budget'):
            INSTALLER.install_preflight([result], 0, 0, dict(INSTALLER.CEILINGS, artifact_bytes=1))
        path, spec = synthetic_archive(self.root, pth=True)
        result = inspect(path, spec)
        with self.assertRaisesRegex(INSTALLER.Refusal, 'bytecode_or_pth_member'):
            INSTALLER.install_preflight([result], 0, 0, INSTALLER.CEILINGS)

    def test_archive_local_header_corruption_rejected(self):
        path, spec = synthetic_archive(self.root)
        raw = bytearray(path.read_bytes())
        raw[0:4] = b'BAD!'
        path.write_bytes(raw)
        spec['sha256'] = hashlib.sha256(raw).hexdigest()
        with self.assertRaisesRegex(INSTALLER.WheelIOError, 'local and central ZIP header'):
            inspect(path, spec)


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.python = self.root/'python'
        self.guard = self.root/'guard'
        for path in (self.python, self.guard):
            path.write_bytes(b'inert executable bytes; never run')
            path.chmod(0o755)
        self.stdlib = self.root/'lib/python3.12'
        self.stdlib.mkdir(parents=True)
        (self.stdlib/'inert.py').write_bytes(b'# inert stdlib fixture\n')
        self.seeds = []
        for relative in ('pip/__init__.py', 'pip/__main__.py'):
            path = self.root/'seed-source'/relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'# inert pip fixture; never run\n')
            self.seeds.append({'relative_path': relative, 'pin': pin(path)})
        original = json.loads(ORIGINAL_PATH.read_bytes())
        keys = ('name', 'version', 'filename', 'bytes', 'sha256', 'url', 'tags')
        source_pins = [pin(ROOT/'offline_installer.py'), pin(ORIGINAL_PATH)]
        runtime_pins = [pin(self.python), pin(self.guard), pin(self.stdlib/'inert.py')]
        runtime_pins.extend(seed['pin'] for seed in self.seeds)
        self.plan = {'schema': INSTALLER.SCHEMA, 'identity': INSTALLER.IDENTITY,
                     'purpose': 'offline-package-install-only', 'single_use': True,
                     'network': False, 'compile': False, 'native_imports': False,
                     'original_plan_pin': pin(ORIGINAL_PATH),
                     'source_pins': sorted(source_pins, key=lambda p: p['path']),
                     'runtime_pins': sorted(runtime_pins, key=lambda p: p['path']),
                     'python_executable': str(self.python), 'python_version': [3, 12, 14],
                     'stdlib_root': str(self.stdlib), 'guard_path': str(self.guard),
                     'seed_pins': self.seeds,
                     'wheels': [{'path': str(self.root/wheel['filename']),
                                 'spec': {key: wheel[key] for key in keys}}
                                for wheel in original['materialization']['official_wheels']],
                     'wheel_lock_utf8': original['materialization']['offline_hash_lock_utf8'],
                     'limits': dict(INSTALLER.CEILINGS), 'output_root': str(self.root/'output')}

    def tearDown(self):
        self.directory.cleanup()

    def validate(self, plan=None):
        raw = INSTALLER.canonical(self.plan if plan is None else plan)
        return INSTALLER.validate_plan(raw, INSTALLER.digest(raw))

    def test_complete_distinct_plan_and_original_cohort_admitted_readonly(self):
        self.assertEqual(self.validate(), self.plan)
        INSTALLER.original_cohort(self.plan, ORIGINAL_PATH.read_bytes())

    def test_plan_hash_limits_scope_and_seed_safety_are_external(self):
        raw = INSTALLER.canonical(self.plan)
        with self.assertRaisesRegex(INSTALLER.Refusal, 'expected_plan_sha256'):
            INSTALLER.validate_plan(raw, '0'*64)
        for mutation, error in ((lambda p: p.update(network=True), 'distinct_offline_installer_scope'),
                                (lambda p: p['limits'].update(wall_seconds=301), 'finite_exact_limits'),
                                (lambda p: p['seed_pins'][0].update(relative_path='pip/inert.pth'), 'pure_pinned_pip_source')):
            plan = copy.deepcopy(self.plan)
            mutation(plan)
            with self.assertRaisesRegex(INSTALLER.Refusal, error):
                self.validate(plan)

    def test_original_wheel_or_lock_mutation_not_promoted_to_authority(self):
        plan = copy.deepcopy(self.plan)
        plan['wheels'][0]['spec']['sha256'] = '0'*64
        with self.assertRaisesRegex(INSTALLER.Refusal, 'exact_original_wheels_and_lock'):
            INSTALLER.original_cohort(plan, ORIGINAL_PATH.read_bytes())
        plan = copy.deepcopy(self.plan)
        plan['wheel_lock_utf8'] += '# mutated\n'
        with self.assertRaisesRegex(INSTALLER.Refusal, 'exact_original_wheels_and_lock'):
            INSTALLER.original_cohort(plan, ORIGINAL_PATH.read_bytes())

    def test_owned_seed_command_has_all_no_network_no_compile_isolation_flags(self):
        command = INSTALLER.pip_argv(self.plan, self.root/'output')
        self.assertEqual(command[:4], [str(self.python), '-I', '-B', '-S'])
        for flag in ('--isolated', '--no-index', '--no-deps', '--no-cache-dir', '--require-hashes',
                     '--only-binary=:all:', '--no-compile', '--target'):
            self.assertIn(flag, command[-1])
        env = INSTALLER.child_environment(self.root/'output')
        self.assertNotIn('PYTHONPATH', env)
        self.assertNotIn('HOME', env)
        self.assertNotIn('PATH', env)
        self.assertEqual(env['PIP_CONFIG_FILE'], '/dev/null')

    def test_preparation_failure_retains_spent_and_second_use_refused(self):
        raw = INSTALLER.canonical(self.plan)
        report = INSTALLER.prepare(raw, INSTALLER.digest(raw), self.plan['output_root'])
        self.assertEqual(report['status'], 'FAILED_CLOSED')
        self.assertIn(report['failure'], ('actual_interpreter_identity_mismatch',
                                          'isolated_no_site_no_bytecode_parent_required'))
        self.assertTrue((Path(self.plan['output_root'])/'spent.json').is_file())
        self.assertEqual(report['installer_child_dispatches_here'], 0)
        with self.assertRaisesRegex(INSTALLER.Refusal, 'existing_output_refused'):
            INSTALLER.prepare(raw, INSTALLER.digest(raw), self.plan['output_root'])

    def test_selected_file_hash_and_symlink_identity_rejected(self):
        actual = pin(self.python)
        INSTALLER.read_verified(actual, budget())
        wrong = dict(actual, sha256='0'*64)
        with self.assertRaisesRegex(INSTALLER.Refusal, 'selected_file_sha256_mismatch'):
            INSTALLER.read_verified(wrong, budget())
        link = self.root/'symlink'
        link.symlink_to(self.python)
        wrong = dict(actual, path=str(link))
        with self.assertRaisesRegex(INSTALLER.Refusal, 'selected_symlink_refused'):
            INSTALLER.read_verified(wrong, budget())

    def test_stdlib_inventory_excludes_sites_and_pins_existing_bytecode(self):
        for relative in ('site-packages/unselected.py', '__pycache__/inert.pyc'):
            path = self.stdlib/relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'inert bytes')
        self.assertEqual(INSTALLER.stdlib_inventory(self.stdlib, budget()),
                         {str(self.stdlib/'inert.py'), str(self.stdlib/'__pycache__/inert.pyc')})

    def test_installed_byte_evidence_requires_successful_guarded_lifetime_receipt(self):
        prepared = {'status': 'OFFLINE_INSTALL_PREPARED_NOT_EXECUTED'}
        for child in ({}, {'child_exit_code': 1}, {'child_exit_code': 0, 'child_reaped': False}):
            with self.assertRaisesRegex(INSTALLER.Refusal, 'successful_guarded_wait4_child_receipt'):
                INSTALLER.verify_installed(prepared, child)

    def test_installed_member_bytes_missing_record_and_extra_code_fail_closed(self):
        output = self.root/'verification-output'
        site = output/'venv/lib/python3.12/site-packages'
        site.mkdir(parents=True)
        members = {}
        metadata = []
        for index in range(3):
            dist = 'fake%d-1.0.dist-info' % index
            metadata.append({'metadata': {'dist_info': dist}})
            for path, raw in ((dist+'/METADATA', b'inert metadata'),
                              (dist+'/RECORD', b'inert rewritten record'),
                              ('fake%d/__init__.py' % index, b'# never imported\n')):
                destination = site/path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(raw)
                members[path] = {'path': path, 'kind': 'file', 'bytes': len(raw),
                                 'sha256': hashlib.sha256(raw).hexdigest()}
        prepared = {'status': 'OFFLINE_INSTALL_PREPARED_NOT_EXECUTED', 'identity': INSTALLER.IDENTITY,
                    'plan_sha256': 'a'*64, 'output_root': str(output), 'limits': INSTALLER.CEILINGS,
                    'parent_read_charged_bytes': 0, 'selected_files_before_child': {'entries': []},
                    'preflight': {'site_member_pins': members, 'generated_paths': []},
                    'inspections': metadata}
        child = {'child_exit_code': 0, 'child_reaped': True, 'child_dispatches': 1,
                 'guarded_leaf': True, 'failure': None, 'wait4_direct_child_ru_maxrss_bytes': 1024}
        result = INSTALLER.verify_installed(prepared, child)
        self.assertEqual(result['status'], 'INSTALLED_BYTES_VERIFIED_NO_PACKAGE_IMPORT')
        self.assertFalse(result['runtime_qualified'])
        (site/'fake0/__init__.py').write_bytes(b'changed')
        with self.assertRaisesRegex(INSTALLER.Refusal, 'installed_member_whole_bytes_mismatch'):
            INSTALLER.verify_installed(prepared, child)
        (site/'fake0/__init__.py').write_bytes(b'# never imported\n')
        (site/'fake0-1.0.dist-info/RECORD').unlink()
        with self.assertRaisesRegex(INSTALLER.Refusal, 'installed_record_required'):
            INSTALLER.verify_installed(prepared, child)

    def test_absolute_expiration_and_failed_verification_retain_partial_read_charge(self):
        raw = INSTALLER.canonical(self.plan)
        result = INSTALLER.prepare(raw, INSTALLER.digest(raw), self.plan['output_root'],
                                   absolute_operation_deadline=time.monotonic()-1)
        self.assertEqual(result['failure'], 'offline_preparation_wall_deadline')
        output = self.root/'partial-verification-output'
        output.mkdir()
        (output/'a').write_bytes(b'x')
        (output/'b').write_bytes(b'yy')
        prepared = {'status': 'OFFLINE_INSTALL_PREPARED_NOT_EXECUTED', 'output_root': str(output),
                    'limits': dict(INSTALLER.CEILINGS, parent_read_bytes=1),
                    'parent_read_charged_bytes': 0}
        child = {'child_exit_code': 0, 'child_reaped': True, 'child_dispatches': 1,
                 'guarded_leaf': True, 'failure': None, 'wait4_direct_child_ru_maxrss_bytes': 1024}
        with self.assertRaisesRegex(INSTALLER.Refusal, 'parent_read_budget_exhausted'):
            INSTALLER.verify_installed(prepared, child)
        self.assertEqual(prepared['verification_parent_read_charged_bytes'], 1)
        self.assertEqual(prepared['verification_parent_read_received_bytes'], 1)
        prepared['parent_read_charged_bytes'] = 0
        with self.assertRaisesRegex(INSTALLER.Refusal, 'offline_preparation_wall_deadline'):
            INSTALLER.verify_installed(prepared, child, absolute_operation_deadline=time.monotonic()-1)
        self.assertEqual(prepared['verification_parent_read_charged_bytes'], 0)


if __name__ == '__main__':
    unittest.main()
