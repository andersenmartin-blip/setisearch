# LS7W prospective native-image study preparation — 19 September 2026

This document freezes the parts of the next CHEOPS study that are already
independent of the unresolved calibration inputs. It is **not** the final
experiment freeze. The study must not evaluate target-image pixels until the
blocking operator/reference fields below have exact values and provenance.

## Fixed observation

- Mission: CHEOPS
- File key: `CH_PR300024_TG000301_V0300`
- OBSID: 1015522
- Target label: 55 Cnc
- Observation date: 9 March 2020
- Public archive revision retained by LS7R: 3
- Overall DRP version: 14.1.2
- Calibration-module version in the retained log: 14.0.1
- Individual exposure duration: 2.20000004768372 s
- Raw imagettes: 3024, NEXP=2, STACKING=gcoadd, ROUNDING=0, NLIN_COR=false
- Raw subarrays: 432, NEXP=14, STACKING=coadd, ROUNDING=0, NLIN_COR=false
- Static raw imagette full-detector offset: (790, 256)
- Raw subarray full-detector offset: (715, 181)
- Raw imagette bounding shape: 50 x 50
- Raw subarray bounding shape: 200 x 200

No alternative visit may be substituted after target pixels are opened.

## Fixed scientific question

Test whether a strictly predeclared, target-protected reduction of the short-
cadence CHEOPS imagettes can recover injected **positive** optical pulses of
30, 60 and 100 seconds while keeping native/no-pulse nuisance controls within
the same fixed decision rule.

The study is a detector-development/qualification experiment on one retained
visit. It is not a blind survey and does not establish artificial origin.

## Fixed pulse family

Pulse widths are exactly 30 s, 60 s and 100 s. Injection occurs at the
individual-exposure level **before** any calibration or data-dependent
correction that is part of the final frozen operator.

The temporal support must use the already audited 6048 individual-exposure
intervals and the exact exposure-to-imagette/subarray joins from LS7R. Long
gaps remain gaps; no interpolation may create exposure time.

Pulse phase sampling must be frozen before native scoring. It may be denser
than LS7R's one-second diagnostic grid only if that denser grid is specified
before any target-image residuals are inspected. Pulse amplitude levels must
also be chosen prospectively from calibration/noise information rather than
from native event outcomes.

## Protected fitting rule

The putative pulse interval plus a predeclared guard region is excluded from
all local background/PSF parameter training for the assessed event. A model
may use data outside that protected interval only according to the final
frozen protocol.

The native realization under an injected pulse, event labels, injected flux
and post-injection residuals may not be used to select a threshold, PSF basis,
mask policy, nuisance filter or calibration option.

Any global parameters must be fitted without using the assessed event's
protected samples. Repeated uses of the same visit are not independent
astronomical observations and must not be reported as such.

## Calibration sequence to be finalized

The final implementation must explicitly name each numerical operator and
input hash for:

1. onboard stacking interpretation for the raw imagette values;
2. gain and bias conversion;
3. offline non-linearity;
4. dark correction and uncertainty;
5. flat-field correction;
6. bad/hot/saturated/telegraphic pixel handling;
7. PSF/background model and uncertainty;
8. any smear/CTI/environmental term used by the chosen estimator.

The current official high-level DRP order and the actual retained log constrain
this list, but the exact operators below remain unresolved. PIPE may be used
only as an independent comparison implementation, not silently as the DRP.

## Fixed nuisance families

The final study must include explicit controls for at least:

- native no-injection windows;
- hot/dead/telegraphic/saturated pixels;
- cosmic-ray-like compact events;
- PSF displacement and modest shape distortion;
- background/straylight changes;
- smear structure;
- readout/stack boundaries;
- data gaps and unavailable windows;
- pulses partly lost at gaps or product boundaries;
- calibration/reference uncertainty propagated according to the frozen model.

A nuisance family may be declared unavailable only with an explicit reason and
must remain visible in the final ledger. It may not be silently removed after
seeing outcomes.

## Decision semantics

The final freeze must define separately:

- signal-recovery requirements for every pulse width/amplitude cohort;
- false-acceptance requirements on native and synthetic nuisance controls;
- availability requirements;
- numerical/native prediction requirements;
- handling of missing or masked samples.

No threshold, margin, clipping level, mask class, pulse amplitude or model
complexity may be changed after the relevant evaluation ledger is exposed,
except to correct a demonstrated implementation error with an explicit
correction record. A failed fixed test remains a result; it does not trigger
an outcome-driven repair sequence.

## Blocking fields before final freeze

The following fields must be filled with exact, source-backed values before
target-image evaluation:

- `gcoadd_operator_source`: exact flight-relevant implementation or RD-11
  numeric definition for NEXP=2;
- `gain_operator_source`: exact DRP 14.0.1 temperature/housekeeping mapping
  and sign/centering convention;
- `lut100_sha256`: exact V0104 file identity and interpolation/domain rule;
- `flat_sha256`: exact V0104 file identity, valid Teff planes/status and
  coordinate/index convention;
- `dark_sha256`: exact V0201 file identity plus native validity interval and
  DRP selection rule;
- `badmap_sha256`: exact V0201 file identity plus native validity interval and
  DRP selection rule;
- `psf_input`: exact source or a prospectively justified PSF-independent
  alternative;
- final uncertainty propagation and saturation policy.

Until every mandatory field is resolved, the state is
**PREPARED_NOT_FROZEN — TARGET PIXELS CLOSED**.

## Already completed evidence to reuse

Do not repeat the completed LS7R timing census, LS7S reference inventory,
LS7T native-HK audit, LS7U electronics measurements, LS7V log reconciliation,
LS7P reconstruction, public IASW assessment or the new auxiliary calibration
source assessment unless a concrete inconsistency requires it.

The next valid state transition is either:

1. required physical documentation/files arrive and the complete experiment is
   frozen before target-image acquisition; or
2. the dependency remains unresolved and the project records that block without
   opening target pixels or substituting an unverified proxy.
