# Latest scientific continuation — D077 completed, 2026-11-14

Read [the D077 report](progress/2026-11-14-feros-d077/REPORT.md), [METHOD.json](progress/2026-11-14-feros-d077/METHOD.json), [SUMMARY.json](progress/2026-11-14-feros-d077/SUMMARY.json), [NUMERICAL_AUDIT.json](progress/2026-11-14-feros-d077/NUMERICAL_AUDIT.json), and [SOURCES.json](progress/2026-11-14-feros-d077/SOURCES.json) before the historical D076/D075 instructions below. All 105,681 prior D076 state cells (and 102,833 D074 cells) remain exact; the checkpoint now holds **107,105 state cells**.

D077 completed the prospectively locked metadata and provenance gate across all **30 declared FEROS daytime WLC raw exposures** (`ESO PRO REC1 WLC RAW1..6 NAME` across the five November 2019 chains `F1`–`F5`) plus the 5 science raw anchors: **73/73 HTTP 200 metadata responses** (`790,968` B; `0` FITS bodies downloaded; `0` pixel arrays read). Every WLC identity (`30/30`) resolves in `dbo.raw`, `hdr`, and `DataLink #this` and is publicly released; all **49 fixed CCD/readout/window cards** match the nighttime science raw headers (`CONAD = GAIN = RON = 0.0`); each chain executes `2x30.04s + 2x150.04s + 2x300.04s` `ThAr+Ne` (`LAMP3`, `BOTHFIBS`, `ND = 0.0`) **9.18–11.93 h before** nighttime `OBJECT,WAVE` science (`SKYFIB`, `ND = 1.301`, unused by automatic `fern/1.0`); and **`0` derived `MASTER_WAVE` (`ThArNe0121..0857`) or atomic line-list files** exist in public `ObsCore` or science TARs. `TIMESYS` (`0/35`), `WLC QC` units, and unobserved lamp slots (`LAMP1, 2, 4`) remain explicitly unestablished/unknown.

Original candidate statistics and flags remain unchanged. **0 qualified lasers; all three candidate physical origins (`D002-0061`, `D002-0063`, `D002-0071`) remain unresolved.** Next is proposed **D078** (bounded empirical wavelength-line / simultaneous fiber-2 / stellar-line gate), not yet frozen or executed. Old 141 raw queue stays closed, 90/Rubin stays stopped, historical 663-file delivery remains deferred, and no background science job is running.

---

# Latest scientific continuation — D076 completed, 2026-11-13

Read [the D076 report](progress/2026-11-13-feros-d076/REPORT.md) before the historical D075 instructions below. The newer version-guarded checkpoint contains both D075/D076 and 105,681 current state cells; it must not be downgraded to D075-only. The retained D075 recalculation is a replication on the same data.

D076: 1,440 reverse curves / 577,440 grid fits; all supported, all minima internally reproduced. Up to 0.95 km/s forward/reverse log-coordinate residual at 0061; this documents reference-direction dependence, not physical stellar RV. Original candidate values/flags are unchanged. No qualified laser or calibrated FAP.

Next is proposed D077: all 30 declared WLC raw references, metadata/provenance only, not yet frozen or executed. Establish independent calibration/reference context before any new calibration arrays or physical registration claim. Preserve the baseline, all current state and stopped-queue boundaries. Publication here remains bounded text only; historical 663-file delivery is still pending.

---

# Current continuation — D075 completed, 2026-11-13

Read [the current FEROS report](progress/2026-11-13-feros-d075/REPORT.md), its METHOD.json, SUMMARY.json and numerical/state audit receipts before using the older continuation instructions below.

All 900 individual-order curves / 360,900 fixed-grid fits are complete and internally audited. All 102,833 prior state cells remain exact; 104,257 cells now exist in the retained checkpoint. Up to 1.45 km/s order–merged disagreement at 0061 prevents treating the local fits as one calibrated physical stellar velocity. No candidate statistics were shifted, no physical cause assigned, no FAP calibrated and no laser qualified.

Next proposed scope: D076 calibrated-reference feasibility, not yet frozen or executed. Establish provenance and accuracy limits before physical registration or broader templates. Do not reopen the old 141 raw queue or the stopped 90/Rubin track. No background science job is active.

Publication here contains only text summaries/method/audits/public archive identifiers. The full extraction chain and binary evidence are retained in project checkpoints; the historical 663-file D002/D003 publication remains pending. The older instructions below are historical, not the active scientific pointer.

---

# Continue SETI from consolidated delivery audit D001

Read the [D001 report](work_seti_20261105_d001_delivery/README.md), [verified tables](work_seti_20261105_d001_delivery/results/DELIVERY_AUDIT.json), [fresh metadata cohort](work_seti_20261105_d001_delivery/results/FRESH_METADATA_COHORT54.csv) and [handoff](work_seti_20261105_d001_delivery/NEXT_ACTION.json). Check live refs and bound source hashes.

D001 reconciles 39 published sources: 300 unique main exposures, 20 target labels and 255,148.743 seconds. V1 was applied to 300 exposures, V2 to 200. All 22 V1 and 669 V2 triggers are retained; 12 later V1 triggers match same-exposure V2 records. Current provisional V2 codes remain 403 A / 46 O / 185 U / 35 M. The original 90-row context queue is closed; physical U is unresolved. Historical numerical reproduction receipts pass. This audit reads no science arrays and does not rehash all historical FITS files.

Original V1 recovery was 11/48. Fresh paired V2 recovery at 4/8/16/32 times the original local standard deviation is 5/36/48/48 out of 48 each, using one star and 16 unique patches. No V2 validation anchor below 4231.19 Å covers the 188 current trigger rows in 3800–4000 Å. There is no global completeness, false-alarm rate, confirmed laser or calibrated survey null.

The next distinct route is fixed from prior metadata: 50 main exposures of 10 fresh target labels and four control spectra from two other fresh stars. The existing V2 method stays unchanged. The prospective design has 288 paired trials, including two blue anchors. D001 contains no new science files, flux reads or control/main calculations. Verify current selected ADP/raw provenance and prior/upstream exclusions, then publish and read back the complete separate acquisition/header/control/main method before new science values. Keep every failed input without substitution and preserve exact acquired bytes.

Budget: 0 DKK. No paid service, new account or researcher contact. Rubin remains stopped with minimum 50 unmet. No background science is running. Earlier sections below are historical.

---

# Continue SETI after original 90-row follow-up queue completion

Read [the current state](work_harps_20261105_c037_context/CONTINUATION_STATE.json), [the source-bound routing ledger](work_harps_20261105_c037_context/scientific_review/ORIGINAL_QUEUE_CLOSURE.json) and [the next-work handoff](work_harps_20261105_c037_context/NEXT_ACTION.json). Verify live refs and source hashes.

C037 is complete: original0319 on HD1397, own July25 2024 reference and positive BERV, six reused 2022/2024 observations, 14 profiles and 28 comparisons. Core and surroundings each favor barycentric raw correlation and normalized RMS in all five nonself pairs. All profiles have full positive-reference support without low flags. Four frame profiles from the one discovery exposure retain nonpositive original source samples. Own native/raw3, supported original mapping stages, false extra-secondary flags and physical U remain.

Public 22-file method readback preceded current arithmetic. Separate reconstruction passes 1,188 checks over 55,299 values. All 22 NPZ containers and four PNGs decode; figure contents were inspected by the same assistant through display copies and every original PNG hash remains exact. No independent agent/human review, new observing time, blind validation, physical origin, qualified laser or calibrated survey null. All 49 frozen source bindings remain exact.

The original90-row routing queue is now covered: 79 previous completed diagnostic rows, ten exact prior-baseline rows and the current0319 row. There are 37 original core groups, 32 completed explicit groups and five baseline-only groups. No unfinished original route remains. Ledger coverage is metadata verification of prior state/proof plus passing C037, not a new re-review of all earlier science or resolution of all U. The four HD135204 bounded zero-selection outcomes do not show archive-wide absence. Completed diagnoses stay closed.

Next: review OPTICAL_AND_RUBIN_WEEK_PLANS_2026-11-01.md and consolidate full-sample hit dispositions, searched coverage, controls/recovery and sensitivity/quality limits. Then select a fresh-data or specifically calibrated follow-up route from metadata with original cohort exclusions, publish its own fixed method and preserve all incomplete outcomes. Current release covers no new-dataset values. Keep 0 DKK, no paid service/account/contact step, and Rubin STOPPED_LIMITED_FEASIBILITY_MINIMUM50_UNMET; its190 original objects remain. Do not invent a next group or replay C037 because U persists.

The user directly approved continued public methods/results and GitHub integration. Verify exact final delivery and final-head CI, merge with expected-head guards and synchronize optical-harps-week-20261101. Creation-time pending fields do not assert later integration; inspect actual refs/PR. No background science job is running.

[Queue completion report](work_harps_20261105_c037_context/ORIGINAL_QUEUE_REPORT.md) · [C037 report](work_harps_20261105_c037_context/analysis/RESULTS_REPORT.md). Earlier sections below are historical.

---

# Continue SETI from completed C035 / HD128582

Read [the current state](work_harps_20261105_c035_context/CONTINUATION_STATE.json), verify live refs/source hashes and resume [the exact C037 handoff](work_harps_20261105_c035_context/NEXT_ACTION.json).

C035 is complete: original0289, own March30 reference and positive BERV, six reused HD128582 observations, 14 profiles and 28 comparisons. Surroundings favor barycentric raw correlation and RMS in all five nonself pairs. The core favors barycentric coordinates in three of five by each quantity, with different winning observations: March14 and June5 have metric disagreements. Do not replace this mixed-core result with the surrounding-pattern result. Physical U remains; no qualified laser.

All 14 profiles have 601 finite raw/normalized samples and positive references without low flags or nonpositive original window samples. Own native/raw54 and all supported original mapping stages remain. The secondary uncertainty flag is true without a blend caution. Fixed native normalization retains a broad slope differing from merged spectra; no additional continuum/response fit is introduced. Fourteen member-support rows have nominal49/51 centers according to original transformed geometry.

The public 20-file method readback preceded current arithmetic. Separate scalar reconstruction passes 1,182 checks over 54,774 values; 22 NPZ containers and five PNGs decode. Four figure contents and the raw caption correction were inspected by the same assistant. All original frozen figures remain; the corrected raw heading changes only Own0271 to Own0289, with every changed pixel above the data axes. No numerical production rerun, fitted statistic or display-scale change. All 46 frozen source bindings remain exact.

Seven physical source IDs differ from recent C032, but HD128582 epoch/raw values were already exposed. No new observing time, blind validation, independent agent/human review, physical cause or calibrated survey null.

Exact last unfinished route is C037 on HD1397, original queue row90, V2E2-0319 at3872.375 air Å. Use that target’s own six epochs and July25 2024 discovery ADP.2024-07-26T01:01:40.049 with BERV+4.62262137764828 km/s. Restore own native/raw products, scan all72 orders and freeze own geometry and quality. Do not transfer the HD128582 cohort, March anchor, native54 scope or current outcomes.

The user directly approved public release and continued GitHub updates. Publish exact results, verify final-head CI, merge with expected-head guards and synchronize optical-harps-week-20261101. Confirm live state: creation-time pending fields do not assert later integration. Completed diagnoses stay closed despite U. Rubin remains STOPPED_LIMITED_FEASIBILITY_MINIMUM50_UNMET; no background science job is running.

[Full report](work_harps_20261105_c035_context/analysis/RESULTS_REPORT.md). Earlier sections below are historical.

---

# Continue SETI from completed C032 / HD126093

Read [the current state](work_harps_20261105_c032_context/CONTINUATION_STATE.json), verify live refs and source hashes, then resume [the exact C035 handoff](work_harps_20261105_c032_context/NEXT_ACTION.json).

C032 is complete: original 0278/0283, two own June/July references, six reused observations, 20 profiles and 64 comparison slots. Core and surroundings each favor barycentric raw correlation and normalized RMS in all 10 directed nonself rows: nine unordered relationships and one reciprocal discovery pair. Both physical U labels remain.

Four order-2 profiles lack the positive reference flank and remain raw-only with 341/347 finite raw grid samples. Their core correlations remain evaluable; surrounding support is below the unchanged 440 gate. Sixteen other profiles have full positive-reference support. All original signed values, original local/baseline mapping failures, two secondary uncertainty flags, four raw contexts and 40 member-support records are retained.

The public 20-file method readback preceded current arithmetic. Separate scalar reconstruction passes 2,100 checks over 76,691 values. All 34 NPZ containers and four final figures decode and were inspected by the same assistant. A native PNG changed/truncated after its recorded render; failed bytes are retained and the same frozen plot script restored all four exact originally recorded hashes without a numerical rerun. All 52 frozen source bindings remain exact.

All 10 current source windows overlap C031 original indices; C034 shared merged windows are disjoint. Reused exposures and previously exposed values remain dependent. No blind validation, independent agent/human review, physical cause, qualified laser or calibrated survey null.

Exact next route: C035, first original queue row 85, V2E2-0289 on HD128582 at 5758.2675 air Å. Use that target’s own six January–July observations and March 30 discovery ADP.2025-03-31T01:04:04.493 with BERV +18.1525360721304 km/s. Restore its own native/raw products, scan all 72 orders and freeze its own geometry and quality. Do not transfer the HD126093 cohort, June anchor, orders 2/3 or current outcomes. C037 on HD1397 follows in original order.

