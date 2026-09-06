"""Known-answer integration, identity, capacity and receiver tests."""
from dataclasses import replace
import unittest
import tempfile
from pathlib import Path
import numpy as np
import test_m43i_transfer as source_fixture
from m43q_fixture import fixture,run_fixture
from m43f_source_cache_preflight import build_context
from seti_repeater import search_v0p6 as core
from seti_repeater import transfer_m43i as transfer
from seti_repeater.detector_m43q import catalogue_bridge,execute
from seti_repeater.receiver_m43q import measure_signature
from m43q_integrated_detector import reference_midpoint,synthetic_artifact
from m43e_economical_bank import write_sealed,read_sealed


class IntegratedDetectorTests(unittest.TestCase):
    def test_all_dispositions_and_mask_rejection_in_one_execution(self):
        result,bridge,selected=run_fixture()
        self.assertEqual(len(selected),6)
        self.assertNotIn(200,selected)
        self.assertTrue(bridge['all_selected_factor_bits_preserved'])
        self.assertTrue(any(x['passes_evaluated_physical_vetoes'] for x in result['decisions']))
        self.assertTrue(all(not x['scientific_candidate'] for x in result['decisions']))
        self.assertTrue(all(x['inclusive_rank_p']>=.2 for x in result['decisions']))

    def test_complete_real_catalogue_preserves_all_factor_bits(self):
        _,_,_,_,basis,parent,old,_=build_context()
        bank,table,bridge=catalogue_bridge(parent,range(len(parent)),basis)
        self.assertEqual(len(bank),1701)
        self.assertNotEqual(table.template_bank_sha256,old.template_bank_sha256)
        self.assertEqual(table.factor_table_sha256,old.factor_table_sha256)
        np.testing.assert_array_equal(table.factors.view('<u8'),old.factors.view('<u8'))
        for i in (0,92,93,888,889,1700):
            self.assertEqual(bank[i]['coefficient_x'],parent[i]['coefficient_x'])
            self.assertEqual(bank[i]['coefficient_y'],parent[i]['coefficient_y'])
            self.assertEqual(bank[i]['m43_parent_template_index'],i)

    def test_changed_score_payload_or_transient_identity_is_rejected(self):
        for mutate_ids in (False,True):
            kwargs,_=fixture();store=kwargs['store'];original=store.get
            def bad(kind,t,w):
                a,identity=original(kind,t,w)
                if (kind,t,w)==('on',0,1):
                    changed=transfer.immutable(a+1)
                    if mutate_ids:store.expected_ids[(kind,t,w)]='0'*64
                    return changed,'0'*64
                return a,identity
            store.get=bad
            with self.assertRaisesRegex(ValueError,'identity'):execute(**kwargs)

    def test_missing_input_and_retention_capacity_fail_closed(self):
        kwargs,_=fixture();kwargs['store'].expected_ids.pop(('off',1,129))
        with self.assertRaisesRegex(ValueError,'inventory'):execute(**kwargs)
        kwargs,_=fixture();kwargs['maximum_records']=1
        with self.assertRaises(core.V0P6CapacityError):execute(**kwargs)

    def test_receiver_native_windows_match_independent_literal_reference(self):
        src,grid,factors=source_fixture.TelescopeTransferTests().fixture()
        for width in core.M37_SPECTRAL_WIDTHS:
            cache=transfer.build_telescope_cache(src,factors,grid,width,bank_sha256='1'*64)
            observed,receipt=measure_signature(cache,0,grid.score_half_bins)
            pred=sum(float(grid.score_hz[grid.score_half_bins])*float(f) for f in factors[0])/len(factors[0])/1e6
            native=np.arange(width//2,src.geometry.channel_count-width//2)
            freq=(src.geometry.raw_zero_hz+native*src.geometry.channel_width_hz)/1e6
            use=np.abs((freq-pred)*1e6)<=100.;native=native[use];freq=freq[use]
            values=np.zeros(len(native),dtype='<f4')
            for row in range(src.integration_count):
                windows=src.values[row,native[:,None]+np.arange(-(width//2),width//2+1)]
                values+=(np.sum(windows,axis=1,dtype=np.float32)/np.sqrt(width)).astype('<f4')
            values/=np.float32(np.sqrt(src.integration_count));winner=int(np.argmax(values))
            self.assertEqual(observed['peak_snr'],float(values[winner]))
            self.assertEqual(observed['peak_frequency_mhz'],float(freq[winner]))
            self.assertEqual(receipt['winning_raw_index'],int(native[winner]))
            with self.assertRaises(ValueError):measure_signature(replace(cache,bank_sha256='0'*64),0,0)

    def test_reference_midpoint_preserves_sequential_binary64_contract(self):
        from seti_repeater.receiver_v0p6 import _predicted_midpoint_hz
        factors=np.array([1e16,1.,1.],dtype='<f8')
        self.assertEqual(reference_midpoint(1.,factors),_predicted_midpoint_hz(1.,factors)/1e6)
        # Regression for the actual Python 3.12 reduction discrepancy.
        self.assertNotEqual(sum(float(x) for x in factors)/3/1e6,reference_midpoint(1.,factors))

    def test_synthetic_evidence_round_trips_with_a_valid_seal(self):
        r,b,k=run_fixture()
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'synthetic.json'
            original=write_sealed(path,synthetic_artifact(r,b,k))
            self.assertEqual(read_sealed(path),original)


if __name__=='__main__':unittest.main()
