# C012: HD112410 individual spectral context

**All six other HD112410 epochs agree better with the fixed discovery profile in barycentric coordinates than in the fixed topocentric frame, in both the original core and surrounding window. V2E2-0087 remains U.** The central broad structure and surrounding peaks recur with retained shape, amplitude and reference-level differences. This is a descriptive comparison of saved spectra, without a line identification, physical-origin assignment, qualified laser candidate, significance estimate or calibrated null.

The single released execution completed on **2026-11-03 at 12:44:19 UTC**: **18 profiles and 36 comparison slots**, including four identical-product self rows, nine bounded source windows and two byte-exact historical raw-panel copies. No source profile is blocked or structurally excluded. **Order 2 is raw-only in both frames because its entire positive reference flank is missing.** There are **34 evaluable raw Pearson values and 32 evaluable normalized RMS values out of 36 slots each**; two surrounding Pearson and all four order 2 RMS values remain unavailable with explicit reasons. The sole reference is the discovery observed on 2025-04-29. No new acquisition or observing time was added.

## All seven epochs and one fixed reference

The exact catalog center is **3869.2675 Å** in barycentric air wavelengths, with original core **[3869.0175,3869.5175] Å** and full context **[3866.2675,3872.2675] Å**. These are fixed inputs rather than a fitted feature location or physical linewidth. All seven April–August 2025 HD112410 observations are retained. Values separated by `/` below are barycentric/topocentric; every row uses the same discovery reference and excludes its four self rows.

| Other observation (UTC) | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 2025-05-28 | 0.912614 / -0.156073 | 0.952137 / 0.098558 | 0.135848 / 0.473892 | 0.186254 / 0.728194 |
| 2025-05-30 | 0.953130 / -0.258594 | 0.981032 / 0.069916 | 0.100544 / 0.483496 | 0.110198 / 0.734182 |
| 2025-06-22 | 0.963934 / -0.349347 | 0.979748 / -0.105845 | 0.121483 / 0.540419 | 0.124319 / 0.799174 |
| 2025-06-27 | 0.941365 / -0.366946 | 0.969823 / -0.103324 | 0.125068 / 0.528733 | 0.142735 / 0.796872 |
| 2025-07-09 | 0.953091 / -0.406239 | 0.970669 / -0.051203 | 0.096448 / 0.483808 | 0.134659 / 0.771555 |
| 2025-08-07 | 0.938003 / -0.417189 | 0.971228 / -0.019795 | 0.108716 / 0.425499 | 0.130052 / 0.753932 |

| Frame | Region | Nonself raw r range | Median raw r | Nonself normalized RMS range |
|---|---|---:|---:|---:|
| barycentric | Core | 0.912614–0.963934 | 0.947228 | 0.096448–0.135848 |
| barycentric | Surroundings | 0.952137–0.981032 | 0.970949 | 0.110198–0.186254 |
| topocentric | Core | -0.417189–-0.156073 | -0.358147 | 0.425499–0.540419 |
| topocentric | Surroundings | -0.105845–0.098558 | -0.035499 | 0.728194–0.799174 |

Barycentric r is higher and normalized RMS lower in **all six pairs in each region**. All six topocentric core correlations are negative, while the barycentric core values span 0.912614–0.963934. May 28 has the lowest barycentric correlation and largest normalized RMS in both regions; it remains included. June 22 has the highest barycentric core correlation, May 30 the highest surrounding correlation, and July 9 the smallest core RMS. These comparisons describe the fixed windows and are not calibrated origin tests. Four identical-product self rows retain r≈1 and RMS=0 and add no recurrence evidence.

- [All seven epochs: broad signed and scaled context](results/figures/MERGED_BROAD_CONTEXT.png)
- [The same epochs: original core](results/figures/MERGED_CORE_CONTEXT.png)

The core figure retains a multi-sample central rise, a neighboring shoulder on its negative-offset side and a trough to its positive side. The discovery is strongest in raw ADU, while the scaled profiles show smaller retained height and shape differences. May 28 is noisier. The broad view retains repeated peaks and troughs across both reference flanks; surrounding agreement does not isolate a single emission line. No fitted center, width, lag, stellar velocity, background, continuum, drift or selected frame shift was tried. Figure markers denote the catalog/discovery coordinate.

