# SETIsearch — current project status

## 21 September LS8V: EC 12578-2107 screen complete and closed

The predetermined rank-5 CHEOPS pair supplied **174 rows and 201 eligible,
overlapping windows**, with **zero positive and zero negative threshold
crossings**. The unchanged one/two/three-row screen uses 60/120/180-second
durations and the original +/-8.5 endpoints. There is no qualified SETI
candidate, detector or observing-coverage claim; no image follow-up is triggered.

The first visit contributes 36 eligible windows, with scores -1.64920 to
+1.40544; the second contributes 165, with scores -5.42090 to +4.89193.
These are screening scores, not Gaussian significances. The empty screen
does not establish short-glint sensitivity or an intrinsically constant source.

Both known-answer tests and **2,412 independent numerical/discrete comparisons**
pass without disagreement. All 20 result files and 26 metadata files were
checksum verified; the figure was visually inspected. Exactly 24,012 table
bytes were acquired, with no images, alternate apertures or later visits.
The original TLS failure before table access remains preserved. A separately
frozen transport-only recovery succeeded with unchanged inputs and arithmetic;
both URL resolutions succeeded on their first recovery attempt.

**Immediate next action: prepare LS8W for rank-6 GJ 436**, beginning with a
separate metadata/header freeze for CH_PR100041_TG000302_V0300 and
CH_PR100041_TG001301_V0300, then exact DEFAULT-L2 ranges and the unchanged
screen. Both 60-second/NEXP=1 values remain ledger entries requiring header
verification. GJ 436 science values remain unopened. EC 12578-2107 is closed.

[Scientific interpretation and exact continuation](LS8V_CONTINUATION.md),
[audited report and figure](results_ls8v_l2_recovered/REPORT.md),
[frozen scientific scope](LS8V_EC125782107_L2_PROTOCOL.md),
[preserved failure and bounded recovery](LS8V_TRANSPORT_RECOVERY.md),
[publication identities](PUBLICATION_2026-09-21_LS8V.md).

All earlier dated next actions are historical. The active queue is the LS8V
continuation above. The prior TESS_260647166 positive remains unresolved;
closed studies, reserved TESS/M43 data and the unsent calibration request
remain unchanged. The calibration gate remains NOT_READY.

## 20 September LS8U: TESS_260647166 retained-data study complete and closed

The positive **TG015701_P0 remains UNRESOLVED_WITHIN_FIXED_SCOPE**; the
negative **TG000101_N0 remains SPATIALLY_STRUCTURED**. The bounded study
quantifies the remaining structure and local variability without changing
original L2 scores, image labels, masks or thresholds. It adds no qualified
SETI candidate, detector or observing coverage.

The positive's combined COR residual/reference energy is **3.77–3.80** after
exact one-row temporal-noise propagation. **1/24** held single-row controls
has at least as much residual/reference energy in both conventions. Its
weighted residual is spatially extended: the top ten pixels account for
**6.47–7.03%**, and the fixed 16–25-pixel ring accounts for **72.95–73.45%**.
This is a model mismatch and a dependent local comparison, not a calibrated
significance or an identified physical cause.

The negative's three-row COR residual/reference energy is **0.705–0.723**;
**6/8** held three-row controls are at least as large. The fixed covariance
model raises its estimated variance by **26.1–26.5%** relative to IID,
compared with about **4.4%** for the positive. A small aggregate residual
ratio does not exclude localized structure or prove an ordinary-noise origin.

Hypothetical displacement subtraction loses **12.79–13.09%** of injected
brightness flux for the positive and **7.31–7.84%** for the negative. No
correction or veto is adopted. All eight native product/convention cases,
**128 duration-matched held cases and 128 signed controls** are retained.
All **18 pre-analysis tests**, **583,488 numerical comparisons and 625,868
exact checks** pass with no disagreements. No new archive bytes were
acquired. All 22 result files match their immutable checksums; both residual
figures were visually inspected.

**This bounded TESS_260647166 study is closed. Immediate next action:**
prepare a separate metadata/header freeze for **rank-5 EC 12578-2107**,
exact pair CH_PR100002_TG008901_V0300 and CH_PR100002_TG008902_V0300, then
freeze exact table ranges and transfer the unchanged DEFAULT-L2 screen.
The existing ledger reports NEXP=1 and 60 seconds for both visits; verify
these against their headers before opening science values. Those values
remain unopened at this checkpoint. Do not transfer residual measures as
new screening cuts or extend the closed target to seek a preferred outcome.
[Scientific interpretation and exact continuation](LS8U_CONTINUATION.md),
[complete report and both figures](results_ls8u_residuals/REPORT.md),
[frozen method](LS8U_RESIDUAL_NOISE_PROTOCOL.md),
[publication identities](PUBLICATION_2026-09-20_LS8U.md).

All earlier dated sections below retain historical next steps. The active
work queue is the LS8U continuation above. Closed HD 136352/GJ 1132/WASP-189
studies, reserved TESS/M43 data and the unsent calibration request remain
unchanged; the calibration gate remains NOT_READY.

## 20 September LS8S–LS8T: rank-4 screen and both image follow-ups complete

TESS_260647166's selected **CHEOPS** pair supplied **1,747 rows and 2,004
eligible overlapping windows**. Six positive crossings form **one positive
cluster**; two negative crossings form **one negative cluster**. Each visit
uses its separately verified 42-/49-second exposure time. The unchanged L2
screen and independent audit pass **24,048 numerical/discrete checks**.

Both representatives received the separately frozen image diagnostic:

| Event | Duration | COR displacement explained C0 / C1 | Fixed outcome |
|---|---:|---:|---|
| TG000101_N0, negative | 126 s | 92.95567% / 92.96205% | SPATIALLY_STRUCTURED |
| TG015701_P0, positive | 49 s | 75.76422% / 75.77892% | UNRESOLVED_WITHIN_FIXED_SCOPE |

The positive's original L2 score is **+45.460348286**, not a Gaussian
significance. Neither correction gate passes. Its displacement fit remains
below the fixed 80% requirement in both conventions, and pure brightness
explains only **2.69041% / 2.67304%**. All apertures and exposure joins are
complete: the remaining limitation is the fixed model's unmeasured
residual/noise comparison. No qualified SETI candidate, detector or observing
coverage is added. The negative's spatial label does not prove one cause.

