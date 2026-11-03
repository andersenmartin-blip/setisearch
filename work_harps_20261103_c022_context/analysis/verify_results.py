#!/usr/bin/env python3
"""Verify C022 delivery without re-executing frozen scientific methods."""
from pathlib import Path
from PIL import Image
import datetime
import hashlib
import itertools
import json
import re

HERE = Path(__file__).resolve().parent
OUT = HERE / 'results'
REPO = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_bytes())
P = read(HERE / 'PLAN.json')
H = read(OUT / 'OUTPUT_HASHES.json')
I = read(OUT / 'PLOT_INDEX.json')
R = read(OUT / 'PROFILE_METRICS.json')
C = read(OUT / 'COMPARISONS.json')
for f, h in P['source_hashes'].items():
    assert sha(REPO / f) == h, f
for f, h in H.items():
    assert sha(OUT / f) == h, f
assert len(P['source_hashes']) == 88 and len(H) == 43
assert sum(f.endswith('.npz') for f in H) == 33
assert sha(OUT / 'OUTPUT_HASHES.json') == '3241c6be3bb3fd51a7c6bc99da96d4b47c91ee2ae236380edd2921450eff372b'
public = read(HERE.parent / 'PROSPECTIVE_PUBLICATION_RECEIPT.json')
assert public['status'] == 'PASS_EXACT_REMOTE_READBACK' and len(public['files']) == 25
for f in public['files']:
    assert sha(REPO / f['path']) == f['sha256']
    assert (REPO / f['path']).stat().st_size == f['bytes']
expected = ['figures/MERGED_BROAD_CONTEXT.png', 'figures/MERGED_CORE_CONTEXT.png']
expected += [f'figures/NATIVE_ORDERS_{i}.png' for i in range(1, 2)]
expected += [f'figures/PRESERVED_RAW_ORDER_CONTEXT_{i}.png' for i in range(1, 2)]
assert [r['path'] for r in I['files']] == expected
assert I['native_pages'] == I['raw_pages'] == 1 and I['total_figures'] == 4
assert I['all_three_reference_and_marker_ids'] == list(P['events'])
assert I['all20_profile_slots_retained'] and I['all_three_original_event_raw_contexts_retained']
assert I['numeric_outputs_unchanged'] and I['origin_assignments'] == 0
figures = []
for row in I['files']:
    f = OUT / row['path']
    assert sha(f) == row['sha256'] and f.stat().st_size == row['bytes']
    Image.open(f).verify()
    im = Image.open(f)
    im.load()
    figures.append({**row, 'size': list(im.size), 'png_decode': 'PASS', 'visually_inspected': True})
assert len(R) == 20 and len(C) == 96
assert sum(r['identical_product_self_pair'] for r in C) == 12
assert all(r['status'] == 'MEASURED_CONTEXT'
           and r['normalization_status'] == 'USABLE_POSITIVE_FLANK_REFERENCE'
           and r['normalization_reasons'] == [] and r['flank_reference'] > 0
           and r['low_flank_reference'] is False
           and r['raw_grid_finite_samples'] == r['normalized_grid_finite_samples'] == 601
           and r['positive_finite_ERR_samples'] == 0
           and r['gap_masked_grid_samples'] == r['outside_native_coverage_grid_samples'] == 0
           and r['window_nonpositive_fraction'] == r['left_flank_nonpositive_fraction']
           == r['right_flank_nonpositive_fraction'] == 0 for r in R)
assert all(r['raw_pearson'] is not None and r['normalized_rms'] is not None
           and r['raw_pearson_block_reason'] is None and r['normalized_rms_block_reason'] is None
           and r['common_finite_raw_samples'] == r['common_finite_normalized_samples']
           == (51 if r['region'] == 'core' else 550) for r in C)
