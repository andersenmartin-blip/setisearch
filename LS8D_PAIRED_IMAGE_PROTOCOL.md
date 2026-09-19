# LS8D: paired CAL/COR images for all eight LS8B/LS8C representatives

Publish this protocol, the completed metadata joins, exact machine scope,
implementation, independent auditor and synthetic tests before opening image
bytes. This is a new bounded image diagnostic on previously selected events;
it is not an independent detector/false-alarm calibration.

## Frozen acquisition

Use exactly `config/ls8d_images.json`: three named visits, eight unchanged
contexts (241 frames per image product), and their exposure-matched CAL,
COR and SCI_COR_SmearingRow ranges. The metadata join requires a unique MJD
match within 1 ms, identical UTC strings and BJD agreement within 1 ms; paired
CE counters/integrity and integration keywords must agree. Index equality
alone is not a join. Only native headers and exposure tables precede this
freeze; all image and smearing arrays remain closed until publication.

Retain each full native 200x200 float64 frame. Total science transfer is
154,240,000 paired-image bytes and 385,600 smearing-row bytes. Require HTTP
206, exact Content-Range/length/disposition and the frozen ETag with If-Match.
Never fall back to whole-file access. Save lossless gzip ranges, raw and
compressed SHA-256, and HTTP receipts. Retry only the identical range after a
transport failure, at most three attempts; record failures. No widened rows,
pixels, aperture, visit, raw imagette or different product version.

## Fixed temporal and spatial quantities

Use the original 24 sideband rows, event rows and two-row guards. Guards are
retained for provenance but excluded from all fits and finite-data masks.
At each pixel, fit an unweighted straight line in seconds to the sidebands,
after subtracting that pixel's sideband median. Sum event residuals to obtain
E_CAL and E_COR; E_DELTA = E_COR - E_CAL. Use a single common mask requiring
finite CAL and COR in all sideband/event frames. Never impute missing pixels.
Calculate the smearing-row event residual with the same temporal operation.

For each context the target anchor is the mean **sideband** L2 centroid,
converted with the native X_WINOFF/Y_WINOFF. Carry both offset conventions:
C0=(centroid-offset), C1=C0-(1,1), with integer pixel centers. Neither is chosen
from the outcome. Use fixed radii 25 (aperture), 35 (outer exclusion), and
30<r<=40 (background annulus), as in LS7Y/Z. No event-fitted center or mask.
Record total/valid aperture pixels and common finite count. A closure decision
requires every geometric radius-25 pixel finite and contained in the image.

For each coordinate convention, report:

1. CAL, COR and DELTA aperture event sums on the identical common mask; signed
   DELTA/COR ratio, absolute ratio and the sign match to the original L2 event.
   Treat a COR sum as numerically zero if its magnitude is <=
   512*binary64_epsilon*max(1,sideband COR aperture absolute-sum mean).
2. Aperture fraction of full common-mask COR absolute L1, and full-frame
   column-constant projection energy fractions for COR and DELTA. The
   projection repeats each column's common-pixel mean. Also report its DELTA
   aperture contribution divided by the COR aperture excess.
3. Descriptive OLS E_DELTA = alpha + beta*E_SMEAR(x), fitted outside r=35
   on finite common pixels; save beta, intercept, rank, residual RMS and
   zero-referenced explained energy. Do not apply this fit as a correction.
4. Build separate CAL/COR brightness templates from their 24-sideband mean
   images, subtracting the median in the fixed 30<r<=40 annulus. Form central
   differences Dx,Dy. Within radius 25 and common pixels with valid neighbors,
   fit brightness [P,1], displacement [Dx,Dy,1] and combined [P,Dx,Dy,1]
   models to each product's event map. These spatial coefficients describe
   the event; template construction never uses event values. Normalize each
   design column by its Euclidean norm for solving; use SVD rcond=1e-12.
   Record rank, coefficients in original units, residual RMS, condition and
   explained fraction 1-SSE/sum(E²), with an unavailable fraction at zero energy.

Image headers' BUNIT labels are retained verbatim. No assumed gain, absolute
electron conversion, re-addition to L2 FLUX or raw-imagette calibration is used.
Comparisons measure the delivered paired products on their common native scale.

## Predeclared stopping / descriptive closure

Require complete radius-25 coverage, a nonzero COR denominator and its sign
matching the original L2 sign in **both** C0/C1. Otherwise stop with
UNRESOLVED_WITHIN_FIXED_SCOPE and a reason. Apply the same rules to both signs.

- CORRECTION_LINKED: in both conventions, either absolute DELTA/COR >=0.5
  or the absolute column-projected DELTA aperture contribution/COR >=0.5.
  This is the LS7Y descriptive coupling rule, extended symmetrically to the
  negative control. It establishes coupling to CAL→COR, not a unique cause.
- If that gate is false, SPATIALLY_STRUCTURED: in both conventions the
  full-rank COR displacement model explains >=0.80 of zero-referenced energy
  and exceeds the brightness model's explained fraction by >=0.20. These
  newly frozen stopping values are motivated by LS7Z and are descriptive,
  not calibrated classifier thresholds or proof of pointing as a cause.
- Otherwise UNRESOLVED_WITHIN_FIXED_SCOPE. No further rows or alternate model
  follows automatically. No event is promoted to a SETI candidate by these labels.

Every eligible map, fit and both coordinate outcomes must be reported, even
when the earlier correction gate is met. A missing/rank-deficient fit remains
explicitly unavailable; it does not justify model replacement or another cut.

## Verification and reporting

Before image access, synthetic tests must cover tiny signed residuals on a
large/sloped baseline, guards excluded from fitting, missing-pixel semantics,
pure brightness/displacement/correction fixtures, both signs, and disagreement
between coordinate conventions at the closure boundary.

The independent auditor decodes saved range bytes with big-endian struct,
uses long-double scalar normal-equation sums for temporal maps, and independently
rebuilds masks/anchors/projections/templates and fits with normalized normal
equations. Audit every available map pixel, mask and numerical summary, and
recompute closure labels. Native-unit agreement tolerance: rtol=2e-8,
atol=1e-6; dimensionless fit/gate diagnostics: rtol=2e-8, atol=1e-8. Exact
indices, availability, finite masks and labels must match. Preserve failures;
never alter tolerances or gates after seeing an outcome. Check exposure joins
independently with struct decoding and verify all saved range checksums.

Publish all retained range bytes, diagnostics, checksums, audit and readable
CAL/COR/DELTA maps together. Report the original LS8B audit FAIL unchanged,
the single-control limitation, and no new detector qualification or observing
coverage. Preserve the closed LS7X/Y/Z branches and unused TESS/M43 panels.
Raw-imagette NOT_READY and the unsent technical request remain separate.
