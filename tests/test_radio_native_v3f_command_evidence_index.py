"""Tiny retained command metadata only; no control or source reader runs."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('v3_command_index_fixture',
    ROOT/'scripts/radio_native_v3f_compact_eight_case_resource_fixture.py')
FIXTURE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURE)


class CommandEvidenceIndexTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='v3-tiny-command-index-')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        (self.root/'command-observations').mkdir()
        self.plan = {'runtime_executables':{'python':{'path':'/usr/bin/python3'}},
            'code_files':{'scripts/radio_native_v3f_process_tree_supervisor.py':
                {'bytes':1,'sha256':'1'*64}}}
        self.labels = ['command-'+str(i) for i in range(38)]+['command-tail']
        self.bundles = {}
        for label in self.labels:
            path = self.root/(label+'-admission.json')
            self.write(path, {'tiny':label})
            digest = FIXTURE.pin(path)['sha256']
            self.bundles[str(path)] = {'role':'command','case_ordinal':0,
                'phase_inputs':{'label':label},'plan':self.plan}
            receipt_root = self.root/(label+'-supervisor')
            receipt_root.mkdir()
            prefix=['/usr/bin/python3','-I','-S','-B',
                str(self.root/'frozen-code'/'scripts/radio_native_v3f_process_tree_supervisor.py'),
                '--admitted-worker','--worker-role','command','--admission-bundle',str(path),
                '--bundle-sha256',digest,'--scope',str(receipt_root),'--seconds']
            self.write(self.root/'command-observations'/(label+'-observation.json'), {
                'observed_argv':prefix+['120','--ordinal','0'],'reason':None,'exit_code':0,
                'direct_child_reaped':True,'reported_identity_verified':True,
                'includes_entire_child_lifetime':True,'complete_pipe_output':True,
                'child_environment':FIXTURE.CHILD_ENVIRONMENT,
                'peak_rss_bytes':1024,'observer_self_kernel_peak_rss_bytes':2048,
                'samples':[{'tiny_retained_original':i} for i in range(3)]})
            self.write(receipt_root/'subreaper-receipt.json', {
                'status':'ENGINEERING_SUBREAPER_SCOPE_COMPLETE',
                'subreaper_scope_reaped_to_echild':True,
                'maximum_individual_process_rss_bytes':4096,
                'admitted_worker_check':{'role':'command','ordinal':0,'bundle_path':str(path),
                    'bundle_sha256':digest,'argv':['tiny-checked',label]},
                'supervisor_code':self.plan['code_files']['scripts/radio_native_v3f_process_tree_supervisor.py']})
        self.admission = {'load_bundle':lambda path, **kwargs:self.bundles[str(path)],
            'worker_role_layout':lambda bundle, **kwargs:{'receipt_scope':
                str(self.root/(bundle['phase_inputs']['label']+'-supervisor'))},
            'expected_worker_argv':lambda bundle, *args, **kwargs:
                ['tiny-checked',bundle['phase_inputs']['label']]}

    def write(self, path, value):
        path.write_bytes(FIXTURE.canonical(value)+b'\n')

    def verified(self):
        with mock.patch.object(FIXTURE,'pinned_component',return_value=self.admission):
            return FIXTURE.verified_command_observations(self.root,self.plan,0)

    def test_exact_39_original_evidence_descriptors_and_rss_are_retained(self):
        index = self.verified()
        self.assertEqual([row['label'] for row in index],self.labels)
        for row in index:
            self.assertEqual(row['maximum_individual_material_process_rss_bytes'],4096)
            self.assertFalse(row['complete_descendant_wait_chain_verified'])
            for key in ('admission_bundle','observation','subreaper_receipt'):
                descriptor = row[key]
                self.assertEqual(set(descriptor),{'path','bytes','sha256'})
                raw = Path(descriptor['path']).read_bytes()
                self.assertEqual(descriptor['bytes'],len(raw))
                self.assertEqual(descriptor['sha256'],hashlib.sha256(raw).hexdigest())
            self.assertNotIn('samples',row['observation'])
            self.assertNotIn('admitted_worker_check',row['subreaper_receipt'])
        self.assertEqual(len(list((self.root/'command-observations').glob('*-observation.json'))),39)
        self.assertLess(len(FIXTURE.canonical(index)),32768)

    def test_mutated_original_observation_before_reopen_is_rejected(self):
        original = FIXTURE.small_json
        def changed(path, *args, **kwargs):
            value = original(path,*args,**kwargs)
            if Path(path).name=='command-0-observation.json':
                Path(path).write_bytes(Path(path).read_bytes()+b' ')
            return value
        with mock.patch.object(FIXTURE,'small_json',side_effect=changed):
            with self.assertRaisesRegex(ValueError,'evidence changed during independent verification'):
                self.verified()


if __name__=='__main__':
    unittest.main()
