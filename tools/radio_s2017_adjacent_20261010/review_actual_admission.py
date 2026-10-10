#!/usr/bin/env python3
"""Read-only metadata/opaque-byte admission of all eight completed search jobs.

No HDF5/NPZ parsing, network, detector execution or signal interpretation.
Root supplies exact public scope and actual receipt hashes in a saved pin file.
Full saved-map rank reconstruction, medians and bitwise source-cell arithmetic
remain explicitly deferred to the two independent empirical output QA scripts.
"""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re

BASE = 'analysis/s2017_next_native'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
ONS = SCANS[::2]
NATIVE, CORE = 1048576, 4096
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
PARTITIONS = {'batch01': list(range(1, 86)), 'batch02': list(range(86, 171)), 'batch03': list(range(171, 255))}
JOBS = {f'native{native}_{batch}': {'kind': 'interior', 'native': native, 'batch': batch, 'qs': qs}
    for native in (170, 172) for batch, qs in PARTITIONS.items()}
JOBS.update({'pair170_171': {'kind': 'boundary', 'chunks': [170, 171], 'qs': [255, 256]},
    'pair171_172': {'kind': 'boundary', 'chunks': [171, 172], 'qs': [255, 256]}})
VERSIONS = {'numpy': '2.3.5', 'scipy': '1.17.0', 'h5py': '3.15.1', 'hdf5plugin': '7.1.0', 'HDF5': '1.14.6'}
SOURCE_SHA = '2a09dcd018e83e822cf19cb088e4f35469e8b160cbcde69f0428e64544ad7909'
PUBLIC_READBACK = BASE + '/publication/SCIENCE_RAW_FREEZE_READBACK_RECEIPT.json'
PUBLIC_READBACK_SHA = '4da07747c4af2c8057c287ee1fd6246ae21ac2e949021fd784ef27e5de97e44b'
PUBLIC_36_SORTED_PATHS_SHA = '050a36d0aa89f238714f1c38f8b56efb381d375e5b29fb8aaf7a910b383363fc'
SOURCE_QA_STATUS = 'PASS_ADJACENT170_172_12_COMPACTS192_COMPRESSED_CHUNKS192_DECODED_ROWS_AND_SOURCE_RANGE_PROVENANCE'
SOURCE_QA_COUNTS = {'native_chunks': 2, 'compact_files': 12, 'source_headers': 12, 'source_descriptors': 192,
    'exact_range_records': 192, 'unique_source_ranges': 192, 'durable_raw_sidecars': 192,
    'compressed_source_chunks': 192, 'decoded_rows': 192}


