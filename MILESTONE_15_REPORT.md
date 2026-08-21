# Milestone 15 report: GJ 581 held-out detector-v0.5 search

Status: **MANUAL RFI-FAMILY REVIEW REQUIRED — no clean survivor**.

Milestone 15 applied frozen detector v0.5.0 to a previously unused public GJ
581 cadence after a metadata-only target screen and a successful 630-case
extraction-coverage proof. GitHub Actions run `32503226164` completed all
detector tests, 30 HDF5 extractions, five searches, 256 global scrambles, and
the preregistered completeness study. The result artifact is `9454753839`,
digest
`sha256:63ecfe61c3b9588a65e4effeef9e7fa31e3e44e8284ff2d72ce2d18ee4ce7e0b`.

## Global result

Across approximately **592,487,280** nominal
frequency/orbit/activity/width trials:

- observed global maximum: **S/N 24.2334** at 1400.220325789 MHz;
- scrambled-null median: **S/N 7.4264**;
- scrambled-null 99th percentile and operational threshold: **S/N 11.7928**;
- empirical global p-value: **1/257 = 0.003891**; and
- pipeline assessment: **FOLLOW-UP REQUIRED**.

This low empirical rank does not support a technosignature interpretation. The
global maximum is rejected by direct OFF-source evidence: its matched OFF-bank
S/N is 20.2621, its best nearby OFF recurrence has S/N 22.4088, and both active
epochs exceed the frozen adjacent-OFF candidate-track floor.

## Window results

| Window | ON maximum S/N | Frequency (MHz) | Width | OFF-global S/N | Empirical p |
|---|---:|---:|---:|---:|---:|
| 1400.0-1401.0 | 24.233 | 1400.220325789 | 9 | 23.007 | 0.003891 |
| 1406.0-1407.0 | 16.246 | 1406.118344073 | 9 | 29.320 | 0.003891 |
| 1412.0-1413.0 | 5.869 | 1412.966406289 | 9 | 5.991 | 0.571984 |
| 1418.0-1419.0 | 6.581 | 1418.942338536 | 9 | 6.673 | 0.066148 |
| 1424.5-1425.5 | 7.473 | 1424.545281656 | 3 | 20.440 | 0.428016 |

The 1400 MHz maximum is physically vetoed by OFF-source recurrence. The 1406
MHz window contains two above-threshold clusters that require the separately
declared morphology review below. The remaining three window maxima do not
exceed the global operational threshold.

## Candidate reduction

The frozen reporting procedure retained 368 hypothesis peaks, formed 220
frequency clusters before per-window caps, and reported 115 clusters:

| Disposition | Clusters |
|---|---:|
| Below operational threshold | 109 |
| OFF-source veto | 3 |
| Single adjacent-OFF-track veto | 1 |
| Arithmetic-family flag pending manual review | 2 |

The two manual-review clusters are separated by 70.888 Hz and use the same
projected-scale 0.25, phase -0.1 orbit template, the widest nine-channel
boxcar, and only ON epochs 1 and 2:

| Frequency (MHz) | S/N | Active-epoch S/N values | Maximum matched OFF-epoch S/N | Frozen context |
|---:|---:|---|---:|---|
| 1406.118344073 | 16.246 | 12.143, 11.487 | 3.155 | families 1 and 4; widest boxcar |
| 1406.118273185 | 13.857 | 9.798, 12.793 | 4.361 | family 5; widest boxcar |

Neither case has an automated recurring OFF veto under detector v0.5. Their
arithmetic-family membership and selected width are triage evidence only, not
a physical rejection. They remain manual-review cases until a fixed post-hoc
analysis tests their six-scan topocentric morphology.

## Completeness and acceleration limit

| Ideal single-epoch S/N | Multichannel recovery | One-channel recovery |
|---:|---:|---:|
| 8 | 0/32 (0%) | 0/32 (0%) |
| 12 | 0/32 (0%) | 0/32 (0%) |
| 16 | 7/32 (21.9%) | 5/32 (15.6%) |
| 20 | 10/32 (31.2%) | 5/32 (15.6%) |
| 24 | 12/32 (37.5%) | 7/32 (21.9%) |
| 32 | 16/32 (50%) | 7/32 (21.9%) |
| 40 | 16/32 (50%) | 8/32 (25%) |

No overall 90% completeness level is reached on the tested grid. Recovery is
strong for the slow template and reaches 100% for the moderate scale-0.5
template by ideal S/N 32. It remains 0% through ideal S/N 40 for the two tested
high-acceleration templates, which sweep about 19.6 and 30.1 channels per
17.986 s integration. Consequently this experiment cannot support a strong
null statement for rapidly accelerating narrowband emitters under the GJ 581 b
working model.

## Scope and limits

- The search covers five disjoint 1 MHz planet-frame bands, not the full
  receiver band.
- All three ON scans belong to one approximately 28-minute ABACAD cadence, not
  independent observing nights.
- The orbital template predicts a coordinate transform; it does not establish
  that an emitter resides on GJ 581 b.
- The empirical p-value measures departure from the circular-shift null.
  Structured RFI can produce the same departure.
- Arithmetic-family membership requires manual physical review unless a
  specific frozen automated veto also applies.
- No technosignature claim or clean survivor exists at this stage.

## Reproducibility

The preregistration commit is
`0538ed4be0407eb2397d3b1e1d676fdf7fb8e08b`; its frozen configuration SHA-256
is
`117b689c9a2d12726133e3f53fd6560b80d8d354540310c94ab9b4032c3a8c99`.
The workflow repeated all detector tests and the 630-case coverage proof before
extraction. `DATA_MANIFEST_M15.sha256` identifies the 30 extracted slices;
`RESULTS_MANIFEST_M15.sha256` identifies the primary published outputs. The
extracted telescope slices are not committed.
