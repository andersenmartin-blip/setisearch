# LS7L closed-context extraction and calibration-array checks

Frozen 14 September 2026 after the four source schemas were published at
`2c95fdd80618d5135cf2301d90006ec507b7c056`, before reading selected
engineering values. Exact tables, source hashes, formats and ranges are in
[config/ls7l_engineering.json](config/ls7l_engineering.json).

## Scope and fixed extraction

Keep the same twenty closed contexts and their 8,020 LS7K timing rows.
Select CAMERA4 in each quaternion file, retaining all twelve columns:
TIME, C4_FOM, C4_NUM_GSUSED, C4_NUM_MSTOT, C4_Q1–Q4 and C4_Q1_SC–Q4_SC.
Do not choose a quaternion frame, infer handedness, or convert it to pixels.

For each sector, select thirteen camera-4 thermal tables: the target CCD's
ALCU and board-temperature channels, driver and interface temperatures, and
pt1000 sensors 1–7, 9 and 10. Retain TIME, VALUE and RAW without interpolation
or outcome-dependent channel selection. The target CCD is 3 for sector 29 and
4 for sector 32. Column names alone do not establish physical sensor placement.

For every table retain exactly the union of the ten saved spacecraft-time
intervals extended by 60 seconds on either side, endpoints included. Preserve
original row indices, ordering, duplicates, nonfinite values and raw units.
Only TIME is inspected outside these intervals to locate the rows. No quality
cut is applied. Report missing/duplicate/unsorted samples and field finiteness.

Use the numeric spacecraft time already saved in LS7K: LC TIME minus TIMECORR.
This follows the mission support team's [TESSVectors description](https://github.com/tessgi/tessvectors/blob/main/README.md)
and its [processing implementation](https://github.com/tessgi/tessvectors/blob/main/src/tessvectors/processing/makevectors.py).
These are evidence for the join convention, not for exact POS_CORR provenance.

Engineering headers label TIME as TJD = BJD-2457000 but omit TIMESYS and
TIMEREF. Compare their TSTART/TSTOP numerically with their own DATE-OBS/DATE-END
UTC calendar values under explicit UTC, TT and TDB interpretations. Publish
all discrepancies; do not silently declare the missing time reference or
estimator kernel resolved. No fitted lag, sign or gain is permitted.

For coverage only, count quaternion samples in the half-open numeric interval
[t-10 seconds, t+10 seconds) around each saved cadence and record worst FOM
and guide-star count when finite. These counts are not exposure averages:
the ten 1.98-second integrations, readout placement, quaternion timestamp
semantics and estimator kernel still need the physical-response specification.
Guide-star counts do not establish whether TIC 307210830 participates.

## Calibration checks without a response fit

Re-read the fifty fixed PRF files and preserve their original hashes.
Enumerate every zero-based residue pair (r,c) in 0..8 and extract
PRF[r::9,c::9], each a 13-by-13 array. Record all 4,050 phase sums and the
sum of corresponding uncertainty entries, without renormalizing. A sum of
uncertainty entries is bookkeeping, not a variance or confidence interval.
Check that all phase sums reconstruct the complete image sum and independently
decode every original image from its big-endian FITS bytes.

Retrieve the two small mission documentation files named and hashed in LS7K's
inventory (00README.txt and export_mat2fits.m); require the exact old hashes.
Inspect the exporter before choosing the absolute-coordinate mapping.
No native pixel values, residual comparisons or detector scores enter this
stage. No source-position phase sign or extra 44-column correction is adopted.

## Verification and publication

Independently decode every selected scalar from the frozen raw FITS table
offset and field format, without Astropy's table reader. Recompute the selected
indices from scalar time comparisons and compare every output array. Audit
all 8,020 per-cadence coverage counts with a separate scalar calculation.
A separate raw-image decoder checks every PRF/uncertainty sample and each
phase sum, with a fixed 1e-12 absolute tolerance for scalar-versus-array sums. Preserve published LS7K and LS7L source manifests unchanged.

Publish the exact raw selected arrays, all per-cadence coverage rows,
phase accounting, source-bound metadata, known limitations, verification and
execution logs. Source caches are reproducible from the four original URLs.
A successful input audit does not qualify the response model or a detector.
Any later native response comparison requires its own numerical freeze.
