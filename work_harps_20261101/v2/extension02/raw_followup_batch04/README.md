# Extension02 raw follow-up batch04 — completed with one unavailable pair

**92 previously unreviewed V2 records in 36 exposures were inspected; two selected records remain unavailable.** Root adopts **50 provisional detector artefacts, 1 O I-compatible feature, 29 unresolved spectral structures, 12 mapping limitations and 2 N records** from the fixed 94-record/37-exposure selection. The pending raw queue falls from 94 to **2 records in one exposure**. No observing time was added and no qualified laser candidate was found.

| Batch04 disposition | Count |
|---|---:|
| A — provisional detector artefact | 50 |
| O — O I-compatible | 1 |
| U — unresolved spectral structure | 29 |
| M — insufficient mapping in at least one covering order | 12 |
| N — unavailable raw/ancillary pair | 2 |

The new 336-record cohort is now **192 A / 21 O / 90 U / 31 M / 2 N**. The older 333 remain **209 A / 25 O / 95 U / 4 M**. All 669 therefore contain **401 A / 46 O / 185 U / 35 M / 2 N**, with **667 of 669 records raw-reviewed**. The 185 unresolved structures and 35 mapping limitations remain follow-up work across both cohorts. [SUMMARY.json](SUMMARY.json) and [the continuation state](CONTINUATION_STATE.json) preserve counts, evidence hashes and the exact remaining queue.

## Visual decisions and retained uncertainty

The [primary review](PRIMARY_VISUAL_REVIEW.json) and [secondary review](SECONDARY_VISUAL_REVIEW.json) separately inspected all 24 atlas pages and all 122 available covering-order cutouts, with explicit notices for missing edge cutouts and the unavailable pair. The primary reviewer additionally inspected all 21 systematic central-enlargement pages covering all 122 cutouts; the secondary inspected nine central pages covering 51 order panels. Fixed arrays, coordinates and display scales are retained. Both reviews agree on **all 94 selected records**; root adopts their codes without overrides. [Adopted dispositions](ADOPTED_DISPOSITIONS.csv) and [review comparison](REVIEW_COMPARISON.json) retain the separate original judgments.

