# LS7D: locate the closed-sector pixel/aperture noise mismatch

12 September 2026. This is retrospective development using the completed
LS7C sector 32 experiment, not a new detector qualification. Freeze this
diagnostic code locally before executing it. No public preregistration is
claimed for this retrospective analysis. No new sector is required.

## Question and fixed scope

LS7C's published method failed its 1,460-case challenge. Its retrospective
review reconstructed 120 nominal matched-signal windows and found a median
4.66-fold difference between the spatial pixel-quadrature noise and temporal
run-level aperture noise. Covariance was suggested but not established as
the cause. Determine how the archived error floor, marginal versus summed
fluctuations, and local versus run-level noise contribute to this mismatch.

Use every one of the **120 recorded nominal matched trials**, with its exact
original selected window. Deduplicate identical (anchor, start, stop) windows
for computation; publish the complete trial-to-window mapping and summarize
both trial-weighted and unique-window distributions. Keep ten-anchor summaries
to expose reuse. These are not 120 independent noise backgrounds. Input hashes
are pinned in `config/ls7d_noise.json`; verify the two original FITS products,
all prior scientific freezes, and both LS7C output manifests.

Use the exact two LS7C sidebands, start-60 to start-5 and stop+5 to stop+60,
within each 401-sample context. Keep the original valid-pixel mask. Require
contiguous cadence IDs inside each sideband. No difference crosses the event
gap. Read restored and mission-corrected pixels plus FLUX_ERR and SAP_FLUX_ERR;
check that all four columns have compatible electron-per-second units.

## Fixed numerical accounting

1. Reproduce each LS7C pixel noise: the maximum of median archived FLUX_ERR
   and first-difference MAD / sqrt(2), with the original MAD constant. Reproduce
   all 120 prior pixel/aperture ratios to relative tolerance 1e-12.
2. Factor the ratio exactly as
   `Qmax / run = (Qmax/Qmad) * (Qmad/local_aperture_MAD) * (local_aperture_MAD/run)`.
   Q denotes quadrature of marginal pixel noise in the optimal aperture.
   The first factor isolates use of the archived error floor. The second mixes
   cross-pixel dependence with MAD's non-additivity; do not call it a covariance
   measurement. The third compares local and run-level estimators. The product
   of separate sample medians need not equal the median total ratio.
3. Independently measure sample covariance `C = cov(pixel first differences)/2`
   on all sideband differences, without clipping or removing cosmic-ray samples.
   Save aperture covariance matrices and verify `1^T C 1 = var(sum(d))/2` by
   a separate scalar path, for both restored and corrected streams. Record
   diagonal and cross terms, their ratio, and the covariance rank bound for
   a hypothetical full-stamp fit. No matrix inversion is performed.
4. Compare median archived SAP_FLUX_ERR to the simultaneous quadrature of
   aperture FLUX_ERR, preserving all ratios. Do not assume that an archived
   error column is a measured white-noise scale.
5. Compute first differences of adjacent nonoverlapping block means for widths
   1/2/3/5 samples within each sideband. Report aperture MAD for restored and
   corrected streams, block counts and unused tail samples. This probes 20–100 s
   noise scaling without crossing gaps or screening for favorable outcomes.

The covariance identity is algebraic. Dividing difference covariance by two
does not establish temporal whiteness, remove cosmic-ray effects, or produce
the covariance of an event-minus-median estimate. Classical moments can be
dominated by restored outliers. Corrected/restored comparisons and robust MAD
values expose this limitation; no significance, confidence interval or physical
false-alarm rate is assigned. Degenerate ratios are retained as missing values.

## Preservation and endpoint

Do not change a temporal threshold, spatial cut, input mask, reference profile,
trial label or acceptance decision. Do not rerun the 1,460 injections. Do not
open another sector or introduce an optimized noise rescaling. The 42/120
original nominal spatial passes remain historical outcomes. Save exact ledgers,
input identities, environment, analytical tests, plots and a readable report.

Passing the identities establishes accounting, not detector qualification.
Use the outcome to specify the next combined development experiment, including
unrelated residual pixels and compact/extended nuisance alternatives. A useful
successor must qualify signal recovery and nuisance rejection jointly.

Primary processing references checked 12 September 2026:
[NASA product overview](https://heasarc.gsfc.nasa.gov/docs/tess/data-products.html)
and [NASA cosmic-ray primer](https://heasarc.gsfc.nasa.gov/docs/tess/TESS-CosmicRayPrimer.html).
The primer documents reversible ground corrections in 20-second products;
adding them back does not independently validate any archived error column.

## Reproduction

```sh
PYTHONPATH=src python -m unittest discover -s tests -p 'test_ls7d_noise.py' -v
sha256sum -c LS7D_FREEZE.sha256
PYTHONPATH=src python scripts/ls7d_noise_diagnostic.py --cache /path/to/original/sector32/FITS
```

The runner refuses an existing output directory. Use a separate `--output` for
a necessary reproduction. Preserve earlier experiments by their own manifests.
