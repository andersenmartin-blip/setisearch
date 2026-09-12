# LS7C: noise-aware pixel discrimination with matched-strength controls

Prospective protocol, 12 September 2026. Continue the authorized optical LS
work after the completed LS7B failure. The new method addresses the hard
cosine/centroid losses and the absence of above-threshold nuisances in LS7B.
The temporal detector is unchanged. **Publish this complete scientific freeze
before downloading or opening sector 32 arrays.** No sector 32 light curve,
pixel image or noise estimate has informed the design.

## One fixed evaluation dataset

Use L 98-59, TIC 307210830, TESS/SPOC sector 32: the next chronological available
20-second sector after the closed sectors 28/29. MAST metadata only selected
observation **28135054**. The two FAST-LC/FAST-TP filenames and their byte sizes
are pinned in [configuration](config/ls7c_tess_l9859.json) and
[archive selection](LS7C_ARCHIVE_SELECTION.json): **287,098,560 bytes** total.
Verify FITS TIC/sector, cadence IDs, TDB timing, units and SAP aperture agreement.
Record retrieved source hashes. A source size or structural mismatch is a failure.

Reuse LS7 cosmic-ray restoration and LS7B eligibility without modifying their
code or original results: allow only quality bits 64/1024 (mask 1088), never
fill gaps, use the same run/edge guards and 401-sample contexts. Require five
searchable cadence-days and ten nonoverlapping, time-separated backgrounds
spanning five days. Anchor positions use timing/flags/finiteness, not brightness,
screening scores or recovery. Require finite, positive archived FLUX_ERR in
every accepted aperture pixel and the same units as FLUX; failure is structural,
not permission to remove additional observations after inspecting scores.

## Fixed temporal detector

Unchanged 121-sample median baseline, first-difference MAD noise per accepted
run, 60-sample edge guards, 2/3/5-sample boxes and threshold **8**. Run both signs;
retain strongest nonoverlapping windows with the existing 2-sample padding and
2,000-event cap per sign per stream. Preserve restored and corrected screens.
Screening statistics are not Gaussian significances or false-alarm probabilities.

## New spatial test

For each selected window use two native sidebands, from 60 to 5 cadences before
and after it. Require at least 20 samples on each side, valid aperture pixels
and at least three other valid pixels. Estimate the per-pixel median reference.
Use the larger of the first-difference MAD noise and median archived FLUX_ERR;
differences never cross the gap between sidebands. No injected values enter
the reference or variance calculation.

For a window of n samples and N sideband samples, use diagonal variance
`sigma_pixel² × (1/n + pi/(2N))` for the mean-minus-median difference image.
The reference term is a Gaussian median approximation. Cross-pixel covariance,
temporal correlations and uncertainty from restoring cosmic rays are not fully
modeled. These limitations are evaluated by the finite challenge rather than
by assigning a theoretical p-value.

The stellar template is the positive native reference within the optimal
aperture, normalized to unit aperture sum, with zero excess outside. Fit a
nonnegative source amplitude plus a free constant background. Try a fixed
nine-template bilinear shift grid: each coordinate in `{0, -0.25, +0.25}` pixels,
aperture-clipped and renormalized. Choose the smallest weighted residual sum.
The fit uses all valid stamp pixels; the background is eliminated analytically.

Competing explanations use the same variance and constant background: uniform
change alone, a positive impulse in each aperture pixel, and both polarities
of four flux-conserving scene shifts of ±0.2 pixel in x/y. A template amplitude
is nonnegative; paired pointing polarities allow both signs. Choose the best
competitor. A spatial pass requires all three fixed cuts:

1. Fitted source amplitude divided by its nominal fit error **at least 5**.
2. Stellar weighted residual sum divided by `(valid pixels - 2)` **at most 2**.
3. Best competitor residual minus best stellar residual **at least 9**.

Template selection and estimated variance mean the residual quantities do not
have an asserted chi-square distribution. A spatial pass is neither a discovery
significance nor a stellar-flare veto. Reference profiles can include blends.

## All 1,460 digital trials

Use ten separated 401-sample backgrounds and two exposure phases, 0/10 seconds.
Integrate the continuous top hats over nominal 20-second bins. Freeze temporal
noise on the unmodified native run. Deterministic digital additions do not add
photon shot noise, reverse all mission processing or evaluate quality survival.

| Family | Definition | Trials |
|---|---|---:|
| Fixed amplitudes | 1%, 3%, 10%; 30/60/100-second single pulses and two 30-second pulses separated by 87 s | 240 |
| Matched nominal signals | Unshifted aperture profile; 30/100 s; observed scores 8.5/12/20 | 120 |
| Matched displaced signals | Four diagonal shifts (±0.2, ±0.2) pixels; same widths/scores | 480 |
| Single-pixel nuisances | Brightest profile pixel; same widths/scores | 120 |
| Compact-block nuisances | Uniform 2×2 block maximizing enclosed reference-profile flux; same widths/scores | 120 |
| Uniform nuisances | Entire stamp; same widths/scores | 120 |
| Pointing-pattern nuisances | Whole median scene shifted ±0.2 pixel in x; same widths/scores | 240 |
| Unchanged controls | No added signal; 30-second matching locations | 20 |
| **Total** | **Many trials share the same ten backgrounds** | **1,460** |