[Root's recorded check](ROOT_VISUAL_CHECK.json) covers 19 atlas pages, including all 44 adopted U/O/M/N records, plus all 21 primary central pages and their 122 available cutouts. This is a selective atlas check supplemented by complete central-display inspection, not a third independent full-atlas review. Agent agreement is not blinded external scientific validation or human peer review.

Important interpretations remain provisional:

- **V2E2-0261 remains U:** both covering orders retain broader trace-centered structure; a separate compact off-trace deposit near column +7 in order 2 does not explain the centered component.
- **V2E2-0274 remains U:** a broad centered feature is present in orders 3 and 4; a separate bright far-corner deposit in order 4 dominates its display scale but does not remove the unresolved component.
- **V2E2-0289 remains U:** the weak flat-topped red-order enhancement is entangled with continuum/background-gradient residuals. Neither a clear isolated charge feature nor a secure photon profile is established.
- **V2E2-0317 and V2E2-0321 remain provisional A for identified narrow charge-like contaminants.** Weaker or displaced structures in their other covering orders are not excluded as additional components.

The sole O record, **V2E2-0244**, has topocentric wavelength **5577.347245 Å**, an offset of **+0.009245 Å** from nominal O I 5577.338 Å. Its weak, noisy, multi-row trace-confined excess is photon-compatible; wavelength and morphology together support compatibility, not a confirmed atmospheric origin. [Fiber inventory](FIBER_INVENTORY.json) records **31 available pairs with an e2ds_B product and FP calibration context, and five STAR,DARK exposures without e2ds_B**. No independent sky fiber is documented for any of the 36 acquired pairs.

The 12 M records are **0249, 0259, 0280, 0290, 0295, 0296, 0297, 0298, 0299, 0300, 0312 and 0336** (all V2E2). Full edge cutouts are unavailable for one covering order of 0280 and 0312. Every recorded mapping limitation is preserved regardless of visible morphology. **V2E2-0332 and V2E2-0333 are N because their product pair is unavailable; they are not mapping failures.**

## Preregistered selection and publication

The selected MAIN100 indices are **61, 62, 63, 64, 66, 67, 68, 69, 70, 71, 72, 73, 74, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 95, 96, 97, 98, 99, 100**. Selection took the entire remaining `current_code == N` queue in frozen MAIN100 order, beginning with V2E2-0243 on HD124553. It did not rank strength, wavelength, morphology, target or product availability. No selected exposure has an accepted V1 event.

[The exact selection and frozen code](FOLLOWUP_FREEZE.json) were published at [d9e9fab](https://github.com/andersenmartin-blip/setisearch/commit/d9e9fab88f86f7ea7c8326157a8afab595176a3d) and independently read back **before payload acquisition**. The [preregistration receipt](PREREGISTRATION_RECEIPT.json) records a complete matching tree of 43 changed files and seven key-file readbacks. All 33 frozen source hashes matched. The [independent preflight](review/PREFLIGHT_REVIEW.json) passed 36 checks; [13 offline transport and identity guards](GUARD_TEST_RESULTS.json) passed with all 72 actual frozen jobs.

[PLAN.json](PLAN.json), [selected exposures](SELECTED_EXPOSURES.csv), [selected events](SELECTED_EVENTS.csv) and [the prospective visual review plan](VISUAL_REVIEW_PLAN.json) preserve the methods and identities. Five immutable predecessor snapshots retain the status at [cb176a2](https://github.com/andersenmartin-blip/setisearch/commit/cb176a288874bc2d0658c40dfab191a21b30dda4). [Cache comparison](CACHE_CHECK.json) found no selected archive identity among 112 canonical products from the previous 56 exposure pairs, or any selected canonical, partial or transient product path in the retained-filename scan.

## Metadata outcome, acquisition and inventory limitations

[HEAD metadata](REMOTE_PRODUCT_METADATA.json) verified 73 of 74 product identities across 85 attempts. Ancillary product `ADP.2023-07-07T01:08:58.253` returned HTTP 503 on both allowed HEAD attempts. Its complete pair was therefore omitted without replacement: exposure `ADP.2023-07-07T01:08:58.252`, target HD141937, MAIN100 index 99, selected records V2E2-0332 and V2E2-0333. The otherwise verified RAW product was not acquired as an incomplete pair. [SELECTION.json](SELECTION.json) retains the omission; there was no third metadata request or alternative route in this batch.

All **72 approved products in 36 complete pairs** were acquired, identity-checked and hashed. The [product manifest and individual receipts](products/MANIFEST.json) record **955,039,604 known returned and charged payload bytes**, below the **1,600,000,000-byte cap**. Three workers made 74 payload attempts: 72 successes and two zero-byte HTTP 503 failures, each followed by its permitted successful retry. There are no unknown-byte charges, replacements, redirects or access-denial workarounds. Original archive identity, DATE-OBS, instrument, native parent, target and BERV were checked before products became canonical.

The [supplemental inventory](independent_audit/SUPPLEMENTAL_INVENTORY.json) independently verifies all 72 canonical hashes and lengths and the 36 extraction pairs. It records two limitations without inferring their cause:

- `acquisition.log` contains only **38 status lines**; 34 manifest receipt identities and the final completion line are absent from the log. The log is preserved without reconstruction. All 72 per-product receipts and the canonical manifest exist and supply the acquisition accounting; the incomplete stdout log is not treated as complete evidence.
- **Nine noncanonical prefix files total 132,489,088 bytes**, including three complete canonical duplicates. Every file matches a canonical prefix, but its origin and any attribution to additional network bytes remain unknown. They are preserved locally and excluded from analysis, all nine saved input archives, the evidence archive and GitHub payload publication.

No cause or extra transfer is inferred from those remnants or the incomplete log. The numerical audit reconstructed evidence only from the verified canonical manifest paths.

## Mapping and independent numerical validation

Native extraction, global registration, local trace checks and five-window mapping arithmetic are byte-identical to batch03; the plot title changes only the batch label. The inherited 24-region global grid fixes orientation. Original two-sided local flags remain separate and descriptive. The five-window gate applies prospectively to every covering order without fitting coordinates to selected morphology.

Event support requires the global gate, every covering-order five-window gate and full cutout availability. Evidence retains 31×33 raw cutouts, exact central 21×25 baseline pixels, both fixed background conventions and 41-point native snippets. An unsupported order or missing full cutout preserves M even when another available order has artifact-like morphology.

The [independent numerical audit](independent_audit/SUMMARY.json) passed:

| Numerical scope | Count |
|---|---:|
| Selected records / exposures | 94 / 37 |
| Raw-reviewed records / available exposure pairs | 92 / 36 |
| Mapping-supported records / mapping-limited records | 80 / 12 |
| Unavailable records / exposure pairs | 2 / 1 |
| Expected event/order records for available pairs | 124 |
| Reconstructed full cutouts | 122 |
| Unique available exposure/order combinations | 90 |
| Verified input files: 72 products + 36 science spectra | 108 |
| Recomputed global region/orientation cases | 6,912 |
| Recomputed five-window references | 450 |
| Unchanged frozen sources | 33 |

**Covering-order and cutout counts apply only to exposures with available validated pairs.** For the omitted exposure, native arrays were not opened and covering orders are unknown. Its N records do not imply zero physical orders or failed mapping.

The audit independently checks provenance, hashes, source pixels, direct-power wavelength/trace polynomials, backgrounds, native profiles and global/five-window registration calculations without importing project analysis modules. NumPy/SciPy/Astropy primitives are shared. Legacy local checks are audited for coverage and gate arithmetic, not full numerical reconstruction. Numerical agreement is not visual or physical-origin validation.

## Current-state reconciliation

All **248 predecessor selected V1/V2 rows**, 242 previously reviewed new V2 records and the older 333 cohort remain unchanged. The cumulative reviewed-selected master adds only the **92 non-N records**, reaching **340 rows**. The complete 94-record batch selection, its adopted table and the current 336-record table retain both unavailable records and their failure evidence. This preserves the distinction between selection and actual raw review, and prevents a later retry from duplicating reviewed IDs.

Two post-preregistration bookkeeping adaptations are explicit. [The continuity helper](update_current.py) excludes unavailable N records from the reviewed-selected master while retaining their full selection history; [24 synthetic continuity checks](CONTINUITY_HELPER_VALIDATION.json) exercise this contract. [The adoption helper](adopt_results.py) accepts the secondary review's actual record-list schema and explicit 122-entry cutout list, checking identities and hashes. These are administrative record-handling changes. Review labels, figures, extraction/mapping rules and all 33 frozen scientific sources were unchanged.

## Saved inputs and reproducible evidence

[Nine saved raw-input ZIP packages](checkpoints/SAVED_INPUTS.md) preserve all **72 canonical products in 36 complete pairs**, totaling **876,883,779 archive bytes**. [LIBRARY_INPUTS.json](checkpoints/LIBRARY_INPUTS.json) records successful save receipts, exact identities and links, archive/member hashes and the omitted pair. The packages are dated 2026-11-02. Source 1D spectra remain in the earlier extension02 science-input packages.

Restore every required earlier science-input package and this batch's raw-input packages into a separate staging directory first. Member paths beginning `v2/extension02/` are relative to `work_harps_20261101`. Verify archive and member hashes; copy only canonical payloads and matching receipts. Do not replace newer status documents with historical copies inside an input archive. Partial or transient files are never science inputs.

The GitHub evidence archive contains **158 members: 122 native NPZ cutouts and 36 reference JSON grids**, totaling **1,252,768 bytes**. SHA-256: `110a35ec15c0da6dc1803ca160b70809ecb47565b34486846b7d4c4e8ba648bc`. [EVIDENCE_ARCHIVE.json](EVIDENCE_ARCHIVE.json) records every member; [EVIDENCE_PARTS.json](EVIDENCE_PARTS.json) records the single ordered binary part. All 24 atlas pages and supplementary central displays remain separately inspectable.

From this directory, in a separate working copy with canonical source products restored:

```bash
python3 restore_evidence.py
python3 independent_audit/check_batch04.py
python3 independent_audit/check_inventory.py
```

Audits rewrite their reports, so preserve the published originals. A clean restore should contain no diagnostic partial files; recreating remnants is not required. [Six restoration checks](EVIDENCE_RESTORE_VALIDATION.json) passed: deterministic packaging, a fresh split-only reconstruction of all 158 members, identical-file retention and refusal of changed files, symlinks or corrupt parts. `restore_evidence.py --verify-only` checks hashes without extraction. Original evidence arrays remain unchanged.

Recorded runtime: Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0, Astropy 8.0.2 and Matplotlib 3.10.8. Use verified inputs and these recorded versions rather than an earlier session's absolute dependency path. Full extraction reproduction requires a separate output copy without existing output markers; it is not a reason to reacquire completed products.

## Survey limits and next action

The main survey remains **300 unique exposures of 20 targets, 70.874650833 hours**. V1 searched all 300 exposures and produced 22 preliminary hits. V2 searched the latter 200 and produced 669 records. Raw follow-up adds no observing time. The [completed epoch comparison](../epoch_followup/README.md) covers all 336 new records against same-target observations among the new 100 spectra: 2,185 event/exposure pairs and 4,370 profiles. It is not repeated here.

The exact pending queue is **V2E2-0332 and V2E2-0333**, both on HD141937 in exposure **ADP.2023-07-07T01:08:58.252**. Start at [CONTINUE_SETI.md](../../../../CONTINUE_SETI.md), fetch current GitHub and compare checkpoint hashes. A separate prospective `raw_followup_batch05/` may address this queue under explicitly frozen product identities, limits and methods while retaining the batch04 metadata failures. No successor selection or new retry has been performed by this handoff.

All **185 unresolved spectral structures and 35 mapping limitations** across both cohorts remain explicit follow-up work. Epoch metrics provide context, not an origin veto. Rubin remains the approved second week, 8–14 November, and has not been analyzed. All physical-origin descriptions are provisional. Descriptive post-detection AI review with heterogeneous historical mapping controls provides no calibrated sensitivity, global false-alarm rate, qualified laser exclusion or calibrated null result.

Final publication and remote readback remain pending at this completed local checkpoint. No unattended science worker or scheduled background search is configured; continuity comes from saved inputs, evidence, explicit decisions and the exact remaining queue. Science timestamps use UTC; the user-facing work date is 2 November 2026 in Europe/Copenhagen.
