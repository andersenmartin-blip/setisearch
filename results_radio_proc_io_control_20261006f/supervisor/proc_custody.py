"""Prospective namespace-aware direct-child proc observer; stdlib only.

No child is started, traced, signalled, reaped, or qualified by importing this
module. Resolution/snapshots are metadata reads. The caller owns admission,
deadlines, guard dispatch and mandatory wait4. No scientific authority is issued.
"""
import base64
import hashlib
import os
from pathlib import Path
import stat
import time


class Refusal(Exception):
    pass


class Budget:
    def __init__(self, read_bytes=8*1024**2, operations=4096, candidates=1024):
        if any(type(n) is not int or n <= 0 for n in (read_bytes,operations,candidates)):
            raise Refusal('positive finite observer budgets required')
        self.read_limit=read_bytes;self.operation_limit=operations;self.candidate_limit=candidates
        self.received_bytes=0;self.operations=0;self.candidates=0;self.errors=0;self.events=[]
        self.rejected_candidates=0

    def operation(self, kind, path):
        self.operations+=1
        if self.operations>self.operation_limit:raise Refusal('observer operation cap')
        event={'kind':kind,'path':str(path),'operation':self.operations};self.events.append(event)
        return event

    def candidate(self):
        self.candidates+=1
        if self.candidates>self.candidate_limit:raise Refusal('candidate scan cap')

    def summary(self):
        return dict(read_received_bytes=self.received_bytes,read_limit=self.read_limit,
            operations=self.operations,operation_limit=self.operation_limit,
            candidates=self.candidates,candidate_limit=self.candidate_limit,errors=self.errors,
            rejected_candidates=self.rejected_candidates)


def directory_identity(st):
    if not stat.S_ISDIR(st.st_mode):raise Refusal('proc directory kind')
    return (st.st_dev,st.st_ino)


