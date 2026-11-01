# Continue SETI from this checkpoint

Read the [current continuation state](work_harps_20261101/v2/extension02/raw_followup_batch03/CONTINUATION_STATE.json), fetch current GitHub, and compare source hashes before starting. Another session may have advanced the project.

## Completed work and current status

The survey remains **300 unique exposures of 20 targets, 70.874650833 hours**. V1 searched 300 exposures and found 22 preliminary hits. V2 searched 200 exposures and produced 669 records. No observing time was added by this follow-up. There is no qualified laser candidate or calibrated null result.

The [epoch comparison](work_harps_20261101/v2/extension02/epoch_followup/README.md) is complete for all 336 new V2 records against same-target observations among the new 100 spectra: 2,185 event/exposure pairs and 4,370 profiles, with discovery observations excluded from other-epoch summaries. Earlier 200 exposures were excluded. Its audit passed; do not repeat it merely to resume.

[This raw batch](work_harps_20261101/v2/extension02/raw_followup_batch03/README.md) selected 115 pending records in 32 exposures. Adopted outcomes: **62 A / 7 O / 34 U / 12 M / 0 N**. All 133 predecessor selected V1/V2 decisions remain unchanged. The current new cohort is:

| New V2 status | Count |
|---|---:|
| Provisional detector artefact | 142 |
| O I-compatible | 20 |
| Unresolved spectral structure | 61 |
| Insufficient raw mapping | 19 |
| No raw review yet | 94 |

Older cohort: 209 A / 25 O / 95 U / 4 M / 0 N. Combined 669: 351 A / 45 O / 156 U / 23 M / 94 N. All origin descriptions are provisional.

Unresolved new IDs: V2E2-0001, V2E2-0016, V2E2-0022, V2E2-0023, V2E2-0025, V2E2-0026, V2E2-0027, V2E2-0028, V2E2-0029, V2E2-0033, V2E2-0035, V2E2-0042, V2E2-0043, V2E2-0044, V2E2-0045, V2E2-0046, V2E2-0047, V2E2-0050, V2E2-0051, V2E2-0052, V2E2-0053, V2E2-0054, V2E2-0086, V2E2-0087, V2E2-0089, V2E2-0092, V2E2-0094, V2E2-0095, V2E2-0096, V2E2-0098, V2E2-0104, V2E2-0110, V2E2-0114, V2E2-0115, V2E2-0116, V2E2-0117, V2E2-0118, V2E2-0119, V2E2-0120, V2E2-0121, V2E2-0122, V2E2-0124, V2E2-0125, V2E2-0126, V2E2-0127, V2E2-0128, V2E2-0129, V2E2-0130, V2E2-0131, V2E2-0133, V2E2-0134, V2E2-0135, V2E2-0136, V2E2-0138, V2E2-0139, V2E2-0229, V2E2-0231, V2E2-0234, V2E2-0235, V2E2-0236, V2E2-0237.
Mapping-limited new IDs: V2E2-0018, V2E2-0034, V2E2-0041, V2E2-0070, V2E2-0074, V2E2-0075, V2E2-0158, V2E2-0159, V2E2-0160, V2E2-0169, V2E2-0170, V2E2-0184, V2E2-0185, V2E2-0194, V2E2-0195, V2E2-0199, V2E2-0223, V2E2-0225, V2E2-0238.
Older mapping limitations: V2-0149, V2-0231, V2-0232, V2-0333.

## Next action

Next: **V2E2-0243**, exposure **ADP.2022-03-16T01:08:24.041**, target **HD124553**. The exact queue contains **94 records in 37 exposures**. Prepare a separate `raw_followup_batch04/` using frozen MAIN100 order. Freeze selection, original raw/ancillary identities, limits and methods before new raw-array reads. Reuse verified cached pairs. Do not replace failures or omitted pairs with more interesting targets. Review every selected event and every covering order.

After pending raw review, follow up all unresolved structures and mapping limitations. Epoch metrics provide context and do not veto an origin. Rubin remains the approved second week (8–14 November) and has not been analyzed.

## Restore, verify and preserve continuity

Input package names, sizes, hashes and Library identities are in the current state. The initial science/raw inputs and every later raw batch have separate checkpoints; preserve them all. Extract into staging first: `v2/extension02/` member paths are relative to `work_harps_20261101`. Copy verified payloads without overwriting newer status files with historical archive reports. Residual `.part` files are never science inputs.

All 4,370 epoch profiles are recoverable from [18 ordered parts](work_harps_20261101/v2/extension02/epoch_followup/PROFILE_ARRAYS_PARTS.json) with `restore_profile_archive.py`. Each raw batch README documents its evidence archive and audit. See [restoration instructions](work_harps_20261101/v2/RESTORE.md). Run audits in a separate copy because reports are rewritten; do not rely on old absolute runtime paths.

After each verified batch, retain source IDs/hashes, decisions, limitations, commands, evidence and the exact next queue. Original catalogs and historical results remain immutable. The user authorized public GitHub updates on 1 November 2026; earlier approval-wait notes are historical.

The completed batch was published and remotely verified on both `main` and `optical-harps-week-20261101` at content commit `6d24e1592748a8d8e44f8a13509b98474a220a03`. The [publication receipt](work_harps_20261101/v2/extension02/raw_followup_batch03/PUBLICATION_RECEIPT.json) records the complete matching tree, 13 key-file readbacks and 48 verified binary blob identities. No unattended background science search is configured.
