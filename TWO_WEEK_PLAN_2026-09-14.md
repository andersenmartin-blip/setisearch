# SETI work plan: 14–27 September 2026

Prepared 13 September 2026, following the completed LS7H result.
This is an operational work plan. The numerical specification for the next
experiment must still be frozen before its evaluation.

## Main objective

By the end of these two weeks, establish whether an observable, time-dependent
background/residual model can satisfy the joint optical signal and control
requirements on both already examined TESS sectors. Deliver a reviewed decision
on whether the method is ready for a limited qualification on unused data.

The useful outcome is either a demonstrably better method with a reproducible
qualification package, or a clear account of why this approach is insufficient
and what additional information would be needed. A discovery is not a scheduled
deliverable. Keep the work in the optical light-sail branch during this period.

## Starting evidence

LS7H re-examines 3,540 LS7G trials on ten sector-29 backgrounds. The one fixed
245-template extension reduces acceptances in four problematic control cells
from 24 to 9 but loses ten previously recovered stellar trial rows. All six
signal-recovery cells still pass. Two control cells fail: weak 2x2 patterns
(4/40 accepted) and weak triangles (3/40), each allowing at most 2/40.

Weak nominal recovery is 36/40, exactly its minimum, and weak displaced
recovery is 130/160, against a minimum of 128. All nine remaining focus-control
acceptances reuse two backgrounds. All 24 original focus acceptances become
margin rejections after removing the known native component at the same
window. That subtraction uses injection truth and is diagnostic only.

This motivates a background model inferred from observable surrounding
cadences. It does **not** demonstrate that those cadences can predict the
relevant fluctuation. Simply disabling the sparse-pixel option also fails
signal recovery. Earlier LS7G/LS7H results remain closed.

## Schedule and deliverables

The dates are planning windows for continued active work sessions and
explicitly started compute jobs. They do not imply unattended work has been
scheduled. Move a dependent stage if its prerequisite is delayed; do not
relax its scientific requirements to meet a date.

| Dates | Work | Concrete deliverable / exit condition |
|---|---|---|
| **14–15 September** | Assemble the time-resolved inputs for both closed sectors. Reuse sector 29's saved cubes; restore the original sector-32 products and eligibility by their recorded hashes. Recover the individual-cadence cutouts and check reconstruction of the existing event vectors. | A documented, restartable input package for both sectors, with source identities, aperture geometry, cadence masks and original trial links. A precise account of any missing input. |
| **16–18 September** | Implement one primary time-dependent background/residual model using samples outside a protected event interval. Fix training exclusions and regularization rules. Test pulse preservation, unpredictable noise, slowly changing backgrounds, disturbed pixels and context boundaries. Freeze the complete joint evaluation before scoring it. | Working model, analytical tests, a frozen protocol and executable evaluation for both sectors. Existing LS7G/LS7H rules are retained as references. |
| **19–20 September** | Run the integrated comparison on both closed sectors, including native background windows and all recoverable historical trial cases. Identify any missing control family before the freeze and include a separately declared supplement where needed. | First complete signal/control ledger and a week-one checkpoint: is the outside-event information useful, and which joint requirements still fail? |
| **21–23 September** | Independently audit the new arithmetic and decisions. Examine stability across backgrounds, pulse strengths, durations and displacements. Publish every additional stellar loss and all unsuccessful control cells. Resolve demonstrated implementation errors with an explicit correction record. | Audited joint result, comparison figures, reproducible code/data/logs and a written readiness decision. No further bank or threshold search is started as a late repair. |
| **24–25 September** | Follow the decision branch below. If the development and audit gates pass, freeze a limited qualification on a genuinely unused, eligible sector. If they fail, finish the limitation analysis and a concrete recommendation for the next information or method needed. | Either a fixed unused-data qualification package, with a pilot run if data and runtime permit, or a completed negative method result and a proposed next direction. |
| **26–27 September** | Review any completed qualification; preserve failures without retuning. Consolidate the scientific result and update the public overview and restart instructions. | A readable two-week report, final figures, complete published evidence and the next work queue. |

## Keep the model work focused

Use one primary background/residual model and the existing reference methods.
Any tuning rule must use only the declared training data, with its search space
and selection criterion fixed before evaluation. Event labels, the known
injected-only vector and the exact native realization under an injected pulse
must not be inference inputs.

Protect a declared interval around the putative pulse. Estimate global model
parameters without training on the assessed background; use local surrounding
samples only in the way explicitly allowed by the inference protocol. Account
for overlap between context windows. Test that the procedure preserves a
short pulse instead of fitting it away.

