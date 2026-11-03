# C011: HD112410 individual spectral context

**All six other epochs agree better with the fixed May discovery profile in barycentric coordinates than in the fixed topocentric frame, in both the original core and surrounding window. V2E2-0089 remains U.** Both native orders have complete coverage and valid positive normalization. **Order 2's two low-reference flags are true** and its noisy signed variation remains explicit. These descriptive results do not identify a spectral line or physical origin, qualify a laser candidate, estimate significance or calibrate a null result.

The single released execution completed on **2026-11-03 at 13:12:26 UTC**: **18 profiles and 36 comparison slots**, including four identical-product self rows, nine bounded source windows and two byte-exact historical raw-panel copies. All 36 Pearson values and all 36 normalized RMS values are evaluable; there are zero raw-only, blocked or structurally excluded slots. The only reference is **`ADP.2025-05-29T01:01:14.389`**, observed **2025-05-28**. All seven April–August 2025 HD112410 observations remain included; no acquisition or observing time was added.

## Complete frame comparisons

The exact input catalog center is **3865.6775000000002 Å** barycentric air, with original core **[3865.4275000000002,3865.9275000000002] Å** and full context **[3862.6775000000002,3868.6775000000002] Å**. These are fixed catalog/window inputs rather than fitted feature locations, measured physical widths or a wavelength-accuracy claim. Figures display 3865.6775 Å.

Each row below compares one other epoch with the unchanged May discovery. Values separated by `/` are barycentric/topocentric; the four self rows are excluded.

| Other observation (UTC) | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 2025-04-29 | 0.972992 / -0.308971 | 0.969492 / 0.093220 | 0.117274 / 0.805930 | 0.111964 / 0.602020 |
| 2025-05-30 | 0.973576 / 0.953127 | 0.965899 / 0.954910 | 0.120557 / 0.159233 | 0.120737 / 0.138355 |
| 2025-06-22 | 0.961393 / -0.074844 | 0.967024 / 0.360514 | 0.138390 / 0.746623 | 0.116701 / 0.509607 |
| 2025-06-27 | 0.949081 / -0.318273 | 0.962877 / 0.235336 | 0.162986 / 0.872518 | 0.126849 / 0.567362 |
| 2025-07-09 | 0.954776 / -0.601689 | 0.961697 / 0.072718 | 0.150378 / 0.900059 | 0.125861 / 0.612298 |
| 2025-08-07 | 0.966022 / -0.711186 | 0.962271 / -0.017720 | 0.133894 / 0.967655 | 0.129754 / 0.649004 |

| Frame | Region | Nonself raw r range | Median raw r | Nonself normalized RMS range |
|---|---|---:|---:|---:|
| barycentric | Core | 0.949081–0.973576 | 0.963708 | 0.117274–0.162986 |
| barycentric | Surroundings | 0.961697–0.969492 | 0.964388 | 0.111964–0.129754 |
| topocentric | Core | -0.711186–0.953127 | -0.313622 | 0.159233–0.967655 |
| topocentric | Surroundings | -0.017720–0.954910 | 0.164278 | 0.138355–0.649004 |

Barycentric r is higher and normalized RMS lower in **all six pairs in each region**. May 30 has high correlation in both frames, consistent with its small metadata-predicted displacement from the May 28 anchor; its topocentric core r is 0.953127 versus barycentric 0.973576. The other five topocentric core correlations are negative. June 27 has the lowest barycentric core r and largest core RMS; July 9 has the lowest surrounding r and August 7 the largest surrounding RMS. These retained differences prevent selecting only the most favorable epoch. The four identical-product self rows retain r≈1 and RMS=0 and add no recurrence evidence.

- [All seven epochs: broad signed and scaled context](results/figures/MERGED_BROAD_CONTEXT.png)
- [The same epochs: fixed original core](results/figures/MERGED_CORE_CONTEXT.png)

