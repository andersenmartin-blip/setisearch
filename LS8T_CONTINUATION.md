# Continue after LS8T

The fixed TESS_260647166 paired-image stage is **complete and audited**.
The negative comparison is **SPATIALLY_STRUCTURED**. The positive
TG015701_P0 remains **UNRESOLVED_WITHIN_FIXED_SCOPE**. Image result commit:
`3e0bd85cee4b191f4bbe82b499977976c1b1484a`.

LS8S retained one positive and one negative cluster among **2,004 eligible
overlapping windows**. Its six positive crossings describe overlapping
windows around one event, not six separate detections. No event is promoted
to a qualified SETI candidate; no detector or observing coverage is qualified.

## Both signed outcomes remain fixed

DELTA is COR minus CAL. Ratios below use the original signed source-aperture
sums in both coordinate conventions. They are not fractions of physical cause.

| Representative | Original L2 score | Duration | DELTA/COR C0 / C1 | COR brightness explained C0 / C1 | COR displacement explained C0 / C1 | Fixed label |
|---|---:|---:|---:|---:|---:|---|
| TG000101_N0 | -10.085104590 | 3 × 42 = 126 s | 0.456591 / 0.459536 | 0.09607% / 0.09494% | 92.95567% / 92.96205% | SPATIALLY_STRUCTURED |
| TG015701_P0 | +45.460348286 | 49 s | -0.089065 / -0.092531 | 2.69041% / 2.67304% | 75.76422% / 75.77892% | UNRESOLVED_WITHIN_FIXED_SCOPE |

All four source apertures are complete, with valid COR denominators and
signs matching their original L2 selections. Neither event passes the
correction gate: direct and column-projected absolute ratios are below
0.5 in both conventions. The column-projected ratios are 0.452273 / 0.454798
for the negative and -0.149857 / -0.155226 for the positive.

The negative passes the original spatial gate: its displacement model
explains more than 80% of COR event-map energy and exceeds the brightness
model by at least 0.2 in both conventions. That label describes morphology;
it does not uniquely identify the physical cause.

The positive's displacement fit explains approximately **75.8%**, below the
required 80% in **both** conventions. Preserve that failure without rounding
up, switching convention or lowering the threshold. Its pure-brightness
model explains only approximately **2.7%**. A large L2 score therefore does
not by itself establish a coherent source-brightness change, artificial
origin or a calibrated significance. All four smearing fits are rank
deficient and remain explicitly unavailable.

## Concrete remaining limitation

The positive's unresolved label comes from the **fixed image model**, not
missing source bytes, incomplete apertures or uncertain exposure joins.
The combined unweighted brightness/gradient/constant fit explains
**77.27903% / 77.38110%** of its COR event-map energy. The present diagnostic
does not measure how its remaining residual compares with local
49-second variability, or how that residual is distributed within the
unchanged aperture. Those are the specific unanswered questions.

The full-frame figures retain CAL, COR and DELTA on a common signed scale
for each event, plus both apertures. Both checksum-verified figures were
visually inspected. Appearance supports examining residual structure but
does not set a new mask, model, classification or physical-cause claim.

## Scope and independent verification

Metadata joins and payload were frozen separately. The metadata-only stage
verified **120 unique CAL/COR joins and 556 exact checks** for all 60 fixed
context rows, before any image values. TG000101_N0 retains rows 303:334
with event rows 317–319; TG015701_P0 retains rows 203:232 with event row 217.
NEXP=1 in both visits, with their separate 42-/49-second exposure times.

Exactly **38,400,000 image bytes plus 96,000 smearing bytes** were acquired
in the six frozen ranges. Each request succeeded on its first attempt.
Raw compressed ranges, receipts, checksums, native maps and complete signed
diagnostics remain preserved. No extra visit, aperture or raw imagette was
opened, and no prior residual model became a screen cut.

All **nine pre-payload image tests** pass, including both signs and the
native one/three-exposure sums. The independent struct/long-double/scalar
audit passes **189,074 numerical comparisons and 321,180 exact checks**,
with zero disagreements at unchanged tolerances. LS8S separately passes
both stable-arithmetic tests and all **24,048 numerical/discrete checks**.
These counts verify reproducibility; they are not independent observations
or a sensitivity/false-alarm calibration.

## Next action: one bounded retained-data residual/noise study

The original LS8T image stage stops here. Before any new native-derived
calculation, publish a separate protocol that fixes the following integrated
study. It has **not yet been executed**.

1. Use only the two already retained contexts, their original event sums,
   both CAL/COR products and both C0/C1 conventions. Keep the negative
   spatially structured comparison alongside the positive unresolved event.
   Preserve original masks, sidebands, guards, score thresholds and labels.
2. Quantify the positive's remaining spatial residual and local noise
   reference, including energy concentration within the full fixed aperture
   and paired CAL/COR/DELTA accounting. Do not select or delete pixels after
   viewing them. Keep signed cross terms when comparing product energies.
3. Freeze duration-matched held-sideband controls and their training rules.
   The positive is a one-exposure 49-second event; the comparison sums three
   42-second exposures and needs an explicit temporal covariance treatment.
   Do not silently transfer an IID or one-row calibration to that sum, pool
   different cadences as equivalent trials, or call dependent control ranks
   false-alarm probabilities.
4. Include both signs in synthetic signal-protection controls and quantify
   any brightness loss from a hypothetical nuisance subtraction. Freeze
   arithmetic, all outputs, independent reconstruction and tolerances before
   the retained native study. No new correction or veto is adopted from it.
5. Publish every result and residual figure, preserve any failure, state the
   remaining uncertainty and stop after this single bounded study. Its
   descriptive results do not replace either original LS8T label.

Rank-5 **EC 12578-2107** remains the next independent CHEOPS target after
this bounded follow-up. Its selected pair is CH_PR100002_TG008901_V0300 and
CH_PR100002_TG008902_V0300 in the unchanged reconciled ledger; its headers
and science values remain unopened and require their own later freezes.
Do not reorder the cohort list or repeat the census based on this event.

Standing research/publication authorization continues without a new
per-stage permission request; collaboration remains deferred. Closed
HD 136352/GJ 1132/WASP-189 studies, reserved TESS/M43 data and the unsent
raw-imagette calibration request remain unchanged. TESS_260647166 here
names CHEOPS products, and the separate calibration gate remains NOT_READY.

[Image report and both figures](results_ls8t_images/REPORT.md) ·
[Independent image audit](results_ls8t_images/audit.json) ·
[L2 result and scope](LS8S_CONTINUATION.md) ·
[Frozen image protocol](LS8T_PAIRED_IMAGE_PROTOCOL.md) ·
[Publication identities](PUBLICATION_2026-09-20_LS8S_LS8T.md).
