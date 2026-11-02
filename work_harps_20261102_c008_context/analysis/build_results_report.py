#!/usr/bin/env python3
"""Render the fixed C008 context from unchanged released tables."""
from pathlib import Path
import datetime
import json
import statistics

HERE = Path(__file__).resolve().parent
OUT = HERE / 'results'
read = lambda p: json.loads(p.read_text())
P = read(HERE / 'PLAN.json')
R = read(OUT / 'PROFILE_METRICS.json')
C = read(OUT / 'COMPARISONS.json')
S = read(OUT / 'SUMMARY.json')
A = read(HERE.parent / 'independent_audit/NUMERICAL_AUDIT.json')
release = read(HERE / 'ROOT_RELEASE.json')
science = read(HERE.parent / 'scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json')
assert len(R) == 16 and len(C) == 32
assert sum(r['identical_product_self_pair'] for r in C) == 4
assert A['status'].startswith('PASS')
assert all(r['normalization_status'] == 'USABLE_POSITIVE_FLANK_REFERENCE'
           and r['raw_grid_finite_samples'] == 601 and r['normalized_grid_finite_samples'] == 601
           and r['low_flank_reference'] is False and r['positive_finite_ERR_samples'] == 0
           and r['window_nonpositive_fraction'] == 0 and r['left_flank_nonpositive_fraction'] == 0
           and r['right_flank_nonpositive_fraction'] == 0 for r in R)
assert all(r['raw_pearson'] is not None and r['normalized_rms'] is not None for r in C)
dates = {r['dp_id']: r['date_obs'][:10] for r in R}
frames = ['barycentric', 'topocentric']
fmt = lambda x: 'Unavailable' if x is None else f'{x:.6f}'
span = lambda values: fmt(min(values)) + '–' + fmt(max(values))
merged = [r for r in R if r['kind'] == 'merged']
native = [r for r in R if r['kind'] == 'native']
assert len(merged) == 14 and len(native) == 2 and all(r['order'] == 43 for r in native)

def pair(dp, frame, region, order=None):
    return next(r for r in C if r['dp_id'] == dp and r['frame'] == frame
                and r['region'] == region and r['order'] == order)

def bt(dp, region, key, order=None):
    return ' / '.join(fmt(pair(dp, frame, region, order)[key]) for frame in frames)

epoch_rows = []
for dp in P['merged_dp_ids']:
    if dp == P['anchor_dp_id']:
        continue
    fields = [bt(dp, region, key) for key in ['raw_pearson', 'normalized_rms']
              for region in ['core', 'broad_pattern']]
    epoch_rows.append('| ' + dates[dp] + ' | ' + ' | '.join(fields) + ' |')
    for region in ['core', 'broad_pattern']:
        b, t = [pair(dp, frame, region) for frame in frames]
        assert b['raw_pearson'] > t['raw_pearson'] and b['normalized_rms'] < t['normalized_rms']
nonself = [r for r in C if r['relationship'] == 'MERGED_EPOCH_TO_DISCOVERY'
           and not r['identical_product_self_pair']]
core = [r['raw_pearson'] for r in nonself if r['frame'] == 'barycentric' and r['region'] == 'core']
broad = [r['raw_pearson'] for r in nonself if r['frame'] == 'barycentric' and r['region'] == 'broad_pattern']
jan = P['merged_dp_ids'][0]
assert dates[jan] == '2022-01-05'
assert pair(jan, 'barycentric', 'core')['raw_pearson'] == min(core)
assert pair(jan, 'barycentric', 'broad_pattern')['raw_pearson'] == min(broad)
native_fields = [bt(P['anchor_dp_id'], region, key, 43) for key in ['raw_pearson', 'normalized_rms']
                 for region in ['core', 'broad_pattern']]
offset_rows = []
for r in science['metadata_expected_feature_locations']:
    role = 'Discovery' if r['dp_id'] == P['anchor_dp_id'] else 'Other epoch'
    offset_rows.append(f"| {r['date_obs'][:10]} | {role} | {r['expected_center_offset_from_fixed_anchor_angstrom']:+.9f} | "
                       + ('Inside' if r['expected_center_inside_fixed_core'] else 'Outside') + ' |')