def check(condition, message):
    if not condition:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as handle:
        for block in iter(lambda: handle.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def unique_pairs(items):
    result = {}
    for key, value in items:
        check(key not in result, 'Duplicate JSON field')
        result[key] = value
    return result


def confined(root, name):
    p = Path(name)
    check(not p.is_absolute() and '..' not in p.parts, 'Relative confined path required')
    path = root / p
    check(path.resolve().is_relative_to(root) and not path.is_symlink(), 'Path escapes frozen workspace or is symlink')
    return path


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=True, allow_nan=False).encode('ascii')).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'pins', 'expected-pins-sha256'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args(); root = Path(args.root).resolve(); pins = {}

    def pin(path, expected=None):
        relative = path.relative_to(root).as_posix()
        observed = {'sha256': digest(path), 'bytes': path.stat().st_size}
        check(expected is None or observed == expected, 'Opaque byte identity differs: ' + relative)
        check(relative not in pins or pins[relative] == observed, 'File changed during admission: ' + relative)
        pins[relative] = observed
        return observed

    def read(name, expected_sha=None):
        path = confined(root, name); check(path.suffix == '.json', 'Only JSON metadata may be decoded')
        raw = path.read_bytes(); observed = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        check(expected_sha is None or observed['sha256'] == expected_sha, 'Root-reviewed JSON SHA differs: ' + name)
        check(name not in pins or pins[name] == observed, 'Metadata changed during admission: ' + name)
        pins[name] = observed
        return json.loads(raw, object_pairs_hook=unique_pairs)

    check(Path(__file__).resolve() == root / BASE / 'review_actual_admission.py', 'Exact admission script path required')
    pin(Path(__file__).resolve())
    check(re.fullmatch('[0-9a-f]{64}', args.expected_pins_sha256), 'Exact root admission pin-file SHA required')
    declared = read(args.pins, args.expected_pins_sha256)
    check(declared['schema'] == 'SETI_S2017_ADJACENT_EIGHT_ACTUAL_JOB_ADMISSION_PINS_V1'
        and set(declared['jobs']) == set(JOBS) and re.fullmatch('[0-9a-f]{40}', declared['public_freeze_commit']),
        'Exactly eight actual root-admitted jobs and public freeze required')
    freeze = declared['public_freeze_commit']
    check(declared['public_readback'] == {'path': PUBLIC_READBACK, 'sha256': PUBLIC_READBACK_SHA},
        'Exact actual36-file science public readback required')
    public = read(declared['public_readback']['path'], declared['public_readback']['sha256'])
    check(public['public_freeze_commit'] == freeze and public['status'].startswith('PASS_')
        and public['checks'] and all(record['pass'] is True for record in public['checks']), 'Public freeze readback is not PASS')
    public_pins = {}
    for record in public['checks']:
        name = record['local_path']
        check(name not in public_pins and Path(name).suffix not in ('.h5', '.hdf5', '.npz', '.npy'),
            'Unique public code/metadata readback only')
        expected = {'sha256': record['sha256'], 'bytes': record['bytes']}
        path = confined(root, name); pin(path, expected)
        raw = path.read_bytes()
        check(hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest() == record['git_blob_sha1'],
            'Exact public Git blob identity differs: ' + name)
        public_pins[name] = expected
    check(len(public_pins) == 36 and canonical(sorted(public_pins)) == PUBLIC_36_SORTED_PATHS_SHA,
        'All exact36 published science-freeze paths are required')
    source = read(BASE + '/source_manifest_v2.json', SOURCE_SHA)
    check(source['native_chunk_indices'] == [170, 172] and set(source['by_native_chunk']) == {'170', '172'},
        'Frozen adjacent source metadata differs')
    original = read('analysis/new_visit_search/results/acquire/FAILURE_RECEIPT.json')
    check(original['status'] == 'INCOMPLETE_ONE_SHOT_PRESERVE_PARTIAL_OUTPUTS_NO_RETRY', 'Original source failure must remain preserved')
    headers = {item['label']: item['current_header']['data_attributes'] for item in source['by_native_chunk']['170']['sources']}
    anchor = min(header['tstart'] for header in headers.values())
    summaries, all_maps, all_files, all_profiles = {}, 0, 0, 0
    acquisition_sha = qa_sha = None
    for job_id, job in JOBS.items():
        boundary = job['kind'] == 'boundary'
        family = BASE + ('/boundaries' if boundary else '/search')
        scope_name = family + '/scopes/' + job_id + '.json'
        out_name = family + '/results/' + job_id + '/measurement' if boundary else BASE + '/results/search/' + job_id
        gates = declared['jobs'][job_id]
        check(gates['scope']['path'] == scope_name and gates['receipt']['path'] == out_name + '/EXECUTION_RECEIPT.json',
            'Fixed scope/receipt namespace required')
        scope = read(scope_name, gates['scope']['sha256']); receipt = read(gates['receipt']['path'], gates['receipt']['sha256'])
        check(scope_name in public_pins and public_pins[scope_name] == pins[scope_name], 'Scope was not in exact public readback')
        for name, expected in scope['pinned_metadata_code_and_prerequisites'].items():
            check(Path(name).suffix not in ('.h5', '.hdf5', '.npz', '.npy'), 'Scope metadata admission must not open power files')
            pin(confined(root, name), expected)
        driver_name = family + '/driver.py'
        check(driver_name in public_pins and scope['driver_sha256'] == receipt['driver_sha256'] == public_pins[driver_name]['sha256'],
            'Public driver/scope/receipt SHA binding differs')
        c0 = job['chunks'][0] * NATIVE if boundary else job['native'] * NATIVE
        qs = job['qs']; expected_maps = 3 * len(qs)
        check(scope['output_stage'] == out_name and scope['scan_order'] == list(SCANS)
            and scope['fch1_hz'] == FCH1 and scope['df_hz'] == DF and scope['tsamp_s'] == TSAMP
            and scope['drift_grid'] == {'first_hz_s': -4, 'last_hz_s': 4, 'count': 785}
            and scope['widths_channels'] == [1, 3] and scope['driver_sha256'] == receipt['driver_sha256']
            and receipt['scope_sha256'] == gates['scope']['sha256'] and receipt['public_freeze_commit'] == freeze
            and receipt['MJD_anchor'] == anchor and receipt['runtime_versions'] == VERSIONS,
            'Frozen physical/runtime execution family differs')
        if boundary:
            check(scope['schema'] == 'SETI_S2017_TWO_NEW_JOINED_BOUNDARIES_V1'
                and scope['pair_id'] == receipt['pair_id'] == job_id and scope['source_chunk_ids'] == job['chunks']
                and scope['joined_reference_core_q'] == receipt['fixed_pair_q'] == qs
                and receipt['status'] == 'COMPLETE_S2017_TWO_NEW_JOINED_CORES_SIX_ON_MAPS_NINE_FIXED_PROFILES_EXPLORATORY_ONLY'
                and receipt['compact_files_verified'] == 12 and receipt['decoded_rows_verified'] == 192,
                'Actual complete joined-pair execution required')
            scope_pins = scope['pinned_metadata_code_and_prerequisites']
            source_gate = {'path': BASE + '/results/acquire/ACQUISITION_RESULT.json',
                'sha256': scope_pins[BASE + '/results/acquire/ACQUISITION_RESULT.json']['sha256']}
            qa_gate = {'path': scope['new_source_QA']['path'],
                'sha256': scope_pins[scope['new_source_QA']['path']]['sha256']}
            acquisition_field, qa_field = 'new_acquisition_receipt_sha256', 'new_source_QA_receipt_sha256'
            cpu, slot = 180, receipt['science_slot_index']
            check(receipt['memory_cap_bytes'] == 2 * 1024**3
                and receipt['memory_cap_bytes_aggregate'] == 4 * 1024**3 and receipt['science_jobs_max'] == 2,
                'Declared boundary per-job/aggregate/two-slot resource cap differs')
        else:
            check(scope['schema'] == 'SETI_S2017_ADJACENT_SAFE_INTERIOR_SEARCH_V1'
                and scope['job_id'] == receipt['job_id'] == job_id and scope['native_chunk_index'] == receipt['native_chunk_index'] == job['native']
                and scope['core_q_indices'] == receipt['core_q_indices'] == qs
                and receipt['status'] == 'COMPLETE_S2017_ADJACENT_NATIVE_SAFE_INTERIOR_JOB_EXPLORATORY_ONLY'
                and receipt['prior_native171_search_rerun'] is False, 'Actual complete new interior job required')
            source_gate, qa_gate = scope['prerequisites']['acquisition'], scope['prerequisites']['source_QA']
            acquisition_field, qa_field = 'acquisition_receipt_sha256', 'source_QA_receipt_sha256'
            cpu, slot = 1000, receipt['simultaneous_job_slot']
            check(receipt['memory_cap_bytes_per_process'] == 2 * 1024**3
                and receipt['memory_cap_bytes_aggregate'] == 4 * 1024**3 and receipt['simultaneous_search_jobs_max'] == 2,
                'Declared interior per-job/aggregate/two-slot resource cap differs')
        check(slot in (0, 1) and receipt['CPU_cap_s'] == cpu and receipt['wall_cap_s'] == 1800,
            'Actual shared two-slot/CPU/wall resource admission differs')
        for field, cap in (('process_CPU_seconds_including_imports', cpu), ('wall_seconds_including_imports', 1800), ('peak_RSS_bytes', 2 * 1024**3)):
            check(math.isfinite(receipt[field]) and 0 < receipt[field] <= cap, 'Measured actual resource cap exceeded')
        check(receipt['new_telescope_HTTP_requests'] == receipt['new_telescope_BODY_bytes'] == receipt['cost_DKK'] == 0
            and receipt['original_A_B_status'] == 'FAIL_CLOSED_UNCHANGED' and receipt['calibrated_SNR_FAP'] is False,
            'Zero traffic/cost and preserved exploratory status required')
        check(source_gate['path'] == BASE + '/results/acquire/ACQUISITION_RESULT.json'
            and qa_gate['path'] == BASE + '/results/source_review/QA_RECEIPT.json'
            and receipt[acquisition_field] == source_gate['sha256'] and receipt[qa_field] == qa_gate['sha256'],
            'Actual completed source/source-QA prerequisite binding differs')
        check(acquisition_sha in (None, source_gate['sha256']) and qa_sha in (None, qa_gate['sha256']), 'Jobs have different source prerequisites')
        acquisition_sha, qa_sha = source_gate['sha256'], qa_gate['sha256']
        acquired = read(source_gate['path'], acquisition_sha); source_qa = read(qa_gate['path'], qa_sha)
        check(acquired['status'] == 'COMPLETE_ADJACENT170_172_192_RANGES_12_COMPACTS_EXPLORATORY_ONLY'
            and source_qa['status'] == SOURCE_QA_STATUS and source_qa['counts'] == SOURCE_QA_COUNTS
            and source_qa['schema'] == 'SETI_S2017_ADJACENT170_172_COMPACT_SOURCE_QA_V1'
            and source_qa['acquisition_receipt_sha256'] == acquisition_sha
            and source_qa['source_manifest_sha256'] == acquired['source_manifest_sha256'] == SOURCE_SHA
            and source_qa['source_range_raw_record_sha256'] == canonical(acquired['raw_range_records'])
            and source_qa['decoded_file_row_record_sha256'] == canonical(acquired['decoded_files'])
            and source_qa['source_range_request_record_sha256'] == canonical(acquired['value_read_requests']), 'Actual source-QA admission differs')
        check(source_qa['compact_input_byte_pins'] == {BASE + '/results/acquire/' + record['array_file']:
            {'sha256': record['file_sha256'], 'bytes': record['bytes']} for record in acquired['decoded_files']}
            and source_qa['scope_sha256'] == acquired['scope_sha256']
            and source_qa['driver_sha256'] == acquired['driver_sha256']
            and source_qa['public_freeze_commit'] == acquired['public_freeze_commit']
            and source_qa['qa_script_sha256'] == digest(confined(root, BASE + '/qa_sources.py'))
            and source_qa['detector_or_score_rerun'] is False
            and source_qa['new_telescope_HTTP_requests'] == source_qa['new_telescope_BODY_bytes'] == 0,
            'Source-QA exact compact/provenance bindings differ')
        out = confined(root, out_name)
        inputs = read(out_name + '/INPUT_PINS.json')
        check(inputs['scope_sha256'] == gates['scope']['sha256'] and inputs['public_freeze_commit'] == freeze, 'Saved execution input pins differ')
        check((inputs['pinned_metadata_code_and_prerequisites'] if boundary else inputs['pins'])
            == scope['pinned_metadata_code_and_prerequisites'], 'Saved scope metadata/code pins differ')
        norm = read(out_name + '/NORMALIZATION.json')
        check(norm['source_channel0'] == c0 and norm['raw_dtype'] == '<f4'
            and set(norm['row_power_medians']) == set(SCANS)
            and all(len(values) == 16 and all(math.isfinite(value) and value > 0 for value in values)
                    for values in norm['row_power_medians'].values()), 'Declared full-row normalization geometry differs')
        checkpoint = read(out_name + '/DRIFT_CHECKPOINT.json')
        check(checkpoint['complete'] is True and checkpoint['completed_ON_maps'] == checkpoint['expected_ON_maps'] == expected_maps,
            'Actual map checkpoint incomplete')
        entries = checkpoint['receipts']
        map_q = 'reference_core_q' if boundary else 'core_q'
        check([(record['scan_id'], record[map_q]) for record in entries] == [(scan, q) for scan in ONS for q in qs],
            'Exact unique map order differs')
        summary = receipt['search_summary']
        check(summary['completed_ON_maps'] == expected_maps and summary['cores_per_ON'] == len(qs)
            and summary['carriers_per_ON'] == len(qs) * CORE and summary['ON_carrier_maximum_records'] == expected_maps * CORE
            and summary['correlated_drift_width_combinations'] == expected_maps * CORE * 1570
            and summary['drift_grid_count'] == 785 and summary['widths_channels'] == [1, 3], 'Declared complete coverage counts differ')
        expected_files = {'EXECUTION_RECEIPT.json', 'INPUT_PINS.json', 'NORMALIZATION.json',
            'DRIFT_CHECKPOINT.json', 'DRIFT_TOP20.json', 'FIXED_TOP3_PROFILES.json'}
        for record in entries:
            scan, q = record['scan_id'], record[map_q]; first = c0 + q * CORE
            tile = qs.index(q)
            map_name = f'{scan}_tile_{tile:02d}_all_carriers.npz' if boundary else f'{scan}_q{q:03d}_all_carriers.npz'
            norm_name = f'{scan}_tile_{tile:02d}_normalization.json' if boundary else f'{scan}_q{q:03d}_normalization.json'
            check(record['path'] == map_name and record['searched_carriers'] == CORE and record['valid_hypotheses_per_carrier'] == 1570
                and record['reference_channel_interval_half_open'] == [first, first + CORE], 'Declared physical map geometry differs')
            pin(confined(out, map_name), {'sha256': record['sha256'], 'bytes': record['bytes']}); expected_files.add(map_name)
            nr = {'path': record['normalization_path'], 'sha256': record['normalization_sha256'], 'bytes': record['normalization_bytes']} if boundary else record['normalization']
            check(nr['path'] == norm_name, 'Declared normalization identity differs')
            pin(confined(out, norm_name), {'sha256': nr['sha256'], 'bytes': nr['bytes']}); expected_files.add(norm_name)
            normal = read(out_name + '/' + norm_name)
            check(normal['normalization_source_channels'] == list(range(first, first + CORE))
                and normal['normalization_unmasked_counts'] == [CORE] * 16, 'Declared core normalization source frame differs')
            for field in ('row_power_median', 'row_residual_median', 'row_winsorized_residual_location', 'row_residual_MAD_scale'):
                check(len(normal[field]) == 16 and all(math.isfinite(value) for value in normal[field]), 'Invalid declared normalization rows')
        tops = read(out_name + '/DRIFT_TOP20.json'); check(set(tops) == set(ONS) and receipt['top20_entries'] == 60, 'Three declared top20 lists required')
        for scan in ONS:
            tracks = tops[scan]
            check(len(tracks) == 20 and tracks == sorted(tracks, key=lambda track: (-track['maximum_robust_box_track_score'], track['source_reference_channel']))
                and all(abs(a['source_reference_channel'] - b['source_reference_channel']) > 3
                        for i, a in enumerate(tracks) for b in tracks[i + 1:]), 'Declared top20 ordering/suppression differs')
            for rank, track in enumerate(tracks, 1):
                channel = track['source_reference_channel']; q = (channel - c0) // CORE
                check(q in qs and track['display_rank'] == rank and track['originating_scan'] == scan
                    and track['track_id'] == f'{scan}_visit20170428_Sband_{job_id}_rank_{rank:02d}'
                    and track['reference_frequency_hz'] == FCH1 + DF * channel
                    and track['reference_seconds_from_anchor'] == (headers[scan]['tstart'] - anchor) * 86400 + .5 * TSAMP
                    and track['width_channels'] in (1, 3) and math.isfinite(track['maximum_robust_box_track_score'])
                    and -4 <= track['drift_hz_s'] <= 4, 'Declared track physical source/time frame differs')
        profiles = read(out_name + '/FIXED_TOP3_PROFILES.json')
        check(len(profiles) == 9 and [record['selected_track'] for record in profiles] == [track for scan in ONS for track in tops[scan][:3]],
            'Exact nine fixed profile selections differ')
        for record in profiles:
            track, patch = record['selected_track'], record['patch']; patch_name = 'profiles/' + track['track_id'] + '.npz'
            check(patch['path'] == patch_name and record['fixed_frequency_shift_channels'] == 0
                and record['classification'] == 'UNRESOLVED_EXPLORATORY_PROFILE_NO_SKY_INFERENCE'
                and [profile['scan_id'] for profile in record['scan_profiles']] == list(SCANS), 'Fixed profile contract differs')
            pin(confined(out, patch_name), {'sha256': patch['sha256'], 'bytes': patch['bytes']}); expected_files.add(patch_name)
            for profile in record['scan_profiles']:
                for field in ('all_16_center_minus_flank_rows', 'all_16_raw_width_mean_power', 'frozen_source_channel_centers'):
                    check(len(profile[field]) == 16 and all(math.isfinite(value) for value in profile[field]), 'All16 declared profile rows required')
                check(all(c0 + 64 <= center < c0 + NATIVE * (2 if boundary else 1) - 64
                    for center in profile['frozen_source_channel_centers']), 'Declared raw patch exceeds source support')
        ps = receipt['fixed_profile_summary']
        check(ps['profile_count'] == 9 and ps['plot_count'] == 0 and ps['all_rows_retained'] == 16
            and ps['shift_frequency_drift_width_optimization_applied'] is False
            and ps['source_top20_sha256'] == pins[out_name + '/DRIFT_TOP20.json']['sha256']
            and ps['saved_normalization_sha256'] == pins[out_name + '/NORMALIZATION.json']['sha256'], 'Actual fixed-profile summary differs')
        check({path.relative_to(out).as_posix() for path in out.rglob('*') if path.is_file()} == expected_files,
            'Actual output inventory incomplete or has failure/temporary/extra files')
        summaries[job_id] = {'scope_sha256': gates['scope']['sha256'], 'execution_receipt_sha256': gates['receipt']['sha256'],
            'driver_sha256': receipt['driver_sha256'], 'maps': expected_maps, 'fixed_profiles': 9, 'top20_entries': 60,
            'required_file_count': len(expected_files), 'search_summary': summary,
            'resources': {field: receipt[field] for field in ('process_CPU_seconds_including_imports', 'wall_seconds_including_imports', 'peak_RSS_bytes')}}
        all_maps += expected_maps; all_files += len(expected_files); all_profiles += 9
    check(all_maps == 1536 and all_profiles == 72 and all_files == 3192, 'Eight-job total counts differ')
    for name, expected in pins.items():
        path = confined(root, name)
        check(path.stat().st_size == expected['bytes'] and digest(path) == expected['sha256'], 'Input changed during actual admission: ' + name)
    report = {'schema': 'SETI_S2017_ADJACENT_EIGHT_ACTUAL_SEARCH_ADMISSION_REVIEW_V1',
        'status': 'PASS_EIGHT_ACTUAL_COMPLETE_JOBS_METADATA_AND_ALL_OUTPUT_BYTE_IDENTITIES',
        'reviewer': '/root/full_band_review', 'reviewed_UTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'public_freeze_commit': freeze, 'admission_pins_sha256': args.expected_pins_sha256,
        'public_readback': declared['public_readback'], 'jobs': summaries,
        'counts': {'search_jobs': 8, 'maps': all_maps, 'carrier_maximum_records': all_maps * CORE,
            'correlated_drift_width_combinations': all_maps * CORE * 1570,
            'required_output_files': all_files, 'top20_entries': 480,
            'fixed_profiles': 72, 'scan_profiles': 432, 'retained_raw_patch_cells_declared': 891648},
        'acquisition_receipt_sha256': acquisition_sha, 'source_QA_receipt_sha256': qa_sha,
        'observed_input_and_output_byte_pins': pins, 'HDF5_NPZ_values_opened': False,
        'source_data_files_opened': False, 'science_or_detector_executed': False, 'HTTP_requests': 0,
        'signal_interpretation_performed': False, 'global_rank_reconstruction_from_saved_map_values': 'DEFERRED_TO_TWO_EMPIRICAL_QA_RECEIPTS',
        'source_cell_and_fixed_profile_arithmetic': 'DEFERRED_TO_TWO_EMPIRICAL_QA_RECEIPTS',
        'original_A_B_status': 'FAIL_CLOSED_UNCHANGED', 'independent_tests_claimed': False}
    target = confined(root, BASE + '/ACTUAL_SEARCH_ADMISSION_REVIEW.json')
    check(not target.exists(), 'Refuse actual admission receipt overwrite')
    temporary = target.with_suffix(target.suffix + '.tmp')
    with temporary.open('x') as handle:
        json.dump(report, handle, indent=2, allow_nan=False); handle.write('\n'); handle.flush(); os.fsync(handle.fileno())
    temporary.replace(target)
    print(json.dumps({'status': report['status'], 'path': target.relative_to(root).as_posix(),
        'sha256': digest(target), 'counts': report['counts']}))


if __name__ == '__main__':
    main()
