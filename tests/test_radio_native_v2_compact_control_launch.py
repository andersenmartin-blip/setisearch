"""Tiny finite-observer/preflight checks; no marker or maximum control runs."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest import mock

import radio_native_v2_compact_control_launch as launch
import radio_native_v2_resource_finalization as finalizer

ROOT = Path(__file__).resolve().parents[1]
PYTHON = str(Path(sys.executable).resolve())
TINY_ENV = {'PATH':'/usr/bin:/bin', 'LANG':'C', 'LC_ALL':'C'}
PUBLIC_ENV = {'PATH':'/usr/bin:/bin', 'LANG':'C', 'LC_ALL':'C', 'HOME':'/nonexistent',
    'PYTHONSAFEPATH':'1', 'PYTHONNOUSERSITE':'1', 'GIT_CONFIG_NOSYSTEM':'1',
    'GIT_CONFIG_GLOBAL':'/dev/null', 'GIT_TERMINAL_PROMPT':'0', 'GIT_NO_LAZY_FETCH':'1'}


def wire(value): return launch.canonical(value)+b'\n'


def file_descriptor(root, relative, value):
    path = root/relative; path.parent.mkdir(parents=True, exist_ok=True)
    raw = wire(value); path.write_bytes(raw)
    return {'path':relative, 'bytes':len(raw), 'sha256':hashlib.sha256(raw).hexdigest()}


def tiny_config(root):
    plan = {'runtime_executables':{'python':{'path':PYTHON}}}
    inputs = {name:file_descriptor(root, 'config/'+name+'.json', value)
        for name,value in (('plan',plan), ('complete_freeze',{}), ('preread',{}), ('activation_readback',{}))}
    return {'schema':launch.CONFIG_SCHEMA, 'namespace':launch.NAMESPACE,
        'mode':'PROSPECTIVE_NOT_EXECUTED', 'repository_root':str(root),
        'scope':str(root/'tiny-scope'), 'inputs':inputs}


def tiny_worker():
    cases = [{'ordinal':ordinal, 'source_case_id':launch.NAMESPACE+f'/case{ordinal:02d}',
        'preparation_through_lossless_seconds':0.0, 'continuous_verifier_append_seconds':0.0,
        'calls':0, 'request_bytes':0, 'response_bytes':0,
        'maximum_individual_material_process_rss_bytes':1} for ordinal in range(8)]
    return {'status':'PENDING_FINAL_MEASUREMENT_JOIN', 'cases':cases,
        'maximum_individual_material_process_rss_bytes':1, **finalizer.AUTHORITY}


def tiny_external(root, scope):
    """Explicit three-component tiny fixture; no actual journal is consumed."""
    rows=[]; components=[]
    for ordinal,role in enumerate(finalizer.EXTERNAL_STORAGE_ROLES):
        retained=root/('tiny-'+role); retained.mkdir(mode=0o700)
        path=retained/'tiny-retained.txt'; path.write_bytes(b'bounded synthetic retained metadata only\n')
        selected=[]
        for path,kind in ((retained,'directory'),(path,'file')):
            info=path.lstat()
            row={'component':role, 'path':str(path), 'kind':kind,
                'device':info.st_dev, 'inode':info.st_ino, 'mode':info.st_mode & 0o7777,
                'nlink':info.st_nlink, 'uid':info.st_uid, 'gid':info.st_gid,
                'bytes':info.st_size, 'allocated_bytes':info.st_blocks*512,
                'mtime_ns':info.st_mtime_ns, 'ctime_ns':info.st_ctime_ns}
            if kind=='file' and role!='prospective_ledger':
                raw=path.read_bytes(); row['raw_pin']={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
            selected.append(row)
        components.append({'role':role,'root':str(retained),'observation_sha256':str(ordinal+1)*64,
            'entry_count':len(selected),'logical_bytes':sum(row['bytes'] for row in selected),
            'allocated_bytes':sum(row['allocated_bytes'] for row in selected)})
        rows.extend(selected)
    return {'schema':finalizer.EXTERNAL_STORAGE_SCHEMA,'current_control_scope':str(scope),
        'components':components,'rows':rows,'entry_count':len(rows),
        'logical_bytes':sum(row['bytes'] for row in rows),'allocated_bytes':sum(row['allocated_bytes'] for row in rows),
        'charged_once':True,'read_only':True,'execution_authorized':False,
        'whole_control_qualified':False,'lifetime_accounting_proved':False}


class FiniteChildObservationTests(unittest.TestCase):
    def test_actual_tiny_child_stdout_stderr_and_full_wait4_peak(self):
        argv = [PYTHON,'-I','-S','-B','-c',
            'import sys,time; x=bytearray(6*1024**2); print("tiny complete output"); '
            'sys.stderr.write("tiny stderr\\n"); time.sleep(0.02)']
        observation, stdout, stderr = launch.observe_child(argv,TINY_ENV,
            deadline_monotonic_ns=time.monotonic_ns()+3*10**9)
        self.assertEqual(stdout,b'tiny complete output\n'); self.assertEqual(stderr,b'tiny stderr\n')
        self.assertEqual(observation['exit_code'],0); self.assertIsNone(observation['reason'])
        self.assertTrue(observation['direct_child_reaped'])
        self.assertTrue(observation['includes_entire_direct_child_lifetime'])
        self.assertTrue(observation['complete_pipe_output'])
        self.assertGreater(observation['wait4_ru_maxrss_bytes'],0)
        self.assertIsNone(observation['procfs_sampled_peak_rss_bytes'])
        self.assertFalse(observation['procfs_sampling_qualified'])
        self.assertFalse(observation['terminal_observer_own_future_termination_covered'])
        with self.assertRaises(ChildProcessError): os.waitpid(observation['namespace_child_pid'],os.WNOHANG)

    def test_original_deadline_kills_and_reaps_tiny_child(self):
        start = time.monotonic()
        observation, stdout, stderr = launch.observe_child([PYTHON,'-I','-S','-B','-c','import time; time.sleep(5)'],
            TINY_ENV, deadline_monotonic_ns=time.monotonic_ns()+100_000_000)
        self.assertLess(time.monotonic()-start,1.5)
        self.assertIn('deadline',observation['reason'])
        self.assertTrue(observation['direct_child_reaped'])
        self.assertNotEqual(observation['exit_code'],0)
        self.assertFalse(observation['complete_pipe_output'])

    def test_inherited_pipe_cannot_extend_deadline_or_recycle_root_before_kill(self):
        start = time.monotonic()
        argv = [PYTHON,'-I','-S','-B','-c',
            'import subprocess,sys; subprocess.Popen([sys.executable,"-I","-S","-B","-c","import time; time.sleep(5)"])']
        observation,_,_ = launch.observe_child(argv,TINY_ENV,
            deadline_monotonic_ns=time.monotonic_ns()+150_000_000)
        self.assertLess(time.monotonic()-start,1.5)
        self.assertTrue(observation['direct_child_reaped'])
        self.assertIn('deadline',observation['reason'])
        self.assertFalse(observation['complete_pipe_output'])
        self.assertFalse(observation['descendant_scope_qualified_by_this_observer'])

    def test_stdout_and_stderr_caps_are_distinct_and_never_silently_truncate(self):
        for stream in ('stdout','stderr'):
            with self.subTest(stream=stream):
                argv = [PYTHON,'-I','-S','-B','-c',
                    'import sys,time; sys.'+stream+'.write("x"*10000); sys.'+stream+'.flush(); time.sleep(5)']
                observation,stdout,stderr = launch.observe_child(argv,TINY_ENV,
                    deadline_monotonic_ns=time.monotonic_ns()+3*10**9, stdout_cap=1024,stderr_cap=1024)
                self.assertIn(stream+' exceeded',observation['reason'])
                self.assertTrue(observation['direct_child_reaped'])
                self.assertFalse(observation['complete_pipe_output'])
                self.assertLessEqual(len(stdout),1024); self.assertLessEqual(len(stderr),1024)
                self.assertGreater(observation['observed_output_bytes'][stream],1024)

    def test_selector_setup_failure_still_kills_reaps_and_closes_child_pipes(self):
        captured = []; real_popen = subprocess.Popen
        def capture(*args,**kwargs):
            child = real_popen(*args,**kwargs); captured.append(child); return child
        with mock.patch.object(launch.subprocess,'Popen',side_effect=capture), \
                mock.patch.object(launch.selectors,'DefaultSelector',side_effect=RuntimeError('tiny injected setup failure')):
            observation,_,_ = launch.observe_child([PYTHON,'-I','-S','-B','-c','import time; time.sleep(5)'],
                TINY_ENV, deadline_monotonic_ns=time.monotonic_ns()+3*10**9)
        self.assertTrue(observation['direct_child_reaped'])
        self.assertIn('observer setup/read failed',observation['reason'])
        self.assertEqual(len(captured),1)
        self.assertTrue(captured[0].stdout.closed); self.assertTrue(captured[0].stderr.closed)

    def test_nonzero_exit_is_retained_as_failed_evidence(self):
        observation,stdout,stderr = launch.observe_child([PYTHON,'-I','-S','-B','-c',
            'import sys; print("tiny failure"); sys.exit(7)'],TINY_ENV,
            deadline_monotonic_ns=time.monotonic_ns()+3*10**9)
        self.assertEqual(observation['exit_code'],7)
        self.assertEqual(stdout,b'tiny failure\n')
        self.assertTrue(observation['direct_child_reaped'])


class FixedConfigAndSourcePreflightTests(unittest.TestCase):
    def test_fixed_config_exact_pin_and_canonical_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); config = tiny_config(root)
            path = root/launch.CONFIG_PATH; raw = wire(config); path.write_bytes(raw)
            with mock.patch.object(launch,'REPO',root):
                self.assertEqual(launch.load_launch_config(hashlib.sha256(raw).hexdigest()),config)
                with self.assertRaisesRegex(ValueError,'independent immutable readback'):
                    launch.load_launch_config('a'*64)
                path.write_bytes(b' '+raw)
                with self.assertRaisesRegex(ValueError,'canonical'):
                    launch.load_launch_config(hashlib.sha256(b' '+raw).hexdigest())

    def test_scope_input_aliases_and_extra_config_keys_refuse(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); original = tiny_config(root)
            mutations = []
            changed=copy.deepcopy(original); changed['scope']=str(root.parent/'outside'); mutations.append(changed)
            changed=copy.deepcopy(original); changed['inputs']['plan']['path']='config/../plan.json'; mutations.append(changed)
            changed=copy.deepcopy(original); changed['unexpected']='override'; mutations.append(changed)
            changed=copy.deepcopy(original); changed['inputs']['preread']=changed['inputs']['plan']; mutations.append(changed)
            with mock.patch.object(launch,'REPO',root):
                for changed in mutations:
                    with self.subTest(config=changed), self.assertRaises(ValueError): launch.validate_launch_config(changed)

    def test_bootstrap_source_pin_cannot_be_selected_by_supplied_plan(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path=root/launch.ENVIRONMENT; path.parent.mkdir()
            marker=root/'unchecked-executed'; raw=('from pathlib import Path\nPath('+repr(str(marker))+').write_text("bad")\n').encode()
            path.write_bytes(raw)
            with mock.patch.object(launch,'REPO',root):
                with self.assertRaisesRegex(ValueError,'independently retained pin'):
                    launch._source_module('tiny_unchecked_environment',launch.ENVIRONMENT)
            self.assertFalse(marker.exists())

    def test_preflight_refuses_false_isolation_before_importing_any_auditor(self):
        # The integrated suite itself runs -I -S -B. Model an actual -S -B
        # interpreter explicitly so this negative does not depend on its host.
        flags=types.SimpleNamespace(isolated=0,no_site=1,dont_write_bytecode=1)
        with mock.patch.object(launch.sys,'flags',flags), \
                mock.patch.object(launch,'_source_module') as source:
            with self.assertRaisesRegex(ValueError,'Actual -I -S -B'):
                launch.preflight({}, {})
            source.assert_not_called()

    def test_original_repository_and_c_journal_binding_precedes_imports(self):
        flags=types.SimpleNamespace(isolated=1,no_site=1,dont_write_bytecode=1)
        for root, ledger in ((str(ROOT.parent/'other'), str(ROOT/'.radio-native-v2-invocation-ledger-20261002c')),
                (str(ROOT), str(ROOT/'.radio-native-v2-invocation-ledger')),
                (str(ROOT), str(ROOT/'nested'/'.radio-native-v2-invocation-ledger-20261002c'))):
            with self.subTest(root=root, ledger=ledger), mock.patch.object(launch.sys,'flags',flags), \
                    mock.patch.object(launch,'_source_module') as source:
                with self.assertRaisesRegex(ValueError,'independently selected original repository'):
                    launch.preflight({'invocation_repository_root':root, 'invocation_ledger_root':ledger}, {})
                source.assert_not_called()

    def test_pinned_source_import_ignores_forged_cached_bytecode(self):
        import marshal
        import struct
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); package=root/'numpy'; package.mkdir()
            source=package/'__init__.py'; raw=b'value=7\n'; source.write_bytes(raw)
            cached=Path(importlib.util.cache_from_source(str(source))); cached.parent.mkdir()
            marker=root/'cached-executed'
            payload=compile('from pathlib import Path; Path('+repr(str(marker))+').write_text("bad")',str(source),'exec')
            info=source.stat(); cached.write_bytes(importlib.util.MAGIC_NUMBER+
                struct.pack('<III',0,int(info.st_mtime),info.st_size)+marshal.dumps(payload))
            loader=launch._PinnedSourceLoader(str(source),hashlib.sha256(raw).hexdigest(),package=True)
            module=types.ModuleType('tiny_source_numpy'); loader.exec_module(module)
            self.assertEqual(module.value,7); self.assertFalse(marker.exists())

    def test_actual_no_site_numpy_import_uses_runtime_derived_pinned_sources(self):
        historical=ROOT/'config/radio_native_v2_runtime_custody_integration_20261002b.runtime.json'
        frozen=json.loads(historical.read_bytes())
        roots=[path[:-len('/numpy/__init__.py')] for path in frozen['runtime_sha256s'] if path.endswith('/numpy/__init__.py')]
        self.assertEqual(len(roots),1)
        program='\n'.join([
            'import hashlib,json,sys',
            'from pathlib import Path',
            'source=Path(sys.argv[1]); raw=source.read_bytes()',
            'assert hashlib.sha256(raw).hexdigest()==sys.argv[2]',
            'm={"__name__":"tiny_numpy_preflight","__file__":str(source)}',
            'exec(compile(raw,str(source),"exec"),m)',
            'freeze=json.loads(Path(sys.argv[3]).read_bytes())',
            'site=sys.argv[4]',
            'finder=m["_PinnedPreflightFinder"](freeze,site)',
            'sys.meta_path.insert(0,finder); sys.path.append(site)',
            'import numpy',
            'assert numpy.__loader__.__class__.__name__=="_PinnedSourceLoader"',
            'assert sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode',
            'print(json.dumps({"version":numpy.__version__,"source_loader":True,"no_site":True},sort_keys=True))'])
        source=ROOT/launch.SELF
        process=subprocess.run([PYTHON,'-I','-S','-B','-c',program,str(source),
            hashlib.sha256(source.read_bytes()).hexdigest(),str(historical),roots[0]],
            capture_output=True,env=PUBLIC_ENV,timeout=30)
        self.assertEqual(process.returncode,0,process.stderr.decode())
        value=json.loads(process.stdout); self.assertTrue(value['source_loader']); self.assertTrue(value['no_site'])
        self.assertEqual(value['version'],frozen['numpy'])

    def test_cli_rejects_path_overrides_extra_interpreter_flags_and_missing_digest(self):
        source=ROOT/launch.SELF
        for argv in ([PYTHON,'-I','-S','-B',str(source),'--run'],
                [PYTHON,'-I','-S','-B',str(source),'--run','--config-sha256','a'*64,'--scope','/tmp/forbidden'],
                [PYTHON,'-I','-S','-B','-X','utf8',str(source),'--run','--config-sha256','a'*64]):
            with self.subTest(argv=argv):
                result=subprocess.run(argv,capture_output=True,env=PUBLIC_ENV,timeout=10)
                self.assertNotEqual(result.returncode,0)
                self.assertEqual(result.stdout,b'')


class TinyLauncherIntegrationTests(unittest.TestCase):
    def execute(self, directory, *, failure=None):
        root=Path(directory); config=tiny_config(root); scope=Path(config['scope'])
        events=[]; external=tiny_external(root,scope); worker=tiny_worker()
        prepared={'schema':launch.SCHEMA+'-preflight','environment':PUBLIC_ENV,
            'status':'SYNTHETIC_TINY_PREFLIGHT_ONLY','independent_original_scope_recomputed':False}
        observation={'schema':launch.SCHEMA+'-child-observation','reason':None,'exit_code':0,
            'maximum_observed_direct_child_rss_bytes':1,'complete_pipe_output':True,
            'direct_child_reaped':True,'includes_entire_direct_child_lifetime':True}
        stored_summary={}
        def audit(plan,freeze):
            events.append('preflight')
            self.assertFalse(scope.exists())
            if failure=='preflight': raise ValueError('tiny preflight refusal')
            return prepared
        def observe(argv,environment,**kwargs):
            self.assertEqual(events,['preflight']); events.append('fixture-child')
            self.assertEqual(environment,PUBLIC_ENV)
            anchor=int(argv[-1]); self.assertLessEqual(anchor,time.monotonic_ns())
            self.assertEqual(kwargs['deadline_monotonic_ns'],anchor+launch.RUN_SECONDS*10**9)
            scope.mkdir(mode=0o700)
            (scope/'cases').mkdir()
            for ordinal in range(8): (scope/'cases'/f'case{ordinal:02d}').mkdir()
            for name,value in ((finalizer.FINAL_INPUT_NAME,{}),(finalizer.FINAL_NAME,{}),
                    (finalizer.FINAL_WRITER_OBSERVATION_NAME,{}),('worker-result.json',worker)):
                (scope/name).write_bytes(wire(value))
            stored_summary.update({'scope':str(scope),'complete_resource_measurement_join_qualified':False,
                'independent_driver_measurement_disposition':{'storage':{
                    'external_ledger_inventory_sha256':finalizer._ledger_inventory_pin(external)}},
                'storage_after_report_writer_lifetime_with_final_reservation':finalizer.allocate_storage(
                    finalizer.storage_inventory(scope),external_inventory=external)})
            stdout=wire(stored_summary)
            self.assertLessEqual(len(stdout),launch.STDOUT_CAP)
            if failure=='exit': observation['exit_code']=7
            if failure=='output-cap': observation['reason']='stdout exceeded fixed retained output cap'
            if failure=='malformed-summary': stdout=b'{"not_canonical":true}'
            return observation,stdout,b'tiny injected stderr\n' if failure=='stderr' else b''
        def join(*args,**kwargs):
            self.assertFalse((scope/launch.STDOUT_NAME).exists(), 'Replay must precede metadata inventory transition')
            events.append('independent-join')
            current=copy.deepcopy(stored_summary)
            current['storage_after_report_writer_lifetime_with_final_reservation']=finalizer.allocate_storage(
                finalizer.storage_inventory(scope),external_inventory=external)
            if failure=='join-drift': current['scope']='different'
            return current
        resource_adapter=types.SimpleNamespace(**{name:getattr(finalizer,name) for name in (
            'FINAL_INPUT_NAME','FINAL_NAME','FINAL_WRITER_OBSERVATION_NAME',
            'read_pinned_json','storage_inventory','allocate_storage','allocate_elapsed','_worker_cases','_match_retained_ledger')})
        resource_adapter.join_final_report_lifetime=join
        resource_adapter.observe_authenticated_ledger_storage=lambda ignored:external
        if failure=='storage': resource_adapter.allocate_storage=lambda *args,**kwargs:(_ for _ in ()).throw(ValueError('tiny storage refusal'))
        if failure=='elapsed': resource_adapter.allocate_elapsed=lambda *args,**kwargs:(_ for _ in ()).throw(ValueError('tiny elapsed refusal'))
        calls=[]; real_write=launch._write_exclusive
        def writer(path,raw,maximum):
            calls.append(Path(path).name)
            pin=real_write(path,raw,maximum)
            if failure=='late-check' and Path(path).name==launch.DISPOSITION_NAME:
                resource_adapter.allocate_elapsed=lambda *args,**kwargs:(_ for _ in ()).throw(ValueError('tiny late elapsed refusal'))
            return pin
        with mock.patch.object(launch,'REPO',root),mock.patch.object(launch,'_launch_entered',False), \
                mock.patch.object(launch,'preflight',side_effect=audit), \
                mock.patch.object(launch,'observe_child',side_effect=observe), \
                mock.patch.object(launch,'_source_module',return_value=resource_adapter), \
                mock.patch.object(launch,'_write_exclusive',side_effect=writer), \
                mock.patch.object(launch.subprocess,'Popen') as actual_launch:
            if failure is None:
                result=launch.launch_control(config)
                self.assertEqual(result['status'],'OBSERVED_FIXTURE_CHILD_JOIN_PASSED')
                self.assertFalse(result['complete_resource_measurement_join_qualified'])
                self.assertFalse(result['terminal_observer_own_future_termination_covered'])
                self.assertTrue(result['persistent_ledger_reobserved_and_charged_after_fixture_termination'])
                retained=json.loads((scope/launch.DISPOSITION_NAME).read_bytes()); self.assertEqual(retained,result)
                self.assertLessEqual((scope/launch.DISPOSITION_NAME).stat().st_size,launch.DISPOSITION_CAP)
                self.assertEqual((scope/launch.STDOUT_NAME).read_bytes(),wire(stored_summary))
                self.assertGreater(result['storage_after_fixture_termination_with_remaining_terminal_allowance']
                    ['metadata_logical_bytes_present'],stored_summary['storage_after_report_writer_lifetime_with_final_reservation']
                    ['metadata_logical_bytes_present'])
                self.assertEqual(events,['preflight','fixture-child','independent-join'])
                self.assertFalse((scope/launch.FAILURE_NAME).exists())
            else:
                with self.assertRaises((RuntimeError,ValueError)): launch.launch_control(config)
                if failure=='preflight':
                    self.assertFalse(scope.exists()); self.assertEqual(events,['preflight'])
                else:
                    closed=json.loads((scope/launch.FAILURE_NAME).read_bytes())
                    self.assertEqual(closed['status'],'CLOSED_FAILED')
                    self.assertFalse(closed['complete_resource_measurement_join_qualified'])
                    self.assertFalse(closed['automatic_retry'])
                    if failure=='late-check': self.assertTrue((scope/launch.DISPOSITION_NAME).exists())
            actual_launch.assert_not_called()
        return root,scope,events

    def test_tiny_join_replays_before_metadata_transition_then_charges_new_files_and_ledger(self):
        with tempfile.TemporaryDirectory() as directory: self.execute(directory)

    def test_preflight_refusal_launches_nothing_and_invents_no_scope(self):
        with tempfile.TemporaryDirectory() as directory: self.execute(directory,failure='preflight')

    def test_postscope_failures_retain_closed_endpoint_without_retry_or_overwrite(self):
        for failure in ('exit','stderr','output-cap','malformed-summary','join-drift','storage','elapsed','late-check'):
            with self.subTest(failure=failure),tempfile.TemporaryDirectory() as directory:
                self.execute(directory,failure=failure)

    def test_reused_scope_and_second_process_entry_are_refused_before_any_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); config=tiny_config(root); scope=Path(config['scope']); scope.mkdir()
            with mock.patch.object(launch,'REPO',root),mock.patch.object(launch,'_launch_entered',False), \
                    mock.patch.object(launch,'preflight') as audit:
                with self.assertRaisesRegex(ValueError,'Fresh exclusive'): launch.launch_control(config)
                with self.assertRaisesRegex(RuntimeError,'no retry'): launch.launch_control(config)
                audit.assert_not_called()
            self.assertEqual(list(scope.iterdir()),[])

    def test_monotonic_anchor_rejects_future_or_fabricated_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory); config=tiny_config(root)
            for value in (True,0,-1,time.monotonic_ns()+10**10):
                with self.subTest(value=value),mock.patch.object(launch,'REPO',root), \
                        mock.patch.object(launch,'_launch_entered',False),self.assertRaisesRegex(ValueError,'monotonic anchor'):
                    launch.launch_control(config,admission_start_monotonic_ns=value)
            self.assertFalse(Path(config['scope']).exists())


if __name__=='__main__': unittest.main()
