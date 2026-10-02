"""Exact activation parent environment tests; no protected execution."""
import copy
import hashlib
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT/'scripts/radio_native_v2_activation_environment.py'
SPEC = importlib.util.spec_from_file_location('activation_environment', SCRIPT)
contract = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(contract)


class ActivationEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.python = {'path': '/opt/frozen/python/bin/python', 'sha256': '1'*64}
        self.node = {'path': '/opt/frozen/node/bin/node', 'sha256': '2'*64}
        self.git = {'resolved': '/usr/bin/git', 'sha256': '3'*64}
        self.plan = {'schema': contract.PLAN_SCHEMA, 'execution_status': 'BLOCKED_PREPARATION_REVIEW',
            'execution_authorized': False, 'reservation_authorized': False,
            'scientific_execution_authorized': False,
            'runtime_executables': {'python': self.python, 'node': self.node}}
        self.freeze = {'schema': contract.FREEZE_SCHEMA, 'mode': 'PROSPECTIVE_ENGINEERING_ONLY',
            'executables': {'python': {'resolved': self.python['path'], 'sha256': '1'*64},
                'node': {'resolved': self.node['path'], 'sha256': '2'*64}, 'git': self.git}}

    def test_exact_secret_free_environment_passes_and_stays_blocked(self):
        expected = contract.expected_environment(self.plan, self.freeze)
        result = contract.validate(self.plan, self.freeze, expected)
        self.assertTrue(result['complete_parent_environment_frozen'])
        self.assertFalse(result['secret_bearing_ambient_environment_inherited'])
        self.assertFalse(result['activation_guard_complete'])
        self.assertEqual(result['environment_sha256'], hashlib.sha256(contract.canonical(expected)).hexdigest())
        self.assertNotIn('PYTHONPATH', expected)
        self.assertNotIn('LD_PRELOAD', expected)

    def test_missing_extra_or_changed_environment_is_refused(self):
        expected = contract.expected_environment(self.plan, self.freeze)
        variants = [dict(expected), dict(expected), dict(expected)]
        del variants[0]['LANG']; variants[1]['TOKEN'] = 'ambient'; variants[2]['PATH'] += ':/tmp'
        for actual in variants:
            with self.subTest(actual=actual), self.assertRaisesRegex(ValueError, 'environment differs'):
                contract.validate(self.plan, self.freeze, actual)

    def test_runtime_path_drift_and_authority_are_refused(self):
        freeze = copy.deepcopy(self.freeze); freeze['executables']['node']['resolved'] = '/other/node'
        with self.assertRaisesRegex(ValueError, 'paths differ'):
            contract.expected_environment(self.plan, freeze)
        plan = copy.deepcopy(self.plan); plan['execution_authorized'] = True
        with self.assertRaisesRegex(ValueError, 'authorized plan'):
            contract.expected_environment(plan, self.freeze)

    def test_noncanonical_or_unpinned_executable_is_refused(self):
        for value in ('relative/python', '/opt/../python', '/opt/python'):
            plan = copy.deepcopy(self.plan); plan['runtime_executables']['python']['path'] = value
            if value == '/opt/python': del plan['runtime_executables']['python']['sha256']
            with self.subTest(value=value), self.assertRaises(ValueError):
                contract.expected_environment(plan, self.freeze)


if __name__ == '__main__': unittest.main()
