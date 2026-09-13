# LS7F: weak stellar / broader-nuisance separation on saved LS7E vectors

13 September 2026. This is retrospective development on the **3,180 already
closed LS7E trial vectors**, all sharing ten L 98-59 sector-32 backgrounds.
LS7E's published failures motivate the comparison. There are **no new digital
injections, telescope observations, native candidate decisions or sector
openings**. The earlier LS7C challenge, LS7E decisions and M43 panels are preserved.

## Fixed comparison, before extracting new LS7F fits

Keep the saved temporal windows, event vectors, sign, 18-pixel optimal aperture,
all 94 saved model contexts, 30 covariance folds, 5% shrinkage, nine stellar
templates, source score >=5, reduced residual <=2 and temporal score >=8.
Compare the existing full-covariance methods with and without the optional
sparse pixel. The sparse penalty stays **9 for both stellar and nuisance fits**.
The diagonal ablation is already answered by LS7E and is not repeated here.

For each method compare the original nuisance bank with its union with **every
in-stamp 3x3, 1x5 and 5x1 rectangle placement intersecting the aperture**.
Use row-major placement order and the stated shape order; keep duplicate
aperture projections and partial overlaps. The new templates have nonnegative
free amplitude plus the same background and optional sparse pixel. No event
selects the bank, position, penalty, covariance or source shape. Coordinates
come from the saved LS7D windows; reconstruct every old 2x2 template to verify
the aperture ordering against LS7E.

The LS7E extended controls are now an explicitly **modeled training class**.
Their rejection is not evidence about unknown artifacts. Adding templates can
only lower the nuisance objective and source/nuisance margin at fixed stellar
fit: it cannot improve recovery at the unchanged margin **9**. Record all lost
LS7E signals individually, alongside any removed control acceptances.

## Exact margin tradeoff, with no adoption

For each of the four method/bank combinations enumerate every distinct
acceptance set under `margin >= threshold`, holding every other gate fixed.
Use each eligible recorded margin (ties included together), the unchanged 9,
and the finite next representable value above the largest margin. A case
failing temporal/source/residual eligibility remains lost at every threshold.
Baseline-confounded signal cases remain in denominators and are not recoveries.

The joint diagnostic requirements are unchanged nominal recovery >=90%
(36/40), displaced recovery >=80% (128/160), and <=5% control acceptance in
each original or extended kind/strength cell (21 control cells, six signal
cells). Keep strengths 8.5, 12 and 20 separate. Report the first threshold
satisfying all control requirements, the last satisfying all signal
requirements if one exists, and the complete feasible intersection. These
endpoints are **outcome-selected diagnostic bounds on these closed records**,
not chosen production thresholds, independent validation or false-alarm rates.

Keep full fixed-9 descriptions of all 3,180 records, including fixed-flux
signals, inside/outside positive/negative sparse stress, original nulls and
physically bounded pointing. They receive no newly invented pass requirement.
Publish the full sweep, per-cell accepted/rejected and prior-signal-loss IDs
at the diagnostic endpoints, and per-background counts. Empty/subthreshold
control sets are not evidence of spatial rejection. Counts are not independent
observations and support no population or physical laser sensitivity limit.

## Verification and continuation

Freeze this protocol, configuration, implementation, tests and independent
auditor before new LS7F scoring. Publish the source freeze separately from the
completed result. This is a prospective implementation freeze within a
retrospective study; it is not preregistration of unseen evaluation data.

Check all pinned source hashes and historical LS7/LS7B/LS7C/LS7D/LS7E freeze and
result manifests before and after scoring. Verify both old fit families against
the archived fits under the explicitly recorded LS7F runtime; preserve archived
stellar fits/margins exactly after the numerical check. Analytical tests cover
template geometry, exact tie/endpoint handling, non-margin eligibility,
template-scale invariance and the known signal-loss effect of enlarging a bank.

An independent audit uses direct whitened least squares for every saved stellar
fit and new winning rectangle fit, QR-based exhaustive rectangle minima for
every vector and method, and direct Boolean counts for every threshold/cell.
Check all endpoint IDs, historical decisions and descriptive counts.

If no threshold meets the joint closed-data requirements, do not spend another
sector merely to re-evaluate this same margin family. Use the explicit losses
and overlap to decide what additional observable or different model is needed.
If development supports transfer, plan and freeze it separately on already
closed sector 29 first. No result here opens sector 29 or another sector.

```sh
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src python -m unittest discover -s tests -p 'test_ls7f_separation.py' -v
sha256sum -c LS7F_FREEZE.sha256
OPENBLAS_NUM_THREADS=1 PYTHONPATH=src python scripts/ls7f_separation.py
OPENBLAS_NUM_THREADS=1 python scripts/ls7f_review.py
```

The extractor refuses an existing result directory. Exact source inputs are
already public at the commit recorded in `config/ls7f_separation.json` and can
be restored without raw FITS downloads or rerunning LS7C/LS7E. LS7F dependencies
are recorded in `requirements_ls7f.txt`; earlier requirements stay unchanged.
