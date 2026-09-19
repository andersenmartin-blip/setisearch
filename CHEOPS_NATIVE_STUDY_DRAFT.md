# Prospective CHEOPS native-image study — draft, blocked

Prepared 19 September 2026 after LS7V, the completed LS7P reconstruction
publication, and the LS7W public-source follow-up. This document deliberately
does **not** freeze a detector or open target-image pixels. It defines the
remaining work so that the eventual native evaluation can be prospective.

## Hard gate before any target-image read

The study cannot move from `DRAFT_BLOCKED_ON_PHYSICAL_INPUTS` to `FROZEN`
until all three operator questions in `CHEOPS_REQUIRED_INPUTS.json` are
`VERIFIED`: gain/units, stacking plus offline nonlinearity, and reference
applicability. The exact LUT100 V0104, point-source flat V0104, dark V0201 and
bad-pixel map V0201 must be received with frozen SHA-256 identities, native
validity intervals and the version-relevant selection/interpolation rules.
The already retained gain V0109 also needs an adopted physical convention.

The executable gate in `scripts/cheops_native_input_gate.py` checks those
conditions and intentionally reads no science image. The companion machine-
readable draft is `config/cheops_native_study_draft.json`. With the present
contract it must exit `NOT_READY`.

## Raw imagette structural constraints fixed

The retained raw imagette representation is now additionally constrained by
matching-version schemas: `NEXP` means number of co-added measurements, the
image is uint32 ADU (the schema history explicitly says it was widened from
uint16 to hold stacked imagettes), and this visit has `ROUNDING=0` and
`NLIN_COR=false`. The final freeze may rely on these facts, but must not
replace the still-missing gcoadd clipping/overflow/invalid-pixel semantics with
an assumed simple sum.

## Exact-visit imagette grouping is now fixed

The same 9 March 2020 55 Cnc observation is described by Morris et al. (2021,
A&A 653 A173, DOI 10.1051/0004-6361/202140892). The paper states that imagettes
were stacked onboard **in pairs**, yielding seven imagettes per 14-readout
subarray. This matches the retained `NEXP=2` metadata and timing joins.
Accordingly, the final study must treat each delivered raw imagette as a
two-readout group. It must not assume the unresolved pixel arithmetic
(sum/normalization/weights/clipping/rounding) until that contract is verified.

## Public PIPE fallback now specified

A pinned public PIPE implementation has been audited separately in
`CHEOPS_PIPE_OPERATOR_ASSESSMENT.md`. It supplies a reproducible ground
calibration/reference-selection path for flat, dark and bad-map handling.
The final freeze may choose this path instead of reproducing DRP 14.0.1 only
if that choice is made prospectively and the remaining gain/gcoadd assumptions
are explicitly justified. PIPE itself does not inspect the `STACKING` keyword,
so it is not evidence for the onboard `gcoadd` contract.

## Fixed scientific skeleton

The retained visit remains `CH_PR300024_TG000301_V0300`, OBSID 1015522,
55 Cnc. Raw imagettes are `NEXP=2, STACKING=gcoadd`; raw subarrays are
`NEXP=14, STACKING=coadd`. No alternate visit is selected because of a
native outcome.

The positive transient family remains exactly **30, 60 and 100 seconds**.
Signals are positive only and must be injected before any data-dependent
correction or fit. Training/fitting must exclude the protected event interval,
and injection truth, event labels and the native outcome may not be inference
inputs or retuning signals.

The integrated experiment must cover calibration reconstruction, protected
PSF/background modelling, uncertainty propagation, pixel masks, exposure
integration and the declared nuisance families: compact cosmic-ray-like
events, hot/unstable pixels, PSF displacement/distortion, straylight/background
variation, smear/readout structure, instantaneous saturation/nonlinearity,
data gaps and compression-entity boundaries, edge/window effects, and lost or
partially sampled pulses.

## Still intentionally unfrozen

Numerical acceptance thresholds are **not** invented while the physical
operator is unresolved. Before the first target-image read, the final freeze
must replace every `TBD_BEFORE_FREEZE` endpoint with a numerical or explicit
categorical decision rule and must define the unavailable-window policy.

The freeze must also record the exact reference hashes, operator provenance,
software versions, input byte ranges, target-protected training regions and
the full injection/control ledger. After that freeze, no threshold, mask,
stacking interpretation, calibration convention or nuisance family may be
changed because of the native result.

## Current decision

**NOT_READY_FOR_TARGET_IMAGE_STUDY.** The remaining obstacle is physical
mission input, not an unfinished detector implementation. The public-source
route is documented in `LS7W_PUBLIC_SOURCE_FOLLOWUP.md`; the narrowly scoped
technical request remains prepared and unsent.
