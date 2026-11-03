#!/usr/bin/env python3
"""Write complete C011 context from the immutable released output tables."""
from pathlib import Path
import datetime,json,statistics
HERE=Path(__file__).resolve().parent;OUT=HERE/'results';read=lambda p:json.loads(p.read_text())
P=read(HERE/'PLAN.json');R=read(OUT/'PROFILE_METRICS.json');C=read(OUT/'COMPARISONS.json');S=read(OUT/'SUMMARY.json')
A=read(HERE.parent/'independent_audit/NUMERICAL_AUDIT.json');release=read(HERE/'ROOT_RELEASE.json')
science=read(HERE.parent/'scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json');nxt=read(HERE.parent/'scientific_review/NEXT_GROUP_METADATA.json')
assert A['status'].startswith('PASS') and len(R)==18 and len(C)==36
assert all(r['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE' and not r['normalization_reasons'] and r['flank_reference']>0 and r['raw_grid_finite_samples']==601 and r['normalized_grid_finite_samples']==601 and r['positive_finite_ERR_samples']==0 and r['gap_masked_grid_samples']==0 and r['outside_native_coverage_grid_samples']==0 for r in R)
assert all(r['raw_pearson'] is not None and r['normalized_rms'] is not None for r in C)
assert sum(r['low_flank_reference']is True for r in R)==2 and all(r['order']==2 for r in R if r['low_flank_reference']is True)
frames=['barycentric','topocentric'];fmt=lambda x:'Unavailable' if x is None else f'{x:.6f}';span=lambda a:fmt(min(a))+'–'+fmt(max(a))
dates={r['dp_id']:r['date_obs'][:10] for r in R};merged=[r for r in R if r['kind']=='merged']
def pair(dp,f,z,o=None):return next(r for r in C if r['dp_id']==dp and r['frame']==f and r['region']==z and r['order']==o)
def bt(dp,z,k,o=None):return ' / '.join(fmt(pair(dp,f,z,o)[k]) for f in frames)
def metric(kind,dp,f,o=None):return next(r for r in R if r['kind']==kind and r['dp_id']==dp and r['frame']==f and r['order']==o)
other=[d for d in P['merged_dp_ids'] if d!=P['anchor_dp_id']];epoch_rows=[]
for dp in other:
 epoch_rows.append('| '+dates[dp]+' | '+' | '.join(bt(dp,z,k) for k in ['raw_pearson','normalized_rms'] for z in ['core','broad_pattern'])+' |')
 for z in ['core','broad_pattern']:
  assert pair(dp,'barycentric',z)['raw_pearson']>pair(dp,'topocentric',z)['raw_pearson']
  assert pair(dp,'barycentric',z)['normalized_rms']<pair(dp,'topocentric',z)['normalized_rms']
summary_rows=[]
for f in frames:
 for z in ['core','broad_pattern']:
  rows=[r for r in C if r['relationship']=='MERGED_EPOCH_TO_DISCOVERY' and not r['identical_product_self_pair'] and r['frame']==f and r['region']==z]
  summary_rows.append('| '+f+' | '+('Core' if z=='core' else 'Surroundings')+' | '+span([r['raw_pearson'] for r in rows])+' | '+fmt(statistics.median(r['raw_pearson'] for r in rows))+' | '+span([r['normalized_rms'] for r in rows])+' |')
locations=science['metadata_expected_feature_locations'];assert all(r['expected_center_inside_fixed_core'] for r in locations)
offset_rows=['| '+r['date_obs'][:10]+' | '+('Discovery' if r['dp_id']==P['anchor_dp_id'] else 'Other epoch')+f" | {r['expected_center_offset_from_fixed_anchor_angstrom']:+.9f} | Inside |" for r in locations]
def count_ratio(r,side):
 n=r['window_native_finite_samples'] if side=='window' else r[side+'_flank_finite_samples']
 f=r['window_nonpositive_fraction'] if side=='window' else r[side+'_flank_nonpositive_fraction']
 return f'{round(f*n)}/{n}'
quality_rows=[]
for kind,dp,o in [('merged',d,None) for d in P['merged_dp_ids']]+[('native',P['anchor_dp_id'],o) for o in [2,3]]:
 label=('Merged '+dates[dp]) if kind=='merged' else 'Native order '+str(o)+', '+dates[dp]
 quality_rows.append('| '+label+' | '+' | '.join('; '.join(count_ratio(metric(kind,dp,f,o),side) for f in frames) for side in ['window','left','right'])+' |')
reference_rows=[]
for kind,o,label in [('merged',None,'Merged (ADU)'),('native',2,'Native order 2 (unspecified)'),('native',3,'Native order 3 (unspecified)')]:
 for frame in frames:
  r=metric(kind,P['anchor_dp_id'],frame,o)
  reference_rows.append('| '+label+' | '+frame+' | '+str(r['left_flank_finite_samples'])+' / '+str(r['right_flank_finite_samples'])+' | '+' | '.join(fmt(r[k]) for k in ['left_flank_median','right_flank_median','flank_reference','first_difference_noise_proxy'])+' | '+str(r['low_flank_reference'])+' |')
native_rows=['| '+str(o)+' | '+' | '.join(bt(P['anchor_dp_id'],z,k,o) for k in ['raw_pearson','normalized_rms'] for z in ['core','broad_pattern'])+' |' for o in [2,3]]
next_rows=['| '+str(m['queue_index'])+' | '+m['candidate_id']+' | '+m['discovery_dp_id']+' | '+str(m['center_bary_air_angstrom'])+' | '+m['current_code']+' |' for m in nxt['members']]
assert nxt['next_core_group']=='C016' and len(nxt['members'])==4
completed=datetime.datetime.fromisoformat(S['completed_utc']).strftime('%Y-%m-%d at %H:%M:%S UTC');diffs=A['maximum_absolute_differences_by_kind']
report=f'''# C011: HD112410 individual spectral context

**All six other epochs agree better with the fixed May discovery profile in barycentric coordinates than in the fixed topocentric frame, in both the original core and surrounding window. V2E2-0089 remains U.** Both native orders have complete coverage and valid positive normalization. **Order 2's two low-reference flags are true** and its noisy signed variation remains explicit. These descriptive results do not identify a spectral line or physical origin, qualify a laser candidate, estimate significance or calibrate a null result.

The single released execution completed on **{completed}**: **18 profiles and 36 comparison slots**, including four identical-product self rows, nine bounded source windows and two byte-exact historical raw-panel copies. All 36 Pearson values and all 36 normalized RMS values are evaluable; there are zero raw-only, blocked or structurally excluded slots. The only reference is **`ADP.2025-05-29T01:01:14.389`**, observed **2025-05-28**. All seven April–August 2025 HD112410 observations remain included; no acquisition or observing time was added.

## Complete frame comparisons

The exact input catalog center is **3865.6775000000002 Å** barycentric air, with original core **[3865.4275000000002,3865.9275000000002] Å** and full context **[3862.6775000000002,3868.6775000000002] Å**. These are fixed catalog/window inputs rather than fitted feature locations, measured physical widths or a wavelength-accuracy claim. Figures display 3865.6775 Å.

Each row below compares one other epoch with the unchanged May discovery. Values separated by `/` are barycentric/topocentric; the four self rows are excluded.

| Other observation (UTC) | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
{chr(10).join(epoch_rows)}

| Frame | Region | Nonself raw r range | Median raw r | Nonself normalized RMS range |
|---|---|---:|---:|---:|
{chr(10).join(summary_rows)}

Barycentric r is higher and normalized RMS lower in **all six pairs in each region**. May 30 has high correlation in both frames, consistent with its small metadata-predicted displacement from the May 28 anchor; its topocentric core r is 0.953127 versus barycentric 0.973576. The other five topocentric core correlations are negative. June 27 has the lowest barycentric core r and largest core RMS; July 9 has the lowest surrounding r and August 7 the largest surrounding RMS. These retained differences prevent selecting only the most favorable epoch. The four identical-product self rows retain r≈1 and RMS=0 and add no recurrence evidence.

- [All seven epochs: broad signed and scaled context](results/figures/MERGED_BROAD_CONTEXT.png)
- [The same epochs: fixed original core](results/figures/MERGED_CORE_CONTEXT.png)

The core figure retains a broad multi-sample central rise and the positive-side trough and secondary rise. The April exposure is strongest in raw ADU, while the May discovery has a sharper scaled central crest. The broad view retains repeated peaks and troughs throughout both fixed reference flanks. Surrounding agreement does not isolate one emission line. No center, width, lag, stellar velocity, continuum, background, drift or selected frame shift was fitted. Markers denote the catalog/discovery coordinate, not fitted peaks.

## Own May anchor and coordinate geometry

The discovery BERV **−5.48386283255014 km/s** gives the newly computed topocentric-air anchor **3865.748213029564 Å**. C012's April reference and numeric anchor were not transferred. The fixed ±3 Å grid has **601 centers at 0.01 Å spacing**, with 51 original-core and 550 surrounding centers; common-support gates remain **41/440**. The seven own-target epochs span **21.30284860830273 km/s** in BERV.

These positions were calculated from metadata before observed values were read, assuming a barycentrically coherent catalog center. They are predicted coordinates rather than measured peak locations.

| Observation (UTC) | Role | Predicted offset from fixed anchor (Å) | Original ±0.25 Å core |
|---|---|---:|---|
{chr(10).join(offset_rows)}

**All seven predicted centers remain inside this fixed topocentric core.** April 29 is at −0.114616520 Å, May 30 only +0.007535802 Å and August 7 at the largest positive displacement, +0.160086601 Å. This differs from C012's April-anchored geometry. A center flag does not establish full finite-width feature coverage. The fixed window is not recentered and can sample different surrounding structure. The BERV span supplies coordinate separation rather than calibrated origin discrimination. [Prospective coordinates and caveats](../scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json).

## Signed quality and positive references

All **18 profiles have full 601-point raw and normalized support**, valid positive two-flank medians, zero outside-coverage/gap masks and **zero positive finite ERR samples**. All 36 comparisons use complete 51-point core or 550-point surrounding common support. **Six profile rows contain nonpositive original source samples**, preserved without clipping or sign changes; the other 12 rows have none. Counts below concern original source samples rather than interpolated grid support. Each cell lists **barycentric; topocentric** counts; two frames of one exposure remain dependent.

| Source / observation (UTC) | Window nonpositive B; T | Left flank nonpositive B; T | Right flank nonpositive B; T |
|---|---:|---:|---:|
{chr(10).join(quality_rows)}

The May discovery retains **3/600 (0.5%)** nonpositive window samples in each frame, all outside both reference flanks. Native order 2 retains **29/655 (4.4275%)**, including **13/168 (7.7381%)** in its right flank and none in its left. Order 3 retains **3/534 (0.5618%)**, outside both flanks. Source masks differ slightly by frame: May 30 topocentric has **599 finite window samples and 149 left-flank samples**, while its barycentric source masks have 600/150. Both still yield full 601-point interpolated support without a gap or extrapolation.

Discovery reference values are:

| Product and units | Frame | Finite flank samples L/R | Left median | Right median | Pooled reference | First-difference proxy | Low flag |
|---|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(reference_rows)}

**Order 2's reference is valid and positive at 43.386597, yet low=true in both frames**, because it is ≤3 times its proxy 17.929966. These are **not raw-only** profiles: normalization and all comparisons remain evaluable under the frozen rule. The noisy scaled curve and true-low annotations are retained in both native panels. The remaining **16 low-reference flags are false**; none is null. Neither outcome is a formal SNR or general quality certificate.

Merged reference levels span **{min(r['flank_reference'] for r in merged):.6f}–{max(r['flank_reference'] for r in merged):.6f} ADU** and first-difference proxies **{min(r['first_difference_noise_proxy'] for r in merged):.6f}–{max(r['first_difference_noise_proxy'] for r in merged):.6f} ADU**. Every fixed-flank source sample and its spectral structure remains in the pooled medians. These descriptive levels are not established line-free continua. Positive scalar division leaves Pearson unchanged; scaled heights and RMS depend on the reference levels. ERR support and descriptive proxies do not supply formal uncertainty, false-alarm probability, sensitivity or a qualified survey null.

## Both native orders and historical raw context

The fresh all-72-order header scan selects **orders 2 and 3**, both covering the entire fixed context, core and both reference flanks in each frame. No C012 missing-flank outcome applies. Native BUNIT is absent; extracted units remain unspecified and distinct from merged ADU. Both orders and the merged discovery share one May exposure and extraction lineage, so agreement is dependent evidence rather than another observation or a physical flux ratio.

| Native order | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
{chr(10).join(native_rows)}

[Both native order contexts](results/figures/NATIVE_ORDERS_1.png) retain full signed and scaled curves. Order 2 is noisier, has nonpositive samples and stronger scaled spikes. Order 3 follows the merged central shape more closely, while surrounding differences and its retained negative trough remain visible. Same-exposure similarity and complete coverage do not independently validate raw registration or physical origin.

[Both exact historical raw cutout/excess pairs](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png) retain diffuse central trace-associated enhancement, weaker/noisier in order 2 and clearer in order 3. Strong right-edge structure remains on the full scales, including alternating positive and negative order 3 residuals. It is not assigned to the catalog feature or given a physical origin. All pixels, original subtraction and separate complete scales remain unchanged; no crop, contrast variant, new registration, background model, subtraction or pixel statistic was introduced.

**Both C011 orders retain true global-grid, original local_mapping_usable, original baseline_mapping_verified and later five-window support.** C012's order 2 original local/baseline false flags do not apply here. All historical primary, secondary and adopted reviews remain **U/U/U** for broad native structure and diffuse trace-associated enhancement. Historical mapping support, current low-reference outcomes and morphology do not change U or qualify a laser candidate. [Exact review and mapping records](../inputs/INPUT_INVENTORY.json).

## Dependence, verification and continuation

C011 uses the same seven HD112410 observing products as C010/C012. Its core lies outside C012's window, but their broader windows overlap over **[3866.2675,3868.6775000000002] Å**, width **2.4100000000003092 Å**. The entire C011 positive reference flank lies within that previously viewed C012 window. Those shared surrounding/reference pixels and prior original C011 epoch/raw evidence make this dependent post-detection context, not blind or independent wavelength validation. C010's window is disjoint. Numeric overlaps with other-target HD106515A windows share no source pixels. Earlier outputs and labels remain unchanged.

The [independent actual arithmetic audit](../independent_audit/NUMERICAL_AUDIT.json) passes **{A['checks_passed']} checks across {A['scalar_values_compared']:,} scalar values**, reconstructing all nine source windows, 18 profiles, 36 comparisons, two raw copies and four self rows without importing production functions. Source flux, ERR, indices and profile metrics agree exactly. Maximum source-wavelength difference is **{diffs['input_source_wavelength']:.3e} Å**, raw interpolation difference **{diffs['profile_signed_raw_flux']:.3e} native units**, normalized difference **{diffs['profile_normalized_flux']:.3e}**, and comparison difference **{diffs['comparison']:.3e}**. Wavelengths/interpolation are therefore not bitwise identical; computational agreement does not establish physical origin.

The exact method was public and read back before execution in commit `{release['publication_commit']}`. [Plan](PLAN.json), [root release](ROOT_RELEASE.json), [summary](results/SUMMARY.json), [bounded inputs](results/BOUNDED_INPUT_INDEX.json), [profile metrics](results/PROFILE_METRICS.csv), [comparisons](results/COMPARISONS.csv) and [numeric hashes](results/OUTPUT_HASHES.json) bind the run. All four figures were visually inspected and fully decoded, with hashes/sizes checked against [PLOT_INDEX.json](results/PLOT_INDEX.json). All **{len(P['source_hashes'])} source bindings and {len(read(OUT/'OUTPUT_HASHES.json'))} numerical files** remain exact. [RESULTS_QA.json](RESULTS_QA.json) records these checks.

The next unfinished original-queue work is **C016 / R017, JOINT_PROFILE_CONTEXT on HD114386**, grouping four records rather than replaying completed normalization routes:

| Queue row | Record | Own discovery product | Catalog center (Å) | Current code |
|---|---|---|---:|---|
{chr(10).join(next_rows)}

C013 / 0092 at row 26 and C014 / 0104 at row 31 already have complete descriptive NORMALIZATION_CONTEXT diagnostics and remain U; they are skipped as completed work. C016 requires its **own HD114386 cohort, four fixed discovery references, newly frozen group geometry/anchor and fresh native/header/mapping scope**. HD112410 products, May anchor and quality outcomes must not be transferred. [Next queue metadata and completion evidence](../scientific_review/NEXT_GROUP_METADATA.json) preserve this selection. No C016 array analysis or replay of completed normalization work was executed here.
'''
(HERE/'RESULTS_REPORT.md').write_text(report);print('Wrote C011 report:',len(report.encode()),'bytes')