The saved historical ledgers contain **3,180 sector-32** and **3,540 sector-29**
rows, or **6,720 rows** to account for across the two archives. These are repeated
uses of twenty background contexts, not 6,720 independent observations. Keep
the original cohorts and denominators intact. Any missing shape-family
coverage or additional native controls need a named, predeclared supplement;
do not silently add those trials to a historical denominator.

Use the existing sector-specific apertures and source identities. Record
explicitly whether a new statistic changes temporal selection, covariance
construction, spatial fitting or decision semantics. Keep reference thresholds
unchanged; any new score or decision threshold needs its own named endpoint
and a prospective specification. Do not choose a margin from the final outcomes.

There is a time limit on this route: after the integrated result and audit,
make the decision. A further sequence of small, outcome-driven repairs is
outside this two-week plan. Reuse completed audits for unchanged arithmetic;
repeat work only for a concrete unresolved risk or required gate.

## Requirements for advancing to unused data

Advancement requires all of the following under the new frozen protocol:

1. **Correct inference:** the independent audit passes, and no injection truth
   or excluded event data enter training or prediction.
2. **Joint recovery and rejection:** the applicable signal and instrumental
   requirements pass on each closed sector, without averaging away a failing
   sector or cell. The current reference requirements include at least 90%
   nominal and 80% displaced recovery at each tested strength, and at most 5%
   acceptance in each core instrumental cell. Retain the other declared
   checks for fixed-flux pulses, nulls, matching, confounding and pointing.
3. **Explicit signal cost:** list every new lost stellar row, recovery headroom
   and residual-stress outcome. A better aggregate count does not conceal a
   sacrificed subgroup. Weak nominal recovery needs particular attention.
4. **Native-background evidence:** complete the predeclared checks on masked
   native windows and background stability. A better injection-only comparison
   does not by itself establish an operational false-alarm rate.
5. **Independent specification:** fix the new sector's eligibility, training
   boundary, trial/control set, stopping rules and candidate follow-up rules
   before examining its evaluation outcomes. Check that it has not already
   been used in project development.

A closed-sector pass is a prerequisite for this limited qualification, not
detector adoption or proof of calibrated false-alarm probabilities.

## Decision branches for the second week

| Outcome by 23 September | Action |
|---|---|
| Both closed sectors meet the joint requirements and the audit passes | Prepare the fixed unused-data qualification. Run a bounded pilot if acquisition and runtime fit the remaining window. Treat all results as qualification evidence before considering a wider search. |
| Controls improve but signal requirements fail, or one sector still fails | Publish the full tradeoff and identify the unresolved background/residual limitation. Recommend the specific extra information or alternative optical method worth pursuing. Keep unused qualification data closed. |
| Surrounding cadences cannot adequately predict the problematic component | Record this information limit, including how it was measured and where it applies. Do not present truth-dependent subtraction as a practical fix. |
| Input recovery or infrastructure prevents a complete joint evaluation | Preserve the validated work, exact missing inputs and restart command. Complete available engineering work, but do not label a partial single-sector run a joint pass. |

If a new qualification fails, keep that result sealed and include it in the
two-week report. If an interesting native event appears in an authorized pilot,
preserve its context and perform the predeclared instrumental/astrophysical
checks before promoting it. A TESS brightening alone cannot establish an
artificial source or a light-sail beam.

## Publication, communication and final package

Publish code, protocols, input checkpoints, result ledgers, audits, logs and
figures to `m43-support-qualification` under the owner's standing authorization;
update the overview on `main` at meaningful checkpoints. No repeated publication
approval is needed. Keep historical results and M43 held-out panels unchanged.

Provide substantial progress reviews around **20 September** and **27 September**
during active sessions. These are work checkpoints, not scheduled notifications.
Each review should state what the evidence changed, what still fails and the
next decision. Routine verification should not become separate milestones.

The final package should contain the restored input description, frozen method
and tests, the complete two-sector comparison, independent audit, signal-loss
ledger, readable figures, readiness decision and explicit restart instructions.
If a qualification was run, include its separate protocol and unchanged result.
Do not claim new observing coverage for reused data or physical laser sensitivity
from the digital injections alone.

## Project references

- [Current status](PROJECT_STATUS.md)
- [LS7H result and figure](results_ls7h_morphology/REPORT.md)
- [LS7H input needs and continuation](LS7H_CONTINUATION.md)
- [LS7G fixed sector-29 transfer](results_ls7g_transfer/REPORT.md)
- [LS7F sector-32 separation study](results_ls7f_separation/REPORT.md)
- [Owner direction and publication authorization](PROJECT_DIRECTION.md)
