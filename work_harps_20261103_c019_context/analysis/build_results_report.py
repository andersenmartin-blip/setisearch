#!/usr/bin/env python3
"""Render all five C019 reference families and actual signed/reference outcomes."""
from pathlib import Path
import datetime,json
HERE=Path(__file__).resolve().parent;OUT=HERE/'results';read=lambda p:json.loads(p.read_text())
P=read(HERE/'PLAN.json');R=read(OUT/'PROFILE_METRICS.json');C=read(OUT/'COMPARISONS.json');S=read(OUT/'SUMMARY.json');A=read(HERE.parent/'independent_audit/NUMERICAL_AUDIT.json');release=read(HERE/'ROOT_RELEASE.json');science=read(HERE.parent/'scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json');N=read(HERE.parent/'scientific_review/NEXT_GROUP_METADATA.json')
assert A['status'].startswith('PASS') and len(R)==34 and len(C)==180
assert all(r['normalization_status']=='USABLE_POSITIVE_FLANK_REFERENCE' and not r['normalization_reasons'] and r['flank_reference']>0 and r['low_flank_reference']is False and r['raw_grid_finite_samples']==r['normalized_grid_finite_samples']==601 and r['positive_finite_ERR_samples']==0 and r['outside_native_coverage_grid_samples']==r['gap_masked_grid_samples']==0 for r in R)
assert all(r['raw_pearson']is not None and r['normalized_rms']is not None for r in C)
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
locations=science['metadata_expected_feature_locations'];locrows=['| '+r['date_obs'][:10]+' | '+('Reference' if r['dp_id']in P['discovery_dp_ids'] else 'Cohort only')+f" | {r['expected_center_offset_from_fixed_anchor_angstrom']:+.9f} | "+('Inside' if r['expected_center_inside_fixed_core'] else 'Outside')+' |' for r in locations];assert sum(not r['expected_center_inside_fixed_core'] for r in locations)==4
quality=[];signed=[];native=[]
for kind,dp,o in [('merged',d,None) for d in P['merged_dp_ids']]+[('native',d,o) for d in P['discovery_dp_ids'] for o in [3,4]]:
 a,b=[met(kind,dp,f,o) for f in frames];label=('Merged '+dates[dp]) if kind=='merged' else 'Native '+str(o)+' '+dates[dp]
 quality.append('| '+label+' | '+f"{a['window_native_finite_samples']} / {b['window_native_finite_samples']} | {a['left_flank_finite_samples']},{a['right_flank_finite_samples']} / {b['left_flank_finite_samples']},{b['right_flank_finite_samples']} | "+fmt(a['flank_reference'])+' / '+fmt(b['flank_reference'])+' | '+fmt(a['first_difference_noise_proxy'])+' / '+fmt(b['first_difference_noise_proxy'])+' |')
for r in R:
 if r['window_nonpositive_fraction']>0:
  n=r['window_native_finite_samples'];l=r['left_flank_finite_samples'];signed.append('| '+r['date_obs'][:10]+' | '+r['frame']+' | '+str(r['order'])+f" | {round(n*r['window_nonpositive_fraction'])}/{n} | {round(l*r['left_flank_nonpositive_fraction'])}/{l} | 0/{r['right_flank_finite_samples']} |")
assert len(signed)==6
for event,dp in P['events'].items():
 for o in [3,4]:native.append('| '+event+' / '+str(o)+' | '+' | '.join(bt(dp,dp,z,k,o) for k in ['raw_pearson','normalized_rms'] for z in ['core','broad_pattern'])+' |')
