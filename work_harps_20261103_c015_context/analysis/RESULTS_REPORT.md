# C015: HD114386 individual spectral context

**All six other HD114386 epochs agree better with the fixed May discovery profile in barycentric coordinates than in the fixed topocentric frame, in both the original core and surrounding window. V2E2-0095 remains U.** The central multi-sample structure and surrounding spectrum recur with retained shape/amplitude differences. August 2023 is visibly noisier and less similar and remains included. These descriptive comparisons do not identify a line or physical origin, qualify a laser candidate, estimate significance or calibrate a null result.

The single released execution completed on **2026-11-03 at 14:54:01 UTC**: **16 profiles and 32 comparison slots**, including four identical-product self rows, eight bounded source windows and one byte-exact historical raw-panel copy. All 32 Pearson values and all 32 normalized RMS values are evaluable; zero slots are raw-only, blocked or structurally excluded. The sole reference is **`ADP.2022-05-17T01:02:16.724`**, observed **2022-05-16**. No acquisition or observing time was added.

## One fixed reference and all seven epochs

C015 uses HD114386's own seven existing January 2022–August 2023 observations, with exact original catalog center **3869.915 Å** barycentric air. The original core is **[3869.665,3870.165] Å**, full context **[3866.915,3872.915] Å**. These are fixed catalog/window inputs rather than fitted feature locations or measured physical widths. This is a singleton analysis with one marker/reference; C016's midpoint, joint reference families and order 19 are not transferred.

Values separated by `/` below are **barycentric/topocentric**. Each other epoch uses the unchanged May reference. Four self rows remain in the complete output at r≈1 and RMS=0 and add no recurrence evidence.

| Other observation (UTC) | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 2022-01-06 | 0.983710 / 0.123852 | 0.968275 / 0.113980 | 0.148496 / 0.697342 | 0.122991 / 0.635316 |
| 2022-03-07 | 0.985659 / -0.426890 | 0.975927 / 0.215856 | 0.130278 / 0.905836 | 0.105893 / 0.605490 |
| 2023-01-02 | 0.966874 / -0.057567 | 0.942904 / 0.125479 | 0.150390 / 0.807394 | 0.162024 / 0.637158 |
| 2023-04-29 | 0.974708 / -0.383864 | 0.973193 / 0.125879 | 0.124497 / 1.017536 | 0.117044 / 0.638473 |
| 2023-07-01 | 0.973475 / -0.292135 | 0.966560 / 0.059279 | 0.228538 / 0.842267 | 0.127739 / 0.657685 |
| 2023-08-27 | 0.827496 / -0.433032 | 0.785728 / 0.056682 | 0.641368 / 1.003192 | 0.347069 / 0.712009 |

| Frame | Region | Nonself raw r range | Median raw r | Nonself normalized RMS range |
|---|---|---:|---:|---:|
| barycentric | Core | 0.827496–0.985659 | 0.974091 | 0.124497–0.641368 |
| barycentric | Surroundings | 0.785728–0.975927 | 0.967418 | 0.105893–0.347069 |
| topocentric | Core | -0.433032–0.123852 | -0.338000 | 0.697342–1.017536 |
| topocentric | Surroundings | 0.056682–0.215856 | 0.119729 | 0.605490–0.712009 |

Barycentric r is higher and normalized RMS lower in **all six pairs in each region**. **August 27 has the lowest barycentric r and largest RMS in both regions**: core r **0.827496**, RMS **0.641368**; surrounding r **0.785728**, RMS **0.347069**. Its lower raw levels, higher/jagged scaled crest and extra surrounding variation remain visible. March 7 2022 has the highest barycentric correlation in both regions; April 29 2023 has the smallest core RMS. No weaker epoch was omitted. January 6 2022 retains positive topocentric core r **0.123852**; the other five topocentric core correlations are negative. This is a fixed-window contrast rather than a calibrated origin test.

- [All seven epochs: broad signed and scaled context](results/figures/MERGED_BROAD_CONTEXT.png)
- [The same epochs: exact original core](results/figures/MERGED_CORE_CONTEXT.png)

The core figure retains a multi-sample central rise, a positive-side trough and neighboring structure. The broad figure retains numerous peaks and troughs through both reference flanks; August shows especially pronounced fine variation. Surrounding agreement does not isolate one emission line, and the plotted sampling does not measure physical linewidth. The marker is the fixed catalog/discovery coordinate, not a fitted peak in every epoch. No center, width, lag, stellar velocity, continuum, background, drift or selected frame shift was fitted.

## Own wavelength-specific May anchor

The May discovery BERV **−10.767337430651 km/s** gives the new fixed topocentric-air anchor **3870.0539967497375 Å**, using `3869.915/(1+BERV/c)` with `c=299792.458 km/s`. C016's March common anchor is not reused. The fixed ±3 Å grid has **601 centers at 0.01 Å spacing**, with **51 original-core and 550 surrounding centers** and unchanged common-support gates **41/440**. The seven own-target epochs span **51.572001697156 km/s** in BERV.

