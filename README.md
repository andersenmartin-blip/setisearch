# SETIsearch

A transparent, reproducible search for intermittent narrowband signals across
multiple observing epochs. Exoplanet motion supplies a frequency-drift
hypothesis; it does not establish where an observed signal originated.

The **light-sail (LS) research branch** explores whether radiation associated
with beamed propulsion could leave detectable radio or optical signatures.
After the TESS method studies, current LS work assesses optical data products
for short-glint searches.
Neither an optical brightening nor a radio trigger alone establishes artificial origin.

**Start here: [current status and continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PROJECT_STATUS.md).**

The [12 September publication record](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PUBLICATION_2026-09-12.md)
links the complete LS7C/LS7D release and the preserved historical archives.

## Where the project stands

**LS8C: all seven positive CHEOPS excursions share a smearing/roll pattern, 19 September 2026.**
The frozen diagnosis of all eight LS8B representatives uses only saved L2
tables. Every positive representative coincides with a large smearing-column
residual (**205,662–293,495 electrons**) at mean roll angles of **16.39–20.42
degrees**. The negative control does not share this pattern. All 112 field
diagnoses and 56 separate sideband-only couplings are retained.

The shared pattern motivates image/correction follow-up. Sideband smearing
fits predict between **−0.42 and 31.78 times** the observed positive brightness
residuals, so they cannot supply a reliable event correction or establish a
unique cause. All eight remain **L2_ONLY_UNRESOLVED**. No SETI candidate,
detector qualification or qualified observing coverage is added.

Six synthetic tests pass, followed by an independent audit with **11,635
numerical comparisons and 1,009 exact checks**. The original LS8B audit FAIL
remains preserved. No new archive science bytes or image pixels were opened.
[Complete report and context plots](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8c_auxiliary/REPORT.md).

**Next:** prepare one bounded CAL/COR image-and-correction study of all eight
fixed representatives. Establish exact product metadata and exposure joins,
then freeze byte/row/pixel scope and stopping rules before image access.
[Exact continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8C_CONTINUATION.md).

**LS8B: four held-out CHEOPS visits evaluated.**
The unchanged DEFAULT-aperture screen covers **4,754 rows and 7,917 eligible
windows**. It finds **seven positive clusters and one negative control cluster**;
per-visit positive/negative counts are 3/1, 2/0, 2/0 and 0/0. These are L2
excursions, not SETI candidates or calibrated Gaussian significances.

The frozen audit fails two tiny near-zero excess comparisons. A 60-decimal
reference verifies every screening decision, and a separately frozen
flux-centered implementation passes **31,668** numerical comparisons at the
original tolerances, with zero changed decisions. The original audit failure
and original values remain preserved; this is an arithmetic repair on closed
data, not detector qualification.
[Result and four-visit figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8b_l2_suite/REPORT.md),
[numerical review](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS8B_NUMERICAL_REVIEW.md).

The preceding LS8A held-out visit had zero positive clusters and four negative
threshold windows. Both fixed transfer results remain separate and unchanged.
[LS8A result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls8a_l2_transfer/REPORT.md).

**LS7Z closes both prospectively screened CHEOPS L2 excursions.**
The LS7X DEFAULT-aperture pilot produced two threshold crossings. LS7Y linked
the first to the CAL→COR correction. For the second, LS7Z used only already
published bytes and found that a fixed displacement-template model explains
about **92.5%** of the event-map squared energy, versus about **0.11%** for a
brightness-profile model. The independent LS7Z audit passes 103,218
comparisons. Following the predeclared stopping rule, both branches are now
closed without widening to other apertures, rows, visits or raw imagettes.
[LS7Z result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7z_morphology/REPORT.md).

The integrated work in the [14–27 September plan](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/TWO_WEEK_PLAN_2026-09-14.md)
is now complete, including the negative-result decision branch. The calendar
dates were work estimates; execution proceeded during active sessions.