nextrows=['| '+str(m['queue_index'])+' | '+m['candidate_id']+' | '+m['discovery_dp_id']+' | '+str(m['center_bary_air_angstrom'])+' | '+m['current_code']+' |' for m in N['members']];assert N['next_core_group']=='C021' and len(N['members'])==5
complete=datetime.datetime.fromisoformat(S['completed_utc']).strftime('%Y-%m-%d at %H:%M:%S UTC');D=A['maximum_absolute_differences_by_kind'];j1=P['events']['V2E2-0115'];j2=P['events']['V2E2-0129'];jc=pair(j1,j2,'topocentric','core')['raw_pearson'];jb=pair(j1,j2,'topocentric','broad_pattern')['raw_pearson']
native_links='\n'.join(f'- [Native page {i}: '+(['0115/0120','0125/0129','0135'][i-1])+f'](results/figures/NATIVE_ORDERS_{i}.png)' for i in range(1,4));raw_links='\n'.join(f'- [Original raw page {i}: '+(['0115/0120','0125/0129','0135'][i-1])+f'](results/figures/PRESERVED_RAW_ORDER_CONTEXT_{i}.png)' for i in range(1,4))
report=f'''# C019: HD114783 joint spectral context

**Each of the five fixed discovery references has higher barycentric raw correlation and lower barycentric normalized RMS against all six other epochs, in both the common core and surrounding window. All five original/current C019 labels remain U.** The central rounded feature, neighboring troughs and wider structured pattern recur with retained amplitude/reference differences. These descriptive comparisons do not identify a line or physical origin, qualify a laser candidate, estimate significance or calibrate a null result.

The single released execution completed on **{complete}**: **34 profiles and 180 comparisons**, including **20 identical-product self rows**, 17 bounded source windows and ten byte-exact original raw-panel copies. All 180 Pearson and 180 RMS values are evaluable. Every profile has full support, a valid positive reference and false low-reference flag. There are zero raw-only, blocked or structurally excluded slots. No acquisition or observing time was added.

## Five references over seven observing products

Retain HD114783's same seven existing January 2022–July 2023 epochs. Fixed references are 0115/0120/0125/0129/0135, observed January 21 2022, February 5 2022, May 5 2022, January 16 2023 and May 15 2023. **March 22 and July 1 2023 remain cohort epochs without becoming discovery references.** There are 140 merged comparisons (7×5×2 frames×2 regions) plus 40 native comparisons (10 sources×2×2), native only to own same-exposure merged products.

Each reference has six other epochs. **Thirty directed nonself rows per frame/region represent 20 unordered exposure pairs and 10 reciprocal reference-pair duplicates**, using seven observations rather than 30 independent epochs. Source/reference identities and dependency flags remain explicit. All 20 self rows remain at r≈1 and RMS=0 and add no recurrence evidence. No favorable reference/epoch is selected. Values separated by `/` below are **barycentric/topocentric**.

{chr(10).join(families)}

Per-reference barycentric ranges across six other epochs are:

| Reference | Common-core raw r range | Surrounding raw r range | Common-core RMS range | Surrounding RMS range |
|---|---:|---:|---:|---:|
{chr(10).join(ranges)}

All six comparisons in each of the five families favor barycentric r and RMS in both regions. This is dependent agreement under fixed windows, not a calibrated origin test. **January 21 2022 ↔ January 16 2023** still has strong topocentric correlation: **{jc:.6f} core / {jb:.6f} surroundings**, consistent with their close BERVs. These close-coordinate results remain included rather than describing all topocentric agreement as weak or negative.

- [All seven epochs: broad signed/scaled context](results/figures/MERGED_BROAD_CONTEXT.png)
- [The same epochs: fixed common core](results/figures/MERGED_CORE_CONTEXT.png)

The common core retains a multi-sample rounded crest and positive-side trough. The broad view retains repeated peaks/troughs and a large high-level region around the positive reference flank. Fixed-frame flank levels differ substantially between epochs/frames, affecting normalized heights and RMS. The same y-scales across frames retain those differences. Surrounding correlation describes a structured spectrum rather than an isolated central emission line. No center, width, lag, stellar velocity, continuum, background, drift or selected frame shift was fitted.

## Exact common midpoint and original member geometry

The fixed midpoint is **3881.6137500000004 Å** barycentric air, from exact catalog extrema rather than fitted peaks. The common ±3 Å context is **[3878.6137500000004,3884.6137500000004] Å** and common ±0.25 Å core **[3881.3637500000004,3881.8637500000004] Å**. The 0.01 Å grid retains **601 centers: 51 common-core and 550 surrounding**, with unchanged support gates **41/440**.

The common core **is not the union of original member cores**. Extrema original cores extend approximately **0.00125 Å outside one common edge**. Preserve 3881.6150000000002 separately from 3881.615 and 3881.6125, and retain the exact midpoint float. These are catalog/computational inputs rather than accuracy claims. Original core bounds remain exact in the plan; intervals displayed here are rounded to six decimals.

| Member | Exact original center (Å) | Original member core, displayed (Å) | Barycentric marker offset (Å) | Own discovery topocentric marker offset (Å) |
|---|---:|---|---:|---:|
{chr(10).join(markers)}

The first-queue 0115 discovery observed **January 21 2022**, BERV **29.658729150824 km/s**, fixes one common coordinate anchor **3881.2297765555622 Å** topocentric air through `group_midpoint/(1+BERV/c)`. This rule does not select a preferred comparison reference. All five markers use their own exact centers/discovery BERVs, with coincident identities preserved. No marker follows a fitted peak and no common-core result claims whole original-core containment or physical linewidth.

The own-target BERV span is **59.073251754930496 km/s**. These group-midpoint coordinates were computed from metadata before observed values were read, assuming barycentric coherence. They are predictions rather than measured peak locations.

| Observation | Cohort role | Predicted common-midpoint offset (Å) | Fixed common ±0.25 Å core |
|---|---|---:|---|
{chr(10).join(locrows)}

**Four of the seven predicted common centers are outside the fixed topocentric core on the positive side**: May 5 2022, March 22 2023, May 15 2023 and July 1 2023. The largest offset is +0.760325116 Å. Three centers remain inside. By contrast, **only two of the five discovery markers are outside**: May 5 2022 and May 15 2023; March/July are not reference markers. Distinguish seven center predictions from five member markers. Center flags do not establish full finite-width feature coverage. The window is never recentered and may sample neighboring structure. BERV span supplies geometry, not calibrated origin discrimination. [Prospective geometry and assumptions](../scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json).

## Full support, valid references and signed outcomes

All **34 profiles have 601 finite raw and normalized grid values**, valid positive two-flank medians and **34 false low-reference flags**. All 180 comparisons use complete 51-point common-core or 550-point surrounding support. There are zero gap/outside-coverage masks. Every profile has **zero positive finite ERR samples**.

**Six profile rows contain nonpositive original source samples, all in native order 4 and all within their left flank.** The other 28 profiles have zero nonpositive window/flank fractions, as do all right flanks. Signed values remain unchanged without clipping or sign flips. Counts concern original sources rather than the 601-point interpolated grid:

| Observation | Frame | Native order | Window nonpositive/finite | Left flank nonpositive/finite | Right flank nonpositive/finite |
|---|---|---:|---:|---:|---:|
{chr(10).join(signed)}

May 5 2022 topocentric/order 4 retains **10/500 window samples and 10/123 left-flank samples**; May 15 2023 topocentric/order 4 retains **5/500 and 5/123**. Their pooled references remain positive and valid and their low flags remain false. For May 5 the reference is **57.970993** with proxy **17.764269**, close to but still above the frozen three-proxy threshold. A false flag is not a formal SNR or general quality certificate.

Each table cell below retains barycentric/topocentric values. `L,R` denotes finite original flank counts. Merged quantities use ADU. Native BUNIT is absent in all five products, so native extracted units remain unspecified and distinct from merged units.

| Source / observation | Finite original window B/T | Finite flanks L,R B/T | Pooled reference B/T | First-difference proxy B/T |
|---|---:|---|---:|---:|
{chr(10).join(quality)}

All merged sources have 600 finite window samples and 150 per flank. Native counts vary by order/frame, with full 601-point grid support retained. These source/interpolation counts are distinct. The May native order-4 topocentric references are substantially below their barycentric levels; all fixed spectral structure remains in the pooled medians, without masks, moved flanks or fitted replacements. They are descriptive levels rather than established line-free continua. Positive scalar division leaves Pearson unchanged while normalized heights/RMS depend on those levels. ERR support/proxies do not establish formal uncertainty, false-alarm probability, sensitivity or a qualified survey null.

## Both native orders and their scaled differences

Fresh scans of **360 order headers** select orders **3 and 4** in every discovery, with full common window/core/flank geometry in all twenty source/frame contexts. No C018 order-2 missing-flank outcome is transferred. Every source compares only with its own same-exposure merged product:

| Native event/order | Common-core raw r B/T | Surrounding raw r B/T | Common-core RMS B/T | Surrounding RMS B/T |
|---|---:|---:|---:|---:|
{chr(10).join(native)}

{native_links}

All ten native contexts remain in three pages. Central structure recurs, but **order-dependent broad scaled differences are substantial**, particularly the high positive-side plateau in order 4. May 5 and May 15 topocentric/order-4 broad RMS are **1.131556 and 1.089980**, despite raw r **0.910748 and 0.913056**, respectively. Correlation and scaled mismatch describe different features of these fixed profiles; neither is hidden or fitted away. Shared exposure/extraction lineage makes native/merged similarity dependent evidence, not another observation, a physical flux ratio or validation of physical origin. No unmeasured instrumental cause is assigned to the differences.

## Complete original raw panels and 0129's absent later stage

{raw_links}

All ten exact original raw/excess pairs retain their saved index extents and complete separate scales. Many show extended central patches/vertical trace structure, with noisier order 4 and retained edge structure. **0135/order 3 has a remote high-left deposit that dominates its full scale**, making the central diffuse feature faint. That deposit does not classify the central feature. No new crop, contrast variant, registration, subtraction, background model, pixel statistic or origin assignment was introduced.

**0129 retains its exact original 21×25 five-array containers**, distinct from the four batch03 members' 31×33 panels. It is a separate event from C018/0128. All five C019 original primary/secondary/adopted reviews remain **U/U/U**. All original global/local/baseline mapping stages are true in orders 3/4.

Four batch03 events explicitly retain later-five-window support true. **0129 has no such later field and was not selected in the later follow-up: its later entries remain null/unassessed**, not false and not inferred true. Do not transfer C018/0128's I/M-normalized-I/baseline-I history, original order-2 failures or later wider diagnosis to 0129. The separate completed mapping diagnosis is not replayed. Mapping support, morphology, normalization quality and physical origin remain distinct; no record is promoted or qualified as a laser candidate. [Exact original review/mapping custody](../inputs/INPUT_INVENTORY.json).

## Dependence, verification and continuation

C019 reuses seven target observations and some native products from C018. Their bounded spectral windows are disjoint, while original epoch/profile/raw evidence already existed. **Bounded spectral disjointness does not establish independence of observations or complete raw crops.** C005's numerical overlap uses another target's observing products and shares no source pixels. No blind, untouched, independent-data, new observing-time or archive-wide completeness claim follows. All prior outputs, classifications and completed normalization/mapping diagnoses remain immutable and are not replayed.

The [independent actual arithmetic audit](../independent_audit/NUMERICAL_AUDIT.json) passes **{A['checks_passed']} checks across {A['scalar_values_compared']:,} scalar values**, reconstructing all 17 source windows, 34 profiles, 180 comparisons, ten byte-identical raw copies and 20 self rows without importing production functions. Source flux, ERR, indices and profile metrics agree exactly. Maximum source-wavelength difference is **{D['input_source_wavelength']:.3e} Å**, raw interpolation difference **{D['profile_signed_raw_flux']:.3e} native units**, normalized difference **{D['profile_normalized_flux']:.3e}**, and comparison difference **{D['comparison']:.3e}**. Wavelengths/interpolation are not bitwise identical; computational agreement does not establish origin.

The exact method was public and read back before execution in commit `{release['publication_commit']}`. [Plan](PLAN.json), [root release](ROOT_RELEASE.json), [summary](results/SUMMARY.json), [bounded inputs](results/BOUNDED_INPUT_INDEX.json), [profile metrics](results/PROFILE_METRICS.csv), [comparisons](results/COMPARISONS.csv) and [numeric hashes](results/OUTPUT_HASHES.json) bind the run. **All eight figures were visually inspected and fully decoded**, with hashes/sizes, three native pages, three raw pages and complete source ordering checked against [PLOT_INDEX.json](results/PLOT_INDEX.json). All **89 source bindings and 71 numerical files** remain unchanged. [RESULTS_QA.json](RESULTS_QA.json) records delivery checks.

The next unfinished original-queue route is **C021 / R022, JOINT_PROFILE_CONTEXT on HD114783**, retaining all five original members:

| Queue row | Record | Fixed discovery product | Exact catalog center (Å) | Current code |
|---|---|---|---:|---|
{chr(10).join(nextrows)}

C021 requires separately frozen common geometry/anchor, all five references, exact member floats/cores and fresh order-19 scope; no current quality/reference level is transferred. **0130 has original primary I, secondary M (normalized I), adopted baseline I, then completed unchanged-coordinate wider support and later U/U/current U.** Do not transfer current 0129's original all-U/true mapping or absent later fields to that distinct event. The four other original C021 members retain U/U/U. Preserve failed original stages separately from later support and do not replay completed follow-up. [Next queue metadata and staged histories](../scientific_review/NEXT_GROUP_METADATA.json) retain these dependencies. No C021 array analysis or replay of completed diagnostics was executed here.
'''
(HERE/'RESULTS_REPORT.md').write_text(report);print('Wrote C019 report:',len(report.encode()),'bytes')
