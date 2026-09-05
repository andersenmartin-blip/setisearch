import unittest
import numpy as np
from m43b_active_support import active_plans
from seti_repeater import search_v0p6 as core


class ActiveSupportTests(unittest.TestCase):
    def setUp(self):
        self.grid=core.make_proxy_carrier_grid(.0005,1.,128,64)
        self.m=tuple(np.ones((2,2),dtype='<f8') for _ in range(3))
        self.t=tuple(np.ones(2,dtype='<f8') for _ in range(3))

    def test_multi_integration_exhaustive_oracle_all_activity_choices(self):
        self.t[2][:]=1.2
        for act in ((0,1),(0,2),(1,2),(0,1,2)):
            plans=active_plans(self.grid,self.m,self.t,500.,act)
            for index,p in enumerate(plans):
                good=np.ones(self.grid.score_bin_count,dtype=bool)
                for epoch in act:
                    for k in range(2):
                        good &= np.abs(self.grid.score_hz*self.m[epoch][index,k]-500*self.t[epoch][k])<=20
                np.testing.assert_array_equal(p.candidate_indices.indices,np.flatnonzero(good))
        self.assertGreater(sum(p.candidate_indices.indices.size for p in active_plans(self.grid,self.m,self.t,500.,(0,1))),0)
        self.assertEqual(sum(p.candidate_indices.indices.size for p in active_plans(self.grid,self.m,self.t,500.,(0,1,2))),0)

    def test_every_integration_is_required(self):
        self.t[0][1]=1.2
        self.assertEqual(sum(p.candidate_indices.indices.size for p in active_plans(self.grid,self.m,self.t,500.,(0,1))),0)

    def test_invalid_or_reordered_activity_rejected(self):
        for act in ((1,0),(0,0),(0,),(),(0,3),(False,1),[0,1]):
            with self.assertRaises(ValueError):active_plans(self.grid,self.m,self.t,500.,act)

    def test_invalid_inactive_epoch_still_rejected(self):
        self.t[2][0]=np.nan
        with self.assertRaises(ValueError):active_plans(self.grid,self.m,self.t,500.,(0,1))
