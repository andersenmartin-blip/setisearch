# SETIsearch — current project status

Updated 14 September 2026. This is the maintained operational entry point.
Earlier reports and continuation files preserve their historical states.

The [14–27 September work plan](TWO_WEEK_PLAN_2026-09-14.md) groups the next
background/residual model, both closed-sector comparisons and auditing into
one integrated study, followed by an explicit unused-data readiness decision.
Its dates are work windows. The original LS7I joint model, evaluation and audit
are complete; the subsequent instrumental-response work is tracked below.

## LS7Q HiPERCAM metadata assessment completed; native pilot not ready

The GTC archive query reports **1,035 matching products**; its first **100
metadata rows** are saved. Six headers and the QC log identify a public XO-2b
run with 11,152 stored frames. Header-derived repeat intervals are approximately
**0.652 seconds** in gs/is/zs, **1.304 seconds** in NaI and **13.040 seconds** in
us. All 66 checked timing tuples agree with the pinned official reader.

A native pilot is **NOT_READY**. The linked flat uses rs where the science
uses NaI; the listed slow full-frame bias differs from the fast windowed
science readout. Raw access returned an invalid negative Content-Length and
a failed bounded byte-range request. The run's QC log records an incomplete
observing block. No science pixels, new candidates or observing coverage are
added. These are metadata/input obstacles, not a failed detection experiment.

Next establish bounded raw delivery and the matching calibration/scene/timing
contract, or inspect the secondary CHEOPS product option at metadata level.
[Findings](LS7Q_OPTICAL_METADATA.md), [saved evidence and reproduction](results_ls7q_metadata/README.md),
[current continuation](LS7Q_CONTINUATION.md).

**LS7P evidence correction:** the earlier conversation reported completion and
publication, but the public branch inspected here contains only its source
freeze `f42aa216b25779d55cd1fabd25545d3277abcfa5` and metadata. Its reported
numerical result is not currently verified. [Reconciliation and recovery task](LS7P_PUBLICATION_RECONCILIATION.md).
LS7Q uses no LS7P numerical output. Unused TESS/M43 panels remain closed.

## Earlier LS7O reference availability completed: input contract fails

Metadata selection establishes **twelve simultaneous 20-second reference
products from seven stars**, on the same CCDs as the science target. All
**48,120 selected reference rows** are restored in **4,812,000 bytes** with
exact cadence and spacecraft-time joins. Centroids and positive quoted errors
are finite, and the centroid masks are disjoint from the target and each other.

The fixed requirement for all six references to have QUALITY=0 at every
sideband row blocks **all 420 windows**. Event-only availability is 72/210 and
101/210; complete-sideband availability is zero in both sectors. Therefore
**zero new corrections and zero pulse transfers were measured**. The 840
model slots and 12,600 pulse slots are unavailable ledger entries. LS7O is an
eligibility obstruction, distinct from the measured LS7J/LS7N response failures.

The independent input audit passes **384,960 exact raw-field comparisons**;
916 numerical comparisons preserve the static baseline. A separate scalar
audit confirms quality counts and all 420 availability attributions. No
reference is removed or quality flag waived to obtain a result.

Next establish the fixed references' pixel-level quality, cosmic-ray treatment
and centroid-response contract before any bounded reference-pixel acquisition
and new integrated comparison. Matching pixel-product identities are known;
their time-series contents remain unread. If the contract cannot be established,
reassess optical product choice. Unused TESS/M43 panels remain closed.

[Findings](LS7O_FINDINGS.md), [report and scope accounting](results_ls7o_response/REPORT.md),
[frozen protocol](LS7O_SPEC.md), [current continuation](LS7O_CONTINUATION.md).
Source freeze: `f2d7aef6e82f90a357ec7f54e349cfc2b43953dc`.

## Earlier LS7N calibrated native response completed: FAIL

The fixed cadence-level PRF plus protected-plane response fails on the same
**420 native windows**, evaluated at both column conventions (**840 paired
model/window rows**). Combined residual energy rises **12.14–12.36% in sector
29** and **12.37–12.49% in sector 32**. Only 0/10 and 2/10 background aggregates
improve, against six required. All predictions are available.

