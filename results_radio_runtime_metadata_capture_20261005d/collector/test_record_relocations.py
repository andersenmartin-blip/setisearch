"""Inert fake pip target layouts; no scientific imports or executable launches."""
import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).resolve().parent
SPEC=importlib.util.spec_from_file_location('collector_relocation_inert',ROOT/'collect_runtime_identity.py')
collector=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)


class Item:
    def __init__(self,path,raw):
        self.path=path
        self.size=len(raw)
        value=base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).rstrip(b'=').decode()
        self.hash=SimpleNamespace(mode='sha256',value=value)
    def __str__(self):
        return self.path


class RelocationTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.venv=Path(self.directory.name)/'venv'
        self.site=self.venv/'lib/python3.12/site-packages'
        (self.site/'bin').mkdir(parents=True)
        self.items=[];rows=[]
        for index,name in enumerate(('f2py','numpy-config')):
            raw=(b'# INERT SCRIPT BYTES NEVER EXECUTED '+bytes([65+index])*224)[:224]
            path=self.site/'bin'/name;path.write_bytes(raw);path.chmod(0o755)
            item=Item('../../bin/'+name,raw);self.items.append(item)
            rows.append({'record_path':str(item),'declared_location':str((self.site/str(item)).resolve()),
                         'actual_installed_path':str(path),'record_hash':'sha256='+item.hash.value,
                         'record_size':item.size,'actual_pin':{'path':str(path),'bytes':len(raw),
                          'sha256':hashlib.sha256(raw).hexdigest(),'mode':0o755}})
        self.input={'schema':'seti-exact-target-record-relocations-v1','distribution':'numpy',
                    'distribution_version':'2.3.5','venv_root':str(self.venv),'rows':rows}
        self.distribution=SimpleNamespace(files=self.items,version='2.3.5',
                                          locate_file=lambda item:self.site/str(item))

    def tearDown(self):
        self.directory.cleanup()

    def inventory(self,reader=None):
        reader=collector.BoundedReader() if reader is None else reader
        return collector.distribution_inventory('numpy',self.distribution,self.venv,reader,self.input)

    def test_exact_two_missing_record_paths_have_full_verified_relocation_witnesses(self):
        reader=collector.BoundedReader()
        result=self.inventory(reader)
        self.assertEqual(result['verified_generated_script_relocations'],2)
        self.assertEqual(reader.charged_bytes,448)
        for row in result['files']:
            self.assertNotEqual(row['declared_located_path'],row['located_path'])
            self.assertTrue(row['record_relocation']['whole_script_bytes_verified'])
            self.assertEqual(row['record_relocation']['actual_pin']['bytes'],224)
        self.assertEqual(result['files'],self.inventory()['files'])
        self.assertEqual(result['declared_native_elf'],[])

    def test_current_record_hash_or_size_mutation_refused_before_script_read(self):
        for field,value in (('hash',SimpleNamespace(mode='sha256',value='0'*43)),('size',225)):
            original=getattr(self.items[0],field);setattr(self.items[0],field,value)
            reader=collector.BoundedReader()
            with self.assertRaisesRegex(collector.Refusal,'current generated script RECORD row'):
                self.inventory(reader)
            self.assertEqual(reader.charged_bytes,0)
            setattr(self.items[0],field,original)

    def test_actual_script_content_or_mode_mutation_refused(self):
        path=self.site/'bin/f2py';original=path.read_bytes()
        path.write_bytes(b'Z'*224)
        with self.assertRaisesRegex(collector.Refusal,'whole bytes differ'):
            self.inventory()
        path.write_bytes(original);path.chmod(0o644)
        with self.assertRaisesRegex(collector.Refusal,'whole bytes differ'):
            self.inventory()

    def test_duplicate_unknown_unused_and_wrong_path_rows_fail_closed(self):
        changed=copy.deepcopy(self.input);changed['rows'][1]=changed['rows'][0]
        with self.assertRaisesRegex(collector.Refusal,'unknown or duplicate'):
            collector._validate_record_relocations(changed,self.venv)
        changed=copy.deepcopy(self.input);changed['rows'][0]['record_path']='../../bin/unknown'
        with self.assertRaisesRegex(collector.Refusal,'unknown or duplicate'):
            collector._validate_record_relocations(changed,self.venv)
        changed=copy.deepcopy(self.input);changed['rows'][0]['actual_installed_path']=str(self.venv/'other')
        with self.assertRaisesRegex(collector.Refusal,'path differs'):
            collector._validate_record_relocations(changed,self.venv)
        self.distribution.files=self.items[:1]
        with self.assertRaisesRegex(collector.Refusal,'row was unused'):
            self.inventory()

    def test_unknown_or_duplicate_distribution_record_does_not_get_generic_fallback(self):
        unknown=Item('../../bin/unknown',b'inert')
        self.distribution.files=[unknown,*self.items]
        with self.assertRaisesRegex(collector.Refusal,'unknown target RECORD relocation'):
            self.inventory()
        self.distribution.files=[self.items[0],self.items[0],self.items[1]]
        with self.assertRaisesRegex(collector.Refusal,'duplicate distribution RECORD path'):
            self.inventory()

    def test_declared_file_or_actual_script_symlink_is_refused(self):
        declared=self.site/str(self.items[0]);declared.parent.mkdir(parents=True)
        declared.write_bytes(b'inert newly appearing declared file')
        with self.assertRaisesRegex(collector.Refusal,'unexpectedly exists'):
            self.inventory()
        declared.unlink()
        actual=self.site/'bin/f2py';actual.unlink();actual.symlink_to(self.site/'bin/numpy-config')
        with self.assertRaisesRegex(collector.Refusal,'namespace alias'):
            self.inventory()

    def test_required_input_read_is_bounded_and_pins_exact_raw_json(self):
        path=Path(self.directory.name)/'relocations.json'
        raw=json.dumps(self.input).encode();path.write_bytes(raw)
        reader=collector.BoundedReader()
        value,pin=collector._read_record_relocations(path,reader,self.venv)
        self.assertEqual(value,self.input)
        self.assertEqual(pin['sha256'],hashlib.sha256(raw).hexdigest())
        self.assertEqual(reader.charged_bytes,len(raw))
        path.write_bytes(b'x'*65537)
        with self.assertRaisesRegex(collector.Refusal,'per-file read cap'):
            collector._read_record_relocations(path,collector.BoundedReader(),self.venv)
        duplicate=json.dumps(self.input)[:-1]+',"schema":"seti-exact-target-record-relocations-v1"}'
        path.write_text(duplicate)
        with self.assertRaisesRegex(collector.Refusal,'duplicate relocation JSON key'):
            collector._read_record_relocations(path,collector.BoundedReader(),self.venv)


if __name__=='__main__':
    unittest.main()
