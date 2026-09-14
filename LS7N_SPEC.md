# LS7N — fixed cadence-level calibrated response comparison

Specified 14 September 2026 after LS7M and before native response evaluation.
This is development on the same twenty closed contexts, not unused-data
qualification. Preserve LS7J and every earlier result without modification.

## Physical scope and evidence

The [mission SDPDD Rev F, tables 8 and 13](https://archive.stsci.edu/files/live/sites/mast/files/home/missions-and-data/active-missions/tess/_documents/EXP-TESS-ARC-ICD-TM-0014-Rev-F.pdf)
defines POS_CORR1/2 as local column/row motion in pixels, including pointing,
DVA and thermal contributions; FLUX is processed, background-subtracted pixel
flux. The [SPOC design paper](https://heasarc.gsfc.nasa.gov/docs/tess/docs/jenkinsSPIE2016-copyright.pdf)
(Jenkins et al. 2016, SPIE 99133E, doi:10.1117/12.2233418, sections 3.1–3.3)
describes ensemble astrometry and commissioning PRFs. These inspected sources
do not specify the complete quaternion-to-pixel mapping or the actual fast
POS_CORR exposure kernel and target exclusion for these releases.

Use LS7M's explicitly permitted cadence-level alternative. Treat each saved
POS_CORR pair as an effective local displacement for one 20-second datum.
At each window, subtract its protected sideband median and add the resulting
x/y displacement to the fixed WCS nominal source position. Positive column
motion increases source x. This unit, zero-lag convention is declared; neither
its sign, gain nor reference astrometry is fitted to native outcomes.

Use the commissioning PRF as an effective, already blurred pixel response,
with fixed shape during local translation. Do not add quaternion jitter or
another exposure convolution. This avoids asserting an instantaneous deblurred
PSF, but still approximates a changed exposure by translating an inherited
profile. Timing, focus, color, deformation and processed-pixel residuals remain
physical limitations. Local DVA/thermal effects are represented only through
the supplied displacement, not assumed to be rigid attitude rotations.

Both LS7M field-column conventions, 0 and -44, remain separate outputs. No
variant is selected on results. Fix a common supported domain: all eleven rows
and columns 1–10 of each stamp (110 pixels). The original 21/18-pixel apertures
are unchanged. Require source offsets, including protection/injection shifts,
to stay within +/-0.5 pixel per axis. This domain is fixed from calibration
geometry and previously inspected motion inputs, not native residuals.

## One fixed model and ablations

Reuse the exact 420 LS7I/LS7J native windows, original sidebands
[start-60,start-5) and [stop+5,stop+60), scalar aperture noise, static predictions
and covariance metrics. No event selection or covariance recalibration.
For each window and coordinate convention:

1. Translate the local PRF at each selected cadence. Form the componentwise
   median sideband PRF and mean event PRF, without normalizing their sums.
2. Fit the sideband median science image on the 110 supported pixels to that
   median PRF plus a constant/x/y plane. Use weighted least squares; the
   per-pixel scale is MAD of within-sideband adjacent differences divided by
   sqrt(2), floored at 1e-6 times the median positive variance. Require rank
   four, condition <=1e8 and positive source amplitude. This is a static source
   amplitude fit from outside-event pixels, not a motion-gain fit.
3. The motion prediction is that amplitude times (mean event PRF minus median
   sideband PRF). Transport calibration uncertainty entries into an envelope:
   amplitude times (mean event entries plus maximum sideband entries). This
   does not include amplitude-estimation error or unknown covariance and is
   not a confidence interval.
4. Estimate a simultaneous residual plane from supported outside-aperture
   pixels after subtracting motion. Protect the span of 18 event-averaged PRF
   profiles: both column conventions at all x/y shifts in {-0.25,0,0.25}.
   Whiten by the same sideband pixel scales, project out that source span, and
   use its projected plane pseudoinverse. Relative SVD cutoff 1e-10; require
   plane rank three and condition <=1e8. Templates use event motion metadata
   but no event photon values. Add the predicted plane to the motion term.

Primary method: combined. Ablations: static, motion only and protected plane
only. Amplitude/reference, signs, gains, lags, shifts, noise floors, rank and
covariance rules are fixed before evaluation. Failure means unavailable
prediction, not a fallback selected on outcome.

## Endpoints and signal protection

Evaluate 420 paired windows at both coordinate conventions: **840 model/window
rows**, still only twenty backgrounds. Use the unchanged common covariance
metric with its uniform-flux component projected out. For each sector and
coordinate convention, combined response must have all 210 windows available,
total energy no larger than static, at least six of ten background aggregates
improved, and no background energy more than doubled. Both conventions and
both sectors must pass; report every ablation with no replacement selection.

For each model/window row test five full-window unit pulses: nominal source
and the four x/y shifts (+/-0.2,+/-0.2). Test the nominal PRF and two separate
uncertainty-entry stresses max(P-U,0), P+U: **12,600 response rows**. The pulse
is constant during the event window; its spatial response averages the supplied
cadence displacements. Relative aperture distortion must be <=1% for nominal
calibration and <=5% for both entry stresses. Record gain as well as distortion.
The stressed images are sensitivity cases, not probabilistic draws. Test
addition by differencing corrected native and corrected injected images while
holding sidebands and motion metadata fixed. Source amplitude/noise estimation
must be unchanged by additions confined to the protected event.

This is downstream protection only. Unknown guide membership and motion-
estimator target weights leave upstream pulse coupling unbounded. No detector
adoption follows even from a descriptive pass. Do not rerun unchanged historical
digital recipes or treat these calibration profiles as extra observations.

## Verification and decision

Freeze protocol, source, config and input hashes publicly before execution.
Known answers cover static flux-plus-plane recovery, protected plane recovery,
source annihilation, downstream additions and event exclusion. Reuse LS7M's
unchanged interpolation verification. An independent script imports no new
producer/operator and uses original FITS bytes, SciPy interpolation, a separate
SVD driver and normal equations for source flux. Rebuild all 840 rows and all
12,600 pulse responses; require native quantities within rtol 1e-8 / atol 1e-7
and pulse metrics within absolute 1e-8. Recompute all aggregate gates and input
identities. Numerical disagreement stops publication as a passed audit; a
code fix requires a documented new freeze and fixed-panel rerun.

If the joint requirement fails, close this exact cadence-level response family
without sign/gain/lag/profile retuning. Use the component and uncertainty
accounting to decide whether an independently justified observable/model or
different data product is needed. Unused TESS sectors and M43 panels remain
closed. Standing publication authorization applies.