The metadata-only audit passes **120 unique joins and 556 exact checks**
before pixels. The exact payload is **38,400,000 image bytes plus 96,000
smearing bytes**. All nine pre-payload image tests and the independent audit
pass: **189,074 numerical comparisons and 321,180 exact checks**, with no
disagreements. Both image figures and the L2 figure were checksum verified
and visually inspected; both original signs and all results are retained.

**Immediate next action:** separately freeze one integrated residual/noise
study of the two retained contexts. Quantify the positive's remaining
structure against local 49-second variability, retain the three-exposure
negative comparison with an explicit temporal-noise treatment, and use
duration-matched held controls and both signs in signal-protection tests.
Keep original labels, masks and thresholds; do not acquire additional
pixels or visits. This follow-up has not yet been executed.
Rank-5 EC 12578-2107 remains a later independent transfer.
[Scientific interpretation and exact continuation](LS8T_CONTINUATION.md),
[image report and both figures](results_ls8t_images/REPORT.md),
[L2 result and figure](results_ls8s_l2_screen/REPORT.md),
[publication identities](PUBLICATION_2026-09-20_LS8S_LS8T.md).

Older sections below retain historical next steps. The active work queue is
the LS8T continuation above. Closed HD 136352/GJ 1132/WASP-189 work, reserved
TESS/M43 data and the unsent raw-imagette calibration request are unchanged.

## 20 September LS8Q–LS8R: HD 136352 screen and image follow-up complete and closed

The unchanged rank-3 pair supplied **1,125 L2 rows and 1,923 eligible
overlapping windows**. There were **zero positive threshold crossings**;
13 negative crossings formed **three clusters**. The independent L2 audit
passes all **23,076 numerical/discrete comparisons**.

All three negative representatives received their separately frozen image
follow-up. **Every one is CORRECTION_LINKED** under the original diagnostic,
with complete apertures and matching negative signs in both conventions:

| Representative | DELTA/COR C0 / C1 |
|---|---:|
| TG000901_N0 | 0.575222 / 0.558559 |
| TG000901_N1 | 0.741593 / 0.736533 |
| TG000101_N0 | 0.791461 / 0.813813 |

Each direct aperture-sum ratio exceeds the frozen 0.5 gate in both
conventions. This describes a material contribution from the difference
between delivered CAL/COR processing products; it does not identify one
physical correction component or exclude source variability. Smearing
regressions remain explicitly unavailable because they are rank deficient.
No qualified SETI candidate, detector or observing coverage is added.

Each delivered row stacks **26 exposures into 44.2 seconds**; the image
representatives span one, one and two stacks. Individual 1.7-second
exposures are not resolved. The image metadata audit verifies **176 unique
joins and 812 exact checks** before pixels. The exact payload is
**56,320,000 image bytes plus 140,800 smearing bytes**. Nine image tests and
the independent audit pass: **283,611 numerical comparisons and 481,748
exact checks**, zero disagreements. All three image figures and the L2
figure were checksum verified and visually inspected.

**The HD 136352 pair is closed under the fixed diagnostic.** No residual
study or wider acquisition follows from these descriptive labels.
**Immediate next action:** separately freeze the metadata/header preflight
for **rank-4 TESS_260647166's CHEOPS pair**, then exact DEFAULT-L2 intervals
and the unchanged stable screen. Its ledger exposures differ by visit,
42 and 49 seconds; verify each header separately before science access.
[Scientific interpretation and exact continuation](LS8R_CONTINUATION.md),
[image report and all maps](results_ls8r_images/REPORT.md),
[L2 result and figure](results_ls8q_l2_screen/REPORT.md),
[publication identities](PUBLICATION_2026-09-20_LS8Q_LS8R.md).

Older sections below retain their historical next steps. The active work
queue is the LS8R continuation above. Closed GJ 1132/WASP-189 work, reserved
TESS/M43 data and the unsent raw-imagette calibration request are unchanged.

## 20 September LS8P: GJ 1132 retained-data study complete and closed

All five negative controls retain **UNRESOLVED_WITHIN_FIXED_SCOPE**. The
three-exposure noise and boundary study is complete; LS8N's **zero positive
crossings among 699 eligible overlapping windows** is unchanged. No event
is promoted and no detector or observing coverage is qualified.

The frozen short-lag covariance model raises COR event-variance estimates
by about **37–67%** compared with IID propagation. The combined COR
residual/reference energy ratio is **1.43–2.02**; **6/8** held blocks are at
least as large for TG000401_N0 and **8/8** for each of the four TG000403
controls, in both conventions. These dependent control comparisons and
estimated covariance ratios are descriptive, not calibrated probabilities.

TG000403_N2's coordinate-sensitive DELTA sum is accounted for exactly by
its two 71-pixel exclusive boundary sets: **-17,526.621987 ADU** in C0-only
pixels and **+294.173710 ADU** in C1-only pixels. Their difference explains
the **+17,820.795698 ADU** change between full apertures. This localizes the
numerical sensitivity without identifying a unique physical cause or
removing pixels. All original gates and labels remain unchanged.

A hypothetical displacement-plus-constant subtraction loses **24–38% of
injected brightness flux** across CAL/COR and C0/C1; it is not adopted.
All five contexts, **160 held three-row cases and 320 signed controls** are
retained. Seventeen pre-analysis tests and one serialization regression
pass. The independent audit passes **1,400,704 numerical comparisons and
1,529,059 exact checks**, with no disagreements. No new archive bytes were
acquired; all five residual figures were inspected.

The initial complete producer run stopped at JSON serialization of NumPy
integer audit coordinates. Its result and error log remain unchanged in
`results_ls8p_residuals`. A separately frozen representation-only repair
completed the same audit in **`results_ls8p_verified`**, without rerunning
the producer or changing arithmetic, tolerances or scientific scope.

