# LS7O — six-reference affine centroid response on the closed TESS fields

Specified 14 September 2026 after LS7N. This is a separately frozen development
experiment on the same twenty contexts. LS7J and LS7N remain closed failures.
The new observable is the measured moment centroid of **other stars**. There
is no adjustment of either earlier response to its completed target scores.

## Metadata selection and acquisition boundary

Use the official [sector 29](https://tess.mit.edu/public/target_lists/20s/all_targets_20s_S029_v1.txt)
and [sector 32](https://tess.mit.edu/public/target_lists/20s/all_targets_20s_S032_v1.txt)
20-second target lists, each containing 1,000 entries, and corresponding
MAST observation/product metadata. Target TIC 307210830 has RA
124.531756290083 degrees, Dec -68.3129998725044 degrees in the archived header.
For each sector require the same camera and CCD as the science target,
Tmag in [8,12], angular separation in [0.25,3] degrees, and a distinct TIC.
Select the six nearest, breaking ties by TIC. These are practical magnitude
and locality restrictions, not claims of saturation or crowding qualification.
Do not change membership using centroids, variability, fit residuals or target
response scores. A missing or invalid reference is not replaced.

Headers and aperture masks are metadata in this assessment. Before requesting
any light-curve table rows, establish product identity, row layout, 20-second
sampling, detector coordinates, moment-centroid masks, target exclusion and
the target's containment in the six-reference convex hull. Save the complete
ranked eligible list and MAST product records, including the existence and
sizes of corresponding pixel products. Pixel time series are not needed for
this particular centroid experiment and are not acquired.

The [mission SDPDD Rev F, tables 13 and 15](https://archive.stsci.edu/files/live/sites/mast/files/home/missions-and-data/active-missions/tess/_documents/EXP-TESS-ARC-ICD-TM-0014-Rev-F.pdf)
defines MOM_CENTR1/2 as flux-weighted column/row centroids, supplies their
one-sigma error fields, and identifies centroid-contributing pixels with
aperture bit value 8. TIME is barycentric; TIMECORR supplies its correction.
These definitions justify the column interpretation and footprint check.
They do **not** establish a unit centroid-to-source displacement response,
the covariance of the errors, or complete upstream calibration independence.

Pin all twelve light-curve identities, full-product lengths, ETags and exact
row byte ranges in config/ls7o_reference.json. Request the same ten 401-row
indices as the original target per sector, **4,010 rows/reference and 48,120
reference rows total**. Each table row is 100 bytes, so the time-series download
limit is exactly **4,812,000 bytes**, with no whole-file fallback. Require
HTTP 206, exact Content-Range, unchanged ETag and byte count. Preserve the raw
selected bytes compressed with SHA-256 plus the request ledger. This cannot
verify a whole-product FITS checksum; do not claim that it does.

Join by exact CADENCENO, not by nearest barycentric timestamp. Require all
selected TIME-TIMECORR spacecraft timestamps to match the original within
0.001 second, without interpolation. A mismatch stops acquisition as an
input-contract failure. No other sector or target context is searched.

## One reference estimator and its error description

For each of the existing 420 native windows use its original 110 protected
sideband rows and its 2, 3 or 5 event rows. On all these rows require all six
references to have QUALITY=0, finite moment centroids and finite positive
moment-centroid errors. No clipping, substitution, smoothing or lag scan.

The fixed six-by-three spatial design has rows
`[1,(reference_column-target_column)/1024,(reference_row-target_row)/1024]`,
using nominal WCS detector positions from metadata. At each window subtract
each reference's componentwise sideband median centroid. For each axis, set
its six weights from the inverse sideband median quoted errors. Solve the
weighted affine field independently at every selected cadence. Its intercept
is the inferred displacement at the science target. Fit rank must be three,
relative singular cutoff 1e-10, condition at most 1e8. All inferred selected
displacements must lie within +/-0.25 pixel per axis. A failure produces an
unavailable prediction and failed joint requirement, not a revised estimator.

The affine field permits linear spatial variation across the CCD. Its input
centroids and weights contain no science-target photon values, target
POS_CORR, target centroid or target-response outcomes. The sideband-only
reference centers and weights are unchanged by event-only reference changes.
The event reference centroids themselves are deliberately observable inputs.
No motion gain, sign, delay, center offset or spatial coefficients are fitted
against the science target. Both reference selection and design are frozen.

Interpret the measured centroid changes provisionally as effective source
displacements with positive unit gain and zero lag. Moment centroids can have
aperture truncation, crowding, color, focus and brightness-dependent responses.
This is an explicit physical approximation to be tested, not a newly verified
centroid calibration. Twenty-second integrated measurements do not recover
unmeasured subcadence jitter. The known commissioning PRF remains an effective
already blurred response; add no new exposure convolution.

Report each cadence's conditional formal target-position error by propagating
the six quoted variances through the fixed affine intercept weights. This
assumes independent reference errors and holds estimated sideband centers and
weights fixed. It omits center-estimation uncertainty, temporal/cross-star
covariance, centroid response error and target PRF error; it is **not** a
calibrated confidence interval. Also report the six-star affine residual sum
of squared quoted-error units, divided by three residual dimensions per axis,
averaged over selected rows. This is an error-consistency diagnostic, without
a chi-square probability claim or outcome-based reweighting.

## Integrated native comparison and signal protection

Feed this new displacement into the unchanged LS7N source-amplitude/PRF/plane
response, at both previously declared field-column origins 0 and -44. Keep
the nominal science-target position, static predictions, covariance metrics,
110-pixel support, 21/18-pixel apertures, sidebands, source fit, noise floor,
18 protected source profiles, ranks and thresholds unchanged. The exact
arithmetic is specified in LS7N_SPEC.md and reused from its verified operator.
Its input is replaced; its completed result is not altered.

Primary: reference motion plus protected plane. Report static, motion-only
and plane-only ablations without adopting a fallback. For every sector/origin
cell require all 210 windows available, total residual energy no greater than
static, at least six of ten background aggregates improved, and no background
energy more than doubled. Require all four cells jointly. There are **840
paired response rows**, not 840 independent observations.

For every paired row rerun the five fixed source positions and three fixed
PRF/uncertainty-entry pulse profiles from LS7N: **12,600 downstream pulse
responses**, limits 1% nominal and 5% entry stresses. Unavailable rows count
as failures. Preserve no-gain/no-lag/no-profile-selection rules. Existing
historical detector recipes need not be rerun because this is a response
comparison and does not adopt a detector.

The disjoint bit-8 footprints and estimator interface exclude science-target
pixels from the final reference-centroid combination. They do not prove
absence of every shared mission-calibration or optical cross-talk pathway.
Do not call downstream digital tests a complete astrophysical injection or
claim fully bounded upstream pulse coupling.

## Freeze, verification and decision

Publish this protocol, exact metadata/input config, acquisition/evaluation
code, numerical audit and meaningful known-answer tests **before acquiring
reference table rows or evaluating the response**. Known answers cover affine
translation/rotation/scale recovery, formal covariance propagation, protected
weight/center fitting, exclusion of unused rows and invalid-reference failure.
Reuse the verified, unchanged PRF and plane arithmetic.

Audit every downloaded row from raw bytes with an independent struct parser,
exact cadence/time/centroid/error/quality joins, metadata selection and mask
geometry checks. Rebuild affine fits with normal equations instead of the
producer pseudoinverse. Reuse LS7N's independent raw-FITS/SciPy/QR response
reconstruction, adapted only for the newly audited displacement and failure
accounting. Compare native quantities at rtol 1e-8 / atol 1e-7 and pulse metrics
at atol 1e-8. Recompute all aggregate gates and preserve historical hashes.

If inputs are unavailable, record that exact limitation. If the integrated
requirement fails, close this fixed six-reference/unit-centroid-response
family without dropping stars or tuning its gain, lag, profile, weights or
threshold. Use its error accounting to reassess the input/product or response
contract. A pass would justify further development, not detector adoption or
opening unused sectors. Standing publication authorization continues.