## Fixed geometry and near-edge epochs

The April discovery BERV **3.40485846065643 km/s** gives a newly computed wavelength-specific topocentric-air anchor **3869.2235557371996 Å**. The fixed ±3 Å context has 601 centers at 0.01 Å spacing: 51 original-core and 550 surrounding centers, with minimum common support **41/440**. The seven HD112410 epochs span **21.30284860830273 km/s** in BERV. C010's numeric anchor was not reused.

These positions were calculated from metadata before observed values were read, assuming a barycentrically coherent catalog center. They are predicted coordinates rather than measured peak locations.

| Observation (UTC) | Role | Predicted offset from fixed anchor (Å) | Original ±0.25 Å core |
|---|---|---:|---|
| 2025-04-29 | Discovery | +0.000000000 | Inside |
| 2025-05-28 | Other epoch | +0.114722963 | Inside |
| 2025-05-30 | Other epoch | +0.122265763 | Inside |
| 2025-06-22 | Other epoch | +0.197611911 | Inside |
| 2025-06-27 | Other epoch | +0.211543557 | Inside |
| 2025-07-09 | Other epoch | +0.240601520 | Inside |
| 2025-08-07 | Other epoch | +0.274958234 | Outside |

**Only August 7 has its predicted center outside the fixed topocentric core**, at +0.274958234 Å, **0.024958234 Å beyond** the positive edge. July 9 remains inside at +0.240601520 Å, only **0.009398480 Å inside** the edge. A center flag does not establish whether an entire finite-width feature is inside or outside. The fixed window may retain part of extended structure and may sample neighboring structure. No boundary or anchor was changed. These displacements and BERV span provide coordinate geometry, not calibrated physical-origin discrimination. [Prospective coordinates and caveats](../scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json).

## Valid references, signed samples and missing errors

The 14 merged profiles and two native order 3 profiles have full 601-point raw and normalized support, valid positive two-flank references and **16 false low-reference flags**. The two order 2 profiles have no valid reference, zero normalized support and **null low-reference flags**, rather than false. Their raw support is retained. There are no wavelength-gap masks. Every profile has **zero positive finite ERR samples**.

Positive reference medians do not require every signed sample to be positive. Four profile rows contain nonpositive source samples: **May 28 in both frames has 3/600 (0.5%)**, all three in its left flank **3/150 (2%)**; **native order 2 in both frames has 2/423 (0.4728%)**, including **1/166 (0.6024%)** in its left flank. The other **14 profile rows have zero nonpositive window samples**. Signed values remain unchanged. The table lists original source samples, which are distinct from interpolated-grid support. Each cell gives barycentric; topocentric counts, and repeated frame rows are dependent.

| Source / observation (UTC) | Window nonpositive B; T | Left flank nonpositive B; T | Right flank nonpositive B; T |
|---|---:|---:|---:|
| Merged 2025-04-29 | 0/600; 0/600 | 0/150; 0/150 | 0/150; 0/150 |
| Merged 2025-05-28 | 3/600; 3/600 | 3/150; 3/150 | 0/150; 0/150 |
| Merged 2025-05-30 | 0/600; 0/600 | 0/150; 0/150 | 0/150; 0/150 |
| Merged 2025-06-22 | 0/600; 0/599 | 0/150; 0/149 | 0/150; 0/150 |
| Merged 2025-06-27 | 0/600; 0/600 | 0/150; 0/150 | 0/150; 0/150 |
| Merged 2025-07-09 | 0/600; 0/600 | 0/150; 0/150 | 0/150; 0/150 |
| Merged 2025-08-07 | 0/600; 0/600 | 0/150; 0/150 | 0/150; 0/150 |
| Native order 2, 2025-04-29 | 2/423; 2/423 | 1/166; 1/166 | Unavailable / 0; Unavailable / 0 |
| Native order 3, 2025-04-29 | 0/546; 0/546 | 0/134; 0/134 | 0/139; 0/139 |