**Immediate next action:** separately freeze a metadata-first independent
transfer to **rank-3 HD 136352**, using its already selected chronological
pair and the unchanged stable DEFAULT-L2 screen. The GJ 1132 bounded study
is closed; its new residual measures are not screening cuts.
[Scientific interpretation and exact continuation](LS8P_CONTINUATION.md),
[verified report and all figures](results_ls8p_verified/REPORT.md),
[scientific freeze](LS8P_THREE_SUM_PROTOCOL.md),
[preserved failure and repair](LS8P_AUDIT_RECOVERY.md),
[publication identities](PUBLICATION_2026-09-20_LS8P.md).

Older sections below retain their historical next steps. The active work
queue is the LS8P continuation above. The raw-imagette calibration request
remains unsent; closed WASP-189 and reserved TESS/M43 material are unchanged.

## 20 September LS8N–LS8O: GJ 1132 screen and all negative-control images complete

The unchanged rank-2 GJ 1132 pair supplied **615 L2 rows and 699 eligible
overlapping windows**. There were **zero positive threshold crossings**;
12 negative crossings formed **five clusters**. The independent L2 audit
passes all **8,388 numerical/discrete comparisons** at unchanged tolerances.

The separately frozen image study followed every negative representative,
each spanning three 60-second exposures. **All five remain
UNRESOLVED_WITHIN_FIXED_SCOPE.** Source bytes, masks and exposure joins are
complete; the limitation is the fixed image model. Neither correction gate
passes. TG000403_N1's displacement fit explains **79.74861% / 83.79823%** in
C0/C1, so it misses the required 80% in both conventions. TG000403_N2's signed
DELTA/COR ratio changes from **+0.37227 to -0.03201** between conventions.
Pure-brightness fits explain only 0.214–4.016% across the five controls.

Image metadata and audit verified **310 unique CAL/COR joins** before pixels.
The frozen payload was **99,200,000 paired-image bytes + 248,000 smearing
bytes**. Nine synthetic tests and the independent image audit pass:
**472,685 numerical comparisons and 802,983 exact checks**, zero disagreements.
There is no positive-glint detection, qualified SETI candidate, new detector
qualification or additional qualified observing coverage.

**Immediate next action:** freeze one integrated retained-data study of all
five controls, addressing local variability of three-exposure sums, residual
structure and the exact boundary contributions of the existing C0/C1 masks.
Keep both synthetic signal signs and explicit signal-loss accounting; do not
choose a favorable coordinate convention or retune the historical gates.
Rank-3 HD 136352 remains a later independent transfer under its own freeze.
[Scientific interpretation and exact continuation](LS8O_CONTINUATION.md),
[image report and maps](results_ls8o_images/REPORT.md),
[L2 screen and figure](results_ls8n_l2_screen/REPORT.md),
[publication identities](PUBLICATION_2026-09-20_LS8N_LS8O.md).

The sections below preserve historical checkpoints and their then-current
next steps. The active work queue is the LS8O continuation above. The separate
raw-imagette request remains unsent; closed WASP-189 and reserved TESS/M43 data
remain unchanged.

## 20 September LS8M: bounded WASP-189 residual/noise study complete

The smaller positive's unmatched COR image residual is **compact and comparable
in weighted energy to the local sideband reference**. Ten pixels account for
48.393–48.514% of weighted residual energy, and native pixel (105,106) alone
for 18.805–18.891%. The combined-model residual/reference ratio is
**1.10127–1.10616** in C0/C1; **8/24 and 7/24** held-sideband controls are at
least as large. Those overlapping control ranks are not false-alarm probabilities.

The study does not prove that the full selected excursion is ordinary noise or
identify the compact feature's physical cause. **TG000201_P0 remains
UNRESOLVED_WITHIN_FIXED_SCOPE.** The stronger positive and negative comparison
keep their original SPATIALLY_STRUCTURED and CORRECTION_LINKED labels. Their
COR weighted residual/reference ratios are 1.80071–1.89187 and
10.86307–10.88848 respectively. No new classification rule is adopted.

All three retained contexts, both products and both center conventions are
complete, including **288 held-sideband cases and 192 signed injection cases**.
Eight pre-analysis tests and the independent audit pass: **790,128 numerical
comparisons and 911,228 exact checks**, with zero disagreements. No new native
source bytes were acquired. Hypothetical displacement removal loses about
8% of the smaller event's injected brightness flux; it is not adopted.

**Immediate next action:** close this bounded WASP-189 follow-up and prepare
a separately frozen metadata-first transfer to **rank-2 GJ 1132**, using its
two already ledger-selected visits and the unchanged stable DEFAULT-L2 screen.
Do not apply LS8M's weights or residual measures as new screening cuts. No
qualified candidate, detector or additional observing coverage is claimed.
[Scientific interpretation and exact continuation](LS8M_CONTINUATION.md),
[full result and figures](results_ls8m_residuals/REPORT.md),
[frozen protocol](LS8M_RESIDUAL_NOISE_PROTOCOL.md),
[publication identities](PUBLICATION_2026-09-20_LS8M.md).

The sections below preserve historical checkpoints and their then-current next
steps. The active work queue is the LS8M continuation above. The separate
raw-imagette calibration request remains unsent; reserved TESS/M43 data stay closed.

## 20 September LS8J–LS8L: WASP-189 pair and all image follow-ups complete

The reconciled metadata-only first-1,000-public-row CHEOPS census selects
WASP-189 as rank 1 among 107 eligible cohorts (452 eligible visits). The
original run discarded full product-browser responses; a separately frozen
reconciliation now retains all 452 fresh inventories with unchanged summaries
and complete ranking. Original bytes and the historical limitation are preserved.

LS8K evaluated the two preselected visits: **1,604 L2 rows, 2,603 eligible
windows, two positive clusters and one negative control cluster**. All
31,236 independent numerical/discrete comparisons pass.

LS8L then completed the separately frozen CAL/COR image follow-up of all three
representatives, after 174 unique native exposure joins. It acquired exactly
**55,680,000 paired-image bytes + 139,200 smearing bytes**. Seven synthetic
tests and the independent audit pass: **283,611 numerical comparisons and
481,739 exact checks**, with zero disagreements.

