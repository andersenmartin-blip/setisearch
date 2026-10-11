"""Create-only archive of completed Burst4 evidence; raw observations stay external.

Import is inert. Only root invokes --build after completed production, both
independent numerical QA phases, report verification and exact code/scope pins.
No detector, numerical module, source HDF5, acquisition or Git operation is used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import sys
import time
import zipfile

BASE = 'analysis/burst4_20261011'
QA = 'analysis/burst4_20261011_qa'
CONTEXT = 'analysis/burst4_20261011_context'
PHASES = (BASE, QA, CONTEXT)
JOBS = ('primary20170428_HIP97319', 'primary20170428_HIP97461', 'primary20170428_HIP97663')
ARCHIVE_NAME = 'SETI_BURST4_RESULTS_2026-10-11.zip'
RECEIPT_NAME = 'BURST4_ARCHIVE_RECEIPT.json'
PLAN_NAME = 'BURST4_PUBLICATION_FILE_PLAN.json'
MANIFEST_NAME = 'RESULT_PACKAGE_MANIFEST.json'
ARCHIVE_CAP_BYTES = 200 * 1024**2
REPORT_FILES = ('SETI_BURST4_FINAL_2026-10-11.md', 'TOP9.csv', 'CONTEXT54.csv',
                'SUMMARY.json', 'REPORT_RECEIPT.json',
                'SETI_BURST4_CONTEXT54_2026-10-11.png',
                'SETI_BURST4_ROW_CONTRIBUTIONS_2026-10-11.png')
EXPLICIT_INPUTS = (
    'analysis/new_visit_search/dependencies/detector.py',
    'analysis/new_visit_search/dependencies/standard_reader.py',
    'analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json',
    'analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json',
    'analysis/s2017_next_native/source_manifest_v2.json',
    'analysis/s2017_next_native/results/acquire/ACQUISITION_RESULT.json',
    'analysis/RESTORE_20261011.py',
    'analysis/RESTORATION_RECEIPT_20261011.json',
)
RAW_EXTERNAL = (
    {'name': 'SETI_S2017_NATIVE171_RAW_2026-10-10.zip', 'bytes': 466351822,
     'sha256': '6e08922aec5c5a6737987887cd62aab6d52495650297cae74745a654728f4786'},
    {'name': 'SETI_S2017_NATIVE170_172_RAW_2026-10-10.zip', 'bytes': 604399781,
     'sha256': 'b78521c9f51a47d698af1ea1f8949b5676c843656389655191042a0fbc06817f',
     'ordered_parts': [
         {'suffix': '.part01', 'bytes': 209715200,
          'sha256': 'ad4be599d3e7da809df1d473c8fa677e0c2581d251fb65d9cc01d90849dd8dbb'},
         {'suffix': '.part02', 'bytes': 209715200,
          'sha256': '2ad6609f4984c536fc4dbee2223975f756459d681b8c9e1f5c6b8731f149a97f'},
         {'suffix': '.part03', 'bytes': 184969381,
          'sha256': 'd585965102de3ac3cbc9864a92249e0fb660ed6968540249c34e650b880b15ca'}]},
)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with Path(path).open('rb') as handle:
        return hashlib.file_digest(handle, 'sha256').hexdigest()


def load_json(path):
    return json.loads(Path(path).read_bytes(), parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def confined(root, name):
    relative = Path(name)
    require(not relative.is_absolute() and '..' not in relative.parts, 'Relative project path required')
    path = root / relative
    require(path.resolve().is_relative_to(root) and not path.is_symlink(), 'Confined regular file required')
    return path


def pin(root, path):
    require(path.is_file() and not path.is_symlink(), f'Missing/nonregular input: {path}')
    return {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size,
            'sha256': digest(path)}


def create_json(path, value):
    with Path(path).open('xb') as handle:
        handle.write((json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8'))
        handle.flush()
        os.fsync(handle.fileno())


def check_pins(root, values, files, text_only=True):
    """Only declared text/code pins are copied; full source compacts remain external."""
    require(isinstance(values, list) and values, 'Nonempty text/code pin list required')
    for expected in values:
        path = confined(root, expected['path'])
        require(not text_only or path.suffix in ('.py', '.json', '.md', '.txt', '.csv'), 'Text/code pin required')
        require(pin(root, path) == {key: expected[key] for key in ('path', 'bytes', 'sha256')},
                f'Declared input pin differs: {expected["path"]}')
        files.add(path)


def readiness(root, scope_sha256, script_sha256):
    """Read completed receipts and hash files, without loading numerical arrays."""
    scope_path = confined(root, BASE + '/scope.json')
    require(digest(scope_path) == scope_sha256, 'Exact primary scope SHA256 required')
    require(digest(Path(__file__).resolve()) == script_sha256, 'Exact frozen packaging script SHA256 required')
    scope = load_json(scope_path)
    require(scope.get('total_maps') == 288 and scope.get('maps_per_target') == 96,
            'Expected completed Burst4 scope required')
    require(scope.get('window_length_rows') == 4 and scope.get('window_start_rows') == [0, 2, 4, 6, 8, 10, 12],
            'Expected four-row seven-window family required')
    require(scope.get('qualified_SETI_detection') is False and scope.get('new_bandwidth_or_observation') is False,
            'Exploratory historical-source interpretation required')
    files = set()
    check_pins(root, scope['text_code_pins'], files)
    scope_pins = {p['path']: p for p in scope['text_code_pins']}
    for name in (BASE + '/build_delivery.py', BASE + '/REPRODUCTION_AND_DATA_AVAILABILITY.md'):
        require(name in scope_pins, f'Packaging code/document must be frozen in primary scope: {name}')

    primary = []
    for job in JOBS:
        path = confined(root, BASE + '/results/' + job + '/EXECUTION_RECEIPT.json')
        value = load_json(path)
        require(value.get('status') == 'COMPLETE_96_NEW_BURST4_COMBINED_MAPS_EXPLORATORY_ONLY',
                f'Primary not complete: {job}')
        require(value.get('scope_sha256') == scope_sha256 and value.get('counts', {}).get('maps') == 96,
                f'Primary scope/count differs: {job}')
        check_pins(root, value['output_byte_pins'], files, text_only=False)
        primary.append(pin(root, path))
    qa_path = confined(root, QA + '/results/QA_RECEIPT.json')
    context_path = confined(root, CONTEXT + '/results/EXECUTION_RECEIPT.json')
    context_qa_path = confined(root, CONTEXT + '/CONTEXT_QA_RECEIPT.json')
    expected_statuses = (
        (qa_path, 'PASS288_BURST4_MAPS1161_RAW4X503_QUERIES144_SOURCE_ROWS_NO_GRID_RERUN'),
        (context_path, 'COMPLETE_NINE_BURST4_FIXED_TRACKS54_SIX_SCAN_CONTEXTS'),
        (context_qa_path, 'PASS54_BURST4_CONTEXTS864_ROW_BOXES108_SCORES9_OWN_MATCHES288_SOURCE_ROWS'),
    )
    for path, status in expected_statuses:
        require(load_json(path).get('status') == status,
                f'Expected completed numerical receipt: {path.relative_to(root)}')
    primary_qa = load_json(qa_path)
    require(primary_qa['primary_scope_sha256'] == scope_sha256
            and primary_qa['primary_receipt_sha256s'] == {job: rec['sha256'] for job, rec in zip(JOBS, primary)},
            'Primary QA pins must bind these exact completed outputs')
    context_scope_path = confined(root, CONTEXT + '/context_scope.json')
    context_scope = load_json(context_scope_path)
    check_pins(root, context_scope['input_pins'], files)
    context_receipt = load_json(context_path)
    require(context_receipt['context_scope_sha256'] == digest(context_scope_path), 'Context receipt/scope differs')
    check_pins(root, context_receipt['output_pins'], files, text_only=False)
    context_qa = load_json(context_qa_path)
    for name in ('context_scope', 'context_matrix'):
        check_pins(root, [context_qa[name]], files)
    report_path = confined(root, CONTEXT + '/delivery/REPORT_RECEIPT.json')
    report = load_json(report_path)
    require(report.get('status') == 'COMPLETE_QA_GATED_SAVED_BURST4_REPORT_AND_TWO_FIGURES',
            'Completed report receipt required')
    check_pins(root, report['input_pins'], files)
    check_pins(root, report['output_pins'], files, text_only=False)
    for name in REPORT_FILES:
        require(confined(root, CONTEXT + '/delivery/' + name).is_file(), f'Missing delivery file: {name}')

    for folder in PHASES:
        directory = confined(root, folder)
        require(directory.is_dir(), f'Missing evidence phase: {folder}')
        for path in directory.rglob('*'):
            require(not path.is_symlink(), f'Symlink not archived: {path}')
            if not path.is_file() or '__pycache__' in path.parts or path.suffix in ('.pyc', '.pyo', '.lock'):
                continue
            require(path.suffix.lower() not in ('.h5', '.hdf5', '.whl'), 'Full raw/source binary excluded from phase tree')
            files.add(path)
    for name in EXPLICIT_INPUTS:
        files.add(confined(root, name))
    wheels = sorted(confined(root, 'analysis/runtime/wheels').glob('*.whl'))
    require(any(p.name.startswith('h5py-3.15.1-') for p in wheels)
            and any(p.name.startswith('hdf5plugin-7.1.0-') for p in wheels), 'Retained exact decoder wheels required')
    files.update(wheels)
    ordered = sorted(files, key=lambda p: p.relative_to(root).as_posix())
    records = [pin(root, path) for path in ordered]
    names = [p['path'] for p in records]
    require(len(names) == len(set(names)) and MANIFEST_NAME not in names, 'Unique archive member names required')
    manifest = {
        'schema': 'SETI_BURST4_COMPLETED_RESULT_PACKAGE_V1',
        'status': 'SNAPSHOT_OF_COMPLETED_RECEIPTS_AND_OUTPUTS',
        'files': records, 'payload_files': len(records),
        'scope': pin(root, scope_path), 'primary_receipts': primary,
        'primary_QA': pin(root, qa_path), 'context_scope': pin(root, context_scope_path),
        'context_receipt': pin(root, context_path), 'context_QA': pin(root, context_qa_path),
        'report_receipt': pin(root, report_path),
        'raw_sources_external': list(RAW_EXTERNAL), 'external_compact_files': 18,
        'raw_sources_copied': False, 'new_observation': False, 'qualified_SETI_detection': False,
        'calibrated_SNR_FAP': False, 'source_arrays_opened_by_packager': False,
        'protected2016_data_opened': False, 'cost_DKK': 0,
        'archive_cap_bytes': ARCHIVE_CAP_BYTES,
        'package_manifest_self_identity': 'SHA256 in external immutable archive receipt; ZIP integrity is not scientific QA',
    }
    return ordered, manifest


def publication_plan(root, manifest, archive_receipt):
    """Describe reviewable source/evidence files; publishing is a separate root action."""
    entries = []
    for record in manifest['files']:
        path = root / record['path']
        if path.suffix.lower() not in ('.py', '.json', '.md', '.txt', '.csv', '.png'):
            continue
        git_sha = hashlib.sha1()
        git_sha.update(('blob ' + str(record['bytes']) + '\0').encode('ascii'))
        with path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(1024**2), b''):
                git_sha.update(chunk)
        entries.append({**record, 'git_blob_sha': git_sha.hexdigest(),
                        'encoding': 'base64' if path.suffix.lower() == '.png' else 'utf-8'})
    return {'schema': 'SETI_BURST4_PUBLICATION_FILE_PLAN_V1',
            'status': 'METADATA_ONLY_NO_GIT_OPERATION',
            'files': entries, 'archive_identity': {key: archive_receipt[key]
                     for key in ('archive', 'bytes', 'sha256', 'payload_files', 'zip_members')},
            'full_map_and_raw503_results': 'Retained in complete archive; NPZs and decoder wheels omitted from this text/PNG publication plan',
            'public_evidence_is_not_new_observation_or_independent_qualification': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--build', action='store_true', help='Root-controlled explicit archive creation')
    parser.add_argument('--scope-sha256', required=True)
    parser.add_argument('--script-sha256', required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    require(root.is_dir(), 'Existing project root required')
    output = root.parent / 'deliverables'
    archive, receipt_path, plan_path = (output / name for name in (ARCHIVE_NAME, RECEIPT_NAME, PLAN_NAME))
    require(not any(path.exists() or path.is_symlink() for path in (archive, receipt_path, plan_path)),
            'Create-only destination exists; preserve outputs and failures without rerun')
    files, manifest = readiness(root, args.scope_sha256, args.script_sha256)
    manifest_bytes = (json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
    if not args.build:
        print(json.dumps({'status': 'PASS_COMPLETED_EVIDENCE_METADATA_CHECK_ONLY_NO_ARCHIVE_WRITE',
                          'payload_files': len(files), 'payload_bytes': sum(p['bytes'] for p in manifest['files']),
                          'archive_cap_bytes': ARCHIVE_CAP_BYTES, 'source_arrays_opened': False}))
        return
    output.mkdir(exist_ok=True)
    start, cpu = time.perf_counter(), time.process_time()
    try:
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as handle:
            for path in files:
                handle.write(path, path.relative_to(root).as_posix())
                require(handle.fp.tell() <= ARCHIVE_CAP_BYTES, 'Prospective 200MiB archive cap exceeded')
            handle.writestr(MANIFEST_NAME, manifest_bytes)
        require(archive.stat().st_size <= ARCHIVE_CAP_BYTES, 'Final 200MiB archive cap exceeded')
        with zipfile.ZipFile(archive, 'r') as handle:
            expected = [p['path'] for p in manifest['files']] + [MANIFEST_NAME]
            require(handle.namelist() == expected, 'Archive member order/names differ')
            require(handle.testzip() is None, 'Archive CRC verification failed')
            require(handle.read(MANIFEST_NAME) == manifest_bytes, 'Embedded manifest differs')
            for record in manifest['files']:
                info = handle.getinfo(record['path'])
                require(info.file_size == record['bytes'], f'Archive member size differs: {record["path"]}')
                member_sha = hashlib.sha256()
                with handle.open(record['path']) as member:
                    for chunk in iter(lambda: member.read(1024**2), b''):
                        member_sha.update(chunk)
                require(member_sha.hexdigest() == record['sha256'], f'Archive member SHA256 differs: {record["path"]}')
        for record in manifest['files']:
            require(pin(root, root / record['path']) == record, f'Evidence changed during archive build: {record["path"]}')
        receipt = {
            'schema': 'SETI_BURST4_ARCHIVE_RECEIPT_V1',
            'status': 'PASS_COMPLETE_ARCHIVE_CRC_AND_ALL_MEMBER_SHA256',
            'archive': str(archive), 'bytes': archive.stat().st_size, 'sha256': digest(archive),
            'payload_files': len(files), 'zip_members': len(files) + 1,
            'manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(),
            'all_members_CRC_verified': True, 'all_payload_member_SHA256_verified': True,
            'all_source_snapshot_pins_unchanged': True,
            'scope_sha256': args.scope_sha256, 'packaging_script_sha256': args.script_sha256,
            'CPU_seconds': time.process_time() - cpu, 'wall_seconds': time.perf_counter() - start,
            'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            'source_arrays_opened': False, 'raw_sources_copied': False, 'cost_DKK': 0,
        }
        plan = publication_plan(root, manifest, receipt)
        create_json(plan_path, plan)
        receipt['publication_plan'] = {'path': str(plan_path), 'bytes': plan_path.stat().st_size,
                                       'sha256': digest(plan_path)}
        create_json(receipt_path, receipt)
        print(json.dumps(receipt))
    except BaseException as exc:
        if not receipt_path.exists():
            create_json(receipt_path, {'schema': 'SETI_BURST4_ARCHIVE_RECEIPT_V1',
                'status': 'INCOMPLETE_PRESERVED_NO_AUTOMATIC_RETRY', 'archive': str(archive),
                'failure_type': type(exc).__name__, 'failure': str(exc),
                'CPU_seconds': time.process_time() - cpu, 'wall_seconds': time.perf_counter() - start,
                'packaging_script_sha256': args.script_sha256, 'scope_sha256': args.scope_sha256})
        raise


if __name__ == '__main__':
    main()
