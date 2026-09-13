# LS7H continuation

13 September 2026. Completed; preserve the sealed outcome.

LS7H diagnoses all **3,540 saved LS7G trials**. All **24** accepted controls in
the four failed cells have clean, background-removed margins below −1: the
native contribution changes the same-window model comparison. One fixed
extension adds **245** cross/ring/rotated-triangle placements. It reduces
those acceptances **24 → 9**, but loses **10** previously recovered stellar
trial rows. **2/30** control cells still fail; all six signal cells pass.
The independent audit passes. No detector or candidate is adopted.

## What this establishes

- The four focus cells change from 4/40, 8/40, 9/40, 3/40 accepted controls
  to 4/40, 2/40, 3/40, 0/40. The weak 2x2 and triangle cells still fail.
- All 24 original focus acceptances become margin rejections when the known
  native component is removed at the same selected window. The clean vectors
  agree with the injected-only event statistic within 2.01e-12 e-/s per pixel.
  This is conditional on injection truth, not a native-event rejection rule.
- A sparse pixel is present in 23/24 original stellar winning fits for those
  controls. Simply disabling that option fails genuine-pulse recovery, so
  neither more shapes alone nor deleting the sparse option solves the joint
  problem. A background/residual interaction is the next concrete question.
- All nine remaining focus acceptances share backgrounds 00 and 01. They are
  repeated uses of two contexts, not nine independent false alarms or an
  estimate of an astronomical false-alarm rate. Do not drop those contexts.
- All six signal-recovery cells still pass with the new bank, but weak nominal
  recovery has no headroom: 36/40, versus 37/40 in LS7G. Weak displaced recovery
  drops 135/160 to 130/160. Every one of the ten additional stellar losses is
  listed in the result, including fixed-flux and residual-stress rows.

## Next integrated study

The [14–27 September work plan](TWO_WEEK_PLAN_2026-09-14.md) provides the
schedule, deliverables and decision branches for this study. It is an
operational plan, not the numerical experiment's source freeze.

Next, develop a joint model of the time-varying background and residual
pixels using observable samples outside the tested pulse. The remaining
nine focus-control acceptances all occur on backgrounds 00 and 01; keep all
ten backgrounds in the next study. Compare with both fixed LS7G and LS7H
references, preserve individual signal-loss accounting, and plan sector 29
and already closed sector 32 together. Do not assume the native contribution
is predictable or use injection-truth subtraction as a detector input.

Start by checking whether a time-resolved predictor can use outside-event
cadences to constrain background and pixel residuals without subtracting the
unknown signal. Define the model, training exclusions, eligible windows and
all joint gates before its outcome is inspected. Combine implementation,
known-answer verification, native background checks and signal/control
comparisons into one study. Keep event labels and the known native realization
out of inference. If outside-event data cannot predict the relevant component,
record that limitation rather than assume a background repair exists.

LS7I has now restored and independently verified both sectors' individual-
cadence inputs. All 6,720 historical trial recipes and 300 training vectors
reproduce exactly. Use `results_ls7i_inputs/datasets.json` and
[LS7I_CONTINUATION.md](LS7I_CONTINUATION.md) for the ready input interface;
no further raw-FITS recovery is required for the model stage. Sector 29 still
uses the unchanged LS7G cutouts, and sector 32 has its original source-hashed
cutouts restored. The historical trial cohorts and apertures are preserved.

The LS7H extension is not adopted as a detector. Its current margin −1 and
all prior decisions remain sealed; no new threshold sweep or automatic unseen
qualification follows. A future study must state any different semantics
explicitly and retain the original joint requirements and denominators.

## Reproduction and publication

- [Complete report and figure](results_ls7h_morphology/REPORT.md)
- [All features](results_ls7h_morphology/features.jsonl.gz),
  [summary with every lost stellar ID](results_ls7h_morphology/summary.json),
  [paired stellar comparisons](results_ls7h_morphology/paired_signals.json)
- [Independent audit](results_ls7h_morphology/AUDIT.json) and
  [sealed output hashes](results_ls7h_morphology/SHA256SUMS)

Five analytical tests and the independent audit pass, including 14,160 direct
new fits, 52,413,240 alternative fits, all 36 core cells, all 360 background
cells and every changed decision. The published source freeze is
`503a159f7bc3337f314565fc4858d130a524626d`. LS7G's unchanged temporal and
covariance audit is reused by hash. No raw FITS recovery is needed to audit
LS7H. The figure is visually checked.

```sh
sha256sum -c LS7H_FREEZE.sha256
(cd results_ls7h_morphology && sha256sum -c SHA256SUMS)
OPENBLAS_NUM_THREADS=1 python scripts/ls7h_review.py
```

All historical LS outcomes and the M43 held-out panels remain unchanged.
PROJECT_STATUS.md is the maintained operational entry point. Continued code,
data and result publication to the science branch, plus main README updates,
remains authorized by PROJECT_DIRECTION.md.
