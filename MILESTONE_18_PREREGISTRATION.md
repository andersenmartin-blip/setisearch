# Milestone 18 preregistration: GJ 649 b held-out detector-v0.5 validation

Status: **FROZEN BEFORE SPECTRAL EXTRACTION OR INSPECTION**.

Frozen configuration SHA-256:
`1dfe92deb385aa39f83af8b1c3c59f01ff8bc405c0c3b0c8671cc57307fd5783`.

## Purpose and boundary

Milestone 18 is a new held-out application of detector v0.5.0. The target is
**GJ 649 / HIP 83043**, with GJ 649 b used only as the motion template. The
primary data are the sole complete compatible GBT L-band ABACAD cadence,
beginning 2016-05-05 08:30:39 UTC, archive cadence `--70291`.

Before this commit, only catalogue records, official orbit/host metadata, HTTP
object identities, HDF5 attributes and geometry, timestamps, and locally
calculated extraction geometry were read. No GJ 649 HDF5 `data` value was
indexed, extracted, plotted, summarized, or searched.

## Fixed selection

The preregistered Milestone 16 low-smearing ranking and corrected header screen
placed GJ 649 fifth. GJ 876 and GJ 514 had only S-band products, while
HD 219134 and GJ 849 were completed in Milestones 16 and 17. GJ 649 is
therefore the next still-unsearched compatible L-band host. Its single
qualifying cadence is the primary held-out data set.

Selection provenance is preserved in `MILESTONE_18_TARGET_SELECTION.md`. The
official metadata query is GitHub Actions run `32573795526`, artifact
`9476012601`, digest
`sha256:79d04eb271fb0f492ae8cf6550b180b69160cc64363992871ad3b6bd98f3220f`.

## Frozen cadence and source identity

| Order | Role | Source | Header start MJD | Integrations | Duration (s) |
|---:|---|---|---:|---:|---:|
| 1 | ON | HIP83043 | 57513.354618055560 | 16 | 287.779586048 |
| 2 | OFF | HIP82185 | 57513.358726851850 | 16 | 287.779586048 |
| 3 | ON | HIP83043 | 57513.362824074070 | 16 | 287.779586048 |
| 4 | OFF | HIP82240 | 57513.366875000000 | 16 | 287.779586048 |
| 5 | ON | HIP83043 | 57513.370925925930 | 16 | 287.779586048 |
| 6 | OFF | HIP82354 | 57513.374976851854 | 16 | 287.779586048 |

Every scan has shape `[16, 1, 318230528]`, float32 samples, 17.986224128 s
integrations, 2.835503418 Hz channels, and coverage from 1023.925784086 to
1926.269531250 MHz. All six identities, sizes, ETags, sources, times, and
geometry are frozen in `config/gj649b_heldout_m18.json`.

## Mandatory extraction-coverage proof

Before this preregistration, `scripts/m14_coverage_preflight.py` evaluated all
21 frozen projected-scale/phase templates at all six scan times in all five
windows. All **630** checks passed without opening a remote file. The smallest
edge headroom is 258,750 channels, approximately 733.687 kHz.

The proof is run `32573991635`, artifact `9476065546`, digest
`sha256:9bcd0023697bedf328caa09e3db15ba1791ac65956b27ac6b7f7b26056df053b`.
The result SHA-256 is
`1bc38620aaaf3def0c2ec3d6fbfd742508f066909b1292f1358ad90880c5c42c`.

## Target and orbital template

The official composite record supplies RA 16h58m08.72s, Dec +25d44m31.10s,
parallax 96.3141 mas, proper motion (-115.479, -507.887) mas/yr, and radial
velocity +3.56586 km/s. The GJ 649 b working orbit has period 600.1 days,
semimajor axis 1.112 au, eccentricity 0.083, periastron epoch BJD 2412876.0,
and longitude of periastron 3 degrees. Its conservative full-projection
periastron drift proxy is 0.01381 Hz/s at 1425 MHz. The orbit remains only a
coordinate-transform template and does not establish an emitter on the planet.

## Frozen detector and windows

Detector v0.5.0 remains frozen at commit
`32720a0b5e097403f864e2b84d53a071d65d7c46`. Projected scales, phase offsets,
activity subsets, S/N rules, moving RFI mask, widths `[1, 3, 5, 9]`, candidate
reduction, v0.5 vetoes, 256 scrambles, and the completeness grid are unchanged.
The new fixed seeds are `1820260822` for scrambles and `181820260822` for
completeness.

| Window | Extraction range (MHz) | Search center (MHz) | Search half-width (kHz) |
|---|---:|---:|---:|
| `m18_1400p5` | 1399.2-1401.8 | 1400.5 | 500 |
| `m18_1406p5` | 1405.2-1407.8 | 1406.5 | 500 |
| `m18_1412p5` | 1411.2-1413.8 | 1412.5 | 500 |
| `m18_1418p5` | 1417.2-1419.8 | 1418.5 | 500 |
| `m18_1425p0` | 1423.7-1426.3 | 1425.0 | 500 |

## Decision rules

Extraction must fail closed on any identity or geometry mismatch. Detector
rules, thresholds, vetoes, templates, bands, seeds, and completeness may not
change in response to the data. A retained candidate is only a trigger for a
separately frozen within-cadence morphology review. With no second qualifying
cadence in the frozen screen, it cannot be called independently recurrent
without later public data. A null applies only to the frozen scope and measured
completeness.
