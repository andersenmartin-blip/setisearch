"""Changed-scope regression tests; no astronomical powers are opened."""
from contextlib import ExitStack, redirect_stdout
from pathlib import Path
from unittest.mock import patch
import ast
import importlib.util
import io
import json
import math
import tempfile
import unittest

import numpy as np

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parent
SOURCE = HERE / 'partial_search.py'
spec = importlib.util.spec_from_file_location('bw_scope_review_subject', SOURCE)
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)


class BoundaryScopeTests(unittest.TestCase):
    def test_scope_gate_rejects_previous_and_outside_cores(self):
        function = next(node for node in ast.parse(SOURCE.read_text()).body
                        if isinstance(node, ast.FunctionDef) and node.name == 'validate_plan')
        # Execute only the family and q-domain gates, before any source/input I/O.
        function.body = function.body[:2]
        environment = {'require': subject.require, 'BATCHES': subject.BATCHES}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])),
                     '<scope-only-gates>', 'exec'), environment)
        validate = environment['validate_plan']
        family = 'SETI_BW_PARTIAL_HIP44295_LOCAL_Q_ESS_V1'
        self.assertEqual(subject.BATCHES, [[254]])
        validate({'schema': family, 'core_q_list': [254], 'batch_q_lists': [[254]]}, None)
        for qs, batches in [([253], [[253]]), ([255], [[255]]), ([0], [[0]]),
                            ([253, 254], [[253, 254]]), ([254], [[254], [254]])]:
            with self.subTest(qs=qs, batches=batches), self.assertRaises(ValueError):
                validate({'schema': family, 'core_q_list': qs, 'batch_q_lists': batches}, None)

    def test_full_halo_boundary_and_exact_header_guard(self):
        plan = json.loads((ROOT / 'work_bv/BV_PARTIAL_PLAN.json').read_text())
        self.assertEqual((254*4096-4096, 255*4096+4096), (1036288, 1048576))
        self.assertEqual(255*4096+4096, plan['native_channel_count'])
        span = (max(s['tref_midpoint_mjd'] for s in plan['scans'])
                - min(s['tref_midpoint_mjd'] for s in plan['scans'])) * 86400
        scope = plan['scans'][0]
        shift = math.ceil(4*(span + 7.5*scope['dt_seconds']) / abs(scope['df_hz'])) + 16
        radius = math.ceil(1 + .5*(8/838)*span / abs(scope['df_hz']))
        self.assertEqual(shift + radius, 2218)
        self.assertLess(shift + radius, 4096)
        self.assertLess(0*4096-4096, 0)
        self.assertGreater(256*4096+4096, plan['native_channel_count'])

    def test_numerical_and_missing_control_semantics_unchanged(self):
        def functions(path):
            return {n.name: ast.dump(n, include_attributes=False)
                    for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef)}
        previous = functions(ROOT / 'work_bv/partial_search.py')
        current = functions(SOURCE)
        for name in ('load_numerics', 'verify_header_content', 'classify_partial',
                     'associate_partial', 'scalar_sum'):
            self.assertEqual(previous[name], current[name], name)

    def test_only_q254_five_scan_batch_and_no_extra_batch(self):
        plan = {'scans': [{'scan': scan} for scan in range(5)]}
        records = [{'support_start': 1036288, 'normalized_support_path': 'synthetic-only'}
                   for _ in range(5)]
        calls = []
        def search(array, scope, plan, start, q):
            calls.append((q, scope['scan'], start))
            return {}, {}, {}, {'local_hits': 0, 'track_trials': 9020928}
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            output = Path(temporary) / 'output'
            for name, value in [('read', plan), ('validate_plan', plan), ('sha', 'synthetic'),
                                ('load_numerics', (None, None, {'search_scan': search})),
                                ('prepare_inputs', {'scans': records}), ('associate_partial', ({}, {}))]:
                stack.enter_context(patch.object(subject, name, return_value=value))
            stack.enter_context(patch.object(subject.np, 'load', return_value=np.zeros((16, 1))))
            stack.enter_context(patch.object(subject, 'save_npz', side_effect=lambda path, arrays:
                                            {'path': str(path), 'bytes': 0, 'sha256': 'synthetic'}))
            stack.enter_context(redirect_stdout(io.StringIO()))
            result = subject.run_batch(Path(temporary) / 'plan.json', output, 1)
            self.assertEqual(calls, [(254, scan, 1036288) for scan in range(5)])
            self.assertEqual(result['q_list'], [254])
            self.assertEqual(result['track_trials'], 45104640)
            self.assertFalse(result['complete_OFF_support'])
            self.assertEqual(result['full_cadence_candidate_assessment'], 'NOT_EVALUABLE_MISSING_OFF5')
            self.assertEqual(sorted(p.name for p in output.glob('q*')), ['q254'])
            for batch in (0, 2):
                with self.subTest(batch=batch), self.assertRaises(ValueError):
                    subject.run_batch(Path(temporary) / 'plan.json', Path(temporary) / 'unused', batch)


if __name__ == '__main__':
    unittest.main()
