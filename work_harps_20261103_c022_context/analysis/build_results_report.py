#!/usr/bin/env python3
"""Render released C022 results with all references and staged custody retained."""
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
assert A['status'].startswith('PASS') and len(R) == 20 and len(C) == 96
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
assert N['next_core_group'] == 'C017' and len(N['members']) == 1
complete = datetime.datetime.fromisoformat(S['completed_utc']).strftime('%Y-%m-%d at %H:%M:%S UTC')
D = A['maximum_absolute_differences_by_kind']
jan1 = P['events']['V2E2-0117']
jan2 = P['events']['V2E2-0131']
jc = pair(jan1, jan2, 'topocentric', 'core')['raw_pearson']
jb = pair(jan1, jan2, 'topocentric', 'broad_pattern')['raw_pearson']
native_links = '- [All three native order-19 contexts](results/figures/NATIVE_ORDERS_1.png)'
raw_links = '- [All three original raw/excess pairs](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png)'
sharedrows = ['| ' + r['kind'] + ' ' + dates[r['dp_id']] + ' | ' + str(r['shared_source_samples']) + ' |' for r in A['prior_C021_shared_source_index_records']]
report = f'''# C022: HD114783 joint spectral context

**Each of the three fixed discovery references has higher barycentric raw correlation and lower barycentric normalized RMS against all six other epochs, in both the common core and surrounding window. All three current C022 codes remain U.** The rounded central crest, neighboring structure and broader multi-peak spectrum align closely in barycentric coordinates, with amplitude/reference differences retained. This descriptive agreement does not assign physical origin, qualify a laser candidate, estimate significance or calibrate a null result.

The single released execution completed on **{complete}**: **20 profiles and 96 comparisons**, including **12 identical-product self rows**, ten bounded source windows and three byte-exact original raw-panel copies. All 96 Pearson and 96 RMS values are evaluable. Every profile has full support, a valid positive reference and false low-reference flag. There are zero raw-only, blocked or structurally excluded slots. No observing time was added.

## Three references over seven existing observations

References are **0117/0127/0131**, observed **January 21 2022, May 5 2022 and January 16 2023**. All seven existing January 2022–July 2023 HD114783 epochs remain included. **February 5 2022 and March 22, May 15 and July 1 2023 are cohort nonreferences.** There are 84 merged comparisons (7×3×2 frames×2 regions) and 12 native comparisons (3 sources×2×2), native only to their own same-exposure merged products.

**Eighteen directed nonself rows per frame/region represent 15 unordered exposure pairs and three reciprocal reference-pair duplicates**, over seven observations rather than 18 independent epochs. Every reference retains all six other epochs; source/reference and same-exposure flags remain explicit. All 12 identical-product self rows remain at r≈1 and RMS=0 and add no recurrence evidence. Values separated by `/` below are **barycentric/topocentric**.

{(chr(10) * 2).join(families)}

Per-reference barycentric ranges across all six other epochs are:

| Reference | Common-core raw r range | Surrounding raw r range | Common-core RMS range | Surrounding RMS range |
|---|---:|---:|---:|---:|
{chr(10).join(ranges)}

All six comparisons in each family favor barycentric r and RMS in both regions. **January 21 2022 ↔ January 16 2023 retains strong topocentric correlation: {jc:.6f} core / {jb:.6f} surroundings**, consistent with close BERVs; barycentric agreement remains stronger. Other topocentric comparisons include positive and negative correlations. No reference or epoch is selected for a favorable outcome, and frame agreement is not a calibrated origin test.

- [All seven epochs: complete broad context](results/figures/MERGED_BROAD_CONTEXT.png)
- [The same epochs: fixed common core](results/figures/MERGED_CORE_CONTEXT.png)

The core retains a rounded crest across multiple grid samples, smaller neighboring structure on both sides and retained small crest/sampling differences. The broad view includes repeated peaks/troughs and a high structured region on the positive side. The barycentric scaled profiles lie close together; the fixed topocentric core samples displaced and neighboring structure. Same y-scales across frames retain all finite values and reference-dependent heights. No peak center, width, lag, stellar velocity, drift, continuum, background or mask was fitted. The broader structured spectrum is not reduced to an isolated central emission line.

## Exact common core and all three original markers

The fixed midpoint is **4312.241249999999 Å** barycentric air, from the exact original catalog extrema. The common ±3 Å window is **[4309.241249999999,4315.241249999999] Å** and common ±0.25 Å metric core **[4311.991249999999,4312.491249999999] Å**. The 0.01 Å grid retains **601 centers: 51 common-core and 550 surrounding**, with unchanged support gates **41/440**.

The common core **is not the union of original member cores**. An original edge extends approximately **0.00375 Å outside one common edge**. Preserve exact centers **4312.245** and **4312.237499999999**, every original ±0.25 core and all three marker identities, including the coincident 0117/0127 barycentric markers. These are computational/catalog inputs rather than accuracy or physical-linewidth claims. Displayed intervals below are rounded to six decimals; the plan retains exact bounds.

| Member | Exact original center (Å) | Original member core, displayed (Å) | Barycentric marker offset (Å) | Own discovery topocentric marker offset (Å) |
|---|---:|---|---:|---:|
{chr(10).join(markers)}

First-queue 0117, observed January 21 2022 at BERV **29.658729150824 km/s**, fixes the single common **4311.814678415948 Å** topocentric-air anchor through `group_midpoint/(1+BERV/c)`. Each marker separately uses its exact original center and own discovery BERV. The coordinate anchor does not select a preferred reference or follow a fitted peak.

The own-target BERV span is **59.073251754930496 km/s**. These common-midpoint positions were computed before current values under a barycentric-coherence assumption; they are metadata predictions rather than measured peak positions.

| Observation | Cohort role | Predicted common-midpoint offset (Å) | Fixed common ±0.25 Å core |
|---|---|---:|---|
{chr(10).join(locrows)}

**Four of seven predicted centers are outside the fixed topocentric core on the positive side**: May 5 2022, March 22, May 15 and July 1 2023; the largest offset is **+0.844675834 Å**. Three centers remain inside. **Only one of the three original discovery markers is outside: May 5 2022**. Distinguish seven center predictions from three member markers. Center flags do not prove whole finite-width feature coverage; fixed windows are never recentered and neighboring structure can enter the core. BERV span supplies geometry rather than calibrated origin discrimination. [Prospective geometry](../scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json).

## Actual support, signed samples and reference quality

All **20 profiles have 601 finite raw and normalized grid values**, valid positive pooled two-flank references and **20 false low-reference flags**. All 96 comparisons retain complete 51-point core or 550-point surrounding support. There are zero gaps/outside-coverage masks and **zero positive finite ERR samples in every profile**. Original window, left-flank and right-flank nonpositive fractions are **zero in all 20 rows**. Signed values remain unchanged, without clipping or sign flips. No quality outcome is transferred from a preceding phase.

The unchanged reference rule uses the pooled signed median of original samples at offsets 1.5–3 Å, requiring at least 20 finite samples separately on each side and a strictly positive pooled median. The first-difference proxy uses the fixed MAD rule. A low flag would be true at reference≤3×proxy and null for invalid normalization; none occurred here. A false flag is not formal SNR, uncertainty or a general quality certificate. Structured spectral features remain in both flanks without masks, moved boundaries or fitted alternatives.

Each cell below retains **barycentric/topocentric** values; `L,R` counts finite original flank samples. Original source counts differ from 601-point interpolation support. Merged quantities use ADU. Native BUNIT is absent in all three products, so native extracted units remain unspecified.

| Source / observation | Finite original window B/T | Finite flanks L,R B/T | Pooled reference B/T | First-difference proxy B/T |
|---|---:|---|---:|---:|
{chr(10).join(quality)}

Merged windows have 600 finite original samples and 150 per flank. Native windows retain **512–515** finite original samples, **126–127** left-flank and **130–131** right-flank samples, with complete interpolation support in every case. Fixed-frame levels and proxies differ with sampled structure. For May 5 the merged pooled reference is **2439.827759 / 2583.656006** and native reference **2876.943237 / 3044.512451**. Such reference differences remain in normalized heights and RMS; positive scalar division leaves raw Pearson unchanged. These levels are descriptive structured references, not established line-free continua. Missing ERR and these proxies do not establish formal significance, sensitivity, false-alarm probability, linewidth or a qualified survey null.

## All native order-19 sources and original raw panels

Fresh scans of **216 order headers** select **only order 19** in every discovery; both fixed frames have complete context/core/flank geometry in all six native contexts. Each native source compares only with its own same-exposure merged extraction:

| Native event/order | Common-core raw r B/T | Surrounding raw r B/T | Common-core RMS B/T | Surrounding RMS B/T |
|---|---:|---:|---:|---:|
{chr(10).join(native)}

{native_links}

All three native rows remain on one page. Multi-peak native/merged shapes agree closely but retain scaled differences, particularly the **January 16 2023 surrounding RMS 0.065480 / 0.065662**, despite raw r **0.999324 / 0.999302**. Its native reference **4256.796875 / 4258.820801** remains distinct from merged **3528.156250 / 3528.156250**; these are separate extracted-unit systems and structured reference levels, not a physical flux ratio. Pearson and scaled mismatch describe different properties. Shared exposure/extraction lineage makes this dependent similarity rather than another observation or physical-origin confirmation.

{raw_links}

All three byte-exact original raw/excess pairs retain every saved pixel, full index extents and separate full scales on one page. The batch03 **0117/0127 panels contain diffuse central enhancements/vertical bands together with dominant periodic right-edge structure**, so central patches are faint at full scale. **0131 retains its original 21×25 five-array container**, distinct from the two batch03 **31×33** panels and its completed later wider container. Its extended central positive patch/vertical trace and **negative excess above the central patch** remain visible. Do not transfer prior 0130's lower-side excess pattern. These views do not isolate compact detector charge morphology or assign origin; remote edge structure does not classify the central feature. No new crop, contrast variant, registration, subtraction, background model, pixel statistic or enhancement variant was introduced.

Historical stages remain separate:

| Member | Original global grid | Original local | Original baseline | Later reference support |
|---|---|---|---|---|
{chr(10).join(mapping)}

**All three original local/baseline stages are false; all global and later support stages are true.** Batch03 uses explicit `baseline_mapping_verified`, while older 0131 preserves its original `mapping_verified` basis. Source-specific coordinates/pixels are unchanged, and later support does not retroactively repair original failures.

The two batch03 original review chains remain **U/U/U**. **0131 originally has primary I, secondary M normalized to I, and adopted baseline I; completed wider support and separate later reviews retain U/U/current U.** Preserve those stages rather than flattening originals to blanket U or transferring 0130/0129 histories. Its exact smaller original panel is not replaced by the completed wider diagnosis. Mapping support, spectral reference quality, raw morphology and physical origin remain separate; all three current codes remain U. [Original custody and completed follow-up](../inputs/INPUT_INVENTORY.json).

## Direct reuse of C021 pixels and independent arithmetic verification

**C022 and C021 directly share source spectral pixels over [4309.241249999999,4312.82625] Å**, width **3.585000000000946 Å**, from the same seven observing products and three reused native products. **The complete C022 core lies inside C021's positive reference flank [4311.32625,4312.82625] Å. Conversely, the complete C021 core [4309.57625,4310.07625] Å lies inside C022's negative reference flank [4309.241249999999,4310.741249999999] Å.** Their cores are disjoint but structured-flank evidence is shared. The C022 core was already exposed in C021's broad view. There is no untouched, blind or independent-data validation claim and no new mask or line-free assumption.

The independent audit confirms same full source hashes and intersections of saved source-index ranges for **all ten current inputs**:

| Reused source / observation | Shared original source indices, count |
|---|---:|
{chr(10).join(sharedrows)}

These counts describe each phase's saved **both-frame union window plus interpolation brackets**, not a new pixel test or a claim that every count equals the nominal fixed-frame wavelength overlap. The auditor used the prior C021 inventory/index metadata; **no prior C021 arrays were opened and no C021 method was rerun**. Original raw crops retain separate custody without inferred equality or independence. C018/C019 bounded blue windows are spectrally disjoint but share observations/native lineage; numeric C006/C007 overlaps belong to a different target and share no source pixels. No new observing time or archive-wide completeness follows.

The [independent actual arithmetic audit](../independent_audit/NUMERICAL_AUDIT.json) passes **{A['checks_passed']} checks across {A['scalar_values_compared']:,} scalar values**, reconstructing all ten source windows, 20 profiles, 96 comparisons, three byte-identical original raw copies and 12 self rows without importing production functions. Source flux, ERR, indices and profile metrics agree exactly. Maximum source-wavelength difference is **{D['input_source_wavelength']:.3e} Å**, raw interpolation difference **{D['profile_signed_raw_flux']:.3e} native units**, normalized difference **{D['profile_normalized_flux']:.3e}**, and comparison difference **{D['comparison']:.3e}**. Wavelength/interpolation results are not bitwise identical; arithmetic agreement does not establish origin.

The method was public and exactly read back before execution at commit `{release['publication_commit']}`. [Plan](PLAN.json), [root release](ROOT_RELEASE.json), [summary](results/SUMMARY.json), [bounded inputs](results/BOUNDED_INPUT_INDEX.json), [profile metrics](results/PROFILE_METRICS.csv), [comparisons](results/COMPARISONS.csv) and [numeric hashes](results/OUTPUT_HASHES.json) bind the run. **All four figures were visually inspected and fully decoded**; hashes/sizes, one native page, one raw page and complete source ordering are checked against [PLOT_INDEX.json](results/PLOT_INDEX.json). All **88 source bindings and 43 numerical files** remain unchanged. [RESULTS_QA.json](RESULTS_QA.json) records delivery checks. All prior classifications/results and completed mapping/normalization diagnoses remain immutable and are not replayed.

## Next original-queue action

The next unfinished route, selected **before C022 values**, is **C017 / R018, INDIVIDUAL_PROFILE_CONTEXT on HD114783**, restoring the singleton design:

| Queue row | Record | Fixed discovery product | Exact catalog center (Å) | Current code |
|---|---|---|---:|---|
{chr(10).join(nextrows)}

Use the exact original **3868.175 Å** center and ±0.25 core, one February 5 2022 discovery reference, BERV **26.6810328154809 km/s**, and own anchor **3867.830769460069 Å**. Six other epochs imply **six directed nonself / six unordered / zero reciprocal duplicates per frame/region**; do not transfer the current midpoint, January anchor or three-reference accounting. Fresh all-order headers must determine actual native scope/geometry and all quality outcomes remain to be measured.

Its original order-2 global/later stages are true and local/baseline false; original order 3 is all true. Original reviews are **U/U/U**, without separate 0131 I/M→I stages. Preserve source-specific mapping and do not replay completed support diagnostics. Historical orders 2/3 are clues for fresh selection, not a transferred scope or missing-flank conclusion.

C017 reuses **4.8412500000004 Å** of same-observation spectral pixels with completed C018, over **[3866.33375,3871.175] Å**. Both distinct cores lie in the other's surrounding context, but **neither intersects the other's fixed reference flanks**. Its core was already exposed; this is not untouched or independent evidence. C019/C021/C022 bounded spectral windows are disjoint while observations/native lineage remain shared; other-target numeric overlaps share no source pixels. Complete original raw crops retain separate custody. [Next metadata and histories](../scientific_review/NEXT_GROUP_METADATA.json) retain these dependencies. Completed 0092/0104 normalization routes stay complete and are skipped. **No C017 array analysis or completed-diagnostic replay was executed here.**
'''
(HERE / 'RESULTS_REPORT.md').write_text(report)
print('Wrote C022 report:', len(report.encode()), 'bytes')
