# Milestone 16 post-hoc candidate-investigation plan

Status: **fixed after held-out result publication and before targeted cutout
inspection**.

This is a labelled post-hoc review of the sole automated follow-up survivor and
the sole `rfi_family_veto_pending_manual_review` cluster in the frozen
Milestone 16 result. It cannot increase the held-out significance and does not
change or rerun detector v0.5.0.

## Frozen inputs

- preregistration commit `287defd3aaabbb54278d74fcfc086abaf83ca48a`;
- result publication commit `059dbdee54bb658a6d8e25903a287ede23a9d655`;
- automated survivor at 1412.485745177 MHz;
- manual RFI-family case at 1425.136278570 MHz; and
- the six original ON/OFF scans and frozen 1411.2-1413.8 and
  1423.7-1426.3 MHz extraction ranges.

## Fixed targeted checks

For both cases and every ON/OFF scan, the investigation will measure:

1. the S/N along the candidate's frozen predicted track;
2. the strongest stationary feature within plus/minus 100 Hz;
3. the strongest free-drift feature within the same interval for absolute drift
   no greater than 2 Hz/s;
4. all separated stationary peaks with S/N at least 5.5;
5. adjacent-OFF receiver-frame coincidences within the frozen 20 Hz tolerance;
   and
6. whether the two planet-frame solutions map to the same receiver feature in
   at least two shared active epochs.

The run will also produce six-panel ON/OFF morphology figures for both cases.

## Classification rule

- An adjacent-OFF coincidence, adjacent-OFF same-track S/N at least 5.5, or a
  cross-candidate receiver-frame alias is classified `RFI_OR_INSTRUMENTAL`.
- Failure to reproduce S/N 3 in every claimed active ON epoch is classified
  `NOT_REPRODUCED_BY_LOCAL_TRACK_CHECK`.
- Otherwise the case remains `UNRESOLVED_REQUIRES_INDEPENDENT_CADENCE`.

Arithmetic-family membership and selection of the widest boxcar remain
context, not sufficient physical vetoes. The corrected header-only screen has
already established that additional HD 219134 cadences exist, but selecting or
examining one is deliberately deferred until this morphology result is fixed.
