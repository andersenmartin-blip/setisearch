"""Single external G launch, exact wait4 lifetime, no retry.

Administrative launcher overhead is separate from the measured gate envelope.
No native/scientific package is imported by this module.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import signal
import stat
import subprocess
import time


def pinned(path, size, sha):
    path = Path(path)
    if not path.is_absolute() or path.resolve() != path:
        raise ValueError('canonical launch input required')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size != size or size > 8*1024**2:
            raise ValueError('bounded launch input size differs')
        raw = stream.read(size+1)
        after = os.fstat(stream.fileno())
    named = path.stat()
    fields = lambda st: (st.st_dev, st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
    if fields(before) != fields(after) or fields(after) != fields(named) or len(raw) != size or hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError('complete launch input hash/identity differs')
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arguments', required=True)
    parser.add_argument('--arguments-bytes', type=int, required=True)
    parser.add_argument('--arguments-sha256', required=True)
    args = parser.parse_args()
    spec = json.loads(pinned(args.arguments, args.arguments_bytes, args.arguments_sha256))
    for key in ('gate', 'config', 'preread_proof', 'publication_proof'):
        info = spec[key]
        pinned(info['path'], info['bytes'], info['sha256'])
    parent = spec['parent_python_pin']
    if parent['path'] != spec['parent_python']:
        raise ValueError('exact parent executable binding required')
    # The interpreter is larger than the bounded JSON inputs: stream its hash.
    parent_path = Path(parent['path'])
    if not parent_path.is_absolute() or parent_path.resolve() != parent_path:
        raise ValueError('canonical parent executable required')
    fd = os.open(parent_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    with os.fdopen(fd, 'rb') as stream:
        before = os.fstat(stream.fileno()); digest = hashlib.sha256()
        if not stat.S_ISREG(before.st_mode): raise ValueError('ordinary parent executable required')
        while block := stream.read(1024**2): digest.update(block)
        after = os.fstat(stream.fileno())
    identity = lambda st: (st.st_dev, st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
    if identity(before) != identity(after) or identity(after) != identity(Path(parent['path']).stat()) or before.st_size != parent['bytes'] or digest.hexdigest() != parent['sha256']:
        raise ValueError('parent executable hash/identity differs')
    config = json.loads(pinned(spec['config']['path'], spec['config']['bytes'], spec['config']['sha256']))
    if Path(config['artifacts']['spent_marker']).exists() or any(Path(config['artifacts']['root']).iterdir()):
        raise ValueError('single fresh G dispatch required')
    stdout_path, stderr_path = Path(spec['stdout']), Path(spec['stderr'])
    receipt_path = Path(spec['caller_receipt'])
    if any(p.exists() for p in (stdout_path, stderr_path, receipt_path)):
        raise ValueError('fresh caller evidence required')
    command = [spec['parent_python'], '-I', '-B', '-S', spec['gate']['path']]
    for label, key in (('config','config'), ('preread-proof','preread_proof')):
        info = spec[key]
        command.extend(['--'+label,info['path'],'--'+label+'-bytes',str(info['bytes']),
                        '--'+label+'-sha256',info['sha256']])
    started = time.monotonic()
    deadline = started+120
    killed = False
    stream_ceiling_exceeded = False
    loop_failure = None
    terminal = None
    with stdout_path.open('xb') as out, stderr_path.open('xb') as err:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                   env=config['environment'], cwd=config['cwd'], start_new_session=True)
        try:
            while True:
                terminal = os.waitid(os.P_PID,process.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT)
                if terminal is not None:
                    if terminal.si_pid != process.pid: raise ValueError('WNOWAIT child identity differs')
                    break
                stream_ceiling_exceeded = stdout_path.stat().st_size > 1024**2 or stderr_path.stat().st_size > 1024**2
                if time.monotonic() >= deadline or stream_ceiling_exceeded:
                    killed = True
                    os.killpg(process.pid,signal.SIGKILL)
                    break
                time.sleep(0.02)
        except BaseException as exc:
            loop_failure = type(exc).__name__+': '+str(exc)[:300]
        finally:
            if terminal is None:
                killed = True
                try: os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError: pass
            waited, status, usage = os.wait4(process.pid,0)
            ended = time.monotonic()
            process.returncode = os.waitstatus_to_exitcode(status)
    stream_ceiling_exceeded = stream_ceiling_exceeded or stdout_path.stat().st_size > 1024**2 or stderr_path.stat().st_size > 1024**2
    exact_wait = waited == process.pid
    receipt = dict(schema='radio-codec16-external-caller-G-v1', one_gate_dispatch=True,
                   waited_pid=waited, expected_gate_pid=process.pid,
                   exact_wait4=exact_wait, parent_reaped=exact_wait,
                   wnowait_pid=terminal.si_pid if terminal is not None else None,
                   loop_failure=loop_failure,
                   exit_code=process.returncode, external_deadline_seconds=120,
                   elapsed_complete_gate_seconds=ended-started, watchdog_kill=killed,
                   caller_stream_each_ceiling_bytes=1024**2,
                   caller_stream_ceiling_exceeded=stream_ceiling_exceeded,
                   gate_peak_rss_bytes=usage.ru_maxrss*1024,
                   gate_cpu_seconds=usage.ru_utime+usage.ru_stime,
                   administrative_launcher_outside_gate_envelope=True,
                   caller_stdout_bytes=stdout_path.stat().st_size,
                   caller_stderr_bytes=stderr_path.stat().st_size,
                   config_sha256=spec['config']['sha256'],
                   publication_proof_sha256=spec['publication_proof']['sha256'],
                   scientific_authority=False)
    with receipt_path.open('xb') as handle:
        handle.write((json.dumps(receipt,sort_keys=True,indent=2)+'\n').encode())
        handle.flush(); os.fsync(handle.fileno())
    print(json.dumps(receipt,sort_keys=True))
    return 0 if process.returncode == 0 and not killed and not stream_ceiling_exceeded and exact_wait and not loop_failure and ended <= deadline else 1


if __name__ == '__main__':
    raise SystemExit(main())