| Representative | Fixed result | Interpretation within the diagnostic |
|---|---|---|
| TG000201_P0, score +8.982074701 | UNRESOLVED_WITHIN_FIXED_SCOPE | Absolute DELTA/COR 0.10789–0.11186; displacement explains 48.614%, brightness about 5.66% |
| TG000202_P0, score +60.894785514 | SPATIALLY_STRUCTURED | Displacement explains 88.331%; correction contribution about 5% |
| TG000202_N0, score -23.271648387 | CORRECTION_LINKED | Absolute DELTA/COR 0.92196–0.94371 |

**One smaller positive excursion remains unresolved.** This does not establish
an astrophysical brightening or artificial signal. None of the three is a
qualified SETI candidate; no detector or additional qualified observing
coverage is claimed. The original L2 scores are not Gaussian significances.

**Immediate next action:** freeze one bounded residual/noise diagnostic using
only the three retained image contexts to establish why the smaller positive
is not described by the current image model. Keep all signed comparison cases
and explicit signal-protection/control tests; do not alter LS8L's original
classifications or acquire more native data for this continuation.
[Exact continuation](LS8L_CONTINUATION.md),
[image result and maps](results_ls8l_images/REPORT.md),
[L2 result and figure](results_ls8k_l2_screen/REPORT.md),
[metadata reconciliation](results_ls8j_reconciliation/REPORT.md),
[publication identities](PUBLICATION_2026-09-20_LS8J_LS8L.md).

The entries below preserve earlier checkpoints and their historical next steps.
The current work queue is the LS8L continuation above. The raw-imagette
calibration gate remains separately NOT_READY, with its technical request unsent.

## 20 September LS8E–LS8I independent CHEOPS host sequence completed

The prospectively frozen post-55-Cnc host sequence is complete. The unchanged
DEFAULT-L2 cadence screen was transferred in fixed host order to GJ 876, GJ 514,
GJ 849 and GJ 649. Across the closed sequence, GJ 876, GJ 514 and GJ 649 are
clean two-visit null results at the unchanged +/-8.5 endpoints.

GJ 849 produced one audited positive L2 cluster in
`CH_PR100018_TG032401_V0300`: six overlapping positive windows in one cluster,
with representative score **23.470080** at one 42-second row. A separately
frozen metadata-first CAL/COR image diagnostic then acquired exactly
**18,560,000 paired image bytes + 46,400 smearing bytes**. The independent
image audit passes **94,537 numerical and 160,581 exact checks** with zero
disagreements.

The GJ 849 event is **SPATIALLY_STRUCTURED**, not CORRECTION_LINKED, under the
predeclared diagnostic: |DELTA/COR| is only **0.03536 / 0.03276** in C0/C1,
while the COR displacement template explains **87.801% / 87.800%** of event-map
energy and the brightness template explains below 1%. This is a morphological
diagnostic label, not a unique physical-cause determination and not a SETI
candidate.

GJ 649 closes the sequence with **381 eligible windows and zero signed
threshold crossings**; its independent audit passes **4,572 comparisons**.
The metadata ledger frozen before LS8E has no later host with at least two
eligible visits, so that target sequence is exhausted without relaxing its
rules.

**Immediate next action:** start a new metadata-only independent population /
dataset selection and freeze its population, target-name authority, product
requirements, minimum visit multiplicity and deterministic ranking before
opening new science values. Do not reopen or retune the closed GJ 849 event.
The raw-imagette calibration branch remains separately NOT_READY.
[LS8H image result](results_ls8h_images/REPORT.md),
[LS8I survey closure](results_ls8i_l2_screen/REPORT.md),
[continuation](LS8I_CONTINUATION.md).

## 20 September LS8D closes all eight retained CHEOPS L2 excursions as correction-linked

The predeclared paired CAL/COR image study is complete for all eight fixed
LS8B/LS8C representatives. Exact metadata preflight produced **482 unique
CAL/COR joins** for 241 retained context rows before image access. The frozen
run then acquired exactly **154,240,000 paired image bytes** plus **385,600
smearing-row bytes** from TG000302–TG000304; every range was constrained by
the frozen offset/count and source ETag.

All **seven positive excursions and the single negative control** satisfy the
same predeclared **CORRECTION_LINKED** rule in both fixed coordinate
conventions. For positives, absolute DELTA/COR is **1.331–2.431**: COR remains
positive, but CAL→COR contributes a large negative aperture event sum. The
negative control is also coupled at **0.857–0.884**, with the correction making
its negative excursion substantially deeper.

This does not identify one physical cause. The DELTA column-constant energy
fraction is **35.66–94.56%** for the positive representatives but only **0.49%**
for the negative control. The COR displacement model explains **35.79–74.42%**
of positive event-map energy, below the separately frozen 80% spatial gate.
The direct DELTA/smearing-row regression is rank-deficient in all eight
contexts and remains unavailable rather than being repaired after inspection.

Seven synthetic tests passed before image access. The independent audit passes
**756,296 numerical comparisons and 1,284,709 exact checks** with zero
disagreements. The original LS8B audit **FAIL** remains preserved. No raw
imagette was opened, no detector is qualified and none of these labels
establishes artificial or astrophysical origin.

**Next action:** close these eight 55 Cnc branches without widening. Start a
separately frozen metadata-only selection of the next independent optical
dataset/product before inspecting new light-curve values or image pixels.
Retain positive/negative controls and prefer a delivered calibrated product
that permits a predeclared image follow-up. The separate raw-imagette gate
remains NOT_READY and its technical request remains unsent.
[LS8D report and maps](results_ls8d_images/REPORT.md),
[exact continuation](LS8D_CONTINUATION.md).

## 19 September LS8C finds a shared smearing/roll pattern in all seven positive excursions

The predeclared auxiliary diagnosis of all eight original LS8B representatives
is complete using only the saved L2 tables. **All seven positive excursions**
coincide with large smearing residuals (**205,662–293,495 e**) at mean event
roll angles of **16.39–20.42 degrees**. The negative control does not share
that smearing pattern. The seven positive background residuals are also negative.

