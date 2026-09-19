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
