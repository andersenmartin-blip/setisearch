"""Single dispatch with external full-parent lifetime and terminal accounting."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import subprocess
import time

def main():
    parser=argparse.ArgumentParser()
    for name in ('freeze','freeze-sha256','proof','proof-sha256','marker','marker-sha256'):
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    freeze_raw=Path(args.freeze).read_bytes()
    if hashlib.sha256(freeze_raw).hexdigest()!=args.freeze_sha256:
        raise ValueError('caller freeze hash mismatch')
    freeze=json.loads(freeze_raw)
    by_path={pin['path']:pin for pin in freeze['source_pins']+freeze['runtime_pins']}
    for path in (freeze['gate_source_path'],freeze['python_executable']):
        pin=by_path[path]
        raw=Path(path).read_bytes()
        if len(raw)!=pin['bytes'] or hashlib.sha256(raw).hexdigest()!=pin['sha256']:
            raise ValueError('caller pinned gate/Python mismatch')
    root=Path(freeze['output_root'])
    if list(root.iterdir()):
        raise ValueError('occupied one-shot root')
    command=[freeze['python_executable'],'-I','-B','-S',freeze['gate_source_path']]
    for name in ('freeze','freeze_sha256','proof','proof_sha256','marker','marker_sha256'):
        command+=['--'+name.replace('_','-'),getattr(args,name)]
    environment={'LANG':'C','LC_ALL':'C','PYTHONDONTWRITEBYTECODE':'1',
                 'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'}
    # The launcher itself is a fresh single-threaded stdlib-only process.
    def before_exec():
        resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2))
        resource.setrlimit(resource.RLIMIT_CPU,(30,30))
        resource.setrlimit(resource.RLIMIT_FSIZE,(1024**2,1024**2))
    started=time.monotonic()
    with (root.parent/(root.name+'.caller-stdout')).open('xb') as stdout, \
         (root.parent/(root.name+'.caller-stderr')).open('xb') as stderr:
        process=subprocess.Popen(command,env=environment,cwd=freeze['preparation_root'],
            stdout=stdout,stderr=stderr,stdin=subprocess.DEVNULL,close_fds=True,
            start_new_session=True,preexec_fn=before_exec)
        killed=False
        terminal=None
        while terminal is None:
            terminal=os.waitid(os.P_PID,process.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT)
            if terminal is not None:
                break
            if time.monotonic()-started>=30:
                killed=True
                try: os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError: pass
            if stdout.tell()+stderr.tell()>128*1024:
                killed=True
                try: os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError: pass
            if killed and time.monotonic()-started>=40:
                raise RuntimeError('bounded parent reap failed')
            time.sleep(0.02)
        pid,status,usage=os.wait4(process.pid,0)
        process.returncode=os.waitstatus_to_exitcode(status)
        stdout.flush();stderr.flush()
        os.fsync(stdout.fileno());os.fsync(stderr.fileno())
    completed=time.monotonic()-started
    result=dict(schema='radio-proc-io-control-caller-receipt-v1',
        identity=freeze['identity'],dispatches=1,pid=pid,child_reaped=True,
        child_exit_code=process.returncode,watchdog_killed=killed,
        elapsed_full_parent_lifetime_seconds=completed,
        parent_wait4_lifetime_ru_maxrss_bytes=usage.ru_maxrss*1024,
        parent_wait4_cpu_user_seconds=usage.ru_utime,parent_wait4_cpu_system_seconds=usage.ru_stime,
        runtime_qualified=False,scientific_authority=False,
        explicit_limitations=['The launcher is administrative caller overhead.',
           'wait4 reports this direct parent and waited child usage; no tree simultaneous RSS measurement.',
           'Final artifact inventory is selected stored bytes, not transient storage peak.'])
    gate_result=root/'result.json'
    if gate_result.is_file():
        try:
            if gate_result.stat().st_size>1024**2:
                raise ValueError('bounded gate result exceeded')
            gate=json.loads(gate_result.read_text())
            if type(gate) is not dict or type(gate.get('status')) is not str or type(gate.get('children')) is not list:
                raise ValueError('gate result shape')
            peaks=[c.get('wait4_direct_child_ru_maxrss_bytes') for c in gate['children']]
            complete=all(type(p) is int and p>=0 for p in peaks)
            result['child_peak_custody_complete']=complete
            result['conservative_joined_rss_upper_bound_bytes']=(usage.ru_maxrss*1024+max(peaks,default=0) if complete else None)
            result['successful_gate_status']=gate['status']
        except Exception as exc:
            result['gate_result_read_error']=str(exc)[:300]
            result['child_peak_custody_complete']=False
            result['conservative_joined_rss_upper_bound_bytes']=None
    result['success']=process.returncode==0 and not killed and completed<30 and \
        result.get('successful_gate_status','').startswith('OBSERVED_KERNEL_IO_ONLY_') and result.get('child_peak_custody_complete') is True
    logical=allocated=files=directories=0
    try:
        for directory,names,filenames in os.walk(root,followlinks=False):
            directories+=1
            if directories>128 or Path(directory).is_symlink():raise ValueError('terminal directory limit/kind')
            for name in names:
                if (Path(directory)/name).is_symlink():raise ValueError('terminal directory symlink')
            st=Path(directory).stat()
            logical+=st.st_size;allocated+=st.st_blocks*512
            for filename in filenames:
                path=Path(directory)/filename
                if path.is_symlink():raise ValueError('terminal artifact symlink')
                st=path.stat();logical+=st.st_size;allocated+=st.st_blocks*512;files+=1
                if files>2000:raise ValueError('terminal file count')
    except Exception as exc:
        result['success']=False
        result['storage_inventory_error']=str(exc)[:300]
        result['storage_inventory_incomplete']=True
    result['storage_before_caller_receipt']=dict(logical_bytes=logical,allocated_bytes=allocated,
        files=files,directories=directories,excludes='caller-receipt.json and caller raw streams outside root')
    if max(logical,allocated)>=16*1024**2-1024**2:
        result['success']=False
        result['terminal_reserve_exceeded']=True
    target=root/'caller-receipt.json'
    raw=(json.dumps(result,sort_keys=True,indent=2)+'\n').encode()
    with target.open('xb') as stream:
        stream.write(raw);stream.flush();os.fsync(stream.fileno())
    print(json.dumps(result,sort_keys=True))
    return 0 if result['success'] else 1

if __name__=='__main__':
    raise SystemExit(main())
