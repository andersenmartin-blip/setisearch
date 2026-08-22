# Milestone 16 independent-cadence result

**FINAL DISPOSITION: BOTH CASES NOT REDETECTED; NO SURVIVING CANDIDATE**

The two fixed Milestone 16 hypotheses were tested in the complete public GBT
L-band HD 219134 cadence `--65393`, beginning 2016-10-01 (MJD
57662.20481481482), approximately 40 days after the original cadence. The
independent sequence is A-B-A-C-A-D, providing three ON scans and three
distinct OFF-source scans.

The workflow completed successfully in GitHub Actions run `32570527391`.
Artifact `9475221592`, named `milestone-16-independent-followup`, has digest
`sha256:ed3f733fec7e2cc7681b99591d23a7306013ba308b006a3f3e10046028652cbf`.
All 12 extracted spectral slices and all four result files passed the published
SHA-256 manifests.

## Frozen-rule results

The preregistered persistence rule required candidate-track S/N at least 3.0
in at least two of three ON scans, with no qualifying OFF evidence. Neither
hypothesis reached S/N 3.0 in any independent ON scan.

| Case | Rest frequency (MHz) | ON candidate-track S/N | OFF candidate-track S/N | Disposition |
|---:|---:|---|---|---|
| 1 | 1412.485745177 | -0.134, 0.035, 0.599 | -1.032, 0.709, 0.234 | `NOT_REDETECTED_IN_INDEPENDENT_CADENCE` |
| 2 | 1425.136278570 | -2.348, 1.180, -1.009 | -1.656, -0.887, -0.330 | `NOT_REDETECTED_IN_INDEPENDENT_CADENCE` |

No stationary feature in either local follow-up window reached the fixed S/N
5.5 reporting floor. The largest bounded free-drift diagnostic was S/N 4.350;
under the frozen protocol, free-drift maxima cannot change a disposition.

## Combined disposition

The 1412.485745177 MHz primary survivor and the 1425.136278570 MHz
arithmetic-family review case are both absent in the earliest later complete
qualifying cadence. Milestone 16 therefore ends with no surviving candidate
and no technosignature claim.

This non-redetection is strong evidence against recurrence of the two exact
hypotheses, but it does not exclude an intermittent transmitter that was
inactive on 2016-10-01. This targeted follow-up is not a second blind search and
does not increase the original empirical global significance.

## Reproducible record

- Frozen plan: `MILESTONE_16_INDEPENDENT_CADENCE_PLAN.md`
- Frozen config: `config/hd219134h_m16_independent_followup.json`
- Analysis: `scripts/m16_independent_cadence_followup.py`
- Machine-readable result:
  `results_m16_independent_followup/independent_followup.json`
- Per-scan metrics: `results_m16_independent_followup/scan_metrics.csv`
- Diagnostic plots: `results_m16_independent_followup/candidate_*.png`
- Extract manifest: `DATA_MANIFEST_M16_INDEPENDENT_FOLLOWUP.sha256`
- Result manifest: `RESULTS_MANIFEST_M16_INDEPENDENT_FOLLOWUP.sha256`
