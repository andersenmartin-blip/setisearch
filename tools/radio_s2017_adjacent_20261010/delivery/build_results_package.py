"""Create/verify adjacent170/172 RESULTS after eight complete jobs/actual QA.

Requires an actual completion-admission JSON, its SHA, source-QA pins and root GO.
No HTTP, detector rerun, raw power decode, sidecar deletion or remote-save claim.
"""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import re
import signal
import time
import zipfile
import archive_common as common
from reconstruct_raw_sidecars import MANIFEST_SHA, STAGE, contract, verify_compacts

PHASE = Path('analysis/s2017_next_native')
DELIVERY = PHASE / 'delivery'
EXECUTION_CONTROL = Path('analysis/s2017_next_native_execution')
SAFE_STATUS = 'COMPLETE_S2017_ADJACENT_NATIVE_SAFE_INTERIOR_JOB_EXPLORATORY_ONLY'
BOUNDARY_STATUS = 'COMPLETE_S2017_TWO_NEW_JOINED_CORES_SIX_ON_MAPS_NINE_FIXED_PROFILES_EXPLORATORY_ONLY'
SAFE_JOBS = tuple('native%d_batch%02d' % (n, b) for n in (170, 172) for b in (1, 2, 3))
PAIRS = ('pair170_171', 'pair171_172')
AUXILIARY_RECEIPT = (PHASE / 'review/AUXILIARY_FILE_QUARANTINE_RECEIPT.json').as_posix()
AUXILIARY_RECEIPT_SHA = '099a1db266f5a9e1a7bda8c4c63cb613a0cfe69932da081e8c92ca16627a1c71'
QA_EXPECTED = {'interior': (1524, 54, 668736), 'boundary': (12, 18, 222912),
               'combined': (1536, 72, 891648)}
QA_CONTRACTS = {
    'interior': ('analysis/s2017_next_native/results/search/review/QA_RECEIPT.json',
        'SETI_S2017_ADJACENT_SIX_INTERIOR_JOBS_SAVED_OUTPUT_SOURCE_QA_V1',
        'PASS1524_S2017_ADJACENT_MAPS54_FIXED_PROFILES_AND668736_BITWISE_SOURCE_CELLS'),
    'boundary': ('analysis/s2017_next_native/boundaries/results/review/QA_RECEIPT.json',
        'SETI_S2017_TWO_JOINED_BOUNDARIES_SAVED_OUTPUT_AND_FULL_SOURCE_QA_V1',
        'PASS12_S2017_JOINED_MAPS18_FIXED_PROFILES192_JOINED_MEDIANS_AND222912_BITWISE_SOURCE_CELLS')}
QA_COUNTS = {
    'interior': {'batch_families': 6, 'maps': 1524, 'map_normalization_records': 1524,
        'carrier_maximum_records': 6242304, 'valid_hypothesis_records': 9800417280,
        'top20_entries': 360, 'patches': 54, 'scan_profiles': 324, 'time_row_occurrences': 5184,
        'retained_raw_patch_cells': 668736, 'compact_files': 12, 'decoded_rows': 192,
        'native_full_row_medians_recomputed': 192, 'ON_core_row_medians_recomputed': 24384,
        'raw_cells_bitwise_checked': 668736},
    'boundary': {'pair_families': 2, 'maps': 12, 'map_normalization_records': 12,
        'carrier_maximum_records': 49152, 'valid_hypothesis_records': 77168640,
        'top20_entries': 120, 'patches': 18, 'scan_profiles': 108, 'time_row_occurrences': 1728,
        'retained_raw_patch_cells': 222912, 'distinct_compact_files': 18, 'distinct_decoded_rows': 288,
        'search_compact_file_occurrences': 24, 'search_decoded_row_occurrences': 384,
        'joined_full_float32_row_median_occurrences_recomputed': 192,
        'ON_core_float64_row_medians_recomputed': 192, 'raw_cells_bitwise_checked': 222912}}
