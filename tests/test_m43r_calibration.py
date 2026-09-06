"""New risks only: native overlay arithmetic and fixed threshold handoff."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import numpy as np
from m43q_fixture import fixture,run_fixture
from seti_repeater import search_v0p6 as core
from seti_repeater import detector_m43r as detector
from seti_repeater.injection_m43r import filtered_patch,replace_and_integrate,ScoreStore,NativeOverlay


class CalibrationPilotTests(unittest.TestCase):
    def test_native_patch_matches_complete_materialization_all_widths(self):
        rng=np.random.default_rng(434343)
        source=rng.normal(size=(16,1200)).astype('<f4')
        centers=np.arange(16)*2+570
        indices=np.stack([np.rint(np.arange(350)*factor).astype(int)+340 for factor in np.linspace(.99,1.01,16)])
        for width in core.M37_SPECTRAL_WIDTHS:
            half=width//2
            def full(values):
                filtered=(np.sum(np.lib.stride_tricks.sliding_window_view(values,width,axis=1),axis=-1,dtype=np.float32)/np.sqrt(width)).astype('<f4')
                rows=np.stack([filtered[r,indices[r]-half] for r in range(16)])
                sums=np.zeros(indices.shape[1],dtype='<f4')
                for row in rows:sums+=row
                return rows,sums/np.float32(4)
            rows,baseline=full(source)
            for amp in (0.,2.,16.):
                overlay=source.copy();overlay[np.arange(16),centers]+=np.float32(amp)
                _,expected=full(overlay)
                columns,sums=replace_and_integrate(rows,indices,filtered_patch(source,centers,width,amp))
                observed=baseline.copy();observed[columns]=sums
                np.testing.assert_array_equal(observed.view('<u4'),expected.view('<u4'))

    def test_frozen_calibration_preserves_all_q_pipeline_dispositions(self):
        kwargs,_=fixture();expected,_,_=run_fixture()
        calibration,summary=detector.calibrate(**{k:v for k,v in kwargs.items() if k not in ('receiver_factory','reference_floor','maximum_records')})
        threshold=core.calibrated_threshold((calibration,),expected_window_ids=(kwargs['window'],),reference_floor=50.,quantile=1.,scientific_p_ceiling=.01)
        fixed={k:v for k,v in kwargs.items() if k not in ('shifts','minimum_shift_bins','reference_floor')}
        # The injected-evaluation entry point is forbidden from recalibrating.
        with patch.object(core,'update_calibration',side_effect=AssertionError('recalibration forbidden')):
            observed=detector.execute(**fixed,calibration=calibration,threshold=threshold)
        for key in ('retained','decisions','receiver_alias','threshold','rank'):
            self.assertEqual(observed[key],expected[key])

    def test_native_patch_rejects_incomplete_support(self):
        with self.assertRaisesRegex(ValueError,'incomplete'):
            filtered_patch(np.zeros((2,300),dtype='<f4'),[2,200],129,3.)

    def test_receiver_signatures_use_injected_native_windows(self):
        rng=np.random.default_rng(1943)
        source=rng.normal(size=(16,1200)).astype('<f4');centers=np.full(16,600)
        grid=core.make_proxy_carrier_grid(.0006,1.,100,64)
        geometry=SimpleNamespace(raw_zero_hz=0.,channel_width_hz=1.,channel_count=1200)
        overlay=NativeOverlay.__new__(NativeOverlay);overlay.grid=grid
        overlay.factors={0:np.ones((1,16),dtype='<f8')};overlay.overlay_receipt={'kind':'synthetic-test'}
        for width in core.M37_SPECTRAL_WIDTHS:
            def filt(values):
                return (np.sum(np.lib.stride_tricks.sliding_window_view(values,width,axis=1),axis=-1,dtype=np.float32)/np.sqrt(width)).astype('<f4')
            cache=SimpleNamespace(source=SimpleNamespace(geometry=geometry,integration_count=16),values=filt(source),identity='synthetic')
            overlay.receiver=SimpleNamespace(cache=lambda label,w:cache)
            overlay.patches={(0,width):filtered_patch(source,centers,width,16.)}
            records=[{'record_id':'test','template_index':0,'proxy_carrier_index':100,
                'spectral_width_channels':width,'active_epochs_zero_based':[0]}]
            got,receipt=overlay(records,[],None)
            injected=source.copy();injected[:,600]+=np.float32(16.)
            full=filt(injected);raw=np.arange(490,711)
            freq=raw.astype('<f8')/1e6;keep=np.abs((freq-.0006)*1e6)<=100
            raw=raw[keep];freq=freq[keep];sums=np.zeros(len(raw),dtype='<f4')
            for row in full:sums+=row[raw-width//2]
            sums/=np.float32(4);win=int(np.argmax(sums))
            self.assertEqual(got['test'][0]['peak_frequency_mhz'],float(freq[win]))
            self.assertEqual(got['test'][0]['peak_snr'],float(sums[win]))

    def test_overlay_store_does_not_accept_changed_payload(self):
        store=ScoreStore({('on',0,1):np.ones((3,10),dtype='<f4')},{'kind':'synthetic'})
        store.arrays['on',0,1]=store.arrays['on',0,1]+1
        with self.assertRaisesRegex(ValueError,'payload'):store.get('on',0,1)


if __name__=='__main__':unittest.main()
