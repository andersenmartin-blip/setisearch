import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import radio_receiver_adapter_common as common
from seti_repeater import receiver_contract_radio as contract
from seti_repeater import pipeline_receiver_radio as pipeline
from seti_repeater import receiver_development_radio as render
from seti_repeater import transfer_m43g as native
from seti_repeater import search_v0p6 as core
from seti_repeater.injection_m43r import ScoreStore


class AdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=common.context()

    def test_explicit_rates_no_invented_orbit(self):
        self.assertEqual([t['rate_label_hz_s'] for t in self.c.bank],list(np.arange(-40,41)/10))
        self.assertFalse(any('phase_cycles' in t or 'projected_scale' in t for t in self.c.bank))

    def test_external_bank_pin_required(self):
        with self.assertRaises(ValueError):contract.build(self.c.factor_contract.factors,self.c.scans,
          trusted_bank_identity='0'*64,source_contract_bytes=self.c.factor_contract.source_contract_bytes)

    def test_source_bytes_pin_required(self):
        with self.assertRaises(ValueError):contract.build(self.c.factor_contract.factors,self.c.scans,
          trusted_bank_identity=self.c.factor_contract.factors.identity,source_contract_bytes=b'{}')

    def test_scan_inventory_cannot_change_under_same_bank(self):
        scans=copy.deepcopy(self.c.scans);scans[0]['expected_header']['tstart_mjd']+=1
        with self.assertRaises(ValueError):contract.build(self.c.factor_contract.factors,scans,
          trusted_bank_identity=self.c.factor_contract.factors.identity,
          source_contract_bytes=self.c.factor_contract.source_contract_bytes)

    def test_ledger_rows_and_factor_slots(self):
        self.assertEqual(self.c.factor_contract.matrix_for_kind('on').shape,(81,48))
        self.assertNotEqual(self.c.factor_contract.row_selection_sha256('on'),self.c.factor_contract.row_selection_sha256('off'))
        self.assertFalse(self.c.factor_contract.record()['orbital_fields_constructed'])

    def test_grid_mutation_rejected(self):
        c=copy.copy(self.c);c.grid=core.make_proxy_carrier_grid(self.c.grid.center_mhz,self.c.grid.channel_width_hz,41,9)
        with self.assertRaises(ValueError):c.validate()

    def test_role_relabel_rejected(self):
        c=copy.copy(self.c);c.window='hd189733_pilot_receiver_v1'
        with self.assertRaises(ValueError):c.validate()

    def test_cross_window_calibration_rejected_before_numerics(self):
        cal=pipeline.Calibration('0'*64,None,None,{}, {},native.digest({}))
        with self.assertRaises(ValueError):cal.validate(self.c)

    def test_source_inventory_missing_rejected(self):
        with self.assertRaises(ValueError):pipeline.NativeRun(self.c,{})

    def test_stale_cache_receipt_after_vector_rehash_rejected(self):
        # Deterministic zero-array interface fixture; no random realization or scoring.
        c=self.c;values=native.immutable(np.zeros((16,65536),dtype='<f4'));sources={}
        for scan in c.scans:
            scope={'kind':'synthetic','scan':scan['label'],'context_sha256':c.identity,
                   'receiver_factor_bank_sha256':c.factor_contract.factors.identity}
            h=native.array_hash(values)
            ident=native.digest({'contract':native.CONTRACT_SHA256,'geometry':c.geometry.__dict__,
                'rows':16,'scope':scope,'raw_sha256':h,'normalized_sha256':h})
            sources[scan['label']]=native.SyntheticSource(c.geometry,16,json.dumps(scope),h,h,ident,values)
        run=pipeline.NativeRun(c,sources)
        arrays={(kind,t,w):np.zeros((3,99),dtype='<f4') for kind in ('on','off') for t in range(81) for w in core.M37_SPECTRAL_WIDTHS}
        cache_sha=native.array_hash(np.zeros((81,99),dtype='<f4'))
        p={'source_domain':'synthetic','context_sha256':c.identity,
           'receiver_factor_contract_sha256':c.factor_contract.identity,'source_ids':run.source_ids,
           'native_caches':[{'scan':s['label'],'width':w,'source_identity':sources[s['label']].identity,
             'cache_identity':'0'*64,'full_support_score_sha256':cache_sha}
             for s in c.scans for w in core.M37_SPECTRAL_WIDTHS]}
        run.validate_store(ScoreStore(arrays,p))
        arrays['on',0,1][0,0]=1
        with self.assertRaisesRegex(ValueError,'cache receipt'):run.validate_store(ScoreStore(arrays,p))

    def test_detector_numerical_body_matches_declared_transform(self):
        s=(ROOT/'src/seti_repeater/detector_direct_radio.py').read_text()
        s=s.replace('DirectFactorContract','ReceiverContract').replace('Direct-table','Receiver-table').replace('direct','receiver')
        s=s.replace('"projected_scale": template["projected_scale"],\n            "phase_cycles": template["phase_cycles"],',
          '"rate_label_hz_s": template["rate_label_hz_s"],\n            "actual_drift_hz_s": float(grid.score_hz[record["proxy_carrier_index"]]) * template["rate_label_hz_s"] / template["rate_reference_hz"],')
        s=s.replace('receiver receiver','receiver-frame').replace('literal-midpoint-table-not-factor-basis','literal-receiver-midpoint-table-not-factor-basis')
        self.assertEqual(s,(ROOT/'src/seti_repeater/detector_receiver_radio.py').read_text())


