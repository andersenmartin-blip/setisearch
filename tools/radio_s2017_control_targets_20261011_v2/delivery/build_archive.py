"""Create-only byte archive of closed control-target results, after root GO.

Standard library only: scientific NPZs are streamed as opaque bytes; HDF5
sources, locks, caches and prior preparations are never archive members.
The original writer FD stays open through fresh-path SHA/member readback,
terminal receipt fsync and parent-directory fsync.
"""
from __future__ import annotations
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import resource
import signal
import stat
import sys
import time
import zipfile

BASE = 'analysis/s2017_control_targets_20261011_v2'
TARGETS = ('primary20170428_HIP97319', 'primary20170428_HIP97461', 'primary20170428_HIP97663')
ARCHIVE = 'deliverables/SETI_CONTROL_TARGET_RESULTS_2026-10-11.zip'
RECEIPT = 'deliverables/SETI_CONTROL_TARGET_RESULTS_2026-10-11_ARCHIVE_RECEIPT.json'
CPU, WALL, RAM, ARCHIVE_CAP, WORKSPACE = 300, 600, 512 * 1024**2, 500 * 1024**2, 8 * 1024**3
PRIMARY_COUNTS = {'maps': 753, 'carrier_maxima': 3084288, 'valid_hypothesis_records': 4842332160,
    'core_row_medians': 12048, 'score_audit_queries': 3021, 'raw_power_cells': 24313008,
    'independent_scores': 3021, 'source_decoded_rows': 48, 'source_compacts': 3,
    'top20_entries': 60, 'top3_entries': 9}
CONTEXT_COUNTS = {'selected_tracks': 9, 'fixed_profiles': 54, 'raw503_capsules': 54,
    'raw_power_cells': 434592, 'source_compacts': 6, 'source_decoded_rows': 96,
    'conditional_normalization_core_row_medians': 864, 'independent_fixed_scores': 54,
    'origin_primary_score_matches': 9}

def check(condition, message):
    if not condition:
        raise ValueError(message)

def pairs(items):
    result = {}
    for key, value in items:
        check(key not in result, 'Duplicate JSON field')
        result[key] = value
    return result

def parse_json(raw):
    return json.loads(raw, object_pairs_hook=pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))

def read_json(path):
    return parse_json(path.read_bytes())

def confined(root, name):
    relative = PurePosixPath(name)
    check(isinstance(name, str) and name and '\\' not in name and not relative.is_absolute()
          and '..' not in relative.parts and relative.as_posix() == name, 'Canonical relative path required')
    path = root / name
    check(path.resolve().is_relative_to(root), 'Path outside workspace')
    return path

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024**2), b''):
            h.update(chunk)
    return h.hexdigest()

def digest_stream(stream):
    stream.seek(0)
    h = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024**2), b''):
        h.update(chunk)
    return h.hexdigest()

def fresh_archive_reader(path, writer):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        original, opened, named = os.fstat(writer.fileno()), os.fstat(fd), path.lstat()
        check(stat.S_ISREG(opened.st_mode) and stat.S_ISREG(named.st_mode)
              and (original.st_dev, original.st_ino, original.st_size)
              == (opened.st_dev, opened.st_ino, opened.st_size)
              == (named.st_dev, named.st_ino, named.st_size),
              'Fresh nofollow regular pathname/reader no longer identifies original writer inode and size')
        return os.fdopen(fd, 'rb')
    except BaseException:
        os.close(fd)
        raise

def pin(root, path):
    return {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)}

def validate_pin(value):
    check(set(value) == {'path', 'bytes', 'sha256'} and type(value['bytes']) is int and value['bytes'] >= 0
          and re.fullmatch('[0-9a-f]{64}', value['sha256']), 'Exact byte pin schema differs')

