"""Finalize the full-ON scientific interpretation from admitted PASS outputs.

No numerical libraries, rank payloads or context profiles are read at import
or --check-only. Finalization requires a separately pinned root phase GO.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re

BASE = 'seti_burst_full'
PILOT = 'seti_burst_on'
SCANS = ('epoch1_on', 'epoch2_on', 'epoch3_on')
CONTEXT_SCANS = ('epoch1_on', 'epoch1_off', 'epoch2_on', 'epoch2_off', 'epoch3_on', 'epoch3_off')
MAIN_STATUS = 'PASS2010_DUAL_MAPS10050_SCALARS18_DC_CORES_INDEPENDENT_DUAL_REMAX9_EMPTY'
GLOBAL_STATUS = 'PASS_INDEPENDENT_FULL_SORT_9412608_CARRIERS_DUAL_GLOBAL_ON_RANKS'
CONTEXT_STATUS = 'PASS54_FULL_BAND_CLEAN_TOP9_FIXED_PROFILES9_OWN_SCORES_ALL_FULL501_NORMALIZATIONS_AND_DC_DIAGNOSTICS'
CONTEXT_EXECUTION_STATUS = 'COMPLETE_FULL_ON_BURST4_CLEAN_TOP9_FIXED_TRACKS54_SIX_SCAN_CONTEXTS'
FINAL_STATUS = 'COMPLETE_AUTHENTICATED_FULL_ON_SCIENTIFIC_REVIEW_NO_QUALIFIED_SETI_DETECTION'
GO_STATUS = 'GO_COMPLETE_FULL_ON_FINAL_SCIENCE_REVIEW'
IDENTITY = ('scan_id', 'native_chunk_index', 'core_q', 'map_id', 'carrier_index_in_core',
            'source_reference_channel', 'frequency_hz_at_window_reference', 'window_start_row',
            'window_length_rows', 'window_source_rows', 'reference_time_mjd', 'drift_grid_index',
            'drift_hz_s', 'width_channels', 'score', 'rounded_absolute_centers')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
    return h.hexdigest()


def read(path):
    return json.loads(path.read_bytes(), parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))


def confined(root, relative):
    name = Path(relative)
    path = root/name
    require(not name.is_absolute() and '..' not in name.parts and not path.is_symlink()
            and path.resolve().is_relative_to(root), 'Confined ordinary relative path required')
    return path


def pin(root, path):
    return {'path': path.relative_to(root).as_posix(), 'bytes': path.stat().st_size, 'sha256': digest(path)}


def save(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def finalize(root, go):
    declared = {item['path']: item for item in go['input_pins']}
    require(len(declared) == len(go['input_pins']), 'Report input pins must be unique')
    checked = {}
    def admitted(relative):
        require(relative in declared, 'Root phase GO must bind every consumed input: '+relative)
        path = confined(root, relative)
        require(pin(root, path) == declared[relative], 'Final-review input changed: '+relative)
        checked[relative] = declared[relative]
        return path
    def loaded(relative):
        return read(admitted(relative))
    main_path = BASE+'/qa_results/QA_RECEIPT.json'
    global_path = BASE+'/aggregate_qa_results/QA_RECEIPT.json'
    context_qa_path = BASE+'/context_qa_results/QA_RECEIPT.json'
    main, global_qa, context_qa = loaded(main_path), loaded(global_path), loaded(context_qa_path)
    require(main['status'] == MAIN_STATUS and global_qa['status'] == GLOBAL_STATUS
            and global_qa['mismatch_count'] == 0 and context_qa['status'] == CONTEXT_STATUS
            and context_qa['portable_saved_crop_replay'] is False, 'Actual source/global/original-H5 context QA must all PASS')
    full_scope = loaded(BASE+'/SCOPE.json')
    aggregate_scope = loaded(BASE+'/AGGREGATE_SCOPE.json')
    aggregate = loaded(BASE+'/aggregate_results/EXECUTION_RECEIPT.json')
    context_scope = loaded(BASE+'/CONTEXT_SCOPE.json')
    context_receipt = loaded(BASE+'/context_results/EXECUTION_RECEIPT.json')
    require(main['scope_sha256'] == declared[BASE+'/SCOPE.json']['sha256']
            and main['driver_sha256'] == digest(admitted(BASE+'/driver.py'))
            and main['qa_sha256'] == digest(admitted(BASE+'/qa_v2.py')), 'Actual producing/source-QA code or scope differs')
    require(global_qa['aggregate_receipt_sha256'] == declared[BASE+'/aggregate_results/EXECUTION_RECEIPT.json']['sha256']
            and global_qa['aggregate_scope_sha256'] == declared[BASE+'/AGGREGATE_SCOPE.json']['sha256']
            and aggregate['aggregate_code_sha256'] == digest(admitted(BASE+'/aggregate.py'))
            and global_qa['qa_code_sha256'] == digest(admitted(BASE+'/aggregate_qa.py')), 'Actual global aggregation/QA binding differs')
    require(context_receipt['status'] == CONTEXT_EXECUTION_STATUS
            and context_qa['context_receipt_sha256'] == declared[BASE+'/context_results/EXECUTION_RECEIPT.json']['sha256']
            and context_qa['context_scope_sha256'] == declared[BASE+'/CONTEXT_SCOPE.json']['sha256']
            and context_qa['primary_qa_receipt_sha256'] == declared[main_path]['sha256']
            and context_qa['aggregate_qa_receipt_sha256'] == declared[global_path]['sha256'], 'Context source/global/producing provenance differs')
    context_code_path = context_scope['context_code_path']
    require(context_code_path == BASE+'/context_v2.py'
            and context_scope['context_code_sha256'] == digest(admitted(context_code_path))
            and context_qa['context_qa_sha256'] == digest(admitted(BASE+'/context_qa.py')), 'Active full-context code/QA identity differs')
    require(full_scope['complete_domains_per_ON_scan_after_merge'] == 766 and full_scope['new_maps'] == 2010
            and aggregate_scope['total_maps'] == 2298 and aggregate_scope['pilot_maps_reused'] == 288
            and global_qa['totalcarriers'] == 9412608 and global_qa['forcedEMPTY'] == 9,
            'Completed full-ON numerical census differs')
    require(9412608*2226 == 20952465408, 'Correlated hypothesis census differs')
    selection_path = BASE+'/aggregate_results/SELECTED_CLEAN_TOP9.json'
    selected = loaded(selection_path)['records']
    aggregate_outputs = {p['path']: p for p in aggregate['output_pins']}
    require(aggregate_outputs[selection_path] == declared[selection_path]
            and global_qa['selected_clean_TOP9_pin'] == declared[selection_path], 'Global nine selection not authenticated by actual aggregate and QA')
    require(len(selected) == 9 and {(p['scan_id'], p['rank']) for p in selected} == {(s, r) for s in SCANS for r in (1, 2, 3)}
            and all(p['winner_family'] == 'DC_clean' and p['eligible_DC_untouched'] for p in selected), 'Exactly nine separate clean selections required')
    maxima_path = BASE+'/aggregate_results/MAP_MAXIMA_AND_COUNTS.json'
    maxima = loaded(maxima_path)
    require(aggregate_outputs[maxima_path] == declared[maxima_path] and len(maxima['records']) == 2298, 'All2298 authenticated per-map dual audits required')
    dual_census = {'raw_DC_contacting_winner_carriers': sum(p['unrestricted_DC_contacting_cached_winners'] for p in maxima['records']),
                  'clean_changed_winner_tuples': sum(p['DC_clean_changed_winner_tuples'] for p in maxima['records']),
                  'clean_EMPTY_carriers': sum(p['DC_clean_EMPTY_carriers'] for p in maxima['records']),
                  'raw_hypothesis_occurrences': sum(p['unrestricted_valid_hypothesis_records'] for p in maxima['records']),
                  'clean_admissible_hypothesis_occurrences': sum(p['DC_clean_valid_hypothesis_records'] for p in maxima['records'])}
    require(dual_census['raw_hypothesis_occurrences'] == 20952465408 and dual_census['clean_EMPTY_carriers'] == 9
            and dual_census['raw_DC_contacting_winner_carriers'] == dual_census['clean_changed_winner_tuples'], 'Exact full dual carrier census differs')
    raw_clean_comparison = {}
    for scan in SCANS:
        families = {}
        for family in ('UNRESTRICTED', 'DC_CLEAN'):
            relative = BASE+'/aggregate_results/'+scan+'_'+family+'_TOP3.json'
            value = loaded(relative)
            require(aggregate_outputs[relative] == declared[relative] and len(value['records']) == 3, 'Authenticated per-family TOP3 required')
            families[family] = value['records']
        raw_keys = {tuple(json.dumps(point[k], sort_keys=True, separators=(',', ':')) for k in IDENTITY) for point in families['UNRESTRICTED']}
        raw_clean_comparison[scan] = {'raw_TOP3_exact_tuples_retained_in_clean_TOP3': sum(tuple(json.dumps(point[k], sort_keys=True, separators=(',', ':')) for k in IDENTITY) in raw_keys for point in families['DC_CLEAN'])}
    profiles_path = BASE+'/context_results/CONTEXT_PROFILES.json'
    matrix = loaded(profiles_path)
    context_outputs = {p['path']: p for p in context_receipt['output_pins']}
    require(context_outputs[profiles_path] == declared[profiles_path]
            and matrix['schema'] == 'SETI_FULL_ON_BURST4_CLEAN_TOP9_FIXED_CONTEXT_PROFILES_V2'
            and matrix['status'] == CONTEXT_EXECUTION_STATUS and matrix['selected_tracks'] == selected
            and matrix['ON_OFF_veto_applied'] is False and matrix['DC_contact_score_veto_or_mask_applied'] is False,
            'Full fixed-context payload identity or interpretation differs')
    profiles = matrix['profiles']
    require(len(profiles) == 54 and {(p['selected_track']['scan_id'], p['selected_track']['rank'], p['context_scan_id']) for p in profiles}
            == {(s, r, context) for s in SCANS for r in (1, 2, 3) for context in CONTEXT_SCANS}, 'Exact54 six-scan context census required')
    require(all(math.isfinite(p['fixed_four_row_score']) and math.isfinite(p['fixed_full16_score']) for p in profiles), 'Context scores must be finite')
    groups = {'origin_ON': [], 'other_ON': [], 'OFF': []}
    for profile in profiles:
        own = profile['context_scan_id'] == profile['selected_track']['scan_id']
        role = 'ON' if profile['context_scan_id'].endswith('_on') else 'OFF'
        require(profile['original_acquisition_role'] == role and profile['DC_contact_score_veto_or_mask_applied'] is False,
                'Original ON/OFF roles and unmodified DC-contact scores required')
        require(profile['DC_contact_count_selected4'] == len(profile['DC_contact_row_indices_selected4'])
                and profile['DC_contact_count_full16'] == len(profile['DC_contact_row_indices_full16']), 'Context DC diagnostics are internally inconsistent')
        if own:
            require(profile['origin_primary_score'] == profile['selected_track']['score']
                    and profile['DC_contact_count_selected4'] == 0,
                    'Origin selected4 primary score identity and DC-clean condition required')
            require(math.isclose(profile['fixed_four_row_score'], profile['origin_primary_score'], rel_tol=1e-10, abs_tol=1e-7), 'Own fixed score failed primary reconciliation')
        else:
            require(profile['origin_primary_score'] is None, 'Only nine origin profiles can carry primary score authority')
        groups['origin_ON' if own else ('other_ON' if role == 'ON' else 'OFF')].append(profile)
    require({key: len(value) for key, value in groups.items()} == {'origin_ON': 9, 'other_ON': 18, 'OFF': 27}, 'Context role partition must be9/18/27')
    context_groups = {}
    for group, items in groups.items():
        context_groups[group] = {'profiles': len(items),
            'profiles_with_selected4_DC_contact': sum(p['DC_contact_any_selected4'] for p in items),
            'profiles_with_full16_DC_contact': sum(p['DC_contact_any_full16'] for p in items),
            'selected4_DC_contact_rows': sum(p['DC_contact_count_selected4'] for p in items),
            'full16_DC_contact_rows': sum(p['DC_contact_count_full16'] for p in items)}
    for field in ('profiles_with_selected4_DC_contact', 'profiles_with_full16_DC_contact', 'selected4_DC_contact_rows', 'full16_DC_contact_rows'):
        require(matrix['counts'][field] == sum(group[field] for group in context_groups.values()), 'Context diagnostic aggregate count differs')
    pilot = []
    pilot_qa = loaded(PILOT+'/qa_results/QA_RECEIPT.json')
    require(pilot_qa['status'] == 'PASS288_ON_BURST4_MAPS1170_RAW4X503_QUERIES144_SOURCE_ROWS_NO_GRID_RERUN', 'Original pilot full-map QA must be authenticated and PASS')
    for epoch in (1, 2, 3):
        primary = 'on20170428_epoch'+str(epoch)+'_HIP98505'
        receipt_path = PILOT+'/results/'+primary+'/EXECUTION_RECEIPT.json'
        pilot_receipt = loaded(receipt_path)
        require(pilot_qa['primary_receipt_sha256s'][primary] == declared[receipt_path]['sha256'], 'Original pilot producer receipt not authenticated by prior QA')
        relative = PILOT+'/results/'+primary+'/DC_AWARE_TOP3.json'
        records = loaded(relative)['records']
        pilot_outputs = {item['path']: item for item in pilot_receipt['output_byte_pins']}
        require(len(records) == 3 and pilot_outputs[relative] == declared[relative], 'Authenticated previous pilot TOP3 required')
        pilot.extend(records)
    def identity(point):
        return tuple(json.dumps(point[key], sort_keys=True, separators=(',', ':')) for key in IDENTITY)
    pilot_keys = {identity(p) for p in pilot}
    matched = sum(identity(p) in pilot_keys for p in selected)
    synthetic = loaded(BASE+'/SYNTHETIC_V2_RECEIPT.json')
    require(synthetic['status'] == 'PASS_INDEPENDENT_DUAL_MAX_SYNTHETIC_REGRESSIONS'
            and synthetic['source_values_read'] is False and len(synthetic['cases']) == 10
            and all(case['status'] == 'PASS' for case in synthetic['cases'])
            and synthetic['qa_sha256'] == digest(admitted(BASE+'/qa_v2.py'))
            and synthetic['test_sha256'] == digest(admitted(BASE+'/test_qa_synthetic_v2.py')),
            'Corrected ten-case synthetic gate must actually PASS and match actual frozen test/code')
    tracks = []
    for point in selected:
        related = [p for p in profiles if (p['selected_track']['scan_id'], p['selected_track']['rank']) == (point['scan_id'], point['rank'])]
        own = next(p for p in related if p['context_scan_id'] == point['scan_id'])
        other_on = [p for p in related if p['original_acquisition_role'] == 'ON' and p['context_scan_id'] != point['scan_id']]
        off = [p for p in related if p['original_acquisition_role'] == 'OFF']
        tracks.append({'selected_track': point, 'matches_previous_pilot_exact_scientific_tuple': identity(point) in pilot_keys,
            'own_selected4_DC_contact_rows': own['DC_contact_count_selected4'], 'own_full16_DC_contact_rows': own['DC_contact_count_full16'],
            'other_ON_fixed_four_row_score_max': max(p['fixed_four_row_score'] for p in other_on),
            'OFF_fixed_four_row_score_max': max(p['fixed_four_row_score'] for p in off),
            'other_ON_fixed_full16_score_max': max(p['fixed_full16_score'] for p in other_on),
            'OFF_fixed_full16_score_max': max(p['fixed_full16_score'] for p in off)})
    for declaration in checked.values():
        require(pin(root, confined(root, declaration['path'])) == declaration, 'Input changed during final scientific review')
    return {'schema': 'SETI_FULL_ON_COMPLETED_SCIENTIFIC_REVIEW_V1', 'status': FINAL_STATUS,
        'date': go['date'], 'target': 'HIP98505 / HD189733', 'observation_visit': '2017-04-28', 'independent_observing_visits': 1,
        'counts': {'new_maps': 2010, 'unchanged_pilot_maps': 288, 'maps_total': 2298, 'reference_carriers_total': 9412608,
                   'reference_carriers_per_ON': 3137536, 'correlated_hypothesis_occurrences': 20952465408, 'clean_EMPTY': 9,
                   'selected_clean_tracks': 9, 'context_profiles': 54, 'origin_ON': 9, 'other_ON': 18, 'OFF': 27},
        'tracks': tracks, 'context_role_groups': context_groups, 'context_execution_counts': matrix['counts'],
        'dual_carrier_census': dual_census, 'raw_clean_TOP3_comparison_by_scan': raw_clean_comparison,
        'previous_pilot_exact_tuple_matches': matched, 'previous_pilot_comparison_identity_fields': list(IDENTITY),
        'all_three_actual_QA_pass': True, 'QA_receipts': {'main': declared[main_path], 'global': declared[global_path], 'context': declared[context_qa_path]},
        'input_pins_verified': list(checked.values()), 'context_scores_unchanged_when_DC_contact': True,
        'DC_contact_is_diagnostic_not_an_OFF_veto': True, 'new_telescope_HTTP': 0, 'cost_DKK': 0,
        'calibrated_SNR_FAP': False, 'qualified_SETI_detection': False, 'protected2016_opened': False,
        'closed2019_transport_opened': False, 'original_AB': 'FAIL_CLOSED_UNCHANGED',
        'failure_correction_history': [{'stage': 'Synthetic fixture v1 before observational QA execution',
            'issue': 'A boundary spike in rows4..7 did not isolate the intended width3-only reference-row case.',
            'correction': 'The v2 fixture places the spike solely in row0; the independent QA wrapper binds the corrected test path explicitly.',
            'production_scoring_code_changed': False, 'observational_arrays_used_for_fixture_correction': False,
            'v2_actual_cases_PASS': 10, 'synthetic_receipt_pin': declared[BASE+'/SYNTHETIC_V2_RECEIPT.json']}],
        'limits': ['Three ON scans belong to one already exposed2017 visit; overlapping windows and carriers create correlated hypothesis occurrences.',
                  'The pilot frequency sampling is completed across the declared766 contiguous core domains perON; native170q0 andnative172q255 remain excluded for full support.',
                  'The fixed159 drift grid, widths1/3, seven4-row windows and constant-drift context cannot cover every possible signal morphology.',
                  'Selection after maximization creates selection bias. Ranking and fixed context provide no calibrated significance or false-alarm probability.',
                  'DC-clean selected four-row support only avoids three fixed center bins. Normalization remains full16/full4096 and adjacent leakage/other interference remain possible.',
                  'OtherON/OFF selected4 andfull16 supports may contact DC; diagnostic flags preserve the original scores and are not a qualified sky-origin veto.',
                  'Time gaps between scan pointings and fixed-track extrapolation prevent treating the context as continuous surveillance or independent observing visits.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('.'))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check-only', action='store_true')
    mode.add_argument('--run', action='store_true')
    parser.add_argument('--go', default=BASE+'/FINAL_SCIENCE_GO.json')
    parser.add_argument('--go-sha256')
    parser.add_argument('--out', default=BASE+'/report_results')
    args = parser.parse_args()
    code_sha = digest(Path(__file__))
    if args.check_only:
        print(json.dumps({'status': 'FINAL_SCIENCE_REVIEW_CODE_ONLY', 'code_sha256': code_sha,
                          'numerical_payloads_read': 0, 'PDF_created': False}))
        return
    root = args.root.resolve()
    go_path = confined(root, args.go)
    require(args.go_sha256 and digest(go_path) == args.go_sha256, 'Exact root report phase GO required')
    go = read(go_path)
    require(go['status'] == GO_STATUS and go['science_review_code_sha256'] == code_sha
            and re.fullmatch('[0-9a-f]{40}', go['public_freeze_commit']), 'Final scientific/report phase not admitted')
    output = confined(root, args.out)
    output.mkdir(parents=True, exist_ok=False)
    result = finalize(root, go)
    require(digest(Path(__file__)) == code_sha and digest(go_path) == args.go_sha256, 'Review code/phase GO changed')
    result.update({'science_review_code_sha256': code_sha, 'phase_GO_sha256': args.go_sha256, 'public_freeze_commit': go['public_freeze_commit']})
    save(output/'FINAL_SCIENCE_REVIEW.json', result)
    lines = ['# Completed full ON burst search', '',
        'All source, independent global-ranking and original-HDF5 context QA stages passed. No qualified SETI detection or calibrated false-alarm probability is established.', '',
        'The three HIP98505 / HD189733 ON scans belong to one already exposed 2017-04-28 visit. The completed search contains 2,010 new maps plus 288 unchanged pilot maps, 9,412,608 carrier references and 20,952,465,408 correlated hypothesis occurrences. Both unrestricted and best per-hypothesis DC-clean winners were preserved.', '',
        '| ON scan | Rank | Reference MHz | Drift Hz/s | Start row | Width | Ranking score | Own DC rows selected4/full16 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for track in result['tracks']:
        point = track['selected_track']
        lines.append('| '+point['scan_id']+' | '+str(point['rank'])+' | '+format(point['frequency_hz_at_window_reference']/1e6, '.9f')+' | '+format(point['drift_hz_s'], '.12g')+' | '+str(point['window_start_row'])+' | '+str(point['width_channels'])+' | '+format(point['score'], '.9f')+' | '+str(track['own_selected4_DC_contact_rows'])+'/'+str(track['own_full16_DC_contact_rows'])+' |')
    lines += ['', str(result['previous_pilot_exact_tuple_matches'])+' of the nine selections exactly match an authenticated previous pilot TOP3 scientific tuple. The 54 fixed profiles comprise 9 origin ON, 18 other ON and 27 OFF contexts. Selected4/full16 DC diagnostics preserve all scores and are not a qualified OFF veto.', '',
              'A faulty synthetic v1 boundary fixture was corrected before observational QA execution. V2 isolated the spike in row0 and passed all ten cases; production scoring code was unchanged.', '',
              'The fixed159 drift grid, widths1/3, overlapping4-row windows, bounded frequency support and time gaps limit coverage. Ranking after maximization is subject to selection bias. Reference-frequency spacing does not establish independent physical sources. Protected2016 and closed2019 states remain unchanged; original A/B remains FAIL_CLOSED. No new telescope request or additional cost occurred.', '',
              'Full-precision tuples, quantitative context diagnostics, provenance pins and actual QA bindings are in FINAL_SCIENCE_REVIEW.json and SELECTED_CLEAN_TOP9.csv. A final PDF is created separately only after the completed archive and fresh saved-data replay pass.']
    with (output/'RESULTS.md').open('x') as stream:
        stream.write('\n'.join(lines)+'\n')
    selected_records = [track['selected_track'] for track in result['tracks']]
    with (output/'SELECTED_CLEAN_TOP9.csv').open('x', newline='') as stream:
        writer = csv.writer(stream)
        header = sorted(selected_records[0])
        writer.writerow(header)
        for point in selected_records:
            writer.writerow([json.dumps(point[field], sort_keys=True, separators=(',', ':'), allow_nan=False) for field in header])
    save(output/'SCIENCE_REVIEW_RECEIPT.json', {'status': 'PASS_COMPLETED_FINAL_SCIENCE_REVIEW_ARTIFACT',
         'science_review_code_sha256': code_sha, 'phase_GO_sha256': args.go_sha256,
         'output': pin(root, output/'FINAL_SCIENCE_REVIEW.json'), 'all_three_actual_QA_PASS': True,
         'supporting_outputs': [pin(root, output/'RESULTS.md'), pin(root, output/'SELECTED_CLEAN_TOP9.csv')]})
    print(json.dumps({'status': result['status'], 'selected_tracks': 9, 'context_profiles': 54,
                      'previous_pilot_exact_tuple_matches': result['previous_pilot_exact_tuple_matches'],
                      'output': pin(root, output/'FINAL_SCIENCE_REVIEW.json')}))


if __name__ == '__main__':
    main()