assert P['target'] == 'HD114783' and P['group_center_bary_air_angstrom'] == 4312.241249999999
assert P['anchor_dp_id'] == 'ADP.2022-01-22T01:09:14.958'
assert P['anchor_berv_km_s'] == 29.658729150824
assert read(OUT / 'SUMMARY.json')['topocentric_anchor_air_angstrom'] == 4311.814678415948
assert len(P['merged_dp_ids']) == 7 and len(P['discovery_dp_ids']) == 3
assert set(P['merged_dp_ids']) - set(P['discovery_dp_ids']) == {
    'ADP.2022-02-06T01:07:28.382', 'ADP.2023-03-23T01:02:04.833',
    'ADP.2023-05-16T01:01:18.574', 'ADP.2023-07-02T01:01:43.311'}
centers = {'V2E2-0117': 4312.245, 'V2E2-0127': 4312.245, 'V2E2-0131': 4312.237499999999}
assert P['individual_event_centers_bary_air_angstrom'] == centers
assert len(P['event_markers']) == 3
for m in P['event_markers']:
    c = centers[m['event']]
    assert m['center_bary_air_angstrom'] == c
    assert m['barycentric_offset_angstrom'] == c - P['group_center_bary_air_angstrom']
    assert m['discovery_dp_id'] == P['events'][m['event']]
    core = P['individual_event_cores_bary_air_angstrom'][m['event']]
    assert core == [c - .25, c + .25]
    assert core[0] < P['group_center_bary_air_angstrom'] - .25 or core[1] > P['group_center_bary_air_angstrom'] + .25
MC = [r for r in C if r['relationship'] == 'MERGED_EPOCH_TO_DISCOVERY']
NC = [r for r in C if r['relationship'] == 'SAME_EPOCH_NATIVE_TO_MERGED']
assert len(MC) == 84 and len(NC) == 12
assert all(r['order'] == 19 and r['dp_id'] == r['reference_dp_id'] and r['same_exposure']
           and not r['identical_product_self_pair'] for r in NC)
nonself = [r for r in MC if not r['identical_product_self_pair']]
assert len(nonself) == 72
by = {(r['dp_id'], r['reference_dp_id'], r['frame'], r['region']): r for r in MC}
families = []
for event, ref in P['events'].items():
    for frame in ['barycentric', 'topocentric']:
        for region in ['core', 'broad_pattern']:
            assert len([r for r in nonself if r['reference_dp_id'] == ref
                        and r['frame'] == frame and r['region'] == region]) == 6
    for dp in P['merged_dp_ids']:
        if dp == ref:
            continue
        for region in ['core', 'broad_pattern']:
            assert by[dp, ref, 'barycentric', region]['raw_pearson'] > by[dp, ref, 'topocentric', region]['raw_pearson']
            assert by[dp, ref, 'barycentric', region]['normalized_rms'] < by[dp, ref, 'topocentric', region]['normalized_rms']
    families.append({'event': event, 'reference_dp_id': ref, 'other_epochs': 6,
                     'all_six_better_barycentric_r_and_RMS_both_regions': True})
for frame in ['barycentric', 'topocentric']:
    for region in ['core', 'broad_pattern']:
        rows = [r for r in nonself if r['frame'] == frame and r['region'] == region]
        assert len(rows) == 18
        assert len({tuple(sorted([r['dp_id'], r['reference_dp_id']])) for r in rows}) == 15
        for a, b in itertools.combinations(P['discovery_dp_ids'], 2):
            assert abs(by[a, b, frame, region]['raw_pearson'] - by[b, a, frame, region]['raw_pearson']) < 1e-12
            assert abs(by[a, b, frame, region]['normalized_rms'] - by[b, a, frame, region]['normalized_rms']) < 1e-12
jan1, jan2 = P['events']['V2E2-0117'], P['events']['V2E2-0131']
assert round(by[jan1, jan2, 'topocentric', 'core']['raw_pearson'], 6) == .989918
assert round(by[jan1, jan2, 'topocentric', 'broad_pattern']['raw_pearson'], 6) == .995462
assert min(r['raw_pearson'] for r in NC if r['region'] == 'core') >= .999927
assert min(r['raw_pearson'] for r in NC if r['region'] == 'broad_pattern') >= .998809
native = [r for r in R if r['kind'] == 'native']
assert sorted(set(r['window_native_finite_samples'] for r in native)) == [512, 513, 515]
assert set(r['left_flank_finite_samples'] for r in native) == {126, 127}
assert set(r['right_flank_finite_samples'] for r in native) == {130, 131}
assert all(r['window_native_finite_samples'] == 600 and r['left_flank_finite_samples']
           == r['right_flank_finite_samples'] == 150 for r in R if r['kind'] == 'merged')
