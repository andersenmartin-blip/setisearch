# LS7I input restoration for the joint background-model study

13 September 2026. This implements the first block of the approved
[two-week plan](TWO_WEEK_PLAN_2026-09-14.md). It is an input-restoration freeze,
not the scientific protocol for a new model. No new data sector is opened.

## Fixed inputs and outputs

Restore the two original L 98-59/TIC 307210830 sector-32 SPOC 20-second FITS
products in `results_ls7e_joint/source_manifest.json`, checking their exact
byte counts and SHA-256. Use the unchanged LS7 loader and LS7B eligibility
implementation with the sector-32 configuration. Require the archived LS7C
preflight and ten anchor indices to reproduce. Restore ground-removed cosmic
ray values before cutting out the same 401-cadence context around each anchor.

Persist a sector-32 NPZ with the same array interface as sector 29's existing
`results_ls7g_transfer/backgrounds.npz`: native full-stamp pixels, relative
seconds, original run noise, aperture, anchors and BTJD, cadence IDs, quality
words, and the original run-flux arrays/bounds. Keep each sector's own mask
(18 or 21 pixels). Sector 29 is referenced by path/hash; do not duplicate or
redownload its existing file. Raw FITS remain reproducible source inputs rather
than large repository artifacts.

Create a common, ordered recipe ledger linking every sector-29 LS7G row (3,540)
and every sector-32 LS7E row (3,180), with globally sector-qualified IDs. Keep
source row positions, trial and model IDs, context IDs, original temporal
choices, flags and exact original injection amplitudes. Export the full
spatial patterns and any residual-pixel additions needed to reconstruct each
injected context. Do not rerun amplitude tuning or select different trials.

For sector-32 base/stress cases, resolve amplitudes from the original LS7C
parent's recorded tuning or original fixed flux fraction, and rebuild its
frozen pattern. Apply sparse stress at that parent's original selected window,
even when the altered case selects a different window. Extended controls use
their recorded placement and amplitude, checking the original deterministic
placement rule. Bounded pointing retains multiplier one. For sector 29, retain
the exact LS7G pattern, scale and residual metadata.

The normalized suite map is `ls7c_replay → base`, `extended → known_extended`,
`physical_pointing → bounded_pointing`; sparse stress is unchanged. Preserve
the legacy suite as well. Sector 32 has no historical cross/ring/triangle
suite corresponding to sector 29's 360 omitted-shape cases. Report this gap;
any additional controls belong to the forthcoming separately frozen model
evaluation, with their own denominators.

## Checks before declaring the package ready

- Verify all preserved source/result manifests before and after preparation.
- Check source identity, original eligibility, timing, flags, aperture,
  context indices and original run-level robust noise.
- Reconstruct every existing injected context from the exported recipe;
  compare its event vector, best temporal window/score and native confounding
  window/score with the unchanged source ledger. This checks restoration; it
  does not fit or qualify a new detector.
- Reconstruct all 300 archived covariance-training vectors from the two sets
  of individual-cadence data. Link every case to its original model window.
- Independently verify every recipe using coordinate/shift pattern construction,
  the previously frozen independent pulse integrator and scalar temporal
  enumeration. Independently restore sector-32 pixel/context and original run
  flux arrays directly from FITS and cosmic-ray records, without the main loader.
- Require exact raw array equality; use event-vector tolerances 1e-11 relative /
  1e-9 absolute, temporal-score 1e-10 / 1e-8, training-vector 1e-11 / 1e-11.
  Verify identical selected window endpoints and decisions.
- Three analytical tests check residual placement after temporal reselection,
  fixed/null amplitudes and complete sector-qualified source identities/order.
  Reuse completed spatial-fit/covariance audits by hash; do not rerun them.

Publish both the source and resulting input evidence. Refuse to overwrite an
existing package. If a mismatch appears, stop and record its cause; do not
change old outputs, amplitudes, thresholds or denominators to make it pass.

## Inference boundary and continuation

Recipes and their labels/amplitudes are evaluation truth. A future background
model cannot use them, the known un-injected realization beneath a pulse or
the background-subtracted target vector as inference features. Its training
and protected event interval require a separate, prospective scientific
specification. Successful input restoration leaves all LS7G/LS7H detector
failures unchanged and adds zero new trials, observing days or candidates.

The GitHub workflow restores the inputs, runs the full audit, saves logs and
environment, then publishes only the audited package and current status.
It checks that the science branch still points to the executing source commit
before making a non-forced result commit. A derived-only local audit can run
without Astropy or raw FITS and must not overwrite the sealed raw-source audit.

```sh
sha256sum -c LS7I_INPUT_FREEZE.sha256
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 python -m unittest discover -s tests -p 'test_ls7i_inputs.py' -v
PYTHONPATH=src OPENBLAS_NUM_THREADS=1 python scripts/ls7i_prepare_inputs.py --cache /path/to/original_sector32_cache
OPENBLAS_NUM_THREADS=1 python scripts/ls7i_review_inputs.py --cache /path/to/original_sector32_cache
python scripts/ls7i_inputs_report.py
```

Add execution/audit/test/environment logs before sealing with the report script.
For later verification of the exported package alone, omit `--cache` from the
auditor; all prior source and result identities remain hash-checked.
