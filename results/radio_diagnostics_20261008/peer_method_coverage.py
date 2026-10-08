"""Audit new METHOD summaries against three immutable original report products.

Pure standard library. No maps, original power, RNG or experiment modules are
opened. Independent Decimal arithmetic verifies descriptive ratios/medians.
"""
import csv
import hashlib
import json
from decimal import Decimal, getcontext
from itertools import product
from pathlib import Path

getcontext().prec = 45
OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
INPUT = ROOT / 'results/radio_pilot_method_report_20261008'
SOURCE = '13131757641c06d7bfcb10790a79811c750b1178'
EXPECTED = {
    'method_cells.csv': ('ee77abf87b5bd83d69124fc1c5246161cd1a009e', '59bbd848364ddf68045dd718ab56adeb81ac9322bbc1ecd17ad44d38f44447b7', 22537),
    'report_data.json': ('c94dd0612988e7ccc3bf45cb6116a058e6bc9773', 'e11b2c892f63e9033468f15aeec8bd57ebfeaf3cae4f789e30260497a4af1ab4', 284875),
    'report_artifact_manifest.json': ('513a3e1523610962dc6507870a1eeb2084277b1d', 'e71fc66034e86d23bb751d41735203925c6f2ea86b7549006801caea2ed1d640', 3097),
}
TABLES = ('method_active_ON_scores.csv', 'method_case_coverage.csv',
          'method_coverage_groups.csv', 'method_missed_active_ON_scans.csv')
PREFIX = 'SETI_RADIO_PILOT_20261008_METHOD_STUDY:method_signal:'
EPS = Decimal('0.000000000001')
scalar_checks = 0


def read(path):
    return json.loads(path.read_bytes())


