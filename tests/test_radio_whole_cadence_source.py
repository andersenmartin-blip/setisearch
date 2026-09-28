"""Reject codec metadata mismatches before the first new native row read."""
import copy
import unittest
from radio_receiver_adapter_common import context
from seti_repeater.whole_cadence_source_radio import texture_law, bind_codec_cadence, validate_codec_binding
from seti_repeater.whole_cadence_reference_radio import digest


class CodecBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c=context('validation');cls.law=texture_law();w=cls.c.native_window
        cls.receipt={'archive_sha256':cls.law['archive_sha256'],'member_sha256':cls.law['member_sha256'],
            'role':'validation','window_identity':w['identity'],'archive_interval':w['archive_interval'],
            'decoded_row_sha256s':['a'*64]*16,'runtime_receipt_sha256':'b'*64}

    def reject(self,**changes):
        calls=[]
        def reader(row):calls.append(row);raise AssertionError('Must reject metadata before row')
        args=dict(case_identity='c'*64,law=self.law,input_receipt=self.receipt,expected_normalized_row_hashes=['d'*64]*16)
        with self.assertRaises(ValueError):bind_codec_cadence(self.c,reader,**{**args,**changes})
        self.assertFalse(calls)

    def test_gaussian_law_label_rejected(self):
        law={**self.law,'gaussian_noise_law':True};self.reject(law=law)

    def test_claimed_independent_cadences_rejected(self):
        self.reject(law={**self.law,'independent_cadences':True})

    def test_wrong_archive_member_rejected(self):
        self.reject(input_receipt={**self.receipt,'member_sha256':'f'*64})

    def test_wrong_role_rejected(self):
        self.reject(input_receipt={**self.receipt,'role':'calibration'})

    def test_wrong_window_rejected(self):
        self.reject(input_receipt={**self.receipt,'window_identity':'f'*64})

    def test_wrong_interval_rejected(self):
        self.reject(input_receipt={**self.receipt,'archive_interval':[0,65536]})

    def test_missing_decoded_row_rejected(self):
        self.reject(input_receipt={**self.receipt,'decoded_row_sha256s':['a'*64]*15})

    def test_missing_normalized_row_rejected(self):
        self.reject(expected_normalized_row_hashes=['a'*64]*15)

    def test_missing_runtime_pin_rejected(self):
        self.reject(input_receipt={**self.receipt,'runtime_receipt_sha256':None})

    def test_bad_case_identity_rejected(self):self.reject(case_identity='case')

    def test_untyped_native_run_rejected(self):
        with self.assertRaisesRegex(ValueError,'NativeRun'):
            validate_codec_binding(object(),case_identity='a'*64,noise_law_sha256=digest(self.law))


if __name__=='__main__':unittest.main()
