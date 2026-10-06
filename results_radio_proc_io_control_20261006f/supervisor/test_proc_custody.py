"""Offline namespace/terminal fixtures only; no child, ptrace or native launch."""
import importlib.util
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

PATH=Path(__file__).with_name('proc_custody.py')
spec=importlib.util.spec_from_file_location('prospective_proc_test',PATH)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def status(pid=1001,parent=1000,chain=(1001,6),tgid=None,state='S',uid=None):
    uid=os.getuid() if uid is None else uid
    return ('Name:\tfixture\nPid:\t%d\nTgid:\t%d\nPPid:\t%d\nNSpid:\t%s\nThreads:\t1\nState:\t%s\n'
            'Uid:\t%d\t%d\t%d\t%d\nCapEff:\t0000000000000000\n'
            %(pid,pid if tgid is None else tgid,parent,' '.join(map(str,chain)),state,uid,uid,uid,uid))


def stats(pid=1001,parent=1000,start=99,state='S'):
    values=[state,str(parent)]+['0']*17+[str(start)]+['0']*3
    return str(pid)+' (fixture name with ) parenthesis) '+' '.join(values)+'\n'


IO='rchar: 0\nwchar: 0\nsyscr: 0\nsyscw: 0\nread_bytes: 0\nwrite_bytes: 0\ncancelled_write_bytes: 0\n'


class FakeFS:
    def __init__(self,budget):
        self.budget=budget;self.ns=(9,123);self.parent_chain=(1000,5)
        self.rows={1001:dict(status=status(),stat=stats(),io=IO,namespace=self.ns,identity=(8,10))}
        self.rows[1000]=dict(status=status(1000,1,self.parent_chain),stat=stats(1000,1,88),namespace=self.ns,identity=(8,9))
        self.root_directory=(8,1);self.root_drift=False;self.owner_uid=None
        self.children_text='1001';self.children_missing=False;self.opened=set();self.closed=[]
        self.read_hook=None;self.reads=[];self.named_drift=False
    def charge(self,body,label):
        self.budget.operation('fake-read',label);self.budget.received_bytes+=len(body.encode())
        if self.budget.received_bytes>self.budget.read_limit:raise module.Refusal('aggregate read cap')
        return body
    def self_status(self):
        self.rows[1000]['status']=status(1000,1,self.parent_chain,uid=self.owner_uid)
        return self.charge(self.rows[1000]['status'],'self-status')
    def self_namespace(self):self.budget.operation('fake-self-ns','self');return self.ns
    def check_root(self):
        self.budget.operation('fake-root-check','root')
        if self.root_drift:raise module.Refusal('root drift')
        return self.root_directory
    def children(self,tid):
        self.budget.operation('fake-children',tid)
        if self.children_missing:
            self.budget.errors+=1;raise FileNotFoundError('fixture missing children')
        return self.charge(self.children_text,'children')
    def list_pids(self):self.budget.operation('fake-list','proc');return sorted(self.rows)
    def open_dir(self,pid):self.budget.operation('fake-open',pid);self.opened.add(pid);return pid
    def dir_identity(self,fd):self.budget.operation('fake-stat',fd);return self.rows[fd]['identity']
    def named_identity(self,pid):
        self.budget.operation('fake-named-stat',pid)
        return (8,999) if self.named_drift and pid==1001 else self.rows[pid]['identity']
    def read_at(self,fd,name):
        self.reads.append((fd,name))
        if self.read_hook:self.read_hook(fd,name,len(self.reads))
        body=self.rows[fd][name]
        if isinstance(body,Exception):self.budget.errors+=1;raise body
        return self.charge(body,name)
    def namespace_at(self,fd):self.budget.operation('fake-ns',fd);return self.rows[fd]['namespace']
    def close(self,fd):self.closed.append(fd);self.opened.discard(fd)


