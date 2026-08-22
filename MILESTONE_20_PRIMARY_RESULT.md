# Milestone 20 primary held-out result

Status: **PRIMARY SEARCH COMPLETE — ONE ARITHMETIC-FAMILY CASE REQUIRES THE
FROZEN MORPHOLOGY REVIEW**.

Milestone 20 applied frozen detector v0.5.0 to the sole complete compatible
GBT L-band cadence for rho CrB, using rho CrB c only as the motion template.
GitHub Actions run `32589563026` executed the preregistered configuration at
commit `fd3113be7ba8ff4a568f3b79921800a1be039d97`. Artifact `9480135893`, named
`milestone-20-held-out-results`, has verified digest
`sha256:a893ec5e6c0f5bd2ae5ef86cdb2c27fb6bf0f26c56904ccc228b78ea7adb37c9`.
All nine primary result files match `RESULTS_MANIFEST_M20.sha256`, and the data
manifest contains the expected 30 extracted-slice hashes. Raw slices were not
published.

## Frozen global result

Across approximately **592,487,280** nominal
frequency/orbit/activity/width trials:

- observed global maximum: **S/N 69,174.591026** at 1400.459812410 MHz;
- empirical global p-value: **1/257 = 0.00389105**;
- scramble-null median: **S/N 6.765559**; and
- scramble-null 99th percentile and operational threshold: **S/N 8.091331**.

The global maximum is stronger in the matched OFF-source hypothesis, at
S/N 70,758.544724, and receives the frozen `rfi_veto_off_source` disposition.
The maxima in the 1406, 1412, and 1418 MHz windows are likewise matched by
equally strong OFF-source features. The 1425 MHz maximum receives the frozen
local-OFF and receiver-frame-alias vetoes. These strong lines are therefore
not candidates.

## Window results

| Window | ON maximum S/N | Frequency (MHz) | Width | OFF-global S/N | Frozen maximum disposition |
|---|---:|---:|---:|---:|---|
| 1400.0-1401.0 | 69,174.591 | 1400.459812410 | 1 | 70,758.545 | matched OFF source |
| 1406.0-1407.0 | 65,873.099 | 1406.319477674 | 1 | 66,228.312 | matched OFF source |
| 1412.0-1413.0 | 59,238.485 | 1412.179142963 | 1 | 59,176.260 | matched OFF source |
| 1418.0-1419.0 | 49,186.779 | 1418.038808201 | 1 | 49,622.097 | matched OFF source |
| 1424.5-1425.5 | 89.778 | 1424.915099356 | 5 | 94.577 | local OFF / receiver alias |

## Candidate reduction

The frozen reporting procedure retained 705 hypothesis peaks, formed 354
frequency clusters before report limits, and reported 109 clusters. Their
automated dispositions are:

- 79 below threshold;
- 15 exact matched-OFF vetoes;
- 8 local-OFF vetoes;
- 3 single-adjacent-OFF vetoes;
- 3 receiver-frame-alias vetoes; and
- 1 arithmetic-family case pending the fixed manual morphology review.

The sole review case is at **1400.196827972 MHz**, with maximum **S/N
11.501586**, the nine-channel width, template 20 (projected scale 1.0, phase
+0.2 cycles), and active ON epochs 1 and 3. Its per-epoch values are
`[8.1328, 0.5223, 11.3935]`. The automated same-track OFF check is null, but
the case belongs to the preregistered arithmetic frequency family `family_5`
and therefore cannot be closed from the primary result alone.

This is not a detection. The arithmetic-family flag is triage evidence, not a
sufficient physical veto, and the post-hoc review cannot increase the frozen
held-out significance. The next permitted step is a separately frozen,
candidate-local ON/OFF morphology review of this one case. The frozen header
screen found no second qualifying rho CrB cadence, so any unresolved case
cannot be called independently recurrent.

## Completeness snapshot

| Ideal single-epoch S/N | Multichannel recovery | One-channel recovery |
|---:|---:|---:|
| 8 | 9/32 (28.1%) | 9/32 (28.1%) |
| 12 | 29/32 (90.6%) | 27/32 (84.4%) |
| 16 | 32/32 (100%) | 30/32 (93.8%) |
| 20 | 32/32 (100%) | 31/32 (96.9%) |
| 24 | 32/32 (100%) | 31/32 (96.9%) |
| 32 | 32/32 (100%) | 31/32 (96.9%) |
| 40 | 32/32 (100%) | 31/32 (96.9%) |

These measurements apply to the frozen injection grid and are not confidence
bounds for every possible signal shape or duty cycle.