June 22 topocentric has **599 finite original window samples and 149 finite left-flank samples**, versus 600/150 in its barycentric source masks. It still has 601 finite interpolated grid values with no gap or outside-coverage mask. Different coordinate masks explain these source counts; no missing point is filled by a new fit.

Merged pooled references span **92.346405–332.728928 ADU**, and descriptive first-difference proxies **16.634240–25.463589 ADU**. May 28 has the weakest barycentric reference, 92.346405 ADU, with proxy 17.123925 ADU; its fixed low-reference flag remains false. This flag is not a general quality certificate or formal SNR. Flank-scaled heights and RMS depend on the fixed reference levels.

Discovery values are retained below. The available one-sided order 2 median, **89.043491**, is not a valid two-flank reference; its reference field remains unavailable.

| Product and units | Frame | Finite flank samples L/R | Left-flank median | Right-flank median | Valid pooled reference | First-difference proxy |
|---|---|---:|---:|---:|---:|---:|
| Merged (ADU) | barycentric | 150 / 150 | 411.437912 | 293.835861 | 332.728928 | 25.463589 |
| Merged (ADU) | topocentric | 150 / 150 | 411.437912 | 293.835861 | 332.728928 | 25.463589 |
| Native order 2 (unspecified) | barycentric | 166 / 0 | 89.043491 | Unavailable | Unavailable | 18.619317 |
| Native order 2 (unspecified) | topocentric | 166 / 0 | 89.043491 | Unavailable | Unavailable | 18.619317 |
| Native order 3 (unspecified) | barycentric | 134 / 139 | 353.979523 | 297.636047 | 311.214966 | 29.717274 |
| Native order 3 (unspecified) | topocentric | 134 / 139 | 353.979523 | 297.636047 | 311.214966 | 29.717274 |

Every fixed-flank sample and its spectral structure remains in the medians; they are descriptive reference levels rather than established line-free continua. Positive scalar division leaves Pearson unchanged, while scaled heights and RMS depend on the levels. The first-difference proxy and reference≤3×proxy rule are descriptive. Missing positive ERR support prevents a formal uncertainty model; these statistics do not establish false-alarm probability, sensitivity or a qualified survey null.

## Both native orders and unavailable statistics

The fresh all-72-order header scan finds **orders 2 and 3** covering the original center. Their native BUNIT is absent, so their extracted units remain unspecified and distinct from merged ADU. Both orders share the April discovery exposure and extraction lineage with the merged product, making agreement dependent evidence rather than another observation or a physical flux ratio.

Order 2 ends at **+0.776413667 Å barycentric / +0.776404849 Å topocentric**. Its two frame profiles retain **378/601 raw grid samples**, including the entire **51-point core** and only **327/550 surrounding samples**, with **223 outside-coverage grid positions**. Its whole positive reference flank [1.5,3] Å is absent. Both normalization reasons are exactly `MISSING_RIGHT_FLANK_COVERAGE`; its available negative-flank median is positive, but no valid two-flank reference or low flag is assigned.

There are **166 finite original left-flank samples and zero right-flank samples**, a one-sided median of 89.043491 and a descriptive first-difference proxy of 18.619317 in unspecified native units. All signed variation and the abrupt coverage endpoint remain visible. Full raw core support permits the two order 2 core Pearson values. Its 327 surrounding samples fail the unchanged 440-sample gate, leaving both surrounding Pearson values unavailable. Invalid normalization leaves all four order 2 RMS values unavailable; no value or flank is borrowed from order 3.

Order 3 has full raw and normalized support in both frames, 134/139 finite original flank samples, positive reference 311.214966, proxy 29.717274 and false low-reference flags. Its 546 finite original window samples contain no nonpositive values.

| Native order | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 2 | 0.730305 / 0.730332 | Unavailable / Unavailable | Unavailable / Unavailable | Unavailable / Unavailable |
| 3 | 0.998642 / 0.998642 | 0.988140 / 0.988143 | 0.034083 / 0.034084 | 0.088252 / 0.088239 |