SOURCE_QA_COUNTS = {'native_chunks': 2, 'compact_files': 12, 'source_headers': 12,
    'source_descriptors': 192, 'exact_range_records': 192, 'unique_source_ranges': 192,
    'durable_raw_sidecars': 192, 'compressed_source_chunks': 192, 'decoded_rows': 192}


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=True, allow_nan=False).encode('utf8')).hexdigest()


def merge_pins(merged, incoming):
    common.require(isinstance(incoming, dict) and bool(incoming), 'Nonempty actual QA byte pins required')
    for name, expected in incoming.items():
        common.require(isinstance(name, str) and name == Path(name).as_posix()
                       and not Path(name).is_absolute() and '..' not in Path(name).parts
                       and '\\' not in name and bool(name), 'Canonical root-relative POSIX QA pin required')
        common.require(set(expected) == {'bytes', 'sha256'} and type(expected['bytes']) is int
                       and expected['bytes'] >= 0 and re.fullmatch('[0-9a-f]{64}', expected['sha256']),
                       'Actual QA byte-pin schema differs')
        common.require(name not in merged or merged[name] == expected, 'Conflicting actual QA byte pins')
        merged[name] = expected


def authenticate_pins(root, expected_pins):
    for relative, expected in expected_pins.items():
        common.require(common.pin(root, relative) == {'path': relative, **expected},
                       'Current file differs from empirical QA bytes: ' + relative)


def source_qa_contract(root, qa, acquisition, acquisition_sha, source_qa_sha):
    common.require(qa['schema'] == 'SETI_S2017_ADJACENT170_172_COMPACT_SOURCE_QA_V1'
        and qa['status'] == 'PASS_ADJACENT170_172_12_COMPACTS192_COMPRESSED_CHUNKS192_DECODED_ROWS_AND_SOURCE_RANGE_PROVENANCE'
        and qa['counts'] == SOURCE_QA_COUNTS and qa['acquisition_receipt_sha256'] == acquisition_sha
        and qa['source_manifest_sha256'] == MANIFEST_SHA
        and qa['qa_script_sha256'] == common.digest(root / PHASE / 'qa_sources.py')
        and qa['scope_sha256'] == acquisition['scope_sha256']
        and qa['driver_sha256'] == acquisition['driver_sha256']
        and qa['public_freeze_commit'] == acquisition['public_freeze_commit']
        and qa['new_telescope_HTTP_requests'] == qa['new_telescope_BODY_bytes'] == 0
        and qa['detector_or_score_rerun'] is False and qa['medians_recomputed'] is False,
        'Actual source QA full provenance contract differs')
    for qa_field, acq_field in (
        ('source_range_raw_record_sha256', 'raw_range_records'),
        ('decoded_file_row_record_sha256', 'decoded_files'),
        ('source_range_request_record_sha256', 'value_read_requests')):
        common.require(qa[qa_field] == canonical_sha(acquisition[acq_field]),
                       'Source QA canonical acquisition-record pin differs')
    compact_pins = {(STAGE / x['array_file']).as_posix():
                    {'bytes': x['bytes'], 'sha256': x['file_sha256']}
                    for x in acquisition['decoded_files']}
    common.require(qa['compact_input_byte_pins'] == compact_pins, 'Source QA exact12 compact pins differ')
    common.require(common.digest(root / PHASE / 'results/source_review/QA_RECEIPT.json') == source_qa_sha,
                   'Actual source QA receipt changed')
    return compact_pins


def actual_json(root, item):
    path = common.confined(root, item['path'])
    common.require(common.digest(path) == item['sha256'], 'Actual receipt pin differs')
    return json.loads(path.read_bytes())