The user directly approved public release and continued GitHub updates. Publish exact results, verify final-head CI, merge with expected-head guards and synchronize optical-harps-week-20261101. Confirm actual live state: creation-time pending fields do not assert later integration. Completed routes stay closed despite U. Rubin remains STOPPED_LIMITED_FEASIBILITY_MINIMUM50_UNMET; no background science job is running.

[Report and four figures](work_harps_20261105_c032_context/analysis/RESULTS_REPORT.md). Prior sections below are historical.

---

# Continue SETI from completed C034 / HD126093

Read [the current state](work_harps_20261105_c034_context/CONTINUATION_STATE.json), verify live refs and source hashes, and resume [the exact C032 handoff](work_harps_20261105_c034_context/NEXT_ACTION.json).

C034 is complete: singleton 0271, own May 29 reference, six reused observations,14 profiles and 28 comparisons. Core and surroundings each favor barycentric correlation and RMS in all 5 nonself pairs. All 14 profiles have 601 finite raw/normalized samples and positive references; no low-reference or nonpositive-source flags. Own order 19 and raw 19 context and original U/U/U chain remain. No physical cause, qualified laser, blind validation or calibrated survey null.

Public 20-file method readback preceded current arithmetic. Separate scalar reconstruction passes 1184 checks over 55,139 values;22 NPZ containers and 4 fixed figures decode and all figures were inspected by the same assistant. Six physical merged sources recur from C033 with disjoint current source windows; own native 19 is an additional context from an existing observation. Reused exposures remain dependent.

Exact next original route is C032, first queue row 80, records 0278/0283 with own June 27 andJuly 16 references, exact centers 3869.2975/3869.295 air Å. Proposed metadata midpoint 3869.2962500000003Å is not the next frozen method. Restore own native/raw sources, scan all 72 orders per product and freeze own original/common geometry and quality; do not inherit current order 19, support, anchor or morphology.

The user directly approved public release and continued GitHub updates. Publish exact results, verify final-head CI, merge with expected-head guards and synchronize optical-harps-week-20261101. Confirm actual live state: creation-time receipts do not assert later integration. Completed routes stay closed despite U. Rubin remains STOPPED_LIMITED_FEASIBILITY_MINIMUM 50_UNMET; no background science job is running.

[Report and four figures](work_harps_20261105_c034_context/analysis/RESULTS_REPORT.md). All prior sections below are historical.

---

# Continue SETI from completed C033 / HD126093

Read [the current state](work_harps_20261105_c033_context/CONTINUATION_STATE.json), verify live GitHub refs and source hashes, and resume the exact next unfinished original route. Earlier method freezes and outputs remain preserved.

C033 is complete: original records 0265/0270/0274/0279, four own discovery references, six reused observations, 28 profiles and 128 comparisons. All four physical U labels remain. Raw Pearson is higher barycentrically in 20/20 directed nonself rows in both regions; normalized RMS is lower in 19/20 core and 17/20 surrounding rows. These are 14 unordered relationships and 6 reciprocal discovery pairs among six observations. Preserve all metric disagreements, including the reciprocal May surrounding pair.

All 28 profiles have full 601-point finite raw/scaled support and positive references. Eight low-reference flags and 14 profiles with nonpositive original samples remain; ERR has no positive finite support. All eight original mapping chains are true. All eight original raw containers and 112 member-support records remain. The 0274 own order 4 possible off-trace deposit/blend caution is distinct from its broad centered component and is not transferred. Two original cores match the common 3880.35±0.25 core; two differ. No original-core-union fit or origin claim follows.

Nine physical source IDs are shared with C031 but their current original-index windows are disjoint; five native/order IDs are additional reused contexts. Earlier C033 epoch/raw values and six observations were already exposed, so no source-pixel independence or blind validation is claimed. The public 25-file method readback preceded current values. Separate reconstruction passes 791 checks over 110,049 values; 50 NPZ containers and 6 fixed PNGs decode and all figures were inspected by the same assistant. One successful production execution; no calibrated significance, linewidth, sensitivity, qualified laser or survey null.

## Exact next action: C034 at original queue row 73

Use [NEXT_ACTION](work_harps_20261105_c033_context/NEXT_ACTION.json), selected before C033 values. Singleton V2E2-0271 on HD126093 retains exact original 4312.202499999999 air Å center and its own May 29 discovery ADP.2025-05-30T01:00:44.357 with its own negative BERV. Restore its own native/raw inputs, scan all 72 native orders and freeze its separate geometry and reference handling. Do not transfer C033 April anchor, orders 3/4, support, low flags, mapping stages or 0274 caution. C032 remains pending later in original queue order.

Completed exact C001–C023, C028–C031, C033 and ten earlier bounded baseline diagnoses remain closed despite physical U. Do not replay extraction, mapping, registration, normalization, spatial or epoch pipelines. Rubin remains STOPPED_LIMITED_FEASIBILITY_MINIMUM50_UNMET. No background science job is running.

## Publication and integration

The current direct user message approves publication and requests continuation. C031 PR #28 passed exact-head CI and merged at 922b78780f690b70d9560956008818152e92f422; main and optical-harps-week-20261101 were synchronized before this method. Earlier C031 publication holds are historical. Publish exact C033 results, verify the public snapshot and passing final-head CI, then merge with expected-head guards and synchronize the work branch. Verify real PR/refs; creation-time state fields do not assert later integration already happened.

[Full report](work_harps_20261105_c033_context/analysis/RESULTS_REPORT.md) · [Closure](work_harps_20261105_c033_context/GROUP_CLOSURE.json).

---

# C031 published with direct approval — 5 November 2026

The user explicitly approved publication and requested continuation. The complete C031 result snapshot is public on `codex/seti-c031-20261105`; [publication receipt](work_harps_20261105_c031_context/PUBLICATION_RECEIPT.json) verifies all 109 phase-file blob identities and the report body. The 111 uploaded files match the exact original result tree. All scientific outputs remain unchanged.

Use [the current public continuation state](work_harps_20261105_c031_context/PUBLIC_CONTINUATION_STATE.json) and the [exact C033 handoff](work_harps_20261105_c031_context/NEXT_ACTION.json). Verify actual PR/refs and successful final-head CI before integration. The prior publication hold is resolved by the direct user message recorded in USER_PUBLICATION_APPROVAL.json. Earlier local-only notes below describe their creation time.

C031 was fixed locally before observed arithmetic; its later publication is not public preregistration. The completed diagnostic stays closed. Continue with C033 at queue row67,not a C031 rerun. No background science job is running.

---

# Continue SETI from completed local C031 / HD126093

Read [the current local state](work_harps_20261105_c031_context/CONTINUATION_STATE.json) and verify real GitHub refs before any publication. Earlier states, methods and outputs remain preserved.

C031 is complete: four original records 0264/0269/0277/0282, four discovery references, six reused observations, 28 profiles and 128 comparisons. All four physical U labels remain. Separate reconstruction passes 791 checks over 109,709 values. All 50 NPZ containers and six fixed scientific PNGs decode; the same assistant inspected all figures. Original raw evidence and mapping stages remain exact.

The core and surrounding pattern each favor barycentric raw correlation and normalized RMS in 19 of 20 directed nonself comparisons. These are 14 unordered relationships and six reciprocal discovery pairs among only six observations. Preserve the distinct May core and June surroundings exceptions. Eight native order-2 profiles are partial; June 27 and July 16 barycentric order-2 profiles are raw-only; July 16 topocentric order 2 has a low reference. All 112 original-member support records remain. No qualified laser, physical origin, blind validation or calibrated null is claimed.

## Public disclosure hold

C030 PR #27 was merged at 48dc62d0b2fb063254f57f3135ce794a560a0000; main and optical-harps-week-20261101 were synchronized there. Automatic approval review blocked C031 push twice, requiring fresh direct authorization for this specific public disclosure despite prior standing permissions. Do not bypass that restriction. C031 has a verified LOCAL method commit before observed arithmetic and makes no public-preregistration claim. Publish only after the requested direct user approval; then run exact-head CI and use guarded integration. Inspect live refs: this local note does not imply C031 was uploaded.

## Next original science route: C033, queue row 67

Use [the exact metadata handoff](work_harps_20261105_c031_context/NEXT_ACTION.json), selected before C031 values. Four original records 0265/0270/0274/0279 retain four own discovery references at proposed metadata midpoint 3880.35 air Å on HD126093. The midpoint is not a new frozen method. Restore own native/raw products, scan all 72 native orders per discovery and freeze original/common geometry and quality handling. Do not transfer C031 partial-coverage, missing-flank or low-reference outcomes. C033 is next by original queue index; C032 remains pending later in that ordering.

Completed exact C001–C023, C028–C031 and the ten earlier bounded baseline diagnoses remain closed despite physical U. Do not replay extraction, mapping, registration, normalization, spatial or epoch pipelines. Rubin remains STOPPED_LIMITED_FEASIBILITY_MINIMUM50_UNMET. No background science job is running.

[Full local report](work_harps_20261105_c031_context/analysis/RESULTS_REPORT.md) · [Local closure](work_harps_20261105_c031_context/GROUP_CLOSURE.json).

---

# Continue SETI from completed C030 / HD126093

Read [the current state](work_harps_20261104_c030_context/CONTINUATION_STATE.json),verify current GitHub heads and source hashes,and resume the exact next unfinished route. Earlier methods and numerical products remain preserved.

C030 is complete:32profiles,160comparisons,8original records and5discovery references on6existing observations. All8physical U labels remain. The metadata midpoint3867.13125Å common core differs from every original member core;256support records retain all original cores. Barycentric raw Pearson wins24of25directed nonself rows and scaled RMS25of25in each region. These25rows are15unordered relationships with10reciprocal pairs. Preserve the June25/June27correlation exception.

Ten native order2profiles have partial broad-edge coverage but sufficient normalization/common support. July16order2has low reference flags in both frames. All16raw containers and exact per-event mapping/review stages remain. Twelve C029source windows overlap and4additional June/July native windows reuse existing observations. No independence,blind validation,physical origin,qualified laser,measured linewidth or calibrated survey null is claimed.

Validation:3,344byte/header checks with360fresh header-order records;132compact synthetic checks;1,449separate scalar preflight checks over73,014values;930observed reconstruction checks over127,836values. All64NPZ containers and9figures decode; all figures inspected by the same assistant. All70frozen source bindings remain intact. One successful observed production execution.

## Exact next action: C031 at original row66

Use [NEXT_ACTION](work_harps_20261104_c030_context/NEXT_ACTION.json),selected before C030values. Four original members0264/0269/0277/0282 on HD126093 retain four own discovery references across six cohort observations. Proposed metadata midpoint3868.1499999999996Å is not a frozen method. Restore all four own native products and original raw contexts,freshly scan all72orders each,and freeze original/common core differences before current arithmetic. Order2may lose more broad-window and positive-flank support; retain missing,invalid,low and raw-only outcomes. Do not transfer C030coverage,mapping stages or absent blend cautions.

Completed original routesC001–C023,C028,C029,C030 and the ten exact baseline routes remain closed despite physical U. Do not replay normalization,mapping,spatial,registration,raw extraction or epoch pipelines. Rubin remains STOPPED_LIMITED_FEASIBILITY_MINIMUM50_UNMET; no background science job is running.

## GitHub authorization and integration

The user already authorizes autonomous continuation and updates to GitHub,including main and optical-harps-week-20261101. Publish exact method before current values,preserve one-shot outputs,verify byte-exact delivery,pass exact-head CI,then merge with expected-head guards and fast-forward the work branch. Verify real current refs/PR state before continuing; receipt/state integration fields describe their creation time. No new permission question is required for this standing scope.

[Full report](work_harps_20261104_c030_context/analysis/RESULTS_REPORT.md) · [Closure](work_harps_20261104_c030_context/GROUP_CLOSURE.json).

---

# Continue SETI from completed C029 / HD126093

Read [the current state](work_harps_20261104_c029_context/CONTINUATION_STATE.json), verify current GitHub heads and source hashes, and resume the exact next unfinished route. All earlier states, methods and numerical outputs remain preserved.

## Completed C029 — 4 November 2026

Six existing April–July2025 observations, three exact original records0261/0266/0272, three own discovery references,24profiles and96comparisons are complete at3866.125air Å. All three original centers/cores are identical; one first-queue April common topocentric anchor retains both May references. Every directed nonself pair favors barycentric raw correlation and normalized RMS in both core and surroundings. All three records remain U,without physical origin,qualified laser,significance,sensitivity or a calibrated null.

Each reference retains five other epochs. Per frame/region15directed rows are12distinct unordered relationships with3reciprocal discovery pairs,within only six observations. Twelve self rows remain labelled. References,reciprocal pairs and same-exposure native/merged extraction are dependent evidence.

All24profiles have full finite601-point raw/scaled support,positive references and false low flags. Eight frame-profile rows from four observing products retain nonpositive original samples; ERR has no positive finite support. All six own native/order contexts and original raw containers remain. Original local/baseline failures apply to0261/0266,while0272 has original support; global/later support is true for all. The0261 off-trace compact deposit/blend caution remains specific to that record and does not dispose of the broad centered component.

