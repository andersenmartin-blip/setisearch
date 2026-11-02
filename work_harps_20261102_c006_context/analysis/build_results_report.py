#!/usr/bin/env python3
"""Summarize all frozen outputs; no new fitting or measurements."""
from pathlib import Path
import json,statistics
HERE=Path(__file__).resolve().parent;OUT=HERE/'results'
read=lambda p:json.loads(p.read_text())
P=read(HERE/'PLAN.json');R=read(OUT/'PROFILE_METRICS.json');C=read(OUT/'COMPARISONS.json');S=read(OUT/'SUMMARY.json');A=read(HERE.parent/'independent_audit/NUMERICAL_AUDIT.json')
labels={P['discovery_dp_ids'][0]:'0025 (2022-01-05)',P['discovery_dp_ids'][1]:'0042/0043 (2022-12-31)'}
def span(v):return f'{min(v):.6f}–{max(v):.6f}'
def pair(v):return ' / '.join(f'{x:.6f}'for x in v)
rows=[]
for dp in P['discovery_dp_ids']:
 for region,title in [('core','Core'),('broad_pattern','Surroundings')]:
  metrics=[]
  for key in ['raw_pearson','normalized_rms']:
   for frame in ['barycentric','topocentric']:
    v=[r[key]for r in C if r['relationship']=='MERGED_EPOCH_TO_DISCOVERY'and r['reference_dp_id']==dp and not r['identical_product_self_pair']and r['region']==region and r['frame']==frame]
    metrics.append(span(v))
  rows.append('| '+labels[dp]+' | '+title+' | '+' | '.join(metrics)+' |')
ref_table='\n'.join(rows)
native_quality=[];native_match=[]
for dp in P['discovery_dp_ids']:
 r=[next(r for r in R if r['kind']=='native'and r['dp_id']==dp and r['frame']==f)for f in ['barycentric','topocentric']]
 native_quality.append('| '+labels[dp]+' | '+' / '.join(f"{x['flank_reference']:.3f}"for x in r)+' | '+' / '.join(f"{x['first_difference_noise_proxy']:.3f}"for x in r)+' | 0 / 0 | false / false |')
 v=[]
 for key in ['raw_pearson','normalized_rms']:
  for reg in ['core','broad_pattern']:
   v.append(pair([next(r[key]for r in C if r['relationship']=='SAME_EPOCH_NATIVE_TO_MERGED'and r['dp_id']==dp and r['frame']==f and r['region']==reg)for f in ['barycentric','topocentric']]))
 native_match.append('| '+labels[dp]+' | '+' | '.join(v)+' |')