assert sum(not r['expected_center_inside_fixed_core'] for r in science['metadata_expected_feature_locations']) == 5
reference_rows = []
for kind, label in [('merged', 'Merged (ADU)'), ('native', 'Native order 43 (unspecified)')]:
    r = next(r for r in R if r['kind'] == kind and r['dp_id'] == P['anchor_dp_id'] and r['frame'] == 'barycentric')
    t = next(x for x in R if x['kind'] == kind and x['dp_id'] == P['anchor_dp_id'] and x['frame'] == 'topocentric')
    keys = ['left_flank_median', 'right_flank_median', 'flank_reference', 'first_difference_noise_proxy']
    assert all(r[k] == t[k] for k in keys)
    reference_rows.append('| ' + label + ' | ' + ' | '.join(fmt(r[k]) for k in keys) + ' |')
completed = datetime.datetime.fromisoformat(S['completed_utc']).strftime('%Y-%m-%d at %H:%M:%S UTC')
diffs = A['maximum_absolute_differences_by_kind']
report = f'''# C008: HD106515A individual spectral context

The shallow asymmetric shoulder near 5182.005 Å and the extensive surrounding spectrum recur in barycentric coordinates across the seven existing epochs. **V2E2-0047 remains U.** The feature sits on a structured, declining spectral level; neither the high surrounding correlation nor the scaled shoulder height establishes an isolated emission line, physical origin, qualified laser candidate or calibrated null.

The single released execution completed on **{completed}**: **16 profiles and 32 comparisons**, including four identical-product self rows, eight bounded source windows and one exact historical raw-panel copy. All profiles and comparisons are numerically evaluable; none is raw-only, blocked or structurally excluded. The fixed discovery reference is 2023-03-22. No new acquisition or observing time was added.

## All six other epochs against the fixed discovery

The original center is **5182.005 Å** in barycentric air wavelengths. The March 2023 discovery BERV **3.26509772194068 km/s** gives the single topocentric-air anchor **5181.9485623946 Å**. The unchanged ±3 Å window has 601 centers on a 0.01 Å grid: 51 in the original ±0.25 Å core and 550 in the surroundings. The common-support minima remain 41/440. No center, width, lag, stellar velocity, drift, continuum or background was fitted.

Values separated by `/` below are barycentric/topocentric. Each row is one other epoch against the sole reference. The four self rows remain in the complete output at r = 1 to floating-point precision and normalized RMS = 0; they add no independent recurrence evidence.

| Other observation (UTC) | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
{chr(10).join(epoch_rows)}

Nonself barycentric core r spans **{span(core)}**, median **{fmt(statistics.median(core))}**; surrounding r spans **{span(broad)}**, median **{fmt(statistics.median(broad))}**. All six nonself pairs have higher barycentric r and lower barycentric normalized RMS in both regions, under this fixed calculation. **January 2022 is retained as the weakest comparison**: core/surrounding r **{fmt(pair(jan, 'barycentric', 'core')['raw_pearson'])} / {fmt(pair(jan, 'barycentric', 'broad_pattern')['raw_pearson'])}**, with the largest barycentric RMS **{fmt(pair(jan, 'barycentric', 'core')['normalized_rms'])} / {fmt(pair(jan, 'barycentric', 'broad_pattern')['normalized_rms'])}**. The other five epochs do not replace this full range.

- [All seven epochs: full signed and scaled context](results/figures/MERGED_BROAD_CONTEXT.png)
- [The same epochs: original core](results/figures/MERGED_CORE_CONTEXT.png)

The core figure shows a shallow, multi-sample asymmetric shoulder and a dip near +0.1 Å on an elevated level. January 2022 differs visibly around that shoulder and dip. The broader figure contains an extended decline, several negative-offset dips and a deep trough near **+2 Å**. The surrounding Pearson statistic includes all of that large-scale structure; its value near one is not a separate validation of an isolated core feature. The singleton marker is the catalog/discovery coordinate, not a fitted peak in each epoch. All seven curves, full titles, legends and matching frame scales are retained.

## Fixed topocentric window

These positions were calculated from metadata before new values were read, assuming a barycentrically coherent catalog center. They are coordinate predictions, not measured peak locations.

| Observation (UTC) | Role | Predicted offset from fixed anchor (Å) | Original ±0.25 Å core |
|---|---|---:|---|
{chr(10).join(offset_rows)}

Five predicted centers lie outside the fixed topocentric core. Only March 2022 and the March 2023 discovery lie inside. The other comparisons may describe neighboring structure in that window, and the window is never recentered. The full BERV span of 59.6098131157401 km/s is coordinate separation, not a calibrated physical-origin test. [Prospective coordinates and caveats](../scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json).

## Reference levels, signed values and uncertainty limits

All **16 profiles have 601 finite raw and normalized grid samples**, positive valid two-flank references and false low-reference flags. Every source-window and separate flank nonpositive fraction is zero; signed values were retained without clipping. All 16 profiles have **zero positive finite ERR samples**. Full support and positive references do not provide a calibrated uncertainty model.

The 14 merged reference levels span **{min(r['flank_reference'] for r in merged):.3f}–{max(r['flank_reference'] for r in merged):.3f} ADU**; their first-difference proxies span **{min(r['first_difference_noise_proxy'] for r in merged):.3f}–{max(r['first_difference_noise_proxy'] for r in merged):.3f} ADU**. The low-reference condition, reference ≤ 3 × proxy, is descriptive and is not formal SNR. Native BUNIT is absent, so native extracted units remain unspecified.

The discovery reference has the following values in both frames:

| Product and units | Left-flank median | Right-flank median | Pooled reference | First-difference proxy |
|---|---:|---:|---:|---:|
{chr(10).join(reference_rows)}

The two flanks sample visibly different structured levels. The deep trough near +2 Å lies **inside the positive [1.5, 3] Å reference flank**; all of that structure remains in the fixed pooled median without masks or alternate flanks. These reference levels are not established line-free continua. A scaled core value around 1.6 is therefore not an emission-line strength relative to a fitted continuum. Positive scalar normalization leaves Pearson unchanged; scaled heights and RMS depend on the selected fixed levels.

## Native order and preserved raw panel

Fresh header checks of all 72 orders identify **order 43 alone** as covering the original center. Both full windows and flanks are retained. Its same-exposure native/merged comparisons are:

| Native order | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 43 | {' | '.join(native_fields)} |

[Native order 43](results/figures/NATIVE_ORDERS_1.png) follows the merged shape closely after separate fixed scaling, with small visible differences preserved. Native and merged products share an extraction lineage; this is not independent observing confirmation or a physical flux ratio.

[The exact historical raw cutout and excess map](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png) retain their complete scales. **Two bright structures at the far right edge dominate those scales**, while the nominal central band and residual are faint. The historical descriptions of an extended, trace-centered central residual and continuum variation concern the enlarged central context; they do not describe every structure in the full panel. The edge structures are retained separately from the catalog feature and receive no new origin assignment. No new pixel statistic, registration, background subtraction or spatial model was applied.

The original global, local, baseline and later five-window mapping stages are all true for order 43 and remain distinct historical diagnostics. They do not establish a new mapping result or physical origin. All primary, secondary and adopted reviews, the U label and prior outputs are unchanged. The catalog fixed-template width is not a measured physical linewidth.

## Dependence and reconstruction

The C008 window [5179.005, 5185.005] Å is disjoint from the completed C001–C007 bounded wavelength windows. Nevertheless, original epoch/profile and raw evidence for 0047 already existed, and all seven observing products are reused. This is not blind, untouched or independent observing evidence and adds no observing time or archive-wide completeness. Missing ERR and descriptive morphology do not establish significance, false-alarm probability, sensitivity or a qualified survey null.

The [independent arithmetic audit](../independent_audit/NUMERICAL_AUDIT.json) passes **{A['checks_passed']} checks across {A['scalar_values_compared']:,} scalar values**, covering all eight source windows, 16 profiles, 32 comparisons, one exact raw copy and four self rows without importing production functions. Source flux, ERR, indices and profile metrics agree exactly. Maximum wavelength difference is **{diffs['input_source_wavelength']:.3e} Å**, so wavelength arrays are not bitwise exact. Maximum raw interpolation difference is **{diffs['profile_signed_raw_flux']:.3e} native units**, normalized-profile difference **{diffs['profile_normalized_flux']:.3e}** and comparison difference **{diffs['comparison']:.3e}**. This verifies arithmetic rather than physical origin.

The method was public and read back before execution in commit `{release['publication_commit']}`. [Plan](PLAN.json), [root release](ROOT_RELEASE.json), [summary](results/SUMMARY.json), [bounded inputs](results/BOUNDED_INPUT_INDEX.json), [all profile metrics](results/PROFILE_METRICS.csv), [all comparisons](results/COMPARISONS.csv) and [numerical hashes](results/OUTPUT_HASHES.json) bind the run.

All four figures were visually inspected and fully decoded, with sizes and hashes checked against [PLOT_INDEX.json](results/PLOT_INDEX.json). All **45 frozen method/input sources and 35 numerical output files** remain unchanged. [RESULTS_QA.json](RESULTS_QA.json) records delivery checks. The next original-queue item is C009 / V2E2-0050; its metadata handoff preserves the root-adopted U despite earlier reviewer A assessments. No C009 analysis was executed here.
'''
(HERE / 'RESULTS_REPORT.md').write_text(report)
print(f'Wrote C008 report: {len(report.encode())} bytes.')
