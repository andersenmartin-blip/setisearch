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