class ProcFS:
    """Finite explicit observer reads. Kernel procfs length is not st_size."""
    def __init__(self,budget,proc_root='/proc'):
        self.budget=budget;self.root=Path(proc_root);self.root_fd=None
        event=budget.operation('open-proc-root',self.root)
        try:
            self.root_fd=os.open(self.root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
            self.root_directory=directory_identity(os.fstat(self.root_fd))
            event['identity']=list(self.root_directory)
        except Exception as exc:
            budget.errors+=1;event.update(error_type=type(exc).__name__,errno=getattr(exc,'errno',None))
            if self.root_fd is not None:os.close(self.root_fd);self.root_fd=None
            raise

    def _stat(self,kind,path,*,dir_fd=None,follow_symlinks=True):
        event=self.budget.operation(kind,path)
        try:
            st=os.stat(path,dir_fd=dir_fd,follow_symlinks=follow_symlinks)
            event['identity']=[st.st_dev,st.st_ino];return st
        except Exception as exc:
            self.budget.errors+=1;event.update(error_type=type(exc).__name__,errno=getattr(exc,'errno',None));raise

    def check_root(self):
        if self.root_fd is None:raise Refusal('held proc root closed')
        if (self.dir_identity(self.root_fd)!=self.root_directory or
            directory_identity(self._stat('named-root-stat',self.root,follow_symlinks=False))!=self.root_directory):
            raise Refusal('held/named proc root identity drift')
        return self.root_directory

    def close_root(self):
        if self.root_fd is not None:
            fd=self.root_fd;self.root_fd=None;self.close(fd)

    def _read(self,path,cap,dir_fd=None):
        if type(cap) is not int or not 0<cap<=65536:raise Refusal('finite proc leaf cap')
        event=self.budget.operation('read',path);fd=None;chunks=[];received=0
        try:
            fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=dir_fd)
            if not stat.S_ISREG(os.fstat(fd).st_mode):raise Refusal('proc regular leaf required')
            while True:
                allocation=min(cap+1-received,self.budget.read_limit-self.budget.received_bytes)
                if allocation<=0:raise Refusal('proc read cap or aggregate read budget')
                raw=os.read(fd,min(4096,allocation));self.budget.received_bytes+=len(raw)
                received+=len(raw);chunks.append(raw)
                if received>cap:raise Refusal('proc per-leaf read cap')
                if not raw:break
            body=b''.join(chunks)
            event.update(bytes=received,sha256=hashlib.sha256(body).hexdigest())
            return body.decode('ascii')
        except Exception as exc:
            self.budget.errors+=1;event.update(bytes=received,error_type=type(exc).__name__,
                errno=getattr(exc,'errno',None),received_base64=base64.b64encode(b''.join(chunks)).decode())
            raise
        finally:
            if fd is not None:os.close(fd)

    def self_status(self):return self._read('self/status',16384,dir_fd=self.root_fd)
    def self_namespace(self):return self.namespace_at(self.root_fd,relative='self/ns/pid')
    def namespace_path(self,path):
        st=self._stat('namespace-stat',path);return (st.st_dev,st.st_ino)
    def children(self,outer_parent_tid):
        return self._read('self/task/'+str(outer_parent_tid)+'/children',65536,dir_fd=self.root_fd)
    def list_pids(self):
        event=self.budget.operation('proc-list',self.root)
        try:
            # Charge/limit every directory entry enumerated, including non-PIDs.
            names=[]
            with os.scandir(self.root_fd) as entries:
                for entry in entries:
                    self.budget.operation('proc-list-entry',entry.name)
                    if entry.name.isdecimal():names.append(int(entry.name))
                    if len(names)>self.budget.candidate_limit:raise Refusal('proc PID list cap')
            event['numeric_entries']=len(names);return sorted(names)
        except Exception as exc:
            self.budget.errors+=1;event.update(error_type=type(exc).__name__,errno=getattr(exc,'errno',None));raise
    def open_dir(self,pid):
        event=self.budget.operation('open-proc-dir',self.root/str(pid));fd=None
        try:
            fd=os.open(str(pid),os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=self.root_fd)
            event['identity']=list(directory_identity(os.fstat(fd)));return fd
        except Exception as exc:
            self.budget.errors+=1;event.update(error_type=type(exc).__name__,errno=getattr(exc,'errno',None))
            if fd is not None:os.close(fd)
            raise
    def dir_identity(self,fd):
        event=self.budget.operation('held-directory-stat',fd)
        try:return directory_identity(os.fstat(fd))
        except Exception as exc:
            self.budget.errors+=1;event.update(error_type=type(exc).__name__,errno=getattr(exc,'errno',None));raise
    def named_identity(self,pid):
        return directory_identity(self._stat('named-directory-stat',str(pid),dir_fd=self.root_fd,follow_symlinks=False))
    def read_at(self,fd,name):
        if name not in ('status','stat','io'):raise Refusal('held proc leaf scope')
        return self._read(name,16384,dir_fd=fd)
    def namespace_at(self,fd,relative='ns/pid'):
        if relative not in ('ns/pid','self/ns/pid'):raise Refusal('proc namespace leaf scope')
        st=self._stat('held-namespace-stat',relative,dir_fd=fd);return (st.st_dev,st.st_ino)
    def close(self,fd):
        try:self.budget.operation('close-proc-dir',fd)
        finally:os.close(fd)


def status_fields(raw):
    result={}
    for line in raw.splitlines():
        if ':' not in line:continue
        key,value=line.split(':',1)
        if key in result:raise Refusal('duplicate status field')
        result[key]=value.strip()
    try:
        out={k:int(result[k]) for k in ('Pid','Tgid','PPid','Threads')}
        out['NSpid']=tuple(int(n) for n in result['NSpid'].split())
        out['Uid']=tuple(int(n) for n in result['Uid'].split())
        out['CapEff']=int(result['CapEff'],16)
    except (KeyError,ValueError) as exc:raise Refusal('required proc status identity missing') from exc
    if not out['NSpid'] or any(n<=0 for n in out['NSpid']):raise Refusal('invalid namespace PID chain')
    if len(out['Uid'])!=4 or any(n<0 for n in out['Uid']) or out['CapEff']<0:raise Refusal('invalid selected owner metadata')
    out['State']=result.get('State','');return out


