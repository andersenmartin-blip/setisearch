#!/usr/bin/env python3
"""Observe one fresh hosted CAS metadata child; no live action on import.

Procfs observations are samples, not complete descendant/ELF/RSS certificates.
The child is allowed 175 seconds; five further seconds are reserved for group
termination, pipe draining and reaping inside the 180-second lifetime bound.
"""
import argparse
import ctypes
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import selectors
import signal
import ssl
import stat
import subprocess
import sys
import time
import urllib.request

NAMESPACE = 'radio-hosted-cas-control-20261004a'
REPOSITORY = 'andersenmartin-blip/setisearch'
BRANCH = 'm43-support-qualification'
PREFIX = 'results_radio_hosted_cas_control_20261004a/'
EXPECTED_SOURCES = frozenset((
    '.github/workflows/radio_hosted_cas_control_20261004a.yml',
    'RADIO_HOSTED_CAS_CONTROL_2026-10-04_PROTOCOL.md',
    *(PREFIX + name for name in ('activation_gate.py', 'control.py',
      'publisher.py', 'supervisor.py', 'test_activation_gate.py',
      'test_control.py', 'test_publisher.py', 'test_supervisor.py'))))
PROOF_KEYS = frozenset(('schema', 'repository', 'branch', 'namespace',
    'activation', 'preparation', 'manifest_sha256', 'run_id', 'source_files'))
GHA_KEYS = ('GITHUB_SHA', 'GITHUB_REPOSITORY', 'GITHUB_REF',
    'GITHUB_EVENT_NAME', 'GITHUB_RUN_ATTEMPT', 'GITHUB_RUN_ID',
    'GITHUB_WORKFLOW_REF')
DEFAULT_LIMITS = {'child_seconds': 175.0, 'reap_seconds': 5.0,
    'stream_bytes': 1024 * 1024, 'combined_bytes': 2 * 1024 * 1024,
    'storage_bytes': 8 * 1024 * 1024, 'metadata_reserve': 1024 * 1024,
    'rss_bytes': 512 * 1024 * 1024, 'sample_seconds': 0.05,
    'max_observed_processes': 256}


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       ensure_ascii=True) + '\n').encode()


