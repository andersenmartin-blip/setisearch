"""Create-only delivery of completed fixed temporal-order diagnostics.

Import is inert. Root alone invokes --build after exact code/scope freeze,
three COMPLETE jobs, independent PASS numerical QA and verified report outputs.
No numerical module, array decoder, source acquisition or Git operation is used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import time
import zipfile

BASE = 'analysis/burst_order_20261011'
JOBS = ('primary20170428_HIP97319', 'primary20170428_HIP97461', 'primary20170428_HIP97663')
PRIMARY_STATUS = 'COMPLETE_387_FIXED_BURST4_TEMPORAL_ORDER_QUERIES'
QA_STATUS = 'PASS_1161_FIXED_TEMPORAL_ORDER_QUERIES18576_ROW_CENTER_BOXES27864_PERMUTATION_SCORES9_TOP3'
REPORT_STATUS = 'COMPLETE_QA_GATED_FIXED_TEMPORAL_ORDER_REPORT_AND_TWO_FIGURES'
ARCHIVE_NAME = 'SETI_BURST_ORDER_RESULTS_2026-10-11.zip'
RECEIPT_NAME = 'BURST_ORDER_ARCHIVE_RECEIPT.json'
PLAN_NAME = 'BURST_ORDER_PUBLICATION_FILE_PLAN.json'
MANIFEST_NAME = 'RESULT_PACKAGE_MANIFEST.json'
ARCHIVE_CAP_BYTES = 100 * 1024**2
REPORT_FILES = ('SETI_BURST_ORDER_FINAL_2026-10-11.md', 'TOP9.csv', 'AUDIT1161.csv',
                'STRATIFIED_COUNTS.csv', 'SUMMARY.json', 'REPORT_RECEIPT.json',
                'SETI_BURST_ORDER_TOP9_2026-10-11.png', 'SETI_BURST_ORDER_STRATA_2026-10-11.png')
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
    require(path.resolve().is_relative_to(root) and not path.is_symlink(), 'Confined nonsymlink path required')
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


def check_pins(root, declarations, files, prior=False):
    require(isinstance(declarations, list) and declarations, 'Nonempty declared pin list required')
    for declaration in declarations:
        path = confined(root, declaration['path'])
        require(path.suffix.lower() not in ('.h5', '.hdf5', '.whl', '.zip'), 'Full sources/runtime archives remain external')
        if prior and path.suffix == '.npz':
            require(path.name.endswith('_raw4x503.npz'), 'Only declared prior raw4x503 capsules, no old carrier maps')
        actual = pin(root, path)
        require(actual == {key: declaration[key] for key in ('path', 'bytes', 'sha256')},
                f'Declared input/output pin differs: {declaration["path"]}')
        files.add(path)


def readiness(root, scope_sha256, script_sha256):
    """Hash saved evidence only; no scientific arrays or full HDF5 are decoded."""
    scope_path = confined(root, BASE + '/scope.json')
    require(digest(scope_path) == scope_sha256, 'Exact frozen scope SHA256 required')
    require(digest(Path(__file__).resolve()) == script_sha256, 'Exact frozen package script SHA256 required')
    scope = load_json(scope_path)
    require(scope['schema'] == 'SETI_BURST4_TEMPORAL_ORDER_SCOPE_V1'
            and set(scope['jobs']) == set(JOBS) and len(scope['source_compacts']) == 9,
            'Exactly three original OFF jobs/nine sources required')
    require(scope['total_queries'] == 1161 and scope['queries_per_target'] == 387
            and scope['center_assignments_per_query'] == 24 and scope['new_detector_grid'] is False
            and scope['new_normalization_estimation'] is False and scope['new_observation'] is False
            and scope['calibrated_SNR_FAP_or_permutation_p_value'] is False,
            'Exact fixed-query noncalibrated scientific scope required')
    files = set()
    check_pins(root, scope['text_code_pins'], files)
    check_pins(root, scope['prior_data_pins'], files, prior=True)
    code_pins = {rec['path']: rec for rec in scope['text_code_pins']}
    for name in ('build_delivery.py', 'REPRODUCTION.md'):
        require(BASE + '/' + name in code_pins, 'Package code/document must be prospectively scope-pinned')
    receipts = []
    for job in JOBS:
        path = confined(root, BASE + '/results/' + job + '/EXECUTION_RECEIPT.json')
        receipt = load_json(path)
        require(receipt['status'] == PRIMARY_STATUS and receipt['scope_sha256'] == scope_sha256,
                f'Expected exact completed query job: {job}')
        groups = scope['jobs'][job]['scientific_tuple_groups']
        require(receipt['primary_id'] == job
                and all(receipt['counts'].get(key) == value for key, value in scope['expected_counts_per_target'].items())
                and receipt['counts']['unique_scientific_tuples'] == len(groups)
                and receipt['counts']['duplicate_scientific_tuple_occurrences'] == 387 - len(groups)
                and sum(len(group['query_ids']) for group in groups) == 387,
                'Closed target query/group/resource accounting differs')
        require(len(receipt['output_byte_pins']) == 388, 'Exactly 387 capsules plus diagnostics required')
        check_pins(root, receipt['output_byte_pins'], files)
        diagnostics = confined(root, BASE + '/results/' + job + '/QUERY_DIAGNOSTICS.json')
        require(diagnostics in files, 'Completed receipt must bind QUERY_DIAGNOSTICS.json')
        receipts.append(pin(root, path))
    qa_path = confined(root, BASE + '/QA_RECEIPT.json')
    qa = load_json(qa_path)
    require(qa['status'] == QA_STATUS and qa['scope_sha256'] == scope_sha256, 'Completed independent query QA required')
    require({value['path']: value for value in qa['producer_receipt_pins']}
            == {value['path']: value for value in receipts} and len(qa['producer_receipt_pins']) == 3,
            'Independent QA must bind these exact completed job receipts')
    check_pins(root, qa['producer_receipt_pins'], files)
    require(qa['job_receipt_sha256s'] == {job: value['sha256'] for job, value in zip(JOBS, receipts)},
            'Independent QA job-hash dictionary differs')
    report_path = confined(root, BASE + '/delivery/REPORT_RECEIPT.json')
    report = load_json(report_path)
    require(report['status'] == REPORT_STATUS, 'Completed QA-gated saved-JSON report required')
    check_pins(root, report['input_pins'], files)
    check_pins(root, report['output_pins'], files)
    require(pin(root, qa_path) in report['input_pins'], 'Report must bind exact independent QA receipt')
    for name in REPORT_FILES:
        require(confined(root, BASE + '/delivery/' + name).is_file(), f'Missing delivered report file: {name}')

    for path in confined(root, BASE).rglob('*'):
        require(not path.is_symlink(), f'Symlink not archived: {path}')
        if not path.is_file() or '__pycache__' in path.parts or path.suffix in ('.pyc', '.pyo', '.lock', '.log'):
            continue
        require(path.suffix.lower() not in ('.h5', '.hdf5', '.whl', '.zip'), 'Full binary source/runtime archive excluded')
        files.add(path)
    ordered = sorted(files, key=lambda p: p.relative_to(root).as_posix())
    records = [pin(root, path) for path in ordered]
    names = [record['path'] for record in records]
    require(len(names) == len(set(names)) and MANIFEST_NAME not in names, 'Unique archive member paths required')
    # Preserve actual scope dictionary keys instead of silently translating caps.
    contract = {key: value for key, value in scope.items()
                if key not in ('text_code_pins', 'prior_data_pins', 'source_compacts', 'jobs')}
    manifest = {
        'schema': 'SETI_FIXED_TEMPORAL_ORDER_COMPLETED_PACKAGE_V1',
        'status': 'SNAPSHOT_OF_COMPLETED_QUERY_QA_AND_REPORT_EVIDENCE',
        'files': records, 'payload_files': len(records), 'scope': pin(root, scope_path),
        'scope_contract_original_keys': contract, 'job_receipts': receipts,
        'independent_QA': pin(root, qa_path), 'report_receipt': pin(root, report_path),
        'external_source_compacts': scope['source_compacts'],
        'canonical_raw_packages_external': list(RAW_EXTERNAL),
        'raw_sources_copied': False, 'prior_carrier_maps_copied': False,
        'source_arrays_decoded_by_packager': False, 'full_grid_rerun': False,
        'new_observation': False, 'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False,
        'permutation_rank_is_not_sky_FAP': True, 'protected2016_data_opened': False,
        'cost_DKK': 0, 'archive_cap_bytes': ARCHIVE_CAP_BYTES,
        'omitted_from_new_phase_tree': ['__pycache__', '*.pyc', '*.pyo', '*.lock', '*.log'],
        'manifest_self_identity': 'SHA256 in immutable external archive receipt; byte integrity is not scientific qualification',
    }
    return ordered, manifest


def publication_plan(root, manifest, receipt):
    entries = []
    for record in manifest['files']:
        path = root / record['path']
        if path.suffix.lower() not in ('.py', '.json', '.md', '.txt', '.csv', '.png'):
            continue
        h = hashlib.sha1(('blob ' + str(record['bytes']) + '\0').encode('ascii'))
        with path.open('rb') as handle:
            for chunk in iter(lambda: handle.read(1024**2), b''):
                h.update(chunk)
        entries.append({**record, 'git_blob_sha': h.hexdigest(),
                        'encoding': 'base64' if path.suffix.lower() == '.png' else 'utf-8'})
    return {'schema': 'SETI_FIXED_TEMPORAL_ORDER_PUBLICATION_FILE_PLAN_V1',
            'status': 'METADATA_ONLY_NO_GIT_OPERATION', 'files': entries,
            'archive_identity': {key: receipt[key] for key in ('archive', 'bytes', 'sha256', 'payload_files', 'zip_members')},
            'NPZ_evidence': 'All new matrices/capsules and pinned prior raw503 anchors remain in the complete ZIP',
            'new_observation_or_qualification': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--scope-sha256', required=True)
    parser.add_argument('--script-sha256', required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    require(root.is_dir(), 'Existing project root required')
    output = root.parent / 'deliverables'
    archive, receipt_path, plan_path = (output / name for name in (ARCHIVE_NAME, RECEIPT_NAME, PLAN_NAME))
    require(not any(path.exists() or path.is_symlink() for path in (archive, receipt_path, plan_path)),
            'Create-only destination exists; preserve completed or failed outputs without rerun')
    files, manifest = readiness(root, args.scope_sha256, args.script_sha256)
    manifest_bytes = (json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
    if not args.build:
        print(json.dumps({'status': 'PASS_COMPLETED_EVIDENCE_CHECK_ONLY_NO_ARCHIVE_WRITE',
            'payload_files': len(files), 'payload_bytes': sum(rec['bytes'] for rec in manifest['files']),
            'archive_cap_bytes': ARCHIVE_CAP_BYTES, 'source_arrays_decoded': False}))
        return
    output.mkdir(exist_ok=True)
    started, cpu = time.perf_counter(), time.process_time()
    try:
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as handle:
            for path in files:
                handle.write(path, path.relative_to(root).as_posix())
                require(handle.fp.tell() <= ARCHIVE_CAP_BYTES, 'Prospective 100MiB ZIP cap exceeded')
            handle.writestr(MANIFEST_NAME, manifest_bytes)
        require(archive.stat().st_size <= ARCHIVE_CAP_BYTES, 'Final 100MiB ZIP cap exceeded')
        with zipfile.ZipFile(archive, 'r') as handle:
            require(handle.namelist() == [rec['path'] for rec in manifest['files']] + [MANIFEST_NAME], 'Member order/identity differs')
            require(handle.testzip() is None, 'ZIP CRC failure')
            require(handle.read(MANIFEST_NAME) == manifest_bytes, 'Embedded manifest bytes differ')
            for record in manifest['files']:
                require(handle.getinfo(record['path']).file_size == record['bytes'], f'Member size differs: {record["path"]}')
                member_hash = hashlib.sha256()
                with handle.open(record['path']) as member:
                    for chunk in iter(lambda: member.read(1024**2), b''):
                        member_hash.update(chunk)
                require(member_hash.hexdigest() == record['sha256'], f'Member SHA256 differs: {record["path"]}')
        for record in manifest['files']:
            require(pin(root, root / record['path']) == record, f'Input/output changed during package build: {record["path"]}')
        receipt = {
            'schema': 'SETI_FIXED_TEMPORAL_ORDER_ARCHIVE_RECEIPT_V1',
            'status': 'PASS_COMPLETE_ZIP_CRC_AND_ALL_MEMBER_SHA256',
            'archive': str(archive), 'bytes': archive.stat().st_size, 'sha256': digest(archive),
            'payload_files': len(files), 'zip_members': len(files) + 1,
            'manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(),
            'all_members_CRC_verified': True, 'all_payload_member_SHA256_verified': True,
            'all_source_snapshot_pins_unchanged': True, 'scope_sha256': args.scope_sha256,
            'packaging_script_sha256': args.script_sha256, 'CPU_seconds': time.process_time() - cpu,
            'wall_seconds': time.perf_counter() - started,
            'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            'archive_cap_bytes': ARCHIVE_CAP_BYTES, 'raw_sources_copied': False,
            'source_arrays_decoded': False, 'new_observation': False, 'cost_DKK': 0,
        }
        create_json(plan_path, publication_plan(root, manifest, receipt))
        receipt['publication_plan'] = {'path': str(plan_path), 'bytes': plan_path.stat().st_size, 'sha256': digest(plan_path)}
        create_json(receipt_path, receipt)
        print(json.dumps(receipt))
    except BaseException as exc:
        if not receipt_path.exists():
            create_json(receipt_path, {'schema': 'SETI_FIXED_TEMPORAL_ORDER_ARCHIVE_RECEIPT_V1',
                'status': 'INCOMPLETE_PRESERVED_NO_AUTOMATIC_RETRY', 'archive': str(archive),
                'failure_type': type(exc).__name__, 'failure': str(exc),
                'CPU_seconds': time.process_time() - cpu, 'wall_seconds': time.perf_counter() - started,
                'scope_sha256': args.scope_sha256, 'packaging_script_sha256': args.script_sha256})
        raise


if __name__ == '__main__':
    main()
