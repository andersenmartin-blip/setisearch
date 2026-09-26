import unittest
from radio_prospective_design import assert_disjoint_chunks, spectral_chunks


class PayloadSeparationTests(unittest.TestCase):
    def test_half_open_boundary(self):
        self.assertEqual(spectral_chunks([1024,2048],1024),{1})
        self.assertEqual(spectral_chunks([1024,2049],1024),{1,2})

    def test_disjoint_rows_can_still_share_decoded_payload(self):
        with self.assertRaisesRegex(ValueError,'same HDF5'):
            assert_disjoint_chunks([{'archive_interval':[100,200]},{'archive_interval':[800,900]}],1024)
        assert_disjoint_chunks([{'archive_interval':[100,200]},{'archive_interval':[1200,1300]}],1024)


if __name__=='__main__':unittest.main()
