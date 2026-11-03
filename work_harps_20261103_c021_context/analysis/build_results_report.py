#!/usr/bin/env python3
"""Render released C021 results with all references and staged custody retained."""
from pathlib import Path
import datetime
import json

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
N = read(HERE.parent / 'scientific_review/NEXT_GROUP_METADATA.json')
assert A['status'].startswith('PASS') and len(R) == 24 and len(C) == 160
assert all(r['normalization_status'] == 'USABLE_POSITIVE_FLANK_REFERENCE'
           and not r['normalization_reasons'] and r['flank_reference'] > 0
           and r['low_flank_reference'] is False
           and r['raw_grid_finite_samples'] == r['normalized_grid_finite_samples'] == 601
           and r['positive_finite_ERR_samples'] == 0
           and r['window_nonpositive_fraction'] == r['left_flank_nonpositive_fraction']
           == r['right_flank_nonpositive_fraction'] == 0
           and r['outside_native_coverage_grid_samples'] == r['gap_masked_grid_samples'] == 0
           for r in R)
assert all(r['raw_pearson'] is not None and r['normalized_rms'] is not None for r in C)
frames = ['barycentric', 'topocentric']
fmt = lambda x: 'Unavailable' if x is None else f'{x:.6f}'
span = lambda a: fmt(min(a)) + '–' + fmt(max(a))
dates = {r['dp_id']: r['date_obs'][:10] for r in R}


def pair(dp, ref, frame, region, order=None):
    return next(r for r in C if r['dp_id'] == dp and r['reference_dp_id'] == ref
                and r['frame'] == frame and r['region'] == region and r['order'] == order)


def bt(dp, ref, region, key, order=None):
    return ' / '.join(fmt(pair(dp, ref, f, region, order)[key]) for f in frames)


def met(kind, dp, frame, order=None):
    return next(r for r in R if r['kind'] == kind and r['dp_id'] == dp
                and r['frame'] == frame and r['order'] == order)


families = []
ranges = []
for event, ref in P['events'].items():
    others = [d for d in P['merged_dp_ids'] if d != ref]
    rows = []
    for dp in others:
        rows.append('| ' + dates[dp] + ' | ' + ' | '.join(
            bt(dp, ref, z, k) for k in ['raw_pearson', 'normalized_rms']
            for z in ['core', 'broad_pattern']) + ' |')
        for z in ['core', 'broad_pattern']:
            assert pair(dp, ref, 'barycentric', z)['raw_pearson'] > pair(dp, ref, 'topocentric', z)['raw_pearson']
            assert pair(dp, ref, 'barycentric', z)['normalized_rms'] < pair(dp, ref, 'topocentric', z)['normalized_rms']
    families.append('### ' + event + ' reference: ' + dates[ref] + '\n\n'
                    '| Other observation | Common-core raw r B/T | Surrounding raw r B/T | Common-core RMS B/T | Surrounding RMS B/T |\n'
                    '|---|---:|---:|---:|---:|\n' + '\n'.join(rows))
    ranges.append('| ' + event + ' | ' + ' | '.join(span([
        pair(dp, ref, 'barycentric', z)[k] for dp in others])
        for k in ['raw_pearson', 'normalized_rms'] for z in ['core', 'broad_pattern']) + ' |')

markers = []
for m in P['event_markers']:
    core = P['individual_event_cores_bary_air_angstrom'][m['event']]
    markers.append('| ' + m['event'] + ' | ' + str(m['center_bary_air_angstrom'])
                   + f" | [{core[0]:.6f}, {core[1]:.6f}] | {m['barycentric_offset_angstrom']:+.9f} | {m['discovery_topocentric_offset_angstrom']:+.9f} |")
locations = science['metadata_expected_feature_locations']
locrows = ['| ' + r['date_obs'][:10] + ' | '
           + ('Reference' if r['dp_id'] in P['discovery_dp_ids'] else 'Cohort only')
           + f" | {r['expected_center_offset_from_fixed_anchor_angstrom']:+.9f} | "
           + ('Inside' if r['expected_center_inside_fixed_core'] else 'Outside') + ' |'
           for r in locations]
