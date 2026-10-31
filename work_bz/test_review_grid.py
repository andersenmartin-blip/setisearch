"""Synthetic-only independent BZ reviewer tests; no observation files are read."""
from pathlib import Path
import importlib.util
import math
import unittest
import numpy as np

ROOT=Path(__file__).resolve().parent

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result

review=module('bz_review_synthetic',ROOT/'review_grid.py')
production=module('bz_production_synthetic',ROOT/'grid_recovery.py')

class IndependentGridTests(unittest.TestCase):
    def test_all_exact_nested_rates_and_endpoints(self):
        coarse=np.linspace(-4,4,839,dtype=np.float64)
        for base in (314,419,524):
            rates=review.nested_rates(base)
            review.exact_array(rates,production.refined_bank(coarse,base),'synthetic full grid')
            self.assertEqual(rates[[0,8,16]].tobytes(),coarse[base-1:base+2].tobytes())
            self.assertTrue((np.diff(rates)>0).all())
            previous=set()
            for factor in (1,2,4,8):
                selected=set(range(0,17,8//factor))
                self.assertTrue(previous<=selected)
                self.assertEqual(len(selected),2*factor+1)
                self.assertEqual(tuple(sorted(selected)),production.factor_indices(factor))
                previous=selected

    def test_all_offset_rounding_order(self):
        dt,df=18.253611008,-2.7939677238464355
        for base in (314,419,524):
            rates=review.nested_rates(base)
            vector=np.rint(rates[:,None]*((np.arange(16)-7.5)*dt)[None,:]/df).astype(np.int32)
            scalar=np.asarray([[round(float(rate)*(row-7.5)*dt/df) for row in range(16)] for rate in rates],dtype=np.int32)
            review.exact_array(scalar,vector,'all synthetic physical offsets')

    def test_direct_vectors_match_independent_scalar_track_sums(self):
        rng=np.random.default_rng(20261031)
        y=rng.normal(size=(16,200)).astype(np.float32)
        offsets=np.array([-3,-3,-2,-2,-1,-1,0,0,0,0,1,1,2,2,3,3],dtype=np.int32)
        centers=np.arange(40,150,7,dtype=np.int32)
        for width in (1,3,9,33):
            vector=review.direct_vector(y,offsets,centers,width)
            scalars=np.asarray([review.scalar_sum(y,offsets,int(center),width) for center in centers])
            np.testing.assert_allclose(vector,scalars,rtol=0,atol=1e-12)

    def test_outside_support_rejected(self):
        with self.assertRaises(ValueError):
            review.direct_vector(np.zeros((16,20),dtype=np.float32),np.zeros(16,dtype=np.int32),np.array([0,19]),3)

    def test_orderstatistics_odd_even_and_degenerate(self):
        for values in ([1.,8.,3.,4.],[1.,3.,8.],[-7.,-3.,-2.,1.,5.,11.]):
            median,scale=review.median_mad(values)
            self.assertEqual(median,float(np.median(values)))
            self.assertEqual(scale,float(1.4826*np.median(np.abs(np.asarray(values)-np.median(values)))))
        with self.assertRaises(ValueError):review.median_mad([0.,0.,0.])

    def test_piecewise_integral_against_declared_cdf(self):
        for low,high in ((-.5,.5),(-1.3,2.1),(3.,3.),(-.99,-.98),(4.25,7.75)):
            weights=[]
            for channel in range(math.floor(low)-1,math.ceil(high)+2):
                direct=review.time_averaged_triangle(low,high,channel)
                cdf=(review.triangle(low-channel) if low==high else
                     (review.declared_cdf(high-channel)-review.declared_cdf(low-channel))/(high-low))
                self.assertAlmostEqual(direct,cdf,places=12)
                weights.append(direct)
            self.assertAlmostEqual(math.fsum(weights),1.,places=12)

    def test_reconstruction_is_one_float32_cast_and_inactive_unchanged(self):
        base=np.full((16,40),.15,dtype=np.float32)
        weights=[(np.array([11,12]),np.array([.25,.75])) for _ in range(16)]
        active=review.reconstructed_matrix(base,weights,4.,True)
        expected=base.copy();expected[:,11:13]=(base[:,11:13].astype(np.float64)+np.array([1.,3.])).astype(np.float32)
        review.exact_array(active,expected,'declared single cast')
        review.exact_array(review.reconstructed_matrix(base,weights,4.,False),base,'inactive background')
        review.exact_array(review.reconstructed_matrix(base,weights,0.,True),base,'zero background')
        self.assertTrue((base==np.float32(.15)).all())

    def test_thresholds_and_missing_sixth_scan(self):
        center=[10.,0.,10.,0.,10.,float('nan')]
        maxima=[10.,4.999,10.,4.999,10.,float('nan')]
        valid=[True]*5+[False]
        self.assertEqual(review.independently_classify(center,maxima,valid),'INCOMPLETE_OFF_COVERAGE')
        maxima[1]=5.
        self.assertEqual(review.independently_classify(center,maxima,valid),'REJECTED_AVAILABLE_OFF')
        center[2]=9.999
        self.assertEqual(review.independently_classify(center,maxima,valid),'THREE_ON_FAIL')
        valid[4]=False
        self.assertEqual(review.independently_classify(center,maxima,valid),'UNSUPPORTED')

    def test_overlap_is_preserved(self):
        cases=[dict(presence='ON_ONLY',amplitude=8.,matched_source_seed_rows=2,three_ON_recovered=True,
                    available_OFF_rejected=True,retained_partial=True)]
        group=[g for g in review.independent_groups(cases) if g['presence']=='ON_ONLY' and g['amplitude']==8.][0]
        self.assertEqual(group['both_retained_and_rejected'],1)
        self.assertEqual(group['retained_partial'],1)
        self.assertEqual(group['available_OFF_rejected'],1)
        self.assertEqual(group['three_ON_recovered'],1)

    def test_byte_identity_rejects_dtype_and_changed_nan(self):
        with self.assertRaises(ValueError):review.exact_array(np.array([1],dtype=np.int32),np.array([1],dtype=np.int64),'dtype')
        with self.assertRaises(ValueError):review.exact_array(np.array([0.]),np.array([-0.]),'signbit')
        original=np.array([float('nan')]);review.exact_array(original,original.copy(),'nan bytes')

    def test_complete_declared_case_matrix(self):
        cases=review.expected_cases()
        self.assertEqual(len(cases),264)
        self.assertEqual(len({case['geometry'] for case in cases}),24)
        self.assertEqual(sum(case['presence']=='ZERO_CONTROL' for case in cases),24)
        self.assertEqual([case['case_index'] for case in cases],list(range(264)))

    def test_local_peak_plateaus_and_edges(self):
        values=np.array([2.,2.,1.,4.,3.])
        self.assertTrue(review.is_local_peak(values,0,1))
        self.assertTrue(review.is_local_peak(values,1,1))
        self.assertFalse(review.is_local_peak(values,2,1))
        self.assertTrue(review.is_local_peak(values,3,1))
        self.assertFalse(review.is_local_peak(values,4,1))

if __name__=='__main__':unittest.main()
