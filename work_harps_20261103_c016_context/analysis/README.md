# Fixed C016 joint spectral context

This prospective method follows the first unfinished original queue route at **row 27**, retaining the whole **C016 / R017 JOINT_PROFILE_CONTEXT** group on **HD114386**. Primary, secondary and adopted reviews remain **U/U/U for all four records**. The completed NORMALIZATION_CONTEXT routes for C013/0092 (row 26) and C014/0104 (row 31) stay complete and are skipped; unresolved origin does not justify replaying a completed diagnostic.

| Record | Original queue row | Exact catalog center (barycentric air Å) | Fixed discovery product | Observation (UTC) |
|---|---:|---:|---|---|
| V2E2-0094 | 27 | 4303.785 | ADP.2022-03-08T01:01:37.348 | 2022-03-07 |
| V2E2-0096 | 29 | 4303.785 | ADP.2022-05-17T01:02:16.724 | 2022-05-16 |
| V2E2-0098 | 30 | 4303.785 | ADP.2023-01-03T01:08:17.803 | 2023-01-02 |
| V2E2-0110 | 32 | 4303.79 | ADP.2023-08-29T01:02:07.487 | 2023-08-27 |

Use **HD114386's own seven existing January 2022–August 2023 observations**, not HD112410's cohort, reference, anchor, native orders or quality outcomes. All four distinct discovery products remain fixed comparison references. Original C016 epoch/profile/raw evidence already exists. These observations also supplied a completed normalization study at other blue wavelengths. No new acquisition, observing time, blind/untouched evidence or independent-data validation is claimed.

[PLAN.json](PLAN.json), [the exact inventory](../inputs/INPUT_INVENTORY.json) and [synthetic checks](SYNTHETIC_PREFLIGHT.json) bind the method before observed arrays are read. The new bounded window is numerically disjoint from completed C001–C012 group windows; those belong to other targets. Prior same-target evidence remains acknowledged.

## Common geometry and exact member coordinates

Set **`cb=4303.7875 Å`**, the midpoint of the minimum/maximum original catalog centers, rather than a fitted peak. The common ±3 Å context is **[4300.7875,4306.7875] Å** and common ±0.25 Å comparison core **[4303.5375,4304.0375] Å**. The `arange(-300,301)/100` grid has **601 centers**: **51 common-core centers** and **550 surrounding centers**.

The common core is **not the union of the original member cores**. Each 4303.785-centered original core is [4303.535,4304.035] Å and extends **0.0025 Å below** the common core. The 4303.79-centered original core is [4303.54,4304.04] Å and extends **0.0025 Å above** it. Exact member centers/core bounds remain in the plan. The three first-member barycentric markers coincide at approximately −0.0025 Å relative to the midpoint; 0110 is at +0.0025 Å. No boundary is expanded, and common-core comparisons are not described as covering every complete original member core or measuring a physical linewidth.

Use `c=299792.458 km/s`. The **first member in original queue order**, 0094 observed on **2022-03-07**, has BERV **19.1606928163471 km/s** and fixes one group topocentric-air anchor:

`ct=cb/(1+19.1606928163471/c)=4303.512448784194 Å`.

This coordinate-anchor rule does not choose a preferred comparison reference. Barycentric profiles query `cb+x`; fixed topocentric profiles query barycentric wavelengths `(ct+x)*(1+BERV_epoch/c)`. Native topocentric-air wavelengths use the unchanged zero-based polynomial on pixels 0..4095, multiplied by `(1+BERV_epoch/c)` once. Each event's discovery marker is its **own exact catalog center divided by its own discovery BERV factor**, relative to the common anchor. Retain all four marker identities and coordinates, including markers outside the common core in the broad view and metadata. No marker is replaced with a fitted peak.

The seven own-target epochs span **51.572001697156 km/s** in BERV. This supplies coordinate separation rather than calibrated origin discrimination. A coherent catalog feature can leave the fixed topocentric core and neighboring structure can enter its comparison. No center, width, lag, RV, continuum, background, drift or alignment is fitted.

## All references, slots and dependence

| Output family | Fixed accounting |
|---|---:|
| Seven merged epochs × two frames | 14 profiles |
| Four discovery/order 19 contexts × two frames | 8 profiles |
| Seven epochs × four fixed references × two frames × two regions | 112 merged comparisons |
| Four native contexts × own same-exposure merged × two frames × two regions | 16 native comparisons |
| Identical-product self rows included above | 16 |
| Exact historical raw cutout/excess pairs retained | 4 |
| Compact pre-interpolation source windows | 11 |

There are **22 profile slots and 128 comparison slots**. Every missing, insufficient, nonpositive, low or invalid result keeps its slot and reason. The merged loop uses all four references. Native profiles compare only with their **own same-exposure merged product**, rather than all four references.

