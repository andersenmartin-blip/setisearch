import unittest
from m43_support_contract import fixtures, audit_case


class SupportContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.results={c[0]:audit_case(c) for c in fixtures()}

    def test_joint_support_cannot_swap_carrier_or_template(self):
        for name in ('incompatible_carriers','different_templates_by_epoch'):
            r=self.results[name]
            self.assertTrue(all(r['per_epoch_support_some_template_and_carrier']))
            self.assertEqual(r['candidate_cell_count'],0)
            self.assertTrue(r['exact_three_way_equivalence'])

    def test_inactive_epoch_removal_changes_contract(self):
        r=self.results['inactive_epoch_mismatch']
        self.assertEqual(r['candidate_cell_count'],0)
        self.assertGreater(r['first_two_epochs_only_cell_count_demonstration'],0)
        self.assertFalse(r['alternative_rule_adopted'])

    def test_continuous_intersection_is_not_discrete_support(self):
        r=self.results['between_grid_cells'];t=r['templates'][0]
        self.assertEqual(t['continuous_lower_hz'],t['continuous_upper_hz'])
        self.assertEqual(r['candidate_cell_count'],0)

    def test_inclusive_binary64_boundary(self):
        self.assertEqual(self.results['aligned']['candidate_cell_count'],41)
        self.assertEqual(self.results['just_below_20']['candidate_cell_count'],39)
        self.assertEqual(self.results['inclusive_zero_width']['candidate_cell_count'],1)
