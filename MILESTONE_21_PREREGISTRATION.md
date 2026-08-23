# Milestone 21 preregistration: HD 154345 b held-out detector-v0.5 validation

Status: **FROZEN BEFORE SPECTRAL EXTRACTION OR INSPECTION**.

Frozen configuration SHA-256:
`441597c69c1b3227648ee7aaf4bd6c8b0a09241c807755e03b355baa194b21e7`.

## Purpose and boundary

Milestone 21 is a new held-out application of detector v0.5.0. The target is
**HD 154345 / HIP 83389**, with HD 154345 b used only as the motion template.
The primary data are its sole complete compatible GBT L-band alternating
ON/OFF cadence, beginning 2016-03-23 12:15:06 UTC, archive cadence `--85132`.

Before this commit, only catalogue records, official orbit/host metadata, HTTP
object identities, HDF5 attributes and geometry, timestamps, and locally
calculated extraction geometry were read. No HD 154345 HDF5 `data` value was
indexed, extracted, plotted, summarized, or searched.

## Fixed selection

The target order and header-screen rule were published before ranks 11-15 were
opened. Rank 11, 14 Her, is technically ineligible because its complete fine
cadence spans 1797.949-2802.832 MHz and does not cover the frozen L-band
windows. HD 154345 at rank 12 is therefore the first compatible host, and its
sole qualifying cadence is selected without spectral inspection. The
qualifying rank 13 HD 87883 cadence remains spectrally untouched.

Selection provenance is preserved in `MILESTONE_21_TARGET_SELECTION.md`. The
official metadata query is GitHub Actions run `32622721356`, artifact
`9488841439`, digest
`sha256:02275d634e7d7bd59ee88c09766ba858bbb462ddc6cbb51d7e7774b9a6c1b6e6`.

## Frozen cadence and source identity

| Order | Role | Source | Header start MJD | Integrations | Duration (s) |
|---:|---|---|---:|---:|---:|
| 1 | ON | HIP83389 | 57470.510486111110 | 16 | 287.779586048 |
| 2 | OFF | HIP83389_OFF | 57470.514386574076 | 16 | 287.779586048 |
| 3 | ON | HIP83389 | 57470.518287037030 | 16 | 287.779586048 |
| 4 | OFF | HIP83389_OFF | 57470.522187500000 | 16 | 287.779586048 |
| 5 | ON | HIP83389 | 57470.526076388890 | 16 | 287.779586048 |
| 6 | OFF | HIP83389_OFF | 57470.529965277776 | 16 | 287.779586048 |

Every scan has shape `[16, 1, 264503296]`, float32 samples, 17.986224128 s
integrations, 2.835503418 Hz channels, and coverage from 1126.464846586 to
1876.464843750 MHz. All six identities, sizes, ETags, sources, times, and
geometry are frozen in `config/hd154345b_heldout_m21.json`.

## Mandatory extraction-coverage proof

Before this preregistration, `scripts/m14_coverage_preflight.py` evaluated all
21 frozen projected-scale/phase templates at all six scan times in all five
windows. All **630** checks passed without opening a remote file. The smallest
edge headroom is 255,833 channels, approximately 725.415 kHz.

The proof is run `32622969253`, artifact `9488916803`, verified digest
`sha256:881ff4af9af483323c55ae34ac357641936758b5ca52331c5b3606ff6d8d32ac`.
The result SHA-256 is
`aa76b849b7807169656213b7c34640e52f3201c7c87a8321a08ba686f3047dfe`.

## Target and orbital template

The official composite record supplies RA 17h02m36.59s, Dec +47d05m08.00s,
parallax 54.6636 mas, proper motion (+123.204, +853.742) mas/yr, and radial
velocity -47.3 km/s. The HD 154345 b working orbit has period 3,280 days,
semimajor axis 4.158 au, eccentricity 0.058, periastron epoch BJD 2458230.0,
and longitude of periastron 309 degrees. Its conservative full-projection
periastron drift proxy is 0.00163790 Hz/s at 1425 MHz. The orbit remains only a
coordinate-transform template and does not establish an emitter on the
planet.

## Frozen detector and windows

Detector v0.5.0 remains frozen at commit
`32720a0b5e097403f864e2b84d53a071d65d7c46`. Projected scales, phase offsets,
four intermittent activity subsets, S/N rules, moving RFI mask, widths
`[1, 3, 5, 9]`, candidate reduction, v0.5 OFF/receiver vetoes, 256 complete
scrambles, and the completeness grid are unchanged. The new fixed seeds are
`2120260823` for scrambles and `212120260823` for completeness.

| Window | Extraction range (MHz) | Search center (MHz) | Search half-width (kHz) |
|---|---:|---:|---:|
| `m21_1400p5` | 1399.2-1401.8 | 1400.5 | 500 |
| `m21_1406p5` | 1405.2-1407.8 | 1406.5 | 500 |
| `m21_1412p5` | 1411.2-1413.8 | 1412.5 | 500 |
| `m21_1418p5` | 1417.2-1419.8 | 1418.5 | 500 |
| `m21_1425p0` | 1423.7-1426.3 | 1425.0 | 500 |

## Decision rules

Extraction must fail closed on any identity or geometry mismatch. Detector
rules, thresholds, vetoes, templates, bands, seeds, and completeness may not
change in response to the data. A retained candidate is only a trigger for a
separately frozen within-cadence morphology review. With no second qualifying
HD 154345 cadence in the frozen screen, it cannot be called independently
recurrent without later public data. A null applies only to this frozen scope
and its measured completeness.
