# Long-term project direction

**Owner direction, 26 September 2026: ordinary radio SETI is active; LS is paused.
Start the new two-week plan and work as autonomously as possible.**

The [26 September–9 October plan](RADIO_TWO_WEEK_PLAN_2026-09-26.md) has now
started with a completed [integrated restart/metadata package](RADIO_RESTART_2026-09-26_RESULT.md).
The deterministic first pilot source is HD 1461 / HIP1499, cadence 71139, on an
observing date/session distinct from M43. All six current object/header
identities are verified, but comparison with the official catalogue exposes a
34.23-arcminute pointing discrepancy. **Spectral readiness is on hold pending
pointing provenance.** The bounded original-product catalogue diagnosis is
complete; it found no matching `.fil` or `.raw` original in that query scope.

Continue from the exact missing-information requirement in PROJECT_STATUS.md:
a same-scan original header/observing log or documented coordinate-conversion
provenance. Do not relabel metadata consistency as target confirmation, correct
coordinates to fit the catalogue, substitute another target automatically, or
open spectra before the integrated primary/control protocol. The live old M43
source entry point also needs a new target-bound interface; old source configs,
receipts, calibrations and closed scientific outcomes stay preserved.

The current HD 3651 catalogue check found only the original M33 cadence.
Preserve all 24 dedicated historical investigation cases, including unresolved
M15 GJ 581 and M33 HD 3651, all five non-redetections and M16's conservative
M35 count. The original M43AF 112+128 held-out inputs remain reserved.

LS remains at LS8BD–LS8BE and its period review; LS8BF is its exact saved restart,
not the current queue. All 16 unresolved LS events remain preserved, CHEOPS
calibration stays NOT_READY and its technical request stays UNSENT. Standing
research/publication authorization continues without repeated approval stops;
delegation remains deferred. Earlier dated directions below describe their
historical tracks and are superseded operationally by this radio status.

26 September 2026 review: the owner asked to continue the current plan after
its progress review. The original two-week plan had already completed its
negative-result branch on 13 September. A consolidated period review now
accounts for the follow-on work through LS8BD–LS8BE, including a pinned
23-cohort/49-representative ledger and the full 16-event unresolved register.
This is a synthesis of closed results, not a new numbered science experiment.
See [TWO_WEEK_REVIEW_2026-09-26.md](TWO_WEEK_REVIEW_2026-09-26.md).
The scientific queue remains LS8BF, rank-24 2MASS J11474440+0048164, under
LS8BE_CONTINUATION.md. No closed result is retuned; the 107-cohort order and
reserved panels stay fixed. Calibration remains NOT_READY and the external
technical request remains UNSENT. Standing publication authorization continues;
delegation remains deferred.

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

15 September 2026, LS7U: the fixed virtual prescan now supplies direct
562.089864 ADU/readout bias and 7.118046 ADU/readout effective noise. The CAL
bias difference exceeds descriptive sampling spread. A separately specified
exploratory check of PIPE's actual eight-column BlankLeft input does not
explain it and gives noise 7.024590 ADU/readout; CAL is 1.500584% higher.
Both array identities, all values, scalar calculations and clean offline
reproduction pass. Electronic-reference array bytes are now retained, while
target-image bytes, source trials, candidates and new qualified coverage
remain zero. Reuse these results. The next substantive step requires new
gain/gcoadd/offline/spatial-reference evidence, followed by one combined
prospective native study. Do not repeat margin estimators to match CAL or
create a checkpoint solely to restate unavailable inputs. Current restart:
LS7U_CONTINUATION.md. Existing publication authority and reserved-data
boundaries remain unchanged.

15 September 2026, LS7V: the original reduction log establishes that CAL/COR
bias and RON are the recorded defaults 563.43 and 7.13 ADU/frame. Their binary32
representations match the saved constants exactly. LS7U's discrepancies are
now understood as measurements compared with defaults; its measurements and
all earlier results remain unchanged. The executed module (14.0.1 within DRP
14.1.2) explicitly skips the spatial bias-frame correction, so the named
reference is not required to replay an unapplied correction. The dark MAP
was applied and still requires its exact content/applicability. Keep the
gain/gcoadd/offline and remaining spatial inputs explicit before the single
prospective native study. No new transfer, source pixel/trial, candidate or
coverage is added. Current restart: LS7V_CONTINUATION.md. Reuse the resolved
defaults and do not repeat margin or generic-source censuses. Standing
publication authorization and reserved TESS/M43 boundaries continue.

15 September 2026, operational follow-up after LS7V: two additional DRT/IASW
repository leads did not resolve the missing instrument documentation. A
complete technical request and exact input manifest are prepared in
CHEOPS_CALIBRATION_REQUEST.md and CHEOPS_REQUIRED_INPUTS.json. The verified
official contact has not been contacted; the draft is unsent and there is no
pending reply. The owner can send it or supply relevant documentation and the
exact files. The native study now explicitly depends on that external input.
Keep LS7V as the latest scientific checkpoint, with no new numbered milestone
for preparing a request. This does not expand the standing authorization to
person-directed contact. Current restart: LS7V_CONTINUATION.md.


19 September 2026, LS8B: the four visits selected at 45bf61f are fully evaluated
under the unchanged DEFAULT-L2 screen. There are seven positive clusters and
one negative control cluster over 7,917 eligible windows. The original audit
failed two near-zero excess comparisons; that failure is preserved. A separate
60-decimal reference verifies every threshold decision, and a subsequently
frozen flux-centered arithmetic implementation passes all 31,668 comparisons
at the unchanged tolerances on the already closed data. This is numerical
repair, not independent revalidation or detector qualification.

Next freeze a bounded auxiliary-column diagnosis for all eight representatives
using only the retained L2 tables. Keep both signs, original representative
windows and all earlier outcomes. Any subsequent image follow-up needs its own
exact scope. No additional visit, alternative aperture, original producer rerun
or unused TESS/M43 panel follows automatically. The raw-imagette calibration
gate and unsent technical request remain separate. Current continuation:
LS8B_CONTINUATION.md. Standing publication authorization continues.

19 September 2026, LS8C: the separately frozen auxiliary study is complete for
all eight LS8B representatives. All seven positive events coincide with large
smearing-column departures at a similar roll orientation; the negative control
does not share that event pattern. Sideband-only extrapolations do not provide
a reliable event correction. The independent audit passes 11,635 numerical
comparisons and 1,009 exact checks, while the original LS8B audit FAIL stays
unchanged. All eight remain L2_ONLY_UNRESOLVED; no new science bytes or images
were opened and no detector/candidate/qualified coverage is claimed.

Next prepare a single bounded CAL/COR image-and-correction study retaining
all eight fixed contexts and both signs. Establish metadata and exposure joins,
then freeze exact byte/row/pixel scope and stopping rules before image access.
Do not turn the observed smearing/roll pattern into a retrospective selection
cut. The separate raw-imagette gate and unsent request remain unresolved;
unused TESS/M43 panels and the earlier LS7X/Y/Z branches stay closed.
Current continuation: LS8C_CONTINUATION.md. Standing publication authorization
continues without a new per-milestone permission request.

20 September 2026, LS8D: the bounded paired CAL/COR image study is complete
for all eight fixed LS8B/LS8C representatives. Metadata and exposure joins were
frozen before image access; the run then acquired exactly 154,240,000 CAL/COR
image bytes plus 385,600 smearing-row bytes. All seven positive excursions and
the one negative control satisfy the same predeclared CORRECTION_LINKED rule in
both coordinate conventions. The independent audit passes 756,296 numerical
comparisons and 1,284,709 exact checks with zero disagreements.

This closes those eight 55 Cnc branches under the frozen stopping rule. The
label establishes material coupling to delivered CAL→COR processing, not a
unique instrumental cause and not artificial/astrophysical origin. Do not
widen the closed events, change apertures or add further 55 Cnc visits to seek
a different result. Next choose a new independent optical dataset/product by
a separately frozen metadata-only selection before opening new signal values.
Retain symmetric positive/negative controls and favor a delivered calibrated
product that supports bounded image follow-up. The separate raw-imagette gate
remains NOT_READY and its technical request is unsent. Current report:
results_ls8d_images/REPORT.md. Restart: LS8D_CONTINUATION.md. Standing
publication authorization continues.


20 September 2026, LS8J–LS8L: the bounded chronological CHEOPS census selected
WASP-189, and a separately dated complete-inventory reconciliation preserved
all 452 fresh product responses with unchanged 107-cohort order. The original
missing full-inventory evidence is disclosed, not reconstructed as original.
LS8K then screened both preselected visits (1,604 rows; 2,603 eligible windows),
with two positive clusters and one negative control; its independent audit passes.

The separately frozen LS8L image follow-up retained all three representatives.
The stronger positive is SPATIALLY_STRUCTURED, the negative control is
CORRECTION_LINKED, and the smaller positive stays UNRESOLVED_WITHIN_FIXED_SCOPE.
All 283,611 numerical and 481,739 exact image checks pass. No new detector,
SETI-candidate claim or qualified coverage is added. These labels are descriptive,
not unique physical-cause determinations.

