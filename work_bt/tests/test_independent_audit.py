"""Tiny archive corruption checks for the independent BT reviewer only."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
import warnings
import zipfile

PATH=Path(__file__).resolve().parents[1]/'review/audit_bt.py'
SPEC=importlib.util.spec_from_file_location('bt_independent_review_tests',PATH)
a=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(a)

class AuditArchiveTests(unittest.TestCase):
    def build(self,folder,body=b'{"small":1}\n',declared=None,extra=False):
        p=Path(folder)/'sample.zip'
        if declared is None:declared=[dict(path='small.json',bytes=len(body),sha256=hashlib.sha256(body).hexdigest())]
        with zipfile.ZipFile(p,'x',compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr('small.json',body)
            if extra:z.writestr('extra.json',b'{}\n')
            z.writestr('ARCHIVE_MANIFEST.json',a.canonical(dict(schema='SETI_BT_ARCHIVE_MANIFEST_V1',members=declared)))
        return p,declared

    def test_good_archive_independent_crc_hash_and_membership(self):
        with tempfile.TemporaryDirectory() as d:
            p,m=self.build(d);r=a.archive_members(p,m)
            self.assertEqual(r['members'],m);self.assertTrue(r['all_member_CRCs_verified'])

    def test_member_changed_with_valid_crc_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            original=b'{"small":1}\n';m=[dict(path='small.json',bytes=len(original),sha256=hashlib.sha256(original).hexdigest())]
            p,m=self.build(d,b'{"small":2}\n',m)
            with self.assertRaises(ValueError):a.archive_members(p,m)

    def test_unexpected_member_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p,m=self.build(d,extra=True)
            with self.assertRaises(ValueError):a.archive_members(p,m)

    def test_truncated_zip_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p,m=self.build(d)
            with p.open('r+b') as f:f.truncate(p.stat().st_size-12)
            with self.assertRaises((ValueError,zipfile.BadZipFile)):a.archive_members(p,m)

    def test_duplicate_member_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p,m=self.build(d)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',UserWarning)
                with zipfile.ZipFile(p,'a') as z:z.writestr('small.json',b'{"small":1}\n')
            with self.assertRaises(ValueError):a.archive_members(p,m)

    def test_unsafe_names_rejected(self):
        for name in ('../x','/x','a//b','a/./b','a\\b'):
            with self.subTest(name=name),self.assertRaises(ValueError):a.safe_name(name)

if __name__=='__main__':unittest.main()
