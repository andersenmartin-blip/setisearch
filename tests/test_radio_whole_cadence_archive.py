"""Concrete malformed archive risks, before allocation and native restoration."""
import io
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import warnings
import zipfile
import numpy as np
from seti_repeater import whole_cadence_archive_radio as a
from seti_repeater import whole_cadence_journal_radio as j
from seti_repeater.whole_cadence_reference_radio import digest
from test_radio_whole_cadence_journal import manifest


class ArchiveTests(unittest.TestCase):
    def decode(self,payload):return a.decode_npz(payload,expected_keys=['v'],expected_shape=(3,5),maximum_decoded_bytes=60)

    def test_valid_float32_archive_is_immutable_and_bit_exact(self):
        original=np.arange(15,dtype='<f4').reshape(3,5)
        out=self.decode(a.npz_bytes({'v':original}))['v']
        self.assertFalse(out.flags.writeable);self.assertEqual(out.tobytes(),original.tobytes())

    def test_missing_member_rejected(self):
        with self.assertRaisesRegex(ValueError,'inventory'):self.decode(a.npz_bytes({}))

    def test_extra_member_rejected(self):
        with self.assertRaisesRegex(ValueError,'inventory'):self.decode(a.npz_bytes({'v':np.zeros((3,5),dtype='<f4'),'extra':np.zeros(1)}))

    def test_duplicate_zip_member_rejected(self):
        buffer=io.BytesIO();data=io.BytesIO();np.save(data,np.zeros((3,5),dtype='<f4'))
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',UserWarning)
            with zipfile.ZipFile(buffer,'w') as z:
                z.writestr('v.npy',data.getvalue());z.writestr('v.npy',data.getvalue())
        with self.assertRaisesRegex(ValueError,'inventory'):self.decode(buffer.getvalue())

    def test_zip_expansion_cap_checked_before_numpy(self):
        payload=a.npz_bytes({'v':np.zeros(100000,dtype='<f4')})
        with patch.object(np,'load',side_effect=AssertionError('Must reject before array allocation')):
            with self.assertRaisesRegex(ValueError,'capacity'):self.decode(payload)

    def test_forged_huge_npy_shape_checked_before_numpy(self):
        member=io.BytesIO();np.lib.format.write_array_header_1_0(member,{'descr':'<f4','fortran_order':False,'shape':(10**12,)})
        payload=io.BytesIO()
        with zipfile.ZipFile(payload,'w') as z:z.writestr('v.npy',member.getvalue())
        with patch.object(np,'load',side_effect=AssertionError('Must reject before array allocation')):
            with self.assertRaisesRegex(ValueError,'header'):self.decode(payload.getvalue())

    def test_object_pickle_header_rejected_before_numpy(self):
        payload=a.npz_bytes({'v':np.zeros((3,5),dtype=object)})
        with patch.object(np,'load',side_effect=AssertionError('Must not unpickle')):
            with self.assertRaisesRegex(ValueError,'header'):self.decode(payload)

    def test_fortran_layout_rejected(self):
        payload=a.npz_bytes({'v':np.asfortranarray(np.zeros((3,5),dtype='<f4'))})
        with self.assertRaisesRegex(ValueError,'header'):self.decode(payload)

    def test_nonfinite_values_rejected(self):
        values=np.zeros((3,5),dtype='<f4');values[2,4]=np.nan
        with self.assertRaisesRegex(ValueError,'finite'):self.decode(a.npz_bytes({'v':values}))

    def test_truncated_archive_rejected(self):
        payload=a.npz_bytes({'v':np.zeros((3,5),dtype='<f4')})
        with self.assertRaises(zipfile.BadZipFile):self.decode(payload[:-10])

    def test_unfinished_ledger_cannot_restore_even_complete_files(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);m=manifest(count=1);store=j.DirectoryStore.create(root/'store',m);cp=store.read()
            lease=j.consume(store,expected_revision=cp.revision,expected_manifest_sha256=digest(m),binding=m['cases'][0],
                milliseconds=10000,artifact_bytes=1000,directory=root/'case')
            lease.write_artifact('result.json',b'{}')
            with self.assertRaisesRegex(ValueError,'Completed'):a.read_completed_bytes(store.read(),root/'case',case_index=0)


if __name__=='__main__':unittest.main()