All **12,600 downstream pulse responses pass**: maximum nominal distortion
is 0.015354%, and maximum calibration-entry stress distortion is 0.226796%.
The independent audit passes **108,604 numerical comparisons**, including all
native/pulse rows and unchanged static baselines. All 146 inherited manifest
entries agree. The energy accounting finds correction size exceeding its
alignment benefit in every sector/coordinate cell.

Close this exact cadence response without gain/sign/lag/profile adjustment.
Next assess whether independent reference-star astrometry or documented
target-excluded motion with timing/uncertainty is available on these same
pointings. That input is not yet established; if unavailable, reconsider the
optical data/product choice. No detector or candidate is adopted, observing
coverage added or unused TESS/M43 panel opened.

[Findings](LS7N_FINDINGS.md), [audited native result](results_ls7n_response/REPORT.md),
[frozen physical contract](LS7N_SPEC.md), [current continuation](LS7N_CONTINUATION.md).
Source freeze: `07c6040715b8425a2051bfdbeb2806974f85d6c7`.

## Earlier LS7M calibrated PRF and exposure operator completed and audited

The new numerical operator passes **10 known-answer tests**, all **4,050 phase
reconstructions** and **144 fixed calibration cases**. The independent
original-MATLAB/SciPy/Simpson audit finds at most **1.39e-16** absolute flux
discrepancy. All fifty original image pairs match the mission FITS exports
exactly; 113 inherited manifest entries remain unchanged.

The explicit 0/-44-column alternatives differ by at most **0.7946%** in
relative L2 response over the fixed panel. Absolute origin remains unresolved.
Only 42/144 cases support all 121 stamp pixels; the others support 110, with
uncovered pixels flagged. A synthetic 30 ms pulse overlaps **10–15 ms** of
live exposure under the three declared readout placements.

Next establish the observable-to-pixel physical contract, including quaternion
geometry, calibration blur, sample timing, supported footprint and upstream
target dependence, then freeze one native comparison on the same closed data.
Numerical correctness does not establish native prediction improvement. No
native pixel values were opened, detector adopted or unused panel evaluated.

[Findings](LS7M_FINDINGS.md), [audited benchmark](results_ls7m_response/REPORT.md),
[frozen contract](LS7M_RESPONSE_SPEC.md), [current continuation](LS7M_CONTINUATION.md).
Numerical source freeze: `b6fea2889d792d6c1980335f5e83b27c54ca22c7`.

## Earlier LS7L engineering and PRF phase inputs completed and audited

LS7L restores **81,200 camera-4 quaternion rows** and **30,594 thermal rows**
on the same twenty closed contexts. All **8,020** saved cadence bins have
exactly ten quaternion samples; no coverage bin is empty. All selected values
are finite. Thermal sampling is approximately sixty seconds, with gaps up to
seven minutes.

The fifty PRFs yield **4,050 phase images**, whose unrenormalized flux sums
span 0.995947949571–1.000000000000. The raw-byte audit passes for 1,066,182
selected table values, all cadence counts and the calibration phase accounting.
Engineering calendar checks support TDB numerically to 20–32 microseconds;
the exact sample/exposure kernel and upstream target exclusion remain open.

The mission exporter was recovered and inspected. It copies the inherited
MATLAB detector references without an explicit 44-column shift; this alone
does not resolve the calibration-to-science origin. Continue with that
coordinate/phase definition and the physical response specification before
any native response comparison. No detector is adopted or unused data opened.

[Findings and limitations](LS7L_FINDINGS.md),
[audited selected inputs](results_ls7l_inputs/REPORT.md),
[complete engineering schemas](results_ls7l_engineering/REPORT.md),
[current continuation](LS7L_CONTINUATION.md).
Audited input result: `665d952f92e6b3687a4eb76976b87e8629db0014`.

## Earlier LS7K instrument-response inputs completed and audited

LS7K restored **50 original mission PRFs**, including their uncertainty images,
and **8,020 timing rows** from the same twenty closed contexts. The independent
raw-file audit passes; all 16,040 reused motion values agree exactly. At that
checkpoint, four engineering products were listed with their samples uninspected.
LS7L subsequently completed the extraction above. Code, calibration files,
timing extracts, metadata and logs are published.