history = P['historical_review_disagreement']['per_event_history']
assert len(history) == 3
for r in history:
    assert r['current_adopted_code'] == 'U'
    if r['candidate_id'] == 'V2E2-0131':
        assert r['original_primary_code'] == 'I' and r['original_secondary_code'] == 'M'
        assert r['original_secondary_normalized_code'] == r['original_adopted_baseline_code'] == 'I'
        assert r['later_mapping_followup_primary_code'] == r['later_mapping_followup_secondary_code'] == 'U'
        assert r['coordinates_changed'] is False and r['original_native_and_raw_pixels_preserved']
    else:
        assert r['original_primary_code'] == r['original_secondary_code'] == r['original_adopted_code'] == 'U'
assert len(P['historical_mapping_stages']) == 3
for r in P['historical_mapping_stages']:
    assert r['order'] == 19 and r['original_grid_mapping_usable'] and r['final_reference_mapping_supported']
    assert r['original_local_mapping_usable'] is False and r['original_baseline_mapping_verified'] is False
    assert r['registration_changed'] is False
    assert r['baseline_field_basis'] == ('mapping_verified in original raw_followup mapping'
                                         if r['event'] == 'V2E2-0131'
                                         else 'explicit baseline_mapping_verified in batch03 mapping')
raw = read(OUT / 'PRESERVED_RAW_CONTEXT.json')
assert len(raw) == 3
for r in raw:
    assert sha(OUT / r['copied_path']) == r['file']['sha256']
    shapes = {v['key']: v['shape'] for v in r['npy_headers']}
    assert shapes['raw_cutout'] == shapes['raw_excess'] == ([21, 25] if r['event'] == 'V2E2-0131' else [31, 33])
science = read(HERE.parent / 'scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json')
assert sum(not r['expected_center_inside_fixed_core'] for r in science['metadata_expected_feature_locations']) == 4
assert sum(abs(m['discovery_topocentric_offset_angstrom']) > .25 for m in P['event_markers']) == 1
dep = P['prior_C021_shared_structured_flank_dependency']
assert dep['shared_bounded_spectral_source_pixels_with_C021']
assert dep['overlap_width_angstrom'] == 3.585000000000946
assert dep['next_common_core_fully_inside_current_positive_reference_flank']
assert dep['current_common_core_fully_inside_next_negative_reference_flank'] and dep['core_intervals_disjoint']
audit = read(HERE.parent / 'independent_audit/NUMERICAL_AUDIT.json')
assert audit['status'].startswith('PASS') and audit['checks_passed'] == 698 and audit['scalar_values_compared'] == 79403
reuse = audit['prior_C021_shared_source_index_records']
assert len(reuse) == audit['shared_C021_source_inputs'] == 10
assert [r['shared_source_samples'] for r in reuse] == [360, 365, 422, 361, 390, 428, 445, 306, 358, 306]
old_index = read(REPO / 'work_harps_20261103_c021_context/analysis/results/BOUNDED_INPUT_INDEX.json')
new_index = read(OUT / 'BOUNDED_INPUT_INDEX.json')
old_sources = {(r['kind'], r['dp_id'], r['order']): r for r in old_index}
new_sources = {(r['kind'], r['dp_id'], r['order']): r for r in new_index}
assert len(new_sources) == 10
for r in reuse:
    key = r['kind'], r['dp_id'], r['order']
    a, b = old_sources[key], new_sources[key]
    assert a['source_file_sha256'] == b['source_file_sha256']
    lo = max(a['original_index_start'], b['original_index_start'])
    hi = min(a['original_index_stop'], b['original_index_stop'])
    assert lo == r['original_index_start'] and hi == r['original_index_stop'] and hi-lo == r['shared_source_samples']
assert all(f in P['source_hashes'] for f in [
    'work_harps_20261103_c021_context/inputs/INPUT_INVENTORY.json',
    'work_harps_20261103_c021_context/analysis/results/BOUNDED_INPUT_INDEX.json'])
