"""BT: retain active evidence in tmpfs and export only a closed verified ZIP.

This changes output handling, not frozen BQ/BR computations. The fixture uses
artificial BS records. A04 uses only the original pinned saved score arrays.
An archive is a byte-preservation mechanism; independent semantic review is
still required before any A04 qualification. No old status is overwritten.
"""
from __future__ import annotations

import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import resource
import stat
import sys
import time
import traceback
import zipfile

REPO = Path(__file__).resolve().parents[1]
PRODUCTION_ISOLATION = Path('/dev/shm/seti_bt_20261031_v1')
MAX_MEMBER_BYTES = 256 * 1024 * 1024
MAX_PAYLOAD_BYTES = 512 * 1024 * 1024
MAX_MEMBERS = 100
CHUNK = 1024 * 1024
MANIFEST_NAME = 'ARCHIVE_MANIFEST.json'
MANIFEST_SCHEMA = 'SETI_BT_ARCHIVE_MANIFEST_V1'
FIXED_SOURCE_PINS = {
    'work_bs/diagnostic.py': '2192d2a9da560e5a4969f7a404849b9db6f63c5db107321ffd941c11dd4ea608',
    'work_br/closed_association.py': '92ec652a82b52a931abb5a4aff3b42ac7e22638cc5e155ddcdb2437e37d5dc1b',
    'work_br/stream_closure.py': '8b3e3887b1b548e06d28cab4fcba127815c047f28b5c6cd72164472c99ced814',
    'work_br/BR_POSTPROCESSING_PLAN.json': '31d2dfa160aebf513adcdff2f4cd20ae05e0188a0cbbfa1d78c62809ded94923',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode('utf-8')


def identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def safe_name(name):
    require(isinstance(name, str) and name and '\\' not in name and '\x00' not in name,
            'Unsafe archive member name')
    path = PurePosixPath(name)
    require(not path.is_absolute() and all(part not in ('', '.', '..') for part in name.split('/'))
            and str(path) == name, 'Archive member must be a normalized relative path')
    return name


def stable_file(path):
    path = Path(path)
    before = path.stat(follow_symlinks=False)
    require(stat.S_ISREG(before.st_mode), 'Evidence member is not a regular file')
    require(path.absolute() == path.resolve(strict=True), 'Evidence path contains a symlink')
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        closed = os.fstat(stream.fileno())
    after = path.stat(follow_symlinks=False)
    require(identity(before) == identity(opened) == identity(closed) == identity(after),
            'Evidence changed while its bytes were hashed')
    return {'bytes': after.st_size, 'sha256': digest}


def save_json(path, value):
    raw = canonical(value)
    with Path(path).open('xb') as stream:
        require(stream.write(raw) == len(raw), 'Short JSON evidence write')
        stream.flush()
        os.fsync(stream.fileno())
    actual = stable_file(path)
    require(actual == {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()},
            'JSON evidence changed after close')
    return actual


def verify_pins(pins):
    checked = []
    seen = set()
    for pin in pins:
        relative = safe_name(pin['path'])
        require(relative not in seen, 'Duplicate bound input/source path')
        seen.add(relative)
        path = REPO / relative
        actual = stable_file(path)
        require(actual['sha256'] == pin['sha256'] and actual['bytes'] == pin['bytes'],
                'Pinned source/input differs: ' + relative)
        checked.append({'path': relative, **actual})
    return checked


def source_and_input_pins(kind):
    fixed = []
    for name, digest in FIXED_SOURCE_PINS.items():
        actual = stable_file(REPO/name)
        require(actual['sha256'] == digest, 'Fixed source differs: ' + name)
        fixed.append({'path': name, **actual})
    plan = json.loads((REPO/'work_br/BR_POSTPROCESSING_PLAN.json').read_text())
    require(plan['schema'] == 'SETI_BR_CLOSED_A04_POSTPROCESSING_V1', 'Wrong frozen BR plan')
    require(not plan['RNG_authorized'] and not plan['new_scan_scores_authorized']
            and not plan['astronomical_powers_authorized'], 'Frozen plan scope differs')
    sources = {pin['path']: pin for pin in fixed}
    for pin in plan['source_pins']:
        if pin['path'] in sources:
            require(pin == sources[pin['path']], 'Conflicting source pins')
        sources[pin['path']] = pin
    return plan, [sources[name] for name in sorted(sources)], list(plan['input_pins']) if kind == 'a04' else []


def load_module(name, relative):
    spec = importlib.util.spec_from_file_location(name, REPO/relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def tmpfs_magic(path):
    """Linux statfs f_type is the first native long in struct statfs."""
    libc = ctypes.CDLL(None, use_errno=True)
    function = libc.statfs
    function.argtypes = [ctypes.c_char_p, ctypes.c_void_p]
    function.restype = ctypes.c_int
    buffer = ctypes.create_string_buffer(256)
    if function(os.fsencode(path), ctypes.byref(buffer)) != 0:
        raise OSError(ctypes.get_errno(), 'statfs failed')
    return ctypes.c_long.from_buffer(buffer).value


def prepare_isolation(path):
    path = Path(path)
    require(path.is_absolute() and path.parent != Path('/dev/shm'), 'Use an exclusive directory beneath a tmpfs task root')
    require(Path('/dev/shm') in path.parents, 'Isolation must be beneath /dev/shm')
    path.parent.mkdir(mode=0o700, parents=False, exist_ok=True)
    require(path.parent == path.parent.resolve(strict=True), 'Isolation parent contains a symlink')
    require(path.parent.stat().st_uid == os.getuid(), 'Isolation root must be owned by this user')
    require(stat.S_IMODE(path.parent.stat().st_mode) & 0o077 == 0, 'Isolation root must be private')
    require(tmpfs_magic(path.parent) == 0x01021994, 'Isolation filesystem is not tmpfs')
    capacity = os.statvfs(path.parent)
    available = capacity.f_bavail * capacity.f_frsize
    required = 2 * MAX_PAYLOAD_BYTES
    require(available >= required, 'Insufficient tmpfs capacity for bounded payload plus closed archive')
    path.mkdir(mode=0o700, exist_ok=False)
    return {'path': str(path), 'filesystem_type_hex': '0x01021994',
            'device': path.stat().st_dev, 'owner_uid': os.getuid(), 'exclusive': True,
            'available_bytes_before_reservation': available, 'required_available_bytes': required}


def validate_manifest(members):
    require(isinstance(members, list) and 0 < len(members) <= MAX_MEMBERS, 'Invalid manifest member count')
    names = []
    for member in members:
        require(isinstance(member, dict) and set(member) == {'path', 'bytes', 'sha256'}, 'Invalid member receipt')
        name = safe_name(member['path'])
        require(name != MANIFEST_NAME, 'Reserved manifest path cannot be a payload member')
        require(isinstance(member['bytes'], int) and not isinstance(member['bytes'], bool)
                and 0 <= member['bytes'] <= MAX_MEMBER_BYTES, 'Member size exceeds fixed cap')
        require(isinstance(member['sha256'], str) and re.fullmatch('[0-9a-f]{64}', member['sha256']), 'Invalid member SHA256')
        names.append(name)
    require(len(names) == len(set(names)), 'Duplicate manifest path')
    require(names == sorted(names), 'Manifest paths must be sorted')
    require(sum(member['bytes'] for member in members) <= MAX_PAYLOAD_BYTES, 'Payload exceeds fixed cap')
    return names


def verify_archive(path, members):
    """Full member CRC/hash/byte validation with strict safe membership.

    No archive bytes are extracted to disk. The ZIP contains exactly the
    manifest-listed regular files plus the canonical manifest itself.
    """
    names = validate_manifest(members)
    path = Path(path)
    before = path.stat(follow_symlinks=False)
    require(stat.S_ISREG(before.st_mode) and not path.is_symlink(), 'Archive must be a regular nonsymlink file')
    require(before.st_size <= MAX_PAYLOAD_BYTES, 'Archive exceeds fixed cap')
    expected_manifest = canonical({'schema': MANIFEST_SCHEMA, 'members': members})
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        with zipfile.ZipFile(stream, 'r') as archive:
            entries = archive.infolist()
            observed = [safe_name(info.filename) for info in entries]
            require(len(observed) == len(set(observed)), 'Duplicate ZIP member')
            require(set(observed) == set(names) | {MANIFEST_NAME}, 'ZIP membership differs from manifest')
            for info in entries:
                require(info.orig_filename == info.filename, 'Ambiguous ZIP member filename')
                mode = (info.external_attr >> 16) & 0xFFFF
                require(not info.is_dir() and stat.S_IFMT(mode) in (0, stat.S_IFREG), 'Nonregular ZIP member')
                require(not info.flag_bits & 1, 'Encrypted ZIP member forbidden')
                require(info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED), 'Unexpected ZIP compression')
            manifest_info = archive.getinfo(MANIFEST_NAME)
            require(manifest_info.file_size == len(expected_manifest), 'Embedded manifest size differs')
            require(archive.read(MANIFEST_NAME) == expected_manifest, 'Embedded manifest bytes differ')
            verified = []
            for member in members:
                info = archive.getinfo(member['path'])
                require(info.file_size == member['bytes'], 'ZIP member declared size differs')
                digest, count = hashlib.sha256(), 0
                with archive.open(info, 'r') as source:
                    while True:
                        chunk = source.read(CHUNK)
                        if not chunk:
                            break
                        count += len(chunk)
                        require(count <= member['bytes'], 'Expanded member exceeds receipt')
                        digest.update(chunk)
                actual = {'path': member['path'], 'bytes': count, 'sha256': digest.hexdigest()}
                require(actual == member, 'ZIP member bytes or SHA256 differ')
                verified.append(actual)
        stream.seek(0)
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        closed = os.fstat(stream.fileno())
    after = path.stat(follow_symlinks=False)
    require(identity(before) == identity(opened) == identity(closed) == identity(after), 'Archive changed during validation')
    return {'status': 'PASS', 'bytes': after.st_size, 'sha256': digest, 'members': verified,
            'manifest_schema': MANIFEST_SCHEMA, 'all_member_CRCs_verified': True}


def create_archive(contents, archive_path):
    contents, archive_path = Path(contents), Path(archive_path)
    members = []
    for path in sorted(contents.rglob('*')):
        require(not path.is_symlink(), 'Symlink in isolated evidence tree')
        if path.is_dir():
            continue
        members.append({'path': safe_name(path.relative_to(contents).as_posix()), **stable_file(path)})
    validate_manifest(members)
    with zipfile.ZipFile(archive_path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=1, allowZip64=False) as archive:
        for member in members:
            archive.write(contents/member['path'], arcname=member['path'])
        archive.writestr(MANIFEST_NAME, canonical({'schema': MANIFEST_SCHEMA, 'members': members}))
    with archive_path.open('rb') as stream:
        os.fsync(stream.fileno())
    receipt = verify_archive(archive_path, members)
    for member in members:
        require(stable_file(contents/member['path']) == {k: member[k] for k in ('bytes', 'sha256')},
                'Isolated source changed after archive creation')
    return receipt


def export_archive(source, destination, receipt):
    with Path(source).open('rb') as reader, Path(destination).open('xb') as writer:
        while True:
            chunk = reader.read(CHUNK)
            if not chunk:
                break
            require(writer.write(chunk) == len(chunk), 'Short closed-archive export write')
        writer.flush()
        os.fsync(writer.fileno())
    exported = verify_archive(destination, receipt['members'])
    require(exported == receipt, 'Exported archive differs from verified isolated archive')
    return exported


def preserved_statuses():
    return {'BP': 'FAIL_23_PASS_1_RSS_FAILURE',
            'BQ': 'EVIDENCE_FAIL_6449_CURRENT_RECORDS_MISSING',
            'BR': 'FAIL_POSTCLOSE_MUTATION_10102_LEGACY_RECORDS_MISSING'}


def run_isolated(kind, output_dir, isolated_dir, fixture_records=45000):
    require(kind in ('fixture', 'a04'), 'Unknown isolated operation')
    require(isinstance(fixture_records, int) and not isinstance(fixture_records, bool)
            and 1 <= fixture_records <= 45000, 'Invalid bounded fixture count')
    require(kind == 'fixture' or fixture_records == 45000, 'Fixture count does not apply to A04')
    output, isolated = Path(output_dir), Path(isolated_dir)
    require(output.is_absolute() and isolated.is_absolute(), 'Output paths must be absolute')
    require(output.parent == output.parent.resolve(strict=True), 'Output parent contains a symlink')
    output.mkdir(exist_ok=False)
    started = time.monotonic()
    result = {'schema': 'SETI_BT_ISOLATED_EXECUTION_V1', 'status': 'FAIL', 'kind': kind,
              'execution_identity': 'BT_TMPFS_' + kind.upper() + '_V1',
              'engineering_or_A04': 'ENGINEERING_FIXTURE' if kind == 'fixture' else 'SAVED_A04_ASSOCIATIONS',
              'original_statuses_preserved': preserved_statuses(), 'new_RNG_calls': 0,
              'new_scan_scores': 0, 'astronomical_powers_opened': 0,
              'isolation_directory': str(isolated), 'archive': None, 'errors': [],
              'source_pins_verified_before': False, 'source_pins_verified_after': False,
              'input_pins_verified_before': False, 'input_pins_verified_after': False,
              'caps': {'max_payload_bytes': MAX_PAYLOAD_BYTES, 'max_member_bytes': MAX_MEMBER_BYTES,
                       'max_members': MAX_MEMBERS, 'max_fixture_records_per_stream': 45000},
              'qualification': 'New execution identity. Original failures remain failed; independent semantic review still required.'}
    contents = isolated/'contents'
    sources, inputs = [], []
    computation_passed = False
    isolation_owned = False
    try:
        result['isolation'] = prepare_isolation(isolated)
        isolation_owned = True
        plan, sources, inputs = source_and_input_pins(kind)
        result['source_pins_before'] = verify_pins(sources)
        result['source_pins_verified_before'] = True
        result['input_pins_before'] = verify_pins(inputs)
        result['input_pins_verified_before'] = True
        if kind == 'fixture':
            diagnostic = load_module('bt_frozen_bs_diagnostic', 'work_bs/diagnostic.py')
            assessment = diagnostic.run_fixture('br', contents, fixture_records, 0, emit=False)
            result['fixture_records_per_stream'] = fixture_records
            computation_passed = assessment['status'] == 'PASS'
            result['assessment_status'] = assessment['status']
        else:
            frozen = load_module('bt_frozen_br_closed_association', 'work_br/closed_association.py')
            bound = [dict(path=str(REPO/pin['path']), bytes=pin['bytes'], sha256=pin['sha256'])
                     for pin in plan['input_pins']+plan['source_pins']]
            assessment = frozen.run_closed_assessment([REPO/path for path in plan['scan_dirs']],
                         plan['case'], contents, [REPO/path for path in plan['base_scan_dirs']], bound)
            save_json(contents/'ASSESSMENT.json', assessment)
            closure = frozen.closure.evaluate_closure(contents, assessment, 'child_end',
                                                       previous_check=assessment['child_stream_closure'])
            save_json(contents/'BT_CLOSURE_CHECK.json', closure)
            result['assessment_status'] = assessment['status']
            result['isolated_end_closure_status'] = closure['effective_status']
            result['same_process_closure_only'] = True
            computation_passed = assessment['status'] == 'PASS' and closure['effective_status'] == 'PASS'
        require(computation_passed, 'Frozen computation or isolated closure failed')
    except BaseException as exc:
        result['errors'].append({'phase': 'computation', 'exception': type(exc).__name__ + ': ' + str(exc),
                                 'traceback': traceback.format_exc()})
    # Verify all inputs even after a computation failure. No retry of the
    # computation occurs. Failed bytes can still receive a faithful archive.
    try:
        require(result['source_pins_verified_before'], 'No complete initial source-pin verification')
        result['source_pins_after'] = verify_pins(sources)
        result['source_pins_verified_after'] = result['source_pins_after'] == result['source_pins_before']
        result['input_pins_after'] = verify_pins(inputs)
        result['input_pins_verified_after'] = result['input_pins_after'] == result['input_pins_before']
        require(result['source_pins_verified_after'] and result['input_pins_verified_after'], 'Pins changed during isolated computation')
    except BaseException as exc:
        result['errors'].append({'phase': 'pins_after', 'exception': type(exc).__name__ + ': ' + str(exc),
                                 'traceback': traceback.format_exc()})
    try:
        require(isolation_owned and contents.is_dir(), 'No newly owned isolated content directory to archive')
        save_json(contents/'BT_SOURCE_INPUT_BINDINGS.json', {
            key: result.get(key) for key in ('source_pins_before', 'source_pins_after', 'input_pins_before', 'input_pins_after',
                'source_pins_verified_before', 'source_pins_verified_after', 'input_pins_verified_before', 'input_pins_verified_after')})
        if result['errors']:
            save_json(contents/'BT_FAILURE.json', {'status': 'FAIL', 'errors': result['errors'],
                       'original_statuses_preserved': preserved_statuses(), 'no_retry': True})
        receipt = create_archive(contents, isolated/'evidence.zip')
        exported = export_archive(isolated/'evidence.zip', output/'EVIDENCE.zip', receipt)
        result['archive'] = {'path': 'EVIDENCE.zip', **{key: exported[key] for key in ('bytes', 'sha256', 'members')}}
        result['isolated_archive_verification'] = receipt
        result['exported_archive_verification'] = exported
    except BaseException as exc:
        result['errors'].append({'phase': 'archive_or_export', 'exception': type(exc).__name__ + ': ' + str(exc),
                                 'traceback': traceback.format_exc()})
    try:
        require(result['source_pins_verified_before'], 'Initial pins were not verified')
        result['final_source_pins_after_export'] = verify_pins(sources)
        result['final_input_pins_after_export'] = verify_pins(inputs)
        require(result['final_source_pins_after_export'] == result['source_pins_before']
                and result['final_input_pins_after_export'] == result['input_pins_before'],
                'Source/input pins differ at final export fence')
        result['final_pins_verified_after_export'] = True
    except BaseException as exc:
        result['final_pins_verified_after_export'] = False
        result['errors'].append({'phase': 'final_pins_after_export', 'exception': type(exc).__name__ + ': ' + str(exc),
                                 'traceback': traceback.format_exc()})
    if computation_passed and not result['errors'] and result['archive']:
        result['status'] = 'PASS'
    result['isolated_files_retained'] = isolation_owned and isolated.exists()
    result['wall_seconds'] = time.monotonic()-started
    result['max_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    result['resource_limits'] = {name: list(resource.getrlimit(getattr(resource, name)))
                               for name in ('RLIMIT_CPU', 'RLIMIT_AS', 'RLIMIT_FSIZE')}
    save_json(output/'RESULT.json', result)
    return result


def tighten_limit(which, desired):
    soft, hard = resource.getrlimit(which)
    hard = desired if hard == resource.RLIM_INFINITY else min(desired, hard)
    soft = hard if soft == resource.RLIM_INFINITY else min(soft, hard)
    resource.setrlimit(which, (soft, hard))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--kind', choices=('fixture', 'a04'), required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--isolated-dir', type=Path, required=True)
    args = parser.parse_args()
    require(args.isolated_dir == PRODUCTION_ISOLATION/args.kind, 'Production isolation identity differs')
    tighten_limit(resource.RLIMIT_CPU, 180)
    tighten_limit(resource.RLIMIT_AS, 1024*1024*1024)
    tighten_limit(resource.RLIMIT_FSIZE, MAX_PAYLOAD_BYTES)
    result = run_isolated(args.kind, args.output_dir, args.isolated_dir)
    print(json.dumps({'event': 'GATE_TERMINAL_EOF', 'status': result['status'],
                      'result_sha256': sha(args.output_dir/'RESULT.json')}), flush=True)
    return 0 if result['status'] == 'PASS' else 2


if __name__ == '__main__':
    sys.exit(main())