The core figure retains a broad multi-sample central rise and the positive-side trough and secondary rise. The April exposure is strongest in raw ADU, while the May discovery has a sharper scaled central crest. The broad view retains repeated peaks and troughs throughout both fixed reference flanks. Surrounding agreement does not isolate one emission line. No center, width, lag, stellar velocity, continuum, background, drift or selected frame shift was fitted. Markers denote the catalog/discovery coordinate, not fitted peaks.

## Own May anchor and coordinate geometry

The discovery BERV **−5.48386283255014 km/s** gives the newly computed topocentric-air anchor **3865.748213029564 Å**. C012's April reference and numeric anchor were not transferred. The fixed ±3 Å grid has **601 centers at 0.01 Å spacing**, with 51 original-core and 550 surrounding centers; common-support gates remain **41/440**. The seven own-target epochs span **21.30284860830273 km/s** in BERV.

These positions were calculated from metadata before observed values were read, assuming a barycentrically coherent catalog center. They are predicted coordinates rather than measured peak locations.

| Observation (UTC) | Role | Predicted offset from fixed anchor (Å) | Original ±0.25 Å core |
|---|---|---:|---|
| 2025-04-29 | Other epoch | -0.114616520 | Inside |
| 2025-05-28 | Discovery | +0.000000000 | Inside |
| 2025-05-30 | Other epoch | +0.007535802 | Inside |
| 2025-06-22 | Other epoch | +0.082812042 | Inside |
| 2025-06-27 | Other epoch | +0.096730762 | Inside |
| 2025-07-09 | Other epoch | +0.125761764 | Inside |
| 2025-08-07 | Other epoch | +0.160086601 | Inside |

**All seven predicted centers remain inside this fixed topocentric core.** April 29 is at −0.114616520 Å, May 30 only +0.007535802 Å and August 7 at the largest positive displacement, +0.160086601 Å. This differs from C012's April-anchored geometry. A center flag does not establish full finite-width feature coverage. The fixed window is not recentered and can sample different surrounding structure. The BERV span supplies coordinate separation rather than calibrated origin discrimination. [Prospective coordinates and caveats](../scientific_review/PRE_ARRAY_SCIENTIFIC_REVIEW.json).

## Signed quality and positive references

All **18 profiles have full 601-point raw and normalized support**, valid positive two-flank medians, zero outside-coverage/gap masks and **zero positive finite ERR samples**. All 36 comparisons use complete 51-point core or 550-point surrounding common support. **Six profile rows contain nonpositive original source samples**, preserved without clipping or sign changes; the other 12 rows have none. Counts below concern original source samples rather than interpolated grid support. Each cell lists **barycentric; topocentric** counts; two frames of one exposure remain dependent.

| Source / observation (UTC) | Window nonpositive B; T | Left flank nonpositive B; T | Right flank nonpositive B; T |
|---|---:|---:|---:|
| Merged 2025-04-29 | 0/600; 0/600 | 0/150; 0/150 | 0/150; 0/150 |
| Merged 2025-05-28 | 3/600; 3/600 | 0/150; 0/150 | 0/150; 0/150 |
| Merged 2025-05-30 | 0/600; 0/599 | 0/150; 0/149 | 0/150; 0/150 |
| Merged 2025-06-22 | 0/600; 0/600 | 0/150; 0/150 | 0/150; 0/150 |
| Merged 2025-06-27 | 0/600; 0/600 | 0/150; 0/150 | 0/150; 0/150 |
| Merged 2025-07-09 | 0/600; 0/600 | 0/150; 0/150 | 0/150; 0/150 |
| Merged 2025-08-07 | 0/600; 0/600 | 0/150; 0/150 | 0/150; 0/150 |
| Native order 2, 2025-05-28 | 29/655; 29/655 | 0/160; 0/160 | 13/168; 13/168 |
| Native order 3, 2025-05-28 | 3/534; 3/534 | 0/132; 0/132 | 0/136; 0/136 |

