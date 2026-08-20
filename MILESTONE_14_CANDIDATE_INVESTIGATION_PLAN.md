# Milestone 14 post-hoc candidate-investigation plan

Status: **fixed after held-out result publication and before targeted cutout
inspection**.

This is a labelled post-hoc review of the five
`rfi_family_veto_pending_manual_review` clusters in the frozen Milestone 14
result. It cannot increase the held-out significance and does not change or
rerun detector v0.5.0.

## Frozen inputs

- preregistration commit `2d8a1d31aac0c650430094aabc7b2cef28c7bfc1`;
- result publication commit `ad36856607040189a39528cef3864466e5aefccf`;
- the five pending clusters at 1425.315276906, 1425.247347169,
  1425.134884380, 1425.360145234, and 1425.328830443 MHz; and
- the six original ON/OFF scans and frozen 1423.9-1426.1 MHz extraction range.

## Fixed targeted checks

For every candidate and every ON/OFF scan, the investigation will measure:

1. the S/N along the candidate's frozen predicted track;
2. the strongest stationary feature within plus/minus 100 Hz;
3. the strongest free-drift feature within the same interval for absolute drift
   no greater than 2 Hz/s;
4. all separated stationary peaks with S/N at least 5.5;
5. adjacent-OFF receiver-frame coincidences within the frozen 20 Hz tolerance;
   and
6. whether different pending planet-frame solutions map to the same receiver
   feature in at least two active epochs.

The run will also produce six-panel ON/OFF morphology figures for every case.

## Classification rule

- An adjacent-OFF coincidence, adjacent-OFF same-track S/N at least 5.5, or a
  cross-candidate receiver-frame alias is classified `RFI_OR_INSTRUMENTAL`.
- Failure to reproduce S/N 3 in every claimed active ON epoch is classified
  `NOT_REPRODUCED_BY_LOCAL_TRACK_CHECK`.
- Otherwise the case remains `UNRESOLVED_REQUIRES_INDEPENDENT_CADENCE`.

Arithmetic-family membership and selection of the widest boxcar remain context,
not sufficient physical vetoes. Cross-cadence searching is deliberately
deferred from this first morphology stage.

