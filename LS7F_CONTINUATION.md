# LS7F continuation

13 September 2026. **LS7F is complete; read its result before transfer.**

The [full report](results_ls7f_separation/REPORT.md) describes a separation
tradeoff on the **3,180 existing LS7E trial vectors**, with zero new injections
and zero observing coverage. All historical LS7C/LS7E outcomes are preserved.

At the unchanged margin 9, adding 108 rectangular nuisance templates rejects
all 960 matched original/extended control cases but loses 74 previously
recovered stellar trial rows in the sparse method. Nominal recovery changes
from 18/40, 37/40, 40/40 to 15/40, 34/40, 40/40. These are shared-background
development counts, not independent validation or evidence of source origin.

An exact margin sweep finds **no jointly feasible cut for the original bank**.
The expanded bank has 26 passing evaluated cuts with the sparse option and six
without it. **All passing cuts are negative**: some accepted events may have
a nuisance fit better than the stellar fit. At margin 0, the expanded sparse
method recovers 36/40 weak nominal but only 125/160 weak displaced pulses,
below the 128/160 requirement. No threshold is adopted.

The first enumerated control-safe expanded sparse margin (-2.9813923063)
recovers 38/40, 40/40, 40/40 nominal and 138/160, 160/160, 159/160 displaced
trials. It accepts 2/40 weak 2x2 controls and 2/40 weak 3x3 controls, with zero
acceptance in the other 19 core control cells. It is an outcome-selected
diagnostic endpoint on already seen data, not a prescribed production rule.

## Next useful integrated step

Prepare one **separately frozen transfer comparison on already closed sector
29**, before examining its transfer results:

- State the exact new rule, nuisance shapes, any chosen development margin and
  the same source, residual, temporal and sparse-penalty gates.
- Fix transfer background eligibility, training/covariance construction and
  source-template generation before scoring. Do not import sector-32 covariance
  as if the instrumental backgrounds were identical.
- Include known rectangles, additional unmodeled shapes, physically bounded
  pointing, and inside-aperture residual stress. Log temporal losses as well as
  spatial decisions, retaining per-background and per-strength denominators.
- Report the unchanged margin 9 and nonnegative margin 0 alongside any
  development-selected margin. Quantify accepted cases for which a nuisance
  fit is better; acceptance is not a stellar-origin identification.
- Call the outcome a transfer on previously inspected data. Independent
  qualification would need a later, separately frozen unseen evaluation.

This continuation does not itself choose a new threshold, open sector 29,
retrieve a new observing sector, alter LS7E, or open M43 held-out panels.
M43AI remains complete/unadopted; the earlier M33 case remains unresolved.

## Reproduction and restart

The LS7F source freeze was published before scoring at
[`6f70ebcdc41d956524f395e1f6a3ffa99a35e308`](https://github.com/andersenmartin-blip/setisearch/commit/6f70ebcdc41d956524f395e1f6a3ffa99a35e308).
The source base is `5eaf27ce96725defe211e744d60ad0f9f2ae4f86`.
All inputs are already in the public repository; raw FITS downloads are not
required to reproduce LS7F. Use [requirements_ls7f.txt](requirements_ls7f.txt)
and preserve the historical requirements files.

```sh
sha256sum -c LS7F_FREEZE.sha256
# From results_ls7f_separation:
sha256sum -c SHA256SUMS
# From repository root:
OPENBLAS_NUM_THREADS=1 python scripts/ls7f_review.py
```

The numerical auditor passes all 12,720 direct fit checks, 6,868,800 alternative
fits and 101,466 threshold/cell counts, including every endpoint certificate.
Use the existing evidence for normal continuation. The extractor refuses an
existing output directory; any necessary reproduction must use a separate
explicit `--output` path and the pinned inputs. The report renderer is a
post-result presentation script and is not part of the scientific source freeze.

The maintained entry point remains [PROJECT_STATUS.md](PROJECT_STATUS.md).
The owner's ongoing publication authorization remains in PROJECT_DIRECTION.md.
