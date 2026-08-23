# Milestone 21 post-hoc candidate-investigation plan

Status: **fixed after held-out primary-result publication and before targeted
cutout inspection**.

This is a labelled post-hoc review of the two
`rfi_family_veto_pending_manual_review` clusters in the frozen Milestone 21
result. It cannot increase the held-out significance and does not change or
rerun detector v0.5.0.

## Frozen inputs

- preregistration commit `f9ae81203ae3bcf44c3c711a447b90322c06ba3b`;
- primary-result publication commit
  `2bbf6d86a1b205401c900aa2d8f4a8545fdb8b8a`;
- frozen configuration SHA-256
  `441597c69c1b3227648ee7aaf4bd6c8b0a09241c807755e03b355baa194b21e7`;
- frozen search-summary SHA-256
  `e098ed1cf2d73a785aa73ece68fc5a490aff80d35758917703b00ef23483dbf0`;
- two arithmetic-family cases at 1424.954541209 and 1424.964184756 MHz; and
- the six original ON/OFF scans and frozen 1423.7-1426.3 MHz extraction range
  for window `m21_1425p0`.

## Fixed targeted checks

For both cases and every ON/OFF scan, the investigation will measure:

1. the S/N along the candidate's frozen predicted track;
2. the strongest stationary feature within plus/minus 100 Hz;
3. the strongest free-drift feature within the same interval for absolute
   drift no greater than 2 Hz/s;
4. all separated stationary peaks with S/N at least 5.5; and
5. adjacent-OFF receiver-frame coincidences within the frozen 20 Hz tolerance.

The two cases will also be compared with each other for receiver-frame aliases,
and the run will produce one six-panel ON/OFF morphology figure per case. No
other reported cluster or frequency interval will be inspected in this stage.

## Classification rule

- An adjacent-OFF coincidence, adjacent-OFF same-track S/N at least 5.5, or
  cross-candidate receiver-frame alias is classified `RFI_OR_INSTRUMENTAL`.
- Failure to reproduce S/N 3 in every claimed active ON epoch is classified
  `NOT_REPRODUCED_BY_LOCAL_TRACK_CHECK`.
- Otherwise the case remains `UNRESOLVED_REQUIRES_INDEPENDENT_CADENCE`.

Arithmetic-family membership remains context, not a sufficient physical veto.
The frozen header-only screen found no second qualifying HD 154345 cadence.
Therefore an unresolved case must remain unresolved unless later public data
supply an independent observation; this review cannot establish recurrence by
itself.