report=f'''# C006: HD106515A joint spectral context

The two crests in the C006 core and the surrounding structured spectrum recur closely in barycentric coordinates across the seven existing cohort epochs. Both native order 19 extractions closely reproduce their same-exposure merged products. **All three records, V2E2-0025, 0042 and 0043, remain U.** This is descriptive spectral context, not a physical-origin identification, qualified laser candidate or calibrated null.

The single released execution completed on **2026-11-02 at 17:14:02 UTC** with **18 profiles, 64 comparisons and eight included identical-product self-comparisons**. All slots are measured, with no blocked sources, raw-only normalization or structural exclusions. There are only **two distinct discovery products**: 0042 and 0043 share the observation on 2022-12-31. Their event identities and all three raw panels remain separate, but their product reference/native profile is counted once. The same seven exposures were used at other wavelengths in C003/C005; no acquisition, new observing time or archive-wide completeness is claimed.

## Both references, all epochs and coordinate limits

The common barycentric air-wavelength center is **4310.455 Å**, and the fixed first-discovery topocentric anchor is **4310.021714958131 Å**. The three catalog centers are 4310.585 Å (0025/R007), 4310.305 Å (0042/R006) and 4310.605 Å (0043/R007). Their original ±0.25 Å cores form one connected union ±0.400 Å around the midpoint. The fixed ±3 Å grid contains 601 centers: **81 core and 520 surrounding centers**. Minimum common support is 65 and 416, respectively. No width, shift, center, stellar velocity, background or continuum was fitted.

The table retains each unique discovery reference separately and reports minimum–maximum over its six nonself epoch comparisons. B/T denotes barycentric/topocentric. Eight identical-product self rows remain in the detailed output at r = 1 and normalized RMS = 0. Reversed discovery pairs and reused epoch profiles are dependent, and one joint-window correlation is not separate evidence for each catalog feature.

| Reference | Region | Raw r B range | Raw r T range | Normalized RMS B range | Normalized RMS T range |
|---|---|---:|---:|---:|---:|
{ref_table}

Across both references, nonself barycentric core r spans **0.960276–0.996426**, and surrounding r **0.973347–0.997366**. The 0025 reference has lower agreement than the 0042/0043 reference with the remaining epochs; both are retained. The broader plot shows repeated crests and troughs throughout the window, rather than an isolated narrow feature. The close-up preserves the two neighboring crests corresponding to the distinct R006/R007 neighborhoods.

The near-BERV discovery pair is an explicit exception to a universal frame ranking: **core r = 0.960276 B versus 0.978027 T**, and **surrounding r = 0.976356 B versus 0.985120 T**. Their BERV values differ by only about 0.237 km/s. The other five epochs supply the wider total 59.6098131157401 km/s span. Neither the span nor a correlation difference is a calibrated origin test.

**The topocentric core is a fixed coordinate window, not the recentered core of each later feature.** Metadata conversion places the group midpoint outside ±0.400 Å for three epochs (May 2022, May 2023 and July 2023). Individual 0025/0043 catalog centers already lie outside that fixed core in March 2022 and March 2023; the 0042 center remains inside on those two dates. All three centers lie outside on the three May/July dates. These are predicted coordinate positions, not fitted peaks. The [prospective scientific review](../scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json) preserves every predicted offset.

All **18 profiles** have complete 601-point raw and normalized support, valid positive flank references, false low-reference flags, zero nonpositive source-window fractions and **zero finite positive ERR samples**. Merged references range from **694.962 to 2282.642 ADU**, with descriptive first-difference proxies **38.051–106.141 ADU**. These are not formal uncertainties or SNRs.

The two fixed 1.5–3 Å flanks contain spectral structure. In particular, the next C007 catalog center at **4312.700 Å** lies at **+2.245 Å** in the positive flank and remains in the reference median. It is not a line-free continuum. Frame-dependent reference scaling changes relative heights and normalized RMS; positive scalar division does not change Pearson correlation. No alternative flank or normalization was selected.

- [All seven epochs: broad signed and scaled profiles](results/figures/MERGED_BROAD_CONTEXT.png)
- [The same profiles: fixed joint core](results/figures/MERGED_CORE_CONTEXT.png)

Both figures retain all three event markers and both R006/R007 identities. Topocentric markers denote the discovery coordinates of each event, not positions fitted to other epochs.

## Two unique native order contexts

Fresh header scans of all 144 orders in the two discovery products identify order 19 as the only covering order. Both numerical native contexts have complete support in both frames. Their merged counterparts share the same observations and extraction lineage; close agreement is not independent confirmation. Native BUNIT is absent, so native levels have **unspecified extracted units**; merged FLUX is explicitly ADU.

Values separated by `/` are B/T. The low flag is the predeclared reference ≤ 3 × first-difference proxy rule; all flags here are false.

| Discovery identity / order 19 | Flank reference B/T | Noise proxy B/T | Nonpositive % B/T | Low flag B/T |
|---|---:|---:|---:|---|
{chr(10).join(native_quality)}

| Discovery identity / order 19 | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
{chr(10).join(native_match)}

All eight native-to-merged r values lie between **0.999626 and 0.999875**. The normalized native and merged curves closely follow one another throughout the displayed window, with small retained differences. This extraction agreement neither validates a raw-detector mapping nor establishes a physical origin.

[Both unique native order contexts](results/figures/NATIVE_ORDERS_1.png) preserve 0025 separately from the shared 0042/0043 product.

## Historical raw panels and mapping qualifications

[All three event-specific raw cutout/excess pairs](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png) are exact copies of the stored evidence. The panels show central enhancements together with much stronger right-edge structures that dominate the full-value color scales. The stored excess maps retain alternating positive/negative edge lobes. They are spatially distinct from the central feature context; no origin or new detector model is assigned to either. The historical separate off-trace feature for 0042 remains visible and is not conflated with its nominal core.

**0025 retains historical `local_mapping_usable=false` and `baseline_mapping_verified=false`**, despite true global and five-window mapping diagnostics. Fresh order coverage and near-perfect native/merged spectral correlation do not retroactively validate that local detector mapping. All primary, secondary and adopted historical reviews remain preserved. The 0042/0043 panels share one exposure and overlapping pixels; presenting both does not create independent evidence.

The raw-excess background subtraction is historical. No new raw registration, background fit, free-width model or morphology classifier was applied. Missing positive ERR and the descriptive noise proxy preclude formal significance from this diagnostic. No physical flux, line identity, false-alarm probability, completeness or survey null is inferred. All three U labels and all earlier pipelines remain unchanged.

## Numerical reconstruction and delivery checks

Independent reconstruction passed **{A['checks_passed']} checks across {A['scalar_values_compared']:,} scalar values**: nine bounded source windows, all 18 profiles, 64 comparisons and three exact raw copies, without importing production functions. Source flux, ERR, indices and wavelengths were exact. Maximum raw-profile difference was 9.09×10⁻¹³ native units, normalized-profile difference 8.88×10⁻¹⁶ and comparison difference 7.77×10⁻¹⁶. [Independent audit](../independent_audit/NUMERICAL_AUDIT.json).

The exact method was public and read back before execution at commit `e495c9fa6e59af1c3927a0b8a57767556eb30eff`. The [plan](PLAN.json), [release](ROOT_RELEASE.json), [run summary](results/SUMMARY.json), [bounded input index](results/BOUNDED_INPUT_INDEX.json), [all profile metrics](results/PROFILE_METRICS.json), [all comparisons](results/COMPARISONS.json) and [output hashes](results/OUTPUT_HASHES.json) bind the result.

All four figures were visually inspected, including the full core title and seven-epoch legend, and their bytes/hashes and PNG decoding checked against the unchanged [plot index](results/PLOT_INDEX.json). All 43 method/input sources and numerical outputs remain unchanged. [RESULTS_QA.json](RESULTS_QA.json) records these checks. The next original-queue group is C007; its overlap with this window must remain explicit rather than being counted as independent data.
'''
(HERE/'RESULTS_REPORT.md').write_text(report)
print('report',len(report.encode()),'bytes')
