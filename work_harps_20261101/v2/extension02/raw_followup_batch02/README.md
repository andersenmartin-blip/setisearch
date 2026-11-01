# Extension02 raw follow-up batch02 — completed

**68 previously unreviewed V2 records in 16 exposures were inspected.** Root adopts 36 provisional detector artefacts, 5 O I-compatible features, 21 unresolved spectral structures and 6 mapping limitations. The raw-review queue falls from 277 to **209 records in 69 exposures**. No observing time was added and no qualified laser candidate was found.

| Batch02 disposition | Count |
|---|---:|
| A — provisional detector artefact | 36 |
| O — O I-compatible | 5 |
| U — unresolved spectral structure | 21 |
| M — insufficient mapping in at least one covering order | 6 |
| N — not raw reviewed | 0 |

The complete new336 cohort is now **80 A / 13 O / 27 U / 7 M / 209 N**. The older333 remain unchanged at209 A /25 O /95 U /4 M. All669 therefore contain289 A /38 O /122 U /11 M /209 N. The main survey remains300 unique exposures of20 targets,70.874650833 hours.

## Decisions and review limits

[Adopted dispositions](ADOPTED_DISPOSITIONS.csv) retain both original reviewer codes and the root decision. Both separate AI reviewers inspected all17 atlas pages and all94 available order cutouts; both returned37 A /5 O /20 U /6 M and agreed on all68 records. Root checked every adopted U/M record, all five O records using central enlargements, the possible blend and artifact examples; [exact root scope](ROOT_VISUAL_CHECK.json) is recorded.

Root conservatively retains **V2E2-0050 as U**, although both reviewers favored a weak charge cluster: broader residual structure and a possible photon contribution remain insufficiently distinguished by visual inspection. **V2E2-0055 remains provisional A for its compact order30 deposit**, while a weaker underlying spectral component in order29 is explicitly not excluded. No mapping or numerical threshold was changed during adjudication. See [review comparison](REVIEW_COMPARISON.json), [primary review](PRIMARY_VISUAL_REVIEW.json), [secondary review](SECONDARY_VISUAL_REVIEW.json) and their central enlargements.

The five O records are0012,0067,0073,0078 and0082 (all V2E2). Their observer-frame wavelengths and photon-compatible central morphology support the provisional description; wavelength alone is insufficient. Every exposure used a calibration fiber B (`STAR,WAVE`), so there is no independent sky-fiber confirmation.

The six M records are0018,0034,0041,0070,0074 and0075. The first two include an unavailable full edge cutout; other covering orders also retain their recorded quality failures. An apparently artifact-like feature in an available order does not remove an unsupported overlapping order. Earlier V2E2-0225 remains the seventh new-cohort mapping limitation.

These are descriptive post-detection AI-agent judgments, not blinded scientific validation, human review or confirmed physical origins. Historical batches use different preserved mapping controls. There is no calibrated sensitivity, global false-alarm rate, qualified laser exclusion or calibrated null result.

## Preregistered selection and acquisition

The first16 pending exposures in frozen MAIN100 order were selected: indices3–13 and15–19, containing every accepted V2 event0011–0058 and0065–0084. Selection did not use strength, wavelength, morphology or availability. Previous adopted decisions and original production catalogs remain unchanged.

