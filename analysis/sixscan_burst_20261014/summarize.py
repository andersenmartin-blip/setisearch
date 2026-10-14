#!/usr/bin/env python3
"""Summarize committed frozen outcomes; never generate, score, or modify cases."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path

ALPHA = 1.0 / 64.0
STATUS_PASS = 'PASS_PRELIMINARY_GAMMA16_BURST_CHAIN_ONLY'
STATUS_FAIL = 'FAIL_CLOSED_NEW_METHOD_CONTROL'
EXPECTED_COUNTS = {'calibration': 63, 'strong': 14, 'operating': 48,
                   'matched_rfi': 24, 'null': 32, 'single_row_transient': 12,
                   'near_off_contamination': 12}
PHASE_NAMES = ('PRIMARY_CALIBRATION', 'PRIMARY_VALIDATION', 'QA')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            value.update(block)
    return value.hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'),
                      parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))


def finite(value, label):
    value = float(value)
    require(math.isfinite(value), label + ' must be finite')
    return value


def save_json(path, value, *, immutable=False):
    path = Path(path)
    encoded = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n'
    if immutable and path.exists():
        require(path.read_text(encoding='utf-8') == encoded, 'Existing immutable calibration differs')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(encoded, encoding='utf-8')
    temporary.replace(path)


def save_csv(path, records, fields):
    path = Path(path)
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fields, extrasaction='raise')
        writer.writeheader()
        writer.writerows({key: record.get(key, '') for key in fields} for record in records)
    temporary.replace(path)


def admission(root):
    scope = read(root / 'SCOPE.json')
    go = read(root / 'GO.json')
    require(go['status'] == 'ADMITTED_AFTER_EXACT_PUBLIC_FREEZE_READBACK', 'Exact public root GO required')
    require(go['scope_sha256'] == sha(root / 'SCOPE.json'), 'Scope identity differs')
    pins = {pin['path']: pin for pin in scope['code_pins']}
    for name in ('summarize.py', 'case_bank.json', 'contract.json', 'real_baselines.json'):
        require(name in pins, 'Required summary prerequisite is not frozen: ' + name)
        require((root / name).stat().st_size == pins[name]['bytes'] and sha(root / name) == pins[name]['sha256'],
                'Frozen summary prerequisite differs: ' + name)
    cases = read(root / 'case_bank.json')
    contract = read(root / 'contract.json')
    require(len(cases) == 205 and Counter(c['family'] for c in cases) == EXPECTED_COUNTS, 'Complete fixed205-case bank required')
    require(len({c['case_id'] for c in cases}) == 205 and len({c['seed_sha256'] for c in cases}) == 205, 'Duplicate frozen identities')
    for case in cases:
        require(hashlib.sha256(case['case_id'].encode('ascii')).hexdigest() == case['seed_sha256'], 'Identity/seed binding differs')
    require(contract['selection']['calibration_references'] == 63
            and contract['selection']['final_candidate_p_cut_inclusive'] == ALPHA,
            'Frozen calibration count/threshold differs')
    return scope, go, cases, contract


def phase_receipt(root, phase, expected_indices, resources):
    path = root / (phase + '_RUN_STATE.json')
    if not path.exists():
        return {'complete': False, 'reason': 'NOT_RUN', 'jobs_by_index': {}, 'CPU_s': None}
    state = read(path)
    jobs = state.get('jobs', [])
    exposed_phase = phase in ('EXPOSED', 'QA_EXPOSED')
    recipes = read(root / ('real_baselines.json' if exposed_phase else 'case_bank.json'))
    by_index = {}
    errors = []
    for job in jobs:
        index = int(job['index'])
        if index in by_index:
            errors.append('duplicate reaped index ' + str(index))
        by_index[index] = job
        if index not in expected_indices:
            errors.append('unplanned index ' + str(index))
        elif 'case_id' in job:
            expected_ids = {recipes[index]['case_id']}
            if job['case_id'] not in expected_ids:
                errors.append('reaped case identity differs ' + str(index))
        if job.get('wait4_reaped') is not True or job.get('exit_code') != 0:
            errors.append('failed/unreaped child ' + str(index))
        try:
            cpu = finite(job['whole_child_CPU_s'], 'whole-child CPU')
            wall = finite(job['wall_s'], 'whole-child wall')
            rss = int(job['peak_RSS_bytes'])
            require(0 <= cpu <= resources['per_case_CPU_s_cap'], 'CPU cap exceeded')
            require(0 <= wall <= resources.get('per_case_wall_s_cap', 1800), 'wall cap exceeded')
            require(0 <= rss <= resources.get('per_case_memory_bytes_cap', 1024 ** 3), 'RSS cap exceeded')
        except (KeyError, ValueError, TypeError) as error:
            errors.append('resource ' + str(index) + ': ' + str(error))
    measured = sum(float(job.get('whole_child_CPU_s', 0)) for job in jobs)
    charged = float(state.get('charged_complete_child_CPU_s', 0))
    if not math.isfinite(measured) or not math.isfinite(charged) or abs(measured - charged) > 1e-8:
        errors.append('closed child charge disagrees with reaped jobs')
    complete = (state.get('status') == 'COMPLETE' and not state.get('running') and not state.get('unsubmitted')
                and set(by_index) == set(expected_indices) and len(jobs) == len(expected_indices) and not errors)
    return {'complete': complete, 'state_status': state.get('status'), 'reason': '; '.join(errors),
            'jobs_by_index': by_index, 'CPU_s': charged, 'state_sha256': sha(path),
            'planned': len(expected_indices), 'reaped': len(jobs)}


def case_record(root, index, recipe, *, require_qa, contract, exposed=False):
    label = ('R' if exposed else 'C') + f'{index:04d}'
    folder = root / 'results' / ('exposed' if exposed else 'cases') / label
    row = {'index': index, 'case_id': recipe['case_id'], 'family': recipe['family'],
           'status': 'NOT_RUN', 'data_integrity_ok': False, 'measurement_available': False,
           'failure_reason': '', 'active_ON_count': None, 'pre_OFF_all_active_recovered': None,
           'pre_OFF_any_active_recovered': None, 'after_OFF_all_active_recovered': None,
           'after_rank_all_active_recovered': None, 'after_rank_any_active_recovered': None,
           'raw_ON_hit_count': None, 'after_OFF_survivor_count': None, 'after_rank_survivor_count': None,
           'maximum_pre_OFF_ON_score': None, 'qa_status': None}
    result = truth = None
    if not folder.exists():
        return row, result, truth
    row['status'] = 'FAIL'
    try:
        require((folder / 'COMMITTED.json').is_file(), 'No committed complete case')
        committed = read(folder / 'COMMITTED.json')
        require(committed.get('status') == 'COMPLETED_CASE_ONLY' and committed.get('data_integrity_ok') is True,
                'Worker closure did not pass')
        require(committed['case_id'] == recipe['case_id'] and committed['case_index'] == index
                and committed['exposed'] == exposed, 'Committed identity/index differs')
        manifest_path = folder / 'artifact_manifest.json'
        require(sha(manifest_path) == committed['artifact_manifest_sha256'], 'Committed manifest differs')
        manifest = read(manifest_path)
        required_files = {'output.json', 'truth.json', 'inputs.npz', 'maps.npz', 'case_definition.json', 'admission.json'}
        require(required_files <= manifest.keys(), 'Committed scientific artifacts missing')
        for name, declaration in manifest.items():
            require(Path(name).name == name and name not in ('.', '..'), 'Invalid manifest path')
            path = folder / name
            require(path.is_file() and path.stat().st_size == declaration['bytes'] and sha(path) == declaration['sha256'],
                    'Committed artifact differs: ' + name)
        require(read(folder / 'case_definition.json') == recipe, 'Saved recipe differs')
        result, truth = read(folder / 'output.json'), read(folder / 'truth.json')
        require(result.get('status') == 'COMPLETED_CASE_ONLY' and result.get('data_integrity_ok') is True,
                'Worker output is failed/incomplete')
        require(result['case_id'] == recipe['case_id'] and result['case_index'] == index and result['exposed'] == exposed,
                'Worker output identity differs')
        require(truth['case_id'] == recipe['case_id'], 'Truth identity differs')
        if not exposed:
            require(truth['seed_sha256'] == recipe['seed_sha256'], 'Truth seed differs')
            expected_active = [contract['geometry']['scan_metadata'][i]['scan_id']
                               for i in recipe['active_scan_indices'] if contract['geometry']['scan_metadata'][i]['role'] == 'ON']
            require(truth['active_ON_scan_ids'] == expected_active, 'Truth primary ON activity differs')
        receipt = result['resource_receipt']
        cpu, wall = finite(receipt['cpu_s'], 'worker CPU'), finite(receipt['wall_s'], 'worker wall')
        caps = receipt['caps']
        require(cpu <= caps['cpu_s'] and wall <= caps['wall_s'] and receipt['peak_rss_bytes'] <= caps['address_space_bytes'],
                'Worker measured resource cap exceeded')
        maximum = finite(result['maximum_pre_OFF_ON_score'], 'complete-family maximum')
        require(maximum == finite(result['calibrationglobal_ON_max'], 'calibration maximum'), 'Two complete-family maxima differ')
        hits = result['all_ON_threshold_hypotheses']
        require(len({hit['hit_id'] for hit in hits}) == len(hits), 'Duplicate ON hit identity')
        for hit in hits:
            require(finite(hit['ON_score'], 'ON score') >= 10 and hit['ON_score'] <= maximum,
                    'Invalid ON threshold hit')
            require(hit['disposition'] in ('OFF_MATCHED', 'SURVIVOR_EXPLORATORY'), 'Unknown OFF disposition')
        off_survivors = sum(hit['disposition'] == 'SURVIVOR_EXPLORATORY' for hit in hits)
        require(off_survivors == result['surviving_ON_threshold_hypothesis_count'], 'OFF survivor census differs')
        row.update(measurement_available=True, active_ON_count=len(truth['active_ON_scan_ids']),
                   raw_ON_hit_count=len(hits), after_OFF_survivor_count=off_survivors,
                   maximum_pre_OFF_ON_score=maximum)
        qa_path = root / 'results' / 'qa' / (label + '.json')
        if require_qa:
            require(qa_path.is_file(), 'Independent QA is missing')
            qa = read(qa_path)
            row['qa_status'] = qa.get('status')
            require(qa.get('status') == 'PASS', 'Independent QA did not pass')
            if 'case_index' in qa:
                require(qa['case_index'] == index, 'QA index differs')
            if 'case_id' in qa:
                require(qa['case_id'] == recipe['case_id'], 'QA identity differs')
            expected_qa_pins = {'output_sha256': sha(folder / 'output.json'),
                                'truth_sha256': sha(folder / 'truth.json'),
                                'artifact_manifest_sha256': sha(manifest_path),
                                'scope_sha256': sha(root / 'SCOPE.json')}
            for key, expected in expected_qa_pins.items():
                if key in qa:
                    require(qa[key] == expected, 'QA source binding differs: ' + key)
        row.update(status='VALID_CASE', data_integrity_ok=True)
    except (KeyError, ValueError, TypeError, OSError) as error:
        row['failure_reason'] = str(error)
    return row, result, truth


def calibration(root, cases, contract, scope):
    indices = [i for i, case in enumerate(cases) if case['family'] == 'calibration']
    phase = phase_receipt(root, 'PRIMARY_CALIBRATION', indices, scope['resources'])
    require(phase['complete'], 'All63 primary reference workers must close completely before calibration')
    values, identities, inputs = [], [], []
    for index in indices:
        row, output, truth = case_record(root, index, cases[index], require_qa=False, contract=contract)
        require(row['data_integrity_ok'], 'Calibration reference failed: ' + str(index) + ': ' + row['failure_reason'])
        values.append(row['maximum_pre_OFF_ON_score'])
        identities.append(cases[index]['case_id'])
        folder = root / 'results' / 'cases' / f'C{index:04d}'
        inputs.append({'index': index, 'case_id': cases[index]['case_id'],
                       'output_sha256': sha(folder / 'output.json'), 'truth_sha256': sha(folder / 'truth.json'),
                       'artifact_manifest_sha256': sha(folder / 'artifact_manifest.json')})
    return {'schema': 'SETI_SIXSCAN_FROZEN_GAMMA16_CALIBRATION_V1',
            'status': 'COMPLETE_63_PRIMARY_REFERENCES_PENDING_FULL_INDEPENDENT_QA',
            'references': 63, 'reference_case_ids': identities, 'reference_global_ON_maxima': values,
            'critical_maximum': max(values), 'statistic': 'global complete declared ON family maximum before OFF',
            'p_rule': '(1 + number of reference global ON maxima >= candidate ON score)/64',
            'ties_counted_inclusively': True, 'final_candidate_p_cut_inclusive': ALPHA,
            'equivalent_candidate_rule': 'OFF-surviving ON score strictly greater than all63 reference maxima',
            'calibration_law': 'independent Gamma(shape16,scale1/16), six scans/rows/channels',
            'validation_or_exposed_outcomes_read_to_form_calibration': False,
            'input_case_receipts': inputs, 'scope_sha256': sha(root / 'SCOPE.json'),
            'contract_sha256': sha(root / 'contract.json'), 'case_bank_sha256': sha(root / 'case_bank.json'),
            'summarizer_sha256': sha(Path(__file__)), 'primary_calibration_state_sha256': phase['state_sha256'],
            'whole_closed_calibration_children_CPU_s': phase['CPU_s'],
            'physical_or_telescope_FAP_calibrated': False, 'qualified_SETI_detection': False}


def rank_hits(index, recipe, output, calibration_values):
    rows = []
    for hit in output['all_ON_threshold_hypotheses']:
        score = float(hit['ON_score'])
        equal_or_greater = sum(value >= score for value in calibration_values)
        p = (1 + equal_or_greater) / 64.0
        off_survived = hit['disposition'] == 'SURVIVOR_EXPLORATORY'
        rows.append({'index': index, 'case_id': recipe['case_id'], 'family': recipe['family'],
                     'hit_id': hit['hit_id'], 'scan_id': hit['scan_id'], 'ON_score': score,
                     'OFF_disposition': hit['disposition'], 'reference_equal_or_greater': equal_or_greater,
                     'model_rank_p': p, 'rank_cut_pass': p <= ALPHA,
                     'final_candidate': off_survived and p <= ALPHA,
                     'calibration_member_in_reference_bank': recipe['family'] == 'calibration',
                     'telescope_FAP_interpretation_allowed': False})
    return rows


def recovery_metrics(row, output, truth, hits):
    final_ids = {hit['hit_id'] for hit in hits if hit['final_candidate']}
    all_source_hits = {hit['hit_id']: hit for hit in output['all_ON_threshold_hypotheses']}
    active = truth['active_ON_scan_ids']
    row['after_rank_survivor_count'] = len(final_ids)
    if not active:
        return
    recovery = output['recovery']
    require(recovery['active_ON_scan_ids'] == active and set(recovery['by_scan']) == set(active), 'Recovery activity differs')
    pre, off, ranked = [], [], []
    for scan_id in active:
        saved = recovery['by_scan'][scan_id]
        for field in ('pre_OFF_matches', 'final_matches'):
            for match in saved[field]:
                require(match['hit_id'] in all_source_hits, 'Recovery refers to unknown hit')
                origin = all_source_hits[match['hit_id']]
                require(origin['scan_id'] == scan_id and origin['ON_score'] == match['ON_score'], 'Recovery hit identity/score differs')
                if field == 'final_matches':
                    require(origin['disposition'] == 'SURVIVOR_EXPLORATORY', 'Recovery final match was OFF rejected')
        pre.append(bool(saved['pre_OFF_matches']))
        off.append(bool(saved['final_matches']))
        ranked.append(any(match['hit_id'] in final_ids for match in saved['final_matches']))
    row.update(pre_OFF_all_active_recovered=all(pre), pre_OFF_any_active_recovered=any(pre),
               after_OFF_all_active_recovered=all(off), after_rank_all_active_recovered=all(ranked),
               after_rank_any_active_recovered=any(ranked))


def family_view(rows, family):
    selected = [row for row in rows if row['family'] == family]
    valid = [row for row in selected if row['data_integrity_ok']]
    return {'expected': len(selected), 'valid': len(valid),
            'missing': sum(row['status'] == 'NOT_RUN' for row in selected),
            'failed': sum(row['status'] == 'FAIL' for row in selected),
            'all_active_pre_OFF_recovered': sum(row['pre_OFF_all_active_recovered'] is True for row in valid),
            'all_active_after_OFF_recovered': sum(row['after_OFF_all_active_recovered'] is True for row in valid),
            'all_active_after_rank_recovered': sum(row['after_rank_all_active_recovered'] is True for row in valid),
            'any_active_after_rank_recovered': sum(row['after_rank_any_active_recovered'] is True for row in valid),
            'cadences_with_any_after_OFF_survivor': sum(row['after_OFF_survivor_count'] > 0 for row in valid),
            'cadences_with_any_after_rank_survivor': sum(row['after_rank_survivor_count'] > 0 for row in valid),
            'missing_or_failed_cases_are_not_measured_null_or_nonrecovery': True}


def summarize(root, scope, cases, contract, cal):
    references = cal['reference_global_ON_maxima']
    records, hit_rows = [], []
    for index, recipe in enumerate(cases):
        row, output, truth = case_record(root, index, recipe, require_qa=True, contract=contract)
        if row['measurement_available']:
            hits = []
            try:
                hits = rank_hits(index, recipe, output, references)
                recovery_metrics(row, output, truth, hits)
            except (KeyError, ValueError, TypeError) as error:
                row.update(status='FAIL', data_integrity_ok=False, failure_reason=str(error))
            for hit in hits:
                hit.update(case_status=row['status'], case_integrity_ok=row['data_integrity_ok'])
            hit_rows.extend(hits)
        records.append(row)
    resources = scope['resources']
    expected_indices = {'PRIMARY_CALIBRATION': [i for i, c in enumerate(cases) if c['family'] == 'calibration'],
                        'PRIMARY_VALIDATION': [i for i, c in enumerate(cases) if c['family'] != 'calibration'],
                        'QA': list(range(205))}
    phase_details = {name: phase_receipt(root, name, expected_indices[name], resources) for name in PHASE_NAMES}
    closed_charge = sum(value['CPU_s'] or 0 for value in phase_details.values())
    total_with_reserved_metadata = closed_charge + resources['metadata_and_delivery_reserved_CPU_s']
    caps_gate = all(value['complete'] for value in phase_details.values()) and total_with_reserved_metadata <= resources['aggregate_new_CPU_s_cap']
    all_integrity = len(records) == 205 and all(row['data_integrity_ok'] for row in records)
    integrity_gate = all_integrity and caps_gate
    families = {name: family_view(records, name) for name in EXPECTED_COUNTS}
    by_id = {row['case_id']: row for row in records}
    subgroups = {}
    for label, field, minimum in (('activity', 'active_scan_indices', 7), ('drift', 'drift_hz_s', 10),
                                  ('intrinsic_width', 'intrinsic_width_channels', 22)):
        grouped = defaultdict(list)
        for recipe in cases:
            if recipe['family'] == 'operating':
                grouped[json.dumps(recipe[field], separators=(',', ':'))].append(by_id[recipe['case_id']])
        subgroups[label] = {name: {'expected': len(rows), 'valid': sum(r['data_integrity_ok'] for r in rows),
                                  'final_all_active_recovered': sum(r['data_integrity_ok'] and r['after_rank_all_active_recovered'] is True for r in rows),
                                  'minimum': minimum}
                            for name, rows in sorted(grouped.items())}
    strong, operating, rfi, null = (families[name] for name in ('strong', 'operating', 'matched_rfi', 'null'))
    checks = {'complete_integrity_QA_and_resource_caps': integrity_gate,
              'strong14of14_final_rank_localized': strong['valid'] == 14 and strong['all_active_after_rank_recovered'] == 14,
              'operating44of48_final_rank_localized': operating['valid'] == 48 and operating['all_active_after_rank_recovered'] >= 44,
              'each_activity7of8': len(subgroups['activity']) == 6 and all(g['valid'] == g['expected'] == 8 and g['final_all_active_recovered'] >= 7 for g in subgroups['activity'].values()),
              'each_drift10of12': len(subgroups['drift']) == 4 and all(g['valid'] == g['expected'] == 12 and g['final_all_active_recovered'] >= 10 for g in subgroups['drift'].values()),
              'each_width22of24': len(subgroups['intrinsic_width']) == 2 and all(g['valid'] == g['expected'] == 24 and g['final_all_active_recovered'] >= 22 for g in subgroups['intrinsic_width'].values()),
              'all24RFI_localized_in_all3ON_before_OFF': rfi['valid'] == 24 and rfi['all_active_pre_OFF_recovered'] == 24
                  and all(r['active_ON_count'] == 3 for r in records if r['family'] == 'matched_rfi' and r['data_integrity_ok']),
              'RFI_zero_any_survivors_after_OFF_before_rank': rfi['valid'] == 24 and rfi['cadences_with_any_after_OFF_survivor'] == 0,
              'null_at_most1of32_any_final_rank_candidate': null['valid'] == 32 and null['cadences_with_any_after_rank_survivor'] <= 1,
              'all24diagnostics_complete_without_recovery_gate': families['single_row_transient']['valid'] == 12 and families['near_off_contamination']['valid'] == 12,
              'all63calibration_references_independently_QA_verified': families['calibration']['valid'] == 63}
    result = {'schema': 'SETI_SIXSCAN_BURST_JOINT_SUMMARY_V1', 'status': STATUS_PASS if all(checks.values()) else STATUS_FAIL,
              'integrity_gate': integrity_gate, 'joint_gate': all(checks.values()), 'checks': checks,
              'expected_cases': 205, 'calibration_cases': 63, 'validation_and_diagnostic_cases': 142,
              'families': families, 'operating_subgroups': subgroups,
              'case_status_counts': dict(Counter(row['status'] for row in records)),
              'calibration': {'references': 63, 'critical_maximum': cal['critical_maximum'],
                              'model_rank_cut_inclusive': ALPHA, 'ties_inclusive': True, 'sha256': sha(root / 'results/CALIBRATION.json')},
              'resources': {'complete_primary_and_QA_wait4_children_CPU_s': closed_charge,
                            'metadata_and_delivery_reserved_CPU_s': resources['metadata_and_delivery_reserved_CPU_s'],
                            'charged_plus_metadata_reserved_CPU_s': total_with_reserved_metadata,
                            'aggregate_CPU_s_cap': resources['aggregate_new_CPU_s_cap'],
                            'caps_gate': caps_gate, 'phase_receipts': {name: {k: v for k, v in value.items() if k != 'jobs_by_index'} for name, value in phase_details.items()},
                            'worker_receipt_CPU_is_not_added_again_to_wait4_charge': True},
              'input_pins': {'scope_sha256': sha(root / 'SCOPE.json'), 'case_bank_sha256': sha(root / 'case_bank.json'),
                            'contract_sha256': sha(root / 'contract.json'), 'summarizer_sha256': sha(Path(__file__))},
              'original_A_B': 'FAIL_CLOSED', 'original_pilot_admitted': False, 'qualified_SETI_detection': False,
              'physical_sensitivity_established': False, 'telescope_FAP_calibrated': False,
              'interpretation': ['Preliminary complete-chain digital result under the frozen Gamma16 law only.',
                                'Operating level16 differs from old level12; this is a new method control, not reclassification of old A/B.',
                                'Fixed placements, activities and widths are partly confounded; no sensitivity-rate or telescope-FAP inference.',
                                'Transient/near-OFF diagnostics have no hidden scientific rejection criterion.',
                                'Missing/failed cases remain separate; they are not measured nulls or measured nonrecoveries.',
                                'All original source closures, protected2016/closed2019 and20October checkpoint remain unchanged.']}
    fields = ('index', 'case_id', 'family', 'status', 'data_integrity_ok', 'measurement_available', 'failure_reason',
              'qa_status', 'active_ON_count', 'pre_OFF_all_active_recovered', 'pre_OFF_any_active_recovered',
              'after_OFF_all_active_recovered', 'after_rank_all_active_recovered', 'after_rank_any_active_recovered',
              'raw_ON_hit_count', 'after_OFF_survivor_count', 'after_rank_survivor_count', 'maximum_pre_OFF_ON_score')
    save_csv(root / 'results/CASE_RESULTS.csv', records, fields)
    save_csv(root / 'results/CALIBRATED_HITS.csv', hit_rows, ('index', 'case_id', 'family', 'hit_id', 'scan_id', 'ON_score',
             'OFF_disposition', 'reference_equal_or_greater', 'model_rank_p', 'rank_cut_pass', 'final_candidate',
             'calibration_member_in_reference_bank', 'telescope_FAP_interpretation_allowed', 'case_status', 'case_integrity_ok'))
    result['output_tables'] = {name: {'bytes': (root / 'results' / name).stat().st_size,
                                    'sha256': sha(root / 'results' / name)} for name in ('CASE_RESULTS.csv', 'CALIBRATED_HITS.csv')}
    save_json(root / 'results/SUMMARY.json', result)
    return result


def summarize_exposed(root, scope, contract, cal):
    bank = read(root / 'real_baselines.json')
    require(len(bank) == 9 and all(c['family'] == 'real_sham' for c in bank), 'Nine original exposed bands required')
    original = read(root / 'results/SUMMARY.json')
    require(original['integrity_gate'] is True, 'Complete synthetic/QA integrity must precede exposed diagnostics')
    state = phase_receipt(root, 'EXPOSED', list(range(9)), scope['resources'])
    qa_state = phase_receipt(root, 'QA_EXPOSED', list(range(9)), scope['resources'])
    records, hits = [], []
    for index, recipe in enumerate(bank):
        row, output, truth = case_record(root, index, recipe, require_qa=True, contract=contract, exposed=True)
        if row['measurement_available']:
            calibrated = rank_hits(index, recipe, output, cal['reference_global_ON_maxima'])
            row['after_rank_survivor_count'] = sum(hit['final_candidate'] for hit in calibrated)
            for hit in calibrated:
                hit.update(case_status=row['status'], case_integrity_ok=row['data_integrity_ok'])
            hits.extend(calibrated)
        records.append(row)
    expected_indices = {'PRIMARY_CALIBRATION': [i for i, c in enumerate(read(root / 'case_bank.json')) if c['family'] == 'calibration'],
                        'PRIMARY_VALIDATION': [i for i, c in enumerate(read(root / 'case_bank.json')) if c['family'] != 'calibration'],
                        'QA': list(range(205))}
    prior_states = {name: phase_receipt(root, name, expected_indices[name], scope['resources']) for name in PHASE_NAMES}
    known_primary_charge = sum(value['CPU_s'] or 0 for value in prior_states.values())
    require(known_primary_charge == original['resources']['complete_primary_and_QA_wait4_children_CPU_s'],
            'Earlier complete child charge differs from frozen synthetic summary')
    for name, value in prior_states.items():
        require(value['state_sha256'] == original['resources']['phase_receipts'][name]['state_sha256'],
                'Earlier reaped phase identity changed after synthetic closure')
    known_exposed_charge = (state['CPU_s'] or 0) + (qa_state['CPU_s'] or 0)
    known_total_with_metadata = known_primary_charge + known_exposed_charge + scope['resources']['metadata_and_delivery_reserved_CPU_s']
    cap_ok = known_total_with_metadata <= scope['resources']['aggregate_new_CPU_s_cap']
    complete = (all(value['complete'] for value in prior_states.values()) and state['complete'] and qa_state['complete']
                and cap_ok and all(row['data_integrity_ok'] for row in records))
    result = {'schema': 'SETI_SIXSCAN_EXPOSED_BACKGROUND_DIAGNOSTIC_V1',
              'status': 'COMPLETE_EXPOSED_MODEL_DIAGNOSTIC_ONLY' if complete else 'INCOMPLETE_EXPOSED_DIAGNOSTIC',
              'integrity_gate': complete, 'expected_bands': 9, 'case_results': records,
              'model_rank_hits': hits, 'source_definitions_sha256': sha(root / 'real_baselines.json'),
              'calibration_sha256': sha(root / 'results/CALIBRATION.json'),
              'whole_exposed_primary_wait4_children_CPU_s': state['CPU_s'],
              'whole_exposed_QA_wait4_children_CPU_s': qa_state['CPU_s'],
              'exposed_primary_phase': {k: v for k, v in state.items() if k != 'jobs_by_index'},
              'exposed_QA_phase': {k: v for k, v in qa_state.items() if k != 'jobs_by_index'},
              'known_primary_QA_and_exposed_children_plus_metadata_reserve_CPU_s': known_total_with_metadata,
              'aggregate_known_charge_cap_gate': cap_ok,
              'setup_and_whole_session_CPU_not_claimed_complete_by_this_field': True,
              'same_historical_observing_visit': '2017-04-28', 'bands_selected_after_prior_exposure': True,
              'Gamma16_rank_p_is_model_diagnostic_only': True, 'telescope_FAP_calibrated': False,
              'celestial_significance_established': False, 'qualified_SETI_detection': False,
              'original_A_B': 'FAIL_CLOSED', 'new_observation': False,
              'interpretation': 'Nine postselected bands in one exposed historical visit; model ranks are not celestial significance or independent null cadences.'}
    save_json(root / 'results/EXPOSED_SUMMARY.json', result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--calibration-only', action='store_true')
    group.add_argument('--exposed', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    scope, go, cases, contract = admission(root)
    cal = calibration(root, cases, contract, scope)
    save_json(root / 'results/CALIBRATION.json', cal, immutable=True)
    if args.calibration_only:
        print(json.dumps({'status': cal['status'], 'references': 63, 'critical_maximum': cal['critical_maximum']}, sort_keys=True))
        return 0
    result = summarize_exposed(root, scope, contract, cal) if args.exposed else summarize(root, scope, cases, contract, cal)
    print(json.dumps({'status': result['status'], 'integrity_gate': result['integrity_gate']}, sort_keys=True))
    return 0 if result['integrity_gate'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
