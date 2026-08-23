# Milestone 21 primary held-out result

Status: **PRIMARY SEARCH COMPLETE — TWO ARITHMETIC-FAMILY CASES REQUIRE THE
FROZEN MORPHOLOGY REVIEW**.

Milestone 21 applied frozen detector v0.5.0 to the sole complete compatible
GBT L-band cadence for HD 154345, using HD 154345 b only as the motion
template. GitHub Actions run `32623205641` executed the preregistered
configuration at commit `f9ae81203ae3bcf44c3c711a447b90322c06ba3b`.
Artifact `9489151424`, named `milestone-21-held-out-results`, has verified
digest
`sha256:54f046b6264c9586e22aa1d1904203c33da3c96696340600dfff377f9f6f1886`.
All nine primary result files match `RESULTS_MANIFEST_M21.sha256`, and the data
manifest contains the expected 30 extracted-slice hashes. Raw slices were not
published.

## Frozen global result

Across approximately **592,487,280** nominal
frequency/orbit/activity/width trials:

- observed global maximum: **S/N 328.353929** at 1400.000778429 MHz;
- empirical global p-value: **1/257 = 0.00389105**;
- scramble-null median: **S/N 6.458955**; and
- scramble-null 99th percentile and operational threshold: **S/N 9.555616**.

The global maximum is stronger in the matched OFF-source search, at S/N
340.317322, and receives the frozen `rfi_veto_off_source` disposition. The
1412 MHz maximum is also stronger in the matched OFF source. The 1406 and
1425 MHz maxima receive the frozen single-adjacent-OFF veto, while the 1418
MHz maximum is below threshold. These window maxima are therefore not
candidates.

## Window results

| Window | ON maximum S/N | Frequency (MHz) | Width | OFF-global S/N | Frozen maximum disposition |
|---|---:|---:|---:|---:|---|
| 1400.0-1401.0 | 328.354 | 1400.000778429 | 9 | 340.317 | matched OFF source |
| 1406.0-1407.0 | 10.237 | 1406.271186215 | 9 | 9.761 | single adjacent OFF |
| 1412.0-1413.0 | 116.611 | 1412.422670150 | 9 | 120.425 | matched OFF source |
| 1418.0-1419.0 | 5.873 | 1418.773730995 | 5 | 5.595 | below threshold |
| 1424.5-1425.5 | 13.187 | 1425.001865761 | 1 | 11.414 | single adjacent OFF |

## Candidate reduction

The frozen reporting procedure retained 2,792 hypothesis peaks, formed 372
frequency clusters before report limits, and reported 199 clusters. Their
automated dispositions are:

- 92 exact matched-OFF vetoes;
- 16 single-adjacent-OFF vetoes;
- 89 below threshold; and
- 2 arithmetic-family cases pending the fixed manual morphology review.

Both review cases are in the 1425 MHz window:

| Frequency (MHz) | Maximum S/N | Width | Template | Active ON epochs | Frozen flag |
|---:|---:|---:|---:|---|---|
| 1424.954541209 | 12.466380 | 1 | 0 (scale 0, phase 0) | 1+2 | arithmetic family |
| 1424.964184756 | 12.015500 | 1 | 12 (scale 0.75, phase -0.1) | 1+2 | arithmetic family |

Their per-epoch values are `[22.2174, 8.8151, 3.3741]` and
`[22.2174, 8.4962, 0.3660]`, respectively. Neither case passes the automated
same-track OFF check. Both are nevertheless members of multiple
preregistered arithmetic frequency families and therefore cannot be closed
from the primary result alone.

These are not detections. Arithmetic-family membership is triage evidence,
not a sufficient physical veto, and the post-hoc review cannot increase the
frozen held-out significance. The next permitted step is a separately frozen,
candidate-local ON/OFF morphology review of exactly these two cases. The
frozen header screen found no second qualifying HD 154345 cadence, so any
unresolved case cannot be called independently recurrent.

## Completeness snapshot

| Ideal single-epoch S/N | Multichannel recovery | One-channel recovery |
|---:|---:|---:|
| 8 | 0/32 (0%) | 0/32 (0%) |
| 12 | 21/32 (65.6%) | 20/32 (62.5%) |
| 16 | 32/32 (100%) | 29/32 (90.6%) |
| 20 | 32/32 (100%) | 32/32 (100%) |
| 24 | 32/32 (100%) | 32/32 (100%) |
| 32 | 32/32 (100%) | 32/32 (100%) |
| 40 | 32/32 (100%) | 32/32 (100%) |

These measurements apply to the frozen injection grid and are not confidence
bounds for every possible signal shape or duty cycle.