class RendererTests(unittest.TestCase):
    def test_oracle_float64_filter_divisor(self):
        from types import SimpleNamespace
        values=np.zeros((1,9),dtype='<f4');values[0,4]=1
        source=SimpleNamespace(geometry=core.NativeFrequencyGeometry(0.,1.,9),integration_count=1,values=values)
        actual=render.score_oracle(source,np.ones((1,1)),np.array([4.]),3)
        expected=np.array([[np.float64(1)/np.sqrt(3)]],dtype='<f4')
        np.testing.assert_array_equal(actual.view('<u4'),expected.view('<u4'))

    def test_zero_drift_aligned(self):
        i,m=render.pixel_masses(100,0,1,256);np.testing.assert_array_equal(i,[100]);np.testing.assert_array_equal(m,[1])

    def test_fractional_zero_drift(self):
        i,m=render.pixel_masses(100.25,0,1,256);np.testing.assert_array_equal(i,[100,101]);np.testing.assert_allclose(m,[.75,.25],rtol=0,atol=1e-14)

    def test_sign_reversal(self):
        a,b=render.pixel_masses(100.3,9.7,1,256);c,d=render.pixel_masses(100.3,-9.7,1,256)
        np.testing.assert_array_equal(a,c);np.testing.assert_array_equal(b,d)

    def test_translation(self):
        a,b=render.pixel_masses(100.25,2.75,1,256);c,d=render.pixel_masses(117.25,2.75,1,256)
        np.testing.assert_array_equal(a+17,c);np.testing.assert_array_equal(b,d)

    def test_conserved_wide_exposure(self):
        for width in (1,5,33,65,129):
            _,m=render.pixel_masses(500.25,25.3,width,1024)
            self.assertAlmostEqual(float(m.sum()),1,places=12)

    def test_independent_midpoint_exposure_integral(self):
        i,m=render.pixel_masses(100.37,2.73,1,256)
        centers=100.37+2.73*((np.arange(20001)+.5)/20001-.5)
        oracle=np.maximum(0,np.minimum(i[:,None]+.5,centers+.5)-np.maximum(i[:,None]-.5,centers-.5)).mean(axis=1)
        np.testing.assert_allclose(m,oracle,rtol=0,atol=5e-5)

    def test_incomplete_support_rejected(self):
        with self.assertRaises(ValueError):render.pixel_masses(0,5,1,256)

    def test_invalid_renderer_domain(self):
        for args in [(100,0,0,256),(float('nan'),0,1,256),(100,float('inf'),1,256)]:
            with self.assertRaises(ValueError):render.pixel_masses(*args)

    def test_nearest_even_negative_and_positive_ties(self):
        np.testing.assert_array_equal(render.nearest_even(np.array([-2.5,-1.5,-.5,.5,1.5,2.5])),[-2,-2,0,0,2,2])


if __name__=='__main__':unittest.main()