assert sum(not r['expected_center_inside_fixed_core'] for r in locations) == 4
quality = []
for kind, dp, order in ([('merged', d, None) for d in P['merged_dp_ids']]
                        + [('native', d, 19) for d in P['discovery_dp_ids']]):
    a, b = [met(kind, dp, f, order) for f in frames]
    label = ('Merged ' if kind == 'merged' else 'Native 19 ') + dates[dp]
    quality.append('| ' + label
                   + f" | {a['window_native_finite_samples']} / {b['window_native_finite_samples']}"
                   + f" | {a['left_flank_finite_samples']},{a['right_flank_finite_samples']} / {b['left_flank_finite_samples']},{b['right_flank_finite_samples']}"
                   + ' | ' + fmt(a['flank_reference']) + ' / ' + fmt(b['flank_reference'])
                   + ' | ' + fmt(a['first_difference_noise_proxy']) + ' / ' + fmt(b['first_difference_noise_proxy']) + ' |')
native = ['| ' + event + ' / 19 | ' + ' | '.join(
    bt(dp, dp, z, k, 19) for k in ['raw_pearson', 'normalized_rms']
    for z in ['core', 'broad_pattern']) + ' |' for event, dp in P['events'].items()]
mapping = []
for r in P['historical_mapping_stages']:
    mapping.append('| ' + r['event'] + ' | ' + ' | '.join(
        str(r[k]).lower() for k in ['original_grid_mapping_usable', 'original_local_mapping_usable',
                                   'original_baseline_mapping_verified', 'final_reference_mapping_supported']) + ' |')
nextrows = ['| ' + str(m['queue_index']) + ' | ' + m['candidate_id'] + ' | '
            + m['discovery_dp_id'] + ' | ' + str(m['center_bary_air_angstrom'])
            + ' | ' + m['current_code'] + ' |' for m in N['members']]
assert N['next_core_group'] == 'C022' and len(N['members']) == 3
complete = datetime.datetime.fromisoformat(S['completed_utc']).strftime('%Y-%m-%d at %H:%M:%S UTC')
D = A['maximum_absolute_differences_by_kind']
jan1 = P['events']['V2E2-0116']
jan2 = P['events']['V2E2-0130']
jc = pair(jan1, jan2, 'topocentric', 'core')['raw_pearson']
jb = pair(jan1, jan2, 'topocentric', 'broad_pattern')['raw_pearson']
native_links = '\n'.join(f'- [Native page {i}: {label}](results/figures/NATIVE_ORDERS_{i}.png)'
                         for i, label in [(1, '0116/0121/0126/0130'), (2, '0139')])
raw_links = '\n'.join(f'- [Original raw page {i}: {label}](results/figures/PRESERVED_RAW_ORDER_CONTEXT_{i}.png)'
                      for i, label in [(1, '0116/0121/0126/0130'), (2, '0139')])
