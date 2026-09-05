"""Contract checks before synthetic policy evaluation."""
import copy
import itertools
import unittest
import numpy as np
from ls4k_off_policy_counterexamples import CLONES, configuration, specs, build, stage1_evidence, decisions

C=configuration()

class PolicyTests(unittest.TestCase):
    def test_exhaustive_gate_table_never_promotes_sky_candidates(self):
        for survives,passed,recovered in itertools.product((False,True),repeat=3):
            if recovered and not passed:continue
            r=decisions(survives,{'passed':passed,'recovered':recovered})
            self.assertEqual(r['current_gate_pass'],survives and passed)
            self.assertEqual(r['diagnostic_admission'],passed)
            self.assertEqual(r['off_vetoed_diagnostic_admission'],passed and not survives)
            self.assertEqual(r['current_truth_recovery'],survives and recovered)
            self.assertFalse(r['sky_candidate_promoted'])

    def test_exact_off_boundary_and_frequency_only_behavior(self):
        self.assertTrue(stage1_evidence('signal_clean',C)['survives_adjacent_off_veto'])
        self.assertFalse(stage1_evidence('signal_smooth_off',C)['survives_adjacent_off_veto'])
        c=copy.deepcopy(C)
        c['stipulated_off_event']['score']=6.
        c['stipulated_off_event']['time_start_s']=100.
        c['stipulated_off_event']['time_stop_s']=110.
        self.assertFalse(stage1_evidence('signal_smooth_off',c)['survives_adjacent_off_veto'])
        c['stipulated_off_event']['score']=5.999
        self.assertTrue(stage1_evidence('signal_smooth_off',c)['survives_adjacent_off_veto'])

    def test_clones_are_exactly_identical_in_waveforms_truth_and_gate(self):
        base=np.random.default_rng(99).normal(100,1,(2,C['sample_count']))
        for clone,original in CLONES.items():
            spec={'family':clone,'width_s':.012,'amplitude_sigma':8.}
            a,ta=build(base,C['pulse_times_s'],spec,C)
            b,tb=build(base,C['pulse_times_s'],{**spec,'family':original},C)
            np.testing.assert_array_equal(a,b);self.assertEqual(ta,tb)
            self.assertEqual(stage1_evidence(clone,C),stage1_evidence(original,C))

    def test_control_interventions_are_at_independent_correct_locations(self):
        base=np.zeros((2,C['sample_count']))
        spec={'family':'signal_smooth_off','width_s':.012,'amplitude_sigma':8.}
        pair,_=build(base,C['pulse_times_s'],spec,C)
        off,_=build(base,C['pulse_times_s'],{**spec,'family':'signal_pulsed_off'},C)
        reference,_=build(base,C['pulse_times_s'],{**spec,'family':'signal_reference_pulse'},C)
        np.testing.assert_array_equal(off[0],pair[0]);np.testing.assert_array_equal(reference[1],pair[1])
        for difference,expected in ((off[1]-pair[1],C['control_time_s']),(reference[0]-pair[0],C['reference_time_s'])):
            indices=np.flatnonzero(difference)
            self.assertEqual(len(indices),12)
            self.assertAlmostEqual(float(((indices+.5)*C['sample_time_s']).mean()),expected)
            np.testing.assert_allclose(difference[indices],C['control_amplitude_sigma'])
        self.assertTrue(np.all(base==0))

    def test_null_and_single_pulse_have_no_train_truth(self):
        base=np.zeros((2,C['sample_count']))
        for family,count in (('null_smooth_off',0),('isolated_on_smooth_off',1)):
            _,truth=build(base,C['pulse_times_s'],{'family':family,'width_s':.012,'amplitude_sigma':8.},C)
            self.assertEqual(len(truth),count)

    def test_unique_complete_specification_and_no_spectral_access(self):
        rows=list(specs(C))
        self.assertEqual(len(rows)*len(C['seeds']),1152)
        self.assertEqual(len({tuple(sorted(r.items())) for r in rows}),len(rows))
        self.assertEqual(len(C['seeds']),len(set(C['seeds'])))
        self.assertFalse(C['raw_spectral_access'])
        self.assertFalse(C['physical_transfer_simulated'])

if __name__=='__main__':unittest.main()
