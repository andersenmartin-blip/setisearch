"""Tiny synthetic Git tests only; never import or execute the material runner."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'scripts/radio_native_v2_control_activation.py'
SPEC = importlib.util.spec_from_file_location('control_activation', SOURCE)
activation = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(activation)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(activation.canonical(value)+b'\n')


def git(root, *args):
    return subprocess.check_output(['git',*args],cwd=root,text=True).strip()


class ControlActivationTests(unittest.TestCase):
    def fixture(self, directory):
        root=Path(directory)/'repo'; root.mkdir(); git(root,'init','-q')
        git(root,'config','user.email','test@example.invalid'); git(root,'config','user.name','Test')
        paths={'plan':'config/plan.json','complete_freeze':'config/freeze.json',
            'execution_preread':'config/preread.json'}
        values={'plan':{'execution_status':'BLOCKED_PREPARATION_REVIEW','value':1},
            'complete_freeze':{'mode':'PROSPECTIVE_ENGINEERING_ONLY','value':2},
            'execution_preread':{'engineering_control_admitted':True,'value':3}}
        for name,path in paths.items(): write(root/path,values[name])
        git(root,'add','.'); git(root,'commit','-q','-m','preread')
        parent=git(root,'rev-parse','HEAD'); parent_tree=git(root,'rev-parse','HEAD^{tree}')
        blobs={name:git(root,'rev-parse',parent+':'+path) for name,path in paths.items()}
        marker={'schema':activation.SCHEMA,'namespace':activation.NAMESPACE,'activate':True,
            'preread_commit':parent,'preread_tree':parent_tree,
            'plan_sha256':hashlib.sha256(activation.canonical(values['plan'])).hexdigest(),
            'complete_freeze_sha256':hashlib.sha256(activation.canonical(values['complete_freeze'])).hexdigest(),
            'execution_preread_sha256':hashlib.sha256(activation.canonical(values['execution_preread'])).hexdigest(),
            'independent_preread_readback':{'verified':True,'commit':parent,'tree':parent_tree,'blobs':blobs},
            'one_control_invocation':True,**{key:False for key in activation.DISABLED}}
        write(root/activation.MARKER,marker); git(root,'add',activation.MARKER); git(root,'commit','-q','-m','activate')
        head=git(root,'rev-parse','HEAD'); marker_raw=(root/activation.MARKER).read_bytes()
        readback={'schema':activation.READBACK_SCHEMA,'repository':activation.REPOSITORY,
            'branch':activation.BRANCH,'verified':True,'activation_commit':head,
            'activation_tree':git(root,'rev-parse','HEAD^{tree}'),'activation_parent':parent,
            'marker_path':activation.MARKER,'marker_blob':git(root,'rev-parse','HEAD:'+activation.MARKER),
            'marker_sha256':hashlib.sha256(marker_raw).hexdigest()}
        readback_path=Path(directory)/'activation-readback.json'; write(readback_path,readback)
        return root,paths,values,readback_path

    def test_exact_marker_only_checkout_and_worker_receipt_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root,paths,values,readback=self.fixture(directory)
            receipt=activation.verify_marker_checkout(root,plan_path=paths['plan'],
                freeze_path=paths['complete_freeze'],preread_path=paths['execution_preread'],
                activation_readback_path=readback)
            self.assertTrue(activation.validate_worker_receipt(receipt,plan=values['plan'],
                complete_freeze=values['complete_freeze'],execution_preread=values['execution_preread']))
            self.assertTrue(receipt['activation_public_readback_verified'])
            self.assertFalse(receipt['automatic_retry'])

    def test_changed_receipt_pins_and_authority_close(self):
        with tempfile.TemporaryDirectory() as directory:
            root,paths,values,readback=self.fixture(directory)
            receipt=activation.verify_marker_checkout(root,plan_path=paths['plan'],
                freeze_path=paths['complete_freeze'],preread_path=paths['execution_preread'],
                activation_readback_path=readback)
            changes=(('plan_sha256','0'*64),('automatic_retry',True),
                ('activation_public_readback_verified',False),('marker_path','config/reused.json'))
            for key,value in changes:
                changed=copy.deepcopy(receipt); changed[key]=value
                with self.subTest(key=key),self.assertRaises(ValueError):
                    activation.validate_worker_receipt(changed,plan=values['plan'],
                        complete_freeze=values['complete_freeze'],execution_preread=values['execution_preread'])

    def test_non_marker_only_commit_closes(self):
        with tempfile.TemporaryDirectory() as directory:
            root,paths,_,readback=self.fixture(directory)
            (root/'extra.txt').write_text('not allowed\n'); git(root,'add','extra.txt'); git(root,'commit','-q','-m','extra')
            with self.assertRaisesRegex(ValueError,'exactly one parent|only the unique marker'):
                activation.verify_marker_checkout(root,plan_path=paths['plan'],
                    freeze_path=paths['complete_freeze'],preread_path=paths['execution_preread'],
                    activation_readback_path=readback)

    def test_changed_public_readback_closes(self):
        with tempfile.TemporaryDirectory() as directory:
            root,paths,_,readback=self.fixture(directory)
            value=json.loads(readback.read_bytes()); value['verified']=False; write(readback,value)
            with self.assertRaisesRegex(ValueError,'public activation readback'):
                activation.verify_marker_checkout(root,plan_path=paths['plan'],
                    freeze_path=paths['complete_freeze'],preread_path=paths['execution_preread'],
                    activation_readback_path=readback)


if __name__=='__main__':
    unittest.main()
