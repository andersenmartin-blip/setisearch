# Continue SETI from the completed May reference-quality follow-up

Read [the current machine-readable state](work_harps_20261102_may_quality/CONTINUATION_STATE.json), fetch current GitHub and compare its source hashes before new work. Another session may have advanced the project. The [previous accelerated checkpoint](work_seti_20261102_accelerated/CONTINUATION_STATE.json) is preserved unchanged. Rubin remains explicitly advanced to **2–8 November 2026**. Earlier checkpoints and calendar dates are historical.

## Latest completed May quality follow-up

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

## Next work after the completed May quality phase

Use [the concrete next step](work_harps_20261102_may_quality/scientific_review/NEXT_STEP.md): prepare a bounded quantitative spatial-support comparison for V2E2-0235 in its already preserved discovery raw image, order50. The documented compact off-trace structure motivates measuring how its excess is distributed across detector rows relative to nearby trace controls. This is a new diagnostic, not a replay of the completed manual raw classification or epoch pipeline. Freeze exact windows, trace-reference controls, extraction/mapping checks and descriptive metrics before running it. Preserve mixed or inconclusive outcomes; no classifier or automatic U-to-A promotion follows from weak epoch repetition.

Do not automatically select another unused May spectrum to seek a stronger correlation. The separate quality-reference phase and the earlier monthly-selection phase are both closed. The remaining saved metadata pool contains 15 unused products (eight May, seven January), retained as inventory rather than an execution queue. All ten original queue identities and four uncovered HD135204 records remain explicit; the earlier zero-row query is not proof of archive-wide absence.

Rubin's [next-data-route review](work_rubin_20261102/next_data_route/README.md) remains complete and stopped. Reopen only a distinct prospective route with adequate public stellar history, provenance and quality. Preserve 190 main identities and unchanged detector; the 500-object ceiling leaves 310 further unique slots. Minimum50 remains unmet. No new Rubin query was made in this May quality phase.

All 35 fixed mapping diagnoses, both normalization follow-ups and the original 4,370 epoch profiles are complete. Do not repeat them merely to resume. All 185 U and 35 M remain unchanged.

## Restore and maintain continuity

For the new May quality phase, use `python3 work_harps_20261102_may_quality/preservation/restore_archive.py SCIENCE_INPUTS_MANIFEST.json`, then `restore_reference_cache.py` in the same directory, then `restore_archive.py PROFILE_EVIDENCE_MANIFEST.json`. These restore the exact new FITS, original discovery/context references and twelve new profiles from preserved parts/archives; no live ESO request is needed. Helpers verify hashes and preserve differing files. Reproduce in a separate copy, retaining published outputs and one-shot guards.

For the new follow-up, run `python3 work_harps_20261102_berv_followup/science_acquisition/restore_inputs.py` to restore both exact FITS files from committed parts. Run `python3 work_harps_20261102_berv_followup/prospective_comparison/restore_profile_evidence.py` to restore all 20 discovery references and 24 derived profiles. Both helpers verify complete hashes and refuse to overwrite differing files. No live ESO download is needed. Reproduce in a separate copy so published outputs and one-shot guards remain intact.

Original HARPS archive identities and hashes remain in the current state and batch checkpoints. Restore into staging, verify member hashes and copy only canonical payloads; historical reports must not overwrite current state. Paths beginning `v2/extension02/` in HARPS archives are relative to `work_harps_20261101`. Partial files are never science inputs.

See [HARPS restoration instructions](work_harps_20261101/v2/RESTORE.md). New mapping diagnostics and normalization arrays have verified ordered evidence parts and restore scripts. Rubin original API responses, exact queries, receipts, Gaia CSV, code and complete outputs are preserved with this repository; no login is needed to reproduce the saved-data analysis. Run reproduction in a separate copy to retain published timestamps and stop guards. Network reacquisition can return a later service state.

Public GitHub updates are authorized. Preserve method/input identities, decisions, limitations and concrete queues after each continuation. Publication receipts identify verified results commits and trees. No unattended science search or paid service is configured.
