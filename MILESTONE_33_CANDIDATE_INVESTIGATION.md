# Milestone 33 candidate investigation

Status: **ONE UNRESOLVED CASE — A NEW INDEPENDENT CADENCE IS REQUIRED**.

The held-out Milestone 33 search reported one weak 1425 MHz cluster above the
frozen global threshold whose only automatic flag was arithmetic-frequency
family membership. This labelled post-hoc investigation applied the protocol
fixed in `MILESTONE_33_CANDIDATE_INVESTIGATION_PLAN.md`; it did not alter or
rerun the held-out detector.

## Reproducibility record

- GitHub Actions run: `32941363711`
- Artifact: `9596661263` (`milestone-33-candidate-investigation`)
- Artifact digest:
  `sha256:076f469c0d4b3fe3d6f89f244316149093f10b782d21243a4792345d44be11c1`
- Protocol commit: `8b1481d6fbeed1bf3bf857b2954af80ef519014c`
- Execution commit: `b911d172d417848cfc4354ef5f9382252538e772`
- Scope: six frozen cadence scans and plus/minus 100 Hz around the single case
- Receiver-frame coincidence tolerance: 20 Hz
- Adjacent-control qualifying peak and candidate-track floor: S/N 5.5

All six extracted-slice hashes and all four investigation-output hashes are
published. Raw cutouts are not committed.

## Frozen-rule disposition

| Planet-frame frequency (MHz) | Frozen S/N | Width | Active ON epochs | Post-hoc disposition |
|---:|---:|---:|---|---|
| 1424.934238381684 | 10.728838 | 33 channels | 1, 2, 3 | `UNRESOLVED_REQUIRES_INDEPENDENT_CADENCE` |

The frozen candidate track reproduces in every claimed active ON scan, and all
three adjacent controls remain below the post-hoc S/N 5.5 same-track floor:

| Epoch | ON track S/N | Strongest stationary ON S/N | OFF track S/N | Nearest qualifying stationary OFF peak |
|---:|---:|---:|---:|---|
| 1 | 7.6967 | 6.6622 | 4.2468 | S/N 5.5945, 173.226 Hz away |
| 2 | 6.4577 | 6.7020 | 4.7200 | none at S/N 5.5 or greater |
| 3 | 6.1943 | 5.9166 | 3.2022 | S/N 6.0908, 203.960 Hz away |

No qualifying adjacent-control peak lies within 20 Hz of its paired ON peak,
and there is no second candidate with which to form a receiver-frame alias.
The fixed rejection conditions therefore do not apply.

The primary search had already recorded aggregate control diagnostics of S/N
5.5463 at the frozen hypothesis and S/N 7.8263 for the best local recurrence
19.558 Hz away. Both were below the frozen primary global threshold of S/N
10.3294. The post-hoc protocol did not replace that threshold with a new
aggregate cutoff: its additional physical veto required a qualifying
single-control track or stationary-peak coincidence, and the six-scan check
found neither.

## Interpretation and boundary

Arithmetic-family membership, selection of the widest 33-channel boxcar, and
free-drift maxima are cautionary context only. None was a fixed physical veto.
The result is therefore unresolved, not a technosignature detection and not a
clean RFI classification.

The pre-contact header screen found no second qualifying public HD 3651
cadence. Independent recurrence cannot be tested with the available archive
data; resolving this exact hypothesis requires a new observation. The
machine-readable measurements and diagnostic figure are in
`results_m33_candidate_investigation/`.
