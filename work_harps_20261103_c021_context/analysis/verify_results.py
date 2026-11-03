#!/usr/bin/env python3
"""Verify C021 delivery without re-executing frozen scientific methods."""
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
assert len(P['source_hashes']) == 92 and len(H) == 51
assert sum(f.endswith('.npz') for f in H) == 41
assert sha(OUT / 'OUTPUT_HASHES.json') == 'd5b90db69fb0877f7c0dfe9eed11bcb3ab502903eae06e98a29aa3552ab00483'
public = read(HERE.parent / 'PROSPECTIVE_PUBLICATION_RECEIPT.json')
assert public['status'] == 'PASS_EXACT_REMOTE_READBACK' and len(public['files']) == 25
for f in public['files']:
    assert sha(REPO / f['path']) == f['sha256']
    assert (REPO / f['path']).stat().st_size == f['bytes']
expected = ['figures/MERGED_BROAD_CONTEXT.png', 'figures/MERGED_CORE_CONTEXT.png']
expected += [f'figures/NATIVE_ORDERS_{i}.png' for i in range(1, 3)]
expected += [f'figures/PRESERVED_RAW_ORDER_CONTEXT_{i}.png' for i in range(1, 3)]
assert [r['path'] for r in I['files']] == expected
assert I['native_pages'] == I['raw_pages'] == 2 and I['total_figures'] == 6
assert I['all_five_reference_and_marker_ids'] == list(P['events'])
assert I['all24_profile_slots_retained'] and I['all_five_original_event_raw_contexts_retained']
assert I['numeric_outputs_unchanged'] and I['origin_assignments'] == 0
figures = []
for row in I['files']:
    f = OUT / row['path']
    assert sha(f) == row['sha256'] and f.stat().st_size == row['bytes']
    Image.open(f).verify()
    im = Image.open(f)
    im.load()
    figures.append({**row, 'size': list(im.size), 'png_decode': 'PASS', 'visually_inspected': True})
assert len(R) == 24 and len(C) == 160
assert sum(r['identical_product_self_pair'] for r in C) == 20
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
assert P['target'] == 'HD114783' and P['group_center_bary_air_angstrom'] == 4309.82625
assert P['anchor_dp_id'] == 'ADP.2022-01-22T01:09:14.958'
assert P['anchor_berv_km_s'] == 29.658729150824
assert read(OUT / 'SUMMARY.json')['topocentric_anchor_air_angstrom'] == 4309.39991731037
assert len(P['merged_dp_ids']) == 7 and len(P['discovery_dp_ids']) == 5
assert set(P['merged_dp_ids']) - set(P['discovery_dp_ids']) == {
    'ADP.2023-03-23T01:02:04.833', 'ADP.2023-05-16T01:01:18.574'}
assert P['events']['V2E2-0139'] == 'ADP.2023-07-02T01:01:43.311'
centers = {'V2E2-0116': 4309.827499999999, 'V2E2-0121': 4309.827499999999,
           'V2E2-0126': 4309.825, 'V2E2-0130': 4309.825, 'V2E2-0139': 4309.827499999999}
assert P['individual_event_centers_bary_air_angstrom'] == centers
assert len(P['event_markers']) == 5
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
assert len(MC) == 140 and len(NC) == 20
assert all(r['order'] == 19 and r['dp_id'] == r['reference_dp_id'] and r['same_exposure']
           and not r['identical_product_self_pair'] for r in NC)
nonself = [r for r in MC if not r['identical_product_self_pair']]
assert len(nonself) == 120
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
        assert len(rows) == 30
        assert len({tuple(sorted([r['dp_id'], r['reference_dp_id']])) for r in rows}) == 20
        for a, b in itertools.combinations(P['discovery_dp_ids'], 2):
            assert abs(by[a, b, frame, region]['raw_pearson'] - by[b, a, frame, region]['raw_pearson']) < 1e-12
            assert abs(by[a, b, frame, region]['normalized_rms'] - by[b, a, frame, region]['normalized_rms']) < 1e-12
jan1, jan2 = P['events']['V2E2-0116'], P['events']['V2E2-0130']
assert round(by[jan1, jan2, 'topocentric', 'core']['raw_pearson'], 6) == .990194
assert round(by[jan1, jan2, 'topocentric', 'broad_pattern']['raw_pearson'], 6) == .994276
assert min(r['raw_pearson'] for r in NC if r['region'] == 'core') >= .999889
assert min(r['raw_pearson'] for r in NC if r['region'] == 'broad_pattern') >= .999297
native = [r for r in R if r['kind'] == 'native']
assert sorted(set(r['window_native_finite_samples'] for r in native)) == [504, 505, 506, 507]
assert set(r['left_flank_finite_samples'] for r in native) == {124, 125}
assert set(r['right_flank_finite_samples'] for r in native) == {128}
assert all(r['window_native_finite_samples'] == 600 and r['left_flank_finite_samples']
           == r['right_flank_finite_samples'] == 150 for r in R if r['kind'] == 'merged')
