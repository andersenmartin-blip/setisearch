# Milestone 17 report: GJ 849 held-out detector-v0.5 search

Status: **NO SURVIVING CANDIDATE; RESERVED CADENCE NOT TRIGGERED**.

Milestone 17 applied frozen detector v0.5.0 to the previously unused complete
GBT L-band GJ 849 cadence `--73890`. GJ 849 b supplies only the motion
template; the search does not assume that an emitter is located on the planet.

GitHub Actions run `32571960780` completed all detector tests, the repeated
630-case extraction-coverage proof, 30 HDF5 extractions, five searches, 256
global scrambles, and the preregistered completeness study. Artifact
`9475729151`, named `milestone-17-held-out-results`, has digest
`sha256:10ead94bb2ac7d4aedd48fb9fe62c501ff3c8f082601b0a95708903c5a5fc6c7`.

## Global result

Across approximately **601,293,840** nominal
frequency/orbit/activity/width trials:

- observed global maximum: **S/N 140.9364** at 1400.254871242 MHz;
- scrambled-null median: **S/N 7.0916**;
- scrambled-null 99th percentile and operational threshold: **S/N 8.9124**;
- empirical global p-value: **1/257 = 0.003891**; and
- final frozen disposition: **RFI/OFF-source veto; no survivor**.

The very low empirical rank does not imply an astrophysical or artificial
origin. The maximum has matched OFF-bank S/N 77.5420. A nearby OFF recurrence
reaches S/N 113.8490 only 11.176 Hz away, inside the fixed 20 Hz tolerance.
The same candidate track is strong in every OFF scan, with S/N 44.084, 79.500,
and 54.830. This is direct terrestrial or instrumental evidence under the
frozen detector rules.

## Window results

| Window | ON maximum S/N | Frequency (MHz) | Width | OFF-global S/N | Empirical p | Frozen disposition |
|---|---:|---:|---:|---:|---:|---|
| 1400.0-1401.0 | 140.936 | 1400.254871242 | 9 | 116.930 | 0.003891 | OFF-source veto |
| 1406.0-1407.0 | 5.745 | 1406.998798676 | 5 | 5.504 | 0.435798 | below threshold |
| 1412.0-1413.0 | 5.556 | 1412.109291553 | 3 | 5.546 | 0.762646 | below threshold |
| 1418.0-1419.0 | 5.368 | 1418.271283008 | 9 | 5.770 | 0.992218 | below threshold |
| 1424.5-1425.5 | 7.323 | 1425.020239502 | 9 | 8.004 | 0.326848 | below threshold |

The 1400 MHz window contains many strong structured features. The global case
also carries receiver-frame alias, widest-boxcar, and arithmetic-family flags,
but the direct OFF-source coincidence is independently sufficient for
rejection. Every other window maximum is below the global threshold.

## Candidate reduction

The frozen reporting procedure retained 1,431 hypothesis peaks, formed 404
frequency clusters before per-window report limits, and reported 103 clusters:

| Disposition | Clusters |
|---|---:|
| OFF-source veto | 50 |
| Below operational threshold | 53 |
| Survives for follow-up | 0 |

All 50 reported clusters above the operational threshold occur in the 1400 MHz
window and receive the physical OFF-source veto. No morphology-only manual case
or automated survivor remains.

## Completeness

| Ideal single-epoch S/N | Multichannel recovery | One-channel recovery |
|---:|---:|---:|
| 8 | 0/32 (0%) | 0/32 (0%) |
| 12 | 24/32 (75.0%) | 16/32 (50.0%) |
| 16 | 32/32 (100%) | 24/32 (75.0%) |
| 20 | 32/32 (100%) | 27/32 (84.4%) |
| 24 | 32/32 (100%) | 29/32 (90.6%) |
| 32 | 32/32 (100%) | 30/32 (93.8%) |
| 40 | 32/32 (100%) | 32/32 (100%) |

Piecewise-linear point estimates place multichannel 50% and 90% recovery near
ideal single-epoch S/N **10.67** and **14.40**. The corresponding one-channel
estimates are **12.00** and **23.60**. These are grid interpolations, not
confidence bounds; a 32/32 level has a Wilson 95% lower bound of 89.3%.

## Reserved cadence decision

The complete GJ 849 cadence `--74424`, beginning 2016-07-11, was reserved for
independent recurrence only if a primary case survived. Because every
above-threshold case is physically vetoed by OFF-source evidence, the trigger
did not fire. No spectral value from the reserved cadence was read in
Milestone 17. Preserving it avoids an unnecessary post-hoc search and keeps it
available for a future independently motivated analysis.

## Scope and limits

- The search covers five disjoint 1 MHz planet-frame bands, not the full GBT
  L-band receiver range.
- All three ON scans belong to one approximately 28-minute ABACAD cadence on
  2016-07-05.
- The orbital model is a coordinate-transform hypothesis; it does not locate
  an emitter on GJ 849 b.
- The minimum empirical p-value measures departure from the circular-shift
  null. The strong OFF-source recurrence identifies that departure as RFI or
  instrumental structure under the frozen rules.
- The null result constrains only the frozen frequency windows, signal model,
  cadence, and measured sensitivity.

## Reproducibility

The public preregistration and execution commit is
`e092213fe1f8def2b5a06f6b5863a16cce62c1d6`; the frozen configuration
SHA-256 is
`87372243bc6f8eec0b9cdf4f80d3a3c37fbffdd13bddd6efeafdfd5f383b2e76`.
`DATA_MANIFEST_M17.sha256` identifies the 30 extracted slices;
`RESULTS_MANIFEST_M17.sha256` identifies all primary published outputs. The
extracted telescope slices are not committed.
