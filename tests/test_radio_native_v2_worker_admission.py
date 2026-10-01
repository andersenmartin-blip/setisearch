"""Synthetic supplied publication claims only; no generator or worker launch."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import radio_native_v2_compact_eight_case_resource_fixture as fixture
import radio_native_v2_worker_admission as admission

ROOT = Path(__file__).resolve().parents[1]
PYTHON = str(Path(sys.executable).resolve())
SCRIPT = ROOT / admission.SELF


def tiny_pin(raw):
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}


def synthetic_worker_materials(root, *, ordinal=0, plan=None, derived_sources=None):
    """Reusable synthetic local proof fixture; no real public readback exists.

    Optional actual prospective plan/derived_sources support testing a pinned
    generated guard through its independent BLOCKED fixture refusal. By
    default only tiny inert derived strings are materialized. The returned
    complete freeze is structurally valid with synthetic measured versions;
    it is deliberately not an independently recomputed execution closure.
    """
    root = Path(root).absolute()
    scope = root / 'whole'; case = scope / 'cases' / f'case{ordinal:02d}'
    code = case / 'frozen-code'; derived = case / 'derived'
    code.mkdir(parents=True); derived.mkdir()
    plan = copy.deepcopy(fixture.build_plan(ROOT) if plan is None else plan)
    # A test can construct materials before root adds the validator to its
    # shared CODE_FILES. The validator is always an explicit prospective pin.
    plan['code_files'][admission.SELF] = tiny_pin(SCRIPT.read_bytes())
    if derived_sources is None:
        derived_sources = {'prepare.py': b'# tiny synthetic inert preparation source\n',
            'fresh-caller.js': b'// tiny synthetic inert caller\n',
            'lossless-helper.js': b'// tiny synthetic inert helper\n'}
    plan['derived_code'] = {name: tiny_pin(raw) for name, raw in derived_sources.items()}
    for relative, wanted in plan['code_files'].items():
        path = code / relative; path.parent.mkdir(parents=True, exist_ok=True)
        raw = (ROOT / relative).read_bytes()
        if tiny_pin(raw) != wanted:
            raise ValueError('Synthetic materials must match supplied prospective source pins')
        path.write_bytes(raw)
    for name, raw in derived_sources.items():
        (derived / name).write_bytes(raw)
    hashes = {path: pin['sha256'] for path, pin in plan['code_files'].items()
              if not path.startswith('tests/')}
    for relative in ('scripts/radio_native_v2_runner_freeze.py', 'scripts/radio_native_v2_broker_host.js'):
        hashes[relative] = tiny_pin((ROOT / relative).read_bytes())['sha256']
    inputs = {path: pin['sha256'] for path, pin in plan['code_files'].items() if path.startswith('tests/')}
    paths = {name: record['path'] for name, record in plan['runtime_executables'].items()}
    paths['git'] = str(Path(shutil.which('git')).resolve())
    runtime = {path: tiny_pin(Path(path).read_bytes())['sha256'] for path in paths.values()}
    coverage = {key: False for key in ('external_tool_transport_runtime_frozen',
        'operating_system_kernel_frozen', 'git_credential_and_network_configuration_frozen',
        'git_script_interpreters_qualified', 'arbitrary_node_modules_qualified',
        'python_cached_bytecode_execution_qualified', 'python_import_source_policy_qualified')}
    coverage.update({'repository': 'synthetic structural metadata only',
        'python_numpy': 'synthetic structural metadata only',
        'git_node': 'synthetic structural metadata only',
        'qualification_scope': 'synthetic local assertions; no public readback or runtime closure'})
    freeze = {'schema': admission.FREEZE_SCHEMA, 'freeze_kind': 'COMPLETE_RUNNER_BROKER_RUNTIME',
        'mode': 'PROSPECTIVE_ENGINEERING_ONLY', 'namespace': admission.FREEZE_NAMESPACE,
        **{key: False for key in admission.FREEZE_DISABLED}, 'transport_qualification': None,
        'repository_code_inventory': sorted(hashes), 'code_sha256s': hashes,
        'input_file_inventory': sorted(inputs), 'input_sha256s': inputs,
        'runtime_file_inventory': sorted(runtime), 'runtime_sha256s': runtime,
        'executables': {name: {'invocation': path, 'resolved': path, 'sha256': runtime[path],
            'version': {'node': 'synthetic-unverified'} if name == 'node' else
                sys.version if name == 'python' else 'synthetic-unverified-git'} for name, path in paths.items()},
        'git_exec_path': '/usr/lib/git-core', 'git_runtime_file_inventory': [],
        'git_node_elf_inventory': [], 'unavailable_unused_python_extensions': {},
        'python': sys.version, 'numpy': 'synthetic-unverified',
        'environment_fingerprints': {key: None for key in admission.ENVIRONMENT_KEYS}, 'coverage': coverage}
    proof = {'schema': admission.PREREAD_SCHEMA, 'namespace': admission.NAMESPACE,
        'plan_sha256': hashlib.sha256(admission.canonical(plan)).hexdigest(),
        'complete_freeze_sha256': hashlib.sha256(admission.canonical(freeze)).hexdigest(),
        'public_immutable_readback_verified': True, 'engineering_control_admitted': True,
        'code_files_verified': plan['code_files'], 'preparation_commit': '1' * 40,
        **admission.AUTHORITY}
    bundle = admission.build_admission_bundle(plan, freeze, proof, execution_scope=str(scope), ordinal=ordinal)
    path = case / 'worker-admission.json'
    raw = admission.bundle_bytes(bundle); path.write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    argv = admission.expected_worker_argv(bundle, str(path), ordinal=ordinal, expected_bundle_sha256=digest)
    return {'bundle': bundle, 'bundle_path': path, 'bundle_sha256': digest, 'argv': argv,
        'scope': scope, 'case_root': case, 'code_root': code, 'derived_root': derived,
        'plan': plan, 'freeze': freeze, 'proof': proof}


class WorkerAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.materials = synthetic_worker_materials(self.root)

    def validate(self, **kwargs):
        materials = self.materials
        values = {'ordinal': materials['bundle']['case_ordinal'],
            'argv': materials['argv'], 'environment': dict(admission.CHILD_ENVIRONMENT),
            'expected_bundle_sha256': materials['bundle_sha256']}
        values.update(kwargs)
        return admission.validate_worker_admission(str(materials['bundle_path']), **values)

    def retain_changed_bundle(self, bundle=None, *, canonical=True):
        bundle = self.materials['bundle'] if bundle is None else bundle
        raw = admission.canonical(bundle) + b'\n' if canonical else json.dumps(bundle, indent=2).encode() + b'\n'
        self.materials['bundle_path'].write_bytes(raw)
        self.materials['bundle_sha256'] = hashlib.sha256(raw).hexdigest()
        self.materials['argv'][-1] = self.materials['bundle_sha256']

    def refresh_embedded_digests(self):
        bundle = self.materials['bundle']; plan = bundle['plan']; freeze = bundle['complete_freeze']; proof = bundle['public_preread']
        bundle['plan_sha256'] = proof['plan_sha256'] = hashlib.sha256(admission.canonical(plan)).hexdigest()
        bundle['complete_freeze_sha256'] = proof['complete_freeze_sha256'] = hashlib.sha256(admission.canonical(freeze)).hexdigest()
        bundle['public_preread_sha256'] = hashlib.sha256(admission.canonical(proof)).hexdigest()
        self.retain_changed_bundle()

    def test_valid_local_supplied_claim_has_no_publication_or_execution_authority(self):
        before = sorted(str(path) for path in self.root.rglob('*'))
        with mock.patch.object(subprocess, 'Popen', side_effect=AssertionError('Admission never launches workers')):
            receipt = self.validate()
        self.assertEqual(receipt['status'], 'LOCAL_SUPPLIED_PREREAD_VALIDATED_EXECUTION_BLOCKED')
        self.assertTrue(receipt['exact_worker_argv_checked'])
        self.assertTrue(receipt['complete_child_environment_checked'])
        self.assertTrue(receipt['current_materialized_code_and_derived_pins_checked'])
        self.assertFalse(receipt['publication_claim_independently_verified'])
        self.assertFalse(receipt['complete_expected_runtime_closure_verified'])
        self.assertFalse(receipt['runtime_and_supplement_join_verified'])
        self.assertTrue(receipt['fixture_execution_guard_still_required'])
        for key, value in admission.AUTHORITY.items():
            self.assertEqual(receipt[key], value, key)
        self.assertFalse(receipt['large_source_generation_admitted'])
        self.assertEqual(before, sorted(str(path) for path in self.root.rglob('*')))

    def test_eight_case_ordinals_bind_exact_domains_and_case_layouts(self):
        receipt = self.validate()
        self.assertEqual(receipt['source_domain_hex'], fixture.source_domain(0).hex())
        another = synthetic_worker_materials(self.root / 'another', ordinal=7)
        result = admission.validate_worker_admission(str(another['bundle_path']), ordinal=7,
            argv=another['argv'], environment=dict(admission.CHILD_ENVIRONMENT),
            expected_bundle_sha256=another['bundle_sha256'])
        self.assertEqual(result['source_domain_hex'], fixture.source_domain(7).hex())
        self.assertTrue(result['source_case_id'].endswith('/case07'))

    def test_builder_creates_no_execution_scope_and_copies_input_metadata(self):
        fresh = self.root / 'must-remain-uncreated'
        bundle = admission.build_admission_bundle(self.materials['plan'], self.materials['freeze'],
            self.materials['proof'], execution_scope=str(fresh), ordinal=2)
        self.assertFalse(fresh.exists())
        bundle['plan']['cases'][2]['source_bytes'] = 0
        self.assertEqual(self.materials['plan']['cases'][2]['source_bytes'], 26*1024**2)

    def test_cached_parent_bundle_digest_refuses_replacement_even_if_internal_pins_match(self):
        old = self.materials['bundle_sha256']
        self.materials['bundle']['public_preread']['preparation_commit'] = '2' * 40
        self.refresh_embedded_digests()
        with self.assertRaisesRegex(ValueError, 'bundle bytes changed'):
            self.validate(expected_bundle_sha256=old)

    def test_retained_digest_is_mandatory_and_covers_the_terminal_newline(self):
        raw = self.materials['bundle_path'].read_bytes()
        for digest in (None, '1' * 64, hashlib.sha256(raw[:-1]).hexdigest()):
            with self.subTest(digest=digest), self.assertRaises(ValueError):
                self.validate(expected_bundle_sha256=digest)

    def test_canonical_json_duplicates_and_nonfinite_are_refused_even_with_matching_digest(self):
        self.retain_changed_bundle(canonical=False)
        with self.assertRaisesRegex(ValueError, 'canonical admission bundle'):
            self.validate()
        for raw in (b'{"schema":"x","schema":"y"}\n', b'{"claim":NaN}\n'):
            self.materials['bundle_path'].write_bytes(raw)
            self.materials['bundle_sha256'] = hashlib.sha256(raw).hexdigest()
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                self.validate()

    def test_exact_argv_refuses_extra_argument_flags_crosscase_or_wrong_domain(self):
        original = list(self.materials['argv'])
        for index, value in ((1, '-E'), (2, '-s'), (3, '-b'), (5, str(self.root / 'wrong-scope')),
                (7, 'different-namespace'), (8, '1'), (9, admission.PREFIX + '/case01-fixed'),
                (10, str(self.root / 'alternate-bundle.json')), (11, '0'*64)):
            changed = list(original); changed[index] = value
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, 'exact preparation worker argv'):
                self.validate(argv=changed)
        with self.assertRaises(ValueError): self.validate(argv=original + ['extra'])
        with self.assertRaises(ValueError): self.validate(role='control-worker')

    def test_minimal_complete_child_environment_refuses_injection_missing_or_numeric_values(self):
        for environment in ({**admission.CHILD_ENVIRONMENT, 'LD_PRELOAD': '/unfrozen.so'},
                {**admission.CHILD_ENVIRONMENT, 'PYTHONPATH': '/alternate'},
                {**admission.CHILD_ENVIRONMENT, 'LC_CTYPE': 'C.UTF-8'},
                {'PATH': '/usr/bin:/bin', 'LANG': 'C'},
                {**admission.CHILD_ENVIRONMENT, 'LANG': 0}):
            with self.subTest(environment=environment), self.assertRaises(ValueError):
                self.validate(environment=environment)

    def test_ordinals_refuse_boolean_float_string_or_crosscase(self):
        for ordinal in (True, 0.0, '0', -1, 8, 1):
            with self.subTest(ordinal=ordinal), self.assertRaises(ValueError):
                self.validate(ordinal=ordinal)

    def test_recomputed_metadata_hashes_do_not_hide_authority_claims(self):
        for location, key, value in (('plan', 'rng_draws', False),
                ('plan', 'execution_authorized', 0), ('plan', 'large_source_generation_admitted', True),
                ('complete_freeze', 'rng_authorized', True),
                ('public_preread', 'native_case_reservations', False),
                ('public_preread', 'public_immutable_readback_verified', 1)):
            old = copy.deepcopy(self.materials['bundle'])
            self.materials['bundle'][location][key] = value
            self.refresh_embedded_digests()
            with self.subTest(location=location, key=key), self.assertRaises(ValueError):
                self.validate()
            self.materials['bundle'] = old; self.retain_changed_bundle()

    def test_unknown_proof_fields_or_nonimmutable_commit_ids_are_refused(self):
        self.materials['bundle']['public_preread']['hidden_authority'] = True
        self.refresh_embedded_digests()
        with self.assertRaisesRegex(ValueError, 'proof structure'):
            self.validate()
        del self.materials['bundle']['public_preread']['hidden_authority']
        self.materials['bundle']['public_preread']['preparation_commit'] = 'main'
        self.refresh_embedded_digests()
        with self.assertRaisesRegex(ValueError, 'immutable public preparation commit'):
            self.validate()

    def test_crosscase_source_domain_is_refused_despite_consistent_digest_refresh(self):
        self.materials['bundle']['plan']['cases'][0]['source_domain_hex'] = fixture.source_domain(1).hex()
        self.refresh_embedded_digests()
        with self.assertRaisesRegex(ValueError, 'fixed case source_domain_hex'):
            self.validate()

    def test_case_shape_and_original_limits_require_exact_integer_types(self):
        self.materials['bundle']['plan']['cases'][0]['real_legacy_tail_operations'] = True
        self.refresh_embedded_digests()
        with self.assertRaisesRegex(ValueError, 'engineering case allocation'):
            self.validate()
        self.materials['bundle']['plan']['cases'][0]['real_legacy_tail_operations'] = 1
        self.materials['bundle']['plan']['original_limits']['case_calls'] = 128
        self.refresh_embedded_digests()
        with self.assertRaisesRegex(ValueError, 'original fixed resource limits'):
            self.validate()

    def test_materialized_generator_or_code_tampering_is_detected(self):
        generator = self.materials['derived_root'] / 'prepare.py'
        generator.write_bytes(b'# changed unadmitted source\n')
        with self.assertRaisesRegex(ValueError, 'materialized source prepare.py'):
            self.validate()
        generator.write_bytes(b'# tiny synthetic inert preparation source\n')
        module = self.materials['code_root'] / admission.SELF
        module.write_bytes(module.read_bytes() + b'\n# changed current bytes\n')
        with self.assertRaisesRegex(ValueError, 'materialized source scripts/radio_native_v2_worker_admission.py'):
            self.validate()

    def test_missing_extra_cache_or_fifo_material_entries_are_refused(self):
        generator = self.materials['derived_root'] / 'prepare.py'; raw = generator.read_bytes()
        generator.unlink()
        with self.assertRaisesRegex(ValueError, 'derived inventory'):
            self.validate()
        generator.write_bytes(raw)
        cache = self.materials['code_root'] / 'injected.pyc'; cache.write_bytes(b'unfrozen cached code')
        with self.assertRaisesRegex(ValueError, 'code inventory'):
            self.validate()
        cache.unlink(); os.mkfifo(cache)
        with self.assertRaisesRegex(ValueError, 'alias or special file'):
            self.validate()

    def test_unpinned_empty_material_directory_is_refused(self):
        empty = self.materials['code_root'] / 'unfrozen-empty-module-path'
        empty.mkdir()
        with self.assertRaisesRegex(ValueError, 'code directory inventory'):
            self.validate()

    def test_existing_generator_outputs_refuse_scope_reuse_before_any_mutation(self):
        previous = self.materials['case_root'] / 'prepared.json'
        previous.write_bytes(b'{}')
        before = sorted(str(path) for path in self.root.rglob('*'))
        with self.assertRaisesRegex(ValueError, 'scope reuse refused'):
            self.validate()
        self.assertEqual(before, sorted(str(path) for path in self.root.rglob('*')))

    def test_symlink_hardlink_and_ancestor_aliases_are_refused(self):
        generator = self.materials['derived_root'] / 'prepare.py'; alternate = self.root / 'alternate-source'
        alternate.write_bytes(generator.read_bytes()); generator.unlink(); generator.symlink_to(alternate)
        with self.assertRaises(ValueError): self.validate()
        generator.unlink(); os.link(alternate, generator)
        with self.assertRaises(ValueError): self.validate()
        alias = self.root / 'case-alias'; alias.symlink_to(self.materials['case_root'], target_is_directory=True)
        with self.assertRaises(OSError):
            admission.load_bundle(str(alias / 'worker-admission.json'),
                expected_bundle_sha256=self.materials['bundle_sha256'])

    def test_bundle_fifo_is_rejected_without_blocking(self):
        path = self.materials['bundle_path']; path.unlink(); os.mkfifo(path)
        with self.assertRaisesRegex(ValueError, 'regular worker evidence'):
            self.validate()

    def test_original_freeze_omission_and_runtime_version_type_are_refused(self):
        del self.materials['bundle']['complete_freeze']['coverage']
        self.refresh_embedded_digests()
        with self.assertRaisesRegex(ValueError, 'complete original runner freeze structure'):
            self.validate()

    def test_canonical_path_aliases_are_refused_before_material_reads(self):
        for value in (str(self.materials['scope']) + '/.', str(self.root) + '//whole',
                      str(self.root) + '/other/../whole', 'relative/scope'):
            old = copy.deepcopy(self.materials['bundle'])
            self.materials['bundle']['execution_scope'] = value
            self.retain_changed_bundle()
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.validate()
            self.materials['bundle'] = old

    def test_check_only_cli_runs_under_isolated_python_and_creates_nothing(self):
        before = sorted(str(path) for path in self.root.rglob('*'))
        process = subprocess.run([PYTHON, '-I', '-S', '-B', str(SCRIPT), '--check-only',
            '--bundle', str(self.materials['bundle_path']), '--bundle-sha256', self.materials['bundle_sha256'],
            '--ordinal', '0'], capture_output=True, timeout=10, env=admission.CHILD_ENVIRONMENT)
        self.assertEqual(process.returncode, 0, process.stderr.decode())
        result = json.loads(process.stdout)
        self.assertFalse(result['publication_claim_independently_verified'])
        self.assertFalse(result['execution_authorized'])
        self.assertEqual(before, sorted(str(path) for path in self.root.rglob('*')))


if __name__ == '__main__':
    unittest.main()
