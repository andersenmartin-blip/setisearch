# LS7G: fixed transfer to already closed TESS sector 29

13 September 2026. Follow LS7F with a **transfer on previously inspected
L 98-59 sector-29 data**. This is method development, not an independent
qualification, a native candidate search, or added observing coverage.
LS7B and the distinct historical sector-29 LS7C archive remain closed and
unchanged. No unseen TESS sector or M43 held-out panel is opened.

## Sources, selection and covariance

Restore the exact two public MAST products recorded in
`results_ls7b_tess/source_manifest.json`; require their original byte counts
and SHA256 hashes. Reproduce the LS7B time/quality eligibility verbatim:
allow only flags 64 and 1024, retain the same ten nonoverlapping 401-cadence
anchors, and preserve its 19.662037 searched cadence-days. These days are
reused, not new exposure. Do not select a different anchor after observing
flux, fit results or tuning failures.

The sector-29 optimal aperture has **21 pixels**, compared with sector 32's
18. Use that actual aperture, not an imported sector-32 mask. Recompute each
anchor's original run-level first-difference MAD and require agreement with
the archived LS7B noise value. Publish the restored background extracts,
run-aperture flux vectors, cadence/quality metadata and source identities so
later reproduction does not require another 289 MB MAST download.

For each background collect event-mean minus sideband-median vectors at
starts 100, 150, 200, 250, 300 and widths 2, 3, 5. Normalize by its run noise.
Estimate each width-specific covariance from all **45 vectors in the other
nine backgrounds**, centered with ddof=1, 5% diagonal shrinkage and the LS7E
1e-10 mean-variance diagonal floor. Rescale to the assessed background's
run noise. All 30 folds and 150 training vectors are retained. Their overlapping
windows and shared backgrounds are not independent observations.

## Fixed rule and comparisons

The primary development rule is **full covariance + optional sparse pixel +
expanded nuisance bank, margin >= -1**. The integer -1 is chosen using the
already published LS7F sector-32 development interval; it is not optimized on
sector 29. Its negative value explicitly permits a nuisance fit to be better
than the stellar fit by up to one objective unit. It is not a source-origin
or significance claim.

For every event also report margins **0 and 9**, the original nuisance bank,
and the full-covariance model without the sparse pixel. This gives 12 paired
fixed rules per trial. There is no sector-29 threshold sweep or post-result
model choice. The no-sparse method is an ablation, not a separately optimized
model; -1 was selected for the sparse method.

Retain LS7E's source score >=5, reduced residual <=2, temporal score >=8,
free uniform background, nonnegative template amplitude, nine stellar shifts
and a sparse penalty of **9 for either hypothesis**. Fit only the actual
optimal-aperture pixels. Build the stellar and original nuisance templates
from the assessed event's native sidebands. Add every 3x3, 1x5 and 5x1 rectangle
placement intersecting that aperture, keeping partial overlaps and duplicate
projections. No template or fit parameter is selected from injected outcomes.

## Joint 3,540-case transfer challenge

All cases share the ten original backgrounds. Shapes, phases, temporal
strengths and matching rules come from the original LS7C sector-32 protocol,
applied prospectively to this LS7G transfer. Pulse phases are 0 and 10 seconds.
Matched single shapes are 30 and 100 seconds, at scores 8.5, 12 and 20.

1. **1,460 base cases:** 240 fixed-flux stellar cases (1%, 3%, 10%; original
   four shapes), 120 matched nominal stellar cases, 480 matched displaced
   stellar cases, 600 matched original instrumental cases and 20 unchanged
   nulls. Use the original fixed 26-step temporal bisection and 50% aperture
   amplitude cap, without pixel feedback. Retain every unmatched/confounded
   case in its denominator and fail the relevant accounting requirement;
   do not replace it or silently increase the cap.
2. **1,040 sparse stress cases:** each matched nominal, matched 2x2 and null
   parent receives one positive/negative inside/outside pixel over the parent's
   selected window. The inside pixel is the faintest native-profile aperture
   pixel; outside is (0,0), which must be outside the aperture. Its amplitude
   is 8 times the fold's predicted inside-pixel event standard deviation,
   identical for all rule comparisons and for the exterior pixel. Repeat
   temporal selection and retain temporal losses. Publish parent IDs,
   selected spans, pixel identities and exact amplitudes.
