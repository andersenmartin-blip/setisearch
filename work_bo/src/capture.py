"""Exact bounded child capture for deterministic BO engineering only.

No shell, random draws, telescope reads or scoring. Capture directories and
published files are exclusive. Every child is reaped with wait4; stdout is
published atomically only after capture has terminated. Passing requires both
a final bound JSON terminal and natural operating-system pipe EOF.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import resource
import selectors
import signal
import stat
import subprocess
import time

THREAD_KEYS = ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS')


class ReservationConflict(FileExistsError):
    pass


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def json_bytes(value):
    return (json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n').encode()


def publish_bytes(path,data):
    """Fixed pending pathname, fsync, exclusive hard link, directory fsync."""
    path=Path(path)
    pending=path.parent/('.'+path.name+'.pending')
    with pending.open('xb') as stream:
        stream.write(data);stream.flush();os.fsync(stream.fileno())
    os.link(pending,path)
    pending.unlink()
    directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(directory)
    finally:os.close(directory)
    if path.stat().st_size!=len(data) or sha(path)!=hashlib.sha256(data).hexdigest():
        raise ValueError('Atomic publication identity differs')


def publish_json(path,value):
    publish_bytes(path,json_bytes(value))


def verify_pins(pins):
    for path,digest in pins.items():
        if not stat.S_ISREG(Path(path).lstat().st_mode):
            raise ValueError('Pinned source/artifact is not a regular file: '+str(path))
        if sha(path)!=digest:
            raise ValueError('Changed pinned file: '+str(path))


def stored_bytes(roots):
    total=0
    for root in roots:
        root=Path(root)
        if not root.exists():continue
        for path in root.rglob('*'):
            info=path.lstat()
            if stat.S_ISREG(info.st_mode):total+=info.st_size
    return total


def inventory(root):
    root=Path(root)
    result={}
    for path in sorted(root.rglob('*')):
        if stat.S_ISREG(path.lstat().st_mode):result[str(path.absolute())]=sha(path)
    return result


def special_inventory(root):
    result={}
    for path in sorted(Path(root).rglob('*')):
        info=path.lstat()
        if stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode):continue
        record=dict(lstat_mode=info.st_mode,lstat_size=info.st_size)
        if stat.S_ISLNK(info.st_mode):
            target=os.readlink(path);record.update(type='symlink',target_text=target,
                target_sha256=hashlib.sha256(os.fsencode(target)).hexdigest())
        elif stat.S_ISFIFO(info.st_mode):record['type']='fifo'
        else:record['type']='other_special'
        result[str(path.absolute())]=record
    return result


def _proc_host(pid):
    try:
        text=Path(f'/proc/{pid}/stat').read_text().rsplit(')',1)[1].split()
        status={line.split(':',1)[0]:line.split(':',1)[1].strip()
                for line in Path(f'/proc/{pid}/status').read_text().splitlines() if ':' in line}
        if int(status['Pid'])!=pid:return None
        try:namespace=os.readlink(f'/proc/{pid}/ns/pid')
        except FileNotFoundError:namespace=None
        return dict(host_pid=pid,host_ppid=int(status['PPid']),state=text[0],start=int(text[19]),
            ns_pids=[int(v) for v in status['NSpid'].split()],
            ns_pgroups=[int(v) for v in status['NSpgid'].split()],ns_sessions=[int(v) for v in status['NSsid'].split()],
            namespace=namespace,cpu_ticks=sum(int(text[i]) for i in (11,12,13,14)),
            rss=int(text[21])*os.sysconf('SC_PAGE_SIZE'))
    except (FileNotFoundError,ProcessLookupError,PermissionError,KeyError):return None


class ProcessObserver:
    """Read host procfs only after validating namespace/parent PID mapping.

    Host PIDs are never passed to signal APIs. Cleanup signals only validated
    process-group IDs in the caller's own PID namespace.
    """
    def __init__(self,child_pid):
        status={line.split(':',1)[0]:line.split(':',1)[1].strip()
                for line in Path('/proc/self/status').read_text().splitlines() if ':' in line}
        self.host_parent=int(status['Pid']);self.levels=len(status['NSpid'].split())
        if int(status['NSpid'].split()[-1])!=os.getpid():raise ValueError('Own procfs namespace PID mapping differs')
        self.namespace=os.readlink('/proc/self/ns/pid');self.child_pid=child_pid
        self.host_child=None;self.child_start=None;self.groups={child_pid};self.mapping_verified=False;self.live_owned=[]

    def sample(self):
        table={}
        for directory in Path('/proc').iterdir():
            if directory.name.isdigit():
                record=_proc_host(int(directory.name))
                if record:table[record['host_pid']]=record
        if self.host_child is None:
            candidates=[r for r in table.values() if r['host_ppid']==self.host_parent
                and len(r['ns_pids'])==self.levels and r['ns_pids'][-1]==self.child_pid
                and r['ns_pgroups'][-1]==self.child_pid and r['ns_sessions'][-1]==self.child_pid
                and (r['namespace']==self.namespace or (r['state']=='Z' and r['namespace'] is None))]
            if len(candidates)!=1:raise ValueError('Cannot uniquely validate host child / namespace identity')
            child=candidates[0];self.host_child=child['host_pid'];self.child_start=child['start'];self.mapping_verified=True
        root=table.get(self.host_child)
        if root and root['start']!=self.child_start:raise ValueError('Host child PID was reused')
        owned={self.host_child};changed=True
        while changed:
            changed=False
            for record in table.values():
                if record['host_ppid'] in owned and record['host_pid'] not in owned:
                    owned.add(record['host_pid']);changed=True
        records=[r for pid,r in table.items() if pid in owned or
                 (r['namespace']==self.namespace and len(r['ns_pids'])==self.levels
                  and r['ns_pgroups'][-1] in self.groups)]
        for record in records:
            if len(record['ns_pids'])!=self.levels or (record['namespace'] not in [self.namespace,None]):
                raise ValueError('Owned descendant changed PID namespace')
            self.groups.add(record['ns_pgroups'][-1])
        self.live_owned=[dict(namespace_pid=r['ns_pids'][-1],namespace_pgrp=r['ns_pgroups'][-1],
            host_starttime_ticks=r['start'],state=r['state']) for r in records if r['state']!='Z']
        return (sum(r['cpu_ticks'] for r in records)/os.sysconf('SC_CLK_TCK'),sum(r['rss'] for r in records))

    def kill(self):
        for group in sorted(self.groups,reverse=True):
            if group<=1 or group==os.getpgrp():raise ValueError('Refusing unrelated/caller process group')
            try:os.killpg(group,signal.SIGKILL)
            except ProcessLookupError:pass


class FailureReserve:
    """One preallocated fixed-size footer; no overwrite after first commit."""
    def __init__(self,path,size):
        self.path=Path(path);self.size=int(size);self.committed=False
        descriptor=os.open(self.path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        try:
            os.ftruncate(descriptor,self.size)
            if hasattr(os,'posix_fallocate'):os.posix_fallocate(descriptor,0,self.size)
            os.fsync(descriptor)
        finally:os.close(descriptor)

    def commit(self,value):
        if self.committed:raise ReservationConflict('Failure footer already committed')
        data=json_bytes(value)
        if len(data)+8>self.size:raise ValueError('Failure footer reserve exceeded')
        with self.path.open('r+b') as stream:
            stream.write(len(data).to_bytes(8,'big'));stream.write(data);stream.flush();os.fsync(stream.fileno())
        self.committed=True
        return dict(path=str(self.path.resolve()),bytes=self.path.stat().st_size,sha256=sha(self.path),json_bytes=len(data))


def capture_child(command,capture_dir,result_path,caps,pins,context,stdout_limit=4194304,poll_seconds=.02,group=None):
    """Run once and return ACTUAL_RECEIPT.json data, including failed attempts.

    group optionally binds an absolute monotonic deadline, remaining child CPU,
    cumulative storage roots/cap and RSS cap. Actual CPU is wait4 user+system;
    the live monitor also includes observed descendants and reaped-child ticks.
    """
    folder=Path(capture_dir).resolve();result_path=Path(result_path).resolve()
    try:folder.mkdir()
    except FileExistsError as exc:raise ReservationConflict(str(folder)) from exc
    if not result_path.is_relative_to(folder):raise ValueError('Result outside reserved capture directory')
    log=folder/'STDOUT.log';receipt_path=folder/'ACTUAL_RECEIPT.json'
    group={} if group is None else group
    start=time.monotonic();parent_cpu_start=time.process_time();wall_deadline=min(start+float(caps['wall_seconds']),group.get('deadline_monotonic',math.inf))
    cpu_limit=min(float(caps['cpu_seconds']),group.get('cpu_remaining',math.inf))
    rss_limit=min(int(caps['rss_bytes']),group.get('rss_bytes',math.inf))
    group_roots=group.get('storage_roots',[])
    reasons=[];buffer=bytearray();observed=hashlib.sha256();observed_bytes=0
    child=None;child_status=None;usage=None;child_wait=False;eof=False;natural_eof=False
    killed=False;kill_time=None;capture_error=None;observer=None;peak_rss=0;peak_cpu=0.;pins_before=False;pins_after=False
    terminal=None;result_digest=None;stdout_full=True
    publish_json(folder/'START.json',dict(schema='SETI_BO_CHILD_START_V1',started_utc=datetime.now(timezone.utc).isoformat(),
        command=list(command),caps=caps,context=context,stdout_limit_bytes=stdout_limit,
        capture_directory_exclusive=True,source_pins=dict(pins)))
    def fail(reason):
        if reason not in reasons:reasons.append(reason)
    def consume(chunk):
        nonlocal observed_bytes,stdout_full
        observed.update(chunk);observed_bytes+=len(chunk)
        if len(buffer)+len(chunk)<=stdout_limit and stdout_full:buffer.extend(chunk)
        else:stdout_full=False;fail('STDOUT_BUFFER_CAP_EXCEEDED')
    try:
        verify_pins(pins);pins_before=True
        if result_path.parent.exists():raise ReservationConflict('Gate payload output already exists')
        if cpu_limit<=0 or wall_deadline<=start:raise ValueError('No remaining phase CPU/wall budget')
        environment=os.environ.copy()
        for key in THREAD_KEYS:environment[key]='1'
        environment['PYTHONDONTWRITEBYTECODE']='1'
        def limits():
            resource.setrlimit(resource.RLIMIT_CPU,(max(1,math.ceil(cpu_limit)),max(2,math.ceil(cpu_limit)+1)))
            resource.setrlimit(resource.RLIMIT_CORE,(0,0))
        child=subprocess.Popen(list(command),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
            cwd=folder,env=environment,start_new_session=True,preexec_fn=limits)
        observer=ProcessObserver(child.pid)
        os.set_blocking(child.stdout.fileno(),False)
        selector=selectors.DefaultSelector();selector.register(child.stdout,selectors.EVENT_READ)
        while not (child_wait and eof):
            now=time.monotonic();live_cpu,live_rss=observer.sample()
            peak_cpu=max(peak_cpu,live_cpu);peak_rss=max(peak_rss,live_rss)
            if now>=wall_deadline:fail('WALL_DEADLINE_BEFORE_CHILD_AND_STDOUT_CLOSED')
            closed_cpu=usage.ru_utime+usage.ru_stime if child_wait and usage else 0.
            if live_cpu+closed_cpu+time.process_time()-parent_cpu_start>cpu_limit:fail('TOTAL_CAPTURE_AND_CHILD_OR_GROUP_CPU_CAP_EXCEEDED')
            if live_rss>rss_limit:fail('CHILD_TREE_RSS_CAP_EXCEEDED')
            if stored_bytes([folder])+len(buffer)>int(caps['stored_bytes']):fail('GATE_STORAGE_CAP_EXCEEDED')
            if group_roots and stored_bytes(group_roots)+len(buffer)>int(group['stored_bytes']):fail('GROUP_STORAGE_CAP_EXCEEDED')
            if reasons and not killed:
                observer.kill();killed=True;kill_time=now
            if not eof:
                for key,_ in selector.select(max(0.,min(float(poll_seconds),wall_deadline-now)) if not killed else float(poll_seconds)):
                    while True:
                        try:chunk=os.read(key.fileobj.fileno(),65536)
                        except BlockingIOError:break
                        if not chunk:
                            eof=True;natural_eof=not killed;selector.unregister(key.fileobj);break
                        consume(chunk)
            if not child_wait:
                pid,status,actual_usage=os.wait4(child.pid,os.WNOHANG)
                if pid:
                    if pid!=child.pid:raise ValueError('Exact child wait identity differs')
                    child_status=status;usage=actual_usage;child_wait=True
                    child.returncode=os.waitstatus_to_exitcode(status)
            if killed and time.monotonic()-kill_time>5 and not (child_wait and eof):
                fail('FORCED_CLEANUP_DID_NOT_OBSERVE_CHILD_WAIT_AND_EOF');break
        selector.close();child.stdout.close()
    except BaseException as exc:
        capture_error=type(exc).__name__+': '+str(exc);fail('CAPTURE_EXCEPTION')
        if child is not None:
            if observer:observer.kill()
            else:
                try:os.killpg(child.pid,signal.SIGKILL)
                except ProcessLookupError:pass
            killed=True
            if not child_wait:
                pid,status,usage=os.wait4(child.pid,0)
                if pid!=child.pid:raise ValueError('Exact failure child wait identity differs')
                child_status=status;child_wait=True;child.returncode=os.waitstatus_to_exitcode(status)
            if child.stdout is not None and not child.stdout.closed:
                drain_deadline=time.monotonic()+5
                os.set_blocking(child.stdout.fileno(),False)
                while not eof and time.monotonic()<drain_deadline:
                    try:chunk=os.read(child.stdout.fileno(),65536)
                    except BlockingIOError:
                        time.sleep(float(poll_seconds));continue
                    if not chunk:eof=True;break
                    consume(chunk)
                if not eof:stdout_full=False
                child.stdout.close()
    cleanup_complete=False;remaining_live=[]
    if observer and observer.mapping_verified:
        try:
            observer.sample()
            if observer.live_owned:
                fail('LIVE_DESCENDANTS_AFTER_PARENT_CLOSE');observer.kill();killed=True
                cleanup_deadline=time.monotonic()+5
                while observer.live_owned and time.monotonic()<cleanup_deadline:
                    time.sleep(float(poll_seconds));observer.sample()
            remaining_live=observer.live_owned;cleanup_complete=not remaining_live
        except (ValueError,FileNotFoundError) as exc:fail('DESCENDANT_CLEANUP_UNVERIFIED: '+str(exc))
    if not cleanup_complete:fail('DESCENDANT_CLEANUP_NOT_PROVED')
    actual_exit=os.waitstatus_to_exitcode(child_status) if child_status is not None else None
    if actual_exit!=0:fail('ACTUAL_CHILD_EXIT_NOT_ZERO')
    if not child_wait:fail('EXACT_CHILD_WAIT_INCOMPLETE')
    if not eof:fail('STDOUT_EOF_NOT_OBSERVED')
    if not natural_eof:fail('NATURAL_STDOUT_EOF_NOT_OBSERVED')
    if not stdout_full:fail('STDOUT_NOT_FULLY_PRESERVED')
    try:
        if not buffer.endswith(b'\n'):raise ValueError('Final stdout terminal newline missing')
        lines=bytes(buffer).decode('utf-8').splitlines();terminal=json.loads(lines[-1])
        if not isinstance(terminal,dict) or terminal.get('event')!='GATE_TERMINAL_EOF' or terminal.get('status')!='PASS':raise ValueError('Terminal status/event differs')
        if result_path.is_symlink() or not result_path.is_file():raise ValueError('Regular RESULT.json missing')
        result_digest=sha(result_path);result=json.loads(result_path.read_text())
        if not isinstance(result,dict) or result.get('status')!='PASS':raise ValueError('Result JSON status differs')
        if terminal.get('result_sha256')!=result_digest:raise ValueError('Stdout/result SHA binding differs')
    except (ValueError,TypeError,KeyError,UnicodeError,FileNotFoundError) as exc:
        fail('TERMINAL_OR_RESULT_VALIDATION_FAILED: '+str(exc))
        if result_path.is_file() and not result_path.is_symlink():result_digest=sha(result_path)
    try:verify_pins(pins);pins_after=True
    except (ValueError,OSError) as exc:fail('POST_CHILD_PIN_FAILURE: '+str(exc))
    if usage and usage.ru_utime+usage.ru_stime+time.process_time()-parent_cpu_start>cpu_limit:fail('ACTUAL_TOTAL_CAPTURE_AND_CHILD_OR_GROUP_CPU_CAP_EXCEEDED')
    if usage and usage.ru_maxrss*1024>rss_limit:fail('ACTUAL_CHILD_RSS_CAP_EXCEEDED')
    if time.monotonic()>wall_deadline:fail('ACTUAL_GATE_OR_GROUP_WALL_CAP_EXCEEDED')
    publish_bytes(log,bytes(buffer))
    base_stored=stored_bytes([folder]);group_stored=stored_bytes(group_roots) if group_roots else None
    receipt=dict(schema='SETI_BO_EXACT_CHILD_CAPTURE_V1',status='PASS' if not reasons else 'FAIL',
        context=context,command=list(command),actual_exit_code=actual_exit,child_pid=child.pid if child else None,
        child_wait_completed=child_wait,wait_method='os.wait4 exact child',stdout_eof=eof,natural_stdout_eof=natural_eof,
        killed=killed,capture_error=capture_error,stdout_fully_preserved=stdout_full,
        process_namespace_mapping_verified=observer.mapping_verified if observer else False,
        descendant_cleanup_completed=cleanup_complete,remaining_live_descendants=remaining_live,
        observed_stdout_bytes=observed_bytes,observed_stdout_sha256=observed.hexdigest(),
        log_path=str(log),log_bytes=log.stat().st_size,log_sha256=sha(log),result_path=str(result_path),
        result_sha256=result_digest,terminal_stdout_json=terminal,source_pins_verified_before=pins_before,
        source_pins_verified_after=pins_after,reasons=reasons,
        resources=dict(wall_seconds=time.monotonic()-start,capture_parent_cpu_seconds=time.process_time()-parent_cpu_start,
            child_user_cpu_seconds=usage.ru_utime if usage else None,child_system_cpu_seconds=usage.ru_stime if usage else None,
            max_child_RSS_bytes=usage.ru_maxrss*1024 if usage else None,peak_tree_RSS_bytes=peak_rss,
            observed_tree_cpu_seconds=peak_cpu,stored_bytes_before_receipt=base_stored,stored_bytes_total=0,
            receipt_bytes=0,group_stored_bytes_total=group_stored),
        completed_utc=datetime.now(timezone.utc).isoformat())
    for _ in range(16):
        length=len(json_bytes(receipt));receipt['resources']['receipt_bytes']=length
        receipt['resources']['stored_bytes_total']=base_stored+length
        if group_stored is not None:receipt['resources']['group_stored_bytes_total']=group_stored+length
        if base_stored+length>int(caps['stored_bytes']):fail('FINAL_GATE_STORAGE_CAP_EXCEEDED')
        if group_stored is not None and group_stored+length>int(group['stored_bytes']):fail('FINAL_GROUP_STORAGE_CAP_EXCEEDED')
        receipt['status']='PASS' if not reasons else 'FAIL'
        if len(json_bytes(receipt))==length:break
    else:raise ValueError('Receipt byte accounting did not stabilize')
    publish_json(receipt_path,receipt)
    if receipt_path.stat().st_size!=receipt['resources']['receipt_bytes']:raise ValueError('Receipt byte accounting differs')
    return receipt
