#!/usr/bin/env python3
"""Write C009's descriptive report from unchanged released tables."""
from pathlib import Path
import datetime,json,statistics
HERE=Path(__file__).resolve().parent;OUT=HERE/'results'
read=lambda p:json.loads(p.read_text())
P=read(HERE/'PLAN.json');R=read(OUT/'PROFILE_METRICS.json');C=read(OUT/'COMPARISONS.json');S=read(OUT/'SUMMARY.json')
A=read(HERE.parent/'independent_audit/NUMERICAL_AUDIT.json');release=read(HERE/'ROOT_RELEASE.json')
science=read(HERE.parent/'scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json')
next_step=read(HERE.parent/'scientific_review/NEXT_GROUP_METADATA.json')
assert len(R)==16 and len(C)==32 and sum(r['identical_product_self_pair'] for r in C)==4
assert A['status'].startswith('PASS')
assert all(r['status']=='MEASURED_CONTEXT' and r['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE' and r['raw_grid_finite_samples']==601 and r['normalized_grid_finite_samples']==601 and r['low_flank_reference'] is False and r['positive_finite_ERR_samples']==0 and r['window_nonpositive_fraction']==0 and r['left_flank_nonpositive_fraction']==0 and r['right_flank_nonpositive_fraction']==0 for r in R)
assert all(r['raw_pearson'] is not None and r['normalized_rms'] is not None for r in C)
frames=['barycentric','topocentric'];fmt=lambda x:'Unavailable' if x is None else f'{x:.6f}'
span=lambda a:fmt(min(a))+'–'+fmt(max(a))
dates={r['dp_id']:r['date_obs'][:10] for r in R};merged=[r for r in R if r['kind']=='merged'];native=[r for r in R if r['kind']=='native']
assert len(merged)==14 and len(native)==2 and all(r['order']==70 for r in native)
def pair(dp,frame,region,order=None):return next(r for r in C if r['dp_id']==dp and r['frame']==frame and r['region']==region and r['order']==order)
def bt(dp,region,key,order=None):return ' / '.join(fmt(pair(dp,f,region,order)[key]) for f in frames)
other=[dp for dp in P['merged_dp_ids'] if dp!=P['anchor_dp_id']]
epoch_rows=[]
for dp in other:
 fields=[bt(dp,region,key) for key in ['raw_pearson','normalized_rms'] for region in ['core','broad_pattern']]
 epoch_rows.append('| '+dates[dp]+' | '+' | '.join(fields)+' |')
 assert pair(dp,'barycentric','core')['raw_pearson']<0
 assert pair(dp,'topocentric','core')['raw_pearson']>pair(dp,'barycentric','core')['raw_pearson']
 for key in ['raw_pearson','normalized_rms']:
  b=pair(dp,'barycentric','broad_pattern')[key];t=pair(dp,'topocentric','broad_pattern')[key]
  assert b>t if key=='raw_pearson' else b<t
assert [dates[dp] for dp in other if pair(dp,'topocentric','core')['normalized_rms']<pair(dp,'barycentric','core')['normalized_rms']]==['2022-01-05','2022-03-07','2022-05-07','2022-12-31']
nonself=[r for r in C if r['relationship']=='MERGED_EPOCH_TO_DISCOVERY' and not r['identical_product_self_pair']]
summary_rows=[]
for frame in frames:
 for region in ['core','broad_pattern']:
  rows=[r for r in nonself if r['frame']==frame and r['region']==region]
  summary_rows.append('| '+frame+' | '+('Core' if region=='core' else 'Surroundings')+' | '+span([r['raw_pearson'] for r in rows])+' | '+fmt(statistics.median(r['raw_pearson'] for r in rows))+' | '+span([r['normalized_rms'] for r in rows])+' |')
offset_rows=[]
for r in science['metadata_expected_feature_locations']:
 offset_rows.append(f"| {r['date_obs'][:10]} | "+('Discovery' if r['dp_id']==P['anchor_dp_id'] else 'Other epoch')+f" | {r['expected_center_offset_from_fixed_anchor_angstrom']:+.9f} | "+('Inside' if r['expected_center_inside_fixed_core'] else 'Outside')+' |')
assert sum(not r['expected_center_inside_fixed_core'] for r in science['metadata_expected_feature_locations'])==5
reference_rows=[]
for kind,label in [('merged','Merged (ADU)'),('native','Native order 70 (unspecified)')]:
 for frame in frames:
  r=next(r for r in R if r['kind']==kind and r['dp_id']==P['anchor_dp_id'] and r['frame']==frame)
  keys=['left_flank_median','right_flank_median','flank_reference','first_difference_noise_proxy']
  reference_rows.append('| '+label+' | '+frame+' | '+str(r['left_flank_finite_samples'])+' / '+str(r['right_flank_finite_samples'])+' | '+' | '.join(fmt(r[k]) for k in keys)+' |')
native_fields=[bt(P['anchor_dp_id'],region,key,70) for key in ['raw_pearson','normalized_rms'] for region in ['core','broad_pattern']]
completed=datetime.datetime.fromisoformat(S['completed_utc']).strftime('%Y-%m-%d at %H:%M:%S UTC')
diffs=A['maximum_absolute_differences_by_kind']
source_count=len(P['source_hashes']);output_count=len(read(OUT/'OUTPUT_HASHES.json'))
report=f'''# C009: HD106515A individual spectral context

**The discovery core does not show same-shape barycentric recurrence in the six other epochs, while its surrounding spectrum does recur. V2E2-0050 remains U.** All six nonself barycentric core Pearson values are negative. The discovery observation retains a local multi-sample excess near the catalog center, whereas the other barycentric core profiles show different, often depressed structure there. This descriptive difference does not establish physical origin, a calibrated nondetection, a qualified laser candidate or a survey null.

The released one-shot execution completed on **{completed}**: **16 profiles and 32 comparisons**, including four identical-product self rows, eight bounded source windows and one exact historical raw-panel copy. All profiles and statistics are numerically evaluable. No profile is raw-only, blocked or structurally excluded. The sole fixed reference is the March 2023 discovery, observed on 2023-03-22. No new acquisition or observing time was added.

## Core and surroundings retain different outcomes

The center is **6802.02 Å** in barycentric air wavelengths. Values separated by `/` are barycentric/topocentric. Each row is one other epoch against the same discovery reference, retaining all six outcomes.

| Other observation (UTC) | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
{chr(10).join(epoch_rows)}

| Frame | Region | Nonself raw r range | Median raw r | Nonself normalized RMS range |
|---|---|---:|---:|---:|
{chr(10).join(summary_rows)}

All six **barycentric core correlations are negative**, and the corresponding topocentric core r is higher in all six cases. Normalized core RMS is lower topocentrically for January, March and May 2022 and December 2022; it is lower barycentrically only for May and July 2023. These two descriptors are retained separately. There is no claim of a coherent topocentric feature, since the fixed window can sample neighboring structure and the core correlations remain mixed.

By contrast, the **surrounding pattern favors barycentric coordinates in all six pairs by both r and normalized RMS**. This comparison includes recurring troughs near approximately −1 Å and +2.4/+2.7 Å and other spectral structure. It does not validate recurrence of the distinct central excess. No surrounding statistic is substituted for a core result. The four self rows remain at r≈1 and RMS=0 to floating-point precision; they add no independent evidence.

- [All seven epochs: full signed and scaled context](results/figures/MERGED_BROAD_CONTEXT.png)
- [The same epochs: original core](results/figures/MERGED_CORE_CONTEXT.png)

The discovery's scaled core rises locally near the catalog marker; the other barycentric profiles do not reproduce that same shape. The full raw view retains the different exposure flux levels, and the scaled view retains the fixed signed reference division. The marker is the original catalog/discovery coordinate, not a fitted peak. No alternate window, recentering, fitted center, width, lag, stellar velocity, continuum, background or drift was introduced. Neither the visual difference nor the negative correlations supply an event probability, a detection threshold or a quantitative limit on recurrence.

## Fixed frame geometry

The March 2023 discovery BERV **3.26509772194068 km/s** defines the wavelength-specific topocentric-air anchor **6801.945918689643 Å**. The fixed ±3 Å window has 601 centers on a 0.01 Å grid, including 51 in the original ±0.25 Å core and 550 in the surroundings. Common-support minima remain 41/440.

The positions below were calculated from metadata before these values were read, assuming a barycentrically coherent catalog center. They are coordinate predictions, not measured peak locations.

| Observation (UTC) | Role | Predicted offset from fixed anchor (Å) | Original ±0.25 Å core |
|---|---|---:|---|
{chr(10).join(offset_rows)}

Five predicted centers lie outside the fixed topocentric core. Only March 2022 and the March 2023 discovery lie inside. The topocentric window remains fixed, so other comparisons can concern neighboring structure instead of the original catalog feature. The 59.6098131157401 km/s BERV span supplies coordinate separation rather than a calibrated origin discriminator. [Prospective coordinates and caveats](../scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json).

## Signed reference levels and uncertainty limits

All **16 profiles have 601 finite raw and normalized samples**, valid positive two-flank references and false low-reference flags. All source-window and separate-flank nonpositive fractions are zero; signed values were retained without clipping. Every profile has **zero positive finite ERR samples**. All comparisons use their complete 51-point core or 550-point surrounding masks.

Merged reference levels span **{min(r['flank_reference'] for r in merged):.3f}–{max(r['flank_reference'] for r in merged):.3f} ADU**, with descriptive first-difference proxies **{min(r['first_difference_noise_proxy'] for r in merged):.3f}–{max(r['first_difference_noise_proxy'] for r in merged):.3f} ADU**. The reference ≤ 3 × proxy rule is descriptive, not formal SNR. The discovery values are retained separately in each frame:

| Product and units | Frame | Finite flank samples L/R | Left-flank median | Right-flank median | Pooled reference | First-difference proxy |
|---|---|---:|---:|---:|---:|---:|
{chr(10).join(reference_rows)}

The discovery center coincides between frames, but ±3 Å and the flank boundaries are defined separately in each frame. Their barycentric widths differ by the fixed BERV factor. The merged discovery therefore has 151 samples per flank barycentrically and 150 per flank topocentrically, with the small reference/proxy differences preserved above; no equality was imposed. Native reference samples remain the same in both frames. Both complete fixed reference flanks remain included. The deep positive-offset troughs fall in the positive reference interval [1.5,3] Å. The pooled medians are descriptive reference levels, not established line-free continua or fitted backgrounds. The plotted normalized excess and RMS depend on these chosen fixed levels. Positive scalar division leaves Pearson unchanged. No emission-line equivalent width, calibrated amplitude or physical linewidth was measured. Native BUNIT is absent, so extracted native values retain unspecified units distinct from merged ADU.

## Native extraction and full preserved raw context

Fresh checks of all 72 native orders identify **order 70 alone** as covering the original center; both complete windows and flanks are retained. The discovery native/merged comparisons are:

| Native order | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 70 | {' | '.join(native_fields)} |

[Native order 70](results/figures/NATIVE_ORDERS_1.png) retains the discovery local excess and surrounding troughs, following its same-exposure merged extraction closely with visible scaled differences preserved. Shared extraction lineage makes this dependent evidence; an event present in both extractions is not a second observation or a physical-origin validation.

[The complete historical raw cutout and excess map](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png) retain separate full scales. Bright structures at the far right and lower-right edge dominate those scales, while the nominal central band and residual are much fainter. The historical compact slanted concentration review concerns the enlarged central context and coexists with broader residual structure; it does not describe the complete panel's scale. All original pixels and the historical subtraction are preserved. No new spatial model, registration, subtraction, pixel statistic or origin assignment was applied to either the central or edge structures.

**Preserve the historical primary A / secondary A / root-adopted U distinction.** Both reviewers provisionally voted A after describing a compact slanted concentration in order 70. The secondary retained broader residual structure and could not exclude an underlying spectral contribution. Root adopted **U** because a possible artifact/spectral blend remained unresolved. The current adopted code is U; neither the earlier votes, the central non-recurrence nor the surrounding recurrence replaces that adoption or qualifies a laser candidate.

The historical global, local, baseline and later five-window mapping stages are all true. They remain distinct existing diagnostics, not a new mapping test or an origin classification. All primary, secondary and adopted texts, current dispositions and prior outputs are unchanged.

## Dependence, verification and continuation

The C009 window [6799.02,6805.02] Å is disjoint from completed C001–C008 bounded wavelength windows. Original epoch/profile and raw evidence already existed for this record, and all seven observing products are reused. Distinct wavelength context does not make the evidence blind, untouched or independent and adds no observing time or archive-wide completeness. Missing ERR and uncalibrated morphology provide no formal significance, false-alarm probability, sensitivity estimate or qualified survey null.

The [independent arithmetic audit](../independent_audit/NUMERICAL_AUDIT.json) passes **{A['checks_passed']} checks across {A['scalar_values_compared']:,} scalar values** without importing production functions, covering all eight source windows, 16 profiles, 32 comparisons, one exact raw copy and four self rows. Source flux, ERR, indices and profile metrics agree exactly. Maximum wavelength difference is **{diffs['input_source_wavelength']:.3e} Å**; wavelength arrays are not bitwise exact. Maximum raw interpolation difference is **{diffs['profile_signed_raw_flux']:.3e} native units**, normalized difference **{diffs['profile_normalized_flux']:.3e}** and comparison difference **{diffs['comparison']:.3e}**. Computational agreement does not establish physical origin.

The method was public and read back before execution in commit `{release['publication_commit']}`. [Plan](PLAN.json), [root release](ROOT_RELEASE.json), [summary](results/SUMMARY.json), [bounded inputs](results/BOUNDED_INPUT_INDEX.json), [all profile metrics](results/PROFILE_METRICS.csv), [all comparisons](results/COMPARISONS.csv) and [numerical hashes](results/OUTPUT_HASHES.json) bind the run.

All four figures were visually inspected and fully decoded with sizes and hashes checked against [PLOT_INDEX.json](results/PLOT_INDEX.json). All **{source_count} frozen method/input source bindings and {output_count} numerical output files** remain unchanged. [RESULTS_QA.json](RESULTS_QA.json) records delivery checks. The next original-queue item is **C010 / V2E2-0086 on HD112410 at 3823.065 Å**, row 23, selected before C009 values. Its seven existing 2025 epochs and April 2025 discovery reference belong to a different target; no HD106515A products or numerical anchor are transferred. [Next fixed-queue metadata](../scientific_review/NEXT_GROUP_METADATA.json) preserves those identities and historical mapping limits. No C010 analysis was executed here.
'''
(HERE/'RESULTS_REPORT.md').write_text(report)
print(f'Wrote C009 report: {len(report.encode())} bytes.')
