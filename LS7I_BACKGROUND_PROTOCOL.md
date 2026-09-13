# LS7I: protected background prediction on two closed TESS sectors

Prospective model specification, 13 September 2026. This freeze is distinct
from the completed LS7I input-restoration freeze. Publish this source boundary
before computing any new closed-sector feature, regression or fit outcome.

## Question and scope

Can observable cadences surrounding a short event predict enough of the
spatial background fluctuation to satisfy the joint signal/control requirements
on **both** already closed sectors 29 and 32 of L 98-59 / TIC 307210830?

LS7H's exact native-background subtraction used injection truth. It showed a
cause of confusion, not a usable correction. Here one fixed ridge predictor
uses only observable outside-event pixels. A paired static-mean ablation
measures the value of its temporal features. There is no parameter, template
or threshold search. An unfavorable result completes this planned route.

The twenty 401-cadence contexts retain their original sector-specific
21/18-pixel apertures. All **6,720 historical recipes** are preserved in their
original order and cohorts. A separately declared **360-case sector-32 shape
supplement** makes the core shape coverage comparable. Total: **7,080 digital
cases**, reusing twenty backgrounds. This adds no observing coverage.

## Observable features and protected response

For the selected local cadence interval `[l:h)`, retain the existing 55-sample
left `[l-60:l-5)` and 55-sample right `[h+5:h+60)` sidebands. The full-stamp
reference is their pixelwise median. The event and five-cadence guards on each
side, `[l-5:h+5)`, cannot enter reference, scale, features or prediction.
Five cadences correspond to approximately 100 seconds on each side.

The local scale sigma is the original MAD-of-first-differences estimator on
the *observable aperture flux* in these bands: take 54 differences within
each band, concatenate the 108 differences, then use
`1.482602218505602 * median(abs(d-median(d))) / sqrt(2)`.
Never difference across the missing interval. Reject invalid/zero scales;
do not substitute a label-dependent or hidden-native estimate.

For p aperture pixels, features x have length 2p. Concatenate the pixelwise
means in `[l-15:l-5)` and `[h+5:h+15)`, subtract the corresponding reference
pixels, and divide by sigma. These are ten observable cadences on each side,
separated from the event by the same five-cadence guard. The unsigned response
y is `(event_mean-reference)/sigma`, of length p. Keep y separate from x.

Template profiles also use the observable long-sideband reference. A final
candidate's unsigned background prediction is subtracted before applying its
brightening/dimming sign. No injection label, amplitude, known native event
value, original covariance, or truth-removed vector enters this inference.

## One fixed predictor and nested calibration

Work separately by sector and width (2, 3 or 5 cadences). Each native context
supplies training starts **80,100,120,140,160,180,200,220,240,260,280,300,320**.
There are 13 samples per context/width, 390 per sector, 780 total. Use all
declared records without clipping, quality-based outcome selection or
relabeling. Starts are local to the already verified contiguous contexts.

For each assessed background A, exclude that *entire* context from global
training and error calibration. The final predictor uses 117 records from
the other nine backgrounds at the same width. Center X and Y on those records.
Set `Cxx = Xc.T @ Xc / (N-1)`, `Cxy = Xc.T @ Yc / (N-1)`, and
`lambda = trace(Cxx)/(2p)`. The ridge strength is exactly **1**; solve
`B = solve(Cxx + lambda*I, Cxy)`. Predict `mean(Y)+(x-mean(X))@B`.
No hyperparameter is chosen from either sector's new results.

The static ablation predicts only the same training mean Y. It uses no x.
Both methods retain the same templates, sparse residual option and cuts.

For each outer background A, covariance calibration additionally leaves out
the background B of the sample being predicted. Train on the remaining eight
backgrounds and predict all thirteen B samples; repeat for each B != A.
Collect all 117 such residuals. This nested scheme prevents fitting and
calibrating on the same background. Cache the 45 unordered two-background
exclusions and ten single exclusions per width: 330 regressions total.

For each method, form the sample covariance of its held-background residuals,
using `ddof=1`. Use 95% of that covariance plus 5% of its diagonal and a
diagonal floor of `1e-10 * mean(diagonal(empirical_covariance))`.
Retain all residuals and positive-definiteness checks. Do not subtract the
calibration residual mean as a second prediction correction. The final model
trains on nine backgrounds whereas calibration predictions train on eight;
this fixed mismatch is disclosed rather than tuned away.

The 13 records within a context have overlapping bands. They are not thirteen
independent observing units. Model covariance and residual degrees of freedom
remain descriptive engineering quantities, not calibrated probabilities.

## Spatial fit and fixed decision

Fit `sign*(y-prediction)` using that outer fold's normalized covariance.
Source templates are the nine historical empirical-profile shifts. Nuisances
include the original uniform/one-pixel/2x2/pointing bank; all intersecting
3x3,1x5,5x1 rectangles; and LS7H's cross, ring and four triangle orientations.
Keep every in-stamp aperture-intersecting placement and duplicate projection,
in the existing deterministic order. The bank is identical for both methods.

Use the previously audited exact FitBank arithmetic: nonnegative source,
free uniform residual, and either no extra pixel or one free residual pixel.
The optional pixel incurs objective penalty **9** symmetrically under both
stellar and nuisance hypotheses. No iterative pixel removal is allowed.

Acceptance requires all of:

- The frozen temporal screen passes (score at least **8**).
- Stellar amplitude/noise score at least **5**.
- Stellar chi-square divided by its recorded residual dof at most **2**.
- Nuisance objective minus stellar objective at least **-1**.