[Full report and six figures](work_harps_20261104_c029_context/analysis/RESULTS_REPORT.md) · [Closure](work_harps_20261104_c029_context/GROUP_CLOSURE.json). The public method and exact23-file readback preceded current values. Separate reconstruction passes675checks over95,862values. Separate scalar formulas and processes run by the same assistant are not independent human or separate-agent review. One successful observed run completed this fixed diagnostic.

Eight source windows share exact original points with C028:all six merged products and two April native orders. Four additional May native/order windows are existing discovery observations,not new observations. [Source-index audit](work_harps_20261104_c029_context/independent_audit/SOURCE_PIXEL_DEPENDENCY_AUDIT.json) reads prior metadata only. No independent pixels,blind validation or added observing time is claimed.

## Next unfinished route: C030

Use [the exact handoff](work_harps_20261104_c029_context/NEXT_ACTION.json):C030 on HD126093,original row64 onward. Include all eight records0262/0263/0267/0268/0273/0275/0276/0281 across R031/R032 and five own discovery products,against the same six epochs. Preserve every original center,member-core bound,own reference/BERV and mapping/review stage. Deduplicate physical native products without dropping event identities or original raw contexts.

Original centers span3866.935–3867.3275 Å. The metadata midrange proposal3867.13125 Å is not a claim that a common±0.25core covers the full original member-core union. Freeze the next group’s own common/member geometry explicitly before new arithmetic. Freshly scan all72native headers per discovery; order2 can approach the broad-window/flank boundary,so retain partial or invalid support. Do not inherit C029 full-coverage,positive-reference quality or0261-specific contamination caution.

C030 was selected before C029 values. Every next original member core already lies within current C029 broad context,and none intersects its positive flank. This differs from C028/C029 partial reciprocal core/flank intersections. Observations,windows and source pixels remain dependent; no masks or blind/independent-validation claim follow. Any distinct future statistic needs its own fixed plan and calibration.

## Closed routes, publication and preservation

All exact C001–C023,C028 and C029 diagnoses remain closed,including C013/C014 normalization. The ten earlier exact bounded baseline diagnoses stay closed with physical U unchanged; source-bound proof remains in the state. Four HD135204 zero-selection results are not archive-wide absence. All mapping and separate0235 spatial/background diagnoses remain closed. Do not replay a completed route solely because origin remains U.

