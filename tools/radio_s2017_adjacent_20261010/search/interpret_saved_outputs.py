#!/usr/bin/env python3
"""Export completed, QA-passed interior JSON only; no H5/NPZ/source/detector reads.

The six administrative job rankings stay separate. Exact sampled frozen-box
geometry recurrence and signed half/row context are descriptive, never gates.
Importing this module opens no measurements; main requires the actual QA SHA
and explicit root GO before it opens any saved ranking or fixed-profile values.
"""
import argparse
import csv
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import time

BASE = 'analysis/s2017_next_native'
STAGE = BASE + '/results/search'
SCRIPT = BASE + '/search/interpret_saved_outputs.py'
QA_PATH = STAGE + '/review/QA_RECEIPT.json'
QA_CODE_SHA = '53d7eafe21a8839abfaad59e560e7e0fd194251b21570ac2dc0131059d73db7d'
QA_STATUS = 'PASS1524_S2017_ADJACENT_MAPS54_FIXED_PROFILES_AND668736_BITWISE_SOURCE_CELLS'
SOURCE_PATH = BASE + '/source_manifest_v2.json'
SOURCE_SHA = '2a09dcd018e83e822cf19cb088e4f35469e8b160cbcde69f0428e64544ad7909'
SOURCE_QA_PATH = BASE + '/results/source_review/QA_RECEIPT.json'
SOURCE_QA_SHA = '21a8edaf91e9a60d3209d33e4620a5f93038aabfafd3910094bd25e0fd66318a'
ACQUISITION_PATH = BASE + '/results/acquire/ACQUISITION_RESULT.json'
ACQUISITION_SHA = '2dd9d1f6f99cb41dbf60d47e28f23771da6b27c6ab786f4945b5696d2449df3e'
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
ONS = SCANS[::2]
NATIVES = (170, 172)
PARTITIONS = {'batch01': tuple(range(1, 86)), 'batch02': tuple(range(86, 171)), 'batch03': tuple(range(171, 255))}
JOBS = tuple(f'native{n}_{b}' for n in NATIVES for b in PARTITIONS)
COUNT, CORE = 1048576, 4096
FCH1, DF, TSAMP = 2802832031.25, -2.7939677238464355, 18.253611008
EXPECTED_QA_COUNTS = {'batch_families': 6, 'maps': 1524, 'map_normalization_records': 1524,
    'carrier_maximum_records': 6242304, 'valid_hypothesis_records': 9800417280,
    'top20_entries': 360, 'patches': 54, 'scan_profiles': 324, 'time_row_occurrences': 5184,
    'retained_raw_patch_cells': 668736, 'compact_files': 12, 'decoded_rows': 192,
    'native_full_row_medians_recomputed': 192, 'ON_core_row_medians_recomputed': 24384,
    'raw_cells_bitwise_checked': 668736}
CPU_CAP, WALL_CAP, RAM_CAP = 120, 180, 2 * 1024**3


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(items):
    result = {}
    for key, value in items:
        require(key not in result, 'Duplicate JSON field: ' + key)
        result[key] = value
    return result


def jload(raw):
    def invalid(value):
        raise ValueError('Nonfinite JSON constant: ' + value)
    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid)


def save_json(path, value):
    with path.open('x', encoding='utf8') as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write('\n')


