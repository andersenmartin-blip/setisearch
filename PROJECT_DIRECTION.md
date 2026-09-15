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


14 September 2026: LS7K completed the instrument-response provenance and
input assessment. Fifty original mission PRFs with uncertainty images and
8,020 reused timing rows are restored and audited. The exact old motion
values and historical manifests agree. Four matching engineering products
are listed; their time-series contents remain uninspected.

This establishes a mission-calibrated response family for the next integrated
coordinate/PRF forward-model benchmark on the same closed data. Combine
coordinate convention and phase/normalization checks with a bounded inspection
of the engineering files, exposure timing and explicit uncertainty/upstream
target dependence. Freeze any new response comparison before evaluation.
LS7K does not establish that the calibrated response will improve native
prediction. LS7J remains a closed negative result, with no gain/sign/lag/profile
retry; unused TESS sectors and M43 held-out panels remain closed.
Current findings: LS7K_INPUT_FINDINGS.md. Restart: LS7K_CONTINUATION.md.

14 September 2026: LS7L completed the bounded engineering acquisition,
closed-context extraction and PRF phase accounting. All 81,200 quaternion
rows, 30,594 thermal rows, 8,020 cadence coverage bins and 4,050 phase images
are published with a passing independent raw-byte audit. No cadence bin is
empty; all contain ten quaternion samples. The phase footprint deficit is at
most 0.405205%. Thermal gaps reach seven minutes.

The recovered exporter copies inherited MATLAB coordinate references without
an explicit shift and omits the original prfRow/prfColumn arrays; the
calibration-to-science origin remains unresolved. Continue with that coordinate
and phase definition, exposure integration, uncertainty and upstream target
dependence before freezing a native physical-response benchmark. The input
audit does not establish detector improvement. LS7J and all unused evaluation
panels remain unchanged. Current findings: LS7L_FINDINGS.md. Restart:
LS7L_CONTINUATION.md. Publication continues under the existing authorization.

14 September 2026: LS7M completed the calibrated PRF and finite-exposure
operator, ten known-answer tests, 4,050 phase reconstructions and 144 fixed
calibration-only cases. The independent original-MATLAB/SciPy/Simpson audit
passes with maximum absolute flux discrepancy 1.39e-16. Original relative axes
and FITS identity are established; absolute column origin remains unresolved.
Both declared origins, finite-stamp coverage and readout placement sensitivity
are reported without selecting on native outcomes.

Next establish the observable-to-pixel physical contract and freeze one native
response comparison on the same twenty closed contexts. Address quaternion
geometry, calibration's inherited pointing blur, exact sample/exposure timing,
supported footprint, uncertainty and upstream target dependence together.
Do not repeat completed numerical censuses without a concrete new risk. No
detector is adopted and unused panels remain closed. LS7J remains a fixed
negative result without an empirical gain/sign/lag/profile retry. Current
findings: LS7M_FINDINGS.md. Restart: LS7M_CONTINUATION.md. Standing publication
authorization continues.

14 September 2026: LS7N completed the separately fixed cadence-level calibrated
PRF/plane comparison. Its 420 native windows at both column conventions
(840 paired model rows) fail the joint native requirement: combined energy
rises 12.14–12.49% and too few backgrounds improve. All 12,600 downstream pulse
responses pass. The independent audit confirms all results and unchanged
historical inputs. This closes the exact cadence-level response family without
an empirical gain/sign/lag/profile repair; LS7J remains separately closed.

Next assess independently measured reference-star astrometry or documented
target-excluded motion with timing and uncertainty on these same pointings.
Availability is not established. Use metadata/geometry first, then freeze
bounded source identities and an integrated comparison only if a viable input
exists. If not, reconsider the optical data/product choice instead of another
local correction adjustment. No unused sector or M43 held-out panel is opened
and no detector is adopted. Current findings: LS7N_FINDINGS.md. Restart:
LS7N_CONTINUATION.md. Standing publication authorization continues.

