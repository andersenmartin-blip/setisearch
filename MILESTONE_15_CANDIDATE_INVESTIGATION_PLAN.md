# Milestone 15 post-hoc candidate-investigation plan

Status: **fixed after held-out result publication and before targeted cutout
inspection**.

This is a labelled post-hoc review of the two
`rfi_family_veto_pending_manual_review` clusters in the frozen Milestone 15
result. It cannot increase the held-out significance and does not change or
rerun detector v0.5.0.

## Frozen inputs

- preregistration commit `0538ed4be0407eb2397d3b1e1d676fdf7fb8e08b`;
- result publication commit `24bf1d0088450340142149c66ef1e5f4820561eb`;
- pending clusters at 1406.118344073 and 1406.118273185 MHz; and
- the six original ON/OFF scans and frozen 1405.2-1407.8 MHz extraction range.

## Fixed targeted checks

For every candidate and every ON/OFF scan, the investigation will measure:

1. the S/N along the candidate's frozen predicted track;
2. the strongest stationary feature within plus/minus 100 Hz;
3. the strongest free-drift feature within the same interval for absolute drift
   no greater than 2 Hz/s;
4. all separated stationary peaks with S/N at least 5.5;
5. adjacent-OFF receiver-frame coincidences within the frozen 20 Hz tolerance;
   and
6. whether the two pending planet-frame solutions map to the same receiver
   feature in at least two active epochs.

The run will also produce six-panel ON/OFF morphology figures for both cases.

## Classification rule

- An adjacent-OFF coincidence, adjacent-OFF same-track S/N at least 5.5, or a
  cross-candidate receiver-frame alias is classified `RFI_OR_INSTRUMENTAL`.
- Failure to reproduce S/N 3 in every claimed active ON epoch is classified
  `NOT_REPRODUCED_BY_LOCAL_TRACK_CHECK`.
- Otherwise the case remains `UNRESOLVED_REQUIRES_INDEPENDENT_CADENCE`.

Arithmetic-family membership and selection of the widest boxcar remain
context, not sufficient physical vetoes. Cross-cadence archive work is
deliberately deferred from this first morphology stage.