Next freeze a bounded residual/noise study on the three already retained
contexts, with both signed comparison cases and signal-loss/control accounting.
The unresolved event's weak pure-brightness fit is not evidence for a stellar
pulse. Preserve original gates and outcomes without widening pixels, apertures
or visits. Current restart: LS8L_CONTINUATION.md. Existing publication authority,
raw-imagette gate and reserved TESS/M43 boundaries continue.

20 September 2026, LS8M: the prospectively frozen integrated residual/noise
study is complete on all three retained WASP-189 contexts. The smaller positive
has a compact COR residual: ten pixels carry 48.393–48.514% of weighted
residual energy, while total weighted residual/reference energy is only
1.10127–1.10616. Eight and seven of the 24 overlapping sideband controls are at
least as large in C0/C1. This does not establish that the entire selected event
is ordinary noise, nor does it identify a unique physical cause. Keep its
historical UNRESOLVED_WITHIN_FIXED_SCOPE label and both signed comparison labels.

All 288 held-sideband cases and 192 signed injections are retained. Eight
pre-analysis tests pass, as do 790,128 independent numerical comparisons and
911,228 exact checks. The hypothetical displacement removal has measured
brightness-signal loss and is not adopted. No new source bytes, pixels,
apertures, visits, classifier, qualified candidate or qualified coverage were
added. Stop the bounded WASP-189 saved-data branch here, without further tuning.

Next separately freeze metadata-first transfer to rank-2 GJ 1132 from the
unchanged reconciled LS8J ledger: CH_PR100041_TG000401_V0300 and
CH_PR100041_TG000403_V0300. Preserve the stable LS8K DEFAULT-L2 screen, both
signs and its audit. LS8M's weights and residual measures are not new selection
or veto criteria. Any image follow-up requires its own exact exposure/byte
freeze and retains all signed representatives. Current restart:
LS8M_CONTINUATION.md. Standing research/publication authorization continues;
the separate raw-imagette request remains unsent and reserved TESS/M43 panels
remain closed.

20 September 2026, LS8N–LS8O: rank-2 GJ 1132 has completed its metadata-first
independent transfer. The unchanged stable DEFAULT-L2 screen evaluated 615
rows and 699 eligible windows, with zero positive crossings and five negative
control clusters. All 8,388 independent L2 comparisons pass. Every negative
representative received its separately frozen CAL/COR image follow-up after
310 unique exposure joins. Nine synthetic tests and all 472,685 numerical /
802,983 exact image checks pass.

All five negative controls remain UNRESOLVED_WITHIN_FIXED_SCOPE. Complete
apertures and matching signs rule out missing coverage as the reason for this
label. No correction ratio reaches the fixed gate in both conventions. One
displacement fit is 79.74861% in C0 and 83.79823% in C1; preserve the failure
to pass both without rounding or choosing C1. Another event's signed
DELTA/COR changes from +0.37227 to -0.03201 across the same two conventions.
These are concrete coordinate/model limitations, not qualified candidates.

Next freeze one integrated diagnostic on the five retained 31-row contexts:
three-exposure-sum variability, residual structure, and explicit contributions
of the two existing apertures' boundary difference. Retain every control,
both coordinate conventions and both signs in synthetic signal-protection
tests. Do not reuse LS8M's single-row noise/control procedure without a newly
specified three-row treatment; do not derive a new veto from these closed
events. Keep original labels and thresholds and stop after the bounded study.
No new native pixels, rows, apertures or visits follow automatically.

Rank-3 HD 136352 stays next for a later independent metadata-first transfer;
the current continuation is LS8O_CONTINUATION.md. No qualified candidate,
detector or coverage is added. Existing publication authority continues.
Closed WASP-189, raw-imagette calibration boundaries, the unsent technical
request and reserved TESS/M43 panels remain unchanged.


20 September 2026: LS8P completes and closes the single bounded GJ 1132
retained-data follow-up. The three-row temporal covariance model and all
160 held-block cases quantify local variability without a calibrated
significance claim. Exact C0/C1 boundary accounting explains the previously
noted signed correction-budget change. All five original LS8O controls
remain unresolved, and LS8N still has zero positive crossings.

A hypothetical displacement-plus-constant subtraction loses 24–38% of
injected brightness flux and is not adopted. The initial audit serialization
failure is retained; a separately frozen NumPy-coordinate representation
repair passes the same independent audit, with no scientific arithmetic or
tolerance change and no producer rerun. All 320 signed controls are retained;
1,400,704 numerical comparisons and 1,529,059 exact checks pass. The verified
result is in results_ls8p_verified.

Continue with rank-3 HD 136352's unchanged chronological pair under separate
metadata/header and exact science-byte freezes. Use the original stable
DEFAULT-L2 screen, without transferring LS8P residual measures as cuts.
Do not reopen this bounded GJ 1132 study merely to improve closure or change
its coordinate convention. LS8P_CONTINUATION.md is the current restart point.
No qualified candidate, detector or observing coverage is added. The separate
raw-imagette calibration request remains unsent; reserved data stay closed.


20 September 2026, LS8Q–LS8R: the independent rank-3 HD 136352 pair is
complete and closed under the unchanged screen and image diagnostic.
The L2 result has zero positive threshold crossings in 1,923 eligible
overlapping windows. All three negative representatives pass the original
CORRECTION_LINKED gate in both coordinate conventions, with direct signed
DELTA/COR ratios 0.558559–0.813813. This describes coupling to delivered
processing, not one unique physical cause or the exclusion of source
variability. No new candidate, detector or coverage qualification follows.

Separate public freezes preceded headers, L2 values, image metadata and
exact image payload. Both stable L2 tests, nine image tests, all 23,076 L2
comparisons, 812 metadata checks and 283,611 numerical / 481,748 exact image
checks pass. All signed outcomes and figures are retained. No residual
study is required under the frozen all-events-closed branch; do not widen
the pair or tune its diagnostic simply to seek a physical explanation.

Next separately freeze rank-4 TESS_260647166 from the unchanged reconciled
LS8J chronology: CH_PR300046_TG000101_V0300 and CH_PR100031_TG015701_V0300.
These are CHEOPS products. Their existing ledger has NEXP=1 in both and
42-/49-second integrations respectively; verify each exact header before
freezing table ranges and transferring the original stable DEFAULT-L2
screen. Do not adopt image labels or previous weighted residual measures
as a new selection rule. LS8R_CONTINUATION.md is the current restart point.
Standing publication authorization continues; collaboration remains deferred.
Closed GJ 1132/WASP-189 work, reserved TESS/M43 panels and the unsent
raw-imagette calibration request remain unchanged.


20 September 2026, LS8S–LS8T: rank-4 TESS_260647166's independent CHEOPS
pair has completed its unchanged L2 screen and both signed image follow-ups.
The 1,747 rows provide 2,004 eligible overlapping windows: six positive
crossings in one cluster and two negative crossings in one cluster. Exact
42-/49-second exposure metadata and separate science-byte scopes were
verified before acquisition. The L2 audit passes all 24,048 comparisons.

The negative is SPATIALLY_STRUCTURED, with 92.95567% / 92.96205% COR
displacement explained energy. The positive remains UNRESOLVED_WITHIN_FIXED_SCOPE:
75.76422% / 75.77892% falls below the fixed 80% requirement in both conventions;
pure brightness explains about 2.7%. Neither correction gate passes. Complete
apertures and unique joins leave a model/residual limitation, not missing data.
The image audit passes 189,074 numerical comparisons and 321,180 exact checks;
nine synthetic tests pass. No qualified candidate, detector or coverage is added.

Next freeze one integrated retained-data study of the positive's residual
structure and local variability, preserving the original three-exposure
negative comparison. Specify duration-matched held controls, training rules,
appropriate temporal covariance for the three-row sum, both signed signal
controls and hypothetical signal-loss accounting before native evaluation.
Use only the two saved contexts and original apertures/conventions. Do not
change historical gates, remove pixels or adopt a new veto from the study.
Publish all outcomes and stop after that bounded follow-up; it has not yet
been executed. LS8T_CONTINUATION.md is the active restart point.

Rank-5 EC 12578-2107 remains the later independent target from the unchanged
reconciled ledger, requiring its own header/science freezes. Closed
HD 136352/GJ 1132/WASP-189 studies and reserved TESS/M43 data remain closed.
The raw-imagette calibration request remains unsent. Standing publication
authorization continues; collaboration remains deferred.

