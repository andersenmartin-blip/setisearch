# Milestone 18 post-hoc candidate-investigation plan

Status: **fixed after held-out result publication and before targeted cutout
inspection**.

This is a labelled post-hoc review of all four
`rfi_family_veto_pending_manual_review` clusters in the frozen Milestone 18
result. It cannot increase the held-out significance and does not change or
rerun detector v0.5.0.

## Frozen inputs

- preregistration commit `5f4ff886919465d2701dc4b4d3db34175f8d3db6`;
- primary-result publication commit
  `48f27ba779829cfd27a72cae35476a8d8b26f9a9`;
- frozen search-summary SHA-256
  `63e8a0d84e3e0940428a29717296e86d5096ee20b5a61cec933bc8ad65b75851`;
- four arithmetic-family cases at 1425.213204339, 1425.144117298,
  1425.201303731, and 1425.191166806 MHz; and
- the six original ON/OFF scans and frozen 1423.7-1426.3 MHz extraction range.

## Fixed targeted checks

For all four cases and every ON/OFF scan, the investigation will measure:

1. the S/N along the candidate's frozen predicted track;
2. the strongest stationary feature within plus/minus 100 Hz;
3. the strongest free-drift feature within the same interval for absolute drift
   no greater than 2 Hz/s;
4. all separated stationary peaks with S/N at least 5.5;
5. adjacent-OFF receiver-frame coincidences within the frozen 20 Hz tolerance;
   and
6. whether different planet-frame cases map to the same receiver feature in at
   least two shared active epochs.

The run will also produce six-panel ON/OFF morphology figures for every case.

## Classification rule

- An adjacent-OFF coincidence, adjacent-OFF same-track S/N at least 5.5, or a
  cross-candidate receiver-frame alias is classified `RFI_OR_INSTRUMENTAL`.
- Failure to reproduce S/N 3 in every claimed active ON epoch is classified
  `NOT_REPRODUCED_BY_LOCAL_TRACK_CHECK`.
- Otherwise the case remains `UNRESOLVED_REQUIRES_INDEPENDENT_CADENCE`.

Arithmetic-family membership and selection of a wider boxcar remain context,
not sufficient physical vetoes. The corrected header-only screen contains no
second qualifying GJ 649 cadence. Therefore an unresolved case must remain
unresolved unless later public data supply an independent observation; this
review cannot establish recurrence by itself.