class ResolverTests(unittest.TestCase):
    def setup(self):
        b=module.Budget();f=FakeFS(b);return b,f
    def test_outer_pid_resolved_and_held_then_closed(self):
        b,f=self.setup();bound=module.resolve_child(6,b,fs=f,local_parent_pid=5)
        self.assertEqual((bound.outer_pid,bound.local_pid,bound.starttime),(1001,6,99))
        self.assertEqual(bound.route,'parent-task-children');self.assertGreater(b.received_bytes,0)
        self.assertEqual(f.opened,{1000,1001});bound.close(f);self.assertFalse(f.opened)
    def test_proc_scan_fallback_is_bounded_and_recorded(self):
        b,f=self.setup();f.children_missing=True
        bound=module.resolve_child(6,b,fs=f,local_parent_pid=5)
        self.assertEqual(bound.route,'bounded-proc-scan');self.assertGreater(b.errors,0);bound.close(f)
    def test_wrong_chain_index_depth_parent_namespace_and_thread_alias(self):
        mutations=[dict(status=status(chain=(6,999))),dict(status=status(chain=(1001,22,6))),
          dict(status=status(parent=2222)),dict(namespace=(9,999)),dict(status=status(tgid=22))]
        for mutation in mutations:
            b,f=self.setup();f.rows[1001].update(mutation)
            with self.subTest(mutation=mutation),self.assertRaises(module.Refusal):
                module.resolve_child(6,b,fs=f,local_parent_pid=5)
            self.assertFalse(f.opened);self.assertGreater(b.rejected_candidates,0)
    def test_multiple_namespace_depth_parent_and_child_can_match(self):
        b,f=self.setup();f.parent_chain=(1000,20,5);f.rows[1001]['status']=status(chain=(1001,21,6))
        bound=module.resolve_child(6,b,fs=f,local_parent_pid=5);bound.close(f)
    def test_wrong_direct_inner_proc_pid_is_not_selected(self):
        b,f=self.setup();f.rows[6]=dict(status=status(pid=6,parent=1,chain=(6,)),stat=stats(pid=6,parent=1),
                                     io=IO,namespace=(9,999),identity=(8,6))
        f.children_text='6 1001'
        bound=module.resolve_child(6,b,fs=f,local_parent_pid=5)
        self.assertEqual(bound.outer_pid,1001);self.assertIn(6,f.closed);bound.close(f)
    def test_ambiguous_matches_refused_with_cleanup(self):
        b,f=self.setup();f.rows[1002]=dict(status=status(pid=1002,chain=(1002,6)),stat=stats(pid=1002),
                                        io=IO,namespace=f.ns,identity=(8,20));f.children_text='1001 1002'
        with self.assertRaises(module.Refusal):module.resolve_child(6,b,fs=f,local_parent_pid=5)
        self.assertFalse(f.opened)
    def test_scan_count_and_read_budget_fail_without_partial_success(self):
        b=module.Budget(candidates=1);f=FakeFS(b);f.children_text='1001 1002'
        with self.assertRaises(module.Refusal):module.resolve_child(6,b,fs=f,local_parent_pid=5)
        b=module.Budget(read_bytes=5);f=FakeFS(b)
        with self.assertRaises(module.Refusal):module.resolve_child(6,b,fs=f,local_parent_pid=5)
    def test_owner_uid_and_starttime_are_bound(self):
        b,f=self.setup();f.owner_uid=os.getuid()+1
        with self.assertRaises(module.Refusal):module.resolve_child(6,b,fs=f,local_parent_pid=5)
        self.assertFalse(f.opened)
        b,f=self.setup()
        def hook(fd,name,count):
            if fd==1001:f.rows[1000]['stat']=stats(1000,1,89)
        f.read_hook=hook
        with self.assertRaises(module.Refusal):module.resolve_child(6,b,fs=f,local_parent_pid=5)
        self.assertFalse(f.opened)
    def test_matched_candidate_drift_cannot_be_ignored_for_second_match(self):
        b,f=self.setup();f.rows[1002]=dict(status=status(pid=1002,chain=(1002,6)),stat=stats(pid=1002),
                                        io=IO,namespace=f.ns,identity=(8,20));f.children_text='1001 1002'
        f.named_drift=True
        with self.assertRaises(module.Refusal):module.resolve_child(6,b,fs=f,local_parent_pid=5)
        self.assertFalse(f.opened);self.assertNotIn(1002,f.closed)
    def test_live_state_transition_without_identity_drift_is_admitted(self):
        b,f=self.setup();seen=0
        def hook(fd,name,count):
            nonlocal seen
            if fd==1001 and name=='stat':
                seen+=1
                if seen==2:f.rows[fd]['stat']=stats(state='R')
        f.read_hook=hook;bound=module.resolve_child(6,b,fs=f,local_parent_pid=5);bound.close(f)