LS7K established the calibrated response family. LS7L has now completed the
engineering-coverage and phase-normalization input checks. The remaining
coordinate/PRF forward-model work includes the absolute-coordinate convention,
exposure averaging and upstream target dependence. Exact fast POS_CORR uncertainty and target
exclusion remain unestablished. No detector is adopted or unused data opened.

[Completed findings and response contract](LS7K_INPUT_FINDINGS.md),
[audited input packet](results_ls7k_inputs/REPORT.md),
[LS7K historical continuation](LS7K_CONTINUATION.md).
Audited input commit: `f1ce03ec5f278a8850125a169a98490ba2cfa204`.

## LS7J auxiliary-observable study completed: FAIL

LS7J completed **420 fixed native windows and 9,480 digital response rows** on the same twenty closed-sector contexts. The combined motion/outside-aperture correction has joint feasibility **FAIL**; the independent audit passes. There are no new detector decisions or added observing days.

Combined native energy increases **45.74% and 34.51%**, with **0/10** backgrounds improved in each sector. All pulse-protection requirements pass, including broadened full-stamp profiles with at most **0.365% distortion**. All required motion inputs are available. The completed [limitation analysis](LS7J_LIMITATIONS.md) attributes the poor comparison to the fixed motion response: its squared size exceeds its limited alignment with the native fluctuation. Plane alone improves only five of ten backgrounds per sector and also fails the native improvement requirement.

Close this correction route. LS7K subsequently completed the requested provenance and calibration input assessment, reported above. It establishes an available mission PRF family while retaining explicit coordinate, timing-estimator and target-dependence questions. No sign, gain, delay, profile or threshold retry is appended to LS7J; unused data remain closed.

[Full result](results_ls7j_auxiliary/REPORT.md), [limitation analysis](LS7J_LIMITATIONS.md), [continuation](LS7J_CONTINUATION.md).
Audited result commit: `52ef2780a374e1314252f8fe9f37d8fcae4d985f`.

## LS7I joint background model completed: FAIL

LS7I completed **7,080 digital cases** on the two closed sectors: **6,720 historical cases plus a separately declared 360-case sector-32 shape supplement**. The primary rule fails **6/12 signal cells** and **2/60 control cells**. The joint development requirement is **FAIL**; the independent audit passes.

The fixed model does not satisfy the joint two-sector requirements. The independent arithmetic audit passes. This is a completed negative method result; no detector is adopted and no unused sector is opened.

Close this fixed ridge-prediction route. The next useful information would be an independently measured instrumental state: time-resolved image motion/centroid indicators and pixel variations outside the target aperture, together with a response model that preserves an injected stellar pulse. First establish whether those observables predict the remaining spatial contamination on these same closed contexts. A separately specified auxiliary-observable study is a proposed next project direction, not a hidden ridge, margin or template-bank retry. The present result alone does not establish that those extra observables will succeed.

[Result and figure](results_ls7i_background/REPORT.md), [signal losses](results_ls7i_background/SIGNAL_LOSSES.md), [continuation](LS7I_CONTINUATION.md), [two-week result](TWO_WEEK_REPORT_2026-09-14.md).

The [limitation analysis](LS7I_LIMITATIONS.md) completes this plan branch:
pulse protection passes exactly, but additional losses are dominated by the
source-score requirement and sector-32 error calibration broadens strongly.
The next proposed information is outside-aperture pixels and verified
instrument-motion/centroid observables on the same closed data. No new fit,
cut search or unused-sector evaluation is hidden in that bookkeeping.
Audited result commit: `1cd89b896a46b666b9328a5db00c1720af341190`.

## Earlier LS7I input preparation: completed before the model study

The two-week plan has started. Both closed TESS sectors now have verified individual-cadence inputs. All **6,720 historical trial recipes** and **300 training vectors** reproduce from **20 background contexts**. The independent sector-32 FITS restoration check passes exactly; sector 29 reuses its sealed LS7G cutouts. This completes input preparation, not evaluation of the new model.

This input stage enabled the separately frozen model study reported above.
Its successful reconstruction alone did not qualify a detector. The earlier
LS7G/LS7H outcomes and original denominators remain unchanged.

[Input report](results_ls7i_inputs/REPORT.md), [continuation](LS7I_CONTINUATION.md), [two-week plan](TWO_WEEK_PLAN_2026-09-14.md).

