"""Compact evidence integrity and prospective ceiling risks, using retained bytes."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from radio_receiver_adapter_common import ROOT,context
from radio_whole_cadence_compact_fixture import inputs
from seti_repeater import whole_cadence_compact_radio as c
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_reference_radio import digest
from seti_repeater.injection_m43r import ScoreStore
from seti_repeater.whole_cadence_archive_radio import npz_bytes,decode_npz


class CompactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx,cls.binding,cls.base,cls.paths=inputs(0)
        cls.proposal=(ROOT/'config/radio_whole_cadence_null_proposal_20260928.json').read_bytes()

    def setUp(self):self.parts=dict(self.base);self.binding=dict(type(self).binding)

    def audit(self,cap=4*c.MIB,ctx=None):
        return c.audit(ctx or self.ctx,self.binding,self.parts,
            expected_sha256s={k:hashlib.sha256(v).hexdigest() for k,v in self.parts.items()},byte_cap=cap)

    def edit(self,name,change,receipt=None):
        r=json.loads(self.parts[name]);change(r)
        if receipt:r.pop(receipt);r[receipt]=digest(r)
        self.parts[name]=canonical(r)

    def test_fixed_phase_totals_do_not_extend_proposal(self):
        b=c.phase_budget(self.proposal)
        self.assertEqual(b['total_milliseconds'],7200000);self.assertEqual(b['total_evidence_bytes'],1024**3)
        self.assertEqual(len(b['cases']),151);self.assertFalse(b['new_scientific_allocation_charged'])
        self.assertEqual(sum(x['reserved_artifact_bytes'] for x in b['cases']),940*c.MIB)

    def test_engineering_receipt_cannot_relabel_retained_law(self):
        self.edit('renderer.json',lambda r:r.update(schema='radio-engineering-gaussian-native-receipt-v1',
            scientific_allocation_charged=False),receipt='receipt_sha256')
        with self.assertRaisesRegex(ValueError,'cannot claim scientific law'):
            self.audit()

    def test_changed_phase_cap_rejected(self):
        b=c.phase_budget(self.proposal);b['cases'][0]['reserved_artifact_bytes']+=1
        with self.assertRaisesRegex(ValueError,'budget differs'):c.reservation(self.proposal,b,b['cases'][0]['case_identity'])

    def test_unknown_case_has_no_budget(self):
        with self.assertRaisesRegex(ValueError,'absent'):c.reservation(self.proposal,c.phase_budget(self.proposal),'a'*64)

    def test_changed_proposal_cannot_allocate(self):
        with self.assertRaisesRegex(ValueError,'immutable'):c.phase_budget(self.proposal+b' ')

    def test_missing_compact_artifact_rejected(self):
        self.parts.pop('maximum.json')
        with self.assertRaisesRegex(ValueError,'inventory'):self.audit()

    def test_artifact_pin_mismatch_before_numpy(self):
        pins={k:hashlib.sha256(v).hexdigest() for k,v in self.parts.items()};pins['scores.npz']='a'*64
        with patch.object(c,'decode_npz',side_effect=AssertionError('No array decoding')):
            with self.assertRaisesRegex(ValueError,'independent pin'):c.audit(self.ctx,self.binding,self.parts,expected_sha256s=pins,byte_cap=4*c.MIB)

    def test_case_cap_rejected_before_numpy(self):
        with patch.object(c,'decode_npz',side_effect=AssertionError('No array decoding')):
            with self.assertRaisesRegex(ValueError,'capacity'):self.audit(cap=1)

    def test_wrong_context_rejected(self):
        with self.assertRaisesRegex(ValueError,'context/source'):self.audit(ctx=context('validation'))

    def test_wrong_plan_rejected(self):
        self.binding['plan_sha256']='a'*64
        with self.assertRaisesRegex(ValueError,'Renderer'):self.audit()

    def test_wrong_noise_law_rejected(self):
        self.binding['noise_law_sha256']='a'*64
        with self.assertRaisesRegex(ValueError,'source metadata'):self.audit()

    def test_missing_row_receipt_is_not_complete(self):
        self.edit('renderer.json',lambda r:r['row_receipts'][0]['rows'].pop(),receipt='receipt_sha256')
        with self.assertRaisesRegex(ValueError,'16-row'):self.audit()

    def test_reordered_scan_receipts_rejected(self):
        self.edit('renderer.json',lambda r:r['row_receipts'].reverse(),receipt='receipt_sha256')
        with self.assertRaisesRegex(ValueError,'ordered source'):self.audit()

    def test_rehashed_source_hash_cannot_impersonate_original_identity(self):
        self.edit('sources.json',lambda r:r['sources']['epoch1_on'].update(normalized_sha256='a'*64))
        with self.assertRaisesRegex(ValueError,'source identity'):self.audit()

    def test_missing_last_vector_is_not_empty(self):
        self.edit('scores.json',lambda r:r['vectors'].pop())
        with self.assertRaisesRegex(ValueError,'vector inventory'):self.audit()

    def test_duplicate_vector_is_not_complete(self):
        def duplicate(r):r['vectors'][-1]=r['vectors'][0]
        self.edit('scores.json',duplicate)
        with self.assertRaisesRegex(ValueError,'vector inventory'):self.audit()

    def test_changed_vector_identity_rejected(self):
        self.edit('scores.json',lambda r:r['vectors'][-1].update(identity='a'*64))
        with self.assertRaisesRegex(ValueError,'vector identity'):self.audit()

    def test_changed_score_bytes_rejected(self):
        meta=json.loads(self.parts['scores.json']);keys=[v['npz_key'] for v in meta['vectors']]
        arrays=decode_npz(self.parts['scores.npz'],expected_keys=keys,expected_shape=(3,99),maximum_decoded_bytes=1296*3*99*4)
        key=keys[-1];arrays[key]=arrays[key].copy();arrays[key][2,-1]+=1
        self.parts['scores.npz']=npz_bytes(arrays)
        with self.assertRaisesRegex(ValueError,'vector identity'):self.audit()

    def test_rehashed_cache_ancestry_still_checked(self):
        meta=json.loads(self.parts['scores.json']);vectors=meta['vectors'];keys=[v['npz_key'] for v in vectors]
        arrays=decode_npz(self.parts['scores.npz'],expected_keys=keys,expected_shape=(3,99),maximum_decoded_bytes=1296*3*99*4)
        meta['provenance']['native_caches'][-1]['width']=1
        store=ScoreStore({tuple(v['key']):arrays[v['npz_key']] for v in vectors},meta['provenance'])
        for v in vectors:v['identity']=store.expected_ids[tuple(v['key'])]
        self.parts['scores.json']=canonical(meta)
        with self.assertRaisesRegex(ValueError,'Cache source ancestry'):self.audit()

    def test_rehashed_maximum_value_is_recomputed_from_scores(self):
        self.edit('maximum.json',lambda r:r['maximum'].update(value=r['maximum']['value']+1),receipt='receipt_sha256')
        with self.assertRaisesRegex(ValueError,'score-derived'):self.audit()

    def test_rehashed_mask_receipt_is_recomputed_from_scores(self):
        self.edit('maximum.json',lambda r:r['mask_receipts'][-1].update(sha256='a'*64),receipt='receipt_sha256')
        with self.assertRaisesRegex(ValueError,'score-derived'):self.audit()

    def test_returned_budget_cannot_mutate_future_phase_constants(self):
        b=c.phase_budget(self.proposal);b['phases']['calibration']['milliseconds_per_case']=1
        b['overhead']['failure_and_summary_bytes']=0
        fresh=c.phase_budget(self.proposal)
        self.assertEqual(fresh['phases']['calibration']['milliseconds_per_case'],40000)
        self.assertEqual(fresh['overhead']['failure_and_summary_bytes'],76*c.MIB)
        with self.assertRaisesRegex(ValueError,'budget differs'):c.reservation(self.proposal,b,b['cases'][0]['case_identity'])


if __name__=='__main__':unittest.main()
