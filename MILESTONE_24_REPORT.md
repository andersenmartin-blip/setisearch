# Milestone 24 report: 16 Cyg B held-out detector-v0.5 search

Status: **NO SURVIVING CANDIDATE; ALL NINE OVER-THRESHOLD CLUSTERS ARE VETOED BY OFF-SOURCE EVIDENCE**.

Milestone 24 applied frozen detector v0.5.0 to the sole complete compatible
GBT L-band 16 Cyg B cadence `--67109`. 16 Cyg B b supplies only the motion
template; the search does not assume that an emitter is located on the planet.

GitHub Actions run `32654162679` completed all detector tests, the repeated
630-case extraction-coverage proof, 30 HDF5 extractions, five searches, 256
global scrambles, and the preregistered completeness study. Artifact
`9497195728`, named `milestone-24-held-out-results`, has verified digest
`sha256:f716689a6e7ee963b16b400186e47761d853c71afa15aa6416f6b99530ad96a5`.
All nine result files match `RESULTS_MANIFEST_M24.sha256`; the data manifest
contains the expected 30 extracted-slice hashes. Raw slices were not
published.

## Global result

Across approximately **601,293,840** nominal
frequency/orbit/activity/width trials:

- observed global maximum: **S/N 54.269129** at 1400.117483467 MHz;
- scrambled-null median: **S/N 6.619889**;
- scrambled-null 99th percentile and operational threshold:
  **S/N 40.339649**;
- empirical global p-value: **1/257 = 0.00389105**; and
- final frozen disposition: **matched OFF-source RFI; no survivor**.

The low empirical rank does not imply an astrophysical or artificial origin.
The maximum is stronger at the exact matched hypothesis in OFF data, S/N
63.784939. The OFF global maximum is S/N 66.045646.

## Window results

| Window | ON maximum S/N | Frequency (MHz) | Width | OFF-global S/N | Empirical p | Frozen maximum disposition |
|---|---:|---:|---:|---:|---:|---|
| 1400.0-1401.0 | 54.269 | 1400.117483467 | 9 | 66.046 | 0.003891 | matched OFF source |
| 1406.0-1407.0 | 6.550 | 1406.222603709 | 9 | 7.547 | 0.027237 | below global threshold |
| 1412.0-1413.0 | 6.095 | 1412.677869573 | 1 | 5.578 | 0.132296 | below global threshold |
| 1418.0-1419.0 | 5.962 | 1418.353302725 | 5 | 5.644 | 0.287938 | below global threshold |
| 1424.5-1425.5 | 7.126 | 1425.216524117 | 9 | 10.955 | 0.081712 | below global threshold |

The window p-values measure departure from the circular-shift null. They do
not override the fixed physical OFF-source evidence or the globally calibrated
threshold.

## Complete disposition accounting

The prospectively raised report cap retained every one of the 388 clusters;
no post-hoc cap expansion or rerun was needed. Nine clusters exceeded the
unchanged global threshold, all in the 1400 MHz window:

| Physical disposition | Count |
|---|---:|
| exact matched OFF-source recurrence | 4 |
| local OFF-source recurrence | 4 |
| single adjacent-OFF track | 1 |
| **survivors** | **0** |

The remaining 379 complete clusters were below the global threshold. The
single-adjacent-OFF case at 1400.133071013 MHz also carries a receiver-frame
template-alias flag, but the frozen adjacent-OFF track is already a sufficient
physical veto. Arithmetic-family and wide-template flags are treated only as
triage evidence.

## Completeness and sensitivity

The 1400 MHz interference creates a heavy-tailed complete-search null and
raises the global threshold to S/N 40.339649. Consequently, the preregistered
injection grid does not reach 50% recovery:

| Ideal single-epoch S/N | Multichannel recovery | One-channel recovery |
|---:|---:|---:|
| 8 | 0/32 | 0/32 |
| 12 | 0/32 | 0/32 |
| 16 | 0/32 | 0/32 |
| 20 | 0/32 | 0/32 |
| 24 | 0/32 | 0/32 |
| 32 | 0/32 | 0/32 |
| 40 | 5/32 (15.6%) | 5/32 (15.6%) |

Neither a 50% nor a 90% recovery point can be estimated from this grid. The
null result is therefore substantially less sensitive than several earlier
milestones and should not be read as excluding moderate-strength intermittent
signals. Lower, window-specific thresholds were not substituted after seeing
the data because the preregistered decision rule used one global threshold.

## Independent-cadence boundary

The frozen header screen contains no second qualifying 16 Cyg B L-band
cadence. Because no primary case survived the automatic physical vetoes,
Milestone 24 closes as a primary-cadence null result. Even if a case had
survived, this archive selection could only have produced an unresolved
candidate pending genuinely independent observations; it could not establish
recurrence.

## Scope and limits

- The search covers five disjoint 1 MHz planet-frame bands, not the full GBT
  L-band receiver range.
- All three ON scans belong to one approximately 28-minute cadence on
  2017-01-02, not independent observing nights.
- The orbital model is a coordinate-transform hypothesis; it does not locate
  an emitter on 16 Cyg B b.
- The minimum empirical p-value measures departure from the circular-shift
  null. The frozen OFF checks identify non-unique local features.
- The heavy-tailed 1400 MHz interference limits the global completeness; no
  50% recovery level is measured through ideal single-epoch S/N 40.
- The null result constrains only the frozen frequency windows, signal model,
  cadence, and measured sensitivity.

## Reproducibility

The public preregistration commit is
`95068209a6ece1f08c92b5cf703452986a364f7a`; the successful execution commit is
`dae44c297034a91f1bffaa494de4e9d306d4bd96`. The frozen configuration SHA-256
is `73cee229fc1696a895444168902f7ae2eb1be5ccced41689206a93f5df4730ca`.
The complete search record SHA-256 is
`45b106be893b4b976b93585aef675c97f8f90885ce90d250742e1db44e87c1cb`.
`DATA_MANIFEST_M24.sha256` identifies all 30 reproducible extracts and
`RESULTS_MANIFEST_M24.sha256` identifies all nine published outputs. Extracted
telescope slices are not committed.
