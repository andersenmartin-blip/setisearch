"""Tiny source guard and spending integration checks; no maximum recipe runs.

The positive metadata-delivery path authenticates a real local bundle and
private synthetic spending witness in a held material fixture. Its process
context and downstream readiness are explicitly mocked. The unmodified cold
prefix separately refuses synthetic roots in an actual isolated interpreter.
Public readback, original-root admission and science remain unqualified.
"""
import copy
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import radio_native_v2_compact_eight_case_resource_fixture as fixture
import radio_native_v2_worker_admission as admission
from tests.test_radio_native_v2_worker_admission import synthetic_worker_materials

ROOT = Path(__file__).resolve().parents[1]
PREFIX_SUCCESS = b'AUTHENTICATED_SYNTHETIC_GUARD_ONLY\n'


def tiny_guard_materials(directory, *, ordinal=0):
    # This file contains no source generator, archive construction, RNG or
    # telescope access. The production prefix is copied without bypass hooks.
    source = ('import os,sys,json,hashlib\nfrom pathlib import Path\n'
        + fixture.source_worker_guard(ROOT)
        + '\nsys.stdout.write("AUTHENTICATED_SYNTHETIC_GUARD_ONLY\\n")\n').encode()
    derived = {'prepare.py': source,
        'fresh-caller.js': b'// tiny inert caller; never executed\n',
        'lossless-helper.js': b'// tiny inert helper; never executed\n'}
    return synthetic_worker_materials(directory, ordinal=ordinal,
        plan=fixture.build_plan(ROOT), derived_sources=derived)


def repin_bundle(material):
    raw = admission.canonical(material['bundle'])+b'\n'
    material['bundle_path'].write_bytes(raw)
    material['bundle_sha256'] = hashlib.sha256(raw).hexdigest()
    # The path/layout remain fixed. Altered evidence must be refused at actual
    # launch, so do not ask the validating argv builder to accept bad evidence.
    material['argv'][-1] = material['bundle_sha256']


def run_guard(material, argv=None):
    return subprocess.run(material['argv'] if argv is None else argv,
        capture_output=True, env=fixture.CHILD_ENVIRONMENT, timeout=10)


def scope_inventory(material):
    root = material['case_root']
    return sorted(str(path.relative_to(root)) for path in root.rglob('*'))


