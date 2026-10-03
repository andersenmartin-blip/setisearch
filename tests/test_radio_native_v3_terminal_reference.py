"""Small terminal wire and real tiny child observations; no e control runs."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name,ROOT/'scripts'/(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIXTURE = load('radio_native_v3_compact_eight_case_resource_fixture')
FINALIZER = load('radio_native_v3_resource_finalization')


class TerminalReferenceTests(unittest.TestCase):
    def join(self):
        return {'schema':FINALIZER.SCHEMA+'-persisted-final-report',
            'scope':'/tmp/tiny-offline-reference','status':'OFFLINE_RESOURCE_MEASUREMENT_JOIN_PASSED',
            'complete_resource_measurement_join_qualified':True,
            'final_report_input_pin':{'bytes':31,'sha256':'1'*64},
            'persisted_final_report_pin':{'bytes':43,'sha256':'2'*64},
            'final_report_writer_observation_pin':{'bytes':59,'sha256':'3'*64},
            'retained_report_body':{'rows':[{'tiny_original':i} for i in range(100)]},
            'storage_after_report_writer_lifetime_with_final_reservation':{
                'metadata_logical_bytes_present':101,'metadata_allocated_bytes_present':4096}}

    def test_compact_reference_binds_retained_pins_and_stable_join_core(self):
        joined = self.join()
        reference = FINALIZER.final_report_join_reference(joined)
        self.assertTrue(FINALIZER.verify_final_report_join_reference(reference,joined))
        self.assertLess(len(FINALIZER.canonical(reference))+1,4096)
        self.assertNotIn(b'tiny_original',FINALIZER.canonical(reference))
        self.assertFalse(reference['execution_authorized'])
        later = copy.deepcopy(joined)
        later['storage_after_report_writer_lifetime_with_final_reservation'].update(
            metadata_logical_bytes_present=999,metadata_allocated_bytes_present=16384)
        self.assertTrue(FINALIZER.verify_final_report_join_reference(reference,later))
        self.assertEqual(FINALIZER.final_report_join_core(joined),FINALIZER.final_report_join_core(later))

    def test_each_retained_pin_or_join_hash_swap_is_closed(self):
        joined = self.join()
        reference = FINALIZER.final_report_join_reference(joined)
        for key in ('final_report_input_pin','persisted_final_report_pin',
                'final_report_writer_observation_pin'):
            with self.subTest(key=key):
                changed = copy.deepcopy(joined)
                changed[key]['sha256']='4'*64
                with self.assertRaisesRegex(ValueError,'independently replayed report join'):
                    FINALIZER.verify_final_report_join_reference(reference,changed)
        changed = copy.deepcopy(reference)
        changed['join_core_sha256']='5'*64
        with self.assertRaises(ValueError):
            FINALIZER.verify_final_report_join_reference(changed,joined)
        changed = copy.deepcopy(joined)
        changed['retained_report_body']['rows'][0]['tiny_original']='changed'
        with self.assertRaises(ValueError):
            FINALIZER.verify_final_report_join_reference(reference,changed)

    def test_launcher_wire_references_actual_retained_disposition_bytes(self):
        result = {'scope':'/tmp/tiny-offline-reference','status':'OBSERVED_FIXTURE_CHILD_JOIN_PASSED',
            'independently_observed_fixture_child_join_qualified':True,
            'metadata':[{'tiny_original':i} for i in range(100)]}
        raw = FINALIZER.canonical(result)+b'\n'
        pin = {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
        reference = FINALIZER.launcher_completion_reference(result,pin)
        self.assertTrue(FINALIZER.verify_launcher_completion_reference(reference,result,pin))
        self.assertLess(len(FINALIZER.canonical(reference))+1,4096)
        self.assertNotIn(b'tiny_original',FINALIZER.canonical(reference))
        self.assertFalse(reference['launcher_termination_covered'])
        changed = dict(pin,sha256='4'*64)
        with self.assertRaises(ValueError):
            FINALIZER.verify_launcher_completion_reference(reference,result,changed)

    def tiny_observation(self, root, high):
        identity_path = root/'tiny-identity.json'
        program = ("import json,os,sys,time; "
            "f=open(sys.argv[1],'x'); "
            "json.dump({'procfs_pid':int(os.readlink('/proc/self')),'namespace_pid':os.getpid()},f); "
            "f.flush();os.fsync(f.fileno());f.close();time.sleep(0.10)")
        count = 0
        def memory(pid):
            nonlocal count
            count += 1
            amount = high if count==3 else 1024
            return {'at_epoch_ms':time.time_ns()//1000000,
                'rss_bytes':amount,'kernel_vm_hwm_bytes':amount}
        argv = [str(Path(sys.executable).resolve()),'-I','-S','-B','-c',program,str(identity_path)]
        with mock.patch.object(FIXTURE,'proc_memory',side_effect=memory):
            observed,_,_ = FIXTURE.observe_process(argv,root,'tiny',identity_path,
                deadline=time.monotonic()+5,pipe_output=True,sample_retention_limit=2)
        return observed

    def test_unretained_high_sample_remains_in_reported_peak(self):
        with tempfile.TemporaryDirectory(prefix='v3-tiny-retention-') as directory:
            observed = self.tiny_observation(Path(directory),400*1024**2)
            self.assertGreater(observed['sample_count'],3)
            self.assertEqual(observed['retained_sample_count'],2)
            self.assertLess(max(row['rss_bytes'] for row in observed['samples']),400*1024**2)
            self.assertEqual(observed['peak_rss_bytes'],400*1024**2)
            self.assertTrue(observed['direct_child_reaped'])

    def test_unretained_over_limit_sample_closes_before_success(self):
        with tempfile.TemporaryDirectory(prefix='v3-tiny-overlimit-') as directory:
            root = Path(directory)
            with self.assertRaisesRegex(RuntimeError,'512MiB.*material process.*cap exceeded'):
                self.tiny_observation(root,FIXTURE.LIMITS['rss_bytes']+1024)
            observed = json.loads((root/'tiny-observation.json').read_bytes())
            self.assertGreater(observed['peak_rss_bytes'],FIXTURE.LIMITS['rss_bytes'])
            self.assertTrue(observed['direct_child_reaped'])


if __name__=='__main__':
    unittest.main()