## LS7H completed: background-driven morphology confusion remains

LS7H diagnoses all **3,540 saved LS7G trials**. All **24** accepted controls in
the four failed cells have clean, background-removed margins below −1: the
native contribution changes the same-window model comparison. One fixed
extension adds **245** cross/ring/rotated-triangle placements. It reduces
those acceptances **24 → 9**, but loses **10** previously recovered stellar
trial rows. **2/30** control cells still fail; all six signal cells pass.
The independent audit passes. No detector or candidate is adopted.

The remaining failures are **4/40 weak 2x2** and **3/40 weak triangle**
controls, each allowing 2/40. Weak nominal recovery is **36/40** (the minimum),
and weak displaced recovery is **130/160** (128 required). The larger bank
alone is insufficient. Removing the sparse option also fails: nominal weak
recovery becomes 35/40 and the fixed 10%-flux recovery check fails.

Next, develop a joint model of the time-varying background and residual
pixels using observable samples outside the tested pulse. The remaining
nine focus-control acceptances all occur on backgrounds 00 and 01; keep all
ten backgrounds in the next study. Compare with both fixed LS7G and LS7H
references, preserve individual signal-loss accounting, and plan sector 29
and already closed sector 32 together. Do not assume the native contribution
is predictable or use injection-truth subtraction as a detector input.

Five analytical tests, all 14,160 direct new fits, **52,413,240** independently
enumerated fit alternatives, all 36 core cells and 360 background/cell counts
pass verification. Earlier manifests remain unchanged. The source freeze
was public before LS7H evaluation at `503a159f7bc3337f314565fc4858d130a524626d`.

[Result and figure](results_ls7h_morphology/REPORT.md),
[protocol](LS7H_MORPHOLOGY_PROTOCOL.md), [concrete continuation](LS7H_CONTINUATION.md).

## LS7G completed: fixed transfer to sector 29

LS7G completed **3,540 fixed transfer trials** on the ten already closed sector-29 backgrounds. The primary joint descriptive gate **fails**. Nominal recovery at the fixed margin −1 is **37/40, 40/40, 40/40**; displaced recovery is **135/160, 153/160, 158/160**. **4/30** instrumental control cells exceed their allowance. The independent audit passes; no detector is adopted and no candidate is promoted.

All six primary signal-recovery cells and the other joint checks pass. The
four failures are control acceptance: 4/40 weak 2x2 blocks, 8/40 weak crosses,
9/40 weak triangles and 3/40 medium-strength triangles, against a 2/40 limit.
LS7H has now completed that diagnosis and one separately frozen bank
extension, with every lost stellar row recorded. Its result and current
continuation appear above. LS7G remains closed and unchanged.