Recovery also requires no pre-existing native temporal confounding. Record
the full gate vector and first-failure path in the order above, then
confounding. Also record accepted negative margins, where the nuisance wins.
These unchanged numerical cuts define a *new statistic* because response,
local normalization and covariance have changed. They do not inherit a
false-alarm interpretation from earlier endpoints.

The historical upstream temporal window and screen are kept fixed for all
6,720 cases, as an isolated candidate/spatial-stage comparison. Their old
full-run sigma is part of the immutable upstream benchmark, not an input to
the new background predictor. This is not a new blind native event search.

## Separate sector-32 supplement

Take the 120 historical sector-32 nominal stellar parents at scores 8.5,12,20,
shapes box30/box100, phases 0/10, and all ten backgrounds. For each parent
create one cross3x3, ring3x3 and upper-triangle3x3 injection, for **360** cases.
Place each shape at maximum empirical-profile overlap using the historical
full-context injection profile, with the historical row-major tie rule.
Normalize its aperture sum to one. Use the parent's *recorded* pattern scale,
with no bisection, retuning or deletion. This truth-defined profile is used
only by the injection harness, never by the predictor.

Compute its temporal selection using the unchanged historical operator:
121-cadence median detrending, widths 2/3/5, center tolerance 20.1 seconds,
20-second exposure-integrated pulse and original full-run sigma. Preserve
both injected and native selections. Any mismatch exceeding 0.01 from the
declared target is a failed matching check, not grounds for a replacement.

Use cohort `sector32_shape_supplement`, global new IDs, explicit parent IDs
and null historical-source-row fields. Store separately as well as in the
complete ledger. The original 3,180-row sector-32 denominator stays intact.

For all 7,080 cases, the harness independently checks that the pulse plus
parent-local residual adds exactly zero in the predictor/reference bands.
It also checks feature, reference and local-scale invariance. Known native
arrays serve only this preservation assertion and never replace prediction.
If protection fails, stop and document an implementation/specification issue;
do not silently widen a band or omit a trial.

## Joint requirements and native prediction checks

Each sector has 36 core cells: six signal and thirty instrumental cells.
Nominal recovery must be at least **36/40** and displaced recovery at least
**128/160** at each of scores 8.5,12,20. Each instrumental cell allows at most
5% acceptance: **2/40**, or **4/80** for the signed pointing family.
No sector or cell may be averaged into a pass. Preserve the other joint
requirements: all matched strengths within 0.01, at least **54/60** recovered
10%-flux single pulses, no accepted base null (20 per sector), at most 20%
native-confounded stellar cases, and at most 5% acceptance among screened
bounded-pointing cases with a nonempty screened denominator.

Fixed-flux, doublet and sparse-residual stress results keep complete ledgers
and groups by duration, displacement, residual location and polarity. Publish
all additional stellar losses against each applicable frozen reference and
the paired static ablation, including losses outside the six core cells.

Native checks use starts **90,130,170,210,250,290,330**, every width 2/3/5 and
every background: 210 windows per sector, **420** total. Predict each with its
outer-background fold. These starts differ from training starts but overlap
in context; the protection against training leakage is the whole-background
exclusion, not an independence claim based on cadence spacing.

For a common comparison metric, use the *static* covariance for both methods.
Project out a free uniform component and compute the squared whitened
residual energy. Compare sums, not method-specific normalized chi-squares.
Per sector the conditional/static energy ratio must be at most **1** overall;
at least **6/10** backgrounds must improve strictly; and no single-background
ratio may exceed **2**. These are prospective descriptive benefit/stability
requirements, not calibrated error rates or candidate tests. Do not select
native windows by outcome or promote any candidate from this check.

## References, audit and decision

Sector 29 references are the sealed LS7G broad/-1 and LS7H augmented/-1
results. Sector 32's reference is the already fixed LS7F covariance-sparse
broad/-1 rule, derived from its saved eligibility and margins. No LS7H
sector-32 result is invented. The added shape cohort has no historical
reference; the paired static comparison covers it explicitly.

Eight synthetic known-answer tests precede the science freeze: protected
event/guard perturbation, signed pulse preservation, all declared pulse
geometries and parent-local stress, an orthogonal ridge solution, an
unpredictable target, a predictable held-background example, complete nested
anchor exclusion, and invalid contexts/scales. The independent reviewer
rebuilds observations, solves ridge with augmented least squares, recomputes
all nested covariances, independently builds the template geometry, checks
all 28,320 direct winning fits and all alternatives with whitened QR, checks
the supplement temporal selections, and recounts every decision, native gate,
72 core cells, 720 background/cell counts and every changed row/reference pair.
The already completed historical input/temporal/FITS audit is reused by hash.

Advancement requires both sector trial gates, both native gates and the audit
to pass. A pass is readiness to *prepare* a separately frozen unused-data
qualification, not detector adoption. A failure closes this single-model
route with a limitation analysis and a concrete recommendation for additional
observable information or a different optical method. Keep unused sectors
and the M43 held-out panels closed. No automatic cut/bank/ridge retry.

The GitHub workflow refuses to overwrite results, runs the tests, evaluation,
audit and report, and publishes the result only if the audit passes and the
science branch still points to the frozen source. Scientific gate failure
is a publishable negative result, not an infrastructure error.

## Reproduction

At the frozen source commit, with `results_ls7i_background` absent:

```sh
python -m pip install -r requirements_ls7g.txt
export PYTHONPATH=src OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
sha256sum -c LS7I_BACKGROUND_FREEZE.sha256
python -m unittest discover -s tests -p 'test_ls7i_background.py' -v
python scripts/ls7i_background.py
python scripts/ls7i_review_background.py
python scripts/ls7i_background_report.py --update-status
```

An audit repeated after publication writes `AUDIT_RECHECK.json` and preserves
the original audit. All older source/result manifests remain unchanged.
