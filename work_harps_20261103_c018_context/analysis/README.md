# Fixed C018 joint spectral context

This prospective method follows original queue **row 33**, retaining the whole **C018 / R019 JOINT_PROFILE_CONTEXT** group on new target **HD114783**. All seven current labels remain **U**, with the distinct original and later histories preserved below. Completed normalization and mapping diagnoses are not replayed because physical origin remains unresolved.

| Record | Queue row | Exact original catalog center (barycentric air Å) | Fixed discovery product |
|---|---:|---:|---|
| V2E2-0114 | 33 | 3869.3349999999996 | ADP.2022-01-22T01:09:14.958 |
| V2E2-0119 | 38 | 3869.3325 | ADP.2022-02-06T01:07:28.382 |
| V2E2-0124 | 42 | 3869.3325 | ADP.2022-05-06T01:04:00.123 |
| V2E2-0128 | 46 | 3869.335 | ADP.2023-01-17T01:07:48.581 |
| V2E2-0133 | 50 | 3869.3349999999996 | ADP.2023-03-23T01:02:04.833 |
| V2E2-0134 | 51 | 3869.3325 | ADP.2023-05-16T01:01:18.574 |
| V2E2-0138 | 54 | 3869.335 | ADP.2023-07-02T01:01:43.311 |

Use **HD114783's own seven existing January 2022–July 2023 observations**. Every observing product is also a fixed discovery reference. Do not transfer HD114386 products, May anchor, singleton design, native scope or quality outcomes. Original C018 epoch/profile/raw evidence and the wider 0128 mapping diagnosis already exist. No new acquisition, observing time, blind/untouched evidence or independent-data validation is claimed. Numeric overlap with C015 and older blue windows belongs to other target observations and shares no source pixels.

[PLAN.json](PLAN.json), [the fresh inventory](../inputs/INPUT_INVENTORY.json) and [synthetic checks](SYNTHETIC_PREFLIGHT.json) bind the method before observed values are read.

## Common geometry and exact member coordinates

Set **`cb=3869.33375 Å`**, the midpoint of the minimum/maximum original catalog centers rather than a fitted peak. The common ±3 Å context is **[3866.33375,3872.33375] Å** and common ±0.25 Å metric core **[3869.08375,3869.58375] Å**. The `arange(-300,301)/100` grid has **601 centers**, comprising **51 common-core and 550 surrounding centers**.

The common core **is not the union of original member cores**. Each exact original member center retains its own ±0.25 Å interval in the plan. The extrema original cores extend approximately **0.00125 Å outside one common edge** (maximum catalog-float offset 0.0012500000002546585 Å). Preserve 3869.3349999999996 separately from 3869.335 and 3869.3325, all seven original core bounds and every marker identity, even when markers visually coincide. No boundary is expanded and common-core comparisons are not described as covering every complete original member core or measuring physical linewidth.

With `c=299792.458 km/s`, the **first original-queue discovery**, 0114 observed **2022-01-21**, has BERV **29.658729150824 km/s** and fixes one common topocentric-air coordinate anchor:

`ct=cb/(1+29.658729150824/c)=3868.9509913064876 Å`.

This coordinate rule does not select a preferred comparison reference. Barycentric profiles query `cb+x`; fixed topocentric profiles query barycentric wavelengths `(ct+x)*(1+BERV_epoch/c)`. Native topocentric-air wavelengths use unchanged zero-based polynomials on pixels 0..4095, multiplied by `(1+BERV_epoch/c)` once. Each exact member/discovery marker uses its own original center and own discovery BERV, relative to the common anchor. Markers outside the common core remain explicit in the broad view, legends and metadata. No fitted peak replaces a marker.

The own-target BERV span is **59.073251754930496 km/s**. This provides coordinate separation rather than calibrated origin discrimination. A coherent center may leave the fixed topocentric common core, allowing neighboring structure into that comparison. No center, width, lag, RV, continuum, background, drift or alignment is fitted.