class SnapshotTests(unittest.TestCase):
    def setup(self):
        b=module.Budget();f=FakeFS(b);bound=module.resolve_child(6,b,fs=f,local_parent_pid=5);return b,f,bound
    def test_zero_counters_are_present_not_missing(self):
        _,f,bound=self.setup();value=module.snapshot(bound,f)
        self.assertTrue(value['available']);self.assertEqual(value['io']['rchar'],0);bound.close(f)
    def test_pid_reuse_starttime_and_named_directory_change_refused(self):
        for kind in ('starttime','named'):
            _,f,bound=self.setup()
            if kind=='starttime':f.rows[1001]['stat']=stats(start=100)
            else:f.named_drift=True
            with self.subTest(kind=kind),self.assertRaises(module.Refusal):module.snapshot(bound,f)
            bound.close(f)
    def test_change_after_io_read_is_refused(self):
        _,f,bound=self.setup()
        def hook(fd,name,count):
            if name=='io':f.rows[fd]['stat']=stats(start=101)
        f.read_hook=hook
        with self.assertRaises(module.Refusal):module.snapshot(bound,f)
        bound.close(f)
    def test_owner_or_proc_root_drift_refuses_snapshot(self):
        for kind in ('uid','starttime','root'):
            _,f,bound=self.setup()
            if kind=='uid':f.rows[1000]['status']=status(1000,1,f.parent_chain,uid=os.getuid()+1)
            elif kind=='starttime':f.rows[1000]['stat']=stats(1000,1,89)
            else:f.root_drift=True
            with self.subTest(kind=kind),self.assertRaises(module.Refusal):module.snapshot(bound,f)
            bound.close(f)
    def test_negative_exported_io_fields_are_refused(self):
        _,f,bound=self.setup()
        for key in ('cancelled_write_bytes','rchar'):
            f.rows[1001]['io']=IO.replace(key+': 0',key+': -1')
            with self.subTest(key=key),self.assertRaises(module.Refusal):module.snapshot(bound,f)
        bound.close(f)
    def test_accounting_failure_still_closes_once_and_marks_closed(self):
        _,f,bound=self.setup();original=f.close
        def close(fd):
            original(fd);raise module.Refusal('injected operation cap')
        f.close=close
        with self.assertRaises(module.Refusal):bound.close(f)
        self.assertTrue(bound.closed);self.assertFalse(f.opened)
        count=len(f.closed);bound.close(f);self.assertEqual(len(f.closed),count)
    def test_terminal_wnowait_observation_does_not_reap(self):
        _,f,bound=self.setup();f.rows[1001]['stat']=stats(state='Z');f.rows[1001]['status']=status(state='Z')
        calls=[]
        def waitid(kind,pid,flags):
            calls.append((kind,pid,flags));return SimpleNamespace(si_pid=6,si_code=module.os.CLD_EXITED,si_status=0)
        with patch.object(module.os,'wait4',side_effect=AssertionError('observer must not reap')):
            result=module.terminal_observation(bound,f,waitid=waitid)
        self.assertTrue(result['available']);self.assertEqual(result['io']['rchar'],0)
        self.assertTrue(calls[0][2]&module.os.WNOWAIT);self.assertFalse(result['wait4_called_here']);bound.close(f)
    def test_missing_terminal_io_is_none_never_zero(self):
        _,f,bound=self.setup();f.rows[1001]['stat']=stats(state='Z');f.rows[1001]['status']=status(state='Z')
        f.rows[1001]['io']=FileNotFoundError('gone')
        result=module.terminal_observation(bound,f,waitid=lambda *a:SimpleNamespace(si_pid=6,si_code=module.os.CLD_EXITED,si_status=0))
        self.assertFalse(result['available']);self.assertIsNone(result['io']);self.assertTrue(result['terminal_observed']);bound.close(f)
    def test_terminal_race_wrong_child_or_live_state_refused(self):
        _,f,bound=self.setup()
        with self.assertRaises(module.Refusal):module.terminal_observation(bound,f,
            waitid=lambda *a:SimpleNamespace(si_pid=7,si_code=module.os.CLD_EXITED,si_status=0))
        missing=module.terminal_observation(bound,f,waitid=lambda *a:None)
        self.assertFalse(missing['terminal_observed']);self.assertIsNone(missing['io'])
        live=module.terminal_observation(bound,f,waitid=lambda *a:SimpleNamespace(si_pid=6,si_code=module.os.CLD_EXITED,si_status=0))
        self.assertFalse(live['available']);self.assertIn('zombie',live['error']);bound.close(f)


if __name__=='__main__':unittest.main()
