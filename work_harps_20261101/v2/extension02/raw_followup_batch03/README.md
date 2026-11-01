# Extension02 raw follow-up batch03 — completed

**115 previously unreviewed V2 records in 32 exposures have been inspected.** Root adopts 62 provisional detector artefacts, 7 O I-compatible features, 34 unresolved spectral structures and 12 mapping limitations. The raw-review queue falls from 209 to **94 records in 37 exposures**. No observing time was added and no qualified laser candidate was found.

| Batch03 disposition | Count |
|---|---:|
| A — provisional detector artefact | 62 |
| O — O I-compatible | 7 |
| U — unresolved spectral structure | 34 |
| M — insufficient mapping in at least one covering order | 12 |
| N — not raw reviewed | 0 |

The full new 336 cohort is now **142 A / 20 O / 61 U / 19 M / 94 N**. The older 333 remain unchanged at 209 A / 25 O / 95 U / 4 M. All 669 therefore contain **351 A / 45 O / 156 U / 23 M / 94 N**. [SUMMARY.json](SUMMARY.json) records the adopted counts, hashes and limits; [the current continuation state](CONTINUATION_STATE.json) contains the exact remaining queue.

## Visual decisions and retained uncertainty

[Adopted dispositions](ADOPTED_DISPOSITIONS.csv) retain both reviewer codes, the adopted evidence and the root decision; the separate review files preserve each reviewer's original reasoning. The [primary review](PRIMARY_VISUAL_REVIEW.json) and [secondary review](SECONDARY_VISUAL_REVIEW.json) each inspected all 29 atlas pages and 155 available order cutouts, accounting for all 157 expected event/order records and both unavailable full edge cutouts. Central enlargements addressed cases where bright calibration-fiber pixels dominated the full-cutout scales. The separate reviewers agreed on **114 of 115 records**; this is AI-agent descriptive agreement, not blinded external validation or human peer review.

The primary review returned 62 A / 7 O / 34 U / 12 M; the secondary returned 63 A / 7 O / 33 U / 12 M. Their sole disagreement was **V2E2-0235**: primary U versus secondary A. Root conservatively retained **U** after inspecting the native profile and both central renderings. A compact asymmetric multi-row patch supports possible charge contamination, but does not securely distinguish an isolated deposit from a photon/charge mixture. No mapping or numerical rule was changed. See [the comparison](REVIEW_COMPARISON.json) and [root adjudication](ROOT_ADJUDICATION.json).

The [recorded root check](ROOT_VISUAL_CHECK.json) covers 25 atlas pages containing 100 records, including every adopted U/O/M record (53 records), possible blends and additional A examples. Root also inspected all eight primary central pages and secondary central page 9. This was a selective check, not a third complete independent 115-record review.

Possible mixtures remain explicit:

- **V2E2-0099:** A describes the clear off-trace compact deposit; broader trace-confined spectral structure is not excluded.
- **V2E2-0122:** U retains an irregular displaced multi-row patch and a weak flat-topped/asymmetric native enhancement, with a possible charge/photon mixture.
- **V2E2-0230:** A describes the sharp order 3 contaminant; the broader weaker structure shared with order 4 remains a possible underlying spectral component.
- **V2E2-0235:** U preserves the sole reviewer disagreement and uncertainty about the compact asymmetric patch.

The seven O records are **0085, 0100, 0111, 0166, 0168, 0219 and 0221** (all V2E2). Their topocentric wavelengths, native profiles and spatially spread central morphology are compatible with O I 5577.338 or 6300.304 Å; wavelength alone does not establish origin. Weak contrast, asymmetry and curved-trace/background residuals remain cautions, especially for 0100, 0168, 0219 and 0221. All 32 fiber B channels were calibration rather than sky fibers, so there is no independent sky-fiber confirmation.

The 12 M records are **0158, 0159, 0160, 0169, 0170, 0184, 0185, 0194, 0195, 0199, 0223 and 0238** (all V2E2). The order 0 cutouts of 0159 and 0160 are edge-truncated; all other recorded quality failures remain explicit. Every M is retained regardless of visible morphology. A plausible interpretation in one available order cannot remove an unsupported overlapping order. The earlier seven new-cohort mapping limitations remain unchanged, giving 19 in the cumulative new 336 table.

## Preregistered selection

