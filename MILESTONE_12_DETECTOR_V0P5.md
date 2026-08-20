# Milestone 12: detector v0.5

Status: complete. Detector-development acceptance passed on 2026-08-20.

## Outcome

Detector v0.5 repairs the three candidate-veto failure modes exposed by the labelled Milestone 11 LHS 1140 development set:

- local recurring OFF-source power under a different width, Doppler template, activity subset, or nearby frequency;
- a single adjacent OFF scan matching the candidate's own frequency track; and
- different planet-frame hypotheses that reconstruct the same strong receiver-frame feature.

All five formal M11 survivors now receive an explicit automated RFI/instrumental veto. Of the sixteen clusters previously held for arithmetic-family manual review, fourteen receive a specific v0.5 veto and two remain conservatively held for manual review. None are promoted to follow-up.

This is detector development on labelled data. It is not independent evidence and does not retroactively convert Milestone 11 into a new blind search.

## Fixed rules

The rules were committed in `MILESTONE_12_PREREGISTRATION.md` before the development validation:

1. multi-hypothesis OFF recurrence within +/-20 Hz, using the existing operational threshold and per-epoch recurrence floor;
2. exact candidate-track S/N >=5.5 in any adjacent active-epoch OFF scan; and
3. receiver-frame peaks within 20 Hz in at least two shared active epochs, with each local peak at S/N >=5.5 and searched within +/-100 Hz.

The rules are opt-in. A v0.4 configuration without `search.candidate_veto_v0p5` follows the old candidate path unchanged. The frozen v0.5 block is:

```json
"candidate_veto_v0p5": {
  "local_off_tolerance_hz": 20.0,
  "single_epoch_snr_floor": 5.5,
  "receiver_local_half_width_hz": 100.0,
  "receiver_alias_tolerance_hz": 20.0,
  "receiver_alias_minimum_shared_epochs": 2
}
```

## Development-set result

The validation reloaded the frozen M11 candidate product and rebuilt only the two relevant OFF spectral banks and ON receiver-frame diagnostics from the public raw filterbanks.

| Frozen M11 frequency (MHz) | v0.5 disposition | Decisive recorded evidence |
|---:|---|---|
| 1425.063540414 | `rfi_veto_local_off_source` | local OFF recurrence S/N 26.428; exact-track OFF max 8.352 |
| 1400.000458129 | `rfi_veto_local_off_source` | local OFF recurrence S/N 13.415; exact-track OFF max 12.159 |
| 1400.787219882 | `rfi_veto_receiver_frame_alias` | aliases reconstruct in at least two shared active epochs |
| 1400.826385722 | `rfi_veto_receiver_frame_alias` | aliases reconstruct in at least two shared active epochs |
| 1424.527517706 | `rfi_veto_single_adjacent_off` | exact-track OFF max 8.609 |

Across all 21 labelled development clusters:

- 5 were vetoed by local multi-hypothesis OFF recurrence;
- 6 were vetoed by a single adjacent-OFF track match;
- 8 were vetoed as receiver-frame template aliases; and
- 2 remain `rfi_family_veto_pending_manual_review` (1400.926242128 and 1400.826341018 MHz).

The two remaining manual flags are retained by design. Milestone 12 did not add or tune a fourth rule after seeing these outcomes.

## Verification

- 15 tests passed in Python 3.12: the original eight regressions and seven v0.5-focused tests.
- The focused controls cover all three veto modes, the five labelled formal failure modes, a clean candidate that must survive, v0.4 compatibility, and JSON-rehydrated null OFF diagnostics.
- The read-only GitHub Actions job completed successfully: run `32332843433`.
- The uploaded development evidence has SHA-256 `58ab3eaa0d83098ede81903f01d22704df5915d9b44e10c9992cc13e0601dde7`.

The machine-readable evidence is `results_m12/development_validation.json`.

## Scientific interpretation

Milestone 12 shows that v0.5 addresses the labelled M11 failure modes without rejecting its synthetic clean control. It does not estimate performance on independent observations. The detector is frozen at version 0.5.0 for the next held-out search.

Milestone 13 must commit its target, cadence, bands, thresholds, and complete v0.5 configuration before any selected spectral payload is inspected. No M12-driven retuning is permitted after that point.