20 September 2026, LS8U: the single retained-data TESS_260647166 study is
complete and closed. The positive retains UNRESOLVED_WITHIN_FIXED_SCOPE:
its COR combined residual/reference energy is 3.77–3.80, with 1/24 held
single-row controls at least as large. The weighted residual is extended,
with only 6.47–7.03% in its top ten pixels. These dependent comparisons
are descriptive, not a calibrated significance or unique physical cause.
The negative remains SPATIALLY_STRUCTURED; its three-row residual/reference
energy is 0.705–0.723, with 6/8 held targets at least as large. Exact duration
and short-lag covariance propagation preserve both IID and correlated
references without changing the original screen or image gates.

All 18 pre-analysis tests, 583,488 numerical comparisons and 625,868 exact
checks pass. Both contexts, eight native product/convention cases, 128 held
cases and 128 signed controls are retained; no new archive bytes were
acquired. Hypothetical displacement subtraction loses 12.79–13.09% of
injected brightness flux in the positive and 7.31–7.84% in the negative,
so no correction or veto is adopted. Both figures were checksum verified
and visually inspected. No qualified candidate, detector or coverage is added.

The active next step is LS8V: separately freeze a metadata-first independent
transfer of the unchanged DEFAULT-L2 screen to rank-5 EC 12578-2107, exact
pair CH_PR100002_TG008901_V0300 and CH_PR100002_TG008902_V0300 from the unchanged
reconciled LS8J ledger. Verify both visits' headers and NEXP=1/60-second
ledger semantics before freezing exact table intervals and accessing science
values. Preserve both signs and independent audits. Do not adopt LS8U
residual ranks, rings or covariance ratios as new screening cuts. The rank-5
science values remain unopened. LS8U_CONTINUATION.md is the active restart
point; prior dated next actions are historical.

Do not extend or retune the closed TESS_260647166 pair merely to improve its
explanation. Closed HD 136352/GJ 1132/WASP-189 work and reserved TESS/M43 data
stay closed. The calibration gate remains NOT_READY and its technical
request remains unsent. Standing publication authorization continues;
collaboration and delegation remain deferred.


## 21 September 2026 — LS8V closed; proceed to rank-6 GJ 436

The rank-5 EC 12578-2107 pair completed its unchanged prospective DEFAULT-L2
screen: 174 rows, 201 eligible overlapping windows and zero positive or
negative threshold crossings. Both known-answer tests and 2,412 independent
numerical/discrete comparisons pass. The first pre-table TLS failure is
preserved; a separately frozen transport-only recovery obtained the same
exact inputs and passed without changes to scientific arithmetic or gates.
All 20 result files and 26 metadata files were checksum verified, and the
figure was visually inspected. No CAL/COR image follow-up is triggered.

Keep this pair closed, including its five later eligible visits. The active
next step is LS8W: separately freeze rank-6 GJ 436's exact chronological pair,
CH_PR100041_TG000302_V0300 and CH_PR100041_TG001301_V0300, for metadata/header
checks. Both ledger exposure tuples are NEXP=1 and 60 seconds; verify each
header before freezing exact DEFAULT-L2 ranges and opening values. Preserve
the unchanged screen, both signs and independent audit. Current restart:
LS8V_CONTINUATION.md. GJ 436 science values remain unopened.

This null is not a sensitivity, completeness or observing-coverage result.
The earlier TESS_260647166 positive remains unresolved and its study closed.
Other closed optical studies, M33 HD 3651, reserved TESS/M43 panels and the
unsent calibration request are unchanged. Standing research/publication
authorization continues; collaboration and delegation remain deferred.


## 21 September 2026 — LS8W–LS8X closed; proceed to rank-7 PG 1245-042

The rank-6 GJ 436 pair completed its unchanged prospective DEFAULT-L2
screen: 640 rows, 936 eligible overlapping windows, one positive crossing
and no negative crossing. The complete representative set received a
separately frozen image diagnostic after 58 unique metadata joins. Its
single 60-second positive TG000302_P0 is CORRECTION_LINKED: DELTA/COR is
-2.089268 / -2.001642, with matching positive COR signs and complete
apertures in both conventions. The correction reduces a larger positive
CAL residual; this is not a causal determination or a SETI detection.

The L2 audit passes 11,232 comparisons. All nine pre-pixel image tests and
the independent image audit pass: 94,537 numerical comparisons and 160,581
exact checks, no disagreements. The fixed scope acquires 88,320 table bytes,
18,560,000 image bytes and 46,400 smearing bytes. Both figures pass visual
inspection. Full workflow verification and the local-copy limitation for
two compressed inputs are explicitly recorded in the publication record.
No qualified detector, candidate or observing coverage is added.

Keep GJ 436 closed under the original stopping rule. The active next step
is LS8Y: separately freeze rank-7 PG 1245-042's chronological pair,
CH_PR100002_TG008601_V0300 and CH_PR100002_TG008602_V0300, for header-only
checks. Verify the ledger NEXP=1 and 60-second exposure tuples before
freezing exact DEFAULT-L2 table ranges and opening science values. Preserve
the unchanged signed screen and audit; do not transfer image correction
ratios as new L2 selection cuts. This pair's values remain unopened.
LS8X_CONTINUATION.md is the current restart point; earlier dated next actions
are historical.

The earlier TESS_260647166 positive remains unresolved and its bounded
study closed. Other closed optical studies, the M33 HD 3651 radio case,
reserved TESS/M43 panels and the unsent calibration request are unchanged.
The calibration gate remains NOT_READY. Standing research/publication
authorization continues; collaboration and delegation remain deferred.


## 21 September 2026 — LS8Y–LS8Z PG 1245-042 complete and closed

The rank-7 pair completes its unchanged prospective DEFAULT-L2 screen:
164 rows, 228 eligible windows, four negative crossings in one cluster and
no positive crossing. Its complete signed representative set receives the
separately frozen image diagnostic after 58 unique metadata joins.
The fixed image diagnostic classifies the negative event as
**CORRECTION_LINKED**. DELTA/COR is **+1.688786 / +1.717959** in the two
coordinate conventions, with complete apertures and negative COR signs
matching L2. The delivered correction reverses a positive CAL aperture
residual into a negative COR residual. The label describes material coupling
to processing; the responsible component and physical cause remain unassigned.

The L2 audit passes 2,736 comparisons; all nine pre-pixel image tests pass.
The independent image audit passes 94,537 numerical comparisons and
160,581 exact checks with no disagreements. Both figures are visually
inspected. Full workflow verification and the exact local-copy scope are
recorded in the publication record. No qualified candidate, detector or
observing coverage is added; no new correction or screening cut is adopted.

**Immediate next action: prepare LS8AA for rank-8 WASP-43**, beginning
with a separate exact-pair/header freeze for CH_PR100016_TG007801_V0300 and
CH_PR100016_TG007802_V0300. Verify their NEXP=1/60-second ledger exposures,
then freeze exact DEFAULT-L2 ranges and transfer the unchanged signed screen.
Those science values remain unopened. The PG 1245-042 pair is closed.

Current restart: LS8Z_CONTINUATION.md. Earlier dated next actions are
historical. TESS_260647166's positive remains unresolved and its bounded
study closed; GJ 436 remains closed under CORRECTION_LINKED. Other optical
studies, M33 HD 3651, reserved TESS/M43 panels and the unsent calibration
request are unchanged. Standing research/publication authorization continues;
collaboration and delegation remain deferred.


## 21 September 2026 — LS8AA–LS8AB WASP-43 complete and closed

The predetermined rank-8 CHEOPS pair supplied **271 rows and 294 eligible
overlapping windows**, with one positive crossing/cluster and no negative
crossing. TG007801_P0 is a 60-second exposure at zero-based row 62, score
**+9.486349813911296**, approximately 0.78% above its local L2 baseline.
Both visits have verified NEXP=1 and 60-second exposures. Scores are not
Gaussian significances.

The fixed image diagnostic classifies the positive event as
**CORRECTION_LINKED**. DELTA/COR is **-0.713546 / -2.797082** in the two
coordinate conventions, with complete apertures and positive COR signs
matching L2. The delivered correction reduces the positive aperture residual;
the amount is sensitive to the coordinate convention, while both satisfy the
original closure gate. The label describes material coupling to processing;
the responsible component and physical cause remain unassigned.

The L2 audit passes **3,528 comparisons**. Before pixels, image metadata
passes **58 unique joins and 269 exact checks**. All nine inherited image
tests pass; the independent image audit passes **94,537 numerical
comparisons and 160,581 exact checks**, zero disagreements. Both figures
were visually inspected. Exactly 37,398 L2 bytes, 18,560,000 image bytes and
46,400 smearing bytes were acquired. The publication record gives the exact
workflow and local verification scope. No qualified SETI candidate, detector
or observing coverage is added.

**Immediate next action: prepare LS8AC for rank-9 PG1303-114**, starting
with a separate exact-pair/header freeze for CH_PR100002_TG006401_V0300 and
CH_PR100002_TG006402_V0300. Verify the NEXP=1/60-second ledger exposures,
then freeze exact DEFAULT-L2 ranges and transfer the unchanged signed screen.
Those science values remain unopened; the cohort's three later eligible
visits stay outside scope. The WASP-43 pair is closed.