class AuthenticatedSourceReceiptTests(unittest.TestCase):
    def assert_no_source_outputs(self, material):
        for name in ('preparation-identity.json', 'deterministic-source.bin',
                'prepared.json', 'store', 'caller-result.json'):
            self.assertFalse((material['case_root']/name).exists(), name)

    def assert_guard_closed(self, material, *, expected=None, argv=None):
        before = scope_inventory(material)
        process = run_guard(material, argv)
        self.assertNotEqual(process.returncode, 0)
        self.assertEqual(process.stdout, b'')
        if expected is not None:
            self.assertIn(expected.lower(), process.stderr.lower())
        self.assertEqual(scope_inventory(material), before)
        self.assert_no_source_outputs(material)
        return process

    def test_exact_pinned_bundle_delivers_receipt_scope_and_durable_witness_to_guard(self):
        for ordinal in (0, 7):
            with self.subTest(ordinal=ordinal), tempfile.TemporaryDirectory() as directory:
                material = tiny_guard_materials(directory, ordinal=ordinal)
                before = scope_inventory(material)
                held=fixture.pinned_component(material['code_root'],fixture.SELF,
                    {fixture.SELF:material['plan']['code_files'][fixture.SELF]})
                ready=mock.Mock(return_value=True)
                # Only metadata delivery is tested positively. These asserted
                # context flags do not claim a real isolated worker or satisfy
                # the independently fixed original-root historical gate.
                flags=SimpleNamespace(**{name:getattr(sys.flags,name) for name in dir(sys.flags)
                    if name.isidentifier() and not name.startswith('_')})
                flags.isolated=flags.no_site=flags.dont_write_bytecode=1
                with mock.patch.dict(held,{'require_execution_ready':ready}), \
                        mock.patch.object(sys,'flags',flags), \
                        mock.patch.object(sys,'orig_argv',material['argv']), \
                        mock.patch.dict(os.environ,fixture.CHILD_ENVIRONMENT,clear=True):
                    received=held['source_worker_admission'](material['bundle_path'],
                        material['bundle_sha256'],ordinal=ordinal,argv=list(sys.orig_argv),
                        environment=dict(os.environ))
                self.assertEqual(received,material['bundle'])
                ready.assert_called_once_with(material['activation_receipt'],material['plan'],
                    material['freeze'],material['proof'],execution_scope=str(material['scope']),
                    invocation_spending=material['invocation_spending'],
                    repository_root=material['bundle']['invocation_repository_root'])
                self.assertEqual(scope_inventory(material), before)
                self.assert_no_source_outputs(material)
                self.assertFalse(material['plan']['execution_authorized'])
                self.assertFalse(material['plan']['complete_resource_measurement_join_qualified'])

    def test_unmodified_cold_prefix_refuses_synthetic_root_before_source_outputs(self):
        for ordinal in (0,7):
            with self.subTest(ordinal=ordinal), tempfile.TemporaryDirectory() as directory:
                material=tiny_guard_materials(directory,ordinal=ordinal)
                self.assert_guard_closed(material,expected=b'original historical repository root')

    def test_structurally_valid_receipt_dict_without_witness_cannot_admit(self):
        with tempfile.TemporaryDirectory() as directory:
            material = tiny_guard_materials(directory)
            # Isolate the missing-witness edge from the stricter independent
            # original-root check; the cold-prefix check below remains real.
            with mock.patch.object(fixture,'_checked_activation_receipt',return_value=True), \
                    self.assertRaisesRegex(RuntimeError, 'spending witness absent'):
                fixture.require_execution_ready(material['activation_receipt'],material['plan'],
                    material['freeze'],material['proof'],execution_scope=str(material['scope']))
            material['bundle']['invocation_spending'] = None
            material['bundle']['invocation_spending_sha256'] = hashlib.sha256(admission.canonical(None)).hexdigest()
            repin_bundle(material)
            self.assert_guard_closed(material, expected=b'spend')

    def test_mutation_and_self_asserted_receipt_hash_do_not_replace_retained_bundle_digest(self):
        with tempfile.TemporaryDirectory() as directory:
            material = tiny_guard_materials(directory)
            original_digest = material['bundle_sha256']
            material['bundle']['activation_receipt']['activation_commit'] = '6'*40
            material['bundle']['activation_receipt_sha256'] = hashlib.sha256(
                admission.canonical(material['bundle']['activation_receipt'])).hexdigest()
            repin_bundle(material)
            argv = list(material['argv']); argv[-1] = original_digest
            self.assert_guard_closed(material, expected=b'independently retained digest', argv=argv)

    def test_repinning_changed_receipt_does_not_reauthenticate_durable_spend(self):
        with tempfile.TemporaryDirectory() as directory:
            material = tiny_guard_materials(directory)
            material['bundle']['activation_receipt']['activation_commit'] = '6'*40
            material['bundle']['activation_receipt_sha256'] = hashlib.sha256(
                admission.canonical(material['bundle']['activation_receipt'])).hexdigest()
            repin_bundle(material)
            self.assert_guard_closed(material, expected=b'spend')

    def test_missing_or_replaced_spend_record_is_refused_before_identity(self):
        for alteration in ('missing', 'same-bytes-new-inode', 'changed-bytes'):
            with self.subTest(alteration=alteration), tempfile.TemporaryDirectory() as directory:
                material = tiny_guard_materials(directory)
                witness = material['bundle']['invocation_spending']
                record = Path(witness['ledger_root'])/witness['record_name']
                raw = record.read_bytes()
                if alteration == 'missing': record.unlink()
                elif alteration == 'same-bytes-new-inode':
                    replacement = record.with_name('replacement.json')
                    replacement.write_bytes(raw); replacement.chmod(0o600)
                    os.replace(replacement, record)
                else:
                    record.write_bytes(raw.replace(b'SPENT_BEFORE_WORKLOAD', b'WRONG_BEFORE_WORKLOAD'))
                self.assert_guard_closed(material)

    def test_duplicate_or_noncanonical_bundle_json_is_refused_even_if_rehashed(self):
        for alteration in ('duplicate', 'noncanonical'):
            with self.subTest(alteration=alteration), tempfile.TemporaryDirectory() as directory:
                material = tiny_guard_materials(directory)
                raw = material['bundle_path'].read_bytes()
                if alteration == 'duplicate': raw = b'{"schema":"forged",'+raw[1:]
                else: raw = b' '+raw
                material['bundle_path'].write_bytes(raw)
                material['argv'][-1] = hashlib.sha256(raw).hexdigest()
                self.assert_guard_closed(material, expected=b'canonical' if alteration == 'noncanonical' else b'duplicate')

    def test_alternative_bundle_path_is_not_an_equivalent_admission(self):
        with tempfile.TemporaryDirectory() as directory:
            material = tiny_guard_materials(directory)
            alias = material['case_root']/'unreviewed-alternate-bundle.json'
            alias.write_bytes(material['bundle_path'].read_bytes())
            argv = list(material['argv']); argv[-2] = str(alias)
            self.assert_guard_closed(material, argv=argv)

    def test_bundle_hardlink_or_symlink_is_refused_without_source_write(self):
        for alteration in ('hardlink', 'symlink'):
            with self.subTest(alteration=alteration), tempfile.TemporaryDirectory() as directory:
                material = tiny_guard_materials(directory)
                path = material['bundle_path']; other = path.with_name('aliased-bundle.json')
                if alteration == 'hardlink': os.link(path, other)
                else:
                    path.rename(other); path.symlink_to(other)
                self.assert_guard_closed(material)

    def test_source_fixture_cannot_be_replaced_by_self_selected_code(self):
        with tempfile.TemporaryDirectory() as directory:
            material = tiny_guard_materials(directory)
            marker = Path(directory)/'unchecked-source-executed'
            path = material['code_root']/fixture.SELF
            path.write_text('from pathlib import Path\nPath('+repr(str(marker))+').write_text("bad")\n')
            self.assert_guard_closed(material, expected=b'admission implementation')
            self.assertFalse(marker.exists())

    def test_actual_argv_ordinal_scope_and_isolation_remain_bound(self):
        for alteration in ('ordinal', 'scope', 'isolation', 'extra-python-option'):
            with self.subTest(alteration=alteration), tempfile.TemporaryDirectory() as directory:
                material = tiny_guard_materials(directory)
                argv = list(material['argv'])
                if alteration == 'ordinal': argv[-4] = '1'
                elif alteration == 'scope': argv[-7] = str(material['scope'])
                elif alteration == 'isolation': argv.remove('-I')
                else: argv[1:1] = ['-X', 'utf8']
                self.assert_guard_closed(material, argv=argv)


