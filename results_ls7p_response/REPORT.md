# LS7P reconstruction: pixel moments reproduced, motion input still unqualified

Completed and verified 15 September 2026. This report accompanies an explicit
reconstruction of the frozen LS7P study, **not recovery of the earlier claimed
original run or its claimed publication**. The retained reconstruction's 16
numerical/evidence files reproduce byte-for-byte in a fresh offline execution.
Its result agrees with the earlier reported counts, but matching counts do
not establish the identity of that earlier run.

## Result and interpretation

The frozen pixel formula reproduces both archived centroid coordinates within
the prescribed binary32 rounding bound in **48,114 of 48,120 reference rows**.
All **45,422 QUALITY=0 rows** satisfy that bound. All six exceptions belong to
TIC 306739391 and carry scattered-light flag 4096; one also carries flag 64.
Their absolute centroid differences are tiny, about 2.4–3.0e-8 pixels in
Euclidean norm. Their association with a quality flag is descriptive and does
not establish the cause or authorize a new exclusion rule.

| Quantity | Sector 29 | Sector 32 |
|---|---:|---:|
| Selected reference rows | 24,060 | 24,060 |
| Both coordinates within binary32 bound | 24,055 | 24,059 |
| QUALITY=0 rows / within bound | 22,377 / 22,377 | 23,045 / 23,045 |
| Rows with archived CR records in moment mask | 411 | 410 |
| Largest shift after restoring archived CR corrections, pixels | 0.635540 | 0.603376 |
| Median background-restoration shift, pixels | 0.009718 | 0.011493 |
| Median conditional worst-correlation / diagonal error ratio | 4.256845 | 4.050284 |

These are repeated reference-star measurements in ten fixed 401-cadence
contexts per sector, not 48,120 independent observing windows. The twelve
products cover seven distinct reference stars. No new target correction,
native prediction window, pulse recovery, candidate or qualified observing
coverage is created.

The saved centroid errors agree numerically with the conditional diagonal
pixel-error calculation: the largest fractional discrepancy is below 1.2e-7.
This agreement does not validate the diagonal covariance assumption. The
unknown-correlation bound uses the same marginal errors and is neither a
calibrated confidence interval nor a bound on instrumental systematics.

Restoring archived CR corrections changes some moments by up to 0.636 pixel,
or roughly 194 times the **processed** diagonal error on an axis. That ratio
is not a detection significance: uncertainty in the restored corrections is
unavailable. Restoring FLUX_BKG separately measures dependence on the archived
subtraction, not the residual background or an improved correction.

For these twelve products the bit-8 moment mask equals the bit-2 optimal
aperture. CR records in that aperture and quality bit 64 agree exactly, with
zero missing/extra associations. LC and TPF quality values also agree in all
selected rows. All 25,506 selected sparse CR records remain accounted for;
these records are not 25,506 independent astronomical events. No mask, quality
policy, clipping threshold or star selection has been changed.

## Fixed PRF response

The archived centroid is a flux-weighted moment. Its successful arithmetic
reconstruction does not imply a unit response to physical image displacement.
The fixed effective-PRF exercise keeps both field-column conventions, without
choosing one from its outcome:

| Column offset | Available model pairs | Available cases | Largest unit-response error, pixels | Largest local-inverse error, pixels |
|---|---:|---:|---:|---:|
| 0 | 11 / 12 | 99 / 108 | 0.090293 | 0.055087 |
| -44 | 10 / 12 | 90 / 108 | 0.090930 | 0.046084 |

All **216 prescribed case slots** are audited, including **27 unavailable**
slots from three reference/convention pairs. Their original nonzero MATLAB
row/column-shift annotations remain uninterpreted. The nine unavailable
slots for each pair are preserved; no PRF is extended, shifted, renormalized
or otherwise repaired to obtain an available result. The preflight response
and the reconstruction response agree exactly.

The available cases are isolated-source, fixed-aperture model calculations
on the prescribed {-0.25, 0, +0.25} pixel grid. They are not native pulse
injections or a gain fitted to the target. Multiplicative isolated-source
flux cancels from a moment, but a blended scene or changing background need
not obey that invariance.

## Provenance and verification

The public source freeze is
`f42aa216b25779d55cd1fabd25545d3277abcfa5`, with the unchanged
[specification](../LS7P_SPEC.md), configuration, producer and independent
auditor. Before the present verification, **695 locally available tracked
files** were checked against the complete public freeze tree. This includes
the actual scripts and retained prerequisite data; no missing file is counted
as verified. The [file inventory](../results_ls7p_reconstruction/frozen_source_inventory.json)
records their Git blob identities and SHA-256 values.

The reconstruction input archive contains 50 files, 65,731,505 bytes, including
the original extracted pixel and sparse-index bytes in lossless gzip form.
Its saved acquisition ledger records **140,176,892 science bytes**: 120 pixel
ranges containing 48,120 rows, plus twelve sparse CR indices containing
688,661 records. Previously completed metadata account for another 421,232
bytes. These numbers describe that reconstruction acquisition, not new
transfers by the present offline verification. No full-product FITS checksum
claim is made. The original acquisition console log was not recovered; the
range receipts, source identities and extracted bytes are retained.

A fresh execution of the frozen producer and the separate raw-FITS/scalar
auditor reproduces all 16 retained result files byte-for-byte. The auditor
performs **1,496,872 numerical comparisons**, with exact discrete counts and
the tolerances fixed in LS7P. All seven analytical known-answer tests pass.
Only the output directory is rebound by the verification driver; source,
inputs, scientific code, parameters and the retained reconstruction remain
unchanged. This fresh audit is not added to the earlier count as extra science.
Python 3.12.14 and the four pinned package versions are recorded alongside
the new verification timestamps and console logs.

[Independent audit](audit.json), [full row/quality summaries](summary.json),
[PRF cases](calibration_response.json),
[reproduction and retained-input accounting](../results_ls7p_reconstruction/README.md).

## Decision and continuation

**Measurement reconstruction: verified with six recorded rounding-bound
exceptions. Target-excluded motion contract: not established.** A usable
motion input still requires justified pixel quality, scene/displacement
response, error covariance and missing-data handling. None is supplied by
discarding the six exceptions or simply adopting the diagonal uncertainties.
The closed LS7J/LS7N failures and LS7O availability decision remain unchanged.

The subsequent optical-product assessment has already been carried out in
[LS7Q](../LS7Q_OPTICAL_METADATA.md) and [LS7R](../LS7R_CHEOPS_INPUT.md), followed
by the CHEOPS calibration work through [LS7V](../LS7V_CALIBRATION_RECONCILIATION.md).
Reuse those completed assessments. The current CHEOPS image study still
requires its documented physical inputs; this reconstruction supplies none
of those missing calibrations. Keep unused TESS sectors and M43 panels closed.
[Current continuation](../LS7V_CONTINUATION.md).
