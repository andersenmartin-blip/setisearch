#!/usr/bin/env python3
"""Write C010's actual descriptive report from immutable released output tables."""
from pathlib import Path
import datetime,json,statistics
HERE=Path(__file__).resolve().parent;OUT=HERE/'results'
read=lambda p:json.loads(p.read_text())
P=read(HERE/'PLAN.json');R=read(OUT/'PROFILE_METRICS.json');C=read(OUT/'COMPARISONS.json');S=read(OUT/'SUMMARY.json')
A=read(HERE.parent/'independent_audit/NUMERICAL_AUDIT.json');release=read(HERE/'ROOT_RELEASE.json')
science=read(HERE.parent/'scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json');nxt=read(HERE.parent/'scientific_review/NEXT_GROUP_METADATA.json')
assert A['status'].startswith('PASS') and len(R)==16 and len(C)==32
assert all(r['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE' and r['raw_grid_finite_samples']==601 and r['normalized_grid_finite_samples']==601 and r['low_flank_reference'] is False and r['positive_finite_ERR_samples']==0 and r['window_nonpositive_fraction']>0 for r in R)
assert all(r['raw_pearson'] is not None and r['normalized_rms'] is not None for r in C)
frames=['barycentric','topocentric'];fmt=lambda x:'Unavailable' if x is None else f'{x:.6f}';span=lambda a:fmt(min(a))+'–'+fmt(max(a))
dates={r['dp_id']:r['date_obs'][:10] for r in R};merged=[r for r in R if r['kind']=='merged'];native=[r for r in R if r['kind']=='native']
def pair(dp,frame,region,order=None):return next(r for r in C if r['dp_id']==dp and r['frame']==frame and r['region']==region and r['order']==order)
def bt(dp,region,key,order=None):return ' / '.join(fmt(pair(dp,f,region,order)[key]) for f in frames)
other=[dp for dp in P['merged_dp_ids'] if dp!=P['anchor_dp_id']]
epoch_rows=[]
for dp in other:
 fields=[bt(dp,z,k) for k in ['raw_pearson','normalized_rms'] for z in ['core','broad_pattern']]
 epoch_rows.append('| '+dates[dp]+' | '+' | '.join(fields)+' |')
 for z in ['core','broad_pattern']:
  assert pair(dp,'barycentric',z)['raw_pearson']>pair(dp,'topocentric',z)['raw_pearson']
  assert pair(dp,'barycentric',z)['normalized_rms']<pair(dp,'topocentric',z)['normalized_rms']
summary_rows=[]
for f in frames:
 for z in ['core','broad_pattern']:
  rows=[r for r in C if r['relationship']=='MERGED_EPOCH_TO_DISCOVERY' and not r['identical_product_self_pair'] and r['frame']==f and r['region']==z]
  summary_rows.append('| '+f+' | '+('Core' if z=='core' else 'Surroundings')+' | '+span([r['raw_pearson'] for r in rows])+' | '+fmt(statistics.median(r['raw_pearson'] for r in rows))+' | '+span([r['normalized_rms'] for r in rows])+' |')
locations=science['metadata_expected_feature_locations'];assert sum(not r['expected_center_inside_fixed_core'] for r in locations)==1
offset_rows=['| '+r['date_obs'][:10]+' | '+('Discovery' if r['dp_id']==P['anchor_dp_id'] else 'Other epoch')+f" | {r['expected_center_offset_from_fixed_anchor_angstrom']:+.9f} | "+('Inside' if r['expected_center_inside_fixed_core'] else 'Outside')+' |' for r in locations]
def metric(kind,dp,frame):return next(r for r in R if r['kind']==kind and r['dp_id']==dp and r['frame']==frame)
def count_ratio(r,side):
 n=r['window_native_finite_samples'] if side=='window' else r[side+'_flank_finite_samples']
 fraction=r['window_nonpositive_fraction'] if side=='window' else r[side+'_flank_nonpositive_fraction']
 return f'{round(fraction*n)}/{n}'
quality_rows=[]
for kind,dp in [('merged',d) for d in P['merged_dp_ids']]+[('native',P['anchor_dp_id'])]:
 label=('Merged '+dates[dp]) if kind=='merged' else 'Native order 1, '+dates[dp]
 vals=['; '.join(count_ratio(metric(kind,dp,f),side) for f in frames) for side in ['window','left','right']]
 quality_rows.append('| '+label+' | '+' | '.join(vals)+' |')
reference_rows=[]
for kind,label in [('merged','Merged (ADU)'),('native','Native order 1 (unspecified)')]:
 for frame in frames:
  r=metric(kind,P['anchor_dp_id'],frame)
  reference_rows.append('| '+label+' | '+frame+' | '+str(r['left_flank_finite_samples'])+' / '+str(r['right_flank_finite_samples'])+' | '+' | '.join(fmt(r[k]) for k in ['left_flank_median','right_flank_median','flank_reference','first_difference_noise_proxy'])+' |')
native_fields=[bt(P['anchor_dp_id'],z,k,1) for k in ['raw_pearson','normalized_rms'] for z in ['core','broad_pattern']]
completed=datetime.datetime.fromisoformat(S['completed_utc']).strftime('%Y-%m-%d at %H:%M:%S UTC')
diffs=A['maximum_absolute_differences_by_kind'];member=nxt['members'][0]
report=f'''# C010: HD112410 individual spectral context

**All six other HD112410 epochs align better with the fixed discovery profile in barycentric coordinates than in the fixed topocentric frame, in both the original core and surrounding window. V2E2-0086 remains U.** The central broad structure and its surrounding pattern are present with substantial shape, amplitude and reference-level differences. The comparison describes these saved spectra; it does not identify a line or physical origin, qualify a laser candidate, establish significance or calibrate a null result.

The released one-shot execution completed on **{completed}**: **16 profiles and 32 comparisons**, including four identical-product self rows, eight bounded source windows and one exact historical raw-panel copy. All statistics are evaluable. All profiles have full support and positive reference medians, while **every profile retains some nonpositive signed source samples**. The sole reference is the discovery observed on 2025-04-29. No new acquisition or observing time was added.

## Target-specific cohort and complete frame comparisons

This phase changes target to **HD112410** and uses its own seven observations from April–August 2025. The previous HD106515A products, reference, numeric anchor and BERV span are not transferred. The original catalog float **3823.0649999999996 Å** is retained in the code and plan; figures display 3823.065 Å for readability. The coordinate is a catalog input, not a measured physical linewidth or a claim of that many digits of wavelength accuracy.

Values separated by `/` below are barycentric/topocentric. Every row uses the one unchanged discovery reference and excludes the self rows.

| Other observation (UTC) | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
{chr(10).join(epoch_rows)}

| Frame | Region | Nonself raw r range | Median raw r | Nonself normalized RMS range |
|---|---|---:|---:|---:|
{chr(10).join(summary_rows)}

Barycentric r is higher and normalized RMS lower in **all six pairs in each region**. This is a descriptive contrast under the fixed method, not a calibrated origin discriminator. The spread remains important: **June 27 has the lowest barycentric core r, 0.596420**, while **May 28 has the largest barycentric RMS, 1.600996 in the core and 0.675335 in the surroundings**. May 30 is the highest-correlation barycentric comparison in both regions. No weaker epoch was removed. The four self rows remain at r≈1 and RMS=0 to floating-point precision and add no recurrence evidence.

- [All seven epochs: full signed and scaled context](results/figures/MERGED_BROAD_CONTEXT.png)
- [The same epochs: original core](results/figures/MERGED_CORE_CONTEXT.png)

The core figure retains the broad central rise, neighboring variation and different exposure levels. The discovery has the strongest raw central crest, while scaled peak heights vary substantially; May 28 appears especially jagged and high after division by its weaker reference level. The broad figure retains several repeated peaks and near-zero troughs, including structure within the reference flanks. Those surrounding features contribute to the broad statistic and are not a separate test of an isolated central emission line. The marker is the catalog/discovery coordinate rather than a fitted peak in every epoch. No fitted center, width, lag, stellar velocity, background, continuum, drift or selected frame shift was tried.

## Fixed geometry and the near-edge epochs

The April 2025 discovery BERV **3.40485846065643 km/s** gives the wavelength-specific topocentric-air anchor **3823.0215804708346 Å**. The fixed ±3 Å context has 601 grid centers at 0.01 Å spacing, with 51 in the original ±0.25 Å core and 550 outside that core. Minimum common support remains 41/440. HD112410's own BERV span is **21.30284860830273 km/s**.

These positions were calculated from metadata before the observed values were read, assuming a barycentrically coherent catalog center. They are predicted coordinates rather than fitted peak positions.

| Observation (UTC) | Role | Predicted offset from fixed anchor (Å) | Original ±0.25 Å core |
|---|---|---:|---|
{chr(10).join(offset_rows)}

**Only August 7 has its predicted center outside the fixed topocentric core**, at +0.271674988 Å: just **0.021674988 Å beyond** the positive edge. July 9 remains inside at +0.237728523 Å, only **0.012271477 Å inside** that edge. This center flag does not say that a whole finite-width feature is inside or outside; the fixed window can retain portions of an extended structure. No boundary was changed. The other epochs remain inside. Frame displacement and the BERV span provide geometry, not calibrated physical-origin evidence. [Prospective coordinates and caveats](../scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json).

## Signed samples, positive references and uncertainty limits

All **16 profiles have 601 finite raw and normalized grid values**, positive valid two-flank references and false low-reference flags. All 32 Pearson and 32 normalized RMS values use complete 51-point core or 550-point surrounding support. No missing-coverage or gap mask is present. Every profile has **zero positive finite ERR samples**.

Positive pooled references do not make every signed source sample positive. **All 16 profiles contain nonpositive source samples**, which remain unchanged. The table retains original-source counts, distinct from interpolated grid counts. Each cell lists **barycentric; topocentric** counts as nonpositive/finite source samples. Frame rows for the same exposure are dependent.

| Source / observation (UTC) | Window nonpositive B; T | Left flank nonpositive B; T | Right flank nonpositive B; T |
|---|---:|---:|---:|
{chr(10).join(quality_rows)}

Merged window fractions range from **2/600 (0.3333%) to 21/600 (3.5%)**. The maximum is May 28 in both frames. Native order 1 retains **3/562 (0.5338%)** in each frame window and **3/139 (2.1583%)** in its left flank. Some left-flank counts change between frames because their fixed source masks differ. Every signed value is preserved without clipping, sign changes or a moved reference region.

Merged pooled references span **{min(r['flank_reference'] for r in merged):.6f}–{max(r['flank_reference'] for r in merged):.6f} ADU**, with descriptive first-difference proxies **{min(r['first_difference_noise_proxy'] for r in merged):.6f}–{max(r['first_difference_noise_proxy'] for r in merged):.6f} ADU**. May 28 has the weakest barycentric reference, **59.985079 ADU**, with proxy **16.266478 ADU**; the fixed low-reference test is still false. That flag is not a general quality certificate or formal SNR. Different reference levels affect scaled peak heights and RMS; they do not supply a calibrated emission strength.

The discovery reference values are:

| Product and units | Frame | Finite flank samples L/R | Left-flank median | Right-flank median | Pooled reference | First-difference proxy |
|---|---|---:|---:|---:|---:|---:|
{chr(10).join(reference_rows)}

The flanks are structured, with near-zero troughs visible in both sides of the broad context. All fixed native samples in those flanks remain in the pooled medians. These are descriptive reference levels rather than established line-free continua or fitted baselines. Positive scalar division leaves Pearson unchanged, while scaled heights and normalized RMS depend on the chosen fixed levels. Native BUNIT is absent, so native extracted units remain unspecified and distinct from merged ADU. Missing positive ERR and descriptive first-difference proxies provide no formal uncertainty model, false-alarm probability, sensitivity estimate or qualified survey null.

## Native extraction and historical raw mapping limits

Fresh checks of all 72 native orders identify **order 1 alone** covering the center, with complete contexts and both flanks in each frame. Its same-exposure native/merged comparisons are:

| Native order | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 1 | {' | '.join(native_fields)} |

[Native order 1](results/figures/NATIVE_ORDERS_1.png) retains the broad central structure and neighboring peaks/troughs, following the merged shape closely with small scaled differences. Native and merged extractions share one observation and pipeline lineage. This is dependent evidence, not a second detection, physical flux ratio or validation of the raw-detector registration.

[The complete historical raw cutout and excess map](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png) show a central vertical band and bright diffuse patch, with positive and negative residual lobes. Weaker right-edge structure remains present. The central context and weaker edge structure remain on the same complete saved scales. All saved pixels, the historical subtraction and separate complete scales are retained. No new crop, contrast variant, pixel statistic, registration, subtraction, background or detector model was applied.

**Original local mapping and baseline verification remain false for order 1**, alongside true global-grid and later five-window diagnostics. The later supported reference window does not retroactively repair those original limits. Fresh wavelength coverage and native/merged similarity do not establish new raw mapping or physical origin. Historical primary, secondary and adopted reviews all remain **U**, describing broad diffuse trace-confined structure without an unambiguous compact charge deposit. The displayed patch does not change those adopted reviews or qualify a laser candidate.

## Dependence, verification and continuation

This target-specific window is disjoint from the completed C001–C009 bounded windows. Original HD112410 epoch/profile and raw evidence already existed for 0086, and its own seven observations are reused. The distinct target/cohort therefore adds no observing time or archive-wide completeness and is not blind, untouched or independent new observing evidence. All original classifications and completed outputs remain unchanged.

The [independent arithmetic audit](../independent_audit/NUMERICAL_AUDIT.json) passes **{A['checks_passed']} checks across {A['scalar_values_compared']:,} scalar values**, reconstructing all eight source windows, 16 profiles, 32 comparisons, one exact raw copy and four self rows without importing production functions. Source flux, ERR, indices and profile metrics agree exactly. Maximum wavelength difference is **{diffs['input_source_wavelength']:.3e} Å**, so wavelength arrays are not bitwise exact. Maximum raw interpolation difference is **{diffs['profile_signed_raw_flux']:.3e} native units**, normalized difference **{diffs['profile_normalized_flux']:.3e}** and comparison difference **{diffs['comparison']:.3e}**. Computational agreement does not establish physical origin.

The method was public and read back before execution in commit `{release['publication_commit']}`. [Plan](PLAN.json), [root release](ROOT_RELEASE.json), [summary](results/SUMMARY.json), [bounded inputs](results/BOUNDED_INPUT_INDEX.json), [all profile metrics](results/PROFILE_METRICS.csv), [all comparisons](results/COMPARISONS.csv) and [numerical hashes](results/OUTPUT_HASHES.json) bind the run.

All four figures were visually inspected and fully decoded with their hashes/sizes checked against [PLOT_INDEX.json](results/PLOT_INDEX.json). All **{len(P['source_hashes'])} frozen source bindings and {len(read(OUT/'OUTPUT_HASHES.json'))} numerical output files** remain unchanged. [RESULTS_QA.json](RESULTS_QA.json) records those checks. The next original-queue item is **{nxt['next_core_group']} / {member['candidate_id']} on {member['target']} at {member['center_bary_air_angstrom']} Å**, row {member['queue_index']} / {member['resolution_group']}. It precedes C011 by queue order and reuses the same target cohort/discovery; a new wavelength-specific anchor and fresh covering-order checks are required. [Next fixed-queue metadata](../scientific_review/NEXT_GROUP_METADATA.json) preserves those dependencies. No C012 analysis was executed here.
'''
(HERE/'RESULTS_REPORT.md').write_text(report)
print(f'Wrote C010 report: {len(report.encode())} bytes.')
