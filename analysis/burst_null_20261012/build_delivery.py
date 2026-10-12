"""Create-only opaque-byte package for completed Gamma51 synthetic families.

Import and --check-only are source-only. Root's --build requires exact frozen
scope/code/GO and completed independent QA/report hashes. The packager opens
no scientific array decoder and performs no numerical or detector computation.
Prior real-data references are text/JSON/CSV only; prior HDF5/NPZ stay external.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import time
import zipfile

BASE = 'analysis/burst_null_20261012'
JOBS = tuple('null%02d' % index for index in range(1, 9))
REPORT_STATUS = 'COMPLETE_QA_GATED_GAMMA51_FULL_SEARCH_ENGINEERING_REPORT_AND_TWO_FIGURES'
ARCHIVE_NAME = 'SETI_BURST_NULL_RESULTS_2026-10-12.zip'
RECEIPT_NAME = 'BURST_NULL_ARCHIVE_RECEIPT.json'
PLAN_NAME = 'BURST_NULL_PUBLICATION_FILE_PLAN.json'
MANIFEST_NAME = 'RESULT_PACKAGE_MANIFEST.json'
ARCHIVE_CAP_BYTES = 200 * 1024**2
WORKSPACE_CAP_BYTES = 8 * 1024**3
CPU_CAP, WALL_CAP, RAM_CAP = 200, 900, 2 * 1024**3
PHASE_CPU_ALLOCATION_S = 6000
PRIMARY_OUTPUT_CAP_BYTES, TOTAL_PRIMARY_OUTPUT_CAP_BYTES = 40 * 1024**2, 320 * 1024**2
NEW_SUFFIXES = ('.py', '.json', '.md', '.txt', '.csv', '.png', '.npz')
PRIOR_TEXT_SUFFIXES = ('.py', '.json', '.md', '.txt', '.csv')
REPORT_FILES = ('SETI_BURST_NULL_FINAL_2026-10-12.md', 'FAMILY8.csv',
                'SYNTHETIC_TOP24.csv', 'REAL_REFERENCE_TOP9.csv', 'SUMMARY.json',
                'SETI_BURST_NULL_FAMILIES_2026-10-12.png',
                'SETI_BURST_NULL_REAL_REFERENCE_2026-10-12.png', 'REPORT_RECEIPT.json')
EXPECTED_QA_COUNTS = {'families': 8, 'maps': 768, 'carrier_maxima': 3145728,
    'valid_hypothesis_records': 7002390528, 'normalization_records': 768,
    'model_raw_crops_regenerated': 768, 'model_raw_rows_SHA256': 12288,
    'model_raw_cells_regenerated': 148635648, 'raw_core_row_medians': 12288,
    'score_audit_queries': 3096, 'score_audit_row_boxes': 12384,
    'score_audit_raw_cells': 6229152, 'TOP20_entries': 160, 'TOP3_entries': 24,
    'order_queries': 24, 'row_center_boxes': 384, 'permutation_scores': 576}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def read_json(path):
    require(path.suffix == '.json', 'JSON evidence required')
    return json.loads(path.read_bytes(), parse_constant=lambda value:
                      (_ for _ in ()).throw(ValueError(value)))


def confined(root, name):
    relative = Path(name)
    require(not relative.is_absolute() and '..' not in relative.parts,
            'Confined relative project path required')
    path = root / relative
    require(path.resolve().is_relative_to(root) and not path.is_symlink(),
            'Confined nonsymlink project path required')
    return path


def pin(root, path):
    require(path.is_file() and not path.is_symlink(), 'Regular input required: ' + str(path))
    return {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size,
            'sha256': digest(path)}


def create_json(path, value):
    with path.open('xb') as stream:
        stream.write((json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8'))
        stream.flush()
        os.fsync(stream.fileno())


def add_pins(root, declarations, files):
    require(isinstance(declarations, list) and declarations, 'Nonempty actual pin list required')
    for declaration in declarations:
        path = confined(root, declaration['path'])
        suffixes = NEW_SUFFIXES if path.is_relative_to(root / BASE) else PRIOR_TEXT_SUFFIXES
        require(path.suffix.lower() in suffixes,
                'Prior arrays/full sources/runtime archives are excluded: ' + declaration['path'])
        require(pin(root, path) == {key: declaration[key] for key in ('path', 'bytes', 'sha256')},
                'Declared input/output pin differs: ' + declaration['path'])
        if path.suffix.lower() in PRIOR_TEXT_SUFFIXES:
            require(re.search(rb'\blibfile_[0-9a-f]{32}\b', path.read_bytes()) is None,
                    'Private native file identifier is excluded from public payload: ' + declaration['path'])
        files.add(path)


def workspace_bytes(root):
    total = 0
    for path in root.rglob('*'):
        if path.is_file() and not path.is_symlink():
            total += path.stat().st_size
    return total


def readiness(root, args):
    """Read authenticated metadata; copy only new synthetic arrays as bytes."""
    require(digest(Path(__file__).resolve()) == args.script_sha256, 'Exact frozen package code required')
    scope_path = confined(root, BASE + '/scope.json')
    go_path = confined(root, args.root_go)
    qa_path = confined(root, BASE + '/QA_RECEIPT.json')
    report_path = confined(root, BASE + '/delivery/REPORT_RECEIPT.json')
    for path, expected in ((scope_path, args.scope_sha256), (go_path, args.root_go_sha256),
                           (qa_path, args.qa_receipt_sha256), (report_path, args.report_receipt_sha256)):
        require(digest(path) == expected, 'Exact frozen/completed evidence hash differs: ' + str(path))
    scope, go, qa, report = (read_json(path) for path in (scope_path, go_path, qa_path, report_path))
    require(scope['schema'] == 'SETI_FULL_BURST_IID_GAMMA_MODEL_SCOPE_V1' and set(scope['jobs']) == set(JOBS),
            'Eight fixed synthetic families required')
    require(scope['model_law']['distribution'] == 'IID Gamma' and scope['model_law']['shape'] == 51.0 and
            scope['model_law']['scale'] == 1.0 / 51.0 and scope['model_law']['fitted_to_observations'] is False and
            scope['total_maps'] == 768 and scope['maps_per_family'] == 96 and
            scope['total_carrier_maximum_records'] == 3145728 and
            scope['total_valid_hypothesis_records'] == 7002390528 and scope['independent_model_units'] == 8 and
            scope['archive_cap_bytes'] == ARCHIVE_CAP_BYTES and scope['workspace_cap_bytes'] == WORKSPACE_CAP_BYTES and
            scope['job_output_budget_bytes'] == PRIMARY_OUTPUT_CAP_BYTES and
            scope['total_output_budget_bytes'] == TOTAL_PRIMARY_OUTPUT_CAP_BYTES and
            scope['phase_CPU_allocation_s'] == PHASE_CPU_ALLOCATION_S,
            'Frozen Gamma model, engineering units, full search or resource contract differs')
    require(go['status'] == 'GO_8_FULL_IID_GAMMA_NULL_FAMILIES' and
            go['scope_sha256'] == args.scope_sha256, 'Root GO for this exact synthetic scope required')
    files = {scope_path, go_path, qa_path, report_path}
    add_pins(root, scope['text_code_pins'], files)
    add_pins(root, scope['prior_reference_pins'], files)
    code_pins = {item['path']: item for item in scope['text_code_pins']}
    require(len(code_pins) == len(scope['text_code_pins']) and
            all(BASE + '/' + name in code_pins for name in ('driver.py', 'qa_saved.py',
                                                          'make_report.py', 'build_delivery.py', 'REPRODUCTION.md')),
            'All producer/QA/report/package sources must be prospectively pinned')
    require(code_pins[BASE + '/build_delivery.py']['sha256'] == args.script_sha256 and
            go['driver_sha256'] == code_pins[BASE + '/driver.py']['sha256'] and
            go['qa_sha256'] == code_pins[BASE + '/qa_saved.py']['sha256'],
            'Root GO code identities differ')
    receipts, total_counts, winning_by_job, output_bytes = [], {}, {}, 0
    for job in JOBS:
        path = confined(root, BASE + '/results/' + job + '/EXECUTION_RECEIPT.json')
        receipt = read_json(path)
        require(receipt['status'] == 'COMPLETE_96_IID_GAMMA_NULL_MAPS387_AUDITS3_ORDER_DIAGNOSTICS' and
                receipt['primary_id'] == receipt['scan_id'] == job and
                receipt['family_index'] == JOBS.index(job) + 1 and receipt['scope_sha256'] == args.scope_sha256 and
                receipt['driver_sha256'] == go['driver_sha256'], 'Exact completed synthetic job required: ' + job)
        require(receipt['root_GO_pin'] == pin(root, go_path), 'Completed synthetic job has different root GO')
        require(set(receipt['counts']) == set(scope['expected_counts_per_family']) | {'winning_raw_crops'} and
                all(receipt['counts'].get(key) == value for key, value in scope['expected_counts_per_family'].items()),
                'Synthetic count contract differs')
        require(len({item['path'] for item in receipt['output_byte_pins']}) == len(receipt['output_byte_pins']) and
                all(Path(item['path']).is_relative_to(Path(BASE) / 'results' / job)
                    for item in receipt['output_byte_pins']),
                'Unique confined new synthetic job output paths required')
        add_pins(root, receipt['output_byte_pins'], files)
        raw_winner_pins = [item for item in receipt['output_byte_pins']
                           if item['path'].endswith('_raw16x12096.npz')]
        require(1 <= len(raw_winner_pins) <= 3 and
                len(receipt['output_byte_pins']) == 588 + len(raw_winner_pins),
                'Closed all-map/audit/order and distinct winner raw inventory differs')
        require(receipt['counts']['winning_raw_crops'] == len(raw_winner_pins),
                'Dynamic winner raw crop count differs from preserved payload')
        winning_by_job[job] = len(raw_winner_pins)
        require(receipt['schema'] == 'SETI_GAMMA_NULL_FAMILY_EXECUTION_V1' and
                0 < receipt['process_CPU_seconds'] <= 600 and 0 < receipt['wall_seconds'] <= 900 and
                0 < receipt['peak_RSS_bytes'] <= RAM_CAP and receipt['observational_arrays_opened'] is False and
                receipt['new_telescope_HTTP_requests'] == 0 and receipt['sky_FAP_or_permutation_p_value'] is False and
                receipt['qualified_SETI_detection'] is False and receipt['original_A_B_status'] == 'FAIL_CLOSED_UNCHANGED',
                'Completed synthetic resource/interpretation limits differ')
        nbytes = sum(item['bytes'] for item in receipt['output_byte_pins'])
        require(nbytes <= PRIMARY_OUTPUT_CAP_BYTES, '40MiB per-family output cap exceeded')
        output_bytes += nbytes
        for key, value in receipt['counts'].items():
            require(type(value) is int and value >= 0, 'Nonnegative integer accounting required')
            total_counts[key] = total_counts.get(key, 0) + value
        receipts.append(pin(root, path))
        files.add(path)
    require(output_bytes <= TOTAL_PRIMARY_OUTPUT_CAP_BYTES, '320MiB total primary output cap exceeded')
    require(total_counts['maps'] == 768 and total_counts['carrier_maximum_records'] == 3145728 and
            total_counts['valid_hypothesis_records'] == 7002390528 and total_counts['score_audit_queries'] == 3096 and
            total_counts['order_queries'] == 24 and total_counts['permutation_scores'] == 576 and
            total_counts['row_center_boxes'] == 384, 'Eight-family exact total accounting differs')
    winning_total = sum(winning_by_job.values())
    expected_qa_counts = {**EXPECTED_QA_COUNTS, 'winning_raw_core_crops': winning_total,
        'winning_full_core_preprocess_rows': winning_total * 16,
        'winning_full_core_residual_cells': winning_total * 16 * 4096}
    require(qa['schema'] == 'SETI_BURST_NULL_RAW_NOISE_INDEPENDENT_QA_V1' and
            qa['status'] == 'PASS_8_IID_GAMMA_FAMILIES768_MAPS3096_AUDITS24_ORDER_QUERIES576_PERMUTATION_SCORES' and
            qa['scope_sha256'] == args.scope_sha256 and qa['driver_sha256'] == go['driver_sha256'] and
            qa['qa_sha256'] == go['qa_sha256'] and qa['counts'] == expected_qa_counts and
            qa['winning_raw_core_crops_per_family'] == winning_by_job and
            qa['full_core_MAD_location_reconstructed_for_winning_cores'] is True and
            qa['full_core_MAD_location_reconstructed_for_all_maps'] is False and
            qa['other_audit_scores_conditional_on_saved_full_core_MAD_location'] is True and
            qa['model_streams_replayed_for_bit_verification'] is True and
            qa['independent_replicates_added_by_QA'] == 0 and qa['full_search_grid_recomputed'] is False and
            qa['actual_telescope_arrays_opened'] is False and qa['qualified_SETI_detection'] is False and
            qa['calibrated_telescope_SNR_FAP'] is False,
            'Completed independent synthetic QA counts, provenance or scientific limits differ')
    require({item['path']: item for item in qa['producer_receipt_pins']} ==
            {item['path']: item for item in receipts} and len(qa['producer_receipt_pins']) == 8,
            'Independent QA must bind all eight exact completed receipts')
    require(qa['job_receipt_sha256s'] == {job: item['sha256'] for job, item in zip(JOBS, receipts)},
            'QA eight-job receipt dictionary differs')
    add_pins(root, qa['producer_receipt_pins'], files)
    add_pins(root, [qa['root_GO_pin']], files)
    qa_go_path = confined(root, qa['root_GO_pin']['path'])
    qa_go = read_json(qa_go_path)
    require(qa['root_GO_pin']['sha256'] == qa['root_go_sha256'] and
            qa_go['status'] == 'GO_INDEPENDENT_SAVED_IID_GAMMA_QA' and
            qa_go['scope_sha256'] == args.scope_sha256 and qa_go['qa_sha256'] == qa['qa_sha256'] and
            qa_go['driver_sha256'] == go['driver_sha256'] and
            qa_go['job_receipt_sha256s'] == qa['job_receipt_sha256s'],
            'Independent QA exact root authorization differs')
    require(report['status'] == REPORT_STATUS and report['scope_sha256'] == args.scope_sha256 and
            report['qa_receipt_sha256'] == args.qa_receipt_sha256 and
            report['report_code_sha256'] == code_pins[BASE + '/make_report.py']['sha256'],
            'Completed exact QA-gated engineering report required')
    add_pins(root, report['input_pins'], files)
    add_pins(root, report['output_pins'], files)
    require(pin(root, qa_path) in report['input_pins'], 'Report does not bind independent QA bytes')
    require({item['path'] for item in report['output_pins']} ==
            {BASE + '/delivery/' + name for name in REPORT_FILES if name != 'REPORT_RECEIPT.json'},
            'Seven exact report outputs required')
    for name in REPORT_FILES:
        require(confined(root, BASE + '/delivery/' + name) in files, 'Missing pinned report output: ' + name)
    for path in confined(root, BASE).rglob('*'):
        require(not path.is_symlink(), 'Symlink in new phase tree is forbidden')
        if not path.is_file() or '__pycache__' in path.parts or path.suffix in ('.pyc', '.pyo', '.lock', '.log'):
            continue
        if (path.name == '_legacy_loop_source.txt' or
                (path.name == 'INPUT_RESTORATION_RECEIPT.json' and path not in files)):
            continue
        require(path.suffix.lower() in NEW_SUFFIXES, 'Unsupported phase payload: ' + str(path))
        if path.suffix.lower() in PRIOR_TEXT_SUFFIXES:
            require(re.search(rb'\blibfile_[0-9a-f]{32}\b', path.read_bytes()) is None,
                    'Private native file identifier is excluded from public payload: ' + path.relative_to(root).as_posix())
        files.add(path)
    ordered = sorted(files, key=lambda path: path.relative_to(root).as_posix())
    records = [pin(root, path) for path in ordered]
    require(len({item['path'] for item in records}) == len(records), 'Duplicate archive member path')
    require(workspace_bytes(root) + ARCHIVE_CAP_BYTES <= WORKSPACE_CAP_BYTES,
            'Prospective 200MiB archive reserve exceeds 8GiB project workspace cap')
    manifest = {'schema': 'SETI_GAMMA51_BURST4_NULL_COMPLETED_PACKAGE_V1',
        'status': 'SNAPSHOT_OF_EIGHT_COMPLETED_SYNTHETIC_FAMILIES_QA_AND_REPORT',
        'files': records, 'payload_files': len(records), 'scope': pin(root, scope_path),
        'root_GO': pin(root, go_path), 'job_receipts': receipts,
        'independent_QA': pin(root, qa_path), 'report_receipt': pin(root, report_path),
        'independent_QA_root_GO': pin(root, qa_go_path), 'QA_counts': qa['counts'],
        'primary_counts_sum': total_counts, 'primary_output_bytes': output_bytes,
        'archive_cap_bytes': ARCHIVE_CAP_BYTES, 'workspace_cap_bytes': WORKSPACE_CAP_BYTES,
        'phase_CPU_allocation_s': PHASE_CPU_ALLOCATION_S,
        'all_new_synthetic_arrays_included_as_opaque_bytes': True,
        'prior_real_HDF5_or_NPZ_copied': False, 'prior_real_references_text_only': True,
        'source_arrays_decoded_by_packager': False, 'detector_or_normalization_rerun': False,
        'synthetic_family_is_independent_astronomical_observation': False,
        'calibrated_telescope_SNR_FAP_or_sensitivity': False, 'qualified_SETI_detection': False,
        'gamma_model_empirical_rank_is_not_real_sky_FAP': True, 'cost_DKK': 0,
        'omitted_from_new_phase_tree': ['__pycache__', '*.pyc', '*.pyo', '*.lock', '*.log'],
        'manifest_self_identity': 'The external archive receipt binds the embedded manifest; no circular full-ZIP hash.'}
    return ordered, manifest


def publication_plan(root, manifest, archive_receipt):
    entries = []
    for declaration in manifest['files']:
        path = root / declaration['path']
        if path.suffix.lower() not in ('.py', '.json', '.md', '.txt', '.csv', '.png'):
            continue
        result = hashlib.sha1(('blob ' + str(declaration['bytes']) + '\0').encode('ascii'))
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024**2), b''):
                result.update(block)
        entries.append({**declaration, 'git_blob_sha': result.hexdigest(),
                        'encoding': 'base64' if path.suffix.lower() == '.png' else 'utf-8'})
    return {'schema': 'SETI_GAMMA51_BURST4_NULL_PUBLICATION_FILE_PLAN_V1',
        'status': 'METADATA_ONLY_NO_GIT_OPERATION', 'files': entries,
        'archive_identity': {key: archive_receipt[key] for key in
                             ('archive', 'bytes', 'sha256', 'payload_files', 'zip_members')},
        'NPZ_evidence': 'All new synthetic maps, audit/order capsules and winner raw inputs remain in the complete ZIP.',
        'prior_real_array_evidence': 'External, not included or decoded.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--scope-sha256')
    parser.add_argument('--script-sha256')
    parser.add_argument('--root-go', default=BASE + '/ROOT_GO.json')
    parser.add_argument('--root-go-sha256')
    parser.add_argument('--qa-receipt-sha256')
    parser.add_argument('--report-receipt-sha256')
    args = parser.parse_args()
    require(args.check_only != args.build, 'Choose exactly one of source-only --check-only or authorized --build')
    if args.check_only:
        print('PASS_SOURCE_ONLY_SYNTHETIC_PACKAGE_INTERFACE_NO_INPUTS_OPENED_NO_ARRAY_DECODING')
        return
    require(all(isinstance(value, str) and len(value) == 64 and
                all(character in '0123456789abcdef' for character in value) for value in
                (args.scope_sha256, args.script_sha256, args.root_go_sha256,
                 args.qa_receipt_sha256, args.report_receipt_sha256)), 'Five exact SHA256 arguments required')
    root = args.root.resolve()
    require(root.is_dir(), 'Existing project root required')
    output = root.parent / 'deliverables'
    archive, receipt_path, plan_path = (output / name for name in (ARCHIVE_NAME, RECEIPT_NAME, PLAN_NAME))
    require(not any(path.exists() or path.is_symlink() for path in (archive, receipt_path, plan_path)),
            'Create-only destinations exist; preserve previous completed or failed attempt')
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (RAM_CAP, RAM_CAP))
    def deadline(signum, frame):
        raise TimeoutError('Opaque-byte package wall cap900s reached')
    signal.signal(signal.SIGALRM, deadline)
    signal.alarm(WALL_CAP)
    started, cpu_started = time.monotonic(), time.process_time()
    created = False
    try:
        files, manifest = readiness(root, args)
        manifest_bytes = (json.dumps(manifest, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')
        output.mkdir(exist_ok=True)
        with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as handle:
            created = True
            for path in files:
                handle.write(path, path.relative_to(root).as_posix())
                require(handle.fp.tell() <= ARCHIVE_CAP_BYTES, '200MiB ZIP cap exceeded during build')
            handle.writestr(MANIFEST_NAME, manifest_bytes)
        require(archive.stat().st_size <= ARCHIVE_CAP_BYTES, 'Completed ZIP exceeds 200MiB cap')
        with zipfile.ZipFile(archive, 'r') as handle:
            require(handle.namelist() == [item['path'] for item in manifest['files']] + [MANIFEST_NAME],
                    'Exact archive member order/inventory differs')
            require(handle.testzip() is None, 'ZIP CRC readback failed')
            require(handle.read(MANIFEST_NAME) == manifest_bytes, 'Embedded manifest readback differs')
            for declaration in manifest['files']:
                require(handle.getinfo(declaration['path']).file_size == declaration['bytes'], 'Archive member size differs')
                result = hashlib.sha256()
                with handle.open(declaration['path']) as stream:
                    for block in iter(lambda: stream.read(1024**2), b''):
                        result.update(block)
                require(result.hexdigest() == declaration['sha256'], 'Archive member SHA256 differs: ' + declaration['path'])
        for declaration in manifest['files']:
            require(pin(root, root / declaration['path']) == declaration, 'Input changed while packaging')
        usage = {'CPU_seconds': time.process_time() - cpu_started,
                 'wall_seconds': time.monotonic() - started,
                 'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
        require(0 < usage['CPU_seconds'] <= CPU_CAP and 0 < usage['wall_seconds'] <= WALL_CAP and
                0 < usage['peak_RSS_bytes'] <= RAM_CAP, 'Archive completion resource bounds exceeded')
        receipt = {'schema': 'SETI_GAMMA51_BURST4_NULL_ARCHIVE_RECEIPT_V1',
            'status': 'PASS_COMPLETE_ZIP_CRC_AND_ALL_MEMBER_SHA256',
            'archive': str(archive), 'bytes': archive.stat().st_size, 'sha256': digest(archive),
            'payload_files': len(files), 'zip_members': len(files) + 1,
            'manifest_sha256': hashlib.sha256(manifest_bytes).hexdigest(),
            'all_members_CRC_verified': True, 'all_payload_member_SHA256_verified': True,
            'all_input_pins_unchanged_after_packaging': True,
            'scope_sha256': args.scope_sha256, 'root_GO_sha256': args.root_go_sha256,
            'qa_receipt_sha256': args.qa_receipt_sha256, 'report_receipt_sha256': args.report_receipt_sha256,
            'packaging_script_sha256': args.script_sha256, **usage,
            'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': RAM_CAP,
            'archive_cap_bytes': ARCHIVE_CAP_BYTES, 'prior_real_arrays_copied': False,
            'source_arrays_decoded': False, 'qualified_SETI_detection': False, 'cost_DKK': 0}
        create_json(plan_path, publication_plan(root, manifest, receipt))
        receipt['publication_plan'] = {'path': str(plan_path), 'bytes': plan_path.stat().st_size, 'sha256': digest(plan_path)}
        create_json(receipt_path, receipt)
        print(json.dumps(receipt))
    except BaseException as error:
        if created and not receipt_path.exists():
            create_json(receipt_path, {'schema': 'SETI_GAMMA51_BURST4_NULL_ARCHIVE_RECEIPT_V1',
                'status': 'INCOMPLETE_PRESERVED_NO_AUTOMATIC_RETRY', 'archive': str(archive),
                'failure_type': type(error).__name__, 'failure': str(error),
                'scope_sha256': args.scope_sha256, 'packaging_script_sha256': args.script_sha256,
                'CPU_seconds': time.process_time() - cpu_started,
                'wall_seconds': time.monotonic() - started})
        raise
    finally:
        signal.alarm(0)


if __name__ == '__main__':
    main()
