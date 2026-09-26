"""Identity, numerical model and handoff checks specific to direct factors."""
from dataclasses import replace
import json
import unittest
import numpy as np
from seti_repeater import factors_radio as direct,transfer_m43g as native,search_v0p6 as core
from radio_direct_factors_fixture import independent_factors


def fixture(e=.172):
    mid=np.array([s*337+r*17.986224128 for s in range(6) for r in range(16)])
    clock=np.column_stack([mid-17.986224128/2,mid,mid+17.986224128/2])
    observer=1+7e-5-1e-10*clock
    templates=[{'template_index':0,'projected_scale':0.,'phase_cycles':0.}]
    templates += [{'template_index':i+1,'projected_scale':1.,'phase_cycles':i/8} for i in range(8)]
    return direct.build(clock_seconds=clock,observer_multipliers=observer,templates=templates,
        orbit={'period_days':5.77152,'semi_major_axis_au':.0634,'eccentricity':e,'omega_deg':-10.},
        provenance={'source_contract_sha256':'1'*64,'clock_sha256':'2'*64,'observer_evidence_sha256':'3'*64,
                    'coordinate_scenario':'explicit-test-only','scan_labels':list(direct.LABELS)})


class DirectFactorTests(unittest.TestCase):
    def test_direct_eccentric_oracle_and_reference_anchor(self):
        bank=fixture();direct.validate(bank)
        np.testing.assert_allclose(bank.factors,independent_factors(bank),rtol=0,atol=2e-15)
        np.testing.assert_array_equal(bank.factors[:,0,1],np.ones(9))
        values=json.loads(bank.inputs_json)
        obs=np.asarray(values['observer_multipliers'])
        np.testing.assert_array_equal(bank.factors[0],obs/obs[0,1])

    def test_circular_limit_remains_directly_reproducible(self):
        bank=fixture(0.)
        np.testing.assert_allclose(bank.factors,independent_factors(bank),rtol=0,atol=2e-15)

    def test_payload_is_immutable_and_forged_digest_cannot_change_model(self):
        bank=fixture()
        with self.assertRaises(ValueError):bank.factors.setflags(write=True)
        corrupt=bank.factors.copy();corrupt[1,2,1]+=1e-7
        altered=replace(bank,factors=native.immutable(corrupt))
        with self.assertRaisesRegex(ValueError,'identity'):direct.validate(altered)
        forged=replace(altered,identity=native.digest(altered.record()))
        with self.assertRaisesRegex(ValueError,'reproduce'):direct.validate(forged)

    def test_coordinate_provenance_changes_identity(self):
        bank=fixture();data=json.loads(bank.inputs_json)
        data['provenance']['coordinate_scenario']='separate-header-test'
        other=direct.build(**data)
        self.assertNotEqual(bank.identity,other.identity)
        np.testing.assert_array_equal(bank.factors,other.factors)

    def test_clock_order_and_duplicate_hypotheses_rejected(self):
        data=json.loads(fixture().inputs_json)
        data['clock_seconds'][20],data['clock_seconds'][21]=data['clock_seconds'][21],data['clock_seconds'][20]
        with self.assertRaisesRegex(ValueError,'ordered'):direct.build(**data)
        data=json.loads(fixture().inputs_json)
        data['templates'][2]['phase_cycles']=data['templates'][1]['phase_cycles']
        with self.assertRaisesRegex(ValueError,'duplicate'):direct.build(**data)

    def test_scan_and_edge_selection_preserves_literal_bits(self):
        bank=fixture()
        for index,label in enumerate(direct.LABELS):
            for column,name in enumerate(('start','midpoint','end')):
                actual=direct.for_scan(bank,label,sample=name)
                np.testing.assert_array_equal(actual.view('<u8'),bank.factors[:,16*index:16*(index+1),column].view('<u8'))
        with self.assertRaises(ValueError):direct.for_scan(bank,'unlisted')

    def test_wrong_source_handoff_and_telescope_type_are_refused(self):
        bank=fixture();grid=core.make_proxy_carrier_grid(1475.,2.835503418,256,64)
        geometry=core.NativeFrequencyGeometry(1475e6-8192*2.835503418,2.835503418,16384)
        rng=np.random.default_rng(321);raw=np.asarray(100+rng.standard_normal((16,16384)),dtype='<f4')
        src=native.normalize_synthetic_rows(lambda r:raw[r],geometry,16,input_orientation='ascending',
            scope={'kind':'synthetic','scan':'epoch1_on','direct_factor_bank_sha256':bank.identity})
        cache=direct.synthetic_cache(src,bank,'epoch1_on',grid,1)
        self.assertEqual(cache.bank_sha256,bank.identity)
        with self.assertRaisesRegex(ValueError,'another scan'):direct.synthetic_cache(src,bank,'epoch2_on',grid,1)
        with self.assertRaisesRegex(ValueError,'typed synthetic'):direct.synthetic_cache(object(),bank,'epoch1_on',grid,1)
        tiny=replace(src,scope_json=json.dumps({'kind':'synthetic','scan':'epoch1_on','direct_factor_bank_sha256':'4'*64}))
        with self.assertRaisesRegex(ValueError,'another scan'):direct.synthetic_cache(tiny,bank,'epoch1_on',grid,1)

    def test_insufficient_late_scan_support_fails_before_gather(self):
        bank=fixture();df=2.835503418
        grid=core.make_proxy_carrier_grid(1475.,df,256,64)
        geometry=core.NativeFrequencyGeometry(1475e6-2048*df,df,4096)
        raw=np.asarray(100+np.random.default_rng(91).standard_normal((16,4096)),dtype='<f4')
        src=native.normalize_synthetic_rows(lambda r:raw[r],geometry,16,input_orientation='ascending',
            scope={'kind':'synthetic','scan':'epoch3_on','direct_factor_bank_sha256':bank.identity})
        with self.assertRaises(core.V0P6CoverageError):direct.synthetic_cache(src,bank,'epoch3_on',grid,129)


if __name__=='__main__':unittest.main()