The May discovery retains **3/600 (0.5%)** nonpositive window samples in each frame, all outside both reference flanks. Native order 2 retains **29/655 (4.4275%)**, including **13/168 (7.7381%)** in its right flank and none in its left. Order 3 retains **3/534 (0.5618%)**, outside both flanks. Source masks differ slightly by frame: May 30 topocentric has **599 finite window samples and 149 left-flank samples**, while its barycentric source masks have 600/150. Both still yield full 601-point interpolated support without a gap or extrapolation.

Discovery reference values are:

| Product and units | Frame | Finite flank samples L/R | Left median | Right median | Pooled reference | First-difference proxy | Low flag |
|---|---|---:|---:|---:|---:|---:|---:|
| Merged (ADU) | barycentric | 150 / 150 | 170.531380 | 122.730335 | 155.309959 | 21.505817 | False |
| Merged (ADU) | topocentric | 150 / 150 | 170.531380 | 122.730335 | 155.309959 | 21.505817 | False |
| Native order 2 (unspecified) | barycentric | 160 / 168 | 69.415939 | 27.218124 | 43.386597 | 17.929966 | True |
| Native order 2 (unspecified) | topocentric | 160 / 168 | 69.415939 | 27.218124 | 43.386597 | 17.929966 | True |
| Native order 3 (unspecified) | barycentric | 132 / 136 | 112.543205 | 108.302868 | 109.767494 | 19.468108 | False |
| Native order 3 (unspecified) | topocentric | 132 / 136 | 112.543205 | 108.302868 | 109.767494 | 19.468108 | False |

**Order 2's reference is valid and positive at 43.386597, yet low=true in both frames**, because it is ≤3 times its proxy 17.929966. These are **not raw-only** profiles: normalization and all comparisons remain evaluable under the frozen rule. The noisy scaled curve and true-low annotations are retained in both native panels. The remaining **16 low-reference flags are false**; none is null. Neither outcome is a formal SNR or general quality certificate.

Merged reference levels span **155.309959–553.642212 ADU** and first-difference proxies **19.663567–36.705803 ADU**. Every fixed-flank source sample and its spectral structure remains in the pooled medians. These descriptive levels are not established line-free continua. Positive scalar division leaves Pearson unchanged; scaled heights and RMS depend on the reference levels. ERR support and descriptive proxies do not supply formal uncertainty, false-alarm probability, sensitivity or a qualified survey null.

## Both native orders and historical raw context

The fresh all-72-order header scan selects **orders 2 and 3**, both covering the entire fixed context, core and both reference flanks in each frame. No C012 missing-flank outcome applies. Native BUNIT is absent; extracted units remain unspecified and distinct from merged ADU. Both orders and the merged discovery share one May exposure and extraction lineage, so agreement is dependent evidence rather than another observation or a physical flux ratio.

| Native order | Core raw r B/T | Surrounding raw r B/T | Core normalized RMS B/T | Surrounding normalized RMS B/T |
|---|---:|---:|---:|---:|
| 2 | 0.918410 / 0.918409 | 0.804246 / 0.804243 | 0.216693 / 0.216697 | 0.458426 / 0.458443 |
| 3 | 0.991103 / 0.991103 | 0.924009 / 0.923999 | 0.143153 / 0.143152 | 0.200610 / 0.200626 |

[Both native order contexts](results/figures/NATIVE_ORDERS_1.png) retain full signed and scaled curves. Order 2 is noisier, has nonpositive samples and stronger scaled spikes. Order 3 follows the merged central shape more closely, while surrounding differences and its retained negative trough remain visible. Same-exposure similarity and complete coverage do not independently validate raw registration or physical origin.