def loaded_gate(root, value, expected_path):
    validate_pin(value)
    check(value['path'] == expected_path, 'Wrong actual gate path')
    path = confined(root, value['path'])
    check(path.suffix in ('.json', '.py'), 'Gate reads text only')
    raw = path.read_bytes()
    actual = {'path': value['path'], 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
    check(actual == value, 'Actual gate byte pin differs')
    return parse_json(raw) if path.suffix == '.json' else None

def allocated(root):
    seen, result = set(), 0
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in files:
            try:
                info = (Path(parent) / name).stat(follow_symlinks=False)
            except FileNotFoundError:
                continue
            key = (info.st_dev, info.st_ino)
            if key not in seen:
                seen.add(key)
                result += info.st_blocks * 512
    return result

def guard(root, stream=None, reserve=0):
    value = allocated(root)
    check(value + reserve <= WORKSPACE, '8GiB workspace bound exceeded')
    if stream is not None:
        check(os.fstat(stream.fileno()).st_size <= ARCHIVE_CAP, '500MiB archive bound exceeded')
    return value

def save_new(path, value):
    raw = (json.dumps(value, separators=(',', ':'), allow_nan=False) + '\n').encode()
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())

def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)

def admission(root, manifest):
    check(manifest['schema'] == 'SETI_S2017_CONTROL_RESULTS_MANIFEST_V1'
          and manifest['status'] == 'CLOSED_ROOT_SELECTED_BYTE_MANIFEST_AFTER_ALL_QA_PASS'
          and re.fullmatch('[0-9a-f]{40}', manifest['science_public_freeze_commit']), 'Closed root manifest required')
    gates = manifest['gates']
    required_gates = {'primary_receipts', 'primary_QA', 'context_execution', 'context_QA',
        'primary_scope', 'context_scope', 'primary_driver', 'context_driver', 'primary_QA_script',
        'context_QA_script', 'primary_QA_scope', 'context_QA_scope'}
    check(set(gates) == required_gates and set(gates['primary_receipts']) == set(TARGETS), 'Exact three completed primary gates required')
    values, authenticated = {}, {}
    paths = {'primary_QA': BASE + '/results/review/QA_RECEIPT.json',
        'context_execution': BASE + '/results/context/EXECUTION_RECEIPT.json',
        'context_QA': BASE + '/results/context_review/QA_RECEIPT.json',
        'primary_scope': BASE + '/scope.json', 'context_scope': BASE + '/context_scope.json',
        'primary_driver': BASE + '/driver.py', 'context_driver': BASE + '/context_profiles.py',
        'primary_QA_script': BASE + '/qa_saved.py', 'context_QA_script': BASE + '/qa_context.py',
        'primary_QA_scope': BASE + '/qa_scope.json', 'context_QA_scope': BASE + '/qa_context_scope.json'}
    for kind, name in paths.items():
        values[kind] = loaded_gate(root, gates[kind], name)
    qa, cq = values['primary_QA'], values['context_QA']
    check(qa['schema'] == 'SETI_S2017_CONTROL_TARGET_SAVED_INDEPENDENT_QA_V1'
          and qa['status'] == 'PASS753_ORIGINAL_OFF_MAPS3021_RAW_SCORE_QUERIES_NO_DETECTOR_RERUN'
          and qa['counts'] == PRIMARY_COUNTS, 'Actual753-map/3021-query independent QA PASS required')
    check(cq['schema'] == 'SETI_S2017_CONTROL_TARGET_FIXED_CONTEXT_INDEPENDENT_QA_V1'
          and cq['status'] == 'PASS54_FIXED_CONTEXT_RAW503_SCORES96_SOURCE_ROWS_NO_SEARCH'
          and cq['counts'] == CONTEXT_COUNTS, 'Actual54-profile context QA PASS required')
    check(qa['scope_sha256'] == qa['primary_scope_sha256'] == gates['primary_scope']['sha256']
          and qa['qa_sha256'] == gates['primary_QA_script']['sha256']
          and qa['qa_scope_sha256'] == gates['primary_QA_scope']['sha256']
          and cq['context_scope_sha256'] == gates['context_scope']['sha256']
          and cq['qa_sha256'] == gates['context_QA_script']['sha256']
          and cq['qa_scope_sha256'] == gates['context_QA_scope']['sha256']
          and cq['primary_qa_receipt_sha256'] == gates['primary_QA']['sha256'], 'QA scope/code/receipt provenance differs')
    check(qa['public_freeze_commit'] == cq['public_freeze_commit'] == manifest['science_public_freeze_commit'], 'Science public freeze differs')
    for record in (qa, cq):
        for name, value in record['input_byte_pins'].items():
            current = {'path': name, **value}
            validate_pin(current)
            check(name not in authenticated or authenticated[name] == current, 'QA input pins conflict')
            authenticated[name] = current
    primary_hashes = {target: gates['primary_receipts'][target]['sha256'] for target in TARGETS}
    check(qa['primary_receipt_sha256s'] == primary_hashes, 'Primary QA binds different completed receipts')
    for target in TARGETS:
        receipt = loaded_gate(root, gates['primary_receipts'][target], BASE + '/results/' + target + '/EXECUTION_RECEIPT.json')
        check(receipt['schema'] == 'SETI_S2017_CONTROL_PRIMARY_TARGET_EXECUTION_V1'
              and receipt['status'] == 'COMPLETE_251_NEW_ORIGINAL_OFF_PRIMARY_TARGET_MAPS_EXPLORATORY_ONLY'
              and receipt['primary_id'] == target and receipt['original_acquisition_role'] == 'OFF'
              and receipt['counts']['maps'] == 251 and receipt['counts']['score_audit_queries'] == 1007
              and receipt['scope_sha256'] == gates['primary_scope']['sha256']
              and receipt['driver_sha256'] == gates['primary_driver']['sha256']
              and receipt['public_freeze_commit'] == manifest['science_public_freeze_commit'], 'Actual distinct primary completion differs')
        for member in receipt['output_byte_pins']:
            validate_pin(member)
            check(authenticated.get(member['path']) == member, 'Primary output differs from actual QA authenticated bytes')
    context = values['context_execution']
    check(context['schema'] == 'SETI_S2017_CONTROL_TARGET_CONTEXT_EXECUTION_V1'
          and context['status'] == 'COMPLETE_NINE_FIXED_TRACKS54_SIX_SCAN_CONTEXT_PROFILES_NO_OPTIMIZATION'
          and context['counts'] == {'selected_tracks': 9, 'context_scores': 54, 'source_files': 6,
              'source_decoded_rows': 96, 'raw_source_capsule_cells': 434592, 'origin_score_matches': 9}
          and context['primary_receipt_sha256s'] == primary_hashes
          and context['primary_scope_sha256'] == gates['primary_scope']['sha256']
          and context['scope_sha256'] == gates['context_scope']['sha256']
          and context['context_driver_sha256'] == gates['context_driver']['sha256']
          and context['public_freeze_commit'] == manifest['science_public_freeze_commit']
          and cq['context_receipt_sha256'] == gates['context_execution']['sha256'], 'Actual fixed context completion differs')
    for name, value in context['output_pins'].items():
        member = {'path': BASE + '/results/context/' + name, **value}
        validate_pin(member)
        check(authenticated.get(member['path']) == member, 'Context output differs from actual QA authenticated bytes')
    members, names, sources = manifest['members'], set(), set()
    check(isinstance(members, list) and members, 'Explicit final member list required')
    for member in members:
        check(set(member) == {'source_path', 'archive_path', 'bytes', 'sha256'}, 'Member schema differs')
        source = confined(root, member['source_path'])
        archive_name = member['archive_path']
        confined(root, archive_name)
        check(archive_name != 'MANIFEST.json' and archive_name not in names and member['source_path'] not in sources,
              'Duplicate or reserved archive identity')
        check(source.suffix.lower() in ('.json', '.py', '.md', '.txt', '.csv', '.log', '.png', '.npz')
              and not any(p in ('__pycache__', 'prior_preparation') for p in source.relative_to(root).parts),
              'H5/raw/cache/lock/prior-preparation members excluded')
        if source.suffix.lower() == '.npz':
            check(member['source_path'].startswith(BASE + '/results/'), 'Scientific NPZs must belong to this new phase')
        if source.suffix.lower() == '.png':
            final_report_png = BASE + '/delivery/SETI_CONTROL_TARGETS_2026-10-11.png'
            check(member['source_path'].startswith(BASE + '/results/')
                  or (member['source_path'] == final_report_png
                      and final_report_png in manifest['required_report_paths']),
                  'PNG must be a new-phase result or the exact root-selected final report figure')
        validate_pin({'path': member['source_path'], 'bytes': member['bytes'], 'sha256': member['sha256']})
        if source.suffix.lower() == '.npz':
            check(authenticated.get(member['source_path']) == {'path': member['source_path'], 'bytes': member['bytes'], 'sha256': member['sha256']},
                  'Every scientific NPZ must be authenticated by actual independent QA')
        names.add(archive_name)
        sources.add(member['source_path'])
    gate_paths = {v['path'] for k, v in gates.items() if k != 'primary_receipts'} | {v['path'] for v in gates['primary_receipts'].values()}
    check(gate_paths <= sources, 'All actual receipts/scopes/scripts must be packaged')
    for target in TARGETS:
        receipt = read_json(root / BASE / 'results' / target / 'EXECUTION_RECEIPT.json')
        check({p['path'] for p in receipt['output_byte_pins']} <= sources, 'Every closed primary output must be packaged')
    check({BASE + '/results/context/' + name for name in context['output_pins']} <= sources,
          'Every closed context output must be packaged')
    required_reports = manifest['required_report_paths']
    check(required_reports and set(required_reports) <= sources
          and any(n.endswith('.md') for n in required_reports) and any(n.endswith('.png') for n in required_reports),
          'Final report and reviewable PNG required')
    check(sum(m['bytes'] for m in members) <= ARCHIVE_CAP, 'Declared member payload exceeds archive bound')
    return sources

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--builder-sha256', required=True)
    parser.add_argument('--root-go', default=BASE + '/delivery/ARCHIVE_ROOT_GO.json')
    parser.add_argument('--root-go-sha256')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    root, started, cpu0 = args.root.resolve(), time.monotonic(), time.process_time()
    check(re.fullmatch('[0-9a-f]{64}', args.builder_sha256) and digest(Path(__file__).resolve()) == args.builder_sha256,
          'Exact reviewed archive builder required')
    path = confined(root, args.manifest)
    manifest_raw = path.read_bytes()
    check(path.suffix == '.json' and re.fullmatch('[0-9a-f]{64}', args.manifest_sha256)
          and hashlib.sha256(manifest_raw).hexdigest() == args.manifest_sha256, 'Exact root manifest required')
    manifest = parse_json(manifest_raw)
    sources = admission(root, manifest)
    if args.check_only:
        print(json.dumps({'status': 'PASS_CLOSED_METADATA_MANIFEST_GATES_NO_NPZ_SOURCE_OPEN_OR_ZIP', 'members': len(sources)}))
        return
    go_path = confined(root, args.root_go)
    go_raw = go_path.read_bytes()
    check(re.fullmatch('[0-9a-f]{64}', args.root_go_sha256 or '') and hashlib.sha256(go_raw).hexdigest() == args.root_go_sha256,
          'Exact root archive GO required')
    go = parse_json(go_raw)
    expected = {'status': 'GO_SERIALIZED_CLOSED_CONTROL_RESULTS_ARCHIVE', 'manifest_sha256': args.manifest_sha256,
        'builder_sha256': args.builder_sha256, 'all_filesystem_actors_paused': True,
        'CPU_cap_s': CPU, 'wall_cap_s': WALL, 'memory_cap_bytes': RAM,
        'archive_cap_bytes': ARCHIVE_CAP, 'workspace_cap_bytes': WORKSPACE}
    check(all(go.get(k) == v for k, v in expected.items()), 'Root archive GO/resource/serialization contract differs')
    resource.setrlimit(resource.RLIMIT_CPU, (CPU, CPU + 1))
    resource.setrlimit(resource.RLIMIT_AS, (RAM, RAM))
    def deadline(signum, frame):
        raise TimeoutError('600s archive wall bound')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(WALL)
    handles, writer, created = [], None, False
    destination, receipt_path = root / ARCHIVE, root / RECEIPT
    try:
        check(not destination.exists() and not receipt_path.exists(), 'Create-only archive and receipt required')
        for name in ('ACTIVE_FAMILY_FLOCK.lock', 'delivery/ARCHIVE_FLOCK.lock'):
            stream = (root / BASE / name).open('a+b')
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            handles.append(stream)
        guard(root, reserve=ARCHIVE_CAP + 8 * 1024**2)
        actual_results = {p.relative_to(root).as_posix() for p in (root / BASE / 'results').rglob('*')
                          if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.lock'}
        check(actual_results <= sources, 'Unlisted new-phase output present during serialized archive admission')
        destination.parent.mkdir(parents=True, exist_ok=True)
        before = [pin(root, confined(root, m['source_path'])) for m in manifest['members']]
        check(before == [{'path': m['source_path'], 'bytes': m['bytes'], 'sha256': m['sha256']}
                         for m in manifest['members']], 'Selected whole-file pre-pins differ from closed root manifest')
        writer = destination.open('xb')
        created = True
        archive_expected = {'MANIFEST.json': {'bytes': path.stat().st_size, 'sha256': args.manifest_sha256}}
        with zipfile.ZipFile(writer, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as archive:
            manifest_raw = path.read_bytes()
            check(hashlib.sha256(manifest_raw).hexdigest() == args.manifest_sha256, 'Manifest changed before writing')
            archive.writestr('MANIFEST.json', manifest_raw)
            for member in manifest['members']:
                source = confined(root, member['source_path'])
                expected_pin = {'path': member['source_path'], 'bytes': member['bytes'], 'sha256': member['sha256']}
                check(source.stat().st_size == member['bytes'], 'Selected file size changed before streaming')
                h, size = hashlib.sha256(), 0
                with source.open('rb') as input_stream, archive.open(member['archive_path'], 'w', force_zip64=True) as output_stream:
                    for chunk in iter(lambda: input_stream.read(1024**2), b''):
                        h.update(chunk)
                        size += len(chunk)
                        output_stream.write(chunk)
                        check(writer.tell() <= ARCHIVE_CAP, 'Archive streaming byte bound exceeded')
                check(size == member['bytes'] and h.hexdigest() == member['sha256'], 'Exact streamed member differs')
                archive_expected[member['archive_path']] = {'bytes': size, 'sha256': h.hexdigest()}
                check(os.fstat(writer.fileno()).st_size <= ARCHIVE_CAP, 'Archive byte bound exceeded')
                if len(archive_expected) % 64 == 0:
                    guard(root, writer)
        writer.flush()
        os.fsync(writer.fileno())
        check(destination.stat().st_size <= ARCHIVE_CAP, 'Final500MiB archive bound exceeded')
        with fresh_archive_reader(destination, writer) as fresh_reader:
            archive_sha = digest_stream(fresh_reader)
            fresh_reader.seek(0)
            with zipfile.ZipFile(fresh_reader, 'r') as readback:
                infos = readback.infolist()
                check(len(infos) == len(archive_expected) and len({p.filename for p in infos}) == len(infos)
                      and {p.filename for p in infos} == set(archive_expected), 'Exact ZIP membership/duplicate validation failed')
                for info in infos:
                    expected_member = archive_expected[info.filename]
                    check(info.file_size == expected_member['bytes'] and not info.is_dir(), 'ZIP member size/type differs')
                    h, size = hashlib.sha256(), 0
                    with readback.open(info) as stream:
                        # ZipExtFile verifies CRC when each member reaches EOF.
                        for chunk in iter(lambda: stream.read(1024**2), b''):
                            h.update(chunk)
                            size += len(chunk)
                    check(size == expected_member['bytes'] and h.hexdigest() == expected_member['sha256'],
                          'Fresh-path ZIP full-member CRC/SHA integrity failed')
        after = [pin(root, confined(root, m['source_path'])) for m in manifest['members']]
        check(after == before and digest(path) == args.manifest_sha256 and digest(go_path) == args.root_go_sha256
              and digest(Path(__file__).resolve()) == args.builder_sha256, 'Selected/input/source bytes changed during packaging')
        admission(root, manifest)
        with fresh_archive_reader(destination, writer) as final_reader:
            check(digest_stream(final_reader) == archive_sha, 'Final fresh nofollow pathname archive changed during validation')
        allocated_final = guard(root, writer)
        record = {'schema': 'SETI_S2017_CONTROL_TARGET_RESULTS_ARCHIVE_RECEIPT_V1',
            'status': 'PASS_CREATE_ONLY_ARCHIVE_ALL_MEMBERS_CRC_SHA_AND_FRESH_PATH_WRITER_FD_RETAINED',
            'archive': {'path': ARCHIVE, 'bytes': destination.stat().st_size, 'sha256': archive_sha},
            'builder_sha256': args.builder_sha256, 'manifest': pin(root, path), 'root_GO': pin(root, go_path),
            'members': len(archive_expected), 'selected_file_pins_before': before, 'selected_file_pins_after': after,
            'all_members_CRC_and_SHA_verified': True, 'manifest_membership_exact': True,
            'fresh_path_matches_original_writer_inode': True,
            'initial_and_final_fresh_reopens_O_NOFOLLOW': True,
            'whole_SHA_and_ZIP_checks_bound_to_same_fresh_reader_FD': True,
            'original_writer_FD_retained_through_receipt_and_parent_fsync': True,
            'CPU_cap_s': CPU, 'wall_cap_s': WALL, 'memory_cap_bytes': RAM,
            'archive_cap_bytes': ARCHIVE_CAP, 'workspace_cap_bytes': WORKSPACE,
            'workspace_allocated_bytes_final_before_receipt': allocated_final,
            'process_CPU_seconds': time.process_time() - cpu0, 'wall_seconds': time.monotonic() - started,
            'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            'scientific_values_decoded': False, 'HDF5_inputs_packaged': False, 'detector_executed': False,
            'new_telescope_HTTP_requests': 0, 'original_A_B_status': 'FAIL_CLOSED_UNCHANGED',
            'qualified_SETI_detection': False}
        check(record['process_CPU_seconds'] <= CPU and record['wall_seconds'] <= WALL and record['peak_RSS_bytes'] <= RAM,
              'Measured archive resource bound exceeded')
        pending = len((json.dumps(record, separators=(',', ':'), allow_nan=False) + '\n').encode())
        check(allocated_final + ((pending + 4095) // 4096) * 4096 <= WORKSPACE, 'Terminal receipt workspace bound exceeded')
        save_new(receipt_path, record)
        sync_directory(destination.parent)
        writer.close()
        writer = None
        print(json.dumps({'status': record['status'], 'archive': record['archive']}))
    except BaseException as error:
        if created and not receipt_path.exists():
            save_new(receipt_path, {'schema': 'SETI_S2017_CONTROL_TARGET_RESULTS_ARCHIVE_RECEIPT_V1',
                'status': 'INCOMPLETE_ARCHIVE_PRESERVED_NO_AUTOMATIC_RETRY', 'archive_path': ARCHIVE,
                'error_type': type(error).__name__, 'error': str(error), 'manifest_sha256': args.manifest_sha256,
                'new_telescope_HTTP_requests': 0})
            sync_directory(destination.parent)
        raise
    finally:
        signal.alarm(0)
        if writer is not None:
            writer.close()
        for stream in reversed(handles):
            stream.close()

if __name__ == '__main__':
    main()
