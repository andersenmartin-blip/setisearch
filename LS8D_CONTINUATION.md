# Continue after LS8D

The bounded paired CAL/COR image study is complete for all eight fixed LS8B/LS8C
representatives. Preserve the exact acquired ranges, audited event maps and
predeclared classifications. Do not widen these event branches.

## Completed result

The study retrieved exactly **154,240,000 paired CAL/COR image bytes** plus
**385,600 SCI_COR_SmearingRow bytes** from the three fixed visits TG000302,
TG000303 and TG000304. All 24 range requests were constrained by the frozen
offset/count, HTTP 206, exact Content-Range, ETag and Content-Disposition.

All **eight** representatives are **CORRECTION_LINKED** in both predeclared
coordinate conventions. The seven positive events retain positive COR aperture
sums, but CAL→COR contributes a large negative event sum; absolute DELTA/COR is
1.331–2.431. The one negative control is also correction-linked, with absolute
DELTA/COR 0.857–0.884: its already negative CAL event becomes substantially
more negative in COR.

The DELTA map's column-constant energy fraction spans 35.66–94.56% across the
seven positives but is only 0.49% in the negative control. Therefore the fixed
result establishes strong coupling to the CAL→COR processing chain without
establishing one common column-smearing mechanism or a unique DRP component.

The COR displacement template explains 35.79–74.42% of event-map energy across
the positive events and about 21.64% for the negative control. None reaches the
separately frozen 80% SPATIALLY_STRUCTURED gate. The direct DELTA-versus-
smearing-row regression is rank-deficient in all eight contexts and remains
unavailable rather than being repaired after inspection.

Seven synthetic tests passed before image access. The independent audit passes
**756,296 numerical comparisons** and **1,284,709 exact checks**, with zero
disagreements. Maximum CAL/COR map difference is 5.82e-11 native ADU and maximum
DELTA difference is 1.16e-10. The original LS8B numerical audit remains FAIL;
its separately documented stable-arithmetic repair is unchanged.

[Full report and event-map figures](results_ls8d_images/REPORT.md),
[machine summary](results_ls8d_images/summary.json),
[independent audit](results_ls8d_images/audit.json).

## Interpretation boundary

CORRECTION_LINKED means that the delivered CAL→COR processing materially changes
the event amplitude under the fixed descriptive gate. It does **not** identify
which correction caused the change and does not prove that the underlying source
variability is instrumental. It also does not establish artificial or
astrophysical origin, detector qualification, a false-alarm rate or new
qualified observing coverage.

All eight branches are closed under the LS8D stopping rule. Do not open more
rows, change the aperture, replace a representative, fit a new threshold or add
another 55 Cnc visit to obtain a different outcome.

The raw-imagette/native-calibration route is separate and remains **NOT_READY**:
the exact gcoadd/gain/reference contract is still incomplete and the prepared
technical clarification request remains unsent. LS8D used mission-delivered
CAL/COR products and does not solve that raw-input contract.

## Next project action

Move away from these closed 55 Cnc event branches. The next optical search must
be a separately frozen **independent dataset/product selection**, chosen without
using prospective event outcomes. Begin with metadata only: define target/product
eligibility, cadence, visit-count, public-delivery and control requirements
before reading new light-curve values or image pixels.

Prefer a product whose delivered calibration is already operationally usable,
so that a future excursion can be followed with a predeclared image diagnostic
without depending on the unresolved raw-imagette contract. Preserve the
positive/negative symmetry learned from LS8A–LS8D and do not interpret screen
scores as Gaussian significance.

Unused TESS sectors and M43 held-out panels remain closed. The earlier LS7X/Y/Z
branches remain closed. Publication continues under the standing project
authorization.

[Protocol](LS8D_PAIRED_IMAGE_PROTOCOL.md),
[metadata freeze](LS8D_METADATA_FREEZE.md).
