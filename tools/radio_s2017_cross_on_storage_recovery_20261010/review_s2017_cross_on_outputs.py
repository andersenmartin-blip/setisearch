#!/usr/bin/env python3
"""One bounded output-only review. Never read original maxima or run matching."""
import hashlib
import io
import json
import math
import os
from pathlib import Path
import resource
import signal
import time

REPO = Path('/workspace/scratch/a8d1e29996d0/setisearch_fullpower')
FAMILY = 'radio_s2017_cross_on_storage_recovery_20261010'
STAGE = REPO / 'results' / FAMILY
OUT = STAGE / 'measurement'
SCOPE = REPO / 'tools' / FAMILY / 'scope.json'
FREEZE = 'ab3915ef936ce5ae7edb9caf226275b0bbfe21af'
SCOPE_SHA = '8b43cb85e15cde702dc02afa0b021083432ce58963897271ed8ba0c59d7cf72f'
SCRIPT_SHA = '4e91ee2495ee898fb77b3c11d7831dd4a37ef32fbb3689115e491688293f5455'
CPU_CAP, WALL_CAP, MEMORY_CAP = 10, 60, 1073741824
RECEIPT = Path('/workspace/scratch/a8d1e29996d0/seti_fullpower_work/recovery_design/continuity_review/S2017_CROSS_ON_STORAGE_ACTUAL_OUTPUT_ONLY_REVIEW.json')
ALLOWED = {SCOPE, STAGE / 'PUBLIC_FREEZE_READBACK.json', STAGE / 'ROOT_OUTER_EXECUTION_RECEIPT.json',
           OUT / 'EXECUTION_RECEIPT.json', OUT / 'TOP1000.json', OUT / 'ALL_MUTUAL_TRIPLES.npy'}


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    started = time.monotonic()
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_CAP, CPU_CAP + 1))
    resource.setrlimit(resource.RLIMIT_AS, (MEMORY_CAP, MEMORY_CAP))
    signal.alarm(WALL_CAP)
    for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[name] = '1'
    import numpy as np
    pins, raw = {}, {}
    for path in ALLOWED:
        check(path.resolve() == path and path.is_file() and not path.is_symlink(), 'Canonical review file required')
        value = path.read_bytes()
        pins[str(path)] = {'path': str(path), 'sha256': hashlib.sha256(value).hexdigest(), 'bytes': len(value)}
        raw[path] = value
    scope = json.loads(raw[SCOPE])
    inner = json.loads(raw[OUT / 'EXECUTION_RECEIPT.json'])
    outer = json.loads(raw[STAGE / 'ROOT_OUTER_EXECUTION_RECEIPT.json'])
    public = json.loads(raw[STAGE / 'PUBLIC_FREEZE_READBACK.json'])
    top = json.loads(raw[OUT / 'TOP1000.json'])
    check(pins[str(SCOPE)]['sha256'] == SCOPE_SHA == inner['scope_sha256'], 'Exact public scope binding failed')
    check(inner['script_sha256'] == scope['script_sha256'] == SCRIPT_SHA, 'Reviewed script identity failed')
    check(inner['public_freeze_commit'] == outer['freeze_commit'] == public['public_freeze_commit'] == FREEZE,
          'Public freeze binding failed')
    check(public['status'] == 'PASS_TWENTY_THREE_EXACT_UTF8_PUBLIC_FREEZE_READBACKS'
          and len(public['files']) == 23 and all(item['exact_utf8_readback'] is True for item in public['files']),
          'Actual public readback metadata failed')
    published = {item['path']: item for item in public['files']}
    check(published[str(SCOPE.relative_to(REPO))]['sha256'] == SCOPE_SHA
          and published['tools/' + FAMILY + '/match_saved.py']['sha256'] == SCRIPT_SHA,
          'Exact path-to-public source/scope pins failed')
    check(inner['status'] == 'COMPLETE_S2017_SAVED_MAXIMA_MUTUAL_CROSS_ON_EXPLORATORY_ONLY'
          and outer['status'] == 'PASS_ONE_CHILD_CLOSED_COMPLETE_AND_OUTER_RESOURCE_CAPS'
          and outer['child_exit_code'] == 0 and outer['child_timed_out'] is False
          and outer['automatic_retry_performed'] is False, 'Actual original closed execution status failed')
    check(outer['inner_terminal_sha256'] == pins[str(OUT / 'EXECUTION_RECEIPT.json')]['sha256']
          and outer['inner_terminal_status'] == inner['status'], 'Outer to inner terminal byte binding failed')
    for receipt, cpu, wall, rss in [(inner, 'process_CPU_seconds', 'wall_seconds', 'peak_RSS_bytes'),
                                   (outer, 'child_process_CPU_seconds', 'child_wall_seconds', 'child_peak_RSS_bytes')]:
        check(0 <= receipt[cpu] <= 120 and 0 <= receipt[wall] <= 1800
              and 0 <= receipt[rss] <= 1073741824, 'Actual resource cap failed')
    for key in ('detector_reexecuted', 'preprocessing_reexecuted', 'profiles_measured', 'source_HDF5_opened'):
        check(inner[key] is False, 'Unauthorized processing reported')
    check(inner['new_HTTP_requests'] == inner['new_source_BODY_bytes'] == inner['cost_DKK'] == 0,
          'New source request/body/cost reported')
    check(not (OUT / 'FAILURE_RECEIPT.json').exists() and not (STAGE / 'PREFLIGHT_FAILURE_RECEIPT.json').exists(),
          'Conflicting failure status present')
    ons = scope['scan_order']
    n = 254 * 4096
    check(ons == ['epoch1_on', 'epoch2_on', 'epoch3_on'] and scope['records_per_ON'] == n
          and inner['records_per_ON'] == n and inner['carrier_maximum_records'] == 3 * n
          and inner['maps_verified'] == 762 and inner['completed_directions'] == 6, 'Count/frame contract failed')
    expected_directions = {ons[a] + '_to_' + ons[b] for a in range(3) for b in range(3) if a != b}
    check(set(inner['directional_neighbor_counts']) == expected_directions
          and all(inner['matched_triples'] <= count <= n for count in inner['directional_neighbor_counts'].values()),
          'Directional count metadata failed')
    for name, key in [('ALL_MUTUAL_TRIPLES.npy', 'relation_pin'), ('TOP1000.json', 'top1000_pin')]:
        check(inner[key] == pins[str(OUT / name)], 'Output SHA/size/path differs from terminal pin')
    relation = np.load(io.BytesIO(raw[OUT / 'ALL_MUTUAL_TRIPLES.npy']), allow_pickle=False)
    count = len(relation)
    check(relation.dtype.str == '<i4' and relation.ndim == 2 and relation.shape == (count, 3)
          and count <= n and inner['relation_shape'] == [count, 3] and inner['relation_dtype'] == '<i4',
          'Relation shape/dtype differs')
    check(inner['relation_columns'] == ons and inner['matched_triples'] == count, 'Relation counts/columns differ')
    check(not count or (int(relation.min()) >= 0 and int(relation.max()) < n), 'Relation index outside original vector domain')
    check(all(np.unique(relation[:, column]).size == count for column in range(3)), 'Relation is not one-to-one')
    check(count < 2 or np.all(np.diff(relation[:, 0].astype(np.int64)) > 0), 'ON1 emitted relation order differs')
    relation_rows = {tuple(int(index) for index in row) for row in relation}
    check(len(relation_rows) == count, 'Repeated relation row')
    check(top['schema'] == scope['schema'] and top['family_id'] == inner['family_id'] == FAMILY
          and top['matched_triples'] == count and top['fixed_display_cap'] == 1000
          and top['displayed_records'] == inner['displayed_records'] == min(count, 1000)
          and top['display_truncated'] is (count > 1000), 'Top count/truncation contract differs')
    records = top['records']
    check(len(records) == min(count, 1000), 'Display record count failed')
    tau, common, anchor = scope['frequency_tolerance_hz'], scope['common_reference_seconds_from_anchor'], scope['MJD_anchor']
    check(top['frequency_tolerance_hz'] == tau and top['common_reference_seconds_from_anchor'] == common
          and top['MJD_anchor'] == anchor and top['drift_index_tolerance'] == 1, 'Top geometry metadata differs')
    grid = np.linspace(-4.0, 4.0, 785, dtype=np.float64)
    check(hashlib.sha256(grid.astype('<f8', copy=False).tobytes()).hexdigest()
          == scope['grid_float64_le_sha256'] == inner['grid_float64_le_sha256'], 'Declared fixed grid bytes differ')
    emitted, ordering, width_patterns = set(), [], {}
    same_channel = stationary = unequal_widths = 0
    max_frequency_gap = 0.0
    for rank, row in enumerate(records, 1):
        check(row['display_rank'] == rank and row['match_id'] == FAMILY + '_rank_%04d' % rank
              and row['status'] == 'EXPLORATORY_ASSOCIATION_UNCLASSIFIED', 'Rank or scientific status failed')
        members = row['members']
        check(len(members) == 3 and [member['scan_id'] for member in members] == ons, 'Member scan order failed')
        indices, channels, frequencies, drifts, scores, widths = [], [], [], [], [], []
        for si, member in enumerate(members):
            index, key = member['global_carrier_vector_index'], member['original_key']
            check(type(index) is int and 0 <= index < n, 'Member vector index failed')
            channel = scope['source_channel0'] + 4096 + index
            ki, width = key['drift_grid_index'], key['width_channels']
            check(type(ki) is int and 0 <= ki < 785 and type(width) is int and width in (1, 3), 'Original winning grid/width key failed')
            reference = scope['ON_reference_seconds_from_anchor'][si]
            check(key['source_reference_channel'] == channel and key['scan_id'] == ons[si]
                  and key['visit'] == '2017-04-28 / AGBT17A_999_55'
                  and key['reference_seconds_from_anchor'] == reference and key['drift_hz_s'] == float(grid[ki])
                  and member['core_q'] == (channel - scope['source_channel0']) // 4096, 'Original member key/frame failed')
            original_frequency = scope['fch1_hz'] + scope['df_hz'] * channel
            projected_frequency = original_frequency + float(grid[ki]) * (common - reference)
            check(member['original_reference_frequency_hz'] == original_frequency
                  and member['frequency_hz_at_common_reference'] == projected_frequency, 'Scalar projection metadata failed')
            score = member['saved_maximum_robust_box_track_score']
            check(math.isfinite(score), 'Nonfinite copied score')
            indices.append(index); channels.append(channel); frequencies.append(projected_frequency)
            drifts.append(ki); scores.append(score); widths.append(width)
        triple = tuple(indices)
        check(triple in relation_rows and triple not in emitted, 'Top membership or repetition failed')
        emitted.add(triple)
        minimum = min(scores)
        check(row['descriptive_minimum_saved_score'] == minimum, 'Descriptive minimum of saved scores differs')
        ordering.append((-minimum, *channels))
        check(max(frequencies) - min(frequencies) <= tau and max(drifts) - min(drifts) <= 1, 'Full triple geometry failed')
        check(len(row['pairwise_gaps']) == 3, 'Pairwise gap inventory differs')
        for gap, (a, b) in zip(row['pairwise_gaps'], [(0, 1), (0, 2), (1, 2)]):
            fg, dg = abs(frequencies[a] - frequencies[b]), abs(drifts[a] - drifts[b])
            check(gap['ON_pair'] == [ons[a], ons[b]] and gap['absolute_frequency_gap_hz'] == fg
                  and gap['absolute_drift_grid_index_gap'] == dg and fg <= tau and dg <= 1,
                  'Exact declared pairwise gap/window differs')
            max_frequency_gap = max(max_frequency_gap, fg)
        same_channel += len(set(channels)) == 1
        stationary += all(float(grid[ki]) == 0.0 for ki in drifts)
        unequal_widths += len(set(widths)) > 1
        pattern = ','.join(str(width) for width in widths)
        width_patterns[pattern] = width_patterns.get(pattern, 0) + 1
    check(ordering == sorted(ordering), 'Displayed descriptive min-score/channel-triple ordering failed')
    check(count > 1000 or emitted == relation_rows, 'Untruncated top does not cover every relation row')
    check(top['limitations'] == inner['limitations'], 'Scientific limitation metadata differs')
    limits = ' '.join(top['limitations']).lower()
    for phrase in ('same 2017 visit', 'not an independent test', 'secondary hypotheses', 'not calibrated',
                   'not an exhaustive', 'do not establish origin', 'display ordering only', 'no score threshold',
                   'candidate qualification', 'no consensus track', 'off veto', 'profile measurement', 'fail_closed'):
        check(phrase in limits, 'Required scientific limitation absent: ' + phrase)
    # Finite end-readback only of the six explicitly allowed output/metadata files.
    for path in ALLOWED:
        check(hashlib.sha256(path.read_bytes()).hexdigest() == pins[str(path)]['sha256'], 'Review input changed')
    check(time.process_time() < CPU_CAP and time.monotonic() - started < WALL_CAP
          and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024 <= MEMORY_CAP, 'Own review cap failed')
    summary = {'matched_and_displayed_triples': count, 'display_truncated': count > 1000,
               'same_original_reference_channel_all_three_count': same_channel,
               'all_three_saved_winners_stationary_count': stationary,
               'unequal_original_member_width_count': unequal_widths,
               'width_patterns_ON1_ON2_ON3': width_patterns, 'maximum_declared_pairwise_frequency_gap_hz': max_frequency_gap,
               'frequency_tolerance_hz': tau,
               'selected_display_rows': [{key: row[key] for key in ('display_rank', 'descriptive_minimum_saved_score', 'members', 'pairwise_gaps')}
                                         for row in records[:3]],
               'lowest_displayed_minimum_saved_score': records[-1]['descriptive_minimum_saved_score'] if records else None}
    receipt = {'status': 'PASS_BOUNDED_OUTPUT_ONLY_636_RELATION_TOP_AND_ACTUAL_EXECUTION_METADATA_CONTRACTS',
               'input_pins': pins, 'public_freeze_commit': FREEZE, 'source_script_sha256': SCRIPT_SHA,
               'scope_sha256': SCOPE_SHA, 'closed_child_outer_resources': {key: outer[key] for key in
                    ('child_process_CPU_seconds', 'child_wall_seconds', 'child_peak_RSS_bytes')},
               'all_contract_checks_passed': True, 'scalar_aggregate_descriptive_only': summary,
               'checked': ['Exact frozen source/scope path pins from actual public readback and inner/outer receipts.',
                           'Actual closed original COMPLETE, outer cap PASS, no failure and no new H5/detector/profile/source requests.',
                           'Relation SHA/size/<i4 Nx3, bounds, uniqueness in each column and increasing ON1 emission order.',
                           'All displayed members map to exact relation rows, copied channel/grid/width/time keys, projected scalar frequencies and exact gaps.',
                           'All636 rows are displayed once, min of copied scores and deterministic display ordering; no truncation.',
                           'Same-visit descriptive limitations, no OFF veto/calibrated joint statistic/origin/candidate qualification.'],
               'review_limits': ['No original maximum map, raw source, H5, normalization or profile array read.',
                                'No target/helper import or invocation, detector/preprocessing/profile or six directed-nearest recomputation.',
                                'Saved member scores are checked internally and bound to authenticated output bytes; not independently reread from original arrays.',
                                'This verifies output contracts and descriptive math, not independent sky detection or calibration.'],
               'review_code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'synthetic_tests_reexecuted': False, 'original_input_maps_read': False,
               'nearest_matching_reexecuted': False, 'only_new_relation_array_decoded': True,
               'CPU_cap_s': CPU_CAP, 'wall_cap_s': WALL_CAP, 'memory_cap_bytes': MEMORY_CAP,
               'process_CPU_seconds': time.process_time(), 'wall_seconds': time.monotonic() - started,
               'peak_RSS_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024}
    with RECEIPT.open('x', encoding='utf-8') as handle:
        json.dump(receipt, handle, indent=2, allow_nan=False); handle.write('\n')
    signal.alarm(0)
    print(json.dumps({'status': receipt['status'], 'receipt': str(RECEIPT), 'receipt_sha256': hashlib.sha256(RECEIPT.read_bytes()).hexdigest(),
                      'receipt_bytes': RECEIPT.stat().st_size, 'scalar_aggregate': {key: value for key, value in summary.items()
                      if key != 'selected_display_rows'}, 'rank1_min': records[0]['descriptive_minimum_saved_score'],
                      'rank2_min': records[1]['descriptive_minimum_saved_score'],
                      'process_CPU_seconds': time.process_time()}))


if __name__ == '__main__':
    main()