[Both native order contexts](results/figures/NATIVE_ORDERS_1.png) retain the noisier order 2 curve and smoother order 3 curve. The order 2 normalized panels display the same-exposure merged curve while the unavailable native curve is explicitly annotated RAW_ONLY; it is not a zero-flux curve. Order 3 follows the same-exposure merged spectrum closely, with visible retained small differences. Neither similarity nor header coverage validates raw-detector mapping.

## Historical raw panels and mapping qualifications

[Both exact historical cutout/excess pairs](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png) retain a central vertical trace and diffuse enhancement, noisier in order 2 and clearer in order 3. Stronger right-edge structure remains visible, including alternating positive and negative residual lobes in order 3. The edge structure is preserved on the original full scales without assigning it to the catalog feature or identifying its physical origin. All saved pixels and historical subtraction remain unchanged; no new crop, contrast variant, registration, background, subtraction, pixel statistic or detector model was applied.

**Order 2 retains original local_mapping_usable=false and baseline_mapping_verified=false**, alongside true global-grid and later five-window support. **Order 3's four historical stages remain true.** Later supported reference geometry does not repair the original order 2 local/baseline limitations. All primary, secondary and adopted reviews remain **U/U/U**, describing broad enhancement in overlapping orders and trace-associated raw structure. Current morphology, core correlation and native/merged agreement do not change the adopted label, establish origin or qualify a laser candidate. [Exact historical reviews and mapping stages](../inputs/INPUT_INVENTORY.json).

## Dependence, verification and continuation

C012 reuses the same seven HD112410 observations and April discovery as C010, but their bounded wavelength windows are disjoint. C012 numerically overlaps HD106515A C002/C003/C004 windows, yet those use different observations and share no source pixels. The numeric overlap is not previously measured C012 flux. Original 0087 epoch/profile and raw evidence already existed, so this is not blind, untouched or independent new observing evidence. No observing time or archive-wide completeness is added; original classifications and completed outputs remain unchanged.

The [independent actual arithmetic audit](../independent_audit/NUMERICAL_AUDIT.json) passes **481 checks across 70,371 scalar values**, reconstructing all nine bounded source windows, 18 profiles, 36 comparisons, two exact raw copies and four self rows without importing production functions. Original source flux, ERR, indices and profile metrics agree exactly. Maximum source-wavelength difference is **4.547e-13 Å**, so wavelengths are not bitwise exact; maximum raw interpolation difference is **1.895e-09 native units**, normalized difference **5.240e-12**, and comparison difference **1.076e-13**. Computational agreement does not establish physical origin.

The exact method was public and read back before execution in commit `3815808d874c9cf927da83dc287631e18de3bdd4`. [Plan](PLAN.json), [root release](ROOT_RELEASE.json), [summary](results/SUMMARY.json), [bounded inputs](results/BOUNDED_INPUT_INDEX.json), [all profile metrics](results/PROFILE_METRICS.csv), [all comparisons](results/COMPARISONS.csv) and [numerical hashes](results/OUTPUT_HASHES.json) bind the run. All four figures were visually inspected and fully decoded, with hashes/sizes checked against [PLOT_INDEX.json](results/PLOT_INDEX.json). All **49 frozen source bindings and 39 numerical output files** remain unchanged. [RESULTS_QA.json](RESULTS_QA.json) records these checks.

The next original-queue item is **C011 / V2E2-0089**, row **25 / R012**, on **HD112410** at **3865.6775000000002 Å**, currently U. It shares this seven-epoch cohort, but its discovery is **2025-05-28**, product `ADP.2025-05-29T01:01:14.389`, and therefore requires its own wavelength-specific discovery anchor plus fresh native scope. Its wider window overlaps C012, so the next analysis will reuse previously viewed flux; it cannot be treated as blind or independent validation. [Next fixed-queue metadata](../scientific_review/NEXT_GROUP_METADATA.json). No C011 profile analysis was executed here.