Current restart: LS8AB_CONTINUATION.md. Earlier dated next actions are
historical. No new correction or screening cut is adopted. The earlier TESS_260647166 positive remains UNRESOLVED_WITHIN_FIXED_SCOPE
and its bounded study closed. GJ 436 and PG 1245-042 remain closed under
CORRECTION_LINKED. Other closed optical studies and M33 HD 3651 are unchanged.
Reserved TESS/M43 panels remain closed. Calibration is NOT_READY and its
technical request unsent. Standing research/publication authorization
continues; delegation remains deferred.


## 22 September 2026 — PG1303-114 bounded study closed; proceed to PG 1207-033

The rank-9 CHEOPS pair supplied **165 rows and 222 eligible overlapping
windows**, with **zero positive crossings** and two negative crossings in
one cluster. TG006402_N0 is one 60-second exposure at zero-based row 21,
score **-10.531570808271077**, approximately 3.00335% below its local L2
baseline. Both visits have verified NEXP=1 and 60-second exposures.
Scores are not Gaussian significances.

The complete signed image follow-up leaves the negative
**UNRESOLVED_WITHIN_FIXED_SCOPE**. DELTA/COR is 0.304773/0.312012 and COR
displacement explained energy is 58.94%/58.68%, below the original gates in
both conventions. The subsequent separately frozen retained-data study finds
COR residual/reference energy **0.878666/0.876726**, with **20/24 and 19/24**
held single-row controls at least as large. The residual is not exceptional
in this fixed local comparison; these dependent counts are not p-values and
do not identify its cause. The original label remains unchanged.

Hypothetical displacement subtraction loses **38.17–38.23%** of injected
COR brightness flux and is not adopted. All four native cases, 96 held cases
and 64 signed controls are retained. The bounded study is closed without
a new correction, cut, qualified SETI candidate, detector or coverage claim.

All five workflows and the 5 transport / 2 L2 / 9 image / 18 residual tests
pass. The independent audits pass 2,664 L2 comparisons, 269 image-metadata
checks, 94,537 numerical / 160,581 exact image checks, then 305,356 numerical /
320,126 exact residual checks. All three figures were visually inspected.
Exactly 22,770 L2 bytes and 18,560,000 image plus 46,400 smearing bytes were
acquired; the residual study used no new archive bytes.

**Immediate next action: prepare LS8AF for rank-10 PG 1207-033**, starting
with a separate exact-pair/header freeze for CH_PR100002_TG000901_V0300 and
CH_PR100002_TG000902_V0300. Verify the NEXP=1/60-second ledger exposures,
then freeze exact DEFAULT-L2 ranges and transfer the unchanged signed screen.
Those science values remain unopened. PG1303-114's three later eligible
visits remain outside scope.

[Scientific interpretation and exact continuation](LS8AE_CONTINUATION.md),
[L2 report](results_ls8ac_l2_screen/REPORT.md),
[image report](results_ls8ad_images/REPORT.md),
[residual report and figure](results_ls8ae_residuals/REPORT.md),
[publication identities and verification](PUBLICATION_2026-09-22_LS8AC_LS8AE.md).

All earlier dated next actions below are historical. The active continuation
is LS8AE above. The prior TESS_260647166 positive remains unresolved and its
bounded study closed. Other closed studies and reserved TESS/M43 data remain
closed. Calibration is NOT_READY and its request unsent. Standing publication
authorization continues; delegation remains deferred.

## 22 September 2026 — LS8AF–LS8AH closed; proceed to rank-11 EC13080-1508

The rank-10 CHEOPS pair supplied **153 rows and 165 eligible overlapping
windows**, with six positive crossings in one cluster and no negative crossing.
TG000901_P0 is one 60-second exposure at zero-based row 60, score
**+141.1054591837304**, approximately 43.12658% above its local L2 baseline.
Both visits have verified NEXP=1 and 60-second exposures. Scores are not
Gaussian significances.

The fixed image diagnostic leaves the positive
**UNRESOLVED_WITHIN_FIXED_SCOPE**. DELTA/COR is 0.218211/0.314435 and COR
displacement explained energy 11.40%/16.23%, below the original gates in
both conventions. The figure shows an extended stripe crossing the upper
aperture edge. Its physical cause remains unassigned; the specific original
displacement-fit gate is not replaced by a visual morphology label.

The separately frozen retained-data study finds COR residual/reference energy
**278.663206/124.118239**, with **0/24 held controls as large** in each
convention. The fixed outer ring contains **98.39%/97.84%** of weighted
residual energy. These results describe a large, edge-dominated mismatch
with the local sideband model, not a calibrated probability or SETI detection.
Exact boundary accounting gives COR C1 minus C0 **-46,369.987482 ADU**.
Hypothetical displacement subtraction loses **42.99–43.53%** of injected
COR brightness flux and is not adopted. All four native cases, 96 held cases
and 64 signed controls are retained. The bounded study is closed and its
original unresolved label preserved, with no new cut, qualified candidate,
detector or coverage claim.

All five workflows and the 5 transport / 2 L2 / 9 image / 18 residual tests
pass. Independent audits pass 1,980 L2 comparisons, 269 image-metadata checks,
94,537 numerical / 160,581 exact image checks and 305,224 numerical /
320,118 exact residual checks. All three figures were visually inspected.
Exact acquisition was 21,114 L2 bytes and 18,560,000 image plus 46,400
smearing bytes; the residual study used no new archive bytes.

**Immediate next action: prepare LS8AI for rank-11 EC13080-1508**, starting
with a separate exact-pair/header freeze for CH_PR100002_TG005201_V0300 and
CH_PR100002_TG005202_V0300. Verify the NEXP=1/60-second ledger exposures,
then freeze exact DEFAULT-L2 ranges and transfer the unchanged signed screen.
Those science values remain unopened. The third eligible visit,
CH_PR100002_TG005203_V0300, stays outside this two-visit transfer.

[Scientific interpretation and exact continuation](LS8AH_CONTINUATION.md),
[L2 report](results_ls8af_l2_screen/REPORT.md),
[image report and figure](results_ls8ag_images/REPORT.md),
[residual report and figure](results_ls8ah_residuals/REPORT.md),
[publication identities and verification](PUBLICATION_2026-09-22_LS8AF_LS8AH.md).

All earlier dated next actions are historical. The active continuation is
LS8AH above. The prior TESS_260647166 positive and PG1303-114 negative retain
their unresolved labels and closed bounded studies. Other closed studies
and reserved TESS/M43 panels remain closed. Calibration is NOT_READY and
its request unsent. Standing publication authorization continues;
delegation remains deferred.


## 22 September 2026 — LS8AI–LS8AJ EC13080-1508 complete and closed

The predetermined rank-11 CHEOPS pair supplied **179 rows and 288 eligible
overlapping windows**, with four negative crossings in one cluster and no positive
crossing. TG005201_N0 is a 60-second exposure at zero-based row 65, score
**-13.17039181262956**, approximately 3.97253% below its local L2 baseline.
Both visits have verified NEXP=1 and 60-second exposures. Scores are not
Gaussian significances.

The fixed image diagnostic classifies the negative event as
**CORRECTION_LINKED**. DELTA/COR is **-3.380189 / -3.413528** in the two
coordinate conventions, with complete apertures and negative COR signs
matching L2. The delivered correction substantially reduces a larger CAL
deficit while leaving a negative COR residual. The label describes material
coupling to processing; the responsible component and physical cause remain
unassigned. No new correction or screening cut is adopted.

The L2 audit passes **3,456 comparisons**. Before pixels, image metadata
passes **58 unique joins and 269 exact checks**. All nine inherited image
tests pass; the independent image audit passes **94,537 numerical
comparisons and 160,581 exact checks**, zero disagreements. Both figures
were visually inspected. Exactly 24,702 L2 bytes, 18,560,000 image bytes and
46,400 smearing bytes were acquired. The publication record gives the exact
workflow and local verification scope. No qualified SETI candidate, detector
or observing coverage is added.

**Immediate next action: prepare LS8AK for rank-12 PG 1343-102**, starting
with a separate exact-pair/header freeze for CH_PR100002_TG008701_V0300 and
CH_PR100002_TG008702_V0300. Verify the NEXP=1/60-second ledger exposures,
then freeze exact DEFAULT-L2 ranges and transfer the unchanged signed screen.
Those science values remain unopened; the cohort's two later eligible visits
stay outside scope. The EC13080-1508 pair is closed, with its third visit
TG005203 outside the completed transfer.


Current restart: LS8AJ_CONTINUATION.md. Earlier dated next actions are
historical. No new correction or screening cut is adopted. The earlier TESS_260647166 positive remains UNRESOLVED_WITHIN_FIXED_SCOPE
and its bounded study closed. PG1303-114’s negative and PG 1207-033’s positive also retain their unresolved
labels and closed bounded studies. WASP-43, GJ 436 and PG 1245-042 remain
closed under CORRECTION_LINKED. Other closed optical studies and M33 HD 3651 are unchanged.
Reserved TESS/M43 panels remain closed. Calibration is NOT_READY and its
technical request unsent. Standing research/publication authorization
continues; delegation remains deferred.