## All references, complete scope and dependence

| Output family | Fixed accounting |
|---|---:|
| Seven merged epochs × two frames | 14 profiles |
| Seven discoveries × two covering orders × two frames | 28 native profiles |
| Seven epochs × seven fixed references × two frames × two regions | 196 merged comparisons |
| Fourteen native contexts × own same-exposure merged × two frames × two regions | 56 native comparisons |
| Identical-product self rows included above | 28 |
| Original event/order raw cutout/excess pairs retained | 14 |
| Compact pre-interpolation source windows | 21 |

There are **42 profile slots and 252 comparison slots**. Every missing, insufficient, nonpositive, low or invalid outcome keeps its slot and reason. The merged loop uses all seven fixed references; native profiles compare only with their own same-exposure merged product.

Each reference has six other epochs per frame/region. Because **all seven observations are references**, the **42 directed nonself rows per frame/region represent 21 unordered observation pairs and 21 reciprocal duplicates**. They reuse seven observations rather than supplying 42 independent epochs. Retain source/reference identities, `same_exposure` and `identical_product_self_pair` flags. Report every reference's six nonself comparisons without choosing a favorable subset or interpreting repeated rows as additional observing evidence. Native/merged agreement is also dependent extraction evidence, not another observation or a physical flux ratio.

## Fresh native geometry and unassessed flux quality

A fresh scan of all **72 order headers in each of seven native products (504 rows)** verifies **orders 2 and 3** at every exact original member coordinate/BERV. All fourteen contexts cover the entire common core. **Every order 2 misses the entire positive reference flank [1.5,3] Å in both frames**, while covering the negative flank; order 3 covers the full common context and both flanks. Keep all original covering orders, including partial order 2. No missing flank is borrowed from order 3.

| Discovery event | Order 2 barycentric geometric grid positions (all / surroundings) | Order 2 topocentric geometric grid positions (all / surroundings) |
|---|---:|---:|
| 0114 | 406 / 355 | 406 / 355 |
| 0119 | 402 / 351 | 406 / 355 |
| 0124 | 351 / 300 | 406 / 355 |
| 0128 | 406 / 355 | 406 / 355 |
| 0133 | 379 / 328 | 406 / 355 |
| 0134 | 346 / 295 | 406 / 355 |
| 0138 | 330 / 279 | 406 / 355 |

All order-2 common cores have 51 geometric positions, but every surrounding count is below the fixed 440-sample gate. Missing positive-flank coverage prevents valid two-flank normalization. These header/grid counts do not establish finite observed flux or evaluable core Pearson. Every resulting raw-only, insufficient-support, nonpositive or low outcome remains an explicit runtime record. All order-3 geometries have 601 total / 51 core / 550 surrounding positions. Exact endpoints and both-frame geometry are bound in the inventory and plan. No prior target's missing-flank counts or quality values are transferred.

## Historical stages, including 0128

**Six batch03 members originally retain U/U/U. 0128 has a different staged history:** original primary **I**, secondary **M (normalized I)** and adopted baseline **I**, for insufficient original local raw mapping. A later completed five-window reference diagnosis and separate visual reviews at unchanged coordinates/pixels retain **U/U/current U**. Preserve all exact texts, source paths, original pixels and stage qualifications. Do not collapse these into blanket original-U reviews or rewrite failed original stages as true.

For every original **order 2**, global support is true while original local usable and baseline verification are false. Original **order 3** has true original stages. Later five-window support is true for both orders, including 0128's separate completed follow-up. Later support does not retroactively repair original order-2 local/baseline failures. That completed mapping diagnosis is not rerun as new progress.

The historical order-2 remote bright pixel in **0134** is separate from its broad weak central enhancement; the remote deposit does not classify the central feature. Keep all saved pixels and complete scales. Morphology, registration support and current U labels do not establish physical origin or qualify a laser candidate.

