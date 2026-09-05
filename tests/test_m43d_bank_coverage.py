import unittest
import numpy as np
from m43d_bank_coverage import nested_banks, heldout_truths, candidate_pairs, bank_summary
from seti_repeater import search_v0p6 as core
from seti_repeater.truth_local_v0p6 import plan_truth_local_template_scores_interval


class DiskCoverageTests(unittest.TestCase):
    def test_nested_disk_banks_preserve_every_baseline_record(self):
        baseline=core.make_line_template_bank()
        banks=nested_banks(baseline)
        previous=baseline
        for bank in banks.values():
            self.assertEqual(bank[:len(previous)],previous)
            self.assertEqual([r['template_index'] for r in bank],list(range(len(bank))))
            points=[(r['coefficient_x'],r['coefficient_y']) for r in bank]
            self.assertEqual(len(points),len(set(points)))
            self.assertTrue(all(x*x+y*y<=1+1e-15 for x,y in points))
            previous=bank
        self.assertEqual([len(v) for v in banks.values()],[93,289,889,3301])

    def test_small_random_fixtures_match_exhaustive_cartesian_oracle(self):
        rng=np.random.default_rng(2301)
        for integration_count in (1,2,5):
            for _ in range(6):
                q=np.linspace(450.,550.,101)
                a=rng.uniform(.85,1.15,(7,integration_count))
                y=rng.uniform(490.,510.,integration_count)
                pairs,distances,_=candidate_pairs(q,a,y)
                dense=np.max(np.abs(a[:,None,:]*q[None,:,None]-y),axis=2)
                np.testing.assert_array_equal(pairs,np.argwhere(dense<=20))
                np.testing.assert_array_equal(distances,dense[dense<=20])

    def test_radio_frequency_inclusive_boundary_and_guard_do_not_relax_endpoint(self):
        y=np.array([1.4125e9])
        q=np.array([np.nextafter(y[0]-20,-np.inf), y[0]-20,
                    y[0],y[0]+20,np.nextafter(y[0]+20,np.inf)])
        pairs,distances,_=candidate_pairs(q,np.ones((1,1)),y)
        np.testing.assert_array_equal(pairs,[[0,1],[0,2],[0,3]])
        np.testing.assert_array_equal(distances,[20.,0.,20.])

    def test_common_carrier_and_every_integration_required(self):
        q=np.arange(400.,601.)
        a=np.ones((1,2))
        y=np.array([470.,530.])
        self.assertEqual(len(candidate_pairs(q,a,y)[0]),0)
        self.assertGreater(len(candidate_pairs(q,a,np.array([490.,510.]))[0]),0)

    def test_matches_existing_interval_planner_at_radio_frequency(self):
        grid=core.make_proxy_carrier_grid(1412.5,2.835503418452676,100,64)
        factors=np.array([[1.,1.],[1.00000001,1.00000002],[1.0000001,1.0000002]])
        truth=np.array([1.,1.000000003])
        plans=plan_truth_local_template_scores_interval(grid,factors,1.4125e9,truth)
        expected=np.array([(i,int(q)) for i,p in enumerate(plans) for q in p.candidate_indices.indices],dtype='<i8').reshape(-1,2)
        pairs,distances,_=candidate_pairs(grid.score_hz,factors,1.4125e9*truth)
        np.testing.assert_array_equal(pairs,expected)
        result=bank_summary(pairs,distances,2,grid)
        self.assertEqual(result['candidate_cells'],sum(len(p.candidate_indices.indices) for p in plans[:2]))
        self.assertLessEqual(result['witness']['max_distance_hz'],20)

    def test_heldout_generator_small_grid_is_unique_area_stratified_and_deterministic(self):
        grid=core.make_proxy_carrier_grid(.001,1.,1000,64)
        a=heldout_truths(grid)
        self.assertEqual(a,heldout_truths(grid))
        self.assertEqual(len({r['truth_id'] for r in a}),512)
        for row in a:
            radius2=row['coefficient_x']**2+row['coefficient_y']**2
            self.assertGreaterEqual(radius2,row['radial_stratum']/16-1e-15)
            self.assertLess(radius2,(row['radial_stratum']+1)/16+1e-15)
            self.assertGreaterEqual(row['proxy_carrier_hz'],grid.score_hz[256])
            self.assertLessEqual(row['proxy_carrier_hz'],grid.score_hz[-257])

    def test_invalid_factors_and_out_of_scope_numeric_domain_rejected(self):
        for value in (0.,float('nan'),2.):
            with self.assertRaises(ValueError):candidate_pairs(np.array([500.,501.]),np.array([[value]]),np.array([500.]))
        with self.assertRaises(ValueError):candidate_pairs(np.array([3e9,3e9+1]),np.ones((1,1)),np.array([3e9]))


if __name__=='__main__':unittest.main()