## 22 September 2026 — LS8AK PG 1343-102 complete and closed

The predetermined rank-12 CHEOPS pair supplied **176 rows and 231 eligible
overlapping windows**, with **zero positive or negative threshold crossings
and zero clusters of either sign**. Both visits have verified NEXP=1 and
EXPTIME=TEXPTIME=60 seconds, pipeline 14.1.2. The unchanged screen uses
60/120/180-second events, 12-row sidebands, two-row guards and endpoints
+/-8.5. The pair is **COMPLETE_AUDITED and closed as a descriptive null**.

The null applies to the eligible windows. The second visit contains an early
STATUS=0 point at zero-based row 10, about 34.46% above the visit median.
It lacks the required left context for every tested event duration; it remains
in the retained table and figure. Its cause is unassigned. No edge rule is
changed and no image follow-up is triggered by this null result.

The five inherited transport tests and two stable L2 tests pass. The independent
audit passes **2,772 numerical/discrete comparisons**, with zero disagreements
at the unchanged tolerances. The figure was visually inspected. Exactly
**24,288 L2 science bytes** and no image bytes were acquired. All **62 new
scientific files** were locally verified against their published Git identities;
the four scientific commits change or remove no earlier file. Scores are not
Gaussian significances; no sensitivity, candidate, detector or qualified
observing-coverage claim is added.

**Immediate next action: prepare LS8AL for rank-13 HD 106315**, beginning
with a separate exact-pair/header freeze for CH_PR100041_TG000801_V0300 and
CH_PR100041_TG001401_V0300. Their ledger exposures are NEXP=1 and
EXPTIME=TEXPTIME=41 seconds, pipeline 14.1.2, and still require their own
header verification. Then freeze exact DEFAULT-L2 ranges and transfer the
unchanged one/two/three-row screen using each visit's verified cadence
(41/82/123 seconds if confirmed). Those science values remain unopened.
The two later eligible PG 1343-102 visits stay outside the closed pair.

[Scientific interpretation and exact continuation](LS8AK_CONTINUATION.md),
[L2 report and figure](results_ls8ak_l2_screen/REPORT.md),
[publication identities and verification](PUBLICATION_2026-09-22_LS8AK.md).

Earlier dated next actions below are historical. The active continuation is
LS8AK_CONTINUATION.md; the next stage is LS8AL.

The original 1,000-row census, 452 eligible visits and 107-cohort ordering
remain fixed. TESS_260647166's positive, PG1303-114's negative and
PG 1207-033's positive retain their unresolved labels and closed bounded
studies. EC13080-1508, WASP-43, GJ 436 and PG 1245-042 remain closed under
CORRECTION_LINKED. Other closed optical studies and M33 HD 3651 are
unchanged. Reserved TESS/M43 panels remain closed. Calibration is NOT_READY
and its technical request remains unsent. Standing research/publication
authorization continues; delegation remains deferred.


## 22 September 2026 — LS8AL–LS8AN HD 106315 complete and closed

The rank-13 CHEOPS pair supplied **2,382 rows and 4,698 eligible overlapping
windows**, with 13 positive crossings in three clusters and no negative
crossing. All three representatives are one 41-second exposure, with L2
scores **+44.503884, +9.691536 and +28.143189**, approximately 1.02026%,
0.24451% and 0.64634% above their respective local L2 baselines.
Scores are not Gaussian significances.

The complete image follow-up leaves all three
**UNRESOLVED_WITHIN_FIXED_SCOPE**. DELTA/COR magnitudes remain below the
original correction gate, and COR displacement explained energy is about
77.58%, 60.39% and 37.60–37.65%, below the original 80% gate in both
coordinate conventions. Physical causes remain unassigned.

The separately frozen retained-data study includes **12 native cases,
288 held cases and 192 signed controls**, using zero new archive bytes.
Its COR residual/reference ratios and local counts are:

- TG000801_P0: 20.138851/19.920447, with 0/24 and 0/24 held controls at least as large.
- TG000801_P1: 0.732455/0.741480, with 16/24 and 15/24 held controls at least as large.
- TG001401_P0: 0.832824/0.840364, with 15/24 and 15/24 held controls at least as large.

TG000801_P0 retains a large mismatch with its local residual/noise model;
none of its 24 held COR controls is as large in either convention. The other
two events do not stand out in this comparison, with 15–16 of 24 held COR
controls at least as large. These dependent counts are not probabilities and
do not establish a noise, astrophysical or artificial origin. All physical
causes remain unassigned. Hypothetical displacement-plus-constant subtraction
loses 7.01–13.12% of injected COR brightness flux across the three contexts
and is not adopted.

All five workflows and the 5 transport / 2 L2 / 9 image / 18 residual tests
pass. Independent audits pass **56,376** L2 comparisons, **803** image-metadata
checks, **283,611 numerical / 481,739 exact** image checks, and
**916,452 numerical / 960,362 exact**
residual checks, with zero disagreements. All seven figures were visually
inspected. Acquisition is exactly **328,716 L2 bytes, 55,680,000 image bytes
and 139,200 smearing bytes**. The bounded HD 106315 study is complete and
closed; all original labels remain unchanged, with no new correction,
screening cut, qualified candidate, detector or observing-coverage claim.

**Immediate next action: prepare LS8AO for rank-14 WASP-103**, beginning
with a separate exact-pair/header freeze for CH_PR100013_TG000101_V0300 and
CH_PR100013_TG000102_V0300. Verify their own NEXP=1, EXPTIME=TEXPTIME=60-second
ledger tuples and pipeline 14.1.2 before freezing exact DEFAULT-L2 ranges.
Transfer the unchanged signed one/two/three-row screen using each visit's
verified cadence. These science values remain unopened. The remaining nine
eligible WASP-103 visits stay outside the prospective pair.

[Scientific interpretation and exact continuation](LS8AN_CONTINUATION.md),
[L2 report and figure](results_ls8al_l2_screen/REPORT.md),
[image report and all three figures](results_ls8am_images/REPORT.md),
[residual report and all three figures](results_ls8an_residuals/REPORT.md),
[publication identities and verification](PUBLICATION_2026-09-22_LS8AL_LS8AN.md).

Earlier dated next actions below are historical. The active continuation is
LS8AN_CONTINUATION.md; the next stage is LS8AO.

The original 1,000-row census, 452 eligible visits and 107-cohort ordering
remain fixed. The HD 106315 pair's three positive labels stay unresolved and
its bounded study is closed. TESS_260647166's positive, PG1303-114's negative
and PG 1207-033's positive retain their unresolved labels and closed bounded
studies. EC13080-1508, WASP-43, GJ 436 and PG 1245-042 remain closed under
CORRECTION_LINKED; PG 1343-102 remains a closed descriptive null. Other closed
optical studies and M33 HD 3651 are unchanged. Reserved TESS/M43 panels stay
closed. Calibration is NOT_READY and its technical request remains unsent.
Standing research/publication authorization continues; delegation is deferred.


## 22 September 2026 — LS8AO–LS8AP WASP-103 complete and closed

The predetermined rank-14 CHEOPS pair supplied **565 rows and 804 eligible
overlapping windows**. The first visit has no signed threshold crossing; the
second has three positive crossings in one cluster and no negative crossing.
The sole representative, **TG000102_P0**, is row 274 of
CH_PR100013_TG000102_V0300: one 60-second exposure, L2 score **+13.672258**,
and **+1.301371%** above its local L2 baseline. Scores are not Gaussian sigma.

The complete paired-image follow-up classifies the event **CORRECTION_LINKED**.
Both coordinate conventions have complete apertures and positive COR sums
matching L2. The CAL event-residual aperture sum is approximately -91,100 ADU,
while COR is +18,550 ADU; DELTA=COR-CAL is about +109,650 ADU.
DELTA/COR is **5.906078 / 5.915583**, and the column-projected ratios are
**6.087909 / 6.093572**, above the pre-existing 0.5 correction gate in both
conventions. These are event-residual sums, not negative total stellar flux.
The label establishes substantial coupling to delivered processing; it does
not identify one physical correction component or exclude source variability.

All four workflows and the **5 transport / 2 L2 / 9 image tests** pass.
Independent audits pass **9,648 L2 comparisons**, **269 image-metadata checks**
and **94,537 numerical / 160,581 exact image checks**, with zero disagreements
at unchanged tolerances. Both figures were visually inspected. Acquisition is
exactly **77,970 L2 bytes, 18,560,000 image bytes and 46,400 smearing bytes**.
The WASP-103 pair is complete and closed under its fixed descriptive label;
no residual study is triggered. No qualified SETI candidate, detector,
sensitivity or observing-coverage claim is added.