**Separate raw-imagette track: resolve the remaining physical input contract.**
The official University of Vienna CHEOPS-IASW repository and ESA documentation
now narrow the onboard stacking question: ordinary window `coadd` is described
as pixel-by-pixel coaddition, while the exact `gcoadd` definition is delegated
to CHEOPS-UVIE-INST-TN-001 issue 2.0. A second bounded public-source pass did
not recover that technical note, a flight-relevant `gcoadd` implementation,
or the required native reference-validity rules. The public-source route is
therefore **incomplete**, and the raw-imagette calibration study remains blocked.
[LS7W follow-up](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7W_PUBLIC_SOURCE_FOLLOWUP.md).

Matching-version public CHEOPS schemas now also fix the required flat/dark/
bad-map/LUT product structures and units, while the pinned public PIPE code
provides an independent comparison for Teff interpolation, detector slicing
and validity-start selection. PIPE's calibration order differs from the
official DRP architecture, so it is **not** adopted as a DRP 14.0.1 proxy.

The invariant parts of the next 30/60/100-second positive-pulse experiment
are predeclared before target access in both a
[human-readable preparation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7W_NATIVE_STUDY_PREPARATION.md)
and a
[machine-readable manifest](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7W_NATIVE_STUDY_PREPARATION.json).
Its state is **PREPARED_NOT_FROZEN — TARGET PIXELS CLOSED**.

A complete
[technical request](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/CHEOPS_CALIBRATION_REQUEST.md)
and [exact-version manifest](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/CHEOPS_REQUIRED_INPUTS.json)
are prepared and narrowed to the remaining operator/reference questions. The
message is **unsent**; no reply is pending. LS7V is the earlier calibration-log
checkpoint; the newer L2 transfer results above do not resolve the raw-image gate.

**LS7V CHEOPS calibration-log reconciliation completed, 15 September 2026.**
The actual reduction log explains the difference investigated in LS7U:
**563.43 ADU/frame bias and 7.13 ADU/frame noise are chosen defaults**, whose
binary32 representations exactly match the saved CAL/COR values. The log also
shows that the spatial bias-frame correction was skipped. Its reference is
not needed to reproduce an unapplied correction.

