# LS7M calibrated PRF and finite-exposure operator

Specified 14 September 2026 after the bounded original-model inspection and
synthetic known-answer tests, before evaluating the target calibration cases.
This is a numerical forward-model benchmark. It does not read native pixel
values, compare native residuals, estimate pointing from quaternions, or evaluate
a detector. The previous LS7J outcome and unused panels remain closed.

## Calibration and coordinate contract

Use all fifty sealed LS7K camera-4 CCD-3/4 FITS image pairs and the coordinate
vectors recovered under LS7M_PRF_ACQUISITION.md. Verify their original SHA-256
identities. The two original MATLAB files reproduce every values and
uncertainties array exactly, without a transpose. Both relative axes contain
117 samples, from -58/9 to 58/9 pixels, with zero at array index 58.

Array order is row, column. A source at s contributes the pixel-response value
P(pixel_x - s_x, pixel_y - s_y). The PRF already describes pixel response; do
not apply a second pixel-box convolution. Use bilinear subpixel interpolation
and bilinear interpolation between the four surrounding CCD field nodes.
The local field kernel is fixed at the nominal source position during a
trajectory. This is a local translation model, not a changing optical solution.
Do not renormalize a phase image or the finite science stamp.

The mission README states a 44-column offset, but the exporter copies the
MATLAB references directly into RAWX/RAWY. The recovered column grid is
[45,557,1069,1580,2092]; the row grid is [1,513,1025,1536,2048]. These facts do
not independently settle the absolute origin. Require an explicit field-column
offset and report **both 0 and -44** relative to the saved science RAWX. This
changes field weights only, not pixel-minus-source offsets. Neither variant
is selected by a native fit; this pair is a sensitivity study, not proof that
all possible coordinate errors have been bounded.

Three original nodes have nonzero rowShift annotations. Their semantics are
not established by the FITS export. Reject any field interpolation with a
positive weight on such a node. None contributes to either target at either
declared offset. No extrapolation or zero-filled tails: a pixel outside the
tabulated relative domain during positive pulse/live overlap is flagged
uncovered and its integrated value is NaN. A pulse that is off contributes zero.

Propagate supplied uncertainty entries with the same nonnegative spatial and
temporal weights. This is an uncertainty-entry envelope, not an independent
pixel-noise estimate, confidence interval, derivative-error calibration or
sector-specific response uncertainty. Do not divide it by sqrt(sample count).

## Fixed numerical panel

Use the nominal target and 11-by-11 geometry already in LS7K inventory for
sectors 29 and 32; no native pixel array is needed. Evaluate the Cartesian
product of two positions, two column offsets, three integration-start phases,
four source trajectories and three pulse windows: **144 cases**.

Ten two-second frames occupy [-10,10] seconds. Each integrates for 1.98 seconds.
Integration starts 0, 0.01 or 0.02 seconds after each frame boundary. The exact
mission phase is unknown. Use these explicit alternatives without identifying
quaternion timestamps with integration centers. The trajectory knots are
[-10,0,10] seconds and source displacements in pixels are:

| Path | At -10 s | At 0 s | At 10 s |
|---|---|---|---|
| stationary | (0,0) | (0,0) | (0,0) |
| x_sweep | (-0.2,0) | (0,0) | (0.2,0) |
| diagonal | (-0.2,-0.15) | (0,0) | (0.2,0.15) |
| kink | (-0.1,0.1) | (0.2,-0.15) | (-0.1,0.1) |

Pulse windows are full live time, [-0.5,0.5] seconds, and [-0.015,0.015]
seconds. Pulse amplitude is one while on. Normalize the integrated response
by the **19.8 seconds of total live time**, including pulse-off intervals.
These synthetic paths and pulses are not measured pointing or candidate events.

Split integration at live/pulse endpoints, trajectory knots and all spatial
interpolation-cell crossings. On each remaining straight segment a bilinear
surface is quadratic in time: two-point Gauss quadrature is exact up to
floating arithmetic. Retain per-pixel flux, uncertainty entries and coverage,
field weights, piece counts, live/pulse overlap and summed *covered* flux.
The latter is a partial-footprint quantity if any stamp pixels are unsupported.
Report coordinate and readout sensitivity without a scientific pass/fail cut.

## Verification and decision boundary

Before the target panel, synthetic tests check axes/sign, integer translation,
amplitude scaling, edge coverage, invalid inputs, constant exposure, readout
rejection, a 30 ms pulse and an analytic quadratic path integral. Reconstruct
all 4,050 interleaved phase images through the operator and compare both image
arrays with their sealed entries (absolute tolerance 2e-12).

An independent audit uses original MATLAB arrays, SciPy RegularGridInterpolator
for field/subpixel interpolation, and Simpson integration with separately
constructed per-pixel cell crossings. It does not import the production
operator. Require identical coverage, all 144 case identities, and absolute
flux/uncertainty differences <=2e-12. Check the original-to-FITS identity and
all inherited LS7K/LS7L manifests. Save the numerical discrepancies, not just
assertions. A failure stops the benchmark and is reported; an implementation
fix requires a documented new source freeze before rerunning the fixed panel.

Passing establishes the arithmetic of this explicit response family. Native
prediction improvement remains untested. A later native comparison must freeze
the mapping from observables to detector motion, timing assumptions, pulse
protection, nuisance handling, uncertainty and endpoints before scoring. Unknown
guide membership/target exclusion, DVA and thermal deformation cannot be made
equivalent to rigid pointing by this operator. No gain, sign, lag, profile or
threshold retry of LS7J is authorized by a numerical pass.

The original MATLAB bytes are retained as a reproducible local cache, following
LS7L's engineering-source policy. The repository retains exact original URLs,
sizes, hashes, validators and coordinate/annotation metadata; the existing
fifty FITS image pairs contain all image values used by the operator. The audit
restores only the two frozen MATLAB sources if their cache is absent.
