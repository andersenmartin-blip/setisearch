# Milestone 33 preregistration: HD 3651 b higher-smearing held-out validation

Status: **FROZEN BEFORE SPECTRAL EXTRACTION OR INSPECTION**.

Frozen configuration SHA-256:
`aaf4e2d53a4b95bb4428195d2567b9d3a8f8f60b62de104d8879c018b320971a`.

## Purpose and boundary

Milestone 33 is the third held-out application of detector v0.5.0 in the
prospectively frozen higher-smearing extension. The target is **HD 3651 /
HIP 3093**, with HD 3651 b used only as the motion template. The primary data
are its sole complete compatible GBT L-band alternating ON/control cadence,
archive cadence `--73274`, beginning 2016-06-18 13:51:06 UTC.

Before this commit, only the frozen discovery and header-screen records,
official orbit and host metadata, HTTP object identities, HDF5 attributes and
geometry, timestamps, and calculated extraction geometry were read. No
HD 3651 HDF5 `data` value was indexed, extracted, plotted, summarized, or
searched.

## Fixed extension and selection

Milestones 31 and 32 consumed extension ranks 31 and 33, while rank 32 had no
qualifying L-band cadence. HD 3651 at frozen rank 34 is therefore the next
eligible untouched host. Rank 35 does not qualify, so HD 3651 is also the last
eligible host in the already frozen ranks 31--35 extension. Selection
provenance is in `MILESTONE_33_TARGET_SELECTION.md` and the immutable
Milestone 31 header screen, workflow run `32867230503`, artifact `9570603163`,
digest
`sha256:2535ae0c218bb6418f6001374445b620ad8d808c6ab51e8fa9ecb85cae7e1ce0`.

## Frozen primary cadence and source identity

| Order | Role | Source | Header start MJD | Integrations | Duration (s) |
|---:|---|---|---:|---:|---:|
| 1 | ON | HIP3093 | 57557.577152777776 | 16 | 292.057776128 |
| 2 | control | HIP2023 | 57557.581168981480 | 16 | 292.057776128 |
| 3 | ON | HIP3093 | 57557.585185185184 | 16 | 292.057776128 |
| 4 | control | HIP2206 | 57557.589201388890 | 16 | 292.057776128 |
| 5 | ON | HIP3093 | 57557.593206018515 | 16 | 292.057776128 |
| 6 | control | HIP2360 | 57557.597233796296 | 16 | 292.057776128 |

Every scan has shape `[16, 1, 322961408]`, float32 samples, 18.253611008 s
integrations, 2.793967724 Hz channels, and coverage from 1023.925784044 to
1926.269531250 MHz. URLs, sizes, ETags, sources, times, and geometry are frozen
in `config/hd3651b_heldout_m33.json`.

## Mandatory motion-plus-width coverage proof

`scripts/m33_coverage_preflight.py` evaluated all 21 frozen projected-scale
and phase templates at all six scan times in all five windows, adding the
16-channel half-width required by the widest 33-channel boxcar. All **630**
checks passed without opening a remote file. The largest within-scan
dedoppler margin is 57 channels. After motion and width margins, the smallest
extraction-edge headroom is 163,266 channels, approximately 456.130 kHz.

The proof is run `32938783093`, artifact `9595786102`, verified digest
`sha256:f0d4ed0bfbf9e03ae9207225231006d7c3cad80a00748a321a1582d8e368a8cc`.
The result SHA-256 is
`f72ac244af604b908ed641b41734212e56dc9dacff2c8246956e83f57545b47f`.

## Target and orbital template

The official composite record supplies RA 00h39m21.29s, Dec +21d14m55.98s,
parallax 89.7891 mas, proper motion (-462.056, -369.814) mas/yr, and radial
velocity -33.5 km/s. The HD 3651 b working orbit has period 62.25 days,
semimajor axis 0.295 au, eccentricity 0.645, periastron epoch BJD 2453932.2,
and longitude of periastron 243.0 degrees. Its conservative full-projection
periastron drift proxy is 2.27163433 Hz/s at 1425 MHz. The orbit is only a
coordinate-transform template.

The exact official metadata query is workflow run `32930265472`, artifact
`9592949499`, digest
`sha256:cbcd897834ee31fa5b081ea3b864fa0d9451d172626c75ab87b146e9831f75d2`.
Its preserved record SHA-256 is
`164167a8fc98574f76e0f7f0bfc4dd3479a61568a4d55daf0fa160209bd17ec6`.

## Frozen detector and higher-smearing method

Detector software v0.5.0 remains frozen at commit
`32720a0b5e097403f864e2b84d53a071d65d7c46`. Projected scales, phase offsets,
four intermittent activity subsets, S/N rules, moving RFI mask, clustering,
physical OFF/receiver vetoes, 256 complete scrambles, and the completeness
procedure are unchanged from Milestones 31 and 32.

The prospectively frozen boxcar bank remains `[1, 3, 5, 9, 17, 33]` channels.
The report cap is 1600, exceeding the finite maximum of 1512 retained
pre-clustering peaks per window, so the disposition record cannot be
truncated. Fresh fixed seeds are `3320260826` for scrambles and
`332120260826` for completeness.

| Window | Extraction range (MHz) | Search center (MHz) | Search half-width (kHz) |
|---|---:|---:|---:|
| `m33_1400p5` | 1399.2--1401.8 | 1400.5 | 500 |
| `m33_1406p5` | 1405.2--1407.8 | 1406.5 | 500 |
| `m33_1412p5` | 1411.2--1413.8 | 1412.5 | 500 |
| `m33_1418p5` | 1417.2--1419.8 | 1418.5 | 500 |
| `m33_1425p0` | 1423.7--1426.3 | 1425.0 | 500 |

## Decision and stopping rules

Extraction fails closed on any identity or geometry mismatch. Detector rules,
thresholds, vetoes, templates, bands, widths, seeds, completeness, and report
retention may not change in response to data. A cluster above the empirical
global threshold survives only if none of the frozen matched-control,
single-adjacent-control, local-control, or receiver-frame-alias vetoes applies.

No survivor closes Milestone 33 as a primary-cadence null result. Any survivor
must remain an unresolved candidate requiring genuinely independent data. No
second qualifying HD 3651 cadence exists, so this milestone cannot perform or
claim independent recurrence. Any conclusion is limited to the frozen scope
and measured completeness.