**Immediate next action: prepare LS8AQ for rank-15 GJ 581**, beginning
with a separate exact-pair/header freeze for CH_PR100011_TG023701_V0300 and
CH_PR100018_TG008301_V0300. They are the first two of seven eligible visits.
Their ledger tuples are NEXP=1, EXPTIME=TEXPTIME=60 seconds and pipeline
14.1.2; verify each product's own identity, schema, rows and exposures before
separately freezing exact DEFAULT-L2 byte ranges. Transfer the unchanged
one/two/three-row signed screen and independent audit using the verified cadence.
GJ 581 science values remain unopened. The nine later eligible WASP-103 visits
stay outside the closed pair; no event in it becomes a new screening cut.

[Scientific interpretation and exact continuation](LS8AP_CONTINUATION.md),
[L2 report and figure](results_ls8ao_l2_screen/REPORT.md),
[paired-image report and figure](results_ls8ap_images/REPORT.md),
[publication identities and verification](PUBLICATION_2026-09-22_LS8AO_LS8AP.md).

Earlier dated next actions below are historical. The active continuation is
LS8AP_CONTINUATION.md; the next stage is LS8AQ.

The original 1,000-row census, 452 eligible visits and 107-cohort ordering
remain fixed. HD 106315 retains all three unresolved labels and its closed
bounded study. TESS_260647166's positive, PG1303-114's negative and
PG 1207-033's positive retain their unresolved labels and closed bounded
studies. EC13080-1508, WASP-43, GJ 436 and PG 1245-042 remain closed under
CORRECTION_LINKED; PG 1343-102 remains a closed descriptive null. Other closed
optical studies and M33 HD 3651 are unchanged. Reserved TESS/M43 panels stay
closed. Calibration is NOT_READY and its technical request remains unsent.
Standing research/publication authorization continues; delegation is deferred.


## 22 September 2026 — LS8AQ–LS8AS GJ 581 complete and closed

The predetermined rank-15 GJ 581 pair supplied **3,623 rows and 7,869
eligible overlapping windows**. The first visit has 30 positive crossings
in nine clusters and 16 negative crossings in five clusters; the second has
zero signed crossings in its 84 eligible windows. The original +/-8.5 scores
are not Gaussian significances, and the windows are not independent trials.

All 14 representatives completed paired-image follow-up: **nine
CORRECTION_LINKED** (four positive, all five negative), **three
SPATIALLY_STRUCTURED** (P2/P6/P8) and **two UNRESOLVED_WITHIN_FIXED_SCOPE**
(P3/P5). The complete positive IDs are prefixed TG023701_. The two-exposure
negative N1 is included and CORRECTION_LINKED; all other representatives
are one 60-second exposure. These labels describe processing or image fits,
without assigning unique physical causes or artificial origin.

The separately frozen retained-data study includes both unresolved events,
eight native product/convention cases, 192 held cases and 128 signed controls,
with **zero new archive bytes**. Its COR residual/reference ratios are
**1.179547 / 1.161620 for P3** and **3.192676 / 3.078003 for P5** (C0/C1).
For P3, **9/24 controls** are at least as large in both conventions. For P5,
the counts are **1/24 and 2/24**. P3 has several comparable or larger local
controls; P5 is larger than most, with some comparable or larger controls.
These dependent counts are not p-values or calibrated false-alarm rates.
Both causes remain unknown and both original unresolved labels are retained.
Hypothetical displacement-plus-constant subtraction loses **10.41–11.21%**
of injected COR brightness flux and is not adopted.

All five workflows and the **5 transport / 2 L2 / 11 image / 18 residual
tests** pass. Independent audits pass 94,428 L2 comparisons, 3,723 metadata
checks, 1,323,518 numerical / 2,248,091 exact image checks and 610,448
numerical / 640,222 exact residual checks, with zero disagreements at
unchanged tolerances. All 17 figures were visually inspected. The pair and
its single bounded study are complete and closed, preserving all 14 labels.
No new cut, subtraction, qualified candidate, detector, sensitivity or
observing-coverage claim is added.

**Immediate next action: prepare LS8AT for rank-16 EC14599-2047**,
the first two of three eligible visits: CH_PR100002_TG010301_V0300 and
CH_PR100002_TG010302_V0300. Their ledger tuple is NEXP=1,
EXPTIME=TEXPTIME=60 seconds and pipeline 14.1.2. Freeze the exact pair and
bounded header reader, independently verify each identity/schema/row count/
exposure, then separately freeze DEFAULT-L2 byte ranges before values.
Transfer the unchanged signed one/two/three-row scorer and independent audit
using the verified cadence. EC14599-2047 science values remain unopened;
TG010303 and the five later eligible GJ 581 visits remain outside their pairs.
No GJ 581 outcome becomes a new screening cut.

[Scientific interpretation and exact continuation](LS8AS_CONTINUATION.md),
[L2 report](results_ls8aq_l2_screen/REPORT.md),
[complete signed-image report](results_ls8ar_images/REPORT.md),
[bounded residual study](results_ls8as_residuals/REPORT.md),
[publication identities and verification](PUBLICATION_2026-09-22_LS8AQ_LS8AS.md).

Earlier dated next actions below are historical. The active continuation is
LS8AS_CONTINUATION.md; the next stage is LS8AT.

The original 1,000-row census, 452 eligible visits and 107-cohort ordering
remain fixed. WASP-103 remains closed under CORRECTION_LINKED; its nine later
visits stay outside its pair. HD 106315 keeps all three unresolved labels and
its closed bounded study. Earlier unresolved labels and closed studies,
including TESS_260647166, PG1303-114 and PG 1207-033, remain unchanged.
Other closed targets and reserved TESS/M43 panels stay closed. Calibration
is NOT_READY and its technical request remains UNSENT. Standing research and
publication authorization continues; delegation is deferred.

## 23 September LS8AT: EC 14599-2047 audited null within eligible windows

The predetermined rank-16 pair supplied **170 retained rows and 225 eligible
overlapping windows**, with **zero positive or negative threshold crossings
or clusters**. The first visit contributes 180 windows and the second 45.
Both verify NEXP=1, EXPTIME=TEXPTIME=60 seconds and pipeline 14.1.2. The
unchanged one/two/three-row screen, 12-row sidebands, two-row guards and
+/-8.5 endpoints remain fixed; scores are not Gaussian significances.

The complete figure retains a large STATUS=0 point at **zero-based row 86 of
TG010301**, **115.605933% above the visit median**. Only three rows follow
it, so it is in no eligible event window under the required right context.
Its cause is unassigned and it has no image classification. The null applies
to eligible windows, not every visible variation; no edge rule or follow-up
selection is changed.

Both workflows, all five transport tests and both stable L2 tests pass.
The independent audit passes **2,700 numerical/discrete comparisons**, with
zero disagreements at unchanged tolerances. The independent scalar header
reader verifies both schemas, identities, receipts, rows and exposure tuples.
All 64 scientific files match their published Git identities locally; all
50 header/science manifest entries pass SHA256 checks. The figure was visually
inspected. Acquisition is exactly 40,320 header bytes and 23,460 science-table
bytes, with zero image bytes. The pair is complete and closed as a descriptive
null; no image/residual follow-up, qualified candidate or detector is added.

**Immediate next action: prepare LS8AU for rank-17 LS IV +09 2**,
CH_PR100002_TG009301_V0300 and CH_PR100002_TG009302_V0300. Freeze the exact
pair and bounded header reader; independently verify each identity, schema,
rows and exposure tuple; then separately freeze DEFAULT-L2 byte ranges before
values. Their ledger tuple is NEXP=1, EXPTIME=TEXPTIME=60 s, pipeline 14.1.2.
Transfer the unchanged signed one/two/three-row scorer and scalar audit.
Those science values remain unopened; EC 14599-2047 TG010303 stays outside
its pair. No outcome here becomes a new screening cut.

[Scientific interpretation and exact continuation](LS8AT_CONTINUATION.md),
[L2 report and figure](results_ls8at_l2_screen/REPORT.md),
[publication identities and verification](PUBLICATION_2026-09-23_LS8AT.md).

Earlier dated next actions below are historical. Active continuation:
LS8AT_CONTINUATION.md; next stage: LS8AU. The original census and 107-cohort
order stay fixed. GJ 581 keeps all 14 labels, including its two unresolved
events, and its closed bounded study. All other earlier labels and studies
are unchanged. Reserved TESS/M43 panels remain closed. Calibration NOT_READY;
technical request UNSENT. Standing research/publication authorization continues;
delegation is deferred.

## 23 September LS8AU: LS IV +09 2 audited null within eligible windows

The predetermined rank-17 pair supplied **212 retained rows and 123 eligible
overlapping windows**, with **zero positive or negative threshold crossings
or clusters**. The first visit contributes 21 windows and the second 102.
Both verify NEXP=1, EXPTIME=TEXPTIME=60 seconds and pipeline 14.1.2. The
unchanged one/two/three-row screen, 12-row sidebands, two-row guards and
+/-8.5 endpoints remain fixed; scores are not Gaussian significances.

