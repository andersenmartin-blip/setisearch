# Milestone 29 candidate investigation

Status: **BOTH MANUAL-REVIEW CASES RESOLVED AS RFI OR INSTRUMENTAL**.

The held-out Milestone 29 search reported two weak 1425 MHz clusters that
exceeded the frozen global threshold but initially had only
arithmetic-frequency-family triage flags. This labelled post-hoc investigation
applied the protocol fixed in
`MILESTONE_29_CANDIDATE_INVESTIGATION_PLAN.md`; it did not alter or rerun the
held-out detector.

## Reproducibility record

- GitHub Actions run: `32759225459`
- Artifact: `9532077277` (`milestone-29-candidate-investigation`)
- Artifact digest:
  `sha256:650d98b3fdb35125279f40c283ac2905cc5c320cefd7eef163740da5892e18f5`
- Protocol commit: `353b0dcf0a6bcb312bc1bb2ba8c4715d6576ea0e`
- Execution commit: `6f440e217615cdeca4fbc082d2d773d076dec190`
- Scope: six frozen cadence scans and plus/minus 100 Hz around each case
- Receiver-frame coincidence tolerance: 20 Hz
- Adjacent-control qualifying peak and candidate-track floor: S/N 5.5

All six extracted-slice hashes and all five investigation-output hashes are
published. Raw cutouts are not committed.

## Frozen-rule dispositions

| Case | Planet-frame frequency (MHz) | Frozen S/N | Post-hoc disposition | Decisive evidence |
|---:|---:|---:|---|---|
| 1 | 1425.239881686866 | 7.820419 | `RFI_OR_INSTRUMENTAL` | Same receiver feature as case 2 in all three ON epochs; epoch-3 control peak within 16.764 Hz. |
| 2 | 1425.223282724619 | 7.593387 | `RFI_OR_INSTRUMENTAL` | Same receiver feature as case 1 in all three ON epochs; epoch-3 control peak within 16.764 Hz. |

Although the two hypotheses have different planet-frame frequencies and
orbital templates, their strongest stationary ON features are identical in
every epoch: 1425.130957738, 1425.130756572, and 1425.130697899 MHz. This is
the fixed cross-candidate receiver-frame-alias condition.

The epoch-3 control contains a qualifying S/N 5.656707 stationary peak at
1425.130714662 MHz, 16.763806 Hz from the ON feature. That independently
satisfies the fixed adjacent-control coincidence rule. Candidate-track S/N in
all controls remains below 5.5, but only one physical RFI rule is required.

## Interpretation

Arithmetic-family membership and selection of the widest nine-channel
boxcar were context only and did not decide the outcome. The receiver-frame
identity and adjacent-control recurrence provide the physical evidence.

The header screen found no second qualifying HD 11964 cadence. No independent
archive test is therefore available or needed for these vetoed cases. Both
manual-review cases are closed; neither is a technosignature candidate.

Machine-readable measurements and diagnostic figures are in
`results_m29_candidate_investigation/`. The primary result remains a held-out
search with empirical p-value 1/257; this targeted review cannot increase that
significance.
