"""Value semantics, independent decoder compatibility, laziness and fault tests."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

import payload


CAP = 2 * 1024**2


def assert_same(test, before, after):
    test.assertIs(type(before), type(after))
    if type(before) is np.ndarray:
        test.assertEqual(before.dtype, after.dtype)
        test.assertEqual(before.dtype.isalignedstruct, after.dtype.isalignedstruct)
        test.assertEqual(before.shape, after.shape)
        test.assertEqual(before.tobytes(order='C'), after.tobytes(order='C'))
    elif isinstance(before, np.generic):
        test.assertEqual(before.dtype, after.dtype)
        test.assertEqual(before.tobytes(), after.tobytes())
    elif type(before) is float:
        test.assertEqual(struct.pack('>d', before), struct.pack('>d', after))
    elif type(before) is dict:
        test.assertEqual(list(before), list(after))
        for key in before:
            assert_same(test, before[key], after[key])
    elif type(before) in (list, tuple):
        test.assertEqual(len(before), len(after))
        for x, y in zip(before, after):
            assert_same(test, x, y)
    else:
        test.assertEqual(before, after)


class PayloadTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name) / 'payload'

    def write(self, value, **kwargs):
        receipt = payload.write_payload(self.folder, value, cap=CAP, **kwargs)
        archive = payload.verify_payload(self.folder, cap=CAP,
                                        expected_semantic_sha256=receipt['semantic_sha256'])
        return receipt, archive

    def test_exact_types_bits_empty_views_scalar_and_reserved_key(self):
        bits = np.array([0x7ff8000000001234, 0x8000000000000000, 0x7ff0000000000000], dtype='>u8')
        value = {'output': {'scores': bits.view('>f8'),
                           'empty': np.empty((0, 4), dtype='<i8'),
                           'transpose': np.arange(24, dtype='>f4').reshape(4, 6).T,
                           'normalization': {'row_power_median': [1., -0., 3.],
                                             'normalization_source_channels': [12, 13, 14]},
                           'tuple': (1, [2, 3], ()),
                           'scalar': np.array(0x80000000, dtype='u4').view('f4')[()],
                           'array_zero_dim': np.array(7, dtype='>i2'),
                           'alias_geometry': {(1, 2, 'source'): np.array([2], dtype='u1')},
                           payload.TAG: ['array', 'ordinary source value']},
                 'truth': {'case_id': 'fixture-identity-only', 'active': [0, 2, 4]},
                 'admission': {'status': 'fixture-metadata-only'},
                 'nan': struct.unpack('>d', bytes.fromhex('7ff8000000004567'))[0],
                 'infinities': [float('inf'), float('-inf')], 'large': 2**100,
                 'inputs': [np.zeros((2, 3), dtype='f4')]}
        receipt, archive = self.write(value)
        assert_same(self, value, archive.materialize())
        self.assertEqual(receipt['payload_bytes'], sum(p.stat().st_size for p in self.folder.iterdir()))
        self.assertEqual(receipt['inventory'], archive.receipt['inventory'])
        self.assertFalse(archive.receipt['scientific_integrity_or_QA_or_admission_established'])
        assert_same(self, value['output']['alias_geometry'][(1, 2, 'source')],
                    archive.load(('output', 'alias_geometry', (1, 2, 'source'))))

    def test_original_normalization_lists_pass_unchanged_independent_qa_decode(self):
        # This is the real frozen independent decoder, not a mirrored decoder.
        qa_path = Path(__file__).resolve().parents[2] / 'analysis/sixscan_burst_20261015/qa.py'
        spec = importlib.util.spec_from_file_location('science_payload_independent_qa', qa_path)
        qa = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(qa)
        qa.np = np

        class Audit:
            def eq(inner, actual, expected, label):
                self.assertEqual(actual, expected, label)

        output = {'normalization': {'row_power_median': [1., -0., 3.],
                                    'normalization_unmasked_counts': [4096] * 16,
                                    'normalization_source_channels': list(range(4096))},
                  'scores': np.arange(30, dtype='f8').reshape(6, 5),
                  'empty_inventory': np.empty((0, 4), dtype='i8')}
        _, archive = self.write({'output': output})
        encoded, lazy_store = archive.qa_decode_pair()
        self.assertIs(type(encoded['normalization']['row_power_median']), list)
        self.assertIs(type(encoded['normalization']['normalization_source_channels']), list)
        self.assertIs(type(encoded['scores']), dict)
        decoded = qa.decode(encoded, lazy_store, Audit())
        assert_same(self, output, decoded)

    def test_verification_and_field_access_do_not_materialize_all_arrays(self):
        value = {'output': {'normalization': [1., 2.], 'a': np.arange(100), 'b': np.arange(200)}}
        receipt = payload.write_payload(self.folder, value, cap=CAP)
        with patch.object(payload.arrays, 'load_typed_array', side_effect=AssertionError('eager array read')):
            archive = payload.verify_payload(self.folder, cap=CAP,
                            expected_semantic_sha256=receipt['semantic_sha256'])
            self.assertEqual(archive.load(('output', 'normalization')), [1., 2.])
            encoded, _ = archive.qa_decode_pair()
            self.assertIn('array_descriptor', encoded['a'])
        with patch.object(payload.arrays, 'load_typed_array', wraps=payload.arrays.load_typed_array) as read:
            assert_same(self, value['output']['b'], archive.load(('output', 'b')))
            self.assertEqual(read.call_count, 1)

    def test_structured_aligned_dtype_and_padding_bytes_survive(self):
        dtype = np.dtype([('flag', 'i1'), ('value', '>f8')], align=True)
        # Deliberately fill padding with nonzero bits, and use a strided view.
        body = bytearray(range(64))
        value = np.ndarray((4,), dtype=dtype, buffer=body)[::2]
        _, archive = self.write({'records': value})
        assert_same(self, value, archive.load(('records',)))

    def test_quota_counts_all_physical_files_and_retains_partial_once_only(self):
        value = {'array': np.arange(2500, dtype='i8')}
        with self.assertRaises((payload.QuotaExceeded, ValueError)):
            payload.write_payload(self.folder, value, cap=300)
        self.assertTrue(self.folder.is_dir())
        self.assertLessEqual(sum(p.stat().st_size for p in self.folder.iterdir()), 300)
        self.assertFalse((self.folder / 'MANIFEST.json').exists())
        with self.assertRaises(FileExistsError):
            payload.write_payload(self.folder, value, cap=CAP)

    def test_manifest_bytes_are_inside_quota(self):
        value = {'a': np.arange(20)}
        receipt, _ = self.write(value)
        second = Path(self.temporary.name) / 'exact'
        exact = payload.write_payload(second, value, cap=receipt['payload_bytes'])
        self.assertEqual(exact['payload_bytes'], receipt['payload_bytes'])
        third = Path(self.temporary.name) / 'short'
        with self.assertRaises(payload.QuotaExceeded):
            payload.write_payload(third, value, cap=receipt['payload_bytes'] - 1)
        self.assertLessEqual(sum(p.stat().st_size for p in third.iterdir()), receipt['payload_bytes'] - 1)

    def test_corruption_inventory_digest_and_expansion_limits_rejected(self):
        _, archive = self.write({'a': np.zeros(8192, dtype='f8')})
        with self.assertRaisesRegex(ValueError, 'producer semantic'):
            payload.verify_payload(self.folder, cap=CAP, expected_semantic_sha256='0' * 64)
        with self.assertRaises(payload.QuotaExceeded):
            payload.verify_payload(self.folder, cap=CAP, max_total_raw_bytes=64)
        with self.assertRaises(payload.QuotaExceeded):
            payload.verify_payload(self.folder, cap=CAP, metadata_unpacked_cap=32)
        (self.folder / 'unexpected').write_bytes(b'')
        with self.assertRaisesRegex(ValueError, 'inventory'):
            payload.verify_payload(self.folder, cap=CAP)
        (self.folder / 'unexpected').unlink()
        asset = self.folder / payload.ARRAY_FILE
        content = bytearray(asset.read_bytes())
        content[40] ^= 1
        asset.write_bytes(content)
        with self.assertRaisesRegex(ValueError, 'hash/length'):
            payload.verify_payload(self.folder, cap=CAP)

    def test_unsupported_or_cyclic_values_fail_before_creating_bundle(self):
        cyclic = []; cyclic.append(cyclic)
        for value in (cyclic, {'bad': np.array([object()])}, {'bad': {1, 2}},
                      {'bad': np.zeros(2, dtype=np.dtype('f4', metadata={'unit': 'Hz'}))}):
            with self.subTest(value_type=type(value).__name__):
                with self.assertRaises((TypeError, ValueError)):
                    payload.write_payload(self.folder, value, cap=CAP)
                self.assertFalse(self.folder.exists())


if __name__ == '__main__':
    unittest.main()
