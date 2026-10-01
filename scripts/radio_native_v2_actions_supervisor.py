#!/usr/bin/env python3
"""Independent Linux lifetime observer for one stdlib publication control.

The child cannot create processes or threads: a kernel seccomp filter denies
fork/vfork/clone/clone3 before exec. wait4 supplies the direct child's complete
kernel peak. No native case, random generator or scientific input is executed.
"""
import argparse
import ctypes
import gzip
import hashlib
import http.client
import json
import os
from pathlib import Path
import platform
import re
import resource
import selectors
import signal
import ssl
import stat
import subprocess
import sys
import sysconfig
import time

NAMESPACE = 'radio-native-v2-actions-control-20261001a'
PUBLISHER = 'scripts/radio_native_v2_actions_publisher_control.py'
MARKER = 'config/radio_native_v2_actions_control_20261001a.activate.json'
MANIFEST = 'config/radio_native_v2_actions_control_20261001a.manifest.json'
RSS_CAP = 512 * 1024 * 1024
SECONDS_CAP = 600
STORAGE_CAP = 192 * 1024 * 1024
LOG_CAP = 64 * 1024
DISABLED = ('reservation_authorized', 'rng_authorized', 'execution_authorized',
            'scientific_execution_authorized', 'restart_authorized',
            'transport_integration_qualified')
REQUIRED_FILES = frozenset((PUBLISHER, 'scripts/radio_native_v2_actions_supervisor.py',
    'scripts/radio_native_v2_actions_activation_gate.py',
    '.github/workflows/radio_native_v2_actions_control_20261001a.yml',
    'config/radio_native_v2_actions_control_20261001a.protocol.json'))


def sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def save_json(path, value):
    path = Path(path)
    payload = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + '\n').encode()
    expected_sha = hashlib.sha256(payload).hexdigest()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'wb') as target:
        target.write(payload)
        target.flush()
        os.fsync(target.fileno())
        written_identity = os.fstat(target.fileno())
    directory = os.open(Path(path).parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as reopened:
        identity = os.fstat(reopened.fileno())
        if (not stat.S_ISREG(identity.st_mode) or identity.st_nlink != 1
                or (identity.st_dev, identity.st_ino) != (written_identity.st_dev, written_identity.st_ino)):
            raise ValueError('Observer receipt identity changed after persistence')
        checksum = hashlib.sha256()
        count = 0
        for block in iter(lambda: reopened.read(65536), b''):
            count += len(block)
            checksum.update(block)
        if count != len(payload) or checksum.hexdigest() != expected_sha:
            raise ValueError('Observer receipt exact readback failed')


def file_record(path):
    path = Path(path)
    stat = path.stat()
    return {'path': str(path), 'bytes': stat.st_size,
            'allocated_bytes': stat.st_blocks * 512, 'sha256': sha_file(path)}


def proc_record(pid):
    """Read public process identity/size only; argv tails and environ are unread."""
    try:
        directory = Path('/proc') / str(pid)
        raw = (directory / 'stat').read_text()
        fields = raw[raw.rfind(')') + 2:].split()
        values = {}
        for line in (directory / 'status').read_text().splitlines():
            key, _, value = line.partition(':')
            if key in ('VmRSS', 'VmHWM'):
                values[key] = int(value.split()[0]) * 1024
            elif key == 'Seccomp':
                values[key] = int(value.strip())
        # Reading at most the first executable name avoids argument credentials.
        with (directory / 'cmdline').open('rb') as source:
            first = source.read(4096).split(b'\0', 1)[0]
        basename = os.path.basename(first.decode(errors='replace')) if first else raw[raw.find('(') + 1:raw.rfind(')')]
        return {'pid': int(pid), 'ppid': int(fields[1]),
                'start_ticks': int(fields[19]), 'state': fields[0],
                'identity': str(pid) + '@' + fields[19],
                'command_basename': basename, 'rss_bytes': values.get('VmRSS', 0),
                'hwm_bytes': values.get('VmHWM', 0),
                'seccomp_mode': values.get('Seccomp')}
    except (OSError, ValueError, IndexError):
        return None


def proc_snapshot():
    records = {}
    for path in Path('/proc').iterdir():
        if path.name.isdigit():
            value = proc_record(int(path.name))
            if value:
                records[value['pid']] = value
    return records


def descendants(records, parent_pid):
    found, frontier = [], [parent_pid]
    while frontier:
        parent = frontier.pop()
        children = [row for row in records.values() if row['ppid'] == parent]
        found.extend(children)
        frontier.extend(row['pid'] for row in children)
    return found


def seccomp_policy():
    machine = platform.machine().lower()
    if machine in ('x86_64', 'amd64'):
        return {'architecture': machine, 'audit_arch': 0xc000003e,
                'denied_syscalls': [56, 57, 58, 435], 'x32_denied': True}
    if machine in ('aarch64', 'arm64'):
        return {'architecture': machine, 'audit_arch': 0xc00000b7,
                'denied_syscalls': [220, 435], 'x32_denied': False}
    raise RuntimeError('Unsupported Linux seccomp architecture')


def install_no_children_filter():
    """Install before exec; Popen's exec handshake fails if this cannot install."""
    policy = seccomp_policy()
    class Filter(ctypes.Structure):
        _fields_ = [('code', ctypes.c_ushort), ('jt', ctypes.c_ubyte),
                    ('jf', ctypes.c_ubyte), ('k', ctypes.c_uint32)]
    class Program(ctypes.Structure):
        _fields_ = [('len', ctypes.c_ushort), ('filter', ctypes.POINTER(Filter))]
    # Load arch; reject foreign ABIs. Load syscall; deny x32 and child creation.
    instructions = [(0x20, 0, 0, 4),
                    (0x15, 1, 0, policy['audit_arch']),
                    (0x06, 0, 0, 0x80000000),
                    (0x20, 0, 0, 0)]
    if policy['x32_denied']:
        instructions.extend([(0x35, 0, 1, 0x40000000),
                             (0x06, 0, 0, 0x00050001)])
    for number in policy['denied_syscalls']:
        instructions.extend([(0x15, 0, 1, number), (0x06, 0, 0, 0x00050001)])
    instructions.append((0x06, 0, 0, 0x7fff0000))
    filters = (Filter * len(instructions))(*(Filter(*row) for row in instructions))
    program = Program(len(instructions), filters)
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(38, 1, 0, 0, 0) != 0 or libc.prctl(22, 2, ctypes.byref(program)) != 0:
        raise OSError(ctypes.get_errno(), 'Kernel process-creation filter unavailable')


def runtime_inventory(root):
    """Before launch: stdlib files, loaded native closure, CA roots and public image."""
    root = Path(root)
    files = {Path(sys.executable).resolve()}
    stdlib = Path(sysconfig.get_path('stdlib')).resolve()
    for folder, directories, names in os.walk(stdlib):
        directories[:] = sorted(name for name in directories
                                if name not in ('site-packages', 'dist-packages'))
        for name in names:
            candidate = Path(folder) / name
            if candidate.is_file() and candidate.suffix in ('.py', '.pyc', '.so'):
                files.add(candidate.resolve())
    for entry in sys.path:
        if entry and Path(entry).is_file():
            files.add(Path(entry).resolve())
    # http.client/ssl/gzip/ctypes imported above force their actual native closure.
    for line in Path('/proc/self/maps').read_text().splitlines():
        parts = line.split(None, 5)
        if len(parts) == 6 and parts[5].startswith('/'):
            candidate = Path(parts[5])
            if candidate.is_file():
                files.add(candidate.resolve())
    certificates = ssl.get_default_verify_paths()
    if certificates.cafile and Path(certificates.cafile).is_file():
        files.add(Path(certificates.cafile).resolve())
    if certificates.capath:
        for path in Path(certificates.capath).iterdir():
            if path.is_file():
                files.add(path.resolve())
    # Configuration selects OpenSSL providers and trust-store behaviour.
    for config in (Path('/usr/lib/ssl/openssl.cnf'), Path('/etc/ssl/openssl.cnf')):
        if config.is_file():
            files.add(config.resolve())
    for key in ('OPENSSL_CONF', 'SSL_CERT_FILE'):
        configured = os.environ.get(key)
        if configured and Path(configured).is_file():
            files.add(Path(configured).resolve())
    image = {'kernel': platform.release(), 'machine': platform.machine(),
             'system': platform.system()}
    image_file = Path('/etc/os-release')
    if image_file.is_file():
        image['os_release'] = image_file.read_text()
        files.add(image_file.resolve())
    # These are public hosted-runner image identifiers, never general env values.
    image['hosted_runner'] = {key: os.environ.get(key) for key in ('ImageOS', 'ImageVersion')}
    records = [file_record(path) for path in sorted(files)]
    return {'schema': 'radio-native-v2-actions-engineering-runtime-inventory-v1',
            'captured_before_publisher_launch': True, 'python': sys.version,
            'openssl': ssl.OPENSSL_VERSION, 'executable': str(Path(sys.executable).resolve()),
            'stdlib': str(stdlib), 'runtime_files': records, 'image': image,
            'inventory_method': 'stdlib-source-bytecode-and-extension-files-plus-runtime-zips-loaded-native-maps-OpenSSL-config-and-CA-roots',
            'future_native_runtime_qualified': False, **{key: False for key in DISABLED}}


def validate_inputs(root, activation, expected_parent, protocol_path, proof_path):
    if not re.fullmatch('[0-9a-f]{40}', activation) or expected_parent != activation:
        raise ValueError('Exact activation/expected-parent identity required')
    root = Path(root).resolve()
    protocol_path, proof_path = Path(protocol_path), Path(proof_path)
    if not protocol_path.is_absolute():
        protocol_path = root / protocol_path
    if not proof_path.is_absolute():
        raise ValueError('Activation proof must be an absolute exclusive gate output')
    if (protocol_path.is_symlink() or proof_path.is_symlink()
            or protocol_path.resolve() != root / 'config/radio_native_v2_actions_control_20261001a.protocol.json'):
        raise ValueError('Unsafe protocol or activation proof')
    protocol = json.loads(protocol_path.read_text())
    proof = json.loads(proof_path.read_text())
    manifest_raw = (root / MANIFEST).read_bytes()
    manifest = json.loads(manifest_raw)
    marker = json.loads((root / MARKER).read_text())
    if (protocol.get('namespace') != NAMESPACE or manifest.get('namespace') != NAMESPACE
            or marker.get('namespace') != NAMESPACE or marker.get('activate') is not True
            or proof.get('schema') != 'radio-native-v2-actions-activation-readback-v1'
            or proof.get('namespace') != NAMESPACE or proof.get('verified') is not True
            or proof.get('activation_commit') != activation
            or proof.get('preparation_commit') != marker.get('preparation_commit')
            or proof.get('manifest_sha256') != sha_file(root / MANIFEST)
            or marker.get('manifest_sha256') != proof.get('manifest_sha256')):
        raise ValueError('Activation readback binding mismatch')
    for document in (protocol, proof, manifest, marker):
        if any(document.get(key) is not False for key in DISABLED):
            raise ValueError('Engineering evidence cannot grant execution authority')
    caps = protocol.get('caps', {})
    expected = {'rss_per_process_bytes': RSS_CAP, 'seconds': SECONDS_CAP,
                'host_receipt_bytes': STORAGE_CAP, 'operations': 64,
                'request_bytes': 48 * 1024 * 1024, 'reply_bytes': 64 * 1024 * 1024,
                'spool_bytes': 40 * 1024 * 1024}
    if any(caps.get(key) != value for key, value in expected.items()):
        raise ValueError('Original resource caps changed')
    entries = manifest.get('files', [])
    if len(entries) != len(REQUIRED_FILES) or {row.get('path') for row in entries} != REQUIRED_FILES:
        raise ValueError('Incomplete preparation source closure')
    for item in entries:
        relative = Path(item['path'])
        path = root / relative
        if (relative.is_absolute() or '..' in relative.parts or path.is_symlink()
                or not path.is_file() or not path.resolve().is_relative_to(root)
                or path.stat().st_size != item.get('bytes') or sha_file(path) != item.get('sha256')):
            raise ValueError('Prepared source identity differs')
    return protocol_path.resolve(), proof, entries


def supervise_process(command, output, *, seconds=SECONDS_CAP, rss_cap=RSS_CAP,
                      sample_seconds=0.02, log_cap=LOG_CAP):
    """One launch, no retry. The directory already exists and has no log files."""
    if not 0 < seconds <= SECONDS_CAP or not 0 < rss_cap <= RSS_CAP:
        raise ValueError('Resource caps must remain within original limits')
    output = Path(output)
    policy = seccomp_policy()
    parent_pid = int(os.readlink('/proc/self'))
    before = proc_snapshot()
    own = before.get(parent_pid)
    started_epoch = time.time_ns() // 1000000
    started = time.monotonic()
    failures, seen, direct_identity = [], {}, None
    peak_supervisor = 0
    child = None
    kernel = None
    status = None
    coverage_errors = []
    captured = {'stdout': 0, 'stderr': 0}
    received = {'stdout': 0, 'stderr': 0}
    with (output / 'publisher-stdout.log').open('xb') as stdout, \
            (output / 'publisher-stderr.log').open('xb') as stderr, \
            (output / 'procfs-samples.jsonl').open('x', encoding='ascii') as samples:
        try:
            child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     start_new_session=True, close_fds=True,
                                     preexec_fn=install_no_children_filter)
        except (OSError, subprocess.SubprocessError):
            failures.append('publisher_launch_or_kernel_no_children_filter_failed')
        if child:
            selector = selectors.DefaultSelector()
            for pipe, label, target in ((child.stdout, 'stdout', stdout), (child.stderr, 'stderr', stderr)):
                os.set_blocking(pipe.fileno(), False)
                selector.register(pipe, selectors.EVENT_READ, (label, target))

            def drain_logs():
                for key, _ in selector.select(0):
                    label, target = key.data
                    try:
                        block = os.read(key.fileobj.fileno(), 32768)
                    except BlockingIOError:
                        continue
                    if not block:
                        selector.unregister(key.fileobj)
                        key.fileobj.close()
                        continue
                    received[label] += len(block)
                    available = max(0, log_cap - captured[label])
                    target.write(block[:available])
                    captured[label] += min(available, len(block))
                    if received[label] > log_cap and 'bounded_log_cap_exceeded' not in failures:
                        failures.append('bounded_log_cap_exceeded')

            try:
                while True:
                    now = time.monotonic()
                    drain_logs()
                    records = proc_snapshot()
                    own = records.get(parent_pid)
                    if own:
                        peak_supervisor = max(peak_supervisor, own['rss_bytes'], own['hwm_bytes'])
                    if direct_identity is None:
                        candidates = [row for row in records.values()
                                      if row['ppid'] == parent_pid
                                      and (row['pid'] not in before
                                           or row['identity'] != before[row['pid']]['identity'])]
                        native = records.get(child.pid)
                        if native in candidates:
                            candidates = [native]
                        if len(candidates) == 1:
                            direct_identity = candidates[0]['identity']
                    active = [row for row in records.values() if row['identity'] == direct_identity]
                    unexpected = descendants(records, active[0]['pid']) if active else []
                    if unexpected and 'unexpected_descendant' not in failures:
                        failures.append('unexpected_descendant')
                    for row in active + unexpected:
                        previous = seen.setdefault(row['identity'], {
                            'identity': row['identity'], 'pid': row['pid'],
                            'command_basename': row['command_basename'],
                            'peak_procfs_bytes': 0, 'first_sample_epoch_ms': time.time_ns() // 1000000})
                        previous['peak_procfs_bytes'] = max(previous['peak_procfs_bytes'], row['rss_bytes'], row['hwm_bytes'])
                        previous['last_sample_epoch_ms'] = time.time_ns() // 1000000
                        if row['identity'] == direct_identity and row['seccomp_mode'] != 2:
                            coverage_errors.append('direct_child_seccomp_mode_not_filter')
                        if previous['peak_procfs_bytes'] > rss_cap and 'rss_cap_exceeded' not in failures:
                            failures.append('rss_cap_exceeded')
                    samples.write(json.dumps({'elapsed_seconds': now - started,
                        'epoch_ms': time.time_ns() // 1000000,
                        'supervisor_rss_bytes': own['rss_bytes'] if own else None,
                        'supervisor_hwm_bytes': own['hwm_bytes'] if own else None,
                        'processes': active + unexpected}, sort_keys=True, separators=(',', ':')) + '\n')
                    if peak_supervisor > rss_cap and 'supervisor_rss_cap_exceeded' not in failures:
                        failures.append('supervisor_rss_cap_exceeded')
                    if now - started > seconds and 'deadline_exceeded' not in failures:
                        failures.append('deadline_exceeded')
                    if failures:
                        try:
                            os.killpg(child.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    waited, status_value, usage = os.wait4(child.pid, os.WNOHANG)
                    if waited:
                        status, kernel = status_value, usage
                        child.returncode = os.waitstatus_to_exitcode(status)
                        break
                    time.sleep(sample_seconds)
                # With kernel-enforced zero children, both pipes reach EOF at exit.
                while selector.get_map():
                    drain_logs()
            except BaseException:
                failures.append('observer_internal_failure')
                coverage_errors.append('observer_interval_interrupted')
            finally:
                if child.returncode is None:
                    try:
                        os.killpg(child.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    _, status, kernel = os.wait4(child.pid, 0)
                    child.returncode = os.waitstatus_to_exitcode(status)
                for key in list(selector.get_map().values()):
                    selector.unregister(key.fileobj)
                    key.fileobj.close()
                selector.close()
        samples.flush()
        os.fsync(samples.fileno())
        stdout.flush()
        stderr.flush()
        os.fsync(stdout.fileno())
        os.fsync(stderr.fileno())
    elapsed = time.monotonic() - started
    kernel_peak = int(kernel.ru_maxrss * 1024) if kernel else None
    own_usage = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
    peak_supervisor = max(peak_supervisor, own_usage)
    proc_peak = seen.get(direct_identity, {}).get('peak_procfs_bytes', 0)
    if kernel_peak is not None and kernel_peak > rss_cap:
        failures.append('kernel_child_rss_cap_exceeded')
    if peak_supervisor > rss_cap:
        failures.append('kernel_supervisor_rss_cap_exceeded')
    if elapsed > seconds:
        failures.append('complete_child_interval_deadline_exceeded')
    if child and child.returncode != 0:
        failures.append('publisher_nonzero_exit')
    if child and direct_identity is None:
        coverage_errors.append('direct_procfs_identity_unobserved')
    complete = bool(child and kernel is not None and direct_identity and not coverage_errors)
    return {'schema': 'radio-native-v2-actions-independent-process-observation-v1',
        'namespace': NAMESPACE, 'status': 'PASS_COMPONENT_RESOURCE_OBSERVATION' if complete and not failures else 'CLOSED_FAILED',
        'started_at_epoch_ms': started_epoch, 'finished_at_epoch_ms': time.time_ns() // 1000000,
        'elapsed_seconds': elapsed, 'rss_cap_per_process_bytes': rss_cap,
        'deadline_seconds': seconds, 'direct_child_identity': direct_identity,
        'direct_child_command_basename': Path(command[0]).name,
        'direct_child_exit_code': child.returncode if child else None,
        'direct_child_kernel_wait4_peak_rss_bytes': kernel_peak,
        'direct_child_peak_rss_bytes': max(proc_peak, kernel_peak or 0),
        'supervisor_identity': own['identity'] if child and own else str(parent_pid),
        'supervisor_peak_rss_bytes': peak_supervisor, 'processes': list(seen.values()),
        'process_creation_policy': {**policy, 'installed_before_exec': bool(child),
            'mechanism': 'Linux seccomp filter returns EPERM for fork/vfork/clone/clone3; foreign ABI killed'},
        'expected_material_descendant_count': 0,
        'observed_descendant_count': max(0, len(seen) - int(direct_identity in seen)),
        'descendant_lifetime_coverage': 'kernel_process_creation_prohibited' if child else 'UNKNOWN',
        'direct_child_termination_coverage_complete': complete,
        'failures': sorted(set(failures)), 'coverage_errors': sorted(set(coverage_errors)),
        'bounded_logs': {'cap_bytes_per_stream': log_cap,
            'received_bytes': received, 'retained_bytes': captured,
            'truncated': any(received[key] > captured[key] for key in received)},
        'status_scope': 'publisher lifetime resource observation; final disposition is supervisor-terminal.json',
        'full_actions_job_resource_qualified': False, 'native_eight_cases_qualified': False,
        'authority': {key: False for key in DISABLED}}


def storage_inventory(output):
    output = Path(output)
    entries = []
    for path in [output, *sorted(output.rglob('*'))]:
        info = path.lstat()
        if path.is_symlink() or not (path.is_file() or path.is_dir()):
            raise ValueError('Unexpected evidence storage object')
        if path.is_file() and info.st_nlink != 1:
            raise ValueError('Evidence hardlink is not separate receipt custody')
        if path.name != 'supervisor-storage-inventory.json':
            row = file_record(path) if path.is_file() else {
                'bytes': info.st_size, 'allocated_bytes': info.st_blocks * 512}
            row['path'] = str(path.relative_to(output))
            row['directory'] = path.is_dir()
            entries.append(row)
    return {'schema': 'radio-native-v2-actions-supervisor-storage-v1', 'files': entries,
        'logical_bytes': sum(row['bytes'] for row in entries),
        'allocated_bytes': sum(row['allocated_bytes'] for row in entries),
        'host_receipt_cap_bytes': STORAGE_CAP, 'git_spool_bytes': 0,
        'excluded_files': ['supervisor-storage-inventory.json', 'supervisor-terminal.json'],
        'exclusion_reason': 'Inventory cannot hash itself; terminal written afterwards with reserved actual storage; terminal audits actual prior files including inventory'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', default='.')
    parser.add_argument('--output', required=True)
    parser.add_argument('--activation-sha', required=True)
    parser.add_argument('--expected-parent', required=True)
    parser.add_argument('--protocol', required=True)
    parser.add_argument('--activation-proof', required=True)
    args = parser.parse_args()
    root, output = Path(args.root).resolve(), Path(args.output)
    if not output.is_absolute() or output.is_symlink():
        raise ValueError('Fresh absolute evidence directory required')
    output.mkdir()  # A consumed or existing namespace is never resumed.
    report = None
    try:
        protocol, proof, sources = validate_inputs(root, args.activation_sha,
            args.expected_parent, args.protocol, args.activation_proof)
        save_json(output / 'activation-proof.json', proof)
        save_json(output / 'prepared-source-inventory.json', {'files': sources,
            'activation_sha': args.activation_sha, 'expected_parent': args.expected_parent,
            'all_authority_false': True})
        runtime = runtime_inventory(root)
        save_json(output / 'runtime-inventory-before-control.json', runtime)
        command = [sys.executable, '-I', '-S', '-B', str(root / PUBLISHER), 'control',
            '--root', str(root), '--output', str(output / 'publisher'),
            '--activation-sha', args.activation_sha, '--expected-parent', args.expected_parent,
            '--protocol', str(protocol), '--activation-proof', str(Path(args.activation_proof))]
        report = supervise_process(command, output)
        summary_path = output / 'publisher' / 'caller-summary.json'
        if not summary_path.is_file():
            report['failures'].append('publisher_summary_missing')
        else:
            summary = json.loads(summary_path.read_text())
            report['publisher_summary_binding'] = file_record(summary_path)
            if summary.get('status') != 'PUBLISHED_SOURCE_CONTROL_COMPONENT_ONLY':
                report['failures'].append('publisher_component_control_not_passed')
            if any(summary.get(key) is not False for key in DISABLED):
                report['failures'].append('publisher_authority_not_disabled')
        if report['failures']:
            report['status'] = 'CLOSED_FAILED'
    except Exception as error:
        # Exception messages may contain remote/request details; public code only.
        report = {'schema': 'radio-native-v2-actions-independent-process-observation-v1',
            'namespace': NAMESPACE, 'status': 'CLOSED_FAILED',
            'failures': ['supervisor_' + type(error).__name__],
            'authority': {key: False for key in DISABLED}}
    save_json(output / 'supervisor-report.json', report)
    inventory = storage_inventory(output)
    save_json(output / 'supervisor-storage-inventory.json', inventory)
    final_paths = [output, *output.rglob('*')]
    final_logical = sum(path.lstat().st_size for path in final_paths)
    final_allocated = sum(path.lstat().st_blocks * 512 for path in final_paths)
    final_peak = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)
    terminal_reserve = 2 * max(4096, os.statvfs(output).f_frsize)
    passed = report['status'] == 'PASS_COMPONENT_RESOURCE_OBSERVATION'
    passed = passed and max(final_logical, final_allocated) + terminal_reserve <= STORAGE_CAP and final_peak <= RSS_CAP
    # Bounded summary contains no request body, authentication value or env dump.
    terminal = {'schema': 'radio-native-v2-actions-supervisor-terminal-v1',
        'status': 'PASS_COMPONENT_CONTROL' if passed else 'CLOSED_FAILED',
        'storage_logical_bytes_before_terminal': final_logical,
        'storage_allocated_bytes_before_terminal': final_allocated,
        'terminal_storage_reservation_bytes': terminal_reserve,
        'storage_cap_bytes': STORAGE_CAP,
        'supervisor_peak_rss_bytes': final_peak, 'native_eight_cases_qualified': False,
        'supervisor_peak_coverage': 'process startup through storage inventory persistence; terminal persistence and parent termination are outside component proof',
        'complete_supervisor_termination_coverage': False,
        'full_actions_job_resource_qualified': False,
        **{key: False for key in DISABLED}}
    terminal_path = output / 'supervisor-terminal.json'
    save_json(terminal_path, terminal)
    if max(terminal_path.stat().st_size, terminal_path.stat().st_blocks * 512) > terminal_reserve:
        # Cannot retract an exclusive receipt: emit a second fail-closed record.
        passed = False
        save_json(output / 'supervisor-terminal-storage-failure.json',
                  {'status': 'CLOSED_FAILED', 'failure': 'terminal_storage_reservation_exceeded'})
    print(json.dumps(terminal if passed else {**terminal, 'status': 'CLOSED_FAILED'}, sort_keys=True))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
