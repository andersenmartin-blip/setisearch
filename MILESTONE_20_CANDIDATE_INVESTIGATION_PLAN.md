# Milestone 20 post-hoc candidate-investigation plan

Status: **fixed after held-out primary-result publication and before targeted
cutout inspection**.

This is a labelled post-hoc review of the sole
`rfi_family_veto_pending_manual_review` cluster in the frozen Milestone 20
result. It cannot increase the held-out significance and does not change or
rerun detector v0.5.0.

## Frozen inputs

- preregistration commit `fd3113be7ba8ff4a568f3b79921800a1be039d97`;
- primary-result publication commit
  `6058d5eef5229efec7399c7b3821aaa0ff5be371`;
- frozen configuration SHA-256
  `d631241a0b55c8a0c3f81d795ad19e2ccb4946918d57431d2817bc785a591696`;
- frozen search-summary SHA-256
  `40365a16ad417ba00d0904cc67fd0f4c31e65f1197fe044bb7dd9927846aab9f`;
- one arithmetic-family case at 1400.196827972 MHz; and
- the six original ON/OFF scans and frozen 1399.7-1401.3 MHz extraction
  range for window `m20_1400p5`.

## Fixed targeted checks

For the case and every ON/OFF scan, the investigation will measure:

1. the S/N along the candidate's frozen predicted track;
2. the strongest stationary feature within plus/minus 100 Hz;
3. the strongest free-drift feature within the same interval for absolute
   drift no greater than 2 Hz/s;
4. all separated stationary peaks with S/N at least 5.5; and
5. adjacent-OFF receiver-frame coincidences within the frozen 20 Hz tolerance.

The run will also produce a six-panel ON/OFF morphology figure. No other
reported cluster or frequency interval will be inspected in this stage.

## Classification rule

- An adjacent-OFF coincidence or adjacent-OFF same-track S/N at least 5.5 is
  classified `RFI_OR_INSTRUMENTAL`.
- Failure to reproduce S/N 3 in every claimed active ON epoch is classified
  `NOT_REPRODUCED_BY_LOCAL_TRACK_CHECK`.
- Otherwise the case remains `UNRESOLVED_REQUIRES_INDEPENDENT_CADENCE`.

Arithmetic-family membership and selection of the widest boxcar remain
context, not sufficient physical vetoes. The frozen header-only screen found
no second qualifying rho CrB cadence. Therefore an unresolved case must remain
unresolved unless later public data supply an independent observation; this
review cannot establish recurrence by itself.
