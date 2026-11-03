# Fixed C021 joint spectral context

This prospective method follows original queue **row 35**, retaining the whole **C021 / R022 JOINT_PROFILE_CONTEXT** group on **HD114783**. All five current labels remain **U**. Four batch03 members originally retain U/U/U, while 0130's distinct original and later review stages remain separate below. Completed groups and mapping/normalization diagnoses are not replayed.

| Record | Queue row | Exact original catalog center (barycentric air Å) | Fixed discovery product |
|---|---:|---:|---|
| V2E2-0116 | 35 | 4309.827499999999 | ADP.2022-01-22T01:09:14.958 |
| V2E2-0121 | 40 | 4309.827499999999 | ADP.2022-02-06T01:07:28.382 |
| V2E2-0126 | 44 | 4309.825 | ADP.2022-05-06T01:04:00.123 |
| V2E2-0130 | 48 | 4309.825 | ADP.2023-01-17T01:07:48.581 |
| V2E2-0139 | 55 | 4309.827499999999 | ADP.2023-07-02T01:01:43.311 |

Use the **same seven existing HD114783 January 2022–July 2023 observations**, with these **five fixed references**. **July 1 replaces C019's May 15 reference**; March 22 and May 15 stay in the cohort without becoming C021 discovery references. Equal comparison counts do not permit transferring the previous reference identities. Reused products and original C021 epoch/profile/raw evidence remain dependent prior evidence. No new acquisition, observing time, blind/untouched evidence or independent-data validation is claimed.

The common spectral window is disjoint from same-target C018/C019 blue windows. The other-target C016 window is disjoint by 0.03875 Å; numerical overlaps with C006/C007 belong to HD106515A and share no observing products/pixels. Bounded spectral disjointness does not prove independence of observations or entire saved raw crops. [PLAN.json](PLAN.json), [fresh inputs](../inputs/INPUT_INVENTORY.json) and [synthetic checks](SYNTHETIC_PREFLIGHT.json) bind the method before observed arrays are read.

## Fixed common geometry and exact original members

Set **`cb=4309.82625 Å`**, the exact catalog-extrema midpoint rather than a fitted peak. The common ±3 Å context is **[4306.82625,4312.82625] Å** and common ±0.25 Å metric core **[4309.57625,4310.07625] Å**. The `arange(-300,301)/100` grid has **601 centers: 51 common-core and 550 surrounding centers**.

The common core **is not the union of original member cores**. Exact original centers retain their own ±0.25 Å intervals and markers in the plan; extrema original cores extend approximately **0.00125 Å outside one common edge**. Preserve 4309.827499999999 separately from 4309.825 and the exact midpoint float. No boundary is expanded, and common-core comparisons are not described as covering every complete original member core or measuring physical linewidth. Exact catalog floats are computational inputs rather than accuracy claims.

With `c=299792.458 km/s`, the **first original-queue discovery**, 0116 observed **2022-01-21**, has BERV **29.658729150824 km/s** and fixes one common coordinate anchor:

`ct=cb/(1+29.658729150824/c)=4309.39991731037 Å` topocentric air.

This coordinate rule does not select a preferred comparison reference. Barycentric profiles query `cb+x`; fixed topocentric profiles query barycentric wavelengths `(ct+x)*(1+BERV_epoch/c)`. Native topocentric-air coordinates use unchanged zero-based polynomials on pixels 0..4095, multiplied by `(1+BERV_epoch/c)` once. All five markers use their own exact member centers and discovery BERVs relative to the common anchor. Coincident identities remain separate; out-of-core markers remain explicit in the broad view, legends and metadata. No fitted peak replaces a marker.

The own-target BERV span is **59.073251754930496 km/s**. It provides coordinate separation rather than calibrated origin discrimination. A coherent center may leave the fixed topocentric core and neighboring structure may enter its comparison. No center, width, lag, RV, continuum, background, drift or alignment is fitted.

## Complete scope and reference dependence

| Output family | Fixed accounting |
|---|---:|
| Seven merged epochs × two frames | 14 profiles |
| Five discovery/order 19 contexts × two frames | 10 native profiles |
| Seven epochs × five references × two frames × two regions | 140 merged comparisons |
| Five native contexts × own same-exposure merged × two frames × two regions | 20 native comparisons |
| Identical-product self rows included above | 20 |
| Exact original raw cutout/excess pairs retained | 5 |
| Compact pre-interpolation source windows | 12 |

There are **24 profile slots and 160 comparison slots**. Every missing, insufficient, nonpositive, low or invalid outcome keeps its slot and reason. Merged profiles compare with all five fixed references; native profiles compare only with their own same-exposure merged product.

Each reference has six other epochs. The **30 directed nonself rows per frame/region represent 20 unordered exposure pairs and 10 reciprocal reference-pair duplicates**, using only seven observations rather than adding 30 independent epochs. Retain source/reference identities, `same_exposure` and `identical_product_self_pair` flags. Report each reference's complete six-epoch family without favorable selection. Native/merged agreement shares exposure/extraction lineage and is dependent evidence rather than another observation or physical flux ratio.

## Fresh geometry and unassessed quality

A fresh scan of **all 72 order headers in five native products (360 rows)** confirms **order 19 alone** covering each exact original event coordinate. All ten source/frame contexts geometrically cover the full common window/core and both reference flanks: **601 total, 51 core and 550 surrounding grid positions**. Exact product-specific endpoints and both-frame geometry are bound in the inventory and plan.

