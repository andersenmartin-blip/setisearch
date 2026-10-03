"""Tiny metadata/child probes; no real v3 marker, claim, journal or control."""
import copy
import errno
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT/relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


observer = load('scripts/radio_native_v3f_engineering_observer.py','tiny_external_observer')
supervisor = load('scripts/radio_native_v3f_process_tree_supervisor.py','tiny_external_supervisor')
finalizer = load('scripts/radio_native_v3f_resource_finalization.py','tiny_external_finalizer')


def pin(raw):
    return {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


def capsule(root):
    return {'schema':observer.CAPSULE_SCHEMA,'namespace':observer.NAMESPACE,
        'repository_root':str(root),'scope':str(root/observer.SCOPE_NAME),
        'python':{'path':str(Path(sys.executable).resolve()),**pin(b'python')},
        'environment':{'PATH':'/usr/bin:/bin',**observer.ENVIRONMENT_FIXED},
        'source_pins':{p:pin(b'source') for p in observer.SOURCE_PATHS},
        'launch_config':{'path':observer.CONFIG_PATH,**pin(b'config')},
        'limits':copy.deepcopy(observer.LIMITS),'authority':copy.deepcopy(observer.AUTHORITY)}


class CapsuleTests(unittest.TestCase):
    def test_fixed_capsule_is_pure_and_accepts_no_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            self.assertTrue(observer.validate_capsule(capsule(root),root=root))
            self.assertEqual(list(root.iterdir()),[])

    def test_scope_command_and_environment_overrides_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            changes=[lambda c:c.update(command=['sh','-c','true']),
                lambda c:c.update(scope=str(root/'other')),
                lambda c:c['environment'].update(LD_PRELOAD='/tmp/x'),
                lambda c:c['environment'].update(HOME='/tmp'),
                lambda c:c['source_pins'].pop(observer.SUPERVISOR),
                lambda c:c['launch_config'].update(path='config/old.json')]
            for change in changes:
                c=capsule(root);change(c)
                with self.subTest(c=c),self.assertRaises(ValueError):
                    observer.validate_capsule(c,root=root)

    def test_expanded_limits_or_authority_cannot_be_admitted(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for field in ['limits','authority']:
                c=capsule(root)
                c[field]['run_seconds' if field=='limits' else 'scientific_execution_authorized']=9999 if field=='limits' else True
                with self.assertRaises(ValueError):observer.validate_capsule(c,root=root)

    def test_duplicate_nonfinite_and_noncanonical_json_refused(self):
        for raw in [b'{"x":1,"x":2}\n',b'{"x":NaN}\n',b'{"x": 1}\n',b'{"x":1}']:
            with self.subTest(raw=raw),self.assertRaises(ValueError):observer._json(raw)
        self.assertEqual(observer._json(b'{"x":1}\n'),{'x':1})

    def test_stable_reads_refuse_symlink_hardlink_and_wrong_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/'material';p.write_bytes(b'abc')
            self.assertEqual(observer.read_pinned(p,expected=pin(b'abc'),retain=True),(pin(b'abc'),b'abc'))
            link=root/'link';link.symlink_to(p)
            with self.assertRaises(OSError):observer.read_pinned(link)
            with self.assertRaises(ValueError):observer.read_pinned(p,expected=pin(b'other'))
            hard=root/'hard';os.link(p,hard)
            with self.assertRaises(ValueError):observer.read_pinned(p)

    def test_exclusive_fsync_outputs_cannot_be_replayed_or_oversized(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'observation'
            self.assertEqual(observer._write_exclusive(p,b'abc',3),pin(b'abc'))
            with self.assertRaises(FileExistsError):observer._write_exclusive(p,b'abc',3)
            with self.assertRaises(ValueError):observer._write_exclusive(Path(tmp)/'large',b'abcd',3)
            self.assertEqual(p.read_bytes(),b'abc')


@unittest.skipUnless(sys.platform.startswith('linux') and hasattr(os,'pidfd_open'),'Linux pidfd/subreaper required')
class ChildTests(unittest.TestCase):
    def observe(self,body,seconds=2,stdout_cap=observer.STDOUT_CAP):
        return observer.observe_child([str(Path(sys.executable).resolve()),'-I','-S','-B','-c',body],
            {'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'},
            deadline_monotonic_ns=time.monotonic_ns()+int(seconds*10**9),
            supervisor=supervisor,stdout_cap=stdout_cap)

    def test_complete_wait4_and_exact_raw_pipe_bytes(self):
        observed,out,err=self.observe("import os;os.write(1,b'hello\\x00');os.write(2,b'err')")
        self.assertEqual(out,b'hello\0');self.assertEqual(err,b'err')
        self.assertEqual(observed['exit_code'],0);self.assertIsNone(observed['reason'])
        self.assertTrue(observed['direct_child_reaped'])
        self.assertTrue(observed['subreaper_scope_reaped_to_echild'])
        self.assertTrue(observed['complete_pipe_output'])
        self.assertGreater(observed['maximum_observed_individual_rss_bytes'],0)
        self.assertFalse(observed['terminal_observer_own_future_termination_covered'])

    def test_output_overflow_retains_only_bound_and_reaps(self):
        observed,out,err=self.observe("import os,time;os.write(1,b'x'*4096);time.sleep(2)",stdout_cap=64)
        self.assertEqual(len(out),64);self.assertGreater(observed['observed_output_bytes']['stdout'],64)
        self.assertIn('output cap',observed['reason'])
        self.assertTrue(observed['direct_child_reaped']);self.assertTrue(observed['subreaper_scope_reaped_to_echild'])

    def test_timeout_reaps_direct_child_without_retry(self):
        observed,_,_=self.observe('import time;time.sleep(5)',seconds=.12)
        self.assertIn('deadline',observed['reason']);self.assertTrue(observed['direct_child_reaped'])
        self.assertTrue(observed['subreaper_scope_reaped_to_echild'])
        self.assertLess(observed['elapsed_seconds'],1.3)

    def test_adopted_new_session_pipe_holder_is_cancelled_with_pidfd(self):
        body='import os,time\np=os.fork()\nif p==0:\n os.setsid();time.sleep(5);os._exit(0)\nos._exit(0)'
        observed,_,_=self.observe(body,seconds=.12)
        self.assertIn('deadline',observed['reason'])
        self.assertTrue(observed['direct_child_reaped']);self.assertTrue(observed['subreaper_scope_reaped_to_echild'])
        self.assertEqual(len(observed['reaped_processes']),2)
        self.assertGreater(observed['cancellation_count'],0)

    def test_namespace_guard_is_inherited_before_exec(self):
        body="import ctypes,errno,os\nlibc=ctypes.CDLL(None,use_errno=True)\nnumber={'x86_64':272,'aarch64':97}[os.uname().machine]\nctypes.set_errno(0)\nresult=libc.syscall(number,0x20000000)\nassert result==-1 and ctypes.get_errno()==errno.EPERM\nprint('guard')"
        observed,out,_=self.observe(body)
        self.assertEqual(out,b'guard\n');self.assertEqual(observed['exit_code'],0)
        self.assertTrue(observed['declared_namespace_tracing_escape_guard_inherited'])
        self.assertFalse(observed['kernel_integrity_or_general_sandbox_qualified'])


class MeasurementTests(unittest.TestCase):
    def joined_fixture(self):
        return {'schema':'synthetic-metadata-only-join','scope':'/tmp/tiny-observer-join',
            'status':'SYNTHETIC_JOIN','complete_resource_measurement_join_qualified':True,
            'final_report_input_pin':pin(b'input'),'persisted_final_report_pin':pin(b'report'),
            'final_report_writer_observation_pin':pin(b'writer'),
            'scientific_execution_authorized':False,
            'storage_after_report_writer_lifetime_with_final_reservation':{'metadata_bytes':100}}

    def test_dynamic_storage_change_preserves_only_the_immutable_join_reference(self):
        before=self.joined_fixture()
        reference=finalizer.final_report_join_reference(before)
        after=copy.deepcopy(before)
        after['storage_after_report_writer_lifetime_with_final_reservation']={'metadata_bytes':900}
        self.assertTrue(finalizer.verify_final_report_join_reference(reference,after))
        self.assertEqual(reference['report_input_pin'],before['final_report_input_pin'])
        self.assertNotIn('storage_after_report_writer_lifetime_with_final_reservation',
            finalizer.final_report_join_core(after))
        self.assertEqual(before['storage_after_report_writer_lifetime_with_final_reservation'],{'metadata_bytes':100})

    def test_changed_persisted_pin_status_or_scientific_core_is_refused(self):
        before=self.joined_fixture();reference=finalizer.final_report_join_reference(before)
        changes=[lambda x:x.update(persisted_final_report_pin=pin(b'swapped')),
            lambda x:x.update(status='OTHER'),
            lambda x:x.update(scientific_execution_authorized=True)]
        for change in changes:
            after=copy.deepcopy(before);change(after)
            with self.subTest(after=after),self.assertRaises(ValueError):
                finalizer.verify_final_report_join_reference(reference,after)

    def test_postexit_measurements_charge_fsynced_observer_files_and_real_elapsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            scope=Path(tmp);seen=[]
            def storage_inventory(path):
                names=sorted(p.name for p in Path(path).iterdir());seen.append(('inventory',names))
                return {'names':names}
            def allocate_storage(inventory,*,external_inventory):
                self.assertIn(observer.DISPOSITION_NAME,inventory['names'])
                return {'charged':inventory['names'],'external':external_inventory}
            def allocate_elapsed(cases,seconds):
                seen.append(('elapsed',seconds));return {'seconds':seconds}
            fake=types.SimpleNamespace(observe_authenticated_ledger_storage=lambda path:{'archive':'pinned'},
                _match_retained_ledger=lambda inventory,digest:self.assertEqual(digest,'a'*64),
                storage_inventory=storage_inventory,allocate_storage=allocate_storage,
                allocate_elapsed=allocate_elapsed)
            anchor=time.monotonic_ns()-10**6
            observer._write_exclusive(scope/observer.DISPOSITION_NAME,b'{}\n',32)
            storage,elapsed=observer._measure(scope,fake,[], 'a'*64,anchor)
            self.assertIn(observer.DISPOSITION_NAME,storage['charged'])
            self.assertGreaterEqual(elapsed['seconds'],.001)
            self.assertEqual([x[0] for x in seen],['inventory','elapsed'])

    def test_replay_does_not_trust_printed_status_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            scope=Path(tmp)
            printed={'status':'OBSERVED_FIXTURE_CHILD_JOIN_PASSED'}
            fake=types.SimpleNamespace(read_pinned_json=lambda *args,**kwargs:({'status':'OTHER'},pin(b'{}')),
                verify_launcher_completion_reference=finalizer.verify_launcher_completion_reference)
            with self.assertRaises(ValueError):
                observer.replay_launcher(scope,observer.canonical(printed)+b'\n',finalizer=fake,python='/usr/bin/python3')

    def test_external_replay_uses_both_compact_pins_and_fresh_full_join(self):
        with tempfile.TemporaryDirectory() as tmp:
            scope=Path(tmp);before=self.joined_fixture();before['scope']=str(scope)
            fixture_reference=finalizer.final_report_join_reference(before)
            fixture_raw=observer.canonical(fixture_reference)+b'\n'
            (scope/'compact-control-launch-stdout.log').write_bytes(fixture_raw)
            retained={'schema':'radio-native-v2-compact-control-launch-v1-disposition',
                'status':'OBSERVED_FIXTURE_CHILD_JOIN_PASSED','scope':str(scope),
                'fixture_child_complete_wait4_lifetime_observed':True,
                'independently_observed_fixture_child_join_qualified':True,
                'terminal_observer_own_future_termination_covered':False,
                'fixture_stdout_pin':pin(fixture_raw),
                'storage_after_fixture_termination_with_remaining_terminal_allowance':
                    {'external_ledger_inventory_sha256':'a'*64},**observer.AUTHORITY}
            retained_pin=pin(observer.canonical(retained)+b'\n')
            launcher_raw=observer.canonical(finalizer.launcher_completion_reference(retained,retained_pin))+b'\n'
            after=copy.deepcopy(before)
            after['storage_after_report_writer_lifetime_with_final_reservation']={'metadata_bytes':900}
            seen=[]
            def read_json(path,**kwargs):
                if Path(path).name=='compact-control-launch-disposition.json':return retained,retained_pin
                if Path(path).name=='worker-result.json':return {'synthetic':True},pin(b'worker')
                return {},pin(b'metadata')
            def joined_replay(*args,**kwargs):seen.append('full_join_replayed');return after
            def match_ledger(inventory,digest):
                self.assertEqual(inventory,{'fresh':'ledger'});self.assertEqual(digest,'a'*64);seen.append('ledger_reobserved')
            fake=types.SimpleNamespace(read_pinned_json=read_json,
                verify_launcher_completion_reference=finalizer.verify_launcher_completion_reference,
                verify_final_report_join_reference=finalizer.verify_final_report_join_reference,
                FINAL_INPUT_NAME=finalizer.FINAL_INPUT_NAME,FINAL_NAME=finalizer.FINAL_NAME,
                FINAL_WRITER_OBSERVATION_NAME=finalizer.FINAL_WRITER_OBSERVATION_NAME,
                join_final_report_lifetime=joined_replay,_worker_cases=lambda value:([],{}),
                observe_authenticated_ledger_storage=lambda scope:{'fresh':'ledger'},_match_retained_ledger=match_ledger)
            replay,cases,digest=observer.replay_launcher(scope,launcher_raw,finalizer=fake,python='/usr/bin/python3')
            self.assertTrue(replay['descendant_join_replayed']);self.assertEqual(cases,[]);self.assertEqual(digest,'a'*64)
            self.assertEqual(seen,['full_join_replayed','ledger_reobserved'])
            after['persisted_final_report_pin']=pin(b'swapped report')
            with self.assertRaisesRegex(ValueError,'Compact terminal reference'):
                observer.replay_launcher(scope,launcher_raw,finalizer=fake,python='/usr/bin/python3')


if __name__=='__main__':unittest.main()