class InvocationSpendingRunnerIntegrationTests(unittest.TestCase):
    def test_spend_precedes_scope_creation_and_survives_later_gate_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            material = tiny_guard_materials(directory)
            # Use a fresh private ledger for this runner-order test; the helper
            # already spent its separate synthetic guard activation.
            private=Path(directory)/'runner-private-repository'; private.mkdir()
            spender = fixture.invocation_spending_module()
            ledger = Path(spender['ledger_root_for_repository'](str(private))); ledger.mkdir(mode=0o700)
            scope = private/'runner-never-created'
            source=private/fixture.CODE_FILES[0]; source.parent.mkdir(parents=True)
            source.write_bytes((ROOT/fixture.CODE_FILES[0]).read_bytes())
            receipt = copy.deepcopy(material['activation_receipt'])
            receipt['control_scope'] = str(scope)
            plan = copy.deepcopy(material['plan'])
            plan.update(invocation_repository_root=str(private),invocation_ledger_root=str(ledger))
            events = []
            real_consume = spender['consume_once']
            def root_contract(value,*args,repository_root,execution_scope,**kwargs):
                self.assertEqual(repository_root,str(private))
                self.assertEqual(value['invocation_repository_root'],str(private))
                self.assertEqual(value['invocation_ledger_root'],str(ledger))
                self.assertEqual(execution_scope,str(scope))
                return str(private)
            def historical(code_root,**kwargs):
                self.assertEqual(code_root,str(private))
                self.assertEqual(kwargs['repository_root'],str(private))
                self.assertFalse(scope.exists()); events.append('synthetic-historical-hook')
            def consume(value, **kwargs):
                self.assertFalse(scope.exists())
                self.assertEqual(kwargs['repository_root'],str(private))
                self.assertEqual(kwargs['ledger_root'],str(ledger))
                events.append('spend')
                return real_consume(value, **kwargs)
            def require(*args, **kwargs):
                self.assertFalse(scope.exists())
                self.assertEqual(events, ['synthetic-historical-hook','spend'])
                self.assertTrue(kwargs['invocation_spending']['durable_before_workload'])
                self.assertEqual(kwargs['repository_root'],str(private))
                events.append('later-refusal')
                raise RuntimeError('synthetic refusal after durable spending')
            # These explicit synthetic trust-edge hooks isolate runner ordering;
            # they never establish original-root historical/control admission.
            with mock.patch.object(fixture,'REPO',private), \
                    mock.patch.object(fixture,'authenticated_repository_root',side_effect=root_contract), \
                    mock.patch.object(fixture,'historical_observation_module',return_value={'observe_historical_storage':historical}), \
                    mock.patch.object(fixture, '_checked_activation_receipt', return_value=True), \
                    mock.patch.object(fixture, 'validate_activation', return_value={}), \
                    mock.patch.object(fixture, 'templates', return_value={'lossless-helper.js':b'tiny-helper'}), \
                    mock.patch.object(fixture, 'invocation_spending_module', return_value={**spender,'consume_once':consume}), \
                    mock.patch.object(fixture, 'require_execution_ready', side_effect=require), \
                    mock.patch.object(fixture.subprocess, 'Popen') as launch:
                with self.assertRaisesRegex(RuntimeError, 'after durable spending'):
                    fixture.run_control(scope, plan, material['proof'], material['freeze'],
                        receipt, b'tiny-helper')
                launch.assert_not_called()
            self.assertEqual(events, ['synthetic-historical-hook','spend', 'later-refusal'])
            self.assertFalse(scope.exists())
            self.assertEqual(len(list(ledger.iterdir())), 1)
            with self.assertRaisesRegex(ValueError, 'already spent'):
                real_consume(receipt, execution_scope=str(scope), ledger_root=str(ledger),
                    repository_root=str(private),receipt_validator=lambda value: True)

    def test_bad_helper_or_reused_scope_refuses_before_consumption(self):
        for failure in ('helper', 'scope'):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                scope = Path(directory)/'scope'
                if failure == 'scope': scope.mkdir(mode=0o700)
                with mock.patch.object(fixture,'authenticated_repository_root',return_value=directory), \
                        mock.patch.object(fixture, '_checked_activation_receipt', return_value=True), \
                        mock.patch.object(fixture, 'validate_activation', return_value={}), \
                        mock.patch.object(fixture, 'templates', return_value={'lossless-helper.js':b'tiny-helper'}), \
                        mock.patch.object(fixture, 'invocation_spending_module') as spend, \
                        mock.patch.object(fixture.subprocess, 'Popen') as launch:
                    expected='Fresh exclusive' if failure=='scope' else 'Exact prospectively pinned lossless helper'
                    with self.assertRaisesRegex((ValueError, RuntimeError),expected):
                        fixture.run_control(scope, {}, {}, {}, {}, b'wrong-helper')
                    spend.assert_not_called(); launch.assert_not_called()
                self.assertEqual(scope.exists(), failure == 'scope')


if __name__ == '__main__':
    unittest.main()
