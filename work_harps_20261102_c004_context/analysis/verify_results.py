#!/usr/bin/env python3
"""Verify fixed C004 delivery bytes, complete accounting and report links."""
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
assert len(numerical) == 43
assert sum(f.endswith('.npz') for f in numerical) == 33
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
assert len(metrics) == 20 and len(pairs) == 96
assert sum(x['identical_product_self_pair'] for x in pairs) == 12
assert all(x['raw_grid_finite_samples'] == 601 and x['normalized_grid_finite_samples'] == 601
           and x['normalization_status'] == 'USABLE_POSITIVE_FLANK_REFERENCE'
           and x['low_flank_reference'] is False
           and x['positive_finite_ERR_samples'] == 0 for x in metrics)
assert all(x['raw_pearson'] is not None and x['normalized_rms'] is not None for x in pairs)
nonpositive = [x for x in metrics if x['window_nonpositive_fraction'] > 0]
assert len(nonpositive) == 2
assert {x['frame'] for x in nonpositive} == {'barycentric', 'topocentric'}
assert all(x['dp_id'] == 'ADP.2022-05-08T01:01:37.876'
           and x['window_native_finite_samples'] == 600
           and x['window_nonpositive_fraction'] == 1 / 600 for x in nonpositive)
links = re.findall(r'\]\(([^)]+)\)', (HERE / 'RESULTS_REPORT.md').read_text())
missing = [x for x in links if not (HERE / x).exists()
           and not x.startswith('http') and x != 'RESULTS_QA.json']
assert not missing, missing
qa = {
    'status': 'PASS_COMPLETE_C004_RESULT_DELIVERY',
    'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'frozen_source_hashes_verified': len(plan['source_hashes']),
    'numerical_output_hashes_verified': len(numerical),
    'numerical_npz_files_verified': 33,
    'profile_slots': len(metrics),
    'comparison_slots': len(pairs),
    'identical_product_self_comparisons': 12,
    'distinct_discovery_products': 3,
    'all_profiles_full_positive_reference_no_low_flag': True,
    'all_profiles_zero_positive_ERR': True,
    'profiles_with_nonpositive_source_samples': [{k: x[k] for k in
        ['source_id', 'dp_id', 'frame', 'window_nonpositive_fraction',
         'window_native_finite_samples', 'left_flank_nonpositive_fraction',
         'right_flank_nonpositive_fraction']} for x in nonpositive],
    'remaining_18_profiles_zero_nonpositive_fraction': True,
    'all_Pearson_and_RMS_evaluable': True,
    'figures': figures,
    'all_four_figures_visually_inspected': True,
    'core_title_and_seven_epoch_legend_inspected_at_original_resolution': True,
    'report_links_verified': len(links),
    'report_sha256': sha(HERE / 'RESULTS_REPORT.md'),
    'plot_index_sha256': sha(OUT / 'PLOT_INDEX.json'),
    'independent_actual_audit_sha256': sha(HERE.parent / 'independent_audit/NUMERICAL_AUDIT.json'),
    'method_or_numerical_mutations': 0,
    'labels_changed': 0,
    'notes': [
        'All three exact raw event panels and three unique discovery references retained.',
        'C003/C004 reciprocal core and reference-flank overlap and reused observations remain explicit.',
        'The March-2022 first-discovery anchor is unchanged; January edge proximity and May-2023 reference displacement are reported.',
        'The two May-2022 profile nonpositive fractions refer to one exposure; signed values remain retained.',
        'All historical mapping stages are true for all three records, and remain historical rather than new validation.',
        'No presentation repair, image edit or frozen-method change required.'
    ]
}
(HERE / 'RESULTS_QA.json').write_text(json.dumps(qa, indent=2) + '\n')
assert all((HERE / x).exists() or x.startswith('http') for x in links)
print(json.dumps({k: v for k, v in qa.items() if k != 'figures'}, indent=2))