The complete result is published at `05fdbf457835df23ed67cced26666dad6ded2cf7`.
All source/result checksums reproduce after retrieval, and the figure is
visually checked. The dedicated [GitHub run](https://github.com/andersenmartin-blip/setisearch/actions/runs/34754959873)
completed acquisition, computation, independent audit and result publication.

[Result and figure](results_ls7g_transfer/REPORT.md), [protocol](LS7G_TRANSFER_PROTOCOL.md), [continuation](LS7G_CONTINUATION.md).

## LS7F completed: broader nuisance tradeoff requires negative margins

The planned separation study reuses all **3,180 saved LS7E trials**, with no
new injections or observing coverage. Adding **108** rectangular nuisance
templates rejects all **960** matched original/extended controls at margin 9,
but loses 74 previously recovered stellar trial rows in the sparse method.
Nominal recovery changes from 18/40, 37/40, 40/40 to **15/40, 34/40, 40/40**.

The exact sweep finds **no joint solution for the original nuisance bank**.
The expanded bank has 26 passing evaluated cuts with the sparse option and
six without it, but **all are negative**: a nuisance model may fit an accepted
case better than the stellar model. At margin 0, the expanded sparse method
recovers 36/40 weak nominal and only 125/160 weak displaced pulses (128 required).
The passing development cuts do not qualify the detector; no model is adopted.

The first enumerated control-safe expanded sparse margin gives nominal recovery
38/40, 40/40, 40/40 and displaced recovery 138/160, 160/160, 159/160. It accepts
2/40 weak 2x2 and 2/40 weak 3x3 controls, with zero in the other 19 core control
cells. These are outcome-selected bounds on ten shared backgrounds.

Six analytical tests and the independent audit pass: 12,720 direct whitened
fits, 6,868,800 alternative rectangle fits and all 101,466 threshold/cell counts.
The source freeze was public before scoring. All historical manifests and
LS7C/LS7E outcomes remain unchanged.
[Result and figure](results_ls7f_separation/REPORT.md),
[protocol](LS7F_SEPARATION_PROTOCOL.md), [continuation](LS7F_CONTINUATION.md).

LS7G has now completed the separately frozen transfer to already closed sector
29, with sector-specific covariance, omitted control shapes, residual stress
and nonnegative-margin comparisons. Its result and current continuation are
recorded above. LS7F itself remains an unchanged sector-32 development study.

## LS7E completed: stronger recovery, remaining weak-signal and extended-control failures

The combined covariance/sparse-pixel prototype completed **3,180 paired trials**
on the ten already closed sector 32 backgrounds. Nominal recovery improves
from 3/40, 12/40, 27/40 to **18/40, 37/40, 40/40** at temporal strengths
8.5, 12 and 20. All 120 original compact 2×2 controls are rejected, compared
with 16/120 accepted by LS7C. All 60 fixed 10%-flux single pulses recover.

The joint requirements still fail: weak nominal and displaced recovery remains
insufficient, and new 3×3 contamination is accepted in 4/40 and 8/40 cases at
strengths 8.5 and 12. The sparse option substantially helps a stellar pulse
coexisting with another disturbed aperture pixel. No detector is adopted.

Eight analytical tests and the independent numerical audit pass: all 1,460
original temporal outcomes reproduce exactly; 30 covariance folds, 19,080
winning fits and 101,400 representative alternative fits are checked.
[Complete result and figure](results_ls7e_joint/REPORT.md),
[protocol](LS7E_JOINT_PROTOCOL.md), [continuation](LS7E_CONTINUATION.md).

LS7F has now completed the planned weak stellar/extended-nuisance separation
study using these saved vectors and explicit signal-loss accounting. Its
conditional development tradeoff and transfer continuation are recorded above.
LS7E parameters remain fixed. No new sector or M43 held-out panel is opened.

## LS7D noise diagnosis completed and published: strong cross-pixel cancellation

All **120** LS7C nominal-trial noise ratios reproduce across **34 unique windows
in ten shared backgrounds**. Archived error floors alter the ratio by at most
0.0083%; local/run aperture MAD differs by a median factor 1.050. A separate
covariance calculation confirms strong cancellation: the corrected aperture
variance has a trial-weighted median of only **4.72%** of diagonal pixel variance.
The diagonal spatial approximation misses that structure. Eight analytical tests
and the scalar audit of 120 links and 68 covariance matrices pass.

This is closed-sector diagnosis, with no new injection, candidate, coverage,
threshold or adopted detector. A full 121-pixel empirical covariance is singular
with these sidebands (rank at most 107). LS7E has now completed that combined development comparison; its improvement
and remaining failures are recorded above. Another independent-sector
evaluation is not yet warranted.
[Result and figure](results_ls7d_noise/REPORT.md), [frozen diagnostic](LS7D_NOISE_PROTOCOL.md),
[continuation and historical LS7C name distinction](LS7D_CONTINUATION.md).

Publication completed on 12 September 2026 after the owner explicitly named
the public repository and branches. The complete LS7C sector 32 and LS7D
payload is preserved at `fa9f8028287a54d9369abc897c948e640c482c78`. The separate complete M43AF archive is also
released. [Release identities and verification](PUBLICATION_2026-09-12.md).

The differently named historical LS7C sector 29 development experiment is now
preserved as an [unchanged archival package](archives/ls7c_sector29_development/README.md).
Its 1,300 retrospective trials are separate from the sector 32 challenge below.

## LS7C TESS challenge completed: recovery and compact-control rejection fail

All **1,460 digital trials** completed on **18.7771 searchable cadence-days**
of L 98-59 sector 32, observed 20 November–16 December 2020. The noise-aware
pixel method was published before opening this sector. Thirty tests and the
complete ledger audit pass; the detector's joint qualification fails.

All 1,200 strength-matched trials reach their intended screening scores. Nominal
stellar recovery is 3/40, 12/40 and 27/40 at scores 8.5, 12 and 20; compact 2×2
controls leak in 0/40, 5/40 and 11/40 cases. Only 44/60 fixed 10% single pulses
recover. All 325 native excursions fail the spatial test; no LS candidate or
physical population limit is established. [Reviewed result](results_ls7c_tess/REVIEW.md).

A retrospective reconstruction of 120 recorded signal windows finds that
quadrature pixel noise exceeds run-level aperture noise by a median factor 4.66.
All 30 residual-cut failures have restored correction pixels contributing
70.9–94.8% of their weighted residual sums. These are diagnostics, not new vetoes.

LS7D has now measured the covariance/noise mismatch on the closed sector 32
backgrounds. LS7E developed and compared a revised covariance/residual model on closed
sector 32, including compact and extended nuisances. Do not
retune this result or open another sector merely because qualification failed.

## LS7B TESS qualification completed: weak-glint recovery failed

The correction-aware sector 29 evaluation completes all **420 digital trials**
on **19.6620 cadence-days** of screened L 98-59 data, observed 26 August–21 September
2020. Ten nonoverlapping backgrounds pass the frozen eligibility requirements.
The code and protocol were public before this sector was opened; 15 tests pass.

The detector recovers only **5/60** baseline single pulses at 1% extra aperture
flux: 35 are below threshold and another 20 fail pixel morphology. All 80 displaced
30-second profile trials are below threshold. The method remains unqualified.
No instrumental control reaches threshold either, so their 0/80 acceptance does
not demonstrate rejection of stronger nuisance events.

All 343 restored-stream native excursions fail the pixel screen and fall below
threshold in the corresponding corrected windows. The strongest four reviewed
images are consistent with cosmic-ray contamination. There is no promoted LS
candidate or astrophysical population limit.
[Reviewed result and concrete continuation](results_ls7b_tess/REVIEW.md).

LS7C subsequently tested a separately frozen noise-aware spatial method and
stronger controls on sector 32. Preserve these completed LS7B denominators and
failed gates. The earlier radio LS/M43 results are unchanged.

## Previous closed LS7 sector 28 pilot: no eligible injection anchors

The owner requested a return to optical light-sail work with TESS. The prospective
L 98-59 sector 28 pilot retrieved and checked the public 20-second light curve
and target pixels, dated 31 July–25 August 2020. Eight implementation tests pass.

The frozen quality mask fragments 20.306 accepted cadence-days into 3,779 runs.
Only 2.39 hours survive the screening guards, and no run supports the required
401-sample injection context. **Zero of the 300 planned digital trials ran.**
The method is not qualified; there is no sensitivity estimate or LS candidate.
[Full result and preserved failure](results_ls7_tess/REPORT.md).

A separate time/quality metadata comparison found 17.527 potentially searchable
cadence-days in sector 28 when correction flags 64 and 1024 are allowed. That
sector 28 alternative remains a metadata diagnostic. LS7B evaluated the explicit
flag policy on the previously unopened sector 29. LS7C subsequently opened sector 32 under its separate freeze.

## M43AI native evaluation completed

The fixed combined rule failed the predeclared same-sequence native challenge. It recovered 53/64 signal cases and lost 0/53 signals required by the reference union. 1/48 controls and 0/128 native null cases had surviving members.

[Complete result](MILESTONE_43AI_NATIVE_VALIDATION_RESULT.md). All 240 sealed records passed the final integrity and accounting audit. The exact protocol and model were public before scoring. No threshold was retuned. The original held-out panels remain unopened; the model is not adopted.

The complete result archive, audit and report accompany this science release.
The owner explicitly approved publication of the prepared M43AI package and
main README update after the earlier automatic-review rejection.
[Restore the 240 original records](results_m43ai_native_archive/README.md).

## Previous closed comparison: M43AH completed

[The M43AH epoch-support study](MILESTONE_43AH_EPOCH_SUPPORT_RESULT.md) compared
two fixed observable rule families on the 241 public closed M43AF training
records. Neither meets the joint training requirements; no rule is adopted.

| Conditional family | Fewest required signal losses with zero non-signal leaks | Fewest leaking controls while recovering all 57 |
|---|---:|---:|
| Original coordinates, exact M43AG family | 1 of 57 | 8 of 48 |
| M43AH raw second-epoch ON support | 3 of 57 | 4 of 48 |
| M43AH second-epoch ON-minus-OFF support | 6 of 57 | 12 of 48 |

M43AH exhausts 1,743 and 1,758 ON-cut equivalence classes, respectively.
A separate scalar path verifies 3,497 member features through 14,744 original
profile-center references. The fixed M43AG auditor verifies both complete
sweeps and their extrema/certificates; every zero-leak optimum has complete
case-level recovery and per-reference loss accounting. All 16 new tests pass.

The protocol, code, tests and source preflight were
[published and verified before extraction](https://github.com/andersenmartin-blip/setisearch/commit/3e6a0b60f65d9599ddc78d0aa9ec2e976d5b323f).
All 244 original training-archive files and the unchanged M43AG dependencies
were hash checked. This is retrospective development, not fresh validation.

## Scientific and publication state

| Item | Current state |
|---|---|
| M43AI | Complete native challenge failed; all 240 records, audit and report released |
| M43AH | Completed with full feature/family ledgers, audits, source identities and output hashes |
| M43AG | Completed exact original-boundary obstruction; [result](MILESTONE_43AG_BOUNDARY_OBSTRUCTION_RESULT.md) |
| M43AF training | Published: 241 records, failed joint qualification; [result](MILESTONE_43AF_TRAINING_RESULT.md) |
| M43AF complete no-model study | Published and byte-verified: 502 records; 69 archive parts restore 508 original files |
| Adopted new detector / new M43AF–M43AI astronomical candidate | None |
| Earlier M33 HD 3651 case | Still unresolved; [investigation](MILESTONE_33_CANDIDATE_INVESTIGATION.md) |
| LS research | [LS7Q](LS7Q_OPTICAL_METADATA.md): HiPERCAM metadata assessed; native pilot not ready; LS7P result publication unverified |

M43AF's 502 records include 261 already completed historical acquisitions and
the 241 training/baseline/null records. Its 940 scientific pins and earlier
endpoints remain unchanged. M43AH performs new downstream feature/rule
calculations, with no full upstream native-pipeline rerun, new telescope data
or additional observing sequence. Control-case counts are not independent
noise realizations; empty native-null/baseline retained sets supply no
conditional tail observations or physical false-alarm probability.

Current science is on m43-support-qualification; main remains a concise overview
with earlier pipeline code. [PROJECT_DIRECTION.md](PROJECT_DIRECTION.md) retains
the owner's long-term direction and ongoing publication authorization.

## Complete M43AF historical release published

All 95 science payload files from `setisearch_M43AF_complete_release.zip`
are preserved at `f41ca8a4e88ecf64c0cc2b86fbf8c501d940e00f`. Its 69 archive parts restore all 508 original files,
including 502 measurement records. All original bytes were reconstructed and
hash-verified with Python 3.12.14 / zlib 1.3.2; no scientific study was rerun.

Archive SHA256:
`b66e2a2dbe41d3dda4a63254c4528185e761aae7fdcf4745ef8e3764ca6c9443`.
Original ZIP SHA256:
`82e649f8aa0faffe88d4020cda4eb5fce4cbdcda1a84015cd48774a94f673999`.

The earlier automatic-review block has been resolved for this publication.
The original scientific manifests are unchanged. Match the historical release
manifest against the exact release commit; current operational documents have
subsequently been updated to preserve the newer LS7D/M43AI continuation.
The old proposed main README is archived as provenance, while the current main
README retains the concise overview. [Complete publication accounting](PUBLICATION_2026-09-12.md).

[Restoration notes](M43AF_CURRENT_CONTINUATION.md) distinguish the 241-record
training archive from the complete 502-record archive. Original held-out
panels remain reserved and unopened.

M43AI is complete. Do not rerun or retune this closed study. Any successor
requires a separately fixed protocol and new evaluation evidence. The original
held-out panels remain reserved. Main CI alone does not establish coverage of
the science branch; use the native study audit and original-byte archive checks.