This is a repeated instrumental-column association, with no unique physical
cause established. Sideband-only smearing fits extrapolate between **−0.42
and 31.78 times** the positive brightness residual, so they do not supply a
reliable event correction. All 112 field diagnoses and 56 separate couplings
are retained, including the constant/error fields. All eight representatives
remain **L2_ONLY_UNRESOLVED**, with no new detector qualification or candidate.

The independent audit passes **11,635 numerical comparisons and 1,009 exact
checks**, following six passing synthetic tests. The original LS8B audit
**FAIL** and all original screen values remain preserved. No new archive
science bytes, image pixels, apertures, windows or visits were opened.

**Next action:** prepare one bounded CAL/COR image-and-correction study of
all eight fixed representatives, first establishing native product metadata
and unique exposure joins, then freezing exact byte/row/pixel scope before
image access. Preserve both signs and the earlier closed branches. The
separate raw-imagette gate remains NOT_READY; its technical request is unsent.
[LS8C report and plots](results_ls8c_auxiliary/REPORT.md),
[exact continuation](LS8C_CONTINUATION.md).

## 19 September LS8B four-visit transfer complete; arithmetic repair verified

The four prospectively fixed unused 55 Cnc visits TG000302–TG000305 have now
been evaluated with the unchanged LS7X/LS8A DEFAULT-L2 screen: **4,754 rows**
and **7,917 eligible windows**, all at 44.220001-second cadence. There are
**15 positive windows in seven clusters** and **one negative window/cluster**.
Per-visit positive/negative cluster counts are **3/1, 2/0, 2/0 and 0/0**.
These are L2 excursions, not SETI candidates or calibrated Gaussian significances.

The frozen audit fails two near-zero excess comparisons because of numerical
cancellation. Full accounting verifies every score, eligibility decision,
cluster and count. A 60-decimal reference changes no signed threshold decision;
its largest score difference is 4.5711e-11. A separately frozen flux-centered
implementation passes **31,668** comparisons at the original tolerances on
these closed data, again with zero changed decisions. The original audit
remains **FAIL**, and every original value and failure log is preserved.
This retrospective arithmetic repair does not qualify a detector.

**Next action:** freeze a bounded diagnosis of all eight positive/negative
cluster representatives using only auxiliary columns in the already saved L2
tables. Compare background, smearing, roll and centroid behavior before any
new image-data follow-up. No new visit or aperture is justified automatically.
The separate raw-imagette calibration gate remains unresolved.
[LS8B report and figure](results_ls8b_l2_suite/REPORT.md),
[numerical review](LS8B_NUMERICAL_REVIEW.md),
[exact continuation](LS8B_CONTINUATION.md).

## 19 September LS8A first held-out L2 transfer completed

The unchanged LS7X DEFAULT-aperture cadence-unit screen has now been transferred
prospectively to the chronologically earliest public 55 Cnc visit after the
March 2020 pilot, `CH_PR100006_TG000301_V0300`, OBSID 1300462. Metadata were
frozen before table bytes were opened. The held-out visit has a 44.220001 s
stacked cadence, 1,178 rows and 1,911 eligible 1/2/3-row windows.

The audited result has **zero positive clusters** at +8.5 but **four negative
control crossings** at -8.5; the maximum positive score is 6.7757 and the
minimum is -10.6024. The independent audit passes **9,555 comparisons**.

This is not detector qualification. In particular, the negative extremes show
that the screen has nontrivial held-out tails and must not be interpreted as a
calibrated Gaussian significance. No threshold, aperture, sideband, duration
or noise rule is changed. The next justified step is a small deterministic
suite of additional unused 55 Cnc visits using the same frozen screen and both
positive/negative control outputs.
[LS8A result](results_ls8a_l2_transfer/REPORT.md),
[continuation](LS8A_CONTINUATION.md).

## 19 September raw schema narrows gcoadd to special accumulator semantics

Matching-version CHEOPS schemas now add three independent constraints to the
exact-visit pair-grouping result: `NEXP` is explicitly the **number of
co-added measurements**; raw imagettes are stored as **uint32 ADU**, with the
schema history stating that the earlier uint16 storage was widened specifically
to support stacked imagettes; and this visit has **ROUNDING=0** and
**NLIN_COR=false**.

Together with the public PIPE treatment of bias as proportional to `NEXP`,
this strongly constrains the delivered raw imagette to an additive/sum-like
representation. It still does not prove the flight `gcoadd` implementation's
clipping/saturation, accumulator width/overflow, invalid-pixel handling or any
special internal normalization. Those remaining details stay behind the hard
raw-image gate.
[Structural constraints](CHEOPS_GCOADD_STRUCTURAL_CONSTRAINTS.md).

## 19 September LS7Z closes both LS7X transient-screen branches

The only remaining LS7X/LS7Y branch, cluster 1, has now completed the
predeclared morphology/component study using **zero new archive science
bytes**. The independent LS7Z audit passes **103,218 comparisons**.

Under both retained coordinate conventions, the fixed brightness template
explains only about **0.11%** of the COR event-map squared energy, whereas the
fixed first-derivative displacement template explains about **92.51%** and the
combined model about **92.62%**. The event map has cosine similarity about
**0.9503** with the x-derivative template but only about **0.0296** with the
brightness profile; its positive-excess centroid is displaced by about
**5.17–5.53 pixels** from the target center.

This follows the already declared LS7Y stopping rule: a pointing/spatially
structured morphology closes the branch without widening. Cluster 0 was
already closed as **CORRECTION_LINKED**. Therefore **both LS7X positive
clusters are now closed as candidate branches**. These labels do not identify
a unique physical cause and do not classify either excursion as artificial or
astrophysical. No new aperture, rows, raw imagettes or visit are opened.
[LS7Z result](results_ls7z_morphology/REPORT.md),
[continuation](LS7Z_CONTINUATION.md).

## 19 September exact 55 Cnc visit establishes imagette pair grouping

A peer-reviewed analysis of the same 9 March 2020 CHEOPS IOC observation
(Morris et al. 2021, A&A 653 A173) states that the 14×2.2-second window stack
was accompanied by **seven imagettes stacked onboard in pairs**. This
independently matches the retained `NEXP=14` subarray, `NEXP=2` imagette,
seven-imagette-per-CE joins and 4.449-second cadence.

