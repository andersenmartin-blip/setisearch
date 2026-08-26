# Milestone 33 post-hoc candidate-investigation plan

Status: **FIXED AFTER HELD-OUT RESULT PUBLICATION AND BEFORE TARGETED CUTOUT
INSPECTION**.

This is a labelled post-hoc review of the sole
`rfi_family_veto_pending_manual_review` cluster in the frozen Milestone 33
result. It cannot increase the held-out significance and does not change or
rerun detector v0.5.0.

## Frozen inputs

- preregistration commit `e8f23e58e00cc57d26db03c06869ea3a2b06f5fa`;
- execution commit `5579899a1d86bfb302ec225073826e91f5f66c26`;
- result publication commit `fd5a11afdba3774554a3d55fcad2f82ee7be6569`;
- search-summary SHA-256
  `8bcc1b7fc2177d93b7a7ef47e7ec9bbe47e8ccc53d38fe7529ae49e389d8ab2b`;
- the one pending cluster at 1424.9342383816838 MHz; and
- the six original ON/control scans and frozen 1423.7--1426.3 MHz extraction
  range.

The frozen hypothesis is:

| Case | Rest frequency (MHz) | Held-out S/N | Scale | Phase | Width | Template | Active ON epochs |
|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 1424.9342383816838 | 10.728838 | 0.75 | +0.2 | 33 ch | 15 | 1, 2, 3 |

No frequency, template, phase, scale, spectral width, candidate, cadence,
scan, tolerance, or threshold may be added or changed after targeted spectral
contact.

## Fixed targeted checks

For the candidate and every ON/control scan, the investigation will measure:

1. the S/N along the candidate's frozen predicted track;
2. the strongest stationary feature within plus/minus 100 Hz;
3. the strongest free-drift feature within the same interval for absolute
   drift no greater than 2 Hz/s;
4. all separated stationary peaks with S/N at least 5.5; and
5. adjacent-control receiver-frame coincidences within the frozen 20 Hz
   tolerance.

The run will also produce a six-panel ON/control morphology figure. The
already reported arithmetic-family flag, 33-channel width, and sub-threshold
local-control feature are context only and cannot decide the classification.

## Classification rule

- An adjacent-control coincidence or adjacent-control same-track S/N at least
  5.5 is classified `RFI_OR_INSTRUMENTAL`.
- Failure to reproduce S/N 3 in any claimed active ON epoch is classified
  `NOT_REPRODUCED_BY_LOCAL_TRACK_CHECK`.
- Otherwise the case remains `UNRESOLVED_REQUIRES_INDEPENDENT_CADENCE`.

Free-drift maxima and visual impression cannot change a disposition.

## Independent-cadence boundary

The pre-contact header screen found no second qualifying HD 3651 cadence.
This morphology stage therefore cannot test independent recurrence. Any case
that remains unresolved requires a new observation; it is not a detection or
technosignature claim.