The following coordinates were calculated from metadata before observed values were read, assuming a barycentrically coherent catalog center. They are predictions rather than measured peak locations.

| Observation (UTC) | Role | Predicted offset from fixed anchor (Å) | Original ±0.25 Å core |
|---|---|---:|---|
| 2022-01-06 | Other epoch | -0.484329367 | Outside |
| 2022-03-07 | Other epoch | -0.386319562 | Outside |
| 2022-05-16 | Discovery | +0.000000000 | Inside |
| 2023-01-02 | Other epoch | -0.476711859 | Outside |
| 2023-04-29 | Other epoch | -0.100042176 | Inside |
| 2023-07-01 | Other epoch | +0.181391100 | Inside |
| 2023-08-27 | Other epoch | +0.147900782 | Inside |

**Three predicted centers lie outside the fixed topocentric core on its negative side**: January 6 2022, March 7 2022 and January 2 2023. The largest negative displacement is **−0.484329367 Å**. The discovery and April/July/August 2023 centers remain inside. A center flag does not establish full finite-width feature coverage. The window is not recentered and may sample neighboring structure. These displacements supply coordinate geometry rather than calibrated physical-origin discrimination. [Prospective geometry and assumptions](../scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json).

## Signed samples, positive references and missing errors

All **16 profiles have full 601-point raw and normalized support**, valid positive two-flank medians and **16 false low-reference flags**. All 32 comparisons use complete 51-point core or 550-point surrounding common support, with zero gap/outside-coverage masks. Every profile has **zero positive finite ERR samples**.

The only nonpositive source outcomes are **January 2 2023 in both frames: 1/600 window samples (0.1667%) and 1/150 right-flank samples (0.6667%)**, with zero left-flank nonpositive samples. The other **14 profile rows have zero nonpositive window/flank fractions**. All signed values remain unchanged; no clipping or sign change produces these counts. The table uses original source counts, distinct from interpolated-grid support; each cell lists **barycentric; topocentric** and repeated frames remain dependent.

| Source / observation | Window nonpositive B; T | Left flank nonpositive B; T | Right flank nonpositive B; T |
|---|---:|---:|---:|
| Merged 2022-01-06 | 0/600; 0/600 | 0/150; 0/150 | 0/150; 0/150 |
| Merged 2022-03-07 | 0/600; 0/600 | 0/150; 0/150 | 0/150; 0/150 |
| Merged 2022-05-16 | 0/600; 0/600 | 0/150; 0/150 | 0/150; 0/150 |
| Merged 2023-01-02 | 1/600; 1/600 | 0/150; 0/150 | 1/150; 1/150 |
| Merged 2023-04-29 | 0/600; 0/600 | 0/150; 0/150 | 0/150; 0/150 |
| Merged 2023-07-01 | 0/600; 0/600 | 0/150; 0/150 | 0/150; 0/150 |
| Merged 2023-08-27 | 0/600; 0/600 | 0/150; 0/150 | 0/150; 0/150 |
| Native order3 2022-05-16 | 0/550; 0/550 | 0/135; 0/135 | 0/140; 0/140 |

Every merged window contains **600 finite original source samples**, with 150 in each flank. Native order 3 contains **550 finite original window samples**, with 135/140 in its left/right flanks, while retaining 601 finite interpolated grid values. These are different source-sampling and grid counts, not missing profile slots.

Merged reference levels span **51.076479–209.268715 ADU**, with first-difference proxies **12.592721–22.729737 ADU**. August has the weakest barycentric reference, **51.076479 ADU**, with proxy **12.592721 ADU**. Its low-reference flag is false under the frozen `reference≤3×proxy` rule despite its visibly noisier scaled profile. That flag is not a formal SNR or general quality certificate. Discovery values are:

| Product and units | Frame | Finite flank samples L/R | Left median | Right median | Pooled reference | First-difference proxy |
|---|---|---:|---:|---:|---:|---:|
| Merged (ADU) | barycentric | 150 / 150 | 242.881737 | 174.416153 | 209.268715 | 22.729737 |
| Merged (ADU) | topocentric | 150 / 150 | 242.881737 | 174.416153 | 209.268715 | 22.729737 |
| Native order3 (unspecified) | barycentric | 135 / 140 | 221.543442 | 182.437508 | 200.031738 | 24.811205 |
| Native order3 (unspecified) | topocentric | 135 / 140 | 221.543442 | 182.437508 | 200.031738 | 24.811205 |

Every fixed-flank source sample and its structured spectrum remains in the pooled median without masks, moved flanks or fitted replacements. These are descriptive levels rather than established line-free continua. Positive scalar division leaves Pearson unchanged; scaled heights and RMS depend on the levels. ERR support and proxies do not provide formal uncertainty, false-alarm probability, sensitivity or a qualified survey null.

## Fresh native order 3 and historical raw context

A fresh all-72-order header scan finds **order 3 alone** covering the original feature coordinate. It covers the full context/core and both reference flanks in both frames. Order 2 ends **0.047010202 Å below** the original topocentric feature coordinate and is not an additional event panel. No C016 order-19 scope applies. Native BUNIT is absent, so extracted units remain unspecified and distinct from merged ADU.