Diagonal injection shifts do not coincide exactly with the fitted grid. The
compact-block nuisance is absent from the competitor library. Other nuisances
partly match fitted alternatives by construction; their rejection alone does
not establish performance on arbitrary instrumental artifacts.

For matched trials, normalize each spatial pattern to absolute aperture sum
one and keep its sign. Use the corresponding positive/negative temporal score.
Use exactly 26 bisections between zero and 50% of median aperture flux to reach
the target score. The matching tolerance is 0.01 score units. Only temporal
strength enters this amplitude calculation; pixel-test outcomes never do.
The strongest window within 20.1 s of a truth peak is the matching window.
Verify the achieved score after injecting the actual spatial pattern.

If the native matched score already exceeds the target, or the amplitude cap
cannot reach it, keep the case as unmatched and fail the strength-coverage gate.
Never silently replace its background or drop it. Record actual aperture
amplitudes, signs and pattern multipliers. Scaled pointing patterns are linear
stress tests, potentially larger than the underlying 0.2-pixel motion, not a
claim to simulate physical spacecraft displacements of that magnitude.

A signal is recovered if the strongest matched window reaches 8, passes the
new spatial rule, and no unmodified matched window reaches 8. Keep confounded
signals in the denominator. Nuisance acceptance counts every combined pass,
irrespective of confounding. A failed tuning attempt is not a missing case.

## Joint restricted engineering gate

Require all of the following; do not pool away a failed strength or nuisance class:

- Complete, unique accounting of all 1,460 cases, successful product/eligibility
  checks, all 1,200 matched cases within tolerance, and no event-cap overflow.
- At each matched score separately, at least **90%** nominal signal recovery
  (40 cases per level) and **80%** displaced-signal recovery (160 per level).
- At each matched score separately, at most **5%** acceptance for each nuisance
  kind: single pixel, block, uniform (40 each per level) and pointing (80 per level).
- At least **90%** recovery of the 60 fixed 10% single pulses.
- No accepted unchanged control; at most 20% confounding across all 840 signals.

The 1%/3% and doublet curves remain reported diagnostics, not the bright gate.
Passing these changed requirements would not overturn LS7B's failed **1%**
qualification or imply that every real 30-second glint is detectable.

## Native review, geometry and boundaries

Archive all retained restored native events with spatial components, quality,
same-window corrected scores using primary noise, local POS_CORR differences
and descriptive conjunction coordinates. Archive corrected-stream trigger
records and both-sign counts. Native follow-up plots show the strongest six
positive spatial passes and strongest four failures, or all if fewer.
Review those images without introducing new vetoes or modifying recorded counts.
No event is promoted as an LS candidate during this method qualification.

Use the unchanged LS3 circular, edge-on, common-node 1D ephemerides on BJD_TDB
for b/c/d separation. Report searched coverage within one stellar radius.
Pair windows can overlap; no geometry selection or beam-interception inference
is allowed. Inclination, nodal and ephemeris uncertainties remain unmodeled.

TESS's nominal 600–1000 nm single band complements LS1 radio observations but
does not identify laser coherence or a narrow spectrum. A 1.06-micron line is
outside that nominal band. These post-processing trials establish no telescope
completeness, physical false-alarm rate or extraterrestrial population limit.

## Reproduction and preservation

```sh
python -m pip install -r requirements_ls7.txt
PYTHONPATH=src python -m unittest discover -s tests -p 'test_ls7*.py' -v
sha256sum -c LS7_FREEZE.sha256
sha256sum -c LS7B_FREEZE.sha256
sha256sum -c LS7C_FREEZE.sha256
PYTHONPATH=src python scripts/ls7c_tess_pilot.py
```

The runner checks the scientific manifest and refuses existing result paths.
Use a new `--output` for reproduction. Save input hashes, completed per-anchor
trial checkpoints, native ledgers, environment, figures, report and output hashes.
Failures keep exact completed endpoints; an unexecuted endpoint is not a null.
Raw FITS are cached outside tracked artifacts. Publish derived outputs and the
main README update under the owner's ongoing authorization. Do not open another
sector or change a threshold after a failed result; any successor gets a new freeze.

The method was designed from the closed LS7B accounting and synthetic known-
answer tests. No new retrospective fit on sector 29 arrays is claimed.

Primary references verified 12 September 2026:
[NASA cosmic-ray processing](https://heasarc.gsfc.nasa.gov/docs/tess/TESS-CosmicRayPrimer.html),
[MAST product/quality documentation](https://outerspace.stsci.edu/spaces/TESS/pages/14563420/2.0%2B-%2BData%2BProduct%2BOverview),
[exact FAST-TP](https://mast.stsci.edu/api/v0.1/Download/file?uri=mast:TESS/product/tess2020324010417-s0032-0000000307210830-0200-a_fast-tp.fits).
