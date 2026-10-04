import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import fixture_scope as fixture
import runner_v2 as runner


class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='radio-receiver-v2-test-')
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, **kw):
        return fixture.build(self.root, identity='disjoint-v2-unit-fixture', **kw)

    def repin_scope(self, args, mutate):
        raw, _, _, claim = args
        doc = json.loads(raw); mutate(doc)
        new = runner.canonical(doc)
        path = self.root/'changed-scope.json'
        fixture.write_new(path, new)
        return new, runner.pin(new), str(path), claim

    def test_actual_isolated_child_validates_complete_packet_and_96_tiny_rows(self):
        result = fixture.run(self.build()).record()
        self.assertEqual(result['status'], 'SYNTHETIC_PROCESS_QUALIFIED', result['error'])
        child = result['child_result']
        self.assertEqual(child['loader_calls'], list(runner.LABELS))
        self.assertEqual(child['normalized_row_bytes'], 1536)
        self.assertEqual(len(child['receiver_result']['per_load_live_clock'][
            'nondecreasing_integer_observations']), 12)
        self.assertFalse(result['scientific_execution_authorized'])
        self.assertFalse(result['telescope_values_opened'])
        self.assertFalse(result['actual_atomic_cas_qualified'])

    def test_duplicate_identity_refused_even_with_different_scope_file(self):
        args = self.build()
        self.assertEqual(fixture.run(args).record()['status'], 'SYNTHETIC_PROCESS_QUALIFIED')
        changed = self.repin_scope(args, lambda doc: doc.update(stderr_cap_bytes=60000))
        with self.assertRaises(FileExistsError):
            fixture.run(changed)

    def test_crash_spend_refuses_dispatch_without_child(self):
        args = self.build(); doc = json.loads(args[0])
        runner.reserve(doc, args[3], args[1])
        with self.assertRaises(FileExistsError):
            fixture.run(args)
        self.assertFalse((Path(args[3]['path'])/doc['dispatch_identity']/'capture').exists())

    def test_concurrent_claim_has_exactly_one_winner(self):
        from concurrent.futures import ThreadPoolExecutor
        args = self.build(); doc = json.loads(args[0])
        def claim():
            try:
                runner.reserve(doc, args[3], args[1])
                return 'claimed'
            except FileExistsError:
                return 'refused'
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda _: claim(), range(2)))
        self.assertEqual(sorted(outcomes), ['claimed', 'refused'])

    def test_loaded_maintained_code_is_not_a_caller_boolean(self):
        args = self.build()
        changed = self.repin_scope(args, lambda d: d['modules']['scientific_admission'].update(sha256='f'*64))
        result = fixture.run(changed).record()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertIsNone(result['capture_sha256'])
        self.assertTrue(result['claim_permanently_spent'])

    def test_synthetic_loader_exception_retains_binary_root_cause_and_traceback(self):
        result = fixture.run(self.build(fault='raise-first'))
        record = result.record(); capture = json.loads(result.capture_payload)
        self.assertEqual(record['status'], 'CLOSED_FAILED')
        self.assertEqual(record['capture_process_status'], 'EXIT_NONZERO')
        retention = sys.modules['failure_output_retention']
        raw = retention.reconstruct_raw(capture['streams']['stderr']['reconstruction'])
        self.assertIn(b'controlled-synthetic-root-cause\x00\xff\n', raw)
        self.assertIn(b'RuntimeError: deliberate synthetic loader failure', raw)

    def test_hung_receiver_callback_is_killed_and_claim_stays_spent(self):
        args = self.build(fault='hang-first', timeout=1)
        result = fixture.run(args)
        self.assertEqual(result.record()['status'], 'CLOSED_FAILED')
        self.assertEqual(result.record()['capture_process_status'], 'TIMEOUT')
        capture = json.loads(result.capture_payload)
        self.assertTrue(capture['child_reaped'])
        self.assertIn(b'synthetic loader entered', sys.modules['failure_output_retention'].reconstruct_raw(
            capture['streams']['stderr']['reconstruction']))
        with self.assertRaises(FileExistsError):
            fixture.run(args)

    def test_cap_breach_cannot_pass_with_child_zero_exit(self):
        result = fixture.run(self.build(stdout_cap=64)).record()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertEqual(result['capture_process_status'], 'OUTPUT_LIMIT')

    def test_complete_synthetic_evidence_cannot_be_relabelled_as_public(self):
        args = self.build()
        changed = self.repin_scope(args, lambda d: d.update(domain='public-scientific-evidence'))
        with self.assertRaisesRegex(runner.Refused, 'actual public'):
            fixture.run(changed)
        self.assertEqual(list(Path(args[3]['path']).iterdir()), [])

    def test_proof_mutation_is_refused_before_launch(self):
        packet = fixture.fixture_packet()
        packet['metadata']['raw_proof'] += b' '
        result = fixture.run(self.build(packet=packet)).record()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertIsNone(result['capture_sha256'])

    def test_failed_scientific_fixture_gate_is_refused_without_tuning(self):
        packet = fixture.fixture_packet()
        # Alter original bytes while preserving the independently expected pin.
        packet['metadata']['raw_documents']['scientific_result'] += b' '
        result = fixture.run(self.build(packet=packet)).record()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertIsNone(result['child_result'])

    def test_tiny_row_mutation_is_refused_before_launch(self):
        packet = fixture.fixture_packet()
        packet['rows']['epoch1_on'][0] = b'\0'*16
        result = fixture.run(self.build(packet=packet)).record()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertIn('fixture row differs', result['error'])

    def test_row_payload_geometry_cannot_be_promoted_to_telescope(self):
        packet = fixture.fixture_packet()
        row = b'\0'*(65536*4)
        packet['rows']['epoch1_on'][0] = row
        packet['row_pins']['epoch1_on'][0] = runner.pin(row)
        result = fixture.run(self.build(packet=packet)).record()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertIn('tiny geometry', result['error'])

    def test_empty_clock_cannot_be_accepted(self):
        args = self.build(); good = fixture.run(args).record()['child_result']
        doc = json.loads(args[0]); modules = runner.load_modules(doc)
        packet, admission, _ = runner.admitted_fixture(doc, modules)
        good['receiver_result']['per_load_live_clock']['nondecreasing_integer_observations'] = []
        with self.assertRaisesRegex(runner.Refused, 'twelve'):
            runner.verify_child(runner.canonical(good), doc, packet, admission)

    def test_regressed_missing_reordered_boolean_expired_clock_observations_refused(self):
        args = self.build(); good = fixture.run(args).record()['child_result']
        doc = json.loads(args[0]); modules = runner.load_modules(doc)
        packet, admission, _ = runner.admitted_fixture(doc, modules)
        mutations = [
            lambda obs: obs.pop(),
            lambda obs: obs.reverse(),
            lambda obs: obs[1].update(epoch_milliseconds=1999),
            lambda obs: obs[1].update(epoch_milliseconds=True),
            lambda obs: obs[1].update(epoch_milliseconds=1201000)]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                candidate = copy.deepcopy(good)
                mutate(candidate['receiver_result']['per_load_live_clock']['nondecreasing_integer_observations'])
                with self.assertRaises(runner.Refused):
                    runner.verify_child(runner.canonical(candidate), doc, packet, admission)

    def test_post_capture_file_error_returns_capture_and_terminal(self):
        args = self.build()
        original = runner.read_checked
        calls = 0
        def read(expected, **kwargs):
            nonlocal calls
            if expected == json.loads(args[0])['child']:
                calls += 1
                if calls == 2:
                    raise OSError('injected post-child identity change')
            return original(expected, **kwargs)
        with patch.object(runner, 'read_checked', side_effect=read):
            result = fixture.run(args)
        self.assertEqual(result.record()['status'], 'CLOSED_FAILED')
        self.assertIsNotNone(result.capture_payload)
        self.assertIn('post-child', result.record()['error'])
        self.assertTrue((Path(result.record()['claim_path'])/'terminal.json').exists())

    def test_identity_registry_rerouting_is_refused(self):
        args = self.build()
        changed = self.repin_scope(args, lambda doc: doc['claim_root'].update(inode=0))
        with self.assertRaisesRegex(runner.Refused, 'claim-root'):
            fixture.run(changed)

    def test_child_argv_cannot_be_injected_into_scope(self):
        args = self.build()
        changed = self.repin_scope(args, lambda d: d.update(argv=[sys.executable, '-c', 'print(1)']))
        with self.assertRaisesRegex(runner.Refused, 'exact receiver dispatch'):
            fixture.run(changed)

    def test_unrelated_parent_environment_does_not_enter_child(self):
        args = self.build()
        with patch.dict(os.environ, {'PYTHONPATH': '/no-import-here', 'PYTHONHOME': '/not-python'}):
            self.assertEqual(fixture.run(args).record()['status'], 'SYNTHETIC_PROCESS_QUALIFIED')

    def test_symlink_packet_ancestor_is_refused(self):
        args = self.build(); link = self.root/'alias'
        link.symlink_to(self.root, target_is_directory=True)
        changed = self.repin_scope(args, lambda d: d['packet'].update(path=str(link/'packet.json')))
        result = fixture.run(changed).record()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertIsNone(result['capture_sha256'])

    def test_scope_raw_hash_repin_cannot_change_source_module_bytes(self):
        args = self.build()
        changed = self.repin_scope(args, lambda d: d['modules']['receiver_telescope_adapter'].update(bytes=1))
        result = fixture.run(changed).record()
        self.assertEqual(result['status'], 'CLOSED_FAILED')
        self.assertIsNone(result['capture_sha256'])


if __name__ == '__main__':
    unittest.main()