Therefore the retained `gcoadd` **group size is resolved as two constituent
readouts**. The remaining operator uncertainty is narrower: pixel-level
normalization/weighting, clipping/saturation, numeric representation and
rounding remain unverified. No target-image pixel is opened.
[Exact-visit evidence](CHEOPS_GCOADD_GROUPING_EVIDENCE.md).

## 19 September public PIPE operator narrows the ground-calibration uncertainty

The pinned public PIPE implementation
(`alphapsa/PIPE@da15a87348e2657eac8dd08623ac258e6ac59df8`)
now supplies explicit executable semantics for several ground steps: gain then
bias, flat correction, optional CTI and non-linearity; flat interpolation in
stellar effective temperature; time-bracketed/interpolated dark selection; and
nearest-time bad-pixel-map selection. These rules are documented in
[CHEOPS_PIPE_OPERATOR_ASSESSMENT.md](CHEOPS_PIPE_OPERATOR_ASSESSMENT.md).

This is useful as an explicitly declared independent PIPE-based fallback, but
it does **not** resolve the onboard imagette operator. The pinned PIPE source
does not branch on the FITS `STACKING` keyword; it uses `NEXP` downstream.
Therefore PIPE cannot establish that `gcoadd` is a simple sum or define its
clipping/weighting/arithmetic semantics. The gain field/sign discrepancy also
remains. **NOT_READY_FOR_TARGET_IMAGE_STUDY** is unchanged.

## 19 September prospective CHEOPS native-study gate prepared and tested

While the physical calibration/operator inputs remain unresolved, the complete
prospective study skeleton is now prepared without opening any target-image
pixels. `CHEOPS_NATIVE_STUDY_DRAFT.md` and
`config/cheops_native_study_draft.json` predeclare the retained visit,
positive 30/60/100-second pulse family, protected-training rules and required
nuisance families. Numerical acceptance thresholds remain intentionally
`TBD_BEFORE_FREEZE` until the physical operator is established.

`scripts/cheops_native_input_gate.py` is a hard execution gate: it refuses
native-image work unless all three operator questions are VERIFIED, the four
required references have frozen SHA-256 identities plus native validity and
selection rules, the gain convention is adopted, the contract is science-ready,
and the study is explicitly FROZEN. The current contract is expected to fail.
A synthetic complete fixture must pass. Both behaviors are covered by
`tests/test_cheops_native_input_gate.py`; GitHub Actions run
`35458588162` passed both tests.

This preparation reduces future degrees of freedom but adds no scientific
result or observing coverage. **NOT_READY_FOR_TARGET_IMAGE_STUDY** remains in
force.

Updated 19 September 2026. This is the maintained operational entry point.
Earlier reports and continuation files preserve their historical states.

The [14–27 September work plan](TWO_WEEK_PLAN_2026-09-14.md) groups the next
background/residual model, both closed-sector comparisons and auditing into
one integrated study, followed by an explicit unused-data readiness decision.
Its dates are work windows. The original LS7I joint model, evaluation and audit
are complete; the subsequent instrumental-response work is tracked below.

## LS7Y audited image follow-up completed, 19 September

The separately frozen mission-delivered L2 route has now advanced beyond the
raw/imagette calibration dependency without pretending to solve it. LS7X
screened only the CHEOPS mission DEFAULT-aperture L2 light curve under the
predeclared 1/2/3-cadence rule and found **two positive clusters** (scores
**10.2766** and **9.1185**) with zero negative-control screens.

LS7Y then opened only the two predeclared 31-frame contexts in the corresponding
CAL and COR 200x200 subarray products: **39,680,000 image bytes**, plus 99,200
selected smearing-row bytes and a 5,760-byte extension header. No other
aperture, visit, raw imagette or neighboring frame was opened. The independent
image audit passes **492,926 numerical comparisons**.

The first cluster is **CORRECTION_LINKED** under the frozen descriptive gate:
the CAL→COR change removes more than half of its COR event excess in both
coordinate conventions, and the DELTA event map is strongly column-coherent
(0.8141). The second cluster is
**IMAGE_LOCALIZED_NOT_CORRECTION_DOMINATED**: its COR event excess remains
positive in both conventions, about 78% of the absolute event-map L1 norm lies
inside r<=25, and the fixed >=50% correction-dominance gate is not met.

These are diagnostic labels only. They do **not** classify either excursion as
astrophysical or artificial, do not qualify a detector, and add no observing
coverage. Cluster 0 needs no widening. Cluster 1 is the only justified narrow
continuation and should be characterized using the already published LS7Y
bytes before any additional science pixels are opened.
[LS7Y protocol](LS7Y_CHEOPS_L1_IMAGE_FOLLOWUP_PROTOCOL.md),
[result](results_ls7y_l1_followup/REPORT.md),
[audit](results_ls7y_l1_followup/audit.json).

The raw-imagette/native-calibration route remains a separate unresolved
dependency because exact `gcoadd`, LUT/flat and reference applicability are
still not established. LS7Y does not resolve that contract.

## 19 September auxiliary calibration assessment and study preparation

Matching-version common_sw schemas now constrain the exact **structure and
units** of the required flat, dark, bad-map and LUT product families. The
pinned public PIPE implementation also gives an independent reference for
Teff interpolation, detector slicing and `V_STRT_U`-based reference selection.
Because PIPE's calibration ordering differs from the official DRP architecture,
it is retained only as auxiliary evidence and is not used as a DRP 14.0.1
substitute.

The invariant parts of the prospective native-image experiment are now
predeclared: the retained visit, 30/60/100-second positive pulses, protected
training interval, nuisance families, no-retuning rule and decision semantics.
The state is **PREPARED_NOT_FROZEN — TARGET PIXELS CLOSED** until the exact
gcoadd/gain operators and required reference-file identities/applicability are
resolved.
[Auxiliary calibration assessment](LS7W_AUXILIARY_CALIBRATION_ASSESSMENT.md),
[study preparation](LS7W_NATIVE_STUDY_PREPARATION.md).

## 19 September LS7W bounded public-source follow-up completed

