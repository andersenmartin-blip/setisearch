# Milestone 14 partial independent-cadence result

**Status: ALL THREE CANDIDATES NOT REDETECTED**

The preregistered targeted follow-up tested the three unresolved Milestone 14
hypotheses in the public 2016-07-15 GJ 687 `A-B-A-D` sequence, seven days
before the held-out search cadence. The workflow completed successfully and
the frozen config, script hashes, source identities, and detector tests all
passed before the spectral measurements were made.

## Reproducibility record

- GitHub Actions run: `32397569824`
- Artifact: `9417269325` (`milestone-14-independent-followup`)
- Artifact digest: `sha256:0ec200ac1a3bc671aadec334814df69ff42092722255bb8ee39b17ca83d6e8e6`
- Extracted-slice hashes: `DATA_MANIFEST_M14_INDEPENDENT_FOLLOWUP.sha256`
- Result hashes: `RESULTS_MANIFEST_M14_INDEPENDENT_FOLLOWUP.sha256`
- Complete ABACAD cadence: no; only `A-B-A-D` fine products are public

## Frozen-rule outcomes

| Original candidate | Rest frequency (MHz) | ON-1 track S/N | ON-2 track S/N | OFF-1 track S/N | Later OFF track S/N | Disposition |
|---:|---:|---:|---:|---:|---:|---|
| 1 | 1425.315276906 | 0.732 | 0.323 | -0.474 | 0.387 | Not redetected |
| 3 | 1425.134884380 | 1.187 | -0.478 | 0.963 | 0.384 | Not redetected |
| 5 | 1425.328830443 | 0.993 | 0.662 | 0.519 | -0.087 | Not redetected |

Both independent ON candidate-track S/N values had to reach 3.0 for a
persistence disposition. None did. Across all three hypotheses and four
scans, no local stationary peak reached the fixed S/N 5.5 qualifying floor;
consequently no 20 Hz ON/OFF receiver-frame coincidence rule fired.

## Combined Milestone 14 disposition

The original five weak arithmetic-family clusters are now resolved as follows:

- candidates 2 and 4: `RFI_OR_INSTRUMENTAL` from adjacent-OFF evidence in the
  original cadence;
- candidates 1, 3, and 5: `NOT_REDETECTED_IN_PARTIAL_INDEPENDENT_CADENCE`.

There is no surviving Milestone 14 candidate for immediate escalation and no
technosignature claim.

## Interpretive boundary

This non-redetection does not prove that the original fluctuations were RFI,
nor does it exclude an intermittent transmitter that was inactive on
2016-07-15. It is limited to two independent five-minute GJ 687 scans, the
three fixed hypotheses, and the sensitivity of this partial cadence. The
public archive contains no complete independent L-band GJ 687 ABACAD cadence
covering 1425 MHz. A new complete observation would be needed for a stronger
persistence constraint.

Machine-readable measurements and diagnostic figures are in
`results_m14_independent_followup/`.
