"""Create-only engineering archive; no array decoding or scientific rerun."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import resource
import signal
import stat
import time
import zipfile

ROOT = Path('/workspace/scratch/5bf3860dacd6')
PHASE = ROOT / 'analysis/s2017_injection_20261011'
PREFIX = PHASE.relative_to(ROOT).as_posix() + '/'
DEST = ROOT / 'deliverables/SETI_SIGNALTEST_RESULTS_2026-10-11.zip'
RECEIPT = DEST.parent / 'SIGNALTEST_ARCHIVE_QA.json'
GO_SHA256 = '12d8f23fbbe1a6e1ad2e2c03261e7b26cef0a30629ef36673297c6f38c090b12'
CPU_CAP_S = 300
WALL_CAP_S = 600
AS_CAP_BYTES = 512 * 1024 * 1024
WORKSPACE_CAP_BYTES = 8 * 1024 * 1024 * 1024
OUTPUT_CAP_BYTES = 500 * 1024 * 1024
BLOCK = 1024 * 1024
REQUIRED_GO_NAMES = {PREFIX + name for name in (
    'scope.json', 'qa_scope.json', 'results/review/QA_RECEIPT.json',
    'results/summary/SUMMARY.json', 'results/summary/SUMMARY_RECEIPT.json',
    'delivery/render_comparison_v2.py', 'delivery/COMPARISON_RENDER_RECEIPT_V2.json',
    'delivery/COMPARISON_DATA_V2.json', 'delivery/comparison_v2.png',
    'delivery/SETI_SIGNALTEST_2026-10-11.md', 'delivery/ALL30_GROUPS.json',
    'review/INJECTION_SAVED_OUTPUT_SCIENCE_REVIEW.json',
    'review/ROOT_VISUAL_REVIEW.json', 'review/SAVED_JSON_LOGICAL_AUDIT.json',
    'results/offcenter/EXECUTION_RECEIPT.json',
    'results/known_center_competitor/EXECUTION_RECEIPT.json')}


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def limit_signal(signum, frame):
    raise RuntimeError('Archive resource limit signal: ' + str(signum))


def install_limits():
    signal.signal(signal.SIGALRM, limit_signal)
    signal.signal(signal.SIGXCPU, limit_signal)
    signal.signal(signal.SIGXFSZ, limit_signal)
    signal.setitimer(signal.ITIMER_REAL, WALL_CAP_S)
    for kind, cap in ((resource.RLIMIT_CPU, CPU_CAP_S),
                      (resource.RLIMIT_AS, AS_CAP_BYTES),
                      (resource.RLIMIT_FSIZE, OUTPUT_CAP_BYTES)):
        soft, hard = resource.getrlimit(kind)
        hard = cap if hard == resource.RLIM_INFINITY else min(hard, cap)
        soft = hard if soft == resource.RLIM_INFINITY else min(soft, hard)
        resource.setrlimit(kind, (soft, hard))


def identity(s):
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)


def confined(name):
    require(isinstance(name, str), 'Source name must be text')
    parts = PurePosixPath(name)
    require(not parts.is_absolute() and name == parts.as_posix() and
            '..' not in parts.parts and parts.parts, 'Noncanonical source path: ' + name)
    path = ROOT / name
    for parent in path.parents:
        if parent == ROOT:
            break
        require(not stat.S_ISLNK(parent.lstat().st_mode), 'Symlink parent: ' + str(parent))
    require(stat.S_ISDIR(ROOT.lstat().st_mode), 'Workspace root must be a directory')
    return path


def regular_identity(path):
    s = path.lstat()
    require(stat.S_ISREG(s.st_mode), 'Not a regular nonsymlink file: ' + str(path))
    return identity(s)


def sha_stream(stream, expected_bytes):
    h = hashlib.sha256()
    remaining = expected_bytes
    while remaining:
        part = stream.read(min(BLOCK, remaining))
        require(bool(part), 'Truncated input while hashing')
        h.update(part)
        remaining -= len(part)
    require(stream.read(1) == b'', 'Input exceeds admitted byte length')
    return h.hexdigest()


def authenticate(name, expected=None):
    path = confined(name)
    before = regular_identity(path)
    require(before[2] <= OUTPUT_CAP_BYTES, 'Selected file exceeds output cap: ' + name)
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as handle:
        require(stat.S_ISREG(os.fstat(handle.fileno()).st_mode) and
                identity(os.fstat(handle.fileno())) == before, 'Source open identity changed: ' + name)
        digest = sha_stream(handle, before[2])
        require(identity(os.fstat(handle.fileno())) == before == regular_identity(path),
                'Source changed while hashing: ' + name)
    pin = {'bytes': before[2], 'sha256': digest}
    if expected is not None:
        require(pin == expected, 'Exact source pin mismatch: ' + name)
    return pin


def read_json(name, expected=None):
    pin = authenticate(name, expected)
    require(pin['bytes'] <= 32 * BLOCK, 'JSON metadata cap exceeded: ' + name)
    path = confined(name)
    before = regular_identity(path)
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as handle:
        require(identity(os.fstat(handle.fileno())) == before, 'Metadata identity changed at open')
        data = handle.read(pin['bytes'] + 1)
        require(len(data) == pin['bytes'] and hashlib.sha256(data).hexdigest() == pin['sha256'],
                'Metadata bytes changed: ' + name)
        require(identity(os.fstat(handle.fileno())) == before == regular_identity(path),
                'Metadata identity changed: ' + name)
    return json.loads(data.decode('utf-8')), pin


def workspace_bytes():
    total = 0
    seen = set()
    for current, dirs, files in os.walk(ROOT, followlinks=False):
        for path in [Path(current)] + [Path(current) / n for n in files] + [Path(current) / n for n in dirs]:
            s = path.lstat()
            key = (s.st_dev, s.st_ino)
            if key not in seen:
                seen.add(key)
                total += s.st_blocks * 512
        require(total <= WORKSPACE_CAP_BYTES, 'Workspace allocation exceeds 8 GiB')
    return total


def fsync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def held_identity(stream, fixed):
    require(stat.S_ISREG(os.fstat(stream.fileno()).st_mode) and
            identity(os.fstat(stream.fileno())) == fixed == regular_identity(DEST),
            'Archive descriptor/path identity changed')


class BudgetedFile:
    """Check every ZIP write before it can exceed the archive byte cap."""
    def __init__(self, stream):
        self.stream = stream

    def write(self, data):
        require(self.stream.tell() + len(data) <= OUTPUT_CAP_BYTES, 'Archive exceeds 500 MiB')
        return self.stream.write(data)

    def __getattr__(self, name):
        return getattr(self.stream, name)


def verify_archive(stream, records, manifest_raw, full_payload):
    stream.seek(0)
    with zipfile.ZipFile(stream) as archive:
        names = archive.namelist()
        require(len(names) == len(set(names)) == len(records) + 1 and
                set(names) == {r['path'] for r in records} | {'PACKAGE_MANIFEST.json'},
                'Archive member inventory mismatch')
        info = archive.getinfo('PACKAGE_MANIFEST.json')
        require(info.file_size == len(manifest_raw), 'Manifest size mismatch')
        require(archive.read(info) == manifest_raw, 'Manifest bytes/CRC mismatch')
        for row in records:
            info = archive.getinfo(row['path'])
            require(info.file_size == row['bytes'] and not info.is_dir() and
                    info.compress_type == zipfile.ZIP_DEFLATED, 'Member geometry mismatch: ' + row['path'])
            if full_payload:
                with archive.open(info) as payload:
                    require(sha_stream(payload, row['bytes']) == row['sha256'],
                            'Payload SHA/CRC mismatch: ' + row['path'])


def main():
    started = time.monotonic()
    install_limits()
    require(hasattr(os, 'O_NOFOLLOW'), 'POSIX no-follow support required')
    go_name = PREFIX + 'ROOT_FINAL_DELIVERY_GO.json'
    admission, go_pin = read_json(go_name)
    require(go_pin['sha256'] == GO_SHA256, 'Root GO immutable SHA mismatch')
    require(admission['schema'] == 'SETI_INJECTION_FINAL_DELIVERY_ROOT_ADMISSION_V1' and
            admission['status'] == 'GO_AFTER_ACTUAL_QA_SUMMARY_SCIENCE_AND_VISUAL_REVIEW', 'Root GO required')
    go_pins = admission['final_artifact_pins']
    require(set(go_pins) == REQUIRED_GO_NAMES, 'Root GO exact sixteen artifact contracts required')
    require(admission['archive_not_yet_executed'] is True and
            set(admission['actual_job_terminal_exits']) ==
            {'offcenter', 'known_center_competitor', 'independent_QA', 'summary'} and
            all(value == 0 for value in admission['actual_job_terminal_exits'].values()),
            'Actual terminal-zero jobs required')
    for name, pin in go_pins.items():
        authenticate(name, pin)
    qa_name = PREFIX + 'results/review/QA_RECEIPT.json'
    qa, _ = read_json(qa_name, go_pins[qa_name])
    require(qa['status'] == 'PASS450_MAPS540_DIAGNOSTICS_RAW_ARITHMETIC_AND_ROUNDED_SUPPORT_NO_DETECTOR_RERUN' and
            qa['counts']['maps'] == 450 and qa['counts']['diagnostics'] == 540, 'Actual independent QA required')
    scope_name = PREFIX + 'scope.json'
    scope, _ = read_json(scope_name, go_pins[scope_name])
    qa_scope_name = PREFIX + 'qa_scope.json'
    qa_scope, _ = read_json(qa_scope_name, go_pins[qa_scope_name])
    require(qa_scope['benchmark_scope_path'] == scope_name and
            qa_scope['benchmark_scope_sha256'] == go_pins[scope_name]['sha256'], 'QA scope binding mismatch')
    summary_receipt_name = PREFIX + 'results/summary/SUMMARY_RECEIPT.json'
    summary_receipt, _ = read_json(summary_receipt_name, go_pins[summary_receipt_name])
    require(summary_receipt['status'] == 'COMPLETE_CREATE_ONLY_ALL_GROUP_SUMMARY' and
            summary_receipt['output_pin'] == go_pins[PREFIX + 'results/summary/SUMMARY.json'],
            'Summary producer/output binding mismatch')
    renderer_name = PREFIX + 'delivery/render_comparison_v2.py'
    producer_name = PREFIX + 'delivery/COMPARISON_RENDER_RECEIPT_V2.json'
    producer, _ = read_json(producer_name, go_pins[producer_name])
    require(producer['schema'] == 'SETI_INJECTION_SAVED_SUMMARY_STATIC_FIGURE_RECEIPT_V1' and
            producer['status'] == 'COMPLETE_ALL30_PREDECLARED_GROUPS_STATIC_PNG' and
            producer['renderer_sha256'] == go_pins[renderer_name]['sha256'] and
            producer['presentation_revision'] == 'V2_header_legend_clearance_only_same_summary_and_metric' and
            producer['H5_NPZ_BIN_opened'] is False and producer['detector_or_score_rerun'] is False and
            producer['new_HTTP_requests'] == 0 and producer['all30_groups_present'] is True and
            producer['numeric_source_is_previously_QA_admitted_saved_summary'] is True,
            'Exact saved-summary V2 figure producer required')
    require(set(producer['output_pins']) == {'comparison_v2.png', 'COMPARISON_DATA_V2.json'},
            'Exact V2 producer output inventory required')
    for name, pin in producer['output_pins'].items():
        require(pin == go_pins[PREFIX + 'delivery/' + name], 'V2 producer output/root GO mismatch')
    for name in (renderer_name, scope_name, qa_name, summary_receipt_name,
                 PREFIX + 'results/summary/SUMMARY.json',
                 PREFIX + 'results/offcenter/EXECUTION_RECEIPT.json',
                 PREFIX + 'results/known_center_competitor/EXECUTION_RECEIPT.json'):
        require(producer['input_byte_pins'].get(name) == go_pins[name], 'V2 producer input/root GO mismatch: ' + name)
    bindings = dict(go_pins)
    bindings[go_name] = go_pin
    # The six original compact bodies are external RAW-package references, not
    # selected payloads. Preserve their actual QA pins without reopening HDF5.
    raw_reference_pins = {name: pin for name, pin in qa['input_byte_pins'].items()
                          if name.endswith('.compact.h5')}
    require(len(raw_reference_pins) == 6, 'Six original RAW compact references required')
    for source in (qa['input_byte_pins'], summary_receipt['input_byte_pins'], producer['input_byte_pins']):
        for name, pin in source.items():
            if name in bindings:
                require(bindings[name] == pin, 'Conflicting input contracts: ' + name)
            bindings[name] = pin
            if name not in raw_reference_pins:
                authenticate(name, pin)
    for name, digest in scope['text_code_pins'].items():
        require(authenticate(name)['sha256'] == digest, 'Original code/scope source changed: ' + name)
    paths = {p for p in PHASE.rglob('*') if p.is_file() and '__pycache__' not in p.parts
             and p.suffix in ('.py', '.json', '.md', '.png', '.npz', '.txt', '.log')}
    paths.update(confined(name) for name in scope['text_code_pins'])
    paths.update((ROOT / 'analysis/runtime/wheels').glob('*.whl'))
    paths.add(ROOT / 'analysis/runtime/restore_exact_dependencies.py')
    paths.update(confined(name) for name in go_pins)
    records = []
    for path in sorted(paths):
        require(path.is_relative_to(ROOT), 'Payload outside workspace')
        name = path.relative_to(ROOT).as_posix()
        pin = authenticate(name, bindings.get(name))
        if path.suffix == '.npz':
            require(name in qa['input_byte_pins'], 'Scientific payload lacks actual QA byte pin: ' + name)
        records.append({'path': name, **pin})
    require(REQUIRED_GO_NAMES <= {row['path'] for row in records}, 'Root GO payload missing')
    manifest = {'schema': 'SETI_SIGNALTEST_RESULTS_ARCHIVE_V1', 'members': records,
                'benchmark_public_freeze': qa['public_freeze_commit'],
                'qa_public_freeze': qa['qa_public_freeze_commit'],
                'root_final_delivery_GO_pin': go_pin,
                'V2_figure_producer_pin': go_pins[producer_name],
                'external_RAW_compact_QA_reference_pins_not_reopened': raw_reference_pins,
                'raw_source_archive_required': {'name': 'SETI_S2017_NATIVE171_RAW_2026-10-10.zip',
                 'bytes': 466351822, 'sha256': '6e08922aec5c5a6737987887cd62aab6d52495650297cae74745a654728f4786'},
                'original_six_compacts_in_this_archive': False, 'cost_DKK': 0}
    manifest_raw = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode('utf-8')
    DEST.parent.mkdir(parents=True, exist_ok=True)
    require(not DEST.exists() and not DEST.is_symlink() and
            not RECEIPT.exists() and not RECEIPT.is_symlink(), 'Archive/receipt create-only namespace already occupied')
    raw_bytes = sum(row['bytes'] for row in records) + len(manifest_raw)
    conservative_archive_bound = raw_bytes + (raw_bytes + 99) // 100 + 4 * BLOCK + 1024 * (len(records) + 1)
    require(conservative_archive_bound <= OUTPUT_CAP_BYTES, 'Conservative archive size exceeds 500 MiB')
    workspace_before = workspace_bytes()
    available = os.statvfs(DEST.parent)
    free_bytes_before = available.f_bavail * available.f_frsize
    required_space = conservative_archive_bound + BLOCK
    require(workspace_before + required_space <= WORKSPACE_CAP_BYTES, 'Conservative workspace admission exceeds 8 GiB')
    require(free_bytes_before >= required_space, 'Insufficient available filesystem space for archive plus receipt')
    fd = os.open(DEST, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'w+b') as stream:
        with zipfile.ZipFile(BudgetedFile(stream), 'w', zipfile.ZIP_DEFLATED,
                             compresslevel=6, allowZip64=True) as archive:
            for index, row in enumerate(records):
                archive.write(confined(row['path']), row['path'])
                stream.flush()
                require(os.fstat(stream.fileno()).st_size <= OUTPUT_CAP_BYTES, 'Actual archive cap exceeded')
                if index % 64 == 0:
                    workspace_bytes()
            archive.writestr('PACKAGE_MANIFEST.json', manifest_raw)
        stream.flush()
        os.fsync(stream.fileno())
        fixed = identity(os.fstat(stream.fileno()))
        require(fixed[2] <= OUTPUT_CAP_BYTES, 'Final archive exceeds 500 MiB')
        held_identity(stream, fixed)
        verify_archive(stream, records, manifest_raw, full_payload=True)
        stream.seek(0)
        archive_sha = sha_stream(stream, fixed[2])
        held_identity(stream, fixed)
        fresh_fd = os.open(DEST, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fresh_fd, 'rb') as fresh:
            require(stat.S_ISREG(os.fstat(fresh.fileno()).st_mode) and
                    identity(os.fstat(fresh.fileno())) == fixed == regular_identity(DEST),
                    'Fresh pathname open identity mismatch')
            require(sha_stream(fresh, fixed[2]) == archive_sha, 'Fresh pathname archive SHA mismatch')
            verify_archive(fresh, records, manifest_raw, full_payload=False)
            require(identity(os.fstat(fresh.fileno())) == fixed, 'Fresh descriptor changed during checks')
        held_identity(stream, fixed)
        # Opaque byte reads only: reauthenticate every selected source after packaging.
        for row in records:
            authenticate(row['path'], {'bytes': row['bytes'], 'sha256': row['sha256']})
        for name, pin in bindings.items():
            if name not in raw_reference_pins:
                authenticate(name, pin)
        workspace_final = workspace_bytes()
        held_identity(stream, fixed)
        elapsed = time.monotonic() - started
        require(elapsed <= WALL_CAP_S and time.process_time() <= CPU_CAP_S, 'Measured resource cap exceeded')
        result = {'schema': 'SETI_SIGNALTEST_ARCHIVE_QA_V1',
                  'status': 'PASS_ALL_PAYLOAD_CRC_SHA_AND_FRESH_PATH_IDENTITY',
                  'archive_path': str(DEST), 'archive_bytes': fixed[2], 'archive_sha256': archive_sha,
                  'payload_members': len(records), 'total_members': len(records) + 1,
                  'manifest_sha256': hashlib.sha256(manifest_raw).hexdigest(),
                  'builder_sha256': next(row['sha256'] for row in records
                                         if row['path'] == PREFIX + 'delivery/build_archive.py'),
                  'root_final_delivery_GO_pin': go_pin,
                  'V2_figure_producer_pin': go_pins[producer_name],
                  'V2_figure_output_pins': producer['output_pins'],
                  'scope_pin': go_pins[scope_name], 'qa_scope_pin': go_pins[qa_scope_name],
                  'all_selected_source_bytes_reauthenticated_after_packaging': True,
                  'writer_descriptor_retained_through_QA_receipt_close': True,
                  'fresh_path_O_NOFOLLOW_full_SHA': True,
                  'CPU_cap_s': CPU_CAP_S, 'wall_cap_s': WALL_CAP_S,
                  'address_space_cap_bytes': AS_CAP_BYTES, 'workspace_cap_bytes': WORKSPACE_CAP_BYTES,
                  'archive_output_cap_bytes': OUTPUT_CAP_BYTES,
                  'conservative_archive_bound_bytes': conservative_archive_bound,
                  'available_space_admission_bytes': free_bytes_before,
                  'workspace_allocated_bytes_before': workspace_before,
                  'workspace_allocated_bytes_before_receipt': workspace_final,
                  'process_CPU_seconds': time.process_time(), 'wall_seconds': elapsed,
                  'wall_measurement': 'main entry through pre-receipt checks; SIGALRM active through receipt close and directory fsync',
                  'new_telescope_HTTP_requests': 0, 'detector_or_score_rerun': False, 'cost_DKK': 0}
        receipt_bytes = (json.dumps(result, indent=2, sort_keys=True) + '\n').encode('utf-8')
        require(len(receipt_bytes) <= BLOCK, 'QA receipt reserve exceeded')
        receipt_fd = os.open(RECEIPT, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(receipt_fd, 'wb') as handle:
            require(handle.write(receipt_bytes) == len(receipt_bytes), 'Incomplete QA receipt write')
            handle.flush()
            os.fsync(handle.fileno())
        fsync_directory(DEST.parent)
        held_identity(stream, fixed)
        workspace_bytes()
        require(time.monotonic() - started <= WALL_CAP_S and time.process_time() <= CPU_CAP_S,
                'Final resource cap exceeded')
    signal.setitimer(signal.ITIMER_REAL, 0)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