report = f'''# C021: HD114783 joint spectral context

**All five fixed discovery references have higher barycentric raw correlation and lower barycentric normalized RMS against all six other epochs, in both the common core and surrounding window. All five current C021 codes remain U.** The rounded central crest and wider multi-peak spectrum align closely in barycentric coordinates, with retained amplitude and reference-level differences. These descriptive comparisons do not identify a line or physical origin, qualify a laser candidate, estimate significance or calibrate a null result.

The single released execution completed on **{complete}**: **24 profiles and 160 comparisons**, including **20 identical-product self rows**, 12 bounded source windows and five byte-exact original raw-panel copies. All 160 Pearson and 160 RMS values are evaluable. Every profile has full support, a valid positive reference and false low-reference flag. There are zero raw-only, blocked or structurally excluded slots. No observing time was added.

## Five references and seven observations

Retain the same seven existing HD114783 January 2022–July 2023 epochs. References are **0116/0121/0126/0130/0139**, observed January 21 2022, February 5 2022, May 5 2022, January 16 2023 and **July 1 2023**. July replaces C019's May 15 reference; **March 22 and May 15 2023 remain cohort nonreferences**. There are 140 merged comparisons (7×5×2 frames×2 regions) and 20 native comparisons (5 sources×2×2), native only to their own same-exposure merged products.

**Thirty directed nonself rows per frame/region represent 20 unordered exposure pairs and 10 reciprocal reference-pair duplicates**, over seven observations rather than 30 independent epochs. Every reference retains six other epochs, with source/reference identities and dependency flags explicit. All 20 self rows remain at r≈1 and RMS=0 and add no recurrence evidence. No favorable reference is selected. Values separated by `/` below are **barycentric/topocentric**.

{(chr(10) * 2).join(families)}

Per-reference barycentric ranges across all six other epochs are:

| Reference | Common-core raw r range | Surrounding raw r range | Common-core RMS range | Surrounding RMS range |
|---|---:|---:|---:|---:|
{chr(10).join(ranges)}

All six comparisons in every family favor barycentric r and RMS in both regions. **January 21 2022 ↔ January 16 2023 retains strong topocentric correlation: {jc:.6f} core / {jb:.6f} surroundings**, consistent with close BERVs; barycentric agreement remains stronger. Other topocentric results include positive and negative correlations. Frame agreement here is dependent descriptive evidence under fixed windows, not a calibrated origin test.

- [All seven epochs: complete broad context](results/figures/MERGED_BROAD_CONTEXT.png)
- [The same epochs: fixed common core](results/figures/MERGED_CORE_CONTEXT.png)

The core retains a multi-sample rounded crest near the catalog centers, a positive-side trough and neighboring structure. The broad view retains repeated peaks and troughs throughout both structured reference flanks. Normalization brings the barycentric profiles close together while preserving smaller differences. The fixed topocentric view samples shifted central and neighboring structure; no center, width, lag, stellar velocity, drift, continuum or background was fitted. Same y-scales across frames retain all finite values and reference-dependent heights. No isolated narrow-line interpretation follows from these views.

## Exact common geometry and all member markers

The fixed midpoint is **4309.82625 Å** barycentric air; the common ±3 Å window is **[4306.82625,4312.82625] Å** and common ±0.25 Å core **[4309.57625,4310.07625] Å**. The 0.01 Å grid has **601 centers: 51 common-core and 550 surrounding**, with unchanged support gates **41/440**.

The common core **is not the union of original member cores**: extrema original cores extend approximately **0.00125 Å outside one common edge**. Preserve exact catalog floats **4309.827499999999** and **4309.825**, original cores and all five identities, including coincident markers. These computational inputs are not accuracy claims; displayed intervals below are rounded to six decimals while the plan retains exact bounds.

| Member | Exact original center (Å) | Original member core, displayed (Å) | Barycentric marker offset (Å) | Own discovery topocentric marker offset (Å) |
|---|---:|---|---:|---:|
{chr(10).join(markers)}

First-queue 0116, observed January 21 2022 at BERV **29.658729150824 km/s**, fixes the common **4309.39991731037 Å** topocentric-air anchor through `group_midpoint/(1+BERV/c)`. Each marker separately uses its exact original center and own discovery BERV. The coordinate-anchor rule does not select a comparison reference or fit a peak.

The own-target BERV span is **59.073251754930496 km/s**. The following common-midpoint coordinates were computed before observed values, assuming barycentric coherence; they are predictions rather than measured peak positions.

| Observation | Cohort role | Predicted common-midpoint offset (Å) | Fixed common ±0.25 Å core |
|---|---|---:|---|
{chr(10).join(locrows)}

**Four of seven predicted centers are outside the fixed topocentric core on the positive side**: May 5 2022, March 22 2023, May 15 2023 and July 1 2023. The largest offset is **+0.844202787 Å**. Three centers remain inside. **Only two of the five discovery markers are outside: May 5 2022 and July 1 2023**; March/May 2023 are cohort predictions without discovery markers. Center flags do not establish whole finite-width feature coverage. No window is recentered, and neighboring structure can enter the fixed core. BERV span supplies geometry, not calibrated origin discrimination. [Prospective geometry](../scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json).

## Complete support and actual reference quality

All **24 profiles have 601 finite raw and normalized grid values**, valid positive pooled two-flank medians and **24 false low-reference flags**. All 160 comparisons retain full 51-point core or 550-point surrounding support. There are zero gaps or outside-coverage masks. Every profile has **zero positive finite ERR samples**. All original window, left-flank and right-flank nonpositive fractions are **zero in all 24 rows**; no clipping or sign changes were applied. No earlier phase's signed-sample or quality outcome is transferred.

The fixed reference is the pooled median of signed original source values at offsets 1.5–3 Å, requiring at least 20 finite samples separately on each side and a positive pooled result. The first-difference proxy uses the fixed MAD rule; a low flag would be true at reference≤3×proxy and null for invalid normalization. No such invalid/low outcome occurred here. A false low flag is not formal SNR, uncertainty or a general quality certificate. All spectral structure remains in the flanks without masks, moved boundaries or fitted replacements.

Each cell below retains **barycentric/topocentric** values; `L,R` counts finite original flank samples. Original sample counts are distinct from 601-point interpolation support. Merged quantities use ADU. Native BUNIT is absent in all five products, so native extracted units remain unspecified.

| Source / observation | Finite original window B/T | Finite flanks L,R B/T | Pooled reference B/T | First-difference proxy B/T |
|---|---:|---|---:|---:|
{chr(10).join(quality)}

All merged windows have 600 finite original samples and 150 on each flank. Native windows contain **504–507 finite original samples**, left flanks **124–125** and right flanks **128**, while every interpolated grid remains complete. Fixed-frame levels and proxies differ with sampled structure. For July 1 the merged reference is **1467.759888 / 1757.341003** and native reference **1714.203125 / 2066.693604**; those differences remain in the scaled profiles and RMS. Positive scalar division leaves raw Pearson unchanged. References are descriptive spectral levels rather than established line-free continua. No formal significance, sensitivity, false-alarm probability, physical linewidth or qualified survey null follows from missing ERR or these proxies.

## Fresh order 19 contexts

Fresh scans of **360 headers** select **only order 19** in every discovery, with complete context/core/flank geometry in all ten source/frame combinations. No C019 orders 3/4 scope or earlier quality is inherited. Each native source compares only with its own same-exposure merged product:

| Native event/order | Common-core raw r B/T | Surrounding raw r B/T | Common-core RMS B/T | Surrounding RMS B/T |
|---|---:|---:|---:|---:|
{chr(10).join(native)}

{native_links}

All five native contexts remain in two pages, with four rows then one. The native/merged multi-peak profiles agree closely, with finite sampling/reference differences retained: across all ten frame contexts the core r is at least **0.999889** and surrounding r at least **0.999297**. Scaled RMS remains nonzero. Native/merged similarities share the same exposure and extraction lineage; they are not new observations, independent physical confirmation or calibrated flux ratios. No instrumental or astrophysical cause is assigned.

## Original raw panels and separate historical stages

{raw_links}

All five exact original raw/excess pairs retain every saved pixel, full original index extents and separate full scales, in pages of four then one. The four batch03 panels show a diffuse central enhancement/vertical band together with **strong periodic right-edge structure that dominates their full scales**, especially 0139. The central patches can consequently look faint. The smaller original 0130 panel retains a stronger extended central patch/vertical trace and lower-side negative excess structure. These are descriptive views, with no compact charge-track or physical-origin assignment. Edge deposits do not classify the central feature. There is no new crop, contrast variant, registration, subtraction, background model, detector statistic or enhancement variant.

**0130 retains its exact original 21×25 five-array container**, distinct from the four batch03 **31×33** panels and from its completed later wider container. The original smaller panel is not replaced by that later diagnosis.

Historical mapping stages remain source-specific:

| Member | Original global grid | Original local | Original baseline | Later reference support |
|---|---|---|---|---|
{chr(10).join(mapping)}

Thus original local/baseline stages are **false for 0116/0126/0130** and **true for 0121/0139**, while all global and later stages are true. Batch03 baseline flags use their explicit `baseline_mapping_verified` field; 0130 preserves its original `mapping_verified` basis. Later support at unchanged coordinates does not rewrite original failures.

Four batch03 original primary/secondary/adopted chains remain **U/U/U**. **0130 originally has primary I, secondary M normalized to I, and adopted baseline I; completed wider support and separate later reviews retain U/U/current U at unchanged coordinates and pixels.** Preserve these stages rather than flattening all original reviews to U, transferring C019/0129's absent/null later fields, or rerunning a completed mapping diagnosis. All five current codes remain U. Mapping support, spectral reference quality, raw morphology and physical origin remain distinct. [Exact review/mapping custody](../inputs/INPUT_INVENTORY.json).

## Verification, dependence and continuation

C021 reuses seven observations and some native products from C018/C019, with disjoint bounded blue spectral windows. Original epoch/raw evidence already existed. Spectral disjointness does not establish independence of observations or whole raw crops. C016 belongs to another target and ends **0.03875 Å** below this context; other-target C006/C007 numeric overlap shares no source pixels. No blind, untouched, independent-observation or archive-wide completeness claim follows. All prior outputs, classifications and completed mapping/normalization diagnoses remain immutable and are not replayed.

The [independent actual arithmetic audit](../independent_audit/NUMERICAL_AUDIT.json) passes **{A['checks_passed']} checks across {A['scalar_values_compared']:,} scalar values**, reconstructing all 12 source windows, 24 profiles, 160 comparisons, five byte-identical raw copies and 20 self rows without importing production functions. Source flux, ERR, indices and profile metrics agree exactly. Maximum source-wavelength difference is **{D['input_source_wavelength']:.3e} Å**, raw interpolation difference **{D['profile_signed_raw_flux']:.3e} native units**, normalized difference **{D['profile_normalized_flux']:.3e}**, and comparison difference **{D['comparison']:.3e}**. Wavelength/interpolation results are not bitwise identical; arithmetic agreement does not establish physical origin.

The method was public and exactly read back before execution at commit `{release['publication_commit']}`. [Plan](PLAN.json), [root release](ROOT_RELEASE.json), [summary](results/SUMMARY.json), [bounded inputs](results/BOUNDED_INPUT_INDEX.json), [profile metrics](results/PROFILE_METRICS.csv), [comparisons](results/COMPARISONS.csv) and [numeric hashes](results/OUTPUT_HASHES.json) bind the run. **All six figures were visually inspected and fully decoded**, with hashes, sizes, two native/two raw pages and source ordering checked against [PLOT_INDEX.json](results/PLOT_INDEX.json). All **92 source bindings and 51 numerical files** remain unchanged. [RESULTS_QA.json](RESULTS_QA.json) records delivery checks.

The next unfinished original-queue route, fixed **before current values**, is **C022 / R023, JOINT_PROFILE_CONTEXT on HD114783**, with all three original members:

| Queue row | Record | Fixed discovery product | Exact catalog center (Å) | Current code |
|---|---|---|---:|---|
{chr(10).join(nextrows)}

C022 proposes midpoint **4312.241249999999 Å** and first-January anchor **4311.814678415948 Å**, retaining exact individual cores and all three references. Its three references over the same seven observations imply **18 directed nonself rows / 15 unordered pairs / 3 reciprocal duplicates per frame/region**. Fresh headers and separately frozen runtime quality are required; no present reference level or outcome is transferred.

**C021 and future C022 directly reuse spectral pixels over 3.585000000000946 Å**, from **[4309.241249999999,4312.82625] Å**. The **entire future C022 core [4311.991249999999,4312.491249999999] Å lies inside the current positive reference flank [4311.32625,4312.82625] Å**. Conversely, the **entire current C021 core [4309.57625,4310.07625] Å lies inside C022's future negative reference flank [4309.241249999999,4310.741249999999] Å**. Original cores are disjoint, but their structured-flank evidence is explicitly shared. The future core is already exposed in current broad context; it is not untouched or independent validation. Fixed structured flanks retain such features without new masks or line-free claims. Complete historical raw crops retain separate custody without assumed equality or independence.

Future 0117/0127 retain original U/U/U. **0131 separately retains original I/M-normalized-I/baseline-I, completed unchanged-coordinate wider support, then later U/U/current U**, with original local/baseline false and later support true. Do not transfer current mixed mapping or distinct 0130/0129 histories. Completed mapping and 0092/0104 normalization routes remain complete and are skipped. [Next metadata and staged histories](../scientific_review/NEXT_GROUP_METADATA.json) retain the dependencies. **No C022 array analysis or completed-diagnostic replay was executed here.**
'''
(HERE / 'RESULTS_REPORT.md').write_text(report)
print('Wrote C021 report:', len(report.encode()), 'bytes')