Source identities, native-header comparisons and fresh offline reproduction
pass. The applied dark map, exact gain/coaddition/offline operator and remaining
spatial inputs still need resolution before the combined native image study.
**Input remains NOT_READY; no source trial or new observing coverage is added.**
[Findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7V_CALIBRATION_RECONCILIATION.md),
[evidence](https://github.com/andersenmartin-blip/setisearch/tree/m43-support-qualification/results_ls7v_reduction_log),
[current continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7V_CONTINUATION.md).

**Earlier LS7U CHEOPS electronic-reference measurements completed, 15 September 2026.**
The fixed virtual prescan now directly measures **562.089864 ADU/readout bias**
and **7.118046 ADU/readout effective noise**. Its bias differs from CAL beyond
the descriptive sampling interval. A separately specified exploratory check
executes PIPE's original estimator on its actual blank-reference input and
gives **562.071429 / 7.024590 ADU/readout**. CAL's noise is **1.500584% higher**,
so this alternative input does not reproduce the calibration numbers.

All **1,036,800 electronic values**, independent scalar checks and clean offline
reproduction pass. The retained arrays contain electronic reference values;
target-image bytes remain zero. The gain/coaddition and exact spatial-reference
contract still needs completion before a prospective native image study.
**Input remains NOT_READY; no candidate or qualified coverage is added.**
[Findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7U_ELECTRONICS_FINDINGS.md),
[evidence](https://github.com/andersenmartin-blip/setisearch/tree/m43-support-qualification/results_ls7u_prescan),
[current continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7U_CONTINUATION.md).

**Earlier LS7T CHEOPS native-HK contract audit completed, 15 September 2026.**
The actual 1,140-row instrument table reveals that the pinned PIPE gain reader
uses a separate voltage field in its temperature term. Running the unchanged
function gives about **−0.57027%** in scale relative to the centered-temperature
diagnostic. The earlier 8.129% comparison used a different conditional input.
Onboard nonlinearity is disabled, so its missing conversion coefficients are
not by themselves a calibration obstacle.

The primary sources disagree on the gain-temperature sign; gcoadd, offline
calibration and exact references still need resolving. Byte/scalar checks and
clean offline reproduction pass. **Native input remains NOT_READY:** no image
search, candidate or additional qualified coverage is added.
[Findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7T_CALIBRATION_CONTRACT.md),
[evidence](https://github.com/andersenmartin-blip/setisearch/tree/m43-support-qualification/results_ls7t_contract),
[current continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7T_CONTINUATION.md).

**Earlier LS7S CHEOPS calibration-input audit completed, 15 September 2026.**
The original gain reference is verified and **14/15 exact calibration versions**
are located. The saved 6,048 exposure rows have missing onboard gain/bias
values; physical calibration and coaddition assumptions still need resolving.
A conditional temperature-offset comparison exposes an absolute-scale
ambiguity, with no calibration adopted. The numerical audit passes.

The remaining reference download was blocked in this session. **Native input
is NOT_READY:** no image search, new candidate or qualified coverage is added.
Next finish the physical calibration contract and one combined protected
pulse/control/native study on the same visit.
[Findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7S_CALIBRATION_FINDINGS.md),
[evidence](https://github.com/andersenmartin-blip/setisearch/tree/m43-support-qualification/results_ls7s_calibration),
[current continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7S_CONTINUATION.md).

**LS7R CHEOPS input and temporal assessment completed, 14 September 2026.**
The selected public 55 Cnc visit provides **3,024 raw imagettes**, **432
matching subarrays** and metadata for **6,048 individual exposures**. Bounded
byte-range access works; only headers and metadata were acquired.

The small images combine two 2.2-second exposures and arrive about every
**4.449 seconds**. A timestamp-only 30-second pulse retains full peak in these
images versus **48–96%** in the larger stacked images on the sampled onset
grid. Four long observation gaps remain explicit. This is a temporal response
calculation, not noisy recovery or a detection.

LS7S subsequently audited the named inputs; the combined native pixel
calibration, signal-protection and nuisance-control study remains pending. No image pixels
were inspected, no detector was qualified and no search coverage was added.
[Findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7R_CHEOPS_INPUT.md),
[evidence](https://github.com/andersenmartin-blip/setisearch/tree/m43-support-qualification/results_ls7r_metadata),
[current continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7R_CONTINUATION.md).

**LS7Q HiPERCAM metadata assessment completed, 14 September 2026.**
A bounded inspection saves 100 catalogue rows, six run/calibration headers and
the observatory QC log. A public XO-2b run contains 11,152 stored frames with
header-derived repeat intervals of **0.652–13.040 seconds**, depending on the
channel. Its timing arithmetic agrees with the official instrument reader.

The native pilot is **not ready**: raw-file access is unresolved and the
identified bias/flat set requires a documented match to the science readout
and filters. No science pixels were opened, no new candidate was assessed and
no observing coverage was added. Next establish the actual input package, with
CHEOPS retained as a secondary metadata option.
[Read the findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7Q_OPTICAL_METADATA.md),
[saved evidence](https://github.com/andersenmartin-blip/setisearch/tree/m43-support-qualification/results_ls7q_metadata),
[current continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7Q_CONTINUATION.md).

**LS7P reconstruction and publication completed.** The explicit
reconstruction is now public as **83/83 release files** on
`m43-support-qualification`, including retained raw extracts, NPZ outputs,
audit records, provenance inventories, report and reproduction code. The
independent audit passes **1,496,872 numerical comparisons**, and
**48,114/48,120** centroid rows meet the fixed binary32 reconstruction bound.
This is reproducible replacement evidence, not recovery of the earlier missing
original run. It does not qualify the reference-star motion input or add new
observing coverage.
[Result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7p_response/REPORT.md),
[verification](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7p_reconstruction/README.md),
[release inventory](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/release_inventory.json).

**LS7O reference availability completed, 14 September 2026: the input contract fails.**
Twelve simultaneous 20-second products from seven reference stars provide
**48,120 selected rows**, acquired in **4,812,000 bytes**. All cadence and
spacecraft-time joins agree exactly, centroids and positive quoted errors are
finite, and the reference pixel masks are disjoint from the science target.

The fixed requirement for six QUALITY=0 references throughout every sideband
blocks **all 420 windows**. Event-only availability is **72/210 and 101/210**,
but complete-sideband availability is zero in both sectors. Consequently,
**zero new corrections and zero pulse transfers were measured**. The 840 model
slots and 12,600 pulse slots are blocked ledger entries, not measured failures.

The independent input audit passes **384,960 exact raw-field comparisons**;
916 numerical comparisons preserve the static baseline. A separate raw-byte
audit confirms every quality count and all 420 window attributions.
LS7J and LS7N remain separate measured response failures.

Next establish pixel-level quality, cosmic-ray handling and centroid response
for these fixed references before any bounded pixel acquisition and new
comparison. Matching pixel products are identified; their time-series contents
remain unread. No flags are waived, stars removed or unused sectors opened.
[Findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7O_FINDINGS.md),
[audited result](https://github.com/andersenmartin-blip/setisearch/blob/c03a07e174af1c49376f5a8e26a8983cd73bcbd0/results_ls7o_response/REPORT.md),
[current continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7O_CONTINUATION.md).

**LS7N calibrated native response completed, 14 September 2026: the joint test failed.**
The fixed cadence-level PRF plus protected-plane model evaluated the same
**420 native windows** under both declared column origins (**840 paired model
rows**). Combined residual energy rises **12.14–12.36% in sector 29** and
**12.37–12.49% in sector 32**. Only **0/10 and 2/10** background aggregates
improve, against six required. All predictions are available.

All **12,600 downstream pulse-response cases pass**: maximum nominal
distortion is **0.015354%**, and maximum calibration-entry stress distortion is
**0.226796%**. The independent audit passes **108,604 numerical comparisons**.
Correction size exceeds its alignment benefit in both sectors; the same failure
holds at both column origins. No detector or candidate is adopted.

This closes the exact cadence response without gain/sign/lag/profile retuning.
LS7O subsequently established simultaneous reference products, but its fixed
all-six/all-sideband quality rule blocks every window. The pixel/quality
measurement contract remains the next need, as described above. Unused TESS
and M43 panels remain closed.
[Findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7N_FINDINGS.md),
[audited result](https://github.com/andersenmartin-blip/setisearch/blob/3354f09bf34af32a3fbf6ed68af77076f9f3d604/results_ls7n_response/REPORT.md),
[current continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7N_CONTINUATION.md).

**LS7M calibrated PRF and exposure operator completed, 14 September 2026.**
Ten known-answer tests, all **4,050 phase reconstructions** and **144 fixed
calibration cases** pass. An independent original-MATLAB/SciPy/Simpson audit
finds at most **1.39e-16** absolute flux discrepancy. Every original PRF image
and uncertainty array matches its mission FITS export exactly.

Both declared column origins are retained; they change modeled pixel responses
by up to **0.7946%** over this panel. Finite stamp coverage is explicit, and a
synthetic 30 ms pulse has **10–15 ms** of live exposure across the declared
readout placements. This stage verified numerical response arithmetic.
LS7N subsequently fixed and evaluated the cadence-level native comparison
reported above. Instantaneous quaternion mapping, exact timing and upstream
target dependence remain limitations. No detector is adopted or unused panel
opened.
[Findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7M_FINDINGS.md),
[audited result](https://github.com/andersenmartin-blip/setisearch/blob/81406913ff12cc7ce91c9c9caf3d25aa758f568f/results_ls7m_response/REPORT.md),
[current continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7M_CONTINUATION.md).

**LS7L engineering and PRF phase inputs completed, 14 September 2026.**
All **81,200 camera-4 orientation rows** and **30,594 thermal rows** are
restored on the same twenty closed contexts. Every one of the **8,020** saved
cadence bins has exactly ten orientation samples. The independent raw-byte
audit passes.

The fifty mission PRFs yield **4,050 phase images** with at most **0.405205%**
footprint flux deficit. Engineering calendar checks support the TDB numeric
time scale. Thermal gaps reach seven minutes. LS7M subsequently completed the
relative-coordinate and exposure arithmetic above. Absolute detector origin,
exact mission timing and upstream target dependence remain physical-model
limits. No detector is adopted or unused sector opened.
[Findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7L_FINDINGS.md),
[audited inputs](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7l_inputs/REPORT.md),
[current continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7L_CONTINUATION.md).

**LS7K instrument-response inputs completed, 14 September 2026.**
All **50 original mission PRFs**, with their uncertainty images, and **8,020
timing rows** from the same twenty closed contexts are restored and audited.
Every reused motion value agrees with the original extraction. Four matching
engineering products were listed at this checkpoint; LS7L has now completed
their bounded extraction above.

LS7K established a mission-calibrated pixel-response family. LS7L completed the
engineering and phase-normalization inputs; LS7M subsequently verified the
numerical PRF/exposure family above. The physical observable-to-pixel mapping,
exact fast-cadence motion uncertainty and target exclusion remain unestablished. No detector is adopted or unused sector opened.
[Findings and response contract](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7K_INPUT_FINDINGS.md),
[audited input packet](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7k_inputs/REPORT.md),
[current continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7K_CONTINUATION.md).

**LS7J auxiliary-information study completed, 14 September 2026: the fixed correction failed.**
All **420 native windows and 9,480 digital response rows** are complete and
independently audited on the same twenty closed-sector contexts. The combined
motion/outside-aperture correction increases residual energy by **45.74% and
34.51%**, with no improved background aggregate. All pulse-protection
requirements pass, including broadened full-stamp profiles with at most
**0.365% distortion**. All required motion values are available.

The component comparison and exact energy accounting identify the fixed motion
response as the limitation: its squared size exceeds its limited alignment
with the measured fluctuation. The plane alone improves only five of ten
backgrounds per sector. No detector is adopted or unused sector opened.

LS7K subsequently completed the requested calibration/provenance input
assessment, reported above. It establishes an available mission PRF family
while retaining explicit coordinate, estimator-timing and target-dependence
questions. No gain, sign, lag or profile retry is appended to LS7J.
[Result and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7j_auxiliary/REPORT.md),
[limitation analysis](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7J_LIMITATIONS.md),
[current continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7J_CONTINUATION.md).

**LS7I protected background model completed, 13 September 2026: the joint test failed.**
The one fixed model and static comparison cover **7,080 digital cases**:
6,720 preserved historical cases plus a separately labeled 360-case sector-32
shape supplement. All **420** fixed native-prediction windows and the independent
audit are complete. Six of twelve signal cells and two of sixty control cells
fail; neither sector improves the aggregate native prediction requirement.
Weak nominal recovery is only **18/40** in sector 29 and **7/40** in sector 32,
against 36/40 required. All pulse-protection checks pass, but the new statistic
rejects too many weak signals. No detector is adopted or unused sector opened.

Every additional signal loss is published. The limitation analysis identifies
source-score losses and much broader conditional error calibration on sector
32. The proposed auxiliary-information direction was subsequently tested in
the separately frozen LS7J study reported above. LS7I's original negative
result remains unchanged; no cut, bank or ridge retry was appended.
[Result and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7i_background/REPORT.md),
[limitation analysis](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7I_LIMITATIONS.md),
[consolidated plan result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/TWO_WEEK_REPORT_2026-09-14.md).

The prerequisite input restoration also passed: both closed-sector packages
reproduce all **6,720 historical recipes** and **300 old training vectors**
exactly across twenty backgrounds, including independent sector-32 raw-FITS
checks. [Input report](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7i_inputs/REPORT.md).

**LS7H TESS morphology diagnosis completed, 13 September 2026.**
All 3,540 saved LS7G trials and the independent numerical audit are complete.
For all 24 accepted controls in the four failed cells, removing the known
native background reverses the spatial comparison; this uses injection truth
and cannot serve as a native-event veto. Adding 245 shape templates reduces
those acceptances **24 → 9**, but loses **10** recovered stellar trial rows.
Two control cells still fail, while all six signal-recovery cells pass.
LS7I subsequently tested one protected background model on both closed
sectors, with the result reported above. No detector or candidate is adopted.
[Read the result and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7h_morphology/REPORT.md).

**LS7G fixed TESS transfer completed, 13 September 2026.**
All 3,540 trials on already closed sector 29 completed and pass the independent
numerical audit. The fixed development rule recovers **37/40, 40/40 and 40/40**
nominal pulses and meets all displaced-signal recovery requirements. The joint
test still fails: four control cells accept too many weak or medium-strength
artifacts, especially crosses and triangles. No detector is adopted or candidate
promoted. [Read the result and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7g_transfer/REPORT.md).

**LS7F TESS separation study completed, 13 September 2026.**
Using all 3,180 saved LS7E trials, the expanded nuisance model rejects all 960
matched control cases at the old margin but also loses more stellar tests.
An exhaustive comparison finds jointly passing development settings only at
**negative margins**, where a nuisance fit may be better than the stellar fit.
These settings are not adopted or independently validated. All six tests and
the independent numerical audit pass. LS7G subsequently completed the fixed
transfer on already closed sector 29; its outcome is recorded above. [Read the result and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7f_separation/REPORT.md).

**LS7E TESS model comparison completed, 12 September 2026.**
Across 3,180 paired development trials on closed sector 32, the combined model
raises nominal recovery from 3/40, 12/40, 27/40 to **18/40, 37/40, 40/40** and
rejects all 120 original compact pixel controls. Weak-signal recovery and
broader-contamination rejection still fail; no detector is adopted or candidate
promoted. The independent numerical audit passes. [Read the result and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7e_joint/REPORT.md).

**LS7D TESS noise diagnosis completed, 12 September 2026.**
The diagonal pixel model misses strong cancellation between pixel fluctuations.
All 120 original trial-noise ratios reproduce across 34 windows in ten shared
backgrounds; eight analytical tests and the covariance audit pass. This is
method development with no new candidate or adopted detector. LS7E subsequently
combined covariance, residual handling and broader nuisance controls on the
closed data. [Read the result and figure](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7d_noise/REPORT.md).

**LS7C TESS qualification completed, 12 September 2026: the joint test failed.**
The noise-aware pixel method completed 1,460 digital trials over 18.78 searchable
cadence-days of L 98-59 sector 32. All planned matched-strength tests reach the
screening threshold, but stellar recovery is insufficient and 16/120 compact
pixel controls are accepted. All 325 native excursions fail spatial screening;
no LS candidate is promoted. LS7D and LS7E subsequently examined covariance
and residual contamination on these closed data.
[Read the reviewed result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7c_tess/REVIEW.md).

**M43AI native evaluation is complete:** The fixed combined rule failed the predeclared same-sequence native challenge. It recovered 53/64 signal cases and lost 0/53 signals required by the reference union. 1/48 controls and 0/128 native null cases had surviving members.
The model remains unadopted; all inputs use one observing sequence.
[Read the complete result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/MILESTONE_43AI_NATIVE_VALIDATION_RESULT.md).

M43AF's frozen joint response rule failed qualification: none of the 1,156
tested boundaries met all requirements. The complete **502-record study and
its lossless archive are now public**: 69 parts restore 508 original files,
verified byte for byte. The original M43AF held-out panels remain unopened.
[Read the complete study](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/MILESTONE_43AF_RESPONSE_STUDY_RESULT.md).

There is no new M43AF astronomical candidate or adopted detector. The earlier
**M33 HD 3651 follow-up at 1424.934238382 MHz remains unresolved**, pending an
independent observing cadence. It is not a detection or technosignature claim.

| Read or do | Entry point |
|---|---|
| Continue the active work | [Current project status](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PROJECT_STATUS.md) |
| Inspect current TESS work | [LS7O availability findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7O_FINDINGS.md), [LS7O audited report](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7o_response/REPORT.md), [LS7N native findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7N_FINDINGS.md), [LS7N audited result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7n_response/REPORT.md), [LS7M PRF/exposure findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7M_FINDINGS.md), [LS7M audited benchmark](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7m_response/REPORT.md), [LS7L engineering/phase findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7L_FINDINGS.md), [LS7L audited inputs](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7l_inputs/REPORT.md), [LS7K input findings](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7K_INPUT_FINDINGS.md), [LS7K audited inputs](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7k_inputs/REPORT.md), [LS7J auxiliary result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7j_auxiliary/REPORT.md), [LS7J limitations](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7J_LIMITATIONS.md), [LS7I joint background result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7i_background/REPORT.md), [LS7I limitations](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7I_LIMITATIONS.md), [LS7H morphology diagnosis](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7h_morphology/REPORT.md), [LS7G sector-29 transfer](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7g_transfer/REPORT.md), [LS7F separation study](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7f_separation/REPORT.md), [LS7E combined development](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7e_joint/REPORT.md), [LS7D noise diagnosis](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7d_noise/REPORT.md), [LS7C reviewed result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7c_tess/REVIEW.md), [frozen protocol](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS7C_TESS_PROTOCOL.md), and [previous LS7B result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/results_ls7b_tess/REVIEW.md) |
| Inspect the latest native evaluation | [M43AI result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/MILESTONE_43AI_NATIVE_VALIDATION_RESULT.md) |
| Inspect the separate historical TESS development | [LS7C sector 29 archive: 1,300 retrospective trials](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/archives/ls7c_sector29_development/README.md) |
| Understand the failed training rule | [M43AF training result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/MILESTONE_43AF_TRAINING_RESULT.md) |
| Inspect the frozen scientific method | [M43AF executable protocol](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/MILESTONE_43AF_EXECUTABLE_PROTOCOL.md) |
| Restore existing M43AF evidence | [M43AF continuation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/M43AF_CURRENT_CONTINUATION.md) |
| Follow the earlier open case | [M33 candidate investigation](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/MILESTONE_33_CANDIDATE_INVESTIGATION.md) |
| Understand the long-term plan | [Project direction](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/PROJECT_DIRECTION.md) |
| Revisit earlier radio LS work | [LS6 result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS6_TRAPPIST1_RESULT.md) and [LS6A result](https://github.com/andersenmartin-blip/setisearch/blob/m43-support-qualification/LS6A_SCAN_END_RESULT.md) |
| Read the full milestone history | [Archived README before cleanup](https://github.com/andersenmartin-blip/setisearch/blob/60bad761f4aa6eebeeef367f7a4123b80fd33e44/README.md) |

## Working with the repository

Current scientific development is on
[`m43-support-qualification`](https://github.com/andersenmartin-blip/setisearch/tree/m43-support-qualification).
The main branch provides this overview and earlier pipeline code.
Use the current status to select the correct branch and evidence archive.

Closed evaluations are restored from their sealed records. For exact M43AF
archive restoration, use the recorded Python 3.12.14 / zlib 1.3.2 and frozen
dependencies. Historical reproduction commands apply to their named milestones;
they are not commands to restart the current work.

The archive link preserves the previous full README and all its milestone
summaries. Its “current” labels and “next step” instructions describe their
historical dates. The current work queue is maintained in PROJECT_STATUS.md.
