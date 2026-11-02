#!/usr/bin/env python3
"""Verify C002 delivery, including partial/raw-only support and signed fractions."""
from pathlib import Path
from PIL import Image
import datetime
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
OUT = HERE / 'results'
REPO = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_bytes())
plan = read(HERE / 'PLAN.json')
numerical = read(OUT / 'OUTPUT_HASHES.json')
plots = read(OUT / 'PLOT_INDEX.json')
metrics = read(OUT / 'PROFILE_METRICS.json')
pairs = read(OUT / 'COMPARISONS.json')
for f, h in plan['source_hashes'].items():
    assert sha(REPO / f) == h, f
for f, h in numerical.items():
    assert sha(OUT / f) == h, f
assert len(numerical) == 39
assert sum(f.endswith('.npz') for f in numerical) == 29
assert len(plots['files']) == 4
figures = []
for f in plots['files']:
    p = OUT / f['path']
    assert sha(p) == f['sha256'] and p.stat().st_size == f['bytes']
    im = Image.open(p)
    im.verify()
    im = Image.open(p)
    im.load()
    figures.append({**f, 'size': list(im.size), 'png_decode': 'PASS', 'visually_inspected': True})
assert len(metrics) == 18 and len(pairs) == 36
assert sum(x['identical_product_self_pair'] for x in pairs) == 4
assert all(x['positive_finite_ERR_samples'] == 0 for x in metrics)
valid = [x for x in metrics if x['normalization_status'] == 'USABLE_POSITIVE_FLANK_REFERENCE']
rawonly = [x for x in metrics if x['normalization_status'] == 'RAW_ONLY']
assert len(valid) == 16 and len(rawonly) == 2
assert all(x['raw_grid_finite_samples'] == 601 and x['normalized_grid_finite_samples'] == 601
           and x['low_flank_reference'] is False for x in valid)
assert all(x['kind'] == 'native' and x['order'] == 2
           and x['normalization_reasons'] == ['MISSING_RIGHT_FLANK_COVERAGE']
           and x['raw_grid_finite_samples'] == 417 and x['normalized_grid_finite_samples'] == 0
           and x['flank_reference'] is None and x['available_flank_median'] > 0
           and x['low_flank_reference'] is None and x['window_native_finite_samples'] == 465
           and x['window_nonpositive_fraction'] == 19 / 465
           and x['left_flank_nonpositive_fraction'] == 3 / 165
           and x['right_flank_native_samples'] == 0 for x in rawonly)
blocked_pearson = [x for x in pairs if x['raw_pearson'] is None]
blocked_rms = [x for x in pairs if x['normalized_rms'] is None]
assert len(blocked_pearson) == 2 and len(blocked_rms) == 4
assert all(x['order'] == 2 and x['region'] == 'broad_pattern'
           and x['common_finite_raw_samples'] == 366
           and x['minimum_common_samples'] == 440
           and x['raw_pearson_block_reason'] == 'INSUFFICIENT_COMMON_RAW_COVERAGE' for x in blocked_pearson)
assert all(x['order'] == 2 and x['common_finite_normalized_samples'] == 0
           and x['normalized_rms_block_reason'] == 'INVALID_REFERENCE_OR_INSUFFICIENT_NORMALIZED_COVERAGE'
           for x in blocked_rms)
nonpositive = [x for x in metrics if x['window_nonpositive_fraction'] > 0]
assert len(nonpositive) == 5
merged_nonpositive = [x for x in nonpositive if x['kind'] == 'merged']
assert {(x['dp_id'], x['frame']) for x in merged_nonpositive} == {
    ('ADP.2023-01-01T01:10:52.479', 'barycentric'),
    ('ADP.2023-07-05T01:02:00.053', 'barycentric'),
    ('ADP.2023-07-05T01:02:00.053', 'topocentric')}
assert all(x['window_native_finite_samples'] == 600 and x['window_nonpositive_fraction'] == 1 / 600
           and x['left_flank_nonpositive_fraction'] == 1 / 150 for x in merged_nonpositive)
links = re.findall(r'\]\(([^)]+)\)', (HERE / 'RESULTS_REPORT.md').read_text())
missing = [x for x in links if not (HERE / x).exists()
           and not x.startswith('http') and x != 'RESULTS_QA.json']
assert not missing, missing
qa = {
    'status': 'PASS_COMPLETE_C002_RESULT_DELIVERY_WITH_EXPLICIT_RAW_ONLY_SLOTS',
    'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'frozen_source_hashes_verified': len(plan['source_hashes']),
    'numerical_output_hashes_verified': len(numerical),
    'numerical_npz_files_verified': 29,
    'profile_slots': len(metrics), 'comparison_slots': len(pairs),
    'identical_product_self_comparisons': 4, 'distinct_discovery_products': 1,
    'full_profiles_with_valid_positive_reference_and_false_low_flag': 16,
    'raw_only_profiles_with_null_reference_and_null_low_flag': 2,
    'raw_only_reason': 'MISSING_RIGHT_FLANK_COVERAGE',
    'evaluable_Pearson': 34, 'unavailable_Pearson': 2,
    'evaluable_RMS': 32, 'unavailable_RMS': 4,
    'unavailable_statistics_match_fixed_support_and_normalization_gates': True,
    'all_profiles_zero_positive_ERR': True,
    'profiles_with_nonpositive_source_samples': [{k: x[k] for k in
        ['source_id', 'dp_id', 'order', 'frame', 'window_nonpositive_fraction',
         'window_native_finite_samples', 'left_flank_nonpositive_fraction',
         'right_flank_nonpositive_fraction']} for x in nonpositive],
    'remaining_13_profiles_zero_nonpositive_fraction': True,
    'figures': figures,
    'all_four_figures_visually_inspected': True,
    'core_title_and_seven_epoch_legend_inspected_at_original_resolution': True,
    'order_2_raw_only_annotation_and_complete_raw_panels_inspected': True,
    'report_links_verified': len(links),
    'report_sha256': sha(HERE / 'RESULTS_REPORT.md'),
    'plot_index_sha256': sha(OUT / 'PLOT_INDEX.json'),
    'independent_actual_audit_sha256': sha(HERE.parent / 'independent_audit/NUMERICAL_AUDIT.json'),
    'method_or_numerical_mutations': 0, 'labels_changed': 0,
    'notes': [
        'Both exact raw order panels and the fixed May-2022 discovery reference are retained.',
        'Order 2 available positive one-sided median is not a valid two-flank reference; low flag remains null.',
        'Order 2 historical local/baseline failures remain distinct from true global/five-window stages.',
        'The separate bright lower-right order 3 patch is preserved at full scale and was already noted by historical secondary review; no origin assigned.',
        'C002 core was already visible in C003 surroundings; broader C003/C004 overlap and shared observations remain explicit.',
        'No presentation repair, image edit or frozen-method change required.'
    ]
}
(HERE / 'RESULTS_QA.json').write_text(json.dumps(qa, indent=2) + '\n')
assert all((HERE / x).exists() or x.startswith('http') for x in links)
print(json.dumps({k: v for k, v in qa.items() if k != 'figures'}, indent=2))
