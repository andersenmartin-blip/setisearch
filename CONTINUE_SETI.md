# Continue SETI from this checkpoint

Start with the [current continuation state](work_harps_20261101/v2/extension02/raw_followup_batch02/CONTINUATION_STATE.json). Fetch current GitHub first and compare checkpoint hashes before starting; another session may have advanced the project. The state preserves every pending event ID, exposure/product identity and exact source hashes.

## Completed work

The survey contains **300 unique exposures of 20 targets, 70.874650833 hours**. V1 searched all300; V2 searched the latter200 and produced669 records. There is no qualified laser candidate and no calibrated null result.

The [epoch comparison](work_harps_20261101/v2/extension02/epoch_followup/README.md) is complete: all336 new V2 records against same-target exposures among the new100, 2,185 event/exposure pairs and4,370 profiles. Discovery observations are excluded from other-epoch summaries. Its independent numerical audit passed. Earlier200 exposures were excluded; follow-up adds no observing time. Do not repeat this calculation merely to resume.

[Raw batch02](work_harps_20261101/v2/extension02/raw_followup_batch02/README.md) selected16 exposures and68 previously unreviewed V2 records in frozen MAIN100 order. It preserves the earlier65 selected V1/V2 decisions and the later mapping overlay. The current table covers all336 new V2 records:

| New V2 status | Count |
|---|---:|
| Provisional detector artefact | 80 |
| O I-compatible | 13 |
| Unresolved spectral structure | 27 |
| Insufficient raw mapping | 7 |
| No raw review yet | 209 |

New unresolved IDs: V2E2-0001, V2E2-0016, V2E2-0022, V2E2-0023, V2E2-0025, V2E2-0026, V2E2-0027, V2E2-0028, V2E2-0029, V2E2-0033, V2E2-0035, V2E2-0042, V2E2-0043, V2E2-0044, V2E2-0045, V2E2-0046, V2E2-0047, V2E2-0050, V2E2-0051, V2E2-0052, V2E2-0053, V2E2-0054, V2E2-0104, V2E2-0128, V2E2-0129, V2E2-0130, V2E2-0131.
New mapping-limited IDs: V2E2-0018, V2E2-0034, V2E2-0041, V2E2-0070, V2E2-0074, V2E2-0075, V2E2-0225.
The older333 remain209 A,25 O,95 U,4 M. Their mapping limitations are V2-0149,0231,0232,0333. All codes are provisional follow-up descriptions, not confirmed physical origins.

## Next action

The next queue head is **V2E2-0085**, exposure **ADP.2025-03-16T01:01:40.685**, target **HD109833**. There are **209 pending records in 69 exposures**. Follow the exact `current_code == N` queue in the current state; prepare a separate `raw_followup_batch03/` with selected IDs, raw/ancillary identities, fixed limits and analysis rules before new raw-array reads. Reuse verified cached pairs when available. Preserve failures/omissions and do not replace selected targets based on morphology.

Review every selected record and every covering order. Preserve original and later mapping decisions. After pending raw review, follow up all unresolved spectral structures and mapping limitations; epoch metrics provide context, not an origin veto. Rubin remains the approved second week (8–14 November) and has not been analyzed.

## Restore and verify

Restore input archives from the exact names, lengths, SHA-256 values and Library links in the current continuation state. Extract into a separate staging directory first. Member paths beginning `v2/extension02/` are relative to `work_harps_20261101/`. Copy verified science inputs without replacing newer status documents with historical report copies. The original four input packages cover the100 science spectra and first8 raw/ancillary pairs; batch02 raw inputs require the separate checkpoint recorded for this batch.

GitHub preserves all4,370 epoch profiles in [18 ordered parts](work_harps_20261101/v2/extension02/epoch_followup/PROFILE_ARRAYS_PARTS.json). Run `python3 restore_profile_archive.py` inside `epoch_followup`; it validates and reconstructs the exact ZIP. Extract there to restore `profiles/`. See [restoration instructions](work_harps_20261101/v2/RESTORE.md) and each batch's README for audit commands. Run audits in a separate working copy because reports get rewritten. Use installed packages and recorded versions; do not rely on an earlier session's absolute runtime path.

## Maintain continuity

After each verified batch, save source IDs/hashes, commands and outcomes, decisions, unresolved cases, evidence and exact next queue. Keep frozen catalogs and historical results unchanged. Publish the new result, then verify remote branch heads and key file hashes before claiming GitHub is current. The user explicitly authorized public GitHub updates on1 November2026. Earlier archive notes requesting approval are historical.

The completed batch was published and remotely verified on both `main` and `optical-harps-week-20261101` at content commit `2fdc358ea21385b12762c945c94143fac943b64b`. See the [publication receipt](work_harps_20261101/v2/extension02/raw_followup_batch02/PUBLICATION_RECEIPT.json) for exact key-file and binary hashes. No automatic background science search is configured. Durable evidence and a precise queue support later continuation; they do not imply execution between turns.
