# SETIsearch

A transparent, reproducible search for intermittent narrowband signals across
multiple observing epochs. Exoplanet motion supplies a frequency-drift
hypothesis; it does not establish where an observed signal originated.

The **light-sail (LS) research branch** explores whether radiation associated
with beamed propulsion could leave detectable radio or optical signatures.
The current LS work uses TESS photometry to qualify a search for short glints.
Neither an optical brightening nor a radio trigger alone establishes artificial origin.

**Start here: [current status and continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PROJECT_STATUS.md).**

The [12 September publication record](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-12.md)
links the complete LS7C/LS7D release and the preserved historical archives.

## Where the project stands

**LS7D TESS noise diagnosis completed, 12 September 2026.**
The diagonal pixel model misses strong cancellation between pixel fluctuations.
All 120 original trial-noise ratios reproduce across 34 windows in ten shared
backgrounds; eight analytical tests and the covariance audit pass. This is
method development with no new candidate or adopted detector. Next work combines
covariance-aware noise, residual handling and broader nuisance controls on the
closed data. [Read the result and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7d_noise/REPORT.md).

**LS7C TESS qualification completed, 12 September 2026: the joint test failed.**
The noise-aware pixel method completed 1,460 digital trials over 18.78 searchable
cadence-days of L 98-59 sector 32. All planned matched-strength tests reach the
screening threshold, but stellar recovery is insufficient and 16/120 compact
pixel controls are accepted. All 325 native excursions fail spatial screening;
no LS candidate is promoted. Next work measures covariance and residual
contamination on the closed sectors before another independent evaluation.
[Read the reviewed result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7c_tess/REVIEW.md).

**M43AI native evaluation is complete:** The fixed combined rule failed the predeclared same-sequence native challenge. It recovered 53/64 signal cases and lost 0/53 signals required by the reference union. 1/48 controls and 0/128 native null cases had surviving members.
The model remains unadopted; all inputs use one observing sequence.
[Read the complete result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/MILESTONE_43AI_NATIVE_VALIDATION_RESULT.md).

M43AF's frozen joint response rule failed qualification: none of the 1,156
tested boundaries met all requirements. The complete **502-record study and
its lossless archive are now public**: 69 parts restore 508 original files,
verified byte for byte. The original M43AF held-out panels remain unopened.
[Read the complete study](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/MILESTONE_43AF_RESPONSE_STUDY_RESULT.md).

There is no new M43AF astronomical candidate or adopted detector. The earlier
**M33 HD 3651 follow-up at 1424.934238382 MHz remains unresolved**, pending an
independent observing cadence. It is not a detection or technosignature claim.

| Read or do | Entry point |
|---|---|
| Continue the active work | [Current project status](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PROJECT_STATUS.md) |
| Inspect current TESS work | [LS7D noise diagnosis](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7d_noise/REPORT.md), [LS7C reviewed result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7c_tess/REVIEW.md), [frozen protocol](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7C_TESS_PROTOCOL.md), and [previous LS7B result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7b_tess/REVIEW.md) |
| Inspect the latest native evaluation | [M43AI result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/MILESTONE_43AI_NATIVE_VALIDATION_RESULT.md) |
| Inspect the separate historical TESS development | [LS7C sector 29 archive: 1,300 retrospective trials](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/archives/ls7c_sector29_development/README.md) |
| Understand the failed training rule | [M43AF training result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/MILESTONE_43AF_TRAINING_RESULT.md) |
| Inspect the frozen scientific method | [M43AF executable protocol](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/MILESTONE_43AF_EXECUTABLE_PROTOCOL.md) |
| Restore existing M43AF evidence | [M43AF continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/M43AF_CURRENT_CONTINUATION.md) |
| Follow the earlier open case | [M33 candidate investigation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/MILESTONE_33_CANDIDATE_INVESTIGATION.md) |
| Understand the long-term plan | [Project direction](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PROJECT_DIRECTION.md) |
| Revisit earlier radio LS work | [LS6 result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS6_TRAPPIST1_RESULT.md) and [LS6A result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS6A_SCAN_END_RESULT.md) |
| Read the full milestone history | [Archived README before cleanup](https://github.com/andersenmartin-blip/setisearch/blob/60bad761f4aa6eebeeef367f7a4123b80fd33e44/README.md) |

## Working with the repository

Current scientific development is on
[`m43-support-qualification`](https://github.com/andersenmartin-blip/setisearch/tree/m43-support-qualification).
The main branch provides this overview and earlier pipeline code.
Use the current status to select the correct branch and evidence archive.

Closed evaluations are restored from their sealed records. For exact M43AF
archive restoration, use the recorded Python 3.12.14 / zlib 1.3.2 and frozen
dependencies. Historical reproduction commands apply to their named milestones;
they are not commands to restart the current work.

The archive link preserves the previous full README and all its milestone
summaries. Its “current” labels and “next step” instructions describe their
historical dates. The current work queue is maintained in PROJECT_STATUS.md.
