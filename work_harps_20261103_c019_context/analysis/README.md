# Fixed C019 joint spectral context

This prospective method follows original queue **row 34**, retaining the whole **C019 / R020 JOINT_PROFILE_CONTEXT** group on **HD114783**. All five original primary, secondary and adopted reviews remain **U/U/U**, including the older 0129 evidence. Current labels remain U. Completed C018 members, normalization routes and the separate 0128 mapping diagnosis are not replayed.

| Record | Queue row | Exact original catalog center (barycentric air Å) | Fixed discovery product |
|---|---:|---:|---|
| V2E2-0115 | 34 | 3881.6125 | ADP.2022-01-22T01:09:14.958 |
| V2E2-0120 | 39 | 3881.615 | ADP.2022-02-06T01:07:28.382 |
| V2E2-0125 | 43 | 3881.6150000000002 | ADP.2022-05-06T01:04:00.123 |
| V2E2-0129 | 47 | 3881.615 | ADP.2023-01-17T01:07:48.581 |
| V2E2-0135 | 52 | 3881.6125 | ADP.2023-05-16T01:01:18.574 |

Use the **same seven existing HD114783 January 2022–July 2023 observations**, with these **five fixed references**. March 22 and July 1 2023 stay in the cohort without becoming C019 discovery references. Reused observations/native products and original C019 epoch/profile/raw evidence are dependent prior evidence. No new acquisition, observing time, blind/untouched evidence or independent-data validation is claimed.

C019's bounded wavelength window is disjoint from same-target C018. That does not establish independence of observations or complete historical raw crops. Numerical overlap with older C005 belongs to a different target and shares no observing products or source pixels. [PLAN.json](PLAN.json), [fresh inputs](../inputs/INPUT_INVENTORY.json) and [synthetic checks](SYNTHETIC_PREFLIGHT.json) bind this method before observed arrays are read.

## Common geometry and exact member floats

Set **`cb=3881.6137500000004 Å`**, the exact catalog-extrema midpoint rather than a fitted peak. The common ±3 Å context is **[3878.6137500000004,3884.6137500000004] Å** and common ±0.25 Å comparison core **[3881.3637500000004,3881.8637500000004] Å**. The `arange(-300,301)/100` grid has **601 centers: 51 common-core and 550 surrounding centers**.

The common core **is not the union of original member cores**. Each original center retains its exact ±0.25 Å bounds and marker in the plan; extrema original cores extend approximately **0.00125 Å outside one common edge**. Preserve 3881.6150000000002 separately from 3881.615 and 3881.6125, and retain the midpoint's exact original float. No boundary is expanded, and common-core results are not described as covering every complete original member core or measuring physical linewidth. Exact catalog floats are computational inputs rather than wavelength-accuracy claims.

With `c=299792.458 km/s`, the **first original-queue discovery**, 0115 observed **2022-01-21**, has BERV **29.658729150824 km/s** and fixes one common coordinate anchor:

`ct=cb/(1+29.658729150824/c)=3881.2297765555622 Å` topocentric air.

This anchor does not select a preferred comparison reference. Barycentric profiles query `cb+x`; fixed topocentric profiles query barycentric wavelengths `(ct+x)*(1+BERV_epoch/c)`. Native topocentric-air coordinates use unchanged zero-based polynomials on pixels 0..4095, multiplied by `(1+BERV_epoch/c)` once. All five exact event/discovery markers use their own original centers and discovery BERVs relative to the common anchor. Coincident markers retain separate IDs; out-of-core markers remain in the broad view, legends and metadata. No fitted peak replaces a marker.

The own-target BERV span is **59.073251754930496 km/s**. This supplies coordinate separation rather than calibrated origin discrimination. A coherent center may leave the fixed common topocentric core and neighboring structure may enter its comparison. No center, width, lag, RV, continuum, background, drift or alignment is fitted.

## All references and dependence

| Output family | Fixed accounting |
|---|---:|
| Seven merged epochs × two frames | 14 profiles |
| Five discoveries × orders 3/4 × two frames | 20 native profiles |
| Seven epochs × five references × two frames × two regions | 140 merged comparisons |
| Ten native contexts × own same-exposure merged × two frames × two regions | 40 native comparisons |
| Identical-product self rows included above | 20 |
| Exact original event/order raw cutout/excess pairs retained | 10 |
| Compact pre-interpolation source windows | 17 |

There are **34 profile slots and 180 comparison slots**. Every missing, insufficient, nonpositive, low or invalid outcome keeps its slot and reason. Merged profiles compare with all five fixed references; native profiles compare only with their own same-exposure merged product.

Each reference has six other epochs. The **30 directed nonself rows per frame/region represent 20 unordered exposure pairs and 10 reciprocal reference-pair duplicates**, reusing only seven observations. They do not add 30 independent epochs. Retain source/reference identities, `same_exposure` and `identical_product_self_pair` flags. Report each reference's six other epochs without favorable selection. Native/merged agreement also shares exposure/extraction lineage and is dependent evidence rather than another observation or physical flux ratio.

## Fresh geometry and unassessed flux quality

