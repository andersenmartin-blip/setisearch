#!/usr/bin/env python3
"""Render the complete released C002 result, including unavailable comparisons."""
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
assert len(R) == 18 and len(C) == 36
assert sum(r['identical_product_self_pair'] for r in C) == 4
assert A['status'].startswith('PASS')
assert all(r['positive_finite_ERR_samples'] == 0 for r in R)
dates = {r['dp_id']: r['date_obs'][:10] for r in R}
frames = ['barycentric', 'topocentric']
fmt = lambda x: 'Unavailable' if x is None else f'{x:.6f}'
span = lambda values: fmt(min(values)) + '–' + fmt(max(values))
merged = [r for r in R if r['kind'] == 'merged']
order2 = [r for r in R if r['kind'] == 'native' and r['order'] == 2]
order3 = [r for r in R if r['kind'] == 'native' and r['order'] == 3]
valid = [r for r in R if r['normalization_status'] == 'USABLE_POSITIVE_FLANK_REFERENCE']
assert len(valid) == 16 and len(order2) == 2 and len(order3) == 2
assert all(r['raw_grid_finite_samples'] == 601 and r['normalized_grid_finite_samples'] == 601
           and r['low_flank_reference'] is False for r in valid)
assert all(r['normalization_reasons'] == ['MISSING_RIGHT_FLANK_COVERAGE']
           and r['raw_grid_finite_samples'] == 417 and r['normalized_grid_finite_samples'] == 0
           and r['flank_reference'] is None and r['low_flank_reference'] is None for r in order2)
assert sum(r['raw_pearson'] is not None for r in C) == 34
assert sum(r['normalized_rms'] is not None for r in C) == 32

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
native_rows = []
for order in [2, 3]:
    fields = [bt(P['anchor_dp_id'], region, key, order) for key in ['raw_pearson', 'normalized_rms']
              for region in ['core', 'broad_pattern']]
    native_rows.append('| ' + str(order) + ' | ' + ' | '.join(fields) + ' |')
offset_rows = []
for r in science['metadata_expected_feature_locations']:
    role = 'Discovery' if r['dp_id'] == P['anchor_dp_id'] else 'Other epoch'
    offset_rows.append(f"| {r['date_obs'][:10]} | {role} | {r['expected_center_offset_from_fixed_anchor_angstrom']:+.9f} | "
                       + ('Inside' if r['expected_center_inside_fixed_core'] else 'Outside') + ' |')
signed_rows = []
nonpositive_merged = [r for r in merged if r['window_nonpositive_fraction'] > 0]
assert len(nonpositive_merged) == 3
for r in nonpositive_merged:
    assert r['window_native_finite_samples'] == 600 and r['window_nonpositive_fraction'] == 1 / 600
    assert r['left_flank_finite_samples'] == 150 and r['left_flank_nonpositive_fraction'] == 1 / 150
    signed_rows.append(f"| {r['date_obs'][:10]} | {r['frame']} | 1 / 600 (0.1667%) | 1 / 150 (0.6667%) |")
assert all(r['window_nonpositive_fraction'] == 19 / 465
           and r['left_flank_nonpositive_fraction'] == 3 / 165 for r in order2)
