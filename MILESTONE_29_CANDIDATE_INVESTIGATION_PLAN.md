# Milestone 29 post-hoc candidate-investigation plan

Status: **FIXED AFTER HELD-OUT RESULT PUBLICATION AND BEFORE TARGETED CUTOUT
INSPECTION**.

This is a labelled post-hoc review of the two
`rfi_family_veto_pending_manual_review` clusters in the frozen Milestone 29
result. It cannot increase the held-out significance and does not change or
rerun detector v0.5.0.

## Frozen inputs

- preregistration commit `ee8ba852a33d6c96b560649a0eca9e8038a6e5c7`;
- execution commit `0c8977a971cf386933e8e2e23bb9f3d9b8ba0339`;
- result publication commit `3285fcaaae0d499542c3c7079419b4d3c78a2c13`;
- search-summary SHA-256
  `6537513cfc08f875328b9fc7887e95a1d130adbad5c14ebc2409b59d316d6ad9`;
- the two pending clusters at 1425.2398816868663 and
  1425.2232827246190 MHz; and
- the six original ON/control scans and frozen 1423.7-1426.3 MHz extraction
  range.

The frozen hypotheses are:

| Case | Rest frequency (MHz) | Held-out S/N | Scale | Phase | Width | Template | Active ON epochs |
|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 1425.2398816868663 | 7.820419 | 0.25 | -0.2 | 9 ch | 1 | 1, 2, 3 |
| 2 | 1425.2232827246190 | 7.593387 | 0.50 | -0.2 | 9 ch | 6 | 1, 2, 3 |

No frequency, template, phase, scale, spectral width, candidate, cadence,
scan, tolerance, or threshold may be added or changed after targeted spectral
contact.

## Fixed targeted checks

For every candidate and every ON/control scan, the investigation will measure:

1. the S/N along the candidate's frozen predicted track;
2. the strongest stationary feature within plus/minus 100 Hz;
3. the strongest free-drift feature within the same interval for absolute
   drift no greater than 2 Hz/s;
4. all separated stationary peaks with S/N at least 5.5;
5. adjacent-control receiver-frame coincidences within the frozen 20 Hz
   tolerance; and
6. whether the two pending planet-frame solutions map to the same receiver
   feature in at least two active epochs.

The run will also produce six-panel ON/control morphology figures for both
cases.

## Classification rule

- An adjacent-control coincidence, adjacent-control same-track S/N at least
  5.5, or a cross-candidate receiver-frame alias is classified
  `RFI_OR_INSTRUMENTAL`.
- Failure to reproduce S/N 3 in any claimed active ON epoch is classified
  `NOT_REPRODUCED_BY_LOCAL_TRACK_CHECK`.
- Otherwise the case remains `UNRESOLVED_REQUIRES_INDEPENDENT_CADENCE`.

Arithmetic-family membership and selection of the widest boxcar remain
context, not sufficient physical vetoes. Free-drift maxima and visual
impression cannot change a disposition.

## Independent-cadence boundary

The pre-contact header screen found no second qualifying HD 11964 cadence.
This morphology stage therefore cannot test independent recurrence. Any case
that remains unresolved requires a new observation; it is not a detection or
technosignature claim.
