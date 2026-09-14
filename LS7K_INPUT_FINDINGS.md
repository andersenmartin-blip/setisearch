# LS7K completed: calibrated response inputs are available

14 September 2026. **The input assessment is complete and the raw-file audit
passes.** We now have fifty original mission PRF files, their uncertainty
images, verified timing extracts for all 8,020 reused cadences, and the
science-frame coordinate metadata. This supplies a concrete starting point
for a physical response benchmark. It does not establish an independent
motion estimator or a qualified detector.

[Audited input packet](results_ls7k_inputs/REPORT.md),
[complete measurements](LS7K_INPUT_FINDINGS.json),
[primary-source assessment](LS7K_PROVENANCE.md).

## Directly measured input contract

| Quantity | Sector 29 | Sector 32 |
|---|---:|---:|
| Camera / CCD | 4 / 3 | 4 / 4 |
| Original release | DR43 | DR48 |
| Reused contexts / timing rows | 10 / 4,010 | 10 / 4,010 |
| Science cutout columns | 757–767 | 1697–1707 |
| Science cutout rows | 255–265 | 555–565 |
| Nominal target detector x / y from celestial WCS | 763.412344 / 259.908569 | 1703.458344 / 560.313001 |
| TIMECORR range, seconds | −102.650982 to −74.428544 | −91.393922 to −53.217872 |
| Original PRF files / bytes | 25 / 5,760,000 | 25 / 5,760,000 |
| Primary PRF full-array sum range | 80.972104–81.000000 | 80.964998–81.000000 |

These values are derived from the [sealed inventory](results_ls7k_inputs/inventory.json).
The nominal target coordinates are the catalog position transformed through
the supplied WCS, not a measured per-cadence source centroid.

Both light curves record TDB, SOLARSYSTEM timing, BJD reference 2457000 and
cadence midpoint 0.5. Their frame metadata specify ten 2-second frames per
cadence, each with 1.98 seconds integration and 0.02 seconds readout: 19.8
seconds nominal integration within a 20-second cadence. This is the exposure
description; it does not specify the POS_CORR estimator's averaging kernel.

The negative TIMECORR values mean that subtracting them moves these spacecraft
timestamps later than their original barycentric timestamps. This conversion
has been checked for every saved cadence. It prepares a later engineering
join. It does not diagnose LS7J, whose original pixel/motion join already
matched cadence IDs and raw TIME values exactly.

All fifty files have the correct camera/CCD, UPDATED_2.0 primary version,
PRF/Uncertainties image types and 9-fold sampling in each dimension.
All **1,368,900** PRF/uncertainty values are finite and nonnegative. Their
internal physical WCS places FITS pixel (59,59) at the filename's grid center
and increments detector coordinates by 1/9 pixel per image sample. These
header relationships pass for all fifty files.

The full 117-by-117 array represents multiple subpixel phases. Its sum near
81 is not the flux normalization of one 13-by-13 physical-pixel source image.
Some boundary models sum slightly below 81; the original arrays are preserved
without clipping or renormalization. A subsequent model must explicitly
extract/interpolate phase-dependent pixel responses and handle finite-stamp
flux rather than silently treating the whole array as a unit-sum image.

## What remains unresolved

| Relationship | Evidence after LS7K | Consequence |
|---|---|---|
| Calibration file identity and internal coordinates | Verified for both complete CCD grids | A PRF implementation can now use fixed original inputs. |
| Absolute calibration-to-science coordinates | Both expose RAWX/RAWY; calibration column nodes begin at 45, row nodes at 1. The documentation also warns about 44 collateral columns. | A further automatic ±44 shift is not established. Trace the exporter/coordinate convention before applying one. |
| Engineering time series | Four exact sector links are present in the archive index | Sample time systems, quality, camera definitions and coverage still require file inspection. No quaternion values were downloaded here. |
| POS_CORR uncertainty | Neither restored light curve contains POS_CORR1_ERR or POS_CORR2_ERR | Missing uncertainty cannot be replaced by target-centroid errors without justification. |
| Fast-cadence estimator and target participation | Exact reference realization, temporal kernel, covariance and target exclusion were not established by the inspected sources | Keep this dependence explicit; saved-pixel injections cannot prove protection against upstream estimator response. |
| Sector-specific PRF accuracy | Mission calibration and uncertainty images exist | They do not by themselves calibrate small-motion derivatives or processed-frame residuals. |

The coordinate warning and estimator limitations are discussed with direct
mission references in [the provenance assessment](LS7K_PROVENANCE.md). Similar
keyword names alone do not resolve an absolute-coordinate convention.

The recorded engineering products are:

- [Sector 29 engineering](https://archive.stsci.edu/missions/tess/engineering/tess2020268170816_sector29-eng.fits)
  and [quaternions](https://archive.stsci.edu/missions/tess/engineering/tess2020268170816_sector29-quat.fits).
- [Sector 32 engineering](https://archive.stsci.edu/missions/tess/engineering/tess2020352110200_sector32-eng.fits)
  and [quaternions](https://archive.stsci.edu/missions/tess/engineering/tess2020352110200_sector32-quat.fits).

These links were returned by the successfully retrieved mission index. They
are not claims that the product contents have been validated.

## Verification and decision

The raw-file audit verifies 8,020 timing rows, 16,040 original motion values,
fifty PRF files, eight science-WCS corners with zero arithmetic discrepancy,
and 56 historical manifest entries. The subsequent summary checks all fifty
calibration headers against their declared detector/grid geometry.

The first attempt exposed an implementation error in serializing undefined
FITS header values. The corrected run compared against the first artifact:
only ten missing header values changed representation, all other header
values agree, all fifty PRF hashes are unchanged and all timing arrays agree.
The [correction record](LS7K_CORRECTION.md) and
[audit](results_ls7k_inputs/AUDIT.json) identify the affected keywords.
[Initial scientific execution log](publication_records/2026-09-14/ls7k_first_attempt.log).

**Proceed to a separately specified coordinate/PRF forward-model benchmark on
the same closed data.** Combine coordinate resolution, subpixel/normalization
checks, a bounded inspection of the listed engineering products, and explicit
uncertainty/upstream-dependence accounting in that work package. Freeze any
new response comparison before evaluating it. A useful PRF source is now
established; a validated motion-to-processed-pixel response is still open.

LS7J's fixed correction remains a completed failure. There is no added
observing coverage, new candidate, detector adoption or unused-sector
qualification. Standing publication authorization continues.

## Reproduce this summary

The summary function was executed directly against the retrieved sealed
inventory. The Node command below reads that same file and verifies its hash:

~~~bash
node scripts/ls7k_summarize_inventory.mjs > /tmp/ls7k-input-findings.json
~~~

Raw acquisition and independent audit commands are in
[LS7K_CONTINUATION.md](LS7K_CONTINUATION.md).

Corrected source freeze: 4084f29a0ad1be192a0126a378f128f22d0fb572.
Audited input commit: f1ce03ec5f278a8850125a169a98490ba2cfa204.
[Execution 34828406647](https://github.com/andersenmartin-blip/setisearch/actions/runs/34828406647)
completed acquisition, audit, checksum verification and publication.