def reject_duplicates(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('Duplicate JSON key')
        value[key] = item
    return value


def checked_path(path, *, absent=False):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('An absolute path without parent traversal is required')
    for ancestor in reversed((path, *path.parents)):
        if ancestor.is_symlink():
            raise ValueError('Symlink path component refused')
    if absent and (path.exists() or os.path.lexists(path)):
        raise ValueError('Output root already exists; no retry or overwrite')
    return path


def read_regular(path, maximum=None):
    path = checked_path(path)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as source:
        identity = os.fstat(source.fileno())
        if not stat.S_ISREG(identity.st_mode) or identity.st_nlink != 1:
            raise ValueError('Sole-link regular file required')
        if maximum is not None and identity.st_size > maximum:
            raise ValueError('Input size exceeds its bound')
        data = source.read()
        after = os.fstat(source.fileno())
        if (identity.st_dev, identity.st_ino, identity.st_size,
            identity.st_mtime_ns, identity.st_ctime_ns) != (
                after.st_dev, after.st_ino, after.st_size,
                after.st_mtime_ns, after.st_ctime_ns):
            raise ValueError('Input changed during read')
    return data, identity


def file_pin(path):
    data, identity = read_regular(path)
    return {'path': str(path), 'bytes': len(data),
        'sha256': hashlib.sha256(data).hexdigest(), 'mode': stat.S_IMODE(identity.st_mode),
        'device': identity.st_dev, 'inode': identity.st_ino,
        'mtime_ns': identity.st_mtime_ns, 'ctime_ns': identity.st_ctime_ns}


def persist(path, raw):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as target:
        target.write(raw)
        target.flush()
        os.fsync(target.fileno())
    directory = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    actual, _ = read_regular(path)
    if actual != raw:
        raise ValueError('Persisted bytes differ')


def proof_sources(raw, root, expected_sources):
    proof = json.loads(raw, object_pairs_hook=reject_duplicates)
    if (not isinstance(proof, dict) or set(proof) != PROOF_KEYS or
        proof['schema'] != 'radio-hosted-cas-control-activation-proof-v1' or
        proof['repository'] != REPOSITORY or proof['branch'] != BRANCH or
        proof['namespace'] != NAMESPACE or
        not all(isinstance(proof[field], str) and re.fullmatch('[0-9a-f]{40}', proof[field])
                for field in ('activation', 'preparation')) or
        not isinstance(proof['manifest_sha256'], str) or
        not re.fullmatch('[0-9a-f]{64}', proof['manifest_sha256']) or
        not isinstance(proof['run_id'], str) or not re.fullmatch('[0-9]+', proof['run_id'])):
        raise ValueError('Gate proof identity or schema differs')
    rows = proof['source_files']
    if not isinstance(rows, list) or len(rows) != len(expected_sources):
        raise ValueError('Complete fixed source selection required')
    observed = {}
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {'path', 'bytes', 'sha256'} or
            row['path'] not in expected_sources or row['path'] in observed or
            type(row['bytes']) is not int or row['bytes'] < 0 or
            not isinstance(row['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', row['sha256'])):
            raise ValueError('Gate source record differs')
        pin = file_pin(root / row['path'])
        if pin['bytes'] != row['bytes'] or pin['sha256'] != row['sha256']:
            raise ValueError('Current source does not match gate proof')
        observed[row['path']] = pin
    if set(observed) != set(expected_sources):
        raise ValueError('Fixed source membership differs')
    freeze_raw, _ = read_regular(root / 'config/radio_hosted_cas_control_20261004a.freeze.json', 256 * 1024)
    freeze = json.loads(freeze_raw, object_pairs_hook=reject_duplicates)
    if (hashlib.sha256(freeze_raw).hexdigest() != proof['manifest_sha256'] or
        not isinstance(freeze, dict) or set(freeze) != {'schema', 'namespace', 'repository', 'branch', 'source_files', 'limits'} or
        freeze['schema'] != 'radio-hosted-cas-control-freeze-v1' or
        freeze['namespace'] != NAMESPACE or freeze['repository'] != REPOSITORY or
        freeze['branch'] != BRANCH or freeze['source_files'] != rows or
        not isinstance(freeze['limits'], dict)):
        raise ValueError('Local exact freeze does not match gate proof')
    return proof, observed


def selected_runtime_paths():
    paths = {Path(sys.executable).resolve(), Path(__file__).resolve()}
    for name in ('argparse', 'hashlib', 'json', 'pathlib', 'selectors', 'subprocess',
                 'ssl', '_ssl', 'http.client', 'urllib.request', 'ctypes', '_ctypes'):
        module = sys.modules.get(name)
        filename = getattr(module, '__file__', None)
        if filename:
            paths.add(Path(filename).resolve())
    cafile = ssl.get_default_verify_paths().cafile
    if cafile and Path(cafile).is_file():
        paths.add(Path(cafile).resolve())
    return sorted(paths)


def child_environment(proof):
    if (os.environ.get('GITHUB_SHA') != proof['activation'] or
        os.environ.get('GITHUB_REPOSITORY') != REPOSITORY or
        os.environ.get('GITHUB_REF') != 'refs/heads/' + BRANCH or
        os.environ.get('GITHUB_EVENT_NAME') != 'push' or
        os.environ.get('GITHUB_RUN_ATTEMPT') != '1' or
        os.environ.get('GITHUB_RUN_ID') != proof['run_id'] or
        os.environ.get('GITHUB_WORKFLOW_REF') != REPOSITORY + '/' +
            '.github/workflows/radio_hosted_cas_control_20261004a.yml@refs/heads/' + BRANCH):
        raise ValueError('Selected GitHub execution metadata differs')
    token = os.environ.get('GITHUB_TOKEN')
    if not token or '\n' in token or '\r' in token or '\0' in token:
        raise ValueError('Runtime child credential unavailable or malformed')
    environment = {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C.UTF-8', 'TZ': 'UTC'}
    environment.update({key: os.environ[key] for key in GHA_KEYS})
    environment['GITHUB_TOKEN'] = token
    return environment


def proc_row(pid):
    try:
        directory = Path('/proc') / str(pid)
        raw = (directory / 'stat').read_text()
        fields = raw[raw.rfind(')') + 2:].split()
        sizes = {}
        for line in (directory / 'status').read_text().splitlines():
            key, _, value = line.partition(':')
            if key in ('VmRSS', 'VmHWM'):
                sizes[key] = int(value.split()[0]) * 1024
        return {'pid': int(pid), 'ppid': int(fields[1]),
                'start_ticks': int(fields[19]), 'state': fields[0],
                'rss_bytes': sizes.get('VmRSS', 0), 'hwm_bytes': sizes.get('VmHWM', 0)}
    except (OSError, ValueError, IndexError):
        return None


def proc_tree(root_pid, known):
    rows = {}
    for entry in Path('/proc').iterdir():
        if entry.name.isdigit():
            row = proc_row(int(entry.name))
            if row:
                rows[row['pid']] = row
    selected = {root_pid}
    selected.update(pid for pid, start in known if rows.get(pid, {}).get('start_ticks') == start)
    while True:
        expanded = selected | {pid for pid, row in rows.items() if row['ppid'] in selected}
        if expanded == selected:
            break
        selected = expanded
    return [rows[pid] for pid in sorted(selected) if pid in rows]


def storage_inventory(root, *, hashes=False):
    logical = allocated = 0
    files = []
    directories = 0
    for folder, children, names in os.walk(root, followlinks=False):
        for path in [Path(folder), *(Path(folder) / name for name in children + names)]:
            identity = path.lstat()
            if stat.S_ISLNK(identity.st_mode) or not (stat.S_ISDIR(identity.st_mode) or stat.S_ISREG(identity.st_mode)):
                raise ValueError('Nonregular or symlink retained member refused')
            # Directory entries are encountered twice by walk; charge exactly once.
            if stat.S_ISDIR(identity.st_mode) and path != Path(folder):
                continue
            allocated += identity.st_blocks * 512
            if stat.S_ISDIR(identity.st_mode):
                directories += 1
                continue
            if identity.st_nlink != 1:
                raise ValueError('Hardlinked retained member refused')
            logical += identity.st_size
            row = {'path': str(path.relative_to(root)), 'bytes': identity.st_size,
                   'allocated_bytes': identity.st_blocks * 512}
            if hashes:
                row['sha256'] = file_pin(path)['sha256']
            files.append(row)
    return {'logical_bytes': logical, 'allocated_bytes_including_directories': allocated,
            'directory_count': directories, 'files': sorted(files, key=lambda row: row['path'])}


def signal_observed(root_pid, known, sig):
    try:
        os.killpg(root_pid, sig)
    except ProcessLookupError:
        pass
    for pid, start in known:
        if pid == root_pid:
            continue
        row = proc_row(pid)
        if row and row['start_ticks'] == start:
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                pass


def subreaper(enable=None):
    libc = ctypes.CDLL(None, use_errno=True)
    current = ctypes.c_int()
    if libc.prctl(37, ctypes.byref(current), 0, 0, 0) != 0:
        raise OSError('Linux subreaper observation unavailable')
    if enable is not None and libc.prctl(36, int(enable), 0, 0, 0) != 0:
        raise OSError('Linux subreaper setup unavailable')
    return current.value


def supervise(output, proof_path, *, repository_root=None, injected_command=None,
              synthetic_environment=None, expected_sources=EXPECTED_SOURCES,
              limits=None, runtime_paths=None):
    """One launch. Injection is for disjoint synthetic tests, never CLI dispatch."""
    root = Path(repository_root or Path(__file__).resolve().parents[1])
    output = checked_path(output, absent=True)
    proof_raw, _ = read_regular(proof_path, 256 * 1024)
    proof, source_before = proof_sources(proof_raw, root, expected_sources)
    synthetic = injected_command is not None
    if not synthetic and (expected_sources != EXPECTED_SOURCES or limits is not None or synthetic_environment is not None):
        raise ValueError('Production supervision cannot override fixed admission or limits')
    settings = dict(DEFAULT_LIMITS)
    if limits:
        if any(key not in settings or type(value) not in (int, float) or value <= 0
               or value > settings[key] for key, value in limits.items()):
            raise ValueError('Synthetic limits may only lower positive bounds')
        settings.update(limits)
    environment = dict(synthetic_environment or {}) if synthetic else child_environment(proof)
    if synthetic and 'GITHUB_TOKEN' in environment:
        raise ValueError('Synthetic children cannot receive a live credential')
    paths = list(runtime_paths or selected_runtime_paths())
    runtime_before = [file_pin(path) for path in paths]
    old_subreaper = subreaper()
    output.mkdir(mode=0o700)
    root_identity = output.lstat()
    persist(output / 'supervisorclaim.json', canonical({'namespace': NAMESPACE,
        'activation': proof['activation'], 'run_id': proof['run_id'],
        'claimed_epoch_ns': time.time_ns(), 'no_retry': True,
        'component_only': True, 'scientific_authority': False}))
    persist(output / 'gateproof.json', proof_raw)
    persist(output / 'before.json', canonical({'source_files': source_before,
        'selected_runtime_files': runtime_before, 'python': sys.version,
        'executable': str(Path(sys.executable).resolve()),
        'selection_is_complete_ELF_or_scientific_freeze': False,
        'component_only': True, 'scientific_authority': False}))
    command = (list(injected_command) if synthetic else [sys.executable, '-I',
        str(root / PREFIX / 'control.py'), '--output', str(output / 'child'),
        '--activation', proof['activation'], '--proof', str(output / 'gateproof.json')])
    # Credential is passed only in the explicit env; argv contains no credential.
    launch_record = {'argv': command, 'environment_keys': sorted(environment),
        'child_seconds': settings['child_seconds'], 'reap_seconds': settings['reap_seconds'],
        'limits': settings, 'domain': 'synthetic-test-fixture' if synthetic else 'hosted-component-observation',
        'component_only': True, 'scientific_authority': False}
    persist(output / 'launch.json', canonical(launch_record))
    started = time.monotonic()
    start_epoch = time.time_ns()
    process = None
    selector = selectors.DefaultSelector()
    streams = {}
    known = set()
    peaks = {}
    observations = samples = aggregate_peak = parent_peak = 0
    dispositions = []
    root_status = None
    failure = None
    terminated_at = None
    total_output = 0
    launch_attempted = False
    try:
        subreaper(True)
        launch_attempted = True
        process = subprocess.Popen(command, env=environment, cwd=str(root),
            stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            start_new_session=True, close_fds=True)
        for name, pipe in (('stdout', process.stdout), ('stderr', process.stderr)):
            descriptor = os.open(output / (name + '.bin'), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            target = os.fdopen(descriptor, 'wb', buffering=0)
            os.set_blocking(pipe.fileno(), False)
            streams[name] = {'pipe': pipe, 'target': target, 'bytes': 0,
                             'observed_bytes': 0, 'full_retained': True}
            selector.register(pipe, selectors.EVENT_READ, name)
        while True:
            elapsed = time.monotonic() - started
            rows = proc_tree(process.pid, known)
            samples += 1
            observations += len(rows)
            parent = proc_row(os.getpid())
            parent_peak = max(parent_peak, (parent or {}).get('rss_bytes', 0))
            aggregate_peak = max(aggregate_peak, sum(row['rss_bytes'] for row in rows))
            for row in rows:
                identity = (row['pid'], row['start_ticks'])
                known.add(identity)
                key = str(identity[0]) + '@' + str(identity[1])
                previous = peaks.get(key, dict(row, observations=0))
                previous['rss_bytes'] = max(previous['rss_bytes'], row['rss_bytes'])
                previous['hwm_bytes'] = max(previous['hwm_bytes'], row['hwm_bytes'])
                previous['observations'] += 1
                peaks[key] = previous
                if row['rss_bytes'] > settings['rss_bytes']:
                    failure = failure or 'sampled_individual_rss_limit'
            if len(known) > settings['max_observed_processes']:
                failure = failure or 'observed_process_count_limit'
            if elapsed >= settings['child_seconds']:
                failure = failure or 'whole_child_deadline'
            try:
                current_root = output.lstat()
                if (current_root.st_dev, current_root.st_ino) != (root_identity.st_dev, root_identity.st_ino):
                    raise ValueError('Original retained root was replaced')
                storage = storage_inventory(output)
                if max(storage['logical_bytes'], storage['allocated_bytes_including_directories']) + settings['metadata_reserve'] > settings['storage_bytes']:
                    failure = failure or 'retained_storage_limit'
            except (OSError, ValueError):
                failure = failure or 'retained_storage_identity_failure'
            if failure and terminated_at is None:
                terminated_at = time.monotonic()
                signal_observed(process.pid, known, signal.SIGKILL)
            for key, _ in selector.select(settings['sample_seconds']):
                stream = streams[key.data]
                chunk = os.read(key.fileobj.fileno(), 65536)
                if not chunk:
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                    continue
                stream['observed_bytes'] += len(chunk)
                room = min(settings['stream_bytes'] - stream['bytes'], settings['combined_bytes'] - total_output)
                retained = chunk[:max(0, int(room))]
                stream['target'].write(retained)
                stream['bytes'] += len(retained)
                total_output += len(retained)
                if len(retained) != len(chunk):
                    stream['full_retained'] = False
                    failure = failure or 'raw_stream_limit'
            while True:
                try:
                    pid, status, usage = os.wait4(-1, os.WNOHANG)
                except ChildProcessError:
                    break
                if pid == 0:
                    break
                disposition = {'pid': pid, 'wait_status': status,
                    'exit_code': os.waitstatus_to_exitcode(status),
                    'wait4_max_rss_bytes': int(usage.ru_maxrss) * 1024,
                    'user_seconds': usage.ru_utime, 'system_seconds': usage.ru_stime,
                    'reaped_epoch_ns': time.time_ns(), 'reaped_elapsed_seconds': time.monotonic() - started}
                dispositions.append(disposition)
                if pid == process.pid:
                    root_status = disposition
                    process.returncode = disposition['exit_code']
                    if root_status['exit_code'] != 0:
                        failure = failure or 'child_nonzero_exit'
            live = [row for row in proc_tree(process.pid, known) if row['state'] != 'Z']
            if root_status is not None and live and terminated_at is None:
                failure = failure or 'descendants_survived_direct_child'
                terminated_at = time.monotonic()
                signal_observed(process.pid, known, signal.SIGKILL)
            if root_status is not None and not selector.get_map() and not live:
                break
            if time.monotonic() - started >= settings['child_seconds'] + settings['reap_seconds']:
                failure = failure or 'bounded_reaping_incomplete'
                signal_observed(process.pid, known, signal.SIGKILL)
                break
    except BaseException as error:
        # Exception text can include sensitive paths or service details; retain
        # only its class, while raw child streams are retained independently.
        failure = failure or 'supervisor_exception_' + type(error).__name__
        if process is not None:
            signal_observed(process.pid, known, signal.SIGKILL)
            until = started + settings['child_seconds'] + settings['reap_seconds']
            while root_status is None and time.monotonic() < until:
                try:
                    pid, status, usage = os.wait4(process.pid, os.WNOHANG)
                except ChildProcessError:
                    break
                if pid:
                    root_status = {'pid': pid, 'wait_status': status,
                        'exit_code': os.waitstatus_to_exitcode(status),
                        'wait4_max_rss_bytes': int(usage.ru_maxrss) * 1024,
                        'user_seconds': usage.ru_utime, 'system_seconds': usage.ru_stime,
                        'reaped_epoch_ns': time.time_ns(),
                        'reaped_elapsed_seconds': time.monotonic() - started}
                    process.returncode = root_status['exit_code']
                    dispositions.append(root_status)
                else:
                    time.sleep(min(0.01, settings['sample_seconds']))
    finally:
        for stream in streams.values():
            try:
                stream['target'].flush()
                os.fsync(stream['target'].fileno())
            finally:
                stream['target'].close()
                stream['pipe'].close()
        selector.close()
        subreaper(bool(old_subreaper))
    finished = time.monotonic()
    source_after = runtime_after = None
    try:
        _, source_after = proof_sources(proof_raw, root, expected_sources)
        runtime_after = [file_pin(path) for path in paths]
        if source_after != source_before or runtime_after != runtime_before:
            failure = failure or 'source_or_selected_runtime_changed'
    except (OSError, ValueError):
        failure = failure or 'source_or_selected_runtime_readback_failed'
    persist(output / 'after.json', canonical({'source_files': source_after,
        'selected_runtime_files': runtime_after, 'component_only': True,
        'scientific_authority': False}))
    stream_records = {}
    for name, stream in streams.items():
        pin = file_pin(output / (name + '.bin'))
        stream_records[name] = {'bytes': stream['bytes'], 'observed_bytes': stream['observed_bytes'],
            'full_retained': stream['full_retained'], 'sha256': pin['sha256']}
    if root_status is None:
        failure = failure or 'direct_child_reaping_not_proven'
    result = {'schema': 'radio-hosted-cas-supervisor-observation-v1', 'namespace': NAMESPACE,
        'status': 'COMPONENT_OBSERVED' if failure is None else 'CLOSED_FAILED',
        'failure': failure, 'started_epoch_ns': start_epoch, 'finished_epoch_ns': time.time_ns(),
        'whole_child_elapsed_seconds': finished - started,
        'launch_attempted': launch_attempted, 'launched': process is not None,
        'no_child_launch_proven': not launch_attempted,
        'direct_child': root_status, 'wait4_dispositions': dispositions,
        'direct_child_reaped': root_status is not None, 'streams': stream_records,
        'procfs': {'sample_count': samples, 'process_observations': observations,
            'individual_process_peaks': peaks, 'aggregate_sampled_peak_bytes': aggregate_peak,
            'parent_sampled_peak_bytes': parent_peak,
            'sampling_cannot_prove_all_short_lived_or_escaped_descendants': True,
            'sampled_RSS_is_not_complete_peak_or_enforced_kernel_limit': True,
            'parent_RSS_is_point_sample_observation_only': True,
            'subreaper_enabled_for_directly_orphaned_descendant_reaping': True},
        'selected_runtime_before_after_match': runtime_before == runtime_after,
        'selected_sources_before_after_match': source_before == source_after,
        'complete_ELF_source_runtime_or_hosted_transport_certificate': False,
        'domain': 'synthetic-test-fixture' if synthetic else 'hosted-component-observation',
        'component_only': True, 'scientific_authority': False, 'no_retry': True}
    persist(output / 'terminal.json', canonical(result))
    try:
        inventory = storage_inventory(output, hashes=True)
        persist(output / 'inventory.json', canonical(inventory))
        # Include inventory itself and directory blocks; no self-hash claim.
        accounting = storage_inventory(output)
        accounting.pop('files')
        receipt = canonical({'storage_before_this_accounting_file': accounting,
            'accounting_file_reserve_bytes': 65536,
            'storage_limit_bytes': settings['storage_bytes'],
            'component_only': True, 'scientific_authority': False})
        conservative = max(accounting['logical_bytes'], accounting['allocated_bytes_including_directories']) + 65536
        if conservative > settings['storage_bytes']:
            failure = failure or 'final_retained_storage_limit'
        persist(output / 'storage-accounting.json', receipt)
    except (OSError, ValueError):
        failure = failure or 'final_storage_inventory_failed'
    # A final status is separate from the already retained immutable terminal.
    persist(output / 'supervisor-outcome.json', canonical({'status': 'COMPONENT_OBSERVED' if failure is None else 'CLOSED_FAILED',
        'failure': failure, 'direct_child_exit_code': (root_status or {}).get('exit_code'),
        'launched': process is not None, 'no_child_launch_proven': not launch_attempted,
        'component_only': True, 'scientific_authority': False, 'no_retry': True}))
    return 0 if failure is None else ((root_status or {}).get('exit_code') or 1) if (root_status or {}).get('exit_code', 1) > 0 else 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--proof', required=True)
    args = parser.parse_args()
    try:
        return supervise(args.output, args.proof)
    except BaseException as error:
        # No credential, proof contents or uncontrolled exception text is logged.
        print('Supervisor refused: ' + type(error).__name__, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
