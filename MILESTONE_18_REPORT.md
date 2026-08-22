# Milestone 18 report: GJ 649 held-out detector-v0.5 search

Status: **NO SURVIVING CANDIDATE; FOUR CASES VETOED AS RFI OR
INSTRUMENTAL**.

Milestone 18 applied frozen detector v0.5.0 to the sole complete compatible
GBT L-band GJ 649 cadence `--70291`. GJ 649 b supplies only the motion
template; the search does not assume that an emitter is located on the planet.

GitHub Actions run `32574746066` completed all detector tests, the repeated
630-case extraction-coverage proof, 30 HDF5 extractions, five searches, 256
global scrambles, and the preregistered completeness study. Artifact
`9476441210`, named `milestone-18-held-out-results`, has digest
`sha256:d8035c01568eb4475adde7033f73f2fe9d0d9b6f167db2b01809e2c70f33ec76`.

## Global result

Across approximately **592,487,280** nominal
frequency/orbit/activity/width trials:

- observed global maximum: **S/N 7.893494** at 1425.213204339 MHz;
- scrambled-null median: **S/N 6.412166**;
- scrambled-null 99th percentile and operational threshold: **S/N 7.288440**;
- empirical global p-value: **1/257 = 0.003891**; and
- final frozen disposition: **RFI or instrumental; no survivor**.

The low empirical rank does not imply an astrophysical or artificial origin.
The automated pass found four over-threshold arithmetic-family cases with no
direct OFF veto. Their separately frozen morphology review shows that four
different planet-frame hypotheses all select the same receiver-frame feature
in ON epochs 2 and 3. This cross-template alias satisfies the preregistered
physical veto.

## Window results

| Window | ON maximum S/N | Frequency (MHz) | Width | OFF-global S/N | Empirical p | Frozen disposition |
|---|---:|---:|---:|---:|---:|---|
| 1400.0-1401.0 | 6.023 | 1400.508259822 | 3 | 5.873 | 0.443580 | below threshold |
| 1406.0-1407.0 | 5.882 | 1406.192350713 | 5 | 6.258 | 0.684825 | below threshold |
| 1412.0-1413.0 | 5.689 | 1412.739438398 | 1 | 5.736 | 0.852140 | below threshold |
| 1418.0-1419.0 | 6.569 | 1418.094074999 | 9 | 6.398 | 0.015564 | below threshold |
| 1424.5-1425.5 | 7.893 | 1425.213204339 | 5 | 6.800 | 0.003891 | morphology veto |

The reporting procedure formed and reported 88 clusters: 84 are below the
operational threshold, while four 1425 MHz cases entered the fixed manual
review. None survives that review.

## Fixed morphology review

The review protocol was published before candidate-local cutout inspection at
commit `a8655a9c66c11133d1f8c22e843f74f361cfb2d4`. GitHub Actions run
`32575836881` produced artifact `9476537463`, named
`milestone-18-candidate-investigation`, with verified digest
`sha256:d83ba85013b9720d9bd0007817842536ade0e74535cc37addf79ffee015b7fd9`.

| Rest frequency (MHz) | Frozen S/N | Local ON track S/N, epochs 2/3 | Adjacent-OFF coincidences | Final class |
|---:|---:|---:|---:|---|
| 1425.213204339 | 7.893494 | 5.098 / 4.942 | 0 | RFI/instrumental |
| 1425.144117298 | 7.757697 | 4.947 / 5.094 | 0 | RFI/instrumental |
| 1425.201303731 | 7.619195 | 5.634 / 5.259 | 0 | RFI/instrumental |
| 1425.191166806 | 7.355817 | 5.098 / 5.070 | 0 | RFI/instrumental |

The four distinct rest-frequency/template solutions map to the identical
strongest receiver-frame local feature at 1425.163723669 MHz in epoch 2 and
1425.163644275 MHz in epoch 3. Every pair matches in both shared active epochs
with recorded separation 0.0 Hz. Under the frozen rule this is
`different_planet_templates_map_to_same_receiver_feature`, independently
sufficient for `RFI_OR_INSTRUMENTAL`. No adjacent-OFF coincidence is needed
for the disposition.

## Completeness

| Ideal single-epoch S/N | Multichannel recovery | One-channel recovery |
|---:|---:|---:|
| 8 | 4/32 (12.5%) | 3/32 (9.4%) |
| 12 | 32/32 (100%) | 26/32 (81.3%) |
| 16 | 32/32 (100%) | 28/32 (87.5%) |
| 20 | 32/32 (100%) | 31/32 (96.9%) |
| 24 | 32/32 (100%) | 30/32 (93.8%) |
| 32 | 32/32 (100%) | 32/32 (100%) |
| 40 | 32/32 (100%) | 32/32 (100%) |

Piecewise-linear point estimates place multichannel 50% and 90% recovery near
ideal single-epoch S/N **9.71** and **11.54**. The corresponding one-channel
estimates are **10.26** and **17.07**. These are grid interpolations, not
confidence bounds; a 32/32 level has a Wilson 95% lower bound of 89.3%.

## Independent-cadence decision

The frozen header screen contains no second complete compatible public GJ 649
cadence. An unresolved morphology case would therefore have remained labelled
as requiring later independent data. In practice all four cases receive the
fixed cross-template receiver-frame veto, so no unresolved survivor remains
and no independent-recurrence claim is made.

## Scope and limits

- The search covers five disjoint 1 MHz planet-frame bands, not the full GBT
  L-band receiver range.
- All three ON scans belong to one approximately 29-minute ABACAD cadence on
  2016-05-05.
- The orbital model is a coordinate-transform hypothesis; it does not locate
  an emitter on GJ 649 b.
- The minimum empirical p-value measures departure from the circular-shift
  null. The morphology review identifies the departure as a non-unique
  receiver-frame feature under the frozen rules.
- The null result constrains only the frozen frequency windows, signal model,
  cadence, and measured sensitivity.

## Reproducibility

The public preregistration and execution commit is
`5f4ff886919465d2701dc4b4d3db34175f8d3db6`; the frozen configuration SHA-256
is `1dfe92deb385aa39f83af8b1c3c59f01ff8bc405c0c3b0c8671cc57307fd5783`.
`DATA_MANIFEST_M18.sha256` identifies the 30 primary slices;
`RESULTS_MANIFEST_M18.sha256` identifies all primary outputs. The candidate
investigation manifests identify six targeted cutouts and seven published
review outputs. Extracted telescope slices are not committed.
