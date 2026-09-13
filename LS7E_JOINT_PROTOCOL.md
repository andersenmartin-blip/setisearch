# LS7E: combined spatial development on closed sector 32

12 September 2026. This is a retrospective engineering comparison using the
already public LS7C sector 32 backgrounds. It is neither independent validation
nor a redefinition of LS7C. Preserve its original 1,460 decisions and LS7D's
noise accounting. No other TESS sector or M43 held-out panel is opened.

## Fixed model and comparison

Use the 18 optimal-aperture pixels. The earlier stellar injection and fit
profiles were defined within that aperture; unrelated pixels elsewhere in the
121-pixel stamp no longer enter a global residual veto. This sacrifices tests
of external image morphology and does not establish an astrophysical origin.

For each of the ten original 401-cadence backgrounds, collect actual
`mean(event) - median(two sidebands)` vectors at starts 100, 150, 200, 250 and
300, for each original width 2, 3 and 5. Each sideband is the original 55 samples
with a five-sample guard. Normalize by that background's original run-level
aperture MAD. No samples or outliers are clipped or selected using outcomes.

When assessing one background, estimate its covariance from the **other nine**
backgrounds: 45 vectors for the matching duration. Use ordinary centered sample
covariance with ddof=1, 5% shrinkage toward its own diagonal, and a diagonal
floor of 1e-10 times its mean variance. Scale to the assessment background's
original run-level aperture MAD. The vectors and sidebands overlap; neither
45 vectors nor the ten folds are independent validation observations. This
estimates the event statistic directly, without a white-noise division by width
or a universal 4.66 noise rescaling. Report every covariance and training ID.

Compare three fixed methods: full covariance plus one optional sparse pixel;
diagonal covariance with the same sparse option; and full covariance without
the sparse option. Each hypothesis has a free uniform background and a
nonnegative amplitude. The sparse option enumerates one unconstrained aperture
pixel coefficient, with a fixed objective penalty of 9, equally available to
stellar and nuisance fits. Stellar templates retain the nine original shifts.
Nuisances include uniform, every aperture single pixel, every overlapping 2x2
block in the stamp, and the original signed 0.2-pixel pointing templates.

Carry the original temporal screening threshold of 8, source score of 5,
reduced residual cut of 2, and nuisance objective margin of 9. These uncalibrated
engineering gates and changed residual degrees of freedom are an explicit new
prototype, not a probability model. No parameter is optimized after this run.

## Complete joint challenge

1. Reconstruct all **1,460** original LS7C digital cases using their recorded
   amplitudes, patterns and phases. Every temporal score, selected window,
   polarity and confounding decision must reproduce; preserve the original
   spatial outcomes alongside the new comparison. No original bisection is rerun.
2. Add **1,040** sparse stress cases: the 120 matched nominal stellar cases,
   120 matched compact 2x2 cases and 20 null cases each receive one extra pixel,
   inside or outside the aperture, positive or negative. The inside pixel is
   the faintest reference-profile aperture pixel; the exterior pixel is (0,0).
   The added level is eight times the inside pixel's predicted event-noise
   standard deviation, constant over the parent's recorded selected window.
   The identical magnitude is used outside. Repeat temporal selection, retain
   altered screening outcomes, and log exact pixels, levels and parent IDs.
3. Add **360** strength-matched extended controls: 3x3, 1x5 and 5x1 patterns,
   placed at the maximal reference-profile overlap with row-major tie breaking.
   They are absent from the fitted nuisance bank. Use both original single-pulse
   shapes and phases, and temporal strengths 8.5, 12 and 20 on every background.
4. Add **320** physically bounded pointing controls: actual reference-image
   displacements of 0.05 or 0.2 pixel in each signed axis, multiplier exactly
   one, both pulse shapes and phases on every background. Report how many cross
   the temporal threshold; subthreshold cases do not demonstrate spatial rejection.

Total: **3,180 paired trials**, three prototype methods per trial. These reuse
ten existing backgrounds and add no observing coverage. Digital injections
occur after mission processing, contain no extra Poisson noise, and are not a
physical laser completeness calculation. Sparse stress amplitudes are referenced
to the fixed full-covariance model for every comparison, not retuned per method.

## Endpoint and preservation

Report recovery and nuisance acceptance by strength, type and background,
including all below-threshold and confounded cases. For continuation, inspect
the old joint requirements (90% nominal, 80% shifted signal recovery; at most
5% nuisance acceptance per kind/strength) together with the new residual and
extended controls. No passing development cell can qualify the detector.
Do not open an independent sector because this comparison fails. Use its paired
losses and ablations to decide whether this model family warrants a separately
frozen transfer study on another already closed sector.

Freeze code, configuration and this protocol locally before extracting these
new features. Save full trial vectors, model matrices, source hashes, environment,
analytical tests, a numerical audit, and a readable report. The public GitHub
publication time is recorded separately; no public preregistration is implied.

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src python -m unittest discover -s tests -p 'test_ls7e_joint.py' -v
sha256sum -c LS7E_FREEZE.sha256
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src python scripts/ls7e_joint_development.py --cache /path/to/sector32
```
