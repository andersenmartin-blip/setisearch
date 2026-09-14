# LS7P — fixed-reference pixel and centroid response examination

Specified 14 September 2026 after LS7O, before any new reference pixel values
or cosmic-ray amplitudes are inspected. This combines pixel acquisition,
archive reconstruction, quality attribution, conditional response calculation
and independent verification. It is development on the same closed contexts.

## Question and scope

Can the archived reference centroids be reconstructed from their documented
pixels, and what prevents interpreting them directly as image displacement?
Keep all seven stars, twelve products, sectors 29/32 and ten 401-cadence
contexts per sector from LS7O. There is no star ranking, cadence selection,
gain/sign/lag choice, target response fitting or new target correction here.
The LS7J/LS7N measured failures and LS7O availability rule remain closed.
Unused TESS sectors and M43 panels remain unopened.

Metadata were read first. All twelve FAST-TP headers and aperture masks match
the existing identities, mask bytes and time definitions. Each file has a
sparse cosmic-ray extension. Exact byte plans and ETags are recorded in
`results_ls7p_metadata/inventory.json`; checksums bind them in
`config/ls7p_pixels.json`.

## Bounded acquisition

Read 120 exact contiguous ranges: **48,120 selected pixel rows**, totaling
**131,912,960 bytes**. Read each sparse CR extension once as a cadence index:
**688,661 interleaved records / 8,263,932 bytes**. Outside the selected
contexts, interpret only the four-byte CADENCENO field. Coordinates and
amplitudes are decoded only for matching cadences. Full sparse-index response
bytes are preserved for independent selection verification; their unselected
payload is not evaluated. Selected CR records are also saved separately.

The exact science transfer allocation is **140,176,892 bytes**, plus the
already completed 421,232 metadata bytes, versus 3,719,056,320 bytes for the
full products. Require HTTP 206, exact Content-Range, unchanged ETag, exact
length and per-range SHA-256. Cache successful ranges for interrupted
transfers; replay must meet the same budget and receipts. Whole-product FITS
checksums cannot be verified from extracts and are not claimed.

Require exact TPF/LC CADENCENO, TIME and TIMECORR equality for all selected
rows. Report LC/TPF QUALITY differences rather than silently changing flags.
Original raw records are archived losslessly. Only the bit-8 moment pixels'
FLUX, FLUX_ERR and FLUX_BKG and the scoped CR corrections enter the
measurement. Other interleaved pixel fields remain unused.

## Documented product meanings

