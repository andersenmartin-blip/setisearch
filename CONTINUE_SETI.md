# Continue SETI from the accelerated checkpoint

Read [the current machine-readable state](work_seti_20261102_accelerated/CONTINUATION_STATE.json), fetch current GitHub and compare its source hashes before new work. Another session may have advanced the project. Rubin was explicitly advanced to **2–8 November 2026**, in parallel with bounded HARPS follow-up. Earlier checkpoints and calendar dates are historical.

## Completed HARPS work

The initial raw-image review covers all 669 V2 records. Provisional totals remain **403 A / 46 O / 185 U / 35 M / 0 N**. The older 333 cohort remains 209 A/25 O/95 U/4 M; the newer 336 remains 194 A/21 O/90 U/31 M. Coverage is unchanged: 300 unique exposures, 20 targets, 70.874650833 hours. V1 searched all 300 exposures (22 preliminary hits); V2 searched the latter 200 (669 records). No qualified laser candidate or calibrated null is established.

- [The fixed mapping diagnostic](work_harps_20261101/v2/extension02/mapping_followup_remaining_20261102/README.md) is complete for all 35 M records in 21 exposures: 1,512 native orders and 7,517 measured reference windows. The last 20 exposures were independently reconstructed with 179,698 metric comparisons. All 35 remain M. Improved robust correlations in some orders do not constitute a newly validated mapping gate; all eight previously failed order 70 references remain poor under the added comparisons. Missing detector coverage is unchanged. Do not rerun this completed queue merely to resume.
- [The normalization follow-up](work_harps_20261101/v2/extension02/normalization_context_20261102/README.md) covers V2E2-0092 and V2E2-0104: 28 preserved profiles, 8 focused windows and 12 native/raw contexts. Four low-continuum flags concern the same later observation on 27 August 2023, not either discovery. Low local flux and uncertain noise limit the comparison; positive scalar normalization alone leaves Pearson correlation invariant. A local trace-offset caveat remains explicit. Both records remain U. Independent numerical and separate visual checks passed.
- [Epoch comparison](work_harps_20261101/v2/extension02/epoch_followup/README.md) is already complete: 336 new records, 2,185 event/exposure pairs, 4,370 profiles. Do not repeat it as new science.
- [Unresolved context](work_harps_20261101/v2/extension02/unresolved_context_20261102/README.md) covers all 90 new U records, 39 nominal-resolution neighborhoods and 37 overlapping-profile neighborhoods. These are correlated groups, not independent physical signals. The older 95 U records remain outside that grouping.

## Completed Rubin main screen

[The accelerated Rubin study](work_rubin_20261102/README.md) uses actual world-public Rubin/Fink data, not ZTF or simulated telescope data. Twenty separate development objects preceded a metadata-selected main sample of 188 unique Gaia associations. Exact development IDs, positions and Gaia counterparts were excluded. The field is bounded and alert-selected, not an all-star survey.

The main selection, detector and code were published in commit `541357ebea3548836285857b548777723744ae15` before main photometry. All 49 files were read back exactly before release. Eight main API jobs succeeded without retry: 807 source measurements for 188 objects and 77 forced measurements for 10 objects. [The complete result](work_rubin_20261102/main_analysis/README.md) accounts for all 188 objects in both separate streams.

Only **2 primary objects / 7 October measurements** were numerically evaluable. Separately, **3 forced objects / 14 measurements** were evaluable; this set includes the two primary objects. Zero rows meet both fixed criteria. The minimum 50-object pilot is **not met**. Unknown withdrawal status, missing forced quality flags and approximately108–112-day baseline gaps remain. This is a limited feasibility study, not a qualified null result.

The fixed method uses same-band direct science flux, 180 days of prior context, at least five distinct visits on three earlier UTC dates, and exclusion of the entire tested UTC date. A trigger requires ≥0.3 mag dimming and conservative deficit score ≥5; the score is not calibrated Gaussian significance. No thresholds changed after main results.

All 36 development injections are preserved: 18 sampled cases recovered and 18 gap cases unsampled; unchanged controls have zero hits. The placement design is not random phase and does not estimate survey sensitivity. Independent main audit passed 33,609 comparisons; controls passed 528,411 comparisons. No main trigger cutouts were requested because both complete trigger lists are empty.

## Next work

The separate [metadata feasibility extension](work_rubin_20261102/extension_feasibility/README.md) is complete: 940 new objects and 8,277 metadata rows yield 104 temporal/quality prerequisite passes. Gaia matching and precision remain untested. Continue their separately frozen Gaia validation before considering more main stars. It preserves the original 188 and fixed method; up to 312 additional identities would respect the approved 500-object total. Metadata temporal/quality eligibility is only a necessary condition, not photometric evaluability or a stellar association. No replacement of failed main objects and no relaxation of thresholds is authorized by a low yield. Read its actual completion status and explicit next action in the current state.

For HARPS, any revised mapping method needs declared controls and independent validation against known perturbations before homogeneous application. The descriptive mapping queue is finished. Follow remaining unresolved-context actions using archived data; the two normalization cases already have their focused follow-up. Preserve all 185 U and 35 M labels unless separately documented new evidence warrants a change. Barycentric coherence, grouping and local trace offsets alone cannot assign origin.

## Restore and maintain continuity

Original HARPS archive identities and hashes remain in the current state and batch checkpoints. Restore into staging, verify member hashes and copy only canonical payloads; historical reports must not overwrite current state. Paths beginning `v2/extension02/` in HARPS archives are relative to `work_harps_20261101`. Partial files are never science inputs.

See [HARPS restoration instructions](work_harps_20261101/v2/RESTORE.md). New mapping diagnostics and normalization arrays have verified ordered evidence parts and restore scripts. Rubin original API responses, exact queries, receipts, Gaia CSV, code and complete outputs are preserved with this repository; no login is needed to reproduce the saved-data analysis. Run reproduction in a separate copy to retain published timestamps and stop guards. Network reacquisition can return a later service state.

Public GitHub updates are authorized. Preserve method/input identities, decisions, limitations and concrete queues after each continuation. Publication receipts identify verified results commits and trees. No unattended science search or paid service is configured.