def stat_fields(raw):
    first,separator,tail=raw.rpartition(')')
    if not separator or '(' not in first:raise Refusal('malformed proc stat')
    try:
        pid=int(first.split('(',1)[0].strip());parts=tail.split()
        out=dict(pid=pid,state=parts[0],ppid=int(parts[1]),starttime=int(parts[19]))
    except (ValueError,IndexError) as exc:raise Refusal('incomplete proc stat identity') from exc
    if out['pid']<=0 or out['starttime']<=0:raise Refusal('invalid proc stat identity')
    return out


def io_fields(raw):
    values={}
    for line in raw.splitlines():
        if ':' not in line:raise Refusal('malformed proc IO field')
        key,value=line.split(':',1)
        if key in values:raise Refusal('duplicate proc IO field')
        try:values[key]=int(value.strip())
        except ValueError as exc:raise Refusal('noninteger proc IO counter') from exc
        if values[key]<0:raise Refusal('negative proc IO counter')
    required={'rchar','wchar','syscr','syscw','read_bytes','write_bytes','cancelled_write_bytes'}
    if not required<=set(values):raise Refusal('missing proc IO counter')
    return values


def parent_context(fs,local_parent_pid):
    parent_raw=fs.self_status();parent=status_fields(parent_raw)
    if (parent['Pid']!=parent['Tgid'] or parent['NSpid'][0]!=parent['Pid']
        or parent['NSpid'][-1]!=local_parent_pid or parent['Threads']!=1
        or parent['Uid']!=(os.getuid(),)*4):
        raise Refusal('outer/inner single-thread parent binding')
    parent['namespace_identity']=fs.self_namespace();parent['root_directory']=fs.check_root()
    fd=fs.open_dir(parent['Pid'])
    try:
        parent['fd']=fd;parent['directory']=fs.dir_identity(fd)
        parent['starttime']=stat_fields(fs.read_at(fd,'stat'))['starttime']
        parent['raw_self_status']=parent_raw
        recheck_owner(parent,fs)
        return parent
    except BaseException:
        fs.close(fd);raise


def recheck_owner(parent,fs):
    if fs.check_root()!=parent['root_directory']:raise Refusal('owner proc root changed')
    held=status_fields(fs.read_at(parent['fd'],'status'));stats=stat_fields(fs.read_at(parent['fd'],'stat'))
    selected=('Pid','Tgid','PPid','Threads','NSpid','Uid','CapEff')
    if (any(held[k]!=parent[k] for k in selected) or held['Uid']!=(os.getuid(),)*4
        or stats['pid']!=parent['Pid'] or stats['ppid']!=parent['PPid'] or stats['starttime']!=parent['starttime']
        or fs.namespace_at(parent['fd'])!=parent['namespace_identity']
        or fs.dir_identity(parent['fd'])!=parent['directory'] or fs.named_identity(parent['Pid'])!=parent['directory']):
        raise Refusal('held owner UID/PID/namespace/starttime identity drift')


def owner_description(parent):
    return dict(outer_pid=parent['Pid'],namespace_pid_chain=list(parent['NSpid']),
        uid_real_effective_saved_fs=list(parent['Uid']),effective_capabilities=parent['CapEff'],
        starttime_ticks=parent['starttime'],held_proc_directory_identity=list(parent['directory']),
        held_proc_root_identity=list(parent['root_directory']),namespace_identity=list(parent['namespace_identity']),
        raw_self_status=parent['raw_self_status'])


