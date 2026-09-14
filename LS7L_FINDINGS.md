# LS7L: engineering coverage and PRF phase inputs verified

Completed 14 September 2026. The engineering acquisition, fixed closed-context
extraction and independent raw-byte audit are complete. The physical
motion-to-processed-pixel response benchmark has not yet been evaluated.

## What the new inputs establish

| Quantity | Sector 29, camera 4 / CCD 3 | Sector 32, camera 4 / CCD 4 |
|---|---:|---:|
| Closed contexts / saved science cadences | 10 / 4,010 | 10 / 4,010 |
| Selected camera-4 quaternion rows, including padding | 40,600 | 40,600 |
| Quaternion rows in every fixed 20-second coverage bin | 10 | 10 |
| Fixed thermal channels / selected rows | 13 / 15,296 | 13 / 15,298 |
| Guide-star count range in the selected quaternion rows | 198–200 | 196–200 |
| FOM range, recorded without a quality cut | 236–252 | 236–252 |

All selected quaternion and thermal values are finite. Every quaternion context
has 4,060 rows, with approximately two-second spacing and no duplicate or
decreasing timestamps. All **8,020** fixed science-cadence bins have ten
quaternion samples. This establishes numerical coverage on the existing
twenty contexts; it adds no observing days and is not a detector result.
[Complete input summary](results_ls7l_inputs/summary.json),
[all coverage rows](results_ls7l_inputs/cadence_coverage.csv),
[table and sampling accounting](results_ls7l_inputs/tables.json).

The thermal channels have median spacing near sixty seconds and gaps up to
approximately **420 seconds**. Their 30,594 rows are preserved at their original
times, without interpolation. They cannot simply be treated as two-second
motion samples. The quaternion packet retains both camera and SC-labeled
components; their mapping to detector motion has not been selected.

## Timing evidence and its limits

The engineering files omit TIMESYS and TIMEREF, despite a generic TIME unit
label referring to BJD. Their start/stop numeric times agree with their own
UTC calendar dates under a **TDB interpretation to 20–32 microseconds**.
Interpreting the same numbers as UTC instead differs by about 69.183 seconds;
TT leaves 0.503–1.615 milliseconds. This is evidence for the numeric time scale,
not an independent calibration of each telemetry sample's physical timestamp.
[All calendar comparisons](results_ls7l_inputs/timing_metadata.json).

The extraction uses the previously saved spacecraft numeric times, LC TIME
minus TIMECORR. This matches the mission support team's documented
[TESSVectors convention](https://github.com/tessgi/tessvectors/blob/main/README.md)
and its [processing implementation](https://github.com/tessgi/tessvectors/blob/main/src/tessvectors/processing/makevectors.py).
The complete ten-sample coverage is consistent with that join. It does not
establish a POS_CORR timing error in LS7J or motivate a fitted lag correction.

A 20-second coverage bin is not the actual exposure kernel. The ten
1.98-second integrations, their readout placement, the telemetry sample's
timestamp convention and fast POS_CORR estimator kernel still require an
explicit forward model. No quaternion average or resampled thermal predictor
is supplied as a validated response.

## PRF normalization and coordinate inspection

The fifty original PRF images decompose into **4,050** 13-by-13 phase images
by their nine-by-nine array residue classes. Their flux sums span
**0.995947949571–1.000000000000**, with the largest numerical excess over one
only 1.3e-15. The maximum footprint deficit is **0.405205%**. The phase sums
reconstruct the original full-array sums; no image was renormalized.
All uncertainty entries are retained. Their sums are bookkeeping quantities,
not variances or calibrated error bounds on derivatives.
[All phase accounting](results_ls7l_inputs/prf_phase_accounting.csv),
[per-model summary](results_ls7l_inputs/prf_summary.json).

The [mission exporter](results_ls7l_inputs/documentation/export_mat2fits.m)
and [mission README](results_ls7l_inputs/documentation/00README.txt) were
restored with their original LS7K hashes. Source inspection establishes that
the exporter copies ccdRow/ccdColumn directly into the filename, reference
keywords and physical-WCS reference values. It applies no explicit 44-column
addition or subtraction. It reads prfRow/prfColumn but does not write those
arrays into the FITS product.

This does **not** by itself establish the inherited MATLAB coordinate
convention relative to the science pixels. The README's collateral-column
warning remains in tension with treating all RAWX labels as automatically
identical. Neither an extra 44-column shift nor zero shift has been adopted
as a science-model choice. The phase residue labels are array indices; their
physical source-displacement sign still needs known-answer checks.

## Verification and public identities

All four complete original files total **1,409,981,760 bytes**. Both engineering
files contain 588 HDUs; both quaternion files contain five. All **1,186**
HDU locations and mission CHECKSUM/DATASUM pairs pass, and all four physical
header chains close at the recorded file sizes.
The complete source headers and original file hashes are public in
[the schema packet](results_ls7l_engineering/REPORT.md).

The independent selected-input audit verifies **1,066,182 raw table scalar
values**, all **8,020 coverage counts**, **1,368,900 raw calibration/uncertainty
values**, and **8,100 phase/uncertainty sums**. Maximum scalar-versus-array sum
discrepancy is 4.44e-16. All 72 entries in the LS7K input and LS7L schema
manifests remain unchanged.
[Independent audit](results_ls7l_inputs/AUDIT.json).

- Schema source freeze: `af7266a9aef8cd8d398419c24b79f72bd746b8e1`.
- Audited schema result: `2c95fdd80618d5135cf2301d90006ec507b7c056`.
- Selected-input freeze: `32a3840eba5325ed98a6e2b6597ac35a495615a3`.
- Audited selected-input result: `665d952f92e6b3687a4eb76976b87e8629db0014`.
- Successful [schema run](https://github.com/andersenmartin-blip/setisearch/actions/runs/34843723232)
  and [selected-input run](https://github.com/andersenmartin-blip/setisearch/actions/runs/34844802350).

The unavailable local runtime was replaced by these explicitly started
GitHub runs. The earlier partial byte-range evidence was absent from the
recovered Git tree; its preservation is not claimed. The four fixed source
URLs and amended acquisition budget remained unchanged.

## Decision and next work

The engineering availability question is now answered positively for these
contexts, and phase normalization has been measured. Proceed with the remaining
coordinate and physical-response specification described in
[LS7L_CONTINUATION.md](LS7L_CONTINUATION.md). Resolve the original MATLAB
coordinate/phase definition or a primary mission implementation before choosing
a mapping; combine that with deterministic translation, finite-stamp flux,
exposure integration and uncertainty tests.

Guide-star counts provide no target identities or estimator weights. Target
exclusion, upstream pulse coupling and exact fast POS_CORR uncertainty remain
unestablished. Saved-pixel injections still cannot prove upstream protection.
The next benchmark must state those limits and freeze any native-response
comparison before scoring it.

LS7J remains a closed negative result. There is no gain/sign/lag/profile retry,
adopted detector, new candidate or opened unused TESS/M43 evaluation.
