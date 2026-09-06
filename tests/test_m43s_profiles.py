"""New profile, association and persisted-calibration risks only."""
import math
import unittest
from unittest.mock import patch
import numpy as np
from m43q_fixture import fixture
from seti_repeater import search_v0p6 as core
from seti_repeater import detector_m43r as detector
from seti_repeater.detector_m43q import digest
from seti_repeater.injection_m43r import replace_and_integrate
from seti_repeater.injection_m43s import fractional_profile,filtered_profile_patch,restore_calibration,association_distances


class ProfileTests(unittest.TestCase):
    def test_profile_mass_symmetry_and_literal_time_average(self):
        profiles,receipts=fractional_profile([600.5,601.125])
        np.testing.assert_allclose(profiles[0][1],profiles[0][1][::-1],atol=2e-16,rtol=0)
        for (start,p),receipt in zip(profiles,receipts):
            expected=[]
            for raw in range(start,start+len(p)):
                values=[]
                for i in range(17):
                    x=raw-receipt['native_position']-((i+.5)/17-.5)
                    values.append((1. if x==0 else math.sin(math.pi*x)/(math.pi*x))**2)
                expected.append(sum(values)/17)
            expected=np.asarray(expected);expected/=sum(expected)
            np.testing.assert_allclose(p,expected,atol=5e-16,rtol=1e-13)
            self.assertAlmostEqual(float(sum(p)),1.,places=14)

    def test_all_widths_match_full_native_addition_filter_and_gather_bits(self):
        rng=np.random.default_rng(430019);source=rng.normal(size=(16,1300)).astype('<f4')
        profiles,_=fractional_profile(np.linspace(580.125,614.875,16))
        idx=np.stack([np.rint(np.arange(400)*f).astype(int)+320 for f in np.linspace(.99,1.01,16)])
        for w in core.M37_SPECTRAL_WIDTHS:
            def full(a):
                filtered=(np.sum(np.lib.stride_tricks.sliding_window_view(a,w,axis=1),axis=-1,dtype=np.float32)/np.sqrt(w)).astype('<f4')
                rows=np.stack([filtered[r,idx[r]-w//2] for r in range(16)])
                sums=np.zeros(400,dtype='<f4')
                for row in rows:sums+=row
                return rows,sums/np.float32(4)
            rows,base=full(source)
            for strength in (0.,.5,8.):
                injected=source.copy()
                for r,(start,p) in enumerate(profiles):injected[r,start:start+len(p)]+=(p*strength).astype('<f4')
                _,expected=full(injected)
                cols,values=replace_and_integrate(rows,idx,filtered_profile_patch(source,profiles,w,strength))
                got=base.copy();got[cols]=values
                np.testing.assert_array_equal(got.view('<u4'),expected.view('<u4'))

    def test_incomplete_profile_support_is_rejected(self):
        p,_=fractional_profile([20.5])
        with self.assertRaises(core.V0P6CoverageError):filtered_profile_patch(np.zeros((1,400),dtype='<f4'),p,129,1.)

    def test_association_requires_every_active_row_and_exact_activity(self):
        grid=core.make_proxy_carrier_grid(.0005,1.,100,64)
        truth={'score_index':100,'fractional_proxy_bin':0.,'active_epochs':[0,1]}
        factors=np.ones((1,3,16),dtype='<f8');true=np.ones((3,16),dtype='<f8')
        members=[{'record_id':'at-boundary','template_index':0,'proxy_carrier_index':120,'active_epochs_zero_based':[0,1]},
            {'record_id':'outside','template_index':0,'proxy_carrier_index':121,'active_epochs_zero_based':[0,1]},
            {'record_id':'wrong-subset','template_index':0,'proxy_carrier_index':100,'active_epochs_zero_based':[0,2]}]
        got=association_distances(members,truth,grid,factors,true)
        self.assertEqual(got,{'at-boundary':20.,'outside':21.})
        factors[0,2,-1]=2.
        self.assertEqual(association_distances(members,truth,grid,factors,true),got)
        factors[0,1,-1]=2.
        self.assertGreater(association_distances(members,truth,grid,factors,true)['at-boundary'],20.)

    def test_persisted_calibration_replays_identical_detector_without_new_nulls(self):
        kw,_=fixture()
        cal,summary=detector.calibrate(**{k:v for k,v in kw.items() if k not in ('receiver_factory','reference_floor','maximum_records')})
        threshold=core.calibrated_threshold((cal,),expected_window_ids=(kw['window'],),reference_floor=50.,quantile=1.,scientific_p_ceiling=.01)
        record={'calibration':summary,'threshold':threshold.as_record(),'null_maxima':cal.null_maxima.tolist()}
        record['result_sha256']=digest(record)
        restored,cert=restore_calibration(record,record['result_sha256'],threshold.certificate_sha256)
        fixed={k:v for k,v in kw.items() if k not in ('shifts','minimum_shift_bins','reference_floor')}
        expected=detector.execute(**fixed,calibration=cal,threshold=threshold)
        with patch.object(core,'update_calibration',side_effect=AssertionError('no recalibration')):
            got=detector.execute(**fixed,calibration=restored,threshold=cert)
        self.assertEqual(expected,got)
        record['null_maxima'][0]+=1
        with self.assertRaisesRegex(ValueError,'identity'):restore_calibration(record,record['result_sha256'],threshold.certificate_sha256)


if __name__=='__main__':unittest.main()
