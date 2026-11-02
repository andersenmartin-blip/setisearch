# Continue SETI from this checkpoint

Read the [current continuation state](work_harps_20261101/v2/extension02/raw_followup_batch05/CONTINUATION_STATE.json), fetch current GitHub and compare source hashes before starting. Another session may have advanced the project. The approved plan is optical HARPS work first, then Rubin on 8–14 November 2026.

## Current status — 2 November 2026

The first raw-image review covers **all 669 V2 records**. This is review coverage, not 669 independent signals or complete physical-origin identification. [Batch05](work_harps_20261101/v2/extension02/raw_followup_batch05/README.md) acquired the previously unavailable original HD141937 product pair. V2E2-0332 and V2E2-0333 have supported mapping and provisional charge-like detector morphology (A). Historical batch04 metadata failures remain preserved.

| Cohort | Provisional artefact A | O I-compatible O | Unresolved U | Mapping-limited M | Unreviewed N |
|---|---:|---:|---:|---:|---:|
| Older 333 | 209 | 25 | 95 | 4 | 0 |
| New 336 | 194 | 21 | 90 | 31 | 0 |
| All 669 | 403 | 46 | 185 | 35 | 0 |

The survey remains **300 unique exposures of 20 targets, 70.874650833 hours**. V1 searched all 300 exposures (22 preliminary hits); V2 searched the latter 200 (669 records). No observing time was added by follow-up. There is **no qualified laser candidate or calibrated null result**.

## Completed follow-ups

- [Epoch comparison](work_harps_20261101/v2/extension02/epoch_followup/README.md): all 336 new records, 2,185 event/exposure pairs and 4,370 profiles among the new 100 spectra. Earlier 200 exposures were excluded; discovery observations are excluded from other-epoch summaries. Audit passed. Do not repeat merely to resume.
- [Mapping diagnosis](work_harps_20261101/v2/extension02/mapping_followup_20261102/README.md): all 35 M records, 21 exposures and 43 distinct exposure/order combinations. There are 28 reference-only cases, five edge-only cases and two with both limitations. Original gates and labels are unchanged.
- First M record **V2-0149** has a completed fixed raw-reference diagnostic over all 72 orders of its exposure. Its order0 predicted trace falls outside the active detector; its order1 original Pearson gate still fails. Robust correlation and offset diagnostics do not recover missing pixels or authorize a coordinate correction. Do not restart this completed diagnostic.
- [Unresolved-context analysis](work_harps_20261101/v2/extension02/unresolved_context_20261102/README.md): all 90 new U records form 39 nominal-resolution neighborhoods / 37 overlapping-profile neighborhoods, with an exhaustive evidence-action queue. Groups are not independent physical signals. The older 95 U records are unchanged and outside this derivative analysis. Fixed template widths are not measured linewidths.

## Next action

There is no pending first-review N queue. Continue the mapping-limited queue, beginning with **V2-0231**, the next record without the new raw-reference diagnostic. Read existing evidence before defining a bounded follow-up. Distinguish missing detector coverage from low reference correlation. Freeze original product identities, candidate exclusions, methods and limits before new array calculations; reuse hash-verified originals. Preserve failed gates and missing coverage. Do not lower thresholds or shift coordinates to make a selected event pass.

After mapping investigations, use the unresolved-context action queue: inspect unnormalized data for V2E2-0092 and V2E2-0104, address inadequate BERV baselines, then inspect grouped and individual profiles with stellar/instrument context. Routes are evidence requirements, not significance rankings. Preserve all 185 U records across both cohorts. Epoch coherence alone cannot determine origin.

Rubin remains **8–14 November** and has not been analyzed. No unattended science search is configured.

## Restore and preserve continuity

Input archive names, hashes and saved-file identities are in the current state and each batch's checkpoint. Extract into staging: paths beginning `v2/extension02/` are relative to `work_harps_20261101`. Copy verified canonical payloads and receipts only; do not overwrite current-state files with historical archive reports. Partial files are never science inputs.

See [restoration instructions](work_harps_20261101/v2/RESTORE.md). Batch05 evidence has a recoverable archive; all 4,370 epoch profiles remain recoverable from their 18 ordered parts. Run audits in a separate copy because reports are rewritten. Use recorded dependencies instead of old absolute runtime paths.

Preserve source IDs/hashes, methods, limitations, evidence, decisions and the next queue after each analysis. Original detectors/catalogs and historical decisions remain immutable. Public GitHub updates were authorized on 1 November. Publication receipts identify remotely verified commits/files; the receipt's own final commit is verified after publication.
