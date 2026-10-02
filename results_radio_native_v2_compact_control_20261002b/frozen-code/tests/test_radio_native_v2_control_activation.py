"""Tiny synthetic Git tests only; never import or execute the material runner."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import radio_native_v2_runtime_custody as custody

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
    def verify(self,root,paths,readback,**kwargs):
        return activation.verify_marker_checkout(root,plan_path=paths['plan'],
            freeze_path=paths['complete_freeze'],preread_path=paths['execution_preread'],
            activation_readback_path=readback,execution_scope=str(root.parent/'control'),**kwargs)

    def test_git_fixed_no_fetch_and_no_prompt_policy_overrides_conflicting_parent(self):
        # Synthetic subprocess capture only: no Git command or remote is run.
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            scope=activation._ActivationGitScope(root,activation.ACTIVATION_GIT_IMPLEMENTATION_PIN['path'])
            with (mock.patch.dict(os.environ,{'GIT_NO_LAZY_FETCH':'0','GIT_TERMINAL_PROMPT':'1',
                    'GIT_CONFIG_GLOBAL':'/candidate-selected/config','GIT_SSH_COMMAND':'candidate-selected transport'}),
                    mock.patch.object(subprocess,'check_output',return_value='synthetic-object\n') as launch):
                self.assertEqual(activation._git(root,'rev-parse','HEAD',activation_scope=scope),'synthetic-object')
            environment=launch.call_args.kwargs['env']
            self.assertEqual(environment['GIT_NO_LAZY_FETCH'],'1')
            self.assertEqual(environment['GIT_TERMINAL_PROMPT'],'0')
            self.assertEqual(environment['GIT_CONFIG_GLOBAL'],'/dev/null')
            self.assertNotIn('GIT_SSH_COMMAND',environment)
            self.assertEqual(launch.call_args.args[0],[activation.ACTIVATION_GIT_IMPLEMENTATION_PIN['path'],
                '--no-replace-objects','rev-parse','HEAD'])

    def refresh_readback(self,root,readback_path):
        head=git(root,'rev-parse','HEAD'); parent=git(root,'rev-parse','HEAD^')
        raw=(root/activation.MARKER).read_bytes()
        value={'schema':activation.READBACK_SCHEMA,'repository':activation.REPOSITORY,
            'branch':activation.BRANCH,'verified':True,'activation_commit':head,
            'activation_tree':git(root,'rev-parse','HEAD^{tree}'),'activation_parent':parent,
            'marker_path':activation.MARKER,'marker_blob':git(root,'rev-parse','HEAD:'+activation.MARKER),
            'marker_sha256':hashlib.sha256(raw).hexdigest()}
        write(readback_path,value)

    def fixture(self, directory):
        root=Path(directory)/'repo'; root.mkdir(); git(root,'init','-q')
        git(root,'config','user.email','test@example.invalid'); git(root,'config','user.name','Test')
        paths={'plan':'config/plan.json','complete_freeze':'config/freeze.json',
            'execution_preread':'config/preread.json'}
        git_path = activation.ACTIVATION_GIT_IMPLEMENTATION_PIN['path']
        material = Path(directory)/'tiny-material-runtime'; material.write_bytes(b'tiny inert material runtime')
        paths_runtime = sorted([git_path,str(material)])
        runtime_hashes = {path:hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in paths_runtime}
        manifest = custody.build_manifest(runtime_paths=paths_runtime,runtime_sha256s=runtime_hashes,
            activation_only_paths=[git_path],alias_roots=['/usr/local/bin','/usr/local/libexec/git-core'])
        custody_path=root/activation.CUSTODY_SOURCE; custody_path.parent.mkdir(parents=True)
        custody_path.write_bytes((ROOT/activation.CUSTODY_SOURCE).read_bytes())
        values={'plan':{'execution_status':'BLOCKED_PREPARATION_REVIEW','value':1},
            'complete_freeze':{'mode':'PROSPECTIVE_ENGINEERING_ONLY','value':2,
                'runtime_file_inventory':paths_runtime,'runtime_sha256s':runtime_hashes,
                'git_runtime_file_inventory':[],'git_exec_path':'/usr/local/libexec/git-core',
                'executables':{'git':{'resolved':git_path,'sha256':runtime_hashes[git_path]},
                    'python':{'resolved':str(material)},'node':{'resolved':str(material)}},
                'runtime_custody_manifest':manifest,
                'runtime_custody_manifest_sha256':hashlib.sha256(custody.canonical(manifest)).hexdigest()},
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
            'one_control_invocation':True,'control_scope':str(Path(directory)/'control'),
            **{key:False for key in activation.DISABLED}}
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
                activation_readback_path=readback,execution_scope=str(root.parent/"control"))
            self.assertTrue(activation.validate_worker_receipt(receipt,plan=values['plan'],
                complete_freeze=values['complete_freeze'],execution_preread=values['execution_preread']))
            self.assertTrue(receipt['activation_public_readback_verified'])
            self.assertFalse(receipt['automatic_retry'])

    def test_changed_receipt_pins_and_authority_close(self):
        with tempfile.TemporaryDirectory() as directory:
            root,paths,values,readback=self.fixture(directory)
            receipt=activation.verify_marker_checkout(root,plan_path=paths['plan'],
                freeze_path=paths['complete_freeze'],preread_path=paths['execution_preread'],
                activation_readback_path=readback,execution_scope=str(root.parent/"control"))
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
                    activation_readback_path=readback,execution_scope=str(root.parent/"control"))

    def test_changed_public_readback_closes(self):
        with tempfile.TemporaryDirectory() as directory:
            root,paths,_,readback=self.fixture(directory)
            value=json.loads(readback.read_bytes()); value['verified']=False; write(readback,value)
            with self.assertRaisesRegex(ValueError,'public activation readback'):
                activation.verify_marker_checkout(root,plan_path=paths['plan'],
                    freeze_path=paths['complete_freeze'],preread_path=paths['execution_preread'],
                    activation_readback_path=readback,execution_scope=str(root.parent/"control"))

    def test_missing_or_dirty_marker_closes(self):
        for mode in ('missing','dirty'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as directory:
                root,paths,_,readback=self.fixture(directory); marker=root/activation.MARKER
                if mode=='missing': marker.unlink()
                else:
                    value=json.loads(marker.read_bytes()); value['unexpected']=True; write(marker,value)
                with self.assertRaises(ValueError):
                    activation.verify_marker_checkout(root,plan_path=paths['plan'],
                        freeze_path=paths['complete_freeze'],preread_path=paths['execution_preread'],
                        activation_readback_path=readback,execution_scope=str(root.parent/"control"))

    def test_wrong_parent_or_tree_claim_closes_even_with_refreshed_commit_readback(self):
        for key,value in (('preread_commit','9'*40),('preread_tree','8'*40)):
            with self.subTest(key=key),tempfile.TemporaryDirectory() as directory:
                root,paths,_,readback=self.fixture(directory); marker=root/activation.MARKER
                document=json.loads(marker.read_bytes()); document[key]=value; write(marker,document)
                git(root,'add',activation.MARKER); git(root,'commit','-q','--amend','--no-edit')
                self.refresh_readback(root,readback)
                with self.assertRaisesRegex(ValueError,'exact preread parent and tree'):
                    activation.verify_marker_checkout(root,plan_path=paths['plan'],
                        freeze_path=paths['complete_freeze'],preread_path=paths['execution_preread'],
                        activation_readback_path=readback,execution_scope=str(root.parent/"control"))

    def test_reused_marker_path_closes_even_when_all_current_bytes_are_read_back(self):
        with tempfile.TemporaryDirectory() as directory:
            root,paths,_,readback=self.fixture(directory)
            git(root,'reset','-q','--hard','HEAD^')
            placeholder={'inactive':True}; write(root/activation.MARKER,placeholder)
            git(root,'add',activation.MARKER); git(root,'commit','-q','-m','reserve marker incorrectly')
            parent=git(root,'rev-parse','HEAD'); parent_tree=git(root,'rev-parse','HEAD^{tree}')
            values={name:json.loads((root/path).read_bytes()) for name,path in paths.items()}
            blobs={name:git(root,'rev-parse',parent+':'+path) for name,path in paths.items()}
            marker={'schema':activation.SCHEMA,'namespace':activation.NAMESPACE,'activate':True,
                'preread_commit':parent,'preread_tree':parent_tree,
                'plan_sha256':hashlib.sha256(activation.canonical(values['plan'])).hexdigest(),
                'complete_freeze_sha256':hashlib.sha256(activation.canonical(values['complete_freeze'])).hexdigest(),
                'execution_preread_sha256':hashlib.sha256(activation.canonical(values['execution_preread'])).hexdigest(),
                'independent_preread_readback':{'verified':True,'commit':parent,'tree':parent_tree,'blobs':blobs},
                'one_control_invocation':True,'control_scope':str(root.parent/'control'),**{key:False for key in activation.DISABLED}}
            write(root/activation.MARKER,marker); git(root,'add',activation.MARKER); git(root,'commit','-q','-m','reuse marker')
            self.refresh_readback(root,readback)
            with self.assertRaisesRegex(ValueError,'new file'):
                activation.verify_marker_checkout(root,plan_path=paths['plan'],
                    freeze_path=paths['complete_freeze'],preread_path=paths['execution_preread'],
                    activation_readback_path=readback,execution_scope=str(root.parent/"control"))

    def test_full_custody_rejects_same_byte_material_replacement_before_git(self):
        with tempfile.TemporaryDirectory() as directory:
            root,paths,_,readback=self.fixture(directory)
            material=root.parent/'tiny-material-runtime'
            replacement=root.parent/'replacement'; replacement.write_bytes(material.read_bytes())
            os.replace(replacement,material)
            with mock.patch.object(activation,'_git') as launch,self.assertRaises(ValueError):
                self.verify(root,paths,readback)
            launch.assert_not_called()

    def test_git_phase_closes_and_material_custody_is_rechecked_before_return(self):
        with tempfile.TemporaryDirectory() as directory:
            root,paths,values,readback=self.fixture(directory)
            scopes=[]; actual=activation._git
            def observed(*args,**kwargs):
                scopes.append(kwargs['activation_scope'])
                return actual(*args,**kwargs)
            with mock.patch.object(activation,'_git',side_effect=observed):
                receipt=self.verify(root,paths,readback)
            self.assertTrue(receipt['activation_only_runtime_complete'])
            self.assertTrue(scopes and all(scope.closed for scope in scopes))
            with self.assertRaisesRegex(ValueError,'activation-only phase'):
                actual(root,'rev-parse','HEAD',activation_scope=scopes[-1])
            # Direct downstream receipt checking must use no Git or alias scan.
            with (mock.patch.object(subprocess,'check_output',side_effect=AssertionError('No downstream Git')),
                    mock.patch.object(os,'scandir',side_effect=AssertionError('No downstream alias enumeration'))):
                self.assertTrue(activation.validate_worker_receipt(receipt,plan=values['plan'],
                    complete_freeze=values['complete_freeze'],execution_preread=values['execution_preread'],
                    execution_scope=str(root.parent/'control')))

    def test_material_mutation_during_git_cannot_return_complete_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root,paths,_,readback=self.fixture(directory)
            material=root.parent/'tiny-material-runtime'; actual=activation._git; seen=[]
            def changed(*args,**kwargs):
                result=actual(*args,**kwargs)
                if not seen:
                    seen.append(True)
                    replacement=root.parent/'replacement'; replacement.write_bytes(material.read_bytes())
                    os.replace(replacement,material)
                return result
            with mock.patch.object(activation,'_git',side_effect=changed),self.assertRaises(ValueError):
                self.verify(root,paths,readback)
            self.assertTrue(seen)

    def test_receipt_custody_scope_completion_and_spent_identity_are_strict(self):
        with tempfile.TemporaryDirectory() as directory:
            root,paths,values,readback=self.fixture(directory); receipt=self.verify(root,paths,readback)
            changes=(('runtime_custody_manifest_sha256','0'*64),
                ('activation_only_runtime_complete',False),('activation_only_runtime_complete',1),
                ('control_scope',str(root.parent/'other-control')),('schema',activation.RECEIPT_SCHEMA.replace('v2','v1')),
                ('marker_path',activation.SPENT_MARKER),('activation_commit',activation.SPENT_ACTIVATION_COMMIT))
            for key,value in changes:
                changed=copy.deepcopy(receipt); changed[key]=value
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                    activation.validate_worker_receipt(changed,plan=values['plan'],
                        complete_freeze=values['complete_freeze'],execution_preread=values['execution_preread'],
                        execution_scope=str(root.parent/'control'))
            with mock.patch.object(activation,'_git') as launch,self.assertRaisesRegex(ValueError,'spent'):
                self.verify(root,paths,readback,marker_path=activation.SPENT_MARKER)
            launch.assert_not_called()

    def test_candidate_selected_git_custody_source_or_policy_cannot_run_before_check(self):
        for mode in ('git','source','roots','classification'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as directory:
                root,paths,values,readback=self.fixture(directory); freeze=values['complete_freeze']
                if mode=='source':
                    (root/activation.CUSTODY_SOURCE).write_bytes(b'raise AssertionError("candidate code executed")\n')
                elif mode=='git':
                    fake_bin=root.parent/'fake-bin'; fake_bin.mkdir()
                    fake=fake_bin/'fake-git'; fake.write_bytes(b'tiny inert fake Git')
                    digest=hashlib.sha256(fake.read_bytes()).hexdigest()
                    freeze['executables']['git']={'resolved':str(fake),'sha256':digest}
                    freeze['runtime_file_inventory']=sorted([str(fake),str(root.parent/'tiny-material-runtime')])
                    freeze['runtime_sha256s']={path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
                        for path in freeze['runtime_file_inventory']}
                    freeze['git_exec_path']=str(root.parent/'fake-core'); Path(freeze['git_exec_path']).mkdir()
                    manifest=custody.build_manifest(runtime_paths=freeze['runtime_file_inventory'],
                        runtime_sha256s=freeze['runtime_sha256s'],activation_only_paths=[str(fake)],
                        alias_roots=sorted([str(fake_bin),freeze['git_exec_path']]))
                    freeze['runtime_custody_manifest']=manifest
                else:
                    manifest=copy.deepcopy(freeze['runtime_custody_manifest'])
                    if mode=='roots': manifest['alias_roots']=['/candidate-selected/aliases']
                    else:
                        material=str(root.parent/'tiny-material-runtime')
                        manifest['activation_only_paths']=sorted(manifest['activation_only_paths']+[material])
                        manifest['material_runtime_paths']=0
                        manifest['runtime_files'][material]['lifecycle']='activation_only'
                    freeze['runtime_custody_manifest']=manifest
                if mode!='source':
                    freeze['runtime_custody_manifest_sha256']=hashlib.sha256(custody.canonical(freeze['runtime_custody_manifest'])).hexdigest()
                    write(root/paths['complete_freeze'],freeze)
                with mock.patch.object(activation,'_git') as launch,self.assertRaises(ValueError):
                    self.verify(root,paths,readback)
                launch.assert_not_called()


if __name__=='__main__':
    unittest.main()