The first 32 exposures containing pending `current_code == N` records were taken from the exact 209-record/69-exposure queue at predecessor commit [e4dd888](https://github.com/andersenmartin-blip/setisearch/commit/e4dd888cd711e7da9bd2e058d874fd55f525f37e). Selection followed frozen MAIN100 order and included every accepted V2 record in those exposures. It did not rank strength, wavelength, target, morphology or availability; no selected exposure has an accepted V1 event.

The exact MAIN100 indices are **20, 21, 22, 24, 26, 28, 29, 30, 31, 32, 34, 35, 36, 37, 39, 40, 41, 42, 43, 44, 45, 46, 47, 49, 50, 52, 54, 56, 57, 58, 59, 60**. The [selected exposures](SELECTED_EXPOSURES.csv) and [all 115 selected events](SELECTED_EVENTS.csv) preserve exact archive and source identities. [Cache comparison](CACHE_CHECK.json) found no selected product identity among the previous 24 canonical exposure pairs.

[Plan, code and exact selection](FOLLOWUP_FREEZE.json) were published in commit [9946192](https://github.com/andersenmartin-blip/setisearch/commit/9946192e76b4887de41083c5972862094c723536) and independently read back **before payload acquisition**. See the [preregistration receipt](PREREGISTRATION_RECEIPT.json), [independent preflight](review/PREFLIGHT_REVIEW.json) and [13 passing guard tests](GUARD_TEST_RESULTS.json), including checks against all 64 frozen jobs. The previous 127 raw-reviewed V2 records, 133 selected V1/V2 records and older 333 cohort are preserved as predecessor snapshots.

The main survey remains **300 unique exposures of 20 targets, 70.874650833 hours**. V1 searched all 300 exposures; V2 searched the latter 200 and produced 669 records. This follow-up reuses survey exposures and adds no observing time. The [epoch comparison](../epoch_followup/README.md) of all 336 new records against same-target observations among the new 100 spectra is already complete and is not repeated by this batch.

## Acquisition and input integrity

All 32 RAW and 32 ancillary products were downloaded from their original public ESO identities and validated against archive identity, DATE-OBS, native parent, target and BERV. [Manifest and receipts](products/MANIFEST.json) record **852,885,545 known and charged payload bytes**, below the 1,400,000,000-byte cap, using three workers and at most two attempts per product.

There were 65 payload attempts: 64 successes and one zero-byte HTTP 503 response followed by its allowed successful retry. No selected pairs were omitted or replaced. There were no redirect fallbacks, access-denial workarounds or unknown-byte charges.

The [independent supplemental inventory](independent_audit/SUPPLEMENTAL_INVENTORY.json) records 10 residual `.part` files totaling 67,346,125 bytes. Each matches a prefix of its verified canonical product, including one complete duplicate. Their persistence is unexplained; no cause or additional network transfer is inferred. These paths are excluded from analysis and input packages. All 64 canonical product hashes and lengths still match, and extraction reads only canonical manifest paths.

A [final publication inventory](independent_audit/FINAL_NONCANONICAL_INVENTORY.json) additionally found one transient local copy of 8,650,752 bytes, an exact prefix of its canonical product. There are therefore 11 noncanonical payload files totaling 75,996,877 bytes; all are excluded from analysis, all eight saved input ZIPs, the evidence archive and GitHub publication. The 64 canonical products and 32 extraction pairs were reverified. The transient files' origin and any attribution to additional network bytes remain unknown; the earlier supplemental report is preserved unchanged.

All 32 exposures used calibration fiber B (`STAR,WAVE`), with no independent sky fiber. Any later atmospheric O I-compatible interpretation must therefore remain provisional and must use both wavelength and photon-compatible morphology.

## Mapping and independent numerical validation

Native extraction, the global registration grid, local trace checks and five-window mapping arithmetic are byte-identical to batch02. The plotting code changes only the batch label. The inherited 24-region global grid fixes orientation; no coordinate adjustment is fitted from selected morphology. Original two-sided local flags remain separate and descriptive.

The five-window check is applied prospectively to **every covering order**. Event support requires the global gate, every covering-order five-window gate and complete cutouts. The method stores 31×33 raw cutouts with exact central 21×25 baseline pixels, both fixed background conventions and 41 native samples.

The [independent audit](independent_audit/README.md) passed:

| Numerical coverage | Count |
|---|---:|
| Selected exposures / events | 32 / 115 |
| Expected event/order records | 157 |
| Reconstructed full raw/native cutouts | 155 |
| Unique exposure/order combinations | 136 |
| Verified input files (64 products + 32 science spectra) | 96 |
| Recomputed global region/orientation cases | 6,144 |
| Recomputed five-window references | 680 |
| Unchanged frozen sources | 33 |

The audit independently reconstructs source pixels, wavelength/trace coordinates, all saved cutouts and the global/five-window calculations without importing project analysis modules. NumPy/SciPy/Astropy primitives are shared. Legacy local checks are audited for coverage and gate arithmetic, not full independent numerical reconstruction. Numerical agreement is not visual or physical-origin validation.

## Saved inputs, evidence and reproduction

[Eight saved raw-input packages](checkpoints/SAVED_INPUTS.md) preserve all 64 canonical products in 32 complete exposure pairs. The ZIP files total **779,783,416 bytes**. [LIBRARY_INPUTS.json](checkpoints/LIBRARY_INPUTS.json) records exact Library identities, links, archive sizes and SHA-256 hashes, and all canonical member identities. The 32 source 1D spectra remain in the earlier 100-spectrum extension02 packages.

Restore input archives into a separate staging directory first. Paths beginning `v2/extension02/` are relative to `work_harps_20261101`. Verify archive and member hashes, then copy only required canonical data and matching receipts. Do not replace newer current-state documents with historical copies inside input archives; diagnostic partial files are never inputs.

The GitHub evidence package contains **187 members: 155 native NPZ cutouts and 32 reference JSON grids**. Its length is 1,397,012 bytes and SHA-256 is `22c8fa897318044e8369639a9b016be59ddbfc675a6075262a4ae00a64cfb1c0`. The [ordered part manifest](EVIDENCE_PARTS.json) and [member manifest](EVIDENCE_ARCHIVE.json) support exact restoration from the single tracked archive part. All 29 atlas PNGs and 18 supplementary central-enlargement pages are retained separately.

From this directory, in a separate working copy with canonical source products restored:

```bash
python3 restore_evidence.py
python3 independent_audit/check_batch03.py
python3 independent_audit/check_inventory.py
```

Audits rewrite their reports, so preserve the published reports. A clean restore should contain no residual `.part` files; the supplemental inventory does not require recreating diagnostic remnants. `restore_evidence.py --verify-only` checks the archive and members without extracting them; differing existing evidence is refused. [Restoration validation](EVIDENCE_RESTORE_VALIDATION.json) records deterministic packaging, a fresh split-only restore of all 187 members, identical-file retention and refusal of changed files, symlinks or corrupt parts.

The recorded runtime uses Python 3.12.14, NumPy 2.3.5, SciPy 1.17.0, Astropy 8.0.2 and Matplotlib 3.10.8. Use the recorded environment and verified inputs for numerical reproduction, rather than a previous session's absolute runtime path. Full extraction reproduction requires a separate output copy without existing output markers; it is not a reason to reacquire completed source products.

## Scientific limits and continuation

This is post-detection follow-up with heterogeneous preserved historical mapping controls. All morphological and physical-origin descriptions remain provisional. There is no calibrated sensitivity, global false-alarm rate, qualified laser exclusion or calibrated null result. AI-agent reviews are not blinded scientific validation or human peer review. No qualified laser candidate is established by this completed follow-up.

The pending raw queue now contains **94 records in 37 exposures**, beginning with **V2E2-0243**, target **HD124553**, exposure **ADP.2022-03-16T01:08:24.041**. Use the exact pending IDs, product identities and source hashes in [CONTINUATION_STATE.json](CONTINUATION_STATE.json), which derives the queue from current `N` rows in frozen MAIN100 order.

Start at [CONTINUE_SETI.md](../../../../CONTINUE_SETI.md), fetch current GitHub first and compare checkpoint hashes. Prepare the next bounded batch in a separate `raw_followup_batch04/`; preserve selected identities, fixed limits, failed/omitted pairs and every covering-order limitation. Do not repeat completed epoch or raw batches merely to resume. Current unresolved structures and mapping limitations remain follow-up work after the pending queue. Rubin remains the approved second week (8–14 November) and has not been analyzed here.

Final publication and remote readback remain pending at this completed local checkpoint. No unattended science worker or scheduled background search is configured; continuity comes from saved inputs, evidence, explicit decisions and the exact remaining queue.