## Signed reference rule and comparisons

Merged flux retains uncalibrated ADU units. Native extracted units remain unspecified when BUNIT is absent in the fresh inventory. Signed values are never clipped or sign-flipped. Only source slices needed by the union of both fixed-frame windows plus interpolation brackets are copied. Full merged coordinates locate slices and native coordinates derive from recorded headers.

Sampling, normalization and comparison functions remain unchanged from the proven C016 joint method. For each source/frame, use the pooled signed median of original samples at **1.5 ≤ |offset| ≤ 3 Å**, requiring **at least 20 finite samples in each flank and a strictly positive pooled median**. Keep geometric/native/finite counts, separate medians/nonpositive fractions, available versus valid reference levels, ERR support and failure reasons explicit. Fixed-flank structure remains; medians are descriptive levels rather than established line-free continua.

The first-difference proxy is `1.4826 × MAD / sqrt(2)` from finite adjacent source samples in the same flank without a large wavelength gap. The low-reference rule `reference ≤ 3×proxy` applies only to valid normalization and is not formal SNR. Missing, insufficient or nonpositive references remain raw-only with null low flags; valid but low references retain true flags. No moved flank, smaller window or fitted replacement is introduced.

Raw Pearson needs nonzero exact range and **41/51 common-core or 440/550 surrounding common finite grid samples**. Normalized RMS uses the same gates with valid references. Adequately covered raw-only profiles may retain raw Pearson. Linear interpolation masks brackets above 1.51 times the full-source median wavelength step and never extrapolates. Interpolation, self rows, reciprocal reference pairs and shared extractions remain dependent. ERR support and descriptive proxies do not establish significance, false alarms, sensitivity or a qualified survey null.

## Release, all ten figures and preservation

All seven merged and seven native headers are checked before new flux access: exact identity/hash/metadata, numeric BERV, merged barycentric-air Angstrom/ADU and unique WAVE/FLUX/ERR single-exposure tables, native shape and polynomial coefficients. The runner has no network code, checks all frozen sources/release hashes before and after execution and refuses to overwrite a result directory.

Twenty-one compact source NPZs preserve exact indices, original-frame and barycentric wavelengths, signed flux, ERR (NaN where native unavailable), BERV, source hashes and full-source spacing. All fourteen original event/order NPZs are copied byte for byte. 0128's separate original source archive and completed follow-up metadata remain distinct from the six batch03 sources. Its exact original five-array NPZ containers retain **21×25** raw/excess panels; the six batch03 members retain **31×33** panels. Each panel keeps its own saved index extent and full scale. Later wider containers do not replace 0128's originals.

| Figure family | Complete fixed coverage |
|---|---|
| Merged broad/core | Two figures, all seven epochs and seven member/discovery marker identities |
| Native pages 1–4 | Fourteen native contexts, four source rows per page, last page two rows |
| Preserved raw pages 1–4 | Fourteen raw/excess pairs, four source rows per page, last page two rows |

There are **ten figures**, with exact native/raw page counts and source ordering bound in PLAN.json. No context is dropped or favorably selected. Keep raw-only reasons, low-reference outcomes and missing support visible. Merged scales match across frames per quantity/window; native raw scales match across frames per source. Every finite value remains with a 5% margin. Raw images use separate full extrema and unchanged historical subtraction. No smoothing, clipping, new crop, contrast variant, registration, detector model, subtraction, pixel statistic or origin assignment is introduced.

After root publishes and reads back the exact method, execute once:

```bash
python work_harps_20261103_c018_context/analysis/compare_group.py
python work_harps_20261103_c018_context/analysis/plot_group.py
```

`ROOT_RELEASE.json` must use `HARPS_C018_GROUP_RELEASE_V1` and bind verified public readback plus plan, runner and inventory hashes. All earlier results and classifications remain immutable.