Coordinate coverage does not establish finite observed flux, positive references, false low flags or usable statistics. All quality outcomes remain runtime checks. Do not transfer blue-window native orders, missing-flank counts or signed/reference outcomes. Preserve any actual invalid/partial result and never borrow a flank or value from another source.

## Mixed original stages and 0130's distinct history

| Event | Original global | Original local | Original baseline | Later five-window support |
|---|---|---|---|---|
| 0116 | true | false | false | true |
| 0121 | true | true | true | true |
| 0126 | true | false | false | true |
| 0130 | true | false | false | true |
| 0139 | true | true | true | true |

Original baseline provenance stays explicit: batch03 stores `baseline_mapping_verified`; older 0130 uses original `mapping_verified`. Later support does not rewrite the **three failed original local/baseline stages** or establish physical origin. No current C019/0129 null stage is transferred here.

**Four original batch03 review chains retain U/U/U. 0130 originally has primary I, secondary M (normalized I), and adopted baseline I**, for insufficient original local raw mapping. A completed wider five-window diagnosis and separate later visual reviews at unchanged coordinates/pixels retain **U/U/current U**. Preserve all exact texts, sources and stage qualifications. Do not collapse the stages into blanket original-U reviews, infer new raw evidence or replay the completed follow-up.

0130 keeps its exact **original 21×25 five-array container**, distinct from the four batch03 members' **31×33** panels. Later wider containers do not replace originals. Each saved index extent and complete separate scale remains unchanged. Mapping-supported morphology and frame agreement do not qualify a laser candidate or identify a physical origin.

## Signed references and comparison rules

Merged flux retains uncalibrated ADU units. Native extracted units remain unspecified when BUNIT is absent in the fresh inventory. Signed values are never clipped or sign-flipped. Only source slices required by the union of both fixed-frame windows plus interpolation brackets are copied; full merged coordinates locate slices and native coordinates derive from recorded headers.

Sampling, normalization and comparison functions remain unchanged from the proven preceding methods. Per profile/frame, use the pooled signed median of original source samples at **1.5 ≤ |offset| ≤ 3 Å**, requiring **at least 20 finite samples in each flank and a strictly positive pooled median**. Retain geometric/native/finite counts, separate medians/nonpositive fractions, available versus valid levels, ERR support and failure reasons. All fixed-flank structure remains; levels are descriptive rather than established line-free continua.

The first-difference proxy is `1.4826 × MAD / sqrt(2)` from finite adjacent source samples in the same flank without a large wavelength gap. The low-reference rule `reference ≤ 3×proxy` applies only to valid normalization and is not formal SNR. Missing, insufficient or nonpositive references remain raw-only with null low flags; valid but low references retain true flags. No moved flank, smaller window or fitted replacement is introduced.

Raw Pearson requires nonzero exact range and **41/51 common-core or 440/550 surrounding common finite grid samples**. Normalized RMS uses the same gates with valid references. Adequately covered raw-only profiles may retain raw Pearson. Linear interpolation masks brackets above 1.51 times the full-source median step and never extrapolates. Interpolation, self rows, reciprocal references and shared extraction remain dependent. ERR support/proxies do not establish significance, false alarms, sensitivity or a qualified survey null.

The next selected C022 original core lies inside this common positive reference flank, and the current C021 core lies in its future negative flank. The fixed structure is retained without masks or retuning; subsequent overlap on the same observing products will be previously viewed, dependent context rather than untouched validation. The future metadata was selected before current values.

## Release, six complete figures and preservation

All seven merged and five native headers are checked before new flux access: exact identity/hash/metadata, numeric BERV, merged barycentric-air Angstrom/ADU and unique WAVE/FLUX/ERR single-exposure tables, native shape and polynomial coefficients. The runner has no network code, checks frozen sources/release hashes before and after execution and refuses to overwrite a result directory.

Twelve compact source NPZs retain exact indices, original-frame/barycentric wavelengths, signed flux, ERR (NaN where native errors are unavailable), BERV, source hashes and full-source spacing. All five exact original raw/native NPZs are copied byte for byte, including 0130's original smaller container.

| Figure family | Complete fixed coverage |
|---|---|
| Merged broad/core | Two figures, all seven epochs and five exact member/discovery marker identities |
| Native pages 1–2 | Five contexts, four rows on page one, one on page two |
| Original raw pages 1–2 | Five raw/excess pairs, four rows on page one, one on page two |

All **six figures** and exact pagination/source ordering are bound in the plan. Retain every outcome without favorable selection. Keep raw-only reasons and low-reference flags visible if present. Merged scales match across frames per quantity/window; native raw scales match across frames per source. Every finite value retains a 5% margin. Raw images use separate full extrema and unchanged historical subtraction. No smoothing, clipping, new crop, contrast variant, registration, subtraction, detector model, pixel statistic or origin assignment is introduced.

After root publishes and reads back the exact method, execute once:

```bash
python work_harps_20261103_c021_context/analysis/compare_group.py
python work_harps_20261103_c021_context/analysis/plot_group.py
```

`ROOT_RELEASE.json` must use `HARPS_C021_GROUP_RELEASE_V1` and bind verified public readback plus plan, runner and inventory hashes. All earlier outputs and classifications remain immutable.
