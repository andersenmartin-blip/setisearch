# LS7V: the CAL electronics are logged defaults

Completed 15 September 2026 for CHEOPS `CH_PR300024_TG000301_V0300`, OBSID
1015522. **The discrepancy investigated in LS7U is now explained at the
provenance level:** the visit's calibration program used default bias and
read-noise values. It also explicitly skipped the spatial bias-frame
correction. These are concrete changes to the input contract; a target-image
study remains pending the other physical inputs.

This is a forensic reading of an existing reduction log, not a new blind
experiment or a new measurement of the star. The full original log was
retained in the LS7S clean-reproduction cache. Its 60,868 bytes match the
SHA-256 and HTTP object identity recorded by LS7R. This packet preserves it
losslessly; only calibration lines 75–96 are analyzed.
[Scope](LS7V_SCOPE.md), [selected original messages](results_ls7v_reduction_log/selected_calibration_lines.json),
[provenance](results_ls7v_reduction_log/provenance.json).

## What the executed calibration reports

The overall reduction was version 14.1.2, while these messages come from
**main_calibration.py 14.0.1**. Its observation ID, 230,000 Hz main-channel
readout, script 6 and ordinary coadd label match the retained RAW, CAL and
COR subarray headers. The log identifies bright read mode and reports CCD
temperature −40.000 °C rounded to −40 °C for the default selection.

| Calibration evidence | What it establishes |
|---|---|
| Defaults selected for the recorded readout configuration | CAL's electronics values are defaults rather than a prescan estimator that LS7U should reproduce |
| Bias 563.43 and RON 7.13, explicitly labelled ADU/frame | Units are documented in the log despite absent unit cards in the two metadata columns |
| Spatial bias-frame correction skipped | A reference named in a header/input list was not necessarily applied |
| Gain approximately 2.0 electrons/ADU; linearization logged | These stages ran, but the approximate gain does not identify its exact formula |
| Dark mode MAP, named V0201 file, pixel correction completed | The dark map was applied; its content and applicability remain relevant |
| Flat-field correction step logged; header completed | Flat calibration is still part of the executed path |

The two recorded constants match the binary32 representations of the logged
decimal defaults **exactly**, when represented as Python floats:

| Field | Logged default | Saved CAL/COR value | Binary32 bits |
|---|---:|---:|---|
| BIAS | 563.43 ADU/frame | 563.4299926757812 | `440cdb85` |
| RON | 7.13 ADU/frame | 7.130000114440918 | `40e428f6` |

LS7S already verified that each field is constant across 432 CAL rows and
equal to COR. That row census is reused. This representation check explains
the tiny decimal tails; it does not prove the program's internal numeric
type or reproduce its complete processing.

## How this changes the interpretation of LS7U

The fixed prescan measurement remains **562.089864418 ADU/readout bias** and
**7.118045642 ADU/readout effective noise**. The separately scoped original
PIPE blank-reference calculation remains **562.071428571 / 7.024590259**.
All original intervals, estimator choices and agreement labels remain intact.

CAL is 1.340128258 ADU above the primary bias, outside the descriptive
resampling interval. Its RON is inside the corresponding noise interval.
These comparisons now have a documented interpretation: **measured reference
electronics versus chosen defaults**. The failed 1% RON comparison for the
PIPE supplement is not evidence that the same estimator was reproduced
incorrectly. No further margin or clipping adjustment is justified by a wish
to match CAL.

The literal logged unit is ADU/frame. LS7U's independent measurements support
interpreting its scale per constituent readout. The complete nonlinear and
stacking operator still needs version-relevant documentation; this log does
not define the imagette `gcoadd` operation.

## Revised physical requirements

The scalar default bias and noise used for this visit are now known. The
ReadOut V0101 file is no longer needed merely to discover those two numbers.
Other readout details may still be required by a future operator, and the
actual uncertainty model must be specified before native evaluation.

The BiasFrame V0109 reference appears in the CAL/COR header, yet its spatial
correction was skipped. Its content is therefore **not required to replay
that unapplied correction**. This does not establish that physical
pixel-dependent bias is negligible for a different raw-image estimator;
such a model must still justify its treatment before evaluation.

The dark reference was explicitly applied in MAP mode. Its archived start
remains 8.3126 days after this early observation. Neither its exact contents
nor the version-relevant applicability rule is recovered by this log. That
question must remain open. The flat and offline LUT contents, exact gain
convention, imagette gcoadd and any required PSF reference remain unresolved.

The approximate gain message must not be used to select a gain convention
by assuming an unseen rounding implementation. The CAL/COR image headers
still label their images ADU; a gain-conversion log line alone does not
establish the final image-unit semantics. No CAL/COR image values were read.

The earlier [primary DRP description](https://arxiv.org/abs/1909.08363) provides
general calibration context; this reconciliation relies on the **actual
visit's log**, which documents its selected path. Generic descriptions and
lists of available references cannot replace that execution evidence.

## Verification and next work

The original log identity and seven reused source identities pass. All
15 observation/readout/header comparisons agree, and both default-value
representations match exactly. A fresh offline execution reproduces the
summary and selected-message files byte-for-byte. No historical row or
margin census is repeated.
[Executable evidence](results_ls7v_reduction_log/README.md),
[verification](results_ls7v_reduction_log/reproduction.json).

**NOT_READY_FOR_TARGET_IMAGE_STUDY** remains the combined decision, with
fewer unresolved requirements. No new transfer, electronic margin, target
image, native source trial, recovery, candidate or qualified observing time
is added. Next obtain the remaining physical documentation/reference package
and then freeze one combined protected calibration, pulse, nuisance and
native-prediction study.
[Updated contract](results_ls7v_reduction_log/calibration_contract.json),
[continuation](LS7V_CONTINUATION.md).
