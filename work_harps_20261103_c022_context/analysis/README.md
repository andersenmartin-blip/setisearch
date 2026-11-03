# C022 / R023: prospective joint profile context

This method retains all three original HD114783 records **V2E2-0117, V2E2-0127 and V2E2-0131**, with their January 21 2022, May 5 2022 and January 16 2023 discovery products as three fixed references. All seven existing January 2022–July 2023 observations remain in the cohort; February 5 2022 and March 22, May 15 and July 1 2023 are nonreference epochs. The own-target BERV span is **59.073251754930496 km/s**. Original epoch/native/raw evidence and the completed wider mapping diagnosis already exist. Current adopted codes remain U.

The parent baseline is `b586350441ce4bf3f21020a83d688e0281bfaca3`. The completed C021 handoff selects this entire group before C017's later queue row. This directory adds a separately frozen descriptive context, with no replay of completed mapping or normalization routes.

## Exact geometry and fixed numerical method

| Record | Exact original barycentric-air center (Å) | Discovery product |
|---|---:|---|
| V2E2-0117 | 4312.245 | ADP.2022-01-22T01:09:14.958 |
| V2E2-0127 | 4312.245 | ADP.2022-05-06T01:04:00.123 |
| V2E2-0131 | 4312.237499999999 | ADP.2023-01-17T01:07:48.581 |

The midpoint of exact catalog extrema is **4312.241249999999 Å**, with fixed common ±3 Å context **[4309.241249999999,4315.241249999999] Å** and common ±0.25 Å metric core **[4311.991249999999,4312.491249999999] Å**. The common core is not the union of original member cores: an original edge extends approximately **0.00375 Å** outside one common edge. `PLAN.json` retains every exact original center, individual ±0.25 core and marker identity, including the coincident 0117/0127 barycentric markers. No core expansion or fitted peak is used.

The first-queue 0117 January discovery BERV **29.658729150824 km/s** fixes the single common topocentric-air anchor **4311.814678415948 Å** through `midpoint/(1+BERV/c)`, with `c=299792.458 km/s`. This coordinate rule does not choose a favorable comparison reference. Each original marker uses its own exact center and discovery BERV. Barycentric queries are `CB+x`; fixed topocentric queries are `(CT+x)*(1+BERVepoch/c)`. Native wavelengths use the ascending header polynomial at zero-based pixels 0…4095, with one BERV conversion to barycentric air.

The unchanged C021 numerical helpers retain the 0.01 Å grid, 601 centers, 51 common-core and 550 surrounding centers. Raw Pearson and normalized RMS use unchanged support gates **41/440**. Normalization uses the pooled signed median of original samples at offsets **1.5–3 Å**, requiring at least 20 finite samples separately in each flank and a strictly positive pooled median. The fixed first-difference MAD proxy and `reference≤3×proxy` low flag remain descriptive. Missing, insufficient, nonpositive, blocked and low-reference cases retain every slot and reason; invalid normalization has a null low flag. Signed values are never clipped or sign-flipped. No center, lag, width, velocity, drift, continuum, mask or background is fitted. Reference flanks remain structured spectral samples, without a line-free assumption.

## Direct dependence on the completed C021 context

C022 reuses the same seven observing products and the three applicable native products from C021. Their bounded barycentric spectral windows overlap over **[4309.241249999999,4312.82625] Å**, width **3.585000000000946 Å**. The full C022 core lies inside C021's positive reference flank **[4311.32625,4312.82625] Å**. Conversely, the full C021 core **[4309.57625,4310.07625] Å** lies inside C022's negative reference flank **[4309.241249999999,4310.741249999999] Å**. The original cores are distinct, but these are directly reused spectral pixels and reciprocal structured-flank exposure. The C022 core has already been shown in C021's broad view. It supplies no untouched or independent validation.

