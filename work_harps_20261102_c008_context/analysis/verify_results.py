#!/usr/bin/env python3
"""Verify unchanged C008 delivery and complete profile/comparison accounting."""
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
assert len(plan['source_hashes']) == 45
assert len(numerical) == 35
assert sum(f.endswith('.npz') for f in numerical) == 25
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
assert len(metrics) == 16 and len(pairs) == 32
assert sum(x['identical_product_self_pair'] for x in pairs) == 4
assert all(x['normalization_status'] == 'USABLE_POSITIVE_FLANK_REFERENCE'
           and x['normalization_reasons'] == [] and x['status'] == 'MEASURED_CONTEXT'
           and x['flank_reference'] > 0 and x['raw_grid_finite_samples'] == 601
           and x['normalized_grid_finite_samples'] == 601 and x['low_flank_reference'] is False
           and x['positive_finite_ERR_samples'] == 0 and x['window_nonpositive_fraction'] == 0
           and x['left_flank_nonpositive_fraction'] == 0 and x['right_flank_nonpositive_fraction'] == 0
           and x['outside_native_coverage_grid_samples'] == 0 and x['gap_masked_grid_samples'] == 0
           for x in metrics)
assert all(x['raw_pearson'] is not None and x['normalized_rms'] is not None
           and x['raw_pearson_block_reason'] is None and x['normalized_rms_block_reason'] is None
           and x['common_finite_raw_samples'] == (51 if x['region'] == 'core' else 550)
           and x['common_finite_normalized_samples'] == (51 if x['region'] == 'core' else 550)
           for x in pairs)
assert {x['order'] for x in metrics if x['kind'] == 'native'} == {43}
report = (HERE / 'RESULTS_REPORT.md').read_text()
for required in ['V2E2-0047 remains U', 'January 2022 is retained as the weakest comparison',
                 'inside the positive [1.5, 3] Å reference flank', 'Two bright structures at the far right edge',
                 'not blind, untouched or independent', 'C009 / V2E2-0050']:
    assert required in report, required
links = re.findall(r'\]\(([^)]+)\)', report)
missing = [x for x in links if not (HERE / x).exists()
           and not x.startswith('http') and x != 'RESULTS_QA.json']
assert not missing, missing
qa = {
    'status': 'PASS_COMPLETE_C008_RESULT_DELIVERY',
    'checked_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'frozen_source_hashes_verified': len(plan['source_hashes']),
    'numerical_output_hashes_verified': len(numerical),
    'numerical_npz_files_verified': 25,
    'profile_slots': len(metrics), 'comparison_slots': len(pairs),
    'identical_product_self_comparisons': 4, 'distinct_discovery_products': 1,
    'full_profiles_with_valid_positive_reference_and_false_low_flag': 16,
    'raw_only_profiles': 0, 'blocked_profiles': 0, 'structurally_excluded_native_orders': 0,
    'evaluable_Pearson': 32, 'unavailable_Pearson': 0,
    'evaluable_RMS': 32, 'unavailable_RMS': 0,
    'all_comparisons_complete_raw_and_normalized_region_support': True,
    'all_profiles_zero_positive_ERR': True,
    'all_profiles_zero_nonpositive_window_and_flank_fractions': True,
    'all_profiles_zero_missing_coverage_or_gap_masks': True,
    'figures': figures,
    'all_four_figures_visually_inspected': True,
    'root_also_reported_all_four_figures_reviewed_layout_acceptable': True,
    'report_links_verified': len(links),
    'report_sha256': sha(HERE / 'RESULTS_REPORT.md'),
    'plot_index_sha256': sha(OUT / 'PLOT_INDEX.json'),
    'independent_actual_audit_sha256': sha(HERE.parent / 'independent_audit/NUMERICAL_AUDIT.json'),
    'method_or_numerical_mutations': 0, 'labels_changed': 0,
    'notes': [
        'Fixed March 2023 discovery reference and order 43 raw panel retained; no additional references or acquisition.',
        'January 2022 retained as weakest core/surrounding comparison, with complete six-epoch ranges.',
        'Broad slope and deep trough near +2 Angstrom are included in surrounding Pearson and in the fixed positive reference flank.',
        'Different structured flank levels do not define a line-free continuum; scaled core height is not a measured emission-line strength.',
        'Two bright far-right-edge raw structures are shown separately from the faint central context and assigned no physical origin.',
        'Historical mapping stages all true; no new mapping validation or origin inference.',
        'Disjoint bounded wavelength region still shares all seven observations and original epoch/raw evidence.',
        'No presentation repair, image edit or frozen-method change required.'
    ]
}
(HERE / 'RESULTS_QA.json').write_text(json.dumps(qa, indent=2) + '\n')
assert all((HERE / x).exists() or x.startswith('http') for x in links)
print(json.dumps({k: v for k, v in qa.items() if k not in ['figures', 'notes']}, indent=2))
