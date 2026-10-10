"""Prepare both boundary scopes from actual complete acquisition/source-QA JSON.

No scientific packages, HDF5 datasets, NPZ arrays, or HTTP operations are used.
This program refuses absent or non-PASS future receipts; scope creation is not
an acquisition/search permission and the driver still requires public freeze
readback, independent review, and root GO before scientific values.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


def pin(root, name):
    path = root / name
    if path.suffix.lower() in ('.h5', '.hdf5', '.npy', '.npz'):
        raise ValueError('Metadata-only scope preparation cannot pin power files')
    data = path.read_bytes()
    return {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve()
    name = 'analysis/s2017_next_native/boundaries/driver.py'
    spec = importlib.util.spec_from_file_location('s2017_boundary_scope_code_only', root / name)
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)
    qa = json.loads(driver.confined(root, driver.NEW_SOURCE_QA).read_bytes())
    driver.require(qa['schema'] == 'SETI_S2017_ADJACENT170_172_COMPACT_SOURCE_QA_V1'
        and qa['status'] == driver.NEW_SOURCE_QA_STATUS and qa['counts'] == driver.NEW_SOURCE_QA_COUNTS,
        'Actual complete new-source QA PASS required before scope preparation')
    prior = json.loads(driver.confined(root, driver.PRIOR_ACQUISITION).read_bytes())
    acquired = json.loads(driver.confined(root, driver.NEW_ACQUISITION).read_bytes())
    names = [name, 'analysis/s2017_next_native/boundaries/prepare_scopes.py',
        driver.NEW_SOURCE, driver.NEW_ACQUISITION, driver.NEW_SOURCE_QA, driver.NEW_SOURCE_QA_CODE,
        driver.NEW_ACQUISITION_SCOPE, driver.NEW_ACQUISITION_DRIVER, *driver.PRIOR_FIXED_PINS]
    code_paths = {'detector': driver.BASE + '/dependencies/detector.py',
        'gap': driver.BASE + '/dependencies/gap_search.py',
        'reader': driver.BASE + '/dependencies/standard_reader.py'}
    names.extend(code_paths.values())
    pins = {name: pin(root, name) for name in names}
    records = {str(chunk): [record for record in acquired['decoded_files']
                           if record['native_chunk_index'] == chunk] for chunk in (170, 172)}
    records['171'] = [{**record, 'native_chunk_index': 171} for record in prior['decoded_files']]
    directories = {'170': driver.NEW_ACQUISITION.rsplit('/', 1)[0],
        '172': driver.NEW_ACQUISITION.rsplit('/', 1)[0], '171': driver.PRIOR_ACQUISITION.rsplit('/', 1)[0]}
    scope_directory = root / driver.BASE / 'scopes'
    driver.require(not any((scope_directory / (pair + '.json')).exists() for pair in driver.PAIRS),
                   'Frozen scopes must never be replaced')
    scopes = {}
    for pair, chunks in driver.PAIRS.items():
        scope = {'schema': 'SETI_S2017_TWO_NEW_JOINED_BOUNDARIES_V1', 'pair_id': pair,
            'source_chunk_ids': list(chunks), 'native_channel_count': driver.COUNT,
            'joined_channel_count': driver.JOINED, 'source_channel0': chunks[0] * driver.COUNT,
            'joined_reference_core_q': list(driver.QS), 'native_reference_cores': [[chunks[0], 255], [chunks[1], 0]],
            'rows_per_scan': 16, 'scan_order': list(driver.SCANS), 'origin_scan_order': list(driver.ONS),
            'fch1_hz': driver.FCH1, 'df_hz': driver.DF, 'tsamp_s': driver.TSAMP,
            'drift_grid': {'first_hz_s': -4, 'last_hz_s': 4, 'count': 785},
            'widths_channels': [1, 3], 'valid_hypotheses_per_carrier': 1570,
            'core_channel_count': driver.CORE, 'crop_halo_channels': driver.HALO,
            'expected_ON_maps': 6, 'carriers_per_ON': 8192, 'expected_fixed_profiles': 9,
            'rank_count_per_ON': 20, 'display_suppression_channels': 3,
            'top20_selection_domain': 'both joined boundary reference cores, separately for each ON',
            'fixed_profile_ranks_per_ON': 3, 'profile_halfwidth_channels': 64, 'profile_shift_channels': 0,
            'joined_profile_normalization': driver.JOINED_NORM,
            'CPU_cap_s': driver.CPU_CAP, 'wall_cap_s': driver.WALL_CAP, 'memory_cap_bytes': driver.MEMORY_CAP,
            'memory_cap_bytes_aggregate': driver.AGGREGATE_MEMORY_CAP, 'science_jobs_max': driver.MAX_SCIENCE_JOBS,
            'shared_family_lock': driver.SOURCE_LOCK, 'shared_science_slot_locks': list(driver.SCIENCE_LOCKS),
            'output_stage': driver.STAGE + '/' + pair + '/measurement',
            'runtime_package_versions': driver.VERSIONS, 'hdf5_version': '1.14.6',
            'new_telescope_HTTP_requests': 0, 'new_telescope_BODY_bytes': 0, 'cost_DKK': 0,
            'previous_native171_safe_interiors_rerun': False,
            'previously_searched_native171_reference_interval_half_open':
                [171 * driver.COUNT + driver.CORE, 172 * driver.COUNT - driver.CORE],
            'retry_resume_or_rerun_authorized': False, 'old_protected_native_chunks_not_read': [156, 159],
            'original_receipts_scopes_or_statuses_modified': False, 'one_historical_visit': True,
            'independent_or_blind_validation': False, 'OFF_veto_applied': False,
            'qualified_SETI_detection': False, 'calibrated_SNR_FAP': False,
            'original_A_B_status': 'FAIL_CLOSED_UNCHANGED', 'driver_sha256': pins[name]['sha256'],
            'unchanged_dependency_SHA256s': driver.DEPENDENCY_SHAS, 'code_paths': code_paths,
            'pinned_metadata_code_and_prerequisites': pins,
            'compact_records_by_native_chunk': records, 'compact_directories_by_native_chunk': directories,
            'new_source_QA': {'path': driver.NEW_SOURCE_QA, 'status': driver.NEW_SOURCE_QA_STATUS,
                'expected_acquisition_receipt_sha256': pins[driver.NEW_ACQUISITION]['sha256'],
                'expected_source_manifest_sha256': pins[driver.NEW_SOURCE]['sha256']},
            'expected_counts': {'maps': 6, 'carrier_maximum_records': 24576,
                'correlated_drift_width_combinations': 38584320, 'top20_entries': 60,
                'patches': 9, 'scan_profiles': 54, 'raw_patch_cell_occurrences': 111456,
                'native_compact_files': 12, 'native_decoded_rows': 192},
            'limitations': ['All six scans are the same2017-04-28 visit; frequency chunks and administrative jobs are not independent visits.',
                'Only previously unsearched reference-carrier boundary cores are added; drift/crop halos overlap prior source channels.',
                'Both joined-native rawfloat32 channels contribute to profile row medians; these means differ from native-only normalization.',
                'Top20 and top3 profiles are selected on the same ON data; robust scores and positive half-window signs are not calibrated significance.',
                'Exact OFF tracks are descriptive; a small frozen OFF value does not establish absence of nearby OFF structure.',
                'Whole original source-file MD5 remains unverified; received compressed pieces, compact files and all decoded rows are authenticated.',
                'No protected2016native156/159 values, historical rerun, qualified OFF veto, physical-origin classification, FAP, flux/EIRP or sensitivity.']}
        driver.contract(root, scope)
        scopes[pair] = scope
    scope_directory.mkdir(parents=True, exist_ok=True)
    for pair, scope in scopes.items():
        driver.save(scope_directory / (pair + '.json'), scope)
    receipt = {'schema': 'SETI_S2017_TWO_JOINED_BOUNDARY_SCOPES_PREPARATION_V1',
        'status': 'PASS_ACTUAL_ACQUISITION_SOURCE_QA_AND_METADATA_ONLY_SCOPE_PREPARATION',
        'driver_sha256': pins[name]['sha256'], 'new_acquisition_receipt_sha256': pins[driver.NEW_ACQUISITION]['sha256'],
        'new_source_QA_receipt_sha256': pins[driver.NEW_SOURCE_QA]['sha256'],
        'source_manifest_sha256': pins[driver.NEW_SOURCE]['sha256'],
        'scope_pins': {pair: pin(root, driver.BASE + '/scopes/' + pair + '.json') for pair in scopes},
        'expected_total_maps': 12, 'expected_total_fixed_profiles': 18,
        'scientific_values_opened': False, 'HTTP_requests': 0, 'scope_creation_is_root_science_GO': False}
    driver.save(root / driver.BASE / 'SCOPES_PREPARATION_RECEIPT.json', receipt)
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