A second bounded public-source pass checked the official University of Vienna
CHEOPS-IASW lead, ESA's Data Products Definition, the CHEOPS mission paper,
the OBDP 2019 presentation, the exact RD-11 identifier/title, `gcoadd`, and
the exact dark/flat filenames. The public evidence confirms the operator family,
ordinary pixel-by-pixel window coaddition and the existence of an authoritative
RD-11 definition, but it still does **not** expose the exact `gcoadd` arithmetic
or the required native reference validity/selection rules.

The public-source route is therefore documented as
**PUBLIC_SOURCE_RESOLUTION_INCOMPLETE**. The prepared technical clarification
request remains **unsent** because person-directed contact has not been
authorized. This continues to block the raw-imagette/native-calibration route.
The separately frozen mission-delivered L2/CAL/COR route has since produced
the audited LS7X/LS7Y result above; do not use that result as a substitute for
the unresolved raw `gcoadd` contract.
[LS7W follow-up](LS7W_PUBLIC_SOURCE_FOLLOWUP.md).

## 19 September public IASW follow-up narrows the stacking dependency

The University of Vienna's official CHEOPS page now provides a concrete public
CHEOPS-IASW repository lead. ESA's Data Products Definition confirms the
distinct `coadd`, `mean`, `gmean`, `gcoadd` and `none` modes and assigns
their exact definitions to `CHEOPS-UVIE-INST-TN-001` issue 2.0. The CHEOPS
mission paper independently describes ordinary window stacking as pixel-by-pixel
coaddition. This resolves the existence/provenance of the onboard operator
family and the high-level ordinary `coadd` behavior, but **not** the exact
`gcoadd` arithmetic for the retained `NEXP=2` imagettes.

The public IASW source repository is now the primary operator lead. The exact
flight-relevant implementation/revision, gcoadd normalization/grouping and the
remaining offline calibration/reference applicability are still unresolved.
No target-image values have been opened. The combined decision remains
**NOT_READY_FOR_TARGET_IMAGE_STUDY**.
[Public-source assessment](CHEOPS_PUBLIC_IASW_ASSESSMENT.md),
[updated input contract](CHEOPS_REQUIRED_INPUTS.json).

## Immediate next action: external CHEOPS calibration clarification

The native image study needs version-relevant gain/units and the exact remaining
`gcoadd`/offline operator, plus verified flat, LUT, dark and bad-map inputs. A
public IASW repository is now identified, but the exact flight-relevant gcoadd
implementation has not yet been recovered. A complete
[technical request](CHEOPS_CALIBRATION_REQUEST.md) and
[exact-version manifest](CHEOPS_REQUIRED_INPUTS.json) are now prepared.
The official technical contact is verified, but the message is **unsent**
and no reply is pending. The owner can send the text or supply the needed
documentation/files directly.

This remains an input dependency for the **raw-imagette/native-calibration**
route. **LS7V remains the latest completed checkpoint for that calibration
contract**, while LS7Y is the latest bounded CHEOPS image-domain diagnostic.
On receipt of the missing physical inputs, verify the raw contract and freeze
one combined native study before raw-imagette evaluation.
[Operational restart](LS7V_CONTINUATION.md).

## LS7P reconstruction completed and verified, 15 September

The previously missing numerical package now has an explicit reconstruction:
**48,114/48,120** reference rows meet the fixed centroid rounding bound; all
**45,422 QUALITY=0** rows do. A fresh offline execution reproduces all 16
retained outputs byte-for-byte, and the independent scalar audit passes
**1,496,872 comparisons**. The seven known-answer tests and 695 source-file
identities also pass. All raw extracts, range receipts and unavailable PRF
cases are retained.

This establishes reproducible LS7P evidence, not recovery of the earlier
original run or verification of its claimed publication. The motion input
remains unqualified. No new target correction, pulse trial or observing
coverage is added. CHEOPS still needs the external inputs above; LS7V remains
its latest completed checkpoint. [Reconstruction result](results_ls7p_response/REPORT.md),
[verification](results_ls7p_reconstruction/README.md),
[historical reconciliation and addendum](LS7P_PUBLICATION_RECONCILIATION.md).

## LS7V explains the CAL electronics as defaults and refines the input contract

The actual **main_calibration.py 14.0.1** log for the retained CHEOPS visit
records default bias **563.43** and default RON **7.13 ADU/frame**. Both CAL/
COR constants match their binary32 representations exactly. The difference
investigated in LS7U is therefore explained as measured reference electronics
compared with chosen defaults; no margin estimator should be tuned to match it.

The log explicitly **skips the spatial bias-frame correction**, despite naming
BiasFrame V0109 in the input/header. That file is not required to reproduce an
unapplied correction. The scalar readout defaults are also now known. The dark
MAP correction, in contrast, was applied; its content and early-visit validity
still need resolving, along with the gain convention, gcoadd/offline operator,
flat and required PSF inputs.

The original log identity, seven reused source identities, 15 native-header
comparisons and both numeric matches pass. Fresh offline outputs reproduce
byte-for-byte. **No new data transfer or source trial is added**, and the
combined input remains **NOT_READY**. This resolves concrete requirements
without repeating the earlier numerical studies.
[Findings](LS7V_CALIBRATION_RECONCILIATION.md),
[evidence](results_ls7v_reduction_log/README.md),
[current continuation](LS7V_CONTINUATION.md).

## Earlier LS7U direct electronic-reference measurements completed

The retained CHEOPS visit's four-column virtual prescan gives **562.089864
ADU/readout bias** and **7.118046 ADU/readout effective noise**. This measures
native electronics directly. CAL agrees numerically within the fixed 1%
comparison under a per-readout ADU interpretation, but its bias lies well
outside the prescan's descriptive sampling interval; it is not reproduced.

The separately specified exploratory supplement checks the eight-column
BlankLeft extension actually read by PIPE. Its unchanged estimator gives
**562.071429 / 7.024590 ADU/readout** after clipping 5,284/691,200 reference
values. CAL noise is **1.500584% higher**, failing the same 1% comparison.
That alternative input does not explain the calibration-number difference.

All **1,036,800 electronic values**, the independent scalar calculations and
both original FITS checksums pass. Clean offline outputs reproduce byte-for-byte.
The new 4,164,480-byte transfer includes 4,147,200 electronic reference-array
bytes and 17,280 header bytes; **target-image bytes remain zero**.