def save_csv(path, records):
    with path.open('x', newline='', encoding='utf8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'expected-interior-QA-sha256', 'expected-code-sha256', 'expected-search-freeze-commit'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--root-go-after-interior-QA', action='store_true')
    args = parser.parse_args()
    require(args.root_go_after_interior_QA, 'Separate root GO after actual interior QA PASS required')
    require(re.fullmatch('[0-9a-f]{64}', args.expected_interior_QA_sha256)
        and re.fullmatch('[0-9a-f]{64}', args.expected_code_sha256)
        and re.fullmatch('[0-9a-f]{40}', args.expected_search_freeze_commit), 'Exact actual SHA/freeze arguments required')
    root = Path(args.root).resolve()
    require(Path(__file__).resolve() == root / SCRIPT, 'Exact prepared exporter path required')
    self_raw = Path(__file__).read_bytes()
    require(sha(self_raw) == args.expected_code_sha256, 'Prepared exporter bytes differ')
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS, (RAM_CAP, RAM_CAP))
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    def deadline(*_):
        raise TimeoutError('Descriptive export wall/CPU limit')
    signal.signal(signal.SIGALRM, deadline)
    signal.signal(signal.SIGXCPU, deadline)
    signal.alarm(WALL_CAP)
    for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[name] = '1'
    pins = {SCRIPT: {'sha256': sha(self_raw), 'bytes': len(self_raw)}}
    qa_raw = (root / QA_PATH).read_bytes()
    require(sha(qa_raw) == args.expected_interior_QA_sha256, 'Actual interior QA SHA differs')
    qa = jload(qa_raw)
    require(qa['schema'] == 'SETI_S2017_ADJACENT_SIX_INTERIOR_JOBS_SAVED_OUTPUT_SOURCE_QA_V1'
        and qa['status'] == QA_STATUS and qa['qa_script_sha256'] == QA_CODE_SHA
        and qa['public_freeze_commit'] == args.expected_search_freeze_commit
        and qa['counts'] == EXPECTED_QA_COUNTS and qa['detector_or_score_rerun'] is False
        and qa['fixed_track_optimization_applied'] is False
        and qa['new_telescope_HTTP_requests'] == qa['new_telescope_BODY_bytes'] == 0,
        'Actual complete six-job saved-output/source QA required before saved numeric opening')
    require(set(qa['scope_SHA256s']) == set(qa['search_receipt_SHA256s']) == set(JOBS), 'All six QA-passed jobs required')
    pins[QA_PATH] = {'sha256': sha(qa_raw), 'bytes': len(qa_raw)}
    allowed = {SOURCE_PATH, SOURCE_QA_PATH, ACQUISITION_PATH}
    for job in JOBS:
        allowed.add(BASE + '/search/scopes/' + job + '.json')
        allowed.update(STAGE + '/' + job + '/' + name for name in
            ('EXECUTION_RECEIPT.json', 'DRIFT_TOP20.json', 'FIXED_TOP3_PROFILES.json', 'NORMALIZATION.json'))

    def read_json(relative):
        require(relative in allowed and Path(relative).suffix == '.json', 'Only authorized completed saved JSON admitted')
        require(relative in qa['all_input_byte_pins'], 'Read lacks actual QA byte pin')
        path = root / relative
        require(path.resolve().is_relative_to(root), 'Read outside workspace')
        raw = path.read_bytes()
        observed = {'sha256': sha(raw), 'bytes': len(raw)}
        require(observed == qa['all_input_byte_pins'][relative], 'Actual QA-passed input changed: ' + relative)
        require(relative not in pins or pins[relative] == observed, 'Repeated JSON input changed')
        pins[relative] = observed
        return jload(raw)

    # Gate values and headers are admitted before the selected numeric outputs.
    source = read_json(SOURCE_PATH)
    source_qa = read_json(SOURCE_QA_PATH)
    acquisition = read_json(ACQUISITION_PATH)
    require(pins[SOURCE_PATH]['sha256'] == SOURCE_SHA and pins[SOURCE_QA_PATH]['sha256'] == SOURCE_QA_SHA
        and pins[ACQUISITION_PATH]['sha256'] == ACQUISITION_SHA, 'Fixed actual source prerequisites differ')
    require(source['native_chunk_indices'] == list(NATIVES) and source['scan_order'] == list(SCANS)
        and source['fch1_hz'] == FCH1 and source['df_hz'] == DF and source['tsamp_s'] == TSAMP,
        'Verified native/time/frequency source frame differs')
    require(source_qa['acquisition_receipt_sha256'] == ACQUISITION_SHA
        and acquisition['status'] == 'COMPLETE_ADJACENT170_172_192_RANGES_12_COMPACTS_EXPLORATORY_ONLY'
        and acquisition['new_telescope_HTTP_requests'] == 192
        and acquisition['new_telescope_BODY_bytes'] == 597792529, 'Actual 192-row new acquisition required')
    import numpy as np

    def distribution(values):
        a = np.asarray(values, dtype=np.float64)
        require(a.size and np.isfinite(a).all(), 'Finite nonempty saved distribution required')
        return {'count': int(a.size), 'minimum': float(a.min()), 'median': float(np.median(a)), 'maximum': float(a.max())}

    headers = {item['label']: item['current_header']['data_attributes'] for item in source['by_native_chunk']['170']['sources']}
    require(tuple(headers) == SCANS and all(item['current_header']['data_attributes'] == headers[item['label']]
        for item in source['by_native_chunk']['172']['sources']), 'Six canonical same-visit source headers required')
    anchor = min(item['tstart'] for item in headers.values())
    times = np.asarray([(headers[s]['tstart'] - anchor) * 86400 + (np.arange(16) + .5) * TSAMP for s in SCANS])

    def geometry(track):
        dt = times - track['reference_seconds_from_anchor']
        centers = np.rint((track['reference_frequency_hz'] - FCH1) / DF + track['drift_hz_s'] * dt / DF).astype(np.int64)
        return dt, centers

    def repeated_groups(groups, name):
        result = []
        for key, members in groups.items():
            origins = [s for s in ONS if any(m['originating_scan'] == s for m in members)]
            if len(origins) > 1:
                result.append({name: list(key) if isinstance(key, tuple) else key,
                    'originating_scans': origins, 'members': members})
        return result

    families, fixed_tracks, measures, rows, top_rows = [], [], [], [], []
    for job in JOBS:
        native = int(job.split('_')[0][6:]); batch = job.split('_', 1)[1]
        qs, c0 = PARTITIONS[batch], native * COUNT
        scope_path = BASE + '/search/scopes/' + job + '.json'
        folder = STAGE + '/' + job + '/'
        scope, receipt = read_json(scope_path), read_json(folder + 'EXECUTION_RECEIPT.json')
        require(pins[scope_path]['sha256'] == qa['scope_SHA256s'][job]
            and pins[folder + 'EXECUTION_RECEIPT.json']['sha256'] == qa['search_receipt_SHA256s'][job]
            and scope['core_q_indices'] == list(qs) and scope['native_chunk_index'] == native
            and receipt['status'] == 'COMPLETE_S2017_ADJACENT_NATIVE_SAFE_INTERIOR_JOB_EXPLORATORY_ONLY'
            and receipt['scope_sha256'] == pins[scope_path]['sha256']
            and receipt['public_freeze_commit'] == args.expected_search_freeze_commit,
            'Actual complete QA-passed job/scope identity differs')
        tops = read_json(folder + 'DRIFT_TOP20.json')
        profiles = read_json(folder + 'FIXED_TOP3_PROFILES.json')
        normalization = read_json(folder + 'NORMALIZATION.json')
        require(pins[folder + 'DRIFT_TOP20.json']['sha256'] == receipt['fixed_profile_summary']['source_top20_sha256']
            and pins[folder + 'NORMALIZATION.json']['sha256'] == receipt['fixed_profile_summary']['saved_normalization_sha256']
            and normalization['source_channel0'] == c0 and normalization['count'] == COUNT
            and normalization['raw_dtype'] == '<f4', 'Saved JSON normalization/ranking binds differ')
        require(set(tops) == set(ONS) and len(profiles) == 9
            and [r['selected_track'] for r in profiles] == [t for s in ONS for t in tops[s][:3]], 'Exact saved local top3 family differs')
        first, stop = c0 + min(qs) * CORE, c0 + (max(qs) + 1) * CORE
        family = {'job_id': job, 'native_chunk_index': native, 'batch_id': batch, 'core_q_indices': list(qs),
            'reference_channel_interval_half_open': [first, stop],
            'reference_frequency_center_limits_MHz': sorted([(FCH1 + DF * first) / 1e6, (FCH1 + DF * (stop - 1)) / 1e6]),
            'ON_maps': 3 * len(qs), 'reference_carriers_per_ON': len(qs) * CORE,
            'reference_carrier_bandwidth_per_ON_hz': len(qs) * CORE * abs(DF),
            'origin_groups': [], 'fixed_tracks': []}
        templates, references = {}, {}
        for on in ONS:
            entries = tops[on]
            require(len(entries) == 20 and [t['display_rank'] for t in entries] == list(range(1, 21)), 'Preserve each complete local top20')
            channels = sorted(t['source_reference_channel'] for t in entries)
            gaps = np.diff(channels)
            group = {'originating_scan': on, 'reference_midpoint_seconds_from_anchor': entries[0]['reference_seconds_from_anchor'],
                'saved_local_top20_in_existing_rank_order': entries,
                'score_distribution_of_saved_local_top20': distribution([t['maximum_robust_box_track_score'] for t in entries]),
                'reference_frequency_center_limits_MHz': sorted([(FCH1 + DF * min(channels)) / 1e6, (FCH1 + DF * max(channels)) / 1e6]),
                'reference_frequency_span_hz': (max(channels) - min(channels)) * abs(DF),
                'sorted_reference_channel_gaps_min_median_max': [int(gaps.min()), float(np.median(gaps)), int(gaps.max())],
                'drift_hz_s_min_max': [min(t['drift_hz_s'] for t in entries), max(t['drift_hz_s'] for t in entries)],
                'width_channel_counts': {str(w): sum(t['width_channels'] == w for t in entries) for w in (1, 3)},
                'counts_by_reference_core_q': {str(q): sum(t['reference_core_tile'] == q for t in entries) for q in qs},
                'constant_all96_sampled_center_track_count': 0}
            for track in entries:
                require(track['originating_scan'] == on and track['reference_core_tile'] in qs
                    and first <= track['source_reference_channel'] < stop, 'Saved local track frame differs')
                dt, centers = geometry(track)
                stationary = bool(np.all(centers == centers.flat[0]))
                group['constant_all96_sampled_center_track_count'] += int(stationary)
                member = {'track_id': track['track_id'], 'originating_scan': on, 'display_rank': track['display_rank'],
                    'drift_hz_s': track['drift_hz_s'], 'width_channels': track['width_channels']}
                key = (track['width_channels'], *map(int, centers.ravel()))
                templates.setdefault(key, []).append(member)
                references.setdefault(track['source_reference_channel'], []).append(member)
                top_rows.append({'job_id': job, 'native_chunk_index': native, **track,
                    'frequency_at_first_visit_midpoint_hz_from_frozen_track': float(track['reference_frequency_hz']
                        + track['drift_hz_s'] * (times[0, 0] - track['reference_seconds_from_anchor'])),
                    'all96_sampled_center_channel_min': int(centers.min()), 'all96_sampled_center_channel_max': int(centers.max()),
                    'all96_sampled_center_stationary': stationary})
            family['origin_groups'].append(group)
        family['repeated_exact_96_sampled_center_and_width_geometry'] = repeated_groups(templates, 'width_then96sampled_center_channels')
        family['repeated_reference_channel_at_different_ON_midpoint_times'] = repeated_groups(references, 'source_reference_channel')
        for item in profiles:
            track = item['selected_track']; origin_index = SCANS.index(track['originating_scan'])
            dt, centers = geometry(track)
            require(item['fixed_frequency_shift_channels'] == 0
                and item['classification'] == 'UNRESOLVED_EXPLORATORY_PROFILE_NO_SKY_INFERENCE'
                and item['fixed_flank_offsets'] == 'absolute channel offset > 3 within +/-64'
                and [m['scan_id'] for m in item['scan_profiles']] == list(SCANS)
                and centers.min() - 64 >= c0 and centers.max() + 64 < c0 + COUNT,
                'Frozen selected profile identity/source support differs')
            means = [m['mean_center_minus_flank'] for m in item['scan_profiles']]
            case = {'job_id': job, 'native_chunk_index': native, **track, 'qualified_claim': False,
                'classification': item['classification'], 'scan_profiles': item['scan_profiles'],
                'six_saved_mean_residuals_in_scan_order': means,
                'origin_mean_is_largest_of_six': means[origin_index] == max(means),
                'origin_mean_minus_largest_exact_fixed_OFF_mean': means[origin_index] - max(means[1::2]),
                'other_ON_scans_with_both_saved_half_means_positive': [],
                'OFF_scans_with_both_saved_half_means_positive': [],
                'all96_sampled_center_stationary': bool(np.all(centers == centers.flat[0])),
                'all96_sampled_center_channel_range': [int(centers.min()), int(centers.max())]}
            for i, saved in enumerate(item['scan_profiles']):
                residual = np.asarray(saved['all_16_center_minus_flank_rows'], dtype=np.float64)
                require(residual.shape == (16,) and np.isfinite(residual).all(), 'All16 saved signed residual rows required')
                require(saved['mean_center_minus_flank'] == float(residual.mean())
                    and saved['median_center_minus_flank'] == float(np.median(residual))
                    and saved['first_eight_mean_center_minus_flank'] == float(residual[:8].mean())
                    and saved['last_eight_mean_center_minus_flank'] == float(residual[8:].mean())
                    and saved['positive_rows'] == int(np.count_nonzero(residual > 0))
                    and saved['frozen_source_channel_centers'] == centers[i].tolist(), 'Saved JSON arithmetic/frozen geometry differs')
                raw_means = saved['all_16_raw_width_mean_power']
                require(len(raw_means) == 16 and all(math.isfinite(v) and v >= 0 for v in raw_means), 'Saved raw width means differ')
                both = saved['first_eight_mean_center_minus_flank'] > 0 and saved['last_eight_mean_center_minus_flank'] > 0
                if i % 2:
                    if both: case['OFF_scans_with_both_saved_half_means_positive'].append(SCANS[i])
                elif i != origin_index and both:
                    case['other_ON_scans_with_both_saved_half_means_positive'].append(SCANS[i])
                record = {'job_id': job, 'native_chunk_index': native, 'track_id': track['track_id'],
                    'originating_scan': track['originating_scan'], 'display_rank': track['display_rank'],
                    'reference_frequency_hz': track['reference_frequency_hz'], 'drift_hz_s': track['drift_hz_s'],
                    'width_channels': track['width_channels'], 'saved_robust_rank_score': track['maximum_robust_box_track_score'],
                    'scan_id': SCANS[i], 'scan_role': 'OFF' if i % 2 else 'ON', 'is_selection_scan': i == origin_index,
                    **{k: saved[k] for k in ('mean_center_minus_flank', 'median_center_minus_flank', 'positive_rows',
                        'first_eight_mean_center_minus_flank', 'last_eight_mean_center_minus_flank')},
                    'both_saved_half_means_positive': both,
                    'first_midpoint_seconds_from_anchor': float(times[i, 0]), 'last_midpoint_seconds_from_anchor': float(times[i, -1]),
                    'frozen_center_channel_min': int(centers[i].min()), 'frozen_center_channel_max': int(centers[i].max())}
                measures.append(record)
                for j in range(16):
                    rows.append({'job_id': job, 'native_chunk_index': native, 'track_id': track['track_id'],
                        'originating_scan': track['originating_scan'], 'display_rank': track['display_rank'],
                        'scan_id': SCANS[i], 'time_row': j, 'time_midpoint_seconds_from_anchor': float(times[i, j]),
                        'time_seconds_from_frozen_reference': float(dt[i, j]), 'frozen_center_source_channel': int(centers[i, j]),
                        'frozen_center_frequency_hz': float(FCH1 + DF * centers[i, j]),
                        'saved_center_minus_flank': float(residual[j]), 'saved_raw_width_mean_power': raw_means[j]})
            case['origin_both_saved_half_means_positive'] = bool(item['scan_profiles'][origin_index]['first_eight_mean_center_minus_flank'] > 0
                and item['scan_profiles'][origin_index]['last_eight_mean_center_minus_flank'] > 0)
            case['all_three_ONs_have_both_saved_half_means_positive'] = case['origin_both_saved_half_means_positive'] and len(case['other_ON_scans_with_both_saved_half_means_positive']) == 2
            fixed_tracks.append(case); family['fixed_tracks'].append(case)
        families.append(family)
    require((len(families), len(top_rows), len(fixed_tracks), len(measures), len(rows)) == (6, 360, 54, 324, 5184), 'Complete descriptive inventory required')
    origin = [m for m in measures if m['is_selection_scan']]
    other_on = [m for m in measures if m['scan_role'] == 'ON' and not m['is_selection_scan']]
    off = [m for m in measures if m['scan_role'] == 'OFF']
    summary = {'saved_fixed_profile_score_distribution': distribution([t['maximum_robust_box_track_score'] for t in fixed_tracks]),
        'selection_ON_mean_distribution': distribution([m['mean_center_minus_flank'] for m in origin]),
        'other_ON_mean_distribution': distribution([m['mean_center_minus_flank'] for m in other_on]),
        'exact_fixed_OFF_mean_distribution': distribution([m['mean_center_minus_flank'] for m in off]),
        'selection_ON_largest_of_six_count': sum(t['origin_mean_is_largest_of_six'] for t in fixed_tracks),
        'selection_ON_both_half_means_positive_count': sum(m['both_saved_half_means_positive'] for m in origin),
        'other_ON_both_half_means_positive_count': sum(m['both_saved_half_means_positive'] for m in other_on),
        'OFF_both_half_means_positive_count': sum(m['both_saved_half_means_positive'] for m in off),
        'all3_ON_both_half_means_positive_track_count': sum(t['all_three_ONs_have_both_saved_half_means_positive'] for t in fixed_tracks),
        'all3_ON_positive_half_tracks_with_some_OFF_positive_halves_count': sum(t['all_three_ONs_have_both_saved_half_means_positive'] and bool(t['OFF_scans_with_both_saved_half_means_positive']) for t in fixed_tracks),
        'constant_all96_sampled_center_fixed_track_count': sum(t['all96_sampled_center_stationary'] for t in fixed_tracks),
        'selection_ON_positive_row_min_max': [min(m['positive_rows'] for m in origin), max(m['positive_rows'] for m in origin)],
        'origin_minus_largest_exact_fixed_OFF_distribution': distribution([t['origin_mean_minus_largest_exact_fixed_OFF_mean'] for t in fixed_tracks])}
    q128_context = []
    for native in NATIVES:
        center_channel = native * COUNT + 128 * CORE
        center_frequency = FCH1 + DF * center_channel
        family = next(f for f in families if f['job_id'] == f'native{native}_batch02')
        selected = [t for t in family['fixed_tracks'] if t['reference_core_tile'] == 128]
        q128_context.append({'native_chunk_index': native, 'job_id': family['job_id'],
            'core_q': 128, 'core_start_source_channel': center_channel,
            'coarse_chunk_midpoint_frequency_hz': center_frequency,
            'core_reference_channel_interval_half_open': [center_channel, center_channel + CORE],
            'existing_local_top20_q128_counts_per_ON': {g['originating_scan']: sum(
                t['reference_core_tile'] == 128 for t in g['saved_local_top20_in_existing_rank_order']) for g in family['origin_groups']},
            'saved_top3_q128_profile_count': len(selected),
            'saved_top3_q128_profiles': selected,
            'exact_coarse_center_stationary_saved_top3_count': sum(t['all96_sampled_center_stationary']
                and t['all96_sampled_center_channel_range'] == [center_channel, center_channel] for t in selected)})
    prior171 = {'native_chunk_index': 171, 'q128_core_start_source_channel': 179830784,
        'previously_known_stationary_frequency_hz': 2300390625.0,
        'known_before_adjacent_native_selection': True,
        'new_measurement_of_native171_performed_here': False,
        'adjacent_coarse_center_frequency_spacing_hz': COUNT * abs(DF),
        'scope': 'Prior stationary native171 ON/OFF structure is earlier context, not an independent replication; adjacent native values are described only from their already saved selected profiles.'}
    limitations = [
        'Six administrative job rankings remain separate; no global top360 or rank across jobs is created.',
        'All selected ranks and fixed profiles are post-search on the same ON data and same 2017-04-28 visit; positive halves or origin dominance are descriptive selection-conditioned properties, not independent confirmation.',
        'Adjacent 170/172 were fixed before their own new values but after 171 results were known; this is coverage extension, not blind independent replication or a new observation.',
        'Ranking maximizes correlated drift/width hypotheses after core row-median/MAD normalization. It is not calibrated SNR, FAP, p-value, flux, EIRP, sensitivity or a count of independent trials.',
        'Fixed signed profile means use full 1048576-channel native-row float32 medians before float64 profile promotion and fixed abs(offset)>3 flanks within +/-64. They differ from detector scores and have no flux unit.',
        'Exact fixed OFF means do not test nearby OFF structure. No OFF score bank, local OFF peak search, veto, retuning, fits or source classification is performed.',
        'Reference frequencies from different ONs correspond to different first-integration midpoints. A shared reference channel alone does not establish a persistent physical track.',
        'Exact sampled geometry recurrence means the same 96 rounded native center channels at actual six-scan row midpoints and same width; it uses no tolerance, fit or significance test and does not identify physical origin.',
        'All 54 selected profiles and all 360 existing local top20 entries are retained; half signs and recurrence are not candidate gates.',
        'The 54 profiles are selection instances, not necessarily 54 distinct source carriers or statistically independent physical tracks; sampled geometry duplicates remain visible.',
        'q128 context uses only existing local top20 entries and saved top3 profiles. Missing q128 selections do not imply quiet q128 data, and geometric coarse-center spacing does not establish instrumental or physical cause.',
        'This exporter reads only actual QA-pinned JSON and its own code. The earlier empirical QA checked 192 decoded rows, native/core median values and 668736 raw patch occurrences bitwise; raw H5/NPZ are not reopened here.',
        'The 2017 S-band coverage is not same-frequency replication of the earlier 2016 L-band cases. Original failures and protected 2016 holdouts remain unchanged.']
    report = {'schema': 'SETI_S2017_SIX_INTERIOR_FAMILIES_SAVED_JSON_DESCRIPTIVE_INTERPRETATION_V1',
        'status': 'COMPLETE_DESCRIPTIVE_ONLY_QUALIFIED_CLAIM_FALSE', 'qualified_claim': False,
        'qualified_SETI_detection': False, 'independent_or_blind_confirmation': False,
        'source_H5_or_NPZ_opened': False, 'detector_or_score_rerun': False,
        'fits_fixed_track_optimization_OFF_veto_or_calibrated_SNR_FAP': False, 'new_HTTP_requests': 0,
        'code_sha256': sha(self_raw), 'visit': '2017-04-28 / AGBT17A_999_55', 'target': 'HIP98505 / HD189733',
        'actual_interior_QA': {'path': QA_PATH, 'sha256': args.expected_interior_QA_sha256, 'counts': qa['counts']},
        'source_QA_sha256': SOURCE_QA_SHA, 'acquisition_receipt_sha256': ACQUISITION_SHA,
        'scope_SHA256s': qa['scope_SHA256s'], 'execution_receipt_SHA256s': qa['search_receipt_SHA256s'],
        'search_public_freeze_commit': qa['public_freeze_commit'], 'QA_public_freeze_commit': qa['qa_public_freeze_commit'],
        'counts': {'jobs': 6, 'ON_maps': 1524, 'local_top20_entries': 360, 'fixed_tracks': 54,
            'fixed_scan_measures': 324, 'fixed_time_rows': 5184, 'selection_ON_measures': 54, 'other_ON_measures': 108, 'OFF_measures': 162},
        'geometry': {'scan_order': SCANS, 'MJD_anchor': anchor, 'fch1_hz': FCH1, 'df_hz': DF, 'tsamp_s': TSAMP,
            'actual_scan_midpoint_seconds_from_anchor': times.tolist(), 'drift_grid_hz_s': {'min': -4, 'max': 4, 'count': 785},
            'widths_channels': [1, 3], 'widths_hz': [abs(DF), 3 * abs(DF)],
            'safe_reference_cores_per_ON_per_native': 254, 'reference_carriers_per_ON_per_native': 254 * CORE,
            'interior_native_chunk_fraction_searched': 254 * CORE / COUNT,
            'reference_carrier_bandwidth_per_ON_per_native_hz': 254 * CORE * abs(DF),
            'ON_carrier_origin_entries': 6242304, 'correlated_drift_width_combinations': 9800417280,
            'new_remote_source_body_bytes': 597792529, 'new_exact_source_ranges': 192},
        'summary': summary, 'families': families, 'fixed_tracks_in_job_origin_rank_order': fixed_tracks,
        'q128_saved_selection_context_per_native': q128_context, 'prior_native171_context': prior171,
        'limitations': limitations, 'authenticated_read_input_byte_pins': pins}
    out = root / STAGE / 'interpretation'
    out.mkdir(exist_ok=False)
    save_json(out / 'INTERIOR_INTERPRETATION.json', report)
    save_csv(out / 'FIXED_SCAN_MEASURES.csv', measures)
    save_csv(out / 'FIXED_TIME_ROWS.csv', rows)
    save_csv(out / 'TOP20_REFERENCE_TRACKS.csv', top_rows)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    labels = ['ON1', 'OFF1', 'ON2', 'OFF2', 'ON3', 'OFF3']
    fig, axes = plt.subplots(2, 3, figsize=(16, 11), constrained_layout=True)
    for ax, family in zip(axes.flat, families):
        tracks = family['fixed_tracks']
        matrix = np.asarray([t['six_saved_mean_residuals_in_scan_order'] for t in tracks])
        v = max(float(np.abs(matrix).max()), float(np.finfo(float).tiny))
        im = ax.imshow(matrix, cmap='RdBu_r', vmin=-v, vmax=v, aspect='auto')
        ax.set_xticks(range(6), labels)
        ax.set_yticks(range(9), ['ON' + t['originating_scan'].replace('epoch', '').replace('_on', '') + ' #' + str(t['display_rank']) for t in tracks], fontsize=8)
        for i, track in enumerate(tracks):
            for j in range(6):
                ax.text(j, i, f'{matrix[i,j]:.3g}', ha='center', va='center', fontsize=7,
                    color='white' if abs(matrix[i,j]) > .7 * v else 'black')
            ax.add_patch(Rectangle((SCANS.index(track['originating_scan']) - .5, i - .5), 1, 1, fill=False, edgecolor='black', lw=1.5))
        ax.set_title(family['job_id'])
        fig.colorbar(im, ax=ax, shrink=.9, label='Native-row-normalized signed residual')
    fig.suptitle('54 frozen tracks in six scans · outlined selection ON · post-search same-visit context\nEach job panel has its own full residual scale; colors are not calibrated SNR', fontsize=13)
    fig.savefig(out / 'FROZEN_TRACK_SCAN_CONTEXT.png', dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(2, 3, figsize=(16, 9), constrained_layout=True)
    colors = dict(zip(ONS, ['#2166ac', '#1b7837', '#762a83']))
    for ax, family in zip(axes.flat, families):
        for group in family['origin_groups']:
            on, entries = group['originating_scan'], group['saved_local_top20_in_existing_rank_order']
            for width, marker in [(1, 'o'), (3, 's')]:
                selected = [t for t in entries if t['width_channels'] == width]
                ax.scatter([t['reference_frequency_hz'] / 1e6 for t in selected], [t['drift_hz_s'] for t in selected],
                    s=22, marker=marker, color=colors[on], alpha=.7,
                    label=on.replace('epoch', 'ON').replace('_on', '') + f' width {width}')
        ax.set_title(family['job_id']); ax.set_xlabel('Reference frequency at each ON midpoint (MHz)')
        ax.set_ylabel('Saved winning drift (Hz/s)'); ax.set_ylim(-4.15, 4.15)
        ax.set_xlim(family['reference_frequency_center_limits_MHz']); ax.ticklabel_format(axis='x', style='plain', useOffset=False)
        ax.legend(fontsize=6, loc='best', ncol=2)
    fig.suptitle('Existing local top20 for each ON in each job · no combined ranking\nCircle: width 1; square: width 3. Nearby reference frequencies have different ON reference times.', fontsize=13)
    fig.savefig(out / 'LOCAL_TOP20_REFERENCE_TRACKS.png', dpi=180)
    plt.close(fig)
    score = summary['saved_fixed_profile_score_distribution']
    lines = ['# Beskrivende gennemgang af seks S2017-interiørfamilier', '',
        'Ingen kvalificeret SETI-detektion er etableret (`qualified_claim=false`). Rapporten bevarer alle seks jobfamilier med hver deres tre lokale ON-top20-lister. De 54 faste top3-profiler giver 324 scanningmålinger og 5.184 gemte tidsrækker. Alt stammer fra samme besøg den 28. april 2017.', '',
        'Native 170 og 172 blev valgt før deres egne nye spektralværdier, mens resultaterne fra native 171 allerede var kendt. Ranglister og profiler blev derimod udvalgt efter søgningen på de samme ON-data. De er ikke blind eller uafhængig bekræftelse.', '',
        f'De valgte 54 profilscores spænder fra {score["minimum"]:.6g} til {score["maximum"]:.6g}. Dette er en række-MAD-standardiseret boksbanescore maksimeret over korrelerede drift/bredde-kombinationer. Den er ikke kalibreret SNR eller falskalarm-sandsynlighed. Der er ikke lavet en samlet top360-rangliste.', '',
        f'Udvælgelses-ON har den største faste middelværdi i {summary["selection_ON_largest_of_six_count"]}/54 profiler og positive middelværdier i begge halvdele i {summary["selection_ON_both_half_means_positive_count"]}/54. Positive rækker i udvælgelses-ON spænder fra {summary["selection_ON_positive_row_min_max"][0]} til {summary["selection_ON_positive_row_min_max"][1]} ud af 16. De øvrige ON-scanninger har positive halvdele i {summary["other_ON_both_half_means_positive_count"]}/108 målinger; OFF i {summary["OFF_both_half_means_positive_count"]}/162.', '',
        f'{summary["all3_ON_both_half_means_positive_track_count"]}/54 faste spor har positive halvdele i alle tre ON-scanninger. Af disse har {summary["all3_ON_positive_half_tracks_with_some_OFF_positive_halves_count"]} også positive halvdele i mindst én OFF. Signer, halvtider og rangdominans er beskrivende egenskaber ved efterudvalgte spor og fungerer ikke som kandidatkrav eller veto.', '',
        'ON/OFF-profiler bruger nøjagtigt den gemte frekvens, drift og bredde ved de faktiske scanningtider. Små residualer på disse præcise OFF-baner kan ikke udelukke nærliggende OFF-struktur. Der er ikke udført OFF-søgning, ny optimering, fit, frekvensforskydning eller astronomisk oprindelsesklassifikation.', '',
        '| Job | ON | Lokale top20 scores, min–maks | Referencefrekvens, MHz, min–maks | Bredde 1/3 | Drift, Hz/s, min–maks |',
        '|---|---|---:|---:|---:|---:|']
    for family in families:
        for group in family['origin_groups']:
            a = group['score_distribution_of_saved_local_top20']; f = group['reference_frequency_center_limits_MHz']; w = group['width_channel_counts']; dr = group['drift_hz_s_min_max']
            lines.append(f'| {family["job_id"]} | {group["originating_scan"]} | {a["minimum"]:.6g}–{a["maximum"]:.6g} | {f[0]:.9f}–{f[1]:.9f} | {w["1"]}/{w["3"]} | {dr[0]:.6g}–{dr[1]:.6g} |')
    lines += ['', 'Referencefrekvenser fra forskellige ON-scanninger gælder forskellige første integrationsmidtpunkter. JSON angiver både gentagne referencekanaler og eksakt gentagen frossen boksgeometri: samme 96 afrundede kanalcentre ved de seks scanningers tidsrækker og samme bredde. Der bruges ingen lighedstolerance eller ny tilpasning; dette er geometri og ikke en test af fysisk oprindelse.', '',
        '| Job | Gentagne eksakte 96-center/breddegrupper på tværs af ON | Faste top3-spor med konstant center i alle 96 rækker |', '|---|---:|---:|']
    for family in families:
        lines.append(f'| {family["job_id"]} | {len(family["repeated_exact_96_sampled_center_and_width_geometry"])} | {sum(t["all96_sampled_center_stationary"] for t in family["fixed_tracks"])} |')
    lines += ['', 'q128 starter i hvert tilfælde ved den geometriske native-chunks frekvensmidte. Den tidligere native 171-linje ved 2300,390625 MHz var kendt før valget af de tilstødende chunks. De geometriske midter er adskilt med 2,9296875 MHz; det er en egenskab ved kildegitteret, ikke en klassifikation af fysisk eller instrumentel årsag.', '',
        '| Native | q128 midterfrekvens, MHz | Eksisterende top20-punkter i q128, ON1/ON2/ON3 | Gemte top3-profiler i q128 | Eksakt stationære ved midterkanalen |', '|---|---:|---:|---:|---:|']
    for context in q128_context:
        qcounts = context['existing_local_top20_q128_counts_per_ON']
        lines.append(f'| {context["native_chunk_index"]} | {context["coarse_chunk_midpoint_frequency_hz"]/1e6:.9f} | {qcounts[ONS[0]]}/{qcounts[ONS[1]]}/{qcounts[ONS[2]]} | {context["saved_top3_q128_profile_count"]} | {context["exact_coarse_center_stationary_saved_top3_count"]} |')
    for context in q128_context:
        for track in context['saved_top3_q128_profiles']:
            profiles = track['scan_profiles']
            means_text = ', '.join(f'{m["mean_center_minus_flank"]:.6g}' for m in profiles)
            halves_text = '; '.join(f'{m["first_eight_mean_center_minus_flank"]:.6g}/{m["last_eight_mean_center_minus_flank"]:.6g}' for m in profiles)
            lines += ['', f'Gemte q128-profiler fra native {context["native_chunk_index"]}, {track["originating_scan"]} rang {track["display_rank"]}: reference {track["reference_frequency_hz"]/1e6:.9f} MHz, drift {track["drift_hz_s"]:.6g} Hz/s, bredde {track["width_channels"]}. Faste middelresidualer i rækkefølgen ON1, OFF1, ON2, OFF2, ON3, OFF3: {means_text}. Første/sidste halvdel: {halves_text}.']
    lines += ['', 'q128-beskrivelsen læser kun eksisterende lokale top20-punkter og gemte top3-profiler. Manglende valg er ikke bevis for stille q128-data. Der er ingen nye patches, justeringer eller fits, og eventuelt fælles ON/OFF-struktur er ikke uafhængig replikation eller en kildeklassifikation.', '',
        'De 54 profiler er udvælgelsesinstanser, ikke nødvendigvis 54 forskellige kildekanaler eller uafhængige fysiske spor. Geometriske dubletter beholdes synligt i materialet.', '',
        'Hver ny native-chunk dækker q1–254 én gang: 1.040.384 referencekanaler pr. ON, svarende til 99,21875% af 1.048.576-kanals chunken. De seks job giver 1.524 ON-kort, 6.242.304 carrier/origin-maksima og 9.800.417.280 korrelerede drift/bredde-kombinationer; tallene er ikke uafhængige forsøg. De nye 192 eksakte kilderanges gav 597.792.529 BODY-bytes. Boundary-profilerne og den tidligere native 171-familie behandles separat.', '',
        'Profilresidualer bruger hele den native float32-rækkes median før float64-promovering og en fast flankemedian uden for ±3 kanaler inden for ±64. Detektorscores bruger den enkelte 4.096-kanals kerne og række-MAD. De to størrelser har forskellige normaliseringer og er ikke fluxmål. Driftgitteret er −4 til +4 Hz/s i 785 trin, bredder 1 og 3 kanaler (2,793968 og 8,381903 Hz).', '',
        'FROZEN_TRACK_SCAN_CONTEXT.png viser alle 324 middelværdier med hver sin fulde skala pr. job; rammer markerer den ON-scanning, der udvalgte sporet. LOCAL_TOP20_REFERENCE_TRACKS.png viser de eksisterende lokale top20-punkter. CSV og JSON bevarer alle identiteter, signerede residualer, positive rækkeantal, halvmidler, tidsrækker og faktisk læste input-byte-pins.', '',
        f'Provenance: faktisk interiør-QA `{args.expected_interior_QA_sha256}`; kilde-QA `{SOURCE_QA_SHA}`; acquisition `{ACQUISITION_SHA}`. Søgefreeze `{qa["public_freeze_commit"]}`; QA-freeze `{qa["qa_public_freeze_commit"]}`. Den empiriske QA kontrollerede 668.736 patch-celler bitvist. Denne rapport læser kun de QA-autentificerede JSON-resultater og åbner ingen H5/NPZ eller teleskopkilder.', '',
        'Der foreligger ingen blind bekræftelse, kalibreret falskalarmrate eller generel nulkonklusion. S2017-frekvenserne er ikke samme-frekvens-replikation af 2016 L-band. Tidligere fejltilstande og beskyttede 2016-holdouts er bevaret.', '']
    with (out / 'RAPPORT_DA.md').open('x', encoding='utf8') as handle:
        handle.write('\n'.join(lines))
    for relative, expected in pins.items():
        observed_raw = (root / relative).read_bytes()
        require({'sha256': sha(observed_raw), 'bytes': len(observed_raw)} == expected, 'Read input changed before export completion')
    use = {'process_CPU_seconds': time.process_time(), 'wall_seconds': time.monotonic() - started,
        'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    require(use['process_CPU_seconds'] <= CPU_CAP and use['wall_seconds'] <= WALL_CAP and use['peak_RSS_bytes'] <= RAM_CAP, 'Descriptive export resource guard exceeded')
    outputs = {p.name: {'sha256': sha(p.read_bytes()), 'bytes': p.stat().st_size} for p in sorted(out.iterdir())}
    save_json(out / 'INTERPRETATION_RECEIPT.json', {'schema': 'SETI_S2017_SIX_INTERIOR_SAVED_JSON_INTERPRETATION_RECEIPT_V1',
        'status': report['status'], 'qualified_claim': False,
        'interpretation_script_sha256': sha(self_raw), 'actual_interior_QA_sha256': args.expected_interior_QA_sha256,
        'source_QA_sha256': SOURCE_QA_SHA, 'acquisition_receipt_sha256': ACQUISITION_SHA,
        'search_public_freeze_commit': qa['public_freeze_commit'], 'QA_public_freeze_commit': qa['qa_public_freeze_commit'],
        'input_pins': pins, 'output_pins': outputs, 'counts': report['counts'], 'source_H5_or_NPZ_opened': False,
        'detector_or_score_rerun': False, 'new_HTTP_requests': 0, 'fits_OFF_veto_or_calibrated_SNR_FAP': False, **use})
    signal.alarm(0)
    print(json.dumps({'status': report['status'], 'output_directory': str(out),
        'receipt_sha256': sha((out / 'INTERPRETATION_RECEIPT.json').read_bytes()), 'counts': report['counts']}))


if __name__ == '__main__':
    main()
