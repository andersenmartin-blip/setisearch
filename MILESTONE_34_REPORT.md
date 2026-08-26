# Milestone 34 report: legacy complete-disposition audit

Status: **CLOSED — ALL 17 PREVIOUSLY OMITTED ABOVE-THRESHOLD CLUSTERS ARE
PHYSICALLY VETOED; ZERO NEW OPEN CASES; NO DETECTION CLAIM**.

Milestone 34 closed a reporting-boundary debt in the Milestone 17 GJ 849 and
Milestone 21 HD 154345 searches. Both legacy searches used a 50-cluster
per-window report cap, and each capped 1400 MHz list ended above its unchanged
global threshold. The complete audit proves that 14 previously omitted GJ 849
clusters from the capped 1400 MHz list and three previously omitted HD 154345
clusters from its corresponding list were above threshold. Every one has
direct OFF-source coincidence evidence under the already frozen physical veto.

This is a retrospective accounting result. It does not increase either
primary search's significance, open a new target or cadence, or alter the
unresolved Milestone 33 case.

## Frozen audit

For each target, the audit generated its configuration from the published
primary JSON with exactly one search change:

`search.candidate_reporting.max_report_clusters`: **50 -> 500**.

The original six-scan primary cadence was re-extracted. All 30 slice hashes
per target matched the corresponding primary manifest. Detector v0.5.0,
Python 3.12.14, NumPy 2.5.2, Astropy 8.0.1, the remaining numerical and HDF5
dependencies, seeds, templates, activity subsets, widths, thresholds,
scrambles, completeness injections, clustering, and physical vetoes were
held fixed.

The audit required reproduction of the global result, search dimensions,
known-answer test, completeness, per-window maxima and nulls, RFI masks,
hypothesis and pre-limit cluster counts, and every previously published
cap-independent cluster measurement, top member, OFF diagnostic, and
receiver-frame signature. Every audit list is complete and below the new
500-cluster cap.

## Fail-closed repair

The initial workflow run `32965249217` published no combined result. M17
passed, while M21 stopped in verification because one ephemeris-derived
diagnostic velocity differed by `1.8189894035458565e-12` m/s. Candidate lists
and dispositions were not used to choose the repair.

Before either audit was rerun, commit
`a78554d18033961b339bfccca4885a37ae43dd0f` froze a zero-relative,
`1e-9`-absolute tolerance only for floating fields inside the acceleration
diagnostic records. All scientific search quantities remained bit-for-bit
constrained. Both targets then reran from extraction onward; no artifact from
the failed run was reused. The successful workflow run was `32966998479`.

## Complete result

| Primary search | Target | Complete clusters | Above threshold | Previously published above threshold | Newly exposed above threshold | Final accounting | New open cases |
|---:|---|---:|---:|---:|---:|---|---:|
| 17 | GJ 849 | 404 | 64 | 50 | 14 | 64 matched-OFF vetoes | 0 |
| 21 | HD 154345 | 372 | 113 | 110 | 3 | 95 matched-OFF; 16 adjacent-OFF; 2 fixed post-hoc RFI/instrumental | 0 |
| **Combined** | — | **776** | **177** | **160** | **17** | all closed | **0** |

All 14 newly exposed M17 cases lie in `m17_1400p5`, span S/N
28.5593--44.1758, and have `rfi_veto_off_source`. All three newly exposed M21
cases lie in `m21_1400p5`, each has S/N 47.2726, and has the same physical
veto. The two M21 arithmetic-family review cases at 1425 MHz retain their
separately frozen `RFI_OR_INSTRUMENTAL` resolutions; neither is newly exposed.

Expanding the retained cluster set added the non-physical
`arithmetic_frequency_family` annotation to seven already published M17
clusters. Six are below threshold and one already has a matched-OFF veto.
No annotation was removed, no receiver-alias status changed, and **zero
published dispositions changed**.

## Interpretation

- The original empirical p-values and operational thresholds are unchanged.
- A large S/N does not override simultaneous recurrence in OFF-source control
  data. The strongest newly exposed case is therefore interference, not a
  surviving candidate.
- The legacy 50-cluster limits hid follow-up accounting, not evidence that
  survives the fixed physical vetoes.
- No independent or reserved cadence and no new target was opened. Extracted
  telescope slices remain unpublished.
- This audit closes only the M17/M21 report-cap debt. Milestone 33 remains
  `UNRESOLVED_REQUIRES_INDEPENDENT_CADENCE` and is not converted into a null.

The result makes M17 and M21 eligible for a later survey-level synthesis whose
scope is explicitly restricted to the searched windows, exact motion bank,
activity model, archive-selected cohort, and measured completeness. It does
not support a population-wide or EIRP statement without further calibration.

## Reproducibility

The initial plan commit is
`2db9a5dd5dc666f3bf0e1b468c52dc1422690764`; the fail-closed repair commit is
`a78554d18033961b339bfccca4885a37ae43dd0f`; and the machine-readable result
publication commit is `48452ac8282fdae40ecf242a4e062ba5fc1055f1`.

Successful workflow run `32966998479` published:

- combined artifact `9606730936`, digest
  `sha256:4a0b964e974fd70e0b586c5f0bc7169f9f6efa3162e8273c34dd047ebfbe80fa`;
- M17 artifact `9606721624`, digest
  `sha256:6b7808c47bd3876f245019eb5ab58fbf3eb6720c2789f185c128311d614e5648`;
- M21 artifact `9606548218`, digest
  `sha256:b90083b0ed0f41412ec70dc0faff3fec7460323efaaf74106c3e25aa837638ff`.

`RESULTS_MANIFEST_M34_LEGACY_COMPLETE_AUDIT.sha256` verifies 21 published
files. Its own SHA-256 is
`0e7d4d67acc528515e197bc5a39ae75e6be1a09a08a22736d061bd2fb9a9746d`;
the combined audit-summary SHA-256 is
`742b3c1d88ed52ca60acb56b26704db29c744f7727745bff41872925245de9a0`.
The two nested result manifests each verify nine target-specific files.

The plan, repair note, machine-readable protocol, audit script, provenance,
complete search summaries, target audit summaries, null arrays, completeness
records, figures, and manifests are committed. A separate workflow
independently verifies the publication and appends a machine-readable receipt.