Four flagged rows per visit and cadence gaps restrict eligible event rows
to 29–35/81–82 in TG009301 and 14–18/48–78 in TG009302 (zero-based).
The largest displayed points, first-visit row 43 and second-visit row 86,
are 9.674890% and 12.248097% above their visit medians. Neither occurs in an
eligible event window: its required right context encounters flags/gaps.
Causes remain unassigned. The null applies to the 123 eligible windows,
not every visible variation. No eligibility or follow-up rule is changed.

Both workflows, all five transport tests and both stable L2 tests pass.
The independent audit passes **1,476 numerical/discrete comparisons**, with
zero disagreements at unchanged tolerances. Separate scalar header checks
verify both complete schemas, identities, receipts, exposures and boundaries.
All 64 scientific files match their published Git identities locally; all
50 header/science manifest entries pass SHA256. The figure was visually
inspected. Acquisition is exactly 40,320 header bytes and 29,256 science-table
bytes, with zero image bytes. The pair is complete and closed as a descriptive
null. No image/residual follow-up, qualified candidate or detector is added.

**Immediate next action: prepare LS8AV for rank-18 GJ 9404**,
CH_PR100018_TG007301_V0300 and CH_PR100018_TG007302_V0300, the first two of
three eligible visits. Freeze the exact pair and bounded header reader;
independently verify each identity, schema, rows and exposure tuple; then
separately freeze DEFAULT-L2 source identities and ranges before values.
Their ledger tuple is NEXP=1, EXPTIME=TEXPTIME=60 s, pipeline 14.1.2.
Transfer the unchanged signed screen and independent scalar audit. These
science values remain unopened; TG007303 stays outside the prospective pair.

[Scientific interpretation and exact continuation](LS8AU_CONTINUATION.md),
[L2 report and figure](results_ls8au_l2_screen/REPORT.md),
[publication identities and verification](PUBLICATION_2026-09-23_LS8AU.md).

Earlier dated next actions below are historical. Active continuation:
LS8AU_CONTINUATION.md; next stage: LS8AV. The original census and 107-cohort
order stay fixed. All earlier labels, closed studies and reserved TESS/M43
panels remain unchanged. Calibration NOT_READY; technical request UNSENT.
Standing research/publication authorization continues; delegation deferred.

## 23 September LS8AV: GJ 9404 audited null within eligible windows

The predetermined rank-18 pair supplied **145 retained rows and 150 eligible
overlapping windows**, with **zero positive or negative threshold crossings
or clusters**. The first visit contributes 90 windows and the second 60.
Both verify NEXP=1, EXPTIME=TEXPTIME=60 seconds and pipeline 14.1.2.
The unchanged one/two/three-row rule, 12-row sidebands, two-row guards and
+/-8.5 endpoints remain fixed; scores are not Gaussian significances.

First-visit eligible event rows are 14–44. Second-visit flags at rows 37/44
and gaps after 36/43 restrict eligible event rows to 14–22 and 59–71.
Indices are zero-based. The visible large dip at second-visit row 44 is
33.149963% below its visit median and has STATUS=1; it remains retained but
fails the original eligibility rule. Display extrema near edges or flagged
gaps are not reselected. The null applies to the 150 eligible windows, not
every retained variation. No eligibility or follow-up rule is changed.

Both workflows, all five transport tests and both stable L2 tests pass.
The independent audit passes **1,800 numerical/discrete comparisons**, with
zero disagreements at unchanged tolerances. Separate scalar header checks
verify full schemas, identities, receipts, exposures and byte boundaries.
All 64 scientific files match public Git identities locally; all 50 header/
science manifest entries pass SHA256. The complete figure was visually
inspected. Acquisition is exactly 40,320 header bytes and 20,010 science-table
bytes, with zero image bytes. The pair is complete and closed as a descriptive
null; no image/residual follow-up, qualified candidate or detector is added.

**Immediate next action: prepare LS8AW for rank-19 EC14338-1445**,
CH_PR100002_TG006601_V0300 and CH_PR100002_TG006602_V0300. Freeze the exact
pair and bounded header reader; independently verify each identity, full
schema, rows and exposure tuple; then separately freeze DEFAULT-L2 source
identities and byte ranges before values. The ledger tuple is NEXP=1,
EXPTIME=TEXPTIME=60 s, pipeline 14.1.2. Transfer the unchanged signed screen
and scalar audit. These science values remain unopened. GJ 9404 TG007303
stays outside its closed pair; no outcome here becomes a new screening cut.

[Scientific interpretation and exact continuation](LS8AV_CONTINUATION.md),
[L2 report and figure](results_ls8av_l2_screen/REPORT.md),
[publication identities and verification](PUBLICATION_2026-09-23_LS8AV.md).

Earlier dated next actions below are historical. Active continuation:
LS8AV_CONTINUATION.md; next stage: LS8AW. The original census and 107-cohort
order stay fixed. Earlier null scopes, unassessed points, unresolved labels,
closed studies and reserved TESS/M43 panels are unchanged. Calibration
NOT_READY; technical request UNSENT. Standing research/publication authorization
continues; delegation is deferred.

## 23 September LS8AW: EC14338-1445 audited null within 63 eligible windows

The predetermined rank-19 pair supplied **159 retained rows and 63 eligible
overlapping windows**, with **zero positive or negative threshold crossings
or clusters**. The first visit contributes 60 windows and the second only
three (two one-row, one two-row, no three-row windows). Both verify NEXP=1,
EXPTIME=TEXPTIME=60 seconds and pipeline 14.1.2. The unchanged one/two/three-row
rule, 12-row sidebands, two-row guards and +/-8.5 endpoints remain fixed;
scores are not Gaussian significances.

First-visit eligible event rows are 14–33/63–64; flag 48 and a gap after 47
restrict eligibility. Second-visit flags 30/54 and a gap after 29 restrict
eligible event rows to **14–15**. Indices are zero-based. The second visit's
large retained maximum at row 23 (265.563670273 times the visit median) and
minimum at row 55 (-184.068365878 times median) have STATUS=0 but fail the
original context rule. Their causes remain unassigned; they are not tested
detections or image-classified events. The full plot retains them. The null
applies to the 63 eligible windows, not every retained variation. No mask,
threshold or follow-up selection changes.

Both workflows, all five transport tests and both stable L2 tests pass.
The independent audit passes **756 numerical/discrete comparisons**, with
zero disagreements at unchanged tolerances. Separate scalar header checks
verify full schemas, identities, receipts, exposures and byte boundaries.
All 64 scientific files match public Git identities locally; all 50 header/
science manifest entries pass SHA256. The full figure was visually inspected.
Acquisition is exactly 40,320 header bytes and 21,942 science-table bytes,
with zero image bytes. The pair is complete and closed within its eligible
scope; no image/residual follow-up, qualified candidate or detector is added.

**Immediate next action: prepare LS8AX for rank-20 GJ 536**,
CH_PR100011_TG023501_V0300 and CH_PR100018_TG007801_V0300, the first two of
five eligible visits. Freeze the pair and bounded header reader; independently
verify each identity, full schema, rows and exposure tuple; then separately
freeze DEFAULT-L2 source identities and byte ranges before values. Ledger
NEXP=1, pipeline 14.1.2, with exposures approximately **40.17 and 40.20 seconds**.
Use each independently verified cadence; do not inherit 60 seconds. Transfer
the unchanged signed screen and scalar audit. GJ 536 science values remain
unopened; its three later eligible visits remain outside the selected pair.

[Scientific interpretation and exact continuation](LS8AW_CONTINUATION.md),
[L2 report and figure](results_ls8aw_l2_screen/REPORT.md),
[publication identities and verification](PUBLICATION_2026-09-23_LS8AW.md).

Earlier dated next actions below are historical. Active continuation:
LS8AW_CONTINUATION.md; next stage: LS8AX. The original census and 107-cohort
order stay fixed. Earlier null scopes, unassessed points, unresolved labels,
closed studies and reserved TESS/M43 panels are unchanged. Calibration
NOT_READY; technical request UNSENT. Standing research/publication authorization
continues; delegation is deferred.

## 23 September LS8AX–LS8AZ: GJ 536 pair and bounded study closed

The predetermined rank-20 pair supplied **4,254 retained rows and 10,215
eligible overlapping windows**. Its 38 positive and five negative crossings
form eight positive clusters and one negative cluster. All nine signed
representatives completed image follow-up: **three CORRECTION_LINKED, four
SPATIALLY_STRUCTURED and two UNRESOLVED_WITHIN_FIXED_SCOPE (P1/P6)**.
Labels describe processing and fits without assigning unique physical causes.
Both visits verify NEXP=1 and pipeline 14.1.2; their own exposure/cadence values
are **40.1699981689453 and 40.2000007629395 seconds**. The unchanged signed
one/two/three-row rule and +/-8.5 endpoints remain fixed. Scores are not
Gaussian significances and windows are not independent trials.

