"""Synthetic supervisor dispatch/wait/proc fixtures; never creates a process."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE=Path(__file__).parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    value=importlib.util.module_from_spec(spec);sys.modules[name]=value
    spec.loader.exec_module(value);return value
proc=load('proc_custody',HERE/'proc_custody.py')
fixtures=load('proc_fixture',HERE/'test_proc_custody.py')
sup=load('F_supervisor_fixture',HERE/'leaf_supervisor.py')
# The fixture module loads its own source instance; use the injected observer
# class and exception identities so no real proc reader can be reached.
fixtures.module=proc


class SupervisorTests(unittest.TestCase):
    def run_fake(self,mode='success'):
        events=[];state={};fd_handles=[]
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);limits=dict(sup.DEFAULT_LIMITS)
            limits['artifact_root']=str(root)
            for name in ('python','guard','exec_seal','phase2'):
                path=root/(name+'.synthetic');raw=('fake '+name).encode();path.write_bytes(raw)
                limits[name+'_path']=str(path);limits[name+'_sha256']=hashlib.sha256(raw).hexdigest()
            argv=[limits['python_path'],'-I','-B','-S',str(root/'never-run-driver.py')]
            def fs_factory(budget):
                fs=fixtures.FakeFS(budget);fs.parent_chain=(1000,os.getpid())
                if state.get('terminal'):
                    fs.rows[1001]['stat']=fixtures.stats(state='Z')
                    fs.rows[1001]['status']=fixtures.status(state='Z')
                def close_root():events.append('root-close')
                fs.close_root=close_root;state['fs']=fs;return fs
            def popen(command,**kwargs):
                events.append('fake-dispatch')
                required=dict(schema='radio-leaf-guard-v1',no_new_privs=1,seccomp_mode=2,
                    descendants_denied=True,sockets_denied=True,async_io_denied=True,phase2_required=True,
                    parent_death_signal=int(sup.signal.SIGKILL),expected_parent_pid=os.getpid(),
                    parent_race_checked=True,pdeathsig_clear_denied=True,credential_mutation_denied=True,
                    python_privilege_metadata_refused=True)
                statusfd=int(command[command.index('--status-fd')+1]);os.write(statusfd,json.dumps(required).encode())
                phase=dict(schema='radio-leaf-phase2-v1',no_new_privs=1,seccomp_mode=2,
                           exec_denied=True,scientific_imports_started=False)
                streams=[]
                for raw in (b'synthetic stdout\n',sup.PHASE2_MARKER+json.dumps(phase).encode()+b'\n'):
                    readfd,writefd=os.pipe();os.write(writefd,raw);os.close(writefd)
                    stream=os.fdopen(readfd,'rb',buffering=0);fd_handles.append(stream);streams.append(stream)
                process=SimpleNamespace(pid=6,returncode=None,stdout=streams[0],stderr=streams[1])
                state['process']=process;state['command']=command;return process
            calls=0
            def waitid(kind,pid,flags):
                nonlocal calls
                calls+=1;events.append('waitid')
                self.assertEqual(pid,6);self.assertTrue(flags&os.WNOWAIT)
                if calls==1:return None
                state['terminal']=True;fs=state.get('fs')
                if fs is not None:
                    fs.rows[1001]['stat']=fixtures.stats(state='Z')
                    fs.rows[1001]['status']=fixtures.status(state='Z')
                if mode=='missing-io':fs.rows[1001]['io']=FileNotFoundError('synthetic missing terminal IO')
                if mode=='identity-drift':fs.rows[1001]['stat']=fixtures.stats(start=100,state='Z')
                return SimpleNamespace(si_pid=6,si_code=os.CLD_EXITED,si_status=3 if mode=='nonzero' else 0)
            def wait4(pid,flags):
                events.append('wait4');self.assertEqual(pid,6)
                # The terminal observer must read the retained zombie before reap.
                self.assertGreaterEqual(events.count('waitid'),3)
                self.assertIn((1001,'io'),state['fs'].reads)
                usage=SimpleNamespace(ru_utime=.01,ru_stime=.01,ru_maxrss=100,
                    ru_inblock=0,ru_oublock=0,ru_nvcsw=1,ru_nivcsw=0)
                return (6,(3 if mode=='nonzero' else 0)<<8,usage)
            selector=sup.selectors.DefaultSelector();original_select=selector.select
            def select(timeout=None):
                if mode=='selector-failure' and 'process' in state:raise OSError('synthetic repeated selector failure')
                return original_select(timeout)
            with patch.object(proc,'ProcFS',side_effect=fs_factory),patch.object(sup.subprocess,'Popen',side_effect=popen),\
                 patch.object(sup.selectors,'DefaultSelector',return_value=selector),patch.object(selector,'select',side_effect=select),\
                 patch.object(sup.os,'waitid',side_effect=waitid),patch.object(sup.os,'wait4',side_effect=wait4),\
                 patch.object(sup.os,'killpg',side_effect=lambda *a:events.append('fake-kill')):
                record=sup.run_leaf(argv,{},str(root),str(root/'receipt'),limits,time.monotonic()+10)
            for stream in fd_handles:
                if not stream.closed:stream.close()
            persisted=json.loads((root/'receipt.custody.json').read_text())
            self.assertEqual(persisted,record);self.assertEqual(record['child_dispatches'],1)
            self.assertTrue(record['child_reaped']);self.assertEqual(events.count('wait4'),1)
            self.assertFalse(state['fs'].opened);self.assertIn('root-close',events)
            if mode=='selector-failure':self.assertFalse(record['guarded_leaf'])
            else:self.assertTrue(record['guarded_leaf'])
            self.assertGreater(record['proc_metadata_read_charge_bytes'],0)
            self.assertIsNone(record['proc_child_metadata_read_charge_bytes'])
            self.assertEqual(record['wrapped_python_argv'][1:4],['-I','-B','-S'])
            self.assertFalse(record['runtime_qualified']);self.assertFalse(record['scientific_authority'])
            return record

    def test_success_observes_namespace_zombie_then_wait4(self):
        record=self.run_fake()
        self.assertEqual(record['status'],'GUARDED_LEAF_COMPLETED_OBSERVATIONS_ONLY')
        self.assertEqual(record['terminal_proc']['io']['rchar'],0)
        self.assertTrue(record['terminal_proc']['wnowait_requested'])
        self.assertEqual(record['proc_resolution']['outer_proc_pid'],1001)
        self.assertEqual(record['proc_resolution']['local_wait_pid'],6)
    def test_missing_terminal_io_refuses_and_still_reaps(self):
        record=self.run_fake('missing-io')
        self.assertEqual(record['status'],'FAILED_CLOSED');self.assertIsNone(record['terminal_proc']['io'])
        self.assertFalse(record['terminal_proc']['available']);self.assertTrue(record['terminal_proc']['terminal_observed'])
    def test_child_starttime_drift_refuses_and_still_reaps(self):
        record=self.run_fake('identity-drift')
        self.assertEqual(record['status'],'FAILED_CLOSED');self.assertIsNone(record['terminal_proc']['io'])
    def test_nonzero_exit_retains_terminal_receipt(self):
        record=self.run_fake('nonzero')
        self.assertEqual(record['status'],'FAILED_CLOSED');self.assertEqual(record['child_exit_code'],3)
        self.assertTrue(record['terminal_proc']['available']);self.assertIn('nonzero_leaf_exit',record['failures'])
    def test_repeated_selector_failure_cannot_skip_terminal_wait4(self):
        record=self.run_fake('selector-failure')
        self.assertEqual(record['status'],'FAILED_CLOSED');self.assertTrue(record['terminal_proc']['available'])
        self.assertTrue(any('selector' in failure for failure in record['failures']))


if __name__=='__main__':unittest.main()