| Native order | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 3 | 0.999421 / 0.999421 | 0.988709 / 0.988719 | 0.037485 / 0.037484 | 0.074336 / 0.074308 |

[The native order 3 context](results/figures/NATIVE_ORDERS_1.png) follows the same-exposure merged pattern closely, retaining small scale/shape differences. Both share a May observation and extraction lineage; agreement is dependent evidence rather than another detection, a physical flux ratio or new validation of raw-detector registration.

[The complete historical raw cutout/excess pair](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png) retains a central vertical trace and diffuse central positive excess, with a weaker negative residual below it. Strong right-edge bands and alternating residual lobes also remain on the full original scales. Edge structure is not assigned to the catalog feature or given a physical origin. All saved pixels and historical subtraction remain unchanged; no crop, contrast variant, new registration, background, subtraction or pixel statistic was introduced.

Original order 3 retains true **global-grid, local_mapping_usable, baseline_mapping_verified and later five-window support**. These historical stages remain distinct from physical origin. All primary, secondary and adopted reviews remain **U/U/U** for broad multi-sample native structure and diffuse trace-associated enhancement without a distinct charge track. Current shape, correlation and mapping support do not promote the record or qualify a laser candidate. [Exact historical review/mapping records](../inputs/INPUT_INVENTORY.json).

## Dependence, verification and continuation

C015 reuses the same seven HD114386 observations as C016, including the May discovery product, but their wavelength windows are disjoint. The completed 0092/0104 normalization windows are also disjoint from C015. Numerical overlaps with earlier C002/C003/C004 on HD106515A and C011/C012 on HD112410 share no observing products or source pixels. Original 0095 epoch/profile/raw evidence already existed. No blind, untouched, independent-data, new observing-time or archive-wide completeness claim follows. C016 and the completed normalization routes are not replayed; all previous outputs and labels remain unchanged.

The [independent actual arithmetic audit](../independent_audit/NUMERICAL_AUDIT.json) passes **455 checks across 63,724 scalar values**, reconstructing all eight source windows, 16 profiles, 32 comparisons, one byte-exact raw copy and four self rows without importing production functions. Source flux, ERR, indices and profile metrics agree exactly. Maximum source-wavelength difference is **4.547e-13 Å**, raw interpolation difference **8.644e-10 native units**, normalized difference **4.321e-12**, and comparison difference **4.136e-15**. Wavelengths/interpolation are not bitwise identical; computational agreement does not establish physical origin.

The exact method was public and read back before execution in commit `622447cb88946e3e2f0020dc7dc59c99c081b11b`. [Plan](PLAN.json), [root release](ROOT_RELEASE.json), [summary](results/SUMMARY.json), [bounded inputs](results/BOUNDED_INPUT_INDEX.json), [profile metrics](results/PROFILE_METRICS.csv), [comparisons](results/COMPARISONS.csv) and [numeric hashes](results/OUTPUT_HASHES.json) bind the run. All four figures were visually inspected and fully decoded, with hashes/sizes checked against [PLOT_INDEX.json](results/PLOT_INDEX.json). All **56 source bindings and 35 numerical files** remain exact. [RESULTS_QA.json](RESULTS_QA.json) records these checks.

The next unfinished original-queue work is **C018 / R019, JOINT_PROFILE_CONTEXT on new target HD114783**. Keep all seven original members and fixed discovery identities together:

| Queue row | Record | Own discovery product | Exact catalog center (Å) | Current code |
|---|---|---|---:|---|
| 33 | V2E2-0114 | ADP.2022-01-22T01:09:14.958 | 3869.3349999999996 | U |
| 38 | V2E2-0119 | ADP.2022-02-06T01:07:28.382 | 3869.3325 | U |
| 42 | V2E2-0124 | ADP.2022-05-06T01:04:00.123 | 3869.3325 | U |
| 46 | V2E2-0128 | ADP.2023-01-17T01:07:48.581 | 3869.335 | U |
| 50 | V2E2-0133 | ADP.2023-03-23T01:02:04.833 | 3869.3349999999996 | U |
| 51 | V2E2-0134 | ADP.2023-05-16T01:01:18.574 | 3869.3325 | U |
| 54 | V2E2-0138 | ADP.2023-07-02T01:01:43.311 | 3869.335 | U |

C018 requires its own target cohort, all seven reference products, separately frozen common geometry/anchor, exact member markers and fresh native scope. HD114386 products, May anchor, singleton design and quality outcomes must not be transferred. Preserve the staged historical distinction: **six batch03 members originally have U/U/U; 0128 originally has primary I, secondary M (normalized I), adopted baseline I, then later unchanged-coordinate U/U/current U after wider five-window support**. Later support does not retroactively make its failed original order-2 local/mapping stage true. The completed mapping diagnosis is not replayed as new progress, and 0134's separate remote bright order-2 pixel does not classify its central feature. [Next queue metadata and staged histories](../scientific_review/NEXT_GROUP_METADATA.json) retain these dependencies. No C018 array analysis or replay of completed diagnostics was executed here.