3. **360 known extended controls:** 3x3 blocks, 1x5 rows and 5x1 columns.
   These are fitted nuisance classes and cannot establish rejection of
   unknown artifacts.
4. **360 additional shape controls:** a five-pixel 3x3 cross, an eight-pixel
   3x3 ring with the central pixel omitted, and the six-pixel upper triangle
   of a 3x3 square. These named shapes are omitted from the fit bank, although
   some aperture projections may resemble or coincide with modeled patterns.
   For both extended suites choose the in-stamp placement of greatest native
   reference-profile overlap, using row-major tie breaking, and normalize
   to unit aperture projection. Use every matched strength, shape and phase.
5. **320 bounded pointing cases:** the original eight signed shifts of 0.05
   or 0.2 pixel, preserving the reference image's total stamp flux, with
   multiplier exactly one, both single-pulse shapes and phases. These are not
   amplified to the screening threshold. Subthreshold counts do not show
   spatial rejection of detectable motion artifacts.

## Endpoints and limitations

Keep strengths separate. The **36 core cells** require nominal recovery
>=36/40 and displaced recovery >=128/160 at each strength, and <=5% acceptance
in all 30 original/known-extended/additional-shape kind/strength cells. The
joint descriptive gate also requires every target strength matched, >=54/60
fixed 10% single pulses recovered, zero base-null acceptance, <=20% signal
confounding, and <=5% acceptance among screened bounded-pointing cases with a
nonempty screened set. The sparse stress suite remains an explicit robustness
description; it receives no invented recovery gate that ignores its temporal
losses. Report every suite, per-background outcome and accepted/recovered ID.

For every accepted case say whether the nuisance objective is lower. Preserve
all stellar losses relative to the same method with the original bank/margin
9, even if the expanded rule improves an aggregate cell. Test counts and
6-to-8-digit numerical objectives are not Gaussian significances, independent
trials, false-alarm probabilities or astrophysical completeness. Injections
occur after mission processing and add no photon shot noise. A pass on this
already examined sector does not qualify a laser detector.

## Freeze, independent audit and publication

Publish this protocol, configuration, code, workflow and source checksums
before LS7G acquisition/extraction. Five analytical tests and an artificial
3,540-case smoke fixture must pass first. The smoke fixture is not telescope
evidence. Reuse unchanged LS7E/LS7F fit arithmetic and its existing tests.

The independent auditor reconstructs injection shapes, all event vectors,
temporal windows, run noise and covariance folds from the saved extracts;
checks direct whitened fits and exhaustive QR-based template/pixel minima
for every vector; and rebuilds all decisions, group/gate and per-background
counts. Check historical manifests before and after extraction. Stop on a
source/implementation discrepancy; do not repair a failed scientific gate by
retuning it. A completed negative scientific result is published normally.

Use the project's existing GitHub Actions pattern for the complete computation.
The dedicated job is bounded to sector 29 and this science branch, saves logs
as an artifact, and publishes checked results only after the numerical audit.
It requires the remote branch still to equal the execution commit before
pushing; no force push or unrelated branch mutation is permitted. Main's
README is updated separately after verifying the result publication.

```sh
python -m pip install -r requirements_ls7g.txt
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src python -m unittest discover -s tests -p 'test_ls7g_transfer.py' -v
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src python scripts/ls7g_synthetic_check.py
sha256sum -c LS7G_FREEZE.sha256
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src python scripts/ls7g_transfer.py --cache data_ls7g_sector29
OPENBLAS_NUM_THREADS=1 python scripts/ls7g_review.py
OPENBLAS_NUM_THREADS=1 python scripts/ls7g_report.py
```

The extractor refuses existing results. Preserve a failed execution and its
logs; any necessary implementation repair needs its own documented source
freeze, while the scientific settings and original outcome remain visible.