FLUX is calibrated and has background and detected cosmic rays removed;
FLUX_ERR supplies per-pixel uncertainties. Bit 8 of APERTURE identifies moment
pixels, distinct from bit 2's photometric aperture. MOM_CENTR1/2 are
flux-weighted column/row coordinates. CR records identify a cadence, detector
pixel and additive correction. QUALITY values 64, 512, 1024 and 4096 concern,
respectively, aperture cosmic rays, pre-cotrending outliers, collateral cosmic
rays and scattered-light exclusion. These definitions do not specify a joint
pixel covariance or guarantee uncontaminated astrometry.
[SPOC product specification, Rev F, Tables 8/10/13/15/32 and §4.3](https://archive.stsci.edu/files/live/sites/mast/files/home/missions-and-data/active-missions/tess/_documents/EXP-TESS-ARC-ICD-TM-0014-Rev-F.pdf).

For 20-second observations the ground pipeline removes detected cosmic rays
and preserves their corrections; the on-board removal used for longer
products does not apply. The actual twelve primary headers independently
record CRMITEN=false, CRBLKSZ=0 and CRSPOC=true.
[NASA TESS cosmic-ray primer](https://heasarc.gsfc.nasa.gov/docs/tess/TESS-CosmicRayPrimer.html).

## Explicit measurement and uncertainty assumptions

For fixed detector pixel coordinates x_i, flux f_i and positive error s_i,
compute S=sum(f_i) and C=sum(f_i*x_i)/S in float64. Retain negative flux;
apply no clipping, interpolation, background refit, outlier removal or mask
change. A row with nonfinite flux/error, any nonpositive error or nonpositive
S is unavailable. QUALITY never becomes an acceptance waiver: flagged rows
are examined and labeled, without adoption as motion inputs.

The following equations are our explicit calculation, not an assertion about
undocumented pipeline implementation:

* Pixel derivative G_i=(x_i-C)/S, including both coordinates.
* Conditional diagonal pixel-error covariance V=sum(s_i² G_i G_i^T).
  Its off-diagonal x/y term is retained. Compare sqrt(diag(V)) to the archived
  centroid errors as ratios, without declaring the diagonal model correct.
* For unknown pixel correlations with those same marginal errors, each axis
  has a worst-correlation bound sum(s_i*abs(G_i)). This is a conditional
  covariance bound, not a calibrated confidence interval or systematics bound.
* If u_i is half the larger adjacent binary32 spacing, the pre-export moment
  can differ by at most sum(u_i*abs(x_i-C))/(S-sum(u_i)), plus 2e-11 pixels
  for numerical accumulation. Count both-axis archive agreement under this
  bound. It tests the simple reconstruction hypothesis, not astrometric truth.
* Adding d_i changes the moment exactly by
  sum(d_i*(x_i-C))/(S+sum(d_i)). Accumulate duplicate signed CR records.
  Compare direct restored moments to this identity. Report displacement in
  pixels and divided by the **processed** diagonal error; uncertainty of the
  restored cosmic-ray amplitudes is unavailable, so this is not a significance.
* Restore FLUX_BKG separately to measure sensitivity to that archived
  subtraction. It is not a residual-background estimate or a proposed fix.
  Doubling all f_i must leave the centroid unchanged.

Report every reference and both sectors, with all rows, QUALITY=0, each
observed bit and each exact quality combination. Flag-bit groups overlap.
Record CR counts in the full stamp, moment mask and optimal aperture;
cross-tabulate aperture CR records against bit 64. Preserve full row outputs,
including unavailable measurements. No empirical quality threshold is tuned.

## Displacement and flux response comparison

Use only the already audited commissioning PRF bank, fixed reference WCS
positions and bit-8 masks. Keep both field-column conventions (0 and −44)
separate. The effective PRF already includes its commissioning blur; do not
apply a second jitter convolution or infer individual two-second motion.
[Mission PRF README](https://archive.stsci.edu/missions/tess/models/prf_fitsfiles/start_s0004/00README.txt).

For each of the 24 reference/convention pairs calculate the fixed-aperture
isolated-source centroid. Compute a central-difference 2×2 displacement
Jacobian with h=0.001 pixel, its singular values, condition and operator
distance from the identity. Compare nine prescribed source shifts on
{−0.25,0,+0.25}² against unit centroid response and the nominal local-Jacobian
inverse: **216 calibration cases**. These are model calculations, not new
native injections or a fitted gain correction. Record unsupported cases;
do not extend or renormalize the PRF to make them available.
The inherited PRF reader also rejects active grid nodes carrying nonzero
original MATLAB rowShift/columnShift annotations. Their interpretation has
not been established for these references. Preserve that exclusion, with an
explicit reason and all nine unavailable case slots; the raw scalar audit
checks the original annotations independently. Preflight exposed this
metadata condition before any reference pixel time series were read.

A pure multiplicative source change cancels from an isolated-source moment.
That identity does not protect a blended source or time-varying background.
The response is a cadence-level, fixed effective-PRF assumption. Existing
header timing establishes cadence centers and live time, not a unique
sub-exposure kernel or upstream target exclusion in mission calibration.

## Verification and decision

Before acquisition, verify seven analytic cases: signed moments/covariance,
scale and coordinate invariance, signed additions, a saturating covariance
bound, binary32 rounding, duplicate CR mapping and unavailable inputs. Run
the entire 216-case calibration computation and its independent raw-FITS /
SciPy reconstruction as a preflight; it uses no new reference time series.

The result audit independently decodes raw FITS cards and rows with struct,
filters the sparse index using cadence fields, uses scalar math.fsum moments
and reconstructs all row measurements and group summaries. Verify input
manifests and archive hashes. Compare floating reconstructions at 2e-10
absolute / 2e-8 relative, aggregate statistics at 2e-8, and discrete counts
exactly. These audit tolerances are distinct from the binary32 scientific
reconstruction bound.

Reproducing moments establishes a measurement convention only. A new
target-excluded motion estimator additionally needs a justified pixel-quality
treatment, scene/displacement response, error model and missing-data rule.
Neither finite errors nor disagreement confined to quality flags supplies
those by itself. Do not use this diagnostic to reopen LS7O or tune the closed
target corrections. If the integrated evidence does not establish that
motion contract, document the remaining obstacle and reassess documented
optical products/instruments for 30–100-second work in the same result
package. That assessment opens no new science data and schedules no work.