[Both exact historical raw cutout/excess pairs](results/figures/PRESERVED_RAW_ORDER_CONTEXT_1.png) retain diffuse central trace-associated enhancement, weaker/noisier in order 2 and clearer in order 3. Strong right-edge structure remains on the full scales, including alternating positive and negative order 3 residuals. It is not assigned to the catalog feature or given a physical origin. All pixels, original subtraction and separate complete scales remain unchanged; no crop, contrast variant, new registration, background model, subtraction or pixel statistic was introduced.

**Both C011 orders retain true global-grid, original local_mapping_usable, original baseline_mapping_verified and later five-window support.** C012's order 2 original local/baseline false flags do not apply here. All historical primary, secondary and adopted reviews remain **U/U/U** for broad native structure and diffuse trace-associated enhancement. Historical mapping support, current low-reference outcomes and morphology do not change U or qualify a laser candidate. [Exact review and mapping records](../inputs/INPUT_INVENTORY.json).

## Dependence, verification and continuation

C011 uses the same seven HD112410 observing products as C010/C012. Its core lies outside C012's window, but their broader windows overlap over **[3866.2675,3868.6775000000002] Å**, width **2.4100000000003092 Å**. The entire C011 positive reference flank lies within that previously viewed C012 window. Those shared surrounding/reference pixels and prior original C011 epoch/raw evidence make this dependent post-detection context, not blind or independent wavelength validation. C010's window is disjoint. Numeric overlaps with other-target HD106515A windows share no source pixels. Earlier outputs and labels remain unchanged.

The [independent actual arithmetic audit](../independent_audit/NUMERICAL_AUDIT.json) passes **481 checks across 71,203 scalar values**, reconstructing all nine source windows, 18 profiles, 36 comparisons, two raw copies and four self rows without importing production functions. Source flux, ERR, indices and profile metrics agree exactly. Maximum source-wavelength difference is **4.547e-13 Å**, raw interpolation difference **1.689e-09 native units**, normalized difference **3.893e-11**, and comparison difference **5.501e-14**. Wavelengths/interpolation are therefore not bitwise identical; computational agreement does not establish physical origin.

The exact method was public and read back before execution in commit `dad9f542b6f7bb830f1020d373634012483e7b15`. [Plan](PLAN.json), [root release](ROOT_RELEASE.json), [summary](results/SUMMARY.json), [bounded inputs](results/BOUNDED_INPUT_INDEX.json), [profile metrics](results/PROFILE_METRICS.csv), [comparisons](results/COMPARISONS.csv) and [numeric hashes](results/OUTPUT_HASHES.json) bind the run. All four figures were visually inspected and fully decoded, with hashes/sizes checked against [PLOT_INDEX.json](results/PLOT_INDEX.json). All **50 source bindings and 39 numerical files** remain exact. [RESULTS_QA.json](RESULTS_QA.json) records these checks.

The next unfinished original-queue work is **C016 / R017, JOINT_PROFILE_CONTEXT on HD114386**, grouping four records rather than replaying completed normalization routes:

| Queue row | Record | Own discovery product | Catalog center (Å) | Current code |
|---|---|---|---:|---|
| 27 | V2E2-0094 | ADP.2022-03-08T01:01:37.348 | 4303.785 | U |
| 29 | V2E2-0096 | ADP.2022-05-17T01:02:16.724 | 4303.785 | U |
| 30 | V2E2-0098 | ADP.2023-01-03T01:08:17.803 | 4303.785 | U |
| 32 | V2E2-0110 | ADP.2023-08-29T01:02:07.487 | 4303.79 | U |

C013 / 0092 at row 26 and C014 / 0104 at row 31 already have complete descriptive NORMALIZATION_CONTEXT diagnostics and remain U; they are skipped as completed work. C016 requires its **own HD114386 cohort, four fixed discovery references, newly frozen group geometry/anchor and fresh native/header/mapping scope**. HD112410 products, May anchor and quality outcomes must not be transferred. [Next queue metadata and completion evidence](../scientific_review/NEXT_GROUP_METADATA.json) preserve this selection. No C016 array analysis or replay of completed normalization work was executed here.
