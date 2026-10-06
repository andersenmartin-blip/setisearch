"""Manufactured driver refusal/read-boundary controls; never calls snapshot."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('capture',Path(__file__).with_name('capture_self.py'))
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)


class CaptureBoundary(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name)
        for name in ('mapping.py','capture_self.py'): (self.base/name).write_bytes(Path(__file__).with_name(name).read_bytes())
        self.freeze={'status':'SOURCE_PLUS_ONE_ADMINISTRATIVE_SELF_SNAPSHOT_NO_TARGET_AUTHORITY',
                     'authority_parent':c.AUTHORITY,'limits':dict(c.LIMITS),
                     'source_files':{name:c.pin((self.base/name).read_bytes()) for name in ('mapping.py','capture_self.py')}}

    def tearDown(self): self.temp.cleanup()

    def preflight(self,digest=None):
        raw=c.canonical(self.freeze);(self.base/'SOURCE_FREEZE.json').write_bytes(raw)
        with patch.object(c,'HERE',self.base): return c.preflight(digest or c.pin(raw)['sha256'],c.Budget())

    def test_frozen_stdlib_component_only_no_snapshot(self):
        module,pin=self.preflight();self.assertFalse(hasattr(module,'launch'))
        self.assertEqual(len(pin['sha256']),64)

    def test_wrong_freeze_hash_refused(self):
        with self.assertRaisesRegex(ValueError,'read-back freeze'): self.preflight('0'*64)

    def test_source_tampering_refused(self):
        (self.base/'mapping.py').write_bytes(b'changed')
        with self.assertRaises(ValueError): self.preflight()

    def test_missing_driver_from_freeze_refused(self):
        del self.freeze['source_files']['capture_self.py']
        with self.assertRaises(ValueError): self.preflight()

    def test_changed_authority_refused(self):
        self.freeze['authority_parent']='0'*40
        with self.assertRaises(ValueError): self.preflight()

    def test_changed_limit_refused(self):
        self.freeze['limits']['explicit_read_bytes']*=2
        with self.assertRaises(ValueError): self.preflight()

    def test_source_symlink_refused(self):
        target=self.base/'mapping.py';other=self.base/'elsewhere';target.rename(other);target.symlink_to(other)
        with self.assertRaises(ValueError): self.preflight()

    def test_path_traversal_refused(self):
        self.freeze['source_files']['../foreign']=self.freeze['source_files']['mapping.py']
        with self.assertRaises(ValueError): self.preflight()

    def test_short_proc_reads_join_until_eof(self):
        with patch.object(c.os,'open',return_value=55),patch.object(c.os,'close') as close,patch.object(c.os,'read',side_effect=[b'one\n',b'two\n',b'']):
            budget=c.Budget();self.assertEqual(c.read_proc(5,'maps',100,budget),b'one\ntwo\n')
            self.assertEqual(budget.read,8);close.assert_called_once_with(55)

    def test_proc_exact_cap_requires_eof(self):
        with patch.object(c.os,'open',return_value=55),patch.object(c.os,'close'),patch.object(c.os,'read',side_effect=[b'1234',b'']):
            self.assertEqual(c.read_proc(5,'maps',4,c.Budget()),b'1234')

    def test_proc_one_byte_over_cap_refused(self):
        with patch.object(c.os,'open',return_value=55),patch.object(c.os,'close') as close,patch.object(c.os,'read',side_effect=[b'1234',b'5']):
            with self.assertRaisesRegex(ValueError,'proc body cap'): c.read_proc(5,'maps',4,c.Budget())
            close.assert_called_once_with(55)

    def test_proc_read_failure_still_closes_fd(self):
        with patch.object(c.os,'open',return_value=55),patch.object(c.os,'close') as close,patch.object(c.os,'read',side_effect=PermissionError(13,'fixture denied')):
            with self.assertRaises(PermissionError): c.read_proc(5,'maps',4,c.Budget())
            close.assert_called_once_with(55)

    def test_arbitrary_proc_name_refused_before_open(self):
        with patch.object(c.os,'open') as open_:
            with self.assertRaises(ValueError): c.read_proc(5,'mem',4,c.Budget())
            open_.assert_not_called()

    def test_read_charge_before_syscall(self):
        with patch.dict(c.LIMITS,{'explicit_read_bytes':1}),patch.object(c.os,'read') as read:
            with self.assertRaises(ValueError): c.Budget().body(55,2)
            read.assert_not_called()

    def test_existing_artifact_not_overwritten(self):
        p=self.base/'foreign';p.write_bytes(b'retain')
        with self.assertRaises(FileExistsError): c.Budget().write(p,b'changed')
        self.assertEqual(p.read_bytes(),b'retain')

    def test_artifact_cap_before_open(self):
        p=self.base/'absent'
        with patch.dict(c.LIMITS,{'artifact_bytes':1}):
            with self.assertRaises(ValueError): c.Budget().write(p,b'two')
        self.assertFalse(p.exists())

    def test_wall_cap_refused(self):
        b=c.Budget();b.start-=21
        with self.assertRaises(ValueError): b.check()


if __name__=='__main__': unittest.main(verbosity=2)
