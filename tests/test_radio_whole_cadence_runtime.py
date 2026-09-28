"""New published/local runtime-file identity risks using an isolated Git repo."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
import sys
from seti_repeater import whole_cadence_runtime_radio as r
from seti_repeater.empty_null_radio import canonical

class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'src/seti_repeater').mkdir(parents=True);(self.root/'scripts').mkdir()
        (self.root/'src/seti_repeater/a.py').write_text('VALUE=1\n');(self.root/'input.json').write_text('{}')
        self.runtime=self.root/'measured-runtime.bin';self.runtime.write_bytes(b'engineering runtime double')
        self.f={'mode':'ENGINEERING_ONLY','scientific_execution_authorized':False,'python':sys.version,'numpy':np.__version__,
            'repository_python_inventory':['src/seti_repeater/a.py'],
            'code_sha256s':{'src/seti_repeater/a.py':r.sha_file(self.root/'src/seti_repeater/a.py')},
            'input_sha256s':{'input.json':r.sha_file(self.root/'input.json')},
            'runtime_sha256s':{str(self.runtime):r.sha_file(self.runtime)}}
        self.raw=canonical(self.f);(self.root/'freeze.json').write_bytes(self.raw);self.h=hashlib.sha256(self.raw).hexdigest()
        self.env={**os.environ,'GIT_AUTHOR_NAME':'Engineering fixture','GIT_AUTHOR_EMAIL':'fixture@example.invalid',
            'GIT_COMMITTER_NAME':'Engineering fixture','GIT_COMMITTER_EMAIL':'fixture@example.invalid'}
        self.git('init','-q');self.git('add','.');self.git('commit','-qm','fixed fixture');self.commit=self.git('rev-parse','HEAD').strip()
        self.verifier=r.PublishedFreeze(self.root,self.commit,'freeze.json',self.h)
        self.m={'mode':'engineering','execution_binding_sha256':self.h}

    def git(self,*args):return subprocess.check_output(['git',*args],cwd=self.root,env=self.env,text=True)
    def tearDown(self):self.temp.cleanup()

    def test_immutable_published_and_local_bytes_verified(self):
        out=self.verifier.verify(self.m);self.assertEqual(out['published_files'],2);self.assertFalse(out['scientific_execution_authorized'])

    def test_changed_local_code_rejected(self):
        (self.root/'src/seti_repeater/a.py').write_text('VALUE=2\n')
        with self.assertRaisesRegex(ValueError,'executable'):self.verifier.verify(self.m)

    def test_new_repository_module_rejected(self):
        (self.root/'scripts/new.py').write_text('pass\n')
        with self.assertRaisesRegex(ValueError,'inventory'):self.verifier.verify(self.m)

    def test_missing_tracked_code_cannot_be_silently_omitted_from_freeze(self):
        (self.root/'src/seti_repeater/a.py').unlink()
        with self.assertRaisesRegex(ValueError,'sparse inventory'):r.repository_inventory(self.root)

    def test_changed_measured_runtime_file_rejected(self):
        self.runtime.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'Runtime dependency'):self.verifier.verify(self.m)

    def test_published_dependency_not_just_local_file_required(self):
        (self.root/'src/seti_repeater/a.py').write_text('VALUE=2\n');self.git('add','.');self.git('commit','-qm','changed published file')
        with self.assertRaisesRegex(ValueError,'Published dependency'):r.PublishedFreeze(self.root,self.git('rev-parse','HEAD').strip(),'freeze.json',self.h)

    def test_engineering_snapshot_cannot_activate_science(self):
        self.m['mode']='scientific'
        with self.assertRaisesRegex(ValueError,'binding'):self.verifier.verify(self.m)

    def test_unavailable_extension_cannot_enter_loaded_runtime(self):
        self.verifier.freeze['unavailable_unused_extensions']={str(self.runtime):['fixture.so => not found']}
        self.verifier.freeze_identity=r.digest(self.verifier.freeze)
        with patch.object(r,'loaded_files',return_value={str(self.runtime)}):
            with self.assertRaisesRegex(ValueError,'unavailable optional'):self.verifier.verify(self.m)

    def test_unavailable_unloaded_extension_is_explicit_not_available(self):
        self.verifier.freeze['unavailable_unused_extensions']={str(self.runtime):['fixture.so => not found']}
        self.verifier.freeze_identity=r.digest(self.verifier.freeze)
        with patch.object(r,'loaded_files',return_value=set()):
            self.assertFalse(self.verifier.verify(self.m)['scientific_execution_authorized'])

if __name__=='__main__':unittest.main()