The complete unresolved set received one separately frozen retained-data
study: eight native product/convention cases, 192 held cases and 128 signed
controls, **zero new archive bytes**. P1's COR residual/reference ratios are
**0.257893 / 0.263414**, with **23/24** local controls at least as large in
both center conventions. P6's ratios are **3841.994548 / 3951.598570**, with
**0/24** at least as large. These dependent counts are not p-values.

**P6's very large peak coincides with a broad oblique bright band crossing
the saved subarray and aperture in CAL and COR; broad signed structure remains
after fitting.** This is a severe mismatch with the local model/reference,
not evidence establishing a clean point-source brightening or a SETI signal.
P1's low residual does not prove ordinary noise. Both original unresolved
labels remain. Hypothetical subtraction loses 10.97–11.48% of injected COR
brightness flux and is not adopted. The pair and this single bounded study
are closed without additional GJ 536 tuning or a qualified candidate/detector.

The largest retained point, row 3408, is P6 and received every prescribed
follow-up. A separate first-visit point at row 1977 is approximately 51.10%
above its STATUS=0 visit median but has STATUS=1 and no eligible event window;
it remains retained and unassessed. All rows and eligible intervals are
documented. Display variation is not qualified observing coverage.

All five data-reading/analysis workflows succeed; the initial AX checkout
attempt timed out before archive access and is preserved with its prospective
recovery. The 5 transport / 2 L2 / 11 image / 18 residual tests pass.
Independent audits pass **122,580 L2 comparisons**, **2,393 metadata checks**,
**850,833 numerical / 1,445,201 exact image checks** and **610,586 numerical /
640,224 exact residual checks**, with zero disagreements. All **309 new
scientific files** match public Git identities locally, all 272 manifest
entries pass SHA256, and all 12 figures have been visually inspected.

**Immediate next action: prepare LS8BA for rank-21 2MASS J11285624+1010395**,
CH_PR100018_TG010801_V0300 / CH_PR100018_TG010802_V0300. These are both eligible
visits in the fixed ledger; NEXP=1, EXPTIME=TEXPTIME=60 seconds and pipeline
14.1.2 remain subject to their own header verification. Freeze bounded headers,
audit identity/schema/exposure, then separately freeze exact L2 ranges before
values. Transfer the unchanged screen and audit. Its science values remain
unopened. GJ 536's three later eligible visits remain outside the closed pair.

[Scientific interpretation and exact continuation](LS8AZ_CONTINUATION.md),
[L2 report](results_ls8ax_l2_screen/REPORT.md),
[complete signed-image report](results_ls8ay_images/REPORT.md),
[bounded residual study](results_ls8az_residuals/REPORT.md),
[publication and verification](PUBLICATION_2026-09-23_LS8AX_LS8AZ.md).

Earlier dated next actions are historical. Active continuation:
LS8AZ_CONTINUATION.md; next stage: LS8BA. The original census and 107-cohort
order, prior labels, unassessed points, closed studies and reserved TESS/M43
panels remain unchanged. Calibration NOT_READY; technical request UNSENT.
Standing research/publication authorization continues; delegation is deferred.

## 23 September LS8BA–LS8BB: 2MASS J11285624+1010395 pair closed

The predetermined rank-21 pair supplied **97 retained rows and 90 eligible
overlapping windows**. Six positive crossings form one cluster and three
negative crossings form one cluster. Both signed representatives completed
image follow-up and are **CORRECTION_LINKED** under the unchanged two-convention
gate. No event is unresolved, so no residual study is triggered. The pair is
closed without a qualified candidate, detector, sensitivity or coverage claim.

Both visits independently verify NEXP=1, EXPTIME=TEXPTIME=60 seconds and pipeline
14.1.2. The first visit has 59 rows and 90 eligible windows; the second has
38 rows and **zero eligible windows, providing no tested null**. The original
one/two/three-row rule and +/-8.5 endpoints remain fixed. Scores are not Gaussian
significances and overlapping windows are not independent trials.

The representatives are adjacent first-visit rows 25 (score **+65.277456**,
local excess **+8.778835%**) and 24 (**-35.043142**, **-4.788958%**). They occur
in each other's original guards and share 28 context rows. Their 58 row
occurrences cover 30 distinct exposures; 116 CAL/COR join occurrences cover
60 distinct product exposures. They are not independent replication. Every
shared CAL/COR/smearing row is verified byte-identical.

DELTA/COR ratios are **-1.485049 / -1.534163** for P0 and
**+9.886640 / +9.536732** for N0 (C0/C1). Both pass the correction gate first.
Displacement fits also exceed the later spatial gate, without changing the
fixed classification. Smearing fits are rank deficient. The maps show broad
processing differences and signed source structure; no unique physical cause
or artificial origin is established, and source variability is not excluded.

The first visit's last point, row 58, is **8.758721% above its STATUS=0 visit
median**, but lacks an eligible complete context and remains unassessed. All
97 points and every eligible window remain preserved. The second visit's gaps
and flagged rows prevent any complete test context. Display variation is not
qualified observing coverage.

All four data-reading/analysis workflows and the retained verification workflow
succeed. The 5 transport / 2 L2 / 11 image tests pass. Independent audits pass
**1,080 L2 comparisons**, **534 metadata checks**, and **189,074 numerical /
321,158 exact image checks**, with zero disagreements. All 175 added
scientific/verification files are public; 171 match public Git identities
locally. Four large compressed CAL/COR files are verified by the independent
image and retained CI audits but were not downloaded locally. Of 143 manifest
entries, 139 are recomputed locally and four pass those published CI checks.
All six payload receipts and all three exact overlap checks pass; all four
figures have been visually reviewed. The optional artifact uploaded, but its
local download returned HTTP 403 and no local ZIP verification is claimed.

**Immediate next action: prepare LS8BC for rank-22 GJ 422**, exact pair
CH_PR100018_TG012201_V0300 / CH_PR100018_TG012202_V0300. These are both eligible
visits in the fixed ledger. NEXP=1, EXPTIME=TEXPTIME=60 seconds and pipeline
14.1.2 remain subject to their own header checks. Freeze bounded headers,
independently verify identity/schema/exposure, then separately freeze exact
L2 ranges before values. Transfer the unchanged screen and audit. GJ 422
science values remain unopened.

[Scientific interpretation and exact continuation](LS8BB_CONTINUATION.md),
[L2 report](results_ls8ba_l2_screen/REPORT.md),
[complete signed-image report](results_ls8bb_images/REPORT.md),
[readable unchanged-map overview](verification_ls8bb_retained/paired_image_review.png),
[publication and verification](PUBLICATION_2026-09-23_LS8BA_LS8BB.md).

Earlier dated next actions are historical. Active continuation:
LS8BB_CONTINUATION.md; next stage: LS8BC. The original census and 107-cohort
order, prior labels, unassessed points, closed studies and reserved TESS/M43
panels stay unchanged. GJ 536's P1/P6 keep their unresolved labels and its one
bounded study stays closed. Calibration NOT_READY; technical request UNSENT.
Standing research/publication authorization continues; delegation is deferred.

24 September 2026: LS8BC closes the predetermined rank-22 GJ 422 pair with
97 retained rows, 75 eligible overlapping windows and no signed threshold
crossings. Both workflows and the 900-comparison independent audit pass.
The null is limited to eligible contexts; the flagged 22.091280% display dip
and other unassessed points remain preserved. No image/residual branch is
triggered. Next prepare LS8BD for rank-23 GJ 494, only chronological first
pair CH_PR100018_TG007401_V0300 / CH_PR100018_TG007402_V0300, using its own
header-verified cadence (ledger 42 seconds). Its other two visits remain
outside the pair. Own-header verification and a separate exact L2 freeze
precede values. All prior labels, closed studies, census/cohort order and
reserved TESS/M43 panels remain unchanged. See LS8BC_CONTINUATION.md.
Calibration NOT_READY; request UNSENT. Publication authorized; delegation
deferred.

24 September 2026: LS8BD–LS8BE closes the predetermined rank-23 GJ 494 first
pair and the complete signed follow-up. The 148 rows supply 165 eligible
windows and one positive representative, CORRECTION_LINKED under the fixed
gate. Independent L2, metadata and image audits pass. No unresolved event
remains and no residual study is triggered. The second visit's unassessed
row-13 maximum and both later visits remain outside follow-up. Next prepare
LS8BF for rank-24 2MASS J11474440+0048164, exact pair
CH_PR100018_TG007101_V0300 / CH_PR100018_TG007102_V0300. Verify own headers
before its separate L2 freeze and use each verified cadence (ledger 60
seconds). Prior labels, unassessed points, closed studies, cohort order and
reserved TESS/M43 panels remain unchanged. See LS8BE_CONTINUATION.md.
Calibration NOT_READY; request UNSENT. Publication authorized; delegation
deferred.