14 September 2026: LS7O completes the reference-product assessment and its
separately frozen availability experiment. Twelve fast products from seven
stars supply 48,120 finite centroid/error rows with exact time joins and
disjoint masks. The requirement that all six references be QUALITY=0 through
every sideband blocks all 420 windows. Zero new corrections or pulse transfers
were measured; this is an eligibility obstruction, not a measured failure of
reference-driven PRF correction. The independent raw-row and quality/scope
audits pass, and earlier LS7J/LS7N outcomes remain unchanged.

Next establish a pixel-level quality, cosmic-ray and centroid-response contract
for the same fixed references, with a bounded pixel acquisition and integrated
endpoints specified together only if justified. The matching FAST-TP products
are identified but their pixel rows remain unread. Do not waive flags, drop
stars or retune the completed model to obtain a pass. If a usable contract
cannot be established, reassess optical products/instruments instead of another
local correction adjustment. No unused TESS or M43 panel is opened. Current
findings: LS7O_FINDINGS.md. Restart: LS7O_CONTINUATION.md. Standing publication
authorization continues.

14 September 2026, LS7Q: the bounded HiPERCAM metadata assessment identifies
XO-2b science run 5070352 and its calibration/QC provenance. Header-derived
channel timing is promising, but the raw-file transfer and calibration mapping
are not ready for a native pilot. The rs/NaI flat mismatch, slow-bias/fast-science
readout difference and invalid transport length are documented; no science
pixel was read. Next resolve the input package or assess actual CHEOPS product
metadata before freezing any new native comparison. Current restart:
LS7Q_CONTINUATION.md. The separate LS7P publication claim cannot currently be
verified beyond its public source freeze; recover the result evidence as
specified in LS7P_PUBLICATION_RECONCILIATION.md. Existing publication authority,
closed studies and reserved TESS/M43 panels are unchanged.

14 September 2026, LS7R: the planned secondary CHEOPS metadata assessment
establishes usable bounded delivery for CH_PR300024_TG000301_V0300 (55 Cnc),
with 3,024 raw imagettes, 432 subarrays and exact individual exposure metadata.
A timestamp-only pulse comparison quantifies stacking losses; no native pixel
response is measured. Calibration references are named, but their contents,
validity and imagette propagation still require checking. Next combine that
work with a single protected calibration/PSF/background and pulse/nuisance
response protocol before opening image arrays. Cosmic-ray and instantaneous
saturation handling must be explicit. Current restart: LS7R_CONTINUATION.md.
No detector, candidate or qualified observing coverage is added. LS7Q and
LS7P's separate evidence gap remain unchanged; existing publication authority
and reserved TESS/M43 panels continue.

15 September 2026: LS7S completes the retained CHEOPS visit's electronic-input
and reference audit. Exact archive rows are saved, the original gain reference
is verified from the official PIPE package, and selected metadata plus two
conditional gain expressions pass byte/scalar checks. All individual onboard
gain/bias entries are missing. Coaddition mapping, temperature convention and
the remaining references are not qualified. Keep the native input NOT_READY;
resolve the combined physical contract before freezing one protected native
pixel comparison. No candidate, source pulse recovery or coverage is added.
Current restart: LS7S_CONTINUATION.md. Standing publication authorization and
unused TESS/M43 boundaries remain unchanged.

15 September 2026, LS7T: the actual native HkExtended input is now retained.
The pinned PIPE gain function reads a separate CCD-voltage field; its native
result differs from the centered-temperature diagnostic by a median −0.57027%.
This refines, rather than reinterprets as a PIPE measurement, the older 8.129%
conditional comparison. CHEOPSim/common_sw disagree on the temperature sign.
The individual missing gain/bias coefficients belong to onboard nonlinearity;
NLIN_COR=false makes their inverse unnecessary on the declared native path.
Keep the remaining physical contract explicit, reuse the completed arithmetic,
and finish it before one integrated prospective native study. No science pixel,
candidate or qualified coverage is added. Current restart: LS7T_CONTINUATION.md.