def main():
    started = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'admission', 'expected-admission-sha256', 'acquisition-sha256', 'source-qa-sha256', 'freeze-commit'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--root-go-after-all-jobs-and-actual-qa', action='store_true')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    common.require(args.root_go_after_all_jobs_and_actual_qa,
                   'Root GO after eight completions and actual empirical QA required')
    for value in (args.expected_admission_sha256, args.acquisition_sha256, args.source_qa_sha256):
        common.require(re.fullmatch('[0-9a-f]{64}', value), 'Actual SHA256 arguments required')
    common.require(re.fullmatch('[0-9a-f]{40}', args.freeze_commit), 'Actual public40-hex delivery freeze required')
    admission_path = common.confined(root, args.admission)
    common.require(common.digest(admission_path) == args.expected_admission_sha256, 'Admission pin differs')
    admission = json.loads(admission_path.read_bytes())
    common.require(admission['schema'] == 'SETI_ADJACENT170_172_RESULTS_ACTUAL_COMPLETION_ADMISSION_V1'
                   and admission['acquisition_receipt_sha256'] == args.acquisition_sha256
                   and admission['source_QA_receipt_sha256'] == args.source_qa_sha256
                   and admission['source_manifest_sha256'] == MANIFEST_SHA,
                   'Results actual completion contract differs')
    for relative, expected in admission['code_pins'].items():
        common.require(common.pin(root, relative) == {'path': relative, **expected}, 'Results builder code pin differs')
    common.require(set(admission['code_pins']) == {
        (DELIVERY / 'build_results_package.py').as_posix(),
        (DELIVERY / 'archive_common.py').as_posix(),
        (DELIVERY / 'reconstruct_raw_sidecars.py').as_posix()}, 'Exact three builder pins required')
    source_qa_path = PHASE / 'results/source_review/QA_RECEIPT.json'
    source_qa = actual_json(root, {'path': source_qa_path.as_posix(), 'sha256': args.source_qa_sha256})
    acquisition, source_manifest = contract(root, args.acquisition_sha256)
    authenticated_pins = source_qa_contract(root, source_qa, acquisition,
                                           args.acquisition_sha256, args.source_qa_sha256)
    safe = admission['safe_receipts']
    boundary = admission['boundary_receipts']
    common.require([x['path'] for x in safe] == [
        (PHASE / 'results/search' / job / 'EXECUTION_RECEIPT.json').as_posix() for job in SAFE_JOBS],
        'Exact six distinct ordered safe jobs required')
    common.require([x['path'] for x in boundary] == [
        (PHASE / 'boundaries/results' / pair / 'measurement/EXECUTION_RECEIPT.json').as_posix()
        for pair in PAIRS], 'Exact two distinct ordered boundary jobs required')
    safe_values, boundary_values = {}, {}
    for job, item in zip(SAFE_JOBS, safe):
        receipt = actual_json(root, item)
        common.require(receipt['status'] == SAFE_STATUS and
                       receipt['job_id'] == job and
                       receipt['acquisition_receipt_sha256'] == args.acquisition_sha256 and
                       receipt['source_QA_receipt_sha256'] == args.source_qa_sha256 and
                       receipt['new_telescope_HTTP_requests'] == receipt['new_telescope_BODY_bytes'] == 0 and
                       receipt['search_summary']['completed_ON_maps'] == (252 if job.endswith('batch03') else 255) and
                       receipt['fixed_profile_summary']['profile_count'] == 9,
                       'Interior receipt is not actual complete new source job')
        safe_values[job] = receipt
    common.require(sum(x['search_summary']['completed_ON_maps'] for x in safe_values.values()) == 1524,
                   'Actual six-job interior map count differs')
    for pair, item in zip(PAIRS, boundary):
        receipt = actual_json(root, item)
        common.require(receipt['status'] == BOUNDARY_STATUS and
                       receipt['pair_id'] == pair and
                       receipt['new_acquisition_receipt_sha256'] == args.acquisition_sha256 and
                       receipt['new_source_QA_receipt_sha256'] == args.source_qa_sha256 and
                       receipt['new_telescope_HTTP_requests'] == receipt['new_telescope_BODY_bytes'] == 0 and
                       receipt['search_summary']['completed_ON_maps'] == 6 and
                       receipt['fixed_profile_summary']['profile_count'] == 9,
                       'Boundary receipt is not actual complete six-map/nine-profile job')
        boundary_values[pair] = receipt
    kinds = [x['kind'] for x in admission['actual_QA_receipts']]
    common.require(kinds == ['interior', 'boundary'],
                   'Actual QA must cover all interiors and both boundaries')
    for item in admission['actual_QA_receipts']:
        qa = actual_json(root, item)
        qa_path, qa_schema, qa_status = QA_CONTRACTS[item['kind']]
        common.require(item['path'] == qa_path and item['expected_status'] == qa_status and
                       qa['schema'] == qa_schema and qa['status'] == qa_status and
                       qa['detector_or_score_rerun'] is False and
                       qa['fixed_track_optimization_applied'] is False and
                       qa['new_telescope_HTTP_requests'] == qa['new_telescope_BODY_bytes'] == 0,
                       'Actual saved-source QA PASS required')
        common.require(qa['counts'] == QA_COUNTS[item['kind']],
                       'Actual empirical QA map/profile/bitwise-cell counts differ')
        interior = item['kind'] == 'interior'
        values, names, actual_items = ((safe_values, SAFE_JOBS, safe) if interior
                                      else (boundary_values, PAIRS, boundary))
        qa_code = (PHASE / ('search' if interior else 'boundaries') / 'qa_saved_outputs.py').as_posix()
        common.require(qa['qa_script_sha256'] == common.digest(root / qa_code),
                       'Actual empirical QA script bytes changed')
        receipt_key = 'search_receipt_SHA256s' if interior else 'pair_execution_receipt_SHA256s'
        common.require(qa[receipt_key] == {name: x['sha256'] for name, x in zip(names, actual_items)}
                       and qa['scope_SHA256s'] == {name: values[name]['scope_sha256'] for name in names},
                       'Actual QA exact execution/scope dictionaries differ')
        freeze_key = 'public_freeze_commit' if interior else 'search_public_freeze_commit'
        common.require(all(values[name]['public_freeze_commit'] == qa[freeze_key]
                           and values[name]['driver_sha256'] == qa['driver_sha256'] for name in names),
                       'Actual QA science driver/freeze identity differs')
        common.require(re.fullmatch('[0-9a-f]{40}', qa['qa_public_freeze_commit']),
                       'Actual QA public freeze identity missing')
        if interior:
            gates = qa['prerequisites']
            common.require(gates['acquisition']['path'] == (STAGE / 'ACQUISITION_RESULT.json').as_posix()
                and gates['acquisition']['sha256'] == args.acquisition_sha256
                and gates['source_QA']['path'] == source_qa_path.as_posix()
                and gates['source_QA']['sha256'] == args.source_qa_sha256,
                'Actual interior QA source/acquisition prerequisite pins differ')
        else:
            common.require(qa['new_acquisition_receipt_sha256'] == args.acquisition_sha256
                and qa['new_source_QA_receipt_sha256'] == args.source_qa_sha256
                and all(values[name]['prior171_source_QA_receipt_sha256'] ==
                        qa['prior171_source_QA_receipt_sha256'] for name in names),
                'Actual boundary QA new/prior source provenance differs')
        qa_pins = qa['all_input_byte_pins']
        merge_pins(authenticated_pins, qa_pins)
        for name, x in zip(names, actual_items):
            scope_path = (PHASE / ('search' if interior else 'boundaries') /
                          'scopes' / (name + '.json')).as_posix()
            common.require(qa_pins[x['path']]['sha256'] == x['sha256']
                and qa_pins[scope_path]['sha256'] == values[name]['scope_sha256'],
                'Actual QA byte inventory omits execution/scope identity')
        driver_path = (PHASE / ('search' if interior else 'boundaries') / 'driver.py').as_posix()
        common.require(qa_pins[driver_path]['sha256'] == qa['driver_sha256']
            and qa_pins[(STAGE / 'ACQUISITION_RESULT.json').as_posix()]['sha256'] == args.acquisition_sha256
            and qa_pins[source_qa_path.as_posix()]['sha256'] == args.source_qa_sha256,
            'Actual QA byte inventory omits driver/source/acquisition identity')
        own_pin = common.pin(root, qa_code)
        merge_pins(authenticated_pins, {qa_code: {key: own_pin[key] for key in ('bytes', 'sha256')}})
    # Receipts/admission/engineering code are exact-byte roots for the audited
    # inventories. They are also checked after package construction.
    roots = safe + boundary + admission['actual_QA_receipts'] + [
        {'path': admission_path.relative_to(root).as_posix(), 'sha256': args.expected_admission_sha256},
        {'path': source_qa_path.as_posix(), 'sha256': args.source_qa_sha256},
        {'path': AUXILIARY_RECEIPT, 'sha256': AUXILIARY_RECEIPT_SHA}]
    for item in roots:
        observed = common.pin(root, item['path'])
        common.require(observed['sha256'] == item['sha256'], 'Actual admission/receipt root changed')
        merge_pins(authenticated_pins, {item['path']: {key: observed[key] for key in ('bytes', 'sha256')}})
    merge_pins(authenticated_pins, admission['code_pins'])
    raw_receipt = actual_json(root, admission['raw_package_receipt'])
    common.require(raw_receipt['status'] == 'PASS_ARCHIVE_CRC_AND_ALL_MEMBER_SHA256' and
                   raw_receipt['kind'] == 'RAW' and
                   raw_receipt['context']['acquisition_receipt_sha256'] == args.acquisition_sha256 and
                   raw_receipt['context']['source_QA_receipt_sha256'] == args.source_qa_sha256 and
                   raw_receipt['new_HTTP_requests'] == raw_receipt['new_decoded_power_rows'] ==
                   raw_receipt['new_detector_or_measurement_runs'] == 0,
                   'Verified new RAW archive receipt required')
    # The root's confirmed remote-save/removal record is receipt-only. This code
    # performs no deletion and never treats a prospective save as actual.
    retention = actual_json(root, admission['root_retention_receipt'])
    common.require(retention['status'] == 'COMPLETE_ROOT_ONLY192_REDUNDANT_SIDECARS_REMOVED_AFTER_DURABLE_RAW_SAVE'
                   and retention['raw_archive_sha256'] == raw_receipt['archive_sha256']
                   and retention['acquisition_receipt_sha256'] == args.acquisition_sha256
                   and retention['source_QA_receipt_sha256'] == args.source_qa_sha256
                   and retention['sidecars_removed'] == 192 and retention['durable_RAW_save_confirmed'] is True
                   and retention['compressed_H5_chunks_verified'] == 192,
                   'Root actual durable-save/retention receipt required')
    for item in (admission['raw_package_receipt'], admission['root_retention_receipt']):
        observed = common.pin(root, item['path'])
        common.require(observed['sha256'] == item['sha256'], 'Durability/archive receipt changed')
        merge_pins(authenticated_pins, {item['path']: {key: observed[key] for key in ('bytes', 'sha256')}})
    merge_pins(authenticated_pins, admission['external_reference_file_pins'])
    common.limits(started)
    locks = []
    try:
        for relative in (PHASE / 'ACTIVE_FAMILY_FLOCK.lock', DELIVERY / 'ARCHIVE_ACTIVE_FLOCK.lock'):
            handle = (root / relative).open('a+')
            locks.append(handle)
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Hash authentication is a byte read, never an H5 dataset decode or
        # detector invocation. The caps and retained family lock cover it.
        authenticate_pins(root, authenticated_pins)
        verify_compacts(root, args.acquisition_sha256)
        for item in acquisition['raw_range_records']:
            common.require(not (root / STAGE / item['path']).exists(), 'Redundant sidecar still exists')
        payload = set()
        allowed = {'.py', '.json', '.md', '.txt', '.csv', '.log', '.npz', '.png', '.gz'}
        for path in (root / PHASE).rglob('*'):
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            if '__pycache__' in relative.parts or 'packages' in relative.parts or 'raw_ranges' in relative.parts:
                continue
            if path.name == 'DATA_PACKAGES.json':
                continue  # final external ZIP identity is never self-embedded
            if path.suffix in allowed:
                payload.add(relative.as_posix())
        # Copy QA-authenticated code/output and external text provenance. Keep
        # H5 and exact pinned cached HDF5 metadata bins in durable RAW packages.
        text_only = {'.py', '.json', '.md', '.txt', '.csv', '.log'}
        omitted_cached_metadata_pins = {}
        for relative in authenticated_pins:
            path = Path(relative)
            if path.suffix.lower() in ('.h5', '.hdf5'):
                continue
            common.require('raw_ranges' not in path.parts and path.name != 'DATA_PACKAGES.json'
                           and 'packages' not in path.parts,
                           'QA-authenticated scientific input unexpectedly points to excluded package/raw payload')
            if path.suffix.lower() == '.bin':
                common.require(relative in source_manifest['code_and_metadata_pins'] and
                               source_manifest['code_and_metadata_pins'][relative] == authenticated_pins[relative],
                               'Binary metadata omission lacks exact frozen source-manifest pin')
                omitted_cached_metadata_pins[relative] = authenticated_pins[relative]
                continue
            if path.is_relative_to(PHASE):
                common.require(path.suffix in allowed, 'Unexpected scientific output payload type')
            else:
                common.require(path.suffix in text_only, 'External QA provenance must be text/code only')
            payload.add(relative)
        for relative, expected in admission['external_reference_file_pins'].items():
            common.require(Path(relative).suffix in text_only and
                           'raw_ranges' not in Path(relative).parts,
                           'Only source identity/runtime/code references allowed externally')
            common.require(common.pin(root, relative) == {'path': relative, **expected},
                           'External171/runtime reference file pin differs')
            payload.add(relative)
        # Execution-control receipts/logs live beside this phase so they could
        # not race RAW's snapshot. Final admission must pin every retained text.
        common.require((root / EXECUTION_CONTROL).is_dir(), 'Sibling execution-control archive references required')
        execution_control_files = set()
        for path in (root / EXECUTION_CONTROL).rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts or path.suffix == '.lock':
                continue
            relative = path.relative_to(root).as_posix()
            common.require(path.suffix in text_only and
                           relative in admission['external_reference_file_pins'],
                           'Every sibling execution-control text/log needs explicit final admission pin')
            execution_control_files.add(relative)
            payload.add(relative)
        common.require((EXECUTION_CONTROL / 'run_six_jobs.py').as_posix() in execution_control_files and
                       (EXECUTION_CONTROL / 'run_wave_once.py').as_posix() in execution_control_files and
                       (EXECUTION_CONTROL / 'preflight/SIX_CHECK_ONLY_RECEIPT.json').as_posix() in execution_control_files,
                       'Execution-control code and actual preflight omitted')
        common.require('analysis/new_visit_recovery/results/acquire/ACQUISITION_RESULT.json' in payload
                       and 'analysis/runtime/EXACT_DEPENDENCY_RESTORATION.json' in payload,
                       'Prior171 H5 identity receipt and exact runtime receipt required')
        common.require(not any(Path(x).suffix in ('.h5', '.whl', '.zip', '.bin') for x in payload),
                       'RESULTS must not duplicate source H5/raw bodies/wheels/ZIPs')
        common.require(all(x in authenticated_pins for x in payload if Path(x).suffix == '.npz'),
                       'Every scientific NPZ payload must belong to actual empirical QA byte pins')
        for item in safe + boundary + admission['actual_QA_receipts']:
            common.require(item['path'] in payload, 'Required actual completion/QA missing from payload')
        common.require(admission_path.relative_to(root).as_posix() in payload, 'Actual admission omitted')
        common.require(AUXILIARY_RECEIPT in payload, 'Supplemental unknown-origin auxiliary preservation receipt omitted')
        context = {'admission_sha256': args.expected_admission_sha256,
                   'public_freeze_commit': args.freeze_commit,
                   'acquisition_receipt_sha256': args.acquisition_sha256,
                   'source_QA_receipt_sha256': args.source_qa_sha256,
                   'new_safe_jobs': 6, 'new_boundary_jobs': 2, 'actual_maps': 1536,
                   'actual_fixed_profiles': 72, 'raw_archive_sha256': raw_receipt['archive_sha256'],
                   'empirical_QA_authenticated_input_files': len(authenticated_pins),
                   'empirical_QA_input_union_sha256': canonical_sha(authenticated_pins),
                   'explicit_execution_control_reference_files': sorted(execution_control_files),
                   'authenticated_cached_metadata_references_omitted_because_RAW_preserves_them': omitted_cached_metadata_pins,
                   'omitted_cached_metadata_reference_count': len(omitted_cached_metadata_pins),
                   'omitted_cached_metadata_reference_bytes': sum(x['bytes'] for x in omitted_cached_metadata_pins.values()),
                   'omitted_cached_metadata_reference_sha256': canonical_sha(omitted_cached_metadata_pins),
                   'old171_H5_or_wheels_copied': False, 'raw_sidecars_copied': False,
                   'prior171_source_inputs_are_external_identity_references': True}
        receipt = common.assemble(root, root / DELIVERY / 'packages/results',
                                  admission['archive_filename'], payload, 'RESULTS', context, started)
        # Common assembly proves every member equals its embedded manifest.
        # Compare those exact member identities to the empirical QA pins, so
        # an altered file cannot be repinned by package preparation.
        with zipfile.ZipFile(root / receipt['archive_path'], 'r') as archive:
            packaged_manifest = json.loads(archive.read('PACKAGE_MANIFEST.json'))
        member_pins = {x['path']: {'bytes': x['bytes'], 'sha256': x['sha256']}
                       for x in packaged_manifest['files']}
        for relative, expected in authenticated_pins.items():
            if relative in payload:
                common.require(member_pins[relative] == expected,
                               'Packaged member differs from empirical QA bytes: ' + relative)
        authenticate_pins(root, authenticated_pins)
        final_use = common.measured(started)
        common.require(final_use['process_CPU_seconds_including_imports'] <= common.CPU_CAP and
                       final_use['wall_seconds_including_imports'] <= common.WALL_CAP and
                       final_use['peak_RSS_bytes'] <= common.MEMORY_CAP,
                       'Final empirical-QA package-admission cap exceeded')
        receipt.update(final_use, packaged_empirical_QA_byte_pins_verified=True,
                       packaged_empirical_QA_byte_pin_count=sum(x in payload for x in authenticated_pins))
        common.save_new(root / DELIVERY / 'RESULTS_PACKAGE_RECEIPT.json', receipt)
        print(json.dumps(receipt), flush=True)
    except BaseException as error:
        package_stage = root / DELIVERY / 'packages/results'
        failure = package_stage / 'RESULTS_ADMISSION_FAILURE_RECEIPT.json'
        if package_stage.is_dir() and not failure.exists():
            common.save_new(failure, {'status': 'INCOMPLETE_RESULTS_ADMISSION_PRESERVE_NO_RETRY_NO_OVERWRITE',
                'public_freeze_commit': args.freeze_commit, 'error_type': type(error).__name__,
                'error': str(error), 'new_HTTP_requests': 0, 'source_payloads_deleted': False,
                **common.measured(started)})
        raise
    finally:
        signal.alarm(0)
        for handle in reversed(locks):
            handle.close()


if __name__ == '__main__':
    main()