A fresh scan of **all 72 order headers in five native products (360 rows)** confirms **orders 3 and 4 alone** covering the exact original event coordinates. All twenty source/frame contexts geometrically cover the full common window/core and both reference flanks: **601 total, 51 core and 550 surrounding grid positions**. Exact product-specific endpoints and fixed-frame geometry are bound in the inventory and plan.

Coordinate coverage does not establish finite observed flux, positive references, false low flags or usable statistics. All quality outcomes remain runtime checks. Do not import C018 order-2 missing flanks, raw-only counts or signed outcomes. Keep any actual partial/invalid result and never borrow a flank or value from an overlapping order.

## Historical stages and the distinct 0129 event

All five C019 original primary/secondary/adopted reviews retain **U/U/U**, including **0129** in the older raw_followup source. Every original order-3/4 context has true global-grid, local usable and baseline support. Four batch03 members explicitly record true later-five-window support.

**0129 has no later-five-window field and was not selected in the later mapping follow-up. Its later fields remain null/unassessed**, rather than false or inferred true. Original mapping remains supported/U. Do not transfer C018/0128's original I/M-normalized-I/baseline-I history, order-2 failures or later wider diagnosis to the distinct 0129 event. The separate completed 0128 diagnosis is prior evidence and is not replayed.

0129 retains its exact original **21×25 five-array raw/excess containers**; the four batch03 members retain **31×33** panels. Each original index extent and full scale stays unchanged. The remote off-trace pixel noted in **0135/order 3** does not classify its diffuse central feature. Mapping support and morphology do not establish physical origin or qualify a laser candidate.

## Signed reference rule and comparisons

Merged flux retains uncalibrated ADU units. Native extracted units remain unspecified when BUNIT is absent in the fresh inventory. Signed values are never clipped or sign-flipped. Only source slices needed by the union of both fixed-frame windows plus interpolation brackets are copied; full merged coordinates locate slices and native coordinates derive from recorded headers.

Sampling, normalization and comparison functions remain unchanged from the proven C018/C016 joint methods. Per profile/frame, use the pooled signed median of original source samples at **1.5 ≤ |offset| ≤ 3 Å**, requiring **at least 20 finite samples in each flank and a strictly positive pooled median**. Retain geometric/native/finite counts, separate medians/nonpositive fractions, available versus valid reference levels, ERR support and failure reasons. Every fixed-flank spectral structure remains; levels are descriptive rather than established line-free continua.

The first-difference proxy is `1.4826 × MAD / sqrt(2)` from finite adjacent source samples in the same flank without a large wavelength gap. The low-reference rule `reference ≤ 3×proxy` applies only to valid normalization and is not formal SNR. Missing, insufficient or nonpositive references remain raw-only with null low flags; valid but low references retain true flags. No moved flank, smaller window or fitted replacement is introduced.

Raw Pearson requires nonzero exact range and **41/51 common-core or 440/550 surrounding common finite grid samples**. Normalized RMS uses the same gates with valid references. Adequately covered raw-only profiles may retain raw Pearson. Linear interpolation masks brackets above 1.51 times the full-source median step and never extrapolates. Interpolation, self rows, reciprocal references and shared extraction remain dependent. ERR support/proxies do not establish significance, false alarms, sensitivity or a qualified survey null.

## Release, all eight figures and preservation

All seven merged and five native headers are checked before new flux access: exact identity/hash/metadata, numeric BERV, merged barycentric-air Angstrom/ADU and unique WAVE/FLUX/ERR single-exposure tables, native shape and polynomial coefficients. The runner has no network code, checks frozen sources/release hashes before and after execution and refuses to overwrite a result directory.

Seventeen compact source NPZs retain exact indices, original-frame/barycentric wavelengths, signed flux, ERR (NaN where native errors are unavailable), BERV, source hashes and full-source spacing. All ten original event/order NPZs are copied byte for byte, including 0129's original smaller containers.

| Figure family | Complete fixed coverage |
|---|---|
| Merged broad/core | Two figures, all seven epochs and five exact member/discovery marker identities |
| Native pages 1–3 | Ten native contexts, four source rows per page, last page two |
| Original raw pages 1–3 | Ten raw/excess pairs, four source rows per page, last page two |

All **eight figures** and exact native/raw pagination/order are bound in the plan. Retain all outcomes without favorable selection. Keep raw-only reasons and low-reference flags visible if present. Merged scales match across frames per quantity/window; native raw scales match across frames per source. Every finite value retains a 5% margin. Raw images use separate full extrema and unchanged historical subtraction. No smoothing, clipping, new crop, contrast variant, registration, subtraction, detector model, pixel statistic or origin assignment is introduced.

After root publishes and reads back the exact method, execute once:

```bash
python work_harps_20261103_c019_context/analysis/compare_group.py
python work_harps_20261103_c019_context/analysis/plot_group.py
```

`ROOT_RELEASE.json` must use `HARPS_C019_GROUP_RELEASE_V1` and bind verified public readback plus plan, runner and inventory hashes. All earlier outputs and classifications remain immutable.