def close_all(fs,fds):
    """An accounting refusal cannot bypass any actual descriptor cleanup."""
    first=None
    for fd in fds:
        try:fs.close(fd)
        except BaseException as exc:
            if first is None:first=exc
    if first is not None:raise first


class BoundChild:
    def __init__(self,fd,outer_pid,local_pid,parent,directory,starttime,route):
        self.fd=fd;self.outer_pid=outer_pid;self.local_pid=local_pid;self.parent=parent
        self.directory=directory;self.starttime=starttime;self.route=route;self.closed=False
    def close(self,fs):
        if not self.closed:
            self.closed=True
            close_all(fs,(self.fd,self.parent['fd']))


def _check_identity(status,stats,namespace,outer_pid,local_pid,parent,starttime=None):
    if (status['Pid']!=outer_pid or status['Tgid']!=outer_pid or stats['pid']!=outer_pid
        or status['NSpid'][0]!=outer_pid or len(status['NSpid'])!=len(parent['NSpid'])
        or status['NSpid'][-1]!=local_pid or status['PPid']!=parent['Pid']
        or stats['ppid']!=parent['Pid'] or namespace!=parent['namespace_identity']
        or status['Threads']!=1 or status['Uid']!=parent['Uid']
        or (starttime is not None and stats['starttime']!=starttime)):
        raise Refusal('candidate/snapshot child PID parent namespace/starttime mismatch')


def resolve_child(local_child_pid,budget,*,fs=None,local_parent_pid=None):
    if type(local_child_pid) is not int or local_child_pid<=0:raise Refusal('waitable child PID required')
    fs=fs or ProcFS(budget);parent=parent_context(fs,os.getpid() if local_parent_pid is None else local_parent_pid)
    route='parent-task-children';matches=[];success=False
    try:
        try:
            text=fs.children(parent['Pid']);pids=[int(n) for n in text.split()]
            if any(n<=0 for n in pids) or len(pids)!=len(set(pids)):raise Refusal('invalid parent children PID list')
            if len(pids)>budget.candidate_limit:raise Refusal('parent children scan cap')
        except OSError:
            route='bounded-proc-scan';pids=fs.list_pids()
        for outer_pid in pids:
            budget.candidate();fd=None;matched=False
            try:
                fd=fs.open_dir(outer_pid);directory=fs.dir_identity(fd)
                status=status_fields(fs.read_at(fd,'status'));stats=stat_fields(fs.read_at(fd,'stat'))
                namespace=fs.namespace_at(fd)
                _check_identity(status,stats,namespace,outer_pid,local_child_pid,parent)
                matched=True
                if fs.dir_identity(fd)!=directory or fs.named_identity(outer_pid)!=directory:
                    raise Refusal('candidate proc directory namespace drift')
                again=stat_fields(fs.read_at(fd,'stat'))
                if before_stats_identity(again)!=before_stats_identity(stats):raise Refusal('candidate starttime/stat drift')
                matches.append(BoundChild(fd,outer_pid,local_child_pid,parent,directory,stats['starttime'],route))
                fd=None
            except (OSError,Refusal) as exc:
                budget.rejected_candidates+=1;budget.errors+=1
                budget.events.append({'kind':'rejected-candidate','outer_pid':outer_pid,
                    'error_type':type(exc).__name__,'errno':getattr(exc,'errno',None),'error':str(exc)[:200]})
                # Rejected candidates remain charged; an exhausted finite budget
                # can never be converted into a successful partial scan.
                if (matched or budget.candidates>budget.candidate_limit or budget.operations>=budget.operation_limit
                    or budget.received_bytes>=budget.read_limit):raise
            finally:
                if fd is not None:fs.close(fd)
        if len(matches)!=1:raise Refusal('direct-child resolution absent or ambiguous')
        recheck_owner(parent,fs);success=True
        return matches.pop()
    finally:
        # Parent FD belongs to the resolution, not to each rejected match.
        cleanup=[match.fd for match in matches]
        for match in matches:match.closed=True
        if not success:cleanup.append(parent['fd'])
        close_all(fs,cleanup)


