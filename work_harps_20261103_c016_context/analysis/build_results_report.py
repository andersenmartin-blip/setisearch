#!/usr/bin/env python3
"""Render all four fixed C016 reference families from immutable output tables."""
from pathlib import Path
import datetime,itertools,json,statistics
HERE=Path(__file__).resolve().parent;OUT=HERE/'results';read=lambda p:json.loads(p.read_text())
P=read(HERE/'PLAN.json');R=read(OUT/'PROFILE_METRICS.json');C=read(OUT/'COMPARISONS.json');S=read(OUT/'SUMMARY.json')
A=read(HERE.parent/'independent_audit/NUMERICAL_AUDIT.json');release=read(HERE/'ROOT_RELEASE.json')
science=read(HERE.parent/'scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json');nxt=read(HERE.parent/'scientific_review/NEXT_GROUP_METADATA.json')
assert A['status'].startswith('PASS') and len(R)==22 and len(C)==128
assert all(r['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE' and not r['normalization_reasons'] and r['flank_reference']>0 and r['raw_grid_finite_samples']==601 and r['normalized_grid_finite_samples']==601 and r['positive_finite_ERR_samples']==0 and r['gap_masked_grid_samples']==0 and r['outside_native_coverage_grid_samples']==0 and r['low_flank_reference']is False and r['window_nonpositive_fraction']==0 and r['left_flank_nonpositive_fraction']==0 and r['right_flank_nonpositive_fraction']==0 for r in R)
assert all(r['raw_pearson']is not None and r['normalized_rms']is not None for r in C)
frames=['barycentric','topocentric'];fmt=lambda x:'Unavailable' if x is None else f'{x:.6f}';span=lambda a:fmt(min(a))+'–'+fmt(max(a))
dates={r['dp_id']:r['date_obs'][:10] for r in R};merged=[r for r in R if r['kind']=='merged'];native=[r for r in R if r['kind']=='native']
def pair(dp,ref,f,z,o=None):return next(r for r in C if r['dp_id']==dp and r['reference_dp_id']==ref and r['frame']==f and r['region']==z and r['order']==o)
def bt(dp,ref,z,k,o=None):return ' / '.join(fmt(pair(dp,ref,f,z,o)[k]) for f in frames)
def metric(kind,dp,f,o=None):return next(r for r in R if r['kind']==kind and r['dp_id']==dp and r['frame']==f and r['order']==o)
families=[];summary_rows=[]
for event,ref in P['events'].items():
 rows=[];other=[dp for dp in P['merged_dp_ids'] if dp!=ref]
 for dp in other:
  rows.append('| '+dates[dp]+' | '+' | '.join(bt(dp,ref,z,k) for k in ['raw_pearson','normalized_rms'] for z in ['core','broad_pattern'])+' |')
  for z in ['core','broad_pattern']:
   assert pair(dp,ref,'barycentric',z)['raw_pearson']>pair(dp,ref,'topocentric',z)['raw_pearson']
   assert pair(dp,ref,'barycentric',z)['normalized_rms']<pair(dp,ref,'topocentric',z)['normalized_rms']
 families.append('### '+event+' reference: '+dates[ref]+'\n\n| Other observation (UTC) | Common-core raw r B/T | Surrounding raw r B/T | Common-core normalized RMS B/T | Surrounding normalized RMS B/T |\n|---|---:|---:|---:|---:|\n'+'\n'.join(rows))
 def vals(z,k):return [pair(dp,ref,'barycentric',z)[k] for dp in other]
 summary_rows.append('| '+event+' | '+' | '.join(span(vals(z,k)) for k in ['raw_pearson','normalized_rms'] for z in ['core','broad_pattern'])+' |')
markers=P['event_markers'];marker_rows=[]
for m in markers:
 core=P['individual_event_cores_bary_air_angstrom'][m['event']]
 marker_rows.append('| '+m['event']+' | '+str(m['center_bary_air_angstrom'])+' | '+f'[{core[0]:.6f}, {core[1]:.6f}]'+f" | {m['barycentric_offset_angstrom']:+.9f} | {m['discovery_topocentric_offset_angstrom']:+.9f} |")
locations=science['metadata_expected_feature_locations'];assert sum(not r['expected_center_inside_fixed_core'] for r in locations)==4
offset_rows=['| '+r['date_obs'][:10]+f" | {r['expected_center_offset_from_fixed_anchor_angstrom']:+.9f} | "+('Inside' if r['expected_center_inside_fixed_core'] else 'Outside')+' |' for r in locations]
quality_rows=[]
for kind,dp,o in [('merged',d,None) for d in P['merged_dp_ids']]+[('native',d,19) for d in P['discovery_dp_ids']]:
 label=('Merged '+dates[dp]) if kind=='merged' else 'Native 19 '+dates[dp]
 n=' / '.join(str(metric(kind,dp,f,o)['window_native_finite_samples']) for f in frames)
 flanks=' / '.join(str(metric(kind,dp,f,o)['left_flank_finite_samples'])+','+str(metric(kind,dp,f,o)['right_flank_finite_samples']) for f in frames)
 refs=' / '.join(fmt(metric(kind,dp,f,o)['flank_reference']) for f in frames)
 noise=' / '.join(fmt(metric(kind,dp,f,o)['first_difference_noise_proxy']) for f in frames)
 quality_rows.append('| '+label+' | '+n+' | '+flanks+' | '+refs+' | '+noise+' |')
native_rows=[]
for event,dp in P['events'].items():native_rows.append('| '+event+' / '+dates[dp]+' | '+' | '.join(bt(dp,dp,z,k,19) for k in ['raw_pearson','normalized_rms'] for z in ['core','broad_pattern'])+' |')
completed=datetime.datetime.fromisoformat(S['completed_utc']).strftime('%Y-%m-%d at %H:%M:%S UTC');diffs=A['maximum_absolute_differences_by_kind'];member=nxt['members'][0]
report=f'''# C016: HD114386 joint spectral context

**For each of the four fixed discovery references, all six other HD114386 epochs agree better in barycentric coordinates than in the fixed topocentric frame, in both the common group core and surrounding window. V2E2-0094/0096/0098/0110 all remain U.** The central rounded structure, nearby secondary rise and wider pattern recur with retained amplitude and shape differences. These descriptive comparisons do not identify a line or physical origin, qualify a laser candidate, estimate significance or calibrate a null result.

The single released execution completed on **{completed}**: **22 profiles and 128 comparisons**, including **16 identical-product self rows**, 11 bounded source windows and four byte-exact historical raw-panel copies. All 128 Pearson and 128 normalized RMS values are evaluable. Every profile has complete support, valid positive references and a false low-reference flag; there are zero raw-only, blocked or structurally excluded slots. No new acquisition or observing time was added.

## Four fixed reference families over seven observations

The new target is **HD114386**, with its own seven existing January 2022–August 2023 observations. All four discovery products remain references: March 7 2022 (0094), May 16 2022 (0096), January 2 2023 (0098) and August 27 2023 (0110). HD112410 products, anchor and quality outcomes were not transferred.

The merged accounting is **7 epochs × 4 references × 2 frames × 2 regions = 112 rows**, including 16 self rows. Native accounting adds **4 discovery/order-19 sources × 2 frames × 2 regions = 16 rows**, compared only with their own same-exposure merged products. Each reference has six nonself epochs per frame/region. The resulting **24 ordered nonself rows per frame/region reuse seven observations; they are not 24 independent epochs**. Six unordered discovery pairs appear in both directions. Across each frame/region, the 24 rows represent 18 unordered exposure pairs, with six reciprocal duplicates. No favorable reference or epoch is selected.

Values separated by `/` in every comparison table are **barycentric/topocentric**. Self rows remain in the complete output at r≈1 and RMS=0 and add no recurrence evidence.

{chr(10).join(families)}

Across each reference's six other epochs, the barycentric ranges are:

| Reference | Common-core raw r range | Surrounding raw r range | Common-core normalized RMS range | Surrounding normalized RMS range |
|---|---:|---:|---:|---:|
{chr(10).join(summary_rows)}

All six comparisons in every reference family have higher barycentric r and lower barycentric RMS in both regions. This agreement is descriptive under the fixed method and dependent across repeated pairs; it is not a calibrated origin test. **August 27 2023 has the lowest barycentric common-core r and largest common-core RMS within each of the other three reference families**; when August itself is the reference, all six other epochs are similarly separated from it. Its lower raw level and retained scaled differences remain visible rather than being omitted.

The topocentric results are not uniformly weak or negative. **January 6 2022 ↔ January 2 2023** retains topocentric r **0.971275 in the common core and 0.986978 in the surroundings**, consistent with their close BERVs. Their barycentric values are still higher. July 1 ↔ August 27 2023 retains topocentric r **0.810019 / 0.799336** in core/surroundings. These close-coordinate cases remain in the tables; no alternative anchor was tried.

- [All seven epochs: full signed and scaled context](results/figures/MERGED_BROAD_CONTEXT.png)
- [The same epochs: fixed common group core](results/figures/MERGED_CORE_CONTEXT.png)

The common-core figure retains a rounded multi-sample central crest and a secondary rise near +0.2 Å. Scaled shapes mostly coincide, while August has a higher scaled crest and visible differences. The broad figure retains numerous repeated peaks and troughs throughout both reference flanks. Surrounding correlation therefore describes a structured pattern rather than an isolated central emission line. All four reference IDs and catalog/discovery markers remain labeled, including three coincident barycentric markers. No center, width, lag, stellar velocity, drift, continuum, background or selected frame shift was fitted.

## Common midpoint, original member cores and four markers

The fixed common midpoint is **4303.7875 Å** barycentric air, derived from the minimum/maximum exact catalog centers rather than fitted peaks. The common ±3 Å context is **[4300.7875,4306.7875] Å**, and the common ±0.25 Å comparison core is **[4303.5375,4304.0375] Å**. The 0.01 Å grid has 601 centers: **51 common-core and 550 surrounding centers**, with unchanged common-support gates **41/440**.

The common core **is not the union of the original member cores**. The three 4303.785-centered original cores extend 0.0025 Å below its lower edge, while 0110's 4303.79-centered original core extends 0.0025 Å above its upper edge. Exact original coordinates and markers remain distinct:

| Member | Catalog center (Å) | Original member core (Å) | Barycentric marker offset (Å) | Own discovery topocentric marker offset (Å) |
|---|---:|---|---:|---:|
{chr(10).join(marker_rows)}

The fixed group coordinate anchor is **4303.512448784194 Å** topocentric air, from the **first original-queue discovery, March 7 2022**, BERV **19.1606928163471 km/s**, through `group_center/(1+BERV/c)`. This coordinate rule does not remove the other three comparison references. Exact event markers use each member's own center and discovery BERV, rather than replacing those coordinates with the common midpoint or a fitted peak. Markers outside the common core remain in the broad view, legends and metadata. The common-core result is not described as covering every complete original member core or measuring a physical linewidth.

The own-target BERV span is **51.572001697156 km/s**. The following group-midpoint coordinates were calculated from metadata before new observed values were read, assuming a barycentrically coherent midpoint; they are predicted coordinates rather than measured peaks.

| Observation (UTC) | Predicted common-midpoint offset from fixed anchor (Å) | Fixed common ±0.25 Å core |
|---|---:|---|
{chr(10).join(offset_rows)}

**Four predicted group centers are outside the fixed topocentric common core**: May 16 2022, April 29 2023, July 1 2023 and August 27 2023. The largest displacement is +0.631359099 Å. January 2022, March 2022 and January 2023 remain inside. Center flags do not establish coverage of an entire finite-width feature. The fixed window can sample neighboring structure and is never recentered. BERV displacement supplies coordinate geometry rather than calibrated physical-origin discrimination. [Prospective geometry and assumptions](../scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json).

## Signed samples, positive references and error limits

All **22 profiles contain 601 finite raw and normalized grid values**, valid positive two-flank reference medians and **22 false low-reference flags**. All comparisons have complete 51-point common-core or 550-point surrounding support, with zero gap/outside-coverage masks. **Every original finite source sample in each fixed window and both flanks is strictly positive**; all window/flank nonpositive fractions are zero. This is the measured signed outcome, not clipping or a sign change. All profiles have **zero positive finite ERR samples**.

Original source counts differ from the 601-point interpolated grid. Merged windows contain 600 finite source samples with 150 per flank; native counts depend on source/frame masks. The table retains barycentric/topocentric values separately. `L,R` gives finite original flank counts. Merged levels/proxies are ADU; native extracted units are unspecified because all four native BUNIT headers are absent.

| Source / observation | Finite source window B/T | Finite flanks L,R B/T | Pooled reference B/T | First-difference proxy B/T |
|---|---:|---|---:|---:|
{chr(10).join(quality_rows)}

Native source-window counts span **485–488**, while all native profiles retain 601 finite grid values. These are distinct source sampling and interpolation counts, not missing profile slots. The first-difference proxy and `reference ≤ 3×proxy` low rule are descriptive rather than formal SNR; false flags are not general quality certificates. No C011 true-low outcome was transferred.

The fixed flanks contain substantial spectral peaks and troughs. Every source sample remains in the pooled medians without masks, moved flanks or fitted replacements. They are descriptive reference levels rather than established line-free continua. Positive scalar division leaves Pearson unchanged; normalized heights and RMS depend on those levels. ERR support and proxies do not establish formal uncertainty, false-alarm probability, sensitivity or a qualified survey null.

## Four native discoveries and complete historical raw panels

Fresh scans of **all 72 headers in each of four native products (288 rows)** identify **order 19 alone** covering each exact event coordinate. Each selected order fully covers the common context/core and both flanks in both frames. Their same-exposure native-to-merged comparisons are:

| Native discovery/order 19 | Common-core raw r B/T | Surrounding raw r B/T | Common-core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
{chr(10).join(native_rows)}

[All four native contexts](results/figures/NATIVE_ORDERS_1.png) retain their complete signed/scaled profiles and small shape/reference differences. Agreement is close, while the August curve has greater visible fine variation. Native and merged products share an exposure and extraction lineage; similarity is dependent evidence rather than another observation, a physical flux ratio or new validation of raw registration.

[All four byte-exact raw cutout/excess pairs](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png) retain their complete saved pixels and separate full scales. **Strong right-edge bands dominate these scales**, with alternating positive and negative residual lobes. The central trace and weak diffuse central excess are consequently faint, particularly in the August panel. The bright edge structure is not assigned to the catalog feature or given a physical origin. No central contrast variant, new crop, registration, subtraction, background model or pixel statistic was introduced.

All four original order-19 contexts retain true **global-grid, original local_mapping_usable, original baseline_mapping_verified and later five-window support**. Those historical stages remain separate from finite flux and physical origin. The later 0092 other-wavelength raw-window registration discrepancy is not transferred here. All four historical primary/secondary/adopted reviews remain **U/U/U** for broad rounded structure, neighboring shoulders and weak diffuse trace-associated excess. Current morphology and correlations do not promote a record or qualify a laser candidate. [Exact review and mapping records](../inputs/INPUT_INVENTORY.json).

## Dependence, verification and continuation

The bounded C016 window is disjoint from all completed C001–C012 group windows, which use other target observations. Original C016 epoch/profile/raw evidence and these seven HD114386 observations already existed. The same observations also supplied a completed normalization study at other blue wavelengths. This is not blind, untouched or independent-data validation and adds no observing time or archive-wide completeness. Completed C013/0092 and C014/0104 NORMALIZATION_CONTEXT routes remain complete and U and are not replayed. All previous outputs and classifications remain immutable.

The [independent actual arithmetic audit](../independent_audit/NUMERICAL_AUDIT.json) passes **{A['checks_passed']} checks across {A['scalar_values_compared']:,} scalar values**, reconstructing all 11 source windows, 22 profiles, 128 comparisons, four byte-identical raw copies and 16 self rows without importing production functions. Source flux, ERR, indices and profile metrics agree exactly. Maximum source-wavelength difference is **{diffs['input_source_wavelength']:.3e} Å**, raw interpolation difference **{diffs['profile_signed_raw_flux']:.3e} native units**, normalized difference **{diffs['profile_normalized_flux']:.3e}**, and comparison difference **{diffs['comparison']:.3e}**. Wavelengths/interpolation are not bitwise identical; computational agreement does not establish physical origin.

The exact method was public and read back before execution in commit `{release['publication_commit']}`. [Plan](PLAN.json), [root release](ROOT_RELEASE.json), [summary](results/SUMMARY.json), [bounded inputs](results/BOUNDED_INPUT_INDEX.json), [profile metrics](results/PROFILE_METRICS.csv), [all comparisons](results/COMPARISONS.csv) and [numerical hashes](results/OUTPUT_HASHES.json) bind the run. All four figures were visually inspected and fully decoded, with hashes/sizes checked against [PLOT_INDEX.json](results/PLOT_INDEX.json). All **{len(P['source_hashes'])} source bindings and {len(read(OUT/'OUTPUT_HASHES.json'))} numerical files** remain exact. [RESULTS_QA.json](RESULTS_QA.json) records these checks.

The next unfinished original-queue item is **{nxt['next_core_group']} / {member['candidate_id']}**, row **{member['queue_index']} / {member['resolution_group']}**, on **{member['target']}** at **{member['center_bary_air_angstrom']} Å**, currently U. This is the distinct INDIVIDUAL_PROFILE_CONTEXT route for 0095, with its own **May 16 2022** discovery `{member['discovery_dp_id']}` and prospective wavelength-specific topocentric anchor **3870.0539967497375 Å**. It reuses HD114386's seven observations and existing epoch/raw evidence; fresh native/header/mapping scope and a separately frozen method are required. [Next fixed-queue metadata](../scientific_review/NEXT_GROUP_METADATA.json) preserves the original selection and completed-route exclusions. No C015 array analysis or replay of completed normalization work was executed here.
'''
(HERE/'RESULTS_REPORT.md').write_text(report);print('Wrote C016 report:',len(report.encode()),'bytes')