completed = datetime.datetime.fromisoformat(S['completed_utc']).strftime('%Y-%m-%d at %H:%M:%S UTC')
report = f'''# C002: HD106515A individual spectral context

The central crest, nearby shoulder and surrounding structured spectrum recur closely in barycentric coordinates across all seven existing target epochs. Native order 3 follows its same-exposure merged spectrum closely. Order 2 is noisier and lacks the entire positive reference flank; its signed raw context is retained with the resulting unavailable statistics. **V2E2-0033 remains U.** This is descriptive context, not a line identification, physical-origin assignment, qualified laser candidate or calibrated null.

The single released execution completed on **{completed}**. It retains **18 profile slots and 36 comparisons**, including **four identical-product self-comparisons**, nine bounded source windows and both historical raw panels. No source profile is blocked or structurally excluded. The two order 2 frame profiles are raw-only: **34 raw Pearson values and 32 normalized RMS values are evaluable out of 36 slots each**. Unavailable outcomes remain explicit. The only fixed discovery reference is the observation on 2022-05-07; no new acquisition or observing time was added.

## One fixed reference and all seven epochs

The barycentric air-wavelength center is **3868.6025 Å**. The fixed topocentric anchor is **3868.846286702511 Å**, using the **May 2022 discovery BERV −18.8907517532076 km/s**. The original ±0.25 Å core has **51 grid centers**, with **550 surrounding centers** across the full ±3 Å window on a 0.01 Å grid. Minimum common support is 41 core and 440 surrounding samples. No width, center, lag, stellar velocity, drift, continuum or background was fitted.

Every nonself merged epoch is compared with that unchanged discovery reference below. Values separated by `/` are barycentric/topocentric. Four discovery self rows remain in the complete output at r = 1 to floating-point precision and normalized RMS = 0; they do not add independent evidence.

| Other observation (UTC) | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
{chr(10).join(epoch_rows)}

Nonself barycentric core r spans **{span(core)}**, with median **{fmt(statistics.median(core))}**. Surrounding r spans **{span(broad)}**, with median **{fmt(statistics.median(broad))}**. All six nonself epoch pairs have higher barycentric r and lower barycentric normalized RMS in both regions. This describes the fixed windows, not a calibrated physical-origin test. The core figure retains a multi-sample central crest and a neighboring shoulder near −0.15 Å. The wider spectrum contains repeated peaks and troughs throughout the window; no isolated-feature or physical-linewidth inference follows.

- [All seven epochs: broad signed and scaled context](results/figures/MERGED_BROAD_CONTEXT.png)
- [The same epochs: fixed original core](results/figures/MERGED_CORE_CONTEXT.png)

Both figures retain their full titles and seven-epoch legends, with matching scales across frames. The marker identifies 0033 / R002 at its catalog/discovery coordinate. It does not follow fitted peaks in other epochs.

## Coordinate displacement in the fixed topocentric core

**The topocentric core is not recentered on the other epochs.** The following positions were calculated from metadata before the observed values were read, assuming a barycentrically coherent center. They are predicted coordinates, not measured peak locations.

| Observation (UTC) | Role | Predicted center offset (Å) | Fixed ±0.25 Å core |
|---|---|---:|---|
{chr(10).join(offset_rows)}

Four predicted centers lie outside the fixed core: January and March 2022, December 2022 and March 2023. The largest displacement is about **0.635715 Å**. The May 2022 discovery, May 2023 and July 2023 centers remain inside. Displaced comparisons may sample neighboring spectral structure in the anchor window. The 59.6098131157401 km/s BERV span supplies coordinate separation, not a calibrated origin discriminator. No alternate anchor or shifted comparison was tried. [All prospective coordinates and assumptions](../scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json).

## Valid references and retained signed samples

The **14 merged profiles and two native order 3 profiles** have complete 601-point raw and normalized support and positive valid flank references. Their **16 low-reference flags are false**. The two order 2 profiles have no valid reference and **low-reference flags are null**, not false. All **18 profiles have zero finite positive ERR samples**.

Merged reference levels range from **{min(r['flank_reference'] for r in merged):.3f} to {max(r['flank_reference'] for r in merged):.3f} ADU**. Their descriptive first-difference proxies range from **{min(r['first_difference_noise_proxy'] for r in merged):.3f} to {max(r['first_difference_noise_proxy'] for r in merged):.3f} ADU**. The low-reference rule is reference ≤ 3 × proxy only for a valid reference. It is not formal SNR, and the first-difference proxy is not a formal uncertainty estimate.

Three merged profile rows retain a nonpositive source sample:

| Observation (UTC) | Frame | Nonpositive source samples in window | Nonpositive source samples in left flank |
|---|---|---:|---:|
{chr(10).join(signed_rows)}

These three rows concern two observations; the July frame rows are not independent evidence. Their right-flank nonpositive fractions are zero. The other 11 merged profiles and both order 3 profiles have zero nonpositive window fractions. Signed values remain unchanged, and the valid pooled medians remain positive. No clipping, sign change or alternate reference was used.

## Both native orders, including order 2 limitations

Fresh checks of all **72 native order headers** identify orders 2 and 3 as covering the original center. They are two extractions from one discovery observation. Native BUNIT is absent, so their values retain **unspecified extracted units**, distinct from merged ADU. Same-exposure native/merged agreement is not independent confirmation or a physical flux ratio.

Order 2's positive endpoint is only **+1.160941197 Å barycentric / +1.161014356 Å topocentric** from the fixed center. Both frame profiles contain **417 of 601 raw grid samples**, including all **51 core samples** and only **366 of 550 surrounding samples**. The entire positive reference flank [1.5, 3] Å is absent. Its two raw-only reasons are exactly `MISSING_RIGHT_FLANK_COVERAGE`.

Order 2 has **165 finite original samples in the negative flank and zero in the positive flank**. The available one-sided median is **{order2[0]['available_flank_median']:.6f}**, with descriptive first-difference proxy **{order2[0]['first_difference_noise_proxy']:.6f}**, in unspecified native units in both frames. That available positive median is **not a valid two-flank reference**; `flank_reference` and the low flag remain null. The missing flank, not a measured nonpositive pooled reference, blocks normalization. The historical phrase about low-continuum order 2 context does not replace this current gate result.

In each order 2 frame window, **19 of 465 finite original source samples are nonpositive (4.0860%)**; in its available left flank, **3 of 165 are nonpositive (1.8182%)**. These original-sample counts differ from interpolated-grid support counts. All signed samples and their noisy variation remain visible. Adequate raw core support permits its core Pearson, while 366 surrounding samples fall below the fixed 440-sample minimum. Both surrounding Pearson values and all four order 2 normalized RMS values therefore remain unavailable.

Order 3 has complete 601-point support in both frames. Both reference levels are **{order3[0]['flank_reference']:.6f}**, and both first-difference proxies are **{order3[0]['first_difference_noise_proxy']:.6f}** in unspecified native units. Its nonpositive fractions are zero and both valid low flags are false.

| Native order | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
{chr(10).join(native_rows)}

[Both native order contexts](results/figures/NATIVE_ORDERS_1.png) retain the full signed order 2 profile and its abrupt coverage end. In its scaled panels, the grey merged spectrum remains visible while the native normalized curve is unavailable and explicitly annotated; it is not a zero-flux native curve. Order 3 follows the merged profile closely with small retained differences across the wider window. No missing order 2 flank or normalized value was filled from order 3.

## Earlier window overlap and structured flanks

The original C002 core [3868.3525, 3868.8525] Å **was already visible in C003's surrounding spectrum**, at offsets [−1.39875, −0.89875] Å from the C003 midpoint. It lies between C003's negative reference flank and original core, outside both masks. The full C002 window [3865.6025, 3871.6025] Å overlaps C003 over [3866.75125, 3871.6025] Å, a width of **4.85125 Å**. It overlaps C004 over [3869.245, 3871.6025] Å, a width of **2.3575 Å**, although the original C002 core lies outside C004's window.

C003's original core union [3869.495, 3870.0075] Å lies inside C002's surrounding region at offsets **+0.8925 to +1.405 Å**. It ends **0.095 Å before** the C002 positive reference flank; it is not inside that flank. Portions of both C002 reference flanks were already visible within C003's wider context. All neighboring structure remains unchanged. The fixed 1.5–3 Å pooled medians are reference levels, not established line-free continua. Positive scalar normalization leaves Pearson unchanged; scaled heights and RMS depend on those reference levels.

Original queue selection preceded C004 interpretation, but C002 flux was already seen in C003 and all seven observations are reused. These results are neither blind nor independent wavelength validation and add no observing time.

## Historical raw panels and mapping qualifications

[Both exact stored raw cutout/excess pairs](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png) retain the noisy order 2 central context and the full order 3 panel. **The order 3 full-value scale is dominated by a separate bright compact patch toward the lower right**, away from the nominal central context. Its central enhancement is subdued at that scale. This separation was already recorded by the historical secondary review as a separate off-event pixel retained for context; the primary/adopted short description concerns the smoother central enhancement. The bright remote patch is not newly assigned to the catalog feature, and no physical origin is assigned to it or to the central structure. The full scales and historical subtraction remain unchanged; no new pixel statistics, registration, background fitting or detector model was applied.

**Order 2 retains historical `local_mapping_usable=false` and `baseline_mapping_verified=false`**, alongside true global and later five-window diagnostics. Order 3's historical stages are true. The later supported mapping diagnostic does not erase the earlier local/baseline failures. Fresh wavelength coverage, core Pearson and order 3 agreement cannot retroactively validate order 2's raw-detector mapping. All primary, secondary and adopted reviews remain preserved in the [input inventory](../inputs/INPUT_INVENTORY.json).

The catalog fixed-template width is not a measured physical linewidth. Missing positive ERR support, reference diagnostics and morphology alone do not establish significance, false-alarm probability, sensitivity or a qualified survey null. The U label and all earlier pipelines remain unchanged.

## Reconstruction and delivery checks

The [independent arithmetic audit](../independent_audit/NUMERICAL_AUDIT.json) passes **{A['checks_passed']} checks across {A['scalar_values_compared']:,} scalar values**, covering all nine bounded source windows, 18 profiles, 36 comparisons, two raw copies and four self rows without importing production functions. Source flux, ERR, indices and profile metrics agree exactly. Wavelength differences are at most 4.55×10⁻¹³ Å, so wavelength arrays are not bitwise exact. Maximum raw interpolation difference is 3.00×10⁻⁹ native units, normalized-profile difference 1.91×10⁻¹¹ and comparison difference 2.82×10⁻¹⁴. The order 2 missing-flank cause and unavailable comparisons were independently reconstructed.

The exact method was public and read back before execution in commit `{release['publication_commit']}`. The [plan](PLAN.json), [release](ROOT_RELEASE.json), [run summary](results/SUMMARY.json), [bounded input index](results/BOUNDED_INPUT_INDEX.json), [complete profile metrics](results/PROFILE_METRICS.json), [complete comparisons](results/COMPARISONS.json) and [output hashes](results/OUTPUT_HASHES.json) bind the calculation.

All four figures were visually inspected, including the full core title and seven-epoch legend at original resolution, the order 2 raw-only annotation and the complete raw panels. PNG decoding, byte sizes and hashes match the unchanged [plot index](results/PLOT_INDEX.json). All **41 frozen method/input sources and 39 numerical output files** remain unchanged. [RESULTS_QA.json](RESULTS_QA.json) records these checks. The next original-queue group is C008; its distinct wavelength region still reuses the same observations and existing historical evidence.
'''
(HERE / 'RESULTS_REPORT.md').write_text(report)
print(f'Wrote C002 report: {len(report.encode())} bytes; every unavailable result retained.')
