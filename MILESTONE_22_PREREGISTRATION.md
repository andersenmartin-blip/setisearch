# Milestone 22 preregistration: HD 87883 b held-out detector-v0.5 validation

Status: **FROZEN BEFORE SPECTRAL EXTRACTION OR INSPECTION**.

Frozen configuration SHA-256:
`13870d7dd9b65bed2fc520211e701134bf4a7b9f9b19aa29e017fe3722430e49`.

## Purpose and boundary

Milestone 22 is a new held-out application of detector v0.5.0. The target is
**HD 87883 / HIP 49699**, with HD 87883 b used only as the motion template.
The primary data are its sole complete compatible GBT L-band alternating
ON/OFF cadence, beginning 2016-05-13 00:35:04 UTC, archive cadence `--70933`.

Before this commit, only catalogue records, official orbit/host metadata, HTTP
object identities, HDF5 attributes and geometry, timestamps, and locally
calculated extraction geometry were read. No HD 87883 HDF5 `data` value was
indexed, extracted, plotted, summarized, or searched.

## Fixed selection

The target order and header-screen rule were published before ranks 11-15 were
opened. Rank 11, 14 Her, is technically ineligible because its complete fine
cadence is S-band. HD 154345 at rank 12 was searched in Milestone 21, so the
retained complete L-band cadence for HD 87883 at rank 13 now advances
mechanically. Its second frozen cadence is S-band and cannot cover the
established search windows.

Selection provenance is preserved in `MILESTONE_22_TARGET_SELECTION.md`. The
official metadata query is GitHub Actions run `32640059392`, artifact
`9493355159`, digest
`sha256:f30a2f61c01bb68b5401bd6eeeecfb99324f866f7d787be06c6d71b8ed15f162`.

## Frozen cadence and source identity

| Order | Role | Source | Header start MJD | Integrations | Duration (s) |
|---:|---|---|---:|---:|---:|
| 1 | ON | HIP49699 | 57521.024351851855 | 16 | 287.779586048 |
| 2 | OFF | HIP48952 | 57521.028229166666 | 16 | 287.779586048 |
| 3 | ON | HIP49699 | 57521.032118055555 | 16 | 287.779586048 |
| 4 | OFF | HIP49056 | 57521.036226851850 | 16 | 287.779586048 |
| 5 | ON | HIP49699 | 57521.040324074070 | 16 | 287.779586048 |
| 6 | OFF | HIP49066 | 57521.044259259260 | 16 | 287.779586048 |

Every scan has shape `[16, 1, 318230528]`, float32 samples, 17.986224128 s
integrations, 2.835503418 Hz channels, and coverage from 1023.925784086 to
1926.269531250 MHz. All six identities, sizes, ETags, sources, times, and
geometry are frozen in `config/hd87883b_heldout_m22.json`.

## Mandatory extraction-coverage proof

Before this preregistration, `scripts/m14_coverage_preflight.py` evaluated all
21 frozen projected-scale/phase templates at all six scan times in all five
windows. All **630** checks passed without opening a remote file. The smallest
edge headroom is 235,988 channels, approximately 669.145 kHz.

The proof is run `32640347459`, artifact `9493430726`, verified digest
`sha256:1bcd5dc9578b82d3ee71fe5bcc6904b711c1c200ef8b0248ec967bd00e9ed4fe`.
The result SHA-256 is
`22f68786a3bd07fa67bd87b5405c1cd2a8c3c9557895a82cd66767aa84273e7e`.

## Target and orbital template

The official composite record supplies RA 10h08m43.06s, Dec +34d14m31.19s,
parallax 54.6421 mas, proper motion (-64.5653, -61.5815) mas/yr, and radial
velocity +9.30382 km/s. The HD 87883 b working orbit has period 3,006 days,
semimajor axis 3.77 au, eccentricity 0.72, periastron epoch BJD 2456913.0,
and longitude of periastron 282.1 degrees. Its conservative full-projection
periastron drift proxy is 0.0200124 Hz/s at 1425 MHz. The orbit remains only a
coordinate-transform template and does not establish an emitter on the
planet.

## Frozen detector and windows

Detector v0.5.0 remains frozen at commit
`32720a0b5e097403f864e2b84d53a071d65d7c46`. Projected scales, phase offsets,
four intermittent activity subsets, S/N rules, moving RFI mask, widths
`[1, 3, 5, 9]`, candidate reduction, v0.5 OFF/receiver vetoes, 256 complete
scrambles, and the completeness grid are unchanged. The new fixed seeds are
`2220260823` for scrambles and `222120260823` for completeness.

| Window | Extraction range (MHz) | Search center (MHz) | Search half-width (kHz) |
|---|---:|---:|---:|
| `m22_1400p5` | 1399.2-1401.8 | 1400.5 | 500 |
| `m22_1406p5` | 1405.2-1407.8 | 1406.5 | 500 |
| `m22_1412p5` | 1411.2-1413.8 | 1412.5 | 500 |
| `m22_1418p5` | 1417.2-1419.8 | 1418.5 | 500 |
| `m22_1425p0` | 1423.7-1426.3 | 1425.0 | 500 |

## Decision rules

Extraction must fail closed on any identity or geometry mismatch. Detector
rules, thresholds, vetoes, templates, bands, seeds, and completeness may not
change in response to the data. A retained candidate is only a trigger for a
separately frozen within-cadence morphology review. With no second compatible
HD 87883 cadence in the frozen screen, it cannot be called independently
recurrent without later public data. A null applies only to this frozen scope
and its measured completeness.