def snapshot(bound,fs):
    if bound.closed:raise Refusal('held proc child already closed')
    recheck_owner(bound.parent,fs)
    if fs.dir_identity(bound.fd)!=bound.directory:raise Refusal('held proc directory identity drift')
    before_status_raw=fs.read_at(bound.fd,'status');before_stat_raw=fs.read_at(bound.fd,'stat')
    before=status_fields(before_status_raw);stats=stat_fields(before_stat_raw)
    _check_identity(before,stats,fs.namespace_at(bound.fd),bound.outer_pid,bound.local_pid,bound.parent,bound.starttime)
    io_raw=fs.read_at(bound.fd,'io');counters=io_fields(io_raw)
    after_status_raw=fs.read_at(bound.fd,'status');after_stat_raw=fs.read_at(bound.fd,'stat')
    after=status_fields(after_status_raw);after_stats=stat_fields(after_stat_raw)
    _check_identity(after,after_stats,fs.namespace_at(bound.fd),bound.outer_pid,bound.local_pid,bound.parent,bound.starttime)
    if (fs.dir_identity(bound.fd)!=bound.directory or fs.named_identity(bound.outer_pid)!=bound.directory
        or before_stats_identity(stats)!=before_stats_identity(after_stats)):
        raise Refusal('snapshot held/named process identity drift')
    recheck_owner(bound.parent,fs)
    return dict(available=True,outer_proc_pid=bound.outer_pid,local_wait_pid=bound.local_pid,
        held_proc_directory_identity=list(bound.directory),starttime_ticks=bound.starttime,
        namespace_identity=list(bound.parent['namespace_identity']),resolution_route=bound.route,
        uid_real_effective_saved_fs=list(before['Uid']),effective_capabilities_before=before['CapEff'],
        effective_capabilities_after=after['CapEff'],
        observed_monotonic_ns=time.monotonic_ns(),io=counters,
        state_before=stats['state'],state_after=after_stats['state'],
        raw=dict(status_before=before_status_raw,stat_before=before_stat_raw,io=io_raw,
                 status_after=after_status_raw,stat_after=after_stat_raw),
        counter_observation_not_continuous_loader_or_per_file_custody=True)


def before_stats_identity(value):return (value['pid'],value['ppid'],value['starttime'])


def terminal_observation(bound,fs,*,waitid=None):
    """Confirm WNOWAIT terminal ownership; sample first; caller must wait4 next.

    Failed reads are retained as missing evidence, never zero substituted.
    This function does not reap and cannot itself guarantee the caller's wait4.
    """
    if waitid is None:waitid=os.waitid
    terminal=waitid(os.P_PID,bound.local_pid,os.WEXITED|os.WNOHANG|os.WNOWAIT)
    if terminal is None:return dict(terminal_observed=False,available=False,reason='not terminal',io=None)
    eligible=(os.CLD_EXITED,os.CLD_KILLED,os.CLD_DUMPED)
    if terminal.si_pid!=bound.local_pid or terminal.si_code not in eligible:
        raise Refusal('terminal wait ownership mismatch')
    result=dict(terminal_observed=True,waitid_pid=terminal.si_pid,waitid_code=terminal.si_code,
        waitid_status=terminal.si_status,wnowait_requested=True,wait4_called_here=False,
        caller_must_reap_exact_waitable_child=True,runtime_qualified=False,scientific_authority=False)
    try:
        value=snapshot(bound,fs)
        if value['state_before']!='Z' or value['state_after']!='Z':raise Refusal('terminal snapshot is not zombie state')
        result.update(available=True,snapshot=value,io=value['io'])
    except Exception as exc:
        result.update(available=False,io=None,error_type=type(exc).__name__,errno=getattr(exc,'errno',None),
            error=str(exc)[:300])
    return result
