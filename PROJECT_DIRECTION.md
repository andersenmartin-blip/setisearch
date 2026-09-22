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