The plan binds the prior C021 inventory, plan and bounded source-index index so an independent audit can document source identity/intersection without rerunning prior methods or broadening source reads. The fixed flanks retain all shared structure; there is no new mask or alternative normalization. Original raw crops retain separate custody without assuming their equality or independence. The C018/C019 blue windows are spectrally disjoint but use the same observations/native lineage. Other-target C006/C007 numerical overlaps share no source pixels. No new observing time, blind data, archive-wide completeness or physical origin is inferred.

## Fresh native scope and complete delivery

Fresh scans of all **216 header rows** in the three discovery native products select **only order 19** for each original event coordinate. Both fixed frames have complete geometric context/core/flank coverage for all six contexts. Header coordinate support does not predict finite values, reference validity, signed counts or runtime low flags; all such outcomes remain unassessed before release.

| Frozen accounting | Count |
|---|---:|
| Merged profiles: seven epochs × two frames | 14 |
| Native profiles: three order-19 sources × two frames | 6 |
| All profile slots | 20 |
| Merged comparisons: seven epochs × three references × two frames × two regions | 84 |
| Native own-same-exposure comparisons: three sources × two frames × two regions | 12 |
| All comparison slots | 96 |
| Identical-product self comparisons | 12 |
| Bounded pre-interpolation source windows | 10 |
| Exact original raw-panel containers | 3 |
| Complete figures | 4 |

Each reference retains all six other epochs. Per frame/region **18 directed nonself records represent 15 unordered observation pairs and three reciprocal reference-pair duplicates**, over seven observations. Native sources compare only against their own same-exposure merged extraction. All source/reference identities, same-exposure flags and identical-product self flags remain explicit. Repeated references, self comparisons and shared extraction do not add independent observations.

The plotter delivers two merged broad/core figures, one native page with all three rows and one original raw page with all three rows. Every exact member marker is retained in the broad view, legend and metadata; out-of-core markers do not move the core. Merged scales match between frames per quantity/window, native raw scales match across frames per source, and all finite values retain 5% margins. Raw cutout/excess views preserve every saved pixel and separate full scales. There is no smoothing, clipping, favorable selection, crop, contrast variant, new registration, subtraction or pixel statistic.

## Original failures, later support and 0131 custody

| Record | Original global | Original local | Original baseline | Later reference support | Review history |
|---|---|---|---|---|---|
| 0117 | true | false | false | true | Original U/U/U; current U |
| 0127 | true | false | false | true | Original U/U/U; current U |
| 0131 | true | false | false | true | Original primary I, secondary M normalized I, baseline I; later U/U/current U |

The two batch03 records preserve explicit `baseline_mapping_verified` fields. Older 0131 preserves its original `mapping_verified` basis and failed original stage separately from completed wider reference support at unchanged coordinates/pixels. Later support does not retroactively repair original failures. Do not transfer C021's mixed true/false stages or distinct 0130/0129 histories. The exact original 0131 smaller five-array container is preserved separately from its completed later wider diagnosis, alongside the two exact batch03 original panels. No completed mapping or normalization route is reopened; mapping support, spectral levels, morphology and physical origin remain separate.

## Release and verification

`prepare_plan.py` binds the current baseline receipt, finalized input inventory/README/restoration receipt, input audit, old handoff/architecture, prior plans and relevant mapping/normalization custody. `synthetic_preflight.py` uses only analytic arrays and JSON/header metadata, tests unchanged numerical functions, signed and invalid outcomes, support boundaries, exact three-reference geometry, historical stages and C021 shared-flank dependence. It does not open observed flux or raw arrays.

The actual runner requires `ROOT_RELEASE.json` with a verified public method commit, exact plan/runner/inventory and source hashes. It refuses any existing `results/` directory and rechecks all bindings after execution. It must run exactly once after explicit root release following public freeze/readback. Until then only compile and synthetic checks are allowed. The frozen plotter then runs once and checks all numerical hashes before and after plotting. Reports and QA are written after actual outcomes, with all three six-epoch families, signed/quality outcomes and every figure. ERR support/native units, descriptive proxies and frame agreement do not establish significance, sensitivity, linewidth, a qualified null or physical origin. All three current codes remain U.
