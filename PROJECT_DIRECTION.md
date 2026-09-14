# Long-term project direction

Current operational status: [PROJECT_STATUS.md](PROJECT_STATUS.md).
The decisions below remain in force; dated milestones describe their original scope.

Owner decision, 5 September 2026: SETIsearch may be a multi-year project.
Resume the narrowband milestone track after LS6A; preserve LS as an open
research branch. A short run without a candidate is not a reason to abandon
a scientifically motivated search.

Progress is measured through validated methods, additional observing coverage,
reproducible negative results, and candidate follow-up. Milestone numbers and
event counts are not measures of evidence. Allow substantial engineering work
when it addresses a concrete limitation, and record why each stage was chosen.

Keep code, protocols, derived checkpoints, checksums and readable findings in
the public project repository. Keep earlier results and their original
denominators intact. Freeze scientific changes before new evaluation, distinguish
retrospective diagnostics from independent tests, and make restart points
explicit. Do not require a new permission merely to continue already authorized
analysis, publication or README commits. Martin retains project direction;
collaboration and delegation remain deferred.

Current track: M43 qualification of the support rule after M42. First establish
a reproducible baseline and explicit requirements across carrier, template,
integration and epoch axes. Repair an implementation error only if one is
demonstrated. A change in matching semantics needs its own named endpoint and
validation, followed by deterministic exhaustive real-data anchors before new
calibration. Preserve the completed LS6/LS6A results for later investigation.

Future LS return points include independently useful observations, better
conjunction qualification, or a separately scoped instrumental diagnostic.
There is no fixed calendar deadline for a discovery and no promise of
unattended computation between active sessions.

Working cadence, owner clarification after M43O: reduce the number of small
control milestones and approval stops. Combine related implementation,
known-answer tests and predeclared real-data anchors into larger useful steps.
Reuse completed evidence for unchanged arithmetic; repeat a large census only
when a concrete remaining risk requires it. Prioritize an integrated detector
and jointly planned null/native-injection calibration. Preserve prospective
scientific freezes and clear claim boundaries while simplifying the workflow.

Owner authorization, 7 September 2026: ongoing publication of SETI code,
experiment plans, results and logs, including M43T and subsequent milestones,
is approved for `andersenmartin-blip/setisearch` on
`m43-support-qualification`, with README updates on `main`.
This authorization does not require a fresh publication approval per milestone.
On 12 September 2026, the owner reaffirmed the public destination and explicitly
included all SETI files, LS7C, LS7D and M43AF code, experimental data, reports
and logs, together with README updates on main. This is the same ongoing
project publication scope; earlier upload-pending notes are historical.

Owner request, 12 September 2026: continue the optical LS investigation with TESS.

Implementation checkpoint: LS7's first mask failed contiguous-background
eligibility. LS7B repaired that coverage problem on a different L 98-59 sector,
but failed the fixed weak-glint recovery requirement after 420 digital trials.
LS7C completed 1,460 stronger trials on sector 32, but the new spatial method
failed recovery and compact-control rejection. LS7D now measures strong
cross-pixel cancellation missed by the diagonal spatial model. Develop a joint
covariance/residual method with broader nuisances on the closed sectors before
another independent evaluation.
Preserve all three closed experiments and the M43AI result; current details
remain in PROJECT_STATUS.md.

LS7E combined development is now complete on the ten closed sector 32
backgrounds. Covariance and a sparse residual option improve recovery and
reject the old compact controls, but weak-signal and broader-contamination
requirements still fail. Continue with a joint stellar/nuisance separation
study using the saved vectors, then a separately fixed transfer to another
already closed sector if justified. Preserve LS7E's 3,180 paired cases and all
prior outcomes; details remain in PROJECT_STATUS.md and LS7E_CONTINUATION.md.

13 September 2026: LS7F completed that separation study on the 3,180 saved
LS7E vectors. The original nuisance bank cannot meet all requirements at any
margin. The expanded bank has a development-feasible interval only at negative
margins, where a nuisance fit may be better than the stellar fit. No detector
is adopted. Next prepare a separately frozen transfer on already closed sector
29 with explicit training/eligibility, new nuisance controls, residual stress
and nonnegative-margin accounting. This remains development before any unseen
qualification. PROJECT_STATUS.md and LS7F_CONTINUATION.md carry the current
details; LS7C/LS7E records and M43 held-out panels remain unchanged.

13 September 2026: LS7G completed **3,540 fixed transfer trials** on the ten already closed sector-29 backgrounds. The primary joint descriptive gate **fails**. Nominal recovery at the fixed margin −1 is **37/40, 40/40, 40/40**; displaced recovery is **135/160, 153/160, 158/160**. **4/30** instrumental control cells exceed their allowance. The independent audit passes; no detector is adopted and no candidate is promoted.

Next, diagnose the failed transfer cells from the saved sector-29 extracts, keeping the frozen LS7G rule and outcomes unchanged. Separate temporal, source-score, residual and nuisance-separation losses before proposing another model or observing sector. Details: LS7G_CONTINUATION.md.

13 September 2026: LS7H completed the frozen diagnosis of all saved LS7G trials.
All 24 accepted focus controls switch to clean-margin rejection after the known
native contribution is removed. A 245-template extension reduces those
acceptances to nine, loses ten recovered stellar rows and still fails two
control cells, while all six signal cells pass. Continue with a joint model
of time-varying background and residual pixels using observable outside-event
samples, with combined planning for the two already closed sectors and full
signal protection. Truth-dependent subtraction is diagnostic only. No
threshold change or unseen sector follows automatically. PROJECT_STATUS.md
and LS7H_CONTINUATION.md carry the current result and concrete input needs.

13 September 2026: the owner asked to proceed with the two-week plan. LS7I
restored both closed-sector inputs, then froze and completed one protected
background predictor and static ablation. All 7,080 cases (6,720 historical
plus 360 separate sector-32 controls), 420 native prediction windows and the
independent audit are complete. The model fails six of twelve signal cells,
two of sixty control cells and both native-prediction gates. No detector is
adopted; unused sectors and M43 held-out panels remain closed.

The plan's negative-result branch is complete. Preserve this fixed model
outcome without a ridge/cut/bank retry. LS7I_LIMITATIONS.md accounts for
source-score losses and sector-dependent error calibration. The next proposed
direction is a separately specified study of additional observable instrumental
information, beginning with existing outside-aperture pixels and verified
image-motion/centroid fields on the same closed data. This is a research
proposal, not evidence those observables will succeed. Publication continues
under the existing standing authorization. Current restart instructions:
LS7I_CONTINUATION.md and TWO_WEEK_REPORT_2026-09-14.md.

14 September 2026: the owner asked to continue. LS7J completed the separately
frozen auxiliary-information study: 420 native windows, all 7,080 existing
recipes and 2,400 separate full-stamp response cases. Both sectors fail the
native correction requirements; combined residual energy increases 45.74%
and 34.51%, with no improved background aggregates. All motion inputs are
available and all pulse-protection requirements pass. The independent audit
and publication are complete. The fixed motion response, rather than missing
fields or downstream pulse removal, is the measured limitation.

Close LS7J without a gain, sign, delay or profile retry. Next assess the
documented response relationship between mission motion fields and the
processed short-cadence pixels, including uncertainty and target dependence.
Identify an independently useful engineering source or calibrated response
description before a new detector comparison; that input is not yet
established. Preserve the validated protected-plane building block without
adopting it as a detector. Current details: LS7J_LIMITATIONS.md and
LS7J_CONTINUATION.md. Unused sectors and M43 held-out panels remain closed.
