# LS7N continuation — fixed calibrated native response closed

Completed and independently audited 14 September 2026. Read
[LS7N_FINDINGS.md](LS7N_FINDINGS.md) and [the report](results_ls7n_response/REPORT.md).

## Decision and next useful work

The cadence-level calibrated PRF plus protected plane fails in both sectors
and at both declared column origins. Every model prediction is available and
downstream pulse protection passes. Close this family without changing its
gain, sign, lag, phase, reference astrometry, profile, rank cutoff or scoring
threshold on the completed native outcomes. The plane-only ablation is not
a jointly passing alternative. Preserve LS7J and LS7N as separate failures.

The next need is **independent reference-star astrometry and a response/error
description**, not another phase census or a locally adjusted correction.
First assess primary mission products and archive metadata for the same two
pointings and times. Seek either documented target-excluded motion estimates
with their temporal kernel/uncertainty, or simultaneous usable reference-star
pixels from which a separately specified independent estimator could be built.
This input is not yet established.

Keep that assessment bounded and useful:

1. Inspect available product identities, cadence, detector geometry, overlap
   and target isolation using metadata. Distinguish 20-second, 2-minute and
   full-frame cadence; slower data cannot validate unmeasured fast jitter.
   A full-frame reference may support only a slower common component.
2. Identify exactly which required relationship each prospective input can
   establish: pointing versus focus/deformation, guide/target membership,
   absolute reference position, estimator noise or processed-pixel response.
   A neighboring target is not automatically an independent guide estimate.
3. If a viable source exists, freeze file identities, size/row/download limits,
   reference-star eligibility, target exclusion, spatial/temporal mapping,
   fit exclusions and native endpoints together before acquisition/evaluation.
   Combine implementation, meaningful tests, comparison and audit into one
   substantive package. Do not choose reference stars by improving LS7N scores.
4. If the required input cannot be established, record that finding and
   reassess the optical data/product choice. Do not open unused sectors or
   M43 held-out panels as an automatic reaction to this failure.

The verified PRF interpolation, exposure arithmetic and protected-plane
building blocks remain reusable. Their correctness does not establish a
qualified detector or upstream pulse independence. No unattended continuation
is scheduled. Standing owner authorization covers work/publication on
m43-support-qualification and README updates on main without a fresh approval.

## Reproduction

Active work starts from the latest science-branch head. For reproduction only,
use an isolated checkout of source freeze
`07c6040715b8425a2051bfdbeb2806974f85d6c7`, where the result directory is absent:

~~~bash
git checkout 07c6040715b8425a2051bfdbeb2806974f85d6c7
python -m pip install -r requirements_ls7g.txt
PYTHONPATH=src python -m unittest discover -s tests -p test_ls7n_calibrated_motion.py -v
python scripts/ls7n_evaluate.py
python scripts/ls7n_audit.py
~~~

Recorded runtime: Python 3.12.14. Producer and audit reject overwriting completed
results. Exact input hashes are in config/ls7n_response.json. Native records,
pulse responses, source provenance and execution logs are published under
results_ls7n_response. No engineering/MATLAB cache download is required for
this reproduction. The later report generator only performs descriptive
arithmetic on completed outputs and does not create another response test.