history = P['historical_review_disagreement']['per_event_history']
assert len(history) == 5
for r in history:
    assert r['current_adopted_code'] == 'U'
    if r['candidate_id'] == 'V2E2-0130':
        assert r['original_primary_code'] == 'I' and r['original_secondary_code'] == 'M'
        assert r['original_secondary_normalized_code'] == r['original_adopted_baseline_code'] == 'I'
        assert r['later_mapping_followup_primary_code'] == r['later_mapping_followup_secondary_code'] == 'U'
        assert r['coordinates_changed'] is False and r['original_native_and_raw_pixels_preserved']
    else:
        assert r['original_primary_code'] == r['original_secondary_code'] == r['original_adopted_code'] == 'U'
assert len(P['historical_mapping_stages']) == 5
for r in P['historical_mapping_stages']:
    expected_original = r['event'] in ['V2E2-0121', 'V2E2-0139']
    assert r['order'] == 19 and r['original_grid_mapping_usable'] and r['final_reference_mapping_supported']
    assert r['original_local_mapping_usable'] is expected_original
    assert r['original_baseline_mapping_verified'] is expected_original
    assert r['registration_changed'] is False
    assert r['baseline_field_basis'] == ('mapping_verified in original raw_followup mapping'
                                         if r['event'] == 'V2E2-0130'
                                         else 'explicit baseline_mapping_verified in batch03 mapping')
raw = read(OUT / 'PRESERVED_RAW_CONTEXT.json')
assert len(raw) == 5
for r in raw:
    assert sha(OUT / r['copied_path']) == r['file']['sha256']
    shapes = {v['key']: v['shape'] for v in r['npy_headers']}
    assert shapes['raw_cutout'] == shapes['raw_excess'] == ([21, 25] if r['event'] == 'V2E2-0130' else [31, 33])
science = read(HERE.parent / 'scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json')
assert sum(not r['expected_center_inside_fixed_core'] for r in science['metadata_expected_feature_locations']) == 4
assert sum(abs(m['discovery_topocentric_offset_angstrom']) > .25 for m in P['event_markers']) == 2
N = read(HERE.parent / 'scientific_review/NEXT_GROUP_METADATA.json')
assert N['next_core_group'] == 'C022'
assert [m['candidate_id'] for m in N['members']] == ['V2E2-0117', 'V2E2-0127', 'V2E2-0131']
assert N['proposed_group_center_bary_air_angstrom'] == 4312.241249999999
assert N['proposed_topocentric_anchor_air_angstrom'] == 4311.814678415948
dep = N['wavelength_dependency']
assert dep['shared_bounded_spectral_source_pixels_with_C021']
assert dep['overlap_width_angstrom'] == 3.585000000000946
assert dep['next_common_core_fully_inside_current_positive_reference_flank']
assert dep['current_common_core_fully_inside_next_negative_reference_flank']
assert dep['core_intervals_disjoint']
special = next(r for r in N['historical_review_disagreement']['per_event_history'] if r['candidate_id'] == 'V2E2-0131')
assert special['original_primary_code'] == 'I' and special['original_secondary_code'] == 'M'
assert special['original_secondary_normalized_code'] == special['original_adopted_baseline_code'] == 'I'
assert special['later_mapping_followup_primary_code'] == special['later_mapping_followup_secondary_code'] == special['current_adopted_code'] == 'U'
report = (HERE / 'RESULTS_REPORT.md').read_text()
for text in ['24 profiles and 160 comparisons', 'All five current C021 codes remain U',
             'Thirty directed nonself rows per frame/region represent 20 unordered exposure pairs and 10 reciprocal',
             'March 22 and May 15 2023 remain cohort nonreferences', '24 false low-reference flags',
             'zero in all 24 rows', '0.990194 core / 0.994276 surroundings',
             'Only two of the five discovery markers are outside: May 5 2022 and July 1 2023',
             'false for 0116/0126/0130', 'true for 0121/0139',
             '0130 originally has primary I, secondary M normalized to I, and adopted baseline I',
             '0130 retains its exact original 21×25 five-array container',
             'strong periodic right-edge structure that dominates their full scales',
             'All six figures were visually inspected and fully decoded',
             'directly reuse spectral pixels over 3.585000000000946 Å',
             'entire future C022 core', 'entire current C021 core',
             'No C022 array analysis or completed-diagnostic replay was executed here']:
    assert text in report, text
