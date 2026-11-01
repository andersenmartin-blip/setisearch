# Extension02 raw follow-up batch04 — preregistered method

This separate batch selects **all 94 remaining pending V2 records in 37 exposures**, in frozen MAIN100 order. All 248 predecessor selected V1/V2 decisions, 242 previously reviewed new V2 records and the older 333 cohort remain unchanged. Selection does not use strength, wavelength, morphology or product availability.

The selected indices are: 61, 62, 63, 64, 66, 67, 68, 69, 70, 71, 72, 73, 74, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 95, 96, 97, 98, 99, 100. The first pending record is V2E2-0243 on HD124553; the exact queue is frozen from predecessor commit `cb176a288874bc2d0658c40dfab191a21b30dda4`.

The planned maximum is 37 RAW and 37 ancillary products, 1,600,000,000 conservatively charged payload bytes, three workers and at most two attempts per product. Redirects are refused; HTTP 401/403 are terminal and receive no alternate path, host, proxy or credential attempt. Failed or omitted pairs are preserved without replacement. HEAD metadata and original provenance are checked before the fixed download jobs are prepared.

[PLAN.json](PLAN.json), [the frozen selection and code](FOLLOWUP_FREEZE.json), [cache comparison](CACHE_CHECK.json), [selected exposures](SELECTED_EXPOSURES.csv), [selected events](SELECTED_EVENTS.csv) and [visual review plan](VISUAL_REVIEW_PLAN.json) define the batch. No payload acquisition or new raw/native array reads occur before root publishes and independently reads back this exact package.

## Metadata preparation outcome

The frozen selection still contains **94 records in 37 exposures**. [HEAD metadata](REMOTE_PRODUCT_METADATA.json) verified 73 of 74 products across 85 attempts. The ancillary product `ADP.2023-07-07T01:08:58.253` returned HTTP 503 on both allowed HEAD attempts, so its complete exposure pair is omitted from acquisition without replacement. This is exposure `ADP.2023-07-07T01:08:58.252`, HD141937, MAIN100 index 99; its selected records **V2E2-0332 and V2E2-0333 remain N/unavailable in this batch**.

The [frozen acquisition jobs](JOBS.json) therefore contain **72 products in 36 complete pairs**, totaling **955,039,604 advertised payload bytes**. If all planned pairs are acquired and reviewed, the pending queue will retain the two unavailable records; no third metadata attempt or alternative route is authorized by this batch. The full failure history and omission remain in [SELECTION.json](SELECTION.json) and the metadata report.

All **13 offline transport/identity guard tests passed against the 72 actual frozen jobs**; see [GUARD_TEST_RESULTS.json](GUARD_TEST_RESULTS.json). Guard tests used no network or science payload. Actual acquisition and scientific review have not started.

Extraction and numerical mapping methods are byte-identical to batch03. Every selected event and every covering order is retained; an unsupported order or incomplete cutout preserves M regardless of visible morphology. Unavailable product pairs retain N. Provisional visual interpretations do not establish physical origin, a qualified laser, sensitivity, a global false-alarm rate or a calibrated null result.

The main survey remains 300 exposures of 20 stars, 70.874650833 hours. The completed 336-event epoch comparison is not repeated. After the pending raw queue, all unresolved structures and mapping limitations remain follow-up work. No unattended background science worker is configured.

Results, validation, saved inputs and the exact next action will be documented here after acquisition and independent review. All science timestamps use UTC; the current user-facing work date is 2 November 2026 in Europe/Copenhagen.
