# LS7S: calibration contract and electronic metadata audit

15 September 2026. Continue the retained LS7R visit
`CH_PR300024_TG000301_V0300`, OBSID 1015522, from science commit
`a6fcb5aaf36b88efb0ee5c8ad409ad82df16a138`.

This is an input-development assessment. The reference query and initial
electronic-field previews preceded this written scope. It is **not** a
preregistered independent experiment, a detector comparison, or a native
pulse-recovery measurement. The science arrays remain unopened.

## Combined work and endpoint

Resolve the fifteen exact reference identities from the saved processing
log. Retain the live archive rows, missing identities, validity metadata and
actual delivery outcomes. Check the contents of any acquired reference,
including its exact version, geometry/schema, units and checksums. Do not
substitute PIPE's small `nonlin.txt` for the recorded mission LUT.

Read only the following additional columns in LS7R's saved metadata:
`GAIN_0`, `BIAS_0`, `BIAS`, `RON`, `CCD_TIMING_SCRIPT`, `PIX_DATA_OFFSET`,
`HK_SOURCE`, and the five `CE_`/`HK_` FEE voltage and CCD-temperature fields.
Reuse timestamps and CE counters for joins. `PHOTOMETRY_1/2/3`, image bodies,
light curves, centroids and source-selection statistics remain excluded.

Compare the selected raw table fields through Astropy and a scalar FITS
decoder. Keep missing values missing. Do not replace NaN gain or bias with
zero, one or a visit median. Report the distinct imagette/subarray STACKING
labels without assuming their reduction operations are equivalent.

The exact gain reference is also distributed in the upstream PIPE package.
Its official PyPI wheel is a separate, bounded HTTPS source: verify the wheel
digest and the selected file's Git blob identity. Extract data and licence
only; do not install or execute the package, deserialize its PSF pickle, or
use it to work around the blocked mission-archive download. The latter is
left blocked. The package does not supply the missing mission calibration
bundle. Cap this package transfer at 2,000,000 bytes.

If the gain reference is valid, compare two explicitly labelled algebraic
interpretations of its temperature offset on the available metadata:
temperature minus the signed reference offset and the literal temperature-
plus-offset expression in the pinned PIPE reader. Check both with a scalar
polynomial evaluator. The latter comparison substitutes degree-C metadata
for PIPE's differently named HK input; it is **not** an actual PIPE run or
proof that PIPE/DRP calibrates this visit incorrectly. Neither convention
is adopted as a physical calibration without the complete input mapping.

## Decision and next integrated native experiment

Return `NOT_READY` if exact required reference contents, time validity or
the raw-to-calibrated mapping remains unresolved. Do not freeze numerical
native-recovery thresholds on an incomplete physical model or acquire
science pixels just to see whether it works. A passed arithmetic audit
does not override an incomplete calibration contract.

The ensuing single native protocol must cover target-protected PSF/background
training, calibration and uncertainty, actual exposure joins, 30/60/100 s
pulses before correction, displaced/distorted PSFs, compact/hot/cosmic pixels,
stray light, smear, saturation, gaps, and native residual prediction. Fix
numerical signal/control/native endpoints, unavailable-window accounting,
the transfer bound and the failure branch together before pixel evaluation.
Keep the same visit as development; independent qualification remains separate.

Publish the integrated input result, code, small reference, provenance,
audit and concrete continuation under the standing project authorization.
Do not open unused TESS/M43 panels, promote a candidate, contact archive
staff, or count additional observing coverage. LS7P reconciliation remains
separate.
