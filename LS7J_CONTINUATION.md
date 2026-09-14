# LS7J continuation — audited FAIL

Completed 2026-09-14.

LS7J completed **420 fixed native windows and 9,480 digital response rows** on the same twenty closed-sector contexts. The combined motion/outside-aperture correction has joint feasibility **FAIL**; the independent audit passes. There are no new detector decisions or added observing days.

The [completed limitation analysis](LS7J_LIMITATIONS.md) identifies the fixed motion response as the measured bottleneck. Combined native energy rises 45.74% and 34.51%, with zero improved backgrounds. Motion alone is almost as poor; the plane alone improves only five of ten backgrounds per sector. All required motion values are available and all pulse-protection gates pass, including broadened profiles with at most 0.365% distortion.

Close this fixed correction route. Next assess the provenance and calibration needed to map mission motion fields to these processed pixels: coordinates, reference frame, time averaging, response uncertainty and target-signal dependence. Identify a usable independent engineering source or calibrated response description before proposing a new joint detector study. That input is not yet established. No fitted sign, gain, delay or profile retry is appended to LS7J; unused sectors remain closed.

[Full result](results_ls7j_auxiliary/REPORT.md), [every failed response](results_ls7j_auxiliary/RESPONSE_FAILURES.md), [protocol](LS7J_AUXILIARY_PROTOCOL.md).

## Reproduce the fixed result

Install `requirements_ls7g.txt`; set `PYTHONPATH=src`, `OPENBLAS_NUM_THREADS=1` and `OMP_NUM_THREADS=1`. Run the evaluator into a new output path; it refuses to overwrite an existing result. The original two light-curve files are fetched and verified when missing from the cache.

```bash
python scripts/ls7j_auxiliary.py --cache data_ls7j_auxiliary --output /tmp/ls7j-reproduction
python scripts/ls7j_review_auxiliary.py --cache data_ls7j_auxiliary --output /tmp/ls7j-reproduction
```

A derived-only audit can omit `--cache`, but cannot replace the original raw-extraction audit. The committed result, source freeze, old baselines and historical ledgers stay unchanged. There is no unattended continuation scheduled between active sessions.

## Published checkpoint

Source freeze: `816a28f757e0da5ffe0f55ec56708b9f1ac3854b`.
Audited result: `52ef2780a374e1314252f8fe9f37d8fcae4d985f`.
[Execution 34819942153](https://github.com/andersenmartin-blip/setisearch/actions/runs/34819942153)
completed every step, including publication. All nineteen result-file hashes
match the retrieved package, and the comparison figure was visually checked.
The independent audit checks 96,240 raw auxiliary values, 594 operators,
60,312 unit-input columns, 420 native windows and 9,480 response rows.

The sealed summary retains its evaluator-stage `FEASIBILITY_EVALUATED_AWAITING_AUDIT`
label. The subsequent audit, report and successful workflow record completion;
that original stage label does not indicate pending work.
