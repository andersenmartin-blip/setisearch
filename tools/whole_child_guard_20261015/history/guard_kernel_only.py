"""Future-use Linux single-process guard. No scientific admission or retry API."""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import time


def durable_json(path, value):
    path = Path(path)
    tmp = path.with_name(path.name + '.tmp')
    with tmp.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    tmp.replace(path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def finite_nonnegative(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def policy(cpu_s, wall_s, address_space_bytes):
    # One complete CPU second of prospective headroom, before integer flooring.
    if not finite_nonnegative(cpu_s) or cpu_s < 2:
        raise ValueError('CPU cap must be finite and >=2 seconds')
    if not finite_nonnegative(wall_s) or wall_s <= 0:
        raise ValueError('Wall cap must be finite and >0')
    if type(address_space_bytes) is not int or address_space_bytes < 64 * 1024**2:
        raise ValueError('Address-space cap must be an integer >=64MiB')
    return {'cpu_s': cpu_s, 'wall_s': wall_s,
            'address_space_bytes': address_space_bytes,
            'kernel_CPU_hard_s': math.floor(cpu_s - 1)}


def assess(receipt, limits):
    """Strict acceptance of final parent measurements; no tolerance or fallback."""
    errors = []
    if receipt.get('wait4_reaped') is not True:
        errors.append('MISSING_WAIT4')
    if type(receipt.get('exit_code')) is not int or receipt['exit_code'] != 0:
        errors.append('CHILD_EXIT_FAILED')
    for field, cap in [('whole_child_CPU_s', limits['cpu_s']),
                       ('wall_s', limits['wall_s']),
                       ('peak_RSS_bytes', limits['address_space_bytes'])]:
        value = receipt.get(field)
        if not finite_nonnegative(value):
            errors.append('INVALID_' + field)
        elif value > cap:
            errors.append('EXCEEDED_' + field)
    if receipt.get('watchdog_fired') is not False:
        errors.append('WATCHDOG_OR_MISSING_WATCHDOG_STATE')
    if receipt.get('launcher_verified') is not True:
        errors.append('LAUNCH_LIMITS_UNVERIFIED')
    return {'resource_acceptance': not errors,
            'status': 'RESOURCE_COMPLIANT_ONLY' if not errors else 'FAILED_RESOURCE_OR_PROCESS',
            'errors': errors,
            'scientific_integrity_or_QA_or_admission_established': False}


def _launch(folder, limits, command):
    resource.setrlimit(resource.RLIMIT_CPU,
                       (limits['kernel_CPU_hard_s'], limits['kernel_CPU_hard_s']))
    resource.setrlimit(resource.RLIMIT_AS,
                       (limits['address_space_bytes'], limits['address_space_bytes']))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    durable_json(Path(folder) / 'LAUNCH_LIMITS.json',
                 {'pid': os.getpid(), 'limits': limits,
                  'CPU_rlimit': list(resource.getrlimit(resource.RLIMIT_CPU)),
                  'AS_rlimit': list(resource.getrlimit(resource.RLIMIT_AS)),
                  'command': command})
    os.execvp(command[0], command)


def run_once(command, folder, limits):
    """Keep one attempt, reap exactly once, gate only after complete termination.

    Caller must have a separate science admission and output budget. In particular
    this function cannot resume a closed study. No Popen.poll/wait double-reaping.
    """
    expected = policy(limits['cpu_s'], limits['wall_s'], limits['address_space_bytes'])
    if expected != limits:
        raise ValueError('Policy is not canonical')
    if not command or any(type(x) is not str or not x for x in command):
        raise ValueError('Nonempty executable argument vector required')
    folder = Path(folder).resolve()
    folder.mkdir()  # Exclusive attempt claim: never replace or retry a directory.
    claim = {'command': command, 'limits': limits, 'status': 'CLAIMED_ONCE',
             'guard_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    durable_json(folder / 'CLAIM.json', claim)
    start = time.monotonic()
    child = None
    usage = None
    interrupted = None
    fired = False
    with (folder / 'stdout.log').open('xb') as out, (folder / 'stderr.log').open('xb') as err:
        try:
            child = subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), '_launch', str(folder),
                 json.dumps(limits), *command], stdout=out, stderr=err,
                start_new_session=True,
                env={**os.environ, 'OPENBLAS_NUM_THREADS': '1', 'OMP_NUM_THREADS': '1',
                     'MKL_NUM_THREADS': '1', 'NUMEXPR_NUM_THREADS': '1'})
            while True:
                pid, status, usage_now = os.wait4(child.pid, os.WNOHANG)
                if pid:
                    usage = usage_now
                    child.returncode = os.waitstatus_to_exitcode(status)
                    break
                if time.monotonic() - start >= limits['wall_s']:
                    fired = True
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                time.sleep(0.01)
        except BaseException as exc:
            interrupted = type(exc).__name__ + ': ' + str(exc)
        finally:
            if child is not None and usage is None:
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                _, status, usage = os.wait4(child.pid, 0)
                child.returncode = os.waitstatus_to_exitcode(status)
    elapsed = time.monotonic() - start
    launch_verified = False
    try:
        launch = json.loads((folder / 'LAUNCH_LIMITS.json').read_text())
        launch_verified = (child is not None and launch['pid'] == child.pid and
                           launch['limits'] == limits and launch['command'] == command and
                           launch['CPU_rlimit'] == [limits['kernel_CPU_hard_s']] * 2 and
                           launch['AS_rlimit'] == [limits['address_space_bytes']] * 2)
    except (OSError, ValueError, KeyError, TypeError):
        pass
    result = {'command': command, 'limits': limits, 'wait4_reaped': usage is not None,
              'pid': child.pid if child is not None else None,
              'exit_code': child.returncode if child is not None else None,
              'whole_child_CPU_s': usage.ru_utime + usage.ru_stime if usage else None,
              'peak_RSS_bytes': usage.ru_maxrss * 1024 if usage else None,
              'wall_s': elapsed, 'watchdog_fired': fired,
              'launcher_verified': launch_verified, 'interruption': interrupted}
    result.update(assess(result, limits))
    if interrupted:
        result['resource_acceptance'] = False
        result['status'] = 'FAILED_RESOURCE_OR_PROCESS'
        result['errors'].append('PARENT_INTERRUPTION')
    durable_json(folder / 'WAIT4_RECEIPT.json', result)
    return result