[C028 PR #25](https://github.com/andersenmartin-blip/setisearch/pull/25) is merged and both previous heads were synchronized at the C029 baseline; [integration receipt](work_harps_20261104_c029_context/C028_INTEGRATION_RECEIPT.json). GitHub updates to main and optical-harps-week-20261101 remain explicitly authorized. Check expected heads and successful exact-head tests before merging. Earlier approval holds below are historical.

[Preservation instructions](work_harps_20261104_c029_context/preservation/README.md) bind12source windows,24profiles and6original raw containers,42NPZs in total,and six scientific PNGs. Restore full archived inputs without a live ESO query; reproduce separately and preserve closed outputs. Survey exposure and provisional codes are unchanged. Rubin remains limited feasibility:190main objects,2primary and4secondary evaluable objects including those primary2; minimum50unmet. Reopen only a distinct qualified public-history route. No unattended science search is configured.

---

All continuation sections below are historical and do not supersede the C030 handoff above.

# Continue SETI from completed C028 / HD126093

Read [the current state](work_harps_20261104_c028_context/CONTINUATION_STATE.json), verify current GitHub heads and source hashes, then resume the exact next route below. Previous states, method freezes and numerical outputs remain preserved.

## Latest completed C028 — 4 November 2026

Six existing April–July 2025 HD126093 epochs, one own April 27 discovery reference, sixteen profiles and thirty-two comparisons are complete at exact catalog center 3864.5550000000003 air Å. All five other epochs favor barycentric raw correlation and normalized RMS in both original core and surrounding spectrum. V2E2-0260 remains U; no physical origin, qualified laser, significance, sensitivity or calibrated survey null is established.

All sixteen profiles retain full 601-point finite raw/scaled support, positive references and false low flags. Four frame-profile rows from two exposures retain nonpositive original samples. ERR has no positive finite support. Both own native orders 2/3 and original raw containers remain. Original global support, local/baseline failures and later five-window support are distinct. The separate reconstruction passes 439 checks over 63,658 values. The method and exact 23-file public readback preceded current values. Separate formulas run by the same assistant are not independent human or separate-agent review.

[Full report](work_harps_20261104_c028_context/analysis/RESULTS_REPORT.md) · [Closure](work_harps_20261104_c028_context/GROUP_CLOSURE.json). The original renderer inherited R021 in two merged-image titles; separate copies correct only that label to R029 while all data pixels, original four PNGs and original method remain unchanged. All six delivered PNGs were inspected and decoded. An initial release JSON-format validation failure read no observed arrays and created no result directory; its newline-only repair is recorded. One successful observed execution completed C028.

## Next unfinished route: C029

Use [the exact handoff](work_harps_20261104_c028_context/NEXT_ACTION.json): C029/R030 on HD126093 at exact 3866.125 air Å, starting at original row 63. Include all three records0261/0266/0272 and their three own discovery references (April 27, May 29 and May 30 2025), against all six existing target epochs. Retain original per-record/order mapping stages. In particular0261 has a compact off-trace deposit/possible blend distinct from its broader centered component; do not transfer that feature to0260 or use it to dispose of the broad component.

Restore the three own native discovery products and all original raw-order containers from batch04 archives. Freshly scan all72headers per product, preserve each original catalog center and discovery reference, then freeze a separate complete joint comparison before current values. No0260 mapping or positive-reference outcome is transferred.

C029 was selected before C028 values. Nominal ±3 Å windows overlap by4.430000000000291 Å. C029's center is inside C028's positive flank, but only part of its core is. C028's core also only partly intersects C029's negative flank. Products and native lineage are shared; preserve source-index dependence, retain structured flank samples and make no independence or blind-validation claim. No masks, fitted-width models or background variants are authorized by this metadata handoff alone; any distinct future analysis needs its own fixed plan and calibration.

## Closed routes, publication and preservation

C001–C023 and C028 exact diagnoses are complete; C013/C014 are completed normalization routes. The ten exact earlier bounded baseline routes stay closed, with physical U unchanged and source-bound proof linked from the state. Four HD135204 zero-selection results are not archive-wide absence. All mapping and separate0235 spatial/background diagnoses remain closed. Never replay an exact finished route solely because origin remains U.

[C020 PR #24](https://github.com/andersenmartin-blip/setisearch/pull/24) was merged and both previous heads synchronized at the C028 baseline; [integration receipt](work_harps_20261104_c028_context/C020_INTEGRATION_RECEIPT.json). GitHub updates to main and optical-harps-week-20261101 remain explicitly authorized. Verify expected heads and passing checks before integration. Older approval holds below are historical.

[Preservation instructions](work_harps_20261104_c028_context/preservation/README.md) bind eight source windows, sixteen profiles and two original raw containers. Restore full archived inputs without a live ESO query and reproduce separately. Survey exposure and provisional labels are unchanged. Rubin remains limited feasibility:190 main objects,2 primary and4 secondary evaluable objects including the primary2; minimum50unmet. Reopen only a distinct qualified public-history route. No unattended science search is configured.

---

All continuation sections below are historical and do not supersede the C029 handoff above.

# Continue SETI from completed C020 / HD114783

Read [the current machine-readable state](work_harps_20261104_c020_context/CONTINUATION_STATE.json), verify current GitHub heads and source hashes, and resume the exact unfinished route below. All earlier states and method freezes remain unchanged.

## Latest completed C020 context — 4 November 2026

Seven existing target epochs, one own May 15 2023 discovery reference, sixteen profiles and thirty-two comparisons are complete at the exact original 4303.13 Å center. All six other epochs favor barycentric raw correlation and normalized RMS in both core and surrounding spectrum. V2E2-0136 remains U. No physical-origin assignment, qualified laser, significance or calibrated survey null follows.

All sixteen profiles retain full finite support, positive pooled flank references, false low flags and zero positive finite ERR samples. Native order 19 and the byte-exact original raw container remain. The separate reconstruction passes 480 checks over 63,829 values; four figures were inspected and fully decoded. The public fixed method and exact 24-file readback preceded current values. Separate formulas run by the same assistant are not independent human or separate-agent review.

The source-index audit records 17 shared original samples with C021 in the July 2023 product and none in the other six. Nominal barycentric windows are disjoint, but both-frame source unions govern dependence. Prior epoch/raw values and these seven observations were already exposed. No source-pixel independence, blind validation or added observing time is claimed.

[Full report](work_harps_20261104_c020_context/analysis/RESULTS_REPORT.md) · [Closure](work_harps_20261104_c020_context/GROUP_CLOSURE.json) · [Dependency audit](work_harps_20261104_c020_context/independent_audit/SOURCE_PIXEL_DEPENDENCY_AUDIT.json).

## Next unfinished original-queue route

Use [the exact C028 handoff](work_harps_20261104_c020_context/NEXT_ACTION.json): C028/R029/V2E2-0260 on **HD126093**, original row 62, exact catalog center **3864.5550000000003 Å**. This was selected before C020 values. Use the six existing April–July 2025 observations, its own April 27 discovery ADP.2025-04-28T01:01:15.579, BERV 5.77068898867443 km/s and cohort span 29.26984563734743 km/s. Restore own raw batch04 sources and freshly scan all 72 native headers before freezing separate signed normalization, frames, support, comparisons and figures. Historical orders 2/3 retain original global support, local/baseline failures and later five-window support as separate stages. No HD114783 seven-epoch count, May reference, order-19 scope, 59.073 km/s span or quality outcome is transferred.

All exact C001–C023 routes are complete; C013/C014 are normalization diagnoses with physical U unchanged. Also skip ten exact earlier FRAME_BASELINE_CONTEXT routes, proved in [the source-bound skip record](work_harps_20261104_c020_context/scientific_review/COMPLETED_ROUTE_SKIP_PROOF.json): HD122640 0229/0231/0234/0235/0236/0237 and HD135204 0303/0305/0308/0309. The six HD122640 records already have bounded BERV and separate May-quality comparisons. Four HD135204 records retained no new selected epoch under bounded filters, which is not archive-wide absence. The separate 0235 spatial/background route is also closed. Physical U does not reopen any exact completed route.

## Publication and preservation

[C023 PR #23](https://github.com/andersenmartin-blip/setisearch/pull/23) is merged and the previous work branch was synchronized at the C020 baseline. [Integration receipt](work_harps_20261104_c020_context/C023_INTEGRATION_RECEIPT.json). The user explicitly authorizes GitHub updates, including main and optical-harps-week-20261101; earlier approval holds are historical. Preserve method freezes, verify expected heads and complete checks before integration.

[Preservation instructions](work_harps_20261104_c020_context/preservation/README.md) bind eight bounded source windows, sixteen profiles and one original raw container. Full archived inputs restore without a live ESO query. Reproduce separately and preserve closed outputs. Rubin remains limited feasibility: 190 main objects, 2 primary and 4 secondary evaluable objects including those primary 2; minimum 50 unmet. Reopen only a distinct qualified public-history route. No unattended science search is configured.

---

All continuation sections below are historical and do not supersede the C028 handoff above.

# Continue SETI from completed C023 / HD114783

Read [the current machine-readable state](work_harps_20261104_c023_context/CONTINUATION_STATE.json), verify current GitHub heads and source hashes, and resume the exact queue below. The previous C017 state and all older checkpoints are preserved unchanged.

## Latest completed C023 context — 4 November 2026

Seven existing target epochs, one own February 5 discovery, sixteen profiles and thirty-two comparisons are complete at the exact original 5944.965 Å center. The surrounding spectrum has better barycentric raw correlation and normalized RMS in all six other epochs. In the original core, topocentric raw correlation is higher in five of six and topocentric RMS is lower in four of six. Preserve the distinction and the two metric-disagreement cases; no origin verdict, qualified laser, significance or calibrated survey null follows. V2E2-0122 remains U.

All sixteen profiles have full 601-point finite raw/scaled support, positive fixed references, false low flags and zero positive finite ERR support. Sole native order 57 and the exact original raw container remain; all historical mapping stages are true but the original asymmetric/flat-topped ambiguity remains. A separate reconstruction passes 437 checks and 63,569 scalar comparisons. All four figures were inspected and decoded. The fixed method and 23-file public readback preceded observed values.

[Complete report](work_harps_20261104_c023_context/analysis/RESULTS_REPORT.md) · [Closed diagnostic](work_harps_20261104_c023_context/GROUP_CLOSURE.json). Same-assistant separate arithmetic is not independent human or separate-agent review. These are reused observations and previously exposed 0122 epoch/raw evidence; no extra observing time or blind validation is claimed.

## Next original-queue route

Use [the exact C020 handoff](work_harps_20261104_c023_context/NEXT_ACTION.json): singleton C020/R021, V2E2-0136 on HD114783 at 4303.13 Å, original queue row 53. It was selected before C023 values. Use its own May 15 2023 discovery reference and BERV, not C023's February reference. Restore original raw/native/mapping/review sources, freshly scan all 72 own native headers, then freeze separate fixed frames, normalization, support and figures before new observed arithmetic. No C023 order-57 scope or quality is transferred.

C001–C019 and C021–C023 are complete as their exact routes; C013/C014 are completed normalization routes with physical U unchanged. C020 remains pending. Do not replay completed mapping, normalization, epoch/raw or context pipelines merely because origin remains U. Rubin is still limited feasibility: 190 selected main objects, 2 primary and 4 secondary evaluable objects including the primary 2; minimum 50 unmet. Reopen only a distinct route with adequate public history, provenance and quality.

## Publication and preservation

[C017 PR #22](https://github.com/andersenmartin-blip/setisearch/pull/22) has been merged and the existing work branch synchronized. The user explicitly authorizes GitHub updates, including main and optical-harps-week-20261101. The old pending-approval records below are historical; [the integration receipt](work_harps_20261104_c023_context/C017_INTEGRATION_RECEIPT.json) supersedes them. Preserve scientific method freezes, verify expected branch heads and complete checks before merging further work.

[Preservation instructions](work_harps_20261104_c023_context/preservation/README.md) bind eight source windows, sixteen profiles and one original raw container. Full archived inputs restore without a live ESO query. Reproduce separately and preserve closed one-shot outputs. No unattended science search is configured.

---

All continuation sections below are historical and do not supersede the C020 handoff above.

# Continue SETI from completed C017 / HD114783

The current reviewed work is on **codex/seti-c017-20261104**. Read [the current machine-readable state](work_harps_20261104_c017_context/CONTINUATION_STATE.json) and verify current branch heads before new work. Integration into main and optical-harps-week-20261101 is pending approval; their older C022 entry point must not cause C017 to be replayed.

## Latest completed C017 individual context — 4 November 2026

Seven existing HD114783 epochs,one own February 5 discovery reference,eighteen profiles and thirty-six comparisons are complete at exact original 3868.175 Å center. All six other epochs have higher barycentric raw correlation and lower normalized RMS in both original core and surrounding spectrum. The rounded central crest and neighboring pattern recur,with amplitude differences. V2E2-0118 remains U; no physical origin,qualified laser,significance or calibrated survey null follows.

Order 2 covers 518 of 601 grid points and has 467 surrounding comparison points,above the fixed 440 gate. It retains 163/77 finite negative/positive reference samples,so normalization is valid despite incomplete positive-flank wavelength coverage. Order 3 and all merged frame profiles have full 601-point support. All 18 profiles have valid positive reference levels and false low flags. Both original raw containers and order-2 original local/baseline failures remain. The separate arithmetic reconstruction passes 469 checks and 71,603 scalar comparisons. All four figures were inspected and decoded.

[Complete C017 report](work_harps_20261104_c017_context/analysis/RESULTS_REPORT.md) · [Closure](work_harps_20261104_c017_context/GROUP_CLOSURE.json). Exact method/input/public readback preceded current observed values. Separate implementations were run by the same assistant; no independent human or separate-agent review is claimed.

## Next original-queue route

Use [the exact C023 handoff](work_harps_20261104_c017_context/NEXT_ACTION.json): singleton C023/R024,V2E2-0122 on HD114783 at 5944.965 Å,original queue row 41. This was selected before C017 values and precedes C020 row 53. Use its own February 5 reference and seven existing target epochs. Restore original raw/native/mapping/review sources; freshly scan all 72 native headers and freeze a separate fixed context before observed C023 arithmetic. Do not inherit C017 orders 2/3,partial coverage or reference quality. The next bounded wavelength window is disjoint from recent same-target blue contexts but shares observations and existing epoch/raw history; no new observing time or blind validation.

C001–C019, C021 and C022 are complete as their exact diagnostic routes; C013/C014 normalization is complete. Do not reopen a completed diagnostic merely because physical U remains. All 35 mapping diagnoses and prior epoch/raw pipelines remain closed.

Rubin is still the completed limited feasibility study: 190 selected main objects, 2 numerically evaluable primary objects and 4 secondary objects including those 2. Minimum 50 unmet; no qualified null. Reopen only a distinct prospective route with adequate public stellar history/provenance/quality. No unattended science search is configured.

## Restore and verify C017

[Preservation instructions](work_harps_20261104_c017_context/preservation/README.md) bind9 pre-interpolation source windows,18 derived profiles and2 byte-exact original rawcontainers,all committed with the results. Full inputs restore from the two existing exact archives without a live ESO query. Preserve all closed outputs and run reproduction in a separate copy. The previous C022 state remains unchanged and is linked from the current compact state.

---

The following C022continuation and earlier sections are historical; their next-action labels do not supersede the C023handoff above.

# Continue SETI from the completed C022 / HD114783 joint context

Read [the current machine-readable state](work_harps_20261103_c022_context/CONTINUATION_STATE.json), fetch current GitHub and compare its source hashes before new work. Another session may have advanced the project. The [previous accelerated checkpoint](work_seti_20261102_accelerated/CONTINUATION_STATE.json) is preserved unchanged. Rubin remains explicitly advanced to **2–8 November 2026**. Earlier checkpoints and calendar dates are historical.

## Latest completed C022 joint context

Each of the three fixed discovery references has higher barycentric raw correlation and lower barycentric normalized RMS against all six other epochs, in both the common core and surrounding window. All three current C022 codes remain U. The rounded central crest, neighboring structure and broader multi-peak spectrum align closely in barycentric coordinates, with amplitude/reference differences retained. This descriptive agreement does not assign physical origin, qualify a laser candidate, estimate significance or calibrate a null result.

[The 4312.24125 Å common-midpoint HD114783 context](work_harps_20261103_c022_context/README.md) is complete: seven existing target-specific epochs, three distinct discovery products, 20 profiles and 96 comparison slots. All three records remain U. All 25 method/input files were read back from `d1ad1e0e8aa6e29c20236929ffb78cbdb0e4667c` before execution. The exact common scientific center is `4312.241249999999` Å. The first January 2022 discovery defines only the common anchor; all three references and exact original markers remain explicit.

The common midpoint ±0.25 Å metric core is not the full union of the three original member cores: their edge shifts are ±0.00375 Å. All three exact catalog markers and original core bounds remain explicit, and the full wavelength intervals of all three original cores lie within the fixed ±3 Å spectral context. Finite profile coverage is reported separately. Raw panels retain their original crop geometry separately from spectral core coverage. A common-window statistic does not separately classify each nearby feature.

Each of the three fixed discovery references compares six other epochs per frame and region: 18 directed source/reference pairs but only 15 distinct unordered observation-pair relationships, including 3 reciprocal discovery-pair repetitions. All use the same seven observations; neither the references nor reciprocal comparisons are independent confirmations.

20 of 20 profiles have full 601-point raw coverage; 20 have usable positive normalization, 0 are raw-only and 0 are blocked. Low-reference flags are 0 true, 20 false and 0 null. All 96 evaluable Pearson and 96 normalized RMS values are retained, including 12 labelled identical-product self-comparisons; 0 Pearson slots and 0 RMS slots remain explicitly unevaluable. Positive finite ERR support is absent in 20 profiles. No finite original source sample in the retained windows or reference flanks is nonpositive (0 of 20 profile rows). merged: 0 nonpositive samples among 600 finite original source samples per window; native: 0 nonpositive samples among 512–515 finite original source samples per window. Frame rows reuse their source observations; all original signs are retained without clipping.

3 of seven metadata-predicted group centers remain inside the fixed January-anchor ±0.25 Å topocentric core and 4 lie outside. These are predicted centers rather than fitted peaks or full finite-feature coverage. No epoch or discovery reference is recentered; a fixed-window comparison can include neighboring structure after a predicted center leaves the core. Frame statistics are descriptive, not calibrated origin tests.

C022 reuses the same seven HD114783 January 2022–July 2023 observations and native lineage as C021, with fixed discovery references observed on January 21 and May 5 2022 and January 16 2023. February 5, March 22, May 15 and July 1 remain non-reference epochs. The C022 and C021 bounded windows share 3.585000000000946 Å of the same spectral source pixels. The entire C022 common core was already exposed inside the C021 positive reference flank; conversely the entire C021 common core lies inside the C022 negative reference flank. Structured pooled flanks retain both features without masks or a line-free claim. This is directly reused spectral evidence, not an untouched or independent test. Original C022 epoch/profile/raw evidence and the completed 0131 wider mapping diagnosis already existed; no observing time is added. Complete historical raw crops retain their original geometry separately; other-target numeric overlaps share no source pixels or observing products.

All three order-19 global/later stages remain true and all three original local/baseline stages remain false. Original 0131 I/M-normalized-I/baseline-I and later U/U/current-U are retained separately from the two batch03 U/U/U histories; no physical origin is assigned. [Independent arithmetic](work_harps_20261103_c022_context/independent_audit/NUMERICAL_AUDIT.json) passes 698 checks / 79,403 scalars. [Report and figures](work_harps_20261103_c022_context/analysis/RESULTS_REPORT.md). No new observations, acquisition, free fits or old pipeline replay were added.

## Earlier completed C021 joint context

All five fixed discovery references have higher barycentric raw correlation and lower barycentric normalized RMS against all six other epochs, in both the common core and surrounding window. All five current C021 codes remain U. The rounded central crest and wider multi-peak spectrum align closely in barycentric coordinates, with retained amplitude and reference-level differences. These descriptive comparisons do not identify a line or physical origin, qualify a laser candidate, estimate significance or calibrate a null result.

[The 4309.82625 Å common-midpoint HD114783 context](work_harps_20261103_c021_context/README.md) is complete: seven existing target-specific epochs, five distinct discovery products, 24 profiles and 160 comparison slots. All five records remain U. All 25 method/input files were read back from `d19abc6b1e4b23e4b6c5e4286ecf74ae5edc2a32` before execution. The exact common scientific center is `4309.82625` Å. The first January 2022 discovery defines only the common anchor; all five references and exact original markers remain explicit.

The common midpoint ±0.25 Å metric core is not the full union of the five original member cores: their edge shifts are ±0.00125 Å. All five exact catalog markers and original core bounds remain explicit, and the full wavelength intervals of all five original cores lie within the fixed ±3 Å spectral context. Finite profile coverage is reported separately. Raw panels retain their original crop geometry separately from spectral core coverage. A common-window statistic does not separately classify each nearby feature.

Each of the five fixed discovery references compares six other epochs per frame and region: 30 directed source/reference pairs but only 20 distinct unordered observation-pair relationships, including 10 reciprocal discovery-pair repetitions. All use the same seven observations; neither the references nor reciprocal comparisons are independent confirmations.

24 of 24 profiles have full 601-point raw coverage; 24 have usable positive normalization, 0 are raw-only and 0 are blocked. Low-reference flags are 0 true, 24 false and 0 null. All 160 evaluable Pearson and 160 normalized RMS values are retained, including 20 labelled identical-product self-comparisons; 0 Pearson slots and 0 RMS slots remain explicitly unevaluable. Positive finite ERR support is absent in 24 profiles. No finite original source sample in the retained windows or reference flanks is nonpositive (0 of 24 profile rows). merged: 0 nonpositive samples among 600 finite original source samples per window; native: 0 nonpositive samples among 504–507 finite original source samples per window. Frame rows reuse their source observations; all original signs are retained without clipping.

3 of seven metadata-predicted group centers remain inside the fixed January-anchor ±0.25 Å topocentric core and 4 lie outside. These are predicted centers rather than fitted peaks or full finite-feature coverage. No epoch or discovery reference is recentered; a fixed-window comparison can include neighboring structure after a predicted center leaves the core. Frame statistics are descriptive, not calibrated origin tests.

C021 reuses the same seven HD114783 January 2022–July 2023 observations as C018/C019, with five fixed discovery references. The July 1 reference replaces the C019 May 15 reference; March 22 and May 15 remain non-reference cohort epochs. The newly bounded C021 ±3 Å spectral window is disjoint from the completed blue C018/C019 windows, although observing products and native files are shared. Complete historical raw crops retain their original geometry separately. Numeric overlap with C006/C007 is a different target with no shared source pixels; the neighboring other-target C016 window is disjoint. Original C021 epoch/profile/raw evidence and the completed 0130 wider mapping diagnosis already existed; these are reused observations, not blind, untouched or independent new data or added observing time.

All five order-19 global/later stages remain true. Original local/baseline failures for 0116/0126/0130 and supported original stages for 0121/0139 remain distinct. Original 0130 I/M-normalized-I/baseline-I and later U/U/current-U are retained; no physical origin is assigned. [Independent arithmetic](work_harps_20261103_c021_context/independent_audit/NUMERICAL_AUDIT.json) passes 834 checks / 94,802 scalars. [Report and figures](work_harps_20261103_c021_context/analysis/RESULTS_REPORT.md). No new observations, acquisition, free fits or old pipeline replay were added.

## Earlier completed C019 joint context

Each of the five fixed discovery references has higher barycentric raw correlation and lower barycentric normalized RMS against all six other epochs, in both the common core and surrounding window. All five original/current C019 labels remain U. The central rounded feature, neighboring troughs and wider structured pattern recur with retained amplitude/reference differences. These descriptive comparisons do not identify a line or physical origin, qualify a laser candidate, estimate significance or calibrate a null result.

[The 3881.61375 Å common-midpoint HD114783 context](work_harps_20261103_c019_context/README.md) is complete: seven existing target-specific epochs, five distinct discovery products, 34 profiles and 180 comparison slots. All five records remain U. All 25 method/input files were read back from `5c1c049f3c04906fd4fdd5480557b5007fc86dec` before execution. The exact common scientific center is `3881.6137500000004` Å. The first January 2022 discovery defines only the common anchor; all five references and exact original markers remain explicit.

The common midpoint ±0.25 Å metric core is not the full union of the five original member cores: their edge shifts are ±0.00125 Å. All five exact catalog markers and original core bounds remain explicit, and the full wavelength intervals of all five original cores lie within the fixed ±3 Å spectral context. Finite profile coverage is reported separately. Raw panels retain their original crop geometry separately from spectral core coverage. A common-window statistic does not separately classify each nearby feature.

Each of the five fixed discovery references compares six other epochs per frame and region: 30 directed source/reference pairs but only 20 distinct unordered observation-pair relationships, including 10 reciprocal discovery-pair repetitions. All use the same seven observations; neither the references nor reciprocal comparisons are independent confirmations.

34 of 34 profiles have full 601-point raw coverage; 34 have usable positive normalization, 0 are raw-only and 0 are blocked. Low-reference flags are 0 true, 34 false and 0 null. All 180 evaluable Pearson and 180 normalized RMS values are retained, including 20 labelled identical-product self-comparisons; 0 Pearson slots and 0 RMS slots remain explicitly unevaluable. Positive finite ERR support is absent in 34 profiles. 6 of 34 profile rows retain nonpositive signed original samples. Valid positive pooled references do not imply positive individual samples. merged: 0 nonpositive samples among 600 finite original source samples per window; native: 0–10 nonpositive samples among 500–603 finite original source samples per window. Frame rows reuse their source observations; all signs are retained without clipping.

3 of seven metadata-predicted group centers remain inside the fixed January-anchor ±0.25 Å topocentric core and 4 lie outside. These are predicted centers rather than fitted peaks or full finite-feature coverage. No epoch or discovery reference is recentered; a fixed-window comparison can include neighboring structure after a predicted center leaves the core. Frame statistics are descriptive, not calibrated origin tests.

C019 reuses the same seven HD114783 January 2022–July 2023 observations as C018, with five fixed discovery references rather than all seven. The March 22 and July 1 observations remain non-reference cohort epochs. The newly bounded C019 ±3 Å spectral window is disjoint from C018, although observing products and some native files are shared; complete historical raw crops retain their original geometry separately. Numeric overlap with older C005 is a different target and shares no products or source pixels. Original C019 epoch/profile/raw evidence already existed; these are reused observations, not blind, untouched or independent new data or added observing time.

All ten original order-3/4 mapping stage triples remain true. Eight later fields are true and two older 0129 later fields remain null/unassessed. Original and current 0129 U/U/U are distinct from the separate C018/0128 history; no physical origin is assigned. [Independent arithmetic](work_harps_20261103_c019_context/independent_audit/NUMERICAL_AUDIT.json) passes 1,026 checks / 134,487 scalars. [Report and figures](work_harps_20261103_c019_context/analysis/RESULTS_REPORT.md). No new observations, acquisition, free fits or old pipeline replay were added.

## Earlier completed C018 joint context

Each of the seven fixed discovery references has higher barycentric raw correlation and lower barycentric normalized RMS against all six other epochs, in both the common core and surrounding window. All seven current C018 labels remain U. The rounded central feature, nearby trough and wider structured spectrum recur with retained differences. These comparisons do not identify a line or physical origin, qualify a laser candidate, estimate significance or calibrate a null result.

[The 3869.33375 Å common-midpoint HD114783 context](work_harps_20261103_c018_context/README.md) is complete: seven existing target-specific epochs, seven distinct discovery products, 42 profiles and 252 comparison slots. All seven records remain U. All 25 method/input files were read back from `514cece459dc1feefafbd2a6faef3958f00ce325` before execution. The first January 2022 discovery defines only the common anchor; all seven references and exact original markers remain explicit.

The common midpoint ±0.25 Å metric core is not the full union of the seven original member cores: their edge shifts are ±0.00125 Å. All seven exact catalog markers and original core bounds remain explicit, and the full wavelength intervals of all seven original cores lie within the fixed ±3 Å spectral context. Finite profile coverage is reported separately. Raw panels retain their original crop geometry separately from spectral core coverage. A common-window statistic does not separately classify each nearby feature.

Each of the seven fixed discovery references compares six other epochs per frame and region: 42 directed source/reference pairs but only 21 distinct unordered observation-pair relationships, including 21 reciprocal discovery-pair repetitions. All use the same seven observations; neither the references nor reciprocal comparisons are independent confirmations.

28 of 42 profiles have full 601-point raw coverage; 28 have usable positive normalization, 14 are raw-only and 0 are blocked. Low-reference flags are 0 true, 28 false and 14 null. All 238 evaluable Pearson and 224 normalized RMS values are retained, including 28 labelled identical-product self-comparisons; 14 Pearson slots and 28 RMS slots remain explicitly unevaluable. Positive finite ERR support is absent in 42 profiles. 12 of 42 profile rows retain nonpositive signed original samples. Valid positive pooled references do not imply positive individual samples. merged: 0 nonpositive samples among 600 finite original source samples per window; native: 0–6 nonpositive samples among 370–549 finite original source samples per window. Frame rows reuse their source observations; all signs are retained without clipping.

3 of seven metadata-predicted group centers remain inside the fixed January-anchor ±0.25 Å topocentric core and 4 lie outside. These are predicted centers rather than fitted peaks or full finite-feature coverage. No epoch or discovery reference is recentered; a fixed-window comparison can include neighboring structure after a predicted center leaves the core. Frame statistics are descriptive, not calibrated origin tests.

C018 changes target to HD114783 and uses its own seven existing January 2022–July 2023 observations, each a distinct discovery reference. No HD114386 product, May 2022 reference, numeric anchor, span or quality outcome is transferred. Numeric wavelength overlap with C015 and earlier other-target blue windows shares no source pixels or observing products. Original C018 epoch/profile/raw evidence and the completed V2E2-0128 wider mapping diagnosis already existed; these are reused observations, not blind, untouched or independent new data or added observing time.

Original order-2 local/baseline failures, supported global/later diagnostics and all-true order-3 stages remain separate. The original/later 0128 I/M-normalized-I/U history is retained; no physical origin is assigned. [Independent arithmetic](work_harps_20261103_c018_context/independent_audit/NUMERICAL_AUDIT.json) passes 1,268 checks / 161,625 scalars. [Report and figures](work_harps_20261103_c018_context/analysis/RESULTS_REPORT.md). No new observations, acquisition, free fits or old pipeline replay were added.

## Earlier completed C015 individual context

All six other HD114386 epochs agree better with the fixed May discovery profile in barycentric coordinates than in the fixed topocentric frame, in both the original core and surrounding window. V2E2-0095 remains U. The central multi-sample structure and surrounding spectrum recur with retained shape/amplitude differences. August 2023 is visibly noisier and less similar and remains included. These descriptive comparisons do not identify a line or physical origin, qualify a laser candidate, estimate significance or calibrate a null result.

[The 3869.915 Å HD114386 context](work_harps_20261103_c015_context/README.md) is complete: seven existing target-specific epochs, one May 2022 discovery reference, 16 profiles and 32 comparisons. The exact scientific center is `3869.915` Å; the fixed anchor uses BERV -10.767337430651 km/s. All 25 method/input files were read back from `622447cb88946e3e2f0020dc7dc59c99c081b11b` before execution.

4 of seven metadata-predicted centers remain inside the fixed May 2022 reference ±0.25 Å topocentric core and 3 lie outside. These are predicted centers rather than fitted peaks or full finite-feature coverage. No epoch is recentered; a fixed-window comparison can include neighboring structure after a predicted center leaves the core. Frame statistics are descriptive, not calibrated origin tests.

16 of 16 profiles have full 601-point raw coverage; 16 have usable positive normalization, 0 are raw-only and 0 are blocked. Low-reference flags are 0 true, 16 false and 0 null. All 32 evaluable Pearson and 32 normalized RMS values are retained, including 4 labelled identical-product self-comparisons; 0 Pearson slots and 0 RMS slots remain explicitly unevaluable under the fixed rules. Positive finite ERR support is absent in 16 profiles. 2 of 16 profile rows retain nonpositive signed original samples; valid positive pooled references do not imply positive individual samples. merged: 0–1 nonpositive samples among 600 finite original source samples per window; native: 0 nonpositive samples among 550 finite original source samples per window. Frame rows reuse their source observations. All signs remain unchanged; no clipping was introduced. The original order-3 context retains true at every original global/local/baseline and later five-window mapping stage. All U reviews and original epoch/raw evidence remain explicit.

C015 reuses the same seven HD114386 January 2022–August 2023 observations as C016, with its own May 16 2022 discovery reference and wavelength-specific anchor. That May product is one of the four C016 references; the C015 context is separate from the C016 order-19 window and completed blue normalization windows. Numeric overlap with older HD106515A and HD112410 contexts shares no source pixels or observing products because those are other targets. Original C015 epoch/profile/raw evidence already existed; these are reused observations, not blind, untouched or independent new data or added observing time.

[Independent arithmetic](work_harps_20261103_c015_context/independent_audit/NUMERICAL_AUDIT.json) passes 455 checks / 63,724 scalars. [Report and figures](work_harps_20261103_c015_context/analysis/RESULTS_REPORT.md). No new observations, acquisition, free fits or old pipeline replay were added.

## Earlier completed C016 joint context

For each of the four fixed discovery references, all six other HD114386 epochs agree better in barycentric coordinates than in the fixed topocentric frame, in both the common group core and surrounding window. V2E2-0094/0096/0098/0110 all remain U. The central rounded structure, nearby secondary rise and wider pattern recur with retained amplitude and shape differences. These descriptive comparisons do not identify a line or physical origin, qualify a laser candidate, estimate significance or calibrate a null result.

[The 4303.7875 Å common-midpoint HD114386 context](work_harps_20261103_c016_context/README.md) is complete: seven existing target-specific epochs, four distinct discovery products, 22 profiles and 128 comparison slots. All four records remain U. All 25 method/input files were read back from `d4283a5d145d747081058783f31826c8e4531837` before execution. The first March 2022 discovery defines only the common anchor; all four references and exact original markers remain explicit.

The common midpoint ±0.25 Å metric core is not the full union of the four original member cores: their edge shifts are ±0.0025 Å. All four exact catalog markers and original core bounds remain explicit, and the full wavelength intervals of all four original cores lie within the fixed ±3 Å spectral context. Finite profile coverage is reported separately. Raw panels retain their original crop geometry separately from spectral core coverage. A common-window statistic does not separately classify each nearby feature.

Each of the four fixed discovery references compares six other epochs per frame and region: 24 directed source/reference pairs but only 18 distinct unordered observation-pair relationships, including 6 reciprocal discovery-pair repetitions. All use the same seven observations; neither the references nor reciprocal comparisons are independent confirmations.

22 of 22 profiles have full 601-point raw coverage; 22 have usable positive normalization, 0 are raw-only and 0 are blocked. Low-reference flags are 0 true, 22 false and 0 null. All 128 evaluable Pearson and 128 normalized RMS values are retained, including 16 labelled identical-product self-comparisons; 0 Pearson slots and 0 RMS slots remain explicitly unevaluable. Positive finite ERR support is absent in 22 profiles. No finite original source sample in the retained windows or reference flanks is nonpositive (0 of 22 profile rows). merged: 0 nonpositive samples among 600 finite original source samples per window; native: 0 nonpositive samples among 485–488 finite original source samples per window. Frame rows reuse their source observations; all original signs are retained without clipping.

3 of seven metadata-predicted group centers remain inside the fixed March-anchor ±0.25 Å topocentric core and 4 lie outside. These are predicted centers rather than fitted peaks or full finite-feature coverage. No epoch or discovery reference is recentered; a fixed-window comparison can include neighboring structure after a predicted center leaves the core. Frame statistics are descriptive, not calibrated origin tests.

C016 changes target to HD114386 and uses its own seven existing January 2022–August 2023 observations with four distinct discovery products. No HD112410 product, May 2025 reference, numeric anchor, span or quality flag is transferred. The C016 window is disjoint from completed bounded contexts and prior blue normalization windows, while its original epoch/profile/raw evidence and these HD114386 observations already existed. These are reused observations, not blind, untouched or independent new data or added observing time.

All four original order-19 mapping contexts remain true at each historical stage; no physical origin is assigned. [Independent arithmetic](work_harps_20261103_c016_context/independent_audit/NUMERICAL_AUDIT.json) passes 700 checks / 86,525 scalars. [Report and figures](work_harps_20261103_c016_context/analysis/RESULTS_REPORT.md). No new observations, acquisition, free fits or old pipeline replay were added.

## Earlier completed C011 individual context

All six other epochs agree better with the fixed May discovery profile in barycentric coordinates than in the fixed topocentric frame, in both the original core and surrounding window. V2E2-0089 remains U. Both native orders have complete coverage and valid positive normalization. Order 2's two low-reference flags are true and its noisy signed variation remains explicit. These descriptive results do not identify a spectral line or physical origin, qualify a laser candidate, estimate significance or calibrate a null result.

[The 3865.6775 Å HD112410 context](work_harps_20261103_c011_context/README.md) is complete: seven existing target-specific epochs, one May 2025 discovery reference, 18 profiles and 36 comparisons. The exact scientific center is `3865.6775000000002` Å; the fixed anchor uses BERV -5.48386283255014 km/s. All 25 method/input files were read back from `dad9f542b6f7bb830f1020d373634012483e7b15` before execution.

All seven metadata-predicted centers remain inside the May-reference ±0.25 Å topocentric core (April −0.114616520 Å; August +0.160086601 Å). Predicted-center containment does not establish full finite-feature coverage.

18 of 18 profiles have full 601-point raw coverage; 18 have usable positive normalization, 0 are raw-only and 0 are blocked. Low-reference flags are 2 true, 16 false and 0 null. Flagged rows: native order 2 barycentric, native order 2 topocentric. Their usable positive normalizations are retained with the flags. All 36 evaluable Pearson and 36 normalized RMS values are retained, including 4 labelled identical-product self-comparisons; 0 Pearson slots and 0 RMS slots remain explicitly unevaluable under the fixed rules. Positive finite ERR support is absent in 18 profiles. 6 of 18 profile rows retain nonpositive signed original samples; valid positive pooled references do not imply positive individual samples. merged: 0–3 nonpositive samples among 599–600 finite original source samples per window; native: 3–29 nonpositive samples among 534–655 finite original source samples per window. Frame rows reuse their source observations. All signs remain unchanged; no clipping was introduced. Both orders 2 and 3 retain true at every original global/local/baseline and later five-window mapping stage; the prior C012 order 2 limitations do not transfer. All U reviews and original epoch/raw evidence remain explicit.

C011 reuses the same seven original HD112410 April–August 2025 observations as C010/C012, with its own May 28 discovery reference and wavelength-specific anchor. Its broader window overlaps C012 on the same observing products by 2.4100000000003092 Å, while the original C011 core lies outside the C012 window. Shared surrounding/reference pixels remain dependent evidence. Original C011 epoch/profile and raw evidence already existed; these are reused observations, not blind or independent new data or added observing time.

[Independent arithmetic](work_harps_20261103_c011_context/independent_audit/NUMERICAL_AUDIT.json) passes 481 checks / 71,203 scalars. [Report and figures](work_harps_20261103_c011_context/analysis/RESULTS_REPORT.md). No new observations, acquisition, free fits or old pipeline replay were added.

## Earlier completed C012 individual context

All six other HD112410 epochs agree better with the fixed discovery profile in barycentric coordinates than in the fixed topocentric frame, in both the original core and surrounding window. V2E2-0087 remains U. The central broad structure and surrounding peaks recur with retained shape, amplitude and reference-level differences. This is a descriptive comparison of saved spectra, without a line identification, physical-origin assignment, qualified laser candidate, significance estimate or calibrated null.

[The 3869.2675 Å HD112410 context](work_harps_20261103_c012_context/README.md) is complete: seven existing target-specific epochs, one April 2025 discovery reference, 18 profiles and 36 comparisons. The exact scientific center is `3869.2675` Å; the fixed anchor uses BERV 3.40485846065643 km/s. All 25 method/input files were read back from `3815808d874c9cf927da83dc287631e18de3bdd4` before execution.

16 of 18 profiles have full 601-point raw coverage; 16 have usable positive normalization, 2 are raw-only and 0 are blocked. Low-reference flags are 0 true, 16 false and 2 null. All 34 evaluable Pearson and 32 normalized RMS values are retained, including 4 labelled identical-product self-comparisons; 2 Pearson slots and 4 RMS slots remain explicitly unevaluable under the fixed rules. Positive finite ERR support is absent in 18 profiles. 4 of 18 profile rows retain nonpositive signed original samples; valid positive pooled references do not imply positive individual samples. merged: 0–3 nonpositive samples among 599–600 finite original source samples per window; native: 0–2 nonpositive samples among 423–546 finite original source samples per window. Frame rows reuse their source observations. All signs remain unchanged; no clipping was introduced. Order 2 original local/baseline mapping failures remain distinct from true global and later five-window diagnostics; order 3 retains all four true stages. All U reviews and original epoch/raw evidence remain explicit.

[Independent arithmetic](work_harps_20261103_c012_context/independent_audit/NUMERICAL_AUDIT.json) passes 481 checks / 70,371 scalars. [Report and figures](work_harps_20261103_c012_context/analysis/RESULTS_REPORT.md). No new observations, acquisition, free fits or old pipeline replay were added.

## Earlier completed C010 individual context

All six other HD112410 epochs align better with the fixed discovery profile in barycentric coordinates than in the fixed topocentric frame, in both the original core and surrounding window. V2E2-0086 remains U. The central broad structure and its surrounding pattern are present with substantial shape, amplitude and reference-level differences. The comparison describes these saved spectra; it does not identify a line or physical origin, qualify a laser candidate, establish significance or calibrate a null result.

[The 3823.065 Å HD112410 context](work_harps_20261103_c010_context/README.md) is complete: seven existing target-specific epochs, one April 2025 discovery reference, 16 profiles and 32 comparisons. The exact scientific center is `3823.0649999999996` Å; the fixed anchor uses BERV 3.40485846065643 km/s. All 25 method/input files were read back from `acb3a382b43ca0b9d3d13f3e30317383f591fb10` before execution.

16 of 16 profiles have full 601-point raw coverage; 16 have usable positive normalization, 0 are raw-only and 0 are blocked. Low-reference flags are 0 true, 16 false and 0 null. All 32 evaluable Pearson and 32 normalized RMS values are retained, including 4 labelled identical-product self-comparisons. Positive finite ERR support is absent in 16 profiles. 16 of 16 profile rows retain nonpositive signed original samples; valid positive pooled references do not imply positive individual samples. merged: 2–21 nonpositive samples among 600 finite original source samples per window; native: 3 nonpositive samples among 562 finite original source samples per window. Frame rows reuse their source observations. All signs remain unchanged; no clipping was introduced. Order 1 original local/baseline mapping failures remain distinct from true global and later five-window diagnostics. All U reviews and original epoch/raw evidence remain explicit.

[Independent arithmetic](work_harps_20261103_c010_context/independent_audit/NUMERICAL_AUDIT.json) passes 432 checks / 63,469 scalars. [Report and figures](work_harps_20261103_c010_context/analysis/RESULTS_REPORT.md). No new observations, acquisition, free fits or old pipeline replay were added.

## Earlier completed C009 individual context

The original C009 core differs from the March 2023 discovery in all six other epochs: barycentric raw Pearson is negative throughout, spanning -0.535854–-0.137821. The surrounding spectrum favors barycentric correlation and normalized RMS in all six comparisons, with r spanning 0.926466–0.959194. The core and surroundings therefore have different descriptive behavior. Higher fixed-topocentric core correlations and mixed core RMS outcomes may involve neighboring structure; they do not assign physical origin. V2E2-0050 remains U.

[The 6802.02 Å HD106515A context](work_harps_20261103_c009_context/README.md) is complete: seven existing epochs, one fixed March 2023 discovery reference, 16 profiles and 32 comparisons. Nonself barycentric core r spans -0.535854–-0.137821; surrounding-pattern r spans 0.926466–0.959194. All 25 method/input files were read back from `d1405bf95678d8225c18dc869d0de4b45c2fec76` before execution. The fixed anchor BERV is 3.26509772194068 km/s.

16 of 16 profiles have full 601-point raw coverage; 16 have usable positive normalization, 0 are raw-only and 0 are blocked. Low-reference flags are 0 true, 16 false and 0 null; unavailable normalization does not count as a false flag. All 32 evaluable Pearson and 32 normalized RMS values are retained, including 4 labelled identical-product self-comparisons. Positive finite ERR support is absent in 16 profiles. V2E2-0050 remains U. Historical order 70 mapping and the primary A / secondary A / adopted U distinction remain explicit. This wavelength window is separate from C001–C008, while original epoch/raw results and all seven observing products were reused.

[Independent arithmetic](work_harps_20261103_c009_context/independent_audit/NUMERICAL_AUDIT.json) passes 428 checks / 63,354 scalars. [Report and figures](work_harps_20261103_c009_context/analysis/RESULTS_REPORT.md). No new observations, acquisition, free fits or old pipeline replay were added.

## Earlier completed C008 individual context

[The 5182.005 Å HD106515A context](work_harps_20261102_c008_context/README.md) is complete: seven existing epochs, one fixed March 2023 discovery reference, 16 profiles and 32 comparisons. Nonself barycentric core r spans 0.844156–0.978778; surrounding-pattern r spans 0.992765–0.999513. All 25 method/input files were read back from `d194c32c3679cebb485f901ceccd1ac4786d66f6` before execution. The fixed anchor BERV is 3.26509772194068 km/s.

16 of 16 profiles have full 601-point raw coverage; 16 have usable positive normalization, 0 are raw-only and 0 are blocked. Low-reference flags are 0 true, 16 false and 0 null; unavailable normalization does not count as a false flag. All 32 evaluable Pearson and 32 normalized RMS values are retained, including 4 labelled identical-product self-comparisons. Positive finite ERR support is absent in 16 profiles. V2E2-0047 remains U. Historical order 43 mapping and asymmetric raw structure remain explicit. This wavelength window is separate from C001–C007, while original epoch/raw results and all seven observing products were reused.

[Independent arithmetic](work_harps_20261102_c008_context/independent_audit/NUMERICAL_AUDIT.json) passes 424 checks / 63,374 scalars. [Report and figures](work_harps_20261102_c008_context/analysis/RESULTS_REPORT.md). No new observations, acquisition, free fits or old pipeline replay were added.

## Earlier completed C002 individual context

[The 3868.6025 Å HD106515A context](work_harps_20261102_c002_context/README.md) is complete: seven existing epochs, one fixed May 2022 discovery reference, 18 profiles and 36 comparisons. Nonself barycentric core r spans 0.938800–0.980641; surrounding-pattern r spans 0.957488–0.986064. All 25 method/input files were read back from `264a6d5cfd8b0b40780df1f28b65986f50659b2e` before execution. The fixed anchor BERV is −18.8907517532076 km/s.

16 of 18 profiles have full 601-point raw coverage; 16 have usable positive normalization, 2 are raw-only and 0 are blocked. Low-reference flags are 0 true, 16 false and 2 null; unavailable normalization does not count as a false flag. All 34 evaluable Pearson and 32 normalized RMS values are retained, including 4 labelled identical-product self-comparisons. Positive finite ERR support is absent in 18 profiles. Both order 2 profiles retain 417 of 601 grid points and lack the right reference flank. Their raw core comparisons remain evaluable; their broad raw correlations and all normalized comparisons stay unavailable under the fixed support rules. The one available flank was not substituted for the missing reference. V2E2-0033 remains U. Historical mapping diagnostics and signed-flux limitations are preserved. The core was already visible in C003, and the wider context overlaps C004; shared flux and observations are explicit.

[Independent arithmetic](work_harps_20261102_c002_context/independent_audit/NUMERICAL_AUDIT.json) passes 456 checks / 71,071 scalars. [Report and figures](work_harps_20261102_c002_context/analysis/RESULTS_REPORT.md). No new observations, acquisition, free fits or old pipeline replay were added.

## Earlier completed C004 joint context

[The 3872.245 Å HD106515A context](work_harps_20261102_c004_context/README.md) is complete: seven existing epochs, all three distinct discovery references, 20 profiles and 96 comparisons. Nonself barycentric core r spans 0.925276–0.990102; surrounding-pattern r spans 0.967167–0.995102. All 25 method/input files were read back from `7c3e46e41fc98073c844259ab91350b8363bc63a` before execution. The fixed first-discovery anchor is the March 2022 observation, with BERV 10.77158288517 km/s.

20 of 20 profiles have full 601-point raw coverage; 20 have usable positive normalization, 0 are raw-only and 0 are blocked. There are 0 low-reference flags under the fixed rule. All 96 evaluable Pearson and 96 normalized RMS values are retained, including 12 labelled identical-product self-comparisons. Positive finite ERR support is absent in 20 profiles. All three records remain U. Their historical global/local/baseline/five-window mapping flags are preserved as true; this is not a new mapping or physical-origin classification. The core was already visible inside C003's positive reference flank, so shared flux and observations are explicit.

[Independent arithmetic](work_harps_20261102_c004_context/independent_audit/NUMERICAL_AUDIT.json) passes 559 checks / 79,803 scalars. [Report and figures](work_harps_20261102_c004_context/analysis/RESULTS_REPORT.md). No new observations, acquisition, free fits or old pipeline replay were added.

## Earlier completed C007 individual context

[The 4312.700 Å HD106515A context](work_harps_20261102_c007_context/README.md) is complete: seven existing epochs, one discovery reference, 16 profiles and 32 comparison slots. Nonself barycentric core r spans 0.959862–0.969939; surrounding-pattern r spans 0.983174–0.987315. All 25 method/input files were read back from `57b5af70c88a3a4ee5fe8f9224ac805a7c3c438a` before this execution.

16 of 16 profiles have full 601-point raw coverage; 16 have usable positive normalization, 0 are raw-only and 0 are blocked. There are 0 low-reference flags under the fixed rule. All 32 evaluable Pearson and 32 normalized RMS values remain. These totals include four labelled identical-product self-comparisons. Positive finite ERR support is absent in 16 profiles. V2E2-0026 remains U. Its original local/baseline mapping limitations remain explicit. The core was already visible within C006's positive reference flank, so this context shares flux and observations with earlier work and is not independent validation.

[Independent arithmetic](work_harps_20261102_c007_context/independent_audit/NUMERICAL_AUDIT.json) passes 410 checks / 64,179 scalars. [Report and figures](work_harps_20261102_c007_context/analysis/RESULTS_REPORT.md). No new observations, acquisition, free fits or old pipeline replay were added.

## Earlier completed C006 group context

[The 4310 Å HD106515A comparison](work_harps_20261102_c006_context/README.md) is complete: seven existing epochs, two unique discovery references, 18 profiles and 64 comparisons. All 25 method/input files were read back from `e495c9fa6e59af1c3927a0b8a57767556eb30eff` before calculation. All three wavelength records and raw panels are retained; 0042/0043 share one product and are not duplicate references.

Nonself barycentric core r spans 0.960276–0.996426; surrounding-pattern r spans 0.973347–0.997366. All 18 profiles have full coverage and positive normalization without low-reference flags. All 64 Pearson/RMS outcomes and eight self-pairs are retained. The joint-window result is not a separate origin test for each feature. 0025's historical local/baseline mapping limitations remain explicit.

[Independent arithmetic](work_harps_20261102_c006_context/independent_audit/NUMERICAL_AUDIT.json) passes 488 checks / 71,701 scalars. All three U labels remain unchanged. [Measurements and four figures](work_harps_20261102_c006_context/analysis/RESULTS_REPORT.md). No new observations or archive queries were added.

## Earlier completed C005 group context

[The 3882 Å HD106515A comparison](work_harps_20261102_c005_context/README.md) is complete: seven existing epochs, all five discovery references, ten native-order contexts, 34 profiles and 180 comparisons. All 33 method/input files were read back from `b9e06d67e3a499dd93bf1b718820a18b0ddbe395` before calculation. No new acquisition or observation was added.

The core and surrounding spectrum recur in barycentric coordinates against every reference: nonself core r = 0.912055–0.994226 and broader r = 0.947577–0.994515. Fixed topocentric-core comparisons can concern neighboring structure because later feature centers move outside the anchor window. Near-BERV exceptions and all references are retained; no physical-origin classification follows.

All 34 profiles have full coverage and valid positive references. Two order 4 topocentric profiles, 0035 and 0054, retain low-reference flags; none is discarded. All 180 Pearson/RMS values and 20 self-pairs are reported. [Independent arithmetic](work_harps_20261102_c005_context/independent_audit/NUMERICAL_AUDIT.json) passes 895 checks / 135,577 scalars. All five U labels remain unchanged. [Complete measurements and eight figures](work_harps_20261102_c005_context/analysis/RESULTS_REPORT.md).

## Earlier completed C003 group context

[The HD106515 A comparison](work_harps_20261102_c003_context/README.md) is complete: seven existing epochs, all five discovery references, eight covering native-order contexts,30 profiles and172 comparisons. All 31 method/input files were read back from `d1046d8306ba34699f0eab9af57be145316eef76` before the calculation. No acquisition or new observation was added.

Core and surrounding structure show high barycentric agreement against every reference. Nonself raw r spans 0.940696–0.988011 in the core and0.928074–0.989934 in the broader pattern. The fixed topocentric core does not follow later feature centers; four of seven epochs place the expected coherent center outside it. This is persistent spectral morphology, not a line identification or physical-origin classification.

All five order3 contexts have full coverage and close same-exposure extraction agreement. Three included order2 contexts lack the right normalization flank; two later order2 combinations do not cover the original feature center and were excluded from headers. All 30 profiles/172slots are accounted for:24normalized,6 raw-only,166Pearson and160RMS values,20 self-comparison records. [Independent arithmetic](work_harps_20261102_c003_context/independent_audit/NUMERICAL_AUDIT.json) passes 807 checks/117,053 scalars. All five U labels remain unchanged. [Report and figures](work_harps_20261102_c003_context/analysis/RESULTS_REPORT.md).

## Earlier completed C001 group context

[The joint HD103991 context](work_harps_20261102_c001_context/README.md) is complete: six existing original-cohort merged epochs, both discovery exposures and both native covering orders, two fixed frames, 20 profile slots and 64 comparison slots. All inputs were already archived; no new request or observation was added. Method commit `c7e53d0180887618817923cfb1bec4b5b300ad53` and all 26 files were read back before the new array calculation.

The broader pattern is generally more barycentrically aligned; core behavior depends on the fixed discovery reference. For the discovery pair, core r is 0.491621 barycentric versus 0.795469 topocentric, while broader-pattern r is 0.936738 versus 0.844334. The five-other-epoch medians retain both references separately in the report. This contrast is descriptive, not physical-origin or calibrated frame-discrimination evidence.

Native order2 closely follows the same-exposure merged extraction; order3 is weak and lacks the entire negative reference flank. All four order3 profiles are explicitly raw-only for missing coverage, distinct from historical near-core low/nonpositive continuum. Of64 comparison slots,60 have a Pearson value and56 a normalized RMS; missing values and eight self-comparison rows are retained. All positive ERR support is absent. Both V2E2-0001/0016 remain U. [Independent arithmetic](work_harps_20261102_c001_context/independent_audit/NUMERICAL_AUDIT.json) passes504 checks/76,086 scalar comparisons. [Full report and figures](work_harps_20261102_c001_context/analysis/RESULTS_REPORT.md).

## Earlier completed spatial diagnostic

[The V2E2-0235 raw spatial analysis](work_harps_20261102_spatial_0235/README.md) is complete. The exact method and input identities were published in `8193e79cefabc32ec4a08230b2f77468905a5eee` and all 30 files read back before the one-shot measurement. No new archive request was made. The exact original raw and ancillary bytes were restored from the saved archive.

All 232 training rows were usable; 8 held-out controls and one target were measured with all 3 fixed templates: 27 window outcomes, 297 row fits and 8,275 native pixels preserved. The pooled target residual L1 is 8,633 ADU, above all eight controls (2,250–4,025 ADU), and its largest-pixel share is 6.52% versus 2.08–2.72%. Its off-trace fraction is lower, 15.70% versus 29.09–38.81%; the discrepancy lies mainly inside the predefined ±3-pixel band. Both flank-only templates agree qualitatively. These are uncalibrated model-discrepancy descriptors, not physical fractions or false-alarm probabilities.

The event remains U. This does not establish an isolated remote off-trace deposit or a photon-only feature. Profile mismatch, trace-adjacent contamination and mixtures remain possible. Fixed-background limitations, including possible FP fiber-B wings, remain explicit. [Full measurements and plots](work_harps_20261102_spatial_0235/analysis/RESULTS_REPORT.md) and [scientific interpretation](work_harps_20261102_spatial_0235/scientific_review/RESULT_INTERPRETATION.md) retain those limits. [Independent numerical verification](work_harps_20261102_spatial_0235/independent_audit/NUMERICAL_AUDIT.json) passes 13,779 checks and 86,442 scalar comparisons; every bounded raw pixel agrees exactly and maximum model/residual difference is 2.28e-10 ADU.

The separately frozen final background sensitivity is also complete: exactly negative-side and positive-side medians, both retraining the pooled template on the same 232 rows and evaluating the same nine windows. All 18 outcomes / 198 row fits are retained. Target residual L1 is 8,817.70 / 8,922.85 ADU and off-trace share 16.24% / 19.21%; each remains more concentrated and larger than every control, primarily near the trace. Independent audit passes 506 checks / 57,522 scalar comparisons. [Case closure](work_harps_20261102_spatial_0235/CASE_CLOSURE.json) retains U and ends further variants for this continuation.

## Earlier completed May quality follow-up

[The separate posthoc quality phase](work_harps_20261102_may_quality/README.md) is complete: exactly one new HD122640 input, six event–epoch pairs and twelve profiles, all measured with the unchanged method. The prior two-spectrum/24-profile run is preserved. All ten queue IDs remain U; four HD135204 records have no newly selected epoch. The original full-spectrum survey and all dispositions are unchanged.

The metadata-selected May20 reference has BERV −9.84628486624399 km/s, giving 36.195–37.087 km/s (13.884–14.227 nominal resolution elements) from discovery. All twelve profiles have no inherited low-continuum flag; the ten blue profiles have continuum/noise-proxy ratios 4.04–6.38, with no positive finite ERR samples. Five blue records correlate at 0.955933–0.979149 in the barycentric frame versus −0.312911–0.153460 topocentrically. This describes stable barycentric spectral morphology, not five independent detections or a physical-origin assignment.

V2E2-0235 has barycentric r=0.475244, but the new profile does not reproduce the discovery's sharp central excursion at comparable amplitude. Adequate continuum and moderate whole-core correlation do not resolve its raw-image charge/photon ambiguity. All six figures retain discovery and all three archival references.

[Full measurements and figures](work_harps_20261102_may_quality/comparison/results/README.md) · [Independent numerical audit](work_harps_20261102_may_quality/comparison_audit/NUMERICAL_AUDIT.json): 1,571 checks and 15,096 scalar comparisons passed, including all twelve profiles/correlations. Methods were public before the header; exact new input bytes were public and read back before array interpretation. One header and one payload succeeded with no retry, redirect or substitution.

## Earlier completed HARPS BERV follow-up

[The broader-date BERV follow-up](work_harps_20261102_berv_followup/README.md) is complete. Successful metadata queries returned 18 additional HD122640 products and zero HD135204 rows under the frozen filters. Two seasonal headers and two exact spectra were verified, published and compared with the inherited method. Failed metadata/header requests and prospective technical amendments are preserved; do not replay their one-shot scripts.

HD122640's available BERV span increases from **2.237910 to 40.363479 km/s** using 22 May 2017 (−11.0816664353 km/s) and 20 January 2018 (+29.2818122856 km/s). All **24 frame profiles / 12 event–epoch pairs** for six HD122640 records were measured. Four HD135204 records have no newly selected epoch. These are targeted archival follow-ups, not two additional full-spectrum survey searches. All ten labels remain U.

Five blue records have January barycentric correlations 0.9609–0.9743, but that cleaner epoch lies only approximately 0.78–1.13 nominal resolution elements from discovery. The May epoch supplies the large BERV separation, while all ten frame profiles of those five blue records have low continuum. The wider geometric range therefore does not establish a clean frame-discrimination result. V2E2-0235 at 5548.09 Å remains weakly correlated with both additional epochs and retains its raw-image ambiguity. No origin assignment, qualified laser candidate or calibrated null follows.

[Full report and all figures](work_harps_20261102_berv_followup/prospective_comparison/results/README.md) · [Independent numerical audit](work_harps_20261102_berv_followup/comparison_independent_audit/NUMERICAL_AUDIT.json) · [Exact input restoration](work_harps_20261102_berv_followup/science_acquisition/RESULTS.md). The audit independently reconstructed all 24 profiles with 2,065 checks and 29,712 scalar comparisons. No finite positive ERR values are available in either new spectrum.

## Completed HARPS work

The initial raw-image review covers all 669 V2 records. Provisional totals remain **403 A / 46 O / 185 U / 35 M / 0 N**. The older 333 cohort remains 209 A/25 O/95 U/4 M; the newer 336 remains 194 A/21 O/90 U/31 M. Coverage is unchanged: 300 unique exposures, 20 targets, 70.874650833 hours. V1 searched all 300 exposures (22 preliminary hits); V2 searched the latter 200 (669 records). No qualified laser candidate or calibrated null is established.

- [The fixed mapping diagnostic](work_harps_20261101/v2/extension02/mapping_followup_remaining_20261102/README.md) is complete for all 35 M records in 21 exposures: 1,512 native orders and 7,517 measured reference windows. The last 20 exposures were independently reconstructed with 179,698 metric comparisons. All 35 remain M. Improved robust correlations in some orders do not constitute a newly validated mapping gate; all eight previously failed order 70 references remain poor under the added comparisons. Missing detector coverage is unchanged. Do not rerun this completed queue merely to resume.
- [The normalization follow-up](work_harps_20261101/v2/extension02/normalization_context_20261102/README.md) covers V2E2-0092 and V2E2-0104: 28 preserved profiles, 8 focused windows and 12 native/raw contexts. Four low-continuum flags concern the same later observation on 27 August 2023, not either discovery. Low local flux and uncertain noise limit the comparison; positive scalar normalization alone leaves Pearson correlation invariant. A local trace-offset caveat remains explicit. Both records remain U. Independent numerical and separate visual checks passed.
- [Epoch comparison](work_harps_20261101/v2/extension02/epoch_followup/README.md) is already complete: 336 new records, 2,185 event/exposure pairs, 4,370 profiles. Do not repeat it as new science.
- [Unresolved context](work_harps_20261101/v2/extension02/unresolved_context_20261102/README.md) covers all 90 new U records, 39 nominal-resolution neighborhoods and 37 overlapping-profile neighborhoods. These are correlated groups, not independent physical signals. The older 95 U records remain outside that grouping.

## Completed Rubin main screen

[The accelerated Rubin study](work_rubin_20261102/README.md) uses actual world-public Rubin/Fink data, not ZTF or simulated telescope data. Twenty separate development objects preceded a metadata-selected main sample of 188 unique Gaia associations. Exact development IDs, positions and Gaia counterparts were excluded. The field is bounded and alert-selected, not an all-star survey.

The main selection, detector and code were published in commit `541357ebea3548836285857b548777723744ae15` before main photometry. All 49 files were read back exactly before release. Eight main API jobs succeeded without retry: 807 source measurements for 188 objects and 77 forced measurements for 10 objects. [The complete result](work_rubin_20261102/main_analysis/README.md) accounts for all 188 objects in both separate streams.

Only **2 primary objects / 7 October measurements** were numerically evaluable. Separately, **3 forced objects / 14 measurements** were evaluable; this set includes the two primary objects. Zero rows meet both fixed criteria. The minimum 50-object pilot is **not met**. Unknown withdrawal status, missing forced quality flags and approximately 108–112-day baseline gaps remain. This is a limited feasibility study, not a qualified null result.

The fixed method uses same-band direct science flux, 180 days of prior context, at least five distinct visits on three earlier UTC dates, and exclusion of the entire tested UTC date. A trigger requires ≥0.3 mag dimming and conservative deficit score ≥5; the score is not calibrated Gaussian significance. No thresholds changed after main results.

All 36 development injections are preserved: 18 sampled cases recovered and 18 gap cases unsampled; unchanged controls have zero hits. The placement design is not random phase and does not estimate survey sensitivity. Independent main audit passed 33,609 comparisons; controls passed 528,411 comparisons. No main trigger cutouts were requested because both complete trigger lists are empty.

## Completed bounded extension and combined Rubin result

The [one-degree metadata extension](work_rubin_20261102/extension_feasibility/README.md) acquired 940 new object histories and 8,277 metadata rows. Only 104 objects met necessary temporal/quality conditions. The separate [Gaia check](work_rubin_20261102/extension_gaia/README.md) retained two stellar associations. Their exact IDs and unchanged method were published in commit `c9f375268ee628088d808842afbd7445def7c9b6`; all 33 files were verified before extension flux.

[The two-object extension](work_rubin_20261102/extension_main_analysis/README.md) is complete: 54 source and 53 forced rows. None of the six October source rows has a usable baseline: three lack sufficient prior visits/dates and three fail the fixed baseline precision/stability floor. One additional object contributes two numerical forced rows. Neither stream has a trigger. Independent audit passed 2,972 comparisons, with original 188 results and method unchanged.

[Combined status](work_rubin_20261102/COMBINED_STATUS.json): **190 selected main objects; 861 source and 130 forced measurements; 2 primary numerical objects / 7 October rows and 4 secondary objects / 16 rows.** The primary objects are contained within the secondary set. This remains a limited feasibility study: minimum 50 unmet, no qualified null, no physical-origin assignment. All 10 main requests succeeded without retry. The original 20 development objects are separate; 36 controls are not multiplied by the number of cohorts. Do not repeat the completed 188+2 search or re-expand the same field merely to resume.

## Next work after the completed C022 phase

Use [the exact C017 handoff](work_harps_20261103_c022_context/NEXT_ACTION.json): original queue row 37, V2E2-0118 on HD114783 at 3868.175 Å / R018. [Evidence requirements](work_harps_20261103_c022_context/scientific_review/NEXT_STEP.md) retain the actual route, target-specific epochs, own discovery metadata and historical limits. Exact next member center(s): `3868.175` Å.

Selection: Original ACTION_QUEUE first unfinished diagnostic route after completedC001–C012/C015/C016/C018/C019/C021 and currently planned fullC022. Skip completedC013/0092 andC014/0104 normalization routes. This selects singletonC017/0118 row37 beforeC023row41 orC020row53; group numbers do not set queue order. Current unresolvedU does not reopen completed diagnostics. Selection is fixed before C022 values.

One own February5 discovery reference over seven existing January2022–July2023 HD114783 observations. Six other epochs retain source identities; no new observations or independent extraction confirmation. C017 reuses the same seven HD114783 observing products and overlaps C018 by4.8412500000004 Angstrom on source spectral pixels. The distinct common cores lie in each other's broad surrounding context but neither intersects the other's fixed1.5–3Angstrom reference flanks. The future C017 core has already been exposed in completed C018 context; no untouched,blind or independent-test claim. C019/C021/C022 bounded spectral windows are disjoint while observations/native lineage remain shared. Numeric other-target overlaps share no source products/pixels. Original historical raw crops remain separate without equality/independence claims. Proposed next group center: `3868.175` Å; proposed first-queue topocentric anchor: `3867.830769460069` Å. Exact singleton original catalog center3868.175; preserve original +/-0.25 core without midpoint averaging,fitting or expansion. Next-group review history: Batch03 original primary,secondary,adoptedU/U/U remains. No separate0131 I/M-normalized-I/baseline-I stages or0130/0129 histories transfer. Next native/mapping scope: Historical covering orders2/3, with source-specific mapping stages: order2 globaltrue/localfalse/baselinefalse/latertrue,order3alltrue. Fresh all72-order header scan of own February native product must determine actual center/core/context/flank scope; do not transfer current sole19 scope or quality, nor C018 missing-right-flank limits. Every signed/partial/invalid/low result retains its fixed slot.

C001 through C012, C015, C016, C018, C019, C021, C022 and the 0235 spatial/background phases are complete with unchanged U labels. C013/C014's exact normalization routes are also complete. Do not replay them or add variants merely to resume.

Do not automatically select another unused May spectrum to seek a stronger correlation. The separate quality-reference phase and the earlier monthly-selection phase are both closed. The remaining saved metadata pool contains 15 unused products (eight May, seven January), retained as inventory rather than an execution queue. All ten original queue identities and four uncovered HD135204 records remain explicit; the earlier zero-row query is not proof of archive-wide absence.

Rubin's [next-data-route review](work_rubin_20261102/next_data_route/README.md) remains complete and stopped. Reopen only a distinct prospective route with adequate public stellar history, provenance and quality. Preserve 190 main identities and unchanged detector; the 500-object ceiling leaves 310 further unique slots. Minimum50 remains unmet. No new Rubin query was made in the May quality, spatial, C001, C002, C003, C004, C005, C006, C007, C008, C009, C010, C012, C011, C016, C015, C018, C019, C021 or C022 context phases.

All 35 fixed mapping diagnoses, both normalization follow-ups and the original 4,370 epoch profiles are complete. Do not repeat them merely to resume. All 185 U and 35 M remain unchanged.

## Restore and maintain continuity

For C022, [preservation instructions](work_harps_20261103_c022_context/preservation/README.md) bind 10 source windows, 20 profiles and 3 historical raw-panel copies: 33 NPZs totaling 384,410 bytes. Exact existing archives restore the own target-specific inputs without a live query. Reproduce in a separate copy.

For C021, [preservation instructions](work_harps_20261103_c021_context/preservation/README.md) bind 12 source windows, 24 profiles and 5 historical raw-panel copies: 41 NPZs totaling 476,728 bytes. Exact existing archives restore the own target-specific inputs without a live query. Reproduce in a separate copy.

For C019, [preservation instructions](work_harps_20261103_c019_context/preservation/README.md) bind 17 source windows, 34 profiles and 10 historical raw-panel copies: 61 NPZs totaling 700,579 bytes. Exact existing archives restore the own target-specific inputs without a live query. Reproduce in a separate copy.

For C018, [preservation instructions](work_harps_20261103_c018_context/preservation/README.md) bind 21 source windows, 42 profiles and 14 historical raw-panel copies: 77 NPZs totaling 780,814 bytes. Exact existing archives restore the own target-specific inputs without a live query. Reproduce in a separate copy.

For C015, [preservation instructions](work_harps_20261103_c015_context/preservation/README.md) bind 8 source windows, 16 profiles and 1 historical raw-panel copy: 25 NPZs totaling 288,991 bytes. Exact existing archives restore the target-specific inputs without a live query. Reproduce in a separate copy.

For C016, [preservation instructions](work_harps_20261103_c016_context/preservation/README.md) bind 11 source windows, 22 profiles and 4 historical raw-panel copies: 37 NPZs totaling 432,482 bytes. Exact existing archives restore the own target-specific inputs without a live query. Reproduce in a separate copy.

For C011, [preservation instructions](work_harps_20261103_c011_context/preservation/README.md) bind 9 source windows, 18 profiles and 2 historical raw-panel copies: 29 NPZs totaling 336,009 bytes. Exact existing archives restore the target-specific inputs without a live query. Reproduce in a separate copy.

For C012, [preservation instructions](work_harps_20261103_c012_context/preservation/README.md) bind 9 source windows, 18 profiles and 2 historical raw-panel copies: 29 NPZs totaling 317,583 bytes. Exact existing archives restore the target-specific inputs without a live query. Reproduce in a separate copy.

For C010, [preservation instructions](work_harps_20261103_c010_context/preservation/README.md) bind 8 source windows, 16 profiles and 1 historical raw-panel copy: 25 NPZs totaling 292,148 bytes. Exact existing archives restore the target-specific inputs without a live query. Reproduce in a separate copy.

For C009, [preservation instructions](work_harps_20261103_c009_context/preservation/README.md) bind 8 source windows, 16 profiles and 1 historical raw-panel copies: 25 NPZs totaling 276,753 bytes. Existing archives restore 10 exact inputs without a live query. Reproduce in a separate copy.

For C008, [preservation instructions](work_harps_20261102_c008_context/preservation/README.md) bind 8 source windows, 16 profiles and 1 historical raw-panel copies: 25 NPZs totaling 282,389 bytes. Existing archives restore 10 exact inputs without a live query. Reproduce in a separate copy.

For C002, [preservation instructions](work_harps_20261102_c002_context/preservation/README.md) bind 9 source windows, 18 profiles and 2 historical raw-panel copies: 29 NPZs totaling 320,652 bytes. Existing archives restore 11 exact inputs without a live query. Reproduce in a separate copy.

For C004, [preservation instructions](work_harps_20261102_c004_context/preservation/README.md) bind 10 source windows, 20 profiles and 3 historical raw-panel copies: 33 NPZs totaling 381,864 bytes. Existing archives restore 16 exact inputs without a live query. Reproduce in a separate copy.

For C007, [preservation instructions](work_harps_20261102_c007_context/preservation/README.md) bind eight source windows, sixteen profiles and one historical raw-panel copy: 25 NPZs totaling 285,753 bytes. Two existing archives restore ten exact inputs without a live query. Reproduce in a separate copy.

For C006, [preservation instructions](work_harps_20261102_c006_context/preservation/README.md) bind nine source windows, 18 profiles and three raw-panel copies: 30 NPZs totaling 341,668 bytes. Two existing archives restore 14 original inputs; no live query is needed. Reproduce in a separate copy.

For C005, [preservation instructions](work_harps_20261102_c005_context/preservation/README.md) bind 17 compact source windows, 34 profiles and ten exact raw-panel copies: 61 NPZs totaling 707,244 bytes. Three existing archives restore all 27 original input files. No live archive query is needed; reproduce in a separate copy.

For C003, [preservation instructions](work_harps_20261102_c003_context/preservation/README.md) bind15compact source windows,30profiles and8exact raw-panel copies:53NPZs totaling568,599bytes. The three existing archives restore all25original input files without new acquisition. Preserve the completed directory and reproduce in a separate copy.

For C001, [preservation instructions](work_harps_20261102_c001_context/preservation/README.md) bind the ten compact pre-interpolation windows, twenty profiles and four unchanged raw-panel copies directly committed with the results. The existing three source archives restore all fourteen exact original inputs via `inputs/restore_inputs.py`; no live archive query is needed. Preserve the published output directory and reproduce only in a separate copy.

For the spatial phase, all 8,275 measured native pixels, exact coordinates and all raw/model/residual arrays are committed directly as compact NPZ files. See [preservation instructions](work_harps_20261102_spatial_0235/preservation/README.md). The full raw/ancillary bytes retain the original batch03 archived-input identity and are restored by the phase input helper; no new ESO request is needed. Published outputs and one-shot scripts remain immutable; reproduction belongs in a separate copy.

For the new May quality phase, use `python3 work_harps_20261102_may_quality/preservation/restore_archive.py SCIENCE_INPUTS_MANIFEST.json`, then `restore_reference_cache.py` in the same directory, then `restore_archive.py PROFILE_EVIDENCE_MANIFEST.json`. These restore the exact new FITS, original discovery/context references and twelve new profiles from preserved parts/archives; no live ESO request is needed. Helpers verify hashes and preserve differing files. Reproduce in a separate copy, retaining published outputs and one-shot guards.

For the new follow-up, run `python3 work_harps_20261102_berv_followup/science_acquisition/restore_inputs.py` to restore both exact FITS files from committed parts. Run `python3 work_harps_20261102_berv_followup/prospective_comparison/restore_profile_evidence.py` to restore all 20 discovery references and 24 derived profiles. Both helpers verify complete hashes and refuse to overwrite differing files. No live ESO download is needed. Reproduce in a separate copy so published outputs and one-shot guards remain intact.

Original HARPS archive identities and hashes remain in the current state and batch checkpoints. Restore into staging, verify member hashes and copy only canonical payloads; historical reports must not overwrite current state. Paths beginning `v2/extension02/` in HARPS archives are relative to `work_harps_20261101`. Partial files are never science inputs.

See [HARPS restoration instructions](work_harps_20261101/v2/RESTORE.md). New mapping diagnostics and normalization arrays have verified ordered evidence parts and restore scripts. Rubin original API responses, exact queries, receipts, Gaia CSV, code and complete outputs are preserved with this repository; no login is needed to reproduce the saved-data analysis. Run reproduction in a separate copy to retain published timestamps and stop guards. Network reacquisition can return a later service state.

Public GitHub updates are authorized. Preserve method/input identities, decisions, limitations and concrete queues after each continuation. Publication receipts identify verified results commits and trees. No unattended science search or paid service is configured.
