# LS7L continuation — engineering and phase inputs complete

Completed 14 September 2026. Start with [LS7L_FINDINGS.md](LS7L_FINDINGS.md)
and the [audited selected inputs](results_ls7l_inputs/REPORT.md).

## Resume the remaining physical-response work

1. Use the fifty original LS7K PRFs and LS7L's restored mission exporter/README.
   Trace the original characterized MATLAB products or a primary mission
   implementation to establish the absolute detector origin and physical
   source-phase orientation. The exporter copies ccdColumn/ccdRow without
   a shift and omits the prfRow/prfColumn arrays. This does not resolve the
   README's 44-column warning. Bound any additional original-model download
   before acquiring it; do not choose coordinates by fitting the native data.
2. Implement one calibrated PRF interpolation/translation family with known-answer
   tests for axis order, integer/subpixel motion, source normalization and the
   finite 11-by-11 science stamp. Preserve the measured 13-by-13 phase sums
   rather than silently renormalizing each phase. Include uncertainty images
   while distinguishing array uncertainty from sector-specific derivative error.
3. Use the 81,200 raw camera-4 quaternion rows and 8,020 verified coverage bins
   to specify finite exposure integration. Counts are ten per bin, but the
   ten 1.98-second frame integrations, readout phase, telemetry timestamp and
   POS_CORR estimator kernel are not interchangeable. The calendar evidence
   supports TDB numerically; exact sample timing/reference remains a model limit.
   Thermal channels are irregular sixty-second series, with gaps up to seven
   minutes; do not interpolate across them without a declared rule.
4. State how camera/SC quaternion components map to local detector motion and
   how DVA/thermal effects differ from rigid pointing. Guide membership, target
   exclusion and upstream pulse coupling are still unknown. Establish or bound
   them, or limit the benchmark's claims explicitly.
5. Freeze the complete response comparison before reading its native outcomes
   on the same twenty closed contexts. Combine implementation, meaningful
   known-answer checks, evaluation, independent audit and readable findings.
   Do not append an empirical gain/sign/lag/profile repair to LS7J.

No unused sector or M43 held-out panel is opened. Earlier counts and negative
results remain unchanged. Ongoing publication on the science branch and README
updates on main remain covered by the standing owner authorization.

## Restore and verify

The complete engineering source identities and original URLs are in
results_ls7l_engineering/sources.json. The full 1.41 GB sources are a reproducible
cache, not part of the Git payload. If the cache has expired, the selected-input
script restores exactly those files under the frozen per-file sizes and hashes.

Use Python 3.12.14 and requirements_ls7g.txt. The original scripts refuse to
overwrite completed results. To recompute the selections and audit, use an isolated checkout of the
selected-input source freeze, where results_ls7l_inputs does not yet exist:

~~~bash
git checkout 32a3840eba5325ed98a6e2b6597ac35a495615a3
python -m pip install -r requirements_ls7g.txt
python scripts/ls7l_extract_inputs.py
python scripts/ls7l_review_inputs.py
~~~

Use that checkout only for reproduction; active new work starts from the latest
science-branch head. The earlier schema run can be reproduced from its source
freeze af7266a9aef8cd8d398419c24b79f72bd746b8e1.

Audited selected-input result: 665d952f92e6b3687a4eb76976b87e8629db0014.
[Execution evidence](https://github.com/andersenmartin-blip/setisearch/actions/runs/34844802350).
No unattended continuation is scheduled between active sessions.