For each reference, six other epochs contribute nonself rows per frame and region. Across four references there are 24 such ordered rows per frame/region, **reusing seven observations rather than supplying 24 independent epochs**. Cross-discovery A→B and B→A rows are reciprocal and dependent. Retain source/reference identities, `same_exposure` and `identical_product_self_pair` flags. Report each reference's six nonself comparisons without selecting a favorable reference or interpreting aggregate rows as additional observing evidence. Native/merged products also share exposure and extraction lineage; their agreement is dependent evidence, not another observation or a physical flux ratio.

## Fresh native scope and historical mapping

A fresh scan of **all 72 order headers for each of four discoveries (288 header rows)** confirms **order 19 alone** covering every exact original feature coordinate. Each selected order covers the full common ±3 Å context, common core and both reference flanks in both frames: **601 grid centers, 51 core and 550 surrounding**. Exact product-specific endpoints and geometry are bound in the inventory and plan. Historical native feature coordinates remain event-specific; they are not replaced by the common group anchor. Coordinate coverage does not establish finite flux, positive references, false low flags or usable comparisons. No previous target's native orders or quality outcomes are transferred.

All four original **order 19** contexts retain true **global-grid, original local usable, original baseline verified and later five-window support**. These historical stages remain separate from flux quality and physical origin. The separate 0092 raw-window registration discrepancy stays with its own other-wavelength evidence and is not transferred to C016.

Historical reviews describe broad rounded native structure, neighboring shoulders and weak diffuse trace-associated raw excess. Exact texts, saved pixels and qualifications remain preserved. No shape, correlation, structured flank or mapping flag changes any **U/U/U**, identifies origin or qualifies a laser candidate.

## Signed reference rule and comparisons

Merged flux retains uncalibrated ADU units. BUNIT is absent in all four freshly inventoried native products, so native extracted units remain unspecified. Signed flux is never clipped or sign-flipped. Only source slices required by the union of both fixed-frame windows, plus interpolation brackets, are copied. Full merged coordinates locate those slices and native coordinates derive from recorded headers.

Sampling, normalization and comparison functions remain unchanged from C011. Per profile/frame, the reference is the pooled signed median of original source samples at **1.5 ≤ |offset| ≤ 3 Å**, requiring **at least 20 finite samples in each flank and a strictly positive pooled median**. Preserve geometric/native/finite counts, separate medians and nonpositive fractions, available versus valid references, ERR support and failure reasons. All fixed-flank structure remains; these medians are descriptive levels rather than established line-free continua.

The first-difference proxy is `1.4826 × MAD / sqrt(2)` from finite adjacent source samples in the same flank without a large wavelength gap. The low-reference rule `reference ≤ 3 × proxy` applies only to valid normalization and is not formal SNR. Missing, insufficient or nonpositive references remain raw-only with null low flags; valid but low references retain true flags. No moved flank, smaller window or fitted replacement is introduced.

Raw Pearson requires nonzero exact range and at least **41/51 common-core or 440/550 surrounding common finite grid values**. Normalized RMS uses the same gate with valid references. An adequately covered raw-only profile may retain raw Pearson. Linear interpolation masks brackets above 1.51 times the full-source median wavelength step and never extrapolates. Interpolated samples, self rows and repeated reference pairs remain dependent. ERR support and descriptive proxies do not establish calibrated significance, sensitivity, false alarms or a qualified survey null.

## Release, complete figures and preservation

All seven merged headers and four native headers are checked before new flux access: exact identity/hash/metadata, numeric BERV, merged barycentric-air Angstrom/ADU and unique WAVE/FLUX/ERR single-exposure tables, native shape and polynomial coefficients. The runner has no network code, checks frozen sources/release hashes before and after execution and refuses to overwrite a result directory.

Eleven compact source NPZs retain exact indices, original-frame and barycentric wavelengths, signed flux, ERR (NaN where native errors are unavailable), BERV, hashes and full-source spacing. All four original event-specific raw/native NPZs are copied byte for byte. Their saved cutout/excess maps are displayed unchanged, without new registration, subtraction, detector modeling, pixel statistics or origin assignment.

Four fixed figures retain **all seven merged broad/core profiles, all four discovery-native contexts and all four original raw/excess pairs**. Legends preserve all four reference IDs and catalog/discovery markers; three coincident barycentric markers are explicitly identified. Keep raw-only reasons and any low-reference outcome visible. Merged scales match across frames per quantity/window; native raw scales match across frames per source. Every finite value remains with a 5% margin. Raw images use separate full extrema. No smoothing, clipping, favorable reference/epoch choice or contrast variant is introduced.

After root publishes and reads back the exact method, execute once:

```bash
python work_harps_20261103_c016_context/analysis/compare_group.py
python work_harps_20261103_c016_context/analysis/plot_group.py
```

`ROOT_RELEASE.json` must use `HARPS_C016_GROUP_RELEASE_V1` and bind verified public readback plus plan, runner and inventory hashes. All prior science outputs and classifications remain immutable.
