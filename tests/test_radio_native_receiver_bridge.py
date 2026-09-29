"""Post-closure regression: fixed signatures, no native replay and no RNG."""
import copy
import hashlib
from types import SimpleNamespace
import unittest
from seti_repeater import search_v0p6 as core
from seti_repeater.whole_cadence_physical_radio import native_receiver_receipt
from seti_repeater.whole_cadence_reference_radio import digest


class NativeReceiptBridgeTests(unittest.TestCase):
    def setUp(self):
        self.context=SimpleNamespace(identity='a'*64,factor_contract=SimpleNamespace(identity='b'*64))
        self.sources={'epoch1_on':'c'*64}
        self.signatures={'d'*64:[{'epoch_zero_based':0,'predicted_mid_mhz':1411.0,
            'peak_frequency_mhz':1411.00001,'peak_snr':6.,'offset_from_prediction_hz':10.}]}
        self.receipt={'schema':'radio-receiver-native-receiver-v1','context_sha256':self.context.identity,
            'receiver_factor_contract_sha256':self.context.factor_contract.identity,'source_ids':self.sources,
            'queries':[{'fixed_test_fixture':True}],
            'signatures_sha256':hashlib.sha256(core.canonical_json_bytes(self.signatures)).hexdigest()}

    def call(self):return native_receiver_receipt(self.signatures,self.receipt,self.context,self.sources)

    def test_native_newline_hash_verified_then_distinct_hash_bridged(self):
        before=copy.deepcopy(self.receipt);r=self.call()
        self.assertNotEqual(before['signatures_sha256'],digest(self.signatures))
        self.assertEqual(r['signatures_sha256'],digest(self.signatures))
        self.assertEqual(r['source_receipt'],before);self.assertEqual(self.receipt,before)
        self.assertEqual(r['source_receipt_sha256_native_bytes'],hashlib.sha256(core.canonical_json_bytes(before)).hexdigest())
        self.assertFalse(r['scientific_admission_authorized'])

    def test_already_relabelled_compact_hash_is_rejected(self):
        self.receipt['signatures_sha256']=digest(self.signatures)
        with self.assertRaises(ValueError):self.call()

    def test_tampered_signature_is_rejected(self):
        self.signatures['d'*64][0]['peak_snr']=7.
        with self.assertRaises(ValueError):self.call()

    def test_wrong_context_factor_source_or_schema_rejected(self):
        for key,value in [('context_sha256','e'*64),('receiver_factor_contract_sha256','e'*64),
                          ('source_ids',{'epoch1_on':'e'*64}),('schema','fixture')]:
            original=copy.deepcopy(self.receipt);self.receipt[key]=value
            with self.assertRaises(ValueError):self.call()
            self.receipt=original

    def test_empty_mapping_keeps_both_byte_domains_distinct(self):
        self.signatures={};self.receipt['signatures_sha256']=hashlib.sha256(core.canonical_json_bytes({})).hexdigest()
        r=self.call();self.assertEqual(r['signatures_sha256'],digest({}))
        self.assertNotEqual(r['signatures_sha256'],r['source_receipt']['signatures_sha256'])

    def test_bridge_source_receipt_is_detached_from_mutable_caller(self):
        r=self.call();self.receipt['queries'][0]['fixed_test_fixture']=False
        self.assertTrue(r['source_receipt']['queries'][0]['fixed_test_fixture'])


if __name__=='__main__':unittest.main()
