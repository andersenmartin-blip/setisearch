#!/usr/bin/env python3
"""Render all C018 reference families and every unavailable native outcome."""
from pathlib import Path
import datetime,json
HERE=Path(__file__).resolve().parent;OUT=HERE/'results';read=lambda p:json.loads(p.read_text())
P=read(HERE/'PLAN.json');R=read(OUT/'PROFILE_METRICS.json');C=read(OUT/'COMPARISONS.json');S=read(OUT/'SUMMARY.json');A=read(HERE.parent/'independent_audit/NUMERICAL_AUDIT.json');release=read(HERE/'ROOT_RELEASE.json');science=read(HERE.parent/'scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json');N=read(HERE.parent/'scientific_review/NEXT_GROUP_METADATA.json')
assert A['status'].startswith('PASS') and len(R)==42 and len(C)==252
valid=[r for r in R if r['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE'];rawonly=[r for r in R if r['normalization_status']=='RAW_ONLY']
assert len(valid)==28 and len(rawonly)==14 and all(r['order']==2 and r['normalization_reasons']==['MISSING_RIGHT_FLANK_COVERAGE'] and r['flank_reference']is None and r['low_flank_reference']is None for r in rawonly)
assert all(r['low_flank_reference']is False and r['raw_grid_finite_samples']==r['normalized_grid_finite_samples']==601 for r in valid)
assert sum(r['raw_pearson']is not None for r in C)==238 and sum(r['normalized_rms']is not None for r in C)==224
frames=['barycentric','topocentric'];fmt=lambda x:'Unavailable' if x is None else f'{x:.6f}';span=lambda a:fmt(min(a))+'–'+fmt(max(a));dates={r['dp_id']:r['date_obs'][:10] for r in R}
def pair(dp,ref,f,z,o=None):return next(r for r in C if r['dp_id']==dp and r['reference_dp_id']==ref and r['frame']==f and r['region']==z and r['order']==o)
def bt(dp,ref,z,k,o=None):return ' / '.join(fmt(pair(dp,ref,f,z,o)[k]) for f in frames)
def met(kind,dp,f,o=None):return next(r for r in R if r['kind']==kind and r['dp_id']==dp and r['frame']==f and r['order']==o)
families=[];ranges=[]
for event,ref in P['events'].items():
 others=[d for d in P['merged_dp_ids'] if d!=ref];rows=[]
 for d in others:
  rows.append('| '+dates[d]+' | '+' | '.join(bt(d,ref,z,k) for k in ['raw_pearson','normalized_rms'] for z in ['core','broad_pattern'])+' |')
  for z in ['core','broad_pattern']:
   assert pair(d,ref,'barycentric',z)['raw_pearson']>pair(d,ref,'topocentric',z)['raw_pearson'];assert pair(d,ref,'barycentric',z)['normalized_rms']<pair(d,ref,'topocentric',z)['normalized_rms']
 families.append('### '+event+' reference: '+dates[ref]+'\n\n| Other observation | Common-core raw r B/T | Surrounding raw r B/T | Common-core RMS B/T | Surrounding RMS B/T |\n|---|---:|---:|---:|---:|\n'+'\n'.join(rows))
 ranges.append('| '+event+' | '+' | '.join(span([pair(d,ref,'barycentric',z)[k] for d in others]) for k in ['raw_pearson','normalized_rms'] for z in ['core','broad_pattern'])+' |')
markers=[]
for m in P['event_markers']:
 core=P['individual_event_cores_bary_air_angstrom'][m['event']]
 markers.append('| '+m['event']+' | '+str(m['center_bary_air_angstrom'])+f" | [{core[0]:.6f}, {core[1]:.6f}] | {m['barycentric_offset_angstrom']:+.9f} | {m['discovery_topocentric_offset_angstrom']:+.9f} |")
locations=science['metadata_expected_feature_locations'];locrows=['| '+r['date_obs'][:10]+f" | {r['expected_center_offset_from_fixed_anchor_angstrom']:+.9f} | "+('Inside' if r['expected_center_inside_fixed_core'] else 'Outside')+' |' for r in locations]
assert sum(not r['expected_center_inside_fixed_core'] for r in locations)==4
support=[];signed=[];references=[];native=[]
for event,dp in P['events'].items():
 a,b=[met('native',dp,f,2) for f in frames]
 support.append('| '+event+' | '+f"{a['raw_grid_finite_samples']} / {b['raw_grid_finite_samples']} | "+' / '.join(str(pair(dp,dp,f,'broad_pattern',2)['common_finite_raw_samples']) for f in frames)+' | '+f"{a['window_native_finite_samples']} / {b['window_native_finite_samples']} | {a['left_flank_finite_samples']} / {b['left_flank_finite_samples']} | "+fmt(a['available_flank_median'])+' / '+fmt(b['available_flank_median'])+' | '+fmt(a['first_difference_noise_proxy'])+' / '+fmt(b['first_difference_noise_proxy'])+' |')
 def ratio(r,side):
  n=r['window_native_finite_samples'] if side=='window' else r[side+'_flank_finite_samples'];f=r['window_nonpositive_fraction'] if side=='window' else r[side+'_flank_nonpositive_fraction'];return 'Unavailable/0' if f is None else f'{round(f*n)}/{n}'
 signed.append('| '+event+' | '+ratio(a,'window')+'; '+ratio(b,'window')+' | '+ratio(a,'left')+'; '+ratio(b,'left')+' | Unavailable/0; Unavailable/0 |')
 c,d=[met('native',dp,f,3) for f in frames]
 references.append('| '+event+' | '+f"{c['window_native_finite_samples']} / {d['window_native_finite_samples']} | {c['left_flank_finite_samples']},{c['right_flank_finite_samples']} / {d['left_flank_finite_samples']},{d['right_flank_finite_samples']} | "+fmt(c['flank_reference'])+' / '+fmt(d['flank_reference'])+' | '+fmt(c['first_difference_noise_proxy'])+' / '+fmt(d['first_difference_noise_proxy'])+' |')
 for o in [2,3]:native.append('| '+event+' / '+str(o)+' | '+' | '.join(bt(dp,dp,z,k,o) for k in ['raw_pearson','normalized_rms'] for z in ['core','broad_pattern'])+' |')
nextrows=['| '+str(m['queue_index'])+' | '+m['candidate_id']+' | '+m['discovery_dp_id']+' | '+str(m['center_bary_air_angstrom'])+' | '+m['current_code']+' |' for m in N['members']]
assert N['next_core_group']=='C019' and len(N['members'])==5
complete=datetime.datetime.fromisoformat(S['completed_utc']).strftime('%Y-%m-%d at %H:%M:%S UTC');D=A['maximum_absolute_differences_by_kind']
native_links='\n'.join(f'- [Native page {i}: '+(['0114/0119','0124/0128','0133/0134','0138'][i-1])+f'](results/figures/NATIVE_ORDERS_{i}.png)' for i in range(1,5))
raw_links='\n'.join(f'- [Original raw page {i}: '+(['0114/0119','0124/0128','0133/0134','0138'][i-1])+f'](results/figures/PRESERVED_RAW_ORDER_CONTEXT_{i}.png)' for i in range(1,5))
report=f'''# C018: HD114783 joint spectral context

**Each of the seven fixed discovery references has higher barycentric raw correlation and lower barycentric normalized RMS against all six other epochs, in both the common core and surrounding window. All seven current C018 labels remain U.** The rounded central feature, nearby trough and wider structured spectrum recur with retained differences. These comparisons do not identify a line or physical origin, qualify a laser candidate, estimate significance or calibrate a null result.

The single released execution completed on **{complete}**: **42 profiles and 252 comparison slots**, including **28 identical-product self rows**, 21 bounded source windows and 14 byte-exact original raw-panel copies. Fourteen native order-2 profiles are **RAW_ONLY** because their entire positive reference flank is absent. There are **238 evaluable Pearson and 224 evaluable RMS values**, with **14 unavailable surrounding Pearson and 28 unavailable normalized RMS outcomes** retained explicitly. No source is blocked or structurally excluded. No acquisition or observing time was added.

## Seven reference families over seven observations

C018 uses HD114783's own seven January 2022–July 2023 observing products; every one is a fixed discovery reference. There are **196 merged comparison rows** (7×7×2 frames×2 regions) and **56 native comparison rows** (14 native sources×2×2). Native profiles compare only with their own same-exposure merged product.

Each reference has six other epochs. The **42 directed nonself rows per frame/region represent 21 unordered exposure pairs and 21 reciprocal duplicates**, reusing only seven observations. They are not 42 independent epochs. Source/reference identities, self flags and same-exposure flags remain in the complete output. All 28 self rows retain r≈1 and RMS=0 and add no recurrence evidence. No favorable reference or epoch is selected. Values separated by `/` below are **barycentric/topocentric**.

{chr(10).join(families)}

Per-reference barycentric ranges across all six other epochs are:

| Reference | Common-core raw r range | Surrounding raw r range | Common-core RMS range | Surrounding RMS range |
|---|---:|---:|---:|---:|
{chr(10).join(ranges)}

All six comparisons in each of the seven families favor barycentric r and RMS in both regions. This is descriptive, dependent agreement rather than a calibrated origin test. **January 21 2022 ↔ January 16 2023** retains strong topocentric agreement at **r=0.987756 in the core and 0.984144 in the surroundings**, consistent with their close BERVs; barycentric agreement remains better. Thus topocentric results are not uniformly weak or negative.

- [All seven epochs: broad signed/scaled context](results/figures/MERGED_BROAD_CONTEXT.png)
- [The same epochs: fixed common group core](results/figures/MERGED_CORE_CONTEXT.png)

The common-core figure retains a rounded multi-sample crest, positive-side trough and neighboring rise. The broad figure preserves many peaks and troughs throughout both reference flanks. **July 1 2023 has a sharp excursion near the far positive edge of the barycentric outer window**, also retained in the native order-3 barycentric panel. It accompanies weaker broad correlations involving July and remains on the full scales without masking or a contrast variant. It falls outside the different fixed topocentric context; its absence there is not a fitted removal. No origin is assigned to that excursion or equated with the central catalog feature. No center, width, lag, stellar velocity, continuum, background, drift or selected frame shift was fitted.

## Common geometry, exact member floats and seven markers

The common midpoint is **3869.33375 Å** barycentric air, from catalog extrema rather than fitted peaks. Its common ±3 Å context is **[3866.33375,3872.33375] Å** and common ±0.25 Å core **[3869.08375,3869.58375] Å**. The 0.01 Å grid has **601 centers: 51 common-core and 550 surrounding**, with unchanged support gates **41/440**.

The common core **is not the union of original member cores**. Original extrema cores extend approximately **0.00125 Å outside one common edge** (maximum machine-float offset 0.0012500000002546585 Å). Preserve 3869.3349999999996 separately from 3869.335 and 3869.3325; these are exact catalog inputs, not wavelength-accuracy claims. All exact original bounds remain in the plan; intervals displayed below are rounded to six decimal places for readability.

| Member | Exact original center (Å) | Original member core, displayed (Å) | Barycentric marker offset (Å) | Own discovery topocentric marker offset (Å) |
|---|---:|---|---:|---:|
{chr(10).join(markers)}

One common topocentric-air anchor is **3868.9509913064876 Å**, from the **first original-queue 0114 discovery, observed January 21 2022**, BERV **29.658729150824 km/s**, under `group_midpoint/(1+BERV/c)`. This coordinate rule does not remove any reference. Event markers use each exact original center and own discovery BERV, not the group midpoint or a fitted peak. Coincident barycentric markers retain separate IDs; out-of-core markers remain in the broad view/legend/metadata. The common core is not claimed to contain every complete original member core or measure physical linewidth.

The own-target BERV span is **59.073251754930496 km/s**. These group-midpoint coordinates were computed from metadata before observed values were read, assuming a barycentrically coherent midpoint; they are predictions, not measured peak locations.

| Observation | Predicted common-midpoint offset from anchor (Å) | Fixed common ±0.25 Å core |
|---|---:|---|
{chr(10).join(locrows)}

**Four predicted centers lie outside the common topocentric core on the positive side**: May 5 2022, March 22 2023, May 15 2023 and July 1 2023. The largest offset is +0.757919727 Å. January/February 2022 and January 2023 remain inside. Center flags do not establish full finite-width feature coverage. The fixed core is not recentered and may sample neighboring structure. BERV displacement supplies geometry rather than calibrated origin discrimination. [Prospective geometry and assumptions](../scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json).

## Fourteen raw-only profiles and every unavailable statistic

Fresh scans of **504 headers** select orders **2 and 3 in every discovery**. All 14 source contexts cover the full common core. Every order 2 covers the negative reference flank but misses the entire positive flank [1.5,3] Å in both frames. The 14 order-2 profiles retain reason exactly **`MISSING_RIGHT_FLANK_COVERAGE`**, no valid pooled reference and **null low-reference flags**, not false.

Order 2 retains 51 common raw core samples, allowing all 14 native core Pearson values. Its surrounding support is below the unchanged 440-sample gate in every frame, so **14 native surrounding Pearson values remain unavailable**. Invalid two-flank normalization leaves **all 28 order-2 normalized RMS slots unavailable**. No flank or value is borrowed from order 3.

| Event/order 2 | Finite raw grid B/T | Surrounding common raw support B/T | Finite original window B/T | Finite left flank B/T | Available one-sided median B/T | First-difference proxy B/T |
|---|---:|---:|---:|---:|---:|---:|
{chr(10).join(support)}

Right-flank finite sample counts are **zero in all 14 profiles**. The available one-sided medians above are positive but **are not valid two-flank references**; their availability does not permit normalization or turn null low flags false. Partial finite grid support and original source sample counts remain distinct. Missing right coverage is not extrapolated or repaired by moving the window.

The 14 merged and 14 order-3 profiles have complete 601-point raw/normalized support, valid positive references and **28 false low-reference flags**. No low flag is true. There are zero wavelength-gap masks. Every profile has **zero positive finite ERR samples**. Complete reference support does not establish formal uncertainty or physical origin.

## Signed values and valid native references

**Twelve profile rows contain nonpositive original window samples**, all in order 2: six discovery exposures in both frames. March 22 2023/order 2 has zero such samples in both frames; all merged and order-3 rows also have zero window/flank nonpositive fractions. The other **30 profile rows have zero nonpositive window samples**. All signed values remain unchanged. The table lists barycentric; topocentric original-source counts, distinct from grid counts. Missing right-flank fractions remain unavailable, not zero-valued measurements.

| Event/order 2 | Window nonpositive/finite B; T | Left flank nonpositive/finite B; T | Right flank B; T |
|---|---|---|---|
{chr(10).join(signed)}

May 5 2022 retains one nonpositive left-flank sample in **both frames (1/166)**. July 1 2023 retains one in the **barycentric left flank (1/166)** while its topocentric left flank has zero; the coordinate masks differ. These three left-flank outcomes remain explicit. All merged original windows contain 600 finite samples and 150 per flank. Their valid references span **{span([r['flank_reference'] for r in R if r['kind']=='merged'])} ADU** and descriptive first-difference proxies **{span([r['first_difference_noise_proxy'] for r in R if r['kind']=='merged'])} ADU**.

Order 3's valid reference/source accounting is:

| Event/order 3 | Finite original window B/T | Finite flanks L,R B/T | Valid pooled reference B/T | First-difference proxy B/T |
|---|---:|---|---:|---:|
{chr(10).join(references)}

Native BUNIT is absent in all seven products, so native extracted units remain unspecified and distinct from merged ADU. Fixed flanks contain substantial spectral structure; every sample remains in the median without masks, moved flanks or fitted replacements. These are descriptive reference levels rather than established line-free continua. Positive scalar division leaves Pearson unchanged, while normalized heights/RMS depend on the levels. The first-difference proxy and reference≤3×proxy rule are not formal SNR or quality certificates. ERR support/proxies do not establish false-alarm probability, sensitivity or a qualified survey null.

## Every native comparison and complete page

Native and merged products share exposure/extraction lineage; agreement is dependent evidence rather than another observation or physical flux ratio. Every source compares only with its own same-exposure merged product. Unavailable values below are preserved outcomes, not omitted rows.

| Native event/order | Common-core raw r B/T | Surrounding raw r B/T | Common-core RMS B/T | Surrounding RMS B/T |
|---|---:|---:|---:|---:|
{chr(10).join(native)}

{native_links}

All fourteen native contexts remain in four fixed pages. Order-2 signed curves retain their noisy structure and abrupt coverage endpoints. Their scaled panels retain the merged curve with explicit RAW_ONLY/missing-flank annotations; absent native normalized curves are not zero-flux measurements. Order 3 follows the merged profile more closely, retaining spectral differences and the July outer excursion. No partial order is filled from an overlapping order.

## Original raw panels and staged history

{raw_links}

All fourteen exact original raw/excess pairs remain in four pages, each with its own complete scales and saved index extent. Many panels show a central extended patch/vertical trace, noisier in order 2 and clearer in order 3, plus retained edge structure. **The remote high-left deposit in 0134/order 2 dominates its full scale**, so its central enhancement is faint/unresolved in that view. The remote deposit does not classify the central feature. No cropped/contrast-enhanced variant, new registration, subtraction, background model, pixel statistic or origin assignment was introduced.

**0128 uses its exact original 21×25, five-array containers**, distinct from the six batch03 members' 31×33 panels. Later wider containers do not replace those originals. Their different saved index extents are not forced to a common spatial scale or interpreted as independent new pixels.

Historical stages remain separate. Every original order 2 has true global support but **false original local_mapping_usable and baseline_mapping_verified**; order 3 has true original stages. Later both-order five-window support is true, including 0128's completed follow-up, and does not retroactively repair original failures. **Six batch03 members originally retain U/U/U. 0128 originally has primary I, secondary M (normalized I), adopted baseline I, then later separate U/U/current U at unchanged coordinates/pixels.** Do not flatten those stages into blanket original-U reviews. The completed mapping diagnosis is not replayed as new progress. Current all-U labels, shape, frame correlation and mapping support do not establish origin or qualify a laser candidate. [Exact stage-specific review and mapping custody](../inputs/INPUT_INVENTORY.json).

## Verification, dependence and continuation

Blue numeric overlaps with earlier HD106515A, HD112410 and HD114386 windows belong to other target observations and share no source pixels. Original C018 epoch/profile/raw evidence and the wider 0128 diagnosis already existed. This is not blind, untouched, independent-data or new observing-time evidence and does not add archive-wide completeness. Completed normalization/mapping diagnoses and prior outputs/classifications remain unchanged.

The [independent actual arithmetic audit](../independent_audit/NUMERICAL_AUDIT.json) passes **{A['checks_passed']} checks across {A['scalar_values_compared']:,} scalar values**, reconstructing all 21 source windows, 42 profiles, 252 comparisons, 14 byte-exact raw copies and 28 self rows without importing production functions. Source flux, ERR, indices and profile metrics agree exactly. Maximum source-wavelength difference is **{D['input_source_wavelength']:.3e} Å**, raw interpolation difference **{D['profile_signed_raw_flux']:.3e} native units**, normalized difference **{D['profile_normalized_flux']:.3e}**, and comparison difference **{D['comparison']:.3e}**. Wavelengths/interpolation are not bitwise identical; computational agreement does not establish origin.

The exact method was public and read back before execution in commit `{release['publication_commit']}`. [Plan](PLAN.json), [root release](ROOT_RELEASE.json), [summary](results/SUMMARY.json), [bounded inputs](results/BOUNDED_INPUT_INDEX.json), [profile metrics](results/PROFILE_METRICS.csv), [all comparisons](results/COMPARISONS.csv) and [numeric hashes](results/OUTPUT_HASHES.json) bind the run. **All ten figures were visually inspected and fully decoded**, with hashes/sizes and complete page counts checked against [PLOT_INDEX.json](results/PLOT_INDEX.json). All **103 source bindings and 87 numerical files** remain unchanged. [RESULTS_QA.json](RESULTS_QA.json) records delivery checks.

The next unfinished original-queue route is **C019 / R020, JOINT_PROFILE_CONTEXT on HD114783**, retaining all five members:

| Queue row | Record | Fixed discovery product | Exact catalog center (Å) | Current code |
|---|---|---|---:|---|
{chr(10).join(nextrows)}

C019 needs its own separately frozen common geometry/anchor, all five reference identities, exact member floats and fresh order-3/4 scope. Do not transfer C018 order-2 missing flanks or staged 0128 history to the distinct **0129** event. C019/0129 was originally supported/U in its older raw_followup source; its absent later-five-window fields remain **null/unassessed**, not failures or inferred later success, and it was not selected in 0128's completed follow-up. Preserve 0135's remote off-trace order-3 pixel separately from its diffuse central feature. [Next queue metadata and distinct histories](../scientific_review/NEXT_GROUP_METADATA.json) retain these dependencies. No C019 array analysis or replay of completed diagnostics was executed here.
'''
(HERE/'RESULTS_REPORT.md').write_text(report);print('Wrote C018 report:',len(report.encode()),'bytes')
