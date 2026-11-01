# Continue SETI from this checkpoint

Start here, then read the [machine-readable continuation state](work_harps_20261101/v2/extension02/epoch_followup/CONTINUATION_STATE.json). It records exact source hashes, all 277 pending event IDs, their 85-exposure queue, input archives and the next action. Fetch the current GitHub branch first and compare its checkpoint hashes before doing more work; another session may have advanced the project.

## Completed work

The main survey has **300 exposures of 20 stars, 70.874650833 hours**. V1 searched all 300 exposures; V2 searched the latter 200 and produced 669 records. There is no qualified laser candidate and no calibrated null result.

The new [epoch comparison](work_harps_20261101/v2/extension02/epoch_followup/README.md) covers **all 336 extension02 V2 records in all same-target observations from the new 100 spectra**: 2,185 event/exposure pairs and 4,370 profiles. Discovery exposures are excluded from other-epoch summaries. The [independent numerical audit](work_harps_20261101/v2/extension02/epoch_followup/independent_audit/README.md) passed. This calculation is complete; do not repeat it merely to resume the project. The earlier 200 exposures were not included, and no new observing time was added.

The newer raw-image and mapping follow-up remains authoritative. [Current raw table](work_harps_20261101/v2/extension02/raw_followup/CURRENT_V2_ALL336_DISPOSITIONS.csv):

| New V2 status | Count |
|---|---:|
| Provisional detector artefact | 44 |
| O I-compatible | 8 |
| Unresolved spectral structure | 6 |
| Insufficient raw mapping | 1 |
| No raw review yet | 277 |

The six unresolved IDs are V2E2-0001, 0104, 0128, 0129, 0130 and 0131. V2E2-0225 is the remaining new mapping limitation. Earlier baseline tables with eight new mapping limitations are historical and must not replace the adopted wider-mapping results. See [current raw report](work_harps_20261101/v2/extension02/raw_followup/CURRENT_RESULTS.md) and [previous 333-record follow-up](work_harps_20261101/v2/followup_synthesis/README.md).

## Next action: remaining raw review

The queue begins at **V2E2-0011**, exposure **ADP.2023-02-27T01:01:03.513**, target **HD103991**. The machine-readable queue is copied from exact rows with `current_code == N`; its exposure order follows frozen `MAIN100.csv`. It contains 277 records in 85 exposures, not 277 new observations.

Prepare the next bounded batch in a new `work_harps_20261101/v2/extension02/raw_followup_batch02/` directory. Before reading new raw arrays, save its selected IDs, all corresponding raw/ancillary product identities, acquisition limits and unchanged analysis rules. Check for hash-verified cached pairs before downloading missing public archive products. Keep omitted or failed pairs explicit; do not replace targets based on interesting morphology. This handoff does not claim that the next batch has already been selected or acquired.

Do not rerun the completed eight-exposure acquisition, overwrite its freeze, alter original hit catalogs or move unresolved cases out of the queue merely because an epoch metric looks ordinary. Review every selected event and every covering order. Preserve original and later mapping decisions separately. After the remaining raw review, follow up the six new unresolved structures, V2E2-0225 and the four older mapping limitations (V2-0149, 0231, 0232, 0333). Rubin remains the approved second week (8–14 November) and has not yet been analyzed.

## Restore evidence only when needed

The [four input packages](work_harps_20261101/v2/extension02/checkpoints/SAVED_INPUTS.md) contain the 100 new science spectra and the already inspected eight raw/ancillary pairs. Exact URLs, lengths and SHA-256 values are in [LIBRARY_INPUTS.json](work_harps_20261101/v2/extension02/checkpoints/LIBRARY_INPUTS.json) and the continuation state. Restore archives into a separate staging directory first. Member paths such as `v2/extension02/...` are relative to `work_harps_20261101`; copy verified data to the expected locations without replacing newer status documents with historical copies inside archives. The remaining raw pairs are not claimed to be present in those four packages.

GitHub preserves all 4,370 epoch profiles in [18 ordered binary parts](work_harps_20261101/v2/extension02/epoch_followup/PROFILE_ARRAYS_PARTS.json). Run `python3 restore_profile_archive.py` inside `epoch_followup`; it validates each part and reconstructs the exact original ZIP against [PROFILE_ARCHIVE.json](work_harps_20261101/v2/extension02/epoch_followup/PROFILE_ARCHIVE.json). Extract that `PROFILE_ARRAYS.zip` inside `epoch_followup` to restore the `profiles/` tree. Source spectrum hashes are in `INPUT_CHECKS.json`; profile hashes are in `ALL_EPOCH_MEASUREMENTS.csv`.

For verification in a separate working copy with inputs restored, run from `work_harps_20261101`:

```bash
python3 v2/extension02/epoch_followup/independent_audit/check_epochs.py
```

The audit writes its own report, so preserve the published report. The recorded audit used Python 3.12.14, NumPy 2.3.5 and Astropy 8.0.2; plotting also uses Matplotlib. Do not rely on a previous session's absolute runtime path. Production reproduction with `measure_epochs.py` is optional and requires a separate output copy without an existing `SUMMARY.json`. It is not a prerequisite for moving to the pending raw queue.

## Keep continuity current

After each completed batch, record exact input IDs/hashes, commands and process outcomes, counts and unresolved cases, reproducible outputs and the next queue head. Update this entry point and a new/current continuation state only after the new results are verified. Keep frozen scientific inputs and historical result tables unchanged. Publish the documentation and evidence, then read back the remote commit and key files before claiming GitHub is updated.

The user explicitly approved public GitHub updating on 1 November 2026. The saved `SETI_HARPS_EPOCH336_2026-11-01.zip` contains an earlier awaiting-approval publication note; that note is historical. Authorization is now granted. Publication on both `main` and `optical-harps-week-20261101` has now been verified by remote readback; see [PUBLICATION_RECEIPT.json](work_harps_20261101/v2/extension02/epoch_followup/PUBLICATION_RECEIPT.json). The receipt also verifies all 18 archive-part hashes and lengths. Use the current committed checkpoint and its verified remote commit, not the old archive note, to establish publication state.

No science worker or automatic background search is running at this checkpoint. Continuity is provided by the durable results and explicit queue; it does not imply execution between conversation turns.
