# Milestone 21 report: HD 154345 held-out detector-v0.5 search

Status: **NO SURVIVING CANDIDATE; BOTH REVIEW CASES ARE VETOED AS RFI OR
INSTRUMENTAL**.

Milestone 21 applied frozen detector v0.5.0 to the sole complete compatible
GBT L-band HD 154345 cadence `--85132`. HD 154345 b supplies only the motion
template; the search does not assume that an emitter is located on the planet.

GitHub Actions run `32623205641` completed all detector tests, the repeated
630-case extraction-coverage proof, 30 HDF5 extractions, five searches, 256
global scrambles, and the preregistered completeness study. Artifact
`9489151424`, named `milestone-21-held-out-results`, has verified digest
`sha256:54f046b6264c9586e22aa1d1904203c33da3c96696340600dfff377f9f6f1886`.
All nine primary result files match `RESULTS_MANIFEST_M21.sha256`; the data
manifest contains the expected 30 extracted-slice hashes. Raw slices were not
published.

## Global result

Across approximately **592,487,280** nominal
frequency/orbit/activity/width trials:

- observed global maximum: **S/N 328.353929** at 1400.000778429 MHz;
- scrambled-null median: **S/N 6.458955**;
- scrambled-null 99th percentile and operational threshold:
  **S/N 9.555616**;
- empirical global p-value: **1/257 = 0.00389105**; and
- final frozen disposition: **RFI or instrumental; no survivor**.

The low empirical rank does not imply an astrophysical or artificial origin.
The global maximum is stronger in its matched OFF-source hypothesis, at S/N
340.317322, and receives the frozen `rfi_veto_off_source` disposition. The
1412 MHz maximum has the same matched-OFF behavior. The 1406 and 1425 MHz
maxima receive the single-adjacent-OFF veto, while the 1418 MHz maximum is
below threshold.

## Window results

| Window | ON maximum S/N | Frequency (MHz) | Width | OFF-global S/N | Empirical p | Frozen maximum disposition |
|---|---:|---:|---:|---:|---:|---|
| 1400.0-1401.0 | 328.354 | 1400.000778429 | 9 | 340.317 | 0.003891 | matched OFF source |
| 1406.0-1407.0 | 10.237 | 1406.271186215 | 9 | 9.761 | 0.003891 | single adjacent OFF |
| 1412.0-1413.0 | 116.611 | 1412.422670150 | 9 | 120.425 | 0.003891 | matched OFF source |
| 1418.0-1419.0 | 5.873 | 1418.773730995 | 5 | 5.595 | 0.214008 | below threshold |
| 1424.5-1425.5 | 13.187 | 1425.001865761 | 1 | 11.414 | 0.003891 | single adjacent OFF |

The window p-values measure departure from the circular-shift null. They do
not override the physical OFF-source evidence.

## Candidate reduction

The frozen procedure retained 2,792 hypothesis peaks, formed 372 frequency
clusters before report limits, and reported 199 clusters:

- 92 exact matched-OFF vetoes;
- 16 single-adjacent-OFF vetoes;
- 89 below threshold; and
- 2 arithmetic-family cases sent to the fixed morphology review.

The two review cases were at **1424.954541209 MHz** (frozen S/N 12.466380)
and **1424.964184756 MHz** (frozen S/N 12.015500). Both used active ON epochs
1 and 2. No other cluster entered the post-hoc stage.

## Fixed morphology review

The review protocol was published before candidate-local cutout inspection at
commit `de1f3b7198b3c59c60b5efea5e24954478c16c33`. GitHub Actions run
`32624405957` produced artifact `9489291884`, named
`milestone-21-candidate-investigation`, with verified digest
`sha256:319bbaf2d6d4a032ad406c5a9f17adbaa7a94f702aa75138652a026e6326260b`.
All five review outputs match their manifest; the separate data manifest
contains six targeted-cutout hashes. Raw cutouts were not published.

| Rest frequency (MHz) | Frozen S/N | Local ON track S/N, epochs 1/2 | Adjacent-OFF track evidence | Final class |
|---:|---:|---:|---|---|
| 1424.954541209 | 12.466380 | 21.605 / 9.324 | below 5.5 | RFI/instrumental |
| 1424.964184756 | 12.015500 | 21.605 / 8.464 | epoch 2 S/N 6.515 | RFI/instrumental |

Although the two cases have different planet-frame rest frequencies and
different orbital templates, both map to exactly the same recorded receiver
features in both claimed active epochs: 1424.997580181 MHz in epoch 1 and
1424.997486610 MHz in epoch 2. The measured cross-case separations are 0.0 Hz.
This satisfies the fixed `different_planet_templates_map_to_same_receiver_feature`
rule for both cases. The second case independently satisfies the fixed
`adjacent_OFF_same_candidate_track_SNR_ge_5p5` rule in epoch 2.

Both cases therefore receive `RFI_OR_INSTRUMENTAL`. Arithmetic-family
membership remains context only; it was not used as a sufficient physical
veto.

## Completeness

| Ideal single-epoch S/N | Multichannel recovery | One-channel recovery |
|---:|---:|---:|
| 8 | 0/32 (0%) | 0/32 (0%) |
| 12 | 21/32 (65.6%) | 20/32 (62.5%) |
| 16 | 32/32 (100%) | 29/32 (90.6%) |
| 20 | 32/32 (100%) | 32/32 (100%) |
| 24 | 32/32 (100%) | 32/32 (100%) |
| 32 | 32/32 (100%) | 32/32 (100%) |
| 40 | 32/32 (100%) | 32/32 (100%) |

Piecewise-linear point estimates place multichannel 50% and 90% recovery near
ideal single-epoch S/N **11.05** and **14.84**. The corresponding one-channel
estimates are **11.20** and **15.91**. These are grid interpolations, not
confidence bounds; a 32/32 level has a Wilson 95% lower bound of 89.3%.

## Independent-cadence decision

The frozen header screen contains no second complete compatible public HD
154345 cadence. An unresolved morphology case would therefore have remained
labelled as requiring later independent data. In practice both review cases
receive fixed physical interference dispositions, so no unresolved survivor
remains and no independent-recurrence claim is made.

## Scope and limits

- The search covers five disjoint 1 MHz planet-frame bands, not the full GBT
  L-band receiver range.
- All three ON scans belong to one approximately 29-minute ABACAD cadence on
  2016-03-23, not independent observing nights.
- The orbital model is a coordinate-transform hypothesis; it does not locate
  an emitter on HD 154345 b.
- The minimum empirical p-value measures departure from the circular-shift
  null. The frozen OFF and cross-template checks identify non-unique receiver
  features.
- The null result constrains only the frozen frequency windows, signal model,
  cadence, and measured sensitivity.

## Reproducibility

The public preregistration and execution commit is
`f9ae81203ae3bcf44c3c711a447b90322c06ba3b`; the frozen configuration SHA-256
is `441597c69c1b3227648ee7aaf4bd6c8b0a09241c807755e03b355baa194b21e7`.
`DATA_MANIFEST_M21.sha256` identifies the 30 primary slices;
`RESULTS_MANIFEST_M21.sha256` identifies all primary outputs. The candidate
investigation manifests identify six targeted cutouts and five published
review outputs. Extracted telescope slices are not committed.
