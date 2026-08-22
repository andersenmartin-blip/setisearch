# Milestone 20 preregistration: rho CrB c held-out detector-v0.5 validation

Status: **FROZEN BEFORE SPECTRAL EXTRACTION OR INSPECTION**.

Frozen configuration SHA-256:
`d631241a0b55c8a0c3f81d795ad19e2ccb4946918d57431d2817bc785a591696`.

## Purpose and boundary

Milestone 20 is a new held-out application of detector v0.5.0. The target is
**rho CrB / HIP 78459**, with rho CrB c used only as the motion template. The
primary data are its sole complete compatible GBT L-band ABACAD cadence,
beginning 2016-05-25 05:27:54 UTC, archive cadence `--71771`.

Before this commit, only catalogue records, official orbit/host metadata, HTTP
object identities, HDF5 attributes and geometry, timestamps, and locally
calculated extraction geometry were read. No rho CrB HDF5 `data` value was
indexed, extracted, plotted, summarized, or searched.

## Fixed selection

The target order and header-screen rule were published before ranks 6-10 were
opened. After the rank 8 47 UMa search completed, rank 9 HD 48948 remained
ineligible because its cadence is S-band only. Rho CrB at rank 10 is the next
and only remaining compatible L-band host in that frozen block, so its sole
qualifying cadence is selected without spectral inspection.

Selection provenance is preserved in `MILESTONE_20_TARGET_SELECTION.md`. The
official metadata query is GitHub Actions run `32589126755`, artifact
`9479829685`, digest
`sha256:7bf61f444c49b1c8491e94cf6f334cb3874bc41b951c94ba71f492bb27018323`.

## Frozen cadence and source identity

| Order | Role | Source | Header start MJD | Integrations | Duration (s) |
|---:|---|---|---:|---:|---:|
| 1 | ON | HIP78459 | 57533.227708333330 | 16 | 287.779586048 |
| 2 | OFF | HIP78859 | 57533.231655092590 | 16 | 287.779586048 |
| 3 | ON | HIP78459 | 57533.235636574070 | 16 | 287.779586048 |
| 4 | OFF | HIP78931 | 57533.239513888890 | 16 | 287.779586048 |
| 5 | ON | HIP78459 | 57533.243402777780 | 16 | 287.779586048 |
| 6 | OFF | HIP79053 | 57533.247453703705 | 16 | 287.779586048 |

Every scan has shape `[16, 1, 318230528]`, float32 samples, 17.986224128 s
integrations, 2.835503418 Hz channels, and coverage from 1023.925784086 to
1926.269531250 MHz. All six identities, sizes, ETags, sources, times, and
geometry are frozen in `config/rhocrbc_heldout_m20.json`.

## Mandatory extraction-coverage proof

Before this preregistration, `scripts/m14_coverage_preflight.py` evaluated all
21 frozen projected-scale/phase templates at all six scan times in all five
windows. All **630** checks passed without opening a remote file. The smallest
edge headroom is 210,329 channels, approximately 596.389 kHz.

The proof is run `32589341938`, artifact `9479885796`, digest
`sha256:6d2e6b67ae14b7db804b5a2249685f36b75690020ec1ebdbb6e9d023dd8de47e`.
The result SHA-256 is
`59a278f75c1a18a11279b68c37a1f0b83185b0feb758d8b00109c9a6f131d507`.

## Target and orbital template

The official composite record supplies RA 16h01m02.42s, Dec +33d18m00.67s,
parallax 57.2216 mas, proper motion (-198.536, -772.415) mas/yr, and radial
velocity +17.8 km/s. The rho CrB c working orbit has period 102.036 days,
semimajor axis 0.4206 au, eccentricity 0.048, periastron epoch BJD
2455480.216, and longitude of periastron 244.4 degrees. Its conservative
full-projection periastron drift proxy is 0.16763 Hz/s at 1425 MHz. The orbit
remains only a coordinate-transform template and does not establish an emitter
on the planet.

## Frozen detector and windows

Detector v0.5.0 remains frozen at commit
`32720a0b5e097403f864e2b84d53a071d65d7c46`. Projected scales, phase offsets,
activity subsets, S/N rules, moving RFI mask, widths `[1, 3, 5, 9]`, candidate
reduction, v0.5 vetoes, 256 scrambles, and the completeness grid are unchanged.
The new fixed seeds are `2020260822` for scrambles and `202020260822` for
completeness.

| Window | Extraction range (MHz) | Search center (MHz) | Search half-width (kHz) |
|---|---:|---:|---:|
| `m20_1400p5` | 1399.2-1401.8 | 1400.5 | 500 |
| `m20_1406p5` | 1405.2-1407.8 | 1406.5 | 500 |
| `m20_1412p5` | 1411.2-1413.8 | 1412.5 | 500 |
| `m20_1418p5` | 1417.2-1419.8 | 1418.5 | 500 |
| `m20_1425p0` | 1423.7-1426.3 | 1425.0 | 500 |

## Decision rules

Extraction must fail closed on any identity or geometry mismatch. Detector
rules, thresholds, vetoes, templates, bands, seeds, and completeness may not
change in response to the data. A retained candidate is only a trigger for a
separately frozen within-cadence morphology review. With no second qualifying
rho CrB cadence in the frozen screen, it cannot be called independently
recurrent without later public data. A null applies only to this frozen scope
and its measured completeness.
