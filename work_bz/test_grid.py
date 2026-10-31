"""Synthetic-only checks for the prospective BZ grid change.

No plan, baseline NPZ, observation NPY, or production output is opened.
"""
import math
import statistics
import unittest

import numpy as np

import grid_recovery as grid


class NestedRates(unittest.TestCase):
    def test_exact_anchors_and_nested_float_values(self):
        original=np.linspace(-4,4,839,dtype=np.float64)
        for base in (314,419,524):
            bank=grid.refined_bank(original,base)
            self.assertEqual(bank[list(grid.ANCHORS)].tobytes(),original[base-1:base+2].tobytes())
            self.assertEqual(bank.dtype,np.dtype('float64'))
            self.assertTrue(np.all(np.diff(bank)>0))
            previous=None
            for factor,expected_size in ((1,3),(2,5),(4,9),(8,17)):
                selected=bank[list(grid.factor_indices(factor))]
                self.assertEqual(len(selected),expected_size)
                self.assertEqual(selected[0],original[base-1])
                self.assertEqual(selected[-1],original[base+1])
                if previous is not None:
                    self.assertEqual(selected[::2].tobytes(),previous.tobytes())
                # A rate halfway between adjacent templates has at most this
                # phase error over a fixed synthetic 1500-second cadence.
                nominal=max(np.diff(original[base-1:base+2]))/factor
                self.assertLessEqual(np.max(np.diff(selected)),nominal+1e-15)
                self.assertLessEqual(.5*np.max(np.diff(selected))*1500/2.7939677238464355,
                                     .5*nominal*1500/2.7939677238464355+1e-12)
                previous=selected
        for invalid in (0,3,16,-1):
            with self.assertRaises(ValueError):grid.factor_indices(invalid)

    def test_declared_work_and_seed_bounds(self):
        per_rate=sum(len(range(0,4096,stride)) for stride in grid.STRIDES)
        self.assertEqual(264*5*14*per_rate,grid.CONFIG['new_correlated_track_combinations'])
        self.assertEqual(264*5*3*per_rate,grid.CONFIG['reused_baseline_track_combinations'])
        self.assertEqual(264*5*17*per_rate,grid.CONFIG['union_nominal_track_combinations'])
        self.assertEqual(264*5*14*4,grid.CONFIG['new_calibration_vectors'])
        per_rate_center_bound=sum((2*(width//2+2))//stride+1
                                  for width,stride in zip(grid.WIDTHS,grid.STRIDES))
        self.assertLessEqual(17*per_rate_center_bound,grid.CONFIG['max_matched_seeds_per_case'])


class NewRateNumerics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kernel,cls.classifier=grid.load_by().load_components()
        cls.y=np.random.default_rng(61208).normal(0,1,(16,12288)).astype(np.float32)

    def test_all_new_rate_full_core_vectors_against_direct_addition(self):
        original=np.linspace(-4,4,839,dtype=np.float64)
        times=(np.arange(16)-7.5)*18.253611008
        for base in (314,419,524):
            bank=grid.refined_bank(original,base)
            for width,stride in zip(grid.WIDTHS,grid.STRIDES):
                prepared=self.kernel.boxcars(self.y,width)
                centers=np.arange(4096,8192,stride,dtype=np.int32)
                for ri in grid.NEW_INDICES:
                    offsets=np.rint(bank[ri]*times/-2.7939677238464355).astype(np.int32)
                    actual=self.kernel.tracks_grid(self.y,prepared,offsets,4096,8192,stride,width)[0]
                    # Independent summation: no boxcar or track helper.
                    reference=np.zeros(len(centers),dtype=np.float64)
                    for row,offset in enumerate(offsets):
                        for delta in range(-(width//2),width//2+1):
                            reference+=self.y[row,centers+int(offset)+delta].astype(np.float64)
                    self.assertLessEqual(float(np.max(np.abs(actual-reference))),5e-5)
                    med=statistics.median(reference.tolist())
                    mad=1.4826*statistics.median(abs(float(x)-med) for x in reference)
                    actual_med=float(np.median(actual))
                    actual_mad=1.4826*float(np.median(np.abs(actual-actual_med)))
                    self.assertAlmostEqual(actual_med,med,places=10)
                    self.assertAlmostEqual(actual_mad,mad,places=10)
                    selected=self.kernel.tracks_selected(self.y,prepared,offsets,centers[[0,len(centers)//2,-1]],width)[0]
                    for center,value in zip(centers[[0,len(centers)//2,-1]],selected):
                        exact=math.fsum(float(self.y[row,int(center)+int(offset)+delta])
                                        for row,offset in enumerate(offsets)
                                        for delta in range(-(width//2),width//2+1))
                        self.assertLessEqual(abs(float(value)-exact),5e-5)
                    self.assertTrue(np.array_equal(selected,actual[[0,len(centers)//2,-1]]))


class ArmAccounting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _,cls.classifier=grid.load_by().load_components()

    def test_nested_cases_keep_failed_and_overlapping_rows(self):
        case={'case_index':0,'presence':'ON_ONLY','amplitude':4.0}
        seeds=[{'refined_index':ri} for ri in (0,1,2,4)]
        centers=np.full((4,6),np.nan)
        centers[:,:5]=[[12,0,9,0,12],[12,0,12,0,12],
                        [12,6,12,0,12],[12,0,12,0,12]]
        maxima=centers.copy();valid=np.isfinite(centers)
        status=type(self).classifier(centers,maxima,valid)['candidate_status']
        values=[grid.summarize_case(case,seeds,status,centers,f) for f in (1,2,4,8)]
        self.assertEqual([x['matched_source_seed_rows'] for x in values],[1,2,3,4])
        self.assertEqual([x['three_ON_recovered'] for x in values],[False,True,True,True])
        self.assertEqual([x['retained_partial'] for x in values],[False,True,True,True])
        self.assertEqual([x['available_OFF_rejected'] for x in values],[False,False,True,True])
        self.assertEqual([x['both_retained_and_rejected'] for x in values],[False,False,True,True])
        expected=dict(case,matched_source_seed_rows=1,three_ON_recovered=False,
                      available_OFF_rejected=False,retained_partial=False,
                      status_counts={'THREE_ON_FAIL':1,'REJECTED_AVAILABLE_OFF':0,
                                     'INCOMPLETE_OFF_COVERAGE':0,'UNSUPPORTED':0})
        self.assertEqual(grid.baseline_case(values[0]),expected)
        for value in values:
            self.assertEqual(sum(value['status_counts'].values()),value['matched_source_seed_rows'])
        groups=grid.group_cases([values[-1]])
        chosen=next(g for g in groups if g['presence']=='ON_ONLY' and g['amplitude']==4.0)
        self.assertEqual(chosen,{'presence':'ON_ONLY','amplitude':4.0,'geometries':1,
                                'source_recovered':1,'three_ON_recovered':1,
                                'available_OFF_rejected':1,'retained_partial':1,
                                'both_retained_and_rejected':1})

    def test_gain_and_loss_accounting_including_source(self):
        baseline=[dict(case_index=i,matched_source_seed_rows=n,three_ON_recovered=on,
                       available_OFF_rejected=off,retained_partial=keep)
                  for i,n,on,off,keep in ((0,0,False,False,False),(1,1,True,False,True))]
        # Include a deliberate loss to prove the report does not suppress it.
        revised=[dict(baseline[0],matched_source_seed_rows=2,three_ON_recovered=True,
                      available_OFF_rejected=True,retained_partial=True),
                 dict(baseline[1],matched_source_seed_rows=0,three_ON_recovered=False,
                      retained_partial=False)]
        result=grid.compare_cases(revised,baseline)
        for event in ('source_recovered','three_ON_recovered','retained_partial'):
            self.assertEqual(result[event],{'gained_case_indices':[0],'lost_case_indices':[1]})
        self.assertEqual(result['available_OFF_rejected'],{'gained_case_indices':[0],'lost_case_indices':[]})
        empty=grid.summarize_case({'case_index':2},[],np.empty(0,dtype='<U28'),np.empty((0,6)),8)
        self.assertEqual(empty['matched_source_seed_rows'],0)
        self.assertFalse(empty['three_ON_recovered'])
        self.assertFalse(empty['both_retained_and_rejected'])


if __name__=='__main__':
    unittest.main(verbosity=2)