N = read(HERE.parent / 'scientific_review/NEXT_GROUP_METADATA.json')
assert N['next_core_group'] == 'C017' and len(N['members']) == 1
assert N['members'][0]['candidate_id'] == 'V2E2-0118' and N['members'][0]['queue_index'] == 37
assert N['members'][0]['route'] == 'INDIVIDUAL_PROFILE_CONTEXT'
assert N['proposed_group_center_bary_air_angstrom'] == 3868.175
assert N['discovery_anchor_dp_id'] == 'ADP.2022-02-06T01:07:28.382'
assert N['discovery_anchor_berv_km_s'] == 26.6810328154809
assert N['proposed_topocentric_anchor_air_angstrom'] == 3867.830769460069
assert N['historical_review_disagreement']['per_event_history'][0]['original_primary_code'] == 'U'
assert N['historical_review_disagreement']['per_event_history'][0]['original_secondary_code'] == 'U'
assert N['historical_review_disagreement']['per_event_history'][0]['original_adopted_code'] == 'U'
for r in N['historical_mapping_stages']:
    assert r['global_grid_usable'] and r['later_five_window_supported']
    assert r['original_local_usable'] is (r['order'] == 3)
    assert r['original_baseline_verified'] is (r['order'] == 3)
nextdep = N['wavelength_dependency']
assert nextdep['same_target_shared_pixel_overlaps'][0]['prior_group'] == 'C018'
assert nextdep['same_target_shared_pixel_overlaps'][0]['width_angstrom'] == 4.8412500000004
assert not nextdep['C017_common_core_intersects_C018_reference_flanks']
assert not nextdep['C018_common_core_intersects_C017_reference_flanks']
assert nextdep['C017_common_core_fully_inside_C018_surrounding_context']
assert nextdep['C018_common_core_fully_inside_C017_surrounding_context']
report = (HERE / 'RESULTS_REPORT.md').read_text()
for text in ['20 profiles and 96 comparisons', 'All three current C022 codes remain U',
             'Eighteen directed nonself rows per frame/region represent 15 unordered exposure pairs and three reciprocal',
             'February 5 2022 and March 22, May 15 and July 1 2023 are cohort nonreferences',
             '20 false low-reference flags', 'zero in all 20 rows', '0.989918 core / 0.995462 surroundings',
             'Only one of the three original discovery markers is outside: May 5 2022',
             'All three original local/baseline stages are false',
             '0131 originally has primary I, secondary M normalized to I, and adopted baseline I',
             '0131 retains its original 21×25 five-array container',
             'negative excess above the central patch', 'dominant periodic right-edge structure',
             '0.065480 / 0.065662', '0.999324 / 0.999302',
             'All four figures were visually inspected and fully decoded',
             '3.585000000000946 Å', 'complete C022 core lies inside C021',
             'complete C021 core', 'both-frame union window plus interpolation brackets',
             'no prior C021 arrays were opened and no C021 method was rerun',
             'INDIVIDUAL_PROFILE_CONTEXT', '4.8412500000004 Å',
             "neither intersects the other's fixed reference flanks",
             'No C017 array analysis or completed-diagnostic replay was executed here']:
    assert text in report, text
for event in P['events']:
    assert '### ' + event + ' reference:' in report
