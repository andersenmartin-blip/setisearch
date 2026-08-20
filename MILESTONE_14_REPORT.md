# Milestone 14 report: GJ 687 held-out detector-v0.5 search

Status: **MANUAL RFI-FAMILY REVIEW REQUIRED — no clean survivor**.

Milestone 14 applied frozen detector v0.5.0 to a previously unused public GJ
687 cadence after a successful 630-case metadata-only extraction-coverage
proof. GitHub Actions run `32392384473` completed all tests, 30 extractions,
five searches, 256 global scrambles, and the preregistered completeness study.
The result artifact is `9416029410`, digest
`sha256:3880d765bc7db8ebbf0ba65e6cda239c0a2b55e63c094eb1892ef36498cbd687`.

## Global result

Across approximately **601,293,840** nominal
frequency/orbit/activity/width trials:

- observed global maximum: **S/N 61,308.5941** at 1400.242513523 MHz;
- scrambled-null median: **S/N 7.5673**;
- scrambled-null 99th percentile and operational threshold: **S/N 9.2902**;
- empirical global p-value: **1/257 = 0.003891**; and
- pipeline assessment: **FOLLOW-UP REQUIRED**.

This p-value does not support a technosignature interpretation. The global
maximum is independently rejected by the frozen local-OFF veto: an OFF-bank
recurrence lies 2.794 Hz away with S/N 62,328.1924. The very large 1406 MHz
maximum and the maxima in the other three bands are also automatically vetoed.

## Window results

| Window | ON maximum S/N | Frequency (MHz) | Width | OFF-global S/N | Frozen disposition |
|---|---:|---:|---:|---:|---|
| 1400.0-1401.0 | 61,308.594 | 1400.242513523 | 1 | 62,328.192 | local-OFF veto |
| 1406.0-1407.0 | 54,362.994 | 1406.101270072 | 1 | 39,030.950 | exact OFF veto |
| 1412.0-1413.0 | 14.163 | 1412.350609340 | 3 | 25.551 | exact OFF veto |
| 1418.0-1419.0 | 42.158 | 1418.985178083 | 5 | 56.544 | exact OFF veto |
| 1424.5-1425.5 | 11.230 | 1424.962245114 | 3 | 18.765 | local-OFF veto |

All five per-window empirical p-values are 1/257 because every observed window
maximum exceeds every corresponding scramble maximum. Their RFI veto evidence,
not the low rank alone, controls candidate disposition.

## Candidate reduction

The frozen reporting procedure retained 928 hypothesis peaks, formed 372
frequency clusters before per-window caps, and reported 85 clusters:

| Disposition | Clusters |
|---|---:|
| Below operational threshold | 34 |
| Exact matched-OFF veto | 8 |
| Local-OFF recurrence veto | 4 |
| Receiver-frame alias veto | 26 |
| Single adjacent-OFF-track veto | 8 |
| Arithmetic-family flag pending manual review | 5 |

No cluster has a clean follow-up disposition. Five clusters in the 1424.5-
1425.5 MHz window lie narrowly above S/N 9.2902 without a specific automated
v0.5 veto. All use the widest 9-channel template, appear in all three ON
epochs, and belong to one or more detected arithmetic frequency families:

| Frequency (MHz) | S/N | Scale | Phase | Matched OFF S/N | Best local OFF S/N |
|---:|---:|---:|---:|---:|---:|
| 1425.315276906 | 9.429 | 1.00 | +0.1 | 6.115 | 7.290 |
| 1425.247347169 | 9.377 | 0.25 | -0.2 | 7.806 | 7.806 |
| 1425.134884380 | 9.377 | 1.00 | -0.1 | fails recurrence | 6.555 |
| 1425.360145234 | 9.338 | 0.50 | +0.2 | 6.301 | 7.743 |
| 1425.328830443 | 9.317 | 0.25 | +0.2 | 7.034 | 8.567 |

The family flag is triage evidence, not by itself a physical veto. These five
records must remain labelled manual-review cases until a separately declared
post-hoc investigation evaluates their topocentric spacing, ON/OFF morphology,
and cross-cadence recurrence. They may not be silently promoted or discarded.

## Completeness

| Ideal single-epoch S/N | Multichannel recovery | One-channel recovery |
|---:|---:|---:|
| 8 | 1/32 (3.1%) | 1/32 (3.1%) |
| 12 | 19/32 (59.4%) | 18/32 (56.2%) |
| 16 | 31/32 (96.9%) | 27/32 (84.4%) |
| 20 | 32/32 (100%) | 31/32 (96.9%) |
| 24 | 32/32 (100%) | 31/32 (96.9%) |
| 32 | 32/32 (100%) | 32/32 (100%) |
| 40 | 32/32 (100%) | 32/32 (100%) |

Piecewise-linear point estimates place multichannel 50% and 90% recovery near
ideal single-epoch S/N **11.33** and **15.27**. The corresponding one-channel
estimates are **11.53** and **17.8**. These are grid interpolations, not
confidence bounds; a 32/32 level has a Wilson 95% lower bound of 89.3%.

## Scope and limits

- The search covers five disjoint 1 MHz planet-frame bands, not the full
  receiver band.
- All three ON scans belong to one approximately 28-minute ABACAD cadence, not
  independent observing nights.
- The orbital template predicts a coordinate transform; it does not establish
  that an emitter resides on GJ 687 b.
- The empirical p-value measures departure from the circular-shift null. Strong
  structured RFI can produce the same departure.
- Arithmetic-family membership requires manual physical review unless a
  specific frozen automated veto also applies.
- A null statement is not yet warranted while the five manual-review cases
  remain unresolved.

## Reproducibility

The preregistration commit is
`2d8a1d31aac0c650430094aabc7b2cef28c7bfc1`. The workflow repeated all detector
tests and the 630-case coverage proof before extraction. `DATA_MANIFEST_M14.sha256`
identifies the 30 extracted slices; `RESULTS_MANIFEST_M14.sha256` identifies the
primary published outputs. The extracted telescope slices are not committed.