def run_sequence(commands, folder, limits, CPU_envelope_s):
    """Minimal serial integration: fail before the next submission, no retries."""
    if not finite_nonnegative(CPU_envelope_s):
        raise ValueError('Finite CPU envelope required')
    folder = Path(folder).resolve()
    folder.mkdir()
    state = {'status': 'RUNNING', 'jobs': [], 'unsubmitted': list(range(len(commands))),
             'whole_child_CPU_s': 0, 'CPU_envelope_s': CPU_envelope_s}
    durable_json(folder / 'STATE.json', state)
    for index, command in enumerate(commands):
        if state['whole_child_CPU_s'] + limits['cpu_s'] > CPU_envelope_s:
            state['status'] = 'STOPPED_RESERVATION_CAPACITY'
            break
        job = run_once(command, folder / f'{index:04d}', limits)
        state['unsubmitted'].remove(index)
        state['jobs'].append(job)
        if finite_nonnegative(job['whole_child_CPU_s']):
            state['whole_child_CPU_s'] += job['whole_child_CPU_s']
        if not job['resource_acceptance']:
            state['status'] = 'STOPPED_RETAINED_NO_RETRY'
            durable_json(folder / 'STATE.json', state)
            break
        durable_json(folder / 'STATE.json', state)
    if state['status'] == 'RUNNING':
        state['status'] = 'COMPLETE_RESOURCE_CHECK_ONLY'
    durable_json(folder / 'STATE.json', state)
    return state


if __name__ == '__main__':
    if len(sys.argv) < 5 or sys.argv[1] != '_launch':
        raise SystemExit('Library for future integration, not a science dispatcher')
    _launch(sys.argv[2], json.loads(sys.argv[3]), sys.argv[4:])