assert not re.search(r'\|\n### V2E2', report)
links = re.findall(r'\]\(([^)]+)\)', report)
assert not [q for q in links if not (HERE/q).exists() and not q.startswith('http') and q != 'RESULTS_QA.json']
qa = {
    'status': 'PASS_COMPLETE_C022_RESULT_DELIVERY',
    'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'target': 'HD114783', 'common_midpoint': 4312.241249999999,
    'exact_member_float_core_and_marker_identities_preserved': True,
    'frozen_source_hashes_verified': 88, 'public_method_bindings_verified': 25,
    'numerical_output_hashes_verified': 43, 'numerical_npz_files_verified': 33,
    'stable_numeric_ledger_sha256': sha(OUT/'OUTPUT_HASHES.json'),
    'profile_slots': 20, 'comparison_slots': 96, 'merged_comparisons': 84,
    'native_same_exposure_comparisons': 12, 'identical_product_self_comparisons': 12,
    'observations': 7, 'fixed_discovery_references': 3,
    'January21_May5_January16_references_and_all_four_nonreferences_preserved': True,
    'per_reference_families': families, 'directed_nonself_rows_per_frame_region': 18,
    'unordered_pairs_per_frame_region': 15, 'reciprocal_duplicates_per_frame_region': 3,
    'bounded_source_windows': 10, 'preserved_original_raw_copies': 3,
    'full_valid_positive_reference_profiles': 20, 'false_low_reference_flags': 20,
    'true_low_reference_flags': 0, 'null_low_reference_flags': 0,
    'raw_only_profiles': 0, 'blocked_profiles': 0, 'evaluable_Pearson': 96, 'evaluable_RMS': 96,
    'all_comparisons_complete_raw_and_normalized_support': True,
    'all_profiles_zero_positive_ERR': True, 'all_profiles_zero_gap_and_outside_coverage_masks': True,
    'profiles_with_nonpositive_source_window_samples': 0,
    'all20_window_left_right_nonpositive_fractions_zero': True,
    'native_original_finite_window_range': [512, 515],
    'native_original_left_flank_range': [126, 127], 'native_original_right_flank_range': [130, 131],
    'January_pair_topocentric_raw_r_core_surrounding': [.989918, .995462],
    'January2023_native_surrounding_RMS_B_T': [.065480, .065662],
    'January2023_native_surrounding_raw_r_B_T': [.999324, .999302],
    'structured_reference_flanks_retained_without_masks': True,
    'all_three_original_local_and_baseline_stages_false': True,
    'all_global_and_later_mapping_stages_true': True,
    'two_batch03_original_U_U_U_histories_preserved': True,
    '0131_original_I_M_normalized_I_baseline_I_then_later_U_U_current_U_preserved': True,
    '0131_original21x25_container_preserved_distinct_from_later_wider_container': True,
    '0131_negative_excess_above_central_patch_distinct_from_prior0130': True,
    'batch03_periodic_right_edge_fullscale_limit_not_central_classification': True,
    'predicted_centers_outside_common_topocentric_core': 4,
    'discovery_markers_outside_common_topocentric_core': 1,
    'direct_C021_same_source_overlap_angstrom': 3.585000000000946,
    'both_full_cores_inside_opposite_reference_flanks': True,
    'shared_C021_source_input_index_records': reuse,
    'shared_index_counts_are_both_frame_union_plus_brackets_not_new_pixel_test': True,
    'prior_C021_arrays_opened_or_method_rerun_for_lineage_check': False,
    'all_four_figures_visually_inspected': True, 'native_pages': 1, 'raw_pages': 1,
    'page_rows': [3], 'figures': figures, 'report_links_verified': len(links),
    'report_sha256': sha(HERE/'RESULTS_REPORT.md'), 'plot_index_sha256': sha(OUT/'PLOT_INDEX.json'),
    'independent_actual_audit_sha256': sha(HERE.parent/'independent_audit/NUMERICAL_AUDIT.json'),
    'next_group': 'C017', 'next_member_count': 1, 'next_route': 'INDIVIDUAL_PROFILE_CONTEXT',
    'next_own_February_anchor_and_original_singleton_core_preserved': True,
    'next_original_order2_false_order3_true_and_U_U_U_preserved': True,
    'next_C018_same_source_overlap_angstrom': 4.8412500000004,
    'next_C017_and_C018_cores_in_surrounding_context_but_not_reference_flanks': True,
    'next_selection_fixed_before_current_values_and_no_future_array_execution': True,
    'method_or_numerical_mutations': 0, 'labels_changed': 0,
}
(HERE/'RESULTS_QA.json').write_text(json.dumps(qa, indent=2)+'\n')
assert all((HERE/q).exists() or q.startswith('http') for q in links)
print(json.dumps({k: v for k, v in qa.items() if k not in ['figures', 'per_reference_families', 'shared_C021_source_input_index_records']}, indent=2))