for event in P['events']:
    assert '### ' + event + ' reference:' in report
links = re.findall(r'\]\(([^)]+)\)', report)
assert not [q for q in links if not (HERE / q).exists() and not q.startswith('http') and q != 'RESULTS_QA.json']
audit = read(HERE.parent / 'independent_audit/NUMERICAL_AUDIT.json')
assert audit['status'].startswith('PASS') and audit['checks_passed'] == 834 and audit['scalar_values_compared'] == 94802
qa = {
    'status': 'PASS_COMPLETE_C021_RESULT_DELIVERY',
    'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'target': 'HD114783', 'common_midpoint': 4309.82625,
    'exact_member_float_core_and_marker_identities_preserved': True,
    'frozen_source_hashes_verified': 92, 'public_method_bindings_verified': 25,
    'numerical_output_hashes_verified': 51, 'numerical_npz_files_verified': 41,
    'stable_numeric_ledger_sha256': sha(OUT / 'OUTPUT_HASHES.json'),
    'profile_slots': 24, 'comparison_slots': 160, 'merged_comparisons': 140,
    'native_same_exposure_comparisons': 20, 'identical_product_self_comparisons': 20,
    'observations': 7, 'fixed_discovery_references': 5,
    'July1_reference_and_March22_May15_nonreferences_preserved': True,
    'per_reference_families': families, 'directed_nonself_rows_per_frame_region': 30,
    'unordered_pairs_per_frame_region': 20, 'reciprocal_duplicates_per_frame_region': 10,
    'bounded_source_windows': 12, 'preserved_original_raw_copies': 5,
    'full_valid_positive_reference_profiles': 24, 'false_low_reference_flags': 24,
    'true_low_reference_flags': 0, 'null_low_reference_flags': 0,
    'raw_only_profiles': 0, 'blocked_profiles': 0, 'evaluable_Pearson': 160, 'evaluable_RMS': 160,
    'all_comparisons_complete_raw_and_normalized_support': True,
    'all_profiles_zero_positive_ERR': True, 'all_profiles_zero_gap_and_outside_coverage_masks': True,
    'profiles_with_nonpositive_source_window_samples': 0,
    'all24_window_left_right_nonpositive_fractions_zero': True,
    'native_original_finite_window_range': [504, 507],
    'native_original_left_flank_range': [124, 125], 'native_original_right_flank_counts': [128],
    'January_pair_topocentric_raw_r_core_surrounding': [.990194, .994276],
    'structured_reference_flanks_retained_without_masks': True,
    'mixed_original_mapping_false_0116_0126_0130_true_0121_0139_preserved': True,
    'all_global_and_later_mapping_stages_true': True,
    'four_batch03_original_U_U_U_histories_preserved': True,
    '0130_original_I_M_normalized_I_baseline_I_then_later_U_U_current_U_preserved': True,
    '0130_original21x25_container_preserved_distinct_from_later_wider_container': True,
    'periodic_right_edge_fullscale_limit_not_central_classification': True,
    'predicted_centers_outside_common_topocentric_core': 4,
    'discovery_markers_outside_common_topocentric_core': 2,
    'bounded_spectral_disjointness_not_claimed_raw_crop_independence': True,
    'all_six_figures_visually_inspected': True, 'native_pages': 2, 'raw_pages': 2,
    'page_rows': [4, 1], 'figures': figures, 'report_links_verified': len(links),
    'report_sha256': sha(HERE / 'RESULTS_REPORT.md'),
    'plot_index_sha256': sha(OUT / 'PLOT_INDEX.json'),
    'independent_actual_audit_sha256': sha(HERE.parent / 'independent_audit/NUMERICAL_AUDIT.json'),
    'next_group': 'C022', 'next_member_count': 3,
    'next0131_staged_I_M_normalized_I_baseline_I_then_later_U_preserved': True,
    'C022_same_source_overlap_angstrom': 3.585000000000946,
    'future_C022_core_inside_current_positive_reference_flank': True,
    'current_C021_core_inside_future_negative_reference_flank': True,
    'next_selection_fixed_before_current_values_and_no_future_array_execution': True,
    'method_or_numerical_mutations': 0, 'labels_changed': 0,
}
(HERE / 'RESULTS_QA.json').write_text(json.dumps(qa, indent=2) + '\n')
assert all((HERE / q).exists() or q.startswith('http') for q in links)
print(json.dumps({k: v for k, v in qa.items() if k not in ['figures', 'per_reference_families']}, indent=2))
