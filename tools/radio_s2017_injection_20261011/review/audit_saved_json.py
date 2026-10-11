"""Independent reconciliation of frozen injection JSON; no detector/NPZ/H5.

Root GO followed actual COMPLETE jobs and numerical QA before this audit.
Checks every saved case and every summary cell; invents no recovery criteria.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

BASE = 'analysis/s2017_injection_20261011'
QA = BASE + '/results/review/QA_RECEIPT.json'
SUMMARY = BASE + '/results/summary/SUMMARY.json'
RECEIPT = BASE + '/results/summary/SUMMARY_RECEIPT.json'
EXPECTED = {QA: 'f9deeaf7fe096484d8fe144aae7c0510a4e2aa77d9454976c1081cdeac0c8551',
    SUMMARY: 'e02dd1500a2cb897eeb00592ab272c36f376e303efa240e5e56b88c36d886afc',
    RECEIPT: 'f86748b470c7e74a5d0509e4dd14d50f0bb6c9212d86b512bea8c861f17f831c'}
SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
DOMAINS = ('local_window_winner', 'nearest_reference_carrier_winner', 'full_core_winner')
LOCAL = 'local_known_truth_nominal_width1_matched_tuple_threshold_crossing_at10'
FULL = 'full_core_rank1_nominal_width1_matched_tuple_threshold_crossing_at10'
FLAGS = ('center_geometry_within_one_channel_all16', 'positive_interval_overlap_all16',
    'exact_injected_width_match', 'score_at_least_operational10')
LABELS = (LOCAL, FULL, 'zero_already_center_compatible_at_operational10',
    'zero_full_core_already_center_compatible_at_operational10')
C0, CORE, FCH1, DF, TSAMP = 179306496, 4096, 2802832031.25, -2.7939677238464355, 18.253611008


def require(ok, message):
    if not ok:
        raise ValueError(message)


def unique(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, 'Duplicate JSON field')
        value[key] = item
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--root-go', action='store_true', required=True)
    args = parser.parse_args()
    require(args.root_go, 'Actual COMPLETE+QA root GO required')
    root, pins = args.root.resolve(), {}

    def read(name):
        path = root / name
        require(path.suffix == '.json' and path.resolve().is_relative_to(root), 'JSON-only confined input')
        raw = path.read_bytes()
        pin = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        if name in EXPECTED:
            require(pin['sha256'] == EXPECTED[name], 'Exact completed input differs')
        pins[name] = pin
        return json.loads(raw, object_pairs_hook=unique,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError('Nonfinite JSON')))

    qa, receipt, summary = read(QA), read(RECEIPT), read(SUMMARY)
    require(qa['status'] == 'PASS450_MAPS540_DIAGNOSTICS_RAW_ARITHMETIC_AND_ROUNDED_SUPPORT_NO_DETECTOR_RERUN', 'Actual QA status differs')
    require(receipt['status'] == 'COMPLETE_CREATE_ONLY_ALL_GROUP_SUMMARY'
        and receipt['output_pin'] == pins[SUMMARY]
        and summary['actual_QA_receipt_sha256'] == EXPECTED[QA], 'Summary actual completion binding differs')
    for name, expected in receipt['input_byte_pins'].items():
        if name not in pins:
            read(name)
        require(pins[name] == expected, 'Summary read input changed')
    source_name = 'analysis/next_visit/S2017_MIDPOINT_SOURCE_MANIFEST.json'
    source = read(source_name)
    require(pins[source_name] == qa['input_byte_pins'][source_name], 'Actual QA source metadata binding differs')
    headers = {item['label']: item['current_header']['data_attributes'] for item in source['sources']}
    originals = []
    for job in ('offcenter', 'known_center_competitor'):
        prefix = BASE + '/results/' + job
        execution_name, diag_name = prefix + '/EXECUTION_RECEIPT.json', prefix + '/DIAGNOSTICS.json'
        execution, diagnostics = read(execution_name), read(diag_name)
        require(pins[execution_name] == qa['input_byte_pins'][execution_name]
            and pins[diag_name] == qa['input_byte_pins'][diag_name]
            and execution['status'] == 'COMPLETE_PROSPECTIVE_RAW_POWER_INJECTION_BENCHMARK_EXPLORATORY_ONLY'
            and execution['public_freeze_commit'] == qa['public_freeze_commit'], 'Actual completed job differs')
        originals.extend(diagnostics['records'])
    require(originals == summary['all540_original_diagnostics_preserved'], 'Original records altered in summary')
    expected_ids = {(q, width, amp, di, scan) for q in (64, 128, 192) for width in (1, 9)
        for amp in (0, 1, 3, 6, 12) for di in (245, 392, 539) for scan in SCANS}
    observed, zero_map_ids, map_ids = set(), {}, {}
    for record in originals:
        q, width, amp, di, scan = (record[k] for k in ('core_q', 'injected_width_channels',
            'amplitude_per_cell_baseline_MAD_units', 'injected_drift_index', 'scan_id'))
        identity = (q, width, amp, di, scan)
        require(identity in expected_ids and identity not in observed, 'Grid identity duplicate/omission')
        observed.add(identity)
        truth = record['rounded_truth_centers']
        times = [j * TSAMP for j in range(16)]
        require(record['role'] == ('off' if SCANS.index(scan) % 2 else 'on')
            and record['relative_row_midpoint_seconds'] == times
            and record['actual_first_midpoint_MJD'] == headers[scan]['tstart'] + .5 * TSAMP / 86400
            and record['truth_reference_source_channel'] == C0 + q * CORE + 2048
            and truth == [round(record['truth_reference_source_channel'] + record['injected_drift_hz_s'] * t / DF) for t in times],
            'Actual per-scan frozen truth geometry differs')
        require(record['truth_score_delta_from_zero'] == record['modified_truth_score'] - record['baseline_truth_score'], 'Truth delta differs')
        require(record['total_added_raw_power_per_row'] == [width * v for v in record['raw_power_increment_per_row']], 'Per-cell/total injected row power differs')
        for domain in (*DOMAINS, 'matched_zero_local_window_winner', 'matched_zero_full_core_winner'):
            value = record[domain]
            centers, winning_width = value['rounded_absolute_centers'], value['width_channels']
            base = (value['frequency_hz_at_own_first_midpoint'] - FCH1) / DF
            require(centers == [round(base + value['drift_hz_s'] * t / DF) for t in times], 'Winning rounded geometry differs')
            errors = [a - b for a, b in zip(centers, truth)]
            overlaps = [max(0, min(a + winning_width // 2, b + width // 2) - max(a - winning_width // 2, b - width // 2) + 1)
                for a, b in zip(centers, truth)]
            require(value['center_errors_channels'] == errors and value['overlap_channels_by_row'] == overlaps
                and value['overlap_fraction_of_winning_box_by_row'] == [v / winning_width for v in overlaps]
                and value['center_geometry_within_one_channel_all16'] == all(abs(v) <= 1 for v in errors)
                and value['positive_interval_overlap_all16'] == all(v > 0 for v in overlaps)
                and value['exact_injected_width_match'] == (winning_width == width)
                and value['score_at_least_operational10'] == (value['score'] >= 10)
                and value['score_delta_same_tuple_from_zero'] == value['score'] - value['matched_zero_score_same_winning_tuple'],
                'Saved winning flags/score arithmetic differs')
        for domain, zero_domain, already_name, label in ((DOMAINS[0], 'matched_zero_local_window_winner', LABELS[2], LOCAL),
            (DOMAINS[2], 'matched_zero_full_core_winner', LABELS[3], FULL)):
            value, zero = record[domain], record[zero_domain]
            already = zero['center_geometry_within_one_channel_all16'] and zero['score'] >= 10
            expected = (amp > 0 and width == 1 and value['exact_injected_width_match']
                and value['center_geometry_within_one_channel_all16'] and value['score'] >= 10
                and record['truth_score_delta_from_zero'] > 0 and not already
                and value['matched_zero_score_same_winning_tuple'] < 10 and value['score_delta_same_tuple_from_zero'] > 0)
            require(record[already_name] == already and record[label] == expected, 'Frozen matched-tuple threshold label differs')
        require(record['baseline_all_compatible_templates_below10_proven'] is False
            and record['width9_is_template_mismatch_stress'] == (width == 9)
            and record['nominal_width9_recovery_available_in_search_family'] is False, 'Unsupported qualification differs')
        if amp == 0:
            require(record['truth_score_delta_from_zero'] == 0 and not record[LOCAL] and not record[FULL], 'Zero credited as injection')
        for target, id_name, sha_name in ((map_ids, 'map_id', 'map_sha256'), (zero_map_ids, 'matched_zero_map_id', 'matched_zero_map_sha256')):
            key, value = record[id_name], record[sha_name]
            require(key not in target or target[key] == value, 'Map alias byte identity differs')
            target[key] = value
    require(observed == expected_ids and len(originals) == 540 and len(map_ids) == 450 and len(zero_map_ids) == 18, 'Full inventory differs')

    def verify_group(saved, rows):
        require(saved['logical_records'] == saved['flag_denominator'] == len(rows), 'Conditional denominator differs')
        for domain in DOMAINS:
            values = [r[domain] for r in rows]
            expected = {name: sum(v[name] for v in values) for name in FLAGS}
            expected['center_geometry_and_operational10'] = sum(v[FLAGS[0]] and v[FLAGS[3]] for v in values)
            expected['support_overlap_and_operational10'] = sum(v[FLAGS[1]] and v[FLAGS[3]] for v in values)
            require(saved['flag_counts'][domain] == expected, 'Summary flag numerator differs')
            for name, field in (('modified_maximum_score', 'score'), ('same_tuple_matched_zero_score', 'matched_zero_score_same_winning_tuple'),
                ('same_tuple_score_delta_from_zero', 'score_delta_same_tuple_from_zero')):
                verify_stats(saved['saved_score_statistics'][domain][name], [v[field] for v in values])
        for name in LABELS:
            require(saved['flag_counts'][name] == sum(r[name] for r in rows), 'Summary matched label differs')
        for name, stat in saved['saved_truth_score_statistics'].items():
            verify_stats(stat, [r[name] for r in rows])

    def verify_stats(saved, values):
        require(all(math.isfinite(v) for v in values), 'Nonfinite statistic')
        require(saved == {'count': len(values), 'minimum': min(values), 'maximum': max(values), 'mean': math.fsum(values) / len(values)},
            'Saved finite distribution differs')

    group_ids, compact_table = set(), []
    for group in summary['all_predeclared_groups']:
        key = (group['core_q'], group['injected_width_channels'], group['amplitude_per_cell_baseline_MAD_units'])
        require(key not in group_ids, 'Duplicate summary group')
        group_ids.add(key)
        members = [r for r in originals if (r['core_q'], r['injected_width_channels'], r['amplitude_per_cell_baseline_MAD_units']) == key]
        require(len(members) == 18, 'Incomplete group')
        verify_group(group, members)
        for role, subset in group['role_subsets'].items():
            rows = [r for r in members if r['role'] == role]; require(len(rows) == 9, 'Role subset differs'); verify_group(subset, rows)
        for scan, subset in group['scan_subsets'].items():
            rows = [r for r in members if r['scan_id'] == scan]; require(len(rows) == 3, 'Scan subset differs'); verify_group(subset, rows)
        compact_table.append({'q': key[0], 'injected_width': key[1], 'A_per_cell': key[2], 'cases': 18,
            'local_support_and10': group['flag_counts'][DOMAINS[0]]['support_overlap_and_operational10'],
            'nearest_support_and10': group['flag_counts'][DOMAINS[1]]['support_overlap_and_operational10'],
            'rank1_support_and10': group['flag_counts'][DOMAINS[2]]['support_overlap_and_operational10'],
            'local_width1_tuple_crossings': group['flag_counts'][LOCAL], 'rank1_width1_tuple_crossings': group['flag_counts'][FULL],
            'truth_delta_min_max': [group['saved_truth_score_statistics']['truth_score_delta_from_zero'][k] for k in ('minimum', 'maximum')]})
    require(group_ids == {(q, w, a) for q in (64, 128, 192) for w in (1, 9) for a in (0, 1, 3, 6, 12)}, 'All30 groups required')
    q128 = [r for r in originals if r['core_q'] == 128]
    q128_global = {r['full_core_winner']['reference_source_channel'] for r in q128}
    audit = {'schema': 'SETI_S2017_INJECTION_INDEPENDENT_SAVED_JSON_LOGICAL_AUDIT_V1',
        'status': 'PASS_ALL540_CASES30_GROUPS240_ROLE_SCAN_SUBSETS_AUTHENTICATED_JSON_ONLY',
        'read_input_byte_pins': pins, 'actual_QA_sha256': EXPECTED[QA], 'summary_receipt_sha256': EXPECTED[RECEIPT],
        'code_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'counts': {'original_records': 540, 'positive_amplitude_records': sum(r['amplitude_per_cell_baseline_MAD_units'] > 0 for r in originals),
            'zero_geometry_queries': sum(r['amplitude_per_cell_baseline_MAD_units'] == 0 for r in originals), 'distinct_maps': 450,
            'shared_zero_maps': 18, 'groups': 30, 'role_subsets': 60, 'scan_subsets': 180},
        'all30_reconciled_groups': compact_table, 'q128_full_core_rank1_reference_channel_set': sorted(q128_global),
        'q128_rank1_scores_min_max': [min(r['full_core_winner']['score'] for r in q128), max(r['full_core_winner']['score'] for r in q128)],
        'no_H5_NPZ_detector_score_bank_or_new_gate': True,
        'limits': ['Logical reconciliation of saved authenticated results, not independent detector-score reproduction.',
            'Strict flags remain the predeclared finite conditional diagnostics, not detection probabilities, physical flux or calibrated FAP.']}
    for name, expected in pins.items():
        raw = (root / name).read_bytes(); require({'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)} == expected, 'Read input changed')
    out = root / 'continuation_20261011/metadata/injection_review/SAVED_JSON_LOGICAL_AUDIT.json'
    with out.open('x') as handle:
        json.dump(audit, handle, indent=2); handle.write('\n')
    raw = out.read_bytes()
    print(json.dumps({'path': str(out), 'sha256': hashlib.sha256(raw).hexdigest(), 'status': audit['status'], 'counts': audit['counts'],
        'q128_rank1_channels': audit['q128_full_core_rank1_reference_channel_set']}))


if __name__ == '__main__':
    main()
