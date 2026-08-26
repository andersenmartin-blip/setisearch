# Milestone 36 ranks 36--40 high-smearing HDF5-header-only extension

Status: **FROZEN BEFORE ANY RANK 36--40 TELESCOPE PRODUCT IS OPENED**.

Milestone 34 closed the two legacy report-cap gaps and explicitly left ranks
36--40 both header-wise and spectrally untouched. Milestone 35 was a
retrospective synthesis and opened no new target or cadence. Milestone 36 now
advances mechanically to the next five unique hosts in the already committed
Milestone 16 discovery order. This stage is metadata-only; it cannot produce a
candidate, change Milestone 33, or revise the conditional Milestone 35 bounds.

## Frozen extension

| Extension rank | Archive target | Planet motion template | Drift proxy at 1425 MHz (Hz/s) | Frozen catalogue cadence IDs |
|---:|---|---|---:|---|
| 36 | HIP48714 | HIP 48714 b | 5.30654596 | `--68360`, `--76348` |
| 37 | HIP84607 | HD 156668 b | 8.71278306 | `--85168` |
| 38 | HIP1499 | HD 1461 b | 10.43998800 | `--71139` |
| 39 | HIP113357 | 51 Peg b | 11.06369758 | `--80977` |
| 40 | HIP67275 | tau Boo b | 17.16939041 | `--68396` |

The source is `results_m16_discovery/discovery.json`, SHA-256
`0310d5ba8e0923062bd0a046b1827a4e814fc3f3adf854620d27e3cccb7fd750`.
Targets are not re-queried or reranked. The unique-host normalization and
deduplication rule is unchanged from Milestone 31. The exact compact records
above are asserted in code before any remote request.

## Frozen qualification and selection rule

This stage may read the public cadence catalogue, HTTP object identity, HDF5
root and dataset attributes, dataset geometry, timing, and frequency coverage.
It may not index or read any HDF5 `data` value. Every recursive result record
must preserve `spectral_dataset_values_read: false` wherever that boundary is
represented.

A cadence qualifies only if six current fine HDF5 products:

- form a time-ordered three-ON/three-OFF alternating sequence within 0.04 day;
- have identical shape, dtype, integration time, and channel width;
- respond without header errors and support the established remote HDF5
  header adapter; and
- cover 1399.65--1425.85 MHz, containing all five established one-megahertz
  search windows and their guards.

All listed cadence IDs for all five hosts are screened. The first host in the
frozen extension order with a qualifying cadence is selected; its earliest
qualifying cadence becomes the prospective blind primary search. Any further
qualifying cadence for that host remains reserved and spectrally untouched.
An incomplete catalogue response, fine-HDF5 enumeration, or HDF5-header probe
is a hard technical failure rather than evidence of ineligibility, so a
higher-ranked host cannot be selected by silently skipping a failed probe. If
all probes succeed but none qualifies, Milestone 36 stops without spectral
contact.

## Prospectively frozen high-smearing adaptation

Detector software remains v0.5.0. The only permitted target-search adaptation
is the config-driven odd boxcar bank
`[1, 3, 5, 9, 17, 33, 65, 129]` and a per-window report cap of **2200**.

This is fixed before header access. Using the most conservative rank-40 drift
proxy and the largest fine-L-band time/channel ratio already published in this
repository (18.253611008 s / 2.7939677238464355 Hz), the maximum proxy sweep is
112.1715 native channels per integration, inside the 129-channel template.
Rank 36 already reaches about 34.6689 channels, so the previous 33-channel bank
is not sufficient for this block.

With eight widths, 21 motion templates, four activity subsets, and three
retained peaks per hypothesis, the finite pre-clustering maximum is 2016 peaks
per window. The cap of 2200 is therefore non-truncating. A later selected-
target coverage proof must still verify all exact scan geometries, orbital
tracks, extraction guards, and the 129-channel half-width before any spectral
value is opened. Failure of that proof is a technical stop, not permission to
adapt the bank after seeing spectra.

The orbital scale/phase grid, activity subsets, recurrence statistic,
single-epoch mask, physical OFF-source vetoes, 256 scrambles, completeness
trial structure, five outcome windows, and candidate rules otherwise remain
unchanged. Fresh random seeds and a target-specific config must be committed
only after selection and official metadata retrieval.

## Sequential boundary

The header screen publishes the complete technical record and then stops.
Only after that publication may the selected planet's exact official orbit and
host astrometry be queried. A width-aware coverage proof and a separate
target-specific preregistration must then be committed before extracting any
spectral slice. No M33 candidate disposition and no M35 inference changes in
this stage.

Frozen at 2026-08-26T15:19:23.320Z.