[Plan and frozen source package](FOLLOWUP_FREEZE.json) were published in commit [5151548](https://github.com/andersenmartin-blip/setisearch/commit/51515488a8154bca9875bfe99afcd01b835d8b06) and remotely verified **before payload acquisition**. See [preregistration receipt](PREREGISTRATION_RECEIPT.json) and [independent preflight](review/PREFLIGHT_REVIEW.json). All13 offline guard tests passed with the32 actual frozen jobs.

All16 RAW and16 ancillary products were downloaded from their original public ESO identities, validated against archive identity, DATE-OBS, native parent/target/BERV and hashed. Total known/charged payload was423,684,432 bytes within the700,000,000-byte cap, with three workers. One ancillary HTTP503 response returned no payload; its single allowed retry succeeded (33 attempts total). There were no omitted pairs, replacements, redirect fallbacks or unknown-byte charges. [Product manifest](products/MANIFEST.json) and receipts preserve the details.

Five residual `.part` paths were observed after completion and excluded. All match prefixes of canonical products, including one complete duplicate; their persistence is unexplained. They are not analysis inputs or checkpoint members. All32 canonical products still verify exactly; see [inventory anomaly](PARTIAL_FILE_ANOMALY.json) and [independent supplemental check](independent_audit/SUPPLEMENTAL_INVENTORY.json). No additional transfers or cause are inferred from these local remnants.

## Mapping and numerical validation

The inherited24-region global grid fixes raw orientation. Original two-sided local flags remain separate. The previously established five-window quality check is applied prospectively to **every covering order**, using fixed coordinates and thresholds. Event support requires global support, every covering-order five-window pass and complete cutouts.

All96 expected event/order records were accounted for;94 full31×33 raw cutouts retain exact central21×25 baseline pixels, both background conventions and41 native samples. There are81 unique exposure/order combinations. [Independent numerical audit](independent_audit/README.md) passed:48 input hashes, every saved cutout,3,072 global region/orientation cases,405 five-window references and31 frozen sources were checked. The audit does not import production analysis modules; its shared numerical primitives and limited coverage of legacy local calculations are explicit.

## Restore and reproduce

[Four saved input packages](checkpoints/SAVED_INPUTS.md) preserve all32 canonical RAW/TAR products. Their archive and member hashes and exact Library identities are in [LIBRARY_INPUTS.json](checkpoints/LIBRARY_INPUTS.json). Source 1D science spectra remain in the earlier extension02 input packages. Restore into staging first; archive member paths are relative to `work_harps_20261101`. Do not overwrite newer status files with historical copies inside an input archive.

The GitHub evidence archive contains94 NPZ cutouts and16 reference JSON files (110 members),816,769 bytes, SHA-256 `7d937e265e38f8f98da0bb59b117094ec952a192865860c75382a0732dd9f66d`. The [ordered part manifest](EVIDENCE_PARTS.json) and [member manifest](EVIDENCE_ARCHIVE.json) support exact restoration. From this directory:

```bash
python3 restore_evidence.py
python3 independent_audit/check_batch02.py
python3 independent_audit/check_inventory.py
```

Run audits in a separate copy with source products restored because audit reports are rewritten. Supplemental inventory should naturally find zero residual files in a clean restore; it does not require recreating diagnostic remnants. `restore_evidence.py --verify-only` verifies hashes without extracting members; different existing evidence is refused. [Packaging validation](EVIDENCE_RESTORE_VALIDATION.json) records deterministic rebuild, fresh reconstruction and overwrite/corruption safeguards.

The recorded runtime is Python3.12.14, NumPy2.3.5, SciPy1.17.0, Astropy8.0.2 and Matplotlib3.10.8. Full extraction reproduction requires a separate output copy without prior output markers; use the frozen code and inputs rather than rerunning acquisition. `adopt_results.py` records the explicit root adjudication; `update_current.py` checks frozen predecessor tables before applying the verified overlay.

## Continue

Start at [CONTINUE_SETI.md](../../../../CONTINUE_SETI.md) and [this continuation state](CONTINUATION_STATE.json). The next raw queue head is **V2E2-0085**, target **HD109833**, in exposure **ADP.2025-03-16T01:01:40.685**. Prepare a separate bounded `raw_followup_batch03` from the exact209-record/69-exposure queue. Do not repeat completed epoch comparison or raw batches merely to resume. Current unresolved structures and mapping limitations remain explicit follow-up work after the pending queue.

[SUMMARY.json](SUMMARY.json) records hashes and counts. The completed result was published on both branches at [2fdc358](https://github.com/andersenmartin-blip/setisearch/commit/2fdc358ea21385b12762c945c94143fac943b64b); [remote readback](PUBLICATION_RECEIPT.json) verified the complete tree, ten key files and all32 binary blob identities. No unattended science worker or scheduled background search is configured.
