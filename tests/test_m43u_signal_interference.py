"""Independent native-window references, ON/OFF routing and policy regressions."""
import unittest
from types import SimpleNamespace as NS
from unittest.mock import patch
import numpy as np
from m43q_fixture import fixture
from seti_repeater import search_v0p6 as core
from seti_repeater import detector_m43t as old
from seti_repeater import detector_m43u as new
from seti_repeater.mask_m43t import bind_calibration as old_bind
from seti_repeater.mask_m43u import build_mask, bind_calibration, validate_binding
from seti_repeater.injection_m43r import ScoreStore
from seti_repeater.injection_m43s import fractional_profile
from seti_repeater.injection_m43u import JointOverlay, joint_filtered_patch


class M43UTests(unittest.TestCase):
    def test_startup_runtime_guard(self):
        import json
        import platform
        import m43u_signal_interference as runner
        cfg={'pinned_sha256':{},'python_version':platform.python_version(),'numpy_version':np.__version__}
        raw=json.dumps(cfg).encode()
        mock=NS(read_text=lambda:raw.decode(),read_bytes=lambda:raw)
        with patch.object(runner,'CONFIG',mock),patch.object(runner.subprocess,'check_output',return_value=raw):
            self.assertEqual(runner.frozen('synthetic-startup-fixture'),cfg)

    def test_complete_overlapping_native_windows_all_widths(self):
        values=np.random.default_rng(43).normal(size=(3,700)).astype('<f4')
        a,_=fractional_profile(np.array([250.2,251.7,250.9]),smear_channels=0.)
        b,_=fractional_profile(np.array([253.8,252.1,255.3]),smear_channels=1.)
        parts=[(a,8.),(b,32.)]; dense=values.copy()
        for ps,s in parts:
            for row,(lo,p) in enumerate(ps):dense[row,lo:lo+len(p)]+=(p*s).astype('<f4')
        for w in core.M37_SPECTRAL_WIDTHS:
            reference=(np.lib.stride_tricks.sliding_window_view(dense,w,axis=1).sum(axis=-1,dtype=np.float32)/np.sqrt(w)).astype('<f4')
            for row,(lo,observed) in enumerate(joint_filtered_patch(values,parts,w)):
                np.testing.assert_array_equal(observed.view('<u4'),reference[row,lo-w//2:lo-w//2+len(observed)].view('<u4'))

    def test_incomplete_support_and_invalid_additions_fail(self):
        x=np.zeros((2,200),dtype='<f4');p=[(1,np.ones(1))]*2
        with self.assertRaises(core.V0P6CoverageError):joint_filtered_patch(x,[(p,32.)],129)
        with self.assertRaises(ValueError):joint_filtered_patch(x,[(p,-1.)],1)
        with self.assertRaises(ValueError):joint_filtered_patch(x,[(p,float('nan'))],1)

    def test_independent_mask_oracle_all_three_radii(self):
        arrays={w:np.zeros((3,55),dtype='<f4') for w in core.M37_SPECTRAL_WIDTHS}
        for i,w in enumerate(arrays):
            arrays[w][i%3,[0,20,54]]=10
            arrays[w][(i+1)%3,23]=3
            arrays[w][(i+2)%3,48]=3
        masks={}
        for policy,radius in [('legacy',0),('neighbor2',2),('neighbor9',9)]:
            expected=np.zeros((3,55),dtype=bool)
            for a in arrays.values():
                for e in range(3):
                    for q in range(55):
                        if a[e,q]>=10 and all(a[k,j]<3 for k in range(3) if k!=e for j in range(max(0,q-radius),min(55,q+radius+1))):
                            expected[e,max(0,q-9):min(55,q+10)]=True
            masks[policy]=build_mask(arrays.__getitem__,policy)
            np.testing.assert_array_equal(masks[policy],expected)
        self.assertFalse(np.any(masks['neighbor9'] & ~masks['neighbor2']))
        self.assertFalse(np.any(masks['neighbor2'] & ~masks['legacy']))

    def test_neighbor2_boundary_and_same_width(self):
        a={w:np.zeros((3,30),dtype='<f4') for w in core.M37_SPECTRAL_WIDTHS};a[1][0,10]=10;a[1][1,12]=3
        self.assertFalse(build_mask(a.__getitem__,'neighbor2').any())
        a[1][1,12]=0;a[1][1,13]=3
        self.assertTrue(build_mask(a.__getitem__,'neighbor2')[0,10])
        self.assertFalse(build_mask(a.__getitem__,'neighbor9')[0,10])
        a[1][1,13]=0;a[3][1,10]=4
        self.assertTrue(build_mask(a.__getitem__,'neighbor9')[0,10])

    def test_unchanged_legacy_and_neighbor9_pipeline(self):
        kwargs,_=fixture();args={k:v for k,v in kwargs.items() if k not in ('receiver_factory','reference_floor','maximum_records')}
        fixed={k:v for k,v in kwargs.items() if k not in ('shifts','minimum_shift_bins','reference_floor')}
        for policy in ('legacy','neighbor9'):
            ca,_=old.calibrate(**args,mask_policy=policy);cb,_=new.calibrate(**args,mask_policy=policy)
            np.testing.assert_array_equal(ca.null_maxima,cb.null_maxima)
            threshold=core.calibrated_threshold((ca,),expected_window_ids=(kwargs['window'],),reference_floor=50.,quantile=1.)
            a=old.execute(**fixed,mask_policy=policy,calibration=ca,threshold=threshold,calibration_binding=old_bind(ca,threshold,policy))
            b=new.execute(**fixed,mask_policy=policy,calibration=cb,threshold=threshold,calibration_binding=bind_calibration(cb,threshold,policy))
            for key in a:
                if key not in ('schema','purpose','result_sha256','calibration_binding'):
                    self.assertEqual(a[key],b[key],key)
            with self.assertRaises(ValueError):validate_binding(bind_calibration(cb,threshold,policy),'neighbor2',cb,threshold)

    def test_joint_ON_OFF_gathers_and_receiver_match_dense_native_reference(self):
        rng=np.random.default_rng(430022)
        raw={f'epoch{e+1}_{k}':rng.normal(0,.1,(2,800)).astype('<f4') for k in ('on','off') for e in range(3)}
        geometry=NS(raw_zero_hz=0.,channel_width_hz=1.,channel_count=800)
        sources={k:NS(values=v,geometry=geometry,integration_count=2,identity=k) for k,v in raw.items()}
        caches={};arrays={};hz=np.arange(200,281,dtype='<f8')
        for k in ('on','off'):
            for w in core.M37_SPECTRAL_WIDTHS:
                rows=[]
                for e in range(3):
                    label=f'epoch{e+1}_{k}'
                    filt=(np.lib.stride_tricks.sliding_window_view(raw[label],w,axis=1).sum(axis=-1,dtype=np.float32)/np.sqrt(w)).astype('<f4')
                    caches[label,w]=NS(values=filt,source=sources[label],identity=f'{label}:{w}')
                    sums=np.zeros(len(hz),dtype='<f4')
                    for row in filt:sums+=row[hz.astype(int)-w//2]
                    rows.append(sums/np.float32(np.sqrt(2)))
                arrays[k,0,w]=np.stack(rows)
        baseline=ScoreStore(arrays,{'family':'synthetic-unit-reference'})
        receiver=NS(cache=lambda label,w:caches[label,w]);grid=NS(support_hz=hz,support_bin_count=len(hz),score_hz=hz,channel_width_hz=1.)
        labels=[NS(scan_label=f'epoch{e+1}_{k}') for k in ('on','off') for e in range(3) for _ in range(2)]
        basis=NS(labels=labels);truth={'score_index':40,'fractional_proxy_bin':0.,'coefficient_x':0.,'coefficient_y':0.}
        comps=[{'component_id':str(i),'kind':k,'epochs':[0,1],'truth':truth,'strength':s,'shape':'point','snap_native':True,'smear_channels':0.}
            for i,(k,s) in enumerate([('on',32.),('on',4.),('off',32.)])]
        with patch.object(core,'factor_table_for_scan',return_value=np.ones((1,2))),patch.object(core,'template_factors_from_basis',return_value=np.ones(12)):
            overlay=JointOverlay(baseline,receiver,[{}],None,basis,grid)
            self.assertEqual(len(overlay.cache_inventory),48)
            store=overlay.trial(comps)
            dense={k:v.copy() for k,v in raw.items()}
            for c in comps:
                for e in c['epochs']:dense[f'epoch{e+1}_{c["kind"]}'][:,240]+=np.float32(c['strength']/np.sqrt(2))
            for k in ('on','off'):
                for w in core.M37_SPECTRAL_WIDTHS:
                    expected=[]
                    for e in range(3):
                        filt=(np.lib.stride_tricks.sliding_window_view(dense[f'epoch{e+1}_{k}'],w,axis=1).sum(axis=-1,dtype=np.float32)/np.sqrt(w)).astype('<f4')
                        sums=np.zeros(len(hz),dtype='<f4')
                        for row in filt:sums+=row[hz.astype(int)-w//2]
                        expected.append(sums/np.float32(np.sqrt(2)))
                    np.testing.assert_array_equal(store.get(k,0,w)[0].view('<u4'),np.stack(expected).view('<u4'))
            rec={'record_id':'fixture','template_index':0,'proxy_carrier_index':40,'spectral_width_channels':1,'active_epochs_zero_based':[0,1]}
            signatures,_=overlay([rec],[{}],None)
            for sig in signatures['fixture']:
                rows=dense[f'epoch{sig["epoch_zero_based"]+1}_on'];sums=(rows[0]+rows[1])/np.float32(np.sqrt(2))
                self.assertEqual(sig['peak_snr'],float(sums[240]))
                self.assertAlmostEqual(sig['peak_frequency_mhz'],240/1e6)
            reset=overlay.trial([])
            for key,value in baseline.arrays.items():np.testing.assert_array_equal(reset.arrays[key],value)


if __name__ == '__main__':
    unittest.main()