def digests(path):
    data = path.read_bytes()
    return {'git_blob_sha1': hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest(),
            'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}


def dec(value):
    return Decimal(str(value))


def middle(values):
    ordered = sorted(map(dec, values))
    n = len(ordered)
    assert n
    return (ordered[(n - 1) // 2] + ordered[n // 2]) / 2


def check(actual, expected, context):
    global scalar_checks
    if isinstance(expected, dict):
        assert set(actual) == set(expected), (context, set(actual), set(expected))
        for key in expected:
            check(actual[key], expected[key], (context, key))
    elif isinstance(expected, list):
        assert len(actual) == len(expected), (context, len(actual), len(expected))
        for index, (a, e) in enumerate(zip(actual, expected)):
            check(a, e, (context, index))
    else:
        scalar_checks += 1
        if isinstance(expected, bool):
            assert actual == expected or isinstance(actual, str) and actual == str(expected), (context, actual, expected)
        elif isinstance(expected, (int, float, Decimal)):
            assert abs(dec(actual) - dec(expected)) <= EPS, (context, actual, expected)
        else:
            assert actual == expected, (context, actual, expected)


def csv_read(path):
    with path.open(newline='') as handle:
        return list(csv.DictReader(handle))


def group_matches(cell, label):
    if label == 'ALL_64_CASES':
        return True
    for condition in label.split(';'):
        field, value = condition.split('=', 1)
        assert field in ('nominal_ideal_box_score', 'activity', 'drift_hz_s',
                         'intrinsic_width_channels', 'reference_native_offset')
        if field == 'activity':
            if cell[field] != value:
                return False
        elif dec(cell[field]) != dec(value):
            return False
    return True


def main():
    result = read(OUT / 'METHOD_COVERAGE.json')
    assert result['status'] == 'DESCRIPTIVE_RETAINED_METHOD_COVERAGE_COMPLETE'
    provenance = result['provenance']
    assert provenance['source_commit'] == SOURCE
    for name in ('new_draws', 'new_scores', 'original_map_archives_opened'):
        assert provenance[name] == 0
    assert provenance['thresholds_changed'] is False and provenance['qualification'] is False
    receipt = read(OUT / 'RESTORED_METHOD_REPORT_INPUTS.json')
    assert receipt['source_commit'] == SOURCE and receipt['all_Git_blob_SHA1_verified'] is True
    assert receipt['new_scores'] is False and len(receipt['records']) == 3
    restoration = {Path(record['path']).name: record for record in receipt['records']}
    verified = []
    for name, (git_hash, sha, size) in EXPECTED.items():
        expected = {'git_blob_sha1': git_hash, 'sha256': sha, 'bytes': size}
        assert digests(INPUT / name) == expected
        for key, value in expected.items():
            assert restoration[name][key] == value
        verified.append({'path': str((INPUT / name).relative_to(ROOT)), **expected})
    assert provenance['verified_inputs'] == verified
    check(provenance['restoration_receipt'], {'path': 'results/radio_diagnostics_20261008/RESTORED_METHOD_REPORT_INPUTS.json',
          **digests(OUT / 'RESTORED_METHOD_REPORT_INPUTS.json')}, 'restoration_receipt')
    script_record = provenance['script']
    assert (ROOT / script_record['path']).resolve() == OUT / 'analyze_method_coverage.py'
    assert {key: script_record[key] for key in ('git_blob_sha1', 'sha256', 'bytes')} == digests(OUT / 'analyze_method_coverage.py')
    assert all(value is True for value in provenance['validation'].values())
    manifest = read(INPUT / 'report_artifact_manifest.json')
    for name in ('method_cells.csv', 'report_data.json'):
        assert manifest[name]['SHA256'] == EXPECTED[name][1]
        assert manifest[name]['size_bytes'] == EXPECTED[name][2]

    originals = read(INPUT / 'report_data.json')['method_cells']
    csv_originals = csv_read(INPUT / 'method_cells.csv')
    assert len(originals) == len(csv_originals) == 64
    original_ids = {cell['case_id']: cell for cell in originals}
    assert len(original_ids) == 64 and set(original_ids) == {f'{PREFIX}{i:03d}' for i in range(64)}
    assert len({row['case_id'] for row in csv_originals}) == 64
    for row in csv_originals:
        expected = original_ids[row['case_id']]
        assert set(row) == set(expected)
        for field, value in expected.items():
            if isinstance(value, dict):
                check(json.loads(row[field]), value, ('original_csv_json', row['case_id'], field))
            else:
                check(row[field], value, ('original_csv_json', row['case_id'], field))

    combinations = {(dec(cell['nominal_ideal_box_score']), dec(cell['drift_hz_s']),
                     cell['intrinsic_width_channels'], cell['activity']) for cell in originals}
    assert combinations == set(product(map(dec, (10, 12, 16, 24)), map(dec, (-4, -1.25, 1.25, 4)),
                                      (1, 3), ('single_third_ON', 'all_three_ON')))
    assert len(combinations) == 64
    for placement in (0.25, 1024.25, 3070.75, 4094.75):
        assert sum(cell['reference_native_offset'] == placement for cell in originals) == 16

    expected_scans, expected_cases = [], []
    for index in range(64):
        cell = original_ids[f'{PREFIX}{index:03d}']
        stages = cell['loss_stage_by_active_ON_scan']
        expected_ids = ('epoch3_on',) if cell['activity'] == 'single_third_ON' else ('epoch1_on', 'epoch2_on', 'epoch3_on')
        assert set(stages) == set(expected_ids)
        assert set(cell['ON_global_maximum_robust_score_by_scan']) == {'epoch1_on', 'epoch2_on', 'epoch3_on'}
        successful = [stages[scan] == 'LOCALIZED_SURVIVOR' for scan in expected_ids]
        assert all(stage in ('LOCALIZED_SURVIVOR', 'NO_ON_THRESHOLD_HIT') for stage in stages.values())
        assert all(successful) == cell['final_all_active_recovered']
        assert any(successful) == cell['final_any_active_recovered']
        assert cell['pre_OFF_all_active_recovered'] == cell['final_all_active_recovered']
        assert cell['pre_OFF_any_active_recovered'] == cell['final_any_active_recovered']
        assert cell['ON_threshold_carrier_count'] == cell['surviving_ON_carrier_count']
        case_scores = []
        shared = {field: cell[field] for field in ('case_id', 'nominal_ideal_box_score', 'drift_hz_s',
                  'intrinsic_width_channels', 'activity', 'reference_native_offset')}
        for scan in expected_ids:
            score = dec(cell['ON_global_maximum_robust_score_by_scan'][scan])
            localized = stages[scan] == 'LOCALIZED_SURVIVOR'
            assert score.is_finite() and localized == (score >= 10)
            case_scores.append(score)
            expected_scans.append({**shared, 'scan_id': scan, 'global_maximum_robust_score': score,
                'global_maximum_divided_by_nominal_ideal': score / dec(cell['nominal_ideal_box_score']),
                'margin_above_original_ON_threshold': score - 10, 'original_loss_stage': stages[scan],
                'localized_survivor': localized, 'case_final_ALL': all(successful), 'case_final_ANY': any(successful)})
        expected_cases.append({**shared, 'active_ON_scan_denominator': len(expected_ids),
            'localized_survivor_active_ON_scans': sum(successful),
            'NO_ON_THRESHOLD_HIT_active_ON_scans': len(successful) - sum(successful),
            'final_ALL': all(successful), 'final_ANY': any(successful),
            'minimum_active_ON_global_maximum': min(case_scores),
            'median_active_ON_global_maximum': middle(case_scores),
            'maximum_active_ON_global_maximum': max(case_scores),
            'ON_threshold_carrier_count': cell['ON_threshold_carrier_count'],
            'surviving_ON_carrier_count': cell['surviving_ON_carrier_count']})
    expected_misses = [row for row in expected_scans if not row['localized_survivor']]
    check(result['active_ON_scans'], expected_scans, 'active_ON_scans')
    check(result['case_coverage'], expected_cases, 'case_coverage')
    check(result['missed_active_ON_scans'], expected_misses, 'missed_active_ON_scans')
    actual_tables = {name: csv_read(OUT / name) for name in TABLES}
    check(actual_tables[TABLES[0]], expected_scans, TABLES[0])
    check(actual_tables[TABLES[1]], expected_cases, TABLES[1])
    check(actual_tables[TABLES[3]], expected_misses, TABLES[3])

    labels = {'ALL_64_CASES'}
    for dimension in ('nominal_ideal_box_score', 'activity', 'drift_hz_s', 'intrinsic_width_channels', 'reference_native_offset'):
        labels |= {f'{dimension}={cell[dimension]}' for cell in originals}
    labels |= {f'nominal_ideal_box_score={level};activity={activity}' for level, activity in product((10.0, 12.0, 16.0, 24.0), ('single_third_ON', 'all_three_ON'))}
    groups = result['summary']['groups']
    assert len(groups) == len(labels) == 25
    assert {group['group'] for group in groups} == labels
    assert {row['group'] for row in actual_tables[TABLES[2]]} == labels
    for i, group in enumerate(groups):
        label = group['group']
        selected_cases = [cell for cell in originals if group_matches(cell, label)]
        selected_scans = [scan for scan in expected_scans if group_matches(scan, label)]
        scores = [row['global_maximum_robust_score'] for row in selected_scans]
        ratios = [row['global_maximum_divided_by_nominal_ideal'] for row in selected_scans]
        expected = {'group': label, 'case_denominator': len(selected_cases),
            'final_ALL_cases': sum(c['final_all_active_recovered'] for c in selected_cases),
            'final_ANY_cases': sum(c['final_any_active_recovered'] for c in selected_cases),
            'active_ON_scan_denominator': len(selected_scans),
            'localized_survivor_active_ON_scans': sum(r['localized_survivor'] for r in selected_scans),
            'NO_ON_THRESHOLD_HIT_active_ON_scans': sum(not r['localized_survivor'] for r in selected_scans),
            'global_maximum_robust_score': {'count': len(scores), 'minimum': min(scores), 'median': middle(scores), 'maximum': max(scores)},
            'global_maximum_divided_by_nominal_ideal': {'count': len(ratios), 'minimum': min(ratios), 'median': middle(ratios), 'maximum': max(ratios)},
            'scan_weighting': 'Each active ON scan contributes one saved global maximum; scans within a case are not independent trials.'}
        check(group, expected, ('group', label))
        flat = {key: value for key, value in expected.items() if not isinstance(value, dict)}
        for metric in ('global_maximum_robust_score', 'global_maximum_divided_by_nominal_ideal'):
            for key, value in expected[metric].items():
                flat[f'{metric}_{key}'] = value
        check(actual_tables[TABLES[2]][i], flat, (TABLES[2], label))
    summary = {'case_count': len(originals), 'active_ON_scan_count': len(expected_scans),
        'localized_survivor_active_ON_scans': sum(row['localized_survivor'] for row in expected_scans),
        'NO_ON_THRESHOLD_HIT_active_ON_scans': len(expected_misses),
        'cases_with_any_missed_active_ON_scan': len({row['case_id'] for row in expected_misses}),
        'final_ALL_cases': sum(c['final_ALL'] for c in expected_cases),
        'final_ANY_cases': sum(c['final_ANY'] for c in expected_cases),
        'pre_OFF_to_final_case_recovery_losses': 0,
        'surviving_carriers': sum(c['surviving_ON_carrier_count'] for c in expected_cases),
        'carrier_count_is_not_independent_trial_count': True, 'original_ON_threshold': 10.0}
    check({key: value for key, value in result['summary'].items() if key != 'groups'}, summary, 'summary')
    assert (summary['case_count'], summary['active_ON_scan_count'], summary['localized_survivor_active_ON_scans'],
            summary['NO_ON_THRESHOLD_HIT_active_ON_scans'], summary['cases_with_any_missed_active_ON_scan'],
            summary['final_ALL_cases'], summary['final_ANY_cases'], summary['surviving_carriers']) == (64, 128, 115, 13, 12, 52, 59, 7051)
    definitions = result['definitions']
    assert 'not measured robust SNR or flux' in definitions['nominal_ideal_box_score']
    assert 'not a truth-localized statistic' in definitions['global_maximum_robust_score']
    assert 'not an estimator of efficiency' in definitions['global_maximum_divided_by_nominal_ideal']
    assert 'No independence claimed' in definitions['independence']
    audit = {'review_status': 'PASS_INDEPENDENT_RETAINED_METHOD_COVERAGE_AUDIT',
        'source_commit': SOURCE, 'verified_original_inputs': verified,
        'independently_verified_summary': summary, 'descriptive_groups_verified': len(groups),
        'CSV_rows_verified': {name: len(actual_tables[name]) for name in TABLES},
        'scalar_cells_verified': scalar_checks,
        'arithmetic': '45-digit Decimal division, threshold margins and sorted middle-value medians; no primary analysis imports',
        'maximum_numeric_comparison_tolerance': str(EPS),
        'script_sha256': digests(Path(__file__))['sha256'],
        'audited_product_sha256': {name: digests(OUT / name)['sha256'] for name in (*TABLES, 'METHOD_COVERAGE.json')},
        'scope': 'Only three authenticated published report products; no map archives or detector/generator code executed.',
        'limitations': [
            'This checks report-derived arithmetic and provenance, not the already completed full saved-map audit.',
            'The saved global template-search maximum is not a prespecified statistic at truth, calibrated SNR, flux, or efficiency estimate.',
            'The descriptive ratio compares different quantities. One realization per design cell and correlated scans/carriers do not establish general detection probabilities or causal effects.',
            'The agreement of maximum>=10 with localized recovery is observed in these retained cells, not a general equivalence.',
        ], 'new_scores': 0, 'new_draws': 0, 'original_map_archives_opened': 0, 'qualification': False}
    (OUT / 'PEER_METHOD_COVERAGE.json').write_text(json.dumps(audit, indent=2) + '\n')
    (OUT / 'PEER_METHOD_COVERAGE.md').write_text(f'''# Independent retained METHOD coverage audit\n\nPASS. The independent standard-library script authenticated the fixed Git blob SHA1, SHA256 and lengths of the three original report products, their restoration receipt and original manifest. It compared original CSV and JSON cells field for field, then checked all four new CSVs and METHOD_COVERAGE.json against independent Decimal arithmetic.\n\nVerified: 64 cases, 128 active ON scans, 115 localized-survivor scans, 13 threshold misses across 12 cases, ALL52/64, ANY59/64, 7051 correlated surviving carriers, and 25 descriptive groups. Every derived minimum, median, maximum, descriptive ratio and count agrees within {EPS}. No maps or power arrays were opened, and no detector, generator or primary analysis code was imported or executed.\n\nThe ratio compares a saved, selected global search maximum with a declared noiseless ideal projection. It is not SNR, flux or efficiency calibration. The 64 exact design cells have one realization each, with balanced placement margins; scan/carrier responses are correlated. The threshold/localized-recovery equivalence is a property checked in these retained cells. No general detection probability, causal effect, additional qualification or repaired A/B status is inferred.\n\nExact hashes and scalar checks are in PEER_METHOD_COVERAGE.json.\n''')
    print(json.dumps({'review_status': audit['review_status'], 'summary': summary, 'groups': len(groups), 'scalar_cells_checked': scalar_checks}))


if __name__ == '__main__':
    main()
