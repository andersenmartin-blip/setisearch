"""Fresh receipt admission stops before decoding any score arrays."""
import copy
import unittest
from unittest.mock import patch

from seti_repeater import native_v2_parent_radio as parent
from seti_repeater import whole_cadence_compact_radio as compact
from seti_repeater.empty_null_radio import canonical
from seti_repeater.whole_cadence_reference_radio import digest
import test_radio_native_v2_chain as chain_tests


class FreshCompactGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        chain_tests.NativeV2ChainTests.setUpClass()
        cls.context=chain_tests.NativeV2ChainTests.context
        cls.plan=chain_tests.NativeV2ChainTests.plans[0]
        cls.maximum=chain_tests.NativeV2ChainTests.records[0]

    def parts(self,change=None):
        binding={k:v for k,v in parent.case_binding(self.plan).items() if k!='role'}
        renderer={'schema':'radio-native-v2-gaussian-receipt-v1',
            'case_identity':binding['case_identity'],'draw_plan_sha256':binding['plan_sha256'],
            'noise_law_sha256':binding['noise_law_sha256'],'noise_law':copy.deepcopy(parent.LAW),
            'scientific_allocation_charged':False,'normal_calls':96,'row_receipts':[]}
        if change is not None:change(binding,renderer)
        renderer['receipt_sha256']=digest(renderer)
        sources={'schema':'radio-whole-cadence-native-source-archive-v1',
            'case_identity':binding['case_identity'],'context_sha256':binding['context_sha256'],
            'noise_law_sha256':binding['noise_law_sha256'],'sources':{}}
        # Deliberately incomplete metadata and absent arrays. The admission gate
        # must run before source completeness or any NumPy archive decoding.
        parts={'sources.json':canonical(sources),
            'scores.json':canonical({'schema':'radio-whole-cadence-score-archive-v1'}),
            'renderer.json':canonical(renderer),'maximum.json':canonical(self.maximum),
            'scores.npz':b'NO_ARRAYS_UNIT_TEST_STUB'}
        return binding,parts

    def audit(self,change=None):
        binding,parts=self.parts(change)
        with patch.object(compact,'decode_npz',side_effect=AssertionError('No array decoding')):
            return compact.audit(self.context,binding,parts,
                expected_sha256s={k:compact.hashlib.sha256(v).hexdigest() for k,v in parts.items()},
                byte_cap=parent.CASE_BYTES)

    def test_rehashed_wrong_plan_law_or_allocation_cannot_admit_fresh_receipt(self):
        def wrong_plan(binding,renderer):
            binding['plan_sha256']=renderer['draw_plan_sha256']=digest('other-plan')
        def wrong_law(binding,renderer):
            renderer['noise_law']['purpose']='different-purpose'
            binding['noise_law_sha256']=renderer['noise_law_sha256']=digest(renderer['noise_law'])
        def charged(binding,renderer):renderer['scientific_allocation_charged']=True
        for change in (wrong_plan,wrong_law,charged):
            with self.subTest(change=change.__name__),self.assertRaisesRegex(ValueError,'Fresh native-v2 renderer'):
                self.audit(change)

    def test_exact_fresh_receipt_still_requires_complete_source_evidence(self):
        with self.assertRaisesRegex(ValueError,'Complete ordered source'):
            self.audit()


if __name__=='__main__':unittest.main()
