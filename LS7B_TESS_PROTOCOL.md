# LS7B: correction-aware TESS qualification on L 98-59 sector 29

Prospective protocol, 12 September 2026. The owner requested continuation and
has authorized ongoing code/results publication. Preserve the failed LS7 sector
28 experiment. Sector 29 is the next chronological available 20-second sector;
selection used MAST metadata only. Its measured arrays remain unopened at this
freeze. Use only the FAST-LC/FAST-TP files pinned in
`config/ls7b_tess_l9859.json` (MAST observation 27973351, 289,062,720 bytes).
Publish the complete scientific freeze before retrieving/reading these arrays.

## Change from LS7 and fixed data eligibility

Retain cadences whose combined LC/TPF quality word contains only bits **64 and
1024**, or no flags: `(QUALITY & ~1088) == 0`. Reject every other nonzero bit,
including unrecognized future bits. Bit 64 indicates a cosmic-ray correction
in the optimal aperture; 1024 concerns a collateral row/column. These are not
automatic proof of unusable data. This change addresses the documented LS7
fragmentation failure, not the outcome of a sector 29 signal search.

Restore the target-pixel ground cosmic-ray contributions using unchanged LS7
code, preserve corrected pixels, and record source SHA-256 hashes and FITS
identity/time/unit checks. Restoring target-pixel corrections does not reverse
collateral calibration or prove that every flagged cadence is good. Keep the
flag-specific counts and corrected/restored comparison as diagnostics.

Before detrending or screening, inspect time, cadence IDs, quality and aperture
finiteness. Keep the previous no-gap-filling policy. Require at least **5 cadence-
days** after the existing run/edge guards. Choose the same 10 evenly spaced
indices in the ordered list of possible 401-sample contexts as in LS7. Require
that those contexts do not overlap, have chronological separation of at least
99% of 401 × 20 seconds, and span at least five days. Numerous overlapping
possible indices do not substitute for ten distinct backgrounds. Selection must
not depend on brightness, variability, candidate scores or injection recovery.
If eligibility fails, publish a structured failure with missing endpoints and
zero completed trials, and stop before native screening.

## Unchanged detector and baseline digital trials

Reuse the original frozen LS7 implementation for calibrated aperture sums,
121-sample median detrending, per-run first-difference MAD noise, 60-sample edge
guards, 2/3/5-sample box scores and threshold 8, event association and the
provisional pixel morphology cuts. Screen both signs. Scores are not Gaussian
significances or astrophysical false-alarm probabilities.

Reuse all **300** original digital trials: 240 stellar-profile injections
(30/60/100-second top hats and two 30-second peaks separated by 87 seconds;
0.1%, 0.3%, 1% added aperture flux; two phases at each of ten anchors), 40
single-pixel/uniform-stamp nuisances and 20 unchanged controls. Integrate shapes
over continuous 20-second bins; readout gaps and earlier processing losses are
not measured by these injections. Freeze the noise on the unmodified background.

A signal trial is recovered only when its highest-scoring matched window reaches
8, passes all original pixel cuts, and no original matched window already reaches
8. Keep baseline-confounded trials in the signal denominator. Nuisance acceptance
counts all above-threshold morphology passes, including confounded cases.

## Additional spatial and pointing challenges

At the exact same anchors and phases, perform **120** additional trials:

- **80 off-profile signals:** a 30-second, 1% pulse with the empirical aperture
  profile shifted by +/−0.25 pixel along each detector axis, bilinearly interpolated,
  aperture-clipped and renormalized to preserve the injected aperture amplitude.
  The morphology reference remains unshifted. This challenges modest profile
  mismatch, not all possible real telescope PSFs.
- **40 pointing controls:** shift the whole local median stamp by +/−0.2 pixel
  along the column axis for a 30-second pulse. Use bilinear interpolation and
  preserve total stamp flux; aperture flux may increase or decrease. Record the
  actual induced aperture amplitude. These are two simple pointing perturbations,
  not a complete model of spacecraft pointing errors.

The experiment therefore contains **420 digital trials**, sharing ten separated
background contexts. They are not 420 independent observations of the sky.

The restricted engineering gate requires all of:

1. Eligibility and product/finite-noise checks pass.
2. At least 90% of the 60 baseline 1% single-pulse trials recover.
3. At least 80% of the 80 shifted-profile signal trials recover.
4. Acceptance is at most 5% **separately** for single-pixel, uniform-stamp and
   pointing controls (20, 20 and 40 trials, respectively).
5. No unchanged control passes the combined screening/morphology rule.
6. At most 20% of the 240 baseline stellar trials are baseline-confounded.
7. Neither sign exceeds the 2,000-event cap in either the restored primary or
   corrected diagnostic screen. Keep the cap and threshold unchanged on failure.

Passing this gate qualifies only this restricted digital experiment. It does
not establish an adopted SETI detector, complete transient sensitivity or a
rate limit for propulsion activity. A stellar flare can pass the morphology cuts.

## Native data review and geometry

Archive all retained restored and corrected events with their provenance. For
restored events record the corrected score in the same window using the same
primary noise, the restored contribution, local pointing proxies, morphology,
and combined quality flags. These quantities are descriptive; they do not add
post-hoc vetoes or change the gate. Render the strongest six positive morphology
passes and four positive failures, or all if fewer, without selecting by geometry.
Inspect the time profile and excess image. State unresolved stellar/instrumental
alternatives; do not promote an event as an LS candidate in this qualification.

Evaluate the unchanged LS3 b/c/d ephemerides using BJD_TDB and the original
circular, edge-on, common-node 1D model. Report coverage and event geometry, but
do not select windows or infer beam interception. Inclinations, nodes and
ephemeris uncertainty are not modeled. No conjunction significance test is made.

This is an optical complement to the earlier LS1 radio analysis. TESS's nominal
600–1000 nm band, 21-arcsecond pixels and one broadband intensity measurement do
not identify a narrow laser spectrum or rule out all unresolved stellar sources.
The proposal's 1.06-micron narrow beam lies outside this nominal band. No physical
light-sail population limit follows from these digital trials.

## Reproduction, publication and failure handling

```sh
python -m pip install -r requirements_ls7.txt
PYTHONPATH=src python -m unittest discover -s tests -p 'test_ls7*.py' -v
sha256sum -c LS7_FREEZE.sha256
sha256sum -c LS7B_FREEZE.sha256
PYTHONPATH=src python scripts/ls7b_tess_pilot.py
```

The runner refuses to replace an existing result directory. Reproduce with a
new `--output` directory. Raw FITS remain in an ignored cache; publish only code,
protocols, provenance, derived ledgers/figures and reports. Record structured
failures and exact completed endpoints. Do not lower thresholds, shorten required
backgrounds, move anchors, change amplitudes or open another sector in response
to an unfavorable result. Any subsequent scientific change gets its own freeze.

## Primary references

- [MAST quality-flag and product definitions](https://outerspace.stsci.edu/spaces/TESS/pages/14563420/2.0%2B-%2BData%2BProduct%2BOverview)
- [NASA TESS cosmic-ray processing](https://heasarc.gsfc.nasa.gov/docs/tess/TESS-CosmicRayPrimer.html)
- [Exact sector 29 FAST-TP source](https://mast.stsci.edu/api/v0.1/Download/file?uri=mast:TESS/product/tess2020238165205-s0029-0000000307210830-0193-a_fast-tp.fits)
- [Original LS7 protocol](LS7_TESS_L9859_PROTOCOL.md) and [failure/metadata diagnosis](results_ls7_tess/REPORT.md)

MAST metadata and processing documentation verified 12 September 2026.
