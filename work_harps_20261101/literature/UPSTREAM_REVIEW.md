# HARPS upstream source and exposure review

Reviewed on 1 November 2026. Repository: https://github.com/goodmanj/optical_seti at commit `195bb3e3e4d067b153895fd2723f839f00e8f82a` (29 July 2026).

## Exposure overlap

`UPSTREAM_REFERENCED_IDS.json` contains 4,132 ADP product IDs and 1,827 HARPS raw exposure IDs found in the current upstream text result tables. The fuller `upstream_referenced_exposure_ids.json` gives file and line provenance for each ID. These are conservative exclusions: some references are inventories, and absence is not proof that an observation was never searched. Different ADP products can refer to the same raw exposure, so compare both identities.

The repository is newer than the August 2025 paper and its tables cannot be presented as the exact paper's exposure manifest. The original input `bigsearchstage1.txt` named by the script is not in the tree. The strongest claim for a new sample is: no overlap with this pinned public reference set, with any missing raw-ID match kept unknown.

The 2019 cutoff concerns the parent target catalogue, not every actual spectrum searched. For example the current core table explicitly references ADP.2023-06-04T01:01:48.415 and HARPS.2023-06-03T09:09:16.351 for BD-114672.

`OSETI_targets.txt` contains 2,820 parsed data rows (the paper says 2,821 stars). Its coordinates, spectral types, temperatures and distances are useful metadata but require object and epoch cross-checks; alias strings alone are insufficient. The exploratory metadata pool is illustrative only and has not selected or exposed any science sample.

## Code review

The published 2025 rule is running median and population standard deviation in a roughly 101-pixel window, at least 4 and at most 60 consecutive pixels above 3.5 local standard deviations, with airglow exclusions and later width/raw-image checks. The catalogue wrapper explicitly calls these parameters.

The current standalone main script instead requests window 1001, percentile 85, multiplier 7.5 and max_count 500. It imports an undefined `airglow_elimination` function and refers to an author's local input path, so it is not a directly reproducible end-to-end entry point.

The core detector hardcodes a loop start of 50 and pixel-index airglow masks. Start 50 is incompatible with the 1001-point setting, because early continuum indices become negative. The final threshold-exceeding run is not flushed. The FITS reader assumes the first two columns contain wavelength and flux without verifying header units; fitting code attaches Angstrom units even though a loader comment says nm. The Gaussian retry uses the same width initialisation and accesses a compound model as though it were a single model. These points justify a small independent implementation of the stated method with header-based units, explicit masks and boundary handling; they do not justify another broad platform project.

No LICENSE/COPYING file was present in the pinned tree. Retain upstream code privately for inspection; publish our own implementation and source links unless reuse permission is separately established.

## Scientific caveat

The paper's abstract, body and table disagree about counts of follow-up stars:8 sources in abstract,6 stars in section IV.1,7 unique names in Table 4. Avoid using that count to select exclusions. Use actual ADP/raw IDs.

Primary paper: https://arxiv.org/html/2508.08628v1
Pinned repository: https://github.com/goodmanj/optical_seti/tree/195bb3e3e4d067b153895fd2723f839f00e8f82a
