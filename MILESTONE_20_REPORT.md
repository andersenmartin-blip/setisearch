# Milestone 20 report: rho CrB held-out detector-v0.5 search

Status: **NO SURVIVING CANDIDATE; THE SOLE REVIEW CASE IS VETOED AS RFI OR
INSTRUMENTAL**.

Milestone 20 applied frozen detector v0.5.0 to the sole complete compatible
GBT L-band rho CrB cadence `--71771`. rho CrB c supplies only the motion
template; the search does not assume that an emitter is located on the planet.

GitHub Actions run `32589563026` completed all detector tests, the repeated
630-case extraction-coverage proof, 30 HDF5 extractions, five searches, 256
global scrambles, and the preregistered completeness study. Artifact
`9480135893`, named `milestone-20-held-out-results`, has verified digest
`sha256:a893ec5e6c0f5bd2ae5ef86cdb2c27fb6bf0f26c56904ccc228b78ea7adb37c9`.
All nine primary result files match `RESULTS_MANIFEST_M20.sha256`; the data
manifest contains the expected 30 extracted-slice hashes. Raw slices were not
published.

## Global result

Across approximately **592,487,280** nominal
frequency/orbit/activity/width trials:

- observed global maximum: **S/N 69,174.591026** at 1400.459812410 MHz;
- scrambled-null median: **S/N 6.765559**;
- scrambled-null 99th percentile and operational threshold:
  **S/N 8.091331**;
- empirical global p-value: **1/257 = 0.00389105**; and
- final frozen disposition: **RFI or instrumental; no survivor**.

The low empirical rank does not imply an astrophysical or artificial origin.
The global maximum is stronger in its matched OFF-source hypothesis, at S/N
70,758.544724, and receives the frozen `rfi_veto_off_source` disposition. The
maxima in the next three windows have the same matched-OFF behavior, while the
1425 MHz maximum receives local-OFF and receiver-frame-alias vetoes.

## Window results

| Window | ON maximum S/N | Frequency (MHz) | Width | OFF-global S/N | Empirical p | Frozen maximum disposition |
|---|---:|---:|---:|---:|---:|---|
| 1400.0-1401.0 | 69,174.591 | 1400.459812410 | 1 | 70,758.545 | 0.003891 | matched OFF source |
| 1406.0-1407.0 | 65,873.099 | 1406.319477674 | 1 | 66,228.312 | 0.003891 | matched OFF source |
| 1412.0-1413.0 | 59,238.485 | 1412.179142963 | 1 | 59,176.260 | 0.003891 | matched OFF source |
| 1418.0-1419.0 | 49,186.779 | 1418.038808201 | 1 | 49,622.097 | 0.003891 | matched OFF source |
| 1424.5-1425.5 | 89.778 | 1424.915099356 | 5 | 94.577 | 0.003891 | local OFF / receiver alias |

The window p-values measure departure from the circular-shift null. They do
not override the physical OFF-source evidence.

## Candidate reduction

The frozen procedure retained 705 hypothesis peaks, formed 354 frequency
clusters before report limits, and reported 109 clusters:

- 79 below threshold;
- 15 exact matched-OFF vetoes;
- 8 local-OFF vetoes;
- 3 single-adjacent-OFF vetoes;
- 3 receiver-frame-alias vetoes; and
- 1 arithmetic-family case sent to the fixed morphology review.

The sole review case was at **1400.196827972 MHz**, with frozen **S/N
11.501586**, the nine-channel width, template 20 (projected scale 1.0, phase
+0.2 cycles), and active ON epochs 1 and 3. No other cluster entered the
post-hoc stage.

## Fixed morphology review

The review protocol was published before candidate-local cutout inspection at
commit `b4ce2b97b2d60b3d0e2d6e31031b6890af61687c`. GitHub Actions run
`32590900412` produced artifact `9480309112`, named
`milestone-20-candidate-investigation`, with verified digest
`sha256:e70ac83efdc514f61a0b317ff1955dbf3c4dec75460a06833f51a7095329e5ff`.
All four review outputs match their manifest; the separate data manifest
contains six targeted-cutout hashes. Raw cutouts were not published.

| Rest frequency (MHz) | Frozen S/N | Local ON track S/N, epochs 1/3 | Adjacent-OFF coincidences | Final class |
|---:|---:|---:|---:|---|
| 1400.196827972 | 11.501586 | 8.637 / 11.344 | 1 | RFI/instrumental |

In active epoch 1, the strongest local ON feature and a stronger adjacent-OFF
feature occur at the identical recorded receiver frequency,
1399.996748056 MHz: ON S/N 15.757 and OFF S/N 16.902, with measured separation
0.0 Hz. This satisfies the fixed
`adjacent_OFF_peak_within_20_Hz` physical veto and yields
`RFI_OR_INSTRUMENTAL`. The widest-boxcar and arithmetic-family flags remain
context only; neither was used as a sufficient veto.

## Completeness

| Ideal single-epoch S/N | Multichannel recovery | One-channel recovery |
|---:|---:|---:|
| 8 | 9/32 (28.1%) | 9/32 (28.1%) |
| 12 | 29/32 (90.6%) | 27/32 (84.4%) |
| 16 | 32/32 (100%) | 30/32 (93.8%) |
| 20 | 32/32 (100%) | 31/32 (96.9%) |
| 24 | 32/32 (100%) | 31/32 (96.9%) |
| 32 | 32/32 (100%) | 31/32 (96.9%) |
| 40 | 32/32 (100%) | 31/32 (96.9%) |

Piecewise-linear point estimates place multichannel 50% and 90% recovery near
ideal single-epoch S/N **9.40** and **11.96**. The corresponding one-channel
estimates are **9.56** and **14.40**. These are grid interpolations, not
confidence bounds; a 32/32 level has a Wilson 95% lower bound of 89.3%.

## Independent-cadence decision

The frozen header screen contains no second complete compatible public rho CrB
cadence. An unresolved morphology case would therefore have remained labelled
as requiring later independent data. In practice the sole review case receives
the fixed adjacent-OFF veto, so no unresolved survivor remains and no
independent-recurrence claim is made.

## Scope and limits

- The search covers five disjoint 1 MHz planet-frame bands, not the full GBT
  L-band receiver range.
- All three ON scans belong to one approximately 29-minute ABACAD cadence on
  2016-05-25, not independent observing nights.
- The orbital model is a coordinate-transform hypothesis; it does not locate
  an emitter on rho CrB c.
- The minimum empirical p-value measures departure from the circular-shift
  null. The frozen OFF checks identify strong non-unique receiver features.
- The null result constrains only the frozen frequency windows, signal model,
  cadence, and measured sensitivity.

## Reproducibility

The public preregistration and execution commit is
`fd3113be7ba8ff4a568f3b79921800a1be039d97`; the frozen configuration SHA-256
is `d631241a0b55c8a0c3f81d795ad19e2ccb4946918d57431d2817bc785a591696`.
`DATA_MANIFEST_M20.sha256` identifies the 30 primary slices;
`RESULTS_MANIFEST_M20.sha256` identifies all primary outputs. The candidate
investigation manifests identify six targeted cutouts and four published
review outputs. Extracted telescope slices are not committed.
