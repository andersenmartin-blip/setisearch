"""Fixed score/signature vectors test the new physical receipt boundaries."""
import copy
import hashlib
import unittest
import numpy as np
from seti_repeater import search_v0p6 as core
from seti_repeater.empty_null_radio import canonical
from seti_repeater.injection_m43r import ScoreStore
from seti_repeater.whole_cadence_reference_radio import Family, digest, reduce_fixture
from seti_repeater.whole_cadence_downstream_radio import bind_threshold
from seti_repeater.whole_cadence_physical_radio import run_fixture, IncompletePhysical, stable
from seti_repeater.receiver_v0p6 import _predicted_midpoint_hz

NS='radio-whole-cadence-physical-engineering-20260928'
def identity(name):return hashlib.sha256((NS+'/'+str(name)).encode()).hexdigest()


class PhysicalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.grid=core.make_proxy_carrier_grid(.0001,10.,4,9)
        cls.family=Family('a'*64,'b'*64,2,cls.grid)
        cls.law=digest({'kind':'deterministic-score-fixture','namespace':NS})
        cls.on=np.ones((2,48),dtype='<f8');cls.off=cls.on.copy()
        units=tuple(reduce_fixture(cls.family,cls.store(i),case_identity=identity(i),noise_law_sha256=cls.law) for i in range(127))
        cls.threshold=bind_threshold(units,source_family=cls.family,destination_family=cls.family,
            expected_case_identities=[identity(i) for i in range(127)],noise_law_sha256=cls.law)

    @classmethod
    def store(cls,i=200,edits=()):
        arrays={(k,t,w):np.zeros((3,cls.grid.support_bin_count),dtype='<f4') for k in ('on','off')
                for t in range(2) for w in core.M37_SPECTRAL_WIDTHS}
        for k,t,w,q,v in edits:arrays[k,t,w][:,q+9]=v
        return ScoreStore(arrays,{'context_sha256':cls.family.context_sha256,
            'case_identity':identity(i),'source_domain':'deterministic-score-fixture'})

    def factory(self,peaks=None,peak_snr=6.,on=None,corrupt=None):
        factors=self.on if on is None else on
        def create(records):
            signatures={}
            for r in records:
                entries=[]
                for e in r['active_epochs_zero_based']:
                    predicted=_predicted_midpoint_hz(r['carrier_hz'],factors[r['template_index'],e*16:(e+1)*16])/1e6
                    peak=predicted if peaks is None else peaks(r,e)
                    snr=peak_snr(r,e) if callable(peak_snr) else peak_snr
                    entries.append({'epoch_zero_based':e,'predicted_mid_mhz':predicted,
                        'peak_frequency_mhz':peak,'peak_snr':snr,'offset_from_prediction_hz':(peak-predicted)*1e6})
                signatures[r['record_id']]=entries
            if corrupt:corrupt(signatures)
            return signatures,{'signatures_sha256':digest(signatures),'domain':'deterministic-signature-fixture'}
        return create

    def run_case(self,edits=(),*,factory=None,on=None,off=None,caps=None):
        return run_fixture(self.family,self.store(edits=edits),self.threshold,case_identity=identity(200),
            noise_law_sha256=self.law,on_factors=self.on if on is None else on,
            off_factors=self.off if off is None else off,receiver_factory=factory or self.factory(on=on),caps=caps)

    def dispositions(self,result):return [d['physical_disposition'] for d in result['decisions']]

    def test_empty_full_chain_is_complete_without_survivor(self):
        r=self.run_case();self.assertTrue(r['complete']);self.assertEqual(r['clusters'],[]);self.assertEqual(r['decisions'],[])

    def test_exact_off_wins_and_all_later_evidence_is_preserved(self):
        r=self.run_case([('on',0,1,4,(20,20,0)),('off',0,1,4,(20,20,0))])
        self.assertEqual(self.dispositions(r),['rfi_veto_matched_off_same_hypothesis'])
        self.assertTrue(r['adjacent_off'][0]['vetoed']);self.assertEqual(len(r['receiver_alias']),1)
        self.assertEqual(len(r['retention']['retained']['off']),1)

    def test_local_off_different_template_width_carrier_is_veto(self):
        r=self.run_case([('on',0,1,2,(20,20,0)),('off',1,3,3,(20,20,0))])
        self.assertEqual(self.dispositions(r),['rfi_veto_local_off_track'])
        self.assertIsNone(r['matched_off'][0]['same_hypothesis_witness_id'])

    def test_literal_track_exact_20_is_inclusive(self):
        r=self.run_case([('on',0,1,2,(20,20,0)),('off',1,3,4,(20,20,0))])
        self.assertEqual(r['matched_off'][0]['local_matches'][0]['maximum_track_distance_hz'],20.)
        self.assertEqual(self.dispositions(r),['rfi_veto_local_off_track'])

    def test_track_just_above_20_is_not_rounded_into_match(self):
        off=self.off.copy();off[1]=np.nextafter(1.,2.)
        r=self.run_case([('on',0,1,2,(20,20,0)),('off',1,3,4,(20,20,0))],off=off)
        self.assertFalse(r['matched_off'][0]['local_matches'])
        self.assertTrue(r['decisions'][0]['diagnostic_final'])

    def test_every_off_midpoint_is_checked_not_only_anchor(self):
        off=self.off.copy();off[1,-1]=1.5
        r=self.run_case([('on',0,1,2,(20,20,0)),('off',1,3,2,(20,20,0))],off=off)
        self.assertFalse(r['matched_off'][0]['local_matches'])

    def test_adjacent_exact_floor_in_active_epoch_vetoes(self):
        r=self.run_case([('on',0,1,4,(20,20,0)),('off',0,1,4,(5.5,0,0))])
        self.assertEqual(self.dispositions(r),['rfi_veto_single_adjacent_off'])
        self.assertEqual(len(r['retention']['retained']['off']),0)

    def test_adjacent_below_floor_does_not_veto(self):
        below=float(np.nextafter(np.float32(5.5),np.float32(0)))
        r=self.run_case([('on',0,1,4,(20,20,0)),('off',0,1,4,(below,0,0))])
        self.assertTrue(r['decisions'][0]['diagnostic_final'])

    def test_adjacent_ignores_inactive_epoch(self):
        r=self.run_case([('on',0,1,4,(20,20,0)),('off',0,1,4,(0,0,20))])
        self.assertFalse(r['adjacent_off'][0]['vetoed'])

    def test_adjacent_uses_unmasked_value(self):
        r=self.run_case([('on',0,1,4,(20,20,0)),('off',0,1,4,(20,0,0))])
        self.assertTrue(r['adjacent_off'][0]['vetoed'])
        self.assertTrue(any(x['kind']=='off' and x['masked_cells']>0 for x in r['retention']['mask_receipts']))

    def test_cross_component_two_epoch_stationary_alias_vetoes_both(self):
        r=self.run_case([('on',0,1,0,(20,20,0)),('on',1,3,8,(20,20,0))],factory=self.factory(lambda r,e:.0001))
        self.assertEqual(self.dispositions(r),['rfi_veto_receiver_frame_alias']*2)
        self.assertEqual(len(r['clusters']),2)

    def test_single_common_epoch_is_not_receiver_alias(self):
        r=self.run_case([('on',0,1,0,(20,20,0)),('on',1,3,8,(0,20,20))],factory=self.factory(lambda r,e:.0001))
        self.assertTrue(all(x['diagnostic_final'] for x in r['decisions']))

    def test_receiver_snr_5_5_inclusive_and_below_excluded(self):
        edits=[('on',0,1,0,(20,20,0)),('on',1,3,8,(20,20,0))]
        yes=self.run_case(edits,factory=self.factory(lambda r,e:.0001,5.5))
        no=self.run_case(edits,factory=self.factory(lambda r,e:.0001,np.nextafter(5.5,0.)))
        self.assertTrue(all(x['matches'] for x in yes['receiver_alias']))
        self.assertTrue(all(not x['matches'] for x in no['receiver_alias']))

    def test_receiver_literal_20_boundary_and_next_float(self):
        edits=[('on',0,1,0,(20,20,0)),('on',1,3,4,(20,20,0))]
        def peaks(r,e):return 0. if r['template_index']==0 else 20/1e6
        yes=self.run_case(edits,factory=self.factory(peaks))
        self.assertTrue(all(x['matches'] for x in yes['receiver_alias']))
        self.assertEqual(yes['receiver_alias'][0]['matches'][0]['shared_epochs'][0]['delta_hz'],20.)
        def beyond(r,e):return 0. if r['template_index']==0 else np.nextafter(20/1e6,np.inf)
        no=self.run_case(edits,factory=self.factory(beyond));self.assertTrue(all(not x['matches'] for x in no['receiver_alias']))

    def test_same_component_peaks_do_not_alias_each_other(self):
        r=self.run_case([('on',0,1,2,(20,20,0)),('on',1,3,4,(20,20,0))],factory=self.factory(lambda r,e:.0001))
        self.assertEqual(len(r['clusters']),1);self.assertTrue(all(not x['matches'] for x in r['receiver_alias']))

    def test_transitive_component_preserves_all_members(self):
        r=self.run_case([('on',0,1,q,(20,20,0)) for q in (0,2,4)])
        self.assertEqual(len(r['clusters']),1);self.assertEqual(r['clusters'][0]['member_count'],3)
        self.assertEqual(len(r['clusters'][0]['diagnostic_final_ids']),3)

    def test_earlier_off_veto_precedes_alias_but_both_evidence_retained(self):
        r=self.run_case([('on',0,1,0,(20,20,0)),('off',0,1,0,(20,20,0)),('on',1,3,8,(20,20,0))],
            factory=self.factory(lambda r,e:.0001))
        self.assertEqual(self.dispositions(r),['rfi_veto_matched_off_same_hypothesis','rfi_veto_receiver_frame_alias'])
        self.assertTrue(all(x['matches'] for x in r['receiver_alias']))

    def test_all_off_witnesses_retained_and_best_by_score_then_order(self):
        r=self.run_case([('on',0,1,4,(20,20,0)),('off',1,3,3,(21,21,0)),('off',1,5,5,(22,22,0))])
        evidence=r['matched_off'][0];self.assertEqual(evidence['matched_local_count'],2)
        best=next(x for x in r['retention']['retained']['off'] if x['spectral_width_channels']==5)
        self.assertEqual(evidence['best_local_witness']['record_id'],best['record_id'])

    def test_indexed_off_matches_equal_literal_all_pairs(self):
        edits=[('on',t,w,q,(20,20,0)) for t,w,q in ((0,1,0),(0,3,3),(1,9,8))]
        edits += [('off',t,w,q,(20,20,0)) for t,w,q in ((1,5,1),(0,17,5),(1,33,8))]
        r=self.run_case(edits)
        off=r['retention']['retained']['off']
        for on,ev in zip(r['retention']['retained']['on'],r['matched_off'],strict=True):
            expected={x['record_id'] for x in off if max(abs(on['carrier_hz']*self.off[on['template_index']]-x['carrier_hz']*self.off[x['template_index']]))<=20}
            self.assertEqual({x['record_id'] for x in ev['local_matches']},expected)

    def test_indexed_alias_matches_equal_literal_cross_component_pairs(self):
        edits=[('on',t,w,q,(20,20,0)) for t,w,q in ((0,1,0),(0,3,3),(1,9,8))]
        r=self.run_case(edits,factory=self.factory(lambda row,e: .000095 if row['proxy_carrier_index']!=8 else .000105))
        components={x['record_id']:x['component_sha256'] for x in r['receiver_alias']};s=r['receiver_signatures']
        for row in r['receiver_alias']:
            rid=row['record_id'];expected=set()
            for oid,entries in s.items():
                if components[oid]==components[rid]:continue
                common=sum(a['epoch_zero_based']==b['epoch_zero_based'] and a['peak_snr']>=5.5 and b['peak_snr']>=5.5 and
                    abs((a['peak_frequency_mhz']-b['peak_frequency_mhz'])*1e6)<=20 for a in s[rid] for b in entries)
                if common>=2:expected.add(oid)
            self.assertEqual({x['record_id'] for x in row['matches']},expected)

    def test_missing_signature_epoch_rejected_with_upstream_preserved(self):
        def corrupt(s):next(iter(s.values())).pop()
        with self.assertRaises(IncompletePhysical) as caught:
            self.run_case([('on',0,1,4,(20,20,0))],factory=self.factory(corrupt=corrupt))
        self.assertFalse(caught.exception.evidence['complete']);self.assertTrue(caught.exception.evidence['retention']['complete'])

    def test_self_consistent_wrong_midpoint_rejected(self):
        def corrupt(s):
            for row in next(iter(s.values())):
                row['predicted_mid_mhz']+=1e-7;row['offset_from_prediction_hz']=(row['peak_frequency_mhz']-row['predicted_mid_mhz'])*1e6
        with self.assertRaisesRegex(IncompletePhysical,'midpoint differs'):
            self.run_case([('on',0,1,4,(20,20,0))],factory=self.factory(corrupt=corrupt))

    def test_oversized_receiver_neighborhood_rejected(self):
        with self.assertRaises(IncompletePhysical):
            self.run_case([('on',0,1,4,(20,20,0))],factory=self.factory(lambda r,e:.0003))

    def test_off_capacity_failure_keeps_full_upstream(self):
        edits=[('on',0,1,4,(20,20,0)),('off',0,3,3,(20,20,0)),('off',1,5,5,(20,20,0))]
        with self.assertRaisesRegex(IncompletePhysical,'OFF candidate') as caught:self.run_case(edits,caps={'off_candidate_visits':1})
        self.assertEqual(len(caught.exception.evidence['retention']['retained']['off']),2)

    def test_alias_bucket_capacity_fails_closed(self):
        with self.assertRaisesRegex(IncompletePhysical,'bucket-entry'):
            self.run_case([('on',0,1,0,(20,20,0)),('on',1,3,8,(20,20,0))],caps={'alias_bucket_entries':1})

    def test_identity_partition_capacity_fails_closed(self):
        with self.assertRaisesRegex(IncompletePhysical,'track-comparison'):
            self.run_case([('on',0,1,q,(20,20,0)) for q in (0,1,2)],caps={'identity_track_comparisons':1})

    def test_alias_visit_capacity_fails_closed(self):
        with self.assertRaisesRegex(IncompletePhysical,'Alias candidate'):
            self.run_case([('on',0,1,0,(20,20,0)),('on',1,3,8,(20,20,0))],factory=self.factory(lambda r,e:.0001),caps={'alias_candidate_visits':1})

    def test_evidence_byte_capacity_keeps_crossing_record(self):
        with self.assertRaisesRegex(IncompletePhysical,'byte capacity') as caught:
            self.run_case([('on',0,1,4,(20,20,0))],caps={'canonical_bytes_per_stage':1})
        self.assertIn('first_capacity_crossing_evidence',caught.exception.evidence)

    def test_invalid_factors_and_cap_increase_rejected(self):
        off=self.off.copy();off[0,0]=np.nan
        with self.assertRaises(ValueError):self.run_case(off=off)
        with self.assertRaises(ValueError):self.run_case(caps={'records':10001})

    def test_no_scientific_authority_and_result_hash_is_complete(self):
        r=self.run_case([('on',0,1,4,(20,20,0))]);sha=r.pop('result_sha256');self.assertEqual(digest(r),sha)
        self.assertFalse(r['legacy_certificates_issued']);self.assertFalse(r['scientific_candidate_selection_authorized'])
        self.assertFalse(r['telescope_admission_authorized']);self.assertFalse(r['decisions'][0]['scientific_candidate'])

    def test_receiver_callback_cannot_mutate_upstream_records(self):
        factory=self.factory()
        def receiver(records):
            result=factory(records)
            records[0]['stack_snr']=-999
            return result
        r=self.run_case([('on',0,1,4,(20,20,0))],factory=receiver)
        self.assertGreater(r['retention']['retained']['on'][0]['stack_snr'],10)

    def test_receiver_callback_late_score_change_fails_closed(self):
        store=self.store(edits=[('on',0,1,4,(20,20,0))]);factory=self.factory()
        def receiver(records):
            result=factory(records);store.expected_ids['off',1,129]='e'*64;return result
        with self.assertRaisesRegex(IncompletePhysical,'identity changed'):
            run_fixture(self.family,store,self.threshold,case_identity=identity(200),noise_law_sha256=self.law,
                on_factors=self.on,off_factors=self.off,receiver_factory=receiver)

    def test_partial_off_witnesses_survive_visit_cap(self):
        edits=[('on',0,1,4,(20,20,0)),('off',0,3,3,(20,20,0)),('off',1,5,5,(20,20,0))]
        with self.assertRaises(IncompletePhysical) as caught:self.run_case(edits,caps={'off_candidate_visits':1})
        r=caught.exception.evidence;self.assertEqual(r['off_candidate_visits'],2)
        self.assertEqual(len(r['current_off_query']['partial_matches']),1)

    def test_late_provenance_change_preserves_original_upstream_receipt(self):
        store=self.store(edits=[('on',0,1,4,(20,20,0))]);factory=self.factory()
        def receiver(records):
            result=factory(records);store.provenance['case_identity']='e'*64;return result
        with self.assertRaises(IncompletePhysical) as caught:
            run_fixture(self.family,store,self.threshold,case_identity=identity(200),noise_law_sha256=self.law,
                on_factors=self.on,off_factors=self.off,receiver_factory=receiver)
        retained=caught.exception.evidence['retention']
        self.assertEqual(retained['source_provenance']['case_identity'],identity(200))
        self.assertEqual(retained['result_sha256'],digest({k:v for k,v in retained.items() if k!='result_sha256'}))


if __name__=='__main__':unittest.main()
