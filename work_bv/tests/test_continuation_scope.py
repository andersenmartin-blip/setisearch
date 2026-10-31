"""Artificial-only continuation boundaries; no astronomical input access."""
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
import ast
import importlib.util
import io
import tempfile
import unittest
import numpy as np

SOURCE = Path(__file__).resolve().parents[1]/'partial_search.py'
spec = importlib.util.spec_from_file_location('bv_scope_test_subject',SOURCE)
subject = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subject)


class ContinuationScopeTests(unittest.TestCase):
    def test_fixed_remaining_coverage_and_variable_last_batch(self):
        self.assertEqual(len(subject.BATCHES),28)
        self.assertEqual(subject.BATCHES[0],list(range(33,41)))
        self.assertEqual(subject.BATCHES[-1],list(range(249,254)))
        self.assertEqual([q for batch in subject.BATCHES for q in batch],list(range(33,254)))
        self.assertEqual(subject.SCOPE_NUMERICS['track_combinations_total'],221*5*9020928)
        self.assertEqual(subject.SCOPE_NUMERICS['track_combinations_final_batch'],5*5*9020928)
        self.assertEqual(subject.SCOPE_NUMERICS['selected_independent_scalar_checks_final_batch'],5*180)
        self.assertEqual(subject.SCOPE_NUMERICS['shared_kernel_calibration_vector_replays_final_batch'],5*60)
        self.assertEqual(subject.SCOPE_NUMERICS['selected_carrier_channels'],221*4096)
        self.assertEqual(subject.SCOPE_NUMERICS['technical_channel_bin_width_hz'],221*4096*2.7939677238464355)

    def test_unmodified_numerical_and_partial_semantics(self):
        predecessor=SOURCE.parents[1]/'work_bu/partial_search.py'
        old={n.name:n for n in ast.parse(predecessor.read_text()).body if isinstance(n,ast.FunctionDef)}
        new={n.name:n for n in ast.parse(SOURCE.read_text()).body if isinstance(n,ast.FunctionDef)}
        for name in ('load_numerics','verify_header_content','classify_partial','associate_partial','scalar_sum'):
            self.assertEqual(ast.dump(old[name],include_attributes=False),ast.dump(new[name],include_attributes=False),name)

    def exercise_batch(self,number,expected_qs):
        plan={'scans':[{'scan':i} for i in range(5)]}
        records=[{'support_start':0,'normalized_support_path':'synthetic-only'} for _ in range(5)]
        called=[]
        def search(y,scope,plan,start,q):
            called.append((q,scope['scan']))
            return {},{},{},{'local_hits':0,'track_trials':9020928}
        with tempfile.TemporaryDirectory() as temporary:
            out=Path(temporary)/'new_output'
            with patch.object(subject,'read',return_value=plan), \
                 patch.object(subject,'validate_plan',return_value=plan), \
                 patch.object(subject,'sha',return_value='artificial-plan'), \
                 patch.object(subject,'load_numerics',return_value=(None,None,{'search_scan':search})), \
                 patch.object(subject,'prepare_inputs',return_value={'scans':records}), \
                 patch.object(subject.np,'load',return_value=np.zeros((16,1),dtype=np.float32)), \
                 patch.object(subject,'save_npz',side_effect=lambda path,arrays:{'path':str(path),'bytes':0,'sha256':'artificial'}), \
                 patch.object(subject,'associate_partial',return_value=({},{})), \
                 redirect_stdout(io.StringIO()):
                result=subject.run_batch(Path(temporary)/'plan.json',out,number)
            self.assertEqual(result['schema'],'SETI_BV_PARTIAL_BATCH_V1')
            self.assertEqual(result['q_list'],expected_qs)
            self.assertEqual(called,[(q,i) for q in expected_qs for i in range(5)])
            self.assertEqual(result['track_trials'],len(expected_qs)*45104640)
            self.assertFalse(result['complete_OFF_support'])
            self.assertEqual(result['full_cadence_candidate_assessment'],'NOT_EVALUABLE_MISSING_OFF5')
            self.assertEqual(sorted(p.name for p in out.glob('q*')),['q%03d'%q for q in expected_qs])

    def test_first_batch_runs_only_q33_to_q40(self):
        self.exercise_batch(1,list(range(33,41)))

    def test_final_short_batch_runs_only_q249_to_q253(self):
        self.exercise_batch(28,list(range(249,254)))


if __name__=='__main__':
    unittest.main()
