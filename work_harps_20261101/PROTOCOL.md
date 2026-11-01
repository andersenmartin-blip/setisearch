# HARPS optical emission pilot — activated 1 November 2026

The authorized work window is 1–7 November 2026. Rubin follows on 8–14 November. These are work-session plans, not an unattended background job. Progress may be made earlier than the daily milestones.

## Selection and independent development

The main cohort is the 100 rows in `selection/MAIN100.csv`: 20 target labels, five individual exposures each, at least three observing nights per label. Selection was fixed using metadata before downloading main spectra. The bounded source catalogue contains 5,000 alphabetically ordered rows and is not representative of the full HARPS archive. The exact rule, exclusions and source hashes are in `selection/SELECTION.json`.

HD203608 and two HD100508 exposures are development only. Three separate, initially unopened HD100508 exposures provide the injection backgrounds. No development target is in the main cohort. The 2025 article and pinned public repository are methodological references; this implementation is independent and is not a reproduction of the entire published survey.

Both reduced-product ADP identifiers and raw-progenitor identifiers are compared with `literature/UPSTREAM_REFERENCED_IDS.json`, extracted from text tables at upstream commit `195bb3e3e4d067b153895fd2723f839f00e8f82a`. No match means absence from that reference list, not proof of no earlier search by anyone.

## Frozen search

Use `code/DETECTOR_CONFIG.json` and the implementation hashes in `code/DETECTOR_FREEZE.json`. Search each exposure independently over 3800–6900 Angstrom, preserving the supplied barycentric air-wavelength frame. The centered 101-sample median and population standard deviation define a local contrast. A run of 4–60 consecutive samples at contrast at least 3.5 is a preliminary emission hit. Save every threshold run, including shorter and broader runs. No threshold change or target reselection is allowed in response to main results.

Nonfinite flux, exactly zero filled samples, and 50-sample segment margins are excluded. The recorded ERR column is not a usable uncertainty vector in the inspected spectra. Local scatter includes absorption structure and the candidate itself; this statistic is not Gaussian significance, a calibrated SNR, or a false-alarm probability. Flux is uncalibrated ADU.

Header checks must establish consistency of identity, times, exposure length, provenance and units before opening the main flux. Intended-target coordinates are reviewed separately from recorded telescope pointing. Any unresolved identity limitation must remain explicit in the report. Download/checksum failures remain recorded and cannot be replaced after looking at flux.

## Sensitivity validation

`validation/VALIDATION_PLAN.json` freezes 48 Gaussian injections: three backgrounds, four wavelength positions and four amplitudes. The four amplitudes reuse each of 12 geometries and are not 48 independent trials. Width is wavelength/115,000. Amplitude is expressed in the unmodified 101-sample local population standard deviation, not in the detector's post-injection contrast. The same frozen detector is applied to injected and unmodified patches. Keep every miss and control outcome, without tuning the detector afterwards.

These tests measure recovery in selected reduced 1D data only. They do not measure losses in acquisition/reduction, completeness over every stellar spectrum or wavelength, nanosecond pulse timing, or physical transmitter power. A low-recovery result restricts interpretation rather than triggering hidden optimization.

## Reporting and follow-up

Publish input identifiers and SHA256, complete threshold-run and preliminary-hit lists, searched-bin and exposure accounting, injection results, code and a runnable procedure. A preliminary hit is not a laser or SETI detection. Raw-image checks, terrestrial/instrumental emission, natural spectral lines and cross-epoch comparisons are follow-up tasks. An isolated event is not rejected solely because it does not repeat. Any unreviewed hits remain explicitly unreviewed; an initial batch report does not claim the whole seven-day study is complete.

Sources: [Fields & Goodman 2025](https://arxiv.org/html/2508.08628v1); [pinned public reference repository](https://github.com/goodmanj/optical_seti/tree/195bb3e3e4d067b153895fd2723f839f00e8f82a); [ESO HARPS archive](https://archive.eso.org/).