The physical input stays **NOT_READY** pending the gain convention, gcoadd/
offline operator and exact spatial-reference content/applicability. No source
trial, recovery, candidate or qualified coverage is added. Reuse the completed
measurements and finish the missing input package before one prospective
native study. [Findings](LS7U_ELECTRONICS_FINDINGS.md),
[evidence](results_ls7u_prescan/README.md),
[current continuation](LS7U_CONTINUATION.md).

## Earlier LS7T native HK and calibration-contract audit completed

The actual **1,140-row HkExtended table** is acquired and verified using only
165,480 instrument/header bytes. PIPE's pinned gain reader uses the distinct
CCD-voltage field (about +34.81) in its temperature term; the actual temperature
is about −40 °C. On these native inputs, the unchanged reader's gain differs
from the centered-temperature diagnostic by a median **−0.57027%**, with at
most **9.134 ppm** after normalizing the ratio. LS7S's 8.129% was a different
conditional adapter comparison, not this native PIPE result.

The inspected mission sources disagree about the temperature-offset sign.
A separate issue is resolved: GAIN_0/BIAS_0/BIAS describe **onboard NLC**, and
both raw headers disable it. Those NaNs alone do not require reconstruction
of a disabled operation. Offline nonlinearity, gcoadd, CAL noise units and
exact reference contents/applicability still need a complete physical contract.

The 9,120 raw-field and 4,560 scalar-gain checks pass. Offline reconstruction
and diagnostic outputs reproduce byte-for-byte. **Native input remains
NOT_READY**; no image pixels, residual trials, source recoveries, candidates
or additional qualified coverage are added. Continue with the missing physical
inputs and one combined prospective study; do not repeat completed censuses.
[Findings](LS7T_CALIBRATION_CONTRACT.md), [evidence](results_ls7t_contract/README.md),
[current continuation](LS7T_CONTINUATION.md).

## Earlier LS7S electronic calibration audit completed; native input NOT_READY

The exact reference query finds **14/15 logged versions**. The small gain
V0109 reference is independently delivered by the official PIPE 1.1 package;
its 14,400 bytes, Git identity, FITS checksums, UTC validity and hardware match
pass. The mission-reference download was blocked by this session's browser
URL policy; no bytes from that attempted bundle were retained. The remaining
large/specialized calibration references still require supported delivery.

All **6,048 exposure rows** have NaN in GAIN_0, BIAS_0 and BIAS, while the
five voltage/temperature inputs are finite. Imagettes/subarrays carry distinct
**gcoadd/coadd** labels. The archived dark/bad-map starts are **8.3126 days
after** the observation; early-visit applicability is unresolved.

Two explicitly conditional gain-offset interpretations differ by about
**8.129% in absolute scale**, but only **1.025 ppm after median normalization**.
This is not an actual PIPE run, an adopted calibration, an upstream bug claim
or a measured astronomical fluctuation. The byte/scalar audit passes 87,696
field, 147 coefficient and 12,096 gain comparisons.

Next resolve the physical gain/coaddition/reference contract, then freeze
one combined protected calibration, pulse/nuisance and native-response study.
No science image, new candidate or additional qualified coverage is added.
[Findings](LS7S_CALIBRATION_FINDINGS.md), [reproduction](results_ls7s_calibration/README.md),
[current continuation](LS7S_CONTINUATION.md). LS7P reconciliation stays separate.

## Earlier LS7R CHEOPS input and temporal assessment completed

A concrete public visit is retained: **CH_PR300024_TG000301_V0300**, OBSID
**1015522**, 55 Cnc on 9 March 2020, pipeline **14.1.2**. Selection uses the
earliest of 31 public visits, before flux inspection. Exact HTTP byte ranges
establish access to 3,024 raw imagettes and 432 matching subarrays; only
**1,203,264 unique header/metadata bytes** were acquired, with **zero image
body bytes**. The five metadata tables contain 6,048 individual exposures,
3,024 imagette rows and three matching sets of 432 subarray rows.

Imagettes combine two 2.2-second exposures, with median cadence **4.449005 s**;
subarrays combine fourteen, with median cadence **31.145472 s**. Every CE join
agrees; four long gaps remain explicit. In the timestamp-only linear pulse
calculation, 30-second pulses wholly within a segment retain full peak in
imagettes versus **0.481837–0.963670** in subarrays on the sampled onset grid.
This is neither noisy injection recovery nor qualified observing coverage.

Calibration reference identities and processing steps are recorded. Raw
imagettes still require calibration; cosmic-ray processing is N/A in the COR
headers and the two-dimensional pixel map is visit-level. Next combine reference
validation, target-protected calibration/PSF/background development and one
joint pulse/nuisance/native-response protocol before image evaluation.
No detector or candidate is adopted. The range, FITS checksum, UTC/TT and
independent scalar-field/response checks pass.

[Findings](LS7R_CHEOPS_INPUT.md), [reproduction](results_ls7r_metadata/README.md),
[current continuation](LS7R_CONTINUATION.md). LS7Q's HiPERCAM obstacle remains
open. The separate LS7P reconstruction is now documented above; the earlier
original-run publication remains unverified. Unused TESS/M43 panels stay closed.

## Earlier LS7Q HiPERCAM metadata assessment; native pilot not ready

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

**Historical LS7P evidence correction:** at the LS7Q start, the public branch
contained the source freeze `f42aa216b25779d55cd1fabd25545d3277abcfa5` and
metadata, but not the result previously claimed in conversation. An explicit
15 September reconstruction now supplies verified numerical evidence; the
earlier original run and claimed publication remain unverified.
[Historical record and reconstruction addendum](LS7P_PUBLICATION_RECONCILIATION.md).
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
| LS research | LS8V rank-5 EC 12578-2107 complete and closed: 174 rows, 201 eligible windows, zero signed threshold crossings; independent audit passes. Earlier TESS_260647166 positive remains unresolved. Next: separately freeze rank-6 GJ 436 metadata/header preflight. [Current continuation](LS8V_CONTINUATION.md) |

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
